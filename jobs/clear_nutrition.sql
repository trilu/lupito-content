-- Clear nutrition data to force re-scraping
UPDATE food_candidates
SET 
  protein_percent = NULL,
  fat_percent = NULL,
  fiber_percent = NULL,
  ash_percent = NULL,
  moisture_percent = NULL,
  kcal_per_100g = NULL,
  last_seen_at = NOW() - INTERVAL '1 day'
WHERE protein_percent IS NULL;