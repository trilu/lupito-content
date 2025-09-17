#!/usr/bin/env python3
"""
Scrape product images from AADF pages
"""

import os
import json
import re
import time
from datetime import datetime
from typing import Dict, Optional
from dotenv import load_dotenv
from supabase import create_client
from scrapingbee import ScrapingBeeClient
from google.cloud import storage

load_dotenv()

# Initialize services
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_KEY')
)

# ScrapingBee client
scraping_client = ScrapingBeeClient(api_key=os.getenv('SCRAPINGBEE_API_KEY'))

# GCS setup
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/sergiubiris/Desktop/lupito-content/secrets/gcp-sa.json'
storage_client = storage.Client()
bucket = storage_client.bucket('lupito-content-raw-eu')

class AADFImageScraper:
    def __init__(self, save_to_gcs=True):
        self.save_to_gcs = save_to_gcs
        self.session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.stats = {
            'total': 0,
            'images_found': 0,
            'images_saved': 0,
            'errors': 0,
            'db_updated': 0
        }
    
    def extract_image_url(self, html: str) -> Optional[str]:
        """Extract product image URL from AADF page"""
        
        # Pattern 1: Look for product image in specific div
        pattern1 = r'<img[^>]+class="[^"]*product-image[^"]*"[^>]+src="([^"]+)"'
        match = re.search(pattern1, html, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Pattern 2: Look for image in product section
        pattern2 = r'<div[^>]+class="[^"]*product[^"]*"[^>]*>.*?<img[^>]+src="([^"]+)"'
        match = re.search(pattern2, html, re.IGNORECASE | re.DOTALL)
        if match:
            img_url = match.group(1)
            # Skip placeholder or icon images
            if 'placeholder' not in img_url.lower() and 'icon' not in img_url.lower():
                return img_url
        
        # Pattern 3: Look for any image that looks like a product image
        pattern3 = r'<img[^>]+src="([^"]+(?:product|food|dog)[^"]+\.(?:jpg|jpeg|png|webp))"'
        match = re.search(pattern3, html, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Pattern 4: General image in main content area
        pattern4 = r'<main[^>]*>.*?<img[^>]+src="([^"]+\.(?:jpg|jpeg|png|webp))"'
        match = re.search(pattern4, html, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1)
        
        # Pattern 5: Open Graph image meta tag
        pattern5 = r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"'
        match = re.search(pattern5, html, re.IGNORECASE)
        if match:
            return match.group(1)
        
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
    
    def scrape_product_image(self, product: Dict) -> Dict:
        """Scrape image from AADF product page"""
        
        self.stats['total'] += 1
        result = {
            'product_key': product['product_key'],
            'product_name': product['product_name'],
            'product_url': product['product_url'],
            'image_url': None,
            'error': None,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            print(f"  Scraping: {product['product_name'][:50]}...")
            
            # Scrape the page
            response = scraping_client.get(
                product['product_url'],
                params={
                    'country_code': 'gb',
                    'premium_proxy': True,
                    'stealth_proxy': True,
                    'render_js': False  # AADF usually doesn't need JS
                }
            )
            
            if response.status_code == 200:
                html = response.text
                
                # Extract image URL
                img_url = self.extract_image_url(html)
                
                if img_url:
                    # Make absolute URL
                    img_url = self.make_absolute_url(img_url, product['product_url'])
                    result['image_url'] = img_url
                    self.stats['images_found'] += 1
                    print(f"    ✅ Found image: {img_url[:80]}...")
                else:
                    result['error'] = 'No image found on page'
                    print(f"    ⚠️ No image found")
            else:
                result['error'] = f'HTTP {response.status_code}'
                print(f"    ❌ HTTP {response.status_code}")
                
        except Exception as e:
            result['error'] = str(e)[:200]
            self.stats['errors'] += 1
            print(f"    ❌ Error: {str(e)[:100]}")
        
        # Save to GCS if enabled
        if self.save_to_gcs:
            self.save_to_gcs_storage(result)
        
        # Small delay to be respectful
        time.sleep(2)
        
        return result
    
    def save_to_gcs_storage(self, result: Dict):
        """Save scraped data to GCS"""
        try:
            # Create filename
            safe_key = result['product_key'].replace('|', '_').replace('/', '_')
            filename = f"scraped/aadf_images/{self.session_id}/{safe_key}.json"
            
            # Upload to GCS
            blob = bucket.blob(filename)
            blob.upload_from_string(
                json.dumps(result, indent=2),
                content_type='application/json'
            )
            
            self.stats['images_saved'] += 1
            
        except Exception as e:
            print(f"    Warning: Failed to save to GCS: {e}")
    
    def update_database(self, result: Dict):
        """Update database with image URL"""
        if result.get('image_url'):
            try:
                # Update the product with image URL
                response = supabase.table('foods_canonical')\
                    .update({'image_url': result['image_url']})\
                    .eq('product_key', result['product_key'])\
                    .execute()
                
                if response.data:
                    self.stats['db_updated'] += 1
                    print(f"    ✅ Database updated")
                    return True
            except Exception as e:
                print(f"    ❌ Database update failed: {e}")
        
        return False
    
    def scrape_batch(self, products: list):
        """Scrape images for a batch of products"""
        print(f"\n🔍 Scraping images from {len(products)} AADF products...")
        print("=" * 80)
        
        results = []
        
        for i, product in enumerate(products, 1):
            print(f"\n[{i}/{len(products)}] {product['brand']} - {product['product_name'][:40]}...")
            
            # Scrape the image
            result = self.scrape_product_image(product)
            results.append(result)
            
            # Update database immediately if image found
            if result.get('image_url'):
                self.update_database(result)
        
        return results
    
    def print_summary(self):
        """Print scraping summary"""
        print("\n" + "=" * 80)
        print("📊 SCRAPING SUMMARY")
        print("=" * 80)
        print(f"Total products processed: {self.stats['total']}")
        print(f"Images found: {self.stats['images_found']}")
        print(f"Images saved to GCS: {self.stats['images_saved']}")
        print(f"Database updated: {self.stats['db_updated']}")
        print(f"Errors: {self.stats['errors']}")
        
        if self.stats['total'] > 0:
            success_rate = (self.stats['images_found'] / self.stats['total']) * 100
            print(f"\nSuccess rate: {success_rate:.1f}%")
        
        if self.save_to_gcs:
            print(f"\nGCS folder: gs://lupito-content-raw-eu/scraped/aadf_images/{self.session_id}/")

def main():
    # Get 5 AADF products without images
    print("🎯 Getting AADF products without images...")
    
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
    
    # Create scraper
    scraper = AADFImageScraper(save_to_gcs=True)
    
    # Scrape images
    results = scraper.scrape_batch(products.data)
    
    # Print summary
    scraper.print_summary()
    
    # Show results
    print("\n📸 RESULTS:")
    print("-" * 80)
    for result in results:
        print(f"\n{result['product_name'][:50]}...")
        if result.get('image_url'):
            print(f"  ✅ Image: {result['image_url'][:80]}...")
        else:
            print(f"  ❌ No image: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main()