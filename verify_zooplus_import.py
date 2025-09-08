#!/usr/bin/env python3
"""
Verify Zooplus import results
"""
import os
from supabase import create_client

# Supabase configuration
SUPABASE_URL = 'https://cibjeqgftuxuezarjsdl.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNpYmplcWdmdHV4dWV6YXJqc2RsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1Mzg1NTY2NywiZXhwIjoyMDY5NDMxNjY3fQ.ngzgvYr2zXisvkz03F86zNWPRHP0tEMX0gQPBm2z_jk'

def main():
    # Connect to Supabase
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Get Zooplus products
    result = supabase.table('food_candidates_sc').select('*').eq('retailer_source', 'zooplus').execute()
    products = result.data
    
    print("=" * 70)
    print("ZOOPLUS IMPORT VERIFICATION")
    print("=" * 70)
    print(f"\n✅ Total products imported: {len(products)}")
    
    # Check for duplicates
    seen = set()
    duplicates = []
    brands = set()
    
    for p in products:
        key = (p['brand'], p['product_name'])
        if key in seen:
            duplicates.append(key)
        seen.add(key)
        brands.add(p['brand'])
    
    if duplicates:
        print(f"⚠️  Found {len(duplicates)} duplicate products")
        for brand, name in duplicates[:5]:
            print(f"   - {brand}: {name[:50]}")
    else:
        print("✅ No duplicate products found")
    
    print(f"\n📊 Unique brands: {len(brands)}")
    
    # Nutrition completeness
    with_protein = sum(1 for p in products if p.get('protein_percent'))
    with_fat = sum(1 for p in products if p.get('fat_percent'))
    with_fiber = sum(1 for p in products if p.get('fiber_percent'))
    with_moisture = sum(1 for p in products if p.get('moisture_percent'))
    with_ash = sum(1 for p in products if p.get('ash_percent'))
    
    print("\n📈 Nutrition Data Completeness:")
    print(f"   Protein:  {with_protein:4d}/{len(products)} ({with_protein/len(products)*100:5.1f}%)")
    print(f"   Fat:      {with_fat:4d}/{len(products)} ({with_fat/len(products)*100:5.1f}%)")
    print(f"   Fiber:    {with_fiber:4d}/{len(products)} ({with_fiber/len(products)*100:5.1f}%)")
    print(f"   Moisture: {with_moisture:4d}/{len(products)} ({with_moisture/len(products)*100:5.1f}%)")
    print(f"   Ash:      {with_ash:4d}/{len(products)} ({with_ash/len(products)*100:5.1f}%)")
    
    # Pack sizes
    with_pack_sizes = sum(1 for p in products if p.get('pack_sizes') and len(p['pack_sizes']) > 0)
    multi_pack = sum(1 for p in products if p.get('pack_sizes') and len(p['pack_sizes']) > 1)
    
    print(f"\n📦 Pack Sizes:")
    print(f"   With sizes: {with_pack_sizes}/{len(products)} ({with_pack_sizes/len(products)*100:.1f}%)")
    print(f"   Multi-pack: {multi_pack} products with multiple sizes")
    
    # Show sample products with multiple pack sizes
    multi_pack_products = [p for p in products if p.get('pack_sizes') and len(p['pack_sizes']) > 1]
    if multi_pack_products:
        print("\n🔍 Sample products with multiple pack sizes:")
        for p in multi_pack_products[:3]:
            print(f"   {p['brand']} - {p['product_name'][:40]}...")
            print(f"      Sizes: {', '.join(p['pack_sizes'])}")
    
    # Top brands
    from collections import Counter
    brand_counts = Counter(p['brand'] for p in products)
    
    print("\n🏆 Top 10 Brands by Product Count:")
    for brand, count in brand_counts.most_common(10):
        print(f"   {brand:30s}: {count:3d} products")
    
    print("\n" + "=" * 70)
    print("✅ IMPORT VERIFICATION COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    main()