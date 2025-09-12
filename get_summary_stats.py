#!/usr/bin/env python3
"""
Get summary statistics from foods_brand_quality_prod_mv
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
    print("SUMMARY STATISTICS FROM foods_brand_quality_prod_mv")
    print("="*80)
    
    for brand in target_brands:
        try:
            response = supabase.table('foods_brand_quality_prod_mv').select("*").eq('brand_slug', brand).execute()
            if response.data:
                data = response.data[0]
                print(f"\n{brand.upper()} Summary Statistics:")
                print("-" * 50)
                print(f"Total SKUs: {data.get('sku_count')}")
                print(f"Form coverage: {data.get('form_coverage_pct')}%")
                print(f"Life stage coverage: {data.get('life_stage_coverage_pct')}%")
                print(f"Ingredients coverage: {data.get('ingredients_coverage_pct')}%")
                print(f"Kcal valid: {data.get('kcal_valid_pct')}%")
                print(f"Overall completion: {data.get('completion_pct')}%")
                print(f"Adult/Puppy/Senior: {data.get('adult_count')}/{data.get('puppy_count')}/{data.get('senior_count')}")
                print(f"Dry/Wet/Treats: {data.get('dry_count')}/{data.get('wet_count')}/{data.get('treats_count')}")
                print(f"Last updated: {data.get('last_updated')}")
        except Exception as e:
            print(f"Error for {brand}: {e}")

if __name__ == "__main__":
    main()