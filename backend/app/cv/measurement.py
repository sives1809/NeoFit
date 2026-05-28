"""
cv/measurement.py
-----------------
Compute Euclidean distances between MediaPipe Pose landmarks.

Migration notes vs. original desktop prototype
-----------------------------------------------
- Landmarks arrive as plain dicts/Pydantic objects with (x, y, visibility)
  in NORMALISED coordinates [0, 1], sent from MediaPipe JS in the browser.
- A video_width / video_height pair is required to convert normalised
  coordinates to pixel space and correct for aspect-ratio distortion.
- Per-side measurements (left vs right) are now returned separately to
  enable asymmetry tracking — a key improvement over the prototype.
- All landmarks are gated by a visibility confidence threshold before use.
  Measurements involving a low-confidence landmark return None so the
  caller can decide whether to discard the frame entirely.

Landmark index reference (MediaPipe Pose, identical in JS and Python):
    NOSE=0, L_SHOULDER=11, R_SHOULDER=12,
    L_ELBOW=13, R_ELBOW=14, L_HIP=23, R_HIP=24,
    L_KNEE=25, R_KNEE=26, L_ANKLE=27, R_ANKLE=28
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


# ── Landmark index constants ──────────────────────────────────────────────────
NOSE          = 0
LEFT_SHOULDER  = 11
RIGHT_SHOULDER = 12
LEFT_ELBOW     = 13
RIGHT_ELBOW    = 14
LEFT_HIP       = 23
RIGHT_HIP      = 24
LEFT_KNEE      = 25
RIGHT_KNEE     = 26
LEFT_ANKLE     = 27
RIGHT_ANKLE    = 28

# Minimum MediaPipe visibility score to consider a landmark trustworthy.
# 0.65 balances sensitivity (don't lose too many frames) vs. noise.
MIN_VISIBILITY: float = 0.65


@dataclass
class Landmark:
    """Minimal representation of a single MediaPipe pose landmark."""
    x: float
    y: float
    z: float = 0.0
    visibility: float = 1.0


# ── Internal helpers ──────────────────────────────────────────────────────────

def _px(lm: Landmark, w: int, h: int) -> tuple[float, float]:
    """Convert normalised landmark coordinates to pixel space."""
    return lm.x * w, lm.y * h


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Euclidean distance between two 2-D points."""
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _visible(lm: Landmark, threshold: float = MIN_VISIBILITY) -> bool:
    """Return True if the landmark meets the minimum visibility threshold."""
    return lm.visibility >= threshold


def _require_visible(
    *landmarks: Landmark,
    threshold: float = MIN_VISIBILITY,
) -> bool:
    """Return True only if ALL supplied landmarks meet the visibility threshold."""
    return all(_visible(lm, threshold) for lm in landmarks)


# ── Per-side length helper functions ───────────────────────────────────────────

def left_arm_length_px(lms: list[Landmark], w: int, h: int) -> Optional[float]:
    """Left shoulder → left elbow length in pixels. None if low confidence."""
    ls, le = lms[LEFT_SHOULDER], lms[LEFT_ELBOW]
    if not _require_visible(ls, le):
        return None
    return _dist(_px(ls, w, h), _px(le, w, h))


def right_arm_length_px(lms: list[Landmark], w: int, h: int) -> Optional[float]:
    """Right shoulder → right elbow length in pixels. None if low confidence."""
    rs, re = lms[RIGHT_SHOULDER], lms[RIGHT_ELBOW]
    if not _require_visible(rs, re):
        return None
    return _dist(_px(rs, w, h), _px(re, w, h))


def left_thigh_length_px(lms: list[Landmark], w: int, h: int) -> Optional[float]:
    """Left hip → left knee length in pixels. None if low confidence."""
    lh, lk = lms[LEFT_HIP], lms[LEFT_KNEE]
    if not _require_visible(lh, lk):
        return None
    return _dist(_px(lh, w, h), _px(lk, w, h))


def right_thigh_length_px(lms: list[Landmark], w: int, h: int) -> Optional[float]:
    """Right hip → right knee length in pixels. None if low confidence."""
    rh, rk = lms[RIGHT_HIP], lms[RIGHT_KNEE]
    if not _require_visible(rh, rk):
        return None
    return _dist(_px(rh, w, h), _px(rk, w, h))


# ── Per-side measurement functions (Scaled to represent width/thickness) ─────

