#!/usr/bin/env python3
"""Check column names in food tables"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase: Client = create_client(url, key)

tables = ['foods_canonical', 'foods_published', 'foods_published_preview']

for table in tables:
    print(f"\n{table}:")
    try:
        response = supabase.table(table).select("*").limit(1).execute()
        if response.data and len(response.data) > 0:
            columns = list(response.data[0].keys())
            print(f"  Columns: {', '.join(columns)}")
        else:
            print("  No data")
    except Exception as e:
        print(f"  Error: {e}")