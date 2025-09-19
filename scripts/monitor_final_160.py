#!/usr/bin/env python3
"""
Monitor progress of final 160 Zooplus products scraping
"""

import os
import subprocess
import time
from datetime import datetime
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()

def monitor():
    """Monitor scraping progress"""
    
    # Set up GCS
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/sergiubiris/Desktop/lupito-content/secrets/gcp-sa.json'
    client = storage.Client()
    bucket = client.bucket('lupito-content-raw-eu')
    
    print("\n" + "="*60)
    print("📊 FINAL 160 PRODUCTS SCRAPING MONITOR")
    print("="*60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check running processes
    result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
    scrapers = [line for line in result.stdout.split('\n') if 'scrape_final_160' in line and 'grep' not in line]
    
    print(f"\n🚀 Active Scrapers: {len(scrapers)}")
    for scraper in scrapers:
        parts = scraper.split()
        if '--session' in scraper:
            session_idx = scraper.index('--session')
            session = scraper.split()[session_idx+1] if session_idx < len(scraper.split())-1 else 'unknown'
            print(f"   • Session {session} (PID: {parts[1]})")
    
    # Check GCS folders
    print("\n☁️ GCS Progress:")
    prefix = 'scraped/zooplus/final_160_'
    blobs = list(bucket.list_blobs(prefix=prefix))
    
    folders = {}
    for blob in blobs:
        folder = '/'.join(blob.name.split('/')[:3])
        if folder not in folders:
            folders[folder] = 0
        folders[folder] += 1
    
    total_files = 0
    for folder in sorted(folders.keys())[-5:]:  # Show last 5 sessions
        timestamp = folder.split('_')[3] + '_' + folder.split('_')[4]
        session = folder.split('_')[5] if len(folder.split('_')) > 5 else 'unknown'
        print(f"   • {timestamp} ({session}): {folders[folder]} files")
        total_files += folders[folder]
    
    # Calculate progress
    print(f"\n📊 Progress Summary:")
    print(f"   Total products to scrape: 160")
    print(f"   Files in GCS: {total_files}")
    
    if total_files > 0:
        # Estimate based on files (some might be errors)
        estimated_complete = min(total_files, 160)
        progress_pct = (estimated_complete / 160) * 100
        print(f"   Estimated progress: {estimated_complete}/160 ({progress_pct:.1f}%)")
        
        # Progress bar
        bar_length = 40
        filled = int(bar_length * progress_pct / 100)
        bar = '█' * filled + '░' * (bar_length - filled)
        print(f"   [{bar}] {progress_pct:.1f}%")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    monitor()