# Product Image Download Pipeline

**Date:** September 16, 2025
**Objective:** Download and store product images from AADF and Zooplus to Google Cloud Storage
**Total Images:** ~3,848 (1,183 AADF + 2,670 Zooplus)

## Current Status

### Database Overview (foods_canonical)
- **Total products:** 9,339
- **Products with image URLs:** ~3,547
  - AADF: 877 products with image URLs (from scraped data)
  - Zooplus: 2,670 products with image URLs (media.zooplus.com)
- **Products without image URLs:** ~5,792

### AADF Status
- **Scraped sessions:** 4 (gb1, de1, ca1, us1)
- **Total scraped:** 1,398 products (85% of 1,643 target)
- **Unique images available:** 1,183 (after deduplication)
- **Current progress:** ~80 images downloaded and continuing

### Zooplus Status
- **Total Zooplus products in DB:** 3,510 (identified by `product_url ILIKE '%zooplus%'`)
- **With image URLs:** 2,670 products
- **Without image URLs:** 840 products
- **Download status:** Ready to start

## GCS Storage Structure

```
gs://lupito-content-raw-eu/
  └── product-images/
      ├── aadf/
      │   ├── able_puppy_dry.jpg
      │   ├── acana_adult_large.jpg
      │   └── ... (1,183 images)
      └── zooplus/
          ├── briantos_adult_lamb_rice.jpg
          ├── bozita_robur_sensitive.jpg
          └── ... (2,670 images)
```

## Phase 1: AADF Image Downloads (1,183 images)

### Status
- **Started:** September 16, 2025 8:20 AM
- **Progress:** ~80/1,183 images (6.8%)
- **ETA:** ~2 hours remaining at current rate

### Rate Limiting Strategy

```python
RATE_LIMITS = {
    'daytime': {
        'delay_min': 4,      # 4-6 seconds between requests
        'delay_max': 6,
        'batch_pause': 60    # 1 minute between 50-image batches
    },
    'nighttime': {
        'delay_min': 2,      # 2-3 seconds between requests
        'delay_max': 3,
        'batch_pause': 30    # 30 seconds between batches
    }
}

# Daytime: 9 AM - 10 PM (slower)
# Nighttime: 10 PM - 9 AM (faster)
```

### Download Process

1. **Extract URLs from scraped JSONs in GCS**
   ```python
   # Session folders in GCS
   sessions = [
       "scraped/aadf_images/aadf_images_20250915_150547_gb1/",
       "scraped/aadf_images/aadf_images_20250915_150547_de1/",
       "scraped/aadf_images/aadf_images_20250915_150547_ca1/",
       "scraped/aadf_images/aadf_images_20250915_150436_us1/"
   ]
   # Total: 1,183 unique product images
   ```

2. **Current implementation** (`scripts/download_aadf_images.py`)
   - Loads URLs from GCS scraped data
   - Downloads with respectful delays
   - Uploads to GCS at `product-images/aadf/`
   - Fixed: Removed `blob.make_public()` due to bucket restrictions

### AADF Image URL Pattern
```
https://www.allaboutdogfood.co.uk/storage/products/560x560/{product-slug}-1.jpg
```

## Phase 2: Zooplus Image Downloads (2,670 images)

### Timeline
- **Start:** Can run in parallel with AADF (different servers)
- **Duration:** 8-16 hours depending on time of day
- **Completion:** September 16-17, 2025

### Rate Limiting Strategy

```python
ZOOPLUS_RATE_LIMITS = {
    'daytime': {
        'delay_min': 6,      # 6-8 seconds between requests
        'delay_max': 8,
        'batch_pause': 90    # 1.5 minutes between 50-image batches
    },
    'nighttime': {
        'delay_min': 3,      # 3-4 seconds between requests
        'delay_max': 4,
        'batch_pause': 45    # 45 seconds between batches
    }
}
```

### Required Fix for Zooplus Script

**Current issue:** Script queries `source = 'zooplus_csv_import'` (only 38 products)

**Fix needed:** Query by product URL pattern
```python
# WRONG (current):
query = supabase.table('foods_canonical').select(
    'product_key, image_url'
).eq(
    'source', 'zooplus_csv_import'
)

# CORRECT (needed):
query = supabase.table('foods_canonical').select(
    'product_key, image_url'
).ilike(
    'product_url', '%zooplus%'
).not_.is_(
    'image_url', 'null'
)
# This will return 2,670 products with image URLs
```

### Zooplus Image URL Patterns
```
https://media.zooplus.com/bilder/{size}/400/{product_id}.jpg
https://media.zooplus.com/bilder/{char}/400/{product_id}_{variant}.jpg
```

## Phase 3: Database Updates

### Update Strategy

After downloads complete, update the database:

```python
# For AADF products
UPDATE foods_canonical
SET
  gcs_image_url = 'gs://lupito-content-raw-eu/product-images/aadf/' || product_key || '.jpg',
  image_source = 'gcs_aadf',
  image_downloaded_at = NOW(),
  updated_at = NOW()
WHERE product_key IN (downloaded_product_keys)
AND product_url ILIKE '%allaboutdogfood%';

# For Zooplus products
UPDATE foods_canonical
SET
  gcs_image_url = 'gs://lupito-content-raw-eu/product-images/zooplus/' || product_key || '.jpg',
  image_source = 'gcs_zooplus',
  image_downloaded_at = NOW(),
  updated_at = NOW()
WHERE product_key IN (downloaded_product_keys)
AND product_url ILIKE '%zooplus%';
```

