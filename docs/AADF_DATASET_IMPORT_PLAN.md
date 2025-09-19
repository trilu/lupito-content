# AADF Dataset Import Plan
**Date:** September 15, 2025  
**Dataset:** `data/aadf/aadf-dataset-2.csv`  
**Target:** Import 972 new products to database with proper normalization

## Executive Summary

We have a new AADF dataset with 1,136 products. Analysis shows:
- **972 products (85.6%)** are truly NEW
- **164 products (14.4%)** already exist in database (fuzzy matches >85%)
- **99.9% have ingredients** 
- **70.2% have nutrition data**
- **99.8% have price data**
- **0% have images** (consistent with existing AADF products)

## Current State Analysis

### Existing Infrastructure
1. **SmartProductImporter** (`scripts/smart_product_importer.py`)
   - Handles variant detection and consolidation
   - Brand normalization with mappings
   - Generates consistent product keys
   - Prevents duplicates

2. **AADF Import Scripts** 
   - `import_aadf_data_fast.py` - Existing AADF importer with brand extraction
   - Brand patterns for URL-based extraction
   - Product name normalization

3. **Deduplication Logic**
   - Base name extraction (removes size/pack indicators)
   - URL normalization (removes variant parameters)
   - Fuzzy matching capabilities

### Dataset Structure
```csv
Columns:
- Product Name-0: Product name with "Review" suffix
- Ingredients-0: Raw ingredients text (99.9% coverage)
- Energy-0: Nutrition in kcal/100g format (70.2% coverage)
- Price per day-0: Daily feeding cost (99.8% coverage)
- Manufacturer-0: Brand name (19.1% coverage)
- Type of food-0: Product type (99.9% coverage)
- Dog ages-0: Age range (99.9% coverage)
- data-page-selector-href: AADF product URL (100% coverage)
- image: Empty (0% coverage)
```

## Import Pipeline Design

### Phase 1: Data Preparation

#### 1.1 Clean Product Names
```python
# Remove "Review" suffix
product_name = product_name.replace(' Review', '')

# Remove extra whitespace
product_name = ' '.join(product_name.split())
```

#### 1.2 Extract & Normalize Brands
Priority order for brand extraction:
1. Use "Manufacturer-0" if available (19.1% have this)
2. Extract from product name patterns
3. Extract from URL patterns
4. Default to "Unknown" if all fail

Brand normalization mappings:
- `royal canin` → Royal Canin
- `hills`, `hill's` → Hill's Science Plan
- `purina pro plan`, `purina-pro-plan` → Purina Pro Plan
- etc. (using existing mappings)

#### 1.3 Generate Product Keys
Format: `brand|product_name|form`
- Lowercase, alphanumeric only
- Replace spaces with underscores
- Maximum 50 chars for name portion

### Phase 2: Deduplication

#### 2.1 Exact Matching
- Clean and normalize product names
- Check for exact matches in database

#### 2.2 Fuzzy Matching (85% threshold)
- Use fuzzywuzzy library for similarity scoring
- Match against ALL existing products
- Flag potential duplicates for review

#### 2.3 Variant Detection
Identify products that are size/pack variants:
- Extract base product name (remove size/quantity)
- Group by base name + brand
- Consolidate data from variants

### Phase 3: Data Enrichment

#### 3.1 Parse Nutrition Data
```python
# Extract from "Energy-0" field
# Format: "400.5 kcal/100g"
if energy_field:
    match = re.search(r'(\d+\.?\d*)\s*kcal/100g', energy_field)
    if match:
        energy_kcal = float(match.group(1))
```

#### 3.2 Parse Price Data
```python
# Format: "£1.75" → 1.75
if price_field:
    price_numeric = float(price_field.replace('£', ''))
```

#### 3.3 Parse Age Range
```python
# Format: "From 18 months to 8 years"
# Extract min/max age in months
```

### Phase 4: Import Process

#### 4.1 Pre-Import Validation
1. Generate preview report:
   - List of new products to add
   - List of existing products to update
   - List of detected variants
   - Data quality warnings

2. Check for critical issues:
   - Missing required fields
   - Invalid data formats
   - Duplicate product keys

