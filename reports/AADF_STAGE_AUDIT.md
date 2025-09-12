# AADF STAGE AUDIT
Generated: 2025-09-12T08:41:38.014751

## Dataset Overview
- **Total rows**: 1,101
- **Distinct brands**: 501
- **Treats/toppers identified**: 0 (0.0%)
- **Complete foods**: 1,101 (100.0%)

## Coverage Analysis

| Field | Count | Coverage % | Status |
|-------|-------|------------|--------|
| Brand (brand_slug) | 1,101 | 100.0% | ✅ |
| Product (product_name_norm) | 1,101 | 100.0% | ✅ |
| Form (form_guess) | 1,095 | 99.5% | ✅ |
| Life Stage (life_stage_guess) | 1,090 | 99.0% | ✅ |
| Ingredients (ingredients_raw) | 1,101 | 100.0% | ✅ |

## Top 20 Brands by Product Count

| Rank | Brand | Products | % of Total |
|------|-------|----------|------------|
| 1 | Royal Canin | 55 | 5.0% |
| 2 | Hill | 21 | 1.9% |
| 3 | Eukanuba | 19 | 1.7% |
| 4 | Millies Wolfheart | 15 | 1.4% |
| 5 | Alpha Spirit | 12 | 1.1% |
| 6 | Natures Menu | 12 | 1.1% |
| 7 | Natures Deli | 12 | 1.1% |
| 8 | Farmina Natural | 12 | 1.1% |
| 9 | Pooch | 11 | 1.0% |
| 10 | Fish | 10 | 0.9% |
| 11 | Wainwrights Dry | 10 | 0.9% |
| 12 | Wolf Of | 10 | 0.9% |
| 13 | Arden Grange | 10 | 0.9% |
| 14 | James Wellbeloved | 10 | 0.9% |
| 15 | Country Dog | 9 | 0.8% |
| 16 | Pro Plan | 9 | 0.8% |
| 17 | Concept For | 8 | 0.7% |
| 18 | Leader Adult | 8 | 0.7% |
| 19 | Burns | 8 | 0.7% |
| 20 | Barking Heads | 7 | 0.6% |

## Ambiguous Records (Missing Brand/Product)

Total ambiguous records: 0

### Sample of 20 Ambiguous Records:

## Form Distribution

| Form | Count | Percentage |
|------|-------|------------|
| dry | 797 | 72.4% |
| wet | 219 | 19.9% |
| raw | 79 | 7.2% |
| unknown | 6 | 0.5% |

## Life Stage Distribution

| Life Stage | Count | Percentage |
|------------|-------|------------|
| senior | 687 | 62.4% |
| puppy | 208 | 18.9% |
| adult | 195 | 17.7% |
| unknown | 11 | 1.0% |

## Data Quality Assessment

### Strengths:
- **Ingredients data**: 100.0% coverage provides valuable nutrition information
- **Price data**: Available for most products (derived from price per day)
- **UK market coverage**: Comprehensive UK brand representation

### Weaknesses:
- **Product name extraction**: Some products have view count prefixes that complicate parsing
- **Brand normalization**: Requires manual mapping for consistency
- **Form/life stage**: Derived from text analysis, may have errors

## Processing Summary

- Records successfully staged: 1,101
- Database table: `retailer_staging_aadf`
- Staging timestamp: 2025-09-12T08:41:38.015045

## OK to Proceed?

**Status: ✅ YES**


All coverage thresholds met:
- Brand/product extraction ≥ 90% ✅
- Form/life_stage classification ≥ 80% ✅

**Recommendation**: Proceed with data validation and potential merge to foods_canonical after:
1. Manual review of top brands for normalization
2. Verification of treat/topper classifications
3. Cross-reference with existing catalog for duplicates
