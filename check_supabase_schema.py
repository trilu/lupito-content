#!/usr/bin/env python3
"""Check Supabase schema to verify tables and columns"""

import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Initialize Supabase
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(url, key)

print("="*80)
print("SUPABASE SCHEMA CHECK")
print("="*80)

# Check foods_canonical table
print("\n1. CHECKING foods_canonical TABLE:")
print("-"*40)
try:
    response = supabase.table('foods_canonical').select('*').limit(1).execute()
    if response.data:
        columns = list(response.data[0].keys())
        print(f"✅ Table exists with {len(columns)} columns:")
        for col in sorted(columns):
            print(f"   - {col}")
except Exception as e:
    print(f"❌ Error: {e}")

# Check foods_published_preview table
print("\n2. CHECKING foods_published_preview TABLE:")
print("-"*40)
try:
    response = supabase.table('foods_published_preview').select('*').limit(1).execute()
    if response.data:
        columns = list(response.data[0].keys())
        print(f"✅ Table exists with {len(columns)} columns:")
        for col in sorted(columns):
            print(f"   - {col}")
except Exception as e:
    print(f"❌ Error: {e}")

# Check foods_published_prod table
print("\n3. CHECKING foods_published_prod TABLE:")
print("-"*40)
try:
    response = supabase.table('foods_published_prod').select('*').limit(1).execute()
    if response.data:
        columns = list(response.data[0].keys())
        print(f"✅ Table exists with {len(columns)} columns:")
        for col in sorted(columns):
            print(f"   - {col}")
except Exception as e:
    print(f"❌ Error: {e}")

# Check if manufacturer_harvest_staging exists
print("\n4. CHECKING manufacturer_harvest_staging TABLE:")
print("-"*40)
try:
    response = supabase.table('manufacturer_harvest_staging').select('*').limit(1).execute()
    if response.data:
        columns = list(response.data[0].keys())
        print(f"✅ Table exists with {len(columns)} columns:")
        for col in sorted(columns):
            print(f"   - {col}")
    else:
        print("ℹ️ Table doesn't exist yet (will be created by SQL script)")
except Exception as e:
    print(f"ℹ️ Table doesn't exist yet: {e}")

# Check column data types for key fields
print("\n5. CHECKING KEY COLUMN TYPES:")
print("-"*40)
try:
    # Get sample data to check types
    response = supabase.table('foods_canonical').select(
        'product_key,brand_slug,product_name,form,life_stage,kcal_per_100g,ingredients_tokens,price_per_kg'
    ).limit(5).execute()
    
    if response.data:
        print("Sample data from foods_canonical:")
        for row in response.data[:2]:
            print(f"\n  product_key: {row['product_key']} (type: {type(row['product_key']).__name__})")
            print(f"  brand_slug: {row['brand_slug']} (type: {type(row['brand_slug']).__name__})")
            print(f"  form: {row['form']} (type: {type(row['form']).__name__ if row['form'] else 'None'})")
            print(f"  life_stage: {row['life_stage']} (type: {type(row['life_stage']).__name__ if row['life_stage'] else 'None'})")
            print(f"  kcal_per_100g: {row['kcal_per_100g']} (type: {type(row['kcal_per_100g']).__name__ if row['kcal_per_100g'] else 'None'})")
            print(f"  ingredients_tokens: {row['ingredients_tokens'][:3] if row['ingredients_tokens'] else None} (type: {type(row['ingredients_tokens']).__name__ if row['ingredients_tokens'] else 'None'})")
            print(f"  price_per_kg: {row['price_per_kg']} (type: {type(row['price_per_kg']).__name__ if row['price_per_kg'] else 'None'})")
except Exception as e:
    print(f"Error: {e}")

# Check foods_published_preview structure
print("\n6. CHECKING foods_published_preview STRUCTURE:")
print("-"*40)
try:
    response = supabase.table('foods_published_preview').select(
        'product_key,brand_slug,product_name,form,life_stage,kcal_per_100g,ingredients_tokens,price_per_kg_eur,sources'
    ).limit(2).execute()
    
    if response.data:
        print("Sample data from foods_published_preview:")
        for row in response.data[:1]:
            print(f"\n  product_key: {row['product_key']}")
            print(f"  price_per_kg_eur: {row.get('price_per_kg_eur')} (note: EUR suffix)")
            print(f"  sources: {type(row.get('sources')).__name__ if row.get('sources') else 'None'}")
            if row.get('sources'):
                print(f"    sources content: {row['sources']}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "="*80)
print("SCHEMA VERIFICATION COMPLETE")
print("="*80)