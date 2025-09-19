#!/usr/bin/env python3
"""
Orchestrated AADF Image Scraper - Using proven infrastructure
Scrapes product images from AADF pages
"""

import os
import json
import re
import time
import random
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

class AADFImageOrchestrator:
    def __init__(self, session_name: str = "aadf_images", country_code: str = "gb"):
        self.session_name = session_name
        self.country_code = country_code
        
        # Initialize services
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(GCS_BUCKET)
        
        # Session tracking
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.session_id = f"{timestamp}_{session_name}"
        self.gcs_folder = f"scraped/aadf_images/{self.session_id}"
        
        # Statistics
        self.stats = {
            'total': 0,
            'successful': 0,
            'images_found': 0,
            'images_saved': 0,
            'db_updated': 0,
            'errors': 0,
            'session_start': datetime.now()
        }
        
        print(f"🚀 AADF IMAGE ORCHESTRATOR STARTED")
        print(f"Session: {self.session_id}")
        print(f"GCS: gs://{GCS_BUCKET}/{self.gcs_folder}/")
    
    def extract_image_patterns(self, html: str, base_url: str) -> Optional[str]:
        """Extract image URL using multiple patterns"""
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Pattern 1: Look for product image in review section
        review_section = soup.find('div', class_='review-content')
        if review_section:
            img = review_section.find('img')
            if img and img.get('src'):
                return self.make_absolute_url(img['src'], base_url)
        
        # Pattern 2: Look for image with product in alt text
        for img in soup.find_all('img'):
            alt = img.get('alt', '').lower()
            src = img.get('src', '')
            if ('product' in alt or 'food' in alt or 'dog' in alt) and src:
                # Skip icons and placeholders
                if 'icon' not in src.lower() and 'placeholder' not in src.lower():
                    return self.make_absolute_url(src, base_url)
        
        # Pattern 3: Open Graph image
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            return self.make_absolute_url(og_image['content'], base_url)
        
        # Pattern 4: First reasonable sized image
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if src and any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                # Skip small images (likely icons)
                if 'thumb' not in src.lower() and 'icon' not in src.lower():
                    return self.make_absolute_url(src, base_url)
        
        # Pattern 5: Look in specific divs
        for div_class in ['product-image', 'food-image', 'review-image', 'main-image']:
            div = soup.find('div', class_=div_class)
            if div:
                img = div.find('img')
                if img and img.get('src'):
                    return self.make_absolute_url(img['src'], base_url)
        
        return None
    
    def make_absolute_url(self, img_url: str, base_url: str) -> str:
        """Convert relative URL to absolute"""
        if not img_url:
            return None
        
        # Already absolute
        if img_url.startswith('http://') or img_url.startswith('https://'):
            return img_url
        
        # Protocol-relative
        if img_url.startswith('//'):
            return 'https:' + img_url
        
        # Relative to root
        if img_url.startswith('/'):
            base_domain = '/'.join(base_url.split('/')[:3])
            return base_domain + img_url
        
        # Relative to current directory
        base_dir = '/'.join(base_url.split('/')[:-1])
        return base_dir + '/' + img_url
    
    def scrape_with_scrapingbee(self, url: str) -> Dict:
        """Scrape using proven ScrapingBee parameters"""
        
        result = {
            'url': url,
            'html': None,
            'error': None,
            'status_code': None
        }
        
        # Use exact parameters that worked for Zooplus
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
            else:
                result['error'] = f"HTTP {response.status_code}"
                
        except Exception as e:
            result['error'] = str(e)[:200]
        
        return result
    
    def scrape_product_image(self, product: Dict) -> Dict:
        """Scrape image from AADF product page"""
        
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
        
        print(f"\n[{self.stats['total']}] Scraping: {product['product_name'][:50]}...")
        print(f"  URL: {product['product_url']}")
        
        # Scrape the page
        scrape_result = self.scrape_with_scrapingbee(product['product_url'])
        
        if scrape_result['html']:
            # Extract image URL
            image_url = self.extract_image_patterns(scrape_result['html'], product['product_url'])
            
            if image_url:
                result['image_url'] = image_url
                self.stats['images_found'] += 1
                self.stats['successful'] += 1
                print(f"  ✅ Found image: {image_url[:80]}...")
            else:
                result['error'] = 'No image found on page'
                print(f"  ⚠️ No image found in HTML")
        else:
            result['error'] = scrape_result['error']
            self.stats['errors'] += 1
            print(f"  ❌ Scraping failed: {scrape_result['error']}")
        
        # Save to GCS
        self.save_to_gcs(result)
        
        # Update database if image found
        if result['image_url']:
            self.update_database(result)
        
        return result
    
    def save_to_gcs(self, result: Dict):
        """Save result to GCS"""
        try:
            # Create filename
            safe_key = result['product_key'].replace('|', '_').replace('/', '_')
            filename = f"{self.gcs_folder}/{safe_key}.json"
            
            # Upload to GCS
            blob = self.bucket.blob(filename)
            blob.upload_from_string(
                json.dumps(result, indent=2),
                content_type='application/json'
            )
            
            self.stats['images_saved'] += 1
            
        except Exception as e:
            print(f"  Warning: Failed to save to GCS: {e}")
    
    def update_database(self, result: Dict):
        """Update database with image URL"""
        if result.get('image_url'):
            try:
                response = self.supabase.table('foods_canonical')\
                    .update({'image_url': result['image_url']})\
                    .eq('product_key', result['product_key'])\
                    .execute()
                
                if response.data:
                    self.stats['db_updated'] += 1
                    print(f"  ✅ Database updated")
                    return True
            except Exception as e:
                print(f"  ❌ Database update failed: {e}")
        
        return False
    
    def process_batch(self, products: List[Dict]):
        """Process a batch of products"""
        
        print(f"\n🔍 Processing {len(products)} AADF products...")
        print("=" * 80)
        
        results = []
        
        for product in products:
            # Scrape the product
            result = self.scrape_product_image(product)
            results.append(result)
            
            # Random delay between requests (15-35 seconds like Zooplus)
            delay = random.randint(15, 35)
            print(f"  Waiting {delay} seconds...")
            time.sleep(delay)
        
        return results
    
    def print_summary(self):
        """Print session summary"""
        
        elapsed = datetime.now() - self.stats['session_start']
        
        print("\n" + "=" * 80)
        print("📊 SESSION SUMMARY")
        print("=" * 80)
        print(f"Session ID: {self.session_id}")
        print(f"Duration: {elapsed}")
        print(f"Total processed: {self.stats['total']}")
        print(f"Successful scrapes: {self.stats['successful']}")
        print(f"Images found: {self.stats['images_found']}")
        print(f"Images saved to GCS: {self.stats['images_saved']}")
        print(f"Database updated: {self.stats['db_updated']}")
        print(f"Errors: {self.stats['errors']}")
        
        if self.stats['total'] > 0:
            success_rate = (self.stats['images_found'] / self.stats['total']) * 100
            print(f"\nSuccess rate: {success_rate:.1f}%")
        
        print(f"\nGCS folder: gs://{GCS_BUCKET}/{self.gcs_folder}/")

def main():
    """Main function to test with 5 products"""
    
    print("🎯 Getting 5 AADF products without images...")
    
    # Initialize Supabase
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Get 5 AADF products without images
    products = supabase.table('foods_canonical')\
        .select('product_key, brand, product_name, product_url')\
        .ilike('product_url', '%allaboutdogfood%')\
        .is_('image_url', 'null')\
        .limit(5)\
        .execute()
    
    if not products.data:
        print("No AADF products without images found!")
        return
    
    print(f"Found {len(products.data)} products to process")
    
    # Create orchestrator
    orchestrator = AADFImageOrchestrator(session_name="test", country_code="gb")
    
    # Process the batch
    results = orchestrator.process_batch(products.data)
    
    # Print summary
    orchestrator.print_summary()
    
    # Show detailed results
    print("\n📸 DETAILED RESULTS:")
    print("-" * 80)
    for result in results:
        print(f"\n{result['brand']} - {result['product_name'][:40]}...")
        if result.get('image_url'):
            print(f"  ✅ Image URL: {result['image_url']}")
        else:
            print(f"  ❌ No image: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main()