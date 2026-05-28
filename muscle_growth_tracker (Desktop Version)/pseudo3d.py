"""
pseudo3d.py
-----------
Approximate a muscle's cross-sectional area by treating it as an ellipse
whose major axis is the front-view "width" and whose minor axis is the
side-view "thickness".

    Area = (pi * width * thickness) / 4

Both inputs are in centimeters, so the output is in cm^2. This is a
geometric proxy for muscle size, NOT a true volumetric reconstruction.
It is sufficient to track relative growth over time, which is the
project's stated goal.
"""

import math


def ellipse_area(width_cm: float, thickness_cm: float) -> float:
    """Cross-sectional area of an ellipse with the given axes (cm^2)."""
    if width_cm <= 0 or thickness_cm <= 0:
        return 0.0
    return (math.pi * width_cm * thickness_cm) / 4.0


def compute_pseudo3d(front_cm: dict, side_cm: dict) -> dict:
    """
    Combine a captured front view and side view into pseudo-3D area
    estimates for arm and thigh.

    `front_cm` and `side_cm` are dicts shaped like the output of
    scaling.convert_all (containing arm_cm, shoulder_cm, thigh_cm).

    For arm and thigh:
        width     <- front view value
        thickness <- side view value
    """
    if not front_cm or not side_cm:
        return {"arm_area": 0.0, "thigh_area": 0.0}

    return {
        "arm_area": ellipse_area(front_cm.get("arm_cm", 0.0),
                                 side_cm.get("arm_cm", 0.0)),
        "thigh_area": ellipse_area(front_cm.get("thigh_cm", 0.0),
                                   side_cm.get("thigh_cm", 0.0)),
    }
