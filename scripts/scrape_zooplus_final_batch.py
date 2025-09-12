#!/usr/bin/env python3
"""
Final Zooplus batch scraper with database updates
Scrapes ingredients and nutrition data from Zooplus products
"""

import os
import re
import json
import time
import random
from typing import Dict, List, Optional
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SCRAPINGBEE_API_KEY = os.getenv('SCRAPING_BEE')
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

class ZooplusFinalBatchScraper:
    def __init__(self):
        self.api_key = SCRAPINGBEE_API_KEY
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.stats = {
            'total': 0,
            'successful': 0,
            'with_ingredients': 0,
            'with_nutrition': 0,
            'database_updated': 0,
            'errors': 0
        }
    
    def get_products_to_scrape(self, limit: int = 20) -> List[Dict]:
        """Get Zooplus products without ingredients"""
        
        print("Fetching products without ingredients...")
        
        try:
            response = self.supabase.table('foods_canonical').select(
                'product_key, product_name, brand, product_url'
            ).ilike('product_url', '%zooplus%').is_('ingredients_raw', 'null').limit(limit).execute()
            
            products = response.data if response.data else []
            print(f"Found {len(products)} products without ingredients")
            return products
            
        except Exception as e:
            print(f"Database error: {e}")
            return []
    
    def scrape_product(self, url: str) -> Optional[Dict]:
        """Scrape a single Zooplus product"""
        
        # Clean URL
        if '?activeVariant=' in url:
            url = url.split('?activeVariant=')[0]
        
        params = {
            'api_key': self.api_key,
            'url': url,
            'render_js': 'true',
            'premium_proxy': 'true',
            'stealth_proxy': 'true',
            'country_code': 'us',
            'return_page_source': 'true',
            
            # Simplified JS scenario
            'js_scenario': json.dumps({
                "instructions": [
                    {"wait": 3000},
                    {"scroll_y": 500},
                    {"wait": 1000},
                    {"evaluate": """
                        document.querySelectorAll('button, [role="tab"]').forEach(el => {
                            const text = el.textContent.toLowerCase();
                            if (text.includes('detail') || text.includes('description')) {
                                el.click();
                            }
                        });
                    """},
                    {"wait": 2000},
                    {"scroll_y": 1000},
                    {"wait": 1000}
                ]
            })
        }
        
        try:
            response = requests.get(
                'https://app.scrapingbee.com/api/v1/',
                params=params,
                timeout=120
            )
            
            if response.status_code == 200:
                return self.parse_response(response.text, url)
            else:
                print(f"    ✗ Error {response.status_code}")
                self.stats['errors'] += 1
                return None
                
        except Exception as e:
            print(f"    ✗ Exception: {str(e)[:100]}")
            self.stats['errors'] += 1
            return None
    
    def parse_response(self, html: str, url: str) -> Dict:
        """Parse the HTML response"""
        
        soup = BeautifulSoup(html, 'html.parser')
        page_text = soup.get_text(separator='\n', strip=True)
        
        result = {'url': url, 'success': False}
        
        # Get product name
        h1 = soup.find('h1')
        if h1:
            result['name'] = h1.text.strip()
        
        # Extract ingredients
        ingredients_found = False
        
        # Try multiple patterns
        patterns = [
            r'(?:Composition|Ingredients)[:\s]*\n?([^\n]{20,}?)(?:\n(?:Analytical|Additives|Nutritional)|$)',
            r'(?:Composition|Ingredients)[:\s]*([A-Za-z][^.]{30,}(?:\.[^.]{20,})*?)(?:Analytical|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, page_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match:
                ingredients = match.group(1).strip()
                # Validate
                food_words = ['meat', 'chicken', 'beef', 'fish', 'rice', 'corn', 'wheat', 'protein', 'meal']
                if any(word in ingredients.lower() for word in food_words):
                    result['ingredients_raw'] = ingredients[:2000]
                    ingredients_found = True
                    result['success'] = True
                    self.stats['with_ingredients'] += 1
                    break
        
        # Try HTML elements if not found
        if not ingredients_found:
            for elem in soup.find_all(['div', 'p', 'section']):
                text = elem.get_text(strip=True)
                if text.startswith(('Composition:', 'Ingredients:')):
                    if len(text) > 50:
                        result['ingredients_raw'] = text[:2000]
                        ingredients_found = True
                        result['success'] = True
                        self.stats['with_ingredients'] += 1
                        break
        
        # Extract nutrition
        nutrition = {}
        
        if re.search(r'Protein[:\s]+\d', page_text, re.I):
            match = re.search(r'(?:Crude\s+)?Protein[:\s]+(\d+(?:\.\d+)?)\s*%', page_text, re.I)
            if match:
                nutrition['protein_percent'] = float(match.group(1))
        
        if re.search(r'Fat[:\s]+\d', page_text, re.I):
            match = re.search(r'(?:Crude\s+)?(?:Fat|Oils)[:\s]+(\d+(?:\.\d+)?)\s*%', page_text, re.I)
            if match:
                nutrition['fat_percent'] = float(match.group(1))
        
        if re.search(r'Fib(?:re|er)[:\s]+\d', page_text, re.I):
            match = re.search(r'(?:Crude\s+)?Fib(?:re|er)[:\s]+(\d+(?:\.\d+)?)\s*%', page_text, re.I)
            if match:
                nutrition['fiber_percent'] = float(match.group(1))
        
        if re.search(r'Ash[:\s]+\d', page_text, re.I):
            match = re.search(r'(?:Crude\s+)?Ash[:\s]+(\d+(?:\.\d+)?)\s*%', page_text, re.I)
            if match:
                nutrition['ash_percent'] = float(match.group(1))
        
        if re.search(r'Moisture[:\s]+\d', page_text, re.I):
            match = re.search(r'Moisture[:\s]+(\d+(?:\.\d+)?)\s*%', page_text, re.I)
            if match:
                nutrition['moisture_percent'] = float(match.group(1))
        
        if nutrition:
            result.update(nutrition)
            self.stats['with_nutrition'] += 1
            result['success'] = True
        
        if result.get('success'):
            self.stats['successful'] += 1
        
        return result
    
    def update_database(self, product_key: str, scraped_data: Dict) -> bool:
        """Update database with scraped data"""
        
        update_data = {}
        
        # Add ingredients
        if 'ingredients_raw' in scraped_data:
            update_data['ingredients_raw'] = scraped_data['ingredients_raw']
            update_data['ingredients_source'] = 'site'
            
            # Tokenize
            tokens = self.tokenize_ingredients(scraped_data['ingredients_raw'])
            if tokens:
                update_data['ingredients_tokens'] = tokens
        
        # Add nutrition
        if 'protein_percent' in scraped_data:
            update_data['protein_percent'] = scraped_data['protein_percent']
            update_data['macros_source'] = 'site'
        
        if 'fat_percent' in scraped_data:
            update_data['fat_percent'] = scraped_data['fat_percent']
            update_data['macros_source'] = 'site'
        
        if 'fiber_percent' in scraped_data:
            update_data['fiber_percent'] = scraped_data['fiber_percent']
        
        if 'ash_percent' in scraped_data:
            update_data['ash_percent'] = scraped_data['ash_percent']
        
        if 'moisture_percent' in scraped_data:
            update_data['moisture_percent'] = scraped_data['moisture_percent']
        
        if update_data:
            try:
                self.supabase.table('foods_canonical').update(
                    update_data
                ).eq('product_key', product_key).execute()
                
                self.stats['database_updated'] += 1
                return True
                
            except Exception as e:
                print(f"    ✗ Database update error: {str(e)[:100]}")
                return False
        
        return False
    
    def tokenize_ingredients(self, text: str) -> List[str]:
        """Tokenize ingredients text"""
        
        # Remove percentages and parentheses
        text = re.sub(r'\([^)]*\)', '', text)
        text = re.sub(r'\d+\.?\d*\s*%', '', text)
        
        # Split and clean
        tokens = []
        for part in re.split(r'[,;]', text)[:50]:
            part = re.sub(r'[^\w\s-]', ' ', part)
            part = ' '.join(part.split()).strip().lower()
            if part and 2 < len(part) < 50:
                # Skip common non-ingredients
                if part not in ['ingredients', 'composition', 'analytical constituents']:
                    tokens.append(part)
        
        return tokens
    
    def run_batch(self, batch_size: int = 20):
        """Run batch scraping with proper delays"""
        
        print("\nZOOPLUS BATCH SCRAPING")
        print("=" * 60)
        
        # Get products
        products = self.get_products_to_scrape(batch_size)
        
        if not products:
            print("No products to scrape")
            return
        
        print(f"\nStarting batch of {len(products)} products")
        print("Using 15-20 second delays to avoid rate limits")
        print("-" * 60)
        
        for i, product in enumerate(products, 1):
            print(f"\n[{i}/{len(products)}] {product.get('product_name', 'Unknown')[:60]}...")
            
            # Rate limiting with safe delays
            if i > 1:
                delay = random.uniform(15, 20)
                print(f"  Waiting {delay:.1f} seconds...")
                time.sleep(delay)
            
            self.stats['total'] += 1
            
            # Scrape
            result = self.scrape_product(product.get('product_url', ''))
            
            if result and result.get('success'):
                # Show what we found
                if 'ingredients_raw' in result:
                    print(f"  ✓ Ingredients: {result['ingredients_raw'][:80]}...")
                
                if 'protein_percent' in result:
                    nutrition_str = f"Protein={result['protein_percent']}%"
                    if 'fat_percent' in result:
                        nutrition_str += f", Fat={result['fat_percent']}%"
                    if 'fiber_percent' in result:
                        nutrition_str += f", Fiber={result['fiber_percent']}%"
                    print(f"  ✓ Nutrition: {nutrition_str}")
                
                # Update database
                if self.update_database(product['product_key'], result):
                    print(f"  ✓ Database updated")
            else:
                print(f"  ✗ No data extracted")
            
            # Stop if too many errors
            if self.stats['errors'] > 5:
                print("\n⚠️ Too many errors, stopping")
                break
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Print batch summary"""
        
        print("\n" + "=" * 60)
        print("BATCH SUMMARY")
        print("=" * 60)
        print(f"Total attempted: {self.stats['total']}")
        print(f"Successful scrapes: {self.stats['successful']}")
        print(f"With ingredients: {self.stats['with_ingredients']}")
        print(f"With nutrition: {self.stats['with_nutrition']}")
        print(f"Database updated: {self.stats['database_updated']}")
        print(f"Errors: {self.stats['errors']}")
        
        if self.stats['total'] > 0:
            success_rate = self.stats['successful'] / self.stats['total'] * 100
            print(f"\nSuccess rate: {success_rate:.1f}%")
            
            if self.stats['with_ingredients'] > 0:
                ingredients_rate = self.stats['with_ingredients'] / self.stats['total'] * 100
                print(f"Ingredients extraction rate: {ingredients_rate:.1f}%")
            
            if self.stats['with_nutrition'] > 0:
                nutrition_rate = self.stats['with_nutrition'] / self.stats['total'] * 100
                print(f"Nutrition extraction rate: {nutrition_rate:.1f}%")

def main():
    """Run the final batch scraper"""
    
    scraper = ZooplusFinalBatchScraper()
    
    # Run a batch of 3 products for testing
    scraper.run_batch(batch_size=3)

if __name__ == "__main__":
    main()