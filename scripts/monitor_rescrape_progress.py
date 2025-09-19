#!/usr/bin/env python3
"""
Monitor the progress of Zooplus rescraping operation
"""

import os
import subprocess
import time
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")

def get_database_stats():
    """Get current database statistics"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Total Zooplus products
    total_response = supabase.table('foods_canonical').select('count', count='exact').ilike('product_url', '%zooplus.com%').execute()
    
    # With ingredients
    with_ingr_response = supabase.table('foods_canonical').select('count', count='exact').ilike('product_url', '%zooplus.com%').not_.is_('ingredients_raw', 'null').execute()
    
    # Missing ingredients
    missing_ingr_response = supabase.table('foods_canonical').select('count', count='exact').ilike('product_url', '%zooplus.com%').is_('ingredients_raw', 'null').execute()
    
    return {
        'total': total_response.count,
        'with_ingredients': with_ingr_response.count,
        'missing_ingredients': missing_ingr_response.count,
        'coverage': with_ingr_response.count / total_response.count * 100 if total_response.count > 0 else 0
    }

def count_gcs_files():
    """Count files in rescrape folders"""
    try:
        # Count files in rescrape folders
        result = subprocess.run([
            'gsutil', 'ls', 
            f'gs://{GCS_BUCKET}/scraped/zooplus/rescrape_zooplus_*/*.json'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            files = result.stdout.strip().split('\n') if result.stdout.strip() else []
            return len(files)
    except:
        pass
    return 0

def count_running_scrapers():
    """Count running scraper processes"""
    try:
        result = subprocess.run([
            'ps', 'aux'
        ], capture_output=True, text=True)
        
        lines = result.stdout.split('\n')
        scrapers = [l for l in lines if 'rescrape_zooplus' in l and 'python' in l]
        return len(scrapers)
    except:
        return 0

def main():
    print("\n" + "="*60)
    print("📊 ZOOPLUS RESCRAPING PROGRESS MONITOR")
    print("="*60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get stats
    db_stats = get_database_stats()
    gcs_files = count_gcs_files()
    running_scrapers = count_running_scrapers()
    
    print("\n📈 DATABASE STATUS:")
    print(f"  Total Zooplus products: {db_stats['total']:,}")
    print(f"  With ingredients: {db_stats['with_ingredients']:,} ({db_stats['coverage']:.1f}%)")
    print(f"  Missing ingredients: {db_stats['missing_ingredients']:,}")
    
    print("\n⚡ SCRAPING PROGRESS:")
    print(f"  Running scrapers: {running_scrapers}")
    print(f"  Files scraped: {gcs_files}")
    
    if gcs_files > 0:
        # Estimate progress
        target = 1627  # Products to rescrape
        progress = min(gcs_files / target * 100, 100)
        print(f"  Progress: {progress:.1f}% ({gcs_files}/{target})")
        
        # Estimate time remaining
        if running_scrapers > 0:
            remaining = target - gcs_files
            # Assuming ~20 seconds per product with 5 scrapers
            minutes_remaining = (remaining * 20) / (running_scrapers * 60)
            print(f"  Est. time remaining: {minutes_remaining:.0f} minutes")
    
    print("\n💾 GCS FOLDERS:")
    # List recent rescrape folders
    try:
        result = subprocess.run([
            'gsutil', 'ls', 
            f'gs://{GCS_BUCKET}/scraped/zooplus/'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            folders = result.stdout.strip().split('\n')
            rescrape_folders = [f for f in folders if 'rescrape_zooplus_' in f]
            for folder in rescrape_folders[-5:]:  # Show last 5
                print(f"  {folder}")
    except:
        pass
    
    print("\n" + "-"*60)
    
    # Calculate improvement
    initial_coverage = 55.3  # From earlier analysis
    improvement = db_stats['coverage'] - initial_coverage
    if improvement > 0:
        print(f"✨ Coverage improved by {improvement:.1f} percentage points!")
    
    if db_stats['coverage'] >= 85:
        print("🎉 TARGET ACHIEVED! Coverage exceeds 85%!")
    elif db_stats['coverage'] >= 80:
        print("✅ Good progress! Coverage exceeds 80%")
    elif db_stats['coverage'] >= 70:
        print("📈 Making progress! Coverage exceeds 70%")

if __name__ == "__main__":
    main()