#!/usr/bin/env python3
"""
Start orchestrator for scraping new Zooplus products
Launches multiple parallel scraping sessions
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

def get_coverage_stats():
    """Get current coverage statistics"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Total products
    total = supabase.table('foods_canonical').select('count', count='exact').execute()
    
    # Products with ingredients
    with_ingredients = supabase.table('foods_canonical').select('count', count='exact')\
        .not_.is_('ingredients_raw', 'null').execute()
    
    # Zooplus products without ingredients
    zooplus_missing = supabase.table('foods_canonical').select('count', count='exact')\
        .ilike('product_url', '%zooplus%')\
        .is_('ingredients_raw', 'null').execute()
    
    coverage_pct = (with_ingredients.count / total.count * 100) if total.count > 0 else 0
    
    return {
        'total': total.count,
        'with_ingredients': with_ingredients.count,
        'coverage_pct': coverage_pct,
        'zooplus_missing': zooplus_missing.count
    }

def main():
    print("🚀 STARTING ZOOPLUS SCRAPING ORCHESTRATOR")
    print("=" * 60)
    
    # Get current status
    stats = get_coverage_stats()
    print(f"📊 Current Status:")
    print(f"   Total products: {stats['total']:,}")
    print(f"   With ingredients: {stats['with_ingredients']:,} ({stats['coverage_pct']:.1f}%)")
    print(f"   Zooplus to scrape: {stats['zooplus_missing']:,}")
    print()
    
    if stats['zooplus_missing'] == 0:
        print("✅ No Zooplus products need scraping!")
        return
    
    print("🎯 Target: Scrape ingredients and nutrition for all Zooplus products")
    print(f"   Estimated time: {stats['zooplus_missing'] * 2 / 60:.1f} minutes (at 2 sec/product)")
    print()
    
    # Start the orchestrator
    print("Starting orchestrator with 5 parallel sessions...")
    print("Sessions will use different country codes to avoid rate limiting")
    print()
    
    # Launch the orchestrator
    cmd = ["python", "scripts/scraper_orchestrator.py"]
    
    print(f"Running: {' '.join(cmd)}")
    print("=" * 60)
    
    try:
        # Start orchestrator
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        print("✅ Orchestrator started (PID: {})".format(process.pid))
        print()
        print("📊 Monitor progress with:")
        print("   python scripts/orchestrator_dashboard.py")
        print()
        print("Or continuously:")
        print("   watch -n 30 'python scripts/orchestrator_dashboard.py'")
        print()
        print("=" * 60)
        
        # Show initial output for 30 seconds
        start_time = time.time()
        while time.time() - start_time < 30:
            line = process.stdout.readline()
            if line:
                print(line.rstrip())
            elif process.poll() is not None:
                # Process ended
                break
            else:
                time.sleep(0.1)
        
        if process.poll() is None:
            print()
            print("✅ Orchestrator is running in background")
            print("   PID:", process.pid)
            print()
            print("To stop the orchestrator:")
            print(f"   kill {process.pid}")
            print()
            print("To see all orchestrator processes:")
            print("   ps aux | grep orchestrator")
        else:
            print()
            print("⚠️ Orchestrator exited with code:", process.returncode)
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
        if process and process.poll() is None:
            print(f"Stopping orchestrator (PID: {process.pid})...")
            process.terminate()
            time.sleep(2)
            if process.poll() is None:
                process.kill()
            print("✅ Orchestrator stopped")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()