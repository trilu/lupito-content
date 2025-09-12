#!/usr/bin/env python3
"""
Safe progressive scraper for Zooplus
Implements smart batching and timing to avoid bans
Goal: Reach 95% coverage for ingredients
"""

import os
import json
import time
import random
from datetime import datetime, timedelta
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

class SafeProgressiveScraper:
    def __init__(self):
        self.api_key = SCRAPINGBEE_API_KEY
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(GCS_BUCKET)
        
        # Session tracking
        self.session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.gcs_folder = f"scraped/zooplus/{self.session_id}"
        
        # Safety parameters (optimized)
        self.min_delay = 10  # Minimum 10 seconds between requests
        self.max_delay = 15  # Maximum 15 seconds
        self.max_per_hour = 240  # Maximum 240 products per hour
        self.max_per_session = 500  # Maximum 500 per session
        self.error_threshold = 10  # Stop after 10 consecutive errors
        
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
    
    def get_priority_products(self, limit: int) -> List[Dict]:
        """Get products to scrape, prioritizing popular brands"""
        
        print("Fetching priority products...")
        
        # Priority brands (most popular)
        priority_brands = [
            'Royal Canin', "Hill's Science Plan", 'Purina', 'Eukanuba',
            'Advance', 'Taste of the Wild', 'Acana', 'Orijen',
            'Wellness', 'Brit', 'Happy Dog', 'Josera'
        ]
        
        all_products = []
        
        # First get priority brand products
        for brand in priority_brands:
            response = self.supabase.table('foods_canonical').select(
                'product_key, product_name, brand, product_url'
            ).ilike('product_url', '%zooplus%')\
            .ilike('brand', f'%{brand}%')\
            .is_('ingredients_raw', 'null')\
            .limit(20).execute()
            
            if response.data:
                all_products.extend(response.data)
        
        # Then get remaining products
        if len(all_products) < limit:
            response = self.supabase.table('foods_canonical').select(
                'product_key, product_name, brand, product_url'
            ).ilike('product_url', '%zooplus%')\
            .is_('ingredients_raw', 'null')\
            .limit(limit - len(all_products)).execute()
            
            if response.data:
                all_products.extend(response.data)
        
        # Shuffle to avoid patterns
        random.shuffle(all_products)
        
        print(f"Found {len(all_products)} products to scrape")
        return all_products[:limit]
    
    def should_continue(self) -> bool:
        """Check if we should continue scraping"""
        
        # Check consecutive errors
        if self.stats['consecutive_errors'] >= self.error_threshold:
            print(f"\n⚠️ Too many consecutive errors ({self.error_threshold})")
            return False
        
        # Check hourly limit
        elapsed = datetime.now() - self.stats['session_start']
        hours = elapsed.total_seconds() / 3600
        if hours > 0:
            rate = self.stats['total'] / hours
            if rate > self.max_per_hour:
                print(f"\n⚠️ Rate limit approaching ({rate:.0f}/hour)")
                time.sleep(300)  # Wait 5 minutes
        
        # Check session limit
        if self.stats['total'] >= self.max_per_session:
            print(f"\n⚠️ Session limit reached ({self.max_per_session})")
            return False
        
        return True
    
    def scrape_product(self, url: str) -> Dict:
        """Scrape with enhanced safety measures"""
        
        # Clean URL
        if '?activeVariant=' in url:
            url = url.split('?activeVariant=')[0]
        
        # Rotate user agents
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) Safari/17.0',
            'Mozilla/5.0 (X11; Linux x86_64) Firefox/120.0'
        ]
        
        params = {
            'api_key': self.api_key,
            'url': url,
            'render_js': 'true',
            'premium_proxy': 'true',
            'stealth_proxy': 'true',
            'country_code': random.choice(['us', 'gb', 'de']),
            'return_page_source': 'true',
            'custom_headers': json.dumps({
                'User-Agent': random.choice(user_agents)
            }),
            
            # JavaScript to reveal content
            'js_scenario': json.dumps({
                "instructions": [
                    {"wait": random.randint(2000, 4000)},
                    {"scroll_y": random.randint(400, 600)},
                    {"wait": random.randint(1000, 2000)},
                    {"evaluate": """
                        document.querySelectorAll('button, [role="tab"]').forEach(el => {
                            const text = el.textContent.toLowerCase();
                            if (text.includes('detail') || text.includes('description')) {
                                el.click();
                            }
                        });
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
                timeout=120
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
        """Parse HTML response"""
        
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
        ingredients_patterns = [
            r'(?:Composition|Ingredients)[:\s]*\n?([^\n]{20,}?)(?:\n(?:Analytical|Additives|Nutritional)|$)',
            r'(?:Composition|Ingredients)[:\s]*([A-Za-z][^.]{30,}(?:\.[^.]{20,})*?)(?:Analytical|$)',
        ]
        
        for pattern in ingredients_patterns:
            import re
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
        
        # Store sample HTML
        result['html_sample'] = html[:30000]
        
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
            print(f"    GCS save error: {str(e)[:100]}")
            return False
    
    def run_safe_batch(self, batch_size: int = 100):
        """Run safe batch with monitoring"""
        
        print("\nSAFE PROGRESSIVE SCRAPING")
        print("=" * 60)
        print(f"Session ID: {self.session_id}")
        print(f"GCS folder: gs://{GCS_BUCKET}/{self.gcs_folder}/")
        print(f"Safety settings:")
        print(f"  • Delay: {self.min_delay}-{self.max_delay} seconds")
        print(f"  • Max per hour: {self.max_per_hour}")
        print(f"  • Error threshold: {self.error_threshold}")
        print("-" * 60)
        
        # Get products
        products = self.get_priority_products(batch_size)
        
        if not products:
            print("No products to scrape")
            return
        
        print(f"\nScraping {len(products)} products")
        print("Starting in 5 seconds...")
        time.sleep(5)
        
        for i, product in enumerate(products, 1):
            if not self.should_continue():
                print("\nStopping due to safety limits")
                break
            
            print(f"\n[{i}/{len(products)}] {product['product_name'][:60]}...")
            print(f"  Brand: {product.get('brand', 'Unknown')}")
            
            # Random delay
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
                print(f"  ✓ Ingredients: {result['ingredients_raw'][:80]}...")
            
            if 'nutrition' in result:
                nut = result['nutrition']
                print(f"  ✓ Nutrition: P={nut.get('protein_percent')}% F={nut.get('fat_percent')}%")
            
            if 'error' in result:
                print(f"  ✗ Error: {result['error']}")
            
            # Save to GCS
            if self.save_to_gcs(product['product_key'], result):
                print(f"  ✓ Saved to GCS")
            
            # Progress update every 10 products
            if i % 10 == 0:
                self.print_progress()
        
        # Final summary
        self.print_summary()
    
    def print_progress(self):
        """Print progress statistics"""
        elapsed = datetime.now() - self.stats['session_start']
        rate = self.stats['total'] / (elapsed.total_seconds() / 3600) if elapsed.total_seconds() > 0 else 0
        
        print(f"\n--- Progress: {self.stats['successful']}/{self.stats['total']} successful, "
              f"{rate:.0f}/hour, {self.stats['errors']} errors ---")
    
    def print_summary(self):
        """Print final summary"""
        print("\n" + "=" * 60)
        print("SESSION SUMMARY")
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
            print(f"\nSuccess rate: {success_rate:.1f}%")
            
            rate = self.stats['total'] / (elapsed.total_seconds() / 3600) if elapsed.total_seconds() > 0 else 0
            print(f"Average rate: {rate:.0f} products/hour")
        
        print(f"\nGCS location: gs://{GCS_BUCKET}/{self.gcs_folder}/")
        print("\nNext step: Run process_gcs_scraped_data.py with this folder")

def main():
    """Run safe progressive scraping"""
    scraper = SafeProgressiveScraper()
    
    # Start with moderate batch for production
    scraper.run_safe_batch(batch_size=50)
    
    print("\n" + "=" * 60)
    print("RECOMMENDATIONS")
    print("=" * 60)
    print("1. Wait 2-3 hours before next batch")
    print("2. Process GCS files: python process_gcs_scraped_data.py " + scraper.gcs_folder)
    print("3. Monitor error rates")
    print("4. Vary batch sizes (50-150)")
    print("5. Run at different times of day")

if __name__ == "__main__":
    main()