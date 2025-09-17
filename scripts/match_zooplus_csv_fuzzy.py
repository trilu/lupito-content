#!/usr/bin/env python3
"""
Zooplus CSV Import Fuzzy Matching
Matches zooplus_csv_import products against existing products with images
Uses optimized approach based on brand matching + name similarity
"""
import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime
import logging
import json
from difflib import SequenceMatcher
import re

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ZooplusCSVMatcher:
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    def get_csv_import_products(self):
        """Get all Zooplus CSV import products without images"""
        logger.info("Loading Zooplus CSV import products...")

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

        logger.info(f"Found {len(all_products)} CSV import products without images")
        return all_products

    def get_existing_products_with_images(self):
        """Get all existing products (non-CSV) that have images, organized by brand"""
        logger.info("Loading existing products with images...")

        products_by_brand = {}
        batch_size = 1000
        offset = 0

        while True:
            result = self.supabase.table('foods_canonical').select(
                'product_key, brand, product_name, image_url'
            ).not_.is_(
                'image_url', 'null'
            ).neq(
                'source', 'zooplus_csv_import'
            ).range(offset, offset + batch_size - 1).execute()

            for product in result.data:
                brand = product.get('brand', '').lower().strip()
                if brand:
                    if brand not in products_by_brand:
                        products_by_brand[brand] = []
                    products_by_brand[brand].append(product)

            if len(result.data) < batch_size:
                break
            offset += batch_size

        total_products = sum(len(products) for products in products_by_brand.values())
        logger.info(f"Loaded {total_products} existing products across {len(products_by_brand)} brands")
        return products_by_brand

    def normalize_name(self, name):
        """Normalize product name for better matching"""
        if not name:
            return ""

        # Convert to lowercase
        name = name.lower()

        # Remove common variations
        name = re.sub(r'\s*[-–]\s*', ' ', name)  # Replace dashes with spaces
        name = re.sub(r'\s*[&+]\s*', ' ', name)  # Replace & and + with spaces
        name = re.sub(r'\s+', ' ', name)  # Normalize spaces
        name = re.sub(r'[^\w\s]', ' ', name)  # Remove special characters
        name = name.strip()

        return name

    def calculate_similarity(self, name1, name2):
        """Calculate similarity between two product names"""
        norm1 = self.normalize_name(name1)
        norm2 = self.normalize_name(name2)

        if not norm1 or not norm2:
            return 0

        # Use SequenceMatcher for overall similarity
        overall_score = SequenceMatcher(None, norm1, norm2).ratio()

        # Bonus for word overlap
        words1 = set(norm1.split())
        words2 = set(norm2.split())

        if len(words1) > 0 and len(words2) > 0:
            word_overlap = len(words1.intersection(words2)) / len(words1.union(words2))
            # Weighted combination
            final_score = (overall_score * 0.7) + (word_overlap * 0.3)
        else:
            final_score = overall_score

        return final_score

    def find_best_match(self, csv_product, existing_by_brand):
        """Find best matching product for a CSV import product"""
        csv_brand = csv_product.get('brand', '').lower().strip()
        csv_name = csv_product.get('product_name', '')

        if not csv_brand or csv_brand not in existing_by_brand:
            return None, 0, 'no_brand_match'

        best_match = None
        best_score = 0

        # Search within same brand
        for existing in existing_by_brand[csv_brand]:
            existing_name = existing.get('product_name', '')
            score = self.calculate_similarity(csv_name, existing_name)

            if score > best_score:
                best_score = score
                best_match = existing

        if best_score > 0.75:
            return best_match, best_score, 'high_confidence'
        elif best_score > 0.60:
            return best_match, best_score, 'medium_confidence'
        elif best_score > 0.45:
            return best_match, best_score, 'low_confidence'
        else:
            return None, best_score, 'no_match'

    def update_matched_products(self, matches):
        """Update database with matched products"""
        updated = 0

        for csv_key, (existing_product, score, confidence, match_type) in matches.items():
            try:
                result = self.supabase.table('foods_canonical').update({
                    'image_url': existing_product['image_url'],
                    'updated_at': datetime.now().isoformat()
                }).eq('product_key', csv_key).execute()

                if result.data:
                    updated += 1
                    logger.info(f"✅ Updated {csv_key} -> {existing_product['product_key']} ({match_type})")

            except Exception as e:
                logger.error(f"Error updating {csv_key}: {e}")

        return updated

    def run(self, dry_run=True):
        """Main fuzzy matching process"""
        logger.info("="*70)
        logger.info("ZOOPLUS CSV IMPORT FUZZY MATCHING")
        logger.info("="*70)

        # Load data
        csv_products = self.get_csv_import_products()
        existing_by_brand = self.get_existing_products_with_images()

        # Track matches by confidence level
        matches = {}
        confidence_counts = {
            'high_confidence': 0,
            'medium_confidence': 0,
            'low_confidence': 0,
            'no_match': 0
        }

        logger.info("Starting fuzzy matching process...")

        for i, csv_product in enumerate(csv_products):
            if i % 50 == 0:
                logger.info(f"Processing {i}/{len(csv_products)}...")

            best_match, score, match_type = self.find_best_match(csv_product, existing_by_brand)

            if best_match:
                matches[csv_product['product_key']] = (best_match, score, match_type, match_type)
                confidence_counts[match_type] += 1

                if match_type == 'high_confidence':
                    logger.debug(f"HIGH: {csv_product['product_key']} -> {best_match['product_key']} ({score:.2f})")
            else:
                confidence_counts['no_match'] += 1

        # Results summary
        logger.info("="*70)
        logger.info("MATCHING RESULTS")
        logger.info("="*70)
        logger.info(f"Total CSV products analyzed: {len(csv_products)}")
        logger.info(f"High confidence matches: {confidence_counts['high_confidence']} ({confidence_counts['high_confidence']/len(csv_products)*100:.1f}%)")
        logger.info(f"Medium confidence matches: {confidence_counts['medium_confidence']} ({confidence_counts['medium_confidence']/len(csv_products)*100:.1f}%)")
        logger.info(f"Low confidence matches: {confidence_counts['low_confidence']} ({confidence_counts['low_confidence']/len(csv_products)*100:.1f}%)")
        logger.info(f"No matches: {confidence_counts['no_match']} ({confidence_counts['no_match']/len(csv_products)*100:.1f}%)")

        total_matches = sum(confidence_counts[k] for k in ['high_confidence', 'medium_confidence', 'low_confidence'])
        logger.info(f"Total potential matches: {total_matches} ({total_matches/len(csv_products)*100:.1f}%)")

        # Show sample matches
        if matches:
            logger.info("\nSample matches:")
            count = 0
            for csv_key, (existing, score, confidence, _) in matches.items():
                if count >= 10:
                    break
                if confidence in ['high_confidence', 'medium_confidence']:
                    logger.info(f"  {confidence.upper()}: {csv_key}")
                    logger.info(f"    -> {existing['product_key']} (similarity: {score:.2f})")
                    count += 1

        # Save results for review
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Save all matches for review
        all_matches_file = f'/tmp/zooplus_csv_matches_{timestamp}.json'
        with open(all_matches_file, 'w') as f:
            json.dump({
                'summary': {
                    'total_csv_products': len(csv_products),
                    'total_matches': total_matches,
                    'confidence_breakdown': confidence_counts,
                    'match_rate': f"{total_matches/len(csv_products)*100:.1f}%"
                },
                'matches': {
                    csv_key: {
                        'existing_key': existing['product_key'],
                        'existing_name': existing['product_name'],
                        'similarity_score': score,
                        'confidence': confidence,
                        'image_url': existing['image_url']
                    }
                    for csv_key, (existing, score, confidence, _) in matches.items()
                }
            }, f, indent=2)

        logger.info(f"\nAll matches saved to {all_matches_file}")

        # Filter high confidence matches for database update
        high_confidence_matches = {
            k: v for k, v in matches.items()
            if v[2] == 'high_confidence'
        }

        if high_confidence_matches:
            high_conf_file = f'/tmp/zooplus_csv_high_confidence_{timestamp}.json'
            with open(high_conf_file, 'w') as f:
                json.dump({
                    csv_key: {
                        'existing_key': existing['product_key'],
                        'similarity_score': score,
                        'image_url': existing['image_url']
                    }
                    for csv_key, (existing, score, confidence, _) in high_confidence_matches.items()
                }, f, indent=2)

            logger.info(f"High confidence matches saved to {high_conf_file}")

            # Ask about database update
            if not dry_run:
                response = input(f"\nUpdate {len(high_confidence_matches)} high confidence matches in database? (y/n): ")
                if response.lower() == 'y':
                    updated = self.update_matched_products(high_confidence_matches)
                    logger.info(f"✅ Successfully updated {updated} products")

                    # Calculate remaining products for ScrapingBee
                    remaining = len(csv_products) - len(high_confidence_matches)
                    logger.info(f"\n📊 NEXT STEPS:")
                    logger.info(f"  Products recovered via fuzzy matching: {len(high_confidence_matches)}")
                    logger.info(f"  Products still needing images: {remaining}")
                    logger.info(f"  Recommended: Use ScrapingBee for remaining {remaining} products")
                else:
                    logger.info("Database update cancelled")
            else:
                logger.info(f"\n🔍 DRY RUN COMPLETE")
                logger.info(f"  Would update {len(high_confidence_matches)} high confidence matches")
                logger.info(f"  {len(csv_products) - len(high_confidence_matches)} products would still need scraping")
        else:
            logger.info("\n❌ No high confidence matches found")
            logger.info("All 840 products will need ScrapingBee scraping")

        return matches

if __name__ == "__main__":
    import sys

    matcher = ZooplusCSVMatcher()

    # Check if dry run
    dry_run = '--dry-run' in sys.argv or len(sys.argv) == 1

    if dry_run:
        logger.info("Running in DRY RUN mode (no database updates)")
    else:
        logger.info("Running in LIVE mode (will prompt for database updates)")

    matcher.run(dry_run=dry_run)