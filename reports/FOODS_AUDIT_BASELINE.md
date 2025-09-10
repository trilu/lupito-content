# FOODS AUDIT BASELINE REPORT

Generated: 2025-09-10 15:08:01

---

## EXECUTIVE SUMMARY

### Key Metrics

- **Total Products:** 1,000.0
- **Unique Brands:** 77.0
- **Ingredients Coverage:** 100.0%
- **Nutrition Coverage:** 95.9%
- **Price Coverage:** 27.1%
- **Classification Coverage:** 29.1%

### Biggest Gaps

1. **Ingredients Tokens:** Missing for significant portion of products, critical for allergy detection
2. **Pricing Buckets:** Low coverage impacts recommendation quality
3. **Nutrition Data:** Kcal missing for many products, especially newer additions
4. **Life Stage Classification:** Inconsistent with product names in many cases

### Top 5 Brands to Enrich (by impact)

Based on product count and quality gaps:

1. Focus on brands with high product counts and low data quality
2. Prioritize ingredients and nutrition data
3. Ensure price bucket classification
4. Validate life stage consistency
5. Complete missing metadata

### Top 5 Fields to Enrich Globally

1. **ingredients_tokens** - Use JSON-LD scraping + PDF parsing
2. **price_bucket** - Apply threshold rules to existing prices
3. **kcal_per_100g** - Extract from product pages or packaging
4. **life_stage** - NLP classification from product names
5. **macros (protein/fat)** - Nutritional table extraction

### Prioritized 10-Item Backlog

1. **Create price bucket rules** - Quick win for products with price data (Est: 2 hrs)
2. **Parse brand websites for ingredients** - High impact (Est: 2 days)
3. **Fix life_stage mismatches** - Use product name NLP (Est: 4 hrs)
4. **Enrich top brands** - Focus on high-volume brands (Est: 1 day per brand)
5. **Implement kcal validation** - Data quality (Est: 2 hrs)
6. **Build allergy detection pipeline** - User value (Est: 1 day)
7. **Standardize form values** - Data consistency (Est: 2 hrs)
8. **Add freshness monitoring** - Track stale data (Est: 3 hrs)
9. **Create brand enrichment API** - Scalability (Est: 3 days)
10. **Implement data validation rules** - Quality assurance (Est: 1 day)

---

## Inventory & Uniqueness


### Inventory & Uniqueness

**Tables Found:** 5
                table  row_count
0     foods_published       5151
1     food_candidates       3851
2  food_candidates_sc       1234
3         food_brands        106
4            food_raw         63

**Product Key Uniqueness:** ✓ All product_keys are unique (in sample)

---

## Coverage & Nulls


### Field Coverage & Nulls

**Total Records Analyzed:** 1,000

**Top Coverage Fields:**
              field  populated_count  total_count  coverage_pct
 ingredients_tokens             1000         1000         100.0
available_countries             1000         1000         100.0
         updated_at             1000         1000         100.0
        fat_percent              993         1000          99.3
    protein_percent              961         1000          96.1

**Biggest Gaps (Missing %):**
          field  missing_pct
   price_bucket         72.9
           form         54.4
     life_stage         45.6
  kcal_per_100g          4.1
protein_percent          3.9

---

## Distributions & Outliers


### Quality Distributions & Outliers

**Kcal Distribution by Form:**
form  count  mean_kcal  min_kcal  max_kcal  median_kcal
 raw     12      368.2     362.5     376.0        366.0
 dry    372      356.8     263.0     400.2        362.4
 wet     44      298.8      50.1     386.0        366.0
BARF      1      355.8     355.8     355.8        355.8

**Kcal Outliers Found:** 33
**Life Stage Mismatches Found:** 1

---

## Ingredients & Allergy Readiness


### Ingredients & Allergy Readiness

**Overall Ingredients Coverage:** 1,000 products with tokens

**Top 10 Ingredient Tokens:**
        token  count
     minerals     41
  glucosamine     25
         peas     24
     turmeric     24
    beet pulp     22
 milk thistle     20
  chondroitin     20
yucca extract     20
         rice     20
      oregano     18

**Allergy Detection Coverage:**
allergen_group  products_detected  coverage_pct
       chicken                 46           4.6
          beef                  7           0.7
   fish_salmon                 36           3.6
  grain_gluten                 30           3.0

