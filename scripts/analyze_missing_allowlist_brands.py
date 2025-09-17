#!/usr/bin/env python3
"""
Analyze why 75 brands from PENDING products are missing from allowlist
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

def analyze_missing_allowlist_brands():
    print('=== MISSING ALLOWLIST BRANDS ANALYSIS ===')
    print()

    # Get all PENDING products with their brand_slugs
    response = supabase.table('foods_published_preview').select('brand_slug, brand, image_url, ingredients_tokens, protein_percent, fat_percent, kcal_per_100g, source').eq('allowlist_status', 'PENDING').execute()
    pending_products = response.data

    # Get unique brand_slugs from PENDING products
    pending_brand_slugs = list(set([p['brand_slug'] for p in pending_products if p['brand_slug']]))

    print(f'Unique brand_slugs in PENDING: {len(pending_brand_slugs)}')

    # Check which ones are missing from allowlist
    if pending_brand_slugs:
        allowlist_response = supabase.table('brand_allowlist').select('brand_slug, status').in_('brand_slug', pending_brand_slugs).execute()
        allowlist_brands = {b['brand_slug']: b['status'] for b in allowlist_response.data}

        missing_brands = [slug for slug in pending_brand_slugs if slug not in allowlist_brands]

        print(f'Brands missing from allowlist: {len(missing_brands)}')
        print()

        if missing_brands:
            print('🔍 Analysis of Missing Brands:')

            for brand_slug in missing_brands[:10]:  # Show first 10
                # Get products for this brand
                brand_products = [p for p in pending_products if p['brand_slug'] == brand_slug]

                print(f'\n📦 Brand: {brand_slug}')
                print(f'   Products: {len(brand_products)}')
                print(f'   Original Brand Names: {list(set([p["brand"] for p in brand_products]))}')
                print(f'   Sources: {list(set([p["source"] for p in brand_products]))}')

                # Check quality criteria for this brand
                products_with_images = sum(1 for p in brand_products if p.get('image_url'))
                products_with_ingredients = sum(1 for p in brand_products if p.get('ingredients_tokens'))
                products_with_nutrition = sum(1 for p in brand_products if (p.get('protein_percent') or p.get('fat_percent') or p.get('kcal_per_100g')))

                print(f'   Quality Check:')
                print(f'     - With Images: {products_with_images}/{len(brand_products)} ({products_with_images/len(brand_products)*100:.1f}%)')
                print(f'     - With Ingredients: {products_with_ingredients}/{len(brand_products)} ({products_with_ingredients/len(brand_products)*100:.1f}%)')
                print(f'     - With Nutrition: {products_with_nutrition}/{len(brand_products)} ({products_with_nutrition/len(brand_products)*100:.1f}%)')

                # Check if any product meets our quality criteria
                quality_products = 0
                for p in brand_products:
                    has_image = bool(p.get('image_url'))
                    has_ingredients = bool(p.get('ingredients_tokens'))
                    has_nutrition = bool(p.get('protein_percent') or p.get('fat_percent') or p.get('kcal_per_100g'))

                    if has_image and has_ingredients and has_nutrition:
                        quality_products += 1

                print(f'     - Meeting ALL criteria: {quality_products}/{len(brand_products)} ({quality_products/len(brand_products)*100:.1f}%)')

                if quality_products == 0:
                    print(f'     ❌ WHY NOT APPROVED: No products meet all 3 criteria (image + ingredients + nutrition)')
                else:
                    print(f'     ⚠️  POTENTIAL ISSUE: {quality_products} products meet criteria but brand not approved')

        print('\n' + '='*60)
        print('📊 SUMMARY OF WHY BRANDS WEREN\'T AUTO-APPROVED:')
        print()

        # Analyze all missing brands to understand patterns
        total_missing_brands = len(missing_brands)
        brands_with_no_quality = 0
        brands_with_some_quality = 0
        brands_with_full_quality = 0

        for brand_slug in missing_brands:
            brand_products = [p for p in pending_products if p['brand_slug'] == brand_slug]

            quality_products = 0
            for p in brand_products:
                has_image = bool(p.get('image_url'))
                has_ingredients = bool(p.get('ingredients_tokens'))
                has_nutrition = bool(p.get('protein_percent') or p.get('fat_percent') or p.get('kcal_per_100g'))

                if has_image and has_ingredients and has_nutrition:
                    quality_products += 1

            if quality_products == 0:
                brands_with_no_quality += 1
            elif quality_products < len(brand_products):
                brands_with_some_quality += 1
            else:
                brands_with_full_quality += 1

        print(f'Brands with NO quality products: {brands_with_no_quality} ({brands_with_no_quality/total_missing_brands*100:.1f}%)')
        print(f'Brands with SOME quality products: {brands_with_some_quality} ({brands_with_some_quality/total_missing_brands*100:.1f}%)')
        print(f'Brands with ALL quality products: {brands_with_full_quality} ({brands_with_full_quality/total_missing_brands*100:.1f}%)')

        print()
        print('🎯 CONCLUSION:')
        if brands_with_no_quality == total_missing_brands:
            print('✅ AUTO-APPROVAL WORKING CORRECTLY: All missing brands lack quality products')
        elif brands_with_full_quality > 0:
            print(f'⚠️  POTENTIAL ISSUE: {brands_with_full_quality} brands have quality products but weren\'t approved')
        else:
            print('🔍 MIXED QUALITY: Brands have some but not all products meeting criteria')

if __name__ == '__main__':
    analyze_missing_allowlist_brands()