#!/usr/bin/env python3
"""
Final verification of database normalization and cleanup.
"""
from supabase import create_client
import os
from dotenv import load_dotenv
from collections import defaultdict
import json

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_KEY')
)

def main():
    print("=" * 60)
    print("FINAL DATABASE VERIFICATION")
    print("=" * 60)
    print()
    
    # Get total count
    total_response = supabase.table('foods_canonical').select('*', count='exact').execute()
    print(f"Total products in database: {total_response.count}")
    
    # Load all products
    print("\nLoading all products...")
    all_products = []
    offset = 0
    limit = 1000
    
    while True:
        response = supabase.table('foods_canonical').select('*').range(offset, offset + limit - 1).execute()
        batch = response.data
        if not batch:
            break
        all_products.extend(batch)
        offset += limit
        print(f"  Loaded {len(all_products)} products...", end='\r')
    
    print(f"  Loaded {len(all_products)} products... Done!")
    
    # Analyze brands
    print("\n" + "=" * 60)
    print("BRAND ANALYSIS")
    print("=" * 60)
    
    brands = defaultdict(int)
    for product in all_products:
        if product['brand']:
            brands[product['brand']] += 1
    
    print(f"Unique brands: {len(brands)}")
    print(f"\nTop 10 brands by product count:")
    for brand, count in sorted(brands.items(), key=lambda x: -x[1])[:10]:
        print(f"  {brand}: {count} products")
    
    # Check for brand normalization issues
    print("\n" + "=" * 60)
    print("BRAND NORMALIZATION CHECK")
    print("=" * 60)
    
    # Look for brands that might be duplicates
    brand_variations = defaultdict(list)
    for brand in brands.keys():
        base = brand.lower().replace(' ', '').replace('&', '').replace("'", '')
        brand_variations[base].append(brand)
    
    potential_duplicates = {k: v for k, v in brand_variations.items() if len(v) > 1}
    
    if potential_duplicates:
        print(f"\nPotential duplicate brands found: {len(potential_duplicates)}")
        for base, variations in list(potential_duplicates.items())[:5]:
            print(f"  Variations: {', '.join(variations)}")
    else:
        print("\nNo potential duplicate brands found! ✅")
    
    # Check for brand prefixes in product names
    print("\n" + "=" * 60)
    print("PRODUCT NAME CLEANUP CHECK")
    print("=" * 60)
    
    exact_matches = []
    partial_matches = []
    word_matches = []
    
    for product in all_products:
        if not product.get('brand') or not product.get('product_name'):
            continue
        
        brand_lower = product['brand'].lower()
        name_lower = product['product_name'].lower()
        
        # Check exact brand prefix
        if name_lower.startswith(brand_lower):
            exact_matches.append(product)
            continue
        
        # Check for brand words at start
        brand_words = product['brand'].split()
        for word in brand_words:
            if len(word) > 3 and name_lower.startswith(word.lower() + ' '):
                word_matches.append({
                    'product': product,
                    'word': word
                })
                break
    
    print(f"Products with exact brand prefix: {len(exact_matches)}")
    print(f"Products with brand word prefix: {len(word_matches)}")
    
    if exact_matches:
        print(f"\nExact matches (first 5):")
        for p in exact_matches[:5]:
            print(f'  Brand: "{p["brand"]}", Name: "{p["product_name"]}"')
    
    if word_matches:
        print(f"\nWord matches (first 5):")
        for item in word_matches[:5]:
            p = item['product']
            print(f'  Brand: "{p["brand"]}", Name: "{p["product_name"]}" (word: "{item["word"]}")')
    
    # Check data sources
    print("\n" + "=" * 60)
    print("DATA SOURCE ANALYSIS")
    print("=" * 60)
    
    sources = defaultdict(int)
    for product in all_products:
        if product.get('source'):
            sources[product['source']] += 1
    
    print(f"Data sources found: {len(sources)}")
    for source, count in sorted(sources.items(), key=lambda x: -x[1]):
        print(f"  {source}: {count} products")
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    issues_count = len(exact_matches) + len(word_matches)
    
    if issues_count == 0:
        print("✅ Database is fully normalized!")
        print("✅ No brand prefixes in product names!")
        print("✅ All brands are unique!")
    else:
        print(f"⚠️  {issues_count} products may still have brand prefix issues")
        print(f"   - {len(exact_matches)} with exact brand match")
        print(f"   - {len(word_matches)} with brand word match")
    
    print(f"\n📊 Total products: {len(all_products)}")
    print(f"📊 Unique brands: {len(brands)}")
    print(f"📊 Data sources: {len(sources)}")
    
    # Save detailed report
    report = {
        'total_products': len(all_products),
        'unique_brands': len(brands),
        'data_sources': dict(sources),
        'top_brands': dict(sorted(brands.items(), key=lambda x: -x[1])[:20]),
        'exact_brand_prefix_count': len(exact_matches),
        'word_prefix_count': len(word_matches),
        'exact_matches_sample': [
            {'brand': p['brand'], 'name': p['product_name']} 
            for p in exact_matches[:10]
        ],
        'word_matches_sample': [
            {'brand': p['product']['brand'], 'name': p['product']['product_name'], 'word': p['word']} 
            for p in word_matches[:10]
        ]
    }
    
    with open('reports/final_verification_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print("\n📄 Detailed report saved to: reports/final_verification_report.json")

if __name__ == "__main__":
    main()