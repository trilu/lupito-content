#!/usr/bin/env python3
"""
Compare staging data with existing database more accurately
"""

import pandas as pd
import re
import os
from dotenv import load_dotenv
from supabase import create_client
from difflib import SequenceMatcher

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def normalize_url(url):
    """Normalize URL for comparison"""
    if not url:
        return ''
    # Remove activeVariant parameter
    if '?activeVariant=' in url:
        url = url.split('?activeVariant=')[0]
    # Remove trailing slashes
    return url.rstrip('/')

def normalize_brand(brand):
    """Apply consistent brand normalization"""
    if not brand:
        return ''
    brand_map = {
        "hill's": "Hill's Science Plan",
        "hill's science plan": "Hill's Science Plan",
        "hill's prescription diet": "Hill's Prescription Diet",
        "royal canin": "Royal Canin",
        "royal canin veterinary": "Royal Canin Veterinary Diet",
        "royal canin vet diet": "Royal Canin Veterinary Diet",
        "pro plan": "Pro Plan",
        "purina pro plan": "Pro Plan",
        "mac's": "MAC's",
        "dogs'n tiger": "Dogs'n Tiger",
        "wolf of wilderness": "Wolf of Wilderness"
    }
    brand_lower = str(brand).lower().strip()
    return brand_map.get(brand_lower, brand)

def main():
    print("🔄 COMPARING WITH EXISTING DATABASE")
    print("=" * 60)
    
    # Load staging data
    staging_df = pd.read_csv('data/zooplus_staging_prepared.csv')
    print(f"Staging products: {len(staging_df)}")
    
    # Normalize URLs in staging
    staging_df['url_normalized'] = staging_df['product_url'].apply(normalize_url)
    staging_df['brand_normalized'] = staging_df['brand'].apply(normalize_brand)
    
    # Get unique base URLs
    unique_base_urls = staging_df['url_normalized'].nunique()
    print(f"Unique base URLs (without variants): {unique_base_urls}")
    
    # Connect to database
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Get all Zooplus products from database
    print("\nFetching existing Zooplus products from database...")
    response = supabase.table('foods_canonical').select(
        'product_key, brand, product_name, product_url, ingredients_raw'
    ).ilike('product_url', '%zooplus%').execute()
    
    db_products = pd.DataFrame(response.data)
    print(f"Database Zooplus products: {len(db_products)}")
    
    # Normalize database URLs
    db_products['url_normalized'] = db_products['product_url'].apply(normalize_url)
    db_products['brand_normalized'] = db_products['brand'].apply(normalize_brand)
    
    # Find matches
    print("\n📊 MATCHING ANALYSIS:")
    
    # 1. Exact URL matches (normalized)
    url_matches = staging_df[staging_df['url_normalized'].isin(db_products['url_normalized'])]
    print(f"  Products with matching URLs: {len(url_matches)}")
    
    # 2. New URLs not in database
    new_urls = staging_df[~staging_df['url_normalized'].isin(db_products['url_normalized'])]
    print(f"  Products with new URLs: {len(new_urls)}")
    
    # 3. Database products that need ingredients
    db_no_ingredients = db_products[db_products['ingredients_raw'].isna()]
    print(f"  DB products missing ingredients: {len(db_no_ingredients)}")
    
    # 4. Find which staging products can update DB products
    update_candidates = []
    for _, db_row in db_no_ingredients.iterrows():
        # Check if we have this URL in staging with ingredients
        staging_match = staging_df[
            (staging_df['url_normalized'] == db_row['url_normalized']) & 
            (staging_df['has_ingredients'] == True)
        ]
        if not staging_match.empty:
            update_candidates.append({
                'db_product_key': db_row['product_key'],
                'db_product_name': db_row['product_name'],
                'staging_url': staging_match.iloc[0]['product_url'],
                'has_ingredients_preview': True
            })
    
    print(f"  Can update with ingredient previews: {len(update_candidates)}")
    
    # 5. Products to scrape (in DB but no ingredients in staging)
    scrape_needed = []
    for _, db_row in db_no_ingredients.iterrows():
        staging_match = staging_df[staging_df['url_normalized'] == db_row['url_normalized']]
        if not staging_match.empty and not staging_match.iloc[0]['has_ingredients']:
            scrape_needed.append({
                'product_key': db_row['product_key'],
                'product_name': db_row['product_name'],
                'url': db_row['product_url']
            })
    
    print(f"  Need scraping (no data available): {len(scrape_needed)}")
    
    # Brand analysis
    print("\n🏷️ BRAND OVERLAP:")
    staging_brands = set(staging_df['brand_normalized'].unique())
    db_brands = set(db_products['brand_normalized'].unique())
    
    common_brands = staging_brands & db_brands
    print(f"  Brands in both: {len(common_brands)}")
    print(f"  New brands in staging: {len(staging_brands - db_brands)}")
    
    # Top overlapping brands
    print("\n  Top overlapping brands by product count:")
    for brand in list(common_brands)[:10]:
        staging_count = len(staging_df[staging_df['brand_normalized'] == brand])
        db_count = len(db_products[db_products['brand_normalized'] == brand])
        print(f"    {brand}: Staging={staging_count}, DB={db_count}")
    
    # Summary
    print("\n📋 FINAL ASSESSMENT:")
    print(f"  Total staging products: {len(staging_df)}")
    print(f"  Already in DB (by URL): {len(url_matches)} ({len(url_matches)/len(staging_df)*100:.1f}%)")
    print(f"  Truly new products: {len(new_urls)} ({len(new_urls)/len(staging_df)*100:.1f}%)")
    print(f"  Can enrich DB products: {len(update_candidates)}")
    print(f"  Need scraping: {len(scrape_needed)}")
    
    # Save results
    if len(new_urls) > 0:
        new_urls.to_csv('data/zooplus_truly_new_products.csv', index=False)
        print(f"\n💾 Saved {len(new_urls)} truly new products to: data/zooplus_truly_new_products.csv")
    
    if update_candidates:
        pd.DataFrame(update_candidates).to_csv('data/zooplus_can_update.csv', index=False)
        print(f"💾 Saved {len(update_candidates)} update candidates to: data/zooplus_can_update.csv")
    
    if scrape_needed:
        pd.DataFrame(scrape_needed).to_csv('data/zooplus_need_scraping.csv', index=False)
        print(f"💾 Saved {len(scrape_needed)} products needing scraping to: data/zooplus_need_scraping.csv")

if __name__ == "__main__":
    import os
    main()
