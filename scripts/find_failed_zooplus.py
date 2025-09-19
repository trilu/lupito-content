#!/usr/bin/env python3
"""
Find the 19 Zooplus products that failed to scrape
"""

import json
import os
from google.cloud import storage

# Load the original 208 products
with open('retry_zooplus_pending.json', 'r') as f:
    all_products = json.load(f)

print(f"Total products to scrape: {len(all_products)}")

# Get list of successfully scraped products from GCS
storage_client = storage.Client()
bucket = storage_client.bucket("lupito-content-raw-eu")

scraped_keys = set()

# Check multiple possible session folders
possible_prefixes = [
    "scraped/zooplus_retry/20250916_222711_full_208/",
    "scraped/zooplus_retry/20250916_222635_full_208/"
]

for prefix in possible_prefixes:
    for blob in bucket.list_blobs(prefix=prefix):
        if blob.name.endswith('.json'):
            # Extract product key from filename
            filename = blob.name.replace(prefix, '').replace('.json', '')
            scraped_keys.add(filename)
            # Also try with pipe conversion
            product_key = filename.replace('_', '|')
            scraped_keys.add(product_key)

print(f"Successfully scraped: {len(scraped_keys)}")

# Find products that weren't scraped
failed_products = []
for product in all_products:
    if product['product_key'] not in scraped_keys:
        failed_products.append(product)

print(f"\nFailed to scrape: {len(failed_products)}")
print("\n" + "="*80)
print("FAILED PRODUCTS:")
print("="*80)

for i, product in enumerate(failed_products, 1):
    print(f"\n{i}. {product['product_name']}")
    print(f"   Key: {product['product_key']}")
    print(f"   URL: {product.get('product_url', 'No URL')}")

# Save to file
with open('failed_zooplus_19.json', 'w') as f:
    json.dump(failed_products, f, indent=2)

print(f"\nFailed products saved to: failed_zooplus_19.json")