#!/usr/bin/env python3
"""
Zooplus fuzzy matching script
Attempts to match zooplus_csv_import products with existing GCS images
"""
import os
from dotenv import load_dotenv
from supabase import create_client
from google.cloud import storage
from datetime import datetime
import logging
import re
from difflib import SequenceMatcher
import json

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")
GCS_PUBLIC_URL = "https://storage.googleapis.com/lupito-content-raw-eu"

# Set up GCS authentication
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/sergiubiris/Desktop/lupito-content/secrets/gcp-sa.json'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ZooplusMatcher:
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(GCS_BUCKET)

    def get_gcs_images(self):
        """Get all Zooplus images from GCS"""
        logger.info("Loading GCS Zooplus images...")
        images = {}
        blobs = self.bucket.list_blobs(prefix="product-images/zooplus/")

        for blob in blobs:
            filename = blob.name.split('/')[-1]
            if filename.endswith('.jpg'):
                product_key = filename[:-4]  # Remove .jpg
                images[product_key] = f"{GCS_PUBLIC_URL}/{blob.name}"

        logger.info(f"Found {len(images)} Zooplus images in GCS")
        return images

    def get_unmatched_products(self):
        """Get Zooplus products without images (all from csv_import)"""
        logger.info("Loading unmatched Zooplus products...")

        all_products = []
        batch_size = 1000
        offset = 0

        while True:
            result = self.supabase.table('foods_canonical').select(
                'product_key, brand, product_name, product_url'
            ).eq(
                'source', 'zooplus_csv_import'
            ).is_(
                'image_url', 'null'
            ).range(offset, offset + batch_size - 1).execute()

            all_products.extend(result.data)

            if len(result.data) < batch_size:
                break
            offset += batch_size

        logger.info(f"Found {len(all_products)} Zooplus CSV import products without images")
        return all_products

    def normalize_key(self, key):
        """Normalize a product key for better matching"""
        key = key.lower()

        # Remove special characters but keep structure
        key = re.sub(r'[^\w_|]', '', key)

        # Remove duplicate underscores
        key = re.sub(r'_+', '_', key)

        # Remove trailing/leading underscores
        key = key.strip('_')

        return key

    def generate_key_variations(self, product):
        """Generate possible key variations for a Zooplus product"""
        variations = []

        # Original key with pipe to underscore
        base_key = product['product_key'].replace('|', '_')
        variations.append(base_key)

        # Normalized version
        variations.append(self.normalize_key(base_key))

        # Extract brand and product name from key parts
        parts = product['product_key'].split('|')
        if len(parts) >= 2:
            brand_part = parts[0]
            name_part = parts[1]
            type_part = parts[2] if len(parts) >= 3 else ''

            # Try different combinations
            variations.append(f"{brand_part}_{name_part}")
            variations.append(f"{brand_part}_{name_part}_{type_part}")

            # Try without numbers in product names (common in pack sizes)
            name_no_nums = re.sub(r'\d+x\d+g?', '', name_part)
            name_no_nums = re.sub(r'\d+_x_\d+g?', '', name_no_nums)
            if name_no_nums != name_part:
                variations.append(f"{brand_part}_{name_no_nums}_{type_part}")
                variations.append(f"{brand_part}_{name_no_nums}")

            # Try simplified versions
            # Remove common words like "economy_pack", "saver_pack", etc.
            simplified = name_part
            for term in ['economy_pack_', 'saver_pack_', '_free', '_dog', '_adult', '_puppy']:
                simplified = simplified.replace(term, '')
            if simplified != name_part:
                variations.append(f"{brand_part}_{simplified}_{type_part}")

        # Try extracting from URL if available
        url = product.get('product_url', '')
        if url:
            # Extract product ID from Zooplus URL
            match = re.search(r'/(\d+)\?activeVariant=(\d+)', url)
            if match:
                product_id = match.group(1)
                variant_id = match.group(2)
                variations.append(f"zooplus_{product_id}")
                variations.append(f"zooplus_{variant_id}")
                variations.append(product_id)
                variations.append(variant_id)

        return list(set(variations))  # Remove duplicates

    def calculate_similarity(self, str1, str2):
        """Calculate similarity between two strings"""
        return SequenceMatcher(None, str1, str2).ratio()

    def find_fuzzy_match(self, product, gcs_keys):
        """Try to find a fuzzy match for a product in GCS keys"""
        # First try exact variations
        variations = self.generate_key_variations(product)

        for var in variations:
            normalized_var = self.normalize_key(var)
            for gcs_key in gcs_keys:
                normalized_gcs = self.normalize_key(gcs_key)
                if normalized_var == normalized_gcs:
                    return gcs_key, 'exact_variation'

        # Try fuzzy matching with high threshold
        best_match = None
        best_score = 0
        best_gcs_key = None

        for var in variations:
            for gcs_key in gcs_keys:
                score = self.calculate_similarity(
                    self.normalize_key(var),
                    self.normalize_key(gcs_key)
                )
                if score > best_score and score > 0.80:  # 80% similarity threshold for Zooplus
                    best_score = score
                    best_match = var
                    best_gcs_key = gcs_key

        if best_gcs_key:
            return best_gcs_key, f'fuzzy_{best_score:.2f}'

        return None, None

    def update_matched_products(self, matches):
        """Update database with matched products"""
        updated = 0

        for product_key, (gcs_key, gcs_url, match_type) in matches.items():
            try:
                result = self.supabase.table('foods_canonical').update({
                    'image_url': gcs_url,
                    'updated_at': datetime.now().isoformat()
                }).eq('product_key', product_key).execute()

                if result.data:
                    updated += 1
                    logger.info(f"Updated {product_key} -> {gcs_key} ({match_type})")

            except Exception as e:
                logger.error(f"Error updating {product_key}: {e}")

        return updated

    def run(self):
        """Main fuzzy matching process"""
        logger.info("="*60)
        logger.info("ZOOPLUS FUZZY MATCHING PROCESS")
        logger.info("="*60)

        # Load data
        gcs_images = self.get_gcs_images()
        gcs_keys = set(gcs_images.keys())
        unmatched_products = self.get_unmatched_products()

        # Track matches
        matches = {}
        match_types = {'exact_variation': 0, 'fuzzy': 0}

        # Try to match each product
        logger.info("Starting fuzzy matching...")
        for i, product in enumerate(unmatched_products):
            if i % 50 == 0:
                logger.info(f"Processing product {i}/{len(unmatched_products)}...")

            gcs_match, match_type = self.find_fuzzy_match(product, gcs_keys)

            if gcs_match:
                matches[product['product_key']] = (
                    gcs_match,
                    gcs_images[gcs_match],
                    match_type
                )

                if 'fuzzy' in match_type:
                    match_types['fuzzy'] += 1
                else:
                    match_types['exact_variation'] += 1

                logger.debug(f"Matched: {product['product_key']} -> {gcs_match} ({match_type})")

        # Report results
        logger.info("="*60)
        logger.info("MATCHING RESULTS")
        logger.info("="*60)
        logger.info(f"Total unmatched products: {len(unmatched_products)}")
        logger.info(f"Total matches found: {len(matches)}")
        logger.info(f"  - Exact variations: {match_types['exact_variation']}")
        logger.info(f"  - Fuzzy matches: {match_types['fuzzy']}")
        if len(unmatched_products) > 0:
            logger.info(f"Match rate: {len(matches)/len(unmatched_products)*100:.1f}%")

        # Sample matches
        if matches:
            logger.info("\nSample matches:")
            for key, (gcs_key, _, match_type) in list(matches.items())[:10]:
                logger.info(f"  {key} -> {gcs_key} ({match_type})")

            # Save all matches to file for review
            matches_file = f'/tmp/zooplus_fuzzy_matches_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            with open(matches_file, 'w') as f:
                json.dump(
                    {k: {'gcs_key': v[0], 'match_type': v[2]}
                     for k, v in matches.items()},
                    f,
                    indent=2
                )
            logger.info(f"\nAll matches saved to {matches_file}")

            # Ask for confirmation before updating
            logger.info("\nReady to update database with matches...")
            response = input(f"Update {len(matches)} products? (y/n): ")

            if response.lower() == 'y':
                updated = self.update_matched_products(matches)
                logger.info(f"✅ Successfully updated {updated} products")
            else:
                logger.info("Update cancelled by user")
        else:
            logger.info("No fuzzy matches found")
            logger.info("\nThis suggests the CSV import products may be:")
            logger.info("  1. Different products not in our GCS collection")
            logger.info("  2. Need to be scraped fresh from Zooplus")
            logger.info("  3. Discontinued products no longer available")

if __name__ == "__main__":
    matcher = ZooplusMatcher()
    matcher.run()