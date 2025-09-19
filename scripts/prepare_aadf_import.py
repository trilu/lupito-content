#!/usr/bin/env python3
"""
Prepare AADF dataset for import with proper normalization
"""

import pandas as pd
import json
import re
from datetime import datetime
from typing import Dict, Optional, List
from fuzzywuzzy import fuzz

def clean_product_name(name: str) -> str:
    """Clean product name by removing Review suffix and normalizing"""
    if not name:
        return ""
    
    # Remove "Review" suffix
    name = name.replace(' Review', '')
    
    # Clean whitespace
    name = ' '.join(name.split())
    
    return name.strip()

def extract_brand_from_name(product_name: str) -> Optional[str]:
    """Extract brand from product name if it starts with known brand"""
    if not product_name:
        return None
    
    # Known brand patterns at start of product names
    brand_patterns = {
        'Royal Canin': ['Royal Canin'],
        "Hill's Science Plan": ["Hill's Science Plan", "Hill's"],
        'Purina': ['Purina Pro Plan', 'Purina ONE', 'Purina'],
        'Eukanuba': ['Eukanuba'],
        'IAMS': ['IAMS'],
        'Burns': ['Burns'],
        'Canagan': ['Canagan'],
        'Orijen': ['Orijen'],
        'Acana': ['Acana'],
        'Applaws': ['Applaws'],
        'Lily\'s Kitchen': ["Lily's Kitchen"],
        'James Wellbeloved': ['James Wellbeloved'],
        'Arden Grange': ['Arden Grange'],
        'Barking Heads': ['Barking Heads'],
        'Natures Menu': ['Natures Menu', "Nature's Menu"],
        'Wellness': ['Wellness'],
        'Taste of the Wild': ['Taste of the Wild'],
        'Wolf of Wilderness': ['Wolf of Wilderness'],
        'Brit': ['Brit Care', 'Brit Premium', 'Brit'],
        'Advance': ['Advance'],
        'Beco': ['Beco'],
        'Pooch & Mutt': ['Pooch & Mutt', 'Pooch and Mutt'],
        'Harringtons': ["Harrington's", 'Harringtons'],
        'Wainwrights': ["Wainwright's", 'Wainwrights'],
        'AVA': ['AVA'],
        'Fish4Dogs': ['Fish4Dogs'],
        'Forthglade': ['Forthglade'],
        'Guru': ['Guru'],
        'Symply': ['Symply'],
        'Aatu': ['Aatu', 'AATU'],
        'Eden': ['Eden'],
        'Piccolo': ['Piccolo'],
        'Akela': ['Akela'],
        'Tribal': ['Tribal'],
        'Pure': ['Pure'],
        "Millie's Wolfheart": ["Millie's Wolfheart"],
        'Gentle': ['Gentle'],
        'Tails.com': ['Tails.com', 'Tails'],
        'Scrumbles': ['Scrumbles'],
        'Nutriment': ['Nutriment'],
        'Chappie': ['Chappie'],
        'Pedigree': ['Pedigree'],
        'Cesar': ['Cesar'],
        'Bakers': ['Bakers', "Baker's"],
        "Butcher's": ["Butcher's", 'Butchers'],
        'Wafcol': ['Wafcol'],
        'Pro Plan': ['Pro Plan'],
        'Alpha Spirit': ['Alpha Spirit'],
        'Rocco': ['Rocco'],
        'Lukullus': ['Lukullus'],
        'Bozita': ['Bozita'],
        'Belcando': ['Belcando'],
        'Bosch': ['Bosch'],
        'Josera': ['Josera'],
        'Happy Dog': ['Happy Dog'],
        'Greenies': ['Greenies'],
        'ZiwiPeak': ['ZiwiPeak', 'Ziwi Peak'],
        'Yarrah': ['Yarrah'],
        'Husse': ['Husse'],
        'Essential': ['Essential'],
        'Jollyes': ['Jollyes'],
        'Sabre Pet Food': ['Sabre Pet Food', 'Sabre'],
        'Trophy Pet Foods': ['Trophy Pet Foods', 'Trophy'],
        'Chudleys': ['Chudleys'],
        'Mole Online': ['Mole Online'],
        'Seven': ['Seven'],
        'Nourish': ['Nourish'],
        'Luna & Me': ['Luna & Me', 'Luna and Me'],
        'Tilly & Ted': ['Tilly & Ted', 'Tilly and Ted'],
        'Edmondson\'s': ['Edmondson\'s', 'Edmondsons'],
        'Simpsons': ['Simpsons Premium', 'Simpsons'],
        'Cotswold Raw': ['Cotswold Raw'],
        'Nature\'s Variety': ['Nature\'s Variety', 'Natures Variety'],
        'Leo & Wolf': ['Leo & Wolf', 'Leo and Wolf']
    }
    
    clean_name = product_name.strip()
    for brand, patterns in brand_patterns.items():
        for pattern in patterns:
            if clean_name.startswith(pattern):
                return brand
    
    return None

