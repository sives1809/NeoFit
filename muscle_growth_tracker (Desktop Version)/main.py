"""
main.py
-------
Entry point for the AI Muscle Growth Tracker.

Captures webcam video, runs MediaPipe Pose, draws the skeleton overlay,
shows live measurements, and handles key bindings:

    M  toggle capture MODE (front <-> side)
    F  capture FRONT view (widths)   — requires FRONT mode
    S  capture SIDE view (thicknesses) — requires SIDE mode
    C  combine into pseudo-3D area + save row to CSV
    V  open growth charts (matplotlib window)
    Q  quit

Usage:
    python main.py
"""

import sys
from collections import deque
from statistics import median

import cv2
import mediapipe as mp

from measurement import all_measurements_px
from scaling import convert_all
from pseudo3d import compute_pseudo3d
from storage import save_measurement

# ---------- Config ----------
WINDOW_NAME = "AI Muscle Growth Tracker"
BUFFER_SIZE = 12              # rolling window for stability
MAX_TILT_DEG_FROM_HORIZ = 12  # FRONT mode: reject tilted shoulders
SIDE_SHOULDER_DX_RATIO = 0.08  # SIDE mode: shoulders should be ~stacked
                               # (|Lx-Rx| / nose-ankle reference)

# ---------- Theme (BGR) ----------
COL_BG          = (24, 24, 28)       # dark panel base
COL_BG_SOFT     = (40, 40, 48)       # secondary panel
COL_BORDER      = (90, 90, 100)
COL_TEXT        = (240, 240, 240)
COL_TEXT_DIM    = (170, 170, 175)
COL_ACCENT      = (255, 180,  60)    # cyan/amber accent (BGR -> orange-ish)
COL_OK          = ( 90, 210, 110)    # green
COL_WARN        = ( 60, 200, 240)    # yellow
COL_REJECT      = ( 70,  70, 230)    # red
COL_INFO        = (220, 170,  60)    # cyan-blue

FONT = cv2.FONT_HERSHEY_SIMPLEX


def prompt_height_cm() -> float:
    """Ask the user for their real height before starting the camera."""
    while True:
        try:
            raw = input("Enter your height in centimeters (e.g. 175): ").strip()
            h = float(raw)
            if 80.0 <= h <= 250.0:
                return h
            print("Please enter a value between 80 and 250 cm.")
        except ValueError:
            print("Please enter a number.")


def median_dict(buffer):
    """Median-aggregate a deque of measurement dicts (per key)."""
    if not buffer:
        return {}
    keys = buffer[0].keys()
    return {k: median(d[k] for d in buffer) for k in keys}


# ---------- UI helpers ----------

def _rounded_panel(frame, x1, y1, x2, y2, color=COL_BG, alpha=0.65,
                   border=COL_BORDER, radius=12):
    """Draw a semi-transparent rounded panel with a 1px border."""
    overlay = frame.copy()
    # body
    cv2.rectangle(overlay, (x1 + radius, y1), (x2 - radius, y2), color, -1)
    cv2.rectangle(overlay, (x1, y1 + radius), (x2, y2 - radius), color, -1)
    # rounded corners
    cv2.circle(overlay, (x1 + radius, y1 + radius), radius, color, -1)
    cv2.circle(overlay, (x2 - radius, y1 + radius), radius, color, -1)
    cv2.circle(overlay, (x1 + radius, y2 - radius), radius, color, -1)
    cv2.circle(overlay, (x2 - radius, y2 - radius), radius, color, -1)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
    # border
    cv2.rectangle(frame, (x1, y1), (x2, y2), border, 1, cv2.LINE_AA)


def _text(frame, txt, org, scale=0.55, color=COL_TEXT, thick=1):
    cv2.putText(frame, txt, org, FONT, scale, color, thick, cv2.LINE_AA)


