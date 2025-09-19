#!/usr/bin/env python3
"""
Safe auto-approval with smaller batches and error handling
"""

import os
import time
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def main():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    print("=" * 60)
    print("SAFE AUTO-APPROVAL EXECUTION")
    print("=" * 60)

    # Get eligible products for auto-approval
    print("Finding eligible products...")

    eligible_products = []
    offset = 0
    batch_size = 1000

    while True:
        response = supabase.table('foods_published_preview')\
            .select('product_key, image_url, ingredients_tokens, protein_percent, fat_percent, kcal_per_100g')\
            .eq('allowlist_status', 'PENDING')\
            .range(offset, offset + batch_size - 1)\
            .execute()

        if not response.data:
            break

        for product in response.data:
            # Apply criteria
            has_image = product.get('image_url') is not None
            has_ingredients = product.get('ingredients_tokens') is not None
            has_nutrients = (
                product.get('protein_percent') is not None or
                product.get('fat_percent') is not None or
                product.get('kcal_per_100g') is not None
            )

            if has_image and has_ingredients and has_nutrients:
                eligible_products.append(product['product_key'])

        if len(response.data) < batch_size:
            break
        offset += batch_size

    print(f"Found {len(eligible_products):,} eligible products")

    if len(eligible_products) == 0:
        print("No products to approve")
        return

    # Execute in small batches with retries
    update_batch_size = 100  # Much smaller batches
    approved_count = 0
    failed_count = 0

    for i in range(0, len(eligible_products), update_batch_size):
        batch = eligible_products[i:i + update_batch_size]
        batch_num = (i // update_batch_size) + 1
        total_batches = (len(eligible_products) + update_batch_size - 1) // update_batch_size

        print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} products)...")

        # Retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = supabase.table('foods_published_preview')\
                    .update({'allowlist_status': 'ACTIVE'})\
                    .in_('product_key', batch)\
                    .execute()

                approved_count += len(batch)
                print(f"  ✅ Approved {len(batch)} products (Total: {approved_count:,})")
                break

            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"  ⚠️  Attempt {attempt + 1} failed, retrying in 2s: {e}")
                    time.sleep(2)
                else:
                    print(f"  ❌ Batch failed after {max_retries} attempts: {e}")
                    failed_count += len(batch)

        # Small delay between batches
        time.sleep(1)

    print(f"\n" + "=" * 60)
    print("EXECUTION COMPLETE")
    print("=" * 60)
    print(f"Successfully approved: {approved_count:,} products")
    print(f"Failed to approve: {failed_count:,} products")

    # Final verification
    print(f"\nVerifying results...")

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

    final_active = sum(1 for p in total_data if p['allowlist_status'] == 'ACTIVE')
    final_pending = sum(1 for p in total_data if p['allowlist_status'] == 'PENDING')

    print(f"Final counts:")
    print(f"  ACTIVE: {final_active:,}")
    print(f"  PENDING: {final_pending:,}")
    print(f"  Production increase: +{final_active - 3119:,} products")

if __name__ == "__main__":
    main()