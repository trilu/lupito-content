#!/usr/bin/env python3
"""
Monitor AADF scraping progress
"""

import os
import json
from datetime import datetime
from google.cloud import storage
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Setup
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/sergiubiris/Desktop/lupito-content/secrets/gcp-sa.json'
storage_client = storage.Client()
bucket = storage_client.bucket('lupito-content-raw-eu')
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY'))

print("🔍 AADF SCRAPING PROGRESS MONITOR")
print("=" * 60)

# Check database coverage
response = supabase.table('foods_canonical')\
    .select('product_key', count='exact')\
    .ilike('product_url', '%allaboutdogfood%')\
    .not_.is_('image_url', 'null')\
    .execute()
with_images = response.count

response = supabase.table('foods_canonical')\
    .select('product_key', count='exact')\
    .ilike('product_url', '%allaboutdogfood%')\
    .execute()
total = response.count

print(f"\n📊 DATABASE STATUS:")
print(f"  Total AADF products: {total}")
print(f"  With images: {with_images}")
print(f"  Without images: {total - with_images}")
print(f"  Coverage: {with_images/total*100:.1f}%")

# Check GCS sessions from today
today = datetime.now().strftime('%Y%m%d')
prefix = f'scraped/aadf_images/aadf_images_{today}'

sessions = {}
blobs = bucket.list_blobs(prefix=prefix)
for blob in blobs:
    parts = blob.name.split('/')
    if len(parts) >= 3:
        session_name = parts[2]
        if session_name not in sessions:
            sessions[session_name] = 0
        sessions[session_name] += 1

print(f"\n☁️ GCS SESSIONS TODAY:")
total_files = 0
for session, count in sorted(sessions.items()):
    print(f"  {session}: {count} files")
    total_files += count
print(f"  Total files scraped today: {total_files}")

# Check running processes
import subprocess
result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
running = [line for line in result.stdout.split('\n') if 'scrape_aadf_images_session' in line and 'grep' not in line]
print(f"\n🚀 RUNNING PROCESSES: {len(running)}")
for proc in running:
    parts = proc.split()
    if len(parts) > 10:
        # Extract session name from command
        for i, part in enumerate(parts):
            if part == '--session' and i + 1 < len(parts):
                print(f"  - {parts[i+1]} session active")
                break

# Estimate completion
if len(running) > 0 and total_files > 0:
    elapsed_hours = 2  # Approximate
    rate = total_files / elapsed_hours
    remaining = total - with_images
    eta_hours = remaining / rate if rate > 0 else 0
    print(f"\n⏱️ ESTIMATES:")
    print(f"  Current rate: ~{rate:.0f} products/hour")
    print(f"  Remaining: {remaining} products")
    print(f"  ETA: ~{eta_hours:.1f} hours")

print("\n" + "=" * 60)