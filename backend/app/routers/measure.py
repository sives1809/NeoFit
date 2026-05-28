"""
routers/measure.py
------------------
Real-time measurement endpoints.

POST /measure/frame     Process a single webcam frame worth of landmarks.
                        Called by the frontend on every pose-detection tick.
                        Returns per-side cm measurements + stability signal.

POST /measure/combine   Combine confirmed front + side CapturePayloads into
                        pseudo-3D girth / area values. Called once by the
                        frontend after both views are captured.

Design note
-----------
The StabilityBuffer is STATEFUL and must persist across multiple /frame
calls for the same session. Because HTTP is stateless, we have two options:

  Option A: Server-side buffer keyed by user_id (in-process dict).
            Simple, works for a single-server deployment (which is all
            we need for the academic prototype).

  Option B: Client-side accumulation (frontend stores frames, calls
            /measure/combine when it decides it's stable).

We implement Option A here with an in-process dict of StabilityBuffer
instances keyed by user_id. This is reset when the user calls /reset.
For a multi-server deployment, migrate to Redis. For the prototype, this
is correct and simple.
"""

from __future__ import annotations

from fastapi import APIRouter
from app.cv.measurement import (
    Landmark as CvLandmark,
    all_measurements_px,
    is_frame_usable,
    log_arm_debug,
)
from app.cv.scaling import convert_all, asymmetry_pct
from app.cv.pseudo3d import compute_pseudo3d
from app.cv.stability import StabilityBuffer
from app.models.measure import (
    MeasureRequest,
    MeasureResponse,
    ValidationResult,
    CapturePayload,
    CombineRequest,
)
from app.dependencies import CurrentUser

router = APIRouter(prefix="/measure", tags=["measure"])

# ── In-process stability buffer store (one per user, per mode) ───────────────
# Key: (user_id, mode)
_buffers: dict[tuple[str, str], StabilityBuffer] = {}

MAX_TILT_DEG         = 12.0   # FRONT: shoulder line must be < 12° from horizontal
MAX_SHOULDER_H_RATIO = 0.12   # SIDE:  shoulder stack threshold (relaxed to 0.12 for usability)

def _get_buffer(user_id: str, mode: str) -> StabilityBuffer:
    key = (user_id, mode)
    if key not in _buffers:
        if mode == "left_side":
            key_metrics = (
                "arm_left_px",
                "thigh_left_px",
            )
            _buffers[key] = StabilityBuffer(key_metrics=key_metrics)
        elif mode == "right_side":
            key_metrics = (
                "arm_right_px",
                "thigh_right_px",
            )
            _buffers[key] = StabilityBuffer(key_metrics=key_metrics)
        elif mode == "side":
            key_metrics = (
                "arm_left_px", "arm_right_px",
                "thigh_left_px", "thigh_right_px",
            )
            _buffers[key] = StabilityBuffer(key_metrics=key_metrics)
        else:
            _buffers[key] = StabilityBuffer()
    return _buffers[key]



# ── Pose validation (same rules as original desktop prototype) ────────────────

