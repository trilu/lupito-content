#!/usr/bin/env python3
"""
Monitor AADF Image Scraping Progress
"""

import os
import json
import time
import glob
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client
from google.cloud import storage

load_dotenv()

# Initialize services
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")

# Set up GCS
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/sergiubiris/Desktop/lupito-content/secrets/gcp-sa.json'

def get_session_status():
    """Read status files from all sessions"""
    sessions = {}
    status_files = glob.glob('/tmp/aadf_session_*.json')
    
    for status_file in status_files:
        try:
            with open(status_file, 'r') as f:
                data = json.load(f)
                session_name = data['session']
                sessions[session_name] = data
        except:
            pass
    
    return sessions

def get_database_coverage():
    """Get current database coverage"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Total AADF products
    total = supabase.table('foods_canonical')\
        .select('count', count='exact')\
        .ilike('product_url', '%allaboutdogfood%')\
        .execute()
    
    # With images
    with_images = supabase.table('foods_canonical')\
        .select('count', count='exact')\
        .ilike('product_url', '%allaboutdogfood%')\
        .not_.is_('image_url', 'null')\
        .execute()
    
    return total.count, with_images.count

def get_gcs_stats():
    """Get GCS folder statistics"""
    storage_client = storage.Client()
    bucket = storage_client.bucket(GCS_BUCKET)
    
    # Count files in today's folders
    prefix = f"scraped/aadf_images/aadf_images_{datetime.now().strftime('%Y%m%d')}"
    blobs = list(bucket.list_blobs(prefix=prefix))
    
    return len(blobs)

def display_monitor():
    """Display monitoring dashboard"""
    
    print("\033[2J\033[H")  # Clear screen
    print("=" * 80)
    print("📊 AADF IMAGE SCRAPING MONITOR")
    print("=" * 80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get database coverage
    total_products, with_images = get_database_coverage()
    without_images = total_products - with_images
    coverage = (with_images / total_products * 100) if total_products > 0 else 0
    
    print(f"\n📈 DATABASE COVERAGE:")
    print(f"  Total AADF products: {total_products:,}")
    print(f"  With images: {with_images:,} ({coverage:.1f}%)")
    print(f"  Without images: {without_images:,}")
    
    # Progress bar
    bar_length = 50
    filled = int(bar_length * coverage / 100)
    bar = '█' * filled + '░' * (bar_length - filled)
    print(f"  Progress: [{bar}] {coverage:.1f}%")
    
    # Get session status
    sessions = get_session_status()
    
    if sessions:
        print(f"\n🚀 ACTIVE SESSIONS: {len(sessions)}")
        print("-" * 80)
        
        total_processed = 0
        total_found = 0
        total_errors = 0
        
        for name, session in sorted(sessions.items()):
            stats = session['stats']
            status = session['status']
            
            total_processed += stats['total']
            total_found += stats['images_found']
            total_errors += stats['errors']
            
            # Session details
            print(f"\n  Session: {name} [{status.upper()}]")
            print(f"    Processed: {stats['total']} | Found: {stats['images_found']} | Errors: {stats['errors']}")
            
            if stats['total'] > 0:
                success_rate = (stats['images_found'] / stats['total'] * 100)
                print(f"    Success rate: {success_rate:.1f}%")
            
            # Calculate rate and ETA
            if 'session_start' in stats and status == 'running':
                start_time = datetime.fromisoformat(stats['session_start'])
                elapsed = datetime.now() - start_time
                if elapsed.total_seconds() > 0 and stats['total'] > 0:
                    rate = stats['total'] / (elapsed.total_seconds() / 60)  # per minute
                    print(f"    Rate: {rate:.1f} products/min")
        
        # Overall statistics
        print("\n" + "=" * 80)
        print("📊 AGGREGATE STATISTICS:")
        print(f"  Total processed: {total_processed}")
        print(f"  Total images found: {total_found}")
        print(f"  Total errors: {total_errors}")
        
        if total_processed > 0:
            overall_success = (total_found / total_processed * 100)
            print(f"  Overall success rate: {overall_success:.1f}%")
    else:
        print("\n⚠️ No active sessions found")
    
    # GCS statistics
    gcs_files = get_gcs_stats()
    if gcs_files > 0:
        print(f"\n💾 GCS Storage: {gcs_files} files saved today")
    
    print("\n" + "=" * 80)
    print("Press Ctrl+C to exit")

def main():
    """Main monitoring loop"""
    try:
        while True:
            display_monitor()
            time.sleep(10)  # Refresh every 10 seconds
    except KeyboardInterrupt:
        print("\n\n👋 Monitor stopped")

if __name__ == "__main__":
    main()