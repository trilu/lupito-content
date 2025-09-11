#!/usr/bin/env python3
"""
Check the actual structure of foods_canonical table in Supabase
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv
import pandas as pd

# Load environment variables
load_dotenv()

# Initialize Supabase client
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')

if not url or not key:
    raise ValueError("Missing Supabase credentials in .env file")

supabase: Client = create_client(url, key)

print("Checking foods_canonical table structure...")
print("="*60)

try:
    # Get a sample row to see all columns
    response = supabase.table('foods_canonical').select("*").limit(1).execute()
    
    if response.data and len(response.data) > 0:
        # Get column names from the first row
        columns = list(response.data[0].keys())
        
        print(f"Found {len(columns)} columns in foods_canonical:\n")
        
        # Group columns by category for better readability
        core_cols = []
        array_cols = []
        price_cols = []
        brand_cols = []
        other_cols = []
        
        for col in sorted(columns):
            if 'brand' in col.lower():
                brand_cols.append(col)
            elif 'price' in col.lower():
                price_cols.append(col)
            elif any(x in col for x in ['tokens', 'countries', 'sources']):
                array_cols.append(col)
            elif any(x in col for x in ['brand_slug', 'name_slug', 'product_key', 'brand', 'product_name']):
                core_cols.append(col)
            else:
                other_cols.append(col)
        
        print("CORE COLUMNS:")
        for col in core_cols:
            sample_val = response.data[0].get(col)
            print(f"  - {col}: {type(sample_val).__name__}")
        
        print("\nBRAND-RELATED COLUMNS:")
        for col in brand_cols:
            sample_val = response.data[0].get(col)
            print(f"  - {col}: {type(sample_val).__name__}")
        
        print("\nARRAY COLUMNS:")
        for col in array_cols:
            sample_val = response.data[0].get(col)
            val_type = type(sample_val).__name__
            if isinstance(sample_val, str) and sample_val.startswith('['):
                val_type += " (looks like stringified array)"
            print(f"  - {col}: {val_type}")
        
        print("\nPRICE COLUMNS:")
        for col in price_cols:
            sample_val = response.data[0].get(col)
            print(f"  - {col}: {type(sample_val).__name__}")
        
        print("\nOTHER COLUMNS:")
        for col in other_cols:
            sample_val = response.data[0].get(col)
            print(f"  - {col}: {type(sample_val).__name__}")
        
        print("\n" + "="*60)
        print("ALL COLUMNS (alphabetical):")
        for col in sorted(columns):
            print(f"  {col}")
            
    else:
        print("No data found in foods_canonical table")
        
except Exception as e:
    print(f"Error accessing foods_canonical: {e}")
    
print("\n" + "="*60)
print("Checking brand_allowlist table...")
try:
    response = supabase.table('brand_allowlist').select("*").limit(5).execute()
    if response.data:
        print(f"✓ brand_allowlist exists with {len(response.data)} sample rows")
        if response.data:
            print("Columns:", list(response.data[0].keys()))
    else:
        print("⚠️ brand_allowlist is empty or doesn't exist")
except Exception as e:
    print(f"⚠️ brand_allowlist not accessible: {e}")