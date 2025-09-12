#!/usr/bin/env python3
"""
Identify failed scrapes and create a list for re-scraping
"""

import os
import json
from typing import List, Dict
from dotenv import load_dotenv
from google.cloud import storage
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")

def identify_failed_scrapes():
    """Identify all failed scrapes from GCS and create re-scraping list"""
    
    storage_client = storage.Client()
    bucket = storage_client.bucket(GCS_BUCKET)
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("🔍 IDENTIFYING FAILED SCRAPES FOR RE-PROCESSING")
    print("=" * 60)
    
    # Get all scraped folders
    blobs = bucket.list_blobs(prefix="scraped/zooplus/")
    folders = set()
    for blob in blobs:
        if '/' in blob.name:
            folder = '/'.join(blob.name.split('/')[:3])
            folders.add(folder)
    
    folders = sorted(list(folders))
    print(f"Found {len(folders)} scraping session folders\n")
    
    failed_products = []
    error_types = {}
    total_files = 0
    
    # Check each folder
    for folder_idx, folder in enumerate(folders, 1):
        print(f"[{folder_idx}/{len(folders)}] Checking {folder}...")
        
        # List files in folder
        folder_blobs = bucket.list_blobs(prefix=folder + '/')
        json_files = [b for b in folder_blobs if b.name.endswith('.json')]
        
        for blob in json_files:
            total_files += 1
            
            try:
                # Download and check content
                content = blob.download_as_text()
                data = json.loads(content)
                
                # Check if it's a failed scrape
                if 'error' in data:
                    error = data['error']
                    error_types[error] = error_types.get(error, 0) + 1
                    
                    # Extract product info
                    failed_products.append({
                        'file': blob.name,
                        'url': data.get('url', ''),
                        'product_key': data.get('product_key', ''),
                        'error': error,
                        'scraped_at': data.get('scraped_at', ''),
                        'folder': folder
                    })
                    
            except Exception as e:
                print(f"   Error reading {blob.name}: {e}")
    
    print(f"\n📊 ANALYSIS COMPLETE")
    print(f"   Total files scanned: {total_files}")
    print(f"   Failed scrapes found: {len(failed_products)}")
    print(f"   Success rate: {(total_files - len(failed_products))/total_files*100:.1f}%")
    
    if error_types:
        print(f"\n❌ ERROR BREAKDOWN:")
        for error, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
            print(f"   {error}: {count} occurrences")
    
    # Get unique URLs for re-scraping
    unique_urls = {}
    for product in failed_products:
        if product['url'] and product['url'] not in unique_urls:
            unique_urls[product['url']] = product['product_key']
    
    print(f"\n🔄 PRODUCTS TO RE-SCRAPE:")
    print(f"   Unique URLs: {len(unique_urls)}")
    
    # Check which ones are still missing ingredients in database
    missing_ingredients = []
    
    if unique_urls:
        print(f"\n🔍 Checking database status of failed products...")
        
        for url, product_key in unique_urls.items():
            if product_key:
                try:
                    result = supabase.table('foods_canonical')\
                        .select('product_key, ingredients_raw')\
                        .eq('product_key', product_key)\
                        .execute()
                    
                    if result.data and not result.data[0].get('ingredients_raw'):
                        missing_ingredients.append({
                            'product_key': product_key,
                            'url': url
                        })
                except:
                    pass
    
    print(f"   Still missing ingredients: {len(missing_ingredients)}")
    
    # Save re-scraping list
    if missing_ingredients:
        output_file = 'scripts/rescrape_failed_products.json'
        with open(output_file, 'w') as f:
            json.dump({
                'total_failed': len(failed_products),
                'unique_urls': len(unique_urls),
                'to_rescrape': len(missing_ingredients),
                'products': missing_ingredients
            }, f, indent=2)
        
        print(f"\n✅ Re-scraping list saved to: {output_file}")
        
        # Show sample of products to re-scrape
        print(f"\n📋 SAMPLE PRODUCTS TO RE-SCRAPE:")
        for product in missing_ingredients[:5]:
            print(f"   - {product['product_key'][:60]}...")
            print(f"     {product['url'][:80]}...")
    
    return missing_ingredients

def create_rescrape_batch_file():
    """Create a batch file that orchestrators can use"""
    
    failed_products = identify_failed_scrapes()
    
    if failed_products:
        # Create batch file for orchestrators
        batch_file = 'scripts/rescrape_batch.txt'
        with open(batch_file, 'w') as f:
            for product in failed_products:
                # Format: product_key|url
                f.write(f"{product['product_key']}|{product['url']}\n")
        
        print(f"\n📝 Batch file created: {batch_file}")
        print(f"   Contains {len(failed_products)} products for re-scraping")
        print(f"\n💡 TO USE WITH ORCHESTRATORS:")
        print(f"   1. Stop current orchestrators")
        print(f"   2. Modify orchestrated_scraper.py to read from this file")
        print(f"   3. Restart orchestrators to process failed products")

if __name__ == "__main__":
    create_rescrape_batch_file()