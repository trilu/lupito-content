#!/usr/bin/env python3
"""
Process batch of 50 scraped files from GCS
"""

import os
import sys
from process_gcs_scraped_data import GCSDataProcessor
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def process_batch_50():
    """Process 50 scraped files from GCS"""
    
    # Get more folders to process
    folders_to_process = [
        'scraped/zooplus/20250912_202523',
        'scraped/zooplus/20250912_203336',
        'scraped/zooplus/20250912_204659',
        'scraped/zooplus/20250912_210045',
        'scraped/zooplus/20250912_210554',
        'scraped/zooplus/20250912_210851_us',
        'scraped/zooplus/20250912_210855_gb',
        'scraped/zooplus/20250912_210859_de',
        'scraped/zooplus/20250912_211713_ca1',
        'scraped/zooplus/20250912_211713_de1',
        'scraped/zooplus/20250912_211713_fr1',
        'scraped/zooplus/20250912_211713_gb1',
        'scraped/zooplus/20250912_211713_us1',
    ]
    
    total_processed = 0
    max_files = 50
    total_stats = {
        'files_processed': 0,
        'products_updated': 0,
        'ingredients_added': 0,
        'nutrition_added': 0,
        'errors': 0,
        'skipped': 0
    }
    
    start_time = datetime.now()
    
    print("🔄 PROCESSING BATCH OF 50 SCRAPED ZOOPLUS FILES")
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
                from google.cloud import storage
                storage_client = storage.Client()
                bucket = storage_client.bucket('lupito-content-raw-eu')
                blob = bucket.blob(file_path)
                content = blob.download_as_text()
                import json
                data = json.loads(content)
                
                if 'error' in data:
                    print(f" ⏭️  Skip (error)")
                    total_stats['skipped'] += 1
                    continue
            except:
                pass
            
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
    print(f"   Skipped: {total_stats['skipped']}")
    print(f"   Errors: {total_stats['errors']}")
    
    if total_stats['files_processed'] > 0:
        success_rate = (total_stats['products_updated'] / total_stats['files_processed']) * 100
        print(f"   Success rate: {success_rate:.1f}%")
        print(f"   Processing speed: {total_stats['files_processed']/duration*60:.1f} files/minute")
    
    # Query database to show updated coverage
    print(f"\n📊 UPDATED DATABASE COVERAGE:")
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Total products
        total_after = supabase.table('foods_canonical').select('*', count='exact').execute().count
        
        # Products with ingredients
        ingredients_after = supabase.table('foods_canonical')\
            .select('*', count='exact')\
            .not_.is_('ingredients_raw', 'null')\
            .execute().count
            
        # Products with complete nutrition
        nutrition_after = supabase.table('foods_canonical')\
            .select('*', count='exact')\
            .not_.is_('protein_percent', 'null')\
            .not_.is_('fat_percent', 'null')\
            .not_.is_('fiber_percent', 'null')\
            .not_.is_('ash_percent', 'null')\
            .not_.is_('moisture_percent', 'null')\
            .execute().count
        
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

if __name__ == "__main__":
    process_batch_50()