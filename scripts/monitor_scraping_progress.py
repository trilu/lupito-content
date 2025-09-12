#!/usr/bin/env python3
"""
Monitor scraping progress toward 95% coverage goal
"""

import os
import time
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
from google.cloud import storage

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")

def check_current_coverage():
    """Check current coverage statistics"""
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Total products
    total = supabase.table('foods_canonical').select('*', count='exact').execute().count
    
    # Ingredients
    ingredients = supabase.table('foods_canonical').select('*', count='exact')\
        .not_.is_('ingredients_raw', 'null').execute().count
    
    # Complete nutrition (all 5 nutrients)
    complete_nutrition = supabase.table('foods_canonical').select('*', count='exact')\
        .not_.is_('protein_percent', 'null')\
        .not_.is_('fat_percent', 'null')\
        .not_.is_('fiber_percent', 'null')\
        .not_.is_('ash_percent', 'null')\
        .not_.is_('moisture_percent', 'null').execute().count
    
    # Individual nutrients
    protein = supabase.table('foods_canonical').select('*', count='exact')\
        .not_.is_('protein_percent', 'null').execute().count
    fat = supabase.table('foods_canonical').select('*', count='exact')\
        .not_.is_('fat_percent', 'null').execute().count
    fiber = supabase.table('foods_canonical').select('*', count='exact')\
        .not_.is_('fiber_percent', 'null').execute().count
    ash = supabase.table('foods_canonical').select('*', count='exact')\
        .not_.is_('ash_percent', 'null').execute().count
    moisture = supabase.table('foods_canonical').select('*', count='exact')\
        .not_.is_('moisture_percent', 'null').execute().count
    
    return {
        'total': total,
        'ingredients': {'count': ingredients, 'percent': ingredients/total*100},
        'complete_nutrition': {'count': complete_nutrition, 'percent': complete_nutrition/total*100},
        'nutrients': {
            'protein': {'count': protein, 'percent': protein/total*100},
            'fat': {'count': fat, 'percent': fat/total*100},
            'fiber': {'count': fiber, 'percent': fiber/total*100},
            'ash': {'count': ash, 'percent': ash/total*100},
            'moisture': {'count': moisture, 'percent': moisture/total*100}
        }
    }

def check_recent_gcs_activity():
    """Check recent GCS scraping activity"""
    
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(GCS_BUCKET)
        
        # List recent folders
        recent_folders = set()
        blobs = bucket.list_blobs(prefix="scraped/zooplus/", delimiter="/")
        
        for blob in blobs:
            if blob.name.endswith('.json'):
                folder = '/'.join(blob.name.split('/')[:-1])
                recent_folders.add(folder)
        
        recent_folders = sorted(recent_folders)[-5:]  # Last 5 sessions
        
        session_stats = {}
        for folder in recent_folders:
            files = list(bucket.list_blobs(prefix=folder + '/'))
            session_stats[folder] = len([f for f in files if f.name.endswith('.json')])
        
        return session_stats
        
    except Exception as e:
        return {'error': str(e)}

def monitor_dashboard():
    """Display monitoring dashboard"""
    
    while True:
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("🔍 SCRAPING PROGRESS MONITOR")
        print("=" * 80)
        print(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Get current stats
        stats = check_current_coverage()
        total = stats['total']
        
        print("📊 CURRENT DATABASE COVERAGE")
        print("-" * 50)
        print(f"Total products: {total:,}")
        print()
        
        # Ingredients progress
        ing_count = stats['ingredients']['count']
        ing_pct = stats['ingredients']['percent']
        ing_goal = int(total * 0.95)
        ing_gap = max(0, ing_goal - ing_count)
        
        print(f"🥘 INGREDIENTS")
        print(f"  Current: {ing_count:,} / {total:,} ({ing_pct:.1f}%)")
        print(f"  Goal (95%): {ing_goal:,}")
        print(f"  Gap: {ing_gap:,} products")
        print(f"  Progress: {'●' * int(ing_pct/5)}{'○' * (20-int(ing_pct/5))} {ing_pct:.1f}%")
        print()
        
        # Complete nutrition progress
        nutr_count = stats['complete_nutrition']['count']
        nutr_pct = stats['complete_nutrition']['percent']
        nutr_goal = int(total * 0.95)
        nutr_gap = max(0, nutr_goal - nutr_count)
        
        print(f"🍖 COMPLETE NUTRITION (All 5 nutrients)")
        print(f"  Current: {nutr_count:,} / {total:,} ({nutr_pct:.1f}%)")
        print(f"  Goal (95%): {nutr_goal:,}")
        print(f"  Gap: {nutr_gap:,} products")
        print(f"  Progress: {'●' * int(nutr_pct/5)}{'○' * (20-int(nutr_pct/5))} {nutr_pct:.1f}%")
        print()
        
        # Individual nutrients
        print(f"📈 INDIVIDUAL NUTRIENTS")
        nutrients = stats['nutrients']
        for name, data in nutrients.items():
            pct = data['percent']
            bar = '●' * int(pct/5) + '○' * (20-int(pct/5))
            print(f"  {name.capitalize():8}: {data['count']:5,} ({pct:5.1f}%) {bar}")
        print()
        
        # GCS activity
        print(f"☁️ RECENT SCRAPING SESSIONS (GCS)")
        print("-" * 50)
        gcs_stats = check_recent_gcs_activity()
        
        if 'error' not in gcs_stats:
            if gcs_stats:
                for folder, file_count in gcs_stats.items():
                    session_id = folder.split('/')[-1]
                    print(f"  {session_id}: {file_count} files")
            else:
                print("  No recent sessions found")
        else:
            print(f"  Error: {gcs_stats['error']}")
        
        print()
        print("🎯 PROGRESS TO 95% GOAL")
        print("-" * 50)
        
        total_gap = ing_gap + nutr_gap
        print(f"Ingredients gap: {ing_gap:,}")
        print(f"Complete nutrition gap: {nutr_gap:,}")
        print(f"Total work remaining: ~{max(ing_gap, nutr_gap):,} products to scrape")
        
        # Estimate time
        if max(ing_gap, nutr_gap) > 0:
            products_per_hour = 120  # Conservative estimate with delays
            hours_needed = max(ing_gap, nutr_gap) / products_per_hour
            days_needed = hours_needed / 8  # 8 hours per day
            
            print()
            print(f"⏱️ TIME ESTIMATE")
            print(f"  At 120 products/hour: {hours_needed:.1f} hours")
            print(f"  At 8 hours/day: {days_needed:.1f} days")
        
        print()
        print("Press Ctrl+C to exit monitoring")
        
        try:
            time.sleep(30)  # Update every 30 seconds
        except KeyboardInterrupt:
            print("\nMonitoring stopped.")
            break

if __name__ == "__main__":
    monitor_dashboard()