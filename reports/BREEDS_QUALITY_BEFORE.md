# Breeds Quality Assessment - BEFORE Enrichment

**Date:** 2025-09-10  
**Database:** breeds_details  
**Total Breeds:** 583

## Current Coverage Status

### Operational Fields (AI Math Critical)

| Field | Coverage | Count | Target | Gap |
|-------|----------|-------|--------|-----|
| size_category | 71.4% | 416/583 | 100% | -28.6% |
| growth_end_months | 0% | 0/583 | 100% | -100% |
| senior_start_months | 0% | 0/583 | 100% | -100% |
| adult_weight_min_kg | 71.4% | 416/583 | 95% | -23.6% |
| adult_weight_max_kg | 71.4% | 416/583 | 95% | -23.6% |
| adult_weight_avg_kg | 0% | 0/583 | 95% | -95% |

### Editorial Fields

| Field | Coverage | Count | Target | Gap |
|-------|----------|-------|--------|-----|
| height_min_cm | 67.2% | 392/583 | 95% | -27.8% |
| height_max_cm | 67.2% | 392/583 | 95% | -27.8% |
| lifespan_min_years | 38.8% | 226/583 | 90% | -51.2% |
| lifespan_max_years | 38.8% | 226/583 | 90% | -51.2% |
| lifespan_avg_years | 0% | 0/583 | 90% | -90% |

## Current Quality Issues

### Critical Outliers Found
1. **Weight outliers:** 0 (previously fixed)
2. **Height outliers:** Multiple breeds with impossible values (e.g., 127cm for Entlebucher)
3. **Lifespan outliers:** Multiple breeds with impossible values (e.g., 50 years max)

### Size-Weight Consistency
- **Consistent:** 416/416 (100%) for breeds with weight data
- **Inconsistent:** 0
- **Missing data:** 167 breeds without weight or size

### Data Sources Currently Used
- Wikipedia scraping: Primary source
- Manual overrides: Applied to ~10 breeds
- Defaults: None currently applied

## Grade Assessment

### Current Score: 89.2% (Grade B)

**Score Breakdown:**
- Data Coverage: 100.0%
- Completeness: 74.7%
- Internal Consistency: 100.0%
- Weight Data Available: 71.4%
- Update Recency: 100.0%

### Required for Grade A+ (≥98%)
1. Add weight data for 167 breeds (28.6%)
2. Calculate weight averages for all breeds
3. Add growth_end_months for all breeds
4. Add senior_start_months for all breeds
5. Fix height outliers
6. Fix lifespan outliers
7. Improve lifespan coverage by 51.2%

## Sample of Missing Data Breeds

| Breed | Weight | Height | Lifespan | Size |
|-------|--------|--------|----------|------|
| affenpinscher | ❌ | ❌ | ❌ | ❌ |
| afghan-hound | ❌ | ❌ | ❌ | ❌ |
| airedale-terrier | ❌ | ❌ | ❌ | ❌ |
| akita | ❌ | ❌ | ❌ | ❌ |
| alaskan-malamute | ❌ | ❌ | ❌ | ❌ |

## Recommendations

1. **Immediate Priority:** Add growth_end_months and senior_start_months (currently 0%)
2. **High Priority:** Fill weight gaps for 167 breeds
3. **Medium Priority:** Fix height/lifespan outliers
4. **Low Priority:** Add narrative content

---
*Generated: 2025-09-10*