# Zooplus Data Import & Enrichment Plan

## Executive Summary
Analysis of two Zooplus CSV data dumps revealed 5,668 total products, but after deduplication, only 2,144 unique base products. Of these, approximately 1,365 are truly new to our database, while 462 existing products can be enriched with scraped data.

## Data Analysis Results

### Raw Data Statistics
- **File 1** (zooplus-com-2025-09-12.csv): 2,322 products (mostly wet food)
- **File 2** (zooplus-com-2025-09-12-2.csv): 3,374 products (mostly dry food)
- **Total raw products**: 5,668
- **Products with ingredient previews**: 1,634 (28.8%)
- **Products with nutrition data**: 0 (would require scraping)

### Variant Analysis
- **Unique base products**: 2,144 (after removing size/weight variants)
- **Removed variants**: 3,524 (62% were duplicates!)
- **Products with multiple variants**: 1,663
  - Example: "Wolf of Wilderness Economy Pack" has 29 size variants

### Database Comparison
- **Current DB size**: 8,190 products
- **Existing Zooplus products in DB**: 2,774
- **With ingredients**: 1,416 (51% of Zooplus products)
- **Products matched by URL**: 2,057
- **Truly new unique products**: 1,365
- **Existing products needing scraping**: 462

## Implementation Plan

### Phase 1: Database Staging Setup

#### 1.1 Create Staging Table
```sql
CREATE TABLE IF NOT EXISTS zooplus_staging (
    id SERIAL PRIMARY KEY,
    product_key TEXT NOT NULL,
    brand TEXT,
    product_name TEXT,
    product_url TEXT UNIQUE,
    base_url TEXT,  -- URL without variant parameters
    food_type TEXT CHECK (food_type IN ('wet', 'dry', 'unknown')),
    has_ingredients BOOLEAN DEFAULT FALSE,
    ingredients_preview TEXT,
    source_file TEXT,
    is_variant BOOLEAN DEFAULT FALSE,
    variant_of_url TEXT,  -- Reference to base product
    created_at TIMESTAMP DEFAULT NOW(),
    processed BOOLEAN DEFAULT FALSE,
    matched_product_key TEXT,
    match_type TEXT CHECK (match_type IN ('exact_url', 'brand_name', 'fuzzy', 'new')),
    match_confidence DECIMAL(3,2)
);

-- Indexes for performance
CREATE INDEX idx_zooplus_staging_base_url ON zooplus_staging(base_url);
CREATE INDEX idx_zooplus_staging_brand ON zooplus_staging(brand);
CREATE INDEX idx_zooplus_staging_product_key ON zooplus_staging(product_key);
CREATE INDEX idx_zooplus_staging_processed ON zooplus_staging(processed);
CREATE INDEX idx_zooplus_staging_is_variant ON zooplus_staging(is_variant);
```

#### 1.2 Load Staging Data Script
```python
# scripts/load_zooplus_staging.py
import pandas as pd
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

def load_staging_data():
    """Load deduplicated Zooplus data into staging table"""
    
    # Load deduplicated data
    df = pd.read_csv('data/zooplus_deduped.csv')
    
    # Connect to Supabase
    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_KEY")
    )
    
    # Prepare data for insertion
    records = df.to_dict('records')
    
    # Insert in batches of 100
    batch_size = 100
    for i in range(0, len(records), batch_size):
        batch = records[i:i+batch_size]
        supabase.table('zooplus_staging').insert(batch).execute()
        print(f"Inserted batch {i//batch_size + 1}/{len(records)//batch_size + 1}")
    
    print(f"✅ Loaded {len(records)} products into staging")
```

### Phase 2: Data Matching & Deduplication

#### 2.1 Matching Algorithm
```python
# scripts/match_staging_products.py

def match_products():
    """Match staging products with existing database"""
    
    # 1. Exact URL matching (normalized)
    # 2. Brand + normalized product name matching
    # 3. Fuzzy matching for similar products
    # 4. Mark remaining as new products
    
    matching_stats = {
        'exact_url': 0,
        'brand_name': 0,
        'fuzzy': 0,
        'new': 0
    }
    
    # Update staging table with matches
    # Set matched_product_key, match_type, match_confidence
```

#### 2.2 Brand Normalization Mappings
```python
BRAND_NORMALIZATION = {
    "hill's": "Hill's Science Plan",
    "hill's science plan": "Hill's Science Plan",
    "hill's prescription diet": "Hill's Prescription Diet",
    "royal canin": "Royal Canin",
    "royal canin veterinary": "Royal Canin Veterinary Diet",
    "royal canin vet diet": "Royal Canin Veterinary Diet",
    "pro plan": "Pro Plan",
    "purina pro plan": "Pro Plan",
    "mac's": "MAC's",
    "dogs'n tiger": "Dogs'n Tiger",
    "wolf of wilderness": "Wolf of Wilderness",
    "concept for life": "Concept for Life",
    "advance vet diets": "Advance Veterinary Diets"
}
```

### Phase 3: Import New Products

#### 3.1 Import Criteria
- Only import products where `match_type = 'new'`
- Skip all variants (`is_variant = FALSE`)
- Total expected: ~1,365 new products

#### 3.2 Import Process
```python
# scripts/import_new_zooplus_products.py

def import_new_products():
    """Import only truly new, non-variant products"""
    
    # Query staging for new products
    new_products = supabase.table('zooplus_staging').select('*')\
        .eq('match_type', 'new')\
        .eq('is_variant', False)\
        .execute()
    
    # Transform to foods_canonical format
    for product in new_products.data:
        canonical_product = {
            'product_key': product['product_key'],
            'brand': product['brand'],
            'product_name': product['product_name'],
            'product_url': product['product_url'],
            'ingredients_raw': product['ingredients_preview'] if product['has_ingredients'] else None,
            'source': 'zooplus_import',
            'last_updated': datetime.now()
        }
        
        # Insert into foods_canonical
        supabase.table('foods_canonical').insert(canonical_product).execute()
```

### Phase 4: Enrichment & Scraping

#### 4.1 Priority Queue
1. **Tier 1**: 462 existing products needing ingredients
   - Top brands: Royal Canin (32), Farmina (30), Schesir (18)
   
2. **Tier 2**: ~873 new products without ingredient data
   - Focus on top brands first

3. **Tier 3**: Products with partial ingredient previews
   - Can be enriched with full scraping

#### 4.2 Scraping Implementation
```python
# scripts/scrape_zooplus_queue.py

def process_scraping_queue():
    """Process products needing scraping"""
    
    # Load queue
    tier1 = pd.read_csv('data/zooplus_need_scraping.csv')
    tier2 = get_new_products_without_ingredients()
    
    # Combine and prioritize
    full_queue = pd.concat([tier1, tier2])
    
    # Use existing orchestrated scraper
    # Rate limit: 15 seconds between requests
    # Save to GCS for processing
```

## Expected Outcomes

### Database Impact
- **Current size**: 8,190 products
- **After import**: 9,555 products (+16.7%)
- **Not 13,735** as originally thought (due to variants)

### Coverage Impact
- **Current coverage**: 39.1% (3,202/8,190)
- **After import**: 33.5% (3,202/9,555) - drops due to new products
- **After Tier 1 scraping**: 38.3% (3,664/9,555)
- **Target 95%**: Need ~5,900 more products with ingredients

### Time Estimates
- **Import process**: ~30 minutes
- **Tier 1 scraping** (462 products): ~2 hours
- **Tier 2 scraping** (873 products): ~3.5 hours
- **Total initial enrichment**: ~6 hours

## File Artifacts

### Generated Analysis Files
- `data/zooplus_staging_prepared.csv` - All 5,668 products normalized
- `data/zooplus_deduped.csv` - 2,144 unique products (no variants)
- `data/zooplus_new_products_deduped.csv` - 1,365 truly new products
- `data/zooplus_need_scraping.csv` - 462 existing products to scrape
- `data/zooplus_can_update.csv` - 26 products with ingredient previews

### Scripts Created
- `scripts/analyze_zooplus_dumps.py` - Initial analysis
- `scripts/prepare_zooplus_staging_sql.py` - Generate staging SQL
- `scripts/deduplicate_variants.py` - Remove product variants
- `scripts/compare_with_existing_db.py` - Database comparison
- `scripts/analyze_zooplus_duplicates.py` - Duplicate analysis

## Quality Checks

### Pre-Import Validation
1. Verify no variants are being imported
2. Check brand normalization is applied
3. Validate product keys are unique
4. Ensure URLs are properly formatted

### Post-Import Validation
1. Check for duplicate product_keys
2. Verify product count matches expected
3. Validate no size variants were imported
4. Audit brand distribution

## Risk Mitigation

### Potential Issues
1. **Duplicate products**: Mitigated by base URL matching
2. **Brand inconsistency**: Addressed with normalization map
3. **Variant explosion**: Prevented by deduplication
4. **Data quality**: Ingredient previews may be incomplete

### Rollback Plan
1. All imports tracked in staging table
2. Products tagged with `source='zooplus_import'`
3. Can identify and remove if needed
4. Backup database before major import

## Next Steps

1. **Immediate Actions**:
   - [ ] Create staging table in database
   - [ ] Load deduplicated data (2,144 products)
   - [ ] Run matching algorithm
   - [ ] Review matching results

2. **Import Phase**:
   - [ ] Import 1,365 new products
   - [ ] Verify no duplicates created
   - [ ] Update statistics

3. **Enrichment Phase**:
   - [ ] Queue 462 products for scraping
   - [ ] Start orchestrated scraping
   - [ ] Monitor progress

4. **Long-term**:
   - [ ] Schedule regular Zooplus data updates
   - [ ] Automate variant detection
   - [ ] Improve matching algorithm

## Success Metrics

- ✅ No variant duplicates in database
- ✅ Clean brand normalization
- ✅ 95%+ matching accuracy
- ✅ <5% duplicate rate
- ✅ Coverage improvement of +5% after scraping

## Appendix: SQL Queries

### Check for variants in staging
```sql
SELECT base_url, COUNT(*) as variant_count
FROM zooplus_staging
GROUP BY base_url
HAVING COUNT(*) > 1
ORDER BY variant_count DESC;
```

### Find unmatched products
```sql
SELECT COUNT(*) as new_products
FROM zooplus_staging
WHERE match_type = 'new'
AND is_variant = FALSE;
```

### Audit brand distribution
```sql
SELECT brand, COUNT(*) as product_count
FROM zooplus_staging
WHERE is_variant = FALSE
GROUP BY brand
ORDER BY product_count DESC
LIMIT 20;
```
