#!/usr/bin/env python3
"""
Debug IAMS brand anomaly - check actual database state
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# Initialize Supabase
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_KEY')
)

def debug_iams_anomaly():
    print('=== IAMS ANOMALY DEBUG - ACTUAL DATABASE STATE ===')
    print()

    # Check foods_canonical table structure
    print('1. Checking foods_canonical table for 155444 brand:')
    response = supabase.table('foods_canonical').select('product_key, brand, brand_slug, product_name').eq('brand', '155444').execute()

    if response.data:
        print(f'   Found {len(response.data)} products with brand="155444"')
        for i, product in enumerate(response.data[:3]):
            print(f'   Product {i+1}:')
            print(f'     brand: "{product["brand"]}"')
            print(f'     brand_slug: {product["brand_slug"]}')
            print(f'     product_name: "{product["product_name"]}"')
            print()
    else:
        print('   ❌ No products found with brand="155444"')
        print()

    # Check if they exist with different conditions
    print('2. Searching for IAMS products in different ways:')

    # Search by product name containing IAMS
    iams_by_name = supabase.table('foods_canonical').select('product_key, brand, brand_slug, product_name').like('product_name', '%IAMS Advanced Nutrition%').execute()
    print(f'   Products with "IAMS Advanced Nutrition" in name: {len(iams_by_name.data)}')

    if iams_by_name.data:
        print('   Sample products:')
        for i, product in enumerate(iams_by_name.data[:3]):
            print(f'     {i+1}. brand="{product["brand"]}", brand_slug={product["brand_slug"]}, name="{product["product_name"]}"')
        print()

    # Check all possible brand values that might be anomalies
    print('3. Checking for numeric/anomalous brand values:')
    all_brands = supabase.table('foods_canonical').select('brand').execute()

    numeric_brands = set()
    for product in all_brands.data:
        brand = product['brand']
        if brand and brand.isdigit():
            numeric_brands.add(brand)

    print(f'   Found {len(numeric_brands)} numeric brand values: {sorted(list(numeric_brands))[:10]}')
    print()

    # Check specifically for product keys starting with 155444
    print('4. Checking product_keys starting with 155444:')
    products_155444 = supabase.table('foods_canonical').select('product_key, brand, brand_slug, product_name').like('product_key', '155444%').execute()
    print(f'   Products with product_key starting with "155444": {len(products_155444.data)}')

    if products_155444.data:
        print('   Sample products:')
        for i, product in enumerate(products_155444.data[:3]):
            print(f'     {i+1}. brand="{product["brand"]}", brand_slug={product["brand_slug"]}, name="{product["product_name"]}"')
        print()

    # Final verification - check if update worked
    print('5. Checking if any IAMS products exist with correct branding:')
    correct_iams = supabase.table('foods_canonical').select('product_key, brand, brand_slug, product_name').eq('brand', 'IAMS').eq('brand_slug', 'iams').execute()
    print(f'   Products with brand="IAMS" and brand_slug="iams": {len(correct_iams.data)}')

    if correct_iams.data:
        print('   Sample corrected products:')
        for i, product in enumerate(correct_iams.data[:3]):
            print(f'     {i+1}. "{product["product_name"]}"')
        print()

    print('6. Summary of findings:')
    print(f'   - Products with brand="155444": {len(response.data) if response.data else 0}')
    print(f'   - Products with "IAMS Advanced Nutrition" in name: {len(iams_by_name.data)}')
    print(f'   - Products with product_key starting "155444": {len(products_155444.data)}')
    print(f'   - Products correctly branded as IAMS: {len(correct_iams.data)}')

if __name__ == '__main__':
    debug_iams_anomaly()