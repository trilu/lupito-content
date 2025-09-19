#!/usr/bin/env python3
"""
Analyze potential duplicates between staging data and existing database
"""

import pandas as pd
import re
from difflib import SequenceMatcher
from collections import defaultdict

def normalize_for_matching(text):
    """Normalize text for matching"""
    if pd.isna(text):
        return ''
    text = str(text).lower()
    # Remove common size/weight indicators
    text = re.sub(r'\d+\s*(kg|g|ml|l|x|×)\s*', '', text)
    # Remove special characters
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    # Normalize spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def similarity_score(s1, s2):
    """Calculate similarity between two strings"""
    return SequenceMatcher(None, s1, s2).ratio()

def analyze_duplicates():
    # Load staging data
    staging_df = pd.read_csv('data/zooplus_staging_prepared.csv')
    print(f"Staging products: {len(staging_df)}")
    
    # Simulate database products (would normally query from Supabase)
    # For now, let's analyze the staging data itself
    
    # Group by normalized brand
    brand_groups = defaultdict(list)
    for _, row in staging_df.iterrows():
        brand_norm = normalize_for_matching(row['brand'])
        brand_groups[brand_norm].append(row)
    
    print(f"\nUnique normalized brands: {len(brand_groups)}")
    
    # Find potential duplicates within staging data
    duplicates = []
    for brand, products in brand_groups.items():
        if len(products) < 2:
            continue
        
        for i in range(len(products)):
            for j in range(i+1, len(products)):
                p1 = products[i]
                p2 = products[j]
                
                # Compare normalized names
                name1 = normalize_for_matching(p1['product_name'])
                name2 = normalize_for_matching(p2['product_name'])
                
                similarity = similarity_score(name1, name2)
                
                if similarity > 0.85:  # High similarity threshold
                    duplicates.append({
                        'product1': p1['product_name'],
                        'url1': p1['product_url'],
                        'product2': p2['product_name'],
                        'url2': p2['product_url'],
                        'similarity': similarity,
                        'brand': p1['brand']
                    })
    
    print(f"\nPotential duplicates found: {len(duplicates)}")
    
    if duplicates:
        print("\nTop 10 potential duplicates:")
        for dup in sorted(duplicates, key=lambda x: x['similarity'], reverse=True)[:10]:
            print(f"\nBrand: {dup['brand']}")
            print(f"  Product 1: {dup['product1'][:60]}")
            print(f"  Product 2: {dup['product2'][:60]}")
            print(f"  Similarity: {dup['similarity']:.2%}")
    
    # Analyze URL patterns
    url_patterns = defaultdict(int)
    for url in staging_df['product_url']:
        if 'activeVariant=' in url:
            # This indicates product variants
            base_url = url.split('?activeVariant=')[0]
            url_patterns[base_url] += 1
    
    print(f"\n📊 URL Analysis:")
    print(f"Total unique URLs: {staging_df['product_url'].nunique()}")
    print(f"Base URLs with variants: {len([k for k, v in url_patterns.items() if v > 1])}")
    print(f"Total variant products: {sum([v for v in url_patterns.values() if v > 1])}")
    
    # Sample of products with variants
    print("\nProducts with multiple variants (top 5):")
    for url, count in sorted(url_patterns.items(), key=lambda x: x[1], reverse=True)[:5]:
        if count > 1:
            product_name = staging_df[staging_df['product_url'].str.contains(url.replace('?', r'\?'), regex=True)]['product_name'].iloc[0]
            print(f"  {product_name[:50]}: {count} variants")
    
    return staging_df, duplicates

if __name__ == "__main__":
    print("🔍 ANALYZING POTENTIAL DUPLICATES IN ZOOPLUS DATA")
    print("=" * 60)
    
    staging_df, duplicates = analyze_duplicates()
    
    # Save duplicate analysis
    if duplicates:
        pd.DataFrame(duplicates).to_csv('data/zooplus_duplicates_analysis.csv', index=False)
        print(f"\n💾 Duplicate analysis saved to: data/zooplus_duplicates_analysis.csv")
