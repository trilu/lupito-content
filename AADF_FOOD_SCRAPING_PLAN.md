# AllAboutDogFood.co.uk Food Directory Scraping Documentation

## Project Overview
This document outlines the comprehensive plan for scraping dog food product data from AllAboutDogFood.co.uk (AADF), a highly respected UK-based dog food review and information website.

**Generated**: 2025-01-09  
**Author**: Claude Code  
**Status**: Planning Phase

## 1. Background & Context

### 1.1 Current Database State
- **Total Foods**: 3,917 products
- **Primary Source**: petfoodexpert.com (~98% of data)
- **AADF Coverage**: 0 entries (completely missing)
- **Database Tables**: 
  - `food_candidates` (primary table)
  - `foods_published` (unified view)
  - `food_raw` (HTML/JSON storage)

### 1.2 Why AADF?
- **Comprehensive Reviews**: One of the most trusted dog food review sites in Europe
- **Detailed Nutrition Data**: Complete ingredient lists and nutritional analysis
- **UK/EU Market Focus**: Complements our existing data which lacks EU coverage
- **Quality Ratings**: Unique scoring system for food quality
- **Independent Source**: Not affiliated with manufacturers

### 1.3 Technical Challenges
- **Site Protection**: Returns 403 errors on direct access
- **JavaScript-Heavy**: Dynamic content loading requires browser rendering
- **Complex Structure**: Multi-level navigation and filtering
- **Solution**: ScrapingBee API with JavaScript rendering

## 2. Site Analysis

### 2.1 Target URL
```
https://www.allaboutdogfood.co.uk/the-dog-food-directory
```

### 2.2 Expected Structure
```
Directory Page
├── Filter Options
│   ├── Brand Filter
│   ├── Type (Dry/Wet/Raw)
│   ├── Life Stage
│   └── Special Diets
├── Product Listings
│   ├── Product Card
│   │   ├── Brand Name
│   │   ├── Product Name
│   │   ├── Rating Score
│   │   ├── Price Range
│   │   └── Product URL
│   └── Pagination/Load More
└── Individual Product Pages
    ├── Detailed Info
    ├── Ingredients List
    ├── Nutrition Table
    ├── Feeding Guide
    └── User Reviews
```

### 2.3 Data Points to Extract

#### From Directory Page:
- Product URLs
- Brand names
- Product names
- Overall ratings
- Price indicators

#### From Product Pages:
- **Brand**: Manufacturer name
- **Product Name**: Full product name
- **Form**: dry/wet/raw/freeze-dried
- **Life Stage**: puppy/adult/senior/all
- **Ingredients**: Full ingredient list (critical for allergies)
- **Nutrition Data**:
  - Protein %
  - Fat %
  - Fiber %
  - Ash %
  - Moisture %
  - Carbohydrates % (calculated)
  - kcal/100g (if available)
- **Price**: Per kg pricing (if available)
- **Packaging Sizes**: Available package options
- **Special Features**: Grain-free, hypoallergenic, etc.
- **AADF Rating**: Their proprietary quality score
- **Image URL**: Product image

## 3. Database Schema Mapping

### 3.1 Target Table: `food_candidates`
```sql
-- Mapping from AADF to food_candidates
{
    'id': generate_uuid(),
    'source_domain': 'allaboutdogfood.co.uk',
    'source_url': product_url,
    'brand': extracted_brand,
    'product_name': extracted_name,
    'form': normalize_form(extracted_type),  -- dry/wet/raw
    'life_stage': normalize_life_stage(extracted_stage),  -- puppy/adult/senior/all
    'kcal_per_100g': extracted_kcal or calculate_from_nutrition(),
    'protein_percent': extracted_protein,
    'fat_percent': extracted_fat,
    'fiber_percent': extracted_fiber,
    'ash_percent': extracted_ash,
    'moisture_percent': extracted_moisture,
    'ingredients_raw': full_ingredients_text,
    'ingredients_tokens': tokenize_ingredients(ingredients_raw),
    'contains_chicken': check_chicken_presence(ingredients_tokens),
    'pack_sizes': extracted_sizes,
    'price_eur': convert_to_eur(extracted_price),
    'available_countries': ['UK', 'EU'],  -- AADF is UK/EU focused
    'image_url': extracted_image,
    'fingerprint': generate_fingerprint(brand, name, form),
    'first_seen_at': now(),
    'last_seen_at': now()
}
```

