#!/usr/bin/env python3
"""
Process first batch of 20 scraped files from GCS to test the pipeline
"""

import os
import sys
from process_gcs_scraped_data import GCSDataProcessor
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def process_first_batch():
    """Process a limited batch of scraped files from multiple folders"""
    
    # List of folders to process (from early successful scrapes)
    folders_to_process = [
        'scraped/zooplus/20250912_204926',  # 8 files
        'scraped/zooplus/20250912_200901',  # Some files
        'scraped/zooplus/20250912_202317',  # Some files
    ]
    
    total_processed = 0
    max_files = 20
    
    print("🔄 PROCESSING FIRST BATCH OF SCRAPED ZOOPLUS DATA")
    print("=" * 60)
    
    # Check database connectivity first
    print("Testing database connection...")
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        result = supabase.table('foods_canonical').select('product_key').limit(1).execute()
        print("✅ Database connection successful\n")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return
    
    # Process each folder
    for folder in folders_to_process:
        if total_processed >= max_files:
            break
            
        print(f"\n📁 Processing folder: {folder}")
        processor = GCSDataProcessor(folder)
        
        # Get list of files
        files = processor.list_scraped_files()
        
        # Process files (up to remaining limit)
        files_to_process = min(len(files), max_files - total_processed)
        
        for i, file_path in enumerate(files[:files_to_process], 1):
            print(f"\n[{total_processed + i}/{max_files}] Processing: {os.path.basename(file_path)}")
            success = processor.download_and_process(file_path)
            
            if success:
                print(f"  ✅ Successfully updated database")
            else:
                print(f"  ⚠️  No updates made")
        
        # Update count and show stats
        total_processed += files_to_process
        
        print(f"\n📊 Folder Stats:")
        print(f"  Files processed: {processor.stats['files_processed']}")
        print(f"  Products updated: {processor.stats['products_updated']}")
        print(f"  Ingredients added: {processor.stats['ingredients_added']}")
        print(f"  Nutrition added: {processor.stats['nutrition_added']}")
        print(f"  Errors: {processor.stats['errors']}")
    
    print("\n" + "=" * 60)
    print(f"✅ BATCH PROCESSING COMPLETE")
    print(f"   Total files processed: {total_processed}")
    
    # Query database to show updated coverage
    print(f"\n📊 DATABASE COVERAGE CHECK:")
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Total products
        total = supabase.table('foods_canonical').select('*', count='exact').execute().count
        
        # Products with ingredients
        with_ingredients = supabase.table('foods_canonical')\
            .select('*', count='exact')\
            .not_.is_('ingredients_raw', 'null')\
            .execute().count
            
        # Products with nutrition
        with_nutrition = supabase.table('foods_canonical')\
            .select('*', count='exact')\
            .not_.is_('protein_percent', 'null')\
            .not_.is_('fat_percent', 'null')\
            .execute().count
        
        print(f"   Total products: {total:,}")
        print(f"   With ingredients: {with_ingredients:,} ({with_ingredients/total*100:.1f}%)")
        print(f"   With nutrition: {with_nutrition:,} ({with_nutrition/total*100:.1f}%)")
        
    except Exception as e:
        print(f"   Error checking coverage: {e}")

if __name__ == "__main__":
    process_first_batch()