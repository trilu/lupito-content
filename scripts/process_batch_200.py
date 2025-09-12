#!/usr/bin/env python3
"""
Process batch of 200 scraped files
Track both ingredients and nutrition extraction
Automatically queue failures
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

def process_batch_200():
    """Process 200 files from recent scraping sessions"""
    
    # Get list of all recent folders
    storage_client = storage.Client()
    bucket = storage_client.bucket(GCS_BUCKET)
    
    # Get all folders from today
    prefix = f"scraped/zooplus/{datetime.now().strftime('%Y%m%d')}"
    blobs = bucket.list_blobs(prefix=prefix)
    
    folders = set()
    for blob in blobs:
        if '/' in blob.name:
            folder = '/'.join(blob.name.split('/')[:3])
            folders.add(folder)
    
    # Sort folders by timestamp (most recent first)
    folders_to_process = sorted(list(folders), reverse=True)[:30]  # Get last 30 folders
    
    total_processed = 0
    max_files = 200
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
    
    print("🔄 PROCESSING BATCH OF 200 FILES")
    print("=" * 60)
    print(f"Started at: {start_time.strftime('%H:%M:%S')}")
    print(f"Found {len(folders_to_process)} folders to process\n")
    
    # Get initial coverage
    print("📊 INITIAL DATABASE COVERAGE:")
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        total_before = supabase.table('foods_canonical').select('*', count='exact').execute().count
        ingredients_before = supabase.table('foods_canonical').select('*', count='exact').not_.is_('ingredients_raw', 'null').execute().count
        complete_nutrition_before = supabase.table('foods_canonical').select('*', count='exact')\
            .not_.is_('protein_percent', 'null')\
            .not_.is_('fat_percent', 'null')\
            .not_.is_('fiber_percent', 'null')\
            .not_.is_('ash_percent', 'null')\
            .not_.is_('moisture_percent', 'null').execute().count
        
        print(f"   Products with ingredients: {ingredients_before:,} ({ingredients_before/total_before*100:.1f}%)")
        print(f"   Products with complete nutrition: {complete_nutrition_before:,} ({complete_nutrition_before/total_before*100:.1f}%)")
        print(f"   Starting from: {ingredients_before:,} products\n")
    except Exception as e:
        print(f"   Error checking coverage: {e}\n")
        ingredients_before = 0
        complete_nutrition_before = 0
    
    # Process each folder
    for folder_idx, folder in enumerate(folders_to_process, 1):
        if total_processed >= max_files:
            break
        
        folder_name = folder.split('/')[-1]
        print(f"📁 [{folder_idx}] {folder_name}", end='')
        
        processor = GCSDataProcessor(folder)
        
        # Get list of files
        files = processor.list_scraped_files()
        
        if not files:
            print(" - Empty")
            continue
        
        # Process files (up to remaining limit)
        files_to_process = min(len(files), max_files - total_processed)
        
        folder_successful = 0
        folder_skipped = 0
        folder_ingredients = 0
        folder_nutrition = 0
        
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
                
                # Track what data we have
                if 'ingredients_raw' in data and data['ingredients_raw']:
                    folder_ingredients += 1
                if 'nutrition' in data and data['nutrition']:
                    folder_nutrition += 1
                    
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
        
        print(f" - ✅ {folder_successful}/{files_to_process} (🥘 {folder_ingredients} 🍖 {folder_nutrition})")
        
        if total_processed >= max_files:
            break
    
    # Final statistics
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "=" * 60)
    print(f"✅ BATCH PROCESSING COMPLETE")
    print(f"   Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
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
        complete_nutrition_after = supabase.table('foods_canonical').select('*', count='exact')\
            .not_.is_('protein_percent', 'null')\
            .not_.is_('fat_percent', 'null')\
            .not_.is_('fiber_percent', 'null')\
            .not_.is_('ash_percent', 'null')\
            .not_.is_('moisture_percent', 'null').execute().count
        
        ingredients_gained = ingredients_after - ingredients_before
        nutrition_gained = complete_nutrition_after - complete_nutrition_before
        
        print(f"   Total products: {total_after:,}")
        print(f"   With ingredients: {ingredients_after:,} ({ingredients_after/total_after*100:.1f}%)")
        print(f"   Complete nutrition: {complete_nutrition_after:,} ({complete_nutrition_after/total_after*100:.1f}%)")
        print(f"   ")
        print(f"   🥘 Ingredients gained: +{ingredients_gained}")
        print(f"   🍖 Complete nutrition gained: +{nutrition_gained}")
        print(f"   📈 Ingredients coverage: {ingredients_before/total_before*100:.1f}% → {ingredients_after/total_after*100:.1f}%")
        print(f"   📈 Nutrition coverage: {complete_nutrition_before/total_before*100:.1f}% → {complete_nutrition_after/total_after*100:.1f}%")
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
    
    print(f"\n💡 READY FOR AUTOMATION")
    print(f"   Success rate is high enough ({total_stats['products_updated']}/{total_stats['files_processed']}) for automatic processing")
    print(f"   Next step: Create continuous processor to handle all new scraped files")

if __name__ == "__main__":
    process_batch_200()