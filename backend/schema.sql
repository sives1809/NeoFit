-- ─────────────────────────────────────────────────────────────────────────────
-- HyperVissipon Supabase Schema Migration SQL
-- ─────────────────────────────────────────────────────────────────────────────
-- Run this script in the Supabase SQL Editor (found in your Supabase Dashboard)
-- to create the required tables for user profiles, measurement sessions, and diet plans.
-- ─────────────────────────────────────────────────────────────────────────────

-- 1. Create Profiles table
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name TEXT NOT NULL,
    age INTEGER NOT NULL,
    sex TEXT NOT NULL CHECK (sex IN ('male', 'female', 'other')),
    height_cm DOUBLE PRECISION NOT NULL,
    weight_kg DOUBLE PRECISION NOT NULL,
    activity_level TEXT NOT NULL CHECK (activity_level IN ('sedentary', 'light', 'moderate', 'active', 'very_active')),
    fitness_goal TEXT NOT NULL CHECK (fitness_goal IN ('muscle_gain', 'fat_loss', 'recomp', 'maintenance')),
    diet_pref TEXT NOT NULL DEFAULT 'omnivore' CHECK (diet_pref IN ('omnivore', 'vegetarian', 'vegan', 'keto', 'paleo')),
    allergies TEXT[] DEFAULT '{}',
    experience TEXT NOT NULL DEFAULT 'beginner' CHECK (experience IN ('beginner', 'intermediate', 'advanced')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Enable RLS for profiles table
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- Create policies for profiles table
CREATE POLICY "Users can view their own profile" 
    ON public.profiles FOR SELECT 
    USING (auth.uid() = id);

CREATE POLICY "Users can create their own profile" 
    ON public.profiles FOR INSERT 
    WITH CHECK (auth.uid() = id);

CREATE POLICY "Users can update their own profile" 
    ON public.profiles FOR UPDATE 
    USING (auth.uid() = id);

-- 2. Create Sessions table
CREATE TABLE IF NOT EXISTS public.sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    captured_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    
    -- Front-view measurements (in cm)
    arm_left_cm DOUBLE PRECISION,
    arm_right_cm DOUBLE PRECISION,
    shoulder_cm DOUBLE PRECISION,
    chest_cm DOUBLE PRECISION,
    waist_cm DOUBLE PRECISION,
    hip_cm DOUBLE PRECISION,
    thigh_left_cm DOUBLE PRECISION,
    thigh_right_cm DOUBLE PRECISION,

    -- Side-view measurements (in cm)
    arm_side_left_cm DOUBLE PRECISION,
    arm_side_right_cm DOUBLE PRECISION,
    thigh_side_left_cm DOUBLE PRECISION,
    thigh_side_right_cm DOUBLE PRECISION,
    chest_side_left_cm DOUBLE PRECISION,
    chest_side_right_cm DOUBLE PRECISION,
    waist_side_left_cm DOUBLE PRECISION,
    waist_side_right_cm DOUBLE PRECISION,
    hip_side_left_cm DOUBLE PRECISION,
    hip_side_right_cm DOUBLE PRECISION,

    -- Derived pseudo-3D girths & areas (computed by measurement engine)
    arm_left_girth_cm DOUBLE PRECISION,
    arm_right_girth_cm DOUBLE PRECISION,
    thigh_left_girth_cm DOUBLE PRECISION,
    thigh_right_girth_cm DOUBLE PRECISION,
    chest_girth_cm DOUBLE PRECISION,
    waist_girth_cm DOUBLE PRECISION,
    hip_girth_cm DOUBLE PRECISION,
    arm_left_area_cm2 DOUBLE PRECISION,
    arm_right_area_cm2 DOUBLE PRECISION,
    thigh_left_area_cm2 DOUBLE PRECISION,
    thigh_right_area_cm2 DOUBLE PRECISION,
    chest_area_cm2 DOUBLE PRECISION,
    waist_area_cm2 DOUBLE PRECISION,
    hip_area_cm2 DOUBLE PRECISION,
    arm_asymmetry_pct DOUBLE PRECISION,
    thigh_asymmetry_pct DOUBLE PRECISION,

    -- Metadata & audit logs
    notes TEXT,
    photo_url TEXT,
    capture_confidence DOUBLE PRECISION,
    frames_averaged INTEGER
);

-- Enable RLS for sessions table
ALTER TABLE public.sessions ENABLE ROW LEVEL SECURITY;

-- Create policies for sessions table
CREATE POLICY "Users can view their own sessions" 
    ON public.sessions FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own sessions" 
    ON public.sessions FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own sessions" 
    ON public.sessions FOR DELETE 
    USING (auth.uid() = user_id);

-- 3. Create Diet Plans table
CREATE TABLE IF NOT EXISTS public.diet_plans (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    bmr DOUBLE PRECISION NOT NULL,
    tdee DOUBLE PRECISION NOT NULL,
    cal_target DOUBLE PRECISION NOT NULL,
    protein_g DOUBLE PRECISION NOT NULL,
    carbs_g DOUBLE PRECISION NOT NULL,
    fat_g DOUBLE PRECISION NOT NULL,
    water_ml DOUBLE PRECISION NOT NULL,
    meals JSONB NOT NULL DEFAULT '[]'::jsonb,
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Enable RLS for diet_plans table
ALTER TABLE public.diet_plans ENABLE ROW LEVEL SECURITY;

-- Create policies for diet_plans table
CREATE POLICY "Users can view their own diet plan" 
    ON public.diet_plans FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own diet plan" 
    ON public.diet_plans FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own diet plan" 
    ON public.diet_plans FOR UPDATE 
    USING (auth.uid() = user_id);

-- 4. Create updated_at trigger helper function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to automatically keep updated_at current
DROP TRIGGER IF EXISTS update_profiles_updated_at ON public.profiles;
CREATE TRIGGER update_profiles_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
