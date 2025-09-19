# Zooplus ScrapingBee Implementation Plan
*Created: September 16, 2025*

## Current Status After Fuzzy Matching ✅ COMPLETE

- **Total Zooplus products**: 3,510
- **With images**: 2,780 (79.2%)
- **Remaining for scraping**: 730 products (all CSV imports)
- **Fuzzy matching recovered**: 110 products (+3.1% coverage)
- **Updated**: September 16, 2025 - High confidence matches applied to database

## Target Achievement

- **Current coverage**: 79.2%
- **Target coverage**: 99%+
- **Expected final**: ~3,460/3,510 products with images

## Implementation Strategy

### Phase 1: ScrapingBee Image URL Extraction
Use the existing ScrapingBee orchestrator to extract image URLs from product pages.

#### Modifications Needed:
1. **Target the 730 CSV import products** instead of ingredients scraping
2. **Extract image URLs** instead of ingredients
3. **Save to GCS** as JSON with image URLs
4. **Process into database** to populate `image_url` field

### Phase 2: Image Download
Once image URLs are extracted:
1. Use existing `download_zooplus_images.py` infrastructure
2. Download images from extracted URLs to GCS
3. Update database with final GCS URLs

## ScrapingBee Configuration

### Session Settings
```python
session_configs = [
    {"name": "zooplus_img_us", "country_code": "us", "min_delay": 15, "max_delay": 25, "batch_size": 12},
    {"name": "zooplus_img_gb", "country_code": "gb", "min_delay": 20, "max_delay": 30, "batch_size": 12},
    {"name": "zooplus_img_de", "country_code": "de", "min_delay": 25, "max_delay": 35, "batch_size": 12}
]
```

### Extraction Pattern
```python
# Image URL extraction patterns for Zooplus
image_selectors = [
    'img.ProductImage__image',
    'div.ProductImage img',
    'picture.ProductImage__picture img',
    'div.swiper-slide img',
    'meta[property="og:image"]'  # Fallback
]
```

## Expected Performance

### Conservative Estimate
- **Rate**: 50-80 products/hour (3 sessions combined)
- **Time to completion**: 9-15 hours
- **Success rate**: 80-85% image URL extraction
- **Final coverage**: ~95-96%

### Optimistic Estimate
- **Rate**: 100-120 products/hour
- **Time to completion**: 6-8 hours
- **Success rate**: 90-95% image URL extraction
- **Final coverage**: ~98-99%

## Scripts to Create/Modify

### 1. Modified Orchestrated Scraper
```bash
scripts/scrape_zooplus_images_orchestrated.py
```
- Extract image URLs instead of ingredients
- Target CSV import products specifically
- Save extracted URLs to GCS for processing

### 2. Image URL Processor
```bash
scripts/process_zooplus_image_urls.py
```
- Read extracted URLs from GCS
- Update database `image_url` field
- Trigger image downloads

### 3. Monitor Dashboard
```bash
scripts/monitor_zooplus_images.py
```
- Track image URL extraction progress
- Monitor final image download progress

## Database Query for Targets

```sql
SELECT product_key, product_name, brand, product_url
FROM foods_canonical
WHERE source = 'zooplus_csv_import'
AND image_url IS NULL
ORDER BY product_key
LIMIT batch_size OFFSET session_offset
```

## Success Metrics

### Milestones
- **25%**: 183 products processed (81.4% total coverage)
- **50%**: 365 products processed (89.6% total coverage)
- **75%**: 548 products processed (94.8% total coverage)
- **100%**: 730 products processed (99%+ total coverage)

### Quality Targets
- **Image URL extraction**: 85%+ success rate
- **Valid image URLs**: 90%+ of extracted URLs work
- **Final image downloads**: 95%+ success rate

## Implementation Commands

```bash
# 1. Start ScrapingBee orchestrator for images
python scripts/scrape_zooplus_images_orchestrated.py

# 2. Monitor progress
python scripts/monitor_zooplus_images.py

# 3. Process extracted URLs
python scripts/process_zooplus_image_urls.py

# 4. Download final images
python scripts/download_zooplus_images.py

# 5. Verify final coverage
python scripts/check_zooplus_final_status.py
```

## Risk Mitigation

### Potential Issues
1. **Rate limiting**: Use 3 country sessions with delays
2. **Image URL changes**: Multiple extraction patterns
3. **Failed extractions**: Log for manual review
4. **Download failures**: Existing retry infrastructure

### Fallback Plans
1. **Medium confidence matches**: Review 111 products from fuzzy matching
2. **Manual verification**: Sample check extracted URLs
3. **External sources**: Manufacturer websites for critical products

## Resource Requirements

### ScrapingBee Credits
- **Estimated**: 730-1,000 API calls
- **Cost**: ~$15-25 depending on success rate
- **Duration**: 6-15 hours depending on performance

### Storage
- **GCS**: ~50MB for extracted JSON files
- **Images**: ~200-300MB for final image files

## Next Immediate Steps

1. ✅ **Complete fuzzy matching** (DONE - 110 products recovered)
2. 🔄 **Create image extraction orchestrator**
3. 🔄 **Test with 10 products**
4. 🔄 **Run full extraction (730 products)**
5. 🔄 **Process URLs and download images**
6. 🔄 **Verify 99% coverage achieved**

---

**Expected Completion**: Within 24-48 hours
**Final Coverage**: 99%+ (3,460+ of 3,510 products with images)