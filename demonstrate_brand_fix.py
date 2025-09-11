#!/usr/bin/env python3
"""
Demonstration of the Brand Normalization Fix
Shows the BEFORE (wrong) and AFTER (correct) approaches
"""

import pandas as pd

def demonstrate_substring_problem():
    """Show why substring matching causes false positives"""
    
    # Sample data that demonstrates the problem
    sample_data = [
        {'brand': 'Bright', 'brand_slug': 'bright', 'product_name': 'Eyes Bushy Tails Canine Best 65% Beef'},
        {'brand': 'Alpha', 'brand_slug': 'alpha', 'product_name': 'Spirit Wild Canine Formula'},
        {'brand': 'Royal Canin', 'brand_slug': 'royal_canin', 'product_name': 'Mini Adult Dog Food'},
        {'brand': 'Ami', 'brand_slug': 'ami', 'product_name': 'One Planet Green Lentils'},
        {'brand': 'Purina', 'brand_slug': 'purina', 'product_name': 'Pro Plan Adult'},
        {'brand': 'Hills', 'brand_slug': 'hills', 'product_name': 'Science Plan Adult'},
    ]
    
    df = pd.DataFrame(sample_data)
    
    print("="*60)
    print("DEMONSTRATION: Why Substring Matching Fails")
    print("="*60)
    
    print("\nSample Catalog:")
    print(df[['brand', 'brand_slug', 'product_name']].to_string())
    
    print("\n" + "="*60)
    print("BEFORE (WRONG): Using Substring Matching")
    print("="*60)
    
    # Wrong approach - substring matching
    print("\nSearching for Royal Canin using substring matching...")
    print("Query: product_name.contains('canin', case=False)")
    
    # Find "Royal Canin" using substring - WRONG!
    rc_substring = df[df['product_name'].str.contains('canin', case=False, na=False)]
    
    print(f"\nResults: Found {len(rc_substring)} 'Royal Canin' products")
    if len(rc_substring) > 0:
        print("\nProducts found:")
        for _, row in rc_substring.iterrows():
            print(f"  - {row['brand']}: {row['product_name']}")
            if row['brand_slug'] != 'royal_canin':
                print(f"    ⚠️ FALSE POSITIVE! Actual brand: {row['brand_slug']}")
    
    # Find "Purina One" using substring - WRONG!
    print("\n" + "-"*40)
    print("Searching for Purina ONE using substring matching...")
    print("Query: product_name.contains('one', case=False)")
    
    purina_substring = df[df['product_name'].str.contains('\\bone\\b', case=False, na=False)]
    
    print(f"\nResults: Found {len(purina_substring)} 'Purina ONE' products")
    if len(purina_substring) > 0:
        print("\nProducts found:")
        for _, row in purina_substring.iterrows():
            print(f"  - {row['brand']}: {row['product_name']}")
            if row['brand_slug'] != 'purina':
                print(f"    ⚠️ FALSE POSITIVE! Actual brand: {row['brand_slug']}")
    
    print("\n" + "="*60)
    print("AFTER (CORRECT): Using brand_slug Only")
    print("="*60)
    
    # Correct approach - brand_slug only
    print("\nSearching for Royal Canin using brand_slug...")
    print("Query: brand_slug == 'royal_canin'")
    
    rc_correct = df[df['brand_slug'] == 'royal_canin']
    
    print(f"\nResults: Found {len(rc_correct)} Royal Canin products")
    if len(rc_correct) > 0:
        print("\nProducts found:")
        for _, row in rc_correct.iterrows():
            print(f"  ✓ {row['brand']}: {row['product_name']}")
    else:
        print("  (Correctly shows actual brand presence)")
    
    print("\n" + "-"*40)
    print("Searching for Purina using brand_slug...")
    print("Query: brand_slug == 'purina'")
    
    purina_correct = df[df['brand_slug'] == 'purina']
    
    print(f"\nResults: Found {len(purina_correct)} Purina products")
    if len(purina_correct) > 0:
        print("\nProducts found:")
        for _, row in purina_correct.iterrows():
            print(f"  ✓ {row['brand']}: {row['product_name']}")
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    print("\n❌ SUBSTRING MATCHING (WRONG):")
    print(f"  - 'Royal Canin': {len(rc_substring)} products (2 false positives)")
    print(f"  - 'Purina ONE': {len(purina_substring)} products (1 false positive)")
    print("  - Creates false data that corrupts analytics")
    
    print("\n✅ BRAND_SLUG MATCHING (CORRECT):")
    print(f"  - Royal Canin: {len(rc_correct)} products (accurate)")
    print(f"  - Purina: {len(purina_correct)} products (accurate)")
    print("  - Provides true brand presence data")
    
    print("\n" + "="*60)
    print("KEY LESSON")
    print("="*60)
    print("""
The word "Canine" appears in many dog food names because it means "dog".
Using substring matching on "canin" will match ALL products with "Canine",
creating false positives for Royal Canin.

Similarly, "One" is a common word that appears in many product names,
not just "Purina ONE".

ALWAYS use brand_slug for brand identification, NEVER substring matching.
    """)

def demonstrate_canonical_mapping():
    """Show how canonical mapping consolidates brands"""
    
    print("\n" + "="*60)
    print("CANONICAL BRAND MAPPING DEMONSTRATION")
    print("="*60)
    
    # Sample data with brand variations
    sample_data = [
        {'brand_slug': 'royal', 'product': 'Product A'},
        {'brand_slug': 'royal_canin', 'product': 'Product B'},
        {'brand_slug': 'royalcanin', 'product': 'Product C'},
        {'brand_slug': 'hills', 'product': 'Product D'},
        {'brand_slug': 'hill_s', 'product': 'Product E'},
        {'brand_slug': 'hills_science_plan', 'product': 'Product F'},
        {'brand_slug': 'arden', 'product': 'Product G'},
        {'brand_slug': 'arden_grange', 'product': 'Product H'},
    ]
    
    df = pd.DataFrame(sample_data)
    
    # Canonical mapping
    canonical_map = {
        'royal': 'royal_canin',
        'royal_canin': 'royal_canin',
        'royalcanin': 'royal_canin',
        'hills': 'hills',
        'hill_s': 'hills',
        'hills_science_plan': 'hills',
        'arden': 'arden_grange',
        'arden_grange': 'arden_grange',
    }
    
    print("\nBEFORE Canonical Mapping:")
    print(f"  Unique brands: {df['brand_slug'].nunique()}")
    print(f"  Brand slugs: {', '.join(df['brand_slug'].unique())}")
    
    # Apply canonical mapping
    df['canonical_brand'] = df['brand_slug'].map(canonical_map)
    
    print("\nAFTER Canonical Mapping:")
    print(f"  Unique brands: {df['canonical_brand'].nunique()}")
    print(f"  Canonical brands: {', '.join(df['canonical_brand'].unique())}")
    
    print("\nConsolidation Results:")
    for brand in df['canonical_brand'].unique():
        original_slugs = df[df['canonical_brand'] == brand]['brand_slug'].unique()
        print(f"  {brand}: consolidated from {', '.join(original_slugs)}")

if __name__ == "__main__":
    demonstrate_substring_problem()
    demonstrate_canonical_mapping()
    
    print("\n" + "="*60)
    print("✅ DEMONSTRATION COMPLETE")
    print("="*60)