**Priority Brands for Enrichment (low token coverage):**
No priority brands identified

---

## Pricing Coverage & Buckets


### Pricing Coverage & Buckets

**Overall Coverage:**
 total_products  with_price  with_price_per_kg  with_bucket  price_coverage_pct  price_per_kg_coverage_pct  bucket_coverage_pct
           1000           0                  0          271                   0                          0                 27.1

**Products with price but no bucket:** 0

**Price Bucket Distribution:**
No bucket data available

**Proposed Bucket Thresholds (based on distribution):**
- Low: < €15/kg
- Mid: €15-30/kg
- High: > €30/kg

---

## Availability & Freshness


### Availability & Freshness

**Data Freshness:**
   age_bucket  products  percentage
    0-30 days      1000       100.0
   31-90 days         0         0.0
  91-180 days         0         0.0
Over 180 days         0         0.0

**Country Availability:** Available
       country  products
            UK       944
            EU       780
       Germany         6
         Spain         2
Czech Republic         2

---

## Brand Quality Leaderboard


### Brand Quality Leaderboard

**Quality Score Weights:**
- Ingredients Tokens: 40%
- Kcal: 25%
- Life Stage + Form: 25%
- Price Bucket: 10%

**Top 10 Brands by Quality Score:**
                   brand  product_count  quality_score
            Arden Grange             14         100.00
             Almo Nature             13          98.08
                 Applaws             31          93.39
                   bosch             26          92.40
                Arquivet              7          91.07
                    Brit             73          90.62
Advance Veterinary Diets             26          90.38
                  Bakers             15          90.33
                Animonda              9          90.28
                 Autarky             19          87.76

**Bottom 15 Brands (Enrichment Priority):**
   brand  product_count  quality_score  tokens_coverage  kcal_coverage
 Benyfit             14          54.29            100.0           0.00
    Bear              7          61.43            100.0          85.71
  Amazon             15          64.17            100.0          93.33
Bentleys              8          65.00            100.0         100.00
   4PAWS              6          65.00            100.0         100.00
   Buddy              9          66.39            100.0         100.00
   Boost              8          66.56            100.0         100.00
    Beco              8          66.56            100.0         100.00
    Aldi             15          66.67            100.0         100.00
AniForte              7          66.79            100.0         100.00
   Alpha             53          67.59            100.0         100.00
  Aflora              9          67.78            100.0         100.00
  Bright             25          68.50            100.0         100.00
   Akela             14          68.57            100.0         100.00
   BETTY             24          69.17            100.0         100.00

---

### Top 10 SKUs to Enrich First

Products from high-volume brands with multiple data gaps:

| Product Key | Brand | Product Name | Primary Gap | Total Gaps |
|-------------|-------|--------------|-------------|------------|
| barking|heads_plant_powered_po... | Barking | Heads Plant Powered Pooches... | ingredients | 4 |
| bright|eyes_bushy_tails_canine... | Bright | Eyes Bushy Tails Canine Best 65% Duck Wi... | ingredients | 3 |
| bright|eyes_bushy_tails_grain_... | Bright | Eyes Bushy Tails Grain Free Pork Sweet P... | ingredients | 3 |
| bright|eyes_bushy_tails_grain_... | Bright | Eyes Bushy Tails Grain Free Lamb Sweet P... | ingredients | 3 |
| bright|eyes_bushy_tails_grain_... | Bright | Eyes Bushy Tails Grain Free Haddock Swee... | ingredients | 3 |
| bright|eyes_bushy_tails_grain_... | Bright | Eyes Bushy Tails Grain Free Duck aLOrang... | ingredients | 3 |
| bright|eyes_bushy_tails_grain_... | Bright | Eyes Bushy Tails Grain Free Chicken Swee... | ingredients | 3 |
| bright|eyes_bushy_tails_grain_... | Bright | Eyes Bushy Tails Grain Free Angus Beef S... | ingredients | 3 |
| bright|eyes_bushy_tails_duck_w... | Bright | Eyes Bushy Tails Duck with Potato Super ... | ingredients | 3 |
| bright|eyes_bushy_tails_chicke... | Bright | Eyes Bushy Tails Chicken with Rice Super... | ingredients | 3 |

---

*End of Report*
