-- Migration to add comprehensive_content JSONB column to breeds_details table
-- This stores ALL extracted content from breed pages including quick facts,
-- exercise requirements, grooming, health, training, history, etc.

-- Add comprehensive_content column to breeds_details table
ALTER TABLE breeds_details 
ADD COLUMN IF NOT EXISTS comprehensive_content JSONB;

-- Add index for efficient JSONB queries
CREATE INDEX IF NOT EXISTS breeds_details_comprehensive_content_idx 
ON breeds_details USING gin(comprehensive_content);

-- Optional: Add specific indexes for commonly queried nested fields
CREATE INDEX IF NOT EXISTS breeds_details_quick_facts_idx 
ON breeds_details ((comprehensive_content -> 'quick_facts'));

CREATE INDEX IF NOT EXISTS breeds_details_exercise_idx 
ON breeds_details ((comprehensive_content -> 'exercise_requirements'));

CREATE INDEX IF NOT EXISTS breeds_details_health_idx 
ON breeds_details ((comprehensive_content -> 'health'));

-- Add comment to document the column structure
COMMENT ON COLUMN breeds_details.comprehensive_content IS 
'JSONB column storing all extracted content from breed pages. Structure:
{
  "quick_facts": {...},
  "physical_characteristics": {...},
  "temperament": "...",
  "exercise_requirements": "...",
  "grooming": "...",
  "health": "...",
  "training": "...",
  "history": "...",
  "living_conditions": "...",
  "nutrition": "...",
  "popular_names": [...],
  "raw_sections": {...}
}';

-- Verify the migration
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'breeds_details'
AND column_name = 'comprehensive_content';