def left_arm_px(lms: list[Landmark], w: int, h: int) -> Optional[float]:
    """Left arm width in pixels. None if low confidence."""
    val = left_arm_length_px(lms, w, h)
    return val * 0.36 if val is not None else None


def right_arm_px(lms: list[Landmark], w: int, h: int) -> Optional[float]:
    """Right arm width in pixels. None if low confidence."""
    val = right_arm_length_px(lms, w, h)
    return val * 0.36 if val is not None else None


def left_thigh_px(lms: list[Landmark], w: int, h: int) -> Optional[float]:
    """Left thigh width in pixels. None if low confidence."""
    val = left_thigh_length_px(lms, w, h)
    return val * 0.42 if val is not None else None


def right_thigh_px(lms: list[Landmark], w: int, h: int) -> Optional[float]:
    """Right thigh width in pixels. None if low confidence."""
    val = right_thigh_length_px(lms, w, h)
    return val * 0.42 if val is not None else None


def shoulder_width_px(lms: list[Landmark], w: int, h: int) -> Optional[float]:
    """Left shoulder → right shoulder distance in pixels. None if low confidence."""
    ls, rs = lms[LEFT_SHOULDER], lms[RIGHT_SHOULDER]
    if not _require_visible(ls, rs):
        return None
    return _dist(_px(ls, w, h), _px(rs, w, h))


def hip_width_px(lms: list[Landmark], w: int, h: int) -> Optional[float]:
    """Left hip → right hip distance in pixels. None if low confidence."""
    lh, rh = lms[LEFT_HIP], lms[RIGHT_HIP]
    if not _require_visible(lh, rh):
        return None
    return _dist(_px(lh, w, h), _px(rh, w, h))


def torso_length_px(lms: list[Landmark], w: int, h: int) -> Optional[float]:
    """Average vertical shoulder-to-hip torso length in pixels."""
    ls, lh = lms[LEFT_SHOULDER], lms[LEFT_HIP]
    rs, rh = lms[RIGHT_SHOULDER], lms[RIGHT_HIP]
    
    visible_sides = []
    if _require_visible(ls, lh):
        visible_sides.append(_dist(_px(ls, w, h), _px(lh, w, h)))
    if _require_visible(rs, rh):
        visible_sides.append(_dist(_px(rs, w, h), _px(rh, w, h)))
        
    if not visible_sides:
        return None
    return sum(visible_sides) / len(visible_sides)


def nose_to_ankle_px(lms: list[Landmark], w: int, h: int) -> Optional[float]:
    """
    Nose → mid-ankle distance in pixels — used as the real-world scale reference.

    We average both ankles so an asymmetric stance does not bias the scale.
    If either ankle is occluded, we fall back to the visible one.
    """
    nose = lms[NOSE]
    la, ra = lms[LEFT_ANKLE], lms[RIGHT_ANKLE]

    if not _visible(nose):
        return None

    visible_ankles = [a for a in (la, ra) if _visible(a)]
    if not visible_ankles:
        return None

    ax = sum(a.x for a in visible_ankles) / len(visible_ankles)
    ay = sum(a.y for a in visible_ankles) / len(visible_ankles)
    ankle_mid = (ax * w, ay * h)
    return _dist(_px(nose, w, h), ankle_mid)


# ── Pose-validation helpers ───────────────────────────────────────────────────

def shoulder_tilt_deg(lms: list[Landmark], w: int, h: int) -> Optional[float]:
    """
    Angle of the shoulder line vs horizontal (degrees).
    Used to reject frames where the subject is visibly tilted in FRONT mode.
    """
    ls, rs = lms[LEFT_SHOULDER], lms[RIGHT_SHOULDER]
    if not _require_visible(ls, rs):
        return None
    lp, rp = _px(ls, w, h), _px(rs, w, h)
    dx, dy = rp[0] - lp[0], rp[1] - lp[1]
    if dx == 0:
        return 90.0
    return abs(math.degrees(math.atan2(dy, dx)))


def shoulder_horizontal_ratio(lms: list[Landmark], w: int, h: int) -> Optional[float]:
    """
    |left_shoulder.x − right_shoulder.x| / nose-to-ankle reference.
    Small value means the body is turned sideways — used to validate SIDE mode.
    """
    ls, rs = lms[LEFT_SHOULDER], lms[RIGHT_SHOULDER]
    if not _require_visible(ls, rs):
        return None
    dx = abs(ls.x * w - rs.x * w)
    ref = nose_to_ankle_px(lms, w, h)
    if not ref or ref <= 0:
        return None
    return dx / ref


