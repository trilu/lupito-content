#!/usr/bin/env python3
"""
Update database with GCS image URLs - Fixed version for AADF key format
Handles conversion between pipe-separated DB keys and underscore-separated GCS keys
"""
import os
from dotenv import load_dotenv
from supabase import create_client
from google.cloud import storage
from datetime import datetime
import logging

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")
GCS_PUBLIC_URL = "https://storage.googleapis.com/lupito-content-raw-eu"

# Set up GCS authentication
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/sergiubiris/Desktop/lupito-content/secrets/gcp-sa.json'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseUpdater:
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(GCS_BUCKET)

    def get_gcs_images(self, prefix):
        """Get all images from GCS for a given prefix"""
        logger.info(f"Listing GCS images in {prefix}/")
        images = {}

        blobs = self.bucket.list_blobs(prefix=f"product-images/{prefix}/")
        for blob in blobs:
            # Extract product_key from filename
            filename = blob.name.split('/')[-1]
            if filename.endswith('.jpg'):
                product_key = filename[:-4]  # Remove .jpg
                images[product_key] = f"{GCS_PUBLIC_URL}/{blob.name}"

        logger.info(f"Found {len(images)} images in {prefix}")
        return images

    def update_aadf_products(self):
        """Update AADF products with GCS URLs - with key format conversion"""
        logger.info("Updating AADF products with key format conversion...")

        # Get GCS images
        gcs_images = self.get_gcs_images("aadf")

        if not gcs_images:
            logger.warning("No AADF images found in GCS")
            return 0

        # Get ALL AADF products from database (with pagination)
        logger.info("Finding AADF products to update...")
        all_aadf_products = []
        batch_size = 1000
        offset = 0

        while True:
            result = self.supabase.table('foods_canonical').select(
                'product_key, image_url'
            ).ilike(
                'product_url', '%allaboutdogfood%'
            ).range(offset, offset + batch_size - 1).execute()

            all_aadf_products.extend(result.data)
            logger.info(f"Fetched batch {offset//batch_size + 1}: {len(result.data)} products")

            if len(result.data) < batch_size:
                break
            offset += batch_size

        logger.info(f"Total AADF products in database: {len(all_aadf_products)}")

        # Update products with key format conversion
        updated = 0
        skipped_already_has_gcs = 0
        skipped_no_match = 0

        for product in all_aadf_products:
            db_key = product['product_key']
            current_url = product.get('image_url')

            # Skip if already has a GCS URL
            if current_url and 'storage.googleapis.com' in current_url:
                skipped_already_has_gcs += 1
                continue

            # Convert database key (pipe format) to GCS key (underscore format)
            gcs_format_key = db_key.replace('|', '_')

            # Check if we have a GCS image for this product
            if gcs_format_key in gcs_images:
                gcs_url = gcs_images[gcs_format_key]

                try:
                    # Update the database
                    update_result = self.supabase.table('foods_canonical').update({
                        'image_url': gcs_url,
                        'updated_at': datetime.now().isoformat()
                    }).eq('product_key', db_key).execute()

                    if update_result.data:
                        updated += 1
                        if updated % 100 == 0:
                            logger.info(f"Updated {updated} AADF products...")
                except Exception as e:
                    logger.error(f"Error updating {db_key}: {e}")
            else:
                skipped_no_match += 1

        logger.info(f"✅ Updated {updated} AADF products with GCS URLs")
        logger.info(f"   Skipped {skipped_already_has_gcs} (already had GCS URLs)")
        logger.info(f"   Skipped {skipped_no_match} (no matching GCS image)")
        return updated

    def update_zooplus_products(self):
        """Update Zooplus products with GCS URLs - original logic works fine"""
        logger.info("Updating Zooplus products...")

        # Get GCS images
        gcs_images = self.get_gcs_images("zooplus")

        if not gcs_images:
            logger.warning("No Zooplus images found in GCS")
            return 0

        # Get all product keys as a list
        product_keys = list(gcs_images.keys())

        # Process in batches of 100
        batch_size = 100
        updated_total = 0

        for i in range(0, len(product_keys), batch_size):
            batch_keys = product_keys[i:i+batch_size]

            try:
                # Get all products in this batch
                result = self.supabase.table('foods_canonical').select(
                    'product_key, image_url'
                ).in_('product_key', batch_keys).execute()

                if result.data:
                    # Update each product that needs it
                    for product in result.data:
                        product_key = product['product_key']
                        current_url = product.get('image_url')

                        # Only update if image_url is NULL or not already a GCS URL
                        if not current_url or 'storage.googleapis.com' not in (current_url or ''):
                            gcs_url = gcs_images[product_key]
                            update_result = self.supabase.table('foods_canonical').update({
                                'image_url': gcs_url,
                                'updated_at': datetime.now().isoformat()
                            }).eq('product_key', product_key).execute()

                            if update_result.data:
                                updated_total += 1

                logger.info(f"Processed batch {i//batch_size + 1}: {updated_total} updated so far")

            except Exception as e:
                logger.error(f"Error processing batch: {e}")

        logger.info(f"✅ Updated {updated_total} Zooplus products with GCS URLs")
        return updated_total

    def verify_updates(self):
        """Verify database updates"""
        logger.info("Verifying database updates...")

        # Check products with GCS URLs
        gcs_result = self.supabase.table('foods_canonical').select(
            'product_key', count='exact'
        ).like('image_url', '%storage.googleapis.com%').execute()

        logger.info(f"Products with GCS URLs: {gcs_result.count}")

        # Check AADF products specifically
        aadf_with_gcs = self.supabase.table('foods_canonical').select(
            'product_key', count='exact'
        ).ilike('product_url', '%allaboutdogfood%').like('image_url', '%storage.googleapis.com%').execute()

        logger.info(f"AADF products with GCS URLs: {aadf_with_gcs.count}")

        # Check Zooplus products specifically
        zooplus_with_gcs = self.supabase.table('foods_canonical').select(
            'product_key', count='exact'
        ).ilike('product_url', '%zooplus%').like('image_url', '%storage.googleapis.com%').execute()

        logger.info(f"Zooplus products with GCS URLs: {zooplus_with_gcs.count}")

    def run(self):
        """Main update process"""
        logger.info("="*60)
        logger.info("DATABASE UPDATE - GCS IMAGE URLs (FIXED)")
        logger.info("="*60)

        # Update AADF with key format conversion
        aadf_updated = self.update_aadf_products()

        # Update Zooplus (original logic works fine)
        zooplus_updated = self.update_zooplus_products()

        # Verify
        self.verify_updates()

        logger.info("="*60)
        logger.info(f"COMPLETE: Updated {aadf_updated + zooplus_updated} products")
        logger.info(f"  AADF: {aadf_updated}")
        logger.info(f"  Zooplus: {zooplus_updated}")
        logger.info("="*60)

if __name__ == "__main__":
    updater = DatabaseUpdater()
    updater.run()