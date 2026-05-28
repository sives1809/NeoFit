import uuid
import math
import random
import json
from datetime import datetime, timedelta

USER_ID = "1eed0d2f-895b-4f9a-856a-9e059809eb6c"
random.seed(42)

START_DATE = datetime(2026, 2, 20, 8, 0, 0)

def area_from_girth(g):
    r = g / (2 * math.pi)
    return math.pi * r * r

base = {
    "waist": 96.0,
    "chest": 104.0,
    "shoulder": 118.0,
    "arm_l": 37.0,
    "arm_r": 37.8,
    "hip": 101.0,
    "thigh_l": 58.0,
    "thigh_r": 58.8
}

meals = [
    {
        "meal": "Breakfast",
        "items": ["Oats", "Eggs", "Banana"],
        "calories": 550
    },
    {
        "meal": "Lunch",
        "items": ["Rice", "Chicken Breast", "Vegetables"],
        "calories": 750
    },
    {
        "meal": "Snack",
        "items": ["Greek Yogurt", "Almonds"],
        "calories": 300
    },
    {
        "meal": "Dinner",
        "items": ["Chapati", "Paneer", "Salad"],
        "calories": 650
    }
]

sql = []

sql.append("-- NeoFit Synthetic Seed Data")
sql.append(f"DELETE FROM public.sessions WHERE user_id = '{USER_ID}';")
sql.append(f"DELETE FROM public.diet_plans WHERE user_id = '{USER_ID}';")
sql.append(f"DELETE FROM public.profiles WHERE id = '{USER_ID}';")

sql.append(f"""
INSERT INTO public.profiles
(id, full_name, age, sex, height_cm, weight_kg, activity_level, fitness_goal, diet_pref, allergies, experience)
VALUES
('{USER_ID}', 'Sives Sundar', 21, 'male', 170, 83, 'active', 'recomp', 'omnivore', '{{}}', 'intermediate');
""")

sql.append(f"""
INSERT INTO public.diet_plans
(user_id, bmr, tdee, cal_target, protein_g, carbs_g, fat_g, water_ml, meals)
VALUES
(
    '{USER_ID}',
    1765,
    2735,
    2350,
    180,
    220,
    75,
    3500,
    '{json.dumps(meals)}'::jsonb
);
""")

for i in range(90):
    progress = i / 89

    waist = base["waist"] - 10 * progress + random.uniform(-0.6, 0.6)
    chest = base["chest"] + 2.2 * progress + random.uniform(-0.5, 0.5)
    shoulder = base["shoulder"] + 1.5 * progress + random.uniform(-0.7, 0.7)
    arm_l = base["arm_l"] + 1.1 * progress + random.uniform(-0.25, 0.25)
    arm_r = base["arm_r"] + 0.8 * progress + random.uniform(-0.25, 0.25)
    hip = base["hip"] - 6 * progress + random.uniform(-0.6, 0.6)
    thigh_l = base["thigh_l"] + 0.8 * progress + random.uniform(-0.4, 0.4)
    thigh_r = base["thigh_r"] + 0.5 * progress + random.uniform(-0.4, 0.4)

    captured = START_DATE + timedelta(
        days=i,
        hours=random.randint(0, 3),
        minutes=random.randint(0, 59)
    )

    arm_left_girth = arm_l * 1.08
    arm_right_girth = arm_r * 1.08
    thigh_left_girth = thigh_l * 1.10
    thigh_right_girth = thigh_r * 1.10
    chest_girth = chest * 1.06
    waist_girth = waist * 1.05
    hip_girth = hip * 1.05

    arm_asym = abs(arm_r - arm_l) / ((arm_r + arm_l) / 2) * 100
    thigh_asym = abs(thigh_r - thigh_l) / ((thigh_r + thigh_l) / 2) * 100

    sql.append(f"""
INSERT INTO public.sessions (
    id,
    user_id,
    captured_at,
    arm_left_cm,
    arm_right_cm,
    shoulder_cm,
    chest_cm,
    waist_cm,
    hip_cm,
    thigh_left_cm,
    thigh_right_cm,
    arm_side_left_cm,
    arm_side_right_cm,
    thigh_side_left_cm,
    thigh_side_right_cm,
    chest_side_left_cm,
    chest_side_right_cm,
    waist_side_left_cm,
    waist_side_right_cm,
    hip_side_left_cm,
    hip_side_right_cm,
    arm_left_girth_cm,
    arm_right_girth_cm,
    thigh_left_girth_cm,
    thigh_right_girth_cm,
    chest_girth_cm,
    waist_girth_cm,
    hip_girth_cm,
    arm_left_area_cm2,
    arm_right_area_cm2,
    thigh_left_area_cm2,
    thigh_right_area_cm2,
    chest_area_cm2,
    waist_area_cm2,
    hip_area_cm2,
    arm_asymmetry_pct,
    thigh_asymmetry_pct,
    notes,
    photo_url,
    capture_confidence,
    frames_averaged
)
VALUES (
    '{uuid.uuid4()}',
    '{USER_ID}',
    '{captured.isoformat()}+00',
    {arm_l:.2f},
    {arm_r:.2f},
    {shoulder:.2f},
    {chest:.2f},
    {waist:.2f},
    {hip:.2f},
    {thigh_l:.2f},
    {thigh_r:.2f},
    {arm_l * 0.52:.2f},
    {arm_r * 0.52:.2f},
    {thigh_l * 0.56:.2f},
    {thigh_r * 0.56:.2f},
    {chest * 0.51:.2f},
    {chest * 0.50:.2f},
    {waist * 0.49:.2f},
    {waist * 0.50:.2f},
    {hip * 0.50:.2f},
    {hip * 0.49:.2f},
    {arm_left_girth:.2f},
    {arm_right_girth:.2f},
    {thigh_left_girth:.2f},
    {thigh_right_girth:.2f},
    {chest_girth:.2f},
    {waist_girth:.2f},
    {hip_girth:.2f},
    {area_from_girth(arm_left_girth):.2f},
    {area_from_girth(arm_right_girth):.2f},
    {area_from_girth(thigh_left_girth):.2f},
    {area_from_girth(thigh_right_girth):.2f},
    {area_from_girth(chest_girth):.2f},
    {area_from_girth(waist_girth):.2f},
    {area_from_girth(hip_girth):.2f},
    {arm_asym:.2f},
    {thigh_asym:.2f},
    'Synthetic NeoFit recomp progress',
    'https://placehold.co/600x800',
    {random.uniform(0.82, 0.98):.3f},
    {random.randint(8, 20)}
);
""")

with open("neofit_seed.sql", "w", encoding="utf-8") as f:
    f.write("\n".join(sql))

print("DONE -> neofit_seed.sql created")