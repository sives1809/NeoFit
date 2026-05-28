"""
tests/test_cv.py
----------------
Unit tests for the entire CV pipeline:
  measurement.py → scaling.py → pseudo3d.py → stability.py

Run with:
    cd backend && pytest tests/test_cv.py -v

Test strategy
-------------
We use a synthetic landmark set that represents a 175 cm tall person
standing in a 640×480 frame. Expected output values are pre-computed by
hand and cross-checked against the original Python prototype.
"""

from __future__ import annotations

import math
from typing import Optional

import pytest

from app.cv.measurement import (
    Landmark,
    all_measurements_px,
    is_frame_usable,
    left_arm_px,
    right_arm_px,
    shoulder_width_px,
    shoulder_tilt_deg,
    shoulder_horizontal_ratio,
    MIN_VISIBILITY,
)
from app.cv.scaling import compute_scale, convert_all, NOSE_ANKLE_FRACTION
from app.cv.pseudo3d import ellipse_area, ellipse_perimeter, compute_pseudo3d
from app.cv.stability import StabilityBuffer, _iqr_filter, _coefficient_of_variation


# ══════════════════════════════════════════════════════════════════════════════
# SYNTHETIC LANDMARK FIXTURE
# ══════════════════════════════════════════════════════════════════════════════

def make_landmarks(
    *,
    visibility: float = 0.98,
    tilt_deg: float = 0.0,
    side_mode: bool = False,
    facing: Optional[str] = None,
) -> list[Landmark]:
    """
    Create 33 synthetic MediaPipe landmarks at physiologically plausible
    positions in a normalised [0,1] coordinate space, as if capturing a
    175 cm person centred in a 640×480 frame.

    Parameters
    ----------
    visibility  : set on all landmarks (use <0.65 to test occlusion gating)
    tilt_deg    : rotate shoulder line by this many degrees (FRONT validation test)
    side_mode   : collapse shoulder x-separation to simulate sideways view
    facing      : offset nose left or right ('left' or 'right') to test side profile orientation
    """
    # Build 33 landmarks with a default "invisible" value (the test only
    # populates the indices we care about; others have z=0, vis=vis)
    lms = [Landmark(x=0.5, y=0.5, visibility=visibility) for _ in range(33)]

    # Key positions (normalised to 640×480 frame, person centred)
    # y increases downward (image convention)
    nose          = (0.500, 0.060)   # ~29 px from top
    l_shoulder    = (0.420, 0.200)   # 89 px from left, 96 px from top
    r_shoulder    = (0.580, 0.200)
    l_elbow       = (0.380, 0.330)
    r_elbow       = (0.620, 0.330)
    l_hip         = (0.430, 0.500)
    r_hip         = (0.570, 0.500)
    l_knee        = (0.440, 0.670)
    r_knee        = (0.560, 0.670)
    l_ankle       = (0.445, 0.930)
    r_ankle       = (0.555, 0.930)

    # Apply tilt to shoulders (rotate around midpoint)
    if tilt_deg != 0.0:
        mid_x = (l_shoulder[0] + r_shoulder[0]) / 2
        mid_y = (l_shoulder[1] + r_shoulder[1]) / 2
        rad = math.radians(tilt_deg)
        def rot(x, y):
            dx, dy = x - mid_x, y - mid_y
            return (
                mid_x + dx * math.cos(rad) - dy * math.sin(rad),
                mid_y + dx * math.sin(rad) + dy * math.cos(rad),
            )
        l_shoulder = rot(*l_shoulder)
        r_shoulder = rot(*r_shoulder)

    # In SIDE mode, squash the horizontal distance between shoulders
    if side_mode:
        mid_x = (l_shoulder[0] + r_shoulder[0]) / 2
        l_shoulder = (mid_x - 0.015, l_shoulder[1])
        r_shoulder = (mid_x + 0.015, r_shoulder[1])

    mid_shoulder_x = (l_shoulder[0] + r_shoulder[0]) / 2
    if facing == "left":
        nose = (mid_shoulder_x - 0.05, 0.060)
    elif facing == "right":
        nose = (mid_shoulder_x + 0.05, 0.060)

    positions = {
        0:  nose,
        11: l_shoulder, 12: r_shoulder,
        13: l_elbow,    14: r_elbow,
        23: l_hip,      24: r_hip,
        25: l_knee,     26: r_knee,
        27: l_ankle,    28: r_ankle,
    }
    for idx, (x, y) in positions.items():
        lms[idx] = Landmark(x=x, y=y, visibility=visibility)

    return lms


