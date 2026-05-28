import { apiFetch } from "./client";

export type Profile = {
  full_name?: string;
  age?: number;
  gender?: string;
  height_cm?: number;
  weight_kg?: number;
  activity_level?: string;
  goal?: string;
  dietary_pref?: string;
  [k: string]: unknown;
};

export const profileApi = {
  get: async () => {
    const raw = await apiFetch<any>("/profile");
    return toFrontend(raw);
  },
  create: async (p: Profile) => {
    const body = toBackend(p);
    const raw = await apiFetch<any>("/profile", { method: "POST", body });
    return toFrontend(raw);
  },
  update: async (p: Profile) => {
    const body = toBackendUpdate(p);
    const raw = await apiFetch<any>("/profile", { method: "PUT", body });
    return toFrontend(raw);
  },
};

function toBackend(p: Profile): any {
  let sex = "other";
  if (p.gender && ["male", "female", "other", "prefer_not_to_say"].includes(p.gender)) {
    sex = p.gender;
  }

  let fitness_goal = "maintain";
  if (p.goal) {
    const g = p.goal.toLowerCase();
    if (g === "lose" || g === "fat_loss" || g === "lose_fat") {
      fitness_goal = "lose_fat";
    } else if (g === "gain" || g === "muscle_gain" || g === "build_muscle") {
      fitness_goal = "build_muscle";
    } else if (g === "lean_bulk") {
      fitness_goal = "lean_bulk";
    } else if (g === "recomp" || g === "recomposition") {
      fitness_goal = "recomposition";
    } else if (g === "maintain" || g === "maintenance") {
      fitness_goal = "maintain";
    }
  }

  let diet_pref = "non_vegetarian";
  if (p.dietary_pref) {
    const d = p.dietary_pref.toLowerCase();
    if (d === "veg" || d === "vegetarian") {
      diet_pref = "vegetarian";
    } else if (d === "vegan") {
      diet_pref = "vegan";
    } else if (d === "non-veg" || d === "non_vegetarian" || d === "omnivore") {
      diet_pref = "non_vegetarian";
    } else if (d === "eggetarian") {
      diet_pref = "eggetarian";
    } else if (d === "pescatarian") {
      diet_pref = "pescatarian";
    }
  }

  let activity_level = "moderate";
  if (p.activity_level && ["sedentary", "light", "moderate", "active", "very_active"].includes(p.activity_level)) {
    activity_level = p.activity_level;
  }

  return {
    full_name: p.full_name ?? "User",
    age: p.age ?? 25,
    sex,
    height_cm: p.height_cm ?? 175,
    weight_kg: p.weight_kg ?? 70,
    activity_level,
    fitness_goal,
    diet_pref,
    allergies: [],
    experience: "beginner",
  };
}

function toBackendUpdate(p: Partial<Profile>): any {
  const out: any = {};
  if (p.full_name !== undefined) out.full_name = p.full_name;
  if (p.age !== undefined) out.age = p.age;
  
  if (p.gender !== undefined) {
    if (["male", "female", "other", "prefer_not_to_say"].includes(p.gender)) {
      out.sex = p.gender;
    } else {
      out.sex = "other";
    }
  }

  if (p.height_cm !== undefined) out.height_cm = p.height_cm;
  if (p.weight_kg !== undefined) out.weight_kg = p.weight_kg;

  if (p.activity_level !== undefined) {
    if (["sedentary", "light", "moderate", "active", "very_active"].includes(p.activity_level)) {
      out.activity_level = p.activity_level;
    } else {
      out.activity_level = "moderate";
    }
  }

  if (p.goal !== undefined) {
    const g = p.goal.toLowerCase();
    if (g === "lose" || g === "fat_loss" || g === "lose_fat") {
      out.fitness_goal = "lose_fat";
    } else if (g === "gain" || g === "muscle_gain" || g === "build_muscle") {
      out.fitness_goal = "build_muscle";
    } else if (g === "lean_bulk") {
      out.fitness_goal = "lean_bulk";
    } else if (g === "recomp" || g === "recomposition") {
      out.fitness_goal = "recomposition";
    } else {
      out.fitness_goal = "maintain";
    }
  }

  if (p.dietary_pref !== undefined) {
    const d = p.dietary_pref.toLowerCase();
    if (d === "veg" || d === "vegetarian") {
      out.diet_pref = "vegetarian";
    } else if (d === "vegan") {
      out.diet_pref = "vegan";
    } else if (d === "non-veg" || d === "non_vegetarian" || d === "omnivore") {
      out.diet_pref = "non_vegetarian";
    } else if (d === "eggetarian") {
      out.diet_pref = "eggetarian";
    } else if (d === "pescatarian") {
      out.diet_pref = "pescatarian";
    } else {
      out.diet_pref = "non_vegetarian";
    }
  }

  return out;
}

function toFrontend(b: any): Profile {
  if (!b) return {};
  
  // Directly map values from backend to frontend fields
  return {
    full_name: b.full_name,
    age: b.age,
    gender: b.sex,
    height_cm: b.height_cm,
    weight_kg: b.weight_kg,
    activity_level: b.activity_level,
    goal: b.fitness_goal,
    dietary_pref: b.diet_pref,
  };
}
