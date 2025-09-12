#!/usr/bin/env python3
"""
Enhanced scraper with maximum ScrapingBee proxy protection
Uses all available anti-detection features
"""

import os
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

class EnhancedProxyScraper:
    def __init__(self, batch_size: int = 30):
        self.api_key = SCRAPINGBEE_API_KEY
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(GCS_BUCKET)
        
        self.session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.gcs_folder = f"scraped/zooplus/{self.session_id}"
        self.batch_size = batch_size
        
        # Conservative delays with proxy protection
        self.min_delay = 15  # 15 seconds minimum
        self.max_delay = 25  # 25 seconds maximum
        
        self.stats = {
            'total': 0,
            'successful': 0,
            'with_ingredients': 0,
            'with_nutrition': 0,
            'errors': 0,
            'consecutive_errors': 0,
            'session_start': datetime.now()
        }
        
        print(f"🛡️ ENHANCED PROXY SCRAPER")
        print(f"Session: {self.session_id}")
        print(f"Batch size: {batch_size}")
        print(f"Enhanced proxy protection: ACTIVE")
    
    def get_products(self) -> List[Dict]:
        """Get priority products to scrape"""
        
        response = self.supabase.table('foods_canonical').select(
            'product_key, product_name, brand, product_url'
        ).ilike('product_url', '%zooplus.com%')\
        .is_('ingredients_raw', 'null')\
        .limit(self.batch_size).execute()
        
        products = response.data if response.data else []
        print(f"Found {len(products)} products to scrape")
        return products
    
    def scrape_with_max_protection(self, url: str) -> Dict:
        """Scrape with maximum ScrapingBee protection"""
        
        # Clean URL
        if '?activeVariant=' in url:
            url = url.split('?activeVariant=')[0]
        
        # Rotate country codes
        countries = ['us', 'gb', 'de', 'fr', 'ca']
        country = random.choice(countries)
        
        # Enhanced ScrapingBee parameters
        params = {
            'api_key': self.api_key,
            'url': url,
            
            # Maximum proxy protection
            'render_js': 'true',
            'premium_proxy': 'true',
            'stealth_proxy': 'true',
            'country_code': country,
            'session_id': f'session_{random.randint(1000, 9999)}',
            
            # Anti-detection features
            'auto_scroll': 'true',
            'screenshot': 'false',  # Don't waste credits on screenshots
            'extract_rules': json.dumps({
                'title': {'selector': 'h1'},
                'price': {'selector': '.price'}
            }),
            
            # Custom headers to appear more human
            'custom_google': 'false',
            'forward_headers': 'true',
            'block_resources': 'false',
            'block_ads': 'false',
            
            # Wait and rendering
            'wait': str(random.randint(5000, 8000)),  # 5-8 second wait
            'window_width': str(random.choice([1920, 1366, 1440])),
            'window_height': str(random.choice([1080, 768, 900])),
            
            # Return full page
            'return_page_source': 'true',
            
            # Enhanced JavaScript scenario
            'js_scenario': json.dumps({
                "instructions": [
                    {"wait": random.randint(2000, 4000)},
                    {"scroll_y": random.randint(300, 600)},
                    {"wait": random.randint(1000, 2000)},
                    {"evaluate": """
                        // Simulate human behavior
                        window.scrollTo(0, 100);
                        setTimeout(() => {
                            document.querySelectorAll('button, [role="tab"]').forEach(el => {
                                const text = el.textContent.toLowerCase();
                                if (text.includes('detail') || text.includes('description') || text.includes('composition')) {
                                    el.click();
                                }
                            });
                        }, 500);
                    """},
                    {"wait": random.randint(2000, 3000)},
                    {"scroll_y": random.randint(800, 1200)},
                    {"wait": random.randint(1000, 2000)}
                ]
            })
        }
        
        try:
            response = requests.get(
                'https://app.scrapingbee.com/api/v1/',
                params=params,
                timeout=120,
                headers={
                    'User-Agent': 'ScrapingBee-Client/1.0'
                }
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
            'html_size': len(html)
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
            print(f"    GCS error: {str(e)[:50]}")
            return False
    
    def run_protected_batch(self):
        """Run batch with maximum protection"""
        
        products = self.get_products()
        if not products:
            print("No products to scrape")
            return
        
        print(f"\n🛡️ Starting protected batch of {len(products)} products")
        print(f"Using {self.min_delay}-{self.max_delay}s delays with proxy rotation")
        print("-" * 60)
        
        for i, product in enumerate(products, 1):
            # Stop on too many errors
            if self.stats['consecutive_errors'] >= 3:
                print(f"\n⚠️ Stopping due to consecutive errors")
                break
            
            print(f"\n[{i}/{len(products)}] {product['product_name'][:50]}...")
            
            # Enhanced delay with randomization
            if i > 1:
                base_delay = random.uniform(self.min_delay, self.max_delay)
                # Add extra delay after errors
                if self.stats['consecutive_errors'] > 0:
                    base_delay += self.stats['consecutive_errors'] * 10
                
                print(f"  Waiting {base_delay:.1f}s (enhanced protection)...")
                time.sleep(base_delay)
            
            self.stats['total'] += 1
            
            # Scrape with protection
            result = self.scrape_with_max_protection(product['product_url'])
            
            # Add metadata
            result['product_key'] = product['product_key']
            result['brand'] = product.get('brand')
            
            # Show results
            if 'error' in result:
                print(f"  ❌ Error: {result['error']}")
            else:
                if 'ingredients_raw' in result:
                    print(f"  ✅ Ingredients: {result['ingredients_raw'][:60]}...")
                
                if 'nutrition' in result:
                    nut = result['nutrition']
                    print(f"  ✅ Nutrition: {len(nut)} nutrients found")
                
                print(f"  ✅ Protected scrape successful")
            
            # Save to GCS
            self.save_to_gcs(product['product_key'], result)
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Print summary"""
        print("\n" + "=" * 60)
        print("ENHANCED PROXY SCRAPING COMPLETE")
        print("=" * 60)
        
        elapsed = datetime.now() - self.stats['session_start']
        
        print(f"Duration: {elapsed}")
        print(f"Total: {self.stats['total']}")
        print(f"Successful: {self.stats['successful']}")
        print(f"With ingredients: {self.stats['with_ingredients']}")
        print(f"With nutrition: {self.stats['with_nutrition']}")
        print(f"Errors: {self.stats['errors']}")
        
        if self.stats['total'] > 0:
            success_rate = self.stats['successful'] / self.stats['total'] * 100
            print(f"\nSuccess rate: {success_rate:.1f}%")
        
        print(f"\nGCS: gs://{GCS_BUCKET}/{self.gcs_folder}/")

def main():
    scraper = EnhancedProxyScraper(batch_size=20)  # Start small
    scraper.run_protected_batch()

if __name__ == "__main__":
    main()