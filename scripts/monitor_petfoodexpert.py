#!/usr/bin/env python3
"""
Monitor PetFoodExpert scraping progress
"""

import os
import subprocess
from datetime import datetime, timedelta
from google.cloud import storage
from dotenv import load_dotenv
import json

load_dotenv()

def monitor():
    """Monitor PetFoodExpert scraping progress"""
    
    # Set up GCS
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/sergiubiris/Desktop/lupito-content/secrets/gcp-sa.json'
    client = storage.Client()
    bucket = client.bucket('lupito-content-raw-eu')
    
    print("\n" + "="*70)
    print("📊 PETFOODEXPERT SCRAPING MONITOR")
    print("="*70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get all PetFoodExpert folders
    prefix = 'scraped/petfoodexpert/'
    all_blobs = list(bucket.list_blobs(prefix=prefix))
    
    # Group by session
    sessions = {}
    total_files = 0
    total_valid = 0
    
    for blob in all_blobs:
        folder = '/'.join(blob.name.split('/')[:3])
        if folder not in sessions:
            sessions[folder] = {
                'count': 0,
                'valid': 0,
                'errors': 0,
                'latest': None,
                'start_time': None
            }
        
        sessions[folder]['count'] += 1
        total_files += 1
        
        # Parse timestamp from folder name
        if not sessions[folder]['start_time']:
            parts = folder.split('_')
            if len(parts) >= 3:
                date_str = parts[1]  # YYYYMMDD
                time_str = parts[2]  # HHMMSS
                try:
                    hour = int(time_str[:2])
                    minute = int(time_str[2:4])
                    second = int(time_str[4:6])
                    sessions[folder]['start_time'] = datetime.now().replace(
                        hour=hour, minute=minute, second=second, microsecond=0
                    )
                except:
                    pass
        
        # Check content
        try:
            content = blob.download_as_text()
            data = json.loads(content)
            if 'ingredients_raw' in data:
                sessions[folder]['valid'] += 1
                total_valid += 1
            elif 'error' in data:
                sessions[folder]['errors'] += 1
        except:
            pass
        
        # Track latest file
        if not sessions[folder]['latest'] or blob.time_created > sessions[folder]['latest']:
            sessions[folder]['latest'] = blob.time_created
    
    # Display session statistics
    print("\n📁 SESSION PROGRESS:")
    print("-" * 70)
    
    # Sort sessions by name
    for folder in sorted(sessions.keys()):
        info = sessions[folder]
        session_name = folder.split('/')[-1]
        
        # Calculate elapsed time and rate
        elapsed_str = "unknown"
        rate_str = "N/A"
        if info['start_time']:
            elapsed = datetime.now() - info['start_time']
            elapsed_str = str(elapsed).split('.')[0]
            if elapsed.total_seconds() > 0:
                rate = info['count'] / (elapsed.total_seconds() / 3600)
                rate_str = f"{rate:.1f}/hour"
        
        # Last activity
        last_activity = "unknown"
        if info['latest']:
            age = (datetime.now(info['latest'].tzinfo) - info['latest']).total_seconds()
            if age < 60:
                last_activity = f"{int(age)}s ago"
            else:
                last_activity = f"{int(age/60)}m ago"
        
        # Success rate
        success_rate = (info['valid'] / info['count'] * 100) if info['count'] > 0 else 0
        
        print(f"\n  {session_name}:")
        print(f"    Files: {info['count']:4} | Valid: {info['valid']:4} | Errors: {info['errors']:4}")
        print(f"    Success rate: {success_rate:.1f}%")
        print(f"    Rate: {rate_str} | Elapsed: {elapsed_str}")
        print(f"    Last activity: {last_activity}")
    
    # Overall statistics
    print("\n" + "="*70)
    print("📈 OVERALL STATISTICS:")
    print("-" * 70)
    
    print(f"  Total files scraped: {total_files}")
    print(f"  With ingredients: {total_valid}")
    print(f"  Overall success rate: {(total_valid/total_files*100):.1f}%" if total_files > 0 else "N/A")
    
    # Progress toward goal
    goal = 3292
    progress = min(total_files / goal * 100, 100)
    bar_length = 50
    filled = int(bar_length * progress / 100)
    bar = '█' * filled + '░' * (bar_length - filled)
    
    print(f"\n  Progress: [{bar}] {total_files}/{goal}")
    print(f"  Completion: {progress:.1f}%")
    
    # Estimate completion time
    if len(sessions) > 0 and total_files > 0:
        # Get average rate across all sessions
        total_elapsed = 0
        active_sessions = 0
        for info in sessions.values():
            if info['start_time'] and info['count'] > 0:
                elapsed = (datetime.now() - info['start_time']).total_seconds()
                if elapsed > 0 and elapsed < 7200:  # Only count recent sessions
                    total_elapsed += elapsed
                    active_sessions += 1
        
        if active_sessions > 0 and total_elapsed > 0:
            avg_rate = total_files / (total_elapsed / active_sessions) * active_sessions
            if avg_rate > 0:
                remaining = goal - total_files
                eta_seconds = remaining / avg_rate
                eta = datetime.now() + timedelta(seconds=eta_seconds)
                print(f"\n  Estimated completion: {eta.strftime('%H:%M')} ({int(eta_seconds/3600)} hours)")
    
    # Check running processes
    print("\n🚀 ACTIVE PROCESSES:")
    print("-" * 70)
    
    result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
    processes = result.stdout.split('\n')
    scrapers = [p for p in processes if 'petfoodexpert' in p and 'grep' not in p and 'monitor' not in p]
    
    print(f"  Active scrapers: {len(scrapers)}")
    for scraper in scrapers:
        parts = scraper.split()
        if len(parts) > 1:
            pid = parts[1]
            # Try to extract session info
            if '--session' in scraper:
                idx = scraper.index('--session')
                session = scraper[idx:].split()[1] if len(scraper[idx:].split()) > 1 else 'unknown'
                print(f"    PID {pid}: session {session}")
            else:
                print(f"    PID {pid}")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    monitor()