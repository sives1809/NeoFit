"""
models/measure.py
-----------------
Pydantic request/response models for the /measure endpoints.

The frontend sends MediaPipe Pose landmarks (extracted in-browser by
MediaPipe JS) as JSON. The backend does all the CV math in Python.
"""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator


class LandmarkIn(BaseModel):
    """Single MediaPipe Pose landmark in normalised coordinates [0, 1]."""
    x: float = Field(..., ge=0.0, le=1.0)
    y: float = Field(..., ge=0.0, le=1.0)
    z: float = 0.0
    visibility: float = Field(default=1.0, ge=0.0, le=1.0)


class MeasureRequest(BaseModel):
    """
    Payload sent from the webcam component on every frame.

    landmarks:    33 MediaPipe Pose landmarks in order (index 0-32).
    height_cm:    User's declared height — used for px→cm scaling.
    video_width:  Actual pixel width of the captured video stream.
    video_height: Actual pixel height of the captured video stream.
    mode:         'front' or 'left_side' or 'right_side' — determines which validation rule applies.
    """
    landmarks: list[LandmarkIn] = Field(..., min_length=33, max_length=33)
    height_cm: float = Field(..., gt=0, le=250)
    video_width: int = Field(default=640, gt=0)
    video_height: int = Field(default=480, gt=0)
    mode: Literal["front", "left_side", "right_side"] = "front"
    silhouette_chest_px: Optional[float] = None
    silhouette_waist_px: Optional[float] = None
    silhouette_hip_px: Optional[float] = None
    silhouette_arm_left_px: Optional[float] = None
    silhouette_arm_right_px: Optional[float] = None

    @field_validator("landmarks")
    @classmethod
    def must_have_33(cls, v: list) -> list:
        if len(v) != 33:
            raise ValueError("MediaPipe Pose always returns exactly 33 landmarks")
        return v



class ValidationResult(BaseModel):
    """Whether the current frame passes pose validation for the given mode."""
    ok: bool
    reason: str = ""  # human-readable rejection reason if ok=False


class MeasureResponse(BaseModel):
    """
    Per-frame measurement result returned to the frontend.

    All _cm fields may be None if a required landmark was occluded.
    The frontend should accumulate these over time and trigger capture
    when stability.ready is True.
    """
    # Pose validation for this frame
    validation: ValidationResult

    # Front-view centimetres (None = occluded or invalid frame)
    arm_left_cm:    Optional[float] = None
    arm_right_cm:   Optional[float] = None
    shoulder_cm:    Optional[float] = None
    chest_cm:       Optional[float] = None
    waist_cm:       Optional[float] = None
    hip_cm:         Optional[float] = None
    thigh_left_cm:  Optional[float] = None
    thigh_right_cm: Optional[float] = None

    # Side-view thicknesses (None = occluded or invalid frame)
    arm_side_left_cm:    Optional[float] = None
    arm_side_right_cm:   Optional[float] = None
    thigh_side_left_cm:  Optional[float] = None
    thigh_side_right_cm: Optional[float] = None
    chest_side_cm:       Optional[float] = None
    waist_side_cm:       Optional[float] = None
    hip_side_cm:         Optional[float] = None

    # Quality metadata
    confidence: Optional[float] = None     # mean landmark visibility [0,1]
    scale_cm_per_px: Optional[float] = None

    # Stability signal for auto-capture
    stability_progress: float = 0.0        # 0.0–1.0
    ready_to_capture: bool = False


class CapturePayload(BaseModel):
    """
    The stable, IQR-filtered measurement values the frontend
    submits when the auto-capture gate fires.
    """
    arm_left_cm:    Optional[float] = None
    arm_right_cm:   Optional[float] = None
    shoulder_cm:    Optional[float] = None
    chest_cm:       Optional[float] = None
    waist_cm:       Optional[float] = None
    hip_cm:         Optional[float] = None
    thigh_left_cm:  Optional[float] = None
    thigh_right_cm: Optional[float] = None

    arm_side_left_cm:    Optional[float] = None
    arm_side_right_cm:   Optional[float] = None
    thigh_side_left_cm:  Optional[float] = None
    thigh_side_right_cm: Optional[float] = None
    chest_side_cm:       Optional[float] = None
    waist_side_cm:       Optional[float] = None
    hip_side_cm:         Optional[float] = None

    confidence:      Optional[float] = None
    scale_cm_per_px: Optional[float] = None
    frames_averaged: int = 0


class CombineRequest(BaseModel):
    """Payload to combine Front, Left Side, and Right Side captures."""
    front: CapturePayload
    left_side: CapturePayload
    right_side: CapturePayload
    height_cm: Optional[float] = None

