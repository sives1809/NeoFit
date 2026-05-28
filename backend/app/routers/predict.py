from datetime import datetime
from fastapi import APIRouter, Query, HTTPException
from app.dependencies import CurrentUser, DB
from scipy.stats import linregress
import numpy as np
from typing import Optional
from app.services.normalization import normalize_goal, normalize_diet, normalize_sex, is_session_physiologically_valid

router = APIRouter(prefix="/predict", tags=["predict"])


def parse_date(date_str: str) -> datetime:
    """Safely parse timezone-aware datetime strings from database."""
    normalized = date_str.replace("Z", "+00:00")
    if " " in normalized and "T" not in normalized:
        normalized = normalized.replace(" ", "T")
    return datetime.fromisoformat(normalized)


@router.get("")
async def predict(
    user: CurrentUser,
    db: DB,
    days: int = Query(90, ge=7, le=365),
) -> dict:
    """
    Perform measurement prediction for up to 90 days out.
    Enforces prediction honesty rules based on valid session count.
    """
    # 1. Fetch and normalize user profile
    profile_res = db.table("profiles").select("*").eq("id", user["user_id"]).maybe_single().execute()
    profile = getattr(profile_res, "data", None) or {}
    
    gender = normalize_sex(profile.get("sex"))
    fitness_goal = normalize_goal(profile.get("fitness_goal"))
    height_cm = profile.get("height_cm") or 171.45
    weight_kg = profile.get("weight_kg") or 70.0

    # 2. Fetch all historical sessions ordered by captured_at ascending
    sessions_res = (
        db.table("sessions")
        .select("*")
        .eq("user_id", user["user_id"])
        .order("captured_at", desc=False)
        .execute()
    )
    sessions = sessions_res.data or []

    # 3. Clean and filter sessions using strict physiological bounds
    valid_sessions = [s for s in sessions if is_session_physiologically_valid(s)]

    # RULE 2: Prediction Honesty
    # < 5 valid sessions: return status "insufficient_data"
    if len(valid_sessions) < 5:
        return {
            "status": "insufficient_data",
            "message": "Need at least 5 valid sessions for progress forecasting."
        }

    # Prepare historical data for frontend plotting
    history_chart = []
    for s in valid_sessions:
        history_chart.append({
            "date": s.get("captured_at"),
            "chest": s.get("chest_girth_cm"),
            "waist": s.get("waist_girth_cm"),
            "hip": s.get("hip_girth_cm"),
            "arm_left": s.get("arm_left_girth_cm"),
            "arm_right": s.get("arm_right_girth_cm"),
            "thigh_left": s.get("thigh_left_girth_cm"),
            "thigh_right": s.get("thigh_right_girth_cm"),
            "weight": weight_kg
        })

    # Latest session details
    latest_s = valid_sessions[-1]
    latest_chest = latest_s.get("chest_girth_cm") or 90.0
    latest_waist = latest_s.get("waist_girth_cm") or 75.0
    latest_hip = latest_s.get("hip_girth_cm") or 90.0
    latest_arm_l = latest_s.get("arm_left_girth_cm") or 30.0
    latest_arm_r = latest_s.get("arm_right_girth_cm") or 30.0
    latest_thigh_l = latest_s.get("thigh_left_girth_cm") or 55.0
    latest_thigh_r = latest_s.get("thigh_right_girth_cm") or 55.0

    # 4. Estimate starting body fat percentage using waist/hip-to-height ratio
    if gender == "male":
        start_body_fat = 85.0 * (latest_waist / height_cm) - 24.0
        start_body_fat = max(5.0, min(45.0, start_body_fat))
    elif gender == "female":
        start_body_fat = 95.0 * ((latest_waist + latest_hip) / 2.0 / height_cm) - 30.0
        start_body_fat = max(10.0, min(50.0, start_body_fat))
    else:
        # Other/Prefer not to say: average
        start_body_fat = 90.0 * ((latest_waist + latest_hip / 2.0) / height_cm) - 27.0
        start_body_fat = max(7.0, min(47.0, start_body_fat))

    # Initialize weekly rates of change (default is flat/maintenance)
    rates = {
        "chest": 0.0, "waist": 0.0, "hip": 0.0,
        "arm_left": 0.0, "arm_right": 0.0,
        "thigh_left": 0.0, "thigh_right": 0.0,
        "weight": 0.0, "body_fat": 0.0
    }

    # Goal-aware rates of change per week
    if fitness_goal == "lose_fat":
        rates = {
            "chest": -0.15, "waist": -0.4, "hip": -0.3,
            "arm_left": -0.02, "arm_right": -0.02,
            "thigh_left": -0.05, "thigh_right": -0.05,
            "weight": -0.5, "body_fat": -0.35
        }
    elif fitness_goal == "lean_bulk":
        rates = {
            "chest": 0.1, "waist": 0.04, "hip": 0.04,
            "arm_left": 0.06, "arm_right": 0.06,
            "thigh_left": 0.08, "thigh_right": 0.08,
            "weight": 0.22, "body_fat": 0.04
        }
    elif fitness_goal == "build_muscle":
        rates = {
            "chest": 0.18, "waist": 0.08, "hip": 0.06,
            "arm_left": 0.10, "arm_right": 0.10,
            "thigh_left": 0.12, "thigh_right": 0.12,
            "weight": 0.4, "body_fat": 0.08
        }
    elif fitness_goal == "recomposition":
        rates = {
            "chest": 0.05, "waist": -0.15, "hip": -0.1,
            "arm_left": 0.03, "arm_right": 0.03,
            "thigh_left": 0.04, "thigh_right": 0.04,
            "weight": 0.0, "body_fat": -0.15
        }

    # Enforce forecasting honesty based on session count
    confidence = "Low"
    if 5 <= len(valid_sessions) < 10:
        # Simple trend forecast (linear regression only)
        confidence = "Low"
        # Compute slope for each key metric using linear regression
        metrics = ["chest", "waist", "hip", "arm_left", "arm_right", "thigh_left", "thigh_right"]
        for m in metrics:
            col = f"{m}_girth_cm"
            points = []
            for s in valid_sessions:
                val = s.get(col)
                cap = s.get("captured_at")
                if val is not None and cap:
                    try:
                        dt = parse_date(cap)
                        points.append((dt, val))
                    except Exception:
                        continue
            if len(points) >= 2:
                t0 = points[0][0]
                x = [(pt[0] - t0).total_seconds() / 86400.0 for pt in points]
                y = [pt[1] for pt in points]
                slope, intercept, r_value, p_value, std_err = linregress(x, y)
                # Convert daily slope to weekly slope
                rates[m] = float(slope) * 7.0
                # Clamp to prevent runaway slopes
                if m == "waist":
                    rates[m] = max(-0.8, min(0.4, rates[m]))
                elif m == "chest":
                    rates[m] = max(-0.5, min(0.5, rates[m]))
                else:
                    rates[m] = max(-0.4, min(0.4, rates[m]))
        # Simple regression weight
        rates["weight"] = -0.3 if fitness_goal == "lose_fat" else (0.2 if fitness_goal in ("lean_bulk", "build_muscle") else 0.0)
        rates["body_fat"] = -0.2 if fitness_goal == "lose_fat" else (0.05 if fitness_goal in ("lean_bulk", "build_muscle") else 0.0)

    else:
        # 10+ sessions: Goal-aware forecasting + confidence computation
        # Compute dynamic confidence based on variance of chest, waist, and hip
        waist_vals = [s.get("waist_girth_cm") for s in valid_sessions if s.get("waist_girth_cm") is not None]
        if len(waist_vals) >= 3:
            std_dev = np.std(waist_vals)
            if std_dev < 1.8:
                confidence = "High"
            else:
                confidence = "Medium"
        else:
            confidence = "Medium"

        # Blend goal-based rates with historical trends (50/50 blend)
        metrics = ["chest", "waist", "hip", "arm_left", "arm_right", "thigh_left", "thigh_right"]
        for m in metrics:
            col = f"{m}_girth_cm"
            points = []
            for s in valid_sessions:
                val = s.get(col)
                cap = s.get("captured_at")
                if val is not None and cap:
                    try:
                        dt = parse_date(cap)
                        points.append((dt, val))
                    except Exception:
                        continue
            if len(points) >= 2:
                t0 = points[0][0]
                x = [(pt[0] - t0).total_seconds() / 86400.0 for pt in points]
                y = [pt[1] for pt in points]
                slope, intercept, r_value, p_value, std_err = linregress(x, y)
                weekly_trend_rate = float(slope) * 7.0
                # Blend
                rates[m] = 0.5 * rates[m] + 0.5 * weekly_trend_rate
                # Clamp safely
                rates[m] = max(-0.8, min(0.6, rates[m]))

    # Ensure physiological sanity and goal alignment
    if fitness_goal == "lose_fat":
        # Waist rate must be negative (between -0.6 and -0.05 cm/week)
        rates["waist"] = min(-0.05, max(-0.6, rates["waist"]))
        # Body fat rate must be negative (between -0.4 and -0.05 %/week)
        rates["body_fat"] = min(-0.05, max(-0.4, rates["body_fat"]))
        # Weight rate must be negative (between -0.8 and -0.1 kg/week)
        rates["weight"] = min(-0.1, max(-0.8, rates["weight"]))
        # Chest / hip should decrease/stay flat
        rates["chest"] = min(0.0, rates["chest"])
        rates["hip"] = min(0.0, rates["hip"])

    # Compute body composition insights at week 16
    weight_diff = rates["weight"] * 16.0
    fat_diff_pct = rates["body_fat"] * 16.0
    
    latest_fat_mass = weight_kg * (start_body_fat / 100.0)
    projected_weight = max(30.0, weight_kg + weight_diff)
    projected_bf = max(3.0, min(50.0, start_body_fat + fat_diff_pct))
    projected_fat_mass = projected_weight * (projected_bf / 100.0)
    
    fat_change_kg = projected_fat_mass - latest_fat_mass
    muscle_change_kg = weight_diff - fat_change_kg

    # Safeguard against absurd muscle loss
    if fitness_goal == "lose_fat" and weight_diff < 0:
        min_muscle_change = 0.35 * weight_diff
        if muscle_change_kg < min_muscle_change:
            muscle_change_kg = min_muscle_change
            fat_change_kg = weight_diff - muscle_change_kg
            projected_fat_mass = latest_fat_mass + fat_change_kg
            projected_bf = max(3.0, (projected_fat_mass / projected_weight) * 100.0)
            rates["body_fat"] = (projected_bf - start_body_fat) / 16.0

    # Ensure no runaway rates (clamp rates to reasonable bounds for all goals)
    for k in rates:
        if k == "waist":
            rates[k] = max(-0.8, min(0.4, rates[k]))
        elif k == "chest" or k == "hip":
            rates[k] = max(-0.6, min(0.6, rates[k]))
        elif k in ("arm_left", "arm_right"):
            rates[k] = max(-0.3, min(0.3, rates[k]))
        elif k in ("thigh_left", "thigh_right"):
            rates[k] = max(-0.4, min(0.4, rates[k]))

    # Generate 16-week projection series
    prediction_chart = []
    weeks = [0, 2, 4, 8, 12, 16]
    for w in weeks:
        chest_val = max(50.0, min(180.0, latest_chest + rates["chest"] * w))
        waist_val = max(40.0, min(160.0, latest_waist + rates["waist"] * w))
        hip_val = max(50.0, min(180.0, latest_hip + rates["hip"] * w))
        arm_l_val = max(15.0, min(80.0, latest_arm_l + rates["arm_left"] * w))
        arm_r_val = max(15.0, min(80.0, latest_arm_r + rates["arm_right"] * w))
        thigh_l_val = max(30.0, min(100.0, latest_thigh_l + rates["thigh_left"] * w))
        thigh_r_val = max(30.0, min(100.0, latest_thigh_r + rates["thigh_right"] * w))
        weight_val = max(30.0, min(300.0, weight_kg + rates["weight"] * w))
        body_fat_val = max(3.0, min(50.0, start_body_fat + rates["body_fat"] * w))

        prediction_chart.append({
            "week": f"Week {w}",
            "chest": round(chest_val, 1),
            "waist": round(waist_val, 1),
            "hip": round(hip_val, 1),
            "arm_left": round(arm_l_val, 1),
            "arm_right": round(arm_r_val, 1),
            "thigh_left": round(thigh_l_val, 1),
            "thigh_right": round(thigh_r_val, 1),
            "weight": round(weight_val, 1),
            "body_fat": round(body_fat_val, 1)
        })

    # Symmetry description
    arm_asym = abs(latest_arm_l - latest_arm_r)
    if arm_asym < 0.5:
        symmetry_trend = "Excellent arm symmetry. Keep up balanced training."
    else:
        symmetry_trend = f"Minor arm asymmetry detected ({arm_asym:.1f} cm difference). Target non-dominant side."

    body_comp_insights = {
        "muscle_change_kg": round(muscle_change_kg, 1),
        "fat_change_kg": round(fat_change_kg, 1),
        "projected_waist_change_cm": round(rates["waist"] * 16.0, 1),
        "symmetry_trend": symmetry_trend
    }

    return {
        "status": "ok",
        "confidence": confidence,
        "history_chart": history_chart,
        "prediction_chart": prediction_chart,
        "body_comp_insights": body_comp_insights
    }