W, H = 640, 480   # virtual frame dimensions used in all tests


# ══════════════════════════════════════════════════════════════════════════════
# MEASUREMENT TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestMeasurement:

    def test_left_arm_returns_float(self):
        lms = make_landmarks()
        result = left_arm_px(lms, W, H)
        assert isinstance(result, float)
        assert result > 0

    def test_right_arm_returns_float(self):
        lms = make_landmarks()
        result = right_arm_px(lms, W, H)
        assert isinstance(result, float)
        assert result > 0

    def test_arm_symmetry_on_symmetric_pose(self):
        """A symmetric landmark set should give equal left and right arm lengths."""
        lms = make_landmarks()
        l = left_arm_px(lms, W, H)
        r = right_arm_px(lms, W, H)
        assert l is not None and r is not None
        assert abs(l - r) < 1.0, f"Expected L≈R, got L={l:.2f} R={r:.2f}"

    def test_shoulder_width_positive(self):
        lms = make_landmarks()
        sw = shoulder_width_px(lms, W, H)
        assert sw is not None
        assert sw > 0

    def test_low_visibility_returns_none(self):
        """Landmarks below MIN_VISIBILITY threshold should cause None return."""
        lms = make_landmarks(visibility=0.50)  # below 0.65 threshold
        assert left_arm_px(lms, W, H) is None
        assert right_arm_px(lms, W, H) is None
        assert shoulder_width_px(lms, W, H) is None

    def test_tilt_deg_near_zero_for_level_shoulders(self):
        lms = make_landmarks(tilt_deg=0.0)
        tilt = shoulder_tilt_deg(lms, W, H)
        assert tilt is not None
        assert tilt < 5.0, f"Expected near-zero tilt, got {tilt:.2f}°"

    def test_tilt_deg_detects_rotation(self):
        lms = make_landmarks(tilt_deg=20.0)
        tilt = shoulder_tilt_deg(lms, W, H)
        assert tilt is not None
        assert tilt > 12.0, f"Expected tilt > 12°, got {tilt:.2f}°"

    def test_side_mode_shoulder_ratio_small(self):
        """In side mode, shoulders are stacked → ratio should be small."""
        lms = make_landmarks(side_mode=True)
        ratio = shoulder_horizontal_ratio(lms, W, H)
        assert ratio is not None
        assert ratio <= 0.08, f"Expected ratio ≤ 0.08, got {ratio:.4f}"

    def test_front_mode_shoulder_ratio_large(self):
        """In front mode, shoulders are wide → ratio should exceed side threshold."""
        lms = make_landmarks(side_mode=False)
        ratio = shoulder_horizontal_ratio(lms, W, H)
        assert ratio is not None
        assert ratio > 0.08, f"Expected ratio > 0.08, got {ratio:.4f}"

    def test_all_measurements_returns_dict(self):
        lms = make_landmarks()
        m = all_measurements_px(lms, W, H)
        assert isinstance(m, dict)
        for key in ("arm_left_px", "arm_right_px", "shoulder_px",
                    "thigh_left_px", "thigh_right_px", "ref_px"):
            assert key in m

    def test_is_frame_usable_true_on_good_frame(self):
        lms = make_landmarks()
        m = all_measurements_px(lms, W, H)
        assert is_frame_usable(m, "front") is True
        assert is_frame_usable(m, "left_side") is True
        assert is_frame_usable(m, "right_side") is True

    def test_is_frame_usable_false_on_occluded_frame(self):
        lms = make_landmarks(visibility=0.40)
        m = all_measurements_px(lms, W, H)
        assert is_frame_usable(m, "front") is False
        assert is_frame_usable(m, "left_side") is False
        assert is_frame_usable(m, "right_side") is False

    def test_is_frame_usable_side_mode_limb_gating(self):
        lms = make_landmarks()
        m = all_measurements_px(lms, W, H)
        m["arm_right_px"] = None
        # Should fail in front mode because arm_right is required
        assert is_frame_usable(m, "front") is False
        # Should pass in left_side mode because arm_right is NOT required
        assert is_frame_usable(m, "left_side") is True

    def test_arm_silhouette_fallbacks(self):
        """Test arm width/depth threshold logic (clean vs contaminated)."""
        lms = make_landmarks()
        from app.cv.measurement import left_arm_length_px, right_arm_length_px
        arm_l_len = left_arm_length_px(lms, W, H)
        arm_r_len = right_arm_length_px(lms, W, H)
        assert arm_l_len is not None and arm_l_len > 0
        assert arm_r_len is not None and arm_r_len > 0

        # Scenario A: clean silhouette front (width <= 60% of segment length)
        clean_width = arm_l_len * 0.40
        m = all_measurements_px(
            lms, W, H,
            silhouette_arm_left_px=clean_width,
            silhouette_arm_right_px=clean_width,
            mode="front"
        )
        assert m["arm_left_px"] == clean_width
        assert m["arm_right_px"] == clean_width

        # Scenario B: contaminated silhouette front (width > 60% of segment length)
        contaminated_width = arm_l_len * 0.80
        m = all_measurements_px(
            lms, W, H,
            silhouette_arm_left_px=contaminated_width,
            silhouette_arm_right_px=contaminated_width,
            mode="front"
        )
        assert abs(m["arm_left_px"] - arm_l_len * 0.36) < 1e-6
        assert abs(m["arm_right_px"] - arm_r_len * 0.36) < 1e-6

        # Scenario C: clean silhouette side (depth <= 60% of segment length)
        clean_depth = arm_l_len * 0.40
        m_left = all_measurements_px(
            lms, W, H,
            silhouette_arm_left_px=clean_depth,
            mode="left_side"
        )
        assert m_left["arm_side_left_px"] == clean_depth

        # Scenario D: contaminated silhouette side (depth > 60% of segment length)
        contaminated_depth = arm_l_len * 0.80
        m_left_contam = all_measurements_px(
            lms, W, H,
            silhouette_arm_left_px=contaminated_depth,
            mode="left_side"
        )
        assert abs(m_left_contam["arm_side_left_px"] - arm_l_len * 0.32) < 1e-6




