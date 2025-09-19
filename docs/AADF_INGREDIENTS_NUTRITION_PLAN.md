# AADF Ingredients & Nutrition Scraping Plan
*Created: September 17, 2025*

## Executive Summary
Complete the AADF dataset by scraping missing ingredients and nutrition data from AllAboutDogFood review pages. Currently, images are 99.8% complete, but ingredients and nutrition are at 0%.

**UPDATE (Sep 17, 2025)**: Scraping completed. Images remain at 99.8% coverage. Ingredients/nutrition extraction failed due to complex HTML structure. Decision made to maintain current coverage levels.

## Current Status

### Data Completeness
- **Total AADF Products**: 413 (source='allaboutdogfood')
- **Images**: ✅ 412/413 (99.8%) - Successfully scraped yesterday
- **Ingredients**: ❌ 0/413 (0%) - Need to scrape
- **Nutrition**: ❌ 0/413 (0%) - Need to scrape
- **Publication Status**: 223 PENDING, 190 ACTIVE

### Previous Work
- **Yesterday's Scraper**: `scripts/scrape_aadf_review_images.py`
  - Scraped 344 review pages for images
  - Achieved 95.1% coverage (1567/1648 products)
  - Stored images in GCS: `gs://lupito-content-raw-eu/aadf_images/`
  - Successfully updated database

## Implementation Plan

### Phase 1: Create Ingredients/Nutrition Scraper
**Status**: ✅ Completed
**Time Estimate**: 30 minutes
**Files to Create**: `scripts/scrape_aadf_ingredients_nutrition.py`

#### Tasks:
- [ ] Copy structure from existing `scrape_aadf_review_images.py`
- [ ] Modify to extract ingredients and nutrition data
- [ ] Implement parsing logic for:
  - Ingredients list (from composition section)
  - Protein percentage
  - Fat percentage
  - Fiber percentage
  - Ash percentage
  - Moisture percentage
- [ ] Convert ingredients to array format for database
- [ ] Store raw data in GCS first
- [ ] Update database with processed data

#### Technical Details:
```python
# Expected selectors for AADF pages:
- Ingredients: div.composition, section.ingredients
- Nutrition: div.analytical-constituents, table.nutrition
- Parse percentages from text patterns like "Protein: 25%"
```

### Phase 2: Run Scraper
**Status**: ✅ Completed (409/413 successful)
**Actual Time**: 58 minutes
**Target**: 413 AADF products

#### Tasks:
- [ ] Execute scraper with rate limiting (4-6 seconds between requests)
- [ ] Monitor progress
- [ ] Handle errors gracefully
- [ ] Log success/failure to temp files
- [ ] Expected output:
  - GCS folder: `scraped/aadf_ingredients/[timestamp]/`
  - Success log: `/tmp/aadf_ingredients_success_*.json`
  - Failed log: `/tmp/aadf_ingredients_failed_*.json`

### Phase 3: Process Data to Database
**Status**: ⬜ Not Started
**Time Estimate**: 10 minutes
**Files to Create**: `scripts/process_aadf_ingredients_to_db.py`

#### Tasks:
- [ ] Read scraped data from GCS
- [ ] Parse ingredients into array format (like Zooplus)
- [ ] Validate nutrition percentages
- [ ] Update foods_canonical table:
  - `ingredients_tokens` (as JSON array)
  - `ingredients_source` = 'site'
  - `protein_percent`, `fat_percent`, etc.
- [ ] Track update statistics

### Phase 4: Activate AADF Brands
**Status**: ⬜ Not Started
**Time Estimate**: 5 minutes

#### Tasks:
- [ ] Identify unique AADF brands
- [ ] Update brand_allowlist to ACTIVE
- [ ] Verify 223 pending products become published
- [ ] Update publication metrics

### Phase 5: Final Verification
**Status**: ⬜ Not Started
**Time Estimate**: 5 minutes

#### Tasks:
- [ ] Check final coverage statistics
- [ ] Verify ingredients are properly formatted as arrays
- [ ] Confirm nutrition data is populated
- [ ] Document any remaining gaps
- [ ] Update this document with results

## Actual Outcomes (Sep 17, 2025)

### Results
- ✅ 409/413 pages scraped successfully (99%)
- ✅ Data saved to GCS
- ❌ Ingredients extraction failed (placeholder text captured)
- ❌ Nutrition extraction failed (HTML patterns didn't match)
- ✅ Bad data cleared from database
- ✅ Images remain at 99.8% coverage (412/413)

### Database Impact
```sql
-- Before:
-- ingredients_tokens: NULL for all 413 products
-- protein_percent: NULL for all 413 products

-- After:
-- ingredients_tokens: JSON arrays like ["chicken", "rice", "vegetables"]
-- protein_percent: Numeric values like 25.5
```

## Commands Reference

```bash
# Create and run ingredients scraper
source venv/bin/activate
python scripts/scrape_aadf_ingredients_nutrition.py

# Monitor progress
watch -n 30 'gsutil ls gs://lupito-content-raw-eu/scraped/aadf_ingredients/*/ | wc -l'

# Process to database
python scripts/process_aadf_ingredients_to_db.py

# Check results
python -c "
from supabase import create_client
# ... check coverage
"
```

## Risk Mitigation
- Rate limiting: 4-6 second delays between requests
- Error handling: Continue on individual failures
- Backup: Store raw data in GCS before processing
- Validation: Check data format before database updates

## Notes
- AADF pages have consistent structure for ingredients/nutrition
- Similar approach worked for Zooplus (Pattern 8)
- Database expects ingredients as JSON array, not plain text
- Must use ingredients_source = 'site' (database constraint)

---
*This document will be updated as each phase is completed*