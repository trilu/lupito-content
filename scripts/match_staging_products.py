#!/usr/bin/env python3
"""
Match staging products with existing database to identify duplicates
"""

import os
from dotenv import load_dotenv
from supabase import create_client
from difflib import SequenceMatcher
import re

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
    return url.rstrip('/')

def normalize_text(text):
    """Normalize text for comparison"""
    if not text:
        return ''
    # Remove special characters and lowercase
    text = re.sub(r'[^a-z0-9\s]', ' ', str(text).lower())
    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def similarity_score(s1, s2):
    """Calculate similarity between two strings"""
    return SequenceMatcher(None, s1, s2).ratio()

def main():
    print("🔄 MATCHING STAGING PRODUCTS WITH DATABASE")
    print("=" * 60)
    
    # Connect to Supabase
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Get all staging products
    print("Loading staging products...")
    staging = supabase.table('zooplus_staging').select('*').execute()
    print(f"  Found {len(staging.data)} staging products")
    
    # Get all existing products from database
    print("Loading existing products from database...")
    existing = supabase.table('foods_canonical').select(
        'product_key, brand, product_name, product_url'
    ).execute()
    print(f"  Found {len(existing.data)} existing products")
    
    # Create lookup dictionaries for faster matching
    existing_by_url = {}
    existing_by_brand_name = {}
    
    for product in existing.data:
        # Normalize URL for comparison
        url_norm = normalize_url(product.get('product_url', ''))
        if url_norm:
            existing_by_url[url_norm] = product
        
        # Create brand+name key
        brand = normalize_text(product.get('brand', ''))
        name = normalize_text(product.get('product_name', ''))
        if brand and name:
            key = f"{brand}|{name}"
            if key not in existing_by_brand_name:
                existing_by_brand_name[key] = []
            existing_by_brand_name[key].append(product)
    
    # Match staging products
    print("\nMatching products...")
    
    match_stats = {
        'exact_url': 0,
        'brand_name': 0,
        'fuzzy': 0,
        'new': 0
    }
    
    updates = []
    
    for staging_product in staging.data:
        staging_id = staging_product['id']
        staging_url = normalize_url(staging_product.get('base_url', ''))
        staging_brand = normalize_text(staging_product.get('brand', ''))
        staging_name = normalize_text(staging_product.get('product_name', ''))
        
        match_found = False
        update = {
            'id': staging_id,
            'matched_product_key': None,
            'match_type': None,
            'match_confidence': None
        }
        
        # 1. Try exact URL match
        if staging_url and staging_url in existing_by_url:
            matched = existing_by_url[staging_url]
            update['matched_product_key'] = matched['product_key']
            update['match_type'] = 'exact_url'
            update['match_confidence'] = 1.0
            match_stats['exact_url'] += 1
            match_found = True
        
        # 2. Try brand + name match
        elif staging_brand and staging_name:
            key = f"{staging_brand}|{staging_name}"
            if key in existing_by_brand_name:
                candidates = existing_by_brand_name[key]
                if candidates:
                    # Take first match
                    matched = candidates[0]
                    update['matched_product_key'] = matched['product_key']
                    update['match_type'] = 'brand_name'
                    update['match_confidence'] = 0.95
                    match_stats['brand_name'] += 1
                    match_found = True
        
        # 3. Try fuzzy matching (disabled for now to avoid false positives)
        # Could implement later with higher threshold
        
        # 4. Mark as new if no match found
        if not match_found:
            update['match_type'] = 'new'
            update['match_confidence'] = 0.0
            match_stats['new'] += 1
        
        updates.append(update)
    
    # Update staging table with matches
    print("\nUpdating staging table with matches...")
    
    batch_size = 100
    for i in range(0, len(updates), batch_size):
        batch = updates[i:i+batch_size]
        
        for update in batch:
            staging_id = update.pop('id')
            supabase.table('zooplus_staging').update(update).eq('id', staging_id).execute()
        
        print(f"  Updated batch {(i//batch_size)+1}/{(len(updates)+batch_size-1)//batch_size}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 MATCHING COMPLETE")
    print(f"  Exact URL matches: {match_stats['exact_url']}")
    print(f"  Brand+Name matches: {match_stats['brand_name']}")
    print(f"  Fuzzy matches: {match_stats['fuzzy']}")
    print(f"  New products: {match_stats['new']}")
    
    total_matched = match_stats['exact_url'] + match_stats['brand_name'] + match_stats['fuzzy']
    print(f"\n  Total matched: {total_matched} ({total_matched/len(staging.data)*100:.1f}%)")
    print(f"  Total new: {match_stats['new']} ({match_stats['new']/len(staging.data)*100:.1f}%)")
    
    # Get some examples of new products
    print("\n📝 Sample of new products to import:")
    new_products = supabase.table('zooplus_staging').select('brand, product_name')\
        .eq('match_type', 'new').limit(10).execute()
    
    for product in new_products.data[:5]:
        print(f"  - {product['brand']}: {product['product_name'][:50]}")
    
    print(f"\n✅ Matching complete! {match_stats['new']} products ready for import")
    print("📝 Next step: Import new products to database")

if __name__ == "__main__":
    main()
