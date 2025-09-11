#!/usr/bin/env python3
"""Check schema of foods_published table"""

import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    print("ERROR: Supabase credentials not found")
    exit(1)

print("Connecting to Supabase...")
supabase = create_client(supabase_url, supabase_key)

# Get one row to see the schema
print("Fetching sample row to check schema...")
response = supabase.table('foods_published').select("*").limit(1).execute()

if response.data and len(response.data) > 0:
    print("\nAvailable columns in foods_published:")
    for key in response.data[0].keys():
        print(f"  - {key}")
else:
    print("No data found")