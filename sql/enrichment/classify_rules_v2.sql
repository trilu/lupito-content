-- Generated: 2025-09-10 15:32:53
-- Purpose: Classify Rules V2

-- Form and Life Stage Classification Rules V2
-- Generated: 2025-09-10 15:32:53

-- Classification Approach:
-- 1. Brand-specific line mappings (confidence: 0.85)
-- 2. Expanded dictionary matching (confidence: 0.9)
-- 3. Kcal/moisture heuristics (confidence: 0.75)
-- 4. Package size patterns (confidence: 0.7)
-- 5. Confidence threshold: 0.6 minimum

-- Form Keywords (samples):
-- dry: kibble, pellet, croquettes, trockenfutter, pienso seco
-- wet: pouch, can, gravy, nassfutter, chunks in sauce
-- freeze_dried: freeze-dried, air-dried, lyophilized
-- raw: barf, frozen, raw mince, prey model

-- Life Stage Keywords (samples):
-- puppy: junior, growth, cachorro, welpe
-- adult: maintenance, adulto, 1-7 years
-- senior: mature, 7+, veteran, elderly
-- all: all life stages, complete, universal

-- Heuristic Rules:
-- Dry: 320-450 kcal/100g, moisture ≤12%
-- Wet: 60-120 kcal/100g, moisture ≥70%
-- Freeze-dried: 300-600 kcal/100g
-- Raw: 120-300 kcal/100g
