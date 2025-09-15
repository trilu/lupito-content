#!/usr/bin/env python3
"""
Deduplicate product variants to get unique base products
"""

import pandas as pd
import re

def get_base_product_url(url):
    """Get base URL without variant parameters"""
    if not url:
        return ''
    # Remove activeVariant parameter
    if '?activeVariant=' in url:
        return url.split('?activeVariant=')[0]
    return url

def normalize_product_name(name):
    """Remove size/quantity indicators to get base product name"""
    if not name:
        return ''
    
    # Remove common size patterns
    name = re.sub(r'\b\d+\s*x\s*\d+\s*(kg|g|ml|l)\b', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\b\d+\s*(kg|g|ml|l)\b', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\bEconomy\s+Pack:?\s*', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\bSaver\s+Pack:?\s*', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\bTrial\s+Pack:?\s*', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+', ' ', name)
    
    return name.strip()

def main():
    print("🔄 DEDUPLICATING PRODUCT VARIANTS")
    print("=" * 60)
    
    # Load staging data
    df = pd.read_csv('data/zooplus_staging_prepared.csv')
    print(f"Total products (with variants): {len(df)}")
    
    # Add base URL column
    df['base_url'] = df['product_url'].apply(get_base_product_url)
    df['base_product_name'] = df['product_name'].apply(normalize_product_name)
    
    # Count variants per base URL
    variants_per_url = df.groupby('base_url').size().reset_index(name='variant_count')
    print(f"\n📊 Variant Analysis:")
    print(f"  Unique base URLs: {len(variants_per_url)}")
    print(f"  Products with multiple variants: {len(variants_per_url[variants_per_url['variant_count'] > 1])}")
    
    # Show top products with most variants
    top_variants = variants_per_url.nlargest(10, 'variant_count')
    print("\nTop 10 products by variant count:")
    for _, row in top_variants.iterrows():
        sample = df[df['base_url'] == row['base_url']].iloc[0]
        print(f"  {sample['brand']} - {sample['base_product_name'][:40]}: {row['variant_count']} variants")
    
    # Deduplicate - keep one variant per base URL (prefer with ingredients)
    print("\n🔧 Deduplicating...")
    
    # Sort to prioritize variants with ingredients
    df_sorted = df.sort_values(['base_url', 'has_ingredients'], ascending=[True, False])
    
    # Keep first variant for each base URL
    df_deduped = df_sorted.drop_duplicates(subset=['base_url'], keep='first')
    
    print(f"\n✅ Results:")
    print(f"  Original products: {len(df)}")
    print(f"  After deduplication: {len(df_deduped)}")
    print(f"  Removed variants: {len(df) - len(df_deduped)}")
    print(f"  Products with ingredients: {df_deduped['has_ingredients'].sum()}")
    
    # Compare with existing database results
    existing_match = pd.read_csv('data/zooplus_truly_new_products.csv')
    existing_match_deduped = existing_match.drop_duplicates(
        subset=['url'], 
        keep='first'
    )
    
    # Apply same deduplication to base URLs
    existing_match_deduped['base_url'] = existing_match_deduped['url'].apply(get_base_product_url)
    existing_match_deduped = existing_match_deduped.drop_duplicates(subset=['base_url'], keep='first')
    
    print(f"\n📊 Impact on New Products:")
    print(f"  Original new products: {len(existing_match)}")
    print(f"  After deduplication: {len(existing_match_deduped)}")
    print(f"  Actual unique new products: {len(existing_match_deduped)}")
    
    # Save deduplicated data
    df_deduped.to_csv('data/zooplus_deduped.csv', index=False)
    existing_match_deduped.to_csv('data/zooplus_new_products_deduped.csv', index=False)
    
    print(f"\n💾 Saved deduplicated data:")
    print(f"  - data/zooplus_deduped.csv ({len(df_deduped)} unique products)")
    print(f"  - data/zooplus_new_products_deduped.csv ({len(existing_match_deduped)} unique new products)")
    
    # Brand summary
    print(f"\n🏷️ Brand Distribution (after deduplication):")
    top_brands = df_deduped['brand'].value_counts().head(10)
    for brand, count in top_brands.items():
        print(f"  {brand}: {count} products")

if __name__ == "__main__":
    main()
