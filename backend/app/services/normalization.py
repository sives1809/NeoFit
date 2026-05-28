from typing import Optional

def normalize_goal(goal: Optional[str]) -> str:
    if not goal:
        return "maintain"
    g = goal.lower().strip()
    mapping = {
        "lose": "lose_fat",
        "fat_loss": "lose_fat",
        "lose_fat": "lose_fat",
        "gain": "build_muscle",
        "muscle_gain": "build_muscle",
        "build_muscle": "build_muscle",
        "lean_bulk": "lean_bulk",
        "recomp": "recomposition",
        "recomposition": "recomposition",
        "maintenance": "maintain",
        "maintain": "maintain",
    }
    return mapping.get(g, "maintain")

def normalize_diet(diet: Optional[str]) -> str:
    if not diet:
        return "non_vegetarian"
    d = diet.lower().strip()
    mapping = {
        "veg": "vegetarian",
        "vegetarian": "vegetarian",
        "vegan": "vegan",
        "non-veg": "non_vegetarian",
        "non_vegetarian": "non_vegetarian",
        "omnivore": "non_vegetarian",
        "eggetarian": "eggetarian",
        "pescatarian": "pescatarian",
    }
    return mapping.get(d, "non_vegetarian")

def normalize_sex(sex: Optional[str]) -> str:
    if not sex:
        return "other"
    s = sex.lower().strip()
    mapping = {
        "male": "male",
        "female": "female",
        "other": "other",
        "prefer_not_to_say": "prefer_not_to_say",
        "prefer-not-to-say": "prefer_not_to_say",
    }
    return mapping.get(s, "other")


def map_to_db_profile(data: dict) -> dict:
    """
    Map application-level enums to database-compliant enums:
    - sex: 'male', 'female', 'other' (prefer_not_to_say -> other)
    - fitness_goal: 'muscle_gain', 'fat_loss', 'recomp', 'maintenance'
    - diet_pref: 'omnivore', 'vegetarian', 'vegan', 'keto', 'paleo'
    """
    mapped = data.copy()
    
    if "sex" in mapped and mapped["sex"] is not None:
        s = mapped["sex"].lower().strip()
        sex_map = {
            "male": "male",
            "female": "female",
            "other": "other",
            "prefer_not_to_say": "other",
        }
        mapped["sex"] = sex_map.get(s, "other")
        
    if "fitness_goal" in mapped and mapped["fitness_goal"] is not None:
        g = mapped["fitness_goal"].lower().strip()
        goal_map = {
            "lose_fat": "fat_loss",
            "maintain": "maintenance",
            "lean_bulk": "muscle_gain",
            "build_muscle": "muscle_gain",
            "recomposition": "recomp",
            "muscle_gain": "muscle_gain",
            "fat_loss": "fat_loss",
            "recomp": "recomp",
            "maintenance": "maintenance",
        }
        mapped["fitness_goal"] = goal_map.get(g, "maintenance")
        
    if "diet_pref" in mapped and mapped["diet_pref"] is not None:
        d = mapped["diet_pref"].lower().strip()
        diet_map = {
            "non_vegetarian": "omnivore",
            "vegetarian": "vegetarian",
            "vegan": "vegan",
            "eggetarian": "vegetarian",
            "pescatarian": "omnivore",
            "omnivore": "omnivore",
            "keto": "keto",
            "paleo": "paleo",
        }
        mapped["diet_pref"] = diet_map.get(d, "omnivore")
        
    return mapped


def check_session_physiological_validity(s: dict) -> tuple[bool, str]:
    """
    Check if a session's girths are physiologically possible.
    Returns (True, "") if valid, or (False, reason) if invalid.
    """
    chest = s.get("chest_girth_cm")
    waist = s.get("waist_girth_cm")
    hip = s.get("hip_girth_cm")
    arm_l = s.get("arm_left_girth_cm")
    arm_r = s.get("arm_right_girth_cm")
    thigh_l = s.get("thigh_left_girth_cm")
    thigh_r = s.get("thigh_right_girth_cm")

    print(f"[PHYSIOLOGICAL VALIDATION CHECK] chest={chest}, waist={waist}, hip={hip}, arm_l={arm_l}, arm_r={arm_r}, thigh_l={thigh_l}, thigh_r={thigh_r}")

    if chest is not None and chest > 180.0:
        return False, f"chest_girth_cm = {chest:.1f} cm (> 180 cm threshold)"
    if waist is not None and waist > 160.0:
        return False, f"waist_girth_cm = {waist:.1f} cm (> 160 cm threshold)"
    if hip is not None and hip > 180.0:
        return False, f"hip_girth_cm = {hip:.1f} cm (> 180 cm threshold)"

    if arm_l is not None and (arm_l < 15.0 or arm_l > 80.0):
        return False, f"left_arm_girth_cm = {arm_l:.1f} cm (outside 15.0 - 80.0 cm range)"
    if arm_r is not None and (arm_r < 15.0 or arm_r > 80.0):
        return False, f"right_arm_girth_cm = {arm_r:.1f} cm (outside 15.0 - 80.0 cm range)"

    if thigh_l is not None and (thigh_l < 30.0 or thigh_l > 100.0):
        return False, f"left_thigh_girth_cm = {thigh_l:.1f} cm (outside 30.0 - 100.0 cm range)"
    if thigh_r is not None and (thigh_r < 30.0 or thigh_r > 100.0):
        return False, f"right_thigh_girth_cm = {thigh_r:.1f} cm (outside 30.0 - 100.0 cm range)"

    return True, ""


def is_session_physiologically_valid(s: dict) -> bool:
    """
    Check if a session's girths are physiologically possible.
    Rejects obvious garbage.
    """
    valid, _ = check_session_physiological_validity(s)
    return valid


