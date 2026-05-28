"""
cv/scaling.py
-------------
Convert pixel measurements to real-world centimetres using the subject's
declared height as the only external reference — no physical ruler needed.

The geometric model (unchanged from the desktop prototype):
    The nose-to-midankle pixel distance corresponds to approximately 93 % of
    the subject's standing height. This factor was empirically validated on
    the prototype and matches published anthropometric proportions.

    scale (cm/px) = (height_cm × NOSE_ANKLE_FRACTION) / ref_px

All per-side values are converted independently, which lets downstream code
compute asymmetry percentages without any additional processing.
"""

from __future__ import annotations

from typing import Optional

# Fraction of standing height represented by nose → mid-ankle span.
# Validated in prototype; consistent with Drillis & Contini (1966) proportions.
NOSE_ANKLE_FRACTION: float = 0.93


def compute_scale(ref_px: float, height_cm: float) -> float:
    """
    Return cm-per-pixel given the nose→ankle pixel distance and the
    subject's declared height.

    Returns 0.0 if either input is invalid, so callers can safely
    multiply without a division-by-zero guard.
    """
    if ref_px <= 0 or height_cm <= 0:
        return 0.0
    return (height_cm * NOSE_ANKLE_FRACTION) / ref_px


def px_to_cm(px: Optional[float], scale: float) -> Optional[float]:
    """Apply scale factor to a single measurement. Passes through None."""
    if px is None or scale <= 0:
        return None
    return px * scale


def convert_all(
    m_px: dict[str, Optional[float]],
    height_cm: float,
) -> dict[str, Optional[float]]:
    """
    Convert a full pixel-measurement dict (output of all_measurements_px)
    into centimetres.

    Returns a new dict with _px suffixes replaced by _cm.
    Non-measurement keys (tilt_deg, confidence, ref_px) are passed through
    unchanged because they are dimensionless or already in natural units.
    """
    ref = m_px.get("ref_px")
    if ref is None:
        # Cannot scale anything — ref landmark occluded
        return {}

    scale = compute_scale(ref, height_cm)

    cm: dict[str, Optional[float]] = {
        "arm_left_cm":        px_to_cm(m_px.get("arm_left_px"),        scale),
        "arm_right_cm":       px_to_cm(m_px.get("arm_right_px"),       scale),
        "shoulder_cm":        px_to_cm(m_px.get("shoulder_px"),        scale),
        "chest_cm":           px_to_cm(m_px.get("chest_px"),           scale),
        "waist_cm":           px_to_cm(m_px.get("waist_px"),           scale),
        "hip_cm":             px_to_cm(m_px.get("hip_px"),             scale),
        "thigh_left_cm":      px_to_cm(m_px.get("thigh_left_px"),      scale),
        "thigh_right_cm":     px_to_cm(m_px.get("thigh_right_px"),     scale),
        
        # Side thicknesses
        "arm_side_left_cm":   px_to_cm(m_px.get("arm_side_left_px"),   scale),
        "arm_side_right_cm":  px_to_cm(m_px.get("arm_side_right_px"),  scale),
        "thigh_side_left_cm":  px_to_cm(m_px.get("thigh_side_left_px"),  scale),
        "thigh_side_right_cm": px_to_cm(m_px.get("thigh_side_right_px"), scale),
        "chest_side_cm":       px_to_cm(m_px.get("chest_side_px"),       scale),
        "waist_side_cm":       px_to_cm(m_px.get("waist_side_px"),       scale),
        "hip_side_cm":         px_to_cm(m_px.get("hip_side_px"),         scale),

        # Pass-through dimensionless fields
        "tilt_deg":           m_px.get("tilt_deg"),
        "shoulder_h_ratio":   m_px.get("shoulder_h_ratio"),
        "confidence":         m_px.get("confidence"),
        "scale_cm_per_px":    scale,
    }
    return cm


def asymmetry_pct(left: Optional[float], right: Optional[float]) -> Optional[float]:
    """
    Compute asymmetry as a percentage of the average:
        |L − R| / mean(L, R) × 100

    Returns None if either side is unavailable.
    A value above ~5 % is worth flagging to the user.
    """
    if left is None or right is None or (left + right) == 0:
        return None
    return abs(left - right) / ((left + right) / 2) * 100
