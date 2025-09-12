# Missing Ingredients Analysis Summary: Briantos & Bozita

**Generated:** 2025-09-12 00:05:00  
**Analysis Date:** September 12, 2025  
**Database Source:** foods_published_prod  
**GCS Bucket:** lupito-content-raw-eu  

## Executive Summary

Query results for Briantos and Bozita brands regarding missing ingredients_tokens:

- **Briantos:** 31 SKUs missing ingredients (0 have snapshots, 31 need harvest)
- **Bozita:** 31 SKUs missing ingredients (2 have snapshots, 29 need harvest)

## Detailed Findings

### Briantos Analysis
- **Total SKUs with missing ingredients_tokens:** 31
- **SKUs with GCS snapshots:** 0 (100% need harvest)
- **SKUs needing harvest:** 31

**Primary Issue:** Complete lack of GCS snapshots for Briantos products. All missing ingredients are due to no snapshots being available.

**Sample SKUs needing harvest:**
- Adult Mobility Grain-Free Chicken & Potato (`briantos|adult_mobility_grain-free_chicken__potato|unknown`)
- Adult Salmon & Rice (`briantos|adult_salmon__rice|unknown`) 
- Adult Sensitive Lamb & Rice (`briantos|adult_sensitive_lamb__rice|unknown`)
- Briantos Adult Light (`briantos|briantos_adult_light|dry`)

**URL Sources Identified:**
- PetFoodExpert.com (3 SKUs)
- Zooplus.com (28 SKUs)

### Bozita Analysis
- **Total SKUs with missing ingredients_tokens:** 31
- **SKUs with GCS snapshots:** 2 (6.5%)
- **SKUs needing harvest:** 29 (93.5%)

**Primary Issues:**
1. **93.5% missing snapshots** - Most products lack GCS snapshots
2. **6.5% extraction failures** - Products with snapshots but failed ingredient extraction

### Sample Failure Analysis (Bozita)

**Failed Extraction Example:**
- **Product:** Robur Sensitive Single Protein Lamb & Rice
- **Snapshot:** Available (manufacturers/bozita/2025-09-11/)
- **Failure Reason:** Ingredients found but in non-standard format
- **Issue:** Extraction logic failed to capture ingredients that ARE present

**Deep Analysis Reveals:**
The snapshot actually contains ingredients in this format:
```
"Lamb 26% (dried lamb protein 15%, freshly prepared lamb 9%, hydrolysed lamb protein 2%), maize*, rice* 14%, maize germs*, maize gluten, dried beet pulp*, animal fat 3%, linseeds*, vegetable oil, yeast..."
```

**Root Cause:** The current extraction selectors and patterns don't capture ingredients when they're:
- Embedded in product descriptions without standard headers like "Ingredients:"
- Mixed with percentage information in the product title/description area
- Presented in a flowing text format rather than structured lists

## Critical Findings

### Bozita Extraction Gap
The analysis revealed that **ingredients ARE present** in the Bozita snapshots but the extraction logic is missing them. Specifically:

**Working Example Found:**
```html
ROBUR SENSITIVE SINGLE PROTEIN WITH LAMB
Lamb 26% (dried lamb protein 15%, freshly prepared lamb 9%, hydrolysed lamb protein 2%), 
maize*, rice* 14%, maize germs*, maize gluten, dried beet pulp*, animal fat 3%, 
linseeds*, vegetable oil, yeast* (of which inactivated yeast 0.1%), minerals.
```

**Current Extraction Miss:** The script searched for standard patterns like:
- "Ingredients:" 
- "Composition:"
- "Contains:"

But missed ingredients embedded in product descriptions without these headers.

## Recommendations

### Immediate Priority Actions

#### 1. Fix Bozita Extraction Logic (High Impact, Low Effort)
- **Impact:** Could recover 2+ SKUs immediately 
- **Action:** Update extraction patterns to capture ingredients from product description text
- **Implementation:** Add regex patterns for `[Food Name]\s*([^.]+containing.*?)` and similar
- **Timeline:** 1-2 days

#### 2. Harvest Missing Snapshots (High Impact, High Effort)  
- **Briantos:** 31 SKUs need complete harvest
- **Bozita:** 29 SKUs need harvest
- **Priority URLs:**
  - Zooplus.com (57 total SKUs across both brands)
  - PetFoodExpert.com (3 Briantos SKUs)

#### 3. Enhanced Extraction Patterns
Add support for:
- Ingredients in product descriptions without headers
- Multi-language ingredient detection (Swedish for Bozita)
- Percentage-based ingredient lists
- Ingredients mixed with analytical constituents

### Technical Implementation

#### Improved Extraction Selectors
```python
# Add these patterns to existing extraction logic:
additional_patterns = [
    r'([A-Za-z][^.]*?(?:protein|meat|chicken|lamb|beef|fish)[^.]*?(?:\d+%[^.]*?){2,}[^.]*)',
    r'((?:[A-Za-z]+\s*\d+%[^,]*,\s*){3,}[^.]*)',
    r'([A-Za-z][^.]*?(?:dried|fresh|meal)[^.]*?(?:rice|potato|maize)[^.]*)',
]
```

#### Brand-Specific Rules
- **Bozita:** Look for ingredients after product name, before "ANALYTICAL CONSTITUENTS"
- **Briantos:** Standard e-commerce extraction (Zooplus format)

## Resource Requirements

### Immediate (Week 1)
- 1 developer day: Fix Bozita extraction patterns
- Test on 2 existing snapshots with known ingredients
- Deploy and re-run extraction on existing Bozita snapshots

### Short-term (2-4 weeks)  
- Harvest missing snapshots:
  - Briantos: 31 URLs (estimated 2-3 harvest sessions)
  - Bozita: 29 URLs (estimated 2-3 harvest sessions)
- Implement enhanced extraction patterns
- Validate results and measure improvement

## Success Metrics

### Target Improvements
- **Bozita:** From 0% to 100% extraction success on existing snapshots (2 SKUs recovered immediately)
- **Overall:** From 0 SKUs with ingredients to 62 SKUs with ingredients (31+31)
- **Coverage:** Achieve 90%+ ingredient coverage for both brands

### Validation Steps
1. Re-run extraction on existing Bozita snapshots
2. Verify ingredient quality and completeness
3. Harvest and process remaining missing snapshots
4. Final validation of ingredient coverage across both brands

## Appendix: Sample Data

### Briantos URLs Needing Harvest
```
https://petfoodexpert.com/food/briantos-adult-mobility-grain-free-chicken-potato
https://petfoodexpert.com/food/briantos-adult-salmon-rice  
https://petfoodexpert.com/food/briantos-adult-sensitive-lamb-rice
https://www.zooplus.com/shop/dogs/dry_dog_food/briantos/briantos_specialised/527598
https://www.zooplus.com/shop/dogs/dry_dog_food/briantos/briantos_adult/527599
[... 26 more Zooplus URLs]
```

### Bozita URLs Needing Harvest  
```
https://www.zooplus.com/shop/dogs/dry_dog_food/bozita/bozita_dog_food/1487109
https://www.zooplus.com/shop/dogs/dry_dog_food/bozita/bozita_dog_food/1488409
https://www.zooplus.com/shop/dogs/dry_dog_food/bozita/bozita_dog_food/128406
[... 26 more Zooplus URLs]
```

---

**Note:** This analysis was performed using production data from foods_published_prod table and GCS bucket lupito-content-raw-eu. The findings indicate both snapshot availability issues and extraction logic gaps that can be addressed to significantly improve ingredient coverage for both brands.