def extract_brand_from_url(url: str) -> Optional[str]:
    """Extract brand from AADF URL patterns"""
    if not url:
        return None
    
    # Extract the slug from URL
    # Format: https://www.allaboutdogfood.co.uk/dog-food-reviews/0387/royal-canin-x-small-adult
    parts = url.split('/')
    if len(parts) > 5:
        slug = parts[-1]
        
        # Known URL patterns
        url_brand_map = {
            'royal-canin': 'Royal Canin',
            'hills': "Hill's Science Plan",
            'purina': 'Purina',
            'eukanuba': 'Eukanuba',
            'iams': 'IAMS',
            'burns': 'Burns',
            'canagan': 'Canagan',
            'orijen': 'Orijen',
            'acana': 'Acana',
            'applaws': 'Applaws',
            'lilys-kitchen': "Lily's Kitchen",
            'james-wellbeloved': 'James Wellbeloved',
            'arden-grange': 'Arden Grange',
            'barking-heads': 'Barking Heads',
            'natures-menu': 'Natures Menu',
            'wellness': 'Wellness',
            'taste-of-the-wild': 'Taste of the Wild',
            'wolf-of-wilderness': 'Wolf of Wilderness',
            'brit': 'Brit',
            'advance': 'Advance',
            'fish4dogs': 'Fish4Dogs',
            'forthglade': 'Forthglade',
            'ava': 'AVA',
            'harringtons': "Harrington's",
            'wainwrights': "Wainwright's",
            'beco': 'Beco',
            'pooch-mutt': 'Pooch & Mutt',
            'guru': 'Guru',
            'symply': 'Symply',
            'aatu': 'Aatu',
            'eden': 'Eden',
            'piccolo': 'Piccolo',
            'akela': 'Akela',
            'tribal': 'Tribal',
            'pure': 'Pure',
            'millies-wolfheart': "Millie's Wolfheart",
            'gentle': 'Gentle',
            'tails': 'Tails.com',
            'scrumbles': 'Scrumbles',
            'nutriment': 'Nutriment'
        }
        
        for pattern, brand in url_brand_map.items():
            if pattern in slug:
                return brand
    
    return None

