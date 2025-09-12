# RETAILER AUDIT SUMMARY
Generated: 2025-09-12T08:28:16.879278

## Executive Summary

### Dataset Overview

**CHEWY:**
- Total records: 1282
- Dog products: 1282
- Treats/toppers: 33
- Complete foods: 1249

**AADF:**
- Total records: 1101
- Dog products: 1101
- Treats/toppers: 0
- Complete foods: 1101

### Field Coverage

**CHEWY Coverage:**
- Form: 1267 (98.8%)
- Life Stage: 1243 (97.0%)
- Price: 1228 (95.8%)
- Ingredients: 0 (0.0%) - Not available in Chewy dataset

**AADF Coverage:**
- Form: 1076 (97.7%)
- Life Stage: 1016 (92.3%)
- Price: 1095 (99.5%)
- Ingredients: 1101 (100.0%)

### Catalog Match Rate

**CHEWY Matches:**
- Exact product key matches: 0
- Fuzzy name matches (>85%): 0
- New products: 1282
- Match rate: 0.0%

**AADF Matches:**
- Exact product key matches: 0
- Fuzzy name matches (>85%): 0
- New products: 1101
- Match rate: 0.0%

### Top 10 Brands by Potential Impact

| Brand | Products | With Form | With Life Stage | Impact Score |
|-------|----------|-----------|-----------------|-------------|
| Stella & Chewy's | 71 | 71 | 70 | 10011 |
| Blue Buffalo | 59 | 59 | 59 | 6962 |
| Purina Pro Plan | 56 | 56 | 56 | 6272 |
| Purina ONE | 44 | 44 | 44 | 3872 |
| 0 0 | 44 | 44 | 44 | 3872 |
| Pedigree | 41 | 41 | 41 | 3362 |
| JustFoodForDogs | 40 | 39 | 39 | 3120 |
| Hill's Science Diet | 37 | 37 | 37 | 2738 |
| Instinct | 35 | 35 | 34 | 2415 |
| Hill's Prescription Diet | 33 | 33 | 31 | 2112 |

## Acceptance Gates

- Match Rate (≥30%): **FAIL ❌**
- Quality Lift (≥10pp): **PASS ✅**
- Safety (0 collisions): **PASS ✅**
- Provenance (100% sourced): **PASS ✅**

## Recommendation

**DO-NOT-MERGE**: Match rate below 30% threshold. Most products appear to be new/unmatched.

### Key Benefits of Merge:
1. **Geographic Coverage**: Chewy (US) + AADF (UK) provide international coverage
2. **Field Completeness**: AADF provides ingredients, Chewy provides better pricing
3. **Brand Diversity**: Combined ~600 unique brands vs existing catalog
4. **High Quality**: 98%+ form coverage, 95%+ life_stage coverage

### Risks:
1. **Brand Normalization**: Some brands may need manual review
2. **Price Conversion**: USD→EUR conversion uses static rate
3. **Product Duplication**: Some products may exist in both datasets
