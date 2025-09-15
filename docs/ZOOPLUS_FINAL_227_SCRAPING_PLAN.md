# Zooplus Final 227 Products Scraping Plan
**Date:** September 14, 2025  
**Goal:** Achieve 95% database coverage by scraping 227 specific Zooplus products

## Executive Summary

We need to scrape 227 specific Zooplus products that are currently missing ingredients data. These products have been identified and exported to JSON/CSV files. By successfully scraping these products, we will reach our target of 95% database coverage.

## Current Status

- **Current Coverage:** 93.0% (3,264 of 3,510 products have ingredients)
- **Target Coverage:** 95%+
- **Products to Scrape:** 227 specific Zooplus products
- **Data Files Available:**
  - `/data/zooplus_missing_ingredients_20250913.json` (primary source)
  - `/data/zooplus_missing_ingredients_20250913.csv` (alternative format)
  - `/data/zooplus_missing_ingredients_20250913.txt` (human-readable)

## Architecture

```
227 Products JSON → Multi-Session Scraper → GCS Storage → Processing Script → Database Update
```

### Data Flow
1. **Input:** Read 227 products from JSON file
2. **Scraping:** Multiple concurrent sessions with different country codes
3. **Storage:** Save scraped data to GCS buckets
4. **Processing:** Download from GCS and update database
5. **Tracking:** Mark processed folders to avoid duplicates

## Implementation Components

### 1. Targeted Scraper (`scripts/scrape_zooplus_final_227.py`)

**Purpose:** Scrape the specific 227 products using proven patterns and parameters

**Key Features:**
- Read products from `/data/zooplus_missing_ingredients_20250913.json`
- Use all 8 extraction patterns including Pattern 8 (relaxed extraction)
- Save individual product results to GCS
- Support multi-session concurrent execution
- Implement retry logic for failed products

**Extraction Patterns (from `orchestrated_scraper.py`):**
```python
patterns = [
    # Pattern 1: "Ingredients / composition" format
    r'Ingredients\s*/\s*composition\s*\n([^\n]+...)',
    
    # Pattern 2: "Ingredients:" with optional product description
    r'Ingredients:\s*\n(?:[^\n]*?(?:wet food|complete|diet)...)',
    
    # Pattern 3: "Ingredients:" with variant info
    r'Ingredients:\s*\n(?:\d+(?:\.\d+)?kg bags?:...)',
    
    # Pattern 4: Simple "Ingredients:" 
    r'Ingredients:\s*\n([A-Z][^\n]+...)',
    
    # Pattern 5: General "Ingredients:" with multiline
    r'Ingredients:\s*\n([^\n]+(?:\([^)]+\))?...)',
    
    # Pattern 6: "Ingredients" (no colon) with meat/duck/chicken
    r'Ingredients\s*\n((?:Meat|Duck|Chicken)...)',
    
    # Pattern 7: "Ingredients:" with specific protein starting
    r'Ingredients:\s*\n((?:Duck|Chicken|Meat|Lamb|Beef|Turkey|Salmon|Fish)...)',
    
    # Pattern 8: Relaxed capture for difficult products
    r'Go to analytical constituents\s*\n(.*?)(?:Analytical constituents|$)'
]
```

**GCS Storage Structure:**
```
gs://lupito-content-raw-eu/scraped/zooplus/
├── final_227_20250914_123456_us1/
│   ├── product_key1.json
│   ├── product_key2.json
│   └── ...
├── final_227_20250914_123456_gb1/
│   └── ...
└── final_227_20250914_123456_de1/
    └── ...
```

### 2. Multi-Session Configuration

**Concurrent Sessions:**
```python
sessions = [
    {
        "name": "us1",
        "country_code": "us",
        "min_delay": 15,
        "max_delay": 25,
        "products": products[0:75]  # First 75 products
    },
    {
        "name": "gb1", 
        "country_code": "gb",
        "min_delay": 20,
        "max_delay": 30,
        "products": products[75:150]  # Next 75 products
    },
    {
        "name": "de1",
        "country_code": "de", 
        "min_delay": 25,
        "max_delay": 35,
        "products": products[150:227]  # Last 77 products
    }
]
```

**ScrapingBee Parameters (Proven Successful):**
```python
params = {
    'api_key': SCRAPINGBEE_API_KEY,
    'url': product_url,
    'render_js': 'true',          # Execute JavaScript
    'premium_proxy': 'true',      # Use premium proxy network
    'stealth_proxy': 'true',      # Anti-detection features
    'country_code': session_country,  # Rotate by country
    'wait': '3000',              # Wait for page load
    'return_page_source': 'true'  # Return full HTML
}
```

### 3. Progress Monitor (`scripts/monitor_final_227.py`)

**Purpose:** Real-time monitoring of scraping progress

**Features:**
- Count files in each GCS session folder
- Calculate overall progress (X/227 completed)
- Display per-session statistics
- Estimate time to completion
- Show extraction success rates

**Example Output:**
```
📊 FINAL 227 SCRAPING PROGRESS
================================
Target: 227 products
Completed: 145/227 (63.9%)
Success Rate: 82.1%

🚀 ACTIVE SESSIONS
------------------
🇺🇸 US1: 65/75 completed (86.7%)
🇬🇧 GB1: 52/75 completed (69.3%)
🇩🇪 DE1: 28/77 completed (36.4%)

⏱️ Time Elapsed: 1h 23m
⏱️ Est. Completion: 45 minutes

📁 GCS Folders:
- final_227_20250914_123456_us1: 65 files
- final_227_20250914_123456_gb1: 52 files
- final_227_20250914_123456_de1: 28 files
```