def _validate(m: dict, mode: str) -> ValidationResult:
    if mode == "front":
        tilt = m.get("tilt_deg")
        if tilt is None:
            return ValidationResult(ok=False, reason="Shoulders not detected")
        horiz_ok = (tilt <= MAX_TILT_DEG) or ((180 - tilt) <= MAX_TILT_DEG)
        if not horiz_ok:
            return ValidationResult(ok=False, reason="Square your shoulders to the camera")
            
        sh_w = m.get("shoulder_px")
        if sh_w is not None and sh_w > 0:
            for key in ("chest_px", "waist_px", "hip_px"):
                val = m.get(key)
                if val is not None and val > sh_w * 1.8:
                    return ValidationResult(ok=False, reason="Measurement invalid. Torso detection failed. Please retake scan.")
            
            waist_px = m.get("waist_px")
            if waist_px is not None and waist_px > sh_w * 1.15:
                return ValidationResult(ok=False, reason="Suspicious waist measurement. Please keep arms away from torso.")

            chest_px = m.get("chest_px")
            if chest_px is not None and chest_px > sh_w * 1.35:
                return ValidationResult(ok=False, reason="Suspicious chest measurement. Please keep arms away from torso.")

            hip_px = m.get("hip_px")
            if hip_px is not None and hip_px > sh_w * 1.4:
                return ValidationResult(ok=False, reason="Suspicious hip measurement. Please keep arms away from torso.")
                    
        return ValidationResult(ok=True)

    elif mode in ("side", "left_side", "right_side"):
        ratio = m.get("shoulder_h_ratio")
        if ratio is None:
            return ValidationResult(ok=False, reason="Shoulders not detected")
        if ratio > MAX_SHOULDER_H_RATIO:
            return ValidationResult(ok=False, reason="Turn fully sideways to the camera")
        
        # Enforce direction orientation for left and right captures
        if mode == "left_side":
            orientation = m.get("orientation")
            if orientation != "left":
                return ValidationResult(ok=False, reason="Turn to your right (showing LEFT profile)")
        elif mode == "right_side":
            orientation = m.get("orientation")
            if orientation != "right":
                return ValidationResult(ok=False, reason="Turn to your left (showing RIGHT profile)")
                
        return ValidationResult(ok=True)

    return ValidationResult(ok=False, reason=f"Unknown mode: {mode}")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/frame", response_model=MeasureResponse)