def _pill(frame, x, y, label, color):
    """Small status pill with colored dot."""
    pad_x, pad_y = 10, 6
    (tw, th), _ = cv2.getTextSize(label, FONT, 0.5, 1)
    w = tw + pad_x * 2 + 16
    h = th + pad_y * 2
    _rounded_panel(frame, x, y, x + w, y + h,
                   color=COL_BG_SOFT, alpha=0.85, border=color, radius=h // 2)
    cv2.circle(frame, (x + 12, y + h // 2), 4, color, -1, cv2.LINE_AA)
    _text(frame, label, (x + 22, y + h - pad_y - 2), 0.5, COL_TEXT, 1)
    return w, h


def _classify_status(status: str):
    """Return (short_label, color) for the status banner."""
    s = status.lower()
    if s.startswith("reject") or s.startswith("no pose"):
        return "REJECT", COL_REJECT
    if s.startswith("saved"):
        return "SAVED", COL_OK
    if "captured" in s:
        return "CAPTURED", COL_OK
    if s.startswith("tracking"):
        return "READY", COL_INFO
    return status.upper(), COL_WARN


def draw_overlay(frame, measurements_cm, status, front_cm, side_cm,
                 last_areas, mode: str = "front"):
    h, w = frame.shape[:2]

    # ---- Top header bar ----
    _rounded_panel(frame, 12, 12, w - 12, 56,
                   color=COL_BG, alpha=0.7, border=COL_BORDER, radius=10)
    _text(frame, "AI MUSCLE GROWTH TRACKER", (28, 42), 0.7, COL_TEXT, 2)

    # mode badge next to title
    (ttw, _), _ = cv2.getTextSize("AI MUSCLE GROWTH TRACKER", FONT, 0.7, 2)
    mode_label = f"MODE: {mode.upper()}"
    mcol = COL_INFO if mode == "front" else COL_ACCENT
    mx = 28 + ttw + 16
    (mtw, _), _ = cv2.getTextSize(mode_label, FONT, 0.5, 2)
    _rounded_panel(frame, mx, 24, mx + mtw + 24, 48,
                   color=COL_BG_SOFT, alpha=0.9, border=mcol, radius=12)
    _text(frame, mode_label, (mx + 12, 41), 0.5, mcol, 2)

    short, scol = _classify_status(status)
    # status pill on the right of header
    pill_label = f"{short}"
    (tw, _), _ = cv2.getTextSize(pill_label, FONT, 0.55, 2)
    pill_w = tw + 36
    pill_x = w - 24 - pill_w
    _rounded_panel(frame, pill_x, 22, w - 24, 50,
                   color=COL_BG_SOFT, alpha=0.9, border=scol, radius=14)
    cv2.circle(frame, (pill_x + 14, 36), 5, scol, -1, cv2.LINE_AA)
    _text(frame, pill_label, (pill_x + 26, 42), 0.55, scol, 2)

    # ---- Left measurement panel ----
    panel_x1, panel_y1, panel_x2, panel_y2 = 12, 72, 320, 270
    _rounded_panel(frame, panel_x1, panel_y1, panel_x2, panel_y2,
                   color=COL_BG, alpha=0.65, border=COL_BORDER, radius=12)
    _text(frame, "MEASUREMENTS", (panel_x1 + 16, panel_y1 + 26),
          0.5, COL_TEXT_DIM, 1)
    cv2.line(frame, (panel_x1 + 16, panel_y1 + 34),
             (panel_x2 - 16, panel_y1 + 34), COL_BORDER, 1, cv2.LINE_AA)

    rows = [
        ("Arm",      measurements_cm.get('arm_cm', 0.0)),
        ("Shoulder", measurements_cm.get('shoulder_cm', 0.0)),
        ("Thigh",    measurements_cm.get('thigh_cm', 0.0)),
    ]
    base_y = panel_y1 + 64
    for i, (label, val) in enumerate(rows):
        y = base_y + i * 38
        _text(frame, label, (panel_x1 + 18, y), 0.55, COL_TEXT_DIM, 1)
        val_txt = f"{val:6.1f}"
        unit_txt = " cm"
        # right-aligned value
        (vw, _), _ = cv2.getTextSize(val_txt, FONT, 0.8, 2)
        vx = panel_x2 - 16 - vw - 26
        _text(frame, val_txt, (vx, y + 4), 0.8, COL_TEXT, 2)
        _text(frame, unit_txt, (vx + vw + 4, y + 4), 0.55, COL_ACCENT, 1)

    # divider
    cv2.line(frame, (panel_x1 + 16, panel_y1 + 188),
             (panel_x2 - 16, panel_y1 + 188), COL_BORDER, 1, cv2.LINE_AA)

    # capture indicators
    fcol = COL_OK if front_cm else COL_TEXT_DIM
    scol2 = COL_OK if side_cm else COL_TEXT_DIM
    _pill(frame, panel_x1 + 16, panel_y1 + 200, "FRONT", fcol)
    _pill(frame, panel_x1 + 110, panel_y1 + 200, "SIDE", scol2)

    # ---- Right pseudo-3D panel ----
    rp_x1, rp_y1, rp_x2, rp_y2 = w - 290, 72, w - 12, 200
    _rounded_panel(frame, rp_x1, rp_y1, rp_x2, rp_y2,
                   color=COL_BG, alpha=0.65, border=COL_BORDER, radius=12)
    _text(frame, "PSEUDO-3D AREA", (rp_x1 + 16, rp_y1 + 26),
          0.5, COL_TEXT_DIM, 1)
    cv2.line(frame, (rp_x1 + 16, rp_y1 + 34),
             (rp_x2 - 16, rp_y1 + 34), COL_BORDER, 1, cv2.LINE_AA)

    arm_a = last_areas.get('arm_area', 0.0)
    thigh_a = last_areas.get('thigh_area', 0.0)
    for i, (label, val) in enumerate([("Arm", arm_a), ("Thigh", thigh_a)]):
        y = rp_y1 + 64 + i * 36
        _text(frame, label, (rp_x1 + 18, y), 0.55, COL_TEXT_DIM, 1)
        vt = f"{val:6.1f}"
        (vw, _), _ = cv2.getTextSize(vt, FONT, 0.7, 2)
        vx = rp_x2 - 16 - vw - 38
        _text(frame, vt, (vx, y + 4), 0.7, COL_TEXT, 2)
        _text(frame, " cm^2", (vx + vw + 2, y + 4), 0.5, COL_ACCENT, 1)

    # ---- Bottom controls bar ----
    bar_h = 44
    _rounded_panel(frame, 12, h - bar_h - 12, w - 12, h - 12,
                   color=COL_BG, alpha=0.75, border=COL_BORDER, radius=10)

    controls = [
        ("M", "Mode",   COL_WARN),
        ("F", "Front",  COL_INFO),
        ("S", "Side",   COL_INFO),
        ("C", "Save",   COL_OK),
        ("V", "Charts", COL_ACCENT),
        ("Q", "Quit",   COL_REJECT),
    ]
    cx = 28
    cy = h - bar_h // 2 - 12
    for key, label, col in controls:
        # key chip
        chip_w = 26
        chip_h = 24
        x1 = cx
        y1 = cy - chip_h // 2
        _rounded_panel(frame, x1, y1, x1 + chip_w, y1 + chip_h,
                       color=COL_BG_SOFT, alpha=0.95, border=col, radius=6)
        (kw, kh), _ = cv2.getTextSize(key, FONT, 0.55, 2)
        _text(frame, key,
              (x1 + (chip_w - kw) // 2, y1 + (chip_h + kh) // 2 - 1),
              0.55, col, 2)
        # label
        _text(frame, label, (x1 + chip_w + 8, cy + 5), 0.5, COL_TEXT, 1)
        (lw, _), _ = cv2.getTextSize(label, FONT, 0.5, 1)
        cx = x1 + chip_w + 8 + lw + 22

    # status text on the right side of the bottom bar
    msg = status if len(status) < 60 else status[:57] + "..."
    (mw, _), _ = cv2.getTextSize(msg, FONT, 0.5, 1)
    _text(frame, msg, (w - 24 - mw, cy + 5), 0.5, scol, 1)


def validate_front_pose(m_px: dict) -> tuple:
    """FRONT pose: shoulders should be roughly horizontal.
    Returns (ok, reason)."""
    tilt = m_px.get("tilt_deg", 0.0)
    # treat ~0 and ~180 as horizontal (atan2 wrap)
    horiz_ok = (tilt <= MAX_TILT_DEG_FROM_HORIZ) or \
               ((180 - tilt) <= MAX_TILT_DEG_FROM_HORIZ)
    if not horiz_ok:
        return False, "Reject: square up to camera"
    return True, ""


def validate_side_pose(m_px: dict) -> tuple:
    """SIDE pose: shoulders should be (nearly) stacked along x-axis,
    so |left_shoulder.x - right_shoulder.x| is small relative to body height.
    Returns (ok, reason)."""
    dx = m_px.get("shoulder_dx_px", 0.0)
    ref = max(m_px.get("ref_px", 1.0), 1.0)
    if (dx / ref) > SIDE_SHOULDER_DX_RATIO:
        return False, "Reject: turn sideways to camera"
    return True, ""


def main() -> int:
    user_height_cm = prompt_height_cm()

    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
    mp_styles = mp.solutions.drawing_styles

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: cannot open webcam (index 0).")
        return 1

    buffer = deque(maxlen=BUFFER_SIZE)
    front_cm: dict = {}
    side_cm: dict = {}
    last_areas: dict = {"arm_area": 0.0, "thigh_area": 0.0}
    status = "Tracking"
    mode = "front"  # 'front' or 'side' — toggled with M

    with mp_pose.Pose(model_complexity=1,
                      enable_segmentation=False,
                      min_detection_confidence=0.5,
                      min_tracking_confidence=0.5) as pose:

        while True:
            ok, frame = cap.read()
            if not ok:
                print("Frame grab failed; exiting.")
                break

            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb.flags.writeable = False
            results = pose.process(rgb)
            rgb.flags.writeable = True

            stable_cm: dict = {}

            if results.pose_landmarks:
                # Skeleton overlay
                mp_drawing.draw_landmarks(
                    frame,
                    results.pose_landmarks,
                    mp_pose.POSE_CONNECTIONS,
                    landmark_drawing_spec=mp_styles
                    .get_default_pose_landmarks_style(),
                )

                m_px = all_measurements_px(
                    results.pose_landmarks.landmark, w, h)

                # Mode-specific validation
                if mode == "front":
                    ok_pose, reason = validate_front_pose(m_px)
                else:
                    ok_pose, reason = validate_side_pose(m_px)

                if not ok_pose:
                    status = reason
                    buffer.clear()  # don't pollute the median window
                else:
                    buffer.append(m_px)
                    smoothed = median_dict(buffer)
                    stable_cm = convert_all(smoothed, user_height_cm)
                    if status.startswith("Reject") or status == "No pose detected":
                        status = "Tracking"
            else:
                status = "No pose detected"

            draw_overlay(frame, stable_cm, status, front_cm, side_cm,
                         last_areas, mode=mode)
            cv2.imshow(WINDOW_NAME, frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('m'):
                mode = "side" if mode == "front" else "front"
                buffer.clear()
                status = f"Mode: {mode.upper()}"
            elif key == ord('f') and stable_cm:
                if mode != "front":
                    status = "Reject: switch to FRONT mode (M)"
                else:
                    front_cm = dict(stable_cm)
                    status = "Front Captured"
                    # auto-suggest side next
                    mode = "side"
                    buffer.clear()
            elif key == ord('s') and stable_cm:
                if mode != "side":
                    status = "Reject: switch to SIDE mode (M)"
                else:
                    side_cm = dict(stable_cm)
                    status = "Side Captured"
            elif key == ord('c'):
                if not front_cm or not side_cm:
                    status = "Reject: need F and S first"
                else:
                    last_areas = compute_pseudo3d(front_cm, side_cm)
                    path = save_measurement(front_cm, last_areas)
                    status = f"Saved -> {path}"
            elif key == ord('v'):
                try:
                    from visualization import load_data, plot_growth
                    plot_growth(load_data())
                except Exception as e:
                    print(f"Could not open charts: {e}")

    cap.release()
    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    sys.exit(main())
