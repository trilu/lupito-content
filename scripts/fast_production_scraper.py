#!/usr/bin/env python3
"""
Fast production scraper for large-scale Zooplus scraping
Optimized delays (10-15 seconds) for faster progress to 95% coverage
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

class FastProductionScraper:
    def __init__(self, batch_size: int = 100):
        self.api_key = SCRAPINGBEE_API_KEY
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(GCS_BUCKET)
        
        # Session tracking
        self.session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.gcs_folder = f"scraped/zooplus/{self.session_id}"
        
        # Optimized parameters for speed
        self.min_delay = 10  # 10 seconds minimum
        self.max_delay = 15  # 15 seconds maximum
        self.batch_size = batch_size
        
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
        
        print(f"🚀 FAST PRODUCTION SCRAPER")
        print(f"Session: {self.session_id}")
        print(f"Batch size: {batch_size}")
        print(f"Delays: {self.min_delay}-{self.max_delay} seconds")
        print(f"GCS: gs://{GCS_BUCKET}/{self.gcs_folder}/")
    
    def get_products_to_scrape(self) -> List[Dict]:
        """Get products prioritizing those missing both ingredients and nutrition"""
        
        print(f"\nFetching {self.batch_size} priority products...")
        
        # Priority 1: Missing both ingredients AND nutrition
        response = self.supabase.table('foods_canonical').select(
            'product_key, product_name, brand, product_url'
        ).ilike('product_url', '%zooplus%')\
        .is_('ingredients_raw', 'null')\
        .is_('protein_percent', 'null')\
        .limit(self.batch_size).execute()
        
        products = response.data if response.data else []
        
        # Priority 2: If not enough, get products missing ingredients only
        if len(products) < self.batch_size:
            response2 = self.supabase.table('foods_canonical').select(
                'product_key, product_name, brand, product_url'
            ).ilike('product_url', '%zooplus%')\
            .is_('ingredients_raw', 'null')\
            .limit(self.batch_size - len(products)).execute()
            
            if response2.data:
                products.extend(response2.data)
        
        # Shuffle to avoid patterns
        random.shuffle(products)
        
        print(f"Found {len(products)} products to scrape")
        return products
    
    def scrape_product(self, url: str) -> Dict:
        """Fast scraping with optimized settings"""
        
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
            
            # Faster JavaScript execution
            'js_scenario': json.dumps({
                "instructions": [
                    {"wait": 2000},
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
                    {"wait": 1500},
                    {"scroll_y": 1000},
                    {"wait": 1000}
                ]
            })
        }
        
        try:
            response = requests.get(
                'https://app.scrapingbee.com/api/v1/',
                params=params,
                timeout=90
            )
            
            if response.status_code == 200:
                self.stats['consecutive_errors'] = 0
                return self.parse_response(response.text, url)
            else:
                self.stats['consecutive_errors'] += 1
                self.stats['errors'] += 1
                return {'url': url, 'error': f'HTTP {response.status_code}'}
                
        except Exception as e:
            self.stats['consecutive_errors'] += 1
            self.stats['errors'] += 1
            return {'url': url, 'error': str(e)[:200]}
    
    def parse_response(self, html: str, url: str) -> Dict:
        """Parse HTML and extract data"""
        
        soup = BeautifulSoup(html, 'html.parser')
        page_text = soup.get_text(separator='\n', strip=True)
        
        result = {
            'url': url,
            'scraped_at': datetime.now().isoformat(),
            'session_id': self.session_id
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
            print(f"    GCS error: {str(e)[:100]}")
            return False
    
    def run_batch(self):
        """Run the batch scraping"""
        
        # Get products
        products = self.get_products_to_scrape()
        
        if not products:
            print("No products to scrape")
            return
        
        print(f"\n🚀 Starting fast batch of {len(products)} products")
        print("-" * 60)
        
        for i, product in enumerate(products, 1):
            # Stop if too many consecutive errors
            if self.stats['consecutive_errors'] >= 5:
                print(f"\n⚠️ Stopping due to consecutive errors")
                break
            
            print(f"\n[{i}/{len(products)}] {product['product_name'][:50]}...")
            
            # Optimized delay (10-15 seconds)
            if i > 1:
                delay = random.uniform(self.min_delay, self.max_delay)
                print(f"  Waiting {delay:.1f}s...")
                time.sleep(delay)
            
            self.stats['total'] += 1
            
            # Scrape
            result = self.scrape_product(product['product_url'])
            
            # Add metadata
            result['product_key'] = product['product_key']
            result['brand'] = product.get('brand')
            
            # Show results
            if 'ingredients_raw' in result:
                print(f"  ✅ Ingredients: {result['ingredients_raw'][:60]}...")
            
            if 'nutrition' in result:
                nut = result['nutrition']
                nutr_count = len(nut)
                print(f"  ✅ Nutrition ({nutr_count} nutrients): {dict(list(nut.items())[:2])}")
            
            if 'error' in result:
                print(f"  ❌ Error: {result['error']}")
            else:
                print(f"  ✅ Saved to GCS")
            
            # Save to GCS
            self.save_to_gcs(product['product_key'], result)
            
            # Progress update every 10 products
            if i % 10 == 0:
                elapsed = datetime.now() - self.stats['session_start']
                rate = self.stats['total'] / (elapsed.total_seconds() / 3600) if elapsed.total_seconds() > 0 else 0
                print(f"\n--- Progress: {self.stats['successful']}/{self.stats['total']} successful, {rate:.0f}/hour ---")
        
        # Final summary
        self.print_summary()
    
    def print_summary(self):
        """Print final summary"""
        print("\n" + "=" * 60)
        print("FAST SCRAPING SESSION COMPLETE")
        print("=" * 60)
        
        elapsed = datetime.now() - self.stats['session_start']
        
        print(f"Duration: {elapsed}")
        print(f"Total attempted: {self.stats['total']}")
        print(f"Successful: {self.stats['successful']}")
        print(f"With ingredients: {self.stats['with_ingredients']}")
        print(f"With nutrition: {self.stats['with_nutrition']}")
        print(f"Errors: {self.stats['errors']}")
        
        if self.stats['total'] > 0:
            success_rate = self.stats['successful'] / self.stats['total'] * 100
            rate = self.stats['total'] / (elapsed.total_seconds() / 3600) if elapsed.total_seconds() > 0 else 0
            
            print(f"\nSuccess rate: {success_rate:.1f}%")
            print(f"Average rate: {rate:.0f} products/hour")
        
        print(f"\nGCS folder: gs://{GCS_BUCKET}/{self.gcs_folder}/")
        print(f"\nNext step:")
        print(f"  python scripts/process_gcs_scraped_data.py {self.gcs_folder}")

def main():
    """Run fast production scraper"""
    
    # Get batch size from command line or default to 100
    batch_size = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    
    scraper = FastProductionScraper(batch_size=batch_size)
    scraper.run_batch()

if __name__ == "__main__":
    main()