def normalize_brand(brand: str) -> str:
    """Normalize brand name to consistent format"""
    if not brand:
        return "Unknown"
    
    # Brand normalization mappings
    brand_mappings = {
        'royal canin': 'Royal Canin',
        'royalcanin': 'Royal Canin',
        'royal-canin': 'Royal Canin',
        'hills': "Hill's Science Plan",
        "hill's": "Hill's Science Plan",
        'hills science plan': "Hill's Science Plan",
        'hills science diet': "Hill's Science Plan",
        'purina': 'Purina',
        'purina pro plan': 'Purina Pro Plan',
        'purina one': 'Purina ONE',
        'purina-one': 'Purina ONE',
        'advance': 'Advance',
        'advance veterinary': 'Advance',
        'eukanuba': 'Eukanuba',
        'wolf of wilderness': 'Wolf of Wilderness',
        'wolf-of-wilderness': 'Wolf of Wilderness',
        'wow': 'Wolf of Wilderness',
        'iams': 'IAMS',
        'burns': 'Burns',
        'canagan': 'Canagan',
        'orijen': 'Orijen',
        'acana': 'Acana',
        'applaws': 'Applaws',
        "lily's kitchen": "Lily's Kitchen",
        'lilys kitchen': "Lily's Kitchen",
        'james wellbeloved': 'James Wellbeloved',
        'arden grange': 'Arden Grange',
        'barking heads': 'Barking Heads',
        'natures menu': 'Natures Menu',
        "nature's menu": 'Natures Menu',
        'wellness': 'Wellness',
        'taste of the wild': 'Taste of the Wild',
        'brit': 'Brit',
        'brit care': 'Brit',
        'brit premium': 'Brit',
        'beco': 'Beco',
        'pooch & mutt': 'Pooch & Mutt',
        'pooch and mutt': 'Pooch & Mutt',
        "harrington's": "Harrington's",
        'harringtons': "Harrington's",
        "wainwright's": "Wainwright's",
        'wainwrights': "Wainwright's",
        'ava': 'AVA',
        'fish4dogs': 'Fish4Dogs',
        'forthglade': 'Forthglade',
        'guru': 'Guru',
        'symply': 'Symply',
        'aatu': 'Aatu',
        'eden': 'Eden',
        'piccolo': 'Piccolo',
        'akela': 'Akela',
        'tribal': 'Tribal',
        'pure': 'Pure',
        "millie's wolfheart": "Millie's Wolfheart",
        'millies wolfheart': "Millie's Wolfheart",
        'gentle': 'Gentle',
        'tails.com': 'Tails.com',
        'tails': 'Tails.com',
        'scrumbles': 'Scrumbles',
        'nutriment': 'Nutriment',
        'chappie': 'Chappie',
        'pedigree': 'Pedigree',
        'cesar': 'Cesar',
        'bakers': 'Bakers',
        "baker's": 'Bakers',
        "butcher's": "Butcher's",
        'butchers': "Butcher's"
    }
    
    # Normalize to lowercase for lookup
    brand_lower = brand.lower().strip()
    
    # Check mappings
    if brand_lower in brand_mappings:
        return brand_mappings[brand_lower]
    
    # If not in mappings, return with proper case
    return brand.strip()

def parse_energy(energy_str: str) -> Optional[float]:
    """Parse energy value from string format"""
    if not energy_str or pd.isna(energy_str):
        return None
    
    # Look for kcal/100g pattern
    match = re.search(r'(\d+\.?\d*)\s*kcal/100g', str(energy_str))
    if match:
        return float(match.group(1))
    
    return None

def parse_price(price_str: str) -> Optional[float]:
    """Parse price value from string format"""
    if not price_str or pd.isna(price_str):
        return None
    
    # Remove currency symbol and convert to float
    price_clean = str(price_str).replace('£', '').replace('$', '').strip()
    try:
        return float(price_clean)
    except:
        return None

def generate_product_key(brand: str, product_name: str, form: str = 'unknown') -> str:
    """Generate unique product key"""
    parts = []
    
    if brand and brand != "Unknown":
        brand_part = re.sub(r'[^\w]', '', brand.lower())
        parts.append(brand_part)
    
    if product_name:
        name_part = re.sub(r'[^\w\s]', '', product_name.lower())
        name_part = re.sub(r'\s+', '_', name_part)[:50]
        parts.append(name_part)
    
    parts.append(form.lower())
    
    return '|'.join(parts)

