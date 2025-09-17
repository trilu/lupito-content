#!/usr/bin/env python3
"""
Auto-approve products meeting quality criteria
Aggressive pipeline simplification for pre-launch
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def main():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    print("=" * 60)
    print("AUTO-APPROVAL ANALYSIS & EXECUTION")
    print("=" * 60)

    # 1. Get current counts (with pagination)
    print("\n1. Current Status:")

    total_data = []
    offset = 0
    batch_size = 1000

    while True:
        response = supabase.table('foods_published_preview').select('allowlist_status').range(offset, offset + batch_size - 1).execute()
        if not response.data:
            break

        total_data.extend(response.data)
        if len(response.data) < batch_size:
            break
        offset += batch_size

    active_count = sum(1 for p in total_data if p['allowlist_status'] == 'ACTIVE')
    pending_count = sum(1 for p in total_data if p['allowlist_status'] == 'PENDING')

    print(f"   Current ACTIVE: {active_count:,}")
    print(f"   Current PENDING: {pending_count:,}")
    print(f"   Total: {len(total_data):,}")

    # 2. Analyze PENDING products for auto-approval eligibility (with pagination)
    print("\n2. Analyzing PENDING products for auto-approval...")

    pending_products = []
    offset = 0

    while True:
        response = supabase.table('foods_published_preview')\
            .select('product_key, brand, image_url, ingredients_tokens, protein_percent, fat_percent, kcal_per_100g')\
            .eq('allowlist_status', 'PENDING')\
            .range(offset, offset + batch_size - 1)\
            .execute()

        if not response.data:
            break

        pending_products.extend(response.data)
        if len(response.data) < batch_size:
            break
        offset += batch_size

    print(f"   Retrieved {len(pending_products):,} PENDING products for analysis")

    # 3. Apply auto-approval criteria
    eligible_products = []

    for product in pending_products:
        # Check criteria:
        # - Has image
        has_image = product.get('image_url') is not None

        # - Has ingredients
        has_ingredients = product.get('ingredients_tokens') is not None

        # - Has nutrient data (any of the three)
        has_nutrients = (
            product.get('protein_percent') is not None or
            product.get('fat_percent') is not None or
            product.get('kcal_per_100g') is not None
        )

        if has_image and has_ingredients and has_nutrients:
            eligible_products.append(product['product_key'])

    print(f"\n3. Auto-Approval Analysis:")
    print(f"   Eligible for auto-approval: {len(eligible_products):,}")
    print(f"   Would remain PENDING: {len(pending_products) - len(eligible_products):,}")
    print(f"   New production total: {active_count + len(eligible_products):,}")

    # 4. Show breakdown by criteria
    image_missing = sum(1 for p in pending_products if p.get('image_url') is None)
    ingredients_missing = sum(1 for p in pending_products if p.get('ingredients_tokens') is None)
    nutrients_missing = sum(1 for p in pending_products if
                           p.get('protein_percent') is None and
                           p.get('fat_percent') is None and
                           p.get('kcal_per_100g') is None)

    print(f"\n4. Missing Data Analysis (PENDING products):")
    print(f"   Missing images: {image_missing:,}")
    print(f"   Missing ingredients: {ingredients_missing:,}")
    print(f"   Missing nutrients: {nutrients_missing:,}")

    # 5. Brand analysis
    brands_affected = set(p['brand'] for p in pending_products if p['product_key'] in eligible_products)
    print(f"\n5. Brand Impact:")
    print(f"   Brands getting products approved: {len(brands_affected)}")

    # 6. Execute auto-approval
    if len(eligible_products) > 0:
        proceed = input(f"\nExecute auto-approval for {len(eligible_products):,} products? (y/n): ")

        if proceed.lower() == 'y':
            print(f"\n6. Executing auto-approval...")

            # Update in batches of 1000
            batch_size = 1000
            approved_count = 0

            for i in range(0, len(eligible_products), batch_size):
                batch = eligible_products[i:i + batch_size]

                try:
                    response = supabase.table('foods_published_preview')\
                        .update({'allowlist_status': 'ACTIVE'})\
                        .in_('product_key', batch)\
                        .execute()

                    approved_count += len(batch)
                    print(f"   Approved batch: {len(batch)} products (Total: {approved_count:,})")

                except Exception as e:
                    print(f"   Error in batch: {e}")
                    break

            print(f"\n✅ Auto-approval complete!")
            print(f"   Products approved: {approved_count:,}")

            # 7. Verify results
            print(f"\n7. Verification:")

            final_response = supabase.table('foods_published_preview').select('allowlist_status').execute()
            final_data = final_response.data

            final_active = sum(1 for p in final_data if p['allowlist_status'] == 'ACTIVE')
            final_pending = sum(1 for p in final_data if p['allowlist_status'] == 'PENDING')

            print(f"   New ACTIVE count: {final_active:,} (was {active_count:,})")
            print(f"   New PENDING count: {final_pending:,} (was {pending_count:,})")
            print(f"   Production increase: +{final_active - active_count:,} products")

        else:
            print("Auto-approval cancelled")
    else:
        print("No products eligible for auto-approval")

if __name__ == "__main__":
    main()