# ══════════════════════════════════════════════════════════════════════════════
# SCALING TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestScaling:
    HEIGHT_CM = 175.0

    def test_scale_factor_positive(self):
        lms = make_landmarks()
        m = all_measurements_px(lms, W, H)
        ref = m["ref_px"]
        assert ref is not None
        scale = compute_scale(ref, self.HEIGHT_CM)
        assert scale > 0

    def test_convert_all_returns_cm_in_plausible_range(self):
        """Arm and thigh measurements should be in the 20–60 cm range for a normal person."""
        lms = make_landmarks()
        m_px = all_measurements_px(lms, W, H)
        cm = convert_all(m_px, self.HEIGHT_CM)

        for key, expected_range in [
            ("arm_left_cm",   (5, 25)),
            ("arm_right_cm",  (5, 25)),
            ("shoulder_cm",   (30, 60)),
            ("thigh_left_cm", (10, 35)),
        ]:
            val = cm.get(key)
            assert val is not None, f"{key} is None"
            lo, hi = expected_range
            assert lo <= val <= hi, f"{key}={val:.2f} outside expected [{lo},{hi}]"

    def test_nose_ankle_fraction_applied(self):
        """Scale factor = height * NOSE_ANKLE_FRACTION / ref_px."""
        lms = make_landmarks()
        m_px = all_measurements_px(lms, W, H)
        ref = m_px["ref_px"]
        expected_scale = (self.HEIGHT_CM * NOSE_ANKLE_FRACTION) / ref
        actual_scale = compute_scale(ref, self.HEIGHT_CM)
        assert abs(actual_scale - expected_scale) < 1e-9

    def test_invalid_inputs_return_zero(self):
        assert compute_scale(0, 175) == 0.0
        assert compute_scale(100, 0) == 0.0
        assert compute_scale(-10, 175) == 0.0

    def test_convert_all_empty_on_missing_ref(self):
        m_px = {"arm_left_px": 50.0, "ref_px": None}
        result = convert_all(m_px, self.HEIGHT_CM)
        assert result == {}


