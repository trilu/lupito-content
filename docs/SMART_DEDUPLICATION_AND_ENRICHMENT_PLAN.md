# Smart Deduplication & Data Enrichment Plan

**Date:** 2025-09-12  
**Version:** 1.0  
**Status:** Ready for Implementation  

## 1. Current State Analysis

### Database Overview
- **Total Products:** 5,223
- **Unique Brands:** 381
- **Data Sources:** 3 (food_candidates, food_candidates_sc, food_brands)

### Data Quality Issues

#### 1.1 Missing Nutritional Data
- **0% products** have complete ingredients lists
- **Limited enrichment**: Some products have protein%, fat%, kcal but missing ingredients
- **97% products** have images (only positive metric)

#### 1.2 Duplicate Products
- **167 product groups** contain duplicates
- **172 total duplicate products** (products appearing 2+ times)
- **Example:** Multiple "Aatu - Free Run Chicken" entries from same source

#### 1.3 Suspicious/Invalid Products
- **19 products** with suspicious names
- **Examples:**
  - Brand: "Bozita", Name: "Bozita" (just brand name)
  - Brand: "Almo Nature", Name: "HFC" (incomplete)
  - Brand: "Gentle", Name: "Fish" (too generic)

#### 1.4 Partial Enrichment Status
Brands previously scraped but incomplete:
- **Bozita:** Has protein%, URLs, but missing ingredients
- **Belcando:** Has protein%, URLs, but missing ingredients  
- **Briantos:** Has ingredients + full data (SUCCESS)
- **Burns:** Has ingredients + full data (SUCCESS)
- **Brit:** Has protein%, URLs, but missing ingredients

## 2. Infrastructure Assessment

### 2.1 Existing Assets
✅ **ScrapingBee Integration**
- API configured with credits
- Handles JavaScript-heavy sites
- Country-specific proxies

✅ **Manufacturer Profiles** (12 configured)
- alpha.yaml, barking.yaml, belcando.yaml, bozita.yaml
- briantos.yaml, brit.yaml, burns.yaml, canagan.yaml
- cotswold.yaml, forthglade.yaml

✅ **Harvesting Scripts**
- `scrapingbee_harvester.py` - Main harvester with JS rendering
- `run_manufacturer_harvest.py` - Orchestrator
- `parallel_multi_brand_harvester.py` - Parallel execution

✅ **Data Pipeline**
- GCS storage for raw data
- Staging tables in Supabase
- Fuzzy matching functions

### 2.2 Previous Work Completed
- 195 brand websites discovered (69.9% coverage)
- 167 brands approved for crawling (robots.txt compliant)
- Infrastructure tested with 3 brands

## 3. Implementation Plan

### Phase 1: Smart Deduplication (Days 1-3)

#### 1.1 Duplicate Detection & Resolution
```python
# Deduplication strategy
1. Group products by: brand_slug + normalized_name + form
2. For each duplicate group:
   - Score each product by data completeness:
     * Has ingredients: +40 points
     * Has all macros: +30 points  
     * Has URL: +20 points
     * Has image: +10 points
   - Keep highest scoring product
   - Merge unique data from duplicates into winner
   - Log all merges for audit trail
```

#### 1.2 Suspicious Product Validation
```python
# Validation process
1. Extract all products where name == brand or len(name) < 5
2. For each suspicious product:
   - Search manufacturer website
   - If product exists: Update with correct name
   - If doesn't exist: Mark for deletion
   - Create audit log
```

### Phase 2: Complete Previous Enrichment (Days 3-5)

#### 2.1 Fix Incomplete Harvests
Priority brands with partial data:
1. **Bozita** - Re-harvest ingredients
2. **Belcando** - Re-harvest ingredients  
3. **Brit** - Re-harvest ingredients

#### 2.2 Data Mapping Fixes
- Ensure `ingredients_raw` field properly populated
- Map `protein_percent`, `fat_percent` correctly
- Verify `product_url` links are valid

### Phase 3: Scale Manufacturer Enrichment (Days 5-15)

#### 3.1 Priority Matrix

| Priority | Brand | Products | Current State | Action |
|----------|-------|----------|---------------|--------|
| P1 | Royal Canin | 253 | No enrichment | Full harvest |
| P1 | Wainwright's | 97 | No enrichment | Full harvest |
| P1 | Natures Menu | 93 | No enrichment | Full harvest |
| P1 | Eukanuba | 85 | Partial | Complete harvest |
| P1 | Hill's Science Plan | 78 | No enrichment | Full harvest |
| P2 | Wolf Of Wilderness | 72 | No enrichment | Full harvest |
| P2 | James Wellbeloved | 67 | No enrichment | Full harvest |
| P2 | Happy Dog | 64 | No enrichment | Full harvest |
| P2 | Lukullus | 59 | No enrichment | Full harvest |
| P2 | Pets at Home | 58 | No enrichment | Full harvest |

#### 3.2 Parallel Processing Strategy
```yaml
Batch 1 (Simple Sites, Direct Access):
  - Royal Canin
  - Hill's Science Plan
  - Eukanuba
  - James Wellbeloved
  - Purina

Batch 2 (JavaScript Heavy, Need ScrapingBee):
  - Bozita
  - Belcando  
  - Wolf of Wilderness
  - Happy Dog
  - Lukullus

Batch 3 (Retailer Sites, Complex):
  - Pets at Home
  - Wainwright's (Pets at Home brand)
  - ASDA, Tesco (private label)
```

#### 3.3 Data Collection Targets
For each product, collect:
- **Ingredients** (raw text + tokenized list)
- **Nutritional Analysis**
  - Protein %
  - Fat %
  - Fiber %
  - Ash %
  - Moisture %