def main():
    print("📊 PREPARING AADF DATASET FOR IMPORT")
    print("=" * 80)
    
    # Load dataset
    df = pd.read_csv('data/aadf/aadf-dataset-2.csv')
    print(f"Loaded {len(df)} products from CSV")
    
    # Clean column names
    df.columns = df.columns.str.strip()
    
    # Prepare data
    prepared_products = []
    stats = {
        'total': len(df),
        'with_brand': 0,
        'with_ingredients': 0,
        'with_energy': 0,
        'with_price': 0,
        'brand_from_manufacturer': 0,
        'brand_from_name': 0,
        'brand_from_url': 0,
        'brand_unknown': 0
    }
    
    print("\n🔄 Processing products...")
    
    for idx, row in df.iterrows():
        # Clean product name
        product_name = clean_product_name(row.get('Product Name-0', ''))
        
        # Extract brand (priority order)
        brand = None
        brand_source = None
        
        # 1. Try manufacturer field first
        if pd.notna(row.get('Manufacturer-0')):
            brand = normalize_brand(row['Manufacturer-0'])
            brand_source = 'manufacturer'
            stats['brand_from_manufacturer'] += 1
        
        # 2. Try extracting from product name
        if not brand or brand == "Unknown":
            extracted = extract_brand_from_name(product_name)
            if extracted:
                brand = normalize_brand(extracted)
                brand_source = 'product_name'
                stats['brand_from_name'] += 1
        
        # 3. Try extracting from URL
        if not brand or brand == "Unknown":
            url = row.get('data-page-selector-href', '')
            extracted = extract_brand_from_url(url)
            if extracted:
                brand = normalize_brand(extracted)
                brand_source = 'url'
                stats['brand_from_url'] += 1
        
        # 4. Default to Unknown
        if not brand or brand == "Unknown":
            brand = "Unknown"
            brand_source = 'default'
            stats['brand_unknown'] += 1
        
        if brand != "Unknown":
            stats['with_brand'] += 1
        
        # Parse other fields
        ingredients = row.get('Ingredients-0', '') if pd.notna(row.get('Ingredients-0')) else None
        if ingredients:
            stats['with_ingredients'] += 1
        
        energy = parse_energy(row.get('Energy-0', ''))
        if energy:
            stats['with_energy'] += 1
        
        price_per_day = parse_price(row.get('Price per day-0', ''))
        if price_per_day:
            stats['with_price'] += 1
        
        # Determine form from type
        type_of_food = row.get('Type of food-0', '').lower() if pd.notna(row.get('Type of food-0')) else ''
        if 'wet' in type_of_food or 'can' in type_of_food or 'pouch' in type_of_food:
            form = 'wet'
        elif 'dry' in type_of_food or 'kibble' in type_of_food:
            form = 'dry'
        elif 'raw' in type_of_food:
            form = 'raw'
        elif 'treat' in type_of_food:
            form = 'treat'
        else:
            form = 'unknown'
        
        # Generate product key
        product_key = generate_product_key(brand, product_name, form)
        
        # Prepare product data
        prepared_product = {
            'product_key': product_key,
            'brand': brand,
            'brand_source': brand_source,
            'product_name': product_name,
            'original_name': row.get('Product Name-0', ''),
            'ingredients_raw': ingredients,
            'energy_kcal': energy,
            'price_per_day': price_per_day,
            'product_url': row.get('data-page-selector-href', ''),
            'type_of_food': row.get('Type of food-0', '') if pd.notna(row.get('Type of food-0')) else None,
            'dog_ages': row.get('Dog ages-0', '') if pd.notna(row.get('Dog ages-0')) else None,
            'form': form,
            'source': 'allaboutdogfood',
            'import_timestamp': datetime.now().isoformat()
        }
        
        prepared_products.append(prepared_product)
        
        if (idx + 1) % 100 == 0:
            print(f"  Processed {idx + 1}/{len(df)} products...")
    
    # Print statistics
    print("\n📈 PREPARATION STATISTICS:")
    print("-" * 80)
    print(f"Total products: {stats['total']}")
    print(f"With brand identified: {stats['with_brand']} ({stats['with_brand']/stats['total']*100:.1f}%)")
    print(f"  - From manufacturer field: {stats['brand_from_manufacturer']}")
    print(f"  - From product name: {stats['brand_from_name']}")
    print(f"  - From URL: {stats['brand_from_url']}")
    print(f"  - Unknown brand: {stats['brand_unknown']}")
    print(f"With ingredients: {stats['with_ingredients']} ({stats['with_ingredients']/stats['total']*100:.1f}%)")
    print(f"With energy data: {stats['with_energy']} ({stats['with_energy']/stats['total']*100:.1f}%)")
    print(f"With price data: {stats['with_price']} ({stats['with_price']/stats['total']*100:.1f}%)")
    
    # Brand distribution
    brand_counts = {}
    for product in prepared_products:
        brand = product['brand']
        brand_counts[brand] = brand_counts.get(brand, 0) + 1
    
    print("\n🏷️ TOP BRANDS:")
    sorted_brands = sorted(brand_counts.items(), key=lambda x: -x[1])
    for brand, count in sorted_brands[:15]:
        print(f"  {brand}: {count} products")
    
    # Save prepared data
    output_file = 'data/aadf/aadf_prepared.json'
    with open(output_file, 'w') as f:
        json.dump(prepared_products, f, indent=2)
    
    print(f"\n✅ Saved prepared data to {output_file}")
    print(f"   Ready for import: {len(prepared_products)} products")
    
    # Also save as CSV for review
    prepared_df = pd.DataFrame(prepared_products)
    prepared_df.to_csv('data/aadf/aadf_prepared.csv', index=False)
    print(f"   Also saved as CSV: data/aadf/aadf_prepared.csv")
    
    return prepared_products

if __name__ == "__main__":
    main()