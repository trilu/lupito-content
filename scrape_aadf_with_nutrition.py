#!/usr/bin/env python3
"""
Updated AADF Scraper with Nutrition Extraction
Extracts both ingredients and nutrition data from AADF pages
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

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SCRAPINGBEE_API_KEY = os.getenv('SCRAPING_BEE')
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")

# Set up GCS authentication
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/sergiubiris/Desktop/lupito-content/secrets/gcp-sa.json'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AADFCompleteScraper:
    def __init__(self, test_mode=False, test_limit=5):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(GCS_BUCKET)
        self.test_mode = test_mode
        self.test_limit = test_limit

        # Session tracking
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.session_id = f"aadf_complete_{timestamp}"
        self.gcs_folder = f"scraped/aadf_complete/{self.session_id}"

        # Tracking
        self.successful = []
        self.failed = []

        logger.info("="*60)
        logger.info("AADF COMPLETE SCRAPER (Ingredients + Nutrition)")
        logger.info("="*60)
        logger.info(f"Session ID: {self.session_id}")
        logger.info(f"Test mode: {test_mode}")

    def get_products(self):
        """Get AADF products"""
        query = self.supabase.table('foods_canonical').select(
            'product_key, brand, brand_slug, product_name, product_url, source'
        ).like('source', '%allaboutdogfood%')

        if self.test_mode:
            query = query.limit(self.test_limit)
        else:
            # Get products without ingredients_tokens
            query = query.is_('ingredients_tokens', 'null')

        result = query.execute()
        return result.data

    def scrape_with_scrapingbee(self, url):
        """Scrape using ScrapingBee"""
        params = {
            'api_key': SCRAPINGBEE_API_KEY,
            'url': url,
            'render_js': 'true',  # Enable JS rendering to get nutrition data
            'premium_proxy': 'true',
            'country_code': 'gb',
            'wait': '2000'  # Wait 2 seconds for JS to load
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
                logger.error(f"ScrapingBee error {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"ScrapingBee exception: {str(e)[:100]}")
            return None

    def extract_ingredients_from_mixing_bowl(self, soup):
        """Extract ingredients from mixing bowl section"""
        ingredients_text = None

        # Look for mixing bowl section
        mixing_bowl_header = soup.find('h4', string=re.compile(r'Mixing bowl', re.IGNORECASE))
        if not mixing_bowl_header:
            # Try finding by text content
            for h4 in soup.find_all('h4'):
                if 'Mixing bowl' in h4.get_text():
                    mixing_bowl_header = h4
                    break

        if mixing_bowl_header:
            # Get the ingredients paragraph
            ingredients_p = mixing_bowl_header.find_next_sibling('p')
            if not ingredients_p:
                # Try parent's next sibling
                parent = mixing_bowl_header.parent
                if parent:
                    ingredients_p = parent.find_next('p')

            if ingredients_p:
                # Extract text preserving spaces
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

        # Alternative: Look in the Composition section
        if not ingredients_text:
            comp_section = soup.find('div', class_='composition')
            if not comp_section:
                # Look for heading with "Composition"
                for heading in soup.find_all(['h2', 'h3', 'h4']):
                    if 'composition' in heading.get_text().lower():
                        comp_section = heading.parent
                        break

            if comp_section:
                # Find mixing bowl within composition
                for p in comp_section.find_all('p'):
                    text = p.get_text()
                    if len(text) > 50 and not text.startswith('Think of'):
                        # This might be the ingredients
                        ingredients_text = p.get_text(strip=True)
                        break

        return ingredients_text

    def extract_nutrition_from_typical_analysis(self, soup):
        """Extract nutrition from Typical Analysis section"""
        nutrition = {}

        # Look for "Typical Analysis" heading
        typical_heading = None
        for heading in soup.find_all(['h2', 'h3', 'h4']):
            if 'typical analysis' in heading.get_text().lower():
                typical_heading = heading
                break

        if typical_heading:
            # Get the content after the heading
            next_elem = typical_heading.find_next_sibling()
            if next_elem:
                text = next_elem.get_text() if next_elem.name == 'p' else ''

                # If not in next sibling, check parent
                if not text or len(text) < 20:
                    parent = typical_heading.parent
                    if parent:
                        text = parent.get_text()
            else:
                # Get all text from parent
                parent = typical_heading.parent
                if parent:
                    text = parent.get_text()
                else:
                    text = ''

            # Parse the text for nutrition values
            if text:
                nutrition = self.parse_nutrition_text(text)

        # Alternative: Search for nutrition patterns in the whole page
        if not nutrition:
            # Look for any div/section with class containing 'analysis' or 'nutrition'
            for elem in soup.find_all(['div', 'section'], class_=re.compile('analysis|nutrition', re.I)):
                text = elem.get_text()
                if 'protein' in text.lower() and '%' in text:
                    nutrition = self.parse_nutrition_text(text)
                    if nutrition:
                        break

        # Last resort: Search entire page for pattern
        if not nutrition:
            full_text = soup.get_text()
            # Look for "Typical Analysis" followed by percentages
            match = re.search(r'Typical Analysis[:\s]*([^\\n]{20,500})', full_text, re.IGNORECASE)
            if match:
                nutrition = self.parse_nutrition_text(match.group(1))

        return nutrition

    def parse_nutrition_text(self, text):
        """Parse nutrition percentages from text"""
        nutrition = {}

        # Patterns to match nutrition values
        patterns = {
            'protein_percent': r'[Pp]rotein[:\s]*([0-9]+(?:\.[0-9]+)?)\s*%',
            'fat_percent': r'[Ff]at[:\s]*([0-9]+(?:\.[0-9]+)?)\s*%',
            'fiber_percent': r'[Ff]ib(?:re|er)[:\s]*([0-9]+(?:\.[0-9]+)?)\s*%',
            'ash_percent': r'[Aa]sh[:\s]*([0-9]+(?:\.[0-9]+)?)\s*%',
            'moisture_percent': r'[Mm]oisture[:\s]*([0-9]+(?:\.[0-9]+)?)\s*%'
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                try:
                    value = float(match.group(1))
                    nutrition[key] = value
                except ValueError:
                    pass

        # Also look for kcal
        kcal_pattern = r'([0-9]+(?:\.[0-9]+)?)\s*kcal/100g'
        kcal_match = re.search(kcal_pattern, text)
        if kcal_match:
            try:
                nutrition['kcal_per_100g'] = float(kcal_match.group(1))
            except ValueError:
                pass

        return nutrition

    def parse_ingredients_to_array(self, ingredients_text):
        """Parse ingredients text into clean array"""
        if not ingredients_text:
            return []

        text = ingredients_text.strip()

        # Fix common concatenations
        text = re.sub(r'([a-z])([A-Z])', r'\1, \2', text)
        text = re.sub(r'(\))([A-Z])', r'\1, \2', text)

        # Remove percentages
        text = re.sub(r'\s*\([^)]*%[^)]*\)', '', text)
        text = re.sub(r'(\d+(?:\.\d+)?%)', '', text)

        # Split by comma
        parts = text.split(',')

        ingredients = []
        for part in parts:
            part = part.strip()
            if not part or len(part) < 2:
                continue

            part = part.rstrip('.')
            part = re.sub(r'^and\s+', '', part, flags=re.IGNORECASE)

            if not re.search(r'[a-zA-Z]', part):
                continue

            # Fix camelCase
            part = re.sub(r'([a-z])([A-Z])', r'\1 \2', part)

            ingredients.append(part)

        # Remove duplicates
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

        logger.info(f"\nProcessing: {product_name[:50]}")

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

        # Extract nutrition
        nutrition = self.extract_nutrition_from_typical_analysis(soup)

        result = {
            'product_key': product_key,
            'product_name': product_name,
            'brand': product['brand'],
            'brand_slug': product['brand_slug'],
            'url': url,
            'ingredients_raw': ingredients_text,
            'ingredients_array': ingredients_array,
            'nutrition': nutrition,
            'scraped_at': datetime.now().isoformat(),
            'session_id': self.session_id
        }

        # Log results
        if ingredients_array:
            logger.info(f"  ✓ Ingredients: {len(ingredients_array)} items")
        else:
            logger.warning(f"  ✗ No ingredients")

        if nutrition:
            logger.info(f"  ✓ Nutrition: {nutrition}")
        else:
            logger.warning(f"  ✗ No nutrition")

        if ingredients_array or nutrition:
            self.successful.append(product_key)
            # Save to GCS
            self.save_to_gcs(result)
            # Update database
            if not self.test_mode:
                self.update_database(result)
        else:
            self.failed.append(product_key)

        return result

    def save_to_gcs(self, data):
        """Save to GCS"""
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
        """Update database"""
        if not product_data.get('ingredients_array') and not product_data.get('nutrition'):
            return False

        update_data = {}

        if product_data.get('ingredients_array'):
            update_data['ingredients_raw'] = product_data['ingredients_raw']
            update_data['ingredients_tokens'] = product_data['ingredients_array']
            update_data['ingredients_source'] = 'site'

        if product_data.get('nutrition'):
            for key, value in product_data['nutrition'].items():
                if key in ['protein_percent', 'fat_percent', 'fiber_percent',
                          'ash_percent', 'moisture_percent', 'kcal_per_100g']:
                    update_data[key] = value

        try:
            self.supabase.table('foods_canonical').update(
                update_data
            ).eq('product_key', product_data['product_key']).execute()
            return True
        except Exception as e:
            logger.error(f"Database update failed: {e}")
            return False

    def run(self):
        """Run the scraper"""
        products = self.get_products()
        total = len(products)

        logger.info(f"Processing {total} products")

        results = []
        for i, product in enumerate(products, 1):
            logger.info(f"\n[{i}/{total}] {product['product_name'][:50]}")

            result = self.process_product(product)
            if result:
                results.append(result)

            # Rate limiting
            if i < total:
                time.sleep(4)

        # Summary
        logger.info("\n" + "="*60)
        logger.info("SUMMARY")
        logger.info("="*60)
        logger.info(f"Total: {total}")
        logger.info(f"Successful: {len(self.successful)} ({len(self.successful)*100/total:.1f}%)")
        logger.info(f"Failed: {len(self.failed)} ({len(self.failed)*100/total:.1f}%)")

        # Show sample results
        if self.test_mode and results:
            logger.info("\nSample results:")
            for r in results[:3]:
                logger.info(f"\n{r['product_name']}:")
                if r.get('ingredients_array'):
                    logger.info(f"  Ingredients: {', '.join(r['ingredients_array'][:5])}...")
                if r.get('nutrition'):
                    logger.info(f"  Nutrition: Protein {r['nutrition'].get('protein_percent')}%, "
                              f"Fat {r['nutrition'].get('fat_percent')}%, "
                              f"Kcal {r['nutrition'].get('kcal_per_100g')}")

        return results

if __name__ == "__main__":
    import sys

    # Check for test mode
    test_mode = '--test' in sys.argv

    scraper = AADFCompleteScraper(test_mode=test_mode)
    results = scraper.run()

    if test_mode:
        # Save test results
        with open(f'aadf_test_nutrition_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"\nTest results saved")