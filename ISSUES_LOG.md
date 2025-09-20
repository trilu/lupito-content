# Breed Content Scraping Issues Log

## Date: 2025-09-20

### Issue 1: Database Schema Cache Not Updated
**Status**: RESOLVED
**Symptoms**:
- Error: `Could not find the 'height_max_cm' column of 'breeds_comprehensive_content' in the schema cache`
- Scripts failing to update database despite columns existing

**Root Cause**:
- Supabase schema cache wasn't refreshed after adding new columns
- The columns DO exist (verified via direct query) but the API cache was stale

**Solution**:
- Schema cache appears to have auto-refreshed (columns now accessible)
- For future: May need to wait or manually refresh schema after ALTER TABLE

---

### Issue 2: Invalid Breed Standard URLs (Phase 3)
**Status**: ACTIVE ISSUE
**Symptoms**:
- 100% failure rate on Phase 3 (breed_standards_import.py)
- All URLs returning 404 errors

**Root Cause**:
- URLs are incorrectly formatted/generated
- Examples of failures:
  - `https://www.akc.org/dog-breeds/dingo/` (404 - dingo is not an AKC breed)
  - `https://www.thekennelclub.org.uk/breed-information/griffon-bruxellois/` (404 - wrong URL format)
  - Many rare/obscure breeds don't have official breed standard pages

**Required Fix**:
1. Need to verify breed exists on target site before attempting to scrape
2. Use proper URL formats for each kennel club site
3. Skip breeds that don't have official standards

---

### Issue 3: Phase 1 Quick Wins Stopped Early
**Status**: UNDERSTOOD
**Symptoms**:
- Script stopped after 5 breeds claiming no fields generated

**Root Cause**:
- The first 5 breeds already had all the target fields filled
- Script's early-exit logic triggered incorrectly

**Solution**:
- Need to sample more breeds before deciding to exit
- Or continue even if some breeds are complete

---

### Issue 4: Missing ScrapingBee Import
**Status**: RESOLVED
**Symptoms**:
- ModuleNotFoundError: No module named 'scrapingbee'

**Solution**:
- Installed with: `pip3 install scrapingbee`

---

## Issue 5: Data Already Exists in breeds Table!
**Status**: CRITICAL FINDING
**Discovery Date**: 2025-09-20

**Finding**:
- The `breeds` table ALREADY HAS 100% coverage for:
  - avg_height_cm (546 breeds)
  - avg_male_weight_kg (546 breeds)
  - avg_female_weight_kg (546 breeds)
- Missing: avg_lifespan_years (0% coverage)

**Impact**:
- We DON'T need to scrape height/weight data - it already exists!
- The breeds_unified_api view is not properly pulling this data
- We only need to focus on lifespan and behavioral traits

**Action Required**:
1. Fix the view to properly pull data from breeds table
2. OR copy the existing data from breeds to breeds_comprehensive_content
3. Focus scraping efforts ONLY on missing data (lifespan, behavioral traits)

---

## Key Learnings

1. **Database Changes**: After adding columns via SQL, need to ensure schema cache is refreshed
2. **URL Validation**: Must validate URLs exist before scraping (especially for rare breeds)
3. **Field Checking**: Should check which fields are actually missing before launching scrapers
4. **Breed Variations**: Many breeds in our database don't exist on official kennel club sites
5. **Check Existing Data**: ALWAYS check ALL tables before scraping - data might already exist!

## Next Steps

1. Fix breed_standards_import.py to:
   - Test URLs before scraping
   - Use correct URL patterns
   - Focus on common breeds first

2. Create a breed mapping table for official sites:
   - Map our breed slugs to official site breed names
   - Store verified working URLs

3. Test on a small subset first before launching large-scale operations