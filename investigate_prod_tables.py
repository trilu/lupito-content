#!/usr/bin/env python3
"""
Investigate production tables structure and data
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv
import json

load_dotenv()

def main():
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_KEY')
    supabase: Client = create_client(url, key)
    
    target_brands = ['briantos', 'bozita']
    
    print("="*80)
    print("INVESTIGATING PRODUCTION TABLES")
    print("="*80)
    
    # Check foods_brand_quality_prod_mv structure
    print("\n1. foods_brand_quality_prod_mv structure and sample data:")
    print("-" * 60)
    
    for brand in target_brands:
        try:
            response = supabase.table('foods_brand_quality_prod_mv').select("*").eq('brand_slug', brand).execute()
            print(f"\n{brand.upper()} in foods_brand_quality_prod_mv:")
            print(f"Records found: {len(response.data)}")
            if response.data:
                print("Sample record structure:")
                print(json.dumps(response.data[0], indent=2, default=str))
        except Exception as e:
            print(f"Error accessing foods_brand_quality_prod_mv for {brand}: {e}")
    
    # Check foods_published_prod structure  
    print("\n\n2. foods_published_prod structure and sample data:")
    print("-" * 60)
    
    for brand in target_brands:
        try:
            response = supabase.table('foods_published_prod').select("*").eq('brand_slug', brand).execute()
            print(f"\n{brand.upper()} in foods_published_prod:")
            print(f"Records found: {len(response.data)}")
            if response.data:
                print("Sample record structure:")
                # Show first record
                print(json.dumps(response.data[0], indent=2, default=str))
                
                # Show count by different groupings if more than 1 record
                if len(response.data) > 1:
                    print(f"\nFirst 5 product IDs:")
                    for i, record in enumerate(response.data[:5]):
                        print(f"  {i+1}: {record.get('product_id')} - {record.get('product_name', 'N/A')}")
        except Exception as e:
            print(f"Error accessing foods_published_prod for {brand}: {e}")
    
    # Check other potential tables
    print("\n\n3. Alternative data sources:")
    print("-" * 60)
    
    tables_to_check = ['foods_canonical', 'brand_allowlist']
    
    for table in tables_to_check:
        print(f"\n{table.upper()}:")
        try:
            for brand in target_brands:
                response = supabase.table(table).select("*").eq('brand_slug', brand).limit(3).execute()
                print(f"  {brand}: {len(response.data)} records")
                if response.data and len(response.data) > 0:
                    # Show sample field names
                    sample_fields = list(response.data[0].keys())[:10]  # First 10 fields
                    print(f"    Sample fields: {sample_fields}")
        except Exception as e:
            print(f"  Error accessing {table}: {e}")
    
    # Check brand allowlist status
    print("\n\n4. Brand allowlist status:")
    print("-" * 60)
    
    try:
        for brand in target_brands:
            response = supabase.table('brand_allowlist').select("*").eq('brand_slug', brand).execute()
            if response.data:
                for record in response.data:
                    print(f"{brand.upper()}: status={record.get('status')}, updated_at={record.get('updated_at')}")
            else:
                print(f"{brand.upper()}: Not found in allowlist")
    except Exception as e:
        print(f"Error checking brand allowlist: {e}")

if __name__ == "__main__":
    main()