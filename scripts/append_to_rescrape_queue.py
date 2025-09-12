#!/usr/bin/env python3
"""
Append failed products to the rescraping queue
"""

import sys
import json
import os

def append_to_queue(failed_products_file=None):
    """Append failed products to rescrape_queue.txt"""
    
    queue_file = 'scripts/rescrape_queue.txt'
    
    # Read existing queue
    existing_urls = set()
    if os.path.exists(queue_file):
        with open(queue_file, 'r') as f:
            for line in f:
                if '|' in line:
                    url = line.split('|')[0].strip()
                    existing_urls.add(url)
    
    # Get failed products from JSON file or stdin
    if failed_products_file and os.path.exists(failed_products_file):
        with open(failed_products_file, 'r') as f:
            data = json.load(f)
            products = data.get('products', [])
    else:
        # Read from stdin if no file provided
        products = json.loads(sys.stdin.read()).get('products', [])
    
    # Append new URLs to queue
    added = 0
    with open(queue_file, 'a') as f:
        for product in products:
            url = product.get('url', '')
            product_key = product.get('product_key', '')
            
            if url and url not in existing_urls:
                f.write(f"{url}|{product_key}\n")
                existing_urls.add(url)
                added += 1
    
    print(f"✅ Added {added} new URLs to rescrape queue")
    print(f"   Queue file: {queue_file}")
    print(f"   Total URLs in queue: {len(existing_urls)}")
    
    return added

if __name__ == "__main__":
    if len(sys.argv) > 1:
        append_to_queue(sys.argv[1])
    else:
        append_to_queue()