### 3.2 Normalization Functions
```python
# Form normalization
FORM_MAPPING = {
    'dry': ['dry', 'kibble', 'biscuit'],
    'wet': ['wet', 'can', 'pouch', 'tray'],
    'raw': ['raw', 'frozen', 'fresh'],
    'freeze_dried': ['freeze-dried', 'freeze dried', 'dehydrated']
}

# Life stage normalization
LIFE_STAGE_MAPPING = {
    'puppy': ['puppy', 'junior', 'growth'],
    'adult': ['adult', 'maintenance'],
    'senior': ['senior', 'mature', 'older'],
    'all': ['all', 'any', 'all life stages']
}

# Chicken detection keywords
CHICKEN_KEYWORDS = [
    'chicken', 'poultry', 'fowl', 'turkey', 'duck', 
    'chicken meal', 'chicken fat', 'poultry meal'
]
```

## 4. Implementation Plan

### 4.1 Phase 1: Discovery & URL Collection
**Duration**: 30-60 minutes  
**ScrapingBee Credits**: ~10-20

1. **Access Directory Page**
   ```python
   # Use ScrapingBee to access protected page
   response = scrapingbee_client.get(
       url='https://www.allaboutdogfood.co.uk/the-dog-food-directory',
       params={
           'api_key': SCRAPINGBEE_API_KEY,
           'render_js': True,
           'wait': 3000,  # Wait for JS to load
           'premium_proxy': True  # Use premium proxy for 403 bypass
       }
   )
   ```

2. **Handle Pagination**
   - Detect pagination method (pages/infinite scroll)
   - Extract total product count
   - Iterate through all pages/scroll positions

3. **Extract Product URLs**
   - Save to `aadf_product_urls.txt`
   - Format: `product_name|brand|url`
   - Estimate: 500-1500 products

### 4.2 Phase 2: Scraper Development
**Duration**: 2-3 hours

1. **Create `jobs/aadf_food_scraper.py`**
   - Adapt from existing universal scraper pattern
   - Force ScrapingBee for all requests
   - Implement robust error handling
   - Add progress tracking and reporting

2. **Key Components**:
   ```python
   class AADFFoodScraper:
       def __init__(self):
           self.scrapingbee_api_key = os.getenv('SCRAPING_BEE')
           self.supabase = create_supabase_client()
           self.total_credits_used = 0
           
       def scrape_product(self, url):
           # 1. Fetch page with ScrapingBee
           # 2. Parse with BeautifulSoup
           # 3. Extract all data points
           # 4. Normalize and validate
           # 5. Return structured data
           
       def save_to_database(self, product_data):
           # 1. Check for duplicates
           # 2. Insert or update
           # 3. Store raw HTML in GCS
   ```

### 4.3 Phase 3: Deduplication Strategy
**Duration**: 1 hour

1. **Duplicate Detection**
   ```python
   def check_duplicate(brand, name, form):
       # Generate fingerprint
       fingerprint = f"{slugify(brand)}|{slugify(name)}|{form}"
       
       # Check existing database
       existing = supabase.table('food_candidates').select('id').eq('fingerprint', fingerprint).execute()
       
       return len(existing.data) > 0
   ```

2. **Merge Strategy**
   - Keep existing nutrition data if complete
   - Add AADF-specific data (ratings, reviews)
   - Update pricing if more recent
   - Preserve best image URL

### 4.4 Phase 4: Execution
**Duration**: 4-6 hours  
**ScrapingBee Credits**: 2,500-5,000

1. **Batch Processing**
   ```python
   BATCH_SIZE = 50
   RATE_LIMIT = 2  # requests per second
   
   for batch in chunks(urls, BATCH_SIZE):
       for url in batch:
           try:
               data = scrape_product(url)
               save_to_database(data)
               time.sleep(1/RATE_LIMIT)
           except Exception as e:
               log_error(url, e)
               failed_urls.append(url)
   ```

