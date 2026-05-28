"""
cv/pseudo3d.py
--------------
Combine front-view width and side-view thickness measurements to estimate
muscle cross-section geometry — treating each muscle belly as an ellipse.

Improvements over desktop prototype
-------------------------------------
1.  GIRTH (circumference) is the PRIMARY metric.
    It is computed using the Ramanujan approximation for ellipse perimeter,
    which is accurate to < 0.5 % for the semi-axis ratios typical of human
    arm / thigh muscle bellies (a/b ≈ 1.0 – 2.5).

    A tape-measure girth reading is directly comparable to this estimate,
    which makes academic validation straightforward: measure both and
    compute the difference.

2.  AREA is retained as a SECONDARY metric for trend analysis.
    It is more sensitive to small changes because area scales as a², while
    circumference scales as a. Both are reported per session.

3.  Per-side girths (left arm, right arm, left thigh, right thigh) are
    computed where both views captured the same side. An asymmetry
    percentage is also returned for the session record.

Mathematics
-----------
For an ellipse with semi-axes a (= width / 2) and b (= thickness / 2):

    Area         = π · a · b
    Circumference ≈ π · (a + b) · [1 + 3h / (10 + √(4 − 3h))]
        where  h = ((a − b) / (a + b))²        [Ramanujan, 1914]

References: Ramanujan, S. (1914). Modular equations and approximations to π.
            Quarterly Journal of Mathematics, 45, 350-372.
"""

from __future__ import annotations

import math
from typing import Optional


# ── Core geometry ─────────────────────────────────────────────────────────────

def ellipse_area(width_cm: Optional[float], thickness_cm: Optional[float]) -> Optional[float]:
    """
    Cross-sectional area of an ellipse with full axes width × thickness (cm²).
    Returns None if either input is missing or non-positive.
    """
    if width_cm is None or thickness_cm is None:
        return None
    if width_cm <= 0 or thickness_cm <= 0:
        return None
    return (math.pi * width_cm * thickness_cm) / 4.0


def ellipse_perimeter(width_cm: Optional[float], thickness_cm: Optional[float]) -> Optional[float]:
    """
    Estimated circumference (girth) of an ellipse with full axes width × thickness (cm).

    Uses the Ramanujan (1914) approximation — accurate to < 0.5 % for
    eccentricities typical of human limb cross-sections.

    Returns None if either input is missing or non-positive.
    """
    if width_cm is None or thickness_cm is None:
        return None
    if width_cm <= 0 or thickness_cm <= 0:
        return None

    a = width_cm / 2.0   # semi-major axis
    b = thickness_cm / 2.0  # semi-minor axis

    # Ensure a ≥ b for the formula
    if b > a:
        a, b = b, a

    h = ((a - b) / (a + b)) ** 2
    return math.pi * (a + b) * (1 + (3 * h) / (10 + math.sqrt(4 - 3 * h)))


# ── High-level session combiner ───────────────────────────────────────────────

def _avg_side(k: str, side1: dict, side2: dict) -> Optional[float]:
    v1 = side1.get(k)
    v2 = side2.get(k)
    if v1 is None and v2 is None:
        return None
    vals = [x for x in (v1, v2) if x is not None]
    return sum(vals) / len(vals)