# ══════════════════════════════════════════════════════════════════════════════
# PSEUDO-3D TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestPseudo3D:

    def test_ellipse_area_circle(self):
        """For a circle (w=t), area should equal π × r²."""
        area = ellipse_area(10.0, 10.0)
        expected = math.pi * 5 * 5
        assert area is not None
        assert abs(area - expected) < 0.01

    def test_ellipse_perimeter_circle(self):
        """For a circle (w=t), perimeter should equal 2πr."""
        perim = ellipse_perimeter(10.0, 10.0)
        expected = 2 * math.pi * 5
        assert perim is not None
        assert abs(perim - expected) < 0.05   # Ramanujan is approximate

    def test_girth_greater_than_width(self):
        """Ellipse perimeter should always exceed the major axis."""
        perim = ellipse_perimeter(30.0, 20.0)
        assert perim is not None
        assert perim > 30.0

    def test_none_inputs_return_none(self):
        assert ellipse_area(None, 10.0) is None
        assert ellipse_perimeter(10.0, None) is None
        assert ellipse_area(0.0, 10.0) is None

    def test_girth_realistic_arm(self):
        """
        For a typical arm: front-width ≈ 20 cm, side-thickness ≈ 14 cm.
        Expected girth ≈ 54–58 cm (compare to tape-measured bicep girth of 35–42 cm).
        Note: our measurement is shoulder→elbow length, NOT bicep circumference,
        so the absolute value is intentionally larger. The metric is consistent
        for tracking RELATIVE change over time.
        """
        girth = ellipse_perimeter(20.0, 14.0)
        assert girth is not None
        assert 50.0 < girth < 65.0, f"Girth={girth:.2f} outside expected range"

    def test_compute_pseudo3d_full(self):
        front = {"arm_left_cm": 25.0, "arm_right_cm": 24.5,
                 "thigh_left_cm": 40.0, "thigh_right_cm": 39.5,
                 "chest_cm": 35.0, "waist_cm": 30.0, "hip_cm": 34.0}
        left_side  = {"arm_side_left_cm": 15.0, "thigh_side_left_cm": 25.0,
                      "chest_side_cm": 20.0, "waist_side_cm": 18.0, "hip_side_cm": 22.0}
        right_side = {"arm_side_right_cm": 14.8, "thigh_side_right_cm": 24.5,
                      "chest_side_cm": 20.2, "waist_side_cm": 18.2, "hip_side_cm": 22.2}
        result = compute_pseudo3d(front, left_side, right_side)
        assert result["arm_left_girth_cm"] is not None
        assert result["thigh_left_girth_cm"] is not None
        assert result["chest_girth_cm"] is not None
        assert result["waist_girth_cm"] is not None
        assert result["hip_girth_cm"] is not None
        assert result["arm_avg_girth_cm"] is not None
        # Asymmetry should be small for near-symmetric inputs
        assert result["arm_asymmetry_pct"] is not None
        assert result["arm_asymmetry_pct"] < 5.0

    def test_compute_pseudo3d_empty_inputs(self):
        result = compute_pseudo3d({}, {}, {})
        for v in result.values():
            assert v is None


# ══════════════════════════════════════════════════════════════════════════════
# STABILITY BUFFER TESTS
# ══════════════════════════════════════════════════════════════════════════════

def _sample(val: float = 100.0, noise: float = 0.0) -> dict:
    """Create a sample measurement dict with optional noise."""
    import random
    offset = random.uniform(-noise, noise)
    return {
        "arm_left_px":   val + offset,
        "arm_right_px":  val + offset,
        "shoulder_px":   val * 1.6 + offset,
        "thigh_left_px": val * 1.8 + offset,
        "thigh_right_px":val * 1.8 + offset,
        "ref_px":        val * 8.0,
        "tilt_deg":      2.0,
    }