def mean_visibility(lms: list[Landmark], indices: list[int]) -> float:
    """Average visibility score for a given set of landmark indices."""
    scores = [lms[i].visibility for i in indices if i < len(lms)]
    return sum(scores) / len(scores) if scores else 0.0


# ── Composite measurement dict ────────────────────────────────────────────────

# Landmarks we consider "key" — all must be visible for a valid measurement frame
KEY_LANDMARK_INDICES = [
    NOSE, LEFT_SHOULDER, RIGHT_SHOULDER,
    LEFT_ELBOW, RIGHT_ELBOW,
    LEFT_HIP, RIGHT_HIP,
    LEFT_KNEE, RIGHT_KNEE,
    LEFT_ANKLE, RIGHT_ANKLE,
]


def check_orientation_side(lms: list[Landmark]) -> Optional[str]:
    """
    Determine if the profile pose is facing left or right.
    Returns 'left' if the nose is to the left of the shoulder midpoint,
    'right' if the nose is to the right of the shoulder midpoint,
    or None if landmarks are not sufficiently visible.
    """
    nose = lms[NOSE]
    ls = lms[LEFT_SHOULDER]
    rs = lms[RIGHT_SHOULDER]
    if not _require_visible(nose, ls, rs):
        return None
    torso_x = (ls.x + rs.x) / 2.0
    return "left" if nose.x < torso_x else "right"


def all_measurements_px(
    lms: list[Landmark],
    w: int,
    h: int,
    silhouette_chest_px: Optional[float] = None,
    silhouette_waist_px: Optional[float] = None,
    silhouette_hip_px: Optional[float] = None,
    silhouette_arm_left_px: Optional[float] = None,
    silhouette_arm_right_px: Optional[float] = None,
    mode: str = "front",
) -> dict[str, Optional[float] | Optional[str]]:
    """
    Compute every tracked pixel measurement in one call.

    Returns a dict with float values (pixels) or None for occluded pairs.
    Downstream code (stability buffer, scaling) should treat None as an
    invalid frame and not add it to the rolling window.
    """
    arm_l_len = left_arm_length_px(lms, w, h)
    arm_r_len = right_arm_length_px(lms, w, h)
    thigh_l_len = left_thigh_length_px(lms, w, h)
    thigh_r_len = right_thigh_length_px(lms, w, h)
    sh_w = shoulder_width_px(lms, w, h)
    h_w = hip_width_px(lms, w, h)
    t_len = torso_length_px(lms, w, h)

    # Use silhouette values when available, falling back to anatomical estimations
    # when the ratio of scanned width to upper arm length is > 60% (overlapping pixels).
    # Front Mode Arm Widths:
    arm_left_px_val = None
    if arm_l_len is not None:
        if mode == "front" and silhouette_arm_left_px is not None:
            # Overlap threshold check: is scanned width > 60% of segment length?
            if silhouette_arm_left_px / arm_l_len <= 0.60:
                arm_left_px_val = silhouette_arm_left_px
            else:
                arm_left_px_val = arm_l_len * 0.36
        else:
            arm_left_px_val = arm_l_len * 0.36

    arm_right_px_val = None
    if arm_r_len is not None:
        if mode == "front" and silhouette_arm_right_px is not None:
            if silhouette_arm_right_px / arm_r_len <= 0.60:
                arm_right_px_val = silhouette_arm_right_px
            else:
                arm_right_px_val = arm_r_len * 0.36
        else:
            arm_right_px_val = arm_r_len * 0.36

    # Side Mode Arm Thicknesses (Depths):
    arm_side_left_px_val = None
    if arm_l_len is not None:
        if mode in ("left_side", "side") and silhouette_arm_left_px is not None:
            if silhouette_arm_left_px / arm_l_len <= 0.60:
                arm_side_left_px_val = silhouette_arm_left_px
            else:
                arm_side_left_px_val = arm_l_len * 0.32
        else:
            arm_side_left_px_val = arm_l_len * 0.32

    arm_side_right_px_val = None
    if arm_r_len is not None:
        if mode in ("right_side", "side") and silhouette_arm_right_px is not None:
            if silhouette_arm_right_px / arm_r_len <= 0.60:
                arm_side_right_px_val = silhouette_arm_right_px
            else:
                arm_side_right_px_val = arm_r_len * 0.32
        else:
            arm_side_right_px_val = arm_r_len * 0.32

    # Separate torso front vs side values
    chest_front_val = silhouette_chest_px if (mode == "front" and silhouette_chest_px is not None) else (sh_w * 0.88 if sh_w is not None else None)
    waist_front_val = silhouette_waist_px if (mode == "front" and silhouette_waist_px is not None) else (h_w * 0.85 if h_w is not None else None)
    hip_front_val = silhouette_hip_px if (mode == "front" and silhouette_hip_px is not None) else h_w

    chest_side_val = silhouette_chest_px if (mode in ("left_side", "right_side") and silhouette_chest_px is not None) else (t_len * 0.45 if t_len is not None else None)
    waist_side_val = silhouette_waist_px if (mode in ("left_side", "right_side") and silhouette_waist_px is not None) else (t_len * 0.40 if t_len is not None else None)
    hip_side_val = silhouette_hip_px if (mode in ("left_side", "right_side") and silhouette_hip_px is not None) else (t_len * 0.48 if t_len is not None else None)

    return {
        # Front widths
        "arm_left_px":        arm_left_px_val,
        "arm_right_px":       arm_right_px_val,
        "shoulder_px":        sh_w,
        "chest_px":           chest_front_val,
        "waist_px":           waist_front_val,
        "hip_px":             hip_front_val,
        "thigh_left_px":      thigh_l_len * 0.42 if thigh_l_len is not None else None,
        "thigh_right_px":     thigh_r_len * 0.42 if thigh_r_len is not None else None,

        # Side thicknesses
        "arm_side_left_px":   arm_side_left_px_val,
        "arm_side_right_px":  arm_side_right_px_val,
        "thigh_side_left_px":  thigh_l_len * 0.38 if thigh_l_len is not None else None,
        "thigh_side_right_px": thigh_r_len * 0.38 if thigh_r_len is not None else None,
        "chest_side_px":       chest_side_val,
        "waist_side_px":       waist_side_val,
        "hip_side_px":         hip_side_val,

        "ref_px":             nose_to_ankle_px(lms, w, h),
        "tilt_deg":           shoulder_tilt_deg(lms, w, h),
        "shoulder_h_ratio":   shoulder_horizontal_ratio(lms, w, h),
        "confidence":         mean_visibility(lms, KEY_LANDMARK_INDICES),
        "orientation":        check_orientation_side(lms),
    }



