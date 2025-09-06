# Image Storage System Plan

## Overview
Complete image storage system for PetFoodExpert product images using Supabase storage bucket.

## Phase 1: Core Infrastructure

### 1. Database Migration (`add_image_url_column.py`)
- Add `image_url` TEXT column to `food_candidates` table
- Safe, idempotent migration script
- Handles errors gracefully with manual fallback option

### 2. Enhanced Image Storage System (`jobs/pfx_url_scraper.py`)
**Features:**
- Download images from PetFoodExpert URLs
- Upload to `dog-food` Supabase bucket
- Generate consistent filenames (slug-based)
- Store bucket URLs in database
- Handle duplicates and errors gracefully

**Image Processing Workflow:**
1. Extract image URL from product page HTML
2. Download image from source URL
3. Generate filename from product slug
4. Upload to Supabase storage bucket
5. Get public bucket URL
6. Store URL in database

**Bucket URL Format:**
`https://[project].supabase.co/storage/v1/object/public/dog-food/[filename].jpg`

## Phase 2: Testing & Validation

### 3. Small Scale Test (5 products)
- Create test file with 5 URLs from `all_pfx_urls.txt`
- Run scraper to verify image download/upload works
- Validate bucket URLs are accessible
- Check database records have proper image URLs

### 4. Backfill Existing Products
- Create separate backfill script for existing products in database
- Query products missing `image_url` but having `source_url`
- Download and upload images for existing records
- Update database with bucket URLs

## Technical Implementation Details

### Image Processing
- **Download**: HTTP request to PetFoodExpert image URL
- **Filename**: Use product slug for consistency (e.g., `canagan-insect-dry-dog.jpg`)
- **Upload**: Supabase storage client upload to `dog-food` bucket
- **URL**: Get public URL from bucket

### Error Handling
- Network failures during download
- Duplicate uploads (check if file exists)
- Invalid/missing images
- Storage quota limits
- Database update failures

### Statistics Tracking
- Images downloaded successfully
- Images uploaded to bucket
- Images failed to download
- Images skipped (already exist)
- Database records updated

## Testing Strategy
1. **Test with 5 new products first**
   - Verify image extraction works
   - Confirm upload to bucket succeeds
   - Check database URLs are correct
   - Validate images are publicly accessible

2. **Backfill existing ~190 products**
   - Process all existing database records
   - Add images to products already in database
   - Update image URLs in bulk

3. **Full 3,804 product harvest**
   - Process complete PetFoodExpert catalog
   - Both new products and images together
   - Complete nutrition + image data

## File Structure
```
/jobs/pfx_url_scraper.py          # Enhanced scraper with image storage
/add_image_url_column.py          # Database migration
/backfill_existing_images.py      # Backfill script for existing products
/test_5_products.txt              # Small test file
/all_pfx_urls.txt                 # Complete URL list (3,804 products)
```

## Success Criteria
- ✅ Database column added successfully
- ✅ Images upload to Supabase bucket
- ✅ Public URLs work and serve images
- ✅ Database records contain correct bucket URLs
- ✅ Error handling prevents scraper crashes
- ✅ Existing products get images backfilled
- ✅ Full catalog harvest includes images

This ensures we have a robust, tested image storage system before processing thousands of products.