#### 4.2 Import Execution
Using SmartProductImporter with modifications:
1. Batch process in groups of 100
2. Track all statistics:
   - New products imported
   - Variants consolidated
   - Data updates performed
   - Errors encountered

3. Create audit log with:
   - Timestamp
   - Product key
   - Action taken
   - Data changes

#### 4.3 Post-Import Validation
1. Verify counts match expectations
2. Check data integrity
3. Generate summary report

### Phase 5: Quality Assurance

#### 5.1 Data Quality Checks
- [ ] All products have valid product keys
- [ ] Brand names are normalized
- [ ] No unintended duplicates created
- [ ] Ingredients properly stored
- [ ] Nutrition data correctly parsed
- [ ] URLs are valid and normalized

#### 5.2 Rollback Plan
If issues detected:
1. Keep backup of affected records
2. Log all changes with timestamps
3. Ability to revert using audit log

## Implementation Steps

### Step 1: Create Preparation Script
**File:** `scripts/prepare_aadf_import.py`
- Load and clean CSV data
- Apply all normalizations
- Generate preview report
- Save prepared data to `data/aadf/aadf_prepared.json`

### Step 2: Create Import Script  
**File:** `scripts/import_aadf_dataset_2.py`
- Use SmartProductImporter as base
- Add AADF-specific logic
- Implement batch processing
- Generate audit log

### Step 3: Execute Dry Run
- Run with `--dry-run` flag
- Review preview report
- Validate data quality
- Get approval before proceeding

### Step 4: Execute Import
- Run import in production
- Monitor progress
- Handle any errors
- Generate final report

## Expected Outcomes

### Metrics
- **New Products:** ~972
- **Updated Products:** ~164 (if missing data)
- **Total Database After:** ~9,898 products
- **Coverage Improvements:**
  - AADF products: 1,000 → 1,972
  - With ingredients: Maintain ~94%
  - With nutrition: Add ~700 products
  - With price data: Add ~1,100 products

### Benefits
1. **Expanded Coverage:** Nearly double AADF product count
2. **Rich Data:** Add nutrition and price information
3. **Better Deduplication:** Consistent product keys and variant handling
4. **Data Quality:** Normalized brands and clean product names

## Risk Mitigation

### Potential Issues & Solutions

1. **False Positive Duplicates**
   - Solution: Manual review of fuzzy matches 80-85%
   - Keep threshold at 85% for auto-matching

2. **Brand Extraction Failures**
   - Solution: Manual brand mapping table
   - Fallback to "Unknown" with flag for review

3. **Data Format Changes**
   - Solution: Defensive parsing with try/catch
   - Log all parsing failures for investigation

4. **Performance Impact**
   - Solution: Batch processing (100 records)
   - Off-peak import timing

## Success Criteria

- [ ] 95%+ of products successfully imported
- [ ] Zero unintended duplicates created
- [ ] All brand names properly normalized
- [ ] Nutrition data parsed for 70%+ of products
- [ ] Complete audit trail available
- [ ] No degradation of existing data

## Timeline

1. **Preparation Phase:** 1 hour
   - Create scripts
   - Test on sample data

2. **Validation Phase:** 30 minutes
   - Run dry run
   - Review reports
   - Get approval

3. **Import Phase:** 1 hour
   - Execute import
   - Monitor progress
   - Handle issues

4. **Verification Phase:** 30 minutes
   - Validate results
   - Generate reports
   - Document outcomes

**Total Time:** ~3 hours

## Appendix: Sample Data Transformations

### Before (CSV):
```
Product Name-0: "Royal Canin X-Small Adult Review"
Manufacturer-0: ""
Ingredients-0: "Rice, Dehydrated Poultry Meat, Maize..."
Energy-0: "400.5 kcal/100g"
Price per day-0: "£1.75"
```

### After (Database):
```json
{
  "product_key": "royalcanin|royal_canin_x_small_adult|dry",
  "brand": "Royal Canin",
  "product_name": "Royal Canin X-Small Adult",
  "ingredients_raw": "Rice, Dehydrated Poultry Meat, Maize...",
  "energy_kcal": 400.5,
  "price_per_day": 1.75,
  "product_url": "https://www.allaboutdogfood.co.uk/dog-food-reviews/0387/royal-canin-x-small-adult",
  "source": "allaboutdogfood"
}
```

---
*Document created: September 15, 2025*