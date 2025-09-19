# AADF Image Scraping Plan
**Date:** September 15, 2025  
**Target:** Scrape images for 1,643 AADF products  
**Success Rate:** 100% (based on test of 5 products)

## Current State

### Coverage Analysis
- **Total AADF products:** 1,648
- **With images:** 5 (0.3%) - just tested
- **Need images:** 1,643 (99.7%)

### Resource Requirements
- **Time:** ~3 hours with 4 parallel sessions
- **ScrapingBee Credits:** 164,300 (100 credits per request)
- **Cost:** ~$164 USD
- **Storage:** ~50MB in GCS (assuming 30KB per JSON)

## Implementation Strategy

### Phase 1: Infrastructure Setup
1. **Orchestrator System**
   - Main controller to manage multiple sessions
   - Auto-restart on failures
   - Progress tracking and monitoring
   - Based on proven Zooplus orchestrator

2. **Scraper Sessions**
   - 4 parallel sessions (us1, gb1, de1, ca1)
   - Each handles ~410 products
   - 20-30 second delays between requests
   - Automatic retry on failures

3. **Data Flow**
   ```
   AADF Website → ScrapingBee API → Image URL Extraction
        ↓                               ↓
   GCS Storage ← JSON Results → Database Update
   ```

### Phase 2: Execution Plan

#### Session Distribution
```python
Session 1 (US): Products 0-410 (~410 products)
Session 2 (GB): Products 411-821 (~410 products)
Session 3 (DE): Products 822-1232 (~410 products)
Session 4 (CA): Products 1233-1643 (~410 products)
```

#### Timing Strategy
- **Delay between requests:** 20-30 seconds (randomized)
- **Timeout per request:** 30 seconds
- **Max retries:** 2 per product
- **Session duration:** ~3 hours each

### Phase 3: Monitoring

#### Real-time Dashboard
- Track progress per session
- Monitor success/failure rates
- Calculate ETA
- Show recent successes/failures

#### Metrics to Track
- Images found per session
- Database updates completed
- Error rates and types
- ScrapingBee credit usage

### Phase 4: Data Processing

#### Image URL Format
AADF uses consistent pattern:
```
https://www.allaboutdogfood.co.uk/storage/products/560x560/{product-slug}-1.jpg
```

#### Database Updates
- Update `image_url` field in `foods_canonical`
- Only update if image successfully found
- Track update success/failure

#### GCS Backup
- Store all scraped data in GCS
- Folder: `gs://lupito-content-raw-eu/scraped/aadf_images/{session_id}/`
- Keep for recovery/analysis

## Script Architecture

### 1. Main Orchestrator
**File:** `scripts/aadf_image_orchestrator.py`
- Manages all sessions
- Monitors progress
- Handles restart logic
- Aggregates statistics

### 2. Session Scraper
**File:** `scripts/scrape_aadf_images_session.py`
- Individual scraper instance
- Accepts offset and batch size
- Reports to orchestrator
- Handles retries

### 3. Monitor Dashboard
**File:** `scripts/monitor_aadf_images.py`
- Real-time progress display
- Session statistics
- ETA calculations
- Error tracking

## Risk Mitigation

### Potential Issues
1. **Rate Limiting**
   - Solution: 20-30 second delays
   - Fallback: Increase delays if needed

2. **ScrapingBee Failures**
   - Solution: Retry with different country codes
   - Fallback: Skip and log for manual review

3. **Image Pattern Changes**
   - Solution: Multiple extraction patterns
   - Fallback: Save HTML for manual extraction

4. **Database Connection Issues**
   - Solution: Batch updates with retry
   - Fallback: Update from GCS data later

## Success Criteria

- [ ] 95%+ images successfully scraped
- [ ] All successful scrapes updated in database
- [ ] Complete audit trail in GCS
- [ ] No duplicate scraping
- [ ] Clean error handling

## Commands

### Start Orchestrator
```bash
python scripts/aadf_image_orchestrator.py --sessions 4 --delay-min 20 --delay-max 30
```

### Monitor Progress
```bash
python scripts/monitor_aadf_images.py
```

### Process GCS Data (Recovery)
```bash
python scripts/process_aadf_images_gcs.py --folder scraped/aadf_images/{session_id}
```

## Expected Outcomes

### After ~3 Hours
- **1,643 AADF products with images**
- **Database:** 100% AADF products have images
- **Success rate:** Expected 95%+
- **Failed products:** <5% (manual review needed)

### Database Impact
- AADF products with images: 5 → 1,648
- Overall products with images: 6,437 → 8,080
- Image coverage: 72.1% → 90.5%

## Next Steps After Completion

1. **Verify Results**
   - Check database coverage
   - Review failed products
   - Validate image URLs

2. **Optimization**
   - Download and store images locally
   - Create thumbnails
   - Implement CDN strategy

3. **Extend to Other Sources**
   - Apply same strategy to other sources
   - Prioritize by product count

---
*Plan created: September 15, 2025*