## Implementation Scripts

### 1. AADF Download Script
**File:** `scripts/download_aadf_images.py`
**Status:** ✅ Running (80/1,183 downloaded)

Key features:
- Loads URLs from GCS scraped JSONs
- Adaptive rate limiting (day/night)
- Batch processing with pauses
- No checkpoint needed (smaller dataset)

### 2. Zooplus Download Script
**File:** `scripts/download_zooplus_images.py`
**Status:** ❌ Needs fix (wrong query)

Key features:
- Checkpoint/resume support for 2,670 images
- More conservative rate limits
- Can run in parallel with AADF
- Different user agent for Zooplus

### 3. Monitoring Script
**File:** `scripts/monitor_image_downloads.py`
**Status:** ✅ Created

Real-time monitoring:
- Download progress for both sources
- Success/failure rates
- ETA calculations
- Failed downloads tracking

## Error Handling

### Common Issues Encountered

1. **GCS Public Access Prevention** (FIXED)
   - Error: `412 PATCH: The member bindings allUsers and allAuthenticatedUsers are not allowed`
   - Solution: Removed `blob.make_public()` calls

2. **Zooplus Query Issue** (TO FIX)
   - Error: No products found with `source='zooplus_csv_import'`
   - Solution: Query by `product_url ILIKE '%zooplus%'`

### Retry Strategy
```python
MAX_RETRIES = 3
RETRY_DELAYS = [10, 30, 60]  # Exponential backoff

for attempt in range(MAX_RETRIES):
    try:
        download_image(url)
        break
    except Exception as e:
        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAYS[attempt])
        else:
            log_permanent_failure(url, e)
```

## Headers Configuration

```python
# AADF Headers
AADF_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Accept': 'image/jpeg, image/png, image/webp, image/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive'
}

# Zooplus Headers (different user agent)
ZOOPLUS_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'image/jpeg, image/png, image/webp, image/*',
    'Accept-Language': 'en-US,en;q=0.9,de;q=0.8',
    'Referer': 'https://www.zooplus.com/'
}
```

## Parallel Processing Capability

Since AADF and Zooplus use different servers, both can run simultaneously:

- **AADF servers:** allaboutdogfood.co.uk (and various retailer sites)
- **Zooplus servers:** media.zooplus.com

This allows for efficient parallel downloading without overloading any single server.

## Commands

### Monitor AADF Progress (Currently Running)
```bash
tail -f logs/aadf_image_download_*.log
```

### Fix and Start Zooplus Download
```bash
# After fixing the query issue
python scripts/download_zooplus_images.py
```

### Monitor Both Downloads
```bash
python scripts/monitor_image_downloads.py --refresh 30
```

### Verify Downloads
```bash
# Count AADF images
gsutil ls gs://lupito-content-raw-eu/product-images/aadf/ | wc -l

# Count Zooplus images
gsutil ls gs://lupito-content-raw-eu/product-images/zooplus/ | wc -l
```

## Timeline Summary

| Phase | Start | Duration | Images | Status |
|-------|-------|----------|--------|--------|
| AADF Downloads | Sept 16, 8:20 AM | ~3 hours | 1,183 | 🟡 In Progress (80/1,183) |
| Zooplus Downloads | Sept 16 (parallel) | 8-16 hours | 2,670 | 🔴 Needs Fix |
| Database Updates | After downloads | 1 hour | 3,848 | ⏳ Pending |
| **Total Completion** | **Sept 16-17** | **16-24 hours** | **3,848** | **In Progress** |

## Cost Analysis

### Storage Costs
- Total size: ~1.2GB (assuming 300KB average per image)
- Monthly cost: ~$0.02
- Annual cost: ~$0.25

### Bandwidth Costs
- Initial download: ~1.2GB (one-time)
- Serving: ~$0.12/GB transferred

## Success Metrics

### Expected Outcomes
- **AADF:** 1,183 images downloaded to GCS
- **Zooplus:** 2,670 images downloaded to GCS
- **Database:** 3,848 products with GCS image paths
- **Coverage improvement:** From 38% to 79% products with images

### Quality Checks
- Verify image dimensions (should be > 100x100)
- Check file sizes (typically 50KB - 500KB)
- Validate image format (JPEG/PNG)
- Test random sample of URLs

## Next Steps

1. ✅ AADF downloads running
2. 🔧 Fix Zooplus query to use `product_url ILIKE '%zooplus%'`
3. ⏳ Start Zooplus downloads in parallel
4. ⏳ Monitor both downloads
5. ⏳ Update database with GCS URLs
6. ⏳ Verify all images accessible
7. ⏳ Address 840 Zooplus products without images (future task)

## Notes on Missing Images

### AADF
- 1,643 target products
- 1,398 scraped (85% success)
- 245 products couldn't be scraped (may not have images)

### Zooplus
- 3,510 total Zooplus products
- 2,670 with image URLs (76%)
- 840 without image URLs (24% - may need additional scraping)

---

**Document Version:** 2.0
**Updated:** September 16, 2025
**Author:** Database Team
**Current Status:** AADF downloading, Zooplus pending fix