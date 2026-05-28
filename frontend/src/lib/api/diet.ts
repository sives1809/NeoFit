import { apiFetch } from "./client";

export type DietPlan = {
  calories?: number;
  protein_g?: number;
  carbs_g?: number;
  fats_g?: number;
  meals?: Array<{ name: string; items: string[]; calories?: number }>;
  [k: string]: unknown;
};

export const dietApi = {
  get: async () => {
    const raw = await apiFetch<any>("/diet");
    return mapDietPlan(raw);
  },
  refresh: async () => {
    const raw = await apiFetch<any>("/diet/refresh", { method: "POST" });
    return mapDietPlan(raw);
  },
};

function mapDietPlan(raw: any): DietPlan {
  if (!raw || typeof raw !== "object") return {};
  const meals = Array.isArray(raw.meals)
    ? raw.meals.map((m: any) => ({
        name: m.name ?? "",
        calories: m.calories ?? m.kcal,
        items: m.items ?? m.foods ?? [],
      }))
    : [];
  return {
    ...raw,
    calories: raw.cal_target ?? raw.calories,
    fats_g: raw.fat_g ?? raw.fats_g,
    meals,
  };
}

