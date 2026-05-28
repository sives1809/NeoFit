"""
routers/profile.py
------------------
GET  /profile      Return the current user's biological profile
POST /profile      Create profile (onboarding)
PUT  /profile      Update profile fields
"""

from fastapi import APIRouter, HTTPException, status
from app.dependencies import CurrentUser, DB
from app.models.profile import ProfileCreate, ProfileUpdate, ProfileOut

router = APIRouter(prefix="/profile", tags=["profile"])


from fastapi import APIRouter, HTTPException, status
from app.dependencies import CurrentUser, DB
from app.models.profile import ProfileCreate, ProfileUpdate, ProfileOut
from app.services.normalization import normalize_goal, normalize_diet, normalize_sex, map_to_db_profile

router = APIRouter(prefix="/profile", tags=["profile"])


def normalize_profile_response(profile: dict) -> dict:
    p = dict(profile)
    p["fitness_goal"] = normalize_goal(p.get("fitness_goal"))
    p["diet_pref"] = normalize_diet(p.get("diet_pref"))
    p["sex"] = normalize_sex(p.get("sex"))
    return p


@router.get("", response_model=dict)
async def get_profile(user: CurrentUser, db: DB) -> dict:
    result = (
        db.table("profiles")
        .select("*")
        .eq("id", user["user_id"])
        .maybe_single()
        .execute()
    )
    if not result or not getattr(result, "data", None):
        raise HTTPException(status_code=404, detail="Profile not found. Complete onboarding first.")
    
    return normalize_profile_response(result.data)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_profile(body: ProfileCreate, user: CurrentUser, db: DB) -> dict:
    row = {"id": user["user_id"], **body.model_dump()}
    mapped_row = map_to_db_profile(row)
    result = db.table("profiles").upsert(mapped_row).execute()
    if not result or not getattr(result, "data", None):
        raise HTTPException(status_code=500, detail="Failed to save profile")
    return normalize_profile_response(result.data[0])


@router.put("")
async def update_profile(body: ProfileUpdate, user: CurrentUser, db: DB) -> dict:
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=422, detail="No fields to update.")

    mapped_updates = map_to_db_profile(updates)
    result = (
        db.table("profiles")
        .update(mapped_updates)
        .eq("id", user["user_id"])
        .execute()
    )
    if not result or not getattr(result, "data", None):
        raise HTTPException(status_code=404, detail="Profile not found.")
    return normalize_profile_response(result.data[0])


