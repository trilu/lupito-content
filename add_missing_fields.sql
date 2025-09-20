-- SQL Script to Add Missing Fields for 95% Completeness Target
-- Execute this to add the zero-completion fields identified in gap analysis

-- Add missing fields to breeds_comprehensive_content table
ALTER TABLE breeds_comprehensive_content
ADD COLUMN IF NOT EXISTS shedding TEXT,
ADD COLUMN IF NOT EXISTS color_varieties TEXT,
ADD COLUMN IF NOT EXISTS breed_standard TEXT;

-- Add any other missing fields that might be needed for the view
-- (These are fields that exist in the view but might be missing from the source table)

-- Verify the additions
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'breeds_comprehensive_content'
AND column_name IN ('shedding', 'color_varieties', 'breed_standard')
ORDER BY column_name;