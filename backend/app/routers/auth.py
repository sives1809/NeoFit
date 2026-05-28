"""
routers/auth.py
---------------
Authentication endpoints.

Login / signup / password-reset happen ENTIRELY on the frontend using the
Supabase JS SDK — the backend never handles credentials.

This router provides:
  GET  /auth/me            Verify the JWT and return the current user's info
  GET  /auth/profile-check Return whether the user has completed onboarding
"""

from fastapi import APIRouter
from app.dependencies import CurrentUser, DB

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
async def me(user: CurrentUser) -> dict:
    """
    Validate the JWT and return basic user info.

    The frontend can call this on startup to confirm the token is still valid
    and to recover the user_id for subsequent requests.
    """
    return {
        "user_id": user["user_id"],
        "email":   user["email"],
        "role":    user["role"],
    }


@router.get("/profile-check")
async def profile_check(user: CurrentUser, db: DB) -> dict:
    """
    Return whether the authenticated user has a profile row in the DB.

    The frontend uses this immediately after login to decide whether to
    redirect to /onboarding or directly to /dashboard.
    """
    result = (
        db.table("profiles")
        .select("id")
        .eq("id", user["user_id"])
        .maybe_single()
        .execute()
    )
    has_profile = result is not None and getattr(result, "data", None) is not None
    return {"has_profile": has_profile}
