#!/usr/bin/env python3
"""
Fast AADF data import - loads all products once for efficient matching
Only updates products that don't have ingredients
"""

import os
import re
import csv
import json
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlparse
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_KEY')
)

def extract_brand_from_url(url: str) -> Optional[str]:
    """Extract brand from AADF URL"""
    if not url:
        return None
    
    # Known brand patterns in AADF URLs
    brand_patterns = {
        'forthglade': 'Forthglade',
        'ava': 'AVA', 
        'fish4dogs': 'Fish4Dogs',
        'royal-canin': 'Royal Canin',
        'hills': "Hill's Science Plan",
        'james-wellbeloved': 'James Wellbeloved',
        'purina': 'Purina',
        'eukanuba': 'Eukanuba',
        'iams': 'IAMS',
        'bakers': 'Bakers',
        'butchers': "Butcher's",
        'pedigree': 'Pedigree',
        'wainwrights': "Wainwright's",
        'harringtons': "Harrington's",
        'burns': 'Burns',
        'lily': "Lily's Kitchen",
        'lilys-kitchen': "Lily's Kitchen",
        'canagan': 'Canagan',
        'aatu': 'Aatu',
        'akela': 'Akela',
        'applaws': 'Applaws',
        'barking-heads': 'Barking Heads',
        'beco': 'Beco',
        'brit': 'Brit',
        'eden': 'Eden',
        'gentle': 'Gentle',
        'guru': 'Guru',
        'millies-wolfheart': "Millie's Wolfheart",
        'natures-menu': 'Natures Menu',
        'orijen': 'Orijen',
        'piccolo': 'Piccolo',
        'pooch-mutt': 'Pooch & Mutt',
        'pure': 'Pure',
        'symply': 'Symply',
        'tails': 'Tails',
        'taste-of-the-wild': 'Taste of the Wild',
        'tribal': 'Tribal',
        'wellness': 'Wellness',
        'wolf-of-wilderness': 'Wolf Of Wilderness',
        'yarrah': 'Yarrah',
        'ziwipeak': 'ZiwiPeak',
        'acana': 'Acana',
        'advance': 'Advance',
        'arden-grange': 'Arden Grange',
        'arkwrights': 'Arkwrights',
        'autarky': 'Autarky',
        'benevo': 'Benevo',
        'beta': 'Beta',
        'blink': 'Blink',
        'burgess': 'Burgess',
        'cesar': 'Cesar',
        'chappie': 'Chappie',
        'encore': 'Encore',
        'greenies': 'Greenies',
        'hilife': 'HiLife',
        'husse': 'Husse',
        'josera': 'Josera',
        'lukullus': 'Lukullus',
        'merrick': 'Merrick',
        'naturediet': 'Nature Diet',
        'nutriment': 'Nutriment',
        'orijen': 'Orijen',
        'platinum': 'Platinum',
        'pro-plan': 'Pro Plan',
        'pro-pac': 'Pro Pac',
        'purina-one': 'Purina ONE',
        'rocco': 'Rocco',
        'scrumbles': 'Scrumbles',
        'skinners': 'Skinners',
        'solid-gold': 'Solid Gold',
        'step-up': 'Step Up',
        'terra-canis': 'Terra Canis',
        'the-dogs-table': "The Dog's Table",
        'thrive': 'Thrive',
        'vets-kitchen': "Vet's Kitchen",
        'wagg': 'Wagg',
        'webbox': 'Webbox',
        'wellness-core': 'Wellness CORE',
        'winalot': 'Winalot',
        'zooplus': 'Zooplus'
    }
    
    # Extract from URL path
    path = urlparse(url).path.lower()
    
    for pattern, brand in brand_patterns.items():
        if pattern in path:
            return brand
    
    # Try to extract from slug
    if '/dog-food-reviews/' in path:
        parts = path.split('/')
        if len(parts) >= 4:
            slug = parts[3]
            # First part is often the brand
            first_part = slug.split('-')[0]
            return first_part.title()
    
    return None

def normalize_name(name: str) -> str:
    """Normalize product name for matching"""
    if not name:
        return ""
    
    # Convert to lowercase and remove special characters
    normalized = re.sub(r'[^\w\s]', ' ', name.lower())
    # Remove extra spaces
    normalized = ' '.join(normalized.split())
    
    return normalized