### 4. GCS Processor (`scripts/process_final_227_gcs.py`)

**Purpose:** Process scraped data from GCS and update database

**Features:**
- List all files in final_227_* folders
- Download and parse JSON files
- Extract ingredients and tokenize
- Update database with nutrition data
- Track processed folders in `processed_folders.txt`

**Database Update Fields:**
```python
update_data = {
    'ingredients_raw': extracted_ingredients[:2000],
    'ingredients_source': 'site',
    'ingredients_tokens': tokenized_ingredients,
    'protein_percent': nutrition.get('protein_percent'),
    'fat_percent': nutrition.get('fat_percent'),
    'fiber_percent': nutrition.get('fiber_percent'),
    'ash_percent': nutrition.get('ash_percent'),
    'moisture_percent': nutrition.get('moisture_percent'),
    'macros_source': 'site'
}
```

## Execution Plan

### Phase 1: Setup & Initial Test (15 minutes)
1. Create the three scripts
2. Test with 5-10 products from the JSON file
3. Verify:
   - JSON file reading works correctly
   - GCS upload successful
   - Pattern 8 extracting difficult products
   - Database connection functional

### Phase 2: Full Scraping (2-3 hours)
1. Launch 3 concurrent sessions
2. Each session processes its assigned products
3. Monitor progress with dashboard
4. Handle any errors or retries

### Phase 3: Database Update (30 minutes)
1. Wait for all scrapers to complete
2. Run GCS processor on all folders
3. Update database with extracted data
4. Mark folders as processed

### Phase 4: Verification (15 minutes)
1. Query database for final coverage
2. Generate statistics report
3. Identify any remaining gaps
4. Document achievement of 95% goal

## Success Criteria

### Primary Goals
- **Extraction Rate:** Successfully scrape 80%+ of 227 products (182+ products)
- **Coverage Target:** Achieve 95% overall database coverage
- **Data Quality:** Valid ingredients extracted and tokenized

### Secondary Goals
- **Nutrition Data:** Extract protein, fat, fiber percentages where available
- **Completion Time:** Finish within 4 hours
- **Error Rate:** Less than 20% failure rate

## Error Handling

### Retry Strategy
```python
max_retries = 3
retry_delay = 60  # seconds
exponential_backoff = True

if error:
    if retry_count < max_retries:
        delay = retry_delay * (2 ** retry_count if exponential_backoff else 1)
        time.sleep(delay)
        retry_count += 1
```

### Common Issues & Solutions
- **Rate Limiting (HTTP 400):** Increase delays, rotate country codes
- **Empty Extraction:** Try Pattern 8 (relaxed extraction)
- **GCS Upload Failure:** Retry with exponential backoff
- **Database Connection:** Queue for later processing

## Monitoring Commands

```bash
# Start scrapers (in separate terminals)
python scripts/scrape_zooplus_final_227.py --session us1
python scripts/scrape_zooplus_final_227.py --session gb1
python scripts/scrape_zooplus_final_227.py --session de1

# Monitor progress
python scripts/monitor_final_227.py

# Process results
python scripts/process_final_227_gcs.py

# Check database coverage
python scripts/check_coverage_stats.py
```

## Expected Timeline

| Phase | Duration | Description |
|-------|----------|-------------|
| Setup & Test | 15 min | Create scripts, test with subset |
| Full Scraping | 2-3 hours | Scrape all 227 products |
| Processing | 30 min | Update database from GCS |
| Verification | 15 min | Check final statistics |
| **Total** | **3-4 hours** | **Complete pipeline** |

## Risk Mitigation

### Potential Risks
1. **Pattern Mismatch:** Some products may have new formats
   - *Mitigation:* Pattern 8 provides relaxed extraction fallback
   
2. **Rate Limiting:** ScrapingBee may throttle requests
   - *Mitigation:* Use multiple country codes, implement delays
   
3. **GCS Issues:** Upload failures or quota limits
   - *Mitigation:* Retry logic, batch uploads
   
4. **Database Locks:** Concurrent updates may conflict
   - *Mitigation:* Process sequentially, use transactions

## Post-Completion Tasks

1. **Generate Report:** Create summary of coverage achievement
2. **Clean GCS:** Archive or delete processed folders
3. **Update Documentation:** Record patterns that worked best
4. **Identify Gaps:** List any products still missing data
5. **Plan Next Steps:** Determine strategy for remaining products

## Appendix: File Locations

### Input Data
- JSON: `/data/zooplus_missing_ingredients_20250913.json`
- CSV: `/data/zooplus_missing_ingredients_20250913.csv`
- TXT: `/data/zooplus_missing_ingredients_20250913.txt`

### Scripts to Create
- `/scripts/scrape_zooplus_final_227.py`
- `/scripts/monitor_final_227.py`
- `/scripts/process_final_227_gcs.py`

### GCS Locations
- Bucket: `gs://lupito-content-raw-eu/`
- Folder: `scraped/zooplus/final_227_*`

### Tracking Files
- `/scripts/processed_folders.txt`
- `/data/final_227_stats.json`

## Conclusion

This plan provides a structured approach to scraping the final 227 Zooplus products needed to achieve 95% database coverage. By using proven extraction patterns (including the relaxed Pattern 8), established GCS infrastructure, and multi-session concurrency, we expect to complete the task within 4 hours with an 80%+ success rate.

The key improvements from previous attempts include:
- Using the exact list of 227 products (no offset queries)
- Including Pattern 8 for difficult-to-extract products
- Following the established GCS → Database pipeline
- Running multiple concurrent sessions for speed

Upon successful completion, we will have achieved our goal of 95% ingredient coverage for the database.