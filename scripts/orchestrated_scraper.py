#!/usr/bin/env python3
"""
Orchestrated Scraper - Individual scraper managed by orchestrator
Accepts configuration via command line arguments
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

class OrchestratedScraper:
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
        self.gcs_folder = f"scraped/zooplus/{self.session_id}"
        
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
        
        print(f"[{name}] 🚀 ORCHESTRATED SCRAPER STARTED")
        print(f"[{name}] Country: {country_code}, Delays: {min_delay}-{max_delay}s")
        print(f"[{name}] Batch: {batch_size}, Offset: {offset}")
        print(f"[{name}] GCS: gs://{GCS_BUCKET}/{self.gcs_folder}/")
    
    def get_products(self) -> List[Dict]:
        """Get products with specific offset"""
        try:
            response = self.supabase.table('foods_canonical').select(
                'product_key, product_name, brand, product_url'
            ).ilike('product_url', '%zooplus.com%')\
            .is_('ingredients_raw', 'null')\
            .range(self.offset, self.offset + self.batch_size - 1).execute()
            
            products = response.data if response.data else []
            print(f"[{self.name}] Found {len(products)} products (offset: {self.offset})")
            return products
        except Exception as e:
            print(f"[{self.name}] Error fetching products: {e}")
            return []
    
    def scrape_product(self, url: str) -> Dict:
        """Scrape with proven parameters"""
        
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
        """Parse HTML response"""
        
        soup = BeautifulSoup(html, 'html.parser')
        page_text = soup.get_text(separator='\n', strip=True)
        
        result = {
            'url': url,
            'scraped_at': datetime.now().isoformat(),
            'session_id': self.session_id,
            'country_code': self.country_code,
            'scraper_name': self.name
        }
        
        # Product name
        h1 = soup.find('h1')
        if h1:
            result['product_name'] = h1.text.strip()
        
        # Extract ingredients
        import re
        ingredients_patterns = [
            r'(?:Composition|Ingredients)[:\s]*\n?([^\n]{20,}?)(?:\n(?:Analytical|Additives|Nutritional)|$)',
            r'(?:Composition|Ingredients)[:\s]*([A-Za-z][^.]{30,}(?:\.[^.]{20,})*?)(?:Analytical|$)',
        ]
        
        for pattern in ingredients_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match:
                ingredients = match.group(1).strip()
                if any(word in ingredients.lower() for word in ['meat', 'chicken', 'beef', 'fish', 'rice', 'wheat']):
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
            result['nutrition'] = nutrition
            self.stats['with_nutrition'] += 1
        
        if 'ingredients_raw' in result or nutrition:
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
                print(f"[{self.name}] ❌ Error: {result['error']}")
            else:
                success_indicators = []
                if 'ingredients_raw' in result:
                    success_indicators.append("ingredients")
                if 'nutrition' in result:
                    success_indicators.append(f"nutrition({len(result['nutrition'])})")
                
                if success_indicators:
                    print(f"[{self.name}] ✅ Found: {', '.join(success_indicators)}")
                else:
                    print(f"[{self.name}] ⚠️ Scraped but no data")
            
            # Save to GCS
            self.save_to_gcs(product['product_key'], result)
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Print summary"""
        print(f"\n[{self.name}] " + "=" * 40)
        print(f"[{self.name}] SCRAPING BATCH COMPLETE")
        print(f"[{self.name}] " + "=" * 40)
        
        elapsed = datetime.now() - self.stats['session_start']
        
        print(f"[{self.name}] Duration: {elapsed}")
        print(f"[{self.name}] Total: {self.stats['total']}")
        print(f"[{self.name}] Successful: {self.stats['successful']}")
        print(f"[{self.name}] With ingredients: {self.stats['with_ingredients']}")
        print(f"[{self.name}] With nutrition: {self.stats['with_nutrition']}")
        print(f"[{self.name}] Errors: {self.stats['errors']}")
        
        if self.stats['total'] > 0:
            success_rate = self.stats['successful'] / self.stats['total'] * 100
            print(f"[{self.name}] Success rate: {success_rate:.1f}%")
        
        print(f"[{self.name}] GCS: gs://{GCS_BUCKET}/{self.gcs_folder}/")

def main():
    """Run orchestrated scraper with command line arguments"""
    if len(sys.argv) < 7:
        print("Usage: python orchestrated_scraper.py <name> <country> <min_delay> <max_delay> <batch_size> <offset>")
        return
    
    try:
        name = sys.argv[1]
        country_code = sys.argv[2]
        min_delay = int(sys.argv[3])
        max_delay = int(sys.argv[4])
        batch_size = int(sys.argv[5])
        offset = int(sys.argv[6])
        
        scraper = OrchestratedScraper(name, country_code, min_delay, max_delay, batch_size, offset)
        scraper.run_batch()
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()