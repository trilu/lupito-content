#!/usr/bin/env python3
"""Query Supabase database to check actual coverage data for the 3 brands"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv
from tabulate import tabulate

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase: Client = create_client(url, key)

print("="*80)
print("SUPABASE DATABASE COVERAGE ANALYSIS")
print("="*80)

# 1. Check if materialized views exist and have data
print("\n1. CHECKING MATERIALIZED VIEWS")
print("-" * 50)

try:
    print("Checking foods_brand_quality_preview_mv...")
    preview_mv_data = supabase.table('foods_brand_quality_preview_mv').select('*').limit(5).execute()
    print(f"✅ Preview MV exists with {len(preview_mv_data.data)} sample records")
    if preview_mv_data.data:
        print(f"Sample columns: {list(preview_mv_data.data[0].keys())}")
except Exception as e:
    print(f"❌ Preview MV error: {e}")

try:
    print("\nChecking foods_brand_quality_prod_mv...")
    prod_mv_data = supabase.table('foods_brand_quality_prod_mv').select('*').limit(5).execute()
    print(f"✅ Prod MV exists with {len(prod_mv_data.data)} sample records")
    if prod_mv_data.data:
        print(f"Sample columns: {list(prod_mv_data.data[0].keys())}")
except Exception as e:
    print(f"❌ Prod MV error: {e}")

# 2. Get actual coverage for the 3 brands from foods_published_preview
print("\n\n2. ACTUAL COVERAGE FROM foods_published_preview")
print("-" * 50)

brands = ['bozita', 'belcando', 'briantos']
coverage_results = []

for brand in brands:
    try:
        print(f"\nAnalyzing {brand.upper()}...")
        
        # Get all records for this brand
        all_records = supabase.table('foods_published_preview').select('*').eq('brand_slug', brand).execute()
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
    print("\n\n3. COVERAGE SUMMARY TABLE")
    print("-" * 50)
    headers = ['Brand', 'Total SKUs', 'Ingredients', 'Form', 'Life Stage', 'Kcal (200-600)', 'All Complete']
    print(tabulate(coverage_results, headers=headers, tablefmt='github'))

# 4. Compare with materialized views if they exist
print("\n\n4. COMPARISON WITH MATERIALIZED VIEWS")
print("-" * 50)

try:
    # Get MV data for our 3 brands
    mv_preview = supabase.table('foods_brand_quality_preview_mv').select('*').in_('brand_slug', brands).execute()
    mv_prod = supabase.table('foods_brand_quality_prod_mv').select('*').in_('brand_slug', brands).execute()
    
    print("\nMaterialized View Data (Preview):")
    for brand in brands:
        brand_data = next((b for b in mv_preview.data if b['brand_slug'] == brand), None)
        if brand_data:
            # Handle both possible column names for coverage
            ingredients_cov = brand_data.get('ingredients_coverage_pct', brand_data.get('ingredients_cov', 'N/A'))
            form_cov = brand_data.get('form_coverage_pct', brand_data.get('form_cov', 'N/A'))
            life_stage_cov = brand_data.get('life_stage_coverage_pct', brand_data.get('life_stage_cov', 'N/A'))
            kcal_cov = brand_data.get('kcal_valid_pct', brand_data.get('kcal_cov', 'N/A'))
            
            print(f"  {brand.upper()}: SKUs={brand_data.get('sku_count', 'N/A')}")
            print(f"    Ingredients={ingredients_cov if isinstance(ingredients_cov, str) else f'{ingredients_cov:.1f}%'}")
            print(f"    Form={form_cov if isinstance(form_cov, str) else f'{form_cov:.1f}%'}")
            print(f"    Life Stage={life_stage_cov if isinstance(life_stage_cov, str) else f'{life_stage_cov:.1f}%'}")
            print(f"    Kcal={kcal_cov if isinstance(kcal_cov, str) else f'{kcal_cov:.1f}%'}")
        else:
            print(f"  {brand.upper()}: No data in preview MV")
    
    print("\nMaterialized View Data (Prod):")
    for brand in brands:
        brand_data = next((b for b in mv_prod.data if b['brand_slug'] == brand), None)
        if brand_data:
            # Handle both possible column names for coverage
            ingredients_cov = brand_data.get('ingredients_coverage_pct', brand_data.get('ingredients_cov', 'N/A'))
            form_cov = brand_data.get('form_coverage_pct', brand_data.get('form_cov', 'N/A'))
            life_stage_cov = brand_data.get('life_stage_coverage_pct', brand_data.get('life_stage_cov', 'N/A'))
            kcal_cov = brand_data.get('kcal_valid_pct', brand_data.get('kcal_cov', 'N/A'))
            
            print(f"  {brand.upper()}: SKUs={brand_data.get('sku_count', 'N/A')}")
            print(f"    Ingredients={ingredients_cov if isinstance(ingredients_cov, str) else f'{ingredients_cov:.1f}%'}")
            print(f"    Form={form_cov if isinstance(form_cov, str) else f'{form_cov:.1f}%'}")
            print(f"    Life Stage={life_stage_cov if isinstance(life_stage_cov, str) else f'{life_stage_cov:.1f}%'}")
            print(f"    Kcal={kcal_cov if isinstance(kcal_cov, str) else f'{kcal_cov:.1f}%'}")
        else:
            print(f"  {brand.upper()}: No data in prod MV")
            
except Exception as e:
    print(f"❌ Error querying materialized views: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80)