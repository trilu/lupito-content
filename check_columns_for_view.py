#!/usr/bin/env python3
"""
Check actual column structure of Supabase tables
"""

import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

def check_table_structure():
    # Initialize Supabase
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    supabase = create_client(url, key)
    
    print("="*60)
    print("CHECKING SUPABASE TABLE STRUCTURES")
    print("="*60)
    
    # Check foods_canonical columns
    print("\n📊 foods_canonical columns:")
    print("-" * 40)
    
    try:
        # Fetch one row to see all columns
        response = supabase.table('foods_canonical').select('*').limit(1).execute()
        if response.data:
            columns = list(response.data[0].keys())
            columns.sort()
            for col in columns:
                sample_value = response.data[0][col]
                value_type = type(sample_value).__name__
                print(f"  - {col}: {value_type}")
        else:
            print("  No data in table")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Check for specific columns we need
    print("\n🔍 Checking for specific columns:")
    print("-" * 40)
    
    expected_cols = ['id', 'brand', 'product_name', 'brand_slug', 'allergens', 
                     'ingredients_tokens', 'available_countries', 'sources']
    
    if response.data:
        actual_cols = set(response.data[0].keys())
        for col in expected_cols:
            if col in actual_cols:
                print(f"  ✓ {col}: EXISTS")
            else:
                print(f"  ✗ {col}: MISSING")
    
    return response.data[0] if response.data else {}

if __name__ == "__main__":
    structure = check_table_structure()