async def process_frame(body: MeasureRequest, user: CurrentUser) -> MeasureResponse:
    """
    Process a single frame of MediaPipe landmarks.

    Called by the webcam component on every pose-detection tick (~4–15 fps).
    Returns the current smoothed measurement and the auto-capture signal.
    """
    # Convert Pydantic landmarks → CV dataclass
    lms = [CvLandmark(x=lm.x, y=lm.y, z=lm.z, visibility=lm.visibility)
           for lm in body.landmarks]

    # Raw pixel measurements
    m_px = all_measurements_px(
        lms,
        body.video_width,
        body.video_height,
        silhouette_chest_px=body.silhouette_chest_px,
        silhouette_waist_px=body.silhouette_waist_px,
        silhouette_hip_px=body.silhouette_hip_px,
        silhouette_arm_left_px=body.silhouette_arm_left_px,
        silhouette_arm_right_px=body.silhouette_arm_right_px,
        mode=body.mode,
    )


    # Pose validation
    validation = _validate(m_px, body.mode)

    buf = _get_buffer(user["user_id"], body.mode)

    # Create a mirrored version of m_px for usability and stability validation in side mode
    m_px_val = m_px.copy()
    if body.mode in ("side", "left_side", "right_side"):
        # Helper to mirror a metric pair if one of them is None
        def mirror_pair(key_l: str, key_r: str):
            val_l = m_px_val.get(key_l)
            val_r = m_px_val.get(key_r)
            if val_l is None and val_r is not None:
                m_px_val[key_l] = val_r
            elif val_r is None and val_l is not None:
                m_px_val[key_r] = val_l

        mirror_pair("arm_left_px", "arm_right_px")
        mirror_pair("thigh_left_px", "thigh_right_px")
        mirror_pair("arm_side_left_px", "arm_side_right_px")
        mirror_pair("thigh_side_left_px", "thigh_side_right_px")

    # If pose validation passes, double check that frame measurements are usable
    if validation.ok and not is_frame_usable(m_px_val, body.mode):
        missing_reasons = []
        if body.mode == "left_side":
            if m_px_val.get("arm_left_px") is None:
                missing_reasons.append("Keep left arm in view")
            if m_px_val.get("thigh_left_px") is None:
                missing_reasons.append("Keep left leg in view")
            if m_px_val.get("shoulder_px") is None:
                missing_reasons.append("Ensure shoulders are detected")
            if m_px_val.get("ref_px") is None:
                missing_reasons.append("Full body must be visible")
        elif body.mode == "right_side":
            if m_px_val.get("arm_right_px") is None:
                missing_reasons.append("Keep right arm in view")
            if m_px_val.get("thigh_right_px") is None:
                missing_reasons.append("Keep right leg in view")
            if m_px_val.get("shoulder_px") is None:
                missing_reasons.append("Ensure shoulders are detected")
            if m_px_val.get("ref_px") is None:
                missing_reasons.append("Full body must be visible")
        else:
            if m_px_val.get("arm_left_px") is None or m_px_val.get("arm_right_px") is None:
                missing_reasons.append("Keep both arms in view")
            if m_px_val.get("thigh_left_px") is None or m_px_val.get("thigh_right_px") is None:
                missing_reasons.append("Keep both legs in view")
            if m_px_val.get("shoulder_px") is None:
                missing_reasons.append("Ensure shoulders are detected")
            if m_px_val.get("ref_px") is None:
                missing_reasons.append("Full body must be visible")
        
        reason = " & ".join(missing_reasons) if missing_reasons else "Adjusting alignment..."
        validation = ValidationResult(ok=False, reason=reason)

    # RIGHT_SIDE temporary logging
    if body.mode == "right_side":
        required_keys = ["arm_right_px", "thigh_right_px", "shoulder_px", "ref_px"]
        missing = [k for k in required_keys if m_px_val.get(k) is None]
        usable = is_frame_usable(m_px_val, body.mode)
        log_msg = (
            f"Mode: {body.mode}\n"
            f"Validation OK: {validation.ok}, Reason: {validation.reason}\n"
            f"Is Frame Usable: {usable}\n"
            f"Missing metrics: {missing}\n"
            f"Buffer size: {len(buf._buffer)}\n"
            f"Stable counter: {buf._consecutive_stable}\n"
        )
        if not validation.ok or not usable:
            log_msg += "Returned early: True\n---\n"
        with open("debug_right_side.log", "a") as f_log:
            f_log.write(log_msg)

    if not validation.ok or not is_frame_usable(m_px_val, body.mode):
        buf.reset_counter()   # soft reset stability counter on bad frame
        return MeasureResponse(
            validation=validation,
            stability_progress=0.0,
            ready_to_capture=False,
        )

    # Scale to cm
    cm_val = convert_all(m_px_val, body.height_cm)
    if not cm_val:
        buf.reset_counter()
        return MeasureResponse(validation=ValidationResult(ok=False, reason="Scaling failed"))

    # Push pixel measurements (not cm) into the stability buffer
    # We use px so the buffer's CV thresholds are scale-independent
    buf.add(m_px_val)
    stability = buf.status()

    if body.mode == "right_side":
        log_msg = f"Progress: {stability['progress'] * 100:.1f}%, Ready: {stability['ready']}\n---\n"
        with open("debug_right_side.log", "a") as f_log:
            f_log.write(log_msg)

    # When ready, use the IQR-filtered pixel values → convert to cm
    final_cm = cm_val  # default: current frame's cm values
    if stability["ready"] and stability["filtered"]:
        # Log landmark coordinates used for torso derivation
        try:
            ls = lms[11]  # left shoulder
            rs = lms[12]  # right shoulder
            lh = lms[23]  # left hip
            rh = lms[24]  # right hip
            print(f"\n[DEBUG /frame CAPTURE SUCCESS] Mode: {body.mode}")
            print(f"LANDMARK COORDINATES:")
            print(f"  - Left Shoulder:  x={ls.x*body.video_width:.1f}, y={ls.y*body.video_height:.1f}")
            print(f"  - Right Shoulder: x={rs.x*body.video_width:.1f}, y={rs.y*body.video_height:.1f}")
            print(f"  - Left Hip:       x={lh.x*body.video_width:.1f}, y={lh.y*body.video_height:.1f}")
            print(f"  - Right Hip:      x={rh.x*body.video_width:.1f}, y={rh.y*body.video_height:.1f}")
            print(f"  - Torso Vertical: shoulder_y_avg={((ls.y + rs.y)/2)*body.video_height:.1f} -> hip_y_avg={((lh.y + rh.y)/2)*body.video_height:.1f}")
        except Exception as e:
            print(f"[DEBUG /frame CAPTURE SUCCESS] Error logging landmarks: {e}")

        filtered_px = stability["filtered"]
        final_cm = convert_all(filtered_px, body.height_cm)

        print("RAW PIXELS (FILTERED):")
        if body.mode in ("front", "side"):
            print(f"  - chest: {filtered_px.get('chest_px')}")
            print(f"  - waist: {filtered_px.get('waist_px')}")
            print(f"  - hip:   {filtered_px.get('hip_px')}")
            print(f"  - left arm width:  {filtered_px.get('arm_left_px')}")
            print(f"  - right arm width: {filtered_px.get('arm_right_px')}")
            print(f"  - left thigh width:  {filtered_px.get('thigh_left_px')}")
            print(f"  - right thigh width: {filtered_px.get('thigh_right_px')}")
        else:
            print(f"  - chest: {filtered_px.get('chest_side_px')}")
            print(f"  - waist: {filtered_px.get('waist_side_px')}")
            print(f"  - hip:   {filtered_px.get('hip_side_px')}")
            print(f"  - left arm width:  {filtered_px.get('arm_side_left_px') or filtered_px.get('arm_left_px')}")
            print(f"  - right arm width: {filtered_px.get('arm_side_right_px') or filtered_px.get('arm_right_px')}")
            print(f"  - left thigh width:  {filtered_px.get('thigh_side_left_px') or filtered_px.get('thigh_left_px')}")
            print(f"  - right thigh width: {filtered_px.get('thigh_side_right_px') or filtered_px.get('thigh_right_px')}")

        print("SCALED CM:")
        if body.mode in ("front", "side"):
            print(f"  - chest: {final_cm.get('chest_cm')}")
            print(f"  - waist: {final_cm.get('waist_cm')}")
            print(f"  - hip:   {final_cm.get('hip_cm')}")
            print(f"  - left arm width:  {final_cm.get('arm_left_cm')}")
            print(f"  - right arm width: {final_cm.get('arm_right_cm')}")
            print(f"  - left thigh width:  {final_cm.get('thigh_left_cm')}")
            print(f"  - right thigh width: {final_cm.get('thigh_right_cm')}")
        else:
            print(f"  - chest: {final_cm.get('chest_side_cm')}")
            print(f"  - waist: {final_cm.get('waist_side_cm')}")
            print(f"  - hip:   {final_cm.get('hip_side_cm')}")
            print(f"  - left arm width:  {final_cm.get('arm_side_left_cm') or final_cm.get('arm_left_cm')}")
            print(f"  - right arm width: {final_cm.get('arm_side_right_cm') or final_cm.get('arm_right_cm')}")
            print(f"  - left thigh width:  {final_cm.get('thigh_side_left_cm') or final_cm.get('thigh_left_cm')}")
            print(f"  - right thigh width: {final_cm.get('thigh_side_right_cm') or final_cm.get('thigh_right_cm')}")
        print("-" * 40 + "\n")

        buf.reset()   # fresh window for the next capture


    # Clear out non-target side metrics in left_side/right_side modes to avoid confusion
    if body.mode == "left_side":
        final_cm["arm_right_cm"] = None
        final_cm["thigh_right_cm"] = None
        final_cm["arm_side_right_cm"] = None
        final_cm["thigh_side_right_cm"] = None
    elif body.mode == "right_side":
        final_cm["arm_left_cm"] = None
        final_cm["thigh_left_cm"] = None
        final_cm["arm_side_left_cm"] = None
        final_cm["thigh_side_left_cm"] = None
    elif body.mode == "side":
        if m_px.get("arm_left_px") is None or m_px.get("thigh_left_px") is None:
            final_cm["arm_left_cm"] = None
            final_cm["thigh_left_cm"] = None
            final_cm["arm_side_left_cm"] = None
            final_cm["thigh_side_left_cm"] = None
        if m_px.get("arm_right_px") is None or m_px.get("thigh_right_px") is None:
            final_cm["arm_right_cm"] = None
            final_cm["thigh_right_cm"] = None
            final_cm["arm_side_right_cm"] = None
            final_cm["thigh_side_right_cm"] = None

    return MeasureResponse(
        validation=ValidationResult(ok=True),
        arm_left_cm=    round(final_cm.get("arm_left_cm",   0) or 0, 2) or None,
        arm_right_cm=   round(final_cm.get("arm_right_cm",  0) or 0, 2) or None,
        shoulder_cm=    round(final_cm.get("shoulder_cm",   0) or 0, 2) or None,
        chest_cm=       round(final_cm.get("chest_cm",      0) or 0, 2) or None,
        waist_cm=       round(final_cm.get("waist_cm",      0) or 0, 2) or None,
        hip_cm=         round(final_cm.get("hip_cm",        0) or 0, 2) or None,
        thigh_left_cm=  round(final_cm.get("thigh_left_cm", 0) or 0, 2) or None,
        thigh_right_cm= round(final_cm.get("thigh_right_cm",0) or 0, 2) or None,

        arm_side_left_cm=   round(final_cm.get("arm_side_left_cm",   0) or 0, 2) or None,
        arm_side_right_cm=  round(final_cm.get("arm_side_right_cm",  0) or 0, 2) or None,
        thigh_side_left_cm= round(final_cm.get("thigh_side_left_cm", 0) or 0, 2) or None,
        thigh_side_right_cm=round(final_cm.get("thigh_side_right_cm",0) or 0, 2) or None,
        chest_side_cm=      round(final_cm.get("chest_side_cm",      0) or 0, 2) or None,
        waist_side_cm=      round(final_cm.get("waist_side_cm",      0) or 0, 2) or None,
        hip_side_cm=        round(final_cm.get("hip_side_cm",        0) or 0, 2) or None,

        confidence=     round(m_px.get("confidence", 0) or 0, 3) or None,
        scale_cm_per_px=final_cm.get("scale_cm_per_px"),
        stability_progress=stability["progress"],
        ready_to_capture=stability["ready"],
    )


