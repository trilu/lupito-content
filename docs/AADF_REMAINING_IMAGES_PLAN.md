# AADF Remaining Images Acquisition Plan

## Current Status
- **Total AADF products**: 1,648
- **Products with images**: 1,183 (71.8%)
- **Products without images**: 465 (28.2%)
  - Database shows 390 without images (due to pagination/query differences)

## Analysis of Missing Products

### 1. URL Pattern Analysis
- **389 products (99.7%)** have review page URLs
- These are individual product review pages on allaboutdogfood.co.uk
- Example: `https://www.allaboutdogfood.co.uk/dog-food-reviews/3716/bonacibo-puppy-can`

### 2. Top Brands Missing Images (Top 20)
| Brand | Missing Products | GCS Images Available |
|-------|-----------------|---------------------|
| Unknown | 44 | - |
| Royal Canin | 28 | 10 (partial match) |
| Nature's Menu | 10 | Check needed |
| Hill's Science Plan | 9 | 21 (good coverage) |
| Pro Plan | 7 | Check needed |
| Husse | 7 | Check needed |
| Eukanuba | 7 | Check needed |
| Pooch & Mutt | 6 | 15 (good coverage) |
| Butcher's | 6 | Check needed |
| Wainwright's | 6 | Check needed |

### 3. Key Issues Identified

#### A. Product Key Mismatch Types
1. **Different naming conventions**:
   - DB: `bonacibo|puppycan|dry`
   - Scraped might be: `bonacibo_puppy_can_dry`

2. **Missing underscores in compound words**:
   - DB: `poochmutt|andmutthepaticdry|dry`
   - Should be: `pooch_mutt|and_mutt_hepatic_dry|dry`

3. **Special characters and encoding**:
   - Some products have special characters that may not match

#### B. Scraping Challenges
- Review pages may have different image locations than product listing pages
- Some products may not have images on AADF site
- Rate limiting considerations for 465 additional requests

## Recommended Solution Strategy

### Phase 1: Quick Wins (Est. 100-150 products recovered)
1. **Fix additional key matching issues**:
   ```python
   # Try multiple key transformations:
   - Remove 'and' vs '&' differences
   - Handle underscore variations
   - Try fuzzy matching for close matches
   ```

2. **Match existing GCS images better**:
   - We have Royal Canin, Hills, Pooch & Mutt images in GCS
   - Implement fuzzy matching algorithm
   - Could recover ~50-100 products

### Phase 2: Targeted Scraping (Est. 300-350 products)
1. **Create focused scraper for review pages**:
   ```python
   # Scrape directly from review URLs
   - Parse review page structure
   - Extract main product image
   - Handle rate limiting (2-3 seconds between requests)
   ```

2. **Priority order**:
   - High-value brands (Royal Canin, Hill's, Pro Plan)
   - Brands with partial GCS coverage
   - Popular/common products

### Phase 3: Manual Resolution (Est. 50-100 products)
1. **Unknown brand products** (44 products)
   - May need manual investigation
   - Could be discontinued or renamed products

2. **No URL products**
   - Need to search AADF site
   - May require manual mapping

## Implementation Plan

### Step 1: Enhanced Matching Script (1-2 hours)
```python
# Create script: match_aadf_fuzzy.py
- Load all GCS image keys
- Load all DB products without images
- Implement fuzzy matching:
  - Levenshtein distance
  - Token-based matching
  - Brand-specific rules
- Update matched products
```

### Step 2: Review Page Scraper (2-3 hours)
```python
# Create script: scrape_aadf_reviews.py
- Input: List of review URLs
- Process:
  - Visit each review page
  - Find product image (usually in specific div/class)
  - Download to GCS
  - Track success/failures
- Rate limiting: 2-3 seconds between requests
- Checkpoint/resume capability
```

### Step 3: Execution Timeline
1. **Day 1**: Run enhanced matching (automated)
2. **Day 2-3**: Run review scraper (overnight)
3. **Day 4**: Verify and update database
4. **Day 5**: Manual resolution for remaining

## Expected Outcomes
- **Phase 1**: Recover 100-150 products (76-81% total coverage)
- **Phase 2**: Add 300-350 products (94-96% total coverage)
- **Phase 3**: Final 50-100 products (97-99% total coverage)

## Technical Considerations
1. **Rate Limiting**:
   - Nighttime: 2-3 seconds between requests
   - Daytime: 4-6 seconds between requests
   - Total time: ~30-45 minutes for 465 products

2. **Storage**:
   - Continue using: `gs://lupito-content-raw-eu/product-images/aadf/`
   - Maintain underscore naming convention

3. **Database Updates**:
   - Use fixed update script with key transformation
   - Batch updates for efficiency

## Success Metrics
- Achieve 95%+ image coverage for AADF products
- Minimize failed scraping attempts
- Maintain data quality and consistency

## Risk Mitigation
1. **Site changes**: Monitor for HTML structure changes
2. **Rate limiting**: Implement exponential backoff
3. **Image quality**: Validate downloaded images
4. **Duplicates**: Check for existing images before downloading

## Next Actions
1. ✅ Review and approve plan
2. ⬜ Implement enhanced matching script
3. ⬜ Develop review page scraper
4. ⬜ Execute scraping campaign
5. ⬜ Update database with new images
6. ⬜ Document final results