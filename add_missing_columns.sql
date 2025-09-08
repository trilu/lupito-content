-- Add any missing columns to food_candidates_sc table

-- Add in_stock column if it doesn't exist (we don't need it but some scripts use it)
ALTER TABLE food_candidates_sc 
ADD COLUMN IF NOT EXISTS in_stock BOOLEAN DEFAULT true;

-- Add ingredients_text as alias for ingredients_raw (if needed)
ALTER TABLE food_candidates_sc 
ADD COLUMN IF NOT EXISTS ingredients_text TEXT;

-- If ingredients_text was added, copy data from ingredients_raw
UPDATE food_candidates_sc 
SET ingredients_text = ingredients_raw 
WHERE ingredients_text IS NULL AND ingredients_raw IS NOT NULL;