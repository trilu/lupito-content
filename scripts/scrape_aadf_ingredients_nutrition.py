#!/usr/bin/env python3
"""
AADF Ingredients and Nutrition Scraper
Scrapes ingredients and nutrition data from AADF review pages
Uses proven approach from existing AADF scrapers with proper anti-bot handling
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
import random
from urllib.parse import urljoin, urlparse

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")
SCRAPINGBEE_API_KEY = os.getenv('SCRAPING_BEE')  # Use ScrapingBee for anti-bot protection

# Set up GCS authentication
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/sergiubiris/Desktop/lupito-content/secrets/gcp-sa.json'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AADFIngredientsNutritionScraper:
    def __init__(self, use_scrapingbee=False):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(GCS_BUCKET)
        self.use_scrapingbee = use_scrapingbee and SCRAPINGBEE_API_KEY

        # Session setup
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })

        # Session tracking
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.session_id = f"aadf_ingredients_{timestamp}"
        self.gcs_folder = f"scraped/aadf_ingredients/{self.session_id}"

        # Tracking
        self.failed_products = []
        self.successful_products = []

        logger.info("=" * 60)
        logger.info("AADF INGREDIENTS & NUTRITION SCRAPER")
        logger.info("=" * 60)
        logger.info(f"Session ID: {self.session_id}")
        logger.info(f"GCS folder: gs://{GCS_BUCKET}/{self.gcs_folder}/")
        logger.info(f"Using ScrapingBee: {self.use_scrapingbee}")

    def get_aadf_products(self):
        """Get AADF products (source='allaboutdogfood') that need ingredients/nutrition"""
        logger.info("Fetching AADF products to scrape...")

        # Get all AADF products
        result = self.supabase.table('foods_canonical').select(
            'product_key, brand, product_name, product_url'
        ).eq(
            'source', 'allaboutdogfood'
        ).execute()

        products = result.data
        logger.info(f"Found {len(products)} AADF products to process")
        return products

    def scrape_page_with_scrapingbee(self, url):
        """Scrape using ScrapingBee API for anti-bot protection"""
        params = {
            'api_key': SCRAPINGBEE_API_KEY,
            'url': url,
            'render_js': 'false',  # AADF doesn't need JS rendering for ingredients
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
            else:
                logger.error(f"ScrapingBee error {response.status_code}: {response.text[:100]}")
                return None
        except Exception as e:
            logger.error(f"ScrapingBee exception: {str(e)[:100]}")
            return None

    def scrape_page_direct(self, url):
        """Direct scraping with session"""
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Direct scrape error: {str(e)[:100]}")
            return None

    def parse_ingredients_to_array(self, ingredients_text):
        """Parse ingredients text into array format for database"""
        if not ingredients_text:
            return []

        # Clean up the text
        text = ingredients_text.strip()

        # Remove common prefixes
        text = re.sub(r'^(Composition|Ingredients)[:\s]*', '', text, flags=re.IGNORECASE)

        # Remove percentages in parentheses
        text = re.sub(r'\s*\([^)]*%[^)]*\)', '', text)

        # Split by comma or semicolon
        parts = re.split(r'[,;]', text)

        ingredients = []
        for part in parts:
            part = part.strip()
            if not part or len(part) < 3:
                continue

            # Clean up each ingredient
            part = part.rstrip('.')

            # Skip if just numbers or special chars
            if not re.search(r'[a-zA-Z]', part):
                continue

            ingredients.append(part)

        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for ing in ingredients:
            if ing.lower() not in seen:
                seen.add(ing.lower())
                unique.append(ing)

        return unique[:50]  # Limit to 50 ingredients max

    def extract_data_from_page(self, html, url):
        """Extract ingredients and nutrition from AADF review page"""
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')
        data = {}

        # Find ingredients/composition section
        # AADF typically shows this in a specific section
        ingredients_text = None

        # Strategy 1: Look for composition heading
        for heading in soup.find_all(['h2', 'h3', 'h4']):
            if 'composition' in heading.text.lower() or 'ingredients' in heading.text.lower():
                # Get the next sibling or parent's text
                next_elem = heading.find_next_sibling()
                if next_elem:
                    ingredients_text = next_elem.get_text(strip=True)
                    break
                # Or check parent
                parent = heading.parent
                if parent:
                    text = parent.get_text(strip=True)
                    # Remove the heading text
                    text = text.replace(heading.get_text(strip=True), '')
                    if len(text) > 20:
                        ingredients_text = text
                        break

        # Strategy 2: Look for patterns in text
        if not ingredients_text:
            page_text = soup.get_text()

            # Pattern for ingredients section
            patterns = [
                r'Composition[:\s]*([^.]{20,}?)(?:Analytical|Additives|Nutritional|$)',
                r'Ingredients[:\s]*([^.]{20,}?)(?:Analytical|Additives|Nutritional|$)',
                r'Main ingredients[:\s]*([^.]{20,}?)(?:Analytical|Additives|$)'
            ]

            for pattern in patterns:
                match = re.search(pattern, page_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                if match:
                    ingredients_text = match.group(1).strip()
                    # Clean up extra whitespace
                    ingredients_text = ' '.join(ingredients_text.split())
                    if len(ingredients_text) > 20:
                        break

        if ingredients_text:
            data['ingredients_raw'] = ingredients_text[:3000]  # Store raw text (truncated)
            data['ingredients_array'] = self.parse_ingredients_to_array(ingredients_text)

        # Extract nutrition data
        # Look for analytical constituents section
        nutrition_text = None

        # Find analytical constituents heading
        for heading in soup.find_all(['h2', 'h3', 'h4']):
            if 'analytical' in heading.text.lower() or 'analysis' in heading.text.lower():
                next_elem = heading.find_next_sibling()
                if next_elem:
                    nutrition_text = next_elem.get_text(strip=True)
                    break
                parent = heading.parent
                if parent:
                    nutrition_text = parent.get_text(strip=True)
                    break

        # If not found, search in page text
        if not nutrition_text:
            page_text = soup.get_text()
            pattern = r'Analytical [Cc]onstituents[:\s]*([^.]{20,}?)(?:Additives|Vitamins|Feeding|$)'
            match = re.search(pattern, page_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match:
                nutrition_text = match.group(1).strip()

        if nutrition_text:
            # Extract percentages
            nutrition_patterns = [
                (r'(?:Crude\s+)?Protein[:\s]+([\d.]+)\s*%', 'protein_percent'),
                (r'(?:Crude\s+)?(?:Fat|Oils?)[:\s]+([\d.]+)\s*%', 'fat_percent'),
                (r'(?:Crude\s+)?Fib(?:re|er)[:\s]+([\d.]+)\s*%', 'fiber_percent'),
                (r'(?:Crude\s+)?Ash[:\s]+([\d.]+)\s*%', 'ash_percent'),
                (r'Moisture[:\s]+([\d.]+)\s*%', 'moisture_percent')
            ]

            for pattern, key in nutrition_patterns:
                match = re.search(pattern, nutrition_text, re.IGNORECASE)
                if match:
                    try:
                        value = float(match.group(1))
                        if 0 <= value <= 100:  # Sanity check
                            data[key] = value
                    except:
                        pass

        return data if data else None

    def save_to_gcs(self, product_key, data):
        """Save scraped data to GCS"""
        try:
            # Create filename from product key
            safe_key = product_key.replace('|', '_').replace('/', '_')
            filename = f"{self.gcs_folder}/{safe_key}.json"

            # Add metadata
            data['product_key'] = product_key
            data['scraped_at'] = datetime.now().isoformat()
            data['session_id'] = self.session_id

            # Upload to GCS
            blob = self.bucket.blob(filename)
            blob.upload_from_string(
                json.dumps(data, indent=2, ensure_ascii=False),
                content_type='application/json'
            )

            return True
        except Exception as e:
            logger.error(f"GCS upload error: {str(e)[:100]}")
            return False

    def update_database(self, product_key, data):
        """Update database with scraped data"""
        try:
            update_data = {}

            # Add ingredients as array
            if 'ingredients_array' in data and data['ingredients_array']:
                update_data['ingredients_tokens'] = data['ingredients_array']
                update_data['ingredients_source'] = 'site'

            # Add nutrition data
            for field in ['protein_percent', 'fat_percent', 'fiber_percent', 'ash_percent', 'moisture_percent']:
                if field in data:
                    update_data[field] = data[field]

            if update_data:
                self.supabase.table('foods_canonical').update(update_data).eq(
                    'product_key', product_key
                ).execute()
                return True

            return False
        except Exception as e:
            logger.error(f"Database update error for {product_key}: {str(e)[:100]}")
            return False

    def run(self):
        """Main execution"""
        products = self.get_aadf_products()

        if not products:
            logger.info("No products to process")
            return

        # Ask for confirmation
        response = input(f"\nReady to scrape {len(products)} AADF products? This will take ~{len(products) * 5 // 60} minutes. (y/n): ")
        if response.lower() != 'y':
            logger.info("Scraping cancelled")
            return

        logger.info("\nStarting scraping process...")

        for i, product in enumerate(products, 1):
            product_key = product['product_key']
            product_url = product.get('product_url', '')

            logger.info(f"\nProcessing {i}/{len(products)}: {product_key}")

            if not product_url or 'allaboutdogfood' not in product_url:
                logger.warning(f"  No valid AADF URL for {product_key}")
                self.failed_products.append(product_key)
                continue

            # Scrape the page
            if self.use_scrapingbee:
                html = self.scrape_page_with_scrapingbee(product_url)
            else:
                html = self.scrape_page_direct(product_url)

            if not html:
                logger.error(f"  Failed to scrape {product_url[:50]}...")
                self.failed_products.append(product_key)
                # Add delay before retry
                time.sleep(random.uniform(4, 6))
                continue

            # Extract data
            data = self.extract_data_from_page(html, product_url)

            if not data:
                logger.warning(f"  No data extracted from {product_url[:50]}...")
                self.failed_products.append(product_key)
            else:
                # Save to GCS
                if self.save_to_gcs(product_key, data):
                    logger.info(f"  ✅ Saved to GCS")

                    # Update database
                    if self.update_database(product_key, data):
                        logger.info(f"  ✅ Updated database")
                        self.successful_products.append(product_key)
                    else:
                        logger.error(f"  ❌ Database update failed")
                else:
                    logger.error(f"  ❌ GCS save failed")
                    self.failed_products.append(product_key)

            # Progress indicator
            if i % 10 == 0:
                logger.info(f"\nProgress: {i}/{len(products)} processed, {len(self.successful_products)} successful")

            # Rate limiting - be respectful to AADF
            delay = random.uniform(4, 6)  # 4-6 seconds between requests
            time.sleep(delay)

        # Final summary
        logger.info("\n" + "=" * 60)
        logger.info("SCRAPING COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total products: {len(products)}")
        logger.info(f"Successful: {len(self.successful_products)} ({len(self.successful_products)/len(products)*100:.1f}%)")
        logger.info(f"Failed: {len(self.failed_products)}")
        logger.info(f"GCS folder: gs://{GCS_BUCKET}/{self.gcs_folder}/")

        # Save logs
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if self.successful_products:
            success_log = f"/tmp/aadf_ingredients_success_{timestamp}.json"
            with open(success_log, 'w') as f:
                json.dump(self.successful_products, f, indent=2)
            logger.info(f"Success log: {success_log}")

        if self.failed_products:
            failed_log = f"/tmp/aadf_ingredients_failed_{timestamp}.json"
            with open(failed_log, 'w') as f:
                json.dump(self.failed_products, f, indent=2)
            logger.info(f"Failed log: {failed_log}")

if __name__ == "__main__":
    # Check if we should use ScrapingBee (for strong anti-bot protection)
    use_scrapingbee = '--scrapingbee' in os.sys.argv

    scraper = AADFIngredientsNutritionScraper(use_scrapingbee=use_scrapingbee)
    scraper.run()