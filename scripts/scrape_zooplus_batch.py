#!/usr/bin/env python3
"""
Batch scrape Zooplus products and update database
Focus on products without ingredients
"""

import os
import json
import re
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

class ZooplusBatchScraper:
    def __init__(self):
        self.api_key = SCRAPINGBEE_API_KEY
        self.base_url = 'https://app.scrapingbee.com/api/v1/'
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.stats = {
            'total': 0,
            'successful': 0,
            'with_ingredients': 0,
            'with_nutrition': 0,
            'database_updated': 0
        }
        
    def get_products_without_ingredients(self, limit: int = 50) -> List[Dict]:
        """Get Zooplus products that don't have ingredients yet"""
        
        print("Fetching products without ingredients...")
        
        try:
            # Get products from Zooplus that don't have ingredients
            response = self.supabase.table('foods_canonical').select(
                'product_key, product_name, brand, product_url'
            ).ilike('product_url', '%zooplus.com%').is_('ingredients_raw', 'null').limit(limit).execute()
        except Exception as e:
            print(f"Database query error: {e}")
            return []
        
        products = response.data if response.data else []
        print(f"Found {len(products)} products without ingredients")
        
        return products
        
    def scrape_product(self, url: str) -> Optional[Dict]:
        """Scrape a single product"""
        
        # Remove activeVariant parameter if present
        if '?activeVariant=' in url:
            url = url.split('?activeVariant=')[0]
        
        params = {
            'api_key': self.api_key,
            'url': url,
            'render_js': 'true',
            'wait': '7000',
            'premium_proxy': 'true',
            'stealth_proxy': 'true',
            'country_code': 'us',
            'return_page_source': 'true',
        }
        
        try:
            response = requests.get(
                self.base_url,
                params=params,
                timeout=90
            )
            
            if response.status_code == 200:
                return self.parse_page(response.text, url)
            else:
                print(f"    Error {response.status_code}")
                return None
                
        except Exception as e:
            print(f"    Exception: {str(e)[:100]}")
            return None
    
    def parse_page(self, html: str, url: str) -> Dict:
        """Parse the scraped page"""
        soup = BeautifulSoup(html, 'html.parser')
        
        result = {'url': url, 'success': False}
        
        # Get product name
        h1 = soup.find('h1')
        if h1:
            result['name'] = h1.text.strip()
        
        # Search for ingredients
        page_text = soup.get_text(separator='\n', strip=True)
        
        # Look for composition/ingredients with better patterns
        ingredients_patterns = [
            # Standard composition pattern
            r'(?:Composition|Ingredients)[:\s]*\n?([^\n]{20,}?)(?:\nAnalytical|\nAdditives|\nFeeding|\nNutritional|\n\n)',
            # Ingredients after "Ingredients:" label
            r'Ingredients:\s*\n?([A-Za-z][^\n]{20,}?)(?:\nAnalytical|\nAdditives|\nFeeding)',
            # Sometimes it's just listed after a heading
            r'(?:Composition|Ingredients)\s*\n+([A-Za-z][^.]{30,}(?:\.[^.]{30,})*?)(?:\nAnalytical|\nAdditives|\n\n)',
        ]
        
        for pattern in ingredients_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE | re.MULTILINE)
            if match:
                ingredients = match.group(1).strip()
                # Validate it's real ingredients (has food words)
                if any(word in ingredients.lower() for word in ['meat', 'chicken', 'rice', 'protein', 'meal', 'fish', 'beef', 'lamb', 'corn', 'wheat']):
                    result['ingredients_raw'] = ingredients[:2000]
                    result['success'] = True
                    self.stats['with_ingredients'] += 1
                    break
        
        # Search for nutrition
        nutrition = {}
        
        if 'Protein' in page_text:
            match = re.search(r'(?:Crude\s+)?Protein[:\s]+(\d+\.?\d*)\s*%', page_text, re.I)
            if match:
                nutrition['protein_percent'] = float(match.group(1))
        
        if 'Fat' in page_text:
            match = re.search(r'(?:Crude\s+)?(?:Fat|Oil)[:\s]+(\d+\.?\d*)\s*%', page_text, re.I)
            if match:
                nutrition['fat_percent'] = float(match.group(1))
        
        if 'Fibre' in page_text or 'Fiber' in page_text:
            match = re.search(r'(?:Crude\s+)?Fib(?:re|er)[:\s]+(\d+\.?\d*)\s*%', page_text, re.I)
            if match:
                nutrition['fiber_percent'] = float(match.group(1))
        
        if 'Ash' in page_text:
            match = re.search(r'(?:Crude\s+)?Ash[:\s]+(\d+\.?\d*)\s*%', page_text, re.I)
            if match:
                nutrition['ash_percent'] = float(match.group(1))
        
        if 'Moisture' in page_text:
            match = re.search(r'Moisture[:\s]+(\d+\.?\d*)\s*%', page_text, re.I)
            if match:
                nutrition['moisture_percent'] = float(match.group(1))
        
        if nutrition:
            result.update(nutrition)
            self.stats['with_nutrition'] += 1
        
        if result.get('success') or nutrition:
            self.stats['successful'] += 1
        
        return result
    
    def update_database(self, product_key: str, scraped_data: Dict) -> bool:
        """Update the database with scraped data"""
        
        update_data = {}
        
        # Add ingredients if found
        if 'ingredients_raw' in scraped_data:
            update_data['ingredients_raw'] = scraped_data['ingredients_raw']
            update_data['ingredients_source'] = 'site'
            
            # Tokenize ingredients
            tokens = self.tokenize(scraped_data['ingredients_raw'])
            if tokens:
                update_data['ingredients_tokens'] = tokens
        
        # Add nutrition if found
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
                self.supabase.table('foods_canonical').update(update_data).eq('product_key', product_key).execute()
                self.stats['database_updated'] += 1
                return True
            except Exception as e:
                print(f"    Database update error: {str(e)[:100]}")
                return False
        
        return False
    
    def tokenize(self, text: str) -> List[str]:
        """Tokenize ingredients"""
        # Remove percentages and parentheses
        text = re.sub(r'\([^)]*\)', '', text)
        text = re.sub(r'\d+\.?\d*\s*%', '', text)
        
        # Split and clean
        tokens = []
        for part in re.split(r'[,;]', text)[:50]:
            part = re.sub(r'[^\w\s-]', ' ', part)
            part = ' '.join(part.split()).strip().lower()
            if part and 2 < len(part) < 50:
                tokens.append(part)
        
        return tokens
    
    def run_batch(self, batch_size: int = 50):
        """Run batch scraping"""
        
        print("\nZOOPLUS BATCH SCRAPING")
        print("="*60)
        
        # Get products to scrape
        products = self.get_products_without_ingredients(batch_size)
        
        if not products:
            print("No products to scrape")
            return
        
        print(f"\nStarting batch scrape of {len(products)} products")
        print("Rate limit: 3-5 seconds between requests")
        print("-"*60)
        
        for i, product in enumerate(products, 1):
            print(f"\n[{i}/{len(products)}] {product.get('product_name', 'Unknown')[:50]}...")
            
            # Rate limiting with proper delay to avoid bans
            if i > 1:
                delay = random.uniform(10, 15)  # 10-15 seconds between requests
                print(f"  Waiting {delay:.1f} seconds to avoid rate limits...")
                time.sleep(delay)
            
            self.stats['total'] += 1
            
            # Scrape the product
            result = self.scrape_product(product.get('product_url', ''))
            
            if result:
                if result.get('success'):
                    print(f"  ✅ Found ingredients: {result['ingredients_raw'][:80]}...")
                
                if result.get('protein_percent'):
                    print(f"  ✅ Found nutrition: Protein={result['protein_percent']}%")
                
                # Update database
                if self.update_database(product['product_key'], result):
                    print(f"  ✅ Database updated")
            else:
                print(f"  ❌ Scraping failed")
            
            # Stop if we're getting too many failures
            if i > 10 and self.stats['successful'] < 2:
                print("\n⚠️ Too many failures, stopping")
                break
        
        # Summary
        print("\n" + "="*60)
        print("BATCH SUMMARY")
        print("="*60)
        print(f"Total attempted: {self.stats['total']}")
        print(f"Successful scrapes: {self.stats['successful']}")
        print(f"With ingredients: {self.stats['with_ingredients']}")
        print(f"With nutrition: {self.stats['with_nutrition']}")
        print(f"Database updated: {self.stats['database_updated']}")
        
        if self.stats['total'] > 0:
            success_rate = self.stats['successful'] / self.stats['total'] * 100
            print(f"\nSuccess rate: {success_rate:.1f}%")

def main():
    """Run the batch scraper"""
    
    scraper = ZooplusBatchScraper()
    
    # Start with a small batch of 10 products (safer with longer delays)
    scraper.run_batch(batch_size=10)

if __name__ == "__main__":
    main()