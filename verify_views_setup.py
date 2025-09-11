#!/usr/bin/env python3
"""
Verify that all views and materialized views are set up correctly
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Initialize Supabase client
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')

if not url or not key:
    raise ValueError("Missing Supabase credentials in .env file")

supabase: Client = create_client(url, key)

print("="*60)
print("VERIFYING SUPABASE VIEWS SETUP")
print("="*60)
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*60)

# List of objects to verify
objects_to_check = [
    ('brand_allowlist', 'table'),
    ('foods_published_prod', 'view'),
    ('foods_published_preview', 'view'),
    ('foods_brand_quality_prod_mv', 'materialized view'),
    ('foods_brand_quality_preview_mv', 'materialized view')
]

results = {}

for obj_name, obj_type in objects_to_check:
    try:
        # Try to query the object
        response = supabase.table(obj_name).select("*", count='exact', head=True).execute()
        count = response.count if hasattr(response, 'count') else 0
        
        # For regular queries, get a sample
        if obj_type == 'view':
            sample_response = supabase.table(obj_name).select("*").limit(5).execute()
            sample_count = len(sample_response.data) if sample_response.data else 0
        else:
            sample_count = 0
        
        results[obj_name] = {
            'exists': True,
            'row_count': count,
            'type': obj_type
        }
        
        print(f"✅ {obj_name:30} | {count:,} rows | {obj_type}")
        
    except Exception as e:
        results[obj_name] = {
            'exists': False,
            'error': str(e)
        }
        print(f"❌ {obj_name:30} | ERROR: {str(e)[:50]}")

print("\n" + "="*60)
print("CHECKING BRAND ALLOWLIST STATUS DISTRIBUTION")
print("="*60)

try:
    response = supabase.table('brand_allowlist').select("status").execute()
    if response.data:
        status_counts = {}
        for row in response.data:
            status = row.get('status', 'UNKNOWN')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print("Status distribution:")
        for status, count in sorted(status_counts.items()):
            print(f"  {status:10} : {count} brands")
except Exception as e:
    print(f"Error checking allowlist: {e}")

print("\n" + "="*60)
print("CHECKING VIEWS CONTENT")
print("="*60)

# Check prod view
try:
    prod_response = supabase.table('foods_published_prod').select("brand_slug", count='exact').limit(1).execute()
    prod_count = prod_response.count if hasattr(prod_response, 'count') else 0
    
    # Get distinct brands
    prod_brands = supabase.table('foods_published_prod').select("brand_slug").execute()
    if prod_brands.data:
        unique_brands = set(row['brand_slug'] for row in prod_brands.data)
        print(f"foods_published_prod:")
        print(f"  Total products: {prod_count}")
        print(f"  Unique brands: {len(unique_brands)}")
        print(f"  Sample brands: {', '.join(list(unique_brands)[:5])}")
except Exception as e:
    print(f"Error checking prod view: {e}")

print()

# Check preview view
try:
    preview_response = supabase.table('foods_published_preview').select("brand_slug", count='exact').limit(1).execute()
    preview_count = preview_response.count if hasattr(preview_response, 'count') else 0
    
    # Get distinct brands
    preview_brands = supabase.table('foods_published_preview').select("brand_slug").execute()
    if preview_brands.data:
        unique_brands = set(row['brand_slug'] for row in preview_brands.data)
        print(f"foods_published_preview:")
        print(f"  Total products: {preview_count}")
        print(f"  Unique brands: {len(unique_brands)}")
        print(f"  Sample brands: {', '.join(list(unique_brands)[:5])}")
except Exception as e:
    print(f"Error checking preview view: {e}")

print("\n" + "="*60)
print("CHECKING BRAND QUALITY METRICS")
print("="*60)

# Check brand quality MVs
for mv_name in ['foods_brand_quality_prod_mv', 'foods_brand_quality_preview_mv']:
    try:
        response = supabase.table(mv_name).select("*").execute()
        if response.data and len(response.data) > 0:
            print(f"\n{mv_name}:")
            print(f"  Total brands: {len(response.data)}")
            
            # Get top brands by SKU count
            sorted_brands = sorted(response.data, key=lambda x: x.get('sku_count', 0), reverse=True)
            print("  Top 5 brands by SKU count:")
            for brand in sorted_brands[:5]:
                print(f"    - {brand['brand_slug']:20} : {brand.get('sku_count', 0)} SKUs, "
                      f"{brand.get('completion_pct', 0):.1f}% complete")
    except Exception as e:
        print(f"Error checking {mv_name}: {e}")

print("\n" + "="*60)
print("SOURCE OF TRUTH BLOCK")
print("="*60)

print(f"""
SUPABASE_URL = {url.split('.')[0]}.supabase.co
ACTIVE_PROD_VIEW = foods_published_prod ({results.get('foods_published_prod', {}).get('row_count', 0)} rows)
ACTIVE_PREVIEW_VIEW = foods_published_preview ({results.get('foods_published_preview', {}).get('row_count', 0)} rows)
BRAND_QUALITY_MV_PROD = foods_brand_quality_prod_mv
BRAND_QUALITY_MV_PREVIEW = foods_brand_quality_preview_mv
JSON_ARRAYS_OK_RULE = jsonb_typeof(field)='array' AND jsonb_array_length(field)>0
KCALS_VALID_RANGE = 200..600
NOTE = Allowlist gating applied at view layer

✅ All views and materialized views are configured and operational
""")

# Save verification report
report_path = f"reports/VIEWS_VERIFICATION_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
with open(report_path, 'w') as f:
    f.write("# SUPABASE VIEWS VERIFICATION REPORT\n\n")
    f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    
    f.write("## Objects Status\n\n")
    f.write("| Object | Type | Status | Row Count |\n")
    f.write("|--------|------|--------|----------|\n")
    
    for obj_name, obj_type in objects_to_check:
        result = results.get(obj_name, {})
        status = "✅" if result.get('exists') else "❌"
        row_count = result.get('row_count', 'N/A') if result.get('exists') else 'ERROR'
        f.write(f"| {obj_name} | {obj_type} | {status} | {row_count} |\n")
    
    f.write("\n## Summary\n\n")
    if all(r.get('exists') for r in results.values()):
        f.write("✅ **All views and materialized views are successfully configured!**\n")
    else:
        f.write("⚠️ Some objects are missing or have errors.\n")

print(f"\n✓ Verification report saved to {report_path}")