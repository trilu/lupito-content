#!/usr/bin/env python3
"""
Parallel scraper - designed to run multiple sessions with different configurations
Each session uses different country codes and delays to avoid rate limiting
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

class ParallelScraper:
    def __init__(self, session_name: str, config: Dict):
        self.session_name = session_name
        self.config = config
        self.api_key = SCRAPINGBEE_API_KEY
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(GCS_BUCKET)
        
        # Session tracking
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.session_id = f"{timestamp}_{session_name}"
        self.gcs_folder = f"scraped/zooplus/{self.session_id}"
        
        # Configuration-based parameters
        self.min_delay = config['min_delay']
        self.max_delay = config['max_delay']
        self.country_code = config['country_code']
        self.batch_size = config['batch_size']
        self.offset = config.get('offset', 0)
        
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
        
        print(f"🚀 PARALLEL SCRAPER [{session_name}]")
        print(f"Session: {self.session_id}")
        print(f"Country: {self.country_code}")
        print(f"Delays: {self.min_delay}-{self.max_delay}s")
        print(f"Batch: {self.batch_size} (offset: {self.offset})")
    
    def get_products(self) -> List[Dict]:
        """Get products with offset to avoid conflicts between parallel scrapers"""
        
        response = self.supabase.table('foods_canonical').select(
            'product_key, product_name, brand, product_url'
        ).ilike('product_url', '%zooplus.com%')\
        .is_('ingredients_raw', 'null')\
        .range(self.offset, self.offset + self.batch_size - 1).execute()
        
        products = response.data if response.data else []
        print(f"[{self.session_name}] Found {len(products)} products (offset: {self.offset})")
        return products
    
    def scrape_product(self, url: str) -> Dict:
        """Scrape with session-specific configuration"""
        
        # Clean URL
        if '?activeVariant=' in url:
            url = url.split('?activeVariant=')[0]
        
        # Use proven parameters with session-specific country
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
            'country_code': self.country_code
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
            print(f"[{self.session_name}] GCS error: {str(e)[:100]}")
            return False
    
    def run_parallel_batch(self):
        """Run parallel batch scraping"""
        
        products = self.get_products()
        if not products:
            print(f"[{self.session_name}] No products to scrape")
            return
        
        print(f"\n[{self.session_name}] Starting batch of {len(products)} products")
        print("-" * 40)
        
        for i, product in enumerate(products, 1):
            # Stop if too many consecutive errors
            if self.stats['consecutive_errors'] >= 3:
                print(f"\n[{self.session_name}] ⚠️ Stopping due to consecutive errors")
                break
            
            print(f"[{self.session_name}] [{i}/{len(products)}] {product['product_name'][:40]}...")
            
            # Session-specific delay
            if i > 1:
                delay = random.uniform(self.min_delay, self.max_delay)
                print(f"[{self.session_name}] Waiting {delay:.1f}s...")
                time.sleep(delay)
            
            self.stats['total'] += 1
            
            # Scrape
            result = self.scrape_product(product['product_url'])
            
            # Add metadata
            result['product_key'] = product['product_key']
            result['brand'] = product.get('brand')
            
            # Show results
            if 'error' in result:
                print(f"[{self.session_name}] ❌ Error: {result['error']}")
            else:
                success_indicators = []
                if 'ingredients_raw' in result:
                    success_indicators.append("ingredients")
                if 'nutrition' in result:
                    success_indicators.append("nutrition")
                
                if success_indicators:
                    print(f"[{self.session_name}] ✅ Found: {', '.join(success_indicators)}")
                else:
                    print(f"[{self.session_name}] ⚠️ Scraped but no data")
            
            # Save to GCS
            self.save_to_gcs(product['product_key'], result)
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Print summary"""
        print(f"\n[{self.session_name}] " + "=" * 40)
        print(f"[{self.session_name}] SESSION COMPLETE")
        print(f"[{self.session_name}] " + "=" * 40)
        
        elapsed = datetime.now() - self.stats['session_start']
        
        print(f"[{self.session_name}] Duration: {elapsed}")
        print(f"[{self.session_name}] Total: {self.stats['total']}")
        print(f"[{self.session_name}] Successful: {self.stats['successful']}")
        print(f"[{self.session_name}] With ingredients: {self.stats['with_ingredients']}")
        print(f"[{self.session_name}] With nutrition: {self.stats['with_nutrition']}")
        print(f"[{self.session_name}] Errors: {self.stats['errors']}")
        
        if self.stats['total'] > 0:
            success_rate = self.stats['successful'] / self.stats['total'] * 100
            print(f"[{self.session_name}] Success rate: {success_rate:.1f}%")
        
        print(f"[{self.session_name}] GCS: gs://{GCS_BUCKET}/{self.gcs_folder}/")

def main():
    """Run specific parallel session"""
    if len(sys.argv) < 2:
        print("Usage: python parallel_scraper.py <session_name>")
        print("Available sessions: us, gb, de, ca")
        return
    
    session_name = sys.argv[1]
    
    # Predefined configurations for different sessions
    configs = {
        'us': {
            'country_code': 'us',
            'min_delay': 20,
            'max_delay': 30,
            'batch_size': 8,
            'offset': 0
        },
        'gb': {
            'country_code': 'gb', 
            'min_delay': 25,
            'max_delay': 35,
            'batch_size': 8,
            'offset': 8
        },
        'de': {
            'country_code': 'de',
            'min_delay': 30,
            'max_delay': 40,
            'batch_size': 8,
            'offset': 16
        },
        'ca': {
            'country_code': 'ca',
            'min_delay': 35,
            'max_delay': 45,
            'batch_size': 8,
            'offset': 24
        }
    }
    
    if session_name not in configs:
        print(f"Unknown session: {session_name}")
        print("Available sessions:", list(configs.keys()))
        return
    
    scraper = ParallelScraper(session_name, configs[session_name])
    scraper.run_parallel_batch()

if __name__ == "__main__":
    main()