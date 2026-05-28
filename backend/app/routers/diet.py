"""
routers/diet.py
---------------
GET  /diet           Return (or compute) the diet plan for the current user
POST /diet/refresh   Force recomputation from the latest profile
"""

from fastapi import APIRouter, HTTPException
from app.dependencies import CurrentUser, DB
from app.services.diet_engine import compute_diet_plan
import json

router = APIRouter(prefix="/diet", tags=["diet"])


from app.services.normalization import normalize_goal, normalize_diet, normalize_sex

def _compute_and_cache(user_id: str, db) -> dict:
    """Fetch profile, compute plan, upsert into diet_plans, return plan dict."""
    profile_res = (
        db.table("profiles")
        .select("*")
        .eq("id", user_id)
        .maybe_single()
        .execute()
    )
    if not profile_res or not getattr(profile_res, "data", None):
        raise HTTPException(status_code=404, detail="Complete your profile first.")

    profile = dict(profile_res.data)
    profile["fitness_goal"] = normalize_goal(profile.get("fitness_goal"))
    profile["diet_pref"] = normalize_diet(profile.get("diet_pref"))
    profile["sex"] = normalize_sex(profile.get("sex"))

    plan = compute_diet_plan(profile)
    row = {
        "user_id":      user_id,
        "bmr":          plan.bmr,
        "tdee":         plan.tdee,
        "cal_target":   plan.calorie_target,
        "protein_g":    plan.protein_g,
        "carbs_g":      plan.carbs_g,
        "fat_g":        plan.fat_g,
        "water_ml":     plan.water_ml,
        "meals":        plan.meals,    # stored as JSONB
    }
    # Upsert: replace any existing plan for this user
    db.table("diet_plans").upsert(row, on_conflict="user_id").execute()
    return row


@router.get("")
async def get_diet(user: CurrentUser, db: DB) -> dict:
    """Return the cached diet plan, or compute one if none exists yet."""
    cached = (
        db.table("diet_plans")
        .select("*")
        .eq("user_id", user["user_id"])
        .order("computed_at", desc=True)
        .limit(1)
        .maybe_single()
        .execute()
    )
    if cached and getattr(cached, "data", None):
        return cached.data
    # No cache — compute now
    return _compute_and_cache(user["user_id"], db)


@router.post("/refresh")
async def refresh_diet(user: CurrentUser, db: DB) -> dict:
    """Force recomputation of the diet plan from the latest profile."""
    return _compute_and_cache(user["user_id"], db)
