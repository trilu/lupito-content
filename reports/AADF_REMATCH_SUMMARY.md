# AADF REMATCH SUMMARY
Generated: 2025-09-12T13:17:01.985689

## Executive Summary
Re-matching AADF products against canonical catalog using normalized brands and brand_alias table.

## Match Statistics

### Totals
- **AADF rows**: 1101
- **Exact key matches**: 0 (0.0%)
- **Candidates ≥0.9**: 5 (0.5%)
- **Candidates ≥0.8**: 13 (1.2%)
- **Candidates ≥0.7**: 23 (2.1%)
- **Would-be new products (<0.7)**: 1078 (97.9%)

## Top 15 Brands by Matchable SKUs (≥0.8)

| Rank | Brand | Total Products | Matchable (≥0.8) | Match Rate |
|------|-------|---------------|------------------|------------|
| 1 | Bentleys | 2 | 2 | 100.0% |
| 2 | Burns | 8 | 2 | 25.0% |
| 3 | Acana | 7 | 2 | 28.6% |
| 4 | Butchers | 12 | 2 | 16.7% |
| 5 | Bug | 2 | 2 | 100.0% |
| 6 | Benyfit | 4 | 1 | 25.0% |
| 7 | Autarky | 5 | 1 | 20.0% |
| 8 | Bosch | 5 | 1 | 20.0% |
| 9 | Billy | 5 | 0 | 0.0% |
| 10 | Forza10 | 1 | 0 | 0.0% |
| 11 | Cotswold | 2 | 0 | 0.0% |
| 12 | Burgess | 4 | 0 | 0.0% |
| 13 | Wellness | 8 | 0 | 0.0% |
| 14 | Freshpet | 4 | 0 | 0.0% |
| 15 | Naturo | 9 | 0 | 0.0% |

## Sample Matches (20 Random ≥0.8)

| AADF Brand | AADF Product | Catalog Brand | Catalog Product | Score | Key Match |
|------------|--------------|---------------|-----------------|-------|-----------|
| Autarky | mature lite delicious | Autarky | Mature Lite Delicious Chicken | 0.84 | ❌ |
| Butchers | simply gentle can | Butchers | Simply Gentle | 0.87 | ❌ |
| Burns | original and rice | Burns | Original Lamb  Brown Rice | 0.84 | ❌ |
| Benyfit | natural meat feast | Benyfit | Natural Meat Feast Turkey | 0.84 | ❌ |
| Bentleys | taste of the ocean | Bentleys | Taste of the Ocean | 1.00 | ❌ |
| Burns | original and rice | Burns | Original Lamb  Brown Rice | 0.84 | ❌ |
| Bosch | light | Bosch | Light | 1.00 | ❌ |
| Bug | bakes regular | Bug | Bakes Regular | 1.00 | ❌ |
| Butchers | traditional recipes foil | Butchers | Traditional Recipes | 0.88 | ❌ |
| Bentleys | superfood blend | Bentleys | Duck Superfood Blend | 0.86 | ❌ |
| Bug | bakes grain free | Bug | Bakes Grain Free | 1.00 | ❌ |
| Acana | highest protein | Acana | Highest Protein Ranchlands | 0.80 | ❌ |
| Acana | light and fit recipe | Acana | Light  fit Recipe | 0.92 | ❌ |

## Product Key Analysis

### Sample Key Comparisons (10 matches)

| AADF Key | Canonical Key | Match |
|----------|---------------|-------|
| burns|original_and_rice|dry | burns|original_lamb__brown_rice|dry | ❌ |
| bentleys|superfood_blend|raw | bentleys|duck_superfood_blend|unknown | ❌ |
| benyfit|natural_meat_feast|wet | benyfit|natural_meat_feast_turkey|raw | ❌ |
| bosch|light|wet | bosch|light|unknown | ❌ |
| burns|original_and_rice|dry | burns|original_lamb__brown_rice|dry | ❌ |
| bentleys|taste_of_the_ocean|dry | bentleys|taste_of_the_ocean|unknown | ❌ |
| bug|bakes_regular|wet | bug|bakes_regular|dry | ❌ |
| acana|light_and_fit_recipe|raw | acana|light__fit_recipe|dry | ❌ |
| butchers|simply_gentle_can|wet | butchers|simply_gentle|unknown | ❌ |
| autarky|mature_lite_delicious|wet | autarky|mature_lite_delicious_chicken|dr... | ❌ |

## Safety Validation

### Data Type Checks
- Ingredients field: ✅ Valid strings
- Product keys: ✅ All generated successfully
- Brand normalization: ✅ Applied via brand_alias table

### Match Quality Assessment

| Quality Tier | Score Range | Count | Percentage | Action |
|--------------|-------------|-------|------------|--------|
| Exact Match | 1.0 | 0 | 0.0% | Auto-merge safe |
| Very High | 0.9-0.99 | 5 | 0.5% | Auto-merge safe |
| High | 0.8-0.89 | 8 | 0.7% | Review recommended |
| Medium | 0.7-0.79 | 10 | 0.9% | Manual review required |
| Low/None | <0.7 | 1078 | 97.9% | New products |

## Recommendations

### ✅ Safe to Proceed

⚠️ **Limited matches found**: Only 13 products have score ≥0.8.

This may indicate:
- Brand normalization needs more aliases
- Product names differ significantly between AADF and catalog
- AADF contains mostly new products not in catalog

### Recommended Actions
1. Review brand mappings for top unmatched brands
2. Consider lower threshold (0.7) for manual review
3. Spot-check low-scoring matches for patterns

## Brand Normalization Impact

The brand_alias table successfully normalized brands for matching:

- **Brands normalized**: 50 products
- **Sample normalizations**:
  - 'Bob and Lush' → 'Bob & Lush'
  - 'Pitpat' → 'PitPat'
  - 'Hills Science' → 'Hill's'
  - 'Mcintyres' → 'McIntyres'
  - 'Pooch' → 'Pooch & Mutt'
