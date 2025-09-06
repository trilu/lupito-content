#!/usr/bin/env python3
"""
PetFoodExpert URL-Based Scraper
Uses known product URLs to harvest all products efficiently
"""
import os
import sys
import time
import random
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from io import BytesIO

import requests
from supabase import create_client, Client
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from etl.normalize_foods import (
    parse_energy, parse_percent, parse_pack_size,
    tokenize_ingredients, check_contains_chicken,
    parse_price, normalize_currency, generate_fingerprint,
    normalize_form, normalize_life_stage, extract_gtin, clean_text,
    estimate_kcal_from_analytical, contains, derive_form, derive_life_stage
)
from etl.nutrition_parser import parse_nutrition_from_html

# Load environment variables
load_dotenv()

class PFXUrlScraper:
    def __init__(self):
        """Initialize the URL-based scraper"""
        self.session = self._setup_session()
        self.supabase = self._setup_supabase()
        
        # Configuration
        self.config = {
            'rate_limit_seconds': 2.0,  # Be respectful
            'timeout': 30,
            'batch_size': 50,  # Process in batches
            'storage_bucket': 'dog-food',  # Supabase storage bucket
            'image_timeout': 15  # Timeout for image downloads
        }
        
        self.stats = {
            'urls_processed': 0,
            'products_processed': 0,
            'products_new': 0,
            'products_updated': 0,
            'products_skipped': 0,
            'nutrition_extracted': 0,
            'images_extracted': 0,
            'images_downloaded': 0,
            'images_uploaded': 0,
            'images_failed': 0,
            'errors': 0
        }

    def _setup_session(self) -> requests.Session:
        """Setup requests session with headers"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; LupitoBot/1.0)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive'
        })
        return session

    def _setup_supabase(self) -> Client:
        """Setup Supabase client"""
        return create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_KEY')
        )

    def _rate_limit(self):
        """Apply rate limiting"""
        time.sleep(self.config['rate_limit_seconds'] + random.uniform(-0.3, 0.3))

    def load_urls_from_file(self, file_path: str) -> List[str]:
        """Load product URLs from file"""
        urls = []
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    url = line.strip()
                    if url and url.startswith('https://'):
                        urls.append(url)
            print(f"📋 Loaded {len(urls)} URLs from {file_path}")
            return urls
        except Exception as e:
            print(f"❌ Error loading URLs from {file_path}: {e}")
            return []

    def download_and_store_image(self, image_url: str, product_url: str) -> Optional[str]:
        """Download image and store in Supabase bucket, return bucket URL"""
        try:
            # Generate filename from product URL slug
            slug = product_url.split('/food/')[-1]
            filename = f"{slug}.jpg"
            
            print(f"    📥 Downloading image: {image_url}")
            
            # Check if file already exists in bucket
            try:
                existing = self.supabase.storage.from_(self.config['storage_bucket']).list(path="")
                if any(file['name'] == filename for file in existing):
                    print(f"    🔄 Image already exists in bucket: {filename}")
                    # Return the existing URL
                    bucket_url = self.supabase.storage.from_(self.config['storage_bucket']).get_public_url(filename)
                    return bucket_url
            except:
                # If we can't check, proceed with download
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
            bucket_path = filename
            
            # Upload image to bucket
            upload_result = self.supabase.storage.from_(self.config['storage_bucket']).upload(
                bucket_path,
                response.content,
                file_options={
                    'content-type': 'image/jpeg',
                    'cache-control': '3600'
                }
            )
            
            self.stats['images_uploaded'] += 1
            
            # Get public URL
            bucket_url = self.supabase.storage.from_(self.config['storage_bucket']).get_public_url(filename)
            print(f"    ✅ Uploaded to bucket: {bucket_url}")
            
            return bucket_url
            
        except Exception as e:
            print(f"    ❌ Image processing failed: {e}")
            self.stats['images_failed'] += 1
            return None

    def extract_image_url(self, product_url: str, soup: BeautifulSoup) -> Optional[str]:
        """Extract product image URL"""
        try:
            # Extract slug from product URL
            # https://petfoodexpert.com/food/canagan-insect-dry-dog -> canagan-insect-dry-dog
            slug = product_url.split('/food/')[-1]
            
            # Look for image ID in the HTML
            # Pattern: <img data-src="https://petfoodexpert.com/packshots/184/conversions/canagan-insect-dry-dog-thumb--md.jpg"
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
            
            # If we can't find it in HTML, try to extract image ID and construct URL
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

    def scrape_product_from_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape a single product from URL"""
        try:
            self._rate_limit()
            
            response = self.session.get(url, timeout=self.config['timeout'])
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract brand and product name from title or headings
            title = soup.find('title')
            title_text = title.get_text(strip=True) if title else ''
            
            # Try to extract brand and name from page structure
            brand = None
            product_name = None
            
            # Look for common heading patterns
            h1 = soup.find('h1')
            if h1:
                h1_text = h1.get_text(strip=True)
                # Try to split into brand and name
                words = h1_text.split()
                if len(words) >= 2:
                    brand = words[0]
                    product_name = ' '.join(words[1:])
            
            # Fallback to title parsing
            if not brand or not product_name:
                # Remove "- PetFoodExpert" or similar suffixes
                clean_title = title_text.replace('Pet Food Expert | ', '').replace(' - PetFoodExpert', '')
                words = clean_title.split()
                if len(words) >= 2:
                    brand = words[0]
                    product_name = ' '.join(words[1:])
            
            if not brand or not product_name:
                print(f"    ⚠️  Could not extract brand/name from {url}")
                return None
            
            # Extract nutrition using our parser
            nutrition_data = parse_nutrition_from_html(response.text)
            
            # Extract other product details from page content
            ingredients = None
            form = None
            life_stage = None
            
            # Look for ingredients text
            page_text = soup.get_text().lower()
            if 'ingredients:' in page_text or 'composition:' in page_text:
                # Extract ingredients section
                for pattern in ['ingredients:', 'composition:']:
                    if pattern in page_text:
                        start = page_text.find(pattern)
                        if start != -1:
                            # Extract next 500 characters and clean up
                            ingredients_text = page_text[start:start+500]
                            # Take until next major section
                            for end_marker in ['\n\n', 'analytical', 'nutritional', 'feeding']:
                                if end_marker in ingredients_text[20:]:  # Skip first 20 chars
                                    ingredients_text = ingredients_text[:ingredients_text.find(end_marker, 20)]
                                    break
                            ingredients = clean_text(ingredients_text.replace(pattern, ''))
                            break
            
            # Derive form and life stage
            if ingredients:
                form = derive_form(ingredients)
                life_stage = derive_life_stage(ingredients)
            
            # If still no form, try to derive from URL or title
            if not form:
                url_lower = url.lower()
                title_lower = title_text.lower()
                if 'dry' in url_lower or 'dry' in title_lower:
                    form = 'dry'
                elif 'wet' in url_lower or 'wet' in title_lower:
                    form = 'wet'
                elif 'raw' in url_lower or 'raw' in title_lower:
                    form = 'raw'
            
            # Extract and process product image
            source_image_url = self.extract_image_url(url, soup)
            bucket_image_url = None
            
            if source_image_url:
                # Download and store in bucket
                bucket_image_url = self.download_and_store_image(source_image_url, url)
            
            # Build product data
            product_data = {
                'source_domain': 'petfoodexpert.com',
                'source_url': url,
                'brand': clean_text(brand),
                'product_name': clean_text(product_name),
                'form': form,
                'life_stage': life_stage,
                'ingredients_raw': ingredients,
                'image_url': bucket_image_url,
                'available_countries': ['UK', 'EU']
            }
            
            # Add nutrition data
            if nutrition_data:
                product_data.update(nutrition_data)
                self.stats['nutrition_extracted'] += 1
                print(f"    ✅ Nutrition: kcal={nutrition_data.get('kcal_per_100g')}, protein={nutrition_data.get('protein_percent')}%")
            
            # Log image processing
            if source_image_url:
                self.stats['images_extracted'] += 1
                if bucket_image_url:
                    print(f"    🖼️  Image stored: {bucket_image_url}")
                else:
                    print(f"    ⚠️  Image extraction failed")
            else:
                print(f"    ⚠️  No image found")
            
            # Add derived fields
            if ingredients:
                product_data['ingredients_tokens'] = tokenize_ingredients(ingredients)
                product_data['contains_chicken'] = check_contains_chicken(ingredients)
            
            return product_data
            
        except Exception as e:
            print(f"    ❌ Error scraping product {url}: {e}")
            self.stats['errors'] += 1
            return None

    def save_product(self, product_data: Dict[str, Any]) -> bool:
        """Save product to database"""
        try:
            # Generate fingerprint
            fingerprint = generate_fingerprint(
                product_data['brand'],
                product_data['product_name'],
                product_data.get('ingredients_raw', '')
            )
            product_data['fingerprint'] = fingerprint
            
            # Check for existing record
            existing = self.supabase.table('food_candidates')\
                .select('id')\
                .eq('fingerprint', fingerprint)\
                .execute()
            
            if existing.data:
                # Update existing
                update_data = {k: v for k, v in product_data.items() 
                              if k not in ['fingerprint', 'first_seen_at']}
                update_data['last_seen_at'] = datetime.now().isoformat()
                
                self.supabase.table('food_candidates')\
                    .update(update_data)\
                    .eq('fingerprint', fingerprint)\
                    .execute()
                
                self.stats['products_updated'] += 1
                print(f"    ✅ Updated existing product")
            else:
                # Insert new
                product_data['first_seen_at'] = datetime.now().isoformat()
                product_data['last_seen_at'] = datetime.now().isoformat()
                
                self.supabase.table('food_candidates').insert(product_data).execute()
                self.stats['products_new'] += 1
                print(f"    ✅ Added new product")
            
            self.stats['products_processed'] += 1
            return True
            
        except Exception as e:
            print(f"    ❌ Database error: {e}")
            self.stats['errors'] += 1
            return False

    def run_url_harvest(self, url_file_path: str):
        """Run the complete URL-based harvest"""
        print("🚀 Starting PetFoodExpert URL-Based Harvest")
        print("="*60)
        
        # Load URLs from file
        urls = self.load_urls_from_file(url_file_path)
        
        if not urls:
            print("❌ No URLs loaded. Exiting.")
            return
        
        print(f"\n📋 Processing {len(urls)} product URLs...")
        print("="*60)
        
        # Process URLs in batches
        batch_size = self.config['batch_size']
        total = len(urls)
        
        for i in range(0, total, batch_size):
            batch = urls[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total + batch_size - 1) // batch_size
            
            print(f"\n📦 Batch {batch_num}/{total_batches} ({len(batch)} URLs)")
            print("-" * 40)
            
            for j, url in enumerate(batch, 1):
                overall_progress = i + j
                self.stats['urls_processed'] += 1
                print(f"[{overall_progress}/{total}] Processing: {url}")
                
                product_data = self.scrape_product_from_url(url)
                if product_data:
                    self.save_product(product_data)
                    print(f"  📦 {product_data['brand']} {product_data['product_name']}")
                else:
                    self.stats['products_skipped'] += 1
            
            # Progress summary every batch
            print(f"\n  📈 Batch {batch_num} complete. Overall: {self.stats['products_processed']} processed, {self.stats['products_new']} new, {self.stats['products_updated']} updated")
        
        self._print_final_report()

    def _print_final_report(self):
        """Print final harvest report"""
        print("\n" + "="*60)
        print("🎯 PETFOODEXPERT URL HARVEST REPORT")
        print("="*60)
        print(f"URLs processed:         {self.stats['urls_processed']}")
        print(f"Products processed:     {self.stats['products_processed']}")
        print(f"New products added:     {self.stats['products_new']}")
        print(f"Products updated:       {self.stats['products_updated']}")
        print(f"Products skipped:       {self.stats['products_skipped']}")
        print(f"Nutrition extracted:    {self.stats['nutrition_extracted']}")
        print(f"Images extracted:       {self.stats['images_extracted']}")
        print(f"Images downloaded:      {self.stats['images_downloaded']}")
        print(f"Images uploaded:        {self.stats['images_uploaded']}")
        print(f"Images failed:          {self.stats['images_failed']}")
        print(f"Errors encountered:     {self.stats['errors']}")
        
        if self.stats['products_processed'] > 0:
            nutrition_rate = (self.stats['nutrition_extracted'] / self.stats['products_processed']) * 100
            image_rate = (self.stats['images_extracted'] / self.stats['products_processed']) * 100
            upload_rate = (self.stats['images_uploaded'] / max(self.stats['images_extracted'], 1)) * 100
            print(f"Nutrition success rate: {nutrition_rate:.1f}%")
            print(f"Image extraction rate:  {image_rate:.1f}%")
            print(f"Image upload rate:      {upload_rate:.1f}%")
        
        print("="*60)

def main():
    import argparse
    parser = argparse.ArgumentParser(description='PFX URL-based scraper')
    parser.add_argument('--urls', default='harvest_urls_v2.txt', help='URL file path')
    
    args = parser.parse_args()
    
    scraper = PFXUrlScraper()
    scraper.run_url_harvest(args.urls)

if __name__ == '__main__':
    main()