@router.post("/combine")
async def combine(
    body: CombineRequest,
    user: CurrentUser,
) -> dict:
    """
    Combine confirmed front-view, left-side-view, and right-side-view measurements 
    into pseudo-3D girth and area estimates.
    """
    # Front-view width measurements
    front_cm = {
        "arm_left_cm":   body.front.arm_left_cm,
        "arm_right_cm":  body.front.arm_right_cm,
        "shoulder_cm":   body.front.shoulder_cm,
        "chest_cm":       body.front.chest_cm,
        "waist_cm":       body.front.waist_cm,
        "hip_cm":         body.front.hip_cm,
        "thigh_left_cm": body.front.thigh_left_cm,
        "thigh_right_cm":body.front.thigh_right_cm,
    }

    # Left-side thickness measurements
    left_side_cm = {
        "arm_side_left_cm":   body.left_side.arm_side_left_cm or body.left_side.arm_left_cm,
        "thigh_side_left_cm":  body.left_side.thigh_side_left_cm or body.left_side.thigh_left_cm,
        "chest_side_cm":       body.left_side.chest_side_cm,
        "waist_side_cm":       body.left_side.waist_side_cm,
        "hip_side_cm":         body.left_side.hip_side_cm,
    }

    # Right-side thickness measurements
    right_side_cm = {
        "arm_side_right_cm":  body.right_side.arm_side_right_cm or body.right_side.arm_right_cm,
        "thigh_side_right_cm": body.right_side.thigh_side_right_cm or body.right_side.thigh_right_cm,
        "chest_side_cm":       body.right_side.chest_side_cm,
        "waist_side_cm":       body.right_side.waist_side_cm,
        "hip_side_cm":         body.right_side.hip_side_cm,
    }

    scale_front = body.front.scale_cm_per_px
    scale_side = body.left_side.scale_cm_per_px or body.right_side.scale_cm_per_px
    pseudo3d = compute_pseudo3d(
        front_cm,
        left_side_cm,
        right_side_cm,
        scale_front=scale_front,
        scale_side=scale_side,
        height_cm=body.height_cm,
    )

    log_arm_debug(
        arm_left_front_cm=body.front.arm_left_cm,
        arm_left_side_cm=left_side_cm.get("arm_side_left_cm"),
        arm_right_front_cm=body.front.arm_right_cm,
        arm_right_side_cm=right_side_cm.get("arm_side_right_cm"),
        scale_front=scale_front,
        scale_side=scale_side,
        arm_left_girth_cm=pseudo3d.get("arm_left_girth_cm"),
        arm_right_girth_cm=pseudo3d.get("arm_right_girth_cm"),
    )

    chest_girth = pseudo3d.get("chest_girth_cm")
    waist_girth = pseudo3d.get("waist_girth_cm")
    hip_girth = pseudo3d.get("hip_girth_cm")

    chest_front = front_cm.get("chest_cm")
    waist_front = front_cm.get("waist_cm")
    hip_front = front_cm.get("hip_cm")

    chest_side_l = left_side_cm.get("chest_side_cm")
    chest_side_r = right_side_cm.get("chest_side_cm")
    waist_side_l = left_side_cm.get("waist_side_cm")
    waist_side_r = right_side_cm.get("waist_side_cm")
    hip_side_l = left_side_cm.get("hip_side_cm")
    hip_side_r = right_side_cm.get("hip_side_cm")

    invalid = False
    error_msg = ""
    arm_left_front = front_cm.get("arm_left_cm")
    arm_right_front = front_cm.get("arm_right_cm")
    arm_left_side = left_side_cm.get("arm_side_left_cm")
    arm_right_side = right_side_cm.get("arm_side_right_cm")

    if (chest_girth is not None and chest_girth > 200.0) or \
       (waist_girth is not None and waist_girth > 200.0) or \
       (hip_girth is not None and hip_girth > 200.0):
        invalid = True
        error_msg = "Measurement invalid. Torso detection failed. Please retake scan."
    elif (chest_side_l is not None and chest_front is not None and chest_side_l > 1.6 * chest_front) or \
         (chest_side_r is not None and chest_front is not None and chest_side_r > 1.6 * chest_front) or \
         (waist_side_l is not None and waist_front is not None and waist_side_l > 1.6 * waist_front) or \
         (waist_side_r is not None and waist_front is not None and waist_side_r > 1.6 * waist_front) or \
         (hip_side_l is not None and hip_front is not None and hip_side_l > 1.6 * hip_front) or \
         (hip_side_r is not None and hip_front is not None and hip_side_r > 1.6 * hip_front) or \
         (arm_left_side is not None and arm_left_front is not None and arm_left_side > 2.2 * arm_left_front) or \
         (arm_right_side is not None and arm_right_front is not None and arm_right_side > 2.2 * arm_right_front):
        invalid = True
        error_msg = "Invalid side profile depth detected. Please stand straight and retake scan."

    return {
        "front":   body.front.model_dump(),
        "left_side": body.left_side.model_dump(),
        "right_side": body.right_side.model_dump(),
        "pseudo3d": pseudo3d,
        "measurement_invalid": invalid,
        "error_message": error_msg,
    }


@router.post("/reset")
async def reset_buffers(user: CurrentUser) -> dict:
    """Clear all mode buffers for the current user. Call when starting a new session."""
    for mode in ("front", "left_side", "right_side", "side"):
        key = (user["user_id"], mode)
        if key in _buffers:
            _buffers[key].reset()
    return {"ok": True, "status": "reset"}
