"""
models/profile.py  +  models/session.py
-----------------------------------------
Pydantic models for biological profile and measurement sessions.
These mirror the Supabase table schemas defined in the SQL migration.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════════════════════
# PROFILE
# ══════════════════════════════════════════════════════════════════════════════

ActivityLevel = Literal["sedentary", "light", "moderate", "active", "very_active"]
FitnessGoal   = Literal["lose_fat", "maintain", "lean_bulk", "build_muscle", "recomposition"]
DietPref      = Literal["vegetarian", "non_vegetarian", "vegan", "eggetarian", "pescatarian"]
Experience    = Literal["beginner", "intermediate", "advanced"]
Sex           = Literal["male", "female", "other", "prefer_not_to_say"]


class ProfileCreate(BaseModel):
    """Payload for initial profile creation (onboarding)."""
    full_name:      str  = Field(..., min_length=1, max_length=120)
    age:            int  = Field(..., ge=10, le=100)
    sex:            Sex
    height_cm:      float = Field(..., gt=80, le=250)
    weight_kg:      float = Field(..., gt=20, le=300)
    activity_level: ActivityLevel
    fitness_goal:   FitnessGoal
    diet_pref:      DietPref = "omnivore"
    allergies:      list[str] = []
    experience:     Experience = "beginner"


class ProfileUpdate(BaseModel):
    """Partial update — all fields optional."""
    full_name:      Optional[str]           = None
    age:            Optional[int]           = None
    sex:            Optional[Sex]           = None
    height_cm:      Optional[float]         = None
    weight_kg:      Optional[float]         = None
    activity_level: Optional[ActivityLevel] = None
    fitness_goal:   Optional[FitnessGoal]   = None
    diet_pref:      Optional[DietPref]      = None
    allergies:      Optional[list[str]]     = None
    experience:     Optional[Experience]    = None


class ProfileOut(ProfileCreate):
    """Full profile as returned by GET /profile."""
    id:         UUID
    created_at: datetime
    updated_at: datetime


# ══════════════════════════════════════════════════════════════════════════════
# SESSION
# ══════════════════════════════════════════════════════════════════════════════

class SessionCreate(BaseModel):
    """
    Payload for POST /sessions — sent after both front and side captures
    have been confirmed stable and the pseudo-3D computation is done.
    """
    # Front-view cm (per side)
    arm_left_cm:    Optional[float] = None
    arm_right_cm:   Optional[float] = None
    shoulder_cm:    Optional[float] = None
    chest_cm:       Optional[float] = None
    waist_cm:       Optional[float] = None
    hip_cm:         Optional[float] = None
    thigh_left_cm:  Optional[float] = None
    thigh_right_cm: Optional[float] = None

    # Side-view cm (per side)
    arm_side_left_cm:    Optional[float] = None
    arm_side_right_cm:   Optional[float] = None
    thigh_side_left_cm:  Optional[float] = None
    thigh_side_right_cm: Optional[float] = None
    chest_side_left_cm:   Optional[float] = None
    chest_side_right_cm:  Optional[float] = None
    waist_side_left_cm:   Optional[float] = None
    waist_side_right_cm:  Optional[float] = None
    hip_side_left_cm:     Optional[float] = None
    hip_side_right_cm:    Optional[float] = None

    # Derived pseudo-3D (computed by /measure/combine before this call)
    arm_left_girth_cm:    Optional[float] = None
    arm_right_girth_cm:   Optional[float] = None
    thigh_left_girth_cm:  Optional[float] = None
    thigh_right_girth_cm: Optional[float] = None
    chest_girth_cm:       Optional[float] = None
    waist_girth_cm:       Optional[float] = None
    hip_girth_cm:         Optional[float] = None

    arm_left_area_cm2:    Optional[float] = None
    arm_right_area_cm2:   Optional[float] = None
    thigh_left_area_cm2:  Optional[float] = None
    thigh_right_area_cm2: Optional[float] = None
    chest_area_cm2:       Optional[float] = None
    waist_area_cm2:       Optional[float] = None
    hip_area_cm2:         Optional[float] = None

    arm_asymmetry_pct:    Optional[float] = None
    thigh_asymmetry_pct:  Optional[float] = None

    # Metadata
    notes:               Optional[str]   = None
    photo_url:           Optional[str]   = None
    capture_confidence:  Optional[float] = None
    frames_averaged:     Optional[int]   = None


class SessionOut(SessionCreate):
    """Full session row as returned by GET /sessions or GET /sessions/{id}."""
    id:          UUID
    user_id:     UUID
    captured_at: datetime

    class Config:
        from_attributes = True


class SessionListItem(BaseModel):
    """Lightweight session summary for the history list."""
    id:                  UUID
    captured_at:         datetime
    arm_left_girth_cm:   Optional[float] = None
    arm_right_girth_cm:  Optional[float] = None
    thigh_left_girth_cm: Optional[float] = None
    shoulder_cm:         Optional[float] = None
    chest_girth_cm:      Optional[float] = None
    waist_girth_cm:      Optional[float] = None
    hip_girth_cm:        Optional[float] = None
    arm_asymmetry_pct:   Optional[float] = None
    notes:               Optional[str]   = None
    photo_url:           Optional[str]   = None
