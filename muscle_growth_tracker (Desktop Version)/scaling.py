"""
scaling.py
----------
Convert pixel measurements to centimeters using the user's real height as
a reference scale.

Geometric assumption (kept intentionally simple, per academic scope):
    Nose-to-ankle pixel distance corresponds to ~0.93 of the user's full
    standing height. This factor approximates the head-top-to-floor span
    minus the portion above the nose and below the ankle bone. It gives
    a pragmatic, repeatable scale without requiring a physical ruler.
"""

# Fraction of total standing height represented by the nose->ankle span.
# Tunable; 0.93 works well in practice for upright frontal poses.
NOSE_ANKLE_FRACTION = 0.93


def compute_scale_cm_per_px(ref_px: float, user_height_cm: float) -> float:
    """
    Return cm-per-pixel given the measured nose->ankle pixel distance and
    the user's actual height in centimeters.
    """
    if ref_px <= 0 or user_height_cm <= 0:
        return 0.0
    real_cm = user_height_cm * NOSE_ANKLE_FRACTION
    return real_cm / ref_px


def px_to_cm(value_px: float, scale_cm_per_px: float) -> float:
    """Apply a precomputed scale factor to a single pixel measurement."""
    return value_px * scale_cm_per_px


def convert_all(measurements_px: dict, user_height_cm: float) -> dict:
    """
    Convert a dict of pixel measurements (as returned by
    measurement.all_measurements_px) into centimeters.
    """
    scale = compute_scale_cm_per_px(measurements_px.get("ref_px", 0.0),
                                    user_height_cm)
    return {
        "arm_cm": px_to_cm(measurements_px["arm_px"], scale),
        "shoulder_cm": px_to_cm(measurements_px["shoulder_px"], scale),
        "thigh_cm": px_to_cm(measurements_px["thigh_px"], scale),
        "scale": scale,
    }
