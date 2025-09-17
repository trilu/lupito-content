#!/usr/bin/env python3
"""
Detailed analysis of production filtering logic based on initial findings.

Key findings from initial analysis:
1. Preview: 9,339 products → Production: 3,119 products (66.6% filter rate)
2. Source filtering: 'zooplus_csv_import' and 'allaboutdogfood' sources missing from production
3. Quality score differences: Preview mean 2.27, Production mean 2.38
4. Brand filtering: Many brands completely missing from production
5. Data completeness: Production has higher completion rates for key fields
"""

import os
from supabase import create_client
from dotenv import load_dotenv
from collections import Counter

load_dotenv()

# Initialize Supabase
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(url, key)

print("="*80)
print("DETAILED PRODUCTION FILTERING LOGIC ANALYSIS")
print("="*80)

# Based on initial findings, let's investigate specific hypotheses

# Hypothesis 1: Source-based filtering
print("\n1. SOURCE-BASED FILTERING ANALYSIS:")
print("-"*50)

try:
    # Get full source distribution from preview
    preview_sources = supabase.table('foods_published_preview').select('source').execute()
    preview_source_counts = Counter([item['source'] for item in preview_sources.data])

    # Get full source distribution from production
    prod_sources = supabase.table('foods_published_prod').select('source').execute()
    prod_source_counts = Counter([item['source'] for item in prod_sources.data])

    print("Source distribution in PREVIEW:")
    for source, count in preview_source_counts.most_common():
        print(f"  {source}: {count:,} products")

    print("\nSource distribution in PRODUCTION:")
    for source, count in prod_source_counts.most_common():
        print(f"  {source}: {count:,} products")

    # Calculate filtering by source
    print("\nFILTERING BY SOURCE:")
    for source in preview_source_counts:
        preview_count = preview_source_counts[source]
        prod_count = prod_source_counts.get(source, 0)
        filter_rate = ((preview_count - prod_count) / preview_count) * 100 if preview_count > 0 else 100

        print(f"  {source}:")
        print(f"    Preview: {preview_count:,} → Production: {prod_count:,} ({filter_rate:.1f}% filtered)")

        if filter_rate == 100:
            print(f"    ❌ COMPLETELY FILTERED OUT")
        elif filter_rate > 80:
            print(f"    🔴 HEAVILY FILTERED")
        elif filter_rate > 50:
            print(f"    🟡 MODERATELY FILTERED")
        else:
            print(f"    🟢 LIGHTLY FILTERED")

except Exception as e:
    print(f"Error analyzing sources: {e}")

# Hypothesis 2: Quality score thresholds
print("\n\n2. QUALITY SCORE THRESHOLD ANALYSIS:")
print("-"*50)

try:
    # Get quality score distributions
    preview_scores = supabase.table('foods_published_preview').select('quality_score').execute()
    prod_scores = supabase.table('foods_published_prod').select('quality_score').execute()

    preview_score_counts = Counter([item['quality_score'] for item in preview_scores.data if item['quality_score'] is not None])
    prod_score_counts = Counter([item['quality_score'] for item in prod_scores.data if item['quality_score'] is not None])

    print("Quality score distribution:")
    print("Score | Preview  | Production | Filter Rate")
    print("------|----------|------------|------------")

    for score in sorted(set(list(preview_score_counts.keys()) + list(prod_score_counts.keys()))):
        preview_count = preview_score_counts.get(score, 0)
        prod_count = prod_score_counts.get(score, 0)
        filter_rate = ((preview_count - prod_count) / preview_count) * 100 if preview_count > 0 else 0

        print(f"{score:5.1f} | {preview_count:8,} | {prod_count:10,} | {filter_rate:10.1f}%")

except Exception as e:
    print(f"Error analyzing quality scores: {e}")

# Hypothesis 3: Data completeness requirements
print("\n\n3. DATA COMPLETENESS ANALYSIS:")
print("-"*50)

key_fields = ['kcal_per_100g', 'ingredients_tokens', 'protein_percent', 'fat_percent', 'life_stage', 'form']

try:
    # Get completeness data for preview
    preview_data = supabase.table('foods_published_preview').select(','.join(key_fields + ['product_key'])).execute()
    preview_completeness = {}

    for field in key_fields:
        non_null_count = sum(1 for item in preview_data.data if item.get(field) is not None and item.get(field) != '')
        preview_completeness[field] = (non_null_count / len(preview_data.data)) * 100

    # Get completeness data for production
    prod_data = supabase.table('foods_published_prod').select(','.join(key_fields + ['product_key'])).execute()
    prod_completeness = {}

    for field in key_fields:
        non_null_count = sum(1 for item in prod_data.data if item.get(field) is not None and item.get(field) != '')
        prod_completeness[field] = (non_null_count / len(prod_data.data)) * 100

    print("Field completeness comparison:")
    print("Field                 | Preview | Production | Difference")
    print("----------------------|---------|------------|----------")

    for field in key_fields:
        preview_pct = preview_completeness[field]
        prod_pct = prod_completeness[field]
        diff = prod_pct - preview_pct

        print(f"{field:21} | {preview_pct:6.1f}% | {prod_pct:9.1f}% | {diff:+8.1f}%")

    # Special analysis for ingredients
    print("\nIngredients analysis:")
    preview_with_ingredients = sum(1 for item in preview_data.data
                                 if item.get('ingredients_tokens') and len(item['ingredients_tokens']) > 0)
    prod_with_ingredients = sum(1 for item in prod_data.data
                              if item.get('ingredients_tokens') and len(item['ingredients_tokens']) > 0)

    print(f"Preview with ingredients: {preview_with_ingredients:,}/{len(preview_data.data):,} ({(preview_with_ingredients/len(preview_data.data)*100):.1f}%)")
    print(f"Production with ingredients: {prod_with_ingredients:,}/{len(prod_data.data):,} ({(prod_with_ingredients/len(prod_data.data)*100):.1f}%)")

