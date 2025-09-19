#!/usr/bin/env python3
"""
Scrape the remaining 66 Zooplus products that don't have ingredients
"""

import os
import json
import time
import requests
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
from google.cloud import storage
from bs4 import BeautifulSoup

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SCRAPINGBEE_API_KEY = os.getenv("SCRAPINGBEE_API_KEY")
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")

class RemainingZooplusScraper:
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(GCS_BUCKET)
        
        # Create session folder
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.session_id = f"{timestamp}_remaining66"
        self.gcs_folder = f"scraped/zooplus/{self.session_id}"
        
        self.stats = {
            'total': 0,
            'successful': 0,
            'with_ingredients': 0,
            'with_nutrition': 0,
            'errors': 0
        }
        
        print("🎯 SCRAPING REMAINING 66 ZOOPLUS PRODUCTS")
        print("=" * 60)
        print(f"Session: {self.session_id}")
        print(f"GCS: gs://{GCS_BUCKET}/{self.gcs_folder}/")
    
    def get_remaining_products(self):
        """Get products with Zooplus URLs but no ingredients"""
        response = self.supabase.table('foods_canonical').select(
            'product_key, product_name, brand, product_url'
        ).ilike('product_url', '%zooplus%')\
        .is_('ingredients_raw', 'null')\
        .execute()
        
        products = response.data if response.data else []
        print(f"\n📦 Found {len(products)} products to scrape")
        return products
    
    def scrape_product(self, url: str) -> dict:
        """Scrape with proven parameters"""
        
        # Clean URL
        if '?activeVariant=' in url:
            url = url.split('?activeVariant=')[0]
        
        params = {
            'api_key': SCRAPINGBEE_API_KEY,
            'url': url,
            'render_js': 'true',
            'premium_proxy': 'true',
            'stealth_proxy': 'true',
            'country_code': 'US',
            'wait': '3000',
            'return_page_source': 'true'
        }
        
        try:
            response = requests.get(
                'https://app.scrapingbee.com/api/v1/',
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                return self.extract_data(response.text, url)
            else:
                return {'error': f'HTTP {response.status_code}', 'url': url}
                
        except Exception as e:
            return {'error': str(e), 'url': url}
    
    def extract_data(self, html: str, url: str) -> dict:
        """Extract ingredients and nutrition from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        
        result = {
            'url': url,
            'timestamp': datetime.now().isoformat(),
            'ingredients_raw': None,
            'nutrition': None
        }
        
        # Extract ingredients
        for header in soup.find_all(['h2', 'h3', 'h4']):
            if 'ingredient' in header.text.lower() or 'composition' in header.text.lower():
                content = header.find_next_sibling()
                if content and content.text:
                    result['ingredients_raw'] = content.text.strip()
                    break
        
        # Extract nutrition
        nutrition_data = {}
        for header in soup.find_all(['h2', 'h3', 'h4']):
            if 'analytical' in header.text.lower() or 'nutritional' in header.text.lower():
                content = header.find_next_sibling()
                if content:
                    text = content.text.strip()
                    
                    # Parse nutrition values
                    if 'protein' in text.lower():
                        parts = text.split(',')
                        for part in parts:
                            part = part.strip()
                            if 'protein' in part.lower():
                                val = ''.join(filter(lambda x: x.isdigit() or x == '.', part))
                                if val:
                                    nutrition_data['protein_percent'] = float(val)
                            elif 'fat' in part.lower():
                                val = ''.join(filter(lambda x: x.isdigit() or x == '.', part))
                                if val:
                                    nutrition_data['fat_percent'] = float(val)
                            elif 'fibre' in part.lower() or 'fiber' in part.lower():
                                val = ''.join(filter(lambda x: x.isdigit() or x == '.', part))
                                if val:
                                    nutrition_data['fiber_percent'] = float(val)
                            elif 'ash' in part.lower():
                                val = ''.join(filter(lambda x: x.isdigit() or x == '.', part))
                                if val:
                                    nutrition_data['ash_percent'] = float(val)
                            elif 'moisture' in part.lower():
                                val = ''.join(filter(lambda x: x.isdigit() or x == '.', part))
                                if val:
                                    nutrition_data['moisture_percent'] = float(val)
                    break
        
        if nutrition_data:
            result['nutrition'] = nutrition_data
        
        return result
    
    def save_to_gcs(self, data: dict, product_key: str):
        """Save to GCS"""
        filename = f"{product_key.replace('|', '_')}.json"
        blob_path = f"{self.gcs_folder}/{filename}"
        
        blob = self.bucket.blob(blob_path)
        blob.upload_from_string(
            json.dumps(data, indent=2),
            content_type='application/json'
        )
        
        return blob_path
    
    def run(self):
        """Main scraping loop"""
        products = self.get_remaining_products()
        self.stats['total'] = len(products)
        
        print("\n🚀 Starting scraping...")
        print("-" * 40)
        
        for i, product in enumerate(products, 1):
            product_key = product['product_key']
            url = product['product_url']
            brand = product['brand']
            name = product['product_name']
            
            print(f"\n[{i}/{len(products)}] {brand} - {name[:30]}...")
            
            # Scrape
            data = self.scrape_product(url)
            data['product_key'] = product_key
            data['brand'] = brand
            data['product_name'] = name
            
            # Check results
            if 'error' in data:
                print(f"   ❌ Error: {data['error']}")
                self.stats['errors'] += 1
            else:
                if data.get('ingredients_raw'):
                    print(f"   ✅ Ingredients found")
                    self.stats['with_ingredients'] += 1
                if data.get('nutrition'):
                    print(f"   ✅ Nutrition found")
                    self.stats['with_nutrition'] += 1
                self.stats['successful'] += 1
            
            # Save to GCS
            gcs_path = self.save_to_gcs(data, product_key)
            print(f"   💾 Saved to {gcs_path}")
            
            # Rate limiting
            if i < len(products):
                delay = 15  # Conservative delay
                print(f"   ⏳ Waiting {delay}s...")
                time.sleep(delay)
        
        # Final stats
        print("\n" + "=" * 60)
        print("✅ SCRAPING COMPLETE")
        print(f"   Total: {self.stats['total']}")
        print(f"   Successful: {self.stats['successful']}")
        print(f"   With ingredients: {self.stats['with_ingredients']}")
        print(f"   With nutrition: {self.stats['with_nutrition']}")
        print(f"   Errors: {self.stats['errors']}")
        print(f"\n📂 Files saved to: gs://{GCS_BUCKET}/{self.gcs_folder}/")
        print("\n💡 Run continuous_processor.py to process these files")

if __name__ == "__main__":
    scraper = RemainingZooplusScraper()
    scraper.run()
