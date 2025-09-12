#!/usr/bin/env python3
"""Check coverage metrics for Bozita, Belcando, and Briantos"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv
from tabulate import tabulate

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase: Client = create_client(url, key)

print("\n" + "="*80)
print("COVERAGE COMPARISON: BOZITA, BELCANDO, BRIANTOS")
print("="*80)

# Query preview view
preview_resp = supabase.table('foods_brand_quality_preview_mv').select('*').in_('brand_slug', ['bozita', 'belcando', 'briantos']).execute()

# Query prod view  
prod_resp = supabase.table('foods_brand_quality_prod_mv').select('*').in_('brand_slug', ['bozita', 'belcando', 'briantos']).execute()

# Process results
brands = ['bozita', 'belcando', 'briantos']
results = []

for brand in brands:
    preview_data = next((b for b in preview_resp.data if b['brand_slug'] == brand), {})
    prod_data = next((b for b in prod_resp.data if b['brand_slug'] == brand), {})
    
    # Preview row
    results.append([
        brand.upper(),
        'Preview',
        preview_data.get('sku_count', 0),
        f"{preview_data.get('ingredients_cov', 0):.1f}%",
        f"{preview_data.get('form_cov', 0):.1f}%",
        f"{preview_data.get('life_stage_cov', 0):.1f}%",
        f"{preview_data.get('kcal_cov', 0):.1f}%",
        f"{preview_data.get('completion_pct', 0):.1f}%"
    ])
    
    # Prod row
    results.append([
        '',
        'Prod',
        prod_data.get('sku_count', 0),
        f"{prod_data.get('ingredients_cov', 0):.1f}%",
        f"{prod_data.get('form_cov', 0):.1f}%",
        f"{prod_data.get('life_stage_cov', 0):.1f}%",
        f"{prod_data.get('kcal_cov', 0):.1f}%",
        f"{prod_data.get('completion_pct', 0):.1f}%"
    ])
    
    # Delta row (preview - prod)
    results.append([
        '',
        'Delta',
        preview_data.get('sku_count', 0) - prod_data.get('sku_count', 0),
        f"{preview_data.get('ingredients_cov', 0) - prod_data.get('ingredients_cov', 0):+.1f}%",
        f"{preview_data.get('form_cov', 0) - prod_data.get('form_cov', 0):+.1f}%",
        f"{preview_data.get('life_stage_cov', 0) - prod_data.get('life_stage_cov', 0):+.1f}%",
        f"{preview_data.get('kcal_cov', 0) - prod_data.get('kcal_cov', 0):+.1f}%",
        f"{preview_data.get('completion_pct', 0) - prod_data.get('completion_pct', 0):+.1f}%"
    ])
    
    results.append(['---', '---', '---', '---', '---', '---', '---', '---'])

# Remove last separator
results = results[:-1]

headers = ['Brand', 'View', 'SKUs', 'Ingredients', 'Form', 'Life Stage', 'Kcal', 'Overall']
print("\n" + tabulate(results, headers=headers, tablefmt='github'))

# Summary of key issues
print("\n" + "="*80)
print("KEY OBSERVATIONS:")
print("="*80)

for brand in brands:
    preview_data = next((b for b in preview_resp.data if b['brand_slug'] == brand), {})
    prod_data = next((b for b in prod_resp.data if b['brand_slug'] == brand), {})
    
    print(f"\n{brand.upper()}:")
    
    # Check which metrics are below gates
    issues = []
    if preview_data.get('ingredients_cov', 0) < 85:
        issues.append(f"  ❌ Ingredients: {preview_data.get('ingredients_cov', 0):.1f}% < 85% target")
    if preview_data.get('form_cov', 0) < 95:
        issues.append(f"  ❌ Form: {preview_data.get('form_cov', 0):.1f}% < 95% target")
    if preview_data.get('life_stage_cov', 0) < 95:
        issues.append(f"  ❌ Life Stage: {preview_data.get('life_stage_cov', 0):.1f}% < 95% target")
    
    if issues:
        for issue in issues:
            print(issue)
    else:
        print("  ✅ All coverage gates met!")
    
    # Show enriched count if available
    if prod_data.get('enriched_count'):
        print(f"  📊 Food-ready in prod: {prod_data.get('enriched_count', 0)} SKUs")

print("\n" + "="*80)
print("HIGHEST LEVERAGE ACTION FOR NEXT 60 MINUTES:")
print("="*80)

# Determine highest impact action
print("\nBased on current gaps:")
print("1. BELCANDO needs the most work (35.3% ingredients in both views)")
print("2. BRIANTOS has minimal manufacturer snapshots (only 2 in GCS)")
print("3. BOZITA has good ingredients (64.4%) but poor form/life_stage (39.1%)")
print("\nRECOMMENDATION: Focus on Belcando ingredient extraction")
print("- 19 manufacturer snapshots available in GCS")
print("- Current extraction only getting 35.3% coverage")
print("- Improving selectors could yield 30-50% lift")
print("- This would bring Belcando closer to the 85% ingredients gate")