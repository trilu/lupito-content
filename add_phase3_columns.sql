-- Add missing columns for Phase 3 breed standards import
-- These columns will store detailed physical and descriptive data about breeds

ALTER TABLE breeds_comprehensive_content
ADD COLUMN IF NOT EXISTS height_min_cm INTEGER,
ADD COLUMN IF NOT EXISTS height_max_cm INTEGER,
ADD COLUMN IF NOT EXISTS weight_min_kg NUMERIC(5,2),
ADD COLUMN IF NOT EXISTS weight_max_kg NUMERIC(5,2),
ADD COLUMN IF NOT EXISTS lifespan_min_years INTEGER,
ADD COLUMN IF NOT EXISTS lifespan_max_years INTEGER,
ADD COLUMN IF NOT EXISTS lifespan_avg_years NUMERIC(3,1),
ADD COLUMN IF NOT EXISTS personality_traits TEXT,
ADD COLUMN IF NOT EXISTS exercise_needs_detail TEXT,
ADD COLUMN IF NOT EXISTS training_tips TEXT,
ADD COLUMN IF NOT EXISTS fun_facts TEXT,
ADD COLUMN IF NOT EXISTS coat_length TEXT,
ADD COLUMN IF NOT EXISTS coat_texture TEXT,
ADD COLUMN IF NOT EXISTS energy_level_numeric INTEGER CHECK (energy_level_numeric BETWEEN 1 AND 5),
ADD COLUMN IF NOT EXISTS barking_tendency TEXT,
ADD COLUMN IF NOT EXISTS drooling_tendency TEXT,
ADD COLUMN IF NOT EXISTS ideal_owner TEXT,
ADD COLUMN IF NOT EXISTS living_conditions TEXT,
ADD COLUMN IF NOT EXISTS weather_tolerance TEXT,
ADD COLUMN IF NOT EXISTS common_nicknames TEXT,
ADD COLUMN IF NOT EXISTS breed_recognition TEXT;

-- Add indexes for better query performance on commonly filtered columns
CREATE INDEX IF NOT EXISTS idx_breeds_height ON breeds_comprehensive_content(height_min_cm, height_max_cm);
CREATE INDEX IF NOT EXISTS idx_breeds_weight ON breeds_comprehensive_content(weight_min_kg, weight_max_kg);
CREATE INDEX IF NOT EXISTS idx_breeds_lifespan ON breeds_comprehensive_content(lifespan_min_years, lifespan_max_years);
CREATE INDEX IF NOT EXISTS idx_breeds_energy ON breeds_comprehensive_content(energy_level_numeric);