#!/usr/bin/env python3
"""
Fast Zooplus import - processes first 500 products as test
"""

import os
import json
import re
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_KEY')
)

# Brand normalization map
BRAND_MAP = {
    'royal canin': 'Royal Canin',
    'hills prescription diet': "Hill's Prescription Diet",
    'hills science plan': "Hill's Science Plan",
    'purina pro plan': 'Pro Plan',
    'wolf of wilderness': 'Wolf Of Wilderness',
    'concept for life': 'Concept for Life',
    'lukullus': 'Lukullus',
    'rocco': 'Rocco',
    'purizon': 'Purizon',
    'josera': 'Josera',
    'briantos': 'Briantos',
    'bozita': 'Bozita',
    'eukanuba': 'Eukanuba',
    'greenwoods': 'Greenwoods',
    'rosies farm': "Rosie's Farm",
    'james wellbeloved': 'James Wellbeloved',
    'lilys kitchen': "Lily's Kitchen",
    'belcando': 'Belcando',
    'animonda': 'Animonda',
    'happy dog': 'Happy Dog',
}

def normalize_brand(brand):
    """Quick brand normalization"""
    if not brand:
        return ""
    brand_lower = brand.lower().strip().replace('_', ' ')
    return BRAND_MAP.get(brand_lower, brand.replace('_', ' ').title())

def create_key(brand, name, form='dry'):
    """Create product key"""
    brand_slug = re.sub(r'[^a-z0-9]', '', brand.lower())
    name_slug = re.sub(r'[^a-z0-9]', '', name.lower())[:50]  # Limit length
    return f"{brand_slug}|{name_slug}|{form}"

def process_product(p):
    """Process single product"""
    # Get brand from breadcrumbs
    breadcrumbs = p.get('breadcrumbs', [])
    if len(breadcrumbs) < 3:
        return None
    
    brand = normalize_brand(breadcrumbs[2])
    if not brand or brand == 'Zooplus Logo':
        return None
    
    name = p.get('name', '')
    if not name:
        return None
    
    # Clean name (remove pack size)
    name_clean = re.sub(r'\d+\s*x\s*\d+[kg|g|ml]', '', name)
    name_clean = re.sub(r'\d+[kg|g|ml]', '', name_clean)
    name_clean = name_clean.strip()
    
    # Determine form
    category = p.get('category', '').lower()
    form = 'wet' if 'wet' in category or 'canned' in category else 'dry'
    
    # Get nutrition
    attrs = p.get('attributes', {})
    
    product_data = {
        'product_key': create_key(brand, name_clean, form),
        'brand': brand,
        'product_name': name_clean[:100],  # Limit length
        'form': form,
    }
    
    # Add nutrition if available
    try:
        if attrs.get('protein'):
            product_data['protein_percent'] = float(attrs['protein'].replace('%', ''))
        if attrs.get('fat'):
            product_data['fat_percent'] = float(attrs['fat'].replace('%', ''))
        if attrs.get('fibre'):
            product_data['fiber_percent'] = float(attrs['fibre'].replace('%', ''))
        if attrs.get('ash'):
            product_data['ash_percent'] = float(attrs['ash'].replace('%', ''))
        if attrs.get('moisture'):
            product_data['moisture_percent'] = float(attrs['moisture'].replace('%', ''))
    except:
        pass
    
    # Mark source
    if any(k in product_data for k in ['protein_percent', 'fat_percent']):
        product_data['macros_source'] = 'site'
    
    return product_data

def main():
    print("Fast Zooplus Import")
    print("="*60)
    
    # Load JSON
    with open('data/zooplus/Zooplus.json', 'r') as f:
        data = json.load(f)
    
    print(f"Processing first 500 of {len(data)} products...")
    
    # Process products
    products = []
    brands = set()
    
    for p in data[:500]:  # Only first 500 for speed
        product = process_product(p)
        if product:
            products.append(product)
            brands.add(product['brand'])
    
    print(f"\\nProcessed {len(products)} valid products")
    print(f"Found {len(brands)} unique brands")
    print(f"\\nTop brands: {', '.join(sorted(brands)[:10])}")
    
    # Check existing
    print("\\nChecking for duplicates...")
    existing_keys = set()
    
    response = supabase.table('foods_canonical').select('product_key').execute()
    for p in response.data:
        existing_keys.add(p['product_key'])
    
    # Filter new products
    new_products = [p for p in products if p['product_key'] not in existing_keys]
    print(f"New products to add: {len(new_products)}")
    
    if new_products:
        # Add in batches
        print("\\nAdding new products...")
        batch_size = 50
        added = 0
        
        for i in range(0, len(new_products), batch_size):
            batch = new_products[i:i+batch_size]
            try:
                supabase.table('foods_canonical').insert(batch).execute()
                added += len(batch)
                print(f"  Added batch {i//batch_size + 1}: {len(batch)} products")
            except Exception as e:
                print(f"  Batch failed: {e}")
                # Try individual
                for p in batch:
                    try:
                        supabase.table('foods_canonical').insert(p).execute()
                        added += 1
                    except:
                        pass
        
        print(f"\\nTotal added: {added}")
    
    # Check results
    print("\\nChecking database status...")
    total = supabase.table('foods_canonical').select('*', count='exact').execute()
    fiber = supabase.table('foods_canonical').select('*', count='exact').not_.is_('fiber_percent', 'null').execute()
    
    print(f"Total products: {total.count}")
    print(f"With fiber: {fiber.count} ({fiber.count/total.count*100:.1f}%)")

if __name__ == "__main__":
    main()