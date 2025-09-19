#!/usr/bin/env python3
"""Check AADF data status in both GCS and database"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv
from tabulate import tabulate

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase: Client = create_client(url, key)

print("="*80)
print("AADF (AllAboutDogFood) DATA STATUS ANALYSIS")
print("="*80)

# Query foods_canonical for AADF products
print("\n1. CHECKING FOODS_CANONICAL TABLE")
print("-"*40)

try:
    # Get all AADF products - identified by having 'allaboutdogfood' in the source field
    # Or by checking specific brands that come from AADF
    aadf_brands = ['aatu', 'akela', 'applaws', 'ardengrange', 'barking_heads', 'beco', 'burns', 'canagan',
                   'greenwoods', 'harringtons', 'iams', 'james_wellbeloved', "lily_s_kitchen", 'millies_wolfheart',
                   "nature_s_harvest", 'nutro', 'orijen', 'pooch_and_mutt', 'wainwright_s']

    # First try to find by source field
    aadf_products = supabase.table('foods_canonical').select(
        'product_key, product_name, brand, brand_slug, image_url, '
        'ingredients_raw, ingredients_tokens, protein_percent, fat_percent, fiber_percent, '
        'kcal_per_100g, form, life_stage, source, sources'
    ).like('source', '%allaboutdogfood%').execute()

    # If no results, try with sources field
    if not aadf_products.data:
        aadf_products = supabase.table('foods_canonical').select(
            'product_key, product_name, brand, brand_slug, image_url, '
            'ingredients_raw, ingredients_tokens, protein_percent, fat_percent, fiber_percent, '
            'kcal_per_100g, form, life_stage, source, sources'
        ).like('sources', '%allaboutdogfood%').execute()

    total_products = len(aadf_products.data)
    print(f"Total AADF products: {total_products}")

    # Count coverage
    has_image_url = len([p for p in aadf_products.data if p.get('image_url')])
    # Check if image_url contains GCS path
    has_gcs_url = len([p for p in aadf_products.data if p.get('image_url') and 'storage.googleapis.com' in str(p['image_url'])])
    has_ingredients_raw = len([p for p in aadf_products.data if p.get('ingredients_raw') and p['ingredients_raw'] != ''])
    has_ingredients_tokens = len([p for p in aadf_products.data if p.get('ingredients_tokens')])
    has_protein = len([p for p in aadf_products.data if p.get('protein_percent') is not None])
    has_fat = len([p for p in aadf_products.data if p.get('fat_percent') is not None])
    has_fiber = len([p for p in aadf_products.data if p.get('fiber_percent') is not None])
    has_kcal = len([p for p in aadf_products.data if p.get('kcal_per_100g') is not None])
    has_form = len([p for p in aadf_products.data if p.get('form') is not None])
    has_life_stage = len([p for p in aadf_products.data if p.get('life_stage') is not None])

    # Calculate percentages
    coverage_data = [
        ['Image URL', has_image_url, f"{has_image_url*100/total_products:.1f}%"],
        ['GCS Image URL', has_gcs_url, f"{has_gcs_url*100/total_products:.1f}%"],
        ['Ingredients (raw)', has_ingredients_raw, f"{has_ingredients_raw*100/total_products:.1f}%"],
        ['Ingredients (tokens)', has_ingredients_tokens, f"{has_ingredients_tokens*100/total_products:.1f}%"],
        ['Protein %', has_protein, f"{has_protein*100/total_products:.1f}%"],
        ['Fat %', has_fat, f"{has_fat*100/total_products:.1f}%"],
        ['Fiber %', has_fiber, f"{has_fiber*100/total_products:.1f}%"],
        ['Kcal/100g', has_kcal, f"{has_kcal*100/total_products:.1f}%"],
        ['Form', has_form, f"{has_form*100/total_products:.1f}%"],
        ['Life Stage', has_life_stage, f"{has_life_stage*100/total_products:.1f}%"]
    ]

    print("\nData Coverage:")
    print(tabulate(coverage_data, headers=['Field', 'Count', 'Percentage'], tablefmt='github'))

    # Show sample GCS URLs
    print("\n2. SAMPLE GCS URLS")
    print("-"*40)
    products_with_gcs = [p for p in aadf_products.data if p.get('image_url') and 'storage.googleapis.com' in str(p['image_url'])]
    if products_with_gcs:
        print(f"Found {len(products_with_gcs)} products with GCS URLs. Sample:")
        for p in products_with_gcs[:5]:
            print(f"  {p['product_name'][:50]:50} -> {p['image_url'][:80] if p['image_url'] else 'None'}")
    else:
        print("No products with GCS URLs found")

    # Check for bad ingredients data (placeholder text)
    print("\n3. CHECKING INGREDIENTS DATA QUALITY")
    print("-"*40)
    placeholder_text = "This is the ingredients list as printed on the packaging"
    bad_ingredients = [p for p in aadf_products.data
                       if p.get('ingredients_raw') and placeholder_text in p['ingredients_raw']]

    print(f"Products with placeholder text in ingredients: {len(bad_ingredients)}")
    if bad_ingredients:
        print("  Sample products with bad ingredients data:")
        for p in bad_ingredients[:3]:
            print(f"    - {p['product_name'][:60]}")

    # Check sample products with all data
    print("\n4. PRODUCTS WITH COMPLETE DATA")
    print("-"*40)
    complete_products = [p for p in aadf_products.data
                        if p.get('image_url') and p.get('ingredients_tokens')
                        and p.get('protein_percent') is not None]

    print(f"Products with images + ingredients + nutrition: {len(complete_products)}")
    if complete_products:
        print("Sample complete products:")
        for p in complete_products[:3]:
            print(f"  - {p['product_name'][:60]}")
            print(f"    Protein: {p['protein_percent']}% | Fat: {p['fat_percent']}% | Fiber: {p['fiber_percent']}%")

    # Check brand distribution
    print("\n5. TOP BRANDS IN AADF DATA")
    print("-"*40)
    brand_counts = Counter(p['brand'] for p in aadf_products.data if p.get('brand'))
    for brand, count in brand_counts.most_common(10):
        print(f"  {brand[:30]:30} : {count:3} products")

except Exception as e:
    print(f"Error querying database: {e}")

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80)