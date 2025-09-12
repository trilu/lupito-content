#!/usr/bin/env python3
"""
Simple live monitor for scraping progress
Run: source venv/bin/activate && python scripts/simple_monitor.py
"""

import os
import time
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

# Load environment
load_dotenv()

def live_monitor():
    supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY'))
    
    print("🔍 LIVE SCRAPING MONITOR")
    print("Press Ctrl+C to stop")
    print("-" * 60)
    
    try:
        while True:
            # Clear screen
            os.system('clear' if os.name == 'posix' else 'cls')
            
            # Get stats
            total = supabase.table('foods_canonical').select('*', count='exact').execute().count
            ingredients = supabase.table('foods_canonical').select('*', count='exact').not_.is_('ingredients_raw', 'null').execute().count
            complete_nutrition = supabase.table('foods_canonical').select('*', count='exact')\
                .not_.is_('protein_percent', 'null')\
                .not_.is_('fat_percent', 'null')\
                .not_.is_('fiber_percent', 'null')\
                .not_.is_('ash_percent', 'null')\
                .not_.is_('moisture_percent', 'null').execute().count
            
            # Calculate percentages
            ing_pct = ingredients/total*100
            nutr_pct = complete_nutrition/total*100
            
            # Calculate gaps to 95%
            ing_goal = int(total * 0.95)
            nutr_goal = int(total * 0.95)
            ing_gap = max(0, ing_goal - ingredients)
            nutr_gap = max(0, nutr_goal - complete_nutrition)
            
            # Display
            print(f"🔍 LIVE MONITOR - {datetime.now().strftime('%H:%M:%S')}")
            print("=" * 50)
            print(f"Total Products: {total:,}")
            print()
            print(f"📋 INGREDIENTS")
            print(f"   Current: {ingredients:,} ({ing_pct:.1f}%)")
            print(f"   Goal: {ing_goal:,} (95%)")
            print(f"   Gap: {ing_gap:,} products")
            print()
            print(f"🍖 COMPLETE NUTRITION")
            print(f"   Current: {complete_nutrition:,} ({nutr_pct:.1f}%)")
            print(f"   Goal: {nutr_goal:,} (95%)")
            print(f"   Gap: {nutr_gap:,} products")
            print()
            
            # Progress bars
            ing_bar = "█" * int(ing_pct/2) + "░" * (50-int(ing_pct/2))
            nutr_bar = "█" * int(nutr_pct/2) + "░" * (50-int(nutr_pct/2))
            
            print("📊 PROGRESS TO 95%")
            print(f"Ingredients:  [{ing_bar}] {ing_pct:5.1f}%")
            print(f"Nutrition:    [{nutr_bar}] {nutr_pct:5.1f}%")
            print()
            print("Refreshing in 30 seconds...")
            
            time.sleep(30)
            
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")

if __name__ == "__main__":
    live_monitor()