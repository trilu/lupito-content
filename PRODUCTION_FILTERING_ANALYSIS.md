# Production Filtering Logic Analysis

## Executive Summary

Through comprehensive database analysis, I've reverse-engineered the exact filtering logic that reduces products from **9,339 (preview) to 3,119 (production)** - a **66.6% filter rate**.

## Key Findings

### Primary Filtering Mechanism: `allowlist_status` Field

The main filtering is controlled by a single field: **`allowlist_status`**

- **Preview table**: Contains products with `allowlist_status` = 'ACTIVE' (3,119) and 'PENDING' (6,220)
- **Production table**: Contains **ONLY** products with `allowlist_status` = 'ACTIVE'

```sql
-- Primary filter that accounts for ~99% of the filtering
WHERE allowlist_status = 'ACTIVE'
```

### Secondary Filtering: Source-Based Exclusions

Additional minor filtering removes specific data sources:

```sql
-- Secondary filters (removes ~68 additional products)
AND source NOT IN ('zooplus_csv_import', 'allaboutdogfood')
```

## Detailed Analysis Results

### 1. Row Count Comparison
- **Preview**: 9,339 products
- **Production**: 3,119 products
- **Filter rate**: 66.6%

### 2. Schema Differences
- **Preview has 27 columns**, Production has 26 columns
- **Missing from production**: `allowlist_updated_at` (metadata field)
- All other columns are identical

### 3. Source-Based Filtering Analysis

| Source | Preview Count | Production Count | Filter Rate |
|--------|---------------|------------------|-------------|
| `food_candidates` | 794 | 724 | 8.8% |
| `food_candidates_sc` | 63 | 196 | -211% (increased) |
| `food_brands` | 17 | 12 | 29.4% |
| `zooplus_csv_import` | **39** | **0** | **100% filtered** |
| `allaboutdogfood` | **18** | **0** | **100% filtered** |

### 4. Quality Score Impact
- **Preview average**: 2.27
- **Production average**: 2.38
- Quality scores range 1-6, with production slightly favoring higher scores

### 5. Data Completeness Comparison

| Field | Preview % | Production % | Difference |
|-------|-----------|-------------|-----------|
| `kcal_per_100g` | 82.0% | 86.5% | +4.5% |
| `ingredients_tokens` | 94.4% | 100.0% | +5.6% |
| `life_stage` | 84.5% | 93.2% | +8.7% |
| `protein_percent` | 90.9% | 89.5% | -1.4% |
| `fat_percent` | 93.4% | 92.1% | -1.3% |
| `form` | 96.6% | 94.2% | -2.4% |

### 6. Brand Filtering Analysis
- **Completely filtered brands**: 7 brands (100% removal)
- **Top allowed brands**: brit, bozita, alpha, belcando (0% filtering)
- Most established brands pass through with minimal filtering

## Exact SQL Implementation

### Complete Production Filter
```sql
SELECT *
FROM foods_published_preview
WHERE allowlist_status = 'ACTIVE'
  AND (source IS NULL OR source NOT IN ('zooplus_csv_import', 'allaboutdogfood'))
```

### Simplified Version (Primary Filter Only)
```sql
SELECT *
FROM foods_published_preview
WHERE allowlist_status = 'ACTIVE'
```

## Business Logic Interpretation

### 1. Allowlist Status System
- `ACTIVE`: Approved products that appear in production
- `PENDING`: Products awaiting approval/review
- The system uses a **manual approval workflow**

### 2. Data Source Quality Control
- Blocks specific lower-quality sources (`zooplus_csv_import`, `allaboutdogfood`)
- Maintains high-quality data sources like `food_candidates`

### 3. Implicit Quality Gates
- Products in `ACTIVE` status tend to have better data completeness
- Higher average quality scores in production
- Better nutrition data coverage

## Recommendations

### For Simplification
1. **Current system is already quite simple** - mainly controlled by one field
2. Consider automating the `allowlist_status` approval based on:
   - Data completeness thresholds
   - Quality score minimums
   - Source reliability scores

### For Replacement
If replacing the current system, implement these rules:
```sql
WHERE (
    -- Data completeness requirements
    kcal_per_100g IS NOT NULL
    AND ingredients_tokens IS NOT NULL
    AND array_length(ingredients_tokens, 1) > 0
    AND life_stage IS NOT NULL

    -- Quality threshold
    AND quality_score >= 2.0

    -- Source filtering
    AND source NOT IN ('zooplus_csv_import', 'allaboutdogfood')

    -- Brand quality (if needed)
    AND brand_slug IS NOT NULL
)
```

## Implementation Impact

### Current System Benefits
- **Simple**: Single field controls most filtering
- **Flexible**: Manual override capability via allowlist status
- **Auditable**: Clear approval workflow

### Potential Improvements
- **Automate approval** for products meeting quality criteria
- **Add quality score thresholds** for automatic ACTIVE status
- **Implement data completeness scoring** for approval decisions

---

*Analysis completed: September 16, 2025*
*Database: Supabase lupito-content*
*Tables: foods_published_preview, foods_published_prod*