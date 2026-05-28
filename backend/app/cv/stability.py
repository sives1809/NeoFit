"""
cv/stability.py
---------------
Rolling measurement buffer with IQR-based outlier rejection and
variance-based stability detection for auto-capture.

Why this replaces the prototype's simple median buffer
------------------------------------------------------
The prototype used a 12-frame rolling median, which is a good start but
has two weaknesses:
  1. A single extreme outlier (e.g. landmark blip) can still shift the
     median if it repeats a few times in the window.
  2. There was no way to know whether the displayed value was "stable
     enough to capture" — the user had to judge manually.

This module adds:
  • IQR outlier rejection: per-metric, frames outside Q1 ± 1.5 × IQR
    are excluded from the statistics.
  • Stability scoring: the coefficient of variation (CV = σ/μ) of the
    retained samples determines a per-frame stability score.
  • Consecutive-stable counter: only increments when CV is below a
    threshold for ALL key metrics simultaneously.
  • Auto-capture gate: returns True once the counter exceeds
    STABLE_FOR_N_FRAMES, then resets so the next capture requires a
    fresh stability window.

Typical usage (in a request handler called once per webcam frame):
    buf = StabilityBuffer()                # one instance per session
    ...
    buf.add(measurement_px_dict)
    result = buf.status()
    if result["ready"]:
        commit_capture(result["filtered"])
"""

from __future__ import annotations

from collections import deque
from statistics import median
from typing import Optional

import numpy as np


# ── Tuneable constants ────────────────────────────────────────────────────────

BUFFER_SIZE: int = 20
"""How many frames to keep in the rolling window."""

STABILITY_CV_THRESHOLD: float = 0.025
"""Max acceptable coefficient of variation (σ/μ) for 'stable' measurements.
2.5 % works well for arm/thigh at typical webcam frame rates."""

STABLE_FOR_N_FRAMES: int = 8
"""How many consecutive stable frames before auto-capture triggers.
At ~4 API frames/s this corresponds to ~2 seconds of stability."""

KEY_METRICS: tuple[str, ...] = (
    "arm_left_px", "arm_right_px",
    "shoulder_px",
    "thigh_left_px", "thigh_right_px",
)
"""Metrics that MUST all be stable before auto-capture fires."""


# ── IQR filtering ─────────────────────────────────────────────────────────────

def _iqr_filter(values: list[float]) -> list[float]:
    """
    Remove outliers from a list using Tukey's 1.5 × IQR fence.
    Returns the original list unchanged if fewer than 4 samples are present
    (not enough data to compute reliable quartiles).
    """
    if len(values) < 4:
        return values
    q1, q3 = float(np.percentile(values, 25)), float(np.percentile(values, 75))
    iqr = q3 - q1
    fence_lo = q1 - 1.5 * iqr
    fence_hi = q3 + 1.5 * iqr
    filtered = [v for v in values if fence_lo <= v <= fence_hi]
    # Safety: if the filter removed everything, return originals
    return filtered if filtered else values


def _coefficient_of_variation(values: list[float]) -> float:
    """
    CV = σ / μ.  Returns 0 for a single-element list, inf if mean is zero.
    """
    if len(values) < 2:
        return 0.0
    mu = float(np.mean(values))
    if mu == 0:
        return float("inf")
    return float(np.std(values)) / mu


# ── StabilityBuffer ────────────────────────────────────────────────────────────

class StabilityBuffer:
    """
    Rolling buffer that tracks measurement stability and fires an auto-capture
    signal when all key metrics have been stable for STABLE_FOR_N_FRAMES
    consecutive valid frames.

    Thread safety: NOT thread-safe. One instance should be used per active
    measurement session (i.e. per connected websocket or per sequential
    request chain managed by the frontend).
    """

    def __init__(
        self,
        buffer_size: int = BUFFER_SIZE,
        cv_threshold: float = STABILITY_CV_THRESHOLD,
        stable_for: int = STABLE_FOR_N_FRAMES,
        key_metrics: tuple[str, ...] = KEY_METRICS,
    ) -> None:
        self._buffer: deque[dict] = deque(maxlen=buffer_size)
        self._cv_threshold = cv_threshold
        self._stable_for = stable_for
        self._key_metrics = key_metrics
        self._consecutive_stable: int = 0
        self._fired: bool = False   # True once per stability window

    # ── Public API ────────────────────────────────────────────────────────────

    def add(self, measurement: dict[str, Optional[float]]) -> None:
        """
        Push a new raw measurement dict into the buffer.
        Frames with ANY None in the key metrics are silently dropped,
        because a None means a required landmark was occluded.
        """
        if any(measurement.get(k) is None for k in self._key_metrics):
            self._consecutive_stable = 0  # lost tracking → reset counter
            return
        self._buffer.append(measurement)

    def status(self) -> dict:
        """
        Compute and return the current stability status.

        Returns
        -------
        {
            "ready":       bool   — True exactly once per stability event
            "stable":      bool   — True while CV < threshold for all keys
            "progress":    float  — 0.0–1.0, fraction of stable window complete
            "filtered":    dict   — IQR-filtered median measurements (or {})
            "cv":          dict   — per-metric CV (for debugging / UI feedback)
            "frame_count": int    — number of frames currently in buffer
        }
        """
        if not self._buffer:
            return self._empty_status()

        filtered_medians, cvs = self._compute_stats()

        all_stable = all(
            cvs.get(k, float("inf")) < self._cv_threshold
            for k in self._key_metrics
        )

        if all_stable:
            self._consecutive_stable += 1
        else:
            self._consecutive_stable = 0
            self._fired = False

        progress = min(self._consecutive_stable / self._stable_for, 1.0)
        ready = False

        if self._consecutive_stable >= self._stable_for and not self._fired:
            ready = True
            self._fired = True          # won't fire again until reset()
            self._consecutive_stable = 0  # start a fresh window

        return {
            "ready":       ready,
            "stable":      all_stable,
            "progress":    round(progress, 3),
            "filtered":    filtered_medians,
            "cv":          cvs,
            "frame_count": len(self._buffer),
        }

    def reset(self) -> None:
        """Clear the buffer and reset the stability counter. Call this after a capture."""
        self._buffer.clear()
        self._consecutive_stable = 0
        self._fired = False

    def reset_counter(self) -> None:
        """Reset the consecutive stable counter without clearing the buffer."""
        self._consecutive_stable = 0

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _compute_stats(self) -> tuple[dict, dict]:
        """
        For each measurement key, collect all buffered values, IQR-filter them,
        and return (median_dict, cv_dict).
        """
        if not self._buffer:
            return {}, {}

        all_keys = self._buffer[0].keys()
        filtered_medians: dict[str, float] = {}
        cvs: dict[str, float] = {}

        for key in all_keys:
            if key == "orientation":
                filtered_medians[key] = self._buffer[-1][key] if self._buffer else None
                continue
            raw_values = [
                frame[key]
                for frame in self._buffer
                if frame.get(key) is not None
            ]
            if not raw_values:
                continue
            clean = _iqr_filter(raw_values)
            filtered_medians[key] = median(clean)
            cvs[key] = _coefficient_of_variation(clean)

        return filtered_medians, cvs

    def _empty_status(self) -> dict:
        return {
            "ready": False,
            "stable": False,
            "progress": 0.0,
            "filtered": {},
            "cv": {},
            "frame_count": 0,
        }
