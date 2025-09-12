# AADF STAGE AUDIT V2
Generated: 2025-09-12T08:53:19.223392

## Dataset Overview
- **Total rows**: 1101
- **CSV file**: data/aadf/aadf-dataset.csv
- **Staging table**: retailer_staging_aadf_v2
- **Processing complete**: ✅

## Coverage Analysis

| Field | Count | Coverage % | Status |
|-------|-------|------------|--------|
| Brand (brand_slug) | 1101 | 100.0% | ✅ |
| Product (product_name_norm) | 1101 | 100.0% | ✅ |
| Form (form_guess) | 1065 | 96.7% | ✅ |
| Life Stage (life_stage_guess) | 806 | 73.2% | ⚠️ |
| Ingredients (ingredients_raw) | 1101 | 100.0% | ✅ |
| Nutrition (kcal_per_100g) | 0 | 0.0% | ⚠️ |

## Top Brands by Product Count

| Rank | Brand | Products | % of Total |
|------|-------|----------|------------|
| 1 | Royal Canin | 55 | 5.0% |
| 2 | Wainwrights | 24 | 2.2% |
| 3 | Husse | 19 | 1.7% |
| 4 | Eukanuba | 19 | 1.7% |
| 5 | Hills Science | 17 | 1.5% |
| 6 | Ava | 16 | 1.5% |
| 7 | Millies Wolfheart | 15 | 1.4% |
| 8 | Natural | 13 | 1.2% |
| 9 | Skinners | 12 | 1.1% |
| 10 | Leader | 12 | 1.1% |
| 11 | Natures Deli | 12 | 1.1% |
| 12 | Natures Menu | 12 | 1.1% |
| 13 | Farmina Natural | 12 | 1.1% |
| 14 | Alpha Spirit | 12 | 1.1% |
| 15 | Essential | 12 | 1.1% |
| 16 | Butchers | 12 | 1.1% |
| 17 | Natures | 11 | 1.0% |
| 18 | Pooch | 11 | 1.0% |
| 19 | Lifestage | 11 | 1.0% |
| 20 | James Wellbeloved | 11 | 1.0% |

## Form Distribution

| Form | Count | Percentage |
|------|-------|------------|
| wet | 683 | 62.0% |
| dry | 315 | 28.6% |
| raw | 55 | 5.0% |
| unknown | 36 | 3.3% |
| freeze_dried | 12 | 1.1% |

## Life Stage Distribution

| Life Stage | Count | Percentage |
|------------|-------|------------|
| adult | 371 | 33.7% |
| unknown | 295 | 26.8% |
| puppy | 270 | 24.5% |
| senior | 165 | 15.0% |

## Processing Summary

- Records successfully processed: 1101
- Unique row hashes: 1101
- Product keys generated: 976
- Staging CSV: data/staging/aadf_staging_v2.csv
- SQL DDL: sql/create_aadf_staging_v2.sql

## Data Quality Gates

**All Required Gates**: ⚠️ REVIEW NEEDED

- Brand/product extraction ≥ 90%: ✅
- Form/life_stage classification ≥ 80%: ❌
- Ingredients coverage (100% expected): ✅