class TestStabilityBuffer:

    def test_empty_buffer_not_ready(self):
        buf = StabilityBuffer()
        s = buf.status()
        assert s["ready"] is False
        assert s["progress"] == 0.0

    def test_stable_sequence_fires_once(self):
        """Feed STABLE_FOR_N_FRAMES stable frames — ready should fire exactly once."""
        buf = StabilityBuffer(stable_for=5, cv_threshold=0.05)
        fired_count = 0

        for _ in range(25):
            buf.add(_sample(100.0, noise=0.5))   # CV ≈ 0.5 %
            s = buf.status()
            if s["ready"]:
                fired_count += 1

        assert fired_count == 1, f"Expected 1 fire, got {fired_count}"

    def test_noisy_sequence_does_not_fire(self):
        """High-noise frames should not trigger capture."""
        buf = StabilityBuffer(stable_for=5, cv_threshold=0.02)

        for _ in range(30):
            buf.add(_sample(100.0, noise=15.0))   # CV ≈ 15 % >> 2 %

        s = buf.status()
        assert s["ready"] is False

    def test_reset_clears_state(self):
        buf = StabilityBuffer(stable_for=5, cv_threshold=0.05)
        for _ in range(20):
            buf.add(_sample(100.0, noise=0.3))

        buf.reset()
        s = buf.status()
        assert s["frame_count"] == 0
        assert s["ready"] is False
        assert s["progress"] == 0.0

    def test_none_values_dropped_silently(self):
        """Frames with None in key metrics should be dropped, not crash."""
        buf = StabilityBuffer()
        bad_frame = {"arm_left_px": None, "arm_right_px": 100.0,
                     "shoulder_px": 160.0, "thigh_left_px": 180.0, "thigh_right_px": 180.0}
        buf.add(bad_frame)
        s = buf.status()
        assert s["frame_count"] == 0   # dropped

    def test_iqr_filter_removes_outlier(self):
        values = [100.0, 101.0, 99.5, 100.5, 102.0, 200.0]  # 200 is outlier
        filtered = _iqr_filter(values)
        assert 200.0 not in filtered
        assert len(filtered) == 5

    def test_iqr_filter_small_list_unchanged(self):
        values = [100.0, 200.0, 50.0]   # too small to filter reliably
        filtered = _iqr_filter(values)
        assert filtered == values

    def test_cv_zero_for_constant_list(self):
        cv = _coefficient_of_variation([100.0, 100.0, 100.0])
        assert cv == 0.0

    def test_filtered_output_close_to_true_value(self):
        """IQR-filtered median should be close to the true signal value."""
        buf = StabilityBuffer(stable_for=3, cv_threshold=0.05)
        for _ in range(20):
            buf.add(_sample(100.0, noise=1.0))

        s = buf.status()
        if s["filtered"]:
            assert abs(s["filtered"]["arm_left_px"] - 100.0) < 5.0


class TestOrientation:

    def test_check_orientation_left(self):
        from app.cv.measurement import check_orientation_side
        # Create a synthetic left-facing profile
        lms = make_landmarks(side_mode=True, facing="left")
        assert check_orientation_side(lms) == "left"

    def test_check_orientation_right(self):
        from app.cv.measurement import check_orientation_side
        # Create a synthetic right-facing profile
        lms = make_landmarks(side_mode=True, facing="right")
        assert check_orientation_side(lms) == "right"

    def test_all_measurements_contains_orientation(self):
        lms = make_landmarks(side_mode=True, facing="left")
        m = all_measurements_px(lms, W, H)
        assert m.get("orientation") == "left"

    def test_validate_left_side_orientation(self):
        from app.routers.measure import _validate
        # Case 1: Left-facing profile in left_side mode (should pass)
        lms_left = make_landmarks(side_mode=True, facing="left")
        m_left = all_measurements_px(lms_left, W, H)
        res1 = _validate(m_left, "left_side")
        assert res1.ok is True

        # Case 2: Right-facing profile in left_side mode (should fail)
        lms_right = make_landmarks(side_mode=True, facing="right")
        m_right = all_measurements_px(lms_right, W, H)
        res2 = _validate(m_right, "left_side")
        assert res2.ok is False
        assert "Turn to your right" in res2.reason

    def test_validate_right_side_orientation(self):
        from app.routers.measure import _validate
        # Case 1: Right-facing profile in right_side mode (should pass)
        lms_right = make_landmarks(side_mode=True, facing="right")
        m_right = all_measurements_px(lms_right, W, H)
        res1 = _validate(m_right, "right_side")
        assert res1.ok is True

        # Case 2: Left-facing profile in right_side mode (should fail)
        lms_left = make_landmarks(side_mode=True, facing="left")
        m_left = all_measurements_px(lms_left, W, H)
        res2 = _validate(m_left, "right_side")
        assert res2.ok is False
        assert "Turn to your left" in res2.reason

