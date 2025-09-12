#!/usr/bin/env python3
"""
Scrape Zooplus products and save to GCS
Decoupled from database - just focuses on scraping
"""

import os
import re
import json
import time
import random
from datetime import datetime
from typing import Dict, Optional
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google.cloud import storage
from supabase import create_client

load_dotenv()

SCRAPINGBEE_API_KEY = os.getenv('SCRAPING_BEE')
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content")

class ZooplusGCSScraper:
    def __init__(self):
        self.api_key = SCRAPINGBEE_API_KEY
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(GCS_BUCKET)
        
        # Create folder structure
        self.gcs_folder = f"scraped/zooplus/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.stats = {
            'total': 0,
            'scraped': 0,
            'with_ingredients': 0,
            'with_nutrition': 0,
            'saved_to_gcs': 0,
            'errors': 0
        }
        
        print(f"Will save to GCS: gs://{GCS_BUCKET}/{self.gcs_folder}/")
    
    def get_products_to_scrape(self, limit: int = 100) -> list:
        """Get products that need scraping"""
        
        print(f"Fetching up to {limit} products without ingredients...")
        
        response = self.supabase.table('foods_canonical').select(
            'product_key, product_name, brand, product_url'
        ).ilike('product_url', '%zooplus%').is_('ingredients_raw', 'null').limit(limit).execute()
        
        products = response.data if response.data else []
        print(f"Found {len(products)} products to scrape")
        
        return products
    
    def scrape_product(self, url: str) -> Optional[Dict]:
        """Scrape a single product"""
        
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
            
            # JavaScript to reveal content
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
                self.stats['scraped'] += 1
                return self.parse_html(response.text, url)
            else:
                self.stats['errors'] += 1
                return {'url': url, 'error': f'HTTP {response.status_code}', 'scraped_at': datetime.now().isoformat()}
                
        except Exception as e:
            self.stats['errors'] += 1
            return {'url': url, 'error': str(e)[:200], 'scraped_at': datetime.now().isoformat()}
    
    def parse_html(self, html: str, url: str) -> Dict:
        """Parse HTML and extract data"""
        
        soup = BeautifulSoup(html, 'html.parser')
        page_text = soup.get_text(separator='\n', strip=True)
        
        result = {
            'url': url,
            'scraped_at': datetime.now().isoformat(),
            'html_size': len(html)
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
            match = re.search(pattern, page_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match:
                ingredients = match.group(1).strip()
                # Validate
                if any(word in ingredients.lower() for word in ['meat', 'chicken', 'beef', 'fish', 'rice', 'wheat', 'protein']):
                    result['ingredients_raw'] = ingredients[:3000]
                    self.stats['with_ingredients'] += 1
                    break
        
        # Try HTML elements
        if 'ingredients_raw' not in result:
            for elem in soup.find_all(['div', 'p', 'section']):
                text = elem.get_text(strip=True)
                if text.startswith(('Composition:', 'Ingredients:')):
                    if len(text) > 50:
                        result['ingredients_raw'] = text[:3000]
                        self.stats['with_ingredients'] += 1
                        break
        
        # Extract nutrition
        nutrition = {}
        
        # Protein
        match = re.search(r'(?:Crude\s+)?Protein[:\s]+(\d+(?:\.\d+)?)\s*%', page_text, re.I)
        if match:
            nutrition['protein_percent'] = float(match.group(1))
        
        # Fat
        match = re.search(r'(?:Crude\s+)?(?:Fat|Oils)[:\s]+(\d+(?:\.\d+)?)\s*%', page_text, re.I)
        if match:
            nutrition['fat_percent'] = float(match.group(1))
        
        # Fiber
        match = re.search(r'(?:Crude\s+)?Fib(?:re|er)[:\s]+(\d+(?:\.\d+)?)\s*%', page_text, re.I)
        if match:
            nutrition['fiber_percent'] = float(match.group(1))
        
        # Ash
        match = re.search(r'(?:Crude\s+)?Ash[:\s]+(\d+(?:\.\d+)?)\s*%', page_text, re.I)
        if match:
            nutrition['ash_percent'] = float(match.group(1))
        
        # Moisture
        match = re.search(r'Moisture[:\s]+(\d+(?:\.\d+)?)\s*%', page_text, re.I)
        if match:
            nutrition['moisture_percent'] = float(match.group(1))
        
        if nutrition:
            result['nutrition'] = nutrition
            self.stats['with_nutrition'] += 1
        
        # Store first 50KB of HTML for debugging
        result['html_sample'] = html[:50000]
        
        return result
    
    def save_to_gcs(self, product_key: str, data: Dict) -> bool:
        """Save scraped data to GCS"""
        
        try:
            # Create filename
            safe_key = product_key.replace('|', '_').replace('/', '_')
            filename = f"{self.gcs_folder}/{safe_key}.json"
            
            # Create blob
            blob = self.bucket.blob(filename)
            
            # Upload
            blob.upload_from_string(
                json.dumps(data, indent=2, ensure_ascii=False),
                content_type='application/json'
            )
            
            self.stats['saved_to_gcs'] += 1
            return True
            
        except Exception as e:
            print(f"    GCS save error: {str(e)[:100]}")
            return False
    
    def run_batch(self, batch_size: int = 50):
        """Run batch scraping"""
        
        print("\nZOOPLUS SCRAPING TO GCS")
        print("="*60)
        
        # Get products
        products = self.get_products_to_scrape(batch_size)
        
        if not products:
            print("No products to scrape")
            return
        
        print(f"\nScraping {len(products)} products")
        print(f"Delays: 15-20 seconds between requests")
        print("-"*60)
        
        for i, product in enumerate(products, 1):
            print(f"\n[{i}/{len(products)}] {product['product_name'][:60]}...")
            
            # Rate limiting
            if i > 1:
                delay = random.uniform(15, 20)
                print(f"  Waiting {delay:.1f}s...")
                time.sleep(delay)
            
            self.stats['total'] += 1
            
            # Scrape
            result = self.scrape_product(product['product_url'])
            
            if result:
                # Add product info
                result['product_key'] = product['product_key']
                result['brand'] = product.get('brand')
                
                # Show what we found
                if 'ingredients_raw' in result:
                    print(f"  ✓ Ingredients: {result['ingredients_raw'][:80]}...")
                
                if 'nutrition' in result:
                    nut = result['nutrition']
                    print(f"  ✓ Nutrition: Protein={nut.get('protein_percent')}%, Fat={nut.get('fat_percent')}%")
                
                if 'error' in result:
                    print(f"  ✗ Error: {result['error']}")
                
                # Save to GCS
                if self.save_to_gcs(product['product_key'], result):
                    print(f"  ✓ Saved to GCS")
            
            # Stop if too many errors
            if self.stats['errors'] > 10:
                print("\n⚠️ Too many errors, stopping")
                break
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Print summary"""
        
        print("\n" + "="*60)
        print("SCRAPING SUMMARY")
        print("="*60)
        print(f"Total attempted: {self.stats['total']}")
        print(f"Successfully scraped: {self.stats['scraped']}")
        print(f"With ingredients: {self.stats['with_ingredients']}")
        print(f"With nutrition: {self.stats['with_nutrition']}")
        print(f"Saved to GCS: {self.stats['saved_to_gcs']}")
        print(f"Errors: {self.stats['errors']}")
        
        if self.stats['total'] > 0:
            success_rate = self.stats['scraped'] / self.stats['total'] * 100
            print(f"\nSuccess rate: {success_rate:.1f}%")
        
        print(f"\nGCS location: gs://{GCS_BUCKET}/{self.gcs_folder}/")

def main():
    scraper = ZooplusGCSScraper()
    
    # Start with 10 products
    scraper.run_batch(batch_size=10)

if __name__ == "__main__":
    main()