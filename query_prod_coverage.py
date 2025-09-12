#!/usr/bin/env python3
"""Query foods_published_prod to understand the coverage discrepancy"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv
from tabulate import tabulate

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase: Client = create_client(url, key)

print("="*80)
print("FOODS_PUBLISHED_PROD COVERAGE ANALYSIS")
print("="*80)

brands = ['bozita', 'belcando', 'briantos']
coverage_results = []

for brand in brands:
    try:
        print(f"\nAnalyzing {brand.upper()} in foods_published_prod...")
        
        # Get all records for this brand from prod table
        all_records = supabase.table('foods_published_prod').select('*').eq('brand_slug', brand).execute()
        total_sku_count = len(all_records.data)
        
        if total_sku_count == 0:
            print(f"  ⚠️  No records found for {brand}")
            continue
        
        # Count records with non-null values for each field
        ingredients_count = len([r for r in all_records.data if r.get('ingredients_tokens') is not None and r.get('ingredients_tokens') != ''])
        form_count = len([r for r in all_records.data if r.get('form') is not None and r.get('form') != ''])
        life_stage_count = len([r for r in all_records.data if r.get('life_stage') is not None and r.get('life_stage') != ''])
        
        # Count records with kcal_per_100g between 200-600
        kcal_count = len([r for r in all_records.data if r.get('kcal_per_100g') is not None and 200 <= r.get('kcal_per_100g', 0) <= 600])
        
        # Calculate percentages
        ingredients_pct = (ingredients_count / total_sku_count * 100) if total_sku_count > 0 else 0
        form_pct = (form_count / total_sku_count * 100) if total_sku_count > 0 else 0
        life_stage_pct = (life_stage_count / total_sku_count * 100) if total_sku_count > 0 else 0
        kcal_pct = (kcal_count / total_sku_count * 100) if total_sku_count > 0 else 0
        
        # Overall completion (all 4 fields populated)
        all_fields_count = len([r for r in all_records.data if 
                               r.get('ingredients_tokens') is not None and r.get('ingredients_tokens') != '' and
                               r.get('form') is not None and r.get('form') != '' and
                               r.get('life_stage') is not None and r.get('life_stage') != '' and
                               r.get('kcal_per_100g') is not None and 200 <= r.get('kcal_per_100g', 0) <= 600])
        overall_pct = (all_fields_count / total_sku_count * 100) if total_sku_count > 0 else 0
        
        coverage_results.append([
            brand.upper(),
            total_sku_count,
            f"{ingredients_count} ({ingredients_pct:.1f}%)",
            f"{form_count} ({form_pct:.1f}%)",
            f"{life_stage_count} ({life_stage_pct:.1f}%)",
            f"{kcal_count} ({kcal_pct:.1f}%)",
            f"{all_fields_count} ({overall_pct:.1f}%)"
        ])
        
        print(f"  Total SKUs: {total_sku_count}")
        print(f"  Ingredients: {ingredients_count} ({ingredients_pct:.1f}%)")
        print(f"  Form: {form_count} ({form_pct:.1f}%)")
        print(f"  Life Stage: {life_stage_count} ({life_stage_pct:.1f}%)")
        print(f"  Kcal (200-600): {kcal_count} ({kcal_pct:.1f}%)")
        print(f"  All Fields: {all_fields_count} ({overall_pct:.1f}%)")
        
    except Exception as e:
        print(f"  ❌ Error querying {brand}: {e}")

# Display results table
if coverage_results:
    print("\n\nPROD TABLE COVERAGE SUMMARY")
    print("-" * 50)
    headers = ['Brand', 'Total SKUs', 'Ingredients', 'Form', 'Life Stage', 'Kcal (200-600)', 'All Complete']
    print(tabulate(coverage_results, headers=headers, tablefmt='github'))

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80)