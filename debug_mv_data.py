#!/usr/bin/env python3
"""Debug materialized view data to understand the discrepancy"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv
import json

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase: Client = create_client(url, key)

print("="*80)
print("DEBUGGING MATERIALIZED VIEW DATA")
print("="*80)

brands = ['bozita', 'belcando', 'briantos']

try:
    # Get all data from preview MV
    mv_preview = supabase.table('foods_brand_quality_preview_mv').select('*').execute()
    print(f"\nTotal records in preview MV: {len(mv_preview.data)}")
    
    # Get all data from prod MV  
    mv_prod = supabase.table('foods_brand_quality_prod_mv').select('*').execute()
    print(f"Total records in prod MV: {len(mv_prod.data)}")
    
    print("\nAll brands in Preview MV:")
    for record in mv_preview.data:
        print(f"  {record['brand_slug']}: {record['sku_count']} SKUs")
    
    print("\nAll brands in Prod MV:")
    for record in mv_prod.data:
        print(f"  {record['brand_slug']}: {record['sku_count']} SKUs")
    
    print("\nFull data for our 3 brands in Preview MV:")
    for brand in brands:
        brand_data = next((b for b in mv_preview.data if b['brand_slug'] == brand), None)
        if brand_data:
            print(f"\n{brand.upper()}:")
            print(json.dumps(brand_data, indent=2, default=str))
        else:
            print(f"\n{brand.upper()}: No data found")
    
    print("\nFull data for our 3 brands in Prod MV:")
    for brand in brands:
        brand_data = next((b for b in mv_prod.data if b['brand_slug'] == brand), None)
        if brand_data:
            print(f"\n{brand.upper()}:")
            print(json.dumps(brand_data, indent=2, default=str))
        else:
            print(f"\n{brand.upper()}: No data found")
            
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("DEBUG COMPLETE")
print("="*80)