2. **Progress Tracking**
   - Real-time console output
   - Progress percentage
   - Credits used
   - Success/failure counts
   - ETA calculation

### 4.5 Phase 5: Price Enhancement
**Duration**: 2-3 hours (if needed)  
**ScrapingBee Credits**: 1,000-2,000

1. **Direct Price Extraction**
   - Check if AADF shows prices
   - Extract price per kg/lb

2. **Retailer Link Following** (if no direct prices)
   - Identify "Buy Now" links
   - Common retailers: Amazon UK, Pets at Home, Zooplus
   - Create secondary price scraper

3. **Price Database Schema**
   ```sql
   CREATE TABLE food_prices (
       id UUID PRIMARY KEY,
       food_id UUID REFERENCES food_candidates(id),
       retailer TEXT,
       price NUMERIC,
       currency TEXT,
       per_unit TEXT,  -- 'kg', 'lb', 'bag'
       url TEXT,
       in_stock BOOLEAN,
       last_checked TIMESTAMPTZ
   );
   ```

## 5. Quality Assurance

### 5.1 Validation Rules
- Brand and name must be non-empty
- Form must be normalized value
- Protein + fat + fiber + ash + moisture ≤ 100%
- kcal/100g should be 250-600 for dry, 50-200 for wet
- Price per kg should be reasonable (£1-£50)
- Ingredients list should contain at least 3 items

### 5.2 QA Report
```python
def generate_qa_report(results):
    return {
        'total_processed': len(results),
        'successful': sum(1 for r in results if r['success']),
        'failed': sum(1 for r in results if not r['success']),
        'duplicates_skipped': sum(1 for r in results if r.get('duplicate')),
        'avg_protein': avg([r['protein'] for r in results if r.get('protein')]),
        'missing_nutrition': sum(1 for r in results if not r.get('kcal_per_100g')),
        'missing_prices': sum(1 for r in results if not r.get('price')),
        'total_credits_used': total_credits,
        'estimated_cost': total_credits * 0.001  # $0.001 per credit
    }
```

## 6. Cost Analysis

### 6.1 ScrapingBee Pricing
- **JavaScript Rendering**: 5 credits per request
- **Premium Proxy**: +10 credits (if needed for 403 bypass)
- **Current Rate**: $0.001 per credit

### 6.2 Estimated Usage
| Phase | Requests | Credits per Request | Total Credits | Cost |
|-------|----------|-------------------|---------------|------|
| Discovery | 10-20 | 15 | 150-300 | $0.15-0.30 |
| Product Scraping | 500-1000 | 5-15 | 2,500-15,000 | $2.50-15.00 |
| Price Scraping | 200-400 | 5 | 1,000-2,000 | $1.00-2.00 |
| **Total** | **710-1420** | - | **3,650-17,300** | **$3.65-17.30** |

### 6.3 Optimization Strategies
1. Cache successful responses locally
2. Skip products already in database
3. Use basic proxy first, premium only if needed
4. Batch similar products to reuse rendered pages
5. Save failed URLs for targeted retry

## 7. Error Handling

### 7.1 Common Errors & Solutions
| Error | Cause | Solution |
|-------|-------|----------|
| 403 Forbidden | Direct access blocked | Use ScrapingBee with premium proxy |
| 429 Rate Limited | Too many requests | Implement exponential backoff |
| Timeout | Slow page load | Increase wait time to 5000ms |
| Missing Data | Changed HTML structure | Update selectors, add fallbacks |
| Duplicate Entry | Product already exists | Skip or merge data |

### 7.2 Retry Strategy
```python
def retry_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait_time = 2 ** attempt  # Exponential backoff
            time.sleep(wait_time)
```

## 8. Expected Outcomes

### 8.1 Data Coverage
- **New Products**: 500-1000+ unique foods
- **Database Growth**: +25-50% total products
- **EU Market Coverage**: Significantly improved
- **Nutrition Completeness**: 80-90% with full nutrition data
- **Ingredient Coverage**: 95%+ with complete ingredient lists