def is_frame_usable(m: dict[str, Optional[float]], mode: str = "front") -> bool:
    """
    Return True if ALL required measurements are present (not None).
    A frame with any occluded key landmark is discarded entirely.
    """
    if mode == "left_side":
        required = [
            "arm_left_px", "thigh_left_px", "ref_px"
        ]
    elif mode == "right_side":
        required = [
            "arm_right_px", "thigh_right_px", "ref_px"
        ]
    else:
        required = [
            "arm_left_px", "arm_right_px", "shoulder_px",
            "thigh_left_px", "thigh_right_px", "ref_px",
        ]
    return all(m.get(k) is not None for k in required)


def log_arm_debug(
    arm_left_front_cm: Optional[float],
    arm_left_side_cm: Optional[float],
    arm_right_front_cm: Optional[float],
    arm_right_side_cm: Optional[float],
    scale_front: Optional[float],
    scale_side: Optional[float],
    arm_left_girth_cm: Optional[float],
    arm_right_girth_cm: Optional[float],
) -> None:
    """Print detailed inputs, scales, and final girths for arm measurement debugging."""
    arm_left_front_px = (arm_left_front_cm / scale_front) if (arm_left_front_cm is not None and scale_front) else None
    arm_left_side_px = (arm_left_side_cm / scale_side) if (arm_left_side_cm is not None and scale_side) else None
    arm_right_front_px = (arm_right_front_cm / scale_front) if (arm_right_front_cm is not None and scale_front) else None
    arm_right_side_px = (arm_right_side_cm / scale_side) if (arm_right_side_cm is not None and scale_side) else None

    print("\n--- ARM GIRTH RECONSTRUCTION DEBUG ---")
    print(f"arm_left_front_px: {arm_left_front_px}")
    print(f"arm_left_side_px: {arm_left_side_px}")
    print(f"arm_right_front_px: {arm_right_front_px}")
    print(f"arm_right_side_px: {arm_right_side_px}")
    print(f"scale_cm_per_px (front): {scale_front}")
    print(f"scale_cm_per_px (side): {scale_side}")
    print(f"arm_left_girth_cm: {arm_left_girth_cm}")
    print(f"arm_right_girth_cm: {arm_right_girth_cm}")
    print("---------------------------------------\n")


