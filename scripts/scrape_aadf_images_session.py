#!/usr/bin/env python3
"""
AADF Image Session Scraper - Individual session for parallel execution
"""

import os
import sys
import json
import re
import time
import random
import argparse
from datetime import datetime
from typing import Dict, Optional, List
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google.cloud import storage
from supabase import create_client

load_dotenv()

# Environment setup
SCRAPINGBEE_API_KEY = os.getenv('SCRAPING_BEE')
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")

# Set up GCS authentication
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/sergiubiris/Desktop/lupito-content/secrets/gcp-sa.json'

class AADFImageSessionScraper:
    def __init__(self, session_name: str, country_code: str, offset: int, batch_size: int, 
                 min_delay: int = 20, max_delay: int = 30):
        self.session_name = session_name
        self.country_code = country_code
        self.offset = offset
        self.batch_size = batch_size
        self.min_delay = min_delay
        self.max_delay = max_delay
        
        # Initialize services
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(GCS_BUCKET)
        
        # Session tracking
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.session_id = f"aadf_images_{timestamp}_{session_name}"
        self.gcs_folder = f"scraped/aadf_images/{self.session_id}"
        
        # Statistics
        self.stats = {
            'total': 0,
            'successful': 0,
            'images_found': 0,
            'images_saved': 0,
            'errors': 0,
            'consecutive_errors': 0,
            'session_start': datetime.now()
        }
        
        # Status file for orchestrator
        self.status_file = f"/tmp/aadf_session_{session_name}.json"
        self.update_status("starting")
        
        print(f"[{session_name}] 🚀 AADF IMAGE SESSION SCRAPER STARTED")
        print(f"[{session_name}] Country: {country_code}, Offset: {offset}, Batch: {batch_size}")
        print(f"[{session_name}] Delays: {min_delay}-{max_delay}s")
        print(f"[{session_name}] GCS: gs://{GCS_BUCKET}/{self.gcs_folder}/")
    
    def update_status(self, status: str):
        """Update status file for orchestrator"""
        try:
            status_data = {
                'session': self.session_name,
                'status': status,
                'stats': self.stats,
                'timestamp': datetime.now().isoformat()
            }
            with open(self.status_file, 'w') as f:
                json.dump(status_data, f)
        except:
            pass
    
    def get_products(self) -> List[Dict]:
        """Get products to scrape"""
        try:
            response = self.supabase.table('foods_canonical')\
                .select('product_key, brand, product_name, product_url')\
                .ilike('product_url', '%allaboutdogfood%')\
                .is_('image_url', 'null')\
                .range(self.offset, self.offset + self.batch_size - 1)\
                .execute()
            
            products = response.data if response.data else []
            print(f"[{self.session_name}] Found {len(products)} products to scrape")
            return products
        except Exception as e:
            print(f"[{self.session_name}] Error fetching products: {e}")
            return []
    
    def extract_image_url(self, html: str, base_url: str) -> Optional[str]:
        """Extract image URL from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # AADF specific patterns
        # Pattern 1: Storage URL pattern (most common)
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if '/storage/products/' in src:
                return self.make_absolute_url(src, base_url)
        
        # Pattern 2: Product review section
        review_section = soup.find('div', class_='review-content')
        if review_section:
            img = review_section.find('img')
            if img and img.get('src'):
                return self.make_absolute_url(img['src'], base_url)
        
        # Pattern 3: Open Graph
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            return self.make_absolute_url(og_image['content'], base_url)
        
        return None
    
    def make_absolute_url(self, img_url: str, base_url: str) -> str:
        """Convert relative URL to absolute"""
        if not img_url:
            return None
        
        if img_url.startswith('http://') or img_url.startswith('https://'):
            return img_url
        
        if img_url.startswith('//'):
            return 'https:' + img_url
        
        if img_url.startswith('/'):
            base_domain = '/'.join(base_url.split('/')[:3])
            return base_domain + img_url
        
        base_dir = '/'.join(base_url.split('/')[:-1])
        return base_dir + '/' + img_url
    
    def scrape_with_scrapingbee(self, url: str, retry_count: int = 0) -> Dict:
        """Scrape using ScrapingBee with retry logic"""
        
        result = {
            'url': url,
            'html': None,
            'error': None,
            'status_code': None
        }
        
        params = {
            'api_key': SCRAPINGBEE_API_KEY,
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
                timeout=30
            )
            
            result['status_code'] = response.status_code
            
            if response.status_code == 200:
                result['html'] = response.text
                self.stats['consecutive_errors'] = 0
            elif response.status_code == 429 and retry_count < 2:
                # Rate limited - wait and retry
                print(f"[{self.session_name}] Rate limited, waiting 60s...")
                time.sleep(60)
                return self.scrape_with_scrapingbee(url, retry_count + 1)
            else:
                result['error'] = f"HTTP {response.status_code}"
                self.stats['consecutive_errors'] += 1
                
        except Exception as e:
            result['error'] = str(e)[:200]
            self.stats['consecutive_errors'] += 1
        
        return result
    
    def scrape_product_image(self, product: Dict) -> Dict:
        """Scrape single product image"""
        
        self.stats['total'] += 1
        
        result = {
            'product_key': product['product_key'],
            'product_name': product['product_name'],
            'brand': product.get('brand', 'Unknown'),
            'product_url': product['product_url'],
            'image_url': None,
            'error': None,
            'timestamp': datetime.now().isoformat()
        }
        
        # Scrape the page
        scrape_result = self.scrape_with_scrapingbee(product['product_url'])
        
        if scrape_result['html']:
            # Extract image URL
            image_url = self.extract_image_url(scrape_result['html'], product['product_url'])
            
            if image_url:
                result['image_url'] = image_url
                self.stats['images_found'] += 1
                self.stats['successful'] += 1
                print(f"[{self.session_name}] ✅ [{self.stats['total']}/{self.batch_size}] Found image for {product['product_name'][:30]}...")
            else:
                result['error'] = 'No image found'
                print(f"[{self.session_name}] ⚠️ [{self.stats['total']}/{self.batch_size}] No image found for {product['product_name'][:30]}...")
        else:
            result['error'] = scrape_result['error']
            self.stats['errors'] += 1
            print(f"[{self.session_name}] ❌ [{self.stats['total']}/{self.batch_size}] Failed: {scrape_result['error']}")
        
        # Save to GCS ONLY - do not update database directly
        self.save_to_gcs(result)
        
        return result
    
    def save_to_gcs(self, result: Dict):
        """Save result to GCS"""
        try:
            safe_key = result['product_key'].replace('|', '_').replace('/', '_')
            filename = f"{self.gcs_folder}/{safe_key}.json"
            
            blob = self.bucket.blob(filename)
            blob.upload_from_string(
                json.dumps(result, indent=2),
                content_type='application/json'
            )
            
            self.stats['images_saved'] += 1
        except Exception as e:
            print(f"[{self.session_name}] Warning: GCS save failed: {e}")
    
    def run(self):
        """Main execution loop"""
        print(f"[{self.session_name}] Starting scraping session...")
        
        # Get products to scrape
        products = self.get_products()
        
        if not products:
            print(f"[{self.session_name}] No products to scrape")
            self.update_status("completed")
            return
        
        self.update_status("running")
        
        # Process each product
        for i, product in enumerate(products):
            # Check for excessive errors
            if self.stats['consecutive_errors'] >= 5:
                print(f"[{self.session_name}] Too many consecutive errors, stopping")
                break
            
            # Scrape the product
            result = self.scrape_product_image(product)
            
            # Update status periodically
            if (i + 1) % 10 == 0:
                self.update_status("running")
                elapsed = datetime.now() - self.stats['session_start']
                rate = self.stats['total'] / elapsed.total_seconds() if elapsed.total_seconds() > 0 else 0
                eta_seconds = (len(products) - self.stats['total']) / rate if rate > 0 else 0
                print(f"[{self.session_name}] Progress: {self.stats['total']}/{len(products)} | Success rate: {self.stats['successful']/self.stats['total']*100:.1f}% | ETA: {eta_seconds/60:.1f} min")
            
            # Random delay between requests
            if i < len(products) - 1:  # Don't delay after last product
                delay = random.randint(self.min_delay, self.max_delay)
                time.sleep(delay)
        
        # Final status
        self.update_status("completed")
        self.print_summary()
    
    def print_summary(self):
        """Print session summary"""
        elapsed = datetime.now() - self.stats['session_start']
        
        print(f"\n[{self.session_name}] " + "=" * 60)
        print(f"[{self.session_name}] SESSION COMPLETE")
        print(f"[{self.session_name}] Duration: {elapsed}")
        print(f"[{self.session_name}] Total processed: {self.stats['total']}")
        print(f"[{self.session_name}] Images found: {self.stats['images_found']}")
        print(f"[{self.session_name}] Files saved to GCS: {self.stats['images_saved']}")
        print(f"[{self.session_name}] Errors: {self.stats['errors']}")
        
        if self.stats['total'] > 0:
            success_rate = (self.stats['images_found'] / self.stats['total']) * 100
            print(f"[{self.session_name}] Success rate: {success_rate:.1f}%")

def main():
    parser = argparse.ArgumentParser(description='AADF Image Session Scraper')
    parser.add_argument('--session', required=True, help='Session name (e.g., us1, gb1)')
    parser.add_argument('--country', default='gb', help='Country code')
    parser.add_argument('--offset', type=int, required=True, help='Starting offset')
    parser.add_argument('--batch', type=int, default=410, help='Batch size')
    parser.add_argument('--delay-min', type=int, default=20, help='Minimum delay between requests')
    parser.add_argument('--delay-max', type=int, default=30, help='Maximum delay between requests')
    
    args = parser.parse_args()
    
    # Create and run scraper
    scraper = AADFImageSessionScraper(
        session_name=args.session,
        country_code=args.country,
        offset=args.offset,
        batch_size=args.batch,
        min_delay=args.delay_min,
        max_delay=args.delay_max
    )
    
    scraper.run()

if __name__ == "__main__":
    main()