def compute_pseudo3d(
    front_cm: dict[str, Optional[float]],
    left_side_cm: dict[str, Optional[float]],
    right_side_cm: dict[str, Optional[float]],
    scale_front: Optional[float] = None,
    scale_side: Optional[float] = None,
    height_cm: Optional[float] = None,
) -> dict[str, Optional[float] | Optional[bool] | Optional[str]]:
    """
    Combine captured front-view and side-view cm measurements into pseudo-3D
    geometry estimates for chest, waist, hip, arms, and thighs.

    Convention
    ----------
    front_cm       → provides WIDTH (facing forward)
    left_side_cm   → provides LEFT limb thickness + torso thickness
    right_side_cm  → provides RIGHT limb thickness + torso thickness
    """
    if not front_cm or (not left_side_cm and not right_side_cm):
        return _empty_result()

    # ── Torso thicknesses (averaged or fallback) ──────────────────────────────
    chest_thickness = _avg_side("chest_side_cm", left_side_cm, right_side_cm)
    waist_thickness = _avg_side("waist_side_cm", left_side_cm, right_side_cm)
    hip_thickness = _avg_side("hip_side_cm", left_side_cm, right_side_cm)

    # ── Torso derived metrics ──────────────────────────────────────────────────
    chest_girth = ellipse_perimeter(front_cm.get("chest_cm"), chest_thickness)
    waist_girth = ellipse_perimeter(front_cm.get("waist_cm"), waist_thickness)
    hip_girth = ellipse_perimeter(front_cm.get("hip_cm"), hip_thickness)

    chest_area = ellipse_area(front_cm.get("chest_cm"), chest_thickness)
    waist_area = ellipse_area(front_cm.get("waist_cm"), waist_thickness)
    hip_area = ellipse_area(front_cm.get("hip_cm"), hip_thickness)

    # ── Arm ──────────────────────────────────────────────────────────────────
    arm_left_girth = ellipse_perimeter(
        front_cm.get("arm_left_cm"),
        left_side_cm.get("arm_side_left_cm"),
    )
    arm_right_girth = ellipse_perimeter(
        front_cm.get("arm_right_cm"),
        right_side_cm.get("arm_side_right_cm"),
    )
    arm_left_area = ellipse_area(
        front_cm.get("arm_left_cm"),
        left_side_cm.get("arm_side_left_cm"),
    )
    arm_right_area = ellipse_area(
        front_cm.get("arm_right_cm"),
        right_side_cm.get("arm_side_right_cm"),
    )

    # ── Thigh ─────────────────────────────────────────────────────────────────
    thigh_left_girth = ellipse_perimeter(
        front_cm.get("thigh_left_cm"),
        left_side_cm.get("thigh_side_left_cm"),
    )
    thigh_right_girth = ellipse_perimeter(
        front_cm.get("thigh_right_cm"),
        right_side_cm.get("thigh_side_right_cm"),
    )
    thigh_left_area = ellipse_area(
        front_cm.get("thigh_left_cm"),
        left_side_cm.get("thigh_side_left_cm"),
    )
    thigh_right_area = ellipse_area(
        front_cm.get("thigh_right_cm"),
        right_side_cm.get("thigh_side_right_cm"),
    )

    # ── Asymmetry percentages ─────────────────────────────────────────────────
    arm_asym   = _asymmetry_pct(arm_left_girth,   arm_right_girth)
    thigh_asym = _asymmetry_pct(thigh_left_girth, thigh_right_girth)

    # ── Runtime Debug Logging ────────────────────────────────────────────────
    print(f"\n" + "="*40)
    print(f"[DEBUG /combine PSEUDO3D CALIBRATION]")
    print(f"HEIGHT REF CM: {height_cm or 'N/A'}")
    print(f"SCALE FRONT: {scale_front or 'N/A'} cm/px")
    print(f"SCALE SIDE:  {scale_side or 'N/A'} cm/px")
    print(f"\nRAW PIXELS (Derived back from scaled CM):")
    if scale_front and scale_front > 0:
        print(f"  - chest_width_px:       {front_cm.get('chest_cm') / scale_front if front_cm.get('chest_cm') is not None else None}")
        print(f"  - waist_width_px:       {front_cm.get('waist_cm') / scale_front if front_cm.get('waist_cm') is not None else None}")
        print(f"  - hip_width_px:         {front_cm.get('hip_cm') / scale_front if front_cm.get('hip_cm') is not None else None}")
        print(f"  - arm_left_width_px:    {front_cm.get('arm_left_cm') / scale_front if front_cm.get('arm_left_cm') is not None else None}")
        print(f"  - arm_right_width_px:   {front_cm.get('arm_right_cm') / scale_front if front_cm.get('arm_right_cm') is not None else None}")
        print(f"  - thigh_left_width_px:  {front_cm.get('thigh_left_cm') / scale_front if front_cm.get('thigh_left_cm') is not None else None}")
        print(f"  - thigh_right_width_px: {front_cm.get('thigh_right_cm') / scale_front if front_cm.get('thigh_right_cm') is not None else None}")
    else:
        print("  - front pixels: N/A (front scale missing)")
        
    if scale_side and scale_side > 0:
        print(f"  - chest_depth_px:       {chest_thickness / scale_side if chest_thickness is not None else None}")
        print(f"  - waist_depth_px:       {waist_thickness / scale_side if waist_thickness is not None else None}")
        print(f"  - hip_depth_px:         {hip_thickness / scale_side if hip_thickness is not None else None}")
        print(f"  - arm_left_depth_px:    {left_side_cm.get('arm_side_left_cm') / scale_side if left_side_cm.get('arm_side_left_cm') is not None else None}")
        print(f"  - arm_right_depth_px:   {right_side_cm.get('arm_side_right_cm') / scale_side if right_side_cm.get('arm_side_right_cm') is not None else None}")
        print(f"  - thigh_left_depth_px:  {left_side_cm.get('thigh_side_left_cm') / scale_side if left_side_cm.get('thigh_side_left_cm') is not None else None}")
        print(f"  - thigh_right_depth_px: {right_side_cm.get('thigh_side_right_cm') / scale_side if right_side_cm.get('thigh_side_right_cm') is not None else None}")
    else:
        print("  - side pixels: N/A (side scale missing)")

    print(f"\nSCALED CM:")
    print(f"  - chest_front_cm: {front_cm.get('chest_cm')}")
    print(f"  - waist_front_cm: {front_cm.get('waist_cm')}")
    print(f"  - hip_front_cm:   {front_cm.get('hip_cm')}")
    print(f"  - chest_depth_cm: {chest_thickness}")
    print(f"  - waist_depth_cm: {waist_thickness}")
    print(f"  - hip_depth_cm:   {hip_thickness}")
    print(f"  - arm_left_width_cm:   {front_cm.get('arm_left_cm')}, depth_cm: {left_side_cm.get('arm_side_left_cm')}")
    print(f"  - arm_right_width_cm:  {front_cm.get('arm_right_cm')}, depth_cm: {right_side_cm.get('arm_side_right_cm')}")
    print(f"  - thigh_left_width_cm: {front_cm.get('thigh_left_cm')}, depth_cm: {left_side_cm.get('thigh_side_left_cm')}")
    print(f"  - thigh_right_width_cm:{front_cm.get('thigh_right_cm')}, depth_cm: {right_side_cm.get('thigh_side_right_cm')}")

    print(f"\nFINAL GIRTHS:")
    print(f"  - chest_girth_cm:       {chest_girth}")
    print(f"  - waist_girth_cm:       {waist_girth}")
    print(f"  - hip_girth_cm:         {hip_girth}")
    print(f"  - arm_left_girth_cm:    {arm_left_girth}")
    print(f"  - arm_right_girth_cm:   {arm_right_girth}")
    print(f"  - thigh_left_girth_cm:  {thigh_left_girth}")
    print(f"  - thigh_right_girth_cm: {thigh_right_girth}")
    print("="*40 + "\n")

    # ── Realism sanity checks ────────────────────────────────────────────────
    is_underestimated = False
    underestimated_reasons = []
    
    height_ref = height_cm or 171.0
    waist_min_thresh = 70.0 * (height_ref / 171.0)
    hip_min_thresh = 80.0 * (height_ref / 171.0)
    
    # Check if other limbs are within normal ranges to ensure it's not a generic small frame
    chest_ok = chest_girth is None or chest_girth > 80.0 * (height_ref / 171.0)
    arm_ok = (arm_left_girth is None or arm_left_girth > 22.0) and (arm_right_girth is None or arm_right_girth > 22.0)
    thigh_ok = (thigh_left_girth is None or thigh_left_girth > 40.0) and (thigh_right_girth is None or thigh_right_girth > 40.0)
    
    if chest_ok and arm_ok and thigh_ok:
        if waist_girth is not None and waist_girth < waist_min_thresh:
            is_underestimated = True
            underestimated_reasons.append(
                f"Waist girth ({waist_girth:.1f} cm) is below physiological realism threshold ({waist_min_thresh:.1f} cm)"
            )
        if hip_girth is not None and hip_girth < hip_min_thresh:
            is_underestimated = True
            underestimated_reasons.append(
                f"Hip girth ({hip_girth:.1f} cm) is below physiological realism threshold ({hip_min_thresh:.1f} cm)"
            )
            
    if is_underestimated:
        warning_msg = f"[WARNING] Torso underestimation suspected: {', '.join(underestimated_reasons)}"
        print(warning_msg)

    return {
        # Primary metric: estimated girth (cm) — comparable to a tape measure
        "arm_left_girth_cm":    _round(arm_left_girth),
        "arm_right_girth_cm":   _round(arm_right_girth),
        "thigh_left_girth_cm":  _round(thigh_left_girth),
        "thigh_right_girth_cm": _round(thigh_right_girth),
        "chest_girth_cm":       _round(chest_girth),
        "waist_girth_cm":       _round(waist_girth),
        "hip_girth_cm":         _round(hip_girth),

        # Secondary metric: cross-sectional area (cm²)
        "arm_left_area_cm2":    _round(arm_left_area),
        "arm_right_area_cm2":   _round(arm_right_area),
        "thigh_left_area_cm2":  _round(thigh_left_area),
        "thigh_right_area_cm2": _round(thigh_right_area),
        "chest_area_cm2":       _round(chest_area),
        "waist_area_cm2":       _round(waist_area),
        "hip_area_cm2":         _round(hip_area),

        # Convenience averages
        "arm_avg_girth_cm":   _avg(arm_left_girth,   arm_right_girth),
        "thigh_avg_girth_cm": _avg(thigh_left_girth, thigh_right_girth),
        "arm_avg_area_cm2":   _avg(arm_left_area,    arm_right_area),
        "thigh_avg_area_cm2": _avg(thigh_left_area,  thigh_right_area),

        # Asymmetry (%) — flag if > 5 %
        "arm_asymmetry_pct":   _round(arm_asym),
        "thigh_asymmetry_pct": _round(thigh_asym),

        # Sanity warning flags
        "underestimation_detected": is_underestimated,
        "underestimation_warning": ", ".join(underestimated_reasons) if is_underestimated else None,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _round(v: Optional[float], decimals: int = 2) -> Optional[float]:
    return round(v, decimals) if v is not None else None


def _avg(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None and b is None:
        return None
    vals = [x for x in (a, b) if x is not None]
    return _round(sum(vals) / len(vals))


def _asymmetry_pct(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b is None or (a + b) == 0:
        return None
    return abs(a - b) / ((a + b) / 2) * 100


def _empty_result() -> dict[str, None]:
    keys = [
        "arm_left_girth_cm", "arm_right_girth_cm",
        "thigh_left_girth_cm", "thigh_right_girth_cm",
        "chest_girth_cm", "waist_girth_cm", "hip_girth_cm",
        "arm_left_area_cm2", "arm_right_area_cm2",
        "thigh_left_area_cm2", "thigh_right_area_cm2",
        "chest_area_cm2", "waist_area_cm2", "hip_area_cm2",
        "arm_avg_girth_cm", "thigh_avg_girth_cm",
        "arm_avg_area_cm2", "thigh_avg_area_cm2",
        "arm_asymmetry_pct", "thigh_asymmetry_pct",
        "underestimation_detected", "underestimation_warning",
    ]
    return {k: None for k in keys}

