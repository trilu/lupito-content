#!/usr/bin/env python3
"""
Re-scrape failed products with the working scraper configuration
Priority scraping for products that previously failed
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

class FailedProductRescraper:
    def __init__(self):
        self.api_key = SCRAPINGBEE_API_KEY
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(GCS_BUCKET)
        
        # Session tracking
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.session_id = f"{timestamp}_rescrape"
        self.gcs_folder = f"scraped/zooplus/{self.session_id}"
        
        # Load failed products
        with open('scripts/products_to_rescrape.json', 'r') as f:
            data = json.load(f)
            self.products_to_rescrape = data['products']
        
        print(f"🔄 RESCRAPING FAILED PRODUCTS")
        print(f"   Session: {self.session_id}")
        print(f"   Products to rescrape: {len(self.products_to_rescrape)}")
        print("=" * 60)
    
    def scrape_product(self, url: str, product_key: str) -> Dict:
        """Scrape a single product using proven working configuration"""
        
        try:
            # Use the PROVEN working parameters
            params = {
                'api_key': self.api_key,
                'url': url,
                'render_js': 'true',
                'premium_proxy': 'true',
                'stealth_proxy': 'true',
                'country_code': 'us',
                'wait': '3000',
                'return_page_source': 'true'
            }
            
            response = requests.get('https://app.scrapingbee.com/api/v1/', params=params)
            
            if response.status_code != 200:
                return {
                    'error': f'HTTP {response.status_code}',
                    'url': url,
                    'product_key': product_key,
                    'scraped_at': datetime.now().isoformat()
                }
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract product data
            product_data = {
                'url': url,
                'product_key': product_key,
                'scraped_at': datetime.now().isoformat()
            }
            
            # Extract ingredients
            ingredients = self.extract_ingredients(soup)
            if ingredients:
                product_data['ingredients_raw'] = ingredients
            
            # Extract nutrition
            nutrition = self.extract_nutrition(soup)
            if nutrition:
                product_data['nutrition'] = nutrition
            
            return product_data
            
        except Exception as e:
            return {
                'error': str(e)[:200],
                'url': url,
                'product_key': product_key,
                'scraped_at': datetime.now().isoformat()
            }
    
    def extract_ingredients(self, soup: BeautifulSoup) -> str:
        """Extract ingredients from page"""
        
        # Try various patterns
        patterns = [
            ('dt', 'Composition'),
            ('dt', 'Ingredients'),
            ('h3', 'Composition'),
            ('h3', 'Ingredients'),
            ('strong', 'Composition'),
            ('strong', 'Ingredients'),
        ]
        
        for tag, text in patterns:
            element = soup.find(tag, string=lambda s: s and text.lower() in s.lower())
            if element:
                # Get next sibling or parent's next text
                next_elem = element.find_next_sibling()
                if next_elem:
                    ingredients = next_elem.get_text(strip=True)
                    if len(ingredients) > 20:
                        return ingredients[:2000]
        
        return None
    
    def extract_nutrition(self, soup: BeautifulSoup) -> Dict:
        """Extract nutrition values"""
        
        nutrition = {}
        
        # Nutrition patterns
        patterns = [
            (r'(?:Crude\s+)?Protein[:\s]+(\d+(?:\.\d+)?)\s*%', 'protein_percent'),
            (r'(?:Crude\s+)?(?:Fat|Oils)[:\s]+(\d+(?:\.\d+)?)\s*%', 'fat_percent'),
            (r'(?:Crude\s+)?Fib(?:re|er)[:\s]+(\d+(?:\.\d+)?)\s*%', 'fiber_percent'),
            (r'(?:Crude\s+)?Ash[:\s]+(\d+(?:\.\d+)?)\s*%', 'ash_percent'),
            (r'Moisture[:\s]+(\d+(?:\.\d+)?)\s*%', 'moisture_percent'),
        ]
        
        text = soup.get_text()
        import re
        
        for pattern, field in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value = float(match.group(1))
                    nutrition[field] = value
                except:
                    pass
        
        return nutrition if nutrition else None
    
    def save_to_gcs(self, product_data: Dict, product_key: str) -> bool:
        """Save scraped data to GCS"""
        
        try:
            # Create filename from product key
            filename = product_key.replace('|', '_').replace('/', '_')[:100] + '.json'
            blob_path = f"{self.gcs_folder}/{filename}"
            
            # Upload to GCS
            blob = self.bucket.blob(blob_path)
            blob.upload_from_string(
                json.dumps(product_data, indent=2),
                content_type='application/json'
            )
            
            return True
        except Exception as e:
            print(f"   GCS Error: {e}")
            return False
    
    def run(self):
        """Process all failed products"""
        
        successful = 0
        failed = 0
        
        for idx, product in enumerate(self.products_to_rescrape, 1):
            url = product['url']
            product_key = product['product_key']
            
            print(f"\n[{idx}/{len(self.products_to_rescrape)}] Re-scraping: {product_key[:50]}...")
            print(f"   URL: {url[:80]}...")
            
            # Scrape the product
            result = self.scrape_product(url, product_key)
            
            # Save to GCS
            saved = self.save_to_gcs(result, product_key)
            
            if 'error' not in result and saved:
                successful += 1
                print(f"   ✅ Success! Ingredients: {'Yes' if 'ingredients_raw' in result else 'No'}, Nutrition: {'Yes' if 'nutrition' in result else 'No'}")
            else:
                failed += 1
                error = result.get('error', 'Unknown error')
                print(f"   ❌ Failed: {error[:100]}")
            
            # Delay between requests (optimized but safe)
            delay = random.uniform(12, 18)
            print(f"   Waiting {delay:.1f} seconds...")
            time.sleep(delay)
        
        # Final summary
        print("\n" + "=" * 60)
        print(f"✅ RE-SCRAPING COMPLETE")
        print(f"   Successful: {successful}/{len(self.products_to_rescrape)}")
        print(f"   Failed: {failed}/{len(self.products_to_rescrape)}")
        print(f"   Success rate: {successful/len(self.products_to_rescrape)*100:.1f}%")
        print(f"   GCS folder: gs://{GCS_BUCKET}/{self.gcs_folder}/")
        
        if successful > 0:
            print(f"\n💡 Next step: Process the re-scraped data:")
            print(f"   python scripts/process_gcs_scraped_data.py {self.gcs_folder}")

if __name__ == "__main__":
    rescraper = FailedProductRescraper()
    rescraper.run()