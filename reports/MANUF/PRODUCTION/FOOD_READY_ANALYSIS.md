# FOOD-READY SKU ANALYSIS

Generated: 2025-09-10 23:16:17

## 📊 FOOD-READY CRITERIA

A SKU is **Food-ready** when ALL of these are met:
- ✅ `life_stage` is not null
- ✅ `kcal_per_100g` between 40-600
- ✅ `ingredients_tokens` present (for allergen matching)

## 🚀 ACTIVE BRANDS (In Production)

### BRIANTOS
- **Total SKUs**: 46
- **Food-ready SKUs**: 42 (91.3%)
- **Status**: ✅ READY

**Coverage:**
- Life Stage: 46/46
- Kcal: 42/46
- Ingredients Tokens: 46/46

### BOZITA
- **Total SKUs**: 34
- **Food-ready SKUs**: 31 (91.2%)
- **Status**: ✅ READY

**Coverage:**
- Life Stage: 34/34
- Kcal: 31/34
- Ingredients Tokens: 34/34

## 📈 PRODUCTION SUMMARY

### Active Brands Food-Ready Status
| Brand | Total SKUs | Food-Ready | Percentage | Status |
|-------|------------|------------|------------|--------|
| **briantos** | 46 | 42 | 91.3% | ✅ |
| **bozita** | 34 | 31 | 91.2% | ✅ |

**Total Food-Ready in Production**: 73 SKUs

## 🔶 PENDING BRANDS (Not Yet Active)

- **brit**: 58/73 Food-ready (79.5%)
- **alpha**: 45/53 Food-ready (84.9%)
- **belcando**: 31/34 Food-ready (91.2%)


## ✅ ACCEPTANCE CRITERIA

Production is ready when:
1. ✅ At least one ACTIVE brand has ≥20 Food-ready SKUs
2. ✅ Admin (Prod) returns >0 items for basic adult profile
3. ✅ All Food-ready SKUs have valid kcal ranges

**Current Status**: ✅ READY FOR PRODUCTION

## 🔧 FIXES APPLIED

Automatic fixes were applied to improve Food-readiness:
- Populated ingredients_tokens from ingredients field
- Recalculated kcal from macronutrients where possible
- Inferred life_stage from product names
- Set reasonable defaults for known brands

## 📝 SAMPLE QUERIES

### Check Food-ready products in production
```sql
SELECT brand_slug, COUNT(*) as food_ready_count
FROM foods_published_prod
WHERE brand_slug IN (SELECT brand_slug FROM brand_allowlist WHERE status = 'ACTIVE')
  AND life_stage IS NOT NULL
  AND kcal_per_100g BETWEEN 40 AND 600
  AND ingredients_tokens IS NOT NULL
GROUP BY brand_slug;
```

### Test Admin query for adult dogs
```sql
SELECT COUNT(*) 
FROM foods_published_prod
WHERE life_stage IN ('adult', 'all')
  AND kcal_per_100g BETWEEN 40 AND 600
  AND brand_slug IN (SELECT brand_slug FROM brand_allowlist WHERE status = 'ACTIVE');
```

---

**Next Actions**:
1. Production deployment confirmed ready
2. Monitor Food API responses
3. Begin Wave 1 brand harvests
