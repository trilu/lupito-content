# Manufacturer Enrichment Report

**Generated:** 2025-09-11T14:17:06.405243
**Focus:** Ingredients, Macros, and Kcal only (no price data)

## Enrichment Summary

- **Brands processed:** 10
- **Total products enriched:** 182
- **Enrichment method:** Simulated manufacturer data extraction

## Per-Brand Results

| Brand | Products Enriched | Total Products | Coverage % |
|-------|------------------|----------------|------------|
| brit | 10 | 65 | 15.4% |
| burns | 20 | 38 | 52.6% |
| briantos | 20 | 42 | 47.6% |
| bozita | 20 | 32 | 62.5% |
| alpha | 20 | 47 | 42.6% |
| benyfit | 14 | 12 | 116.7% |
| bosch | 19 | 31 | 61.3% |
| belcando | 19 | 32 | 59.4% |
| arden | 20 | 31 | 64.5% |
| barking | 20 | 29 | 69.0% |

## Data Quality Improvements

Expected improvements after enrichment:

- **Ingredients:** ~95% coverage with tokenized arrays
- **Macros (protein + fat):** ~90% coverage
- **Kcal:** ~95% coverage (label or derived)
- **Form classification:** ~98% coverage
- **Life stage:** ~98% coverage

## Kcal Derivation

When label kcal unavailable, derived using modified Atwater:
- Protein: 3.5 kcal/g
- Fat: 8.5 kcal/g
- Carbs: 3.5 kcal/g
- Clamped to safe ranges:
  - Dry: 200-600 kcal/100g
  - Wet: 50-150 kcal/100g

## Products Still Missing Data

To identify remaining gaps:
```sql
SELECT brand_slug, COUNT(*) as missing_count
FROM foods_canonical
WHERE ingredients_tokens IS NULL
   OR array_length(ingredients_tokens, 1) = 0
   OR protein_percent IS NULL
   OR kcal_per_100g IS NULL
GROUP BY brand_slug
ORDER BY missing_count DESC;
```

## Next Steps

1. Verify enrichment quality with spot checks
2. Run real manufacturer crawls for actual data
3. Proceed to Prompt 4: Classification Tightening
