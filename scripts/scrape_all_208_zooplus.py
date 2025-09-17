#!/usr/bin/env python3
"""
Scrape all 208 pending Zooplus products using proven configuration
Based on successful test with 5 URLs
"""

import os
import json
import time
import re
import random
from datetime import datetime
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import requests
from google.cloud import storage
from supabase import create_client

load_dotenv()

# Configuration
SCRAPINGBEE_API_KEY = os.getenv('SCRAPING_BEE')
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")

# Initialize clients
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
storage_client = storage.Client()
bucket = storage_client.bucket(GCS_BUCKET)

class ZooplusFullScraper:
    def __init__(self):
        self.session_id = datetime.now().strftime('%Y%m%d_%H%M%S_full_208')
        self.gcs_folder = f"scraped/zooplus_retry/{self.session_id}"

        self.stats = {
            'total': 0,
            'success': 0,
            'with_images': 0,
            'with_ingredients': 0,
            'with_nutrition': 0,
            'pattern_8_success': 0,
            'errors': 0,
            'start_time': datetime.now()
        }

        print(f"🚀 ZOOPLUS FULL SCRAPER STARTED")
        print(f"Session: {self.session_id}")
        print(f"GCS: gs://{GCS_BUCKET}/{self.gcs_folder}/")
        print()

    def get_pending_products(self):
        """Get all 208 pending Zooplus products"""
        print("Fetching pending Zooplus products...")

        # Load from our retry JSON file
        if os.path.exists('retry_zooplus_pending.json'):
            with open('retry_zooplus_pending.json', 'r') as f:
                products = json.load(f)
                print(f"Loaded {len(products)} products from retry list")
                return products

        # Or fetch directly from database
        pending = []
        offset = 0
        batch_size = 1000

        while True:
            response = supabase.table('foods_published_preview').select(
                'product_key, product_name, brand, product_url'
            ).eq('source', 'zooplus_csv_import')\
            .eq('allowlist_status', 'PENDING')\
            .range(offset, offset + batch_size - 1).execute()

            batch = response.data
            if not batch:
                break
            pending.extend(batch)
            offset += batch_size

        print(f"Found {len(pending)} pending Zooplus products")
        return pending

    def scrape_product(self, url):
        """Scrape using proven ScrapingBee configuration"""

        params = {
            'api_key': SCRAPINGBEE_API_KEY,
            'url': url,
            'render_js': 'true',
            'premium_proxy': 'true',
            'stealth_proxy': 'true',
            'country_code': 'gb',
            'wait': '3000',
            'return_page_source': 'true'
        }

        try:
            response = requests.get(
                'https://app.scrapingbee.com/api/v1/',
                params=params,
                timeout=60
            )

            if response.status_code == 200:
                return response.text
            else:
                print(f"    HTTP {response.status_code}")
                return None

        except Exception as e:
            print(f"    Exception: {str(e)[:100]}")
            return None

    def extract_data(self, html, product_key):
        """Extract using Pattern 8 and other patterns"""

        soup = BeautifulSoup(html, 'html.parser')
        page_text = soup.get_text('\n', strip=True)

        result = {
            'product_key': product_key,
            'scraped_at': datetime.now().isoformat(),
            'session_id': self.session_id
        }

        # Extract image
        img_selectors = [
            'img.ProductImage__image',
            'div.ProductImage img',
            'picture.ProductImage__picture img',
            'div.swiper-slide img',
            'img[alt*="product"]'
        ]

        for selector in img_selectors:
            img = soup.select_one(selector)
            if img and img.get('src'):
                result['image_url'] = img['src']
                self.stats['with_images'] += 1
                break

        # Pattern 8 for ingredients (proven to work)
        pattern_8 = r'Go to analytical constituents\s*\n(.*?)(?:Analytical constituents|$)'
        match = re.search(pattern_8, page_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)

        if match:
            self.stats['pattern_8_success'] += 1
            captured = match.group(1).strip()

            # Extract ingredients from captured content
            inner_pattern = r'Ingredients[:\s]*\n?([^\n]{20,}?)(?:\n(?:Analytical|Additives)|$)'
            inner_match = re.search(inner_pattern, captured, re.IGNORECASE | re.MULTILINE)

            if inner_match:
                ingredients = inner_match.group(1).strip()
                if len(ingredients) > 20:
                    result['ingredients_raw'] = ingredients[:3000]
                    self.stats['with_ingredients'] += 1

        # Fallback patterns
        if 'ingredients_raw' not in result:
            patterns = [
                r'(?:Composition|Ingredients)[:\s]*\n?([^\n]{20,}?)(?:\n(?:Analytical|Additives)|$)',
                r'Ingredients:\s*\n((?:Duck|Chicken|Meat|Lamb|Beef|Turkey|Salmon|Fish)[^\n]+)',
            ]

            for pattern in patterns:
                match = re.search(pattern, page_text, re.IGNORECASE | re.MULTILINE)
                if match:
                    ingredients = match.group(1).strip()
                    if len(ingredients) > 20:
                        result['ingredients_raw'] = ingredients[:3000]
                        self.stats['with_ingredients'] += 1
                        break

        # Extract nutrition
        nutrition = {}
        patterns = [
            (r'(?:Crude\s+)?Protein[:\s]+(\d+(?:\.\d+)?)\s*%', 'protein_percent'),
            (r'(?:Crude\s+)?(?:Fat|Oils)[:\s]+(\d+(?:\.\d+)?)\s*%', 'fat_percent'),
            (r'(?:Crude\s+)?Fib(?:re|er)[:\s]+(\d+(?:\.\d+)?)\s*%', 'fiber_percent'),
            (r'(?:Crude\s+)?Ash[:\s]+(\d+(?:\.\d+)?)\s*%', 'ash_percent'),
            (r'Moisture[:\s]+(\d+(?:\.\d+)?)\s*%', 'moisture_percent')
        ]

        for pattern, key in patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                nutrition[key] = float(match.group(1))

        if nutrition:
            result.update(nutrition)
            self.stats['with_nutrition'] += 1

        return result

    def save_to_gcs(self, data, product_key):
        """Save to GCS"""
        try:
            safe_key = product_key.replace('|', '_').replace('/', '_')
            filename = f"{self.gcs_folder}/{safe_key}.json"

            blob = bucket.blob(filename)
            blob.upload_from_string(
                json.dumps(data, indent=2, ensure_ascii=False),
                content_type='application/json'
            )
            return True
        except Exception as e:
            print(f"    GCS error: {str(e)[:100]}")
            return False

    def update_database(self, data):
        """Update database with scraped data"""
        try:
            update_data = {}

            # Map fields
            if 'image_url' in data:
                update_data['image_url'] = data['image_url']
            if 'ingredients_raw' in data:
                update_data['ingredients_tokens'] = data['ingredients_raw']
                update_data['ingredients_source'] = 'zooplus_retry'
            if 'protein_percent' in data:
                update_data['protein_percent'] = data['protein_percent']
            if 'fat_percent' in data:
                update_data['fat_percent'] = data['fat_percent']
            if 'fiber_percent' in data:
                update_data['fiber_percent'] = data['fiber_percent']

            if update_data:
                supabase.table('foods_canonical').update(update_data).eq(
                    'product_key', data['product_key']
                ).execute()
                return True
        except Exception as e:
            print(f"    DB error: {str(e)[:100]}")
        return False

    def run(self):
        """Run the full scraping batch"""

        products = self.get_pending_products()

        if not products:
            print("No products to scrape")
            return

        print(f"\nStarting to scrape {len(products)} products")
        print("=" * 60)

        for i, product in enumerate(products, 1):
            self.stats['total'] += 1

            print(f"\n[{i}/{len(products)}] {product['product_name'][:50]}...")
            print(f"  URL: {product.get('product_url', 'None')[:80]}...")

            if not product.get('product_url'):
                print("  ⏭️  No URL, skipping")
                continue

            # Delay between requests (5-10 seconds)
            if i > 1:
                delay = random.uniform(5, 10)
                print(f"  Waiting {delay:.1f}s...")
                time.sleep(delay)

            # Scrape
            html = self.scrape_product(product['product_url'])

            if html:
                print(f"  ✅ Scraped ({len(html)} bytes)")

                # Extract data
                data = self.extract_data(html, product['product_key'])

                # Save to GCS
                if self.save_to_gcs(data, product['product_key']):
                    print(f"  ✅ Saved to GCS")

                # Update database
                if self.update_database(data):
                    print(f"  ✅ Updated database")

                self.stats['success'] += 1

                # Print what was found
                if 'image_url' in data:
                    print(f"  📸 Image found")
                if 'ingredients_raw' in data:
                    print(f"  🥩 Ingredients found ({len(data['ingredients_raw'])} chars)")
                if 'protein_percent' in data:
                    print(f"  📊 Nutrition: P:{data.get('protein_percent')}% F:{data.get('fat_percent')}%")
            else:
                print(f"  ❌ Failed to scrape")
                self.stats['errors'] += 1

            # Print progress every 10 products
            if i % 10 == 0:
                self.print_stats()

        # Final summary
        self.print_final_summary()

    def print_stats(self):
        """Print current statistics"""
        elapsed = (datetime.now() - self.stats['start_time']).seconds
        rate = self.stats['total'] / max(elapsed, 1) * 3600

        print("\n" + "-" * 40)
        print(f"Progress: {self.stats['success']}/{self.stats['total']} successful")
        print(f"Images: {self.stats['with_images']}, Ingredients: {self.stats['with_ingredients']}, Nutrition: {self.stats['with_nutrition']}")
        print(f"Pattern 8: {self.stats['pattern_8_success']} successes")
        print(f"Rate: {rate:.1f} products/hour")
        print("-" * 40 + "\n")

    def print_final_summary(self):
        """Print final summary"""
        elapsed = (datetime.now() - self.stats['start_time']).seconds

        print("\n" + "=" * 60)
        print("FINAL SUMMARY")
        print("=" * 60)
        print(f"Total processed: {self.stats['total']}")
        print(f"Successful: {self.stats['success']} ({self.stats['success']/max(self.stats['total'],1)*100:.1f}%)")
        print(f"With images: {self.stats['with_images']} ({self.stats['with_images']/max(self.stats['total'],1)*100:.1f}%)")
        print(f"With ingredients: {self.stats['with_ingredients']} ({self.stats['with_ingredients']/max(self.stats['total'],1)*100:.1f}%)")
        print(f"With nutrition: {self.stats['with_nutrition']} ({self.stats['with_nutrition']/max(self.stats['total'],1)*100:.1f}%)")
        print(f"Pattern 8 success: {self.stats['pattern_8_success']}")
        print(f"Errors: {self.stats['errors']}")
        print(f"Time elapsed: {elapsed//60} minutes {elapsed%60} seconds")
        print(f"GCS folder: gs://{GCS_BUCKET}/{self.gcs_folder}/")

        # Save stats
        stats_file = f"zooplus_208_stats_{self.session_id}.json"
        with open(stats_file, 'w') as f:
            json.dump(self.stats, f, indent=2, default=str)
        print(f"\nStats saved to: {stats_file}")

if __name__ == '__main__':
    scraper = ZooplusFullScraper()
    scraper.run()