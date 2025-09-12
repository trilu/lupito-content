#!/usr/bin/env python3
"""
Process next batch of 100 scraped files
Automatically queues failures for rescraping
"""

import os
import json
from datetime import datetime
from process_gcs_scraped_data import GCSDataProcessor
from dotenv import load_dotenv
from supabase import create_client
from google.cloud import storage

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")

def process_next_batch():
    """Process next 100 files from recent scraping sessions"""
    
    # Get more recent folders (continuing from where we left off)
    folders_to_process = [
        'scraped/zooplus/20250912_215454_ca3',  # Continuing from partial
        'scraped/zooplus/20250912_215647_de1',
        'scraped/zooplus/20250912_220249_no2',
        'scraped/zooplus/20250912_220323_it2',
        'scraped/zooplus/20250912_220323_nl2',
        'scraped/zooplus/20250912_220318_es4',
        'scraped/zooplus/20250912_220318_it4',
        'scraped/zooplus/20250912_220352_nl4',
        'scraped/zooplus/20250912_220349_gb1',
        'scraped/zooplus/20250912_220244_no4',
        'scraped/zooplus/20250912_220244_au4',
        'scraped/zooplus/20250912_220249_es2',
        'scraped/zooplus/20250912_220249_au2',
        'scraped/zooplus/20250912_220232_gb3',
        'scraped/zooplus/20250912_220232_us3',
        'scraped/zooplus/20250912_220638_ca1',
        'scraped/zooplus/20250912_220638_es4',
        'scraped/zooplus/20250912_220638_it4',
        'scraped/zooplus/20250912_224629_rescrape',  # Include completed rescrapes
        'scraped/zooplus/20250912_225238_queue_rescrape',  # Queue rescrapes
    ]
    
    total_processed = 0
    max_files = 100
    failed_products = []
    
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
    
    print("🔄 PROCESSING NEXT BATCH OF 100 FILES")
    print("=" * 60)
    print(f"Started at: {start_time.strftime('%H:%M:%S')}\n")
    
    # Get initial coverage
    print("📊 INITIAL DATABASE COVERAGE:")
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        total_before = supabase.table('foods_canonical').select('*', count='exact').execute().count
        ingredients_before = supabase.table('foods_canonical').select('*', count='exact').not_.is_('ingredients_raw', 'null').execute().count
        print(f"   Products with ingredients: {ingredients_before:,} ({ingredients_before/total_before*100:.1f}%)")
        print(f"   Starting from: {ingredients_before:,} products\n")
    except Exception as e:
        print(f"   Error checking coverage: {e}\n")
        ingredients_before = 0
    
    # Process each folder
    for folder_idx, folder in enumerate(folders_to_process, 1):
        if total_processed >= max_files:
            break
            
        print(f"📁 [{folder_idx}] {folder.split('/')[-1]}")
        processor = GCSDataProcessor(folder)
        
        # Get list of files
        files = processor.list_scraped_files()
        
        if not files:
            print(f"   No files found\n")
            continue
        
        # Process files (up to remaining limit)
        files_to_process = min(len(files), max_files - total_processed)
        print(f"   Processing {files_to_process} of {len(files)} files")
        
        folder_successful = 0
        folder_skipped = 0
        
        for i, file_path in enumerate(files[:files_to_process], 1):
            product_name = os.path.basename(file_path).replace('.json', '')
            
            # Download and check for error first
            try:
                blob = bucket.blob(file_path)
                content = blob.download_as_text()
                data = json.loads(content)
                
                if 'error' in data:
                    folder_skipped += 1
                    total_stats['skipped'] += 1
                    
                    # Add to failed products list for queue
                    if data.get('url'):
                        failed_products.append({
                            'url': data['url'],
                            'product_key': data.get('product_key', product_name.replace('_', '|')),
                            'error': data['error']
                        })
                    continue
            except Exception as e:
                continue
            
            success = processor.download_and_process(file_path)
            
            if success:
                folder_successful += 1
        
        # Update total stats
        total_processed += files_to_process
        total_stats['files_processed'] += processor.stats['files_processed']
        total_stats['products_updated'] += processor.stats['products_updated']
        total_stats['ingredients_added'] += processor.stats['ingredients_added']
        total_stats['nutrition_added'] += processor.stats['nutrition_added']
        total_stats['errors'] += processor.stats['errors']
        
        print(f"   ✅ {folder_successful} updated, ⏭️  {folder_skipped} skipped\n")
        
        if total_processed >= max_files:
            break
    
    # Final statistics
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("=" * 60)
    print(f"✅ BATCH PROCESSING COMPLETE")
    print(f"   Duration: {duration:.1f} seconds")
    print(f"   Files processed: {total_stats['files_processed']}")
    print(f"   Products updated: {total_stats['products_updated']}")
    print(f"   Ingredients added: {total_stats['ingredients_added']}")
    print(f"   Nutrition added: {total_stats['nutrition_added']}")
    print(f"   Skipped (errors): {total_stats['skipped']}")
    
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
        print(f"   📈 Coverage: {ingredients_before/total_before*100:.1f}% → {ingredients_after/total_after*100:.1f}%")
        print(f"   🚀 Gap to 95%: {int(total_after * 0.95) - ingredients_after:,} products")
        
    except Exception as e:
        print(f"   Error checking coverage: {e}")
    
    # Handle failed products - append to queue
    if failed_products:
        print(f"\n❌ FAILED PRODUCTS: {len(failed_products)}")
        
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
        print(f"   Queue size: {len(existing_urls)} total URLs")
    else:
        print(f"\n✅ NO FAILURES - All processed successfully!")

if __name__ == "__main__":
    process_next_batch()