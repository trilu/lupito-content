# Ingredients Type Fix Report

**Generated:** 2025-09-11T14:12:05.570215

## Audit Summary

| Table | Total Rows | Valid Arrays | Strings | NULLs | Empty | Needs Fix |
|-------|------------|--------------|---------|-------|-------|----------|
| foods_canonical | 1,000 | 1,000 (100.0%) | 0 | 0 | 897 | 0 |
| foods_published | 1,000 | 1,000 (100.0%) | 0 | 0 | 897 | 0 |
| food_candidates | 1,000 | 1,000 (100.0%) | 0 | 0 | 967 | 0 |
| food_candidates_sc | 1,000 | 0 (0.0%) | 0 | 1,000 | 0 | 0 |

**Total rows to fix:** 0
**Total rows analyzed:** 4,000

## Coverage After Fix

Expected improvements after running migrations:

- **foods_canonical**: 10.3% → 10.3%
- **foods_published**: 10.3% → 10.3%
- **food_candidates**: 3.3% → 3.3%
- **food_candidates_sc**: 0.0% → 0.0%

## Top 50 Most Common Ingredients

After standardization, the most common ingredient tokens are:

| Rank | Ingredient | Count |
|------|------------|-------|
| 1 | minerals | 150 |
| 2 | rice | 104 |
| 3 | maize | 91 |
| 4 | chicken | 75 |
| 5 | vitamins | 70 |
| 6 | glucosamine | 61 |
| 7 | barley | 56 |
| 8 | animal fat | 56 |
| 9 | dried beet pulp | 56 |
| 10 | peas | 56 |
| 11 | turmeric | 55 |
| 12 | beet pulp | 49 |
| 13 | chondroitin | 49 |
| 14 | yucca extract | 49 |
| 15 | milk thistle | 47 |
| 16 | oregano | 42 |
| 17 | yeast | 42 |
| 18 | carrot | 38 |
| 19 | tomato | 31 |
| 20 | prebiotic mos | 31 |
| 21 | ginger | 31 |
| 22 | cereals | 31 |
| 23 | fresh whole butternut squash | 30 |
| 24 | fresh whole pumpkin | 30 |
| 25 | burdock root | 30 |
| 26 | marshmallow root | 30 |
| 27 | fish oil | 30 |
| 28 | seaweed | 29 |
| 29 | prebiotic fos | 29 |
| 30 | refined chicken oil | 29 |
| 31 | krill | 29 |
| 32 | msm | 29 |
| 33 | cranberry | 28 |
| 34 | thyme | 28 |
| 35 | marigold | 28 |
| 36 | aniseed | 28 |
| 37 | fenugreek | 28 |
| 38 | cranberries | 28 |
| 39 | oils and fats | 28 |
| 40 | chicken fat | 27 |
| 41 | lavender | 26 |
| 42 | meat and animal derivatives | 26 |
| 43 | peppermint | 25 |
| 44 | whole green peas | 25 |
| 45 | whole red lentils | 25 |
| 46 | whole green lentils | 25 |
| 47 | whole yellow peas | 25 |
| 48 | dried chicory root | 25 |
| 49 | rosehip | 24 |
| 50 | dried kelp | 24 |

## Metadata Fields Added

The following metadata fields were added to track processing:

- `ingredients_tokens_version`: Version of tokenization (default: 'v1')
- `ingredients_parsed_at`: Timestamp of last parsing
- `ingredients_source`: Source of ingredients (label|html|pdf|manual)
- `ingredients_language`: Language code (default: 'en')

## Migration Files

SQL migrations saved to: `sql/migrations/fix_ingredients_types_20250911_141204.sql`

## Next Steps

1. Review and run the SQL migrations
2. Refresh any affected views/materialized views
3. Proceed to Prompt 2: Tokenize + Canonicalize
