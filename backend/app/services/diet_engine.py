"""
services/diet_engine.py
-----------------------
Personalized diet recommendation engine.

Formulae used
-------------
BMR  — Mifflin-St Jeor (1990), most accurate for general population.
TDEE — Harris-Benedict activity multipliers.
Goal — calorie offset aligned with evidence-based hypertrophy / fat-loss rates:
         muscle_gain : +250 kcal (lean bulk — minimises fat gain)
         fat_loss    : −500 kcal (≈ 0.45 kg/week loss)
         recomp      :   0 kcal  (maintenance with high protein)
         maintenance :   0 kcal

Macros
------
Protein targets from International Society of Sports Nutrition (2017):
  muscle_gain : 2.2 g / kg bodyweight
  fat_loss    : 2.0 g / kg (preserve muscle on deficit)
  recomp      : 2.0 g / kg
  maintenance : 1.6 g / kg
Fat : 0.8 g / kg (floor for hormonal health)
Carbohydrate: remainder of calories after protein and fat are accounted for.

References
----------
Mifflin, M. D. et al. (1990). A new predictive equation for resting energy
  expenditure in healthy individuals. American Journal of Clinical Nutrition.
Morton, R. W. et al. (2018). A systematic review, meta-analysis and
  meta-regression of the effect of protein supplementation on resistance
  training-induced gains in muscle mass and strength. British Journal of
  Sports Medicine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ── Activity multipliers (TDEE = BMR × multiplier) ───────────────────────────

ACTIVITY_MULTIPLIERS: dict[str, float] = {
    "sedentary":  1.2,   # desk job, no exercise
    "light":      1.375, # 1-3 days/week light exercise
    "moderate":   1.55,  # 3-5 days/week moderate exercise
    "active":     1.725, # 6-7 days/week hard exercise
    "very_active":1.9,   # physical job + daily training
}

# ── Goal calorie offsets (kcal/day) ──────────────────────────────────────────

GOAL_OFFSETS: dict[str, int] = {
    "muscle_gain": +250,
    "fat_loss":    -500,
    "recomp":        0,
    "maintenance":   0,
    
    # New enums
    "lose_fat":      -500,
    "maintain":         0,
    "lean_bulk":     +250,
    "build_muscle":  +350,
    "recomposition":    0,
}

# ── Protein targets (g / kg bodyweight) ──────────────────────────────────────

PROTEIN_G_PER_KG: dict[str, float] = {
    "muscle_gain": 2.2,
    "fat_loss":    2.0,
    "recomp":      2.0,
    "maintenance": 1.6,
    
    # New enums
    "lose_fat":      2.0,
    "maintain":      1.6,
    "lean_bulk":     2.2,
    "build_muscle":  2.2,
    "recomposition": 2.0,
}

FAT_G_PER_KG: float = 0.8  # minimum regardless of goal


@dataclass
class DietPlan:
    bmr:            float
    tdee:           float
    calorie_target: float
    protein_g:      float
    fat_g:          float
    carbs_g:        float
    water_ml:       float
    meals:          list[dict] = field(default_factory=list)


# ── Core calculations ─────────────────────────────────────────────────────────

def mifflin_bmr(weight_kg: float, height_cm: float, age: int, sex: str) -> float:
    """Mifflin-St Jeor BMR in kcal/day."""
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + 5 if sex == "male" else base - 161


def calculate_tdee(bmr: float, activity_level: str) -> float:
    multiplier = ACTIVITY_MULTIPLIERS.get(activity_level, 1.2)
    return bmr * multiplier


def calculate_macros(
    calorie_target: float,
    weight_kg: float,
    fitness_goal: str,
) -> tuple[float, float, float]:
    """Return (protein_g, fat_g, carbs_g)."""
    protein_g = PROTEIN_G_PER_KG.get(fitness_goal, 1.6) * weight_kg
    fat_g     = FAT_G_PER_KG * weight_kg

    # Remaining calories go to carbohydrates
    cals_from_protein = protein_g * 4
    cals_from_fat     = fat_g * 9
    remaining         = calorie_target - cals_from_protein - cals_from_fat
    carbs_g           = max(remaining / 4, 0)   # never negative

    return round(protein_g, 1), round(fat_g, 1), round(carbs_g, 1)


def hydration_ml(weight_kg: float, activity_level: str) -> float:
    """
    Baseline: 35 ml / kg. Add 500 ml for active levels.
    Rounded to nearest 50 ml for practicality.
    """
    base = 35 * weight_kg
    bonus = 500 if activity_level in ("active", "very_active") else 0
    total = base + bonus
    return round(total / 50) * 50


def compute_diet_plan(profile: dict) -> DietPlan:
    """
    Build a complete DietPlan from a profile dict.
    Profile keys: weight_kg, height_cm, age, sex, activity_level,
                  fitness_goal, diet_pref, allergies.
    """
    weight_kg      = profile["weight_kg"]
    height_cm      = profile["height_cm"]
    age            = profile["age"]
    sex            = profile["sex"]
    activity_level = profile["activity_level"]
    fitness_goal   = profile["fitness_goal"]
    diet_pref      = profile.get("diet_pref", "omnivore")
    allergies      = profile.get("allergies", [])

    bmr  = mifflin_bmr(weight_kg, height_cm, age, sex)
    tdee = calculate_tdee(bmr, activity_level)
    cal_target = tdee + GOAL_OFFSETS.get(fitness_goal, 0)
    protein_g, fat_g, carbs_g = calculate_macros(cal_target, weight_kg, fitness_goal)
    water_ml = hydration_ml(weight_kg, activity_level)
    meals = generate_meal_suggestions(
        protein_g=protein_g,
        carbs_g=carbs_g,
        fat_g=fat_g,
        diet_pref=diet_pref,
        allergies=allergies,
        fitness_goal=fitness_goal,
    )

    return DietPlan(
        bmr=round(bmr, 1),
        tdee=round(tdee, 1),
        calorie_target=round(cal_target, 1),
        protein_g=protein_g,
        fat_g=fat_g,
        carbs_g=carbs_g,
        water_ml=water_ml,
        meals=meals,
    )


# ── Meal suggestions ──────────────────────────────────────────────────────────

def generate_meal_suggestions(
    protein_g: float,
    carbs_g: float,
    fat_g: float,
    diet_pref: str,
    allergies: list[str],
    fitness_goal: str,
) -> list[dict]:
    """
    Generate 5 daily meal templates distributed across breakfast, mid-morning
    snack, lunch, afternoon snack, and dinner.

    Macros are split roughly as:
        Breakfast   : 25 %
        Mid-morning : 10 %
        Lunch       : 30 %
        Snack       : 10 %
        Dinner      : 25 %

    Food choices are filtered by diet_pref and allergies.
    This is a rule-based generator — a future phase can replace it with
    an LLM call to /api/diet/ai-suggest.
    """
    splits = [0.25, 0.10, 0.30, 0.10, 0.25]
    names  = ["Breakfast", "Mid-morning snack", "Lunch", "Afternoon snack", "Dinner"]

    has_gluten  = "gluten"  not in [a.lower() for a in allergies]
    has_dairy   = "dairy"   not in [a.lower() for a in allergies]
    is_vegan    = diet_pref == "vegan"
    is_veg      = diet_pref in ("vegetarian", "vegan", "veg")
    is_egg      = diet_pref == "eggetarian"
    is_pesca    = diet_pref == "pescatarian"

    # Protein food pool
    protein_foods: list[str]
    if is_vegan:
        protein_foods = ["tofu", "tempeh", "edamame", "chickpeas", "lentils", "hemp seeds"]
    elif is_veg:
        protein_foods = ["eggs", "paneer", "Greek yoghurt", "tofu", "cottage cheese"] if has_dairy else ["tofu", "tempeh", "lentils"]
    elif is_egg:
        protein_foods = ["eggs", "Greek yoghurt", "cottage cheese", "tofu", "tempeh"] if has_dairy else ["eggs", "tofu", "tempeh"]
    elif is_pesca:
        protein_foods = ["salmon", "tuna", "eggs", "Greek yoghurt", "tofu"] if has_dairy else ["salmon", "tuna", "eggs", "tofu"]
    else:
        protein_foods = ["chicken breast", "eggs", "tuna", "salmon", "turkey", "whey protein"] if has_dairy else ["chicken breast", "tuna", "salmon", "turkey", "eggs"]

    carb_foods   = ["oats", "brown rice", "sweet potato", "quinoa"] if has_gluten else ["rice", "sweet potato", "quinoa"]
    fat_foods    = ["almonds", "avocado", "olive oil", "walnuts"]
    veggie_foods = ["spinach", "broccoli", "mixed salad", "cucumber", "tomatoes"]

    meals = []
    for i, (split, name) in enumerate(zip(splits, names)):
        p = round(protein_g * split, 1)
        c = round(carbs_g   * split, 1)
        f = round(fat_g     * split, 1)
        kcal = round(p * 4 + c * 4 + f * 9, 0)

        # Select foods cyclically so meals feel varied
        pf = protein_foods[i % len(protein_foods)]
        cf = carb_foods[i % len(carb_foods)]
        ff = fat_foods[i % len(fat_foods)]
        vf = veggie_foods[i % len(veggie_foods)]

        meals.append({
            "name":       name,
            "protein_g":  p,
            "carbs_g":    c,
            "fat_g":      f,
            "calories":   kcal,
            "foods":      [pf, cf, ff, vf],
        })

    return meals
