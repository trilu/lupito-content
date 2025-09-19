#!/usr/bin/env python3
"""
Scrape PetFoodExpert.com products missing ingredients
Based on successful Zooplus orchestrator pattern
Target: 3,292 products
"""

import os
import sys
import json
import time
import random
import argparse
from datetime import datetime
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google.cloud import storage
from supabase import create_client
import re

load_dotenv()

SCRAPINGBEE_API_KEY = os.getenv('SCRAPING_BEE')
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

class PetFoodExpertScraper:
    def __init__(self, session_name: str = "us1", batch_size: int = 100, offset: int = 0):
        self.session_name = session_name
        self.batch_size = batch_size
        self.offset = offset
        
        # Use proven session configurations from orchestrator
        session_configs = {
            "us1": {"country_code": "us", "min_delay": 10, "max_delay": 20},
            "gb1": {"country_code": "gb", "min_delay": 12, "max_delay": 22},
            "de1": {"country_code": "de", "min_delay": 15, "max_delay": 25},
            "ca1": {"country_code": "ca", "min_delay": 18, "max_delay": 28},
            "fr1": {"country_code": "fr", "min_delay": 20, "max_delay": 30}
        }
        
        config = session_configs.get(session_name, session_configs["us1"])
        self.country_code = config["country_code"]
        self.min_delay = config["min_delay"]
        self.max_delay = config["max_delay"]
        
        # Initialize services
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/sergiubiris/Desktop/lupito-content/secrets/gcp-sa.json'
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(GCS_BUCKET)
        
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Create session folder
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.gcs_folder = f"scraped/petfoodexpert/{timestamp}_{session_name}"
        
        # Statistics
        self.stats = {
            'total': 0,
            'successful': 0,
            'with_ingredients': 0,
            'with_nutrition': 0,
            'errors': 0,
            'consecutive_errors': 0,
            'session_start': datetime.now()
        }
        
        print(f"🚀 PETFOODEXPERT SCRAPER - Session: {session_name}")
        print(f"   Country: {self.country_code}")
        print(f"   Delays: {self.min_delay}-{self.max_delay}s")
        print(f"   Batch: {batch_size} products, offset {offset}")
        print(f"   GCS: gs://{GCS_BUCKET}/{self.gcs_folder}/")
        print("-" * 50)
    
    def load_products(self) -> List[Dict]:
        """Load products from database that need ingredients"""
        try:
            # Query for PetFoodExpert products missing ingredients
            response = self.supabase.table('foods_canonical')\
                .select('product_key, product_name, brand, product_url')\
                .ilike('product_url', '%petfoodexpert%')\
                .is_('ingredients_raw', 'null')\
                .range(self.offset, self.offset + self.batch_size - 1)\
                .execute()
            
            products = response.data
            print(f"📦 Loaded {len(products)} products to scrape")
            
            # Show sample
            if products:
                print(f"   First: {products[0]['product_name'][:50]}")
                print(f"   Last: {products[-1]['product_name'][:50]}")
            
            return products
            
        except Exception as e:
            print(f"❌ Error loading products: {e}")
            return []
    
    def scrape_product(self, url: str, retry_count: int = 0) -> Dict:
        """Scrape using simple approach for PetFoodExpert"""
        
        # PetFoodExpert doesn't need JS rendering
        params = {
            'api_key': SCRAPINGBEE_API_KEY,
            'url': url,
            'render_js': 'false',  # No JS needed
            'premium_proxy': 'true',
            'country_code': self.country_code
        }
        
        try:
            response = requests.get(
                'https://app.scrapingbee.com/api/v1/',
                params=params,
                timeout=60
            )
            
            if response.status_code == 200:
                return self.parse_response(response.text, url)
            elif response.status_code == 429 and retry_count < 3:
                # Rate limited, wait and retry
                wait_time = 60 * (retry_count + 1)
                print(f"   ⏳ Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
                return self.scrape_product(url, retry_count + 1)
            else:
                return {'url': url, 'error': f'HTTP {response.status_code}'}
                
        except Exception as e:
            return {'url': url, 'error': str(e)[:100]}
    
    def parse_response(self, html: str, url: str) -> Dict:
        """Parse PetFoodExpert HTML for ingredients"""
        
        soup = BeautifulSoup(html, 'html.parser')
        page_text = soup.get_text(separator='\n', strip=True)
        
        result = {
            'url': url,
            'scraped_at': datetime.now().isoformat(),
            'session': self.session_name,
            'country_code': self.country_code,
            'source': 'petfoodexpert'
        }
        
        # Check for 404/error pages
        if '404' in html or 'Page not found' in html:
            result['error'] = '404 - Page not found'
            return result
        
        # Get product name from h1
        h1 = soup.find('h1')
        if h1:
            result['product_name'] = h1.text.strip()
        
        # PetFoodExpert-specific extraction patterns
        ingredients_patterns = [
            # Pattern 1: After "Ingredients" heading
            r'Ingredients\s*\n([^\n]{20,1500})',
            r'Ingredients[\s:]*([A-Za-z][^.]{30,1500})',
            # Pattern 2: With colon
            r'Ingredients:\s*([^\n]{20,1500})',
            # Pattern 3: More flexible
            r'Ingredients[^:]*:\s*([^.]{20,1500})',
            # Pattern 4: Very flexible
            r'(?:Ingredients|Composition)[:\s]*([^.]{20,1500})'
        ]
        
        # Try each pattern
        for i, pattern in enumerate(ingredients_patterns, 1):
            match = re.search(pattern, page_text, re.IGNORECASE | re.MULTILINE)
            if match:
                ingredients = match.group(1).strip()
                
                # Clean up the ingredients
                ingredients = re.sub(r'\s+', ' ', ingredients)  # Normalize whitespace
                
                # Validate it contains food-related words
                food_words = ['rice', 'maize', 'wheat', 'meat', 'chicken', 'beef', 
                             'fish', 'protein', 'oil', 'flour', 'meal', 'vegetable',
                             'mineral', 'vitamin', '%', 'powder', 'gluten']
                
                if any(word in ingredients.lower() for word in food_words):
                    result['ingredients_raw'] = ingredients[:3000]
                    result['pattern_used'] = f"Pattern {i}"
                    self.stats['with_ingredients'] += 1
                    break
        
        # Extract nutrition data (if available)
        nutrition = {}
        nutrition_patterns = [
            (r'(?:Crude\s+)?Protein[:\s]+(\d+(?:\.\d+)?)\s*%', 'protein_percent'),
            (r'(?:Crude\s+)?(?:Fat|Oils)[:\s]+(\d+(?:\.\d+)?)\s*%', 'fat_percent'),
            (r'(?:Crude\s+)?Fib(?:re|er)[:\s]+(\d+(?:\.\d+)?)\s*%', 'fiber_percent'),
            (r'(?:Crude\s+)?Ash[:\s]+(\d+(?:\.\d+)?)\s*%', 'ash_percent'),
            (r'Moisture[:\s]+(\d+(?:\.\d+)?)\s*%', 'moisture_percent')
        ]
        
        for pattern, key in nutrition_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                nutrition[key] = float(match.group(1))
        
        if nutrition:
            result['nutrition'] = nutrition
            self.stats['with_nutrition'] += 1
        
        # Mark as successful if we got data
        if 'ingredients_raw' in result or nutrition:
            self.stats['successful'] += 1
            self.stats['consecutive_errors'] = 0
        else:
            self.stats['consecutive_errors'] += 1
        
        return result
    
    def save_to_gcs(self, product_key: str, data: Dict) -> bool:
        """Save to GCS"""
        try:
            # Clean product key for filename
            safe_key = product_key.replace('|', '_').replace('/', '_')
            filename = f"{self.gcs_folder}/{safe_key}.json"
            
            blob = self.bucket.blob(filename)
            blob.upload_from_string(
                json.dumps(data, indent=2, ensure_ascii=False),
                content_type='application/json'
            )
            return True
            
        except Exception as e:
            print(f"   ❌ GCS error: {str(e)[:100]}")
            return False
    
    def run(self):
        """Main execution"""
        
        # Load products
        products = self.load_products()
        if not products:
            print("❌ No products to scrape")
            return
        
        print(f"\n🎯 Starting scraping of {len(products)} products\n")
        
        # Process each product
        for i, product in enumerate(products, 1):
            # Check for too many consecutive errors
            if self.stats['consecutive_errors'] >= 10:
                print("\n⚠️ Stopping due to 10 consecutive errors")
                break
            
            # Progress indicator
            print(f"[{i}/{len(products)}] {product['product_name'][:50]}...")
            
            self.stats['total'] += 1
            
            # Scrape the product
            result = self.scrape_product(product['product_url'])
            
            # Add product metadata
            result['product_key'] = product['product_key']
            result['brand'] = product.get('brand')
            
            # Show result
            if 'error' in result:
                if '404' in result.get('error', ''):
                    print(f"   ⏭️ Skipping: 404 page")
                else:
                    print(f"   ❌ Error: {result['error']}")
                    self.stats['errors'] += 1
            else:
                indicators = []
                if 'ingredients_raw' in result:
                    pattern = result.get('pattern_used', 'Unknown')
                    indicators.append(f"ingredients ({pattern})")
                if 'nutrition' in result:
                    indicators.append(f"nutrition ({len(result['nutrition'])} values)")
                
                if indicators:
                    print(f"   ✅ Found: {', '.join(indicators)}")
                else:
                    print(f"   ⚠️ No data extracted")
            
            # Save to GCS
            if self.save_to_gcs(product['product_key'], result):
                print(f"   💾 Saved to GCS")
            
            # Delay between requests (except first)
            if i > 1 and i < len(products):
                if 'error' in result and '404' in result.get('error', ''):
                    delay = random.uniform(3, 5)  # Short delay for 404s
                else:
                    delay = random.uniform(self.min_delay, self.max_delay)
                print(f"   ⏱️ Waiting {delay:.1f}s...")
                time.sleep(delay)
            
            # Every 10 products, print mini summary
            if i % 10 == 0:
                elapsed = datetime.now() - self.stats['session_start']
                if self.stats['total'] > 0:
                    success_rate = self.stats['with_ingredients'] / self.stats['total'] * 100
                    print(f"\n   --- Progress: {i}/{len(products)} | Success: {success_rate:.1f}% | Elapsed: {elapsed} ---\n")
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print session summary"""
        print("\n" + "=" * 50)
        print("📊 SCRAPING SESSION COMPLETE")
        print("=" * 50)
        
        elapsed = datetime.now() - self.stats['session_start']
        
        print(f"Session: {self.session_name}")
        print(f"Duration: {elapsed}")
        print(f"Total processed: {self.stats['total']}")
        print(f"Successful: {self.stats['successful']}")
        print(f"With ingredients: {self.stats['with_ingredients']}")
        print(f"With nutrition: {self.stats['with_nutrition']}")
        print(f"Errors: {self.stats['errors']}")
        
        if self.stats['total'] > 0:
            success_rate = self.stats['with_ingredients'] / self.stats['total'] * 100
            print(f"Success rate: {success_rate:.1f}%")
        
        print(f"\n📁 GCS folder: gs://{GCS_BUCKET}/{self.gcs_folder}/")
        print("=" * 50)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Scrape PetFoodExpert products')
    parser.add_argument('--session', type=str, default='us1',
                       choices=['us1', 'gb1', 'de1', 'ca1', 'fr1'],
                       help='Session name (country code)')
    parser.add_argument('--batch', type=int, default=100,
                       help='Batch size')
    parser.add_argument('--offset', type=int, default=0,
                       help='Starting offset in database')
    
    args = parser.parse_args()
    
    # Create and run scraper
    scraper = PetFoodExpertScraper(
        session_name=args.session,
        batch_size=args.batch,
        offset=args.offset
    )
    scraper.run()

if __name__ == "__main__":
    main()