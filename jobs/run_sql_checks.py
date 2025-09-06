#!/usr/bin/env python3
"""
Run SQL checks on the database
"""
import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment
load_dotenv()

# Connect to Supabase
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
client = create_client(url, key)

print("=" * 60)
print("DATABASE STATISTICS")
print("=" * 60)

# 1. Total count from food_candidates
try:
    result = client.rpc('count', {'table_name': 'food_candidates'}).execute()
    total = len(client.table('food_candidates').select('id').execute().data)
    print(f"\nTotal products in food_candidates: {total}")
except:
    # Fallback method
    result = client.table('food_candidates').select('id', count='exact').execute()
    print(f"\nTotal products in food_candidates: {result.count if hasattr(result, 'count') else len(result.data)}")

# 2. Country availability from foods_published
try:
    # Get all products
    result = client.table('foods_published').select('available_countries').execute()
    
    ro_count = 0
    eu_count = 0
    total_count = len(result.data)
    
    for row in result.data:
        countries = row.get('available_countries', [])
        if 'RO' in countries:
            ro_count += 1
        if 'EU' in countries:
            eu_count += 1
    
    print(f"\nCountry availability in foods_published:")
    print(f"  RO (Romania): {ro_count}")
    print(f"  EU (Europe): {eu_count}")
    print(f"  Total: {total_count}")
    
except Exception as e:
    print(f"Error checking country availability: {e}")

# 3. Additional statistics
try:
    # Products with prices
    with_price = client.table('food_candidates').select('id').not_.is_('price_eur', 'null').execute()
    print(f"\nProducts with prices: {len(with_price.data)}")
    
    # Products with nutrition (all nulls for now)
    with_nutrition = client.table('food_candidates').select('id').not_.is_('kcal_per_100g', 'null').execute()
    print(f"Products with nutrition data: {len(with_nutrition.data)}")
    
    # Products by form
    forms = client.table('food_candidates').select('form').execute()
    form_counts = {}
    for row in forms.data:
        form = row.get('form', 'unknown')
        form_counts[form] = form_counts.get(form, 0) + 1
    
    print(f"\nProducts by form:")
    for form, count in sorted(form_counts.items()):
        print(f"  {form}: {count}")
    
except Exception as e:
    print(f"Error getting additional stats: {e}")

print("\n" + "=" * 60)