def parse_ingredients(ingredients_text: str) -> List[str]:
    """Parse ingredients into tokens"""
    if not ingredients_text:
        return []
    
    # Remove percentages
    text = re.sub(r'\([^)]*\)', '', ingredients_text)
    
    # Split and clean
    parts = []
    for part in re.split(r'[,;]', text):
        part = re.sub(r'[^\w\s-]', ' ', part).strip()
        if part and len(part) > 1:
            parts.append(part.lower())
    
    return parts[:50]  # Limit to 50 ingredients

def main():
    import sys
    
    print("="*60)
    print("AADF DATA IMPORT - FAST VERSION")
    print("="*60)
    
    # Load all products from database first
    print("\nLoading products from database...")
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
    
    print(f"Loaded {len(all_products)} products from database")
    
    # Create lookup index by brand
    products_by_brand = {}
    products_without_ingredients = []
    
    for product in all_products:
        brand = product.get('brand', '')
        if brand:
            if brand not in products_by_brand:
                products_by_brand[brand] = []
            products_by_brand[brand].append(product)
            
            # Track products without ingredients
            if not product.get('ingredients_raw'):
                products_without_ingredients.append(product)
    
    print(f"Found {len(products_without_ingredients)} products without ingredients")
    
    # Process AADF CSV
    print("\nProcessing AADF data...")
    
    updates = []
    unmatched = []
    matched_count = 0
    
    with open('data/aadf/aadf-dataset.csv', 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        for row_num, row in enumerate(reader, 1):
            if row_num % 100 == 0:
                print(f"  Processed {row_num} rows...", end='\r')
            
            # Extract data
            url = row.get('data-page-selector-href', '').strip()
            ingredients = row.get('ingredients-0', '').strip()
            
            if not ingredients or not url:
                continue
            
            # Extract brand
            brand = extract_brand_from_url(url)
            if not brand:
                continue
            
            # Look for products of this brand without ingredients
            if brand in products_by_brand:
                brand_products = products_by_brand[brand]
                
                # Try to match based on URL similarity
                url_parts = urlparse(url).path.lower().split('/')
                
                for product in brand_products:
                    # Skip if already has ingredients
                    if product.get('ingredients_raw'):
                        continue
                    
                    # Simple matching: if product name contains key words from URL
                    product_name_normalized = normalize_name(product.get('product_name', ''))
                    
                    # Extract keywords from URL
                    url_keywords = []
                    for part in url_parts:
                        words = part.split('-')
                        url_keywords.extend([w for w in words if len(w) > 3])
                    
                    # Check for keyword matches
                    matches = sum(1 for keyword in url_keywords if keyword in product_name_normalized)
                    
                    if matches >= 2:  # At least 2 keyword matches
                        updates.append({
                            'product_key': product['product_key'],
                            'brand': brand,
                            'name': product['product_name'],
                            'updates': {
                                'ingredients_raw': ingredients,
                                'ingredients_source': 'site',  # Using valid value
                                'ingredients_tokens': parse_ingredients(ingredients)
                            }
                        })
                        matched_count += 1
                        break
            else:
                unmatched.append(brand)
    
    print(f"\n\nMatched {matched_count} products with AADF data")
    
    # Apply updates
    if updates:
        print(f"\nUpdating {len(updates)} products with ingredients...")
        
        # Limit for testing
        limit = 50 if '--all' not in sys.argv else len(updates)
        
        for i, update in enumerate(updates[:limit], 1):
            try:
                response = supabase.table('foods_canonical').update(
                    update['updates']
                ).eq('product_key', update['product_key']).execute()
                
                print(f"  [{i}/{limit}] ✅ {update['brand']}: {update['name']}")
                
            except Exception as e:
                print(f"  [{i}/{limit}] ❌ Failed: {update['brand']}: {update['name']}")
                print(f"      Error: {e}")
        
        if len(updates) > limit:
            print(f"\n  ⚠️  {len(updates) - limit} more products ready to update")
            print("  Run with --all flag to update all products")
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Products matched: {matched_count}")
    print(f"Products updated: {min(limit if updates else 0, len(updates))}")
    print(f"Unique unmatched brands: {len(set(unmatched))}")
    
    print("\n✅ AADF import completed!")

if __name__ == "__main__":
    main()