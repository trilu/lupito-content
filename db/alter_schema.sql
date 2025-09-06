-- Add raw_type field to food_raw table to track API vs HTML source
-- Run this in Supabase SQL editor after the initial schema

ALTER TABLE food_raw 
ADD COLUMN IF NOT EXISTS raw_type TEXT DEFAULT 'html';

-- Add index for filtering by raw type
CREATE INDEX IF NOT EXISTS idx_food_raw_type ON food_raw(raw_type);

-- Update existing rows to set raw_type based on file extension in path
UPDATE food_raw 
SET raw_type = CASE 
    WHEN html_gcs_path LIKE '%.json' THEN 'api'
    ELSE 'html'
END
WHERE raw_type IS NULL;