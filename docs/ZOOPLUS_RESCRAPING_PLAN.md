# Zooplus Full-Scale Rescraping Plan

**Date:** September 13, 2025  
**Purpose:** Rescrape all Zooplus products missing ingredients with improved extraction patterns  
**Expected Outcome:** Increase ingredients coverage from 55% to 85-90%

## Current State Analysis

### Database Status
- **Total Zooplus products:** 3,676
- **Products with ingredients:** 2,031 (55.3%)
- **Missing ingredients:** 1,645 (44.7%)
- **Missing nutrition:** 993 (27.0%)

### Key Insights
- **1,181 products** have nutrition but no ingredients (prime rescrape candidates)
- **18 trial packs** should be excluded (no detailed ingredients)
- **Net products to rescrape:** ~1,627

### Pattern Improvements Validated
Test results on 50 previously failed products:
- **Extraction rate:** 98-100% (49/50 products tested)
- **Wet food fix:** Now handles variant names correctly
- **Navigation text:** Handles "Go to analytical constituents" properly
- **Multiple formats:** Supports various ingredient header structures

## Rescraping Strategy

### Phase 1: High-Priority Products (1,181 products)
Products with nutrition but missing ingredients - these are most likely to have ingredients that our previous patterns missed.

**Query criteria:**
```sql
WHERE product_url LIKE '%zooplus.com%' 
  AND ingredients_raw IS NULL 
  AND protein_percent IS NOT NULL
  AND product_name NOT LIKE '%trial%pack%'
```

### Phase 2: Remaining Products (446 products)
Products with no ingredients or nutrition data.

**Query criteria:**
```sql
WHERE product_url LIKE '%zooplus.com%' 
  AND ingredients_raw IS NULL 
  AND protein_percent IS NULL
  AND product_name NOT LIKE '%trial%pack%'
  AND product_name NOT LIKE '%sample%'
```

## Implementation Plan

### 1. Rescraping Script Structure
```python
# scripts/rescrape_zooplus_missing_ingredients.py

Key features:
- Query products WHERE ingredients_raw IS NULL
- Prioritize products with existing nutrition data
- Exclude trial/sample packs
- Check GCS for already scraped files
- Use improved orchestrated_scraper patterns
- Batch processing with configurable size
```

### 2. Orchestration Configuration

**5 Concurrent Scrapers:**
| Scraper | Country | Batch Size | Delay Range |
|---------|---------|------------|-------------|
| scraper_1 | gb | 100 | 15-25s |
| scraper_2 | de | 100 | 15-25s |
| scraper_3 | fr | 100 | 15-25s |
| scraper_4 | es | 100 | 15-25s |
| scraper_5 | it | 100 | 15-25s |

**Total Processing Time Estimate:**
- 1,627 products ÷ 5 scrapers = 325 products per scraper
- 325 products × 20 seconds average = ~108 minutes
- **Expected completion: ~2 hours**

### 3. Monitoring Setup

**Dashboard Metrics:**
- Products processed (real-time)
- Extraction success rate
- Products remaining
- Estimated time to completion
- Error rate and retry count
- Country code distribution

**Progress Tracking:**
```bash
# Monitor command
watch -n 30 'gsutil ls gs://lupito-content-raw-eu/scraped/zooplus/rescrape_*/*.json | wc -l'
```

### 4. Processing Pipeline

```
[Scraper] → [GCS Storage] → [Continuous Processor] → [Database]
     ↓           ↓                    ↓                    ↓
  Scrapes    JSON files         Extracts data      Updates rows
```

**Continuous Processor Configuration:**
- Poll interval: 30 seconds
- Batch size: 50 files
- Error handling: Retry 3 times
- Validation: Check ingredients contain food terms

## Efficiency Optimizations

### 1. Duplicate Prevention
- Check GCS before scraping: `gs://lupito-content-raw-eu/scraped/zooplus/{session_id}/{product_key}.json`
- Skip if file exists and has ingredients

### 2. Smart Querying
```python
# Get products in order of likelihood to have ingredients
ORDER BY 
  CASE 
    WHEN protein_percent IS NOT NULL THEN 0  # Has nutrition
    WHEN brand IN ('Royal Canin', 'Bosch', 'Advance') THEN 1  # Known good brands
    ELSE 2 
  END
```

### 3. Pattern Optimization
Current improved patterns in `orchestrated_scraper.py`:
1. Wet food with product descriptions
2. Navigation text handling
3. Multiple header formats
4. Variant name skipping

## Commands to Execute

### Step 1: Create Rescraping Script
```bash
# Create scripts/rescrape_zooplus_missing_ingredients.py
# (Implementation based on orchestrated_scraper.py with prioritization)
```

### Step 2: Launch Orchestrator
```bash
# Start 5 concurrent scrapers
python scripts/scraper_orchestrator.py \
  --instance-id 1 \
  --offset-start 0 \
  --max-scrapers 5
```

### Step 3: Start Processor
```bash
# Process scraped files to database
python scripts/continuous_processor.py \
  --poll-interval 30 \
  --batch-size 50
```

### Step 4: Monitor Progress
```bash
# Dashboard
python scripts/multi_orchestrator_dashboard.py

# Or simple monitoring
watch -n 30 'python scripts/check_rescrape_progress.py'
```

## Expected Outcomes

### Success Metrics
- **Extraction rate:** 80-90% (based on test results)
- **New ingredients extracted:** ~1,300-1,460 products
- **Final coverage:** 85-90% of all Zooplus products
- **Processing time:** ~2 hours

### Coverage Improvement
| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Products with ingredients | 2,031 | ~3,350 | +65% |
| Coverage percentage | 55.3% | ~91% | +35.7% |
| Missing ingredients | 1,645 | ~326 | -80% |

## Risk Management

### Rate Limiting
- 15-25 second delays between requests
- Country code rotation (5 different codes)
- Maximum 5 concurrent connections
- Automatic backoff on 429 errors

### Data Quality
- Validate ingredients contain food-related terms
- Check minimum length (>20 characters)
- Verify against known patterns
- Log suspicious extractions for review

### Error Handling
- Automatic retry with exponential backoff
- Maximum 3 retries per product
- Log failed products for manual review
- Continue processing on individual failures

## Post-Rescraping Tasks

1. **Validation:**
   - Compare extraction rates across brands
   - Identify products still missing ingredients
   - Analyze patterns in failed extractions

2. **Cleanup:**
   - Remove trial pack products from database
   - Standardize ingredient formats
   - Update brand anomalies

3. **Migration:**
   - Execute variant migration plan
   - Consolidate duplicate products
   - Update import processes

## Notes

- Test showed 100% extraction on first 28/50 products
- Wet food pattern fix was crucial improvement
- Some products genuinely don't display ingredients
- ScrapingBee API performing well with stealth proxy

## Timeline

- **Test completion:** ~5 minutes remaining
- **Setup time:** 15 minutes
- **Scraping time:** ~2 hours
- **Total time:** ~2.5 hours from start

---

*This plan will be executed after the current test completes to avoid resource conflicts.*