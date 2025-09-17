#!/usr/bin/env python3
"""
Zooplus Image Extraction Orchestrated Scraper
Extracts image URLs from Zooplus product pages using ScrapingBee
Based on orchestrated_scraper.py but modified for image extraction
"""

import os
import sys
import json
import time
import random
from datetime import datetime
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google.cloud import storage
from supabase import create_client

load_dotenv()

SCRAPINGBEE_API_KEY = os.getenv('SCRAPING_BEE')
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")

class ZooplusImageScraper:
    def __init__(self, name: str, country_code: str, min_delay: int, max_delay: int, batch_size: int, offset: int):
        self.name = name
        self.country_code = country_code
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.batch_size = batch_size
        self.offset = offset

        self.api_key = SCRAPINGBEE_API_KEY
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(GCS_BUCKET)

        # Session tracking
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.session_id = f"{timestamp}_{name}"
        self.gcs_folder = f"scraped/zooplus_images/{self.session_id}"

        # Statistics
        self.stats = {
            'total': 0,
            'successful': 0,
            'with_image_urls': 0,
            'errors': 0,
            'consecutive_errors': 0,
            'session_start': datetime.now(),
            'skipped_404': 0,
            'skipped_category': 0
        }

        print(f"[{name}] 🚀 ZOOPLUS IMAGE SCRAPER STARTED")
        print(f"[{name}] Country: {country_code}, Delays: {min_delay}-{max_delay}s")
        print(f"[{name}] Batch: {batch_size}, Offset: {offset}")
        print(f"[{name}] GCS: gs://{GCS_BUCKET}/{self.gcs_folder}/")

    def get_products(self) -> List[Dict]:
        """Get CSV import products without images"""
        try:
            response = self.supabase.table('foods_canonical').select(
                'product_key, product_name, brand, product_url'
            ).eq('source', 'zooplus_csv_import')\
            .is_('image_url', 'null')\
            .range(self.offset, self.offset + self.batch_size - 1).execute()

            products = response.data if response.data else []
            print(f"[{self.name}] Found {len(products)} CSV import products (offset: {self.offset})")
            return products
        except Exception as e:
            print(f"[{self.name}] Error fetching products: {e}")
            return []

    def is_category_page(self, url: str, page_text: str) -> bool:
        """Detect if page is a category/search page rather than product page"""
        # URL patterns that indicate category pages
        category_url_patterns = [
            '/shop/dogs/', '/shop/cats/', '/search', '/category',
            'filter=', 'sort=', '/brand/', '/food-type/'
        ]

        # Check URL patterns
        for pattern in category_url_patterns:
            if pattern in url:
                return True

        # Content patterns that indicate category pages
        category_content_patterns = [
            'products found', 'filter results', 'sort by',
            'product categories', 'browse products',
            'no products found', 'refine your search'
        ]

        page_text_lower = page_text.lower()
        for pattern in category_content_patterns:
            if pattern in page_text_lower:
                return True

        return False

    def scrape_product(self, url: str) -> Dict:
        """Scrape product page for image URLs"""

        # Clean URL
        if '?activeVariant=' in url:
            url = url.split('?activeVariant=')[0]

        # Use proven stealth parameters
        params = {
            'api_key': self.api_key,
            'url': url,
            'render_js': 'true',
            'premium_proxy': 'true',
            'stealth_proxy': 'true',
            'country_code': self.country_code,
            'wait': '3000',
            'return_page_source': 'true'
        }

        try:
            response = requests.get(
                'https://app.scrapingbee.com/api/v1/',
                params=params,
                timeout=120
            )

            if response.status_code == 200:
                self.stats['consecutive_errors'] = 0
                return self.parse_response(response.text, url)
            elif response.status_code == 404:
                self.stats['skipped_404'] += 1
                return {'url': url, 'error': '404_not_found', 'skip': True}
            else:
                self.stats['consecutive_errors'] += 1
                self.stats['errors'] += 1
                error_msg = f'HTTP {response.status_code}'
                if response.text:
                    error_msg += f': {response.text[:100]}'
                return {'url': url, 'error': error_msg}

        except Exception as e:
            self.stats['consecutive_errors'] += 1
            self.stats['errors'] += 1
            return {'url': url, 'error': str(e)[:200]}

    def parse_response(self, html: str, url: str) -> Dict:
        """Parse HTML for image URLs"""

        soup = BeautifulSoup(html, 'html.parser')
        page_text = soup.get_text(separator='\n', strip=True)

        result = {
            'url': url,
            'scraped_at': datetime.now().isoformat(),
            'session_id': self.session_id,
            'country_code': self.country_code,
            'scraper_name': self.name
        }

        # Check if this is a category page
        if self.is_category_page(url, page_text):
            self.stats['skipped_category'] += 1
            return {'url': url, 'error': 'category_page', 'skip': True}

        # Extract product name
        h1 = soup.find('h1')
        if h1:
            result['product_name'] = h1.text.strip()

        # Extract image URLs using multiple selectors
        image_selectors = [
            'img.ProductImage__image',           # Primary product image
            'div.ProductImage img',              # Product image container
            'picture.ProductImage__picture img', # Picture element
            'div.swiper-slide img',              # Carousel images
            'img[data-testid*="product"]',       # Test ID based selectors
            'img[alt*="product" i]',             # Alt text containing "product"
        ]

        extracted_urls = []

        # Try each selector
        for selector in image_selectors:
            images = soup.select(selector)
            for img in images:
                # Get src or data-src
                img_url = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                if img_url:
                    # Clean and validate URL
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    elif img_url.startswith('/'):
                        img_url = 'https://www.zooplus.com' + img_url

                    # Skip placeholder/loading images
                    if any(skip in img_url.lower() for skip in ['placeholder', 'loading', 'spinner', 'blank']):
                        continue

                    # Must be a reasonable image URL
                    if any(ext in img_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']) and len(img_url) > 20:
                        extracted_urls.append(img_url)

        # Fallback: Try Open Graph image
        if not extracted_urls:
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                og_url = og_image['content']
                if og_url.startswith('//'):
                    og_url = 'https:' + og_url
                elif og_url.startswith('/'):
                    og_url = 'https://www.zooplus.com' + og_url
                extracted_urls.append(og_url)

        # Remove duplicates and take best URL
        if extracted_urls:
            unique_urls = list(set(extracted_urls))

            # Prefer larger images (look for size indicators in URL)
            best_url = unique_urls[0]
            for url_candidate in unique_urls:
                # Prefer URLs with size indicators like 500x500, 800x800, etc.
                if any(size in url_candidate for size in ['800x', '600x', '500x', 'large', 'big']):
                    best_url = url_candidate
                    break

            result['image_url'] = best_url
            result['all_image_urls'] = unique_urls[:5]  # Keep up to 5 alternatives
            self.stats['with_image_urls'] += 1
            self.stats['successful'] += 1

        return result

    def save_to_gcs(self, product_key: str, data: Dict) -> bool:
        """Save to GCS"""
        try:
            safe_key = product_key.replace('|', '_').replace('/', '_')
            filename = f"{self.gcs_folder}/{safe_key}.json"

            blob = self.bucket.blob(filename)
            blob.upload_from_string(
                json.dumps(data, indent=2, ensure_ascii=False),
                content_type='application/json'
            )
            return True
        except Exception as e:
            print(f"[{self.name}] GCS error: {str(e)[:100]}")
            return False

    def run_batch(self):
        """Run the scraping batch"""

        products = self.get_products()
        if not products:
            print(f"[{self.name}] No products to scrape")
            return

        print(f"[{self.name}] Starting batch of {len(products)} products")

        for i, product in enumerate(products, 1):
            # Stop if too many consecutive errors
            if self.stats['consecutive_errors'] >= 3:
                print(f"[{self.name}] ⚠️ Stopping due to consecutive errors")
                break

            print(f"[{self.name}] [{i}/{len(products)}] {product['product_name'][:40]}...")

            # Delay between requests
            if i > 1:
                delay = random.uniform(self.min_delay, self.max_delay)
                print(f"[{self.name}] Waiting {delay:.1f}s...")
                time.sleep(delay)

            self.stats['total'] += 1

            # Scrape
            result = self.scrape_product(product['product_url'])

            # Add metadata
            result['product_key'] = product['product_key']
            result['brand'] = product.get('brand')

            # Show results
            if 'error' in result:
                if result.get('skip'):
                    skip_reason = result['error']
                    if skip_reason == '404_not_found':
                        print(f"[{self.name}] ⏭️ Skipped: 404 Not Found")
                    elif skip_reason == 'category_page':
                        print(f"[{self.name}] ⏭️ Skipped: Category page detected")
                else:
                    print(f"[{self.name}] ❌ Error: {result['error']}")
            else:
                if 'image_url' in result:
                    num_alternatives = len(result.get('all_image_urls', []))
                    print(f"[{self.name}] ✅ Found image URL (+{num_alternatives-1} alternatives)")
                    print(f"[{self.name}]    {result['image_url'][:60]}...")
                else:
                    print(f"[{self.name}] ⚠️ Scraped but no image found")

            # Save to GCS
            self.save_to_gcs(product['product_key'], result)

        # Summary
        self.print_summary()

    def print_summary(self):
        """Print summary"""
        print(f"\n[{self.name}] " + "=" * 50)
        print(f"[{self.name}] ZOOPLUS IMAGE SCRAPING COMPLETE")
        print(f"[{self.name}] " + "=" * 50)

        elapsed = datetime.now() - self.stats['session_start']

        print(f"[{self.name}] Duration: {elapsed}")
        print(f"[{self.name}] Total: {self.stats['total']}")
        print(f"[{self.name}] Successful: {self.stats['successful']}")
        print(f"[{self.name}] With image URLs: {self.stats['with_image_urls']}")
        print(f"[{self.name}] Errors: {self.stats['errors']}")
        print(f"[{self.name}] Skipped (404): {self.stats['skipped_404']}")
        print(f"[{self.name}] Skipped (category): {self.stats['skipped_category']}")

        if self.stats['total'] > 0:
            success_rate = self.stats['successful'] / self.stats['total'] * 100
            image_rate = self.stats['with_image_urls'] / self.stats['total'] * 100
            print(f"[{self.name}] Success rate: {success_rate:.1f}%")
            print(f"[{self.name}] Image URL rate: {image_rate:.1f}%")

        print(f"[{self.name}] GCS: gs://{GCS_BUCKET}/{self.gcs_folder}/")

def main():
    """Run orchestrated scraper with command line arguments"""
    if len(sys.argv) < 7:
        print("Usage: python scrape_zooplus_images_orchestrated.py <name> <country> <min_delay> <max_delay> <batch_size> <offset>")
        return

    try:
        name = sys.argv[1]
        country_code = sys.argv[2]
        min_delay = int(sys.argv[3])
        max_delay = int(sys.argv[4])
        batch_size = int(sys.argv[5])
        offset = int(sys.argv[6])

        scraper = ZooplusImageScraper(name, country_code, min_delay, max_delay, batch_size, offset)
        scraper.run_batch()

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()