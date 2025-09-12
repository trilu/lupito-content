# Comprehensive Zooplus Import Plan with ACCURATE Metrics

**Date:** 2025-09-12  
**Author:** Claude  
**Status:** Ready for Implementation

## Current Database Status (CORRECTED)

### Actual Nutrition Coverage
- **Total Products**: 6,336
- **Nutrition Coverage Reality**:
  - ✅ **90.8% have PROTEIN data** (5,755/6,336) - This is what was mistakenly called "90% nutrition"
  - ✅ 90.4% have basic nutrition (protein + fat)
  - ⚠️ **Only 17.1% have complete standard nutrition** (protein + fat + fiber)
  - ❌ **Only 12.4% have ALL 5 macros** (protein, fat, fiber, ash, moisture)
  - 70.1% have caloric data
- **Ingredients**: Only 30.4% coverage (1,925/6,336)
- **UK/AADF**: 1,235 products (88.2% have protein, 100% have ingredients)

### Key Finding
The database has good PROTEIN coverage (90.8%) but poor COMPLETE nutrition (12.4%). Most products are missing fiber, ash, and moisture data.

## Previous Zooplus Work Analysis

### Existing Assets
- **Already scraped**: 2,079 products in `data/zooplus/Zooplus.json`
- **Previously imported**: Only 177 (8.5% success due to duplicates)
- **Data quality**: 68% have protein, 89% have fat, 85% have fiber
- **Brand overlap**: 67.7% of Zooplus products already in DB

### Missing Brands (High Priority)
32 brands with 960 products opportunity:
- Hill's Prescription Diet (111 products)
- Purizon (101 products)
- Josera (57 products)
- Concept for Life (107 products)
- Plus 28 other brands

## Implementation Plan

### Phase 1: Import Existing Zooplus JSON Data (Day 1-2)

#### 1.1 Process Existing Data
- Load 2,079 products from `data/zooplus/Zooplus.json`
- Apply brand normalization (extract from breadcrumbs[2], not "zooplus logo")
- Extract nutrition from attributes field
- Handle pack size variants properly

#### 1.2 Expected Outcomes
- ~900 new products (after deduplication)
- Significantly improve fiber coverage (Zooplus has 85% fiber data)
- Add missing brands to database

### Phase 2: Create Staging Infrastructure (Day 2)

#### 2.1 Staging Table
```sql
CREATE TABLE retailer_staging_zooplus (
    -- Similar structure to foods_canonical
    -- Add source tracking fields
    -- Enable safe testing before production
);
```

#### 2.2 Matching Strategy
- Match by normalized brand + product name
- Update only missing fields (preserve manufacturer data)
- Create variants for different pack sizes
- Track import metrics

### Phase 3: ScrapingBee Deep Scraping for Ingredients (Day 3-5)

#### 3.1 Priority Targets
Focus on products missing ingredients (4,411 products need ingredients):
1. Hill's Prescription Diet (111 products)
2. Purizon (101 products)
3. Josera (57 products)
4. Concept for Life (107 products)

#### 3.2 ScrapingBee Configuration
```python
params = {
    'api_key': os.getenv('SCRAPING_BEE'),
    'url': product_url,
    'render_js': 'true',        # For AJAX/JavaScript content
    'premium_proxy': 'true',     # Avoid blocking
    'country_code': 'gb',        # UK proxy
    'wait': 2000,                # Wait for content to load
    'extract_rules': {           # CSS selectors for data
        'ingredients': '.ingredients-section',
        'nutrition': '.nutrition-table',
        'feeding': '.feeding-guidelines'
    }
}
```

#### 3.3 Data Points to Extract
- Full ingredients list (parse from product descriptions)
- Complete nutritional analysis table
- Feeding guidelines
- Product variants and sizes
- Special dietary indicators (grain-free, hypoallergenic, etc.)

### Phase 4: Data Enhancement Pipeline (Day 5-7)

#### 4.1 Parse Ingredients
- Extract from "Composition:" sections in descriptions
- Tokenize ingredients for database storage
- Mark ingredients_source as 'site'

#### 4.2 Complete Nutrition Gaps
Target products with partial nutrition:
- 4,669 products need fiber data
- 4,673 products need ash data  
- 4,964 products need moisture data

### Phase 5: Integration & Quality Control (Day 7-8)

#### 5.1 Import to Production
- Batch processing with error handling
- Preserve data hierarchy (manufacturer > site > retailer)
- Create rollback files for safety
- Track all changes

#### 5.2 Metrics to Track
- Products added vs updated
- Nutrition completeness improvement
- Ingredients coverage increase
- Brand coverage expansion

## Expected Final Outcomes

### Coverage Improvements
| Metric | Current | Expected | Improvement |
|--------|---------|----------|-------------|
| Total Products | 6,336 | 7,200+ | +900-1,000 |
| Fiber Coverage | 17.1% | ~35% | +17.9% |
| Complete Nutrition | 12.4% | ~25% | +12.6% |
| Ingredients | 30.4% | ~45% | +14.6% |
| Brands | 470 | 500+ | +32 brands |

### Data Quality Improvements
- Fill nutrition gaps for 4,600+ products
- Add ingredients for 1,000+ products
- Complete brand portfolio for Hill's, Purizon, Josera
- Establish reusable Zooplus scraping pipeline

## Technical Implementation Details

### Scripts to Create
1. `import_zooplus_json.py` - Process existing JSON data
2. `create_zooplus_staging.py` - Set up staging infrastructure
3. `scrape_zooplus_deep.py` - ScrapingBee integration for deep scraping
4. `parse_zooplus_ingredients.py` - Extract and parse ingredients
5. `merge_zooplus_data.py` - Final integration to production

### Database Considerations
- Everything currently goes to `foods_canonical` (no staging)
- Need to create staging table for safer imports
- Maintain data source hierarchy
- Track all changes for audit trail

## Risk Mitigation
1. **Duplicates**: Use variant keys for different pack sizes
2. **Data conflicts**: Preserve manufacturer data, only fill gaps
3. **Scraping limits**: ScrapingBee has 100 req/hour limit, plan accordingly
4. **Rollback capability**: Create backup before each major import

## Success Criteria
- ✅ Import 900+ new products from Zooplus
- ✅ Achieve 35%+ fiber coverage (from 17.1%)
- ✅ Achieve 45%+ ingredients coverage (from 30.4%)
- ✅ Add all 32 missing brands
- ✅ Establish repeatable Zooplus import pipeline

## Timeline
- **Week 1**: Import existing JSON, create staging
- **Week 2**: ScrapingBee setup and deep scraping
- **Week 3**: Parse and integrate enhanced data
- **Week 4**: Quality control and production import

## Notes
- The "90.8% nutrition coverage" claim was misleading - it's only protein coverage
- Real complete nutrition is only 12.4% - this is the key gap to address
- Zooplus data is particularly valuable for fiber, ash, and moisture data
- ScrapingBee is essential for ingredients extraction due to JavaScript rendering