except Exception as e:
    print(f"Error analyzing completeness: {e}")

# Hypothesis 4: Brand allowlist/blocklist
print("\n\n4. BRAND ALLOWLIST ANALYSIS:")
print("-"*50)

try:
    # Get brand distributions
    preview_brands = supabase.table('foods_published_preview').select('brand_slug').execute()
    prod_brands = supabase.table('foods_published_prod').select('brand_slug').execute()

    preview_brand_counts = Counter([item['brand_slug'] for item in preview_brands.data if item['brand_slug']])
    prod_brand_counts = Counter([item['brand_slug'] for item in prod_brands.data if item['brand_slug']])

    all_brands = set(list(preview_brand_counts.keys()) + list(prod_brand_counts.keys()))

    # Categorize brands
    completely_filtered_brands = []
    heavily_filtered_brands = []
    allowed_brands = []

    for brand in all_brands:
        preview_count = preview_brand_counts.get(brand, 0)
        prod_count = prod_brand_counts.get(brand, 0)

        if preview_count > 0:
            filter_rate = ((preview_count - prod_count) / preview_count) * 100

            if filter_rate == 100:
                completely_filtered_brands.append((brand, preview_count))
            elif filter_rate > 80:
                heavily_filtered_brands.append((brand, preview_count, prod_count, filter_rate))
            else:
                allowed_brands.append((brand, preview_count, prod_count, filter_rate))

    print(f"COMPLETELY FILTERED BRANDS ({len(completely_filtered_brands)}):")
    for brand, count in sorted(completely_filtered_brands, key=lambda x: x[1], reverse=True)[:20]:
        print(f"  {brand}: {count:,} products (100% filtered)")

    if len(completely_filtered_brands) > 20:
        print(f"  ... and {len(completely_filtered_brands) - 20} more brands")

    print(f"\nHEAVILY FILTERED BRANDS ({len(heavily_filtered_brands)}):")
    for brand, preview_count, prod_count, filter_rate in sorted(heavily_filtered_brands, key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {brand}: {preview_count:,} → {prod_count:,} ({filter_rate:.1f}% filtered)")

    print(f"\nTOP ALLOWED BRANDS:")
    for brand, preview_count, prod_count, filter_rate in sorted(allowed_brands, key=lambda x: x[2], reverse=True)[:15]:
        print(f"  {brand}: {preview_count:,} → {prod_count:,} ({filter_rate:.1f}% filtered)")

except Exception as e:
    print(f"Error analyzing brands: {e}")

# Hypothesis 5: Allowlist status field
print("\n\n5. ALLOWLIST STATUS ANALYSIS:")
print("-"*50)

try:
    # Check allowlist_status field distribution
    preview_allowlist = supabase.table('foods_published_preview').select('allowlist_status').execute()
    prod_allowlist = supabase.table('foods_published_prod').select('allowlist_status').execute()

    preview_status_counts = Counter([item['allowlist_status'] for item in preview_allowlist.data])
    prod_status_counts = Counter([item['allowlist_status'] for item in prod_allowlist.data])

    print("Allowlist status distribution:")
    print("Status      | Preview  | Production | Filter Rate")
    print("------------|----------|------------|------------")

    all_statuses = set(list(preview_status_counts.keys()) + list(prod_status_counts.keys()))

    for status in sorted(all_statuses, key=lambda x: str(x)):
        preview_count = preview_status_counts.get(status, 0)
        prod_count = prod_status_counts.get(status, 0)
        filter_rate = ((preview_count - prod_count) / preview_count) * 100 if preview_count > 0 else 0

        status_str = str(status) if status is not None else 'NULL'
        print(f"{status_str:11} | {preview_count:8,} | {prod_count:10,} | {filter_rate:10.1f}%")

except Exception as e:
    print(f"Error analyzing allowlist status: {e}")

print("\n" + "="*80)
print("FILTERING LOGIC CONCLUSIONS")
print("="*80)

print("\nBased on the analysis, the production filtering appears to use:")
print("1. 🚫 SOURCE-BASED FILTERING:")
print("   - Completely blocks: 'zooplus_csv_import', 'allaboutdogfood'")
print("   - Heavily filters other sources")

print("\n2. 📊 QUALITY SCORE THRESHOLDS:")
print("   - Likely minimum quality score requirement")
print("   - Production has higher average quality scores")

print("\n3. 🏷️ BRAND ALLOWLIST/BLOCKLIST:")
print("   - Many brands completely filtered out")
print("   - Suggests a strict brand allowlist system")

print("\n4. ✅ DATA COMPLETENESS REQUIREMENTS:")
print("   - Higher completion rates in production")
print("   - Likely requires complete nutrition data")

print("\n5. 🔐 ALLOWLIST STATUS FIELD:")
print("   - Uses 'allowlist_status' field for filtering")
print("   - Check specific status values for criteria")

print("\nTo implement similar filtering, use SQL conditions like:")
print("WHERE allowlist_status = 'approved'")
print("  AND source NOT IN ('zooplus_csv_import', 'allaboutdogfood')")
print("  AND quality_score >= [threshold]")
print("  AND kcal_per_100g IS NOT NULL")
print("  AND ingredients_tokens IS NOT NULL AND array_length(ingredients_tokens, 1) > 0")
print("  AND brand_slug IN ([allowlist])")