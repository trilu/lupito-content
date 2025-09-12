#!/usr/bin/env python3
"""
Quick check of known failed scraping sessions
"""

import os
import json
from dotenv import load_dotenv
from google.cloud import storage
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")

def check_failed_folders():
    """Check specific folders we know had errors"""
    
    storage_client = storage.Client()
    bucket = storage_client.bucket(GCS_BUCKET)
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Folders we know had errors from the processing run
    error_folders = [
        'scraped/zooplus/20250912_202523',  # 1 error
        'scraped/zooplus/20250912_203336',  # 10 errors
        'scraped/zooplus/20250912_204659',  # 3 errors
        'scraped/zooplus/20250912_202317',  # Had errors
    ]
    
    print("🔍 CHECKING FAILED SCRAPING SESSIONS")
    print("=" * 60)
    
    failed_products = []
    
    for folder in error_folders:
        print(f"\n📁 Checking {folder}...")
        
        # List files in folder
        blobs = bucket.list_blobs(prefix=folder + '/')
        json_files = [b for b in blobs if b.name.endswith('.json')]
        
        for blob in json_files:
            try:
                # Download and check content
                content = blob.download_as_text()
                data = json.loads(content)
                
                # Check if it's a failed scrape
                if 'error' in data:
                    print(f"   ❌ {os.path.basename(blob.name)}: {data['error']}")
                    
                    # Extract URL from the data
                    url = data.get('url', '')
                    
                    # Try to get product_key from filename if not in data
                    if not data.get('product_key'):
                        filename = os.path.basename(blob.name).replace('.json', '')
                        product_key = filename.replace('_', '|')
                    else:
                        product_key = data['product_key']
                    
                    failed_products.append({
                        'product_key': product_key,
                        'url': url,
                        'error': data['error']
                    })
                    
            except Exception as e:
                print(f"   Error reading {blob.name}: {e}")
    
    print(f"\n📊 SUMMARY")
    print(f"   Total failed products found: {len(failed_products)}")
    
    # Check database status
    products_to_rescrape = []
    
    if failed_products:
        print(f"\n🔍 Checking database status...")
        
        for product in failed_products:
            # Parse product_key to get identifiable components
            key_parts = product['product_key'].split('|')
            if len(key_parts) >= 2:
                brand = key_parts[0]
                name_part = key_parts[1]
                
                try:
                    # Search for product in database
                    result = supabase.table('foods_canonical')\
                        .select('product_key, product_url, ingredients_raw')\
                        .ilike('product_key', f'%{brand}%{name_part}%')\
                        .limit(1)\
                        .execute()
                    
                    if result.data:
                        db_product = result.data[0]
                        if not db_product.get('ingredients_raw'):
                            products_to_rescrape.append({
                                'product_key': db_product['product_key'],
                                'url': db_product.get('product_url', product['url'])
                            })
                            print(f"   📌 Found in DB, needs ingredients: {db_product['product_key'][:50]}...")
                except Exception as e:
                    print(f"   Error checking DB for {product['product_key'][:30]}: {e}")
    
    # Save re-scraping list
    if products_to_rescrape:
        output_file = 'scripts/products_to_rescrape.json'
        with open(output_file, 'w') as f:
            json.dump({
                'total_failed': len(failed_products),
                'to_rescrape': len(products_to_rescrape),
                'products': products_to_rescrape
            }, f, indent=2)
        
        print(f"\n✅ Re-scraping list saved to: {output_file}")
        print(f"   {len(products_to_rescrape)} products need re-scraping")
        
        # Create simple URL list for scrapers
        url_file = 'scripts/rescrape_urls.txt'
        with open(url_file, 'w') as f:
            for product in products_to_rescrape:
                if product['url']:
                    f.write(f"{product['url']}\n")
        
        print(f"   URL list saved to: {url_file}")
    
    return products_to_rescrape

if __name__ == "__main__":
    check_failed_folders()