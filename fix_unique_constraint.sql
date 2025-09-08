-- Fix unique constraint for food_candidates_sc table
-- Run this in Supabase SQL Editor

-- First, drop the existing constraint if it exists
ALTER TABLE food_candidates_sc 
DROP CONSTRAINT IF EXISTS unique_retailer_product_sc;

-- Create a new unique constraint without pack_sizes (JSONB can't be in unique constraints easily)
ALTER TABLE food_candidates_sc 
ADD CONSTRAINT unique_retailer_product 
UNIQUE (brand, product_name, retailer_source);