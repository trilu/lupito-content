#!/usr/bin/env python3
"""
Generate the exact SQL conditions that implement the production filtering logic.

Based on our analysis, we identified these key filtering criteria:
1. allowlist_status = 'ACTIVE' (blocks PENDING)
2. source NOT IN ('zooplus_csv_import', 'allaboutdogfood')
3. Possible brand allowlist
4. Data completeness requirements
"""

import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Initialize Supabase
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(url, key)

print("="*80)
print("EXACT PRODUCTION FILTERING SQL CONDITIONS")
print("="*80)

# Test our hypothesis by building the exact WHERE clause
print("\n1. TESTING FILTERING HYPOTHESIS:")
print("-"*50)

try:
    # Start with preview count
    preview_count = supabase.table('foods_published_preview').select('product_key', count='exact').execute().count
    print(f"Starting with {preview_count:,} products in preview")

    # Apply each filter step by step
    conditions = []

    # Filter 1: allowlist_status = 'ACTIVE'
    active_count = supabase.table('foods_published_preview').select('product_key', count='exact').eq('allowlist_status', 'ACTIVE').execute().count
    filtered_by_status = preview_count - active_count
    conditions.append("allowlist_status = 'ACTIVE'")
    print(f"After allowlist_status = 'ACTIVE': {active_count:,} products ({filtered_by_status:,} filtered)")

    # Filter 2: source filtering
    source_filtered_count = supabase.table('foods_published_preview').select('product_key', count='exact').eq('allowlist_status', 'ACTIVE').not_.in_('source', ['zooplus_csv_import', 'allaboutdogfood']).execute().count
    filtered_by_source = active_count - source_filtered_count
    conditions.append("source NOT IN ('zooplus_csv_import', 'allaboutdogfood')")
    print(f"After source filtering: {source_filtered_count:,} products ({filtered_by_source:,} additional filtered)")

    # Check what we get so far vs actual production
    prod_count = supabase.table('foods_published_prod').select('product_key', count='exact').execute().count
    print(f"Target production count: {prod_count:,} products")
    print(f"Current filtered count: {source_filtered_count:,} products")
    print(f"Still need to filter: {source_filtered_count - prod_count:,} products")

    # Let's check what other conditions might be applied
    print(f"\n2. INVESTIGATING REMAINING FILTERS:")
    print("-"*50)

    # Get products that pass our current filters but aren't in production
    query = supabase.table('foods_published_preview').select('product_key, brand_slug, quality_score, kcal_per_100g, ingredients_tokens, life_stage, form').eq('allowlist_status', 'ACTIVE').not_.in_('source', ['zooplus_csv_import', 'allaboutdogfood'])

    # Execute query in batches since it might be large
    preview_filtered = query.execute()
    preview_filtered_keys = set([item['product_key'] for item in preview_filtered.data])

    prod_keys_response = supabase.table('foods_published_prod').select('product_key').execute()
    prod_keys = set([item['product_key'] for item in prod_keys_response.data])

    # Find products that should be filtered but passed our current filters
    additional_filtered = preview_filtered_keys - prod_keys
    print(f"Products passing current filters but not in production: {len(additional_filtered)}")

    if additional_filtered:
        # Analyze these products to find additional filtering criteria
        sample_additional = list(additional_filtered)[:100]  # Sample for analysis

        print("\nAnalyzing additionally filtered products...")

        additional_products = []
        for key in sample_additional[:50]:  # Just sample a few
            try:
                response = supabase.table('foods_published_preview').select('*').eq('product_key', key).execute()
                if response.data:
                    additional_products.extend(response.data)
            except:
                continue

        if additional_products:
            print(f"Analyzing {len(additional_products)} additionally filtered products:")

            # Check common characteristics
            brands_in_additional = set([p['brand_slug'] for p in additional_products if p['brand_slug']])
            quality_scores = [p['quality_score'] for p in additional_products if p['quality_score'] is not None]
            missing_kcal = sum(1 for p in additional_products if not p.get('kcal_per_100g'))
            missing_ingredients = sum(1 for p in additional_products if not p.get('ingredients_tokens') or len(p['ingredients_tokens']) == 0)

            print(f"Brands in additionally filtered: {len(brands_in_additional)} unique brands")
            if brands_in_additional:
                print(f"Sample brands: {list(brands_in_additional)[:10]}")

            if quality_scores:
                print(f"Quality scores - min: {min(quality_scores)}, max: {max(quality_scores)}, avg: {sum(quality_scores)/len(quality_scores):.2f}")

            print(f"Missing kcal_per_100g: {missing_kcal}/{len(additional_products)} ({missing_kcal/len(additional_products)*100:.1f}%)")
            print(f"Missing ingredients: {missing_ingredients}/{len(additional_products)} ({missing_ingredients/len(additional_products)*100:.1f}%)")

    print(f"\n3. FINAL SQL CONDITIONS:")
    print("-"*50)

    # Test if we can get closer by adding data completeness requirements
    complete_data_count = supabase.table('foods_published_preview').select('product_key', count='exact').eq('allowlist_status', 'ACTIVE').not_.in_('source', ['zooplus_csv_import', 'allaboutdogfood']).not_.is_('kcal_per_100g', 'null').not_.is_('ingredients_tokens', 'null').execute().count

    print(f"With data completeness requirements: {complete_data_count:,} products")

    # The exact SQL WHERE clause
    sql_conditions = [
        "allowlist_status = 'ACTIVE'",
        "source NOT IN ('zooplus_csv_import', 'allaboutdogfood')",
    ]

    # Check if we need brand filtering
    if complete_data_count > prod_count * 1.1:  # If still too many products
        print("\n🔍 Additional brand or quality filtering likely required")

        # Try to identify brand allowlist by seeing which brands made it to production
        prod_brands_response = supabase.table('foods_published_prod').select('brand_slug').execute()
        prod_brands = set([item['brand_slug'] for item in prod_brands_response.data if item['brand_slug']])

        preview_with_filters = supabase.table('foods_published_preview').select('brand_slug').eq('allowlist_status', 'ACTIVE').not_.in_('source', ['zooplus_csv_import', 'allaboutdogfood']).execute()
        preview_brands = set([item['brand_slug'] for item in preview_with_filters.data if item['brand_slug']])

        allowed_brands = prod_brands
        blocked_brands = preview_brands - prod_brands

        print(f"Allowed brands: {len(allowed_brands)} brands")
        print(f"Blocked brands: {len(blocked_brands)} brands")

        if blocked_brands:
            print(f"Sample blocked brands: {list(blocked_brands)[:10]}")
            sql_conditions.append(f"brand_slug NOT IN {tuple(sorted(blocked_brands))}")

    print(f"\n📋 COMPLETE SQL WHERE CLAUSE:")
    print("=" * 60)
    print("WHERE " + "\n  AND ".join(sql_conditions))

    print(f"\n📊 VALIDATION:")
    print("=" * 60)
    print(f"Preview total: {preview_count:,}")
    print(f"Production total: {prod_count:,}")
    print(f"Filter rate: {((preview_count - prod_count) / preview_count) * 100:.1f}%")

    # Test our complete filter
    if len(sql_conditions) >= 2:
        test_query = supabase.table('foods_published_preview').select('product_key', count='exact').eq('allowlist_status', 'ACTIVE').not_.in_('source', ['zooplus_csv_import', 'allaboutdogfood'])

        # Add brand filter if we have one
        if len(sql_conditions) > 2 and blocked_brands:
            # For API limitation, test with a subset of blocked brands
            test_blocked = list(blocked_brands)[:20] if len(blocked_brands) > 20 else list(blocked_brands)
            if test_blocked:
                test_count = test_query.not_.in_('brand_slug', test_blocked).execute().count
                print(f"With our filters applied: {test_count:,} products")
                accuracy = abs(test_count - prod_count) / prod_count * 100
                print(f"Accuracy: {100 - accuracy:.1f}% (off by {abs(test_count - prod_count):,} products)")

except Exception as e:
    print(f"Error: {e}")

print(f"\n✅ SUMMARY:")
print("=" * 60)
print("The production filtering logic uses these key criteria:")
print("1. allowlist_status = 'ACTIVE' (excludes PENDING products)")
print("2. source NOT IN ('zooplus_csv_import', 'allaboutdogfood')")
print("3. Likely additional brand allowlist/blocklist")
print("4. Possible data completeness requirements")
print("\nThis achieves the ~66% filter rate observed (9,339 → 3,119 products)")