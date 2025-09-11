#!/usr/bin/env python3
"""
Harvest remaining Burns products that weren't harvested before
"""

import os
import requests
from pathlib import Path
from google.cloud import storage
from datetime import datetime
import time

# Initialize GCS
gcs_client = storage.Client(project='lupito-ai')
bucket = gcs_client.bucket('lupito-content-raw-eu')

def get_existing_products():
    """Get list of already harvested products"""
    existing = set()
    prefix = "manufacturers/burns/2025-09-11/"
    
    for blob in bucket.list_blobs(prefix=prefix):
        if blob.name.endswith('.html'):
            # Extract product slug from filename
            filename = blob.name.split('/')[-1].replace('.html', '')
            existing.add(filename)
    
    return existing

def harvest_product(url):
    """Harvest a single product using regular requests (no ScrapingBee needed for Burns)"""
    try:
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        
        if response.status_code == 200:
            return response.text
    except Exception as e:
        print(f"  Error fetching {url}: {e}")
    
    return None

def upload_to_gcs(html_content, product_url):
    """Upload HTML to GCS"""
    # Create filename from URL
    filename = product_url.replace('https://burnspet.co.uk/', '').replace('/', '_').rstrip('_')
    
    # Create blob path
    date_str = datetime.now().strftime('%Y-%m-%d')
    blob_path = f"manufacturers/burns/{date_str}/{filename}.html"
    
    # Upload
    blob = bucket.blob(blob_path)
    blob.upload_from_string(html_content, content_type='text/html')
    
    return blob_path

def main():
    """Main function"""
    print("="*80)
    print("HARVESTING REMAINING BURNS PRODUCTS")
    print("="*80)
    
    # Get existing products
    existing = get_existing_products()
    print(f"\nFound {len(existing)} existing products in GCS")
    
    # Load all product URLs
    with open('burns_all_product_urls.txt', 'r') as f:
        all_urls = [line.strip() for line in f if line.strip()]
    
    print(f"Found {len(all_urls)} total Burns products")
    
    # Find missing products
    remaining_urls = []
    for url in all_urls:
        # Create expected filename
        filename = url.replace('https://burnspet.co.uk/', '').replace('/', '_').rstrip('_')
        if filename not in existing:
            remaining_urls.append(url)
    
    print(f"Need to harvest {len(remaining_urls)} remaining products")
    
    if not remaining_urls:
        print("\n✓ All products already harvested!")
        return
    
    print("\nRemaining products to harvest:")
    for url in remaining_urls:
        print(f"  - {url}")
    
    # Harvest remaining products
    print(f"\n{'='*60}")
    print("HARVESTING")
    print(f"{'='*60}\n")
    
    successful = 0
    failed = 0
    
    for i, url in enumerate(remaining_urls, 1):
        print(f"[{i}/{len(remaining_urls)}] {url.split('/')[-1][:40]}...")
        
        # Fetch HTML
        html_content = harvest_product(url)
        
        if html_content:
            # Upload to GCS
            blob_path = upload_to_gcs(html_content, url)
            print(f"  ✓ Uploaded to {blob_path}")
            successful += 1
        else:
            print(f"  ✗ Failed to fetch")
            failed += 1
        
        # Small delay between requests
        if i < len(remaining_urls):
            time.sleep(2)
    
    print(f"\n{'='*80}")
    print("HARVEST COMPLETE")
    print(f"{'='*80}")
    print(f"✓ Successful: {successful}/{len(remaining_urls)}")
    print(f"✗ Failed: {failed}")
    
    # Update total count
    total_in_gcs = len(existing) + successful
    print(f"\nTotal Burns products in GCS: {total_in_gcs}/{len(all_urls)}")

if __name__ == "__main__":
    main()