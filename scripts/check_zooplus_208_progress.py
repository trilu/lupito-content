#!/usr/bin/env python3
"""
Check progress of the 208 Zooplus scraper
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv
from google.cloud import storage
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")

# Initialize clients
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
storage_client = storage.Client()
bucket = storage_client.bucket(GCS_BUCKET)

# Check GCS for scraped files
print("Checking GCS for scraped files...")
prefix = "scraped/zooplus_retry/"

# List all folders in zooplus_retry
folders = set()
for blob in bucket.list_blobs(prefix=prefix):
    path_parts = blob.name.replace(prefix, '').split('/')
    if len(path_parts) > 1:
        folders.add(path_parts[0])

if folders:
    latest_folder = sorted(folders)[-1]
    print(f"\nLatest session: {latest_folder}")

    # Count files in latest session
    session_prefix = f"{prefix}{latest_folder}/"
    file_count = 0
    for blob in bucket.list_blobs(prefix=session_prefix):
        if blob.name.endswith('.json'):
            file_count += 1

    print(f"Files uploaded: {file_count}")

# Check database for updates
print("\nChecking database for recent updates...")

# Get products updated in last hour
response = supabase.table('foods_canonical').select(
    'product_key, product_name, ingredients_source, updated_at'
).eq('source', 'zooplus_csv_import')\
.eq('ingredients_source', 'zooplus_retry')\
.gte('updated_at', datetime.now().replace(hour=datetime.now().hour-1).isoformat())\
.execute()

recent_updates = response.data if response.data else []
print(f"Products updated in last hour: {len(recent_updates)}")

# Check PENDING status
response = supabase.table('foods_published_preview').select(
    'count'
).eq('source', 'zooplus_csv_import')\
.eq('allowlist_status', 'PENDING')\
.execute()

if response.data:
    pending_count = response.data[0]['count'] if response.data else 0
    print(f"Zooplus products still PENDING: {pending_count}")
    print(f"Progress: {208 - pending_count}/208 processed")

# Check local stats file if exists
import glob
stats_files = glob.glob('zooplus_208_stats_*.json')
if stats_files:
    latest_stats = sorted(stats_files)[-1]
    with open(latest_stats, 'r') as f:
        stats = json.load(f)
    print(f"\nLocal stats file: {latest_stats}")
    print(f"Success: {stats.get('success', 0)}")
    print(f"With ingredients: {stats.get('with_ingredients', 0)}")
    print(f"Pattern 8 success: {stats.get('pattern_8_success', 0)}")