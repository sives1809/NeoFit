"""
routers/sessions.py
-------------------
POST /sessions          Save a completed measurement session
GET  /sessions          List all sessions for the current user (newest first)
GET  /sessions/{id}     Get a single session by ID
DELETE /sessions/{id}   Delete a session
"""

from fastapi import APIRouter, HTTPException, status
from app.dependencies import CurrentUser, DB
from app.models.profile import SessionCreate, SessionListItem
from app.services.normalization import is_session_physiologically_valid, check_session_physiological_validity

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_session(body: SessionCreate, user: CurrentUser, db: DB) -> dict:
    # Calculate average side depths for logging
    chest_depth = None
    if body.chest_side_left_cm is not None or body.chest_side_right_cm is not None:
        vals = [x for x in (body.chest_side_left_cm, body.chest_side_right_cm) if x is not None]
        chest_depth = sum(vals) / len(vals)
    waist_depth = None
    if body.waist_side_left_cm is not None or body.waist_side_right_cm is not None:
        vals = [x for x in (body.waist_side_left_cm, body.waist_side_right_cm) if x is not None]
        waist_depth = sum(vals) / len(vals)
    hip_depth = None
    if body.hip_side_left_cm is not None or body.hip_side_right_cm is not None:
        vals = [x for x in (body.hip_side_left_cm, body.hip_side_right_cm) if x is not None]
        hip_depth = sum(vals) / len(vals)

    # 1. Log exact values
    print("shoulder_width_cm:", body.shoulder_cm)
    print("\nfront:")
    print("chest_front_cm:", body.chest_cm)
    print("waist_front_cm:", body.waist_cm)
    print("hip_front_cm:", body.hip_cm)
    print("\nside:")
    print("chest_depth_cm:", chest_depth)
    print("waist_depth_cm:", waist_depth)
    print("hip_depth_cm:", hip_depth)
    print("\nfinal:")
    print("chest_girth_cm:", body.chest_girth_cm)
    print("waist_girth_cm:", body.waist_girth_cm)
    print("hip_girth_cm:", body.hip_girth_cm)
    print("left_arm_girth_cm:", body.arm_left_girth_cm)
    print("right_arm_girth_cm:", body.arm_right_girth_cm)
    print("left_thigh_girth_cm:", body.thigh_left_girth_cm)
    print("right_thigh_girth_cm:", body.thigh_right_girth_cm)

    # 2. Check physiological validity
    valid, reason = check_session_physiological_validity(body.model_dump())
    if not valid:
        contamination_info = ""
        if body.hip_cm and hip_depth and hip_depth > 1.6 * body.hip_cm:
            contamination_info = " (side depth contamination detected)"
        elif body.waist_cm and waist_depth and waist_depth > 1.6 * body.waist_cm:
            contamination_info = " (side depth contamination detected)"
        elif body.chest_cm and chest_depth and chest_depth > 1.6 * body.chest_cm:
            contamination_info = " (side depth contamination detected)"
        elif body.arm_left_cm and body.arm_side_left_cm and body.arm_side_left_cm > 2.2 * body.arm_left_cm:
            contamination_info = " (side depth contamination detected)"
        elif body.arm_right_cm and body.arm_side_right_cm and body.arm_side_right_cm > 2.2 * body.arm_right_cm:
            contamination_info = " (side depth contamination detected)"
        
        rejection_msg = f"Rejected: {reason}{contamination_info}"
        print(f"[SESSION SAVE REJECTED] {rejection_msg}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=rejection_msg
        )

    row = {"user_id": user["user_id"], **body.model_dump(exclude_none=True)}
    result = db.table("sessions").insert(row).execute()
    return result.data[0]


@router.post("/cleanup")
async def cleanup_sessions(user: CurrentUser, db: DB) -> dict:
    deleted_count = 0
    try:
        res1 = db.table("sessions").delete().gt("chest_girth_cm", 180).execute()
        res2 = db.table("sessions").delete().gt("waist_girth_cm", 160).execute()
        res3 = db.table("sessions").delete().gt("hip_girth_cm", 180).execute()
        res4 = db.table("sessions").delete().gt("arm_left_girth_cm", 80).execute()
        res5 = db.table("sessions").delete().gt("arm_right_girth_cm", 80).execute()
        res6 = db.table("sessions").delete().gt("thigh_left_girth_cm", 100).execute()
        res7 = db.table("sessions").delete().gt("thigh_right_girth_cm", 100).execute()
        
        for res in [res1, res2, res3, res4, res5, res6, res7]:
            if res and getattr(res, "data", None):
                deleted_count += len(res.data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database cleanup failed: {e}"
        )
    return {"status": "success", "deleted_count": deleted_count}


@router.get("")
async def list_sessions(user: CurrentUser, db: DB) -> list[dict]:
    result = (
        db.table("sessions")
        .select("*")
        .eq("user_id", user["user_id"])
        .order("captured_at", desc=True)
        .execute()
    )
    sessions = result.data or []
    return [s for s in sessions if is_session_physiologically_valid(s)]


@router.get("/{session_id}")
async def get_session(session_id: str, user: CurrentUser, db: DB) -> dict:
    result = (
        db.table("sessions")
        .select("*")
        .eq("id", session_id)
        .eq("user_id", user["user_id"])
        .maybe_single()
        .execute()
    )
    if not result or not getattr(result, "data", None):
        raise HTTPException(status_code=404, detail="Session not found.")
    return result.data


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: str, user: CurrentUser, db: DB) -> None:
    result = (
        db.table("sessions")
        .delete()
        .eq("id", session_id)
        .eq("user_id", user["user_id"])
        .execute()
    )
    if not result or not getattr(result, "data", None):
        raise HTTPException(status_code=404, detail="Session not found.")
