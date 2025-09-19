#!/usr/bin/env python3
"""
Full AADF Ingredients Scraper
Based on successful test - scrapes ingredients from all AADF products
Saves to GCS and updates database
"""

import os
import time
import json
import re
import requests
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
from google.cloud import storage
from bs4 import BeautifulSoup
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SCRAPINGBEE_API_KEY = os.getenv('SCRAPING_BEE')
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")

# Set up GCS authentication
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/sergiubiris/Desktop/lupito-content/secrets/gcp-sa.json'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AADFFullScraper:
    def __init__(self, batch_size=50):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(GCS_BUCKET)
        self.batch_size = batch_size

        # Session tracking
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.session_id = f"aadf_ingredients_{timestamp}"
        self.gcs_folder = f"scraped/aadf_ingredients_v2/{self.session_id}"

        # Tracking
        self.successful = []
        self.failed = []
        self.processed = 0
        self.total = 0

        logger.info("="*60)
        logger.info("AADF FULL INGREDIENTS SCRAPER")
        logger.info("="*60)
        logger.info(f"Session ID: {self.session_id}")
        logger.info(f"GCS folder: gs://{GCS_BUCKET}/{self.gcs_folder}/")

    def get_aadf_products(self):
        """Get all AADF products that need ingredients"""
        logger.info("Fetching AADF products...")

        # Get products with AADF source that don't have ingredients_tokens
        result = self.supabase.table('foods_canonical').select(
            'product_key, brand, brand_slug, product_name, product_url, source'
        ).like('source', '%allaboutdogfood%').is_('ingredients_tokens', 'null').execute()

        products = result.data
        logger.info(f"Found {len(products)} AADF products without ingredients")
        return products

    def scrape_with_scrapingbee(self, url, retry_count=2):
        """Scrape using ScrapingBee with retries"""
        for attempt in range(retry_count):
            params = {
                'api_key': SCRAPINGBEE_API_KEY,
                'url': url,
                'render_js': 'false',
                'premium_proxy': 'true',
                'country_code': 'gb'
            }

            try:
                response = requests.get(
                    'https://app.scrapingbee.com/api/v1/',
                    params=params,
                    timeout=30
                )
                if response.status_code == 200:
                    return response.text
                elif response.status_code == 429:
                    logger.warning(f"Rate limited, waiting 10s...")
                    time.sleep(10)
                else:
                    logger.error(f"ScrapingBee error {response.status_code}")

            except Exception as e:
                logger.error(f"ScrapingBee exception: {str(e)[:100]}")

            if attempt < retry_count - 1:
                time.sleep(5)

        return None

    def extract_ingredients_from_mixing_bowl(self, soup):
        """Extract ingredients from mixing bowl section - improved parsing"""
        ingredients_text = None

        # Look for mixing bowl section
        mixing_bowl_header = soup.find('h4', string=re.compile(r'Mixing bowl', re.IGNORECASE))
        if mixing_bowl_header:
            # Get the ingredients paragraph
            ingredients_p = mixing_bowl_header.find_next_sibling('p')
            if ingredients_p and 'ingredients' in ingredients_p.get('class', []):
                # Extract text preserving spaces between elements
                parts = []
                for elem in ingredients_p.children:
                    if elem.name == 'a':
                        # Get link text
                        text = elem.get_text(strip=True)
                        if text:
                            parts.append(text)
                    elif elem.name is None:
                        # Text node
                        text = str(elem).strip()
                        # Add non-empty text that's not just punctuation
                        if text and text not in [',', '(', ')', '.', ' and ']:
                            if text.startswith('and '):
                                text = text[4:]  # Remove leading 'and '
                            if text.endswith(' and'):
                                text = text[:-4]  # Remove trailing ' and'
                            if text.strip():
                                parts.append(text.strip())

                # Join with spaces and commas
                ingredients_text = ', '.join(parts)

        # Alternative: Look for p tag with class 'variety ingredients'
        if not ingredients_text:
            ingredients_p = soup.find('p', class_='variety ingredients')
            if ingredients_p:
                parts = []
                for elem in ingredients_p.children:
                    if elem.name == 'a':
                        parts.append(elem.get_text(strip=True))
                    elif elem.name is None:
                        text = str(elem).strip()
                        if text and text not in [',', '(', ')', '.', ' and ']:
                            if text.startswith('and '):
                                text = text[4:]
                            if text.strip():
                                parts.append(text.strip())
                ingredients_text = ', '.join(parts)

        return ingredients_text

    def parse_ingredients_to_array(self, ingredients_text):
        """Parse ingredients text into clean array"""
        if not ingredients_text:
            return []

        # Clean up the text
        text = ingredients_text.strip()

        # Fix common concatenations
        text = re.sub(r'([a-z])([A-Z])', r'\1, \2', text)  # Add comma between camelCase
        text = re.sub(r'(\))([A-Z])', r'\1, \2', text)  # Add comma after parenthesis before capital

        # Remove percentages but keep the ingredient
        text = re.sub(r'\s*\([^)]*%[^)]*\)', '', text)
        text = re.sub(r'(\d+(?:\.\d+)?%)', '', text)  # Remove standalone percentages

        # Split by comma
        parts = text.split(',')

        ingredients = []
        for part in parts:
            part = part.strip()
            if not part or len(part) < 2:
                continue

            # Clean up
            part = part.rstrip('.')
            part = re.sub(r'^and\s+', '', part, flags=re.IGNORECASE)

            # Skip if just numbers or special chars
            if not re.search(r'[a-zA-Z]', part):
                continue

            # Fix common issues
            part = part.replace('FreshlyPrepared', 'Freshly Prepared')
            part = part.replace('DriedChicken', 'Dried Chicken')
            part = re.sub(r'([a-z])([A-Z])', r'\1 \2', part)  # Add space in camelCase

            ingredients.append(part)

        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for ing in ingredients:
            ing_lower = ing.lower()
            if ing_lower not in seen and ing_lower != 'and':
                seen.add(ing_lower)
                unique.append(ing)

        return unique[:50]

    def process_product(self, product):
        """Process a single product"""
        product_key = product['product_key']
        product_name = product['product_name']

        # Build URL
        if product.get('product_url'):
            url = product['product_url']
            if not url.startswith('http'):
                url = f"https://www.allaboutdogfood.co.uk{url}"
        else:
            logger.warning(f"No URL for {product_key}, skipping")
            return None

        # Scrape the page
        html = self.scrape_with_scrapingbee(url)

        if not html:
            logger.error(f"Failed to scrape {product_key}")
            self.failed.append(product_key)
            return None

        # Parse HTML
        soup = BeautifulSoup(html, 'html.parser')

        # Extract ingredients
        ingredients_text = self.extract_ingredients_from_mixing_bowl(soup)
        ingredients_array = self.parse_ingredients_to_array(ingredients_text) if ingredients_text else []

        result = {
            'product_key': product_key,
            'product_name': product_name,
            'brand': product['brand'],
            'brand_slug': product['brand_slug'],
            'url': url,
            'ingredients_raw': ingredients_text,
            'ingredients_array': ingredients_array,
            'scraped_at': datetime.now().isoformat(),
            'session_id': self.session_id
        }

        # Save to GCS
        if ingredients_array:
            self.save_to_gcs(result)
            self.successful.append(product_key)
            logger.info(f"✓ {product_key}: {len(ingredients_array)} ingredients")
        else:
            self.failed.append(product_key)
            logger.warning(f"✗ {product_key}: No ingredients found")

        return result

    def save_to_gcs(self, data):
        """Save scraped data to GCS"""
        try:
            product_key = data['product_key'].replace('|', '_')
            blob_name = f"{self.gcs_folder}/{product_key}.json"
            blob = self.bucket.blob(blob_name)
            blob.upload_from_string(
                json.dumps(data, indent=2),
                content_type='application/json'
            )
        except Exception as e:
            logger.error(f"Failed to save to GCS: {e}")

    def update_database(self, product_data):
        """Update database with scraped ingredients"""
        if not product_data.get('ingredients_array'):
            return False

        try:
            update = self.supabase.table('foods_canonical').update({
                'ingredients_raw': product_data['ingredients_raw'],
                'ingredients_tokens': product_data['ingredients_array'],
                'ingredients_source': 'site'
            }).eq('product_key', product_data['product_key']).execute()

            return True
        except Exception as e:
            logger.error(f"Database update failed for {product_data['product_key']}: {e}")
            return False

    def process_batch(self, products):
        """Process a batch of products"""
        results = []
        for i, product in enumerate(products, 1):
            logger.info(f"[{self.processed + i}/{self.total}] Processing {product['product_name'][:50]}")

            result = self.process_product(product)
            if result:
                results.append(result)
                # Update database immediately if successful
                if result.get('ingredients_array'):
                    self.update_database(result)

            # Rate limiting
            time.sleep(4)  # 4 seconds between requests

        self.processed += len(products)
        return results

    def run(self):
        """Run the full scraping process"""
        # Get all products
        products = self.get_aadf_products()
        self.total = len(products)

        if not products:
            logger.info("No products to process")
            return

        logger.info(f"Processing {self.total} products in batches of {self.batch_size}")

        # Process in batches
        all_results = []
        for i in range(0, len(products), self.batch_size):
            batch = products[i:i+self.batch_size]
            logger.info(f"\n--- Batch {i//self.batch_size + 1}/{(len(products)-1)//self.batch_size + 1} ---")

            batch_results = self.process_batch(batch)
            all_results.extend(batch_results)

            # Progress update
            logger.info(f"Progress: {self.processed}/{self.total} ({self.processed*100/self.total:.1f}%)")
            logger.info(f"Success: {len(self.successful)} | Failed: {len(self.failed)}")

            # Take a break between batches
            if i + self.batch_size < len(products):
                logger.info("Taking 10 second break between batches...")
                time.sleep(10)

        # Final summary
        self.print_summary()

        # Save summary to GCS
        self.save_summary()

        return all_results

    def print_summary(self):
        """Print final summary"""
        logger.info("\n" + "="*60)
        logger.info("SCRAPING COMPLETE")
        logger.info("="*60)
        logger.info(f"Total processed: {self.processed}")
        logger.info(f"Successful: {len(self.successful)} ({len(self.successful)*100/self.total:.1f}%)")
        logger.info(f"Failed: {len(self.failed)} ({len(self.failed)*100/self.total:.1f}%)")
        logger.info(f"GCS location: gs://{GCS_BUCKET}/{self.gcs_folder}/")

    def save_summary(self):
        """Save summary to GCS"""
        summary = {
            'session_id': self.session_id,
            'started_at': datetime.now().isoformat(),
            'total_products': self.total,
            'processed': self.processed,
            'successful': len(self.successful),
            'failed': len(self.failed),
            'success_rate': len(self.successful) / self.total if self.total > 0 else 0,
            'successful_products': self.successful,
            'failed_products': self.failed,
            'gcs_folder': f"gs://{GCS_BUCKET}/{self.gcs_folder}/"
        }

        blob_name = f"{self.gcs_folder}/_summary.json"
        blob = self.bucket.blob(blob_name)
        blob.upload_from_string(
            json.dumps(summary, indent=2),
            content_type='application/json'
        )
        logger.info(f"Summary saved to: gs://{GCS_BUCKET}/{blob_name}")

if __name__ == "__main__":
    scraper = AADFFullScraper(batch_size=50)
    scraper.run()