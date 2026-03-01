-- FocusFlow Supabase Schema (PostgreSQL)

-- 1. Enable UUID Extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Create Users/Profiles Table
-- Linked to Supabase Auth
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID REFERENCES auth.users ON DELETE CASCADE PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    role TEXT CHECK (role IN ('student', 'teacher', 'admin')) DEFAULT 'student',
    streak_count INTEGER DEFAULT 0,
    max_streak INTEGER DEFAULT 0,
    last_study_date DATE,
    title TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS (Row Level Security)
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- 3. Create Classrooms Table
CREATE TABLE IF NOT EXISTS public.classrooms (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name TEXT NOT NULL,
    code TEXT UNIQUE NOT NULL,
    teacher_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Classroom Students Junction
CREATE TABLE IF NOT EXISTS public.classroom_students (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    classroom_id UUID REFERENCES public.classrooms(id) ON DELETE CASCADE,
    student_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    role TEXT CHECK (role IN ('student', 'representative')) DEFAULT 'student',
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(classroom_id, student_id)
);

-- 5. Sessions Table
CREATE TABLE IF NOT EXISTS public.sessions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    classroom_id UUID REFERENCES public.classrooms(id) ON DELETE SET NULL,
    technique TEXT CHECK (technique IN ('pomodoro', '52-17', 'study-sprint', 'flowtime')) NOT NULL,
    study_mode TEXT CHECK (study_mode IN ('screen', 'book')) NOT NULL,
    camera_enabled BOOLEAN DEFAULT FALSE,
    duration INTEGER NOT NULL, -- Seconds
    distractions INTEGER DEFAULT 0,
    focus_score NUMERIC(5,2) DEFAULT 0.00,
    mouse_inactive_time INTEGER DEFAULT 0,
    keyboard_inactive_time INTEGER DEFAULT 0,
    tab_switches INTEGER DEFAULT 0,
    camera_absence_time INTEGER DEFAULT 0,
    dominant_emotion TEXT DEFAULT 'UNKNOWN',
    emotion_confidence NUMERIC(5,2) DEFAULT 0.00,
    user_state TEXT DEFAULT 'focused',
    recommended_technique TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Trigger: Auto-Calculate Focus Score (PostgreSQL Version)
CREATE OR REPLACE FUNCTION calculate_focus_score()
RETURNS TRIGGER AS $$
DECLARE
    idle_ratio NUMERIC;
    dist_penalty NUMERIC;
    cons_score NUMERIC;
    cam_score NUMERIC;
    total_idle INTEGER;
BEGIN
    total_idle := NEW.mouse_inactive_time + NEW.keyboard_inactive_time;
    idle_ratio := total_idle::NUMERIC / NULLIF(NEW.duration, 0);
    
    -- 40% Weight for Idle Ratio
    NEW.focus_score := (1 - COALESCE(idle_ratio, 0)) * 40;
    
    -- 30% Weight for Distractions
    dist_penalty := GREATEST(0, 30 - (NEW.distractions * 3));
    NEW.focus_score := NEW.focus_score + dist_penalty;
    
    -- 20% Consistency Score
    IF NEW.distractions = 0 THEN cons_score := 20;
    ELSE cons_score := GREATEST(0, 20 - (NEW.distractions * 2));
    END IF;
    NEW.focus_score := NEW.focus_score + cons_score;
    
    -- 10% Camera Score
    IF NEW.camera_enabled THEN 
        cam_score := (1 - (NEW.camera_absence_time::NUMERIC / NULLIF(NEW.duration, 0))) * 10;
    ELSE cam_score := 5; END IF;
    NEW.focus_score := NEW.focus_score + cam_score;
    
    -- Clip 0-100
    NEW.focus_score := GREATEST(0, LEAST(100, NEW.focus_score));
    
    -- Auto Recommend Tech
    IF NEW.distractions > 5 THEN NEW.recommended_technique := 'study-sprint';
    ELSIF NEW.focus_score >= 70 THEN NEW.recommended_technique := '52-17';
    ELSIF NEW.focus_score >= 50 THEN NEW.recommended_technique := 'pomodoro';
    ELSE NEW.recommended_technique := 'flowtime'; END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_calc_focus_score
BEFORE INSERT ON public.sessions
FOR EACH ROW EXECUTE FUNCTION calculate_focus_score();

-- 7. Sync Profile on Signup (Supabase Hook)
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, username, email, role)
  VALUES (new.id, new.raw_user_meta_data->>'username', new.email, COALESCE(new.raw_user_meta_data->>'role', 'student'));
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