### 8.2 Data Quality Improvements
- Independent quality ratings from AADF
- More accurate EU pricing
- Better coverage of specialty/premium brands
- Enhanced allergy filtering capability

### 8.3 Business Value
- Better recommendations for EU customers
- Comprehensive allergy avoidance options
- Price comparison capabilities
- Quality-based food rankings

## 9. File Structure

```
/Users/sergiubiris/Desktop/lupito-content/
├── AADF_FOOD_SCRAPING_PLAN.md (this file)
├── jobs/
│   ├── aadf_food_scraper.py (main scraper)
│   └── aadf_price_scraper.py (price enhancement)
├── data/
│   ├── aadf_product_urls.txt (discovered URLs)
│   ├── aadf_failed_urls.txt (retry list)
│   └── aadf_scraping_report.json (results)
└── logs/
    └── aadf_scraping_YYYYMMDD.log
```

## 10. Commands & Usage

### 10.1 Discovery Phase
```bash
# Discover all product URLs
python3 jobs/aadf_food_scraper.py --discover --output aadf_product_urls.txt
```

### 10.2 Scraping Phase
```bash
# Scrape all products
python3 jobs/aadf_food_scraper.py --urls-file aadf_product_urls.txt --batch-size 50

# Scrape specific product
python3 jobs/aadf_food_scraper.py --url "https://www.allaboutdogfood.co.uk/product/..."

# Resume from failures
python3 jobs/aadf_food_scraper.py --urls-file aadf_failed_urls.txt --retry
```

### 10.3 Price Enhancement
```bash
# Scrape prices from retailers
python3 jobs/aadf_price_scraper.py --check-prices
```

### 10.4 Reporting
```bash
# Generate QA report
python3 jobs/aadf_food_scraper.py --generate-report
```

## 11. Monitoring & Maintenance

### 11.1 Key Metrics
- Success rate (target: >90%)
- Credits per product (target: <10)
- Data completeness (target: >80%)
- Duplicate rate (expected: <10%)

### 11.2 Regular Maintenance
- Weekly: Check for HTML structure changes
- Monthly: Update product catalog
- Quarterly: Full re-scrape for updates

### 11.3 Alerts
- Success rate drops below 80%
- Credit usage exceeds budget
- HTML structure changes detected
- Database connection failures

## 12. Next Steps

1. **Immediate Actions**:
   - [ ] Review and approve this plan
   - [ ] Verify ScrapingBee API key and credits
   - [ ] Test access to AADF with ScrapingBee

2. **Development**:
   - [ ] Implement discovery script
   - [ ] Build main scraper
   - [ ] Test with 10 products
   - [ ] Execute full run

3. **Post-Scraping**:
   - [ ] Validate data quality
   - [ ] Generate QA report
   - [ ] Import to production database
   - [ ] Update foods_published view

## Appendix A: Sample AADF Product Data

```json
{
    "brand": "Orijen",
    "product_name": "Original Adult Dog Food",
    "form": "dry",
    "life_stage": "adult",
    "ingredients_raw": "Fresh chicken meat (13%), fresh turkey meat (7%), fresh cage-free eggs (7%), fresh chicken liver (6%), fresh whole herring (6%), fresh whole flounder (5%), fresh turkey liver (5%), fresh chicken necks (4%), fresh chicken heart (4%), fresh turkey heart (4%)...",
    "protein_percent": 38.0,
    "fat_percent": 18.0,
    "fiber_percent": 4.0,
    "moisture_percent": 12.0,
    "kcal_per_100g": 385,
    "aadf_rating": 4.5,
    "price_per_kg": 15.99,
    "available_sizes": ["2kg", "6kg", "11.4kg"],
    "special_features": ["grain-free", "high-protein", "biologically-appropriate"]
}
```

## Appendix B: Useful Resources

- [AADF Website](https://www.allaboutdogfood.co.uk)
- [ScrapingBee Documentation](https://www.scrapingbee.com/documentation/)
- [Supabase Python Client](https://github.com/supabase-community/supabase-py)
- [BeautifulSoup Documentation](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)

---

*Document Status: Ready for Review*  
*Last Updated: 2025-01-09*  
*Next Review: Before implementation*