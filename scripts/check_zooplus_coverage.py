#!/usr/bin/env python3
"""
Check Zooplus coverage specifically
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def main():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Total Zooplus products
    total_zooplus = supabase.table('foods_canonical').select(
        'product_key', count='exact'
    ).ilike('product_url', '%zooplus.com%').execute()
    
    # Zooplus with ingredients
    zooplus_with = supabase.table('foods_canonical').select(
        'product_key', count='exact'
    ).ilike('product_url', '%zooplus.com%')\
    .not_.is_('ingredients_raw', 'null').execute()
    
    # Zooplus without ingredients
    zooplus_without = supabase.table('foods_canonical').select(
        'product_key', count='exact'
    ).ilike('product_url', '%zooplus.com%')\
    .is_('ingredients_raw', 'null').execute()
    
    total = total_zooplus.count
    with_ing = zooplus_with.count
    without_ing = zooplus_without.count
    pct = (with_ing / total * 100) if total > 0 else 0
    
    print(f"\n🐾 ZOOPLUS COVERAGE STATUS")
    print("=" * 50)
    print(f"Total Zooplus products: {total:,}")
    print(f"With ingredients: {with_ing:,} ({pct:.1f}%)")
    print(f"Without ingredients: {without_ing:,}")
    print(f"\nNeed for 95%: {int(total * 0.95) - with_ing:,} more products")
    
    # Calculate progress for 235 target
    if without_ing <= 235:
        scraped_from_235 = 235 - without_ing
        print(f"\n📊 Progress on 235 remaining:")
        print(f"   Scraped: {scraped_from_235}/235 ({scraped_from_235/235*100:.1f}%)")

if __name__ == "__main__":
    main()