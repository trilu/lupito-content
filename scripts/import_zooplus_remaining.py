#!/usr/bin/env python3
"""
Import remaining Zooplus products (501-2079)
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

# Extended brand map
BRAND_MAP = {
    'royal canin': 'Royal Canin',
    'royal canin breed': 'Royal Canin',
    'royal canin veterinary': 'Royal Canin',
    'hills prescription diet': "Hill's Prescription Diet", 
    'hills science plan': "Hill's Science Plan",
    'purina pro plan': 'Pro Plan',
    'purina one': 'Purina ONE',
    'wolf of wilderness': 'Wolf Of Wilderness',
    'concept for life': 'Concept for Life',
    'concept for life veterinary diet': 'Concept for Life',
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
    'markus muhle': 'Markus Mühle',
    'markus mühle': 'Markus Mühle',
    'rinti': 'Rinti',
    'almo nature': 'Almo Nature',
    'applaws': 'Applaws',
    'burns': 'Burns',
    'cesar': 'Cesar',
    'encore': 'Encore',
    'iams': 'IAMS',
    'pedigree': 'Pedigree',
    'wau': 'WAU',
    'wow': 'WOW',
    'ziwipeak': 'ZiwiPeak',
    'nutriplus': 'NutriPlus',
    'dogsn tiger': "Dogs'n Tiger",
    'herrmanns': "Herrmann's",
    'ultima': 'Ultima',
    'frolic': 'Frolic',
    'chappi': 'Chappi',
    'beneful': 'Beneful',
    'purely': 'Purely',
    'schesir': 'Schesir',
    'trovet': 'Trovet',
    'specific': 'Specific',
    'forza10': 'Forza10',
    'terra canis': 'Terra Canis',
    'granatapet': 'GranataPet',
    'naturediet': 'Nature Diet',
    'yarrah': 'Yarrah',
}

def normalize_brand(brand):
    """Normalize brand name"""
    if not brand:
        return ""
    brand_lower = brand.lower().strip().replace('_', ' ')
    return BRAND_MAP.get(brand_lower, brand.replace('_', ' ').title())

def create_key(brand, name, form='dry'):
    """Create unique product key"""
    brand_slug = re.sub(r'[^a-z0-9]', '', brand.lower())
    name_slug = re.sub(r'[^a-z0-9]', '', name.lower())[:50]
    return f"{brand_slug}|{name_slug}|{form}"

def create_variant_key(base_key, variant_num):
    """Create variant key for duplicates"""
    parts = base_key.split('|')
    if len(parts) == 3:
        return f"{parts[0]}|{parts[1]}_v{variant_num}|{parts[2]}"
    return f"{base_key}_v{variant_num}"

def process_product(p, existing_keys):
    """Process single product with duplicate handling"""
    breadcrumbs = p.get('breadcrumbs', [])
    if len(breadcrumbs) < 3:
        return None
    
    brand = normalize_brand(breadcrumbs[2])
    if not brand or brand == 'Zooplus Logo':
        return None
    
    name = p.get('name', '')
    if not name:
        return None
    
    # Clean name
    name_clean = re.sub(r'\d+\s*x\s*\d+[kg|g|ml]', '', name)
    name_clean = re.sub(r'\d+[kg|g|ml]', '', name_clean)
    name_clean = name_clean.strip()
    
    # Determine form
    category = p.get('category', '').lower()
    breadcrumb_text = ' '.join(breadcrumbs).lower()
    
    if 'wet' in category or 'wet' in breadcrumb_text or 'canned' in category:
        form = 'wet'
    else:
        form = 'dry'
    
    # Check moisture as secondary indicator
    attrs = p.get('attributes', {})
    if attrs.get('moisture'):
        try:
            moisture = float(attrs['moisture'].replace('%', ''))
            if moisture > 60:
                form = 'wet'
        except:
            pass
    
    # Create base key
    base_key = create_key(brand, name_clean, form)
    
    # Handle duplicates with variants
    product_key = base_key
    if base_key in existing_keys:
        # Try variant keys
        for v in range(2, 10):
            variant_key = create_variant_key(base_key, v)
            if variant_key not in existing_keys:
                product_key = variant_key
                name_clean = f"{name_clean} (Variant {v})"
                break
        else:
            return None  # Skip if too many variants
    
    product_data = {
        'product_key': product_key,
        'brand': brand,
        'product_name': name_clean[:100],
        'form': form,
    }
    
    # Add nutrition
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
    
    # Add URL and image if available
    if p.get('url'):
        product_data['product_url'] = p['url']
    if p.get('main_image'):
        product_data['image_url'] = p['main_image']
    
    return product_data

def main():
    print("Importing Remaining Zooplus Products (501-2079)")
    print("="*60)
    
    # Load JSON
    with open('data/zooplus/Zooplus.json', 'r') as f:
        data = json.load(f)
    
    print(f"Processing products 501-2079 of {len(data)} total...")
    
    # Get existing keys
    print("Loading existing product keys...")
    existing_keys = set()
    offset = 0
    limit = 1000
    
    while True:
        response = supabase.table('foods_canonical').select('product_key').range(offset, offset + limit - 1).execute()
        if not response.data:
            break
        for p in response.data:
            existing_keys.add(p['product_key'])
        offset += limit
        if len(response.data) < limit:
            break
    
    print(f"Found {len(existing_keys)} existing products")
    
    # Process remaining products
    products = []
    brands = set()
    skipped = 0
    
    for p in data[500:]:  # Process from 501 onwards
        product = process_product(p, existing_keys)
        if product:
            products.append(product)
            brands.add(product['brand'])
            existing_keys.add(product['product_key'])  # Add to set to prevent duplicates
        else:
            skipped += 1
    
    print(f"\\nProcessed {len(products)} valid products")
    print(f"Skipped {skipped} products (duplicates or invalid)")
    print(f"Found {len(brands)} unique brands")
    
    # Show brands
    print(f"\\nBrands found: {', '.join(sorted(brands)[:20])}...")
    
    # Import in batches
    if products:
        print(f"\\nImporting {len(products)} new products...")
        batch_size = 30  # Smaller batches to avoid conflicts
        added = 0
        failed = 0
        
        for i in range(0, len(products), batch_size):
            batch = products[i:i+batch_size]
            
            # Try batch insert
            try:
                supabase.table('foods_canonical').insert(batch).execute()
                added += len(batch)
                print(f"  Batch {i//batch_size + 1}/{len(products)//batch_size + 1}: Added {len(batch)} ✅")
            except:
                # Try individual inserts
                for p in batch:
                    try:
                        supabase.table('foods_canonical').insert(p).execute()
                        added += 1
                    except:
                        failed += 1
                print(f"  Batch {i//batch_size + 1}: Added {added - (i + failed)} individually")
        
        print(f"\\nTotal added: {added}")
        print(f"Failed: {failed}")
    
    # Final check
    print("\\nChecking final database status...")
    total = supabase.table('foods_canonical').select('*', count='exact').execute()
    fiber = supabase.table('foods_canonical').select('*', count='exact').not_.is_('fiber_percent', 'null').execute()
    ash = supabase.table('foods_canonical').select('*', count='exact').not_.is_('ash_percent', 'null').execute()
    moisture = supabase.table('foods_canonical').select('*', count='exact').not_.is_('moisture_percent', 'null').execute()
    
    print(f"\\nFinal Database Status:")
    print(f"Total products: {total.count}")
    print(f"With fiber: {fiber.count} ({fiber.count/total.count*100:.1f}%)")
    print(f"With ash: {ash.count} ({ash.count/total.count*100:.1f}%)")
    print(f"With moisture: {moisture.count} ({moisture.count/total.count*100:.1f}%)")

if __name__ == "__main__":
    main()