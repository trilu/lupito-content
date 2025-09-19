#!/usr/bin/env python3
"""
Test AADF scraper with relaxed extraction for 5 products
Uses ScrapingBee and extracts ingredients from the mixing bowl section
"""

import os
import time
import json
import re
import requests
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
from bs4 import BeautifulSoup
import logging

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SCRAPINGBEE_API_KEY = os.getenv('SCRAPING_BEE')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RelaxedAADFScraper:
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.successful = []
        self.failed = []

    def get_test_products(self, limit=5):
        """Get 5 AADF products for testing"""
        # First try with source field
        result = self.supabase.table('foods_canonical').select(
            'product_key, brand, brand_slug, product_name, product_url, source, sources'
        ).like('source', '%allaboutdogfood%').limit(limit).execute()

        if not result.data:
            # Try with specific AADF brands
            result = self.supabase.table('foods_canonical').select(
                'product_key, brand, brand_slug, product_name, product_url, source, sources'
            ).in_('brand_slug', ['aatu', 'akela', 'applaws', 'canagan', 'orijen']).limit(limit).execute()

        return result.data

    def scrape_with_scrapingbee(self, url):
        """Scrape using ScrapingBee API"""
        params = {
            'api_key': SCRAPINGBEE_API_KEY,
            'url': url,
            'render_js': 'false',  # AADF doesn't need JS for ingredients
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
                logger.error(f"ScrapingBee error {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"ScrapingBee exception: {str(e)}")
            return None

    def extract_ingredients_from_mixing_bowl(self, soup):
        """Extract ingredients from the mixing bowl section"""
        ingredients_text = None

        # Look for mixing bowl section
        # Pattern 1: Find h4 with "Mixing bowl:" text
        mixing_bowl_header = soup.find('h4', string=re.compile(r'Mixing bowl', re.IGNORECASE))
        if mixing_bowl_header:
            # Get the next sibling which should be the ingredients paragraph
            next_elem = mixing_bowl_header.find_next_sibling('p')
            if next_elem and 'ingredients' in next_elem.get('class', []):
                # Extract text from all links and non-link text
                ingredients_parts = []
                for elem in next_elem.descendants:
                    if elem.name is None:  # Text node
                        text = elem.strip()
                        if text and text not in [',', '(', ')', '.']:
                            ingredients_parts.append(text)
                    elif elem.name == 'a':
                        ingredients_parts.append(elem.get_text(strip=True))

                # Join and clean
                ingredients_text = ' '.join(ingredients_parts)

        # Pattern 2: Look for p tag with class 'variety ingredients'
        if not ingredients_text:
            ingredients_p = soup.find('p', class_='variety ingredients')
            if ingredients_p:
                ingredients_text = ingredients_p.get_text(strip=True)

        # Pattern 3: Regex search in full text for mixing bowl content
        if not ingredients_text:
            full_text = soup.get_text()
            match = re.search(r'Mixing bowl:?\s*([^\\n]{50,2000})', full_text, re.IGNORECASE)
            if match:
                ingredients_text = match.group(1).strip()

        return ingredients_text

    def extract_nutrition_from_javascript(self, html):
        """Extract nutrition data from JavaScript variables"""
        nutrition = {}

        # Look for the data array pattern: data[0] = protein, data[1] = fat, etc.
        # Pattern: chartData.push( new Array ( 'protein', data[0], ...

        patterns = {
            'protein': r"chartData\.push\s*\(\s*new Array\s*\(\s*'protein',\s*data\[0\]",
            'fat': r"chartData\.push\s*\(\s*new Array\s*\(\s*'fat',\s*data\[1\]",
            'fiber': r"chartData\.push\s*\(\s*new Array\s*\(\s*'fibre',\s*data\[2\]",
            'ash': r"chartData\.push\s*\(\s*new Array\s*\(\s*'ash',\s*data\[3\]"
        }

        # Check if these patterns exist (meaning nutrition data is structured this way)
        has_chart_data = any(re.search(pattern, html) for pattern in patterns.values())

        if has_chart_data:
            # Look for the actual data values
            # They might be in a format like: ['Protein', 30], ['Fat', 20], etc.
            data_pattern = r"\['([^']+)',\s*([0-9.]+)\]"
            matches = re.findall(data_pattern, html)

            for label, value in matches:
                label_lower = label.lower()
                if 'protein' in label_lower:
                    nutrition['protein_percent'] = float(value)
                elif 'fat' in label_lower:
                    nutrition['fat_percent'] = float(value)
                elif 'fibre' in label_lower or 'fiber' in label_lower:
                    nutrition['fiber_percent'] = float(value)
                elif 'ash' in label_lower:
                    nutrition['ash_percent'] = float(value)

        return nutrition

    def parse_ingredients_to_array(self, ingredients_text):
        """Parse ingredients text into clean array"""
        if not ingredients_text:
            return []

        # Clean up the text
        text = ingredients_text.strip()

        # Remove percentages in parentheses
        text = re.sub(r'\s*\([^)]*%[^)]*\)', '', text)

        # Remove other parenthetical content
        text = re.sub(r'\s*\([^)]+\)', '', text)

        # Split by comma
        parts = text.split(',')

        ingredients = []
        for part in parts:
            part = part.strip()
            if not part or len(part) < 2:
                continue

            # Clean up
            part = part.rstrip('.')

            # Skip if just numbers or special chars
            if not re.search(r'[a-zA-Z]', part):
                continue

            # Remove leading 'and'
            part = re.sub(r'^and\s+', '', part, flags=re.IGNORECASE)

            ingredients.append(part)

        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for ing in ingredients:
            ing_lower = ing.lower()
            if ing_lower not in seen and ing_lower != 'and':
                seen.add(ing_lower)
                unique.append(ing)

        return unique[:50]  # Limit to 50

    def process_product(self, product):
        """Process a single product"""
        product_key = product['product_key']
        product_name = product['product_name']

        logger.info(f"\nProcessing: {product_name}")

        # Build URL from product_key
        # AADF URLs typically follow pattern: /dog-food-reviews/[id]/[slug]
        # We need to find the actual URL - check if it's in product_url field

        if product.get('product_url'):
            url = product['product_url']
            if not url.startswith('http'):
                url = f"https://www.allaboutdogfood.co.uk{url}"
        else:
            # Try to construct from product_key
            # This is a fallback - ideally we should have the URL
            logger.warning(f"No product_url for {product_key}, skipping")
            return None

        logger.info(f"  URL: {url}")

        # Scrape the page
        html = self.scrape_with_scrapingbee(url)

        if not html:
            logger.error(f"  Failed to scrape")
            self.failed.append(product_key)
            return None

        # Parse HTML
        soup = BeautifulSoup(html, 'html.parser')

        # Extract ingredients from mixing bowl
        ingredients_text = self.extract_ingredients_from_mixing_bowl(soup)

        if ingredients_text:
            logger.info(f"  Found ingredients: {ingredients_text[:100]}...")
            ingredients_array = self.parse_ingredients_to_array(ingredients_text)
            logger.info(f"  Parsed to {len(ingredients_array)} ingredients")
        else:
            logger.warning(f"  No ingredients found")
            ingredients_array = []

        # Extract nutrition from JavaScript
        nutrition = self.extract_nutrition_from_javascript(html)

        if nutrition:
            logger.info(f"  Found nutrition: {nutrition}")
        else:
            logger.warning(f"  No nutrition found")

        result = {
            'product_key': product_key,
            'product_name': product_name,
            'brand': product['brand'],
            'url': url,
            'ingredients_raw': ingredients_text,
            'ingredients_array': ingredients_array,
            'nutrition': nutrition,
            'scraped_at': datetime.now().isoformat()
        }

        if ingredients_array or nutrition:
            self.successful.append(product_key)
            logger.info(f"  ✓ SUCCESS")
        else:
            self.failed.append(product_key)
            logger.warning(f"  ✗ No data extracted")

        return result

    def run_test(self):
        """Run test on 5 products"""
        logger.info("="*60)
        logger.info("AADF RELAXED EXTRACTION TEST - 5 PRODUCTS")
        logger.info("="*60)

        # Get test products
        products = self.get_test_products(5)
        logger.info(f"Testing with {len(products)} products\n")

        results = []

        for i, product in enumerate(products, 1):
            logger.info(f"[{i}/{len(products)}] {product['product_name']}")

            result = self.process_product(product)
            if result:
                results.append(result)

            # Rate limiting
            if i < len(products):
                time.sleep(3)

        # Summary
        logger.info("\n" + "="*60)
        logger.info("TEST SUMMARY")
        logger.info("="*60)
        logger.info(f"Successful: {len(self.successful)}/{len(products)}")
        logger.info(f"Failed: {len(self.failed)}/{len(products)}")

        if self.successful:
            logger.info("\nSuccessful products:")
            for pk in self.successful:
                logger.info(f"  ✓ {pk}")

        if self.failed:
            logger.info("\nFailed products:")
            for pk in self.failed:
                logger.info(f"  ✗ {pk}")

        # Save results for analysis
        output_file = f"aadf_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"\nResults saved to: {output_file}")

        # Show sample of extracted data
        if results:
            logger.info("\nSample extracted data:")
            for r in results[:2]:
                logger.info(f"\n{r['product_name']}:")
                if r.get('ingredients_array'):
                    logger.info(f"  Ingredients: {', '.join(r['ingredients_array'][:5])}...")
                if r.get('nutrition'):
                    logger.info(f"  Nutrition: {r['nutrition']}")

        return results

if __name__ == "__main__":
    scraper = RelaxedAADFScraper()
    results = scraper.run_test()

    # Check if we should proceed with full scraping
    success_rate = len(scraper.successful) / 5 if results else 0

    if success_rate >= 0.6:  # 60% success rate
        logger.info(f"\n✓ Test successful ({success_rate*100:.0f}% success rate)")
        logger.info("Ready to proceed with full scraping!")
    else:
        logger.info(f"\n✗ Test needs improvement ({success_rate*100:.0f}% success rate)")
        logger.info("Review the extraction patterns before proceeding")