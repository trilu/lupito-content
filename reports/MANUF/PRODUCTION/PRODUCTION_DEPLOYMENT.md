# FOODS_PUBLISHED_PROD - PRODUCTION DEPLOYMENT
Generated: 2025-09-10 20:58:34

## Production Allowlist
Brands approved for production enrichment:
- **Briantos** ✅ (Passed quality gates)
- **Bozita** ✅ (Passed quality gates)

## Deployment Statistics

### Overall Catalog
- Total Products: 340
- Allowlisted Products: 80
- Enriched Products: 80
- Enrichment Rate: 100.0% of allowlisted

### Coverage Improvement (Allowlisted Brands Only)

| Field | Before | After | Improvement |
|-------|--------|-------|-------------|
| Form | 0 | 79 | +79 |
| Life Stage | 0 | 78 | +78 |
| Ingredients | 0 | 80 | +80 |
| Price | 0 | 68 | +68 |

### Allowlisted Brands Coverage
- Form: 98.8%
- Life Stage: 97.5%
- Ingredients: 100.0%
- Price: 85.0%

## Fields Enriched
- ingredients: 80 products
- ingredients_tokens: 80 products
- allergen_groups: 80 products
- pack_size: 80 products
- form_confidence: 80 products
- life_stage_confidence: 80 products
- form: 79 products
- life_stage: 78 products
- protein_percent: 73 products
- fat_percent: 73 products
- fiber_percent: 73 products
- ash_percent: 73 products
- moisture_percent: 73 products
- kcal_per_100g: 73 products
- price: 68 products
- price_per_kg: 68 products
- price_bucket: 68 products

## Data Quality Assurance
- ✅ Only production-approved brands enriched
- ✅ Read-additive approach (no data overwritten)
- ✅ Full provenance tracking with _source fields
- ✅ Atomic swap capability for brand cohorts

## Production Configuration
```python
PRODUCTION_ALLOWLIST = ['briantos', 'bozita']
```

## Rollback Instructions
To rollback to catalog-only data:
1. Remove brand from PRODUCTION_ALLOWLIST
2. Re-run `create_foods_published_prod.py`
3. Deploy new foods_published_prod.csv

## Next Steps
1. Monitor production metrics for 24-48 hours
2. Review user feedback and quality reports
3. Add Brit, Alpha, Belcando after fixes
4. Scale to next 10 brands per roadmap
