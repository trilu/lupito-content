# Plan: Capture Ingredients for Final 237 Zooplus Products

**Date:** September 13, 2025  
**Current Coverage:** 93.2% (3,273 of 3,510 Zooplus products have ingredients)  
**Remaining:** 237 products without ingredients

## Problem Analysis

Based on manual testing of product pages, ALL products have ingredients under the "Ingredients" tab. The issue is our current regex patterns are too restrictive and miss certain page structures.

### Page Structure (from screenshots)
All pages follow this consistent structure:
1. "Go to analytical constituents" link
2. "Ingredients" or "Ingredients:" header
3. The actual ingredients list
4. "Additives" or "Additives per kg:" section  
5. "Analytical constituents" section

### Current Pattern Limitations
Our 7 existing patterns fail because they:
- Require specific text after ingredients (like "Additives")
- Expect ingredients to start with specific words
- Are too strict about formatting
- Miss variations in the "Ingredients" header format

## Products to Process

### Total: 237 Products

#### By Form:
- **Dry food:** 193 (81.4%)
- **Wet food:** 43 (18.1%)
- **Unknown:** 1 (0.4%)

#### Top Brands Missing Ingredients:
1. Farmina N&D: 20 products
2. Eukanuba: 11 products
3. Lukullus: 11 products
4. Nova Foods Natural Trainer: 10 products
5. Brit: 10 products
6. Smølke: 9 products
7. Rinti: 8 products
8. Forza10: 8 products
9. Wolf Of Wilderness: 7 products
10. Specific Veterinary Diet: 7 products
11. Others: 136 products

### Test URLs (5 products)
1. https://www.zooplus.com/shop/dogs/canned_dog_food/rinti/rinti_cans/128729
2. https://www.zooplus.com/shop/dogs/canned_dog_food/wolf_of_wilderness/hundenassfuttermitdreifachenproteinenregionen/1952494
3. https://www.zooplus.com/shop/dogs/canned_dog_food/rinti/specialist_diet/1582654
4. https://www.zooplus.com/shop/dogs/canned_dog_food/wow/1947711
5. https://www.zooplus.com/shop/dogs/dry_dog_food/simpsons_premium/sensitive/538330

## Implementation Strategy

### Approach: Relaxed Content Capture
Instead of trying to match specific patterns, capture EVERYTHING from "Go to analytical constituents" onwards, then process later.

### New Pattern to Add (Pattern 8)
```python
# Pattern 8: Relaxed - capture everything from "Go to analytical constituents" onwards
r'Go to analytical constituents\s*\n(.*?)(?:Analytical constituents|$)'
```

This pattern will:
- Find the "Go to analytical constituents" marker
- Capture everything after it
- Stop at "Analytical constituents" or end of text
- Store the entire block including Ingredients header, ingredients list, and additives

## Execution Plan

### Phase 1: Update Extraction Logic
**File to modify:** `scripts/orchestrated_scraper.py`

Add Pattern 8 to the ingredients_patterns list (line 141-166):
```python
# Pattern 8: Relaxed capture from "Go to analytical constituents" 
r'Go to analytical constituents\s*\n(.*?)(?:Analytical constituents|$)',
```

### Phase 2: Test on 5 URLs
Create test script: `scripts/test_relaxed_extraction.py`

Test objectives:
- Verify Pattern 8 captures full content block
- Ensure ingredients and additives are both captured
- Check extraction rate (target: >80%)

### Phase 3: Full-Scale Rescraping (if test succeeds)

#### Scraping Configuration
- **Total products:** 237
- **Concurrent scrapers:** 5
- **Batch size:** 50 products per scraper
- **Country codes:** Rotate through gb, de, fr, es, it
- **Delays:** 15-25 seconds between requests
- **Estimated time:** 45-60 minutes

#### Execution Commands
```bash
# Start orchestrator for 237 products
python scripts/scraper_orchestrator.py --instance 1 --offset-start 0

# Monitor progress
python scripts/orchestrator_dashboard.py

# Process scraped data
python scripts/process_gcs_scraped_data.py scraped/zooplus/[folder_name]
```

### Phase 4: Post-Processing

Create cleanup script if needed to parse the raw captured content:
1. Extract ingredients from the full block
2. Separate additives if required
3. Update database with parsed values

## Success Metrics

- **Test Phase:** >80% extraction on 5 test URLs
- **Full Batch:** >90% extraction rate for 237 products
- **Final Coverage:** >95% (3,273 + ~213 = 3,486 of 3,510 products)

## Risk Mitigation

1. **Test First:** Validate on 5 URLs before full batch
2. **Fallback:** Keep existing 7 patterns as backup
3. **Raw Storage:** Store complete captured content for manual review
4. **Batch Processing:** Process in smaller batches to monitor progress
5. **Rollback Plan:** Keep backup of current data before updates

## Alternative Approach (if Pattern 8 fails)

If the relaxed pattern doesn't work, create an even more permissive pattern:
```python
# Ultra-relaxed: Capture from "Ingredients" to end of visible content
r'(?:Ingredients|Ingredients:)\s*\n(.*?)$'
```

This would capture everything after the Ingredients header, which we can then clean up in post-processing.

## Database Update Strategy

When processing captured content:
1. Store raw captured block in a temporary field
2. Parse ingredients from the block
3. Parse additives separately if present
4. Update `ingredients_raw` field with cleaned ingredients
5. Log any products that still fail for manual review

## Timeline

- **Test Phase:** 30 minutes
- **Review Results:** 15 minutes
- **Full Scraping:** 45-60 minutes
- **Processing:** 30 minutes
- **Total:** ~2.5 hours

## Decision Points

1. **After Test Phase:** If extraction rate <80%, refine pattern
2. **During Full Scrape:** If error rate >20%, pause and investigate
3. **After Processing:** If final coverage <95%, consider manual extraction

## Notes

- Most remaining products are dry food (81.4%), which typically have simpler page structures
- Wet food (18.1%) may need special handling due to variant selectors
- The "Go to analytical constituents" anchor appears consistent across all pages
- Capturing raw content allows flexibility in post-processing

## Next Steps

1. Review and approve this plan
2. Implement Pattern 8 in orchestrated_scraper.py
3. Run test on 5 URLs
4. Evaluate results
5. Proceed with full batch if successful