- **Caloric Content** (kcal/100g)
- **Product URL** (canonical from manufacturer)
- **Price** (if available)
- **Feeding Guidelines**
- **Product Description**

### Phase 4: Add Missing Products (Days 15-20)

#### 4.1 Gap Analysis Process
```python
1. For each brand with website:
   - Crawl full product catalog
   - Compare with foods_canonical
   - Identify products on website but not in DB
   - Validate these are dog food products
   
2. Product Addition:
   - Create new entries with full data
   - Apply deduplication check before insert
   - Maintain audit log of additions
```

## 4. Technical Implementation Details

### 4.1 Deduplication Script Structure
```python
# deduplicate_products.py
class ProductDeduplicator:
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.merge_log = []
    
    def find_duplicates(self):
        # Group by normalized key
        # Return duplicate groups
    
    def score_product(self, product):
        # Score by data completeness
        # Return score
    
    def merge_products(self, products):
        # Keep best product
        # Merge unique data
        # Return merged product
    
    def execute(self):
        # Run full deduplication
        # Update database
        # Generate report
```

### 4.2 Enrichment Pipeline
```python
# enrich_manufacturer_data.py
class ManufacturerEnricher:
    def __init__(self, brand, profile):
        self.brand = brand
        self.profile = profile
        self.harvester = ScrapingBeeHarvester(brand, profile)
    
    def harvest_products(self):
        # Discover product URLs
        # Harvest each product
        # Store in staging
    
    def match_products(self):
        # Fuzzy match with canonical
        # Handle ambiguous matches
        # Return matches
    
    def update_canonical(self):
        # Update foods_canonical
        # Maintain audit trail
        # Generate report
```

### 4.3 Parallel Execution Framework
```python
# parallel_enrichment.py
from concurrent.futures import ThreadPoolExecutor
import time

def enrich_brand(brand_config):
    enricher = ManufacturerEnricher(**brand_config)
    return enricher.execute()

def run_parallel_enrichment(brands, max_workers=5):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for brand in brands:
            future = executor.submit(enrich_brand, brand)
            futures.append(future)
            time.sleep(2)  # Stagger starts
        
        results = [f.result() for f in futures]
    return results
```

## 5. Quality Assurance

### 5.1 Data Validation Rules
- **Ingredients:** Must be non-empty string, >20 characters
- **Protein %:** Must be 15-45% range for dog food
- **Fat %:** Must be 5-25% range  
- **Moisture %:** Must be <12% for dry, >60% for wet
- **URLs:** Must return 200 status code
- **Product names:** Must not equal brand name

### 5.2 Success Metrics

| Metric | Current | Target | Priority |
|--------|---------|--------|----------|
| Products with ingredients | 0% | 80% | P1 |
| Products with full macros | <5% | 90% | P1 |
| Products with valid URLs | <10% | 95% | P2 |
| Duplicate products | 172 | 0 | P1 |
| Suspicious products validated | 0/19 | 19/19 | P1 |
| Top 20 brands enriched | 2/20 | 20/20 | P1 |

### 5.3 Monitoring & Reporting
- Daily progress reports
- API credit usage tracking
- Error logs per brand
- Data quality dashboards
- Rollback capability for all changes

## 6. Risk Mitigation

### 6.1 Technical Risks
| Risk | Mitigation |
|------|------------|
| ScrapingBee credits exhausted | Monitor usage, batch priority brands |
| Website structure changes | Use multiple selectors, fallback strategies |
| Rate limiting | Implement exponential backoff, respect robots.txt |
| Data quality issues | Validation rules, manual QA sampling |

### 6.2 Data Risks
| Risk | Mitigation |
|------|------------|
| Over-deduplication | Conservative matching, manual review |
| Incorrect product matching | Fuzzy match threshold tuning, brand constraints |
| Missing critical products | Gap analysis, manufacturer catalog comparison |

## 7. Timeline

### Week 1
- Days 1-3: Smart deduplication
- Days 3-5: Complete previous enrichments

### Week 2  
- Days 6-10: Enrich top 10 priority brands
- Days 11-12: Quality validation

### Week 3
- Days 13-17: Enrich next 10 brands
- Days 18-20: Add missing products

### Week 4
- Days 21-22: Final validation
- Days 23-24: Documentation and handover

## 8. Cost Estimates

### ScrapingBee Credits
- ~100 pages per brand average
- 20 brands × 100 pages = 2,000 API calls
- With JS rendering: ~10,000 credits
- Cost: ~$100

### Time Investment
- Development: 40 hours
- Execution: 20 hours
- QA & Validation: 10 hours
- Total: 70 hours

## 9. Next Steps

1. **Immediate Actions**
   - Create deduplication script
   - Fix Bozita/Belcando data mapping
   - Prepare Royal Canin profile

2. **This Week**
   - Complete Phase 1 & 2
   - Start Phase 3 with top 5 brands

3. **Success Criteria**
   - Zero duplicates
   - 80%+ ingredients coverage
   - All suspicious products resolved

## Appendix A: Existing Code References

### Key Scripts
- `/scrapingbee_harvester.py` - Main harvesting logic
- `/run_manufacturer_harvest.py` - Orchestration
- `/profiles/manufacturers/*.yaml` - Brand configurations

### Database Tables
- `foods_canonical` - Main product table
- `manufacturer_harvest_staging` - Temporary enrichment data
- `manufacturer_matches` - View for matching

### Previous Reports
- `/docs/MANUFACTURER-ENRICHMENT-REPORT.md`
- `/reports/PRODUCT_NAME_CLEANUP_PROGRESS.md`
- `/reports/COMPREHENSIVE_NORMALIZATION_SUMMARY.md`