-- Add kcal_basis column to track whether energy values are measured or estimated
ALTER TABLE food_candidates 
ADD COLUMN IF NOT EXISTS kcal_basis TEXT CHECK (kcal_basis IN ('measured', 'estimated'));

-- Add comment explaining the column
COMMENT ON COLUMN food_candidates.kcal_basis IS 'Indicates whether kcal_per_100g was measured from label or estimated using Modified Atwater factors';