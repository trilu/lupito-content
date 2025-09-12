#!/usr/bin/env python3
"""
Process batch of 100 scraped files and track failures for rescraping
"""

import os
import sys
import json
from datetime import datetime
from typing import List, Dict
from process_gcs_scraped_data import GCSDataProcessor
from dotenv import load_dotenv
from supabase import create_client
from google.cloud import storage

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")

def process_batch_100_with_tracking():
    """Process 100 files and track failures"""
    
    # Get recent folders to process (skip the ones we already processed)
    folders_to_process = [
        'scraped/zooplus/20250912_212536_fr1',
        'scraped/zooplus/20250912_212536_us1',
        'scraped/zooplus/20250912_212610_gb1',
        'scraped/zooplus/20250912_212645_de1',
        'scraped/zooplus/20250912_212831_ca1',
        'scraped/zooplus/20250912_215454_us3',
        'scraped/zooplus/20250912_215454_gb3',
        'scraped/zooplus/20250912_215454_de3',
        'scraped/zooplus/20250912_215454_fr3',
        'scraped/zooplus/20250912_215454_ca3',
        'scraped/zooplus/20250912_215504_it2',
        'scraped/zooplus/20250912_215504_es2',
        'scraped/zooplus/20250912_215504_nl2',
        'scraped/zooplus/20250912_215504_au2',
        'scraped/zooplus/20250912_215504_no2',
        'scraped/zooplus/20250912_215504_it4',
        'scraped/zooplus/20250912_215504_es4',
        'scraped/zooplus/20250912_215504_nl4',
        'scraped/zooplus/20250912_215504_au4',
        'scraped/zooplus/20250912_215504_no4',
        'scraped/zooplus/20250912_224629_rescrape',  # Include rescrape results
    ]
    
    total_processed = 0
    max_files = 100
    failed_products = []  # Track failures for rescraping
    
    total_stats = {
        'files_processed': 0,
        'products_updated': 0,
        'ingredients_added': 0,
        'nutrition_added': 0,
        'errors': 0,
        'skipped': 0
    }
    
    start_time = datetime.now()
    storage_client = storage.Client()
    bucket = storage_client.bucket(GCS_BUCKET)
    
    print("🔄 PROCESSING BATCH OF 100 FILES WITH FAILURE TRACKING")
    print("=" * 60)
    print(f"Started at: {start_time.strftime('%H:%M:%S')}\n")
    
    # Get initial coverage
    print("📊 INITIAL DATABASE COVERAGE:")
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        total_before = supabase.table('foods_canonical').select('*', count='exact').execute().count
        ingredients_before = supabase.table('foods_canonical').select('*', count='exact').not_.is_('ingredients_raw', 'null').execute().count
        print(f"   Products with ingredients: {ingredients_before:,} ({ingredients_before/total_before*100:.1f}%)\n")
    except Exception as e:
        print(f"   Error checking coverage: {e}\n")
        ingredients_before = 0
    
    # Process each folder
    for folder_idx, folder in enumerate(folders_to_process, 1):
        if total_processed >= max_files:
            break
            
        print(f"📁 [{folder_idx}/{len(folders_to_process)}] Processing: {folder}")
        processor = GCSDataProcessor(folder)
        
        # Get list of files
        files = processor.list_scraped_files()
        
        if not files:
            print(f"   No files found in this folder\n")
            continue
        
        # Process files (up to remaining limit)
        files_to_process = min(len(files), max_files - total_processed)
        
        for i, file_path in enumerate(files[:files_to_process], 1):
            product_name = os.path.basename(file_path).replace('.json', '')
            print(f"   [{total_processed + i}/{max_files}] {product_name[:50]}...", end='')
            
            # Download and check for error first
            try:
                blob = bucket.blob(file_path)
                content = blob.download_as_text()
                data = json.loads(content)
                
                if 'error' in data:
                    print(f" ⏭️  Skip (error: {data['error'][:30]})")
                    total_stats['skipped'] += 1
                    
                    # Add to failed products list for rescraping
                    if data.get('url'):
                        failed_products.append({
                            'url': data['url'],
                            'product_key': data.get('product_key', product_name.replace('_', '|')),
                            'error': data['error'],
                            'file': file_path
                        })
                    continue
            except Exception as e:
                print(f" ❌ Error: {str(e)[:30]}")
                continue
            
            success = processor.download_and_process(file_path)
            
            if success:
                print(f" ✅")
            else:
                print(f" ⚠️")
        
        # Update total stats
        total_processed += files_to_process
        total_stats['files_processed'] += processor.stats['files_processed']
        total_stats['products_updated'] += processor.stats['products_updated']
        total_stats['ingredients_added'] += processor.stats['ingredients_added']
        total_stats['nutrition_added'] += processor.stats['nutrition_added']
        total_stats['errors'] += processor.stats['errors']
        
        print(f"   Folder complete: {processor.stats['products_updated']}/{files_to_process} updated\n")
        
        if total_processed >= max_files:
            break
    
    # Final statistics
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("=" * 60)
    print(f"✅ BATCH PROCESSING COMPLETE")
    print(f"   Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    print(f"   Files processed: {total_stats['files_processed']}")
    print(f"   Products updated: {total_stats['products_updated']}")
    print(f"   Ingredients added: {total_stats['ingredients_added']}")
    print(f"   Nutrition added: {total_stats['nutrition_added']}")
    print(f"   Skipped (errors): {total_stats['skipped']}")
    print(f"   Processing errors: {total_stats['errors']}")
    
    if total_stats['files_processed'] > 0:
        success_rate = (total_stats['products_updated'] / total_stats['files_processed']) * 100
        print(f"   Success rate: {success_rate:.1f}%")
        print(f"   Processing speed: {total_stats['files_processed']/duration*60:.1f} files/minute")
    
    # Query database to show updated coverage
    print(f"\n📊 UPDATED DATABASE COVERAGE:")
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        total_after = supabase.table('foods_canonical').select('*', count='exact').execute().count
        ingredients_after = supabase.table('foods_canonical').select('*', count='exact').not_.is_('ingredients_raw', 'null').execute().count
        nutrition_after = supabase.table('foods_canonical').select('*', count='exact')\
            .not_.is_('protein_percent', 'null')\
            .not_.is_('fat_percent', 'null')\
            .not_.is_('fiber_percent', 'null')\
            .not_.is_('ash_percent', 'null')\
            .not_.is_('moisture_percent', 'null').execute().count
        
        ingredients_gained = ingredients_after - ingredients_before
        
        print(f"   Total products: {total_after:,}")
        print(f"   With ingredients: {ingredients_after:,} ({ingredients_after/total_after*100:.1f}%)")
        print(f"   Complete nutrition: {nutrition_after:,} ({nutrition_after/total_after*100:.1f}%)")
        print(f"   ")
        print(f"   🎯 Ingredients gained: +{ingredients_gained}")
        print(f"   📈 Coverage increased: {ingredients_before/total_before*100:.1f}% → {ingredients_after/total_after*100:.1f}%")
        print(f"   🚀 Gap to 95%: {int(total_after * 0.95) - ingredients_after:,} products")
        
    except Exception as e:
        print(f"   Error checking coverage: {e}")
    
    # Handle failed products
    if failed_products:
        print(f"\n❌ FAILED PRODUCTS FOUND: {len(failed_products)}")
        
        # Append to rescrape queue
        queue_file = 'scripts/rescrape_queue.txt'
        
        # Read existing queue to avoid duplicates
        existing_urls = set()
        if os.path.exists(queue_file):
            with open(queue_file, 'r') as f:
                for line in f:
                    if '|' in line:
                        url = line.split('|')[0].strip()
                        existing_urls.add(url)
        
        # Append new failures to queue
        added = 0
        with open(queue_file, 'a') as f:
            for product in failed_products:
                url = product.get('url', '')
                product_key = product.get('product_key', '')
                
                if url and url not in existing_urls:
                    f.write(f"{url}|{product_key}\n")
                    existing_urls.add(url)
                    added += 1
        
        print(f"   ✅ Added {added} URLs to rescrape queue")
        print(f"   Queue file: {queue_file}")
        print(f"   Total URLs in queue: {len(existing_urls)}")
        
        # Show error breakdown
        error_types = {}
        for product in failed_products:
            error = product['error'][:50]
            error_types[error] = error_types.get(error, 0) + 1
        
        print(f"\n   Error breakdown:")
        for error, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"      {error}: {count} occurrences")
        
        print(f"\n💡 Next step: Run rescraper on these {len(unique_urls)} failed URLs")
        
        return failed_products
    else:
        print(f"\n✅ NO FAILED PRODUCTS - All processed successfully!")
        return []

if __name__ == "__main__":
    failed_products = process_batch_100_with_tracking()