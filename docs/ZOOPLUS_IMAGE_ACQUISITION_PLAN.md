# Zooplus Image Acquisition Plan
*Created: September 16, 2025*

## Current Status
- **Total Zooplus products**: 3,510
- **With images**: 2,670 (76.1%)
- **Without images**: 840 (23.9%)
- **All missing products**: From `zooplus_csv_import` source

## Key Findings

### 1. Missing Products Analysis
- **Source**: 100% from `zooplus_csv_import`
- **URLs**: All have valid zooplus.com URLs
- **Key format**: All use pipe separator format
- **GCS images**: 2,665 images already in storage

### 2. Technical Challenges
- **403 Forbidden**: Zooplus CDN blocks direct image downloads
- **Bot protection**: Images at media.zooplus.com require proper headers/cookies
- **No fuzzy matches**: CSV import products don't match existing GCS images

## Three-Phase Approach

### Phase 1: Browser Automation ⭐ RECOMMENDED
**Expected coverage gain: 20-23% (700-800 products)**

Use Selenium or Playwright to:
1. Navigate to product pages with full browser context
2. Wait for images to load properly
3. Extract image URLs with valid session cookies
4. Download images through browser context

**Pros:**
- Bypasses CDN restrictions
- Gets high-quality images
- Works with dynamic content

**Cons:**
- Slower than direct scraping
- Requires browser automation setup

### Phase 2: API/Feed Investigation
**Expected coverage gain: Variable**

1. Check if Zooplus offers:
   - Product data feeds
   - Affiliate API with images
   - Partner access

2. Alternative sources:
   - Check manufacturer websites
   - Use brand-specific sources

### Phase 3: Manual Resolution
**For remaining ~40-100 products**

1. Discontinued products - mark as unavailable
2. Special bundles - use component images
3. Manual download for critical products

## Implementation Strategy

### Immediate Action (Browser Automation)
```python
# Pseudo-code for browser automation
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait

driver = webdriver.Chrome()
driver.get(product_url)

# Wait for image to load
image = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, "img.ProductImage__image"))
)

# Get image with cookies/session
image_url = image.get_attribute("src")
# Download through browser context
```

### Alternative Headers Approach
Try enhanced headers to mimic real browser:
```python
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': 'https://www.zooplus.com/',
    'Sec-Fetch-Dest': 'image',
    'Sec-Fetch-Mode': 'no-cors',
    'Sec-Fetch-Site': 'same-site',
}
```

## Expected Outcomes

### With Browser Automation
- **Current**: 2,670/3,510 (76.1%)
- **After Phase 1**: ~3,470/3,510 (98.9%)
- **Final**: ~3,500/3,510 (99.7%)

### Without Browser Automation
- Limited improvement possible
- Consider marking CSV imports as "external only"
- Focus on maintaining existing 76% coverage

## Resources Needed

1. **Browser automation setup**:
   - Selenium or Playwright
   - Headless Chrome/Firefox
   - ~3-4 hours for 840 products

2. **Alternative if blocked**:
   - Partner/API access request
   - Manual batch processing
   - Accept current coverage level

## Recommendation

Given that Zooplus blocks direct downloads, **browser automation is the most viable path** to achieving near-100% coverage. The alternative is to accept the current 76% coverage and focus efforts on other sources.

## Next Steps

1. Set up Selenium/Playwright environment
2. Test with 10 products to validate approach
3. Run full batch if successful
4. Document any products that still fail
5. Consider Phase 2/3 for remainders

## Files Created
- `scripts/match_zooplus_fuzzy.py` - Attempted fuzzy matching (no matches found)
- `scripts/scrape_zooplus_csv_images.py` - Direct scraper (blocked by 403)
- This plan document

## Commands for Testing
```bash
# Test browser automation (to be created)
python scripts/scrape_zooplus_browser.py --test

# Check current status
python scripts/check_zooplus_coverage.py
```