"""
measurement.py
--------------
Compute Euclidean distances between MediaPipe Pose landmarks for the
body regions tracked by the system: arm, shoulder, and thigh.

All functions accept a list of landmarks (MediaPipe `pose_landmarks.landmark`)
and the image (width, height) so normalized coordinates can be turned into
pixel coordinates.
"""

import math
from typing import List, Tuple

# MediaPipe Pose landmark indices we care about
NOSE = 0
LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12
LEFT_ELBOW = 13
RIGHT_ELBOW = 14
LEFT_HIP = 23
RIGHT_HIP = 24
LEFT_KNEE = 25
RIGHT_KNEE = 26
LEFT_ANKLE = 27
RIGHT_ANKLE = 28


def _to_pixel(landmark, w: int, h: int) -> Tuple[float, float]:
    """Convert a normalized MediaPipe landmark to pixel coordinates."""
    return landmark.x * w, landmark.y * h


def _dist(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Euclidean distance between two 2D points."""
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def arm_length_px(landmarks, w: int, h: int) -> float:
    """Average of left and right (shoulder -> elbow) distances in pixels."""
    ls = _to_pixel(landmarks[LEFT_SHOULDER], w, h)
    le = _to_pixel(landmarks[LEFT_ELBOW], w, h)
    rs = _to_pixel(landmarks[RIGHT_SHOULDER], w, h)
    re = _to_pixel(landmarks[RIGHT_ELBOW], w, h)
    return (_dist(ls, le) + _dist(rs, re)) / 2.0


def shoulder_width_px(landmarks, w: int, h: int) -> float:
    """Distance between left and right shoulder landmarks (pixels)."""
    ls = _to_pixel(landmarks[LEFT_SHOULDER], w, h)
    rs = _to_pixel(landmarks[RIGHT_SHOULDER], w, h)
    return _dist(ls, rs)


def thigh_length_px(landmarks, w: int, h: int) -> float:
    """Average of left and right (hip -> knee) distances in pixels."""
    lh = _to_pixel(landmarks[LEFT_HIP], w, h)
    lk = _to_pixel(landmarks[LEFT_KNEE], w, h)
    rh = _to_pixel(landmarks[RIGHT_HIP], w, h)
    rk = _to_pixel(landmarks[RIGHT_KNEE], w, h)
    return (_dist(lh, lk) + _dist(rh, rk)) / 2.0


def nose_to_ankle_px(landmarks, w: int, h: int) -> float:
    """
    Vertical-ish reference distance used for real-world scaling.
    We use the average ankle position so a slight stance asymmetry doesn't
    bias the result.
    """
    nose = _to_pixel(landmarks[NOSE], w, h)
    la = _to_pixel(landmarks[LEFT_ANKLE], w, h)
    ra = _to_pixel(landmarks[RIGHT_ANKLE], w, h)
    ankle_mid = ((la[0] + ra[0]) / 2.0, (la[1] + ra[1]) / 2.0)
    return _dist(nose, ankle_mid)


def shoulder_tilt_deg(landmarks, w: int, h: int) -> float:
    """
    Angle of the shoulder line vs horizontal, in degrees.
    Used by main.py to reject visibly tilted frames so measurements are
    only taken when the subject is reasonably square to the camera.
    """
    ls = _to_pixel(landmarks[LEFT_SHOULDER], w, h)
    rs = _to_pixel(landmarks[RIGHT_SHOULDER], w, h)
    dy = rs[1] - ls[1]
    dx = rs[0] - ls[0]
    if dx == 0:
        return 90.0
    return abs(math.degrees(math.atan2(dy, dx)))


def shoulder_dx_px(landmarks, w: int, h: int) -> float:
    """Absolute horizontal distance between left and right shoulders (pixels).
    Small value -> body is turned sideways to the camera."""
    ls = _to_pixel(landmarks[LEFT_SHOULDER], w, h)
    rs = _to_pixel(landmarks[RIGHT_SHOULDER], w, h)
    return abs(ls[0] - rs[0])


def all_measurements_px(landmarks, w: int, h: int) -> dict:
    """Convenience: return every pixel measurement we track in one dict."""
    return {
        "arm_px": arm_length_px(landmarks, w, h),
        "shoulder_px": shoulder_width_px(landmarks, w, h),
        "thigh_px": thigh_length_px(landmarks, w, h),
        "ref_px": nose_to_ankle_px(landmarks, w, h),
        "tilt_deg": shoulder_tilt_deg(landmarks, w, h),
        "shoulder_dx_px": shoulder_dx_px(landmarks, w, h),
    }
