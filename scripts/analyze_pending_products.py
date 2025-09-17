#!/usr/bin/env python3
"""
Analyze PENDING products to understand blocking patterns
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

def analyze_pending_products():
    print('=== PENDING PRODUCTS ANALYSIS ===')
    print()

    # Get all PENDING products
    response = supabase.table('foods_published_preview').select('*').eq('allowlist_status', 'PENDING').execute()
    pending_products = response.data

    print(f'Total PENDING products: {len(pending_products)}')
    print()

    # Analyze by source
    sources = {}
    for p in pending_products:
        source = p.get('source', 'Unknown')
        sources[source] = sources.get(source, 0) + 1

    print('📊 PENDING by Source:')
    for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
        pct = count * 100.0 / len(pending_products)
        print(f'  {source}: {count} ({pct:.1f}%)')
    print()

    # Analyze missing data patterns
    missing_patterns = {
        'image_url': 0,
        'ingredients_tokens': 0,
        'protein_percent': 0,
        'fat_percent': 0,
        'kcal_per_100g': 0,
        'brand_slug': 0
    }

    for p in pending_products:
        if not p.get('image_url'):
            missing_patterns['image_url'] += 1
        if not p.get('ingredients_tokens'):
            missing_patterns['ingredients_tokens'] += 1
        if not p.get('protein_percent'):
            missing_patterns['protein_percent'] += 1
        if not p.get('fat_percent'):
            missing_patterns['fat_percent'] += 1
        if not p.get('kcal_per_100g'):
            missing_patterns['kcal_per_100g'] += 1
        if not p.get('brand_slug'):
            missing_patterns['brand_slug'] += 1

    print('🔍 Missing Data in PENDING Products:')
    for field, count in sorted(missing_patterns.items(), key=lambda x: x[1], reverse=True):
        pct = count * 100.0 / len(pending_products)
        print(f'  Missing {field}: {count} ({pct:.1f}%)')
    print()

    # Analyze brand distribution
    brands = {}
    for p in pending_products:
        brand = p.get('brand', 'Unknown')
        brands[brand] = brands.get(brand, 0) + 1

    print('🏷️  Top 10 Brands in PENDING:')
    for brand, count in sorted(brands.items(), key=lambda x: x[1], reverse=True)[:10]:
        pct = count * 100.0 / len(pending_products)
        print(f'  {brand}: {count} products ({pct:.1f}%)')
    print()

    # Analyze data quality gaps - what specifically blocks each product
    blocking_reasons = {
        'missing_images_only': 0,
        'missing_ingredients_only': 0,
        'missing_nutrition_only': 0,
        'missing_images_ingredients': 0,
        'missing_images_nutrition': 0,
        'missing_ingredients_nutrition': 0,
        'missing_all_three': 0,
        'unknown_reason': 0
    }

    for p in pending_products:
        has_image = bool(p.get('image_url'))
        has_ingredients = bool(p.get('ingredients_tokens'))
        has_nutrition = bool(p.get('protein_percent') or p.get('fat_percent') or p.get('kcal_per_100g'))

        if not has_image and not has_ingredients and not has_nutrition:
            blocking_reasons['missing_all_three'] += 1
        elif not has_image and not has_ingredients:
            blocking_reasons['missing_images_ingredients'] += 1
        elif not has_image and not has_nutrition:
            blocking_reasons['missing_images_nutrition'] += 1
        elif not has_ingredients and not has_nutrition:
            blocking_reasons['missing_ingredients_nutrition'] += 1
        elif not has_image:
            blocking_reasons['missing_images_only'] += 1
        elif not has_ingredients:
            blocking_reasons['missing_ingredients_only'] += 1
        elif not has_nutrition:
            blocking_reasons['missing_nutrition_only'] += 1
        else:
            blocking_reasons['unknown_reason'] += 1

    print('🚫 Blocking Reasons Analysis:')
    for reason, count in sorted(blocking_reasons.items(), key=lambda x: x[1], reverse=True):
        if count > 0:
            pct = count * 100.0 / len(pending_products)
            print(f'  {reason.replace("_", " ").title()}: {count} ({pct:.1f}%)')
    print()

    # Brand allowlist status check
    print('🔍 Brand Allowlist Analysis:')
    brand_slugs = [p.get('brand_slug') for p in pending_products if p.get('brand_slug')]
    unique_brand_slugs = list(set(brand_slugs))

    if unique_brand_slugs:
        allowlist_response = supabase.table('brand_allowlist').select('brand_slug, status').in_('brand_slug', unique_brand_slugs).execute()
        allowlist_brands = {b['brand_slug']: b['status'] for b in allowlist_response.data}

        allowlist_status = {}
        missing_from_allowlist = 0

        for brand_slug in unique_brand_slugs:
            if brand_slug in allowlist_brands:
                status = allowlist_brands[brand_slug]
                allowlist_status[status] = allowlist_status.get(status, 0) + 1
            else:
                missing_from_allowlist += 1

        print(f'  Brands missing from allowlist: {missing_from_allowlist}')
        for status, count in allowlist_status.items():
            print(f'  Brands with {status} status: {count}')

    print()

    # Sample pending products for manual review
    print('📋 Sample PENDING Products (first 5):')
    for i, p in enumerate(pending_products[:5]):
        print(f'  {i+1}. {p.get("brand", "Unknown")} - {p.get("product_name", "Unknown")}')
        print(f'     Source: {p.get("source", "Unknown")}')
        print(f'     Image: {"✅" if p.get("image_url") else "❌"}')
        print(f'     Ingredients: {"✅" if p.get("ingredients_tokens") else "❌"}')
        print(f'     Nutrition: {"✅" if (p.get("protein_percent") or p.get("fat_percent") or p.get("kcal_per_100g")) else "❌"}')
        print(f'     Brand Slug: {p.get("brand_slug", "Missing")}')
        print()

if __name__ == '__main__':
    analyze_pending_products()