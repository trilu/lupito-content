#!/usr/bin/env python3
"""
Backfill images for existing products in database
Adds images to products that already exist but lack image_url
"""
import os
import sys
import time
import random
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

import requests
from supabase import create_client, Client
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

load_dotenv()

class PFXImageBackfill:
    def __init__(self):
        """Initialize the image backfill system"""
        self.supabase = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_KEY')
        )
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; LupitoBot/1.0)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })
        
        self.config = {
            'rate_limit_seconds': 2.0,
            'timeout': 30,
            'storage_bucket': 'dog-food',
            'image_timeout': 15
        }
        
        self.stats = {
            'products_found': 0,
            'products_processed': 0,
            'images_extracted': 0,
            'images_downloaded': 0,
            'images_uploaded': 0,
            'images_failed': 0,
            'database_updated': 0,
            'errors': 0
        }

    def get_products_without_images(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get PFX products missing image URLs"""
        print("🔍 Finding products without images...")
        
        query = self.supabase.table('food_candidates')\
            .select('id, brand, product_name, source_url, fingerprint')\
            .eq('source_domain', 'petfoodexpert.com')\
            .is_('image_url', 'null')
        
        if limit:
            query = query.limit(limit)
        
        result = query.execute()
        products = result.data if result.data else []
        
        print(f"📊 Found {len(products)} products without images")
        return products

    def extract_image_url(self, product_url: str, soup: BeautifulSoup) -> Optional[str]:
        """Extract product image URL from HTML"""
        try:
            # Extract slug from product URL
            slug = product_url.split('/food/')[-1]
            
            # Look for image ID in the HTML
            img_elements = soup.find_all('img', {'data-src': True})
            for img in img_elements:
                data_src = img.get('data-src', '')
                if slug in data_src and 'packshots' in data_src and 'thumb--md.jpg' in data_src:
                    return data_src
            
            # Fallback: look for standard img src
            img_elements = soup.find_all('img', {'src': True})
            for img in img_elements:
                src = img.get('src', '')
                if slug in src and 'packshots' in src:
                    return src
            
            # Look for any packshot URL patterns to get the ID
            all_text = str(soup)
            import re
            packshot_match = re.search(r'packshots/(\d+)/', all_text)
            if packshot_match:
                image_id = packshot_match.group(1)
                constructed_url = f"https://petfoodexpert.com/packshots/{image_id}/conversions/{slug}-thumb--md.jpg"
                return constructed_url
            
            return None
            
        except Exception as e:
            print(f"    ⚠️  Could not extract image URL: {e}")
            return None

    def download_and_store_image(self, image_url: str, product_url: str) -> Optional[str]:
        """Download image and store in Supabase bucket"""
        try:
            # Generate filename from product URL slug
            slug = product_url.split('/food/')[-1]
            filename = f"{slug}.jpg"
            
            print(f"    📥 Downloading: {image_url}")
            
            # Check if file already exists in bucket
            try:
                existing = self.supabase.storage.from_(self.config['storage_bucket']).list(path="")
                if any(file['name'] == filename for file in existing):
                    print(f"    🔄 Already in bucket: {filename}")
                    bucket_url = self.supabase.storage.from_(self.config['storage_bucket']).get_public_url(filename)
                    return bucket_url
            except:
                pass
            
            # Download image
            response = self.session.get(image_url, timeout=self.config['image_timeout'])
            response.raise_for_status()
            
            if len(response.content) == 0:
                print(f"    ⚠️  Empty image file")
                return None
            
            self.stats['images_downloaded'] += 1
            print(f"    📦 Downloaded {len(response.content)} bytes")
            
            # Upload to Supabase storage
            upload_result = self.supabase.storage.from_(self.config['storage_bucket']).upload(
                filename,
                response.content,
                file_options={
                    'content-type': 'image/jpeg',
                    'cache-control': '3600'
                }
            )
            
            self.stats['images_uploaded'] += 1
            
            # Get public URL
            bucket_url = self.supabase.storage.from_(self.config['storage_bucket']).get_public_url(filename)
            print(f"    ✅ Uploaded: {bucket_url}")
            
            return bucket_url
            
        except Exception as e:
            print(f"    ❌ Image processing failed: {e}")
            self.stats['images_failed'] += 1
            return None

    def update_product_image(self, product_id: int, image_url: str) -> bool:
        """Update product with image URL"""
        try:
            self.supabase.table('food_candidates')\
                .update({'image_url': image_url, 'last_seen_at': datetime.now().isoformat()})\
                .eq('id', product_id)\
                .execute()
            
            self.stats['database_updated'] += 1
            return True
            
        except Exception as e:
            print(f"    ❌ Database update failed: {e}")
            return False

    def process_product(self, product: Dict[str, Any]) -> bool:
        """Process a single product for image backfill"""
        try:
            product_id = product['id']
            brand = product['brand']
            name = product['product_name']
            source_url = product['source_url']
            
            print(f"  📦 {brand} {name}")
            
            # Fetch HTML page
            time.sleep(self.config['rate_limit_seconds'] + random.uniform(-0.3, 0.3))
            
            response = self.session.get(source_url, timeout=self.config['timeout'])
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract image URL
            source_image_url = self.extract_image_url(source_url, soup)
            
            if not source_image_url:
                print(f"    ⚠️  No image found")
                return False
            
            self.stats['images_extracted'] += 1
            
            # Download and store image
            bucket_image_url = self.download_and_store_image(source_image_url, source_url)
            
            if not bucket_image_url:
                return False
            
            # Update database
            success = self.update_product_image(product_id, bucket_image_url)
            if success:
                print(f"    ✅ Updated database")
            
            self.stats['products_processed'] += 1
            return success
            
        except Exception as e:
            print(f"    ❌ Error processing product: {e}")
            self.stats['errors'] += 1
            return False

    def run_backfill(self, limit: Optional[int] = None):
        """Run the image backfill process"""
        print("🚀 Starting PFX Image Backfill")
        print("=" * 60)
        
        # Get products without images
        products = self.get_products_without_images(limit)
        self.stats['products_found'] = len(products)
        
        if not products:
            print("✅ All products already have images!")
            return
        
        print(f"\n📋 Processing {len(products)} products...")
        print("=" * 60)
        
        # Process each product
        for i, product in enumerate(products, 1):
            print(f"\n[{i}/{len(products)}]", end=" ")
            self.process_product(product)
        
        self._print_final_report()

    def _print_final_report(self):
        """Print final backfill report"""
        print("\n" + "=" * 60)
        print("🎯 PFX IMAGE BACKFILL REPORT")
        print("=" * 60)
        print(f"Products found:         {self.stats['products_found']}")
        print(f"Products processed:     {self.stats['products_processed']}")
        print(f"Images extracted:       {self.stats['images_extracted']}")
        print(f"Images downloaded:      {self.stats['images_downloaded']}")
        print(f"Images uploaded:        {self.stats['images_uploaded']}")
        print(f"Images failed:          {self.stats['images_failed']}")
        print(f"Database updated:       {self.stats['database_updated']}")
        print(f"Errors encountered:     {self.stats['errors']}")
        
        if self.stats['products_found'] > 0:
            success_rate = (self.stats['products_processed'] / self.stats['products_found']) * 100
            image_rate = (self.stats['images_extracted'] / self.stats['products_found']) * 100
            upload_rate = (self.stats['images_uploaded'] / max(self.stats['images_extracted'], 1)) * 100
            print(f"Processing success rate: {success_rate:.1f}%")
            print(f"Image extraction rate:   {image_rate:.1f}%")
            print(f"Image upload rate:       {upload_rate:.1f}%")
        
        print("=" * 60)

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Backfill images for existing PFX products')
    parser.add_argument('--limit', type=int, help='Limit number of products to process')
    
    args = parser.parse_args()
    
    backfill = PFXImageBackfill()
    backfill.run_backfill(args.limit)

if __name__ == '__main__':
    main()