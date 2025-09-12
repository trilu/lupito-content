#!/usr/bin/env python3
"""
Analyze and stage Chewy and AADF retailer datasets - V2 with better parsing
"""

import json
import csv
import re
import os
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import yaml
from difflib import SequenceMatcher
import hashlib

# Create output directories
Path("data/staging").mkdir(parents=True, exist_ok=True)
Path("reports").mkdir(exist_ok=True)

# Load brand normalization maps if they exist
BRAND_PHRASE_MAP = {}
CANONICAL_BRAND_MAP = {}

if Path("data/brand_phrase_map.csv").exists():
    with open("data/brand_phrase_map.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if 'phrase' in row and 'brand' in row:
                BRAND_PHRASE_MAP[row['phrase'].lower()] = row['brand']

if Path("data/canonical_brand_map.yaml").exists():
    with open("data/canonical_brand_map.yaml") as f:
        CANONICAL_BRAND_MAP = yaml.safe_load(f) or {}

def normalize_brand(brand_raw: str) -> Tuple[str, str, str]:
    """Normalize brand and return (brand, brand_slug, brand_family)"""
    if not brand_raw:
        return ("Unknown", "unknown", "unknown")
    
    brand_lower = brand_raw.lower().strip()
    
    # Check phrase map first
    for phrase, canonical in BRAND_PHRASE_MAP.items():
        if phrase in brand_lower:
            brand = canonical
            break
    else:
        # Check canonical map
        brand = CANONICAL_BRAND_MAP.get(brand_raw, brand_raw)
    
    # Generate slug
    brand_slug = re.sub(r'[^a-z0-9]+', '_', brand.lower()).strip('_')
    
    # Determine family (simplified)
    brand_family = brand_slug.split('_')[0] if '_' in brand_slug else brand_slug
    
    return (brand, brand_slug, brand_family)

def generate_name_slug(product_name: str) -> str:
    """Generate name slug from product name"""
    if not product_name:
        return "unknown"
    slug = re.sub(r'[^a-z0-9]+', '-', product_name.lower()).strip('-')
    return slug[:100]  # Limit length

def generate_product_key(brand_slug: str, name_slug: str, form: str = None) -> str:
    """Generate deterministic product key"""
    base_key = f"{brand_slug}::{name_slug}"
    if form:
        base_key += f"::{form}"
    # Add hash suffix for uniqueness
    hash_suffix = hashlib.md5(base_key.encode()).hexdigest()[:6]
    return f"{brand_slug}_{hash_suffix}"

def extract_weight_from_text(text: str) -> Optional[float]:
    """Extract weight in kg from text containing lb, oz, kg"""
    if not text:
        return None
    
    # Look for patterns like "30 lb", "15.5 lbs", "4 oz", "2.5 kg"
    # Also handle "30-lb" format
    patterns = [
        (r'(\d+(?:\.\d+)?)\s*[-]?lb', 0.453592),  # pounds to kg
        (r'(\d+(?:\.\d+)?)\s*[-]?oz', 0.0283495),  # ounces to kg
        (r'(\d+(?:\.\d+)?)\s*[-]?kg', 1.0),        # already kg
    ]
    
    for pattern, conversion in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            return value * conversion
    
    return None

def parse_chewy_specifications(desc_text: str) -> Dict:
    """Parse Chewy's Specifications block from description"""
    specs = {}
    
    if not desc_text:
        return specs
    
    # Look for Specifications section
    if 'Specifications' in desc_text:
        spec_section = desc_text.split('Specifications')[-1]
        
        # Common patterns in Chewy specs
        patterns = {
            'lifestage': r'Lifestage[:\s]+([^,\n]+)',
            'food_form': r'Food Form[:\s]+([^,\n]+)',
            'special_diet': r'Special Diet[:\s]+([^,\n]+)',
            'item_number': r'Item Number[:\s]+([^,\n]+)',
            'breed_size': r'Breed Size[:\s]+([^,\n]+)',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, spec_section, re.IGNORECASE)
            if match:
                specs[key] = match.group(1).strip()
    
    return specs

def extract_brand_from_chewy(item: Dict) -> str:
    """Extract brand from Chewy item - improved logic"""
    # Try brand.slogan first (most common in this dataset)
    if item.get('brand') and isinstance(item['brand'], dict):
        if item['brand'].get('slogan'):
            return item['brand']['slogan']
        if item['brand'].get('name'):
            return item['brand']['name']
    
    # Try extracting from product name (first word before space often is brand)
    name = item.get('name', '')
    if name:
        # Common brand patterns in names
        brand_patterns = [
            r'^([\w\s&\']+?)\s+(?:Dog|Puppy|Adult|Senior|Grain)',  # Brand before product type
            r'^([\w\s&\']+?)\s+(?:Dry|Wet|Raw|Freeze)',  # Brand before form
            r'^([\w\s&\']+?)\s+\w+\s+Recipe',  # Brand before "X Recipe"
        ]
        
        for pattern in brand_patterns:
            match = re.match(pattern, name, re.IGNORECASE)
            if match:
                potential_brand = match.group(1).strip()
                # Filter out common non-brand words
                if potential_brand.lower() not in ['the', 'a', 'an', 'dog', 'cat']:
                    return potential_brand
    
    return ''

def detect_form(text: str, specs: Dict = None) -> Optional[str]:
    """Detect product form from text and specifications"""
    if specs and specs.get('food_form'):
        form_text = specs['food_form'].lower()
        if 'dry' in form_text or 'kibble' in form_text:
            return 'dry'
        elif 'wet' in form_text or 'can' in form_text or 'pate' in form_text:
            return 'wet'
        elif 'raw' in form_text or 'freeze' in form_text or 'air-dried' in form_text:
            return 'raw'
    
    # Fallback to text analysis
    text_lower = (text or '').lower()
    if any(word in text_lower for word in ['dry food', 'kibble', 'dry dog', 'air-dried']):
        return 'dry'
    elif any(word in text_lower for word in ['wet food', 'canned', 'pate', 'paté', 'chunks', 'stew', 'gravy']):
        return 'wet'
    elif any(word in text_lower for word in ['raw', 'freeze-dried', 'frozen', 'air-dried']):
        return 'raw'
    elif any(word in text_lower for word in ['treat', 'topper', 'supplement', 'booster']):
        return 'treat'
    
    return None

def detect_life_stage(text: str, specs: Dict = None) -> Optional[str]:
    """Detect life stage from text and specifications"""
    if specs and specs.get('lifestage'):
        stage_text = specs['lifestage'].lower()
        if 'puppy' in stage_text or 'junior' in stage_text:
            return 'puppy'
        elif 'adult' in stage_text:
            return 'adult'
        elif 'senior' in stage_text:
            return 'senior'
        elif 'all' in stage_text:
            return 'all'
    
    # Fallback to text analysis
    text_lower = (text or '').lower()
    if 'puppy' in text_lower or 'junior' in text_lower:
        return 'puppy'
    elif 'senior' in text_lower or 'mature' in text_lower:
        return 'senior'
    elif 'adult' in text_lower:
        return 'adult'
    elif 'all life' in text_lower or 'all stage' in text_lower or 'all ages' in text_lower:
        return 'all'
    
    return None

def analyze_chewy_dataset():
    """Analyze Chewy JSON dataset - improved"""
    print("\nAnalyzing Chewy dataset...")
    
    with open("data/chewy/chewy-dataset.json") as f:
        data = json.load(f)
    
    products = []
    stats = {
        'total': 0,
        'dog_products': 0,
        'treats_toppers': 0,
        'has_price': 0,
        'has_weight': 0,
        'has_form': 0,
        'has_life_stage': 0,
        'has_brand': 0,
        'brands': set(),
        'sample_products': [],
    }
    
    for item in data:
        stats['total'] += 1
        
        # Check if it's a dog product
        name = item.get('name', '')
        url = item.get('url', '')
        desc = item.get('description', '')
        
        # More comprehensive dog product check
        is_dog = ('dog' in url.lower() or 'dog' in name.lower() or 
                  'dog' in desc.lower() or '/dp/' in url)  # Chewy dog products have /dp/ in URL
        
        if not is_dog:
            continue
        
        stats['dog_products'] += 1
        
        # Extract brand - improved
        brand_raw = extract_brand_from_chewy(item)
        
        if brand_raw:
            stats['has_brand'] += 1
            stats['brands'].add(brand_raw)
        
        # Normalize brand
        brand, brand_slug, brand_family = normalize_brand(brand_raw)
        
        # Parse specifications
        specs = parse_chewy_specifications(desc)
        
        # Detect form and life stage
        form = detect_form(name + ' ' + desc, specs)
        life_stage = detect_life_stage(name + ' ' + desc, specs)
        
        if form:
            stats['has_form'] += 1
        if life_stage:
            stats['has_life_stage'] += 1
        
        # Check if treat/topper
        if form == 'treat' or any(word in name.lower() for word in ['topper', 'supplement', 'booster']):
            stats['treats_toppers'] += 1
        
        # Extract price and weight
        price = None
        currency = 'USD'
        weight_kg = extract_weight_from_text(name)
        
        if item.get('offers'):
            offers = item['offers']
            if isinstance(offers, dict):
                price = offers.get('price')
                currency = offers.get('priceCurrency', 'USD')
            elif isinstance(offers, list) and offers:
                price = offers[0].get('price')
                currency = offers[0].get('priceCurrency', 'USD')
        
        if price:
            stats['has_price'] += 1
        if weight_kg:
            stats['has_weight'] += 1
        
        # Calculate price per kg
        price_per_kg = None
        if price and weight_kg:
            try:
                price_float = float(price) if isinstance(price, (int, str)) else price
                price_per_kg = price_float / weight_kg
                # Convert USD to EUR (placeholder rate 0.92)
                if currency == 'USD':
                    price_per_kg *= 0.92
            except:
                pass
        
        # Generate keys
        name_slug = generate_name_slug(name)
        product_key = generate_product_key(brand_slug, name_slug, form)
        
        # Create product record
        product = {
            'product_key': product_key,
            'brand': brand,
            'brand_slug': brand_slug,
            'brand_family': brand_family,
            'product_name': name,
            'name_slug': name_slug,
            'form': form,
            'life_stage': life_stage,
            'kcal_per_100g': None,  # Not in Chewy data
            'protein_percent': None,
            'fat_percent': None,
            'fiber_percent': None,
            'ash_percent': None,
            'moisture_percent': None,
            'ingredients_raw': None,  # Not typically in Chewy data
            'ingredients_tokens': json.dumps([]),
            'price_per_kg_eur': price_per_kg,
            'price_bucket': 'medium' if price_per_kg and 10 <= price_per_kg <= 50 else 'high' if price_per_kg and price_per_kg > 50 else 'low' if price_per_kg else None,
            'available_countries': json.dumps(['US']),
            'sources': json.dumps([{'type': 'retailer:chewy', 'url': url}]),
            'product_url': url,
            'staging_source': 'chewy',
            'staging_confidence': 0.8 if brand_raw and form and life_stage else 0.6 if form and life_stage else 0.4,
        }
        
        products.append(product)
        
        # Collect samples
        if len(stats['sample_products']) < 5:
            stats['sample_products'].append({
                'name': name[:80],
                'brand': brand,
                'form': form,
                'life_stage': life_stage,
                'weight': weight_kg,
                'price_per_kg': price_per_kg
            })
    
    return products, stats

def analyze_aadf_dataset():
    """Analyze AADF CSV dataset - improved"""
    print("\nAnalyzing AADF dataset...")
    
    products = []
    stats = {
        'total': 0,
        'dog_products': 0,
        'treats_toppers': 0,
        'has_price': 0,
        'has_weight': 0,
        'has_form': 0,
        'has_life_stage': 0,
        'has_brand': 0,
        'has_ingredients': 0,
        'brands': set(),
        'sample_products': [],
    }
    
    # Read CSV
    df = pd.read_csv("data/aadf/aadf-dataset.csv")
    stats['total'] = len(df)
    
    for _, row in df.iterrows():
        # Extract product name from data-page-selector
        product_name_raw = str(row.get('data-page-selector', ''))
        
        # Clean up product name (remove newlines, extra spaces)
        product_name = re.sub(r'\s+', ' ', product_name_raw).strip()
        
        # Skip if no valid product name
        if not product_name or len(product_name) < 3:
            continue
        
        stats['dog_products'] += 1
        
        # Extract brand from product name (usually first part)
        brand_raw = ''
        if product_name:
            # Try to extract brand (usually first word or two)
            parts = product_name.split()
            if parts:
                # Common patterns: "Brand Name Product" or "Brand's Product"
                if len(parts) > 1:
                    if parts[1].lower() in ['dog', 'puppy', 'adult', 'senior', 'grain', 'dry', 'wet']:
                        brand_raw = parts[0]
                    elif "'" in parts[0]:  # Like "Nature's"
                        brand_raw = parts[0]
                    else:
                        # Take first two words as potential brand
                        brand_raw = ' '.join(parts[:2])
                else:
                    brand_raw = parts[0]
        
        if brand_raw:
            stats['has_brand'] += 1
            stats['brands'].add(brand_raw)
        
        # Normalize brand
        brand, brand_slug, brand_family = normalize_brand(brand_raw)
        
        # Extract form from type_of_food-0
        type_of_food = str(row.get('type_of_food-0', ''))
        form = None
        if 'dry' in type_of_food.lower() or 'kibble' in type_of_food.lower():
            form = 'dry'
        elif 'wet' in type_of_food.lower() or 'pate' in type_of_food.lower() or 'paté' in type_of_food.lower():
            form = 'wet'
        elif 'raw' in type_of_food.lower() or 'freeze' in type_of_food.lower():
            form = 'raw'
        elif 'complete' in type_of_food.lower():
            # Try to determine from product name
            form = detect_form(product_name)
        
        if form:
            stats['has_form'] += 1
        
        # Extract life stage from dog_ages-0
        dog_ages = str(row.get('dog_ages-0', ''))
        life_stage = None
        if 'puppy' in dog_ages.lower() or 'junior' in dog_ages.lower() or 'young' in dog_ages.lower():
            life_stage = 'puppy'
        elif 'senior' in dog_ages.lower() or 'old' in dog_ages.lower():
            life_stage = 'senior'
        elif 'adult' in dog_ages.lower() or '12 months' in dog_ages.lower():
            life_stage = 'adult'
        elif 'all' in dog_ages.lower():
            life_stage = 'all'
        
        if life_stage:
            stats['has_life_stage'] += 1
        
        # Check if treat/topper
        if form == 'treat' or any(word in product_name.lower() for word in ['topper', 'supplement', 'mixer']):
            stats['treats_toppers'] += 1
        
        # Extract price (price per day)
        price_per_day = row.get('price_per_day-0')
        if price_per_day and str(price_per_day) != 'nan':
            stats['has_price'] += 1
            try:
                # Convert price per day to approximate price per kg
                # Assume average dog eats 300g/day
                price_per_kg = float(price_per_day) * (1000/300) * 0.92  # Convert to EUR
            except:
                price_per_kg = None
        else:
            price_per_kg = None
        
        # Extract ingredients if available
        ingredients_raw = row.get('ingredients-0')
        if ingredients_raw and str(ingredients_raw) != 'nan':
            stats['has_ingredients'] += 1
            ingredients_raw = str(ingredients_raw)
        else:
            ingredients_raw = None
        
        # Extract URL from href
        url = str(row.get('data-page-selector-href', ''))
        if url == 'nan':
            url = f"https://www.allaboutdogfood.co.uk/product/{brand_slug}/{generate_name_slug(product_name)}"
        
        # Generate keys
        name_slug = generate_name_slug(product_name)
        product_key = generate_product_key(brand_slug, name_slug, form)
        
        # Create product record
        product = {
            'product_key': product_key,
            'brand': brand,
            'brand_slug': brand_slug,
            'brand_family': brand_family,
            'product_name': product_name,
            'name_slug': name_slug,
            'form': form,
            'life_stage': life_stage,
            'kcal_per_100g': None,
            'protein_percent': None,
            'fat_percent': None,
            'fiber_percent': None,
            'ash_percent': None,
            'moisture_percent': None,
            'ingredients_raw': ingredients_raw,
            'ingredients_tokens': json.dumps([]) if not ingredients_raw else json.dumps(
                [i.strip() for i in re.split(r'[,;]', ingredients_raw) if i.strip()][:20]
            ),
            'price_per_kg_eur': price_per_kg,
            'price_bucket': 'medium' if price_per_kg and 10 <= price_per_kg <= 50 else 'high' if price_per_kg and price_per_kg > 50 else 'low' if price_per_kg else None,
            'available_countries': json.dumps(['UK']),
            'sources': json.dumps([{'type': 'retailer:aadf', 'url': url}]),
            'product_url': url,
            'staging_source': 'aadf',
            'staging_confidence': 0.7 if brand_raw and form and life_stage else 0.5 if form or life_stage else 0.3,
        }
        
        products.append(product)
        
        # Collect samples
        if len(stats['sample_products']) < 5:
            stats['sample_products'].append({
                'name': product_name[:80],
                'brand': brand,
                'form': form,
                'life_stage': life_stage,
                'type_of_food': type_of_food[:30],
                'dog_ages': dog_ages[:30]
            })
    
    return products, stats

def main():
    """Main execution"""
    print("="*80)
    print("RETAILER DATA AUDIT & STAGING - V2")
    print("="*80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Analyze Chewy
    chewy_products, chewy_stats = analyze_chewy_dataset()
    
    # Analyze AADF
    aadf_products, aadf_stats = analyze_aadf_dataset()
    
    # Save staging CSVs
    print("\nSaving staging CSVs...")
    
    chewy_df = pd.DataFrame(chewy_products)
    chewy_df.to_csv("data/staging/retailer_staging.chewy.csv", index=False)
    print(f"  Saved {len(chewy_products)} Chewy products to data/staging/retailer_staging.chewy.csv")
    
    aadf_df = pd.DataFrame(aadf_products)
    aadf_df.to_csv("data/staging/retailer_staging.aadf.csv", index=False)
    print(f"  Saved {len(aadf_products)} AADF products to data/staging/retailer_staging.aadf.csv")
    
    # Print summary statistics
    print("\n" + "="*80)
    print("AUDIT SUMMARY")
    print("="*80)
    
    print("\nCHEWY Dataset:")
    print(f"  Total records: {chewy_stats['total']}")
    print(f"  Dog products: {chewy_stats['dog_products']}")
    print(f"  Treats/toppers: {chewy_stats['treats_toppers']}")
    print(f"  Has brand: {chewy_stats['has_brand']}")
    print(f"  Has form: {chewy_stats['has_form']}")
    print(f"  Has life_stage: {chewy_stats['has_life_stage']}")
    print(f"  Has price: {chewy_stats['has_price']}")
    print(f"  Has weight: {chewy_stats['has_weight']}")
    print(f"  Unique brands: {len(chewy_stats['brands'])}")
    
    print("\n  Sample products:")
    for i, sample in enumerate(chewy_stats['sample_products'][:3], 1):
        print(f"    {i}. {sample['name']}")
        print(f"       Brand: {sample['brand']}, Form: {sample['form']}, Stage: {sample['life_stage']}")
    
    print("\nAADF Dataset:")
    print(f"  Total records: {aadf_stats['total']}")
    print(f"  Dog products: {aadf_stats['dog_products']}")
    print(f"  Treats/toppers: {aadf_stats['treats_toppers']}")
    print(f"  Has brand: {aadf_stats['has_brand']}")
    print(f"  Has form: {aadf_stats['has_form']}")
    print(f"  Has life_stage: {aadf_stats['has_life_stage']}")
    print(f"  Has ingredients: {aadf_stats['has_ingredients']}")
    print(f"  Unique brands: {len(aadf_stats['brands'])}")
    
    print("\n  Sample products:")
    for i, sample in enumerate(aadf_stats['sample_products'][:3], 1):
        print(f"    {i}. {sample['name']}")
        print(f"       Form: {sample['form']}, Stage: {sample['life_stage']}")
    
    # Show top brands across both datasets
    print("\nTop 10 brands by product count (combined):")
    all_products = chewy_products + aadf_products
    brand_counts = {}
    for p in all_products:
        brand = p['brand']
        brand_counts[brand] = brand_counts.get(brand, 0) + 1
    
    for brand, count in sorted(brand_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {brand}: {count} products")
    
    print("\n" + "="*80)
    print("QUICK ASSESSMENT:")
    print("="*80)
    
    # Calculate potential impact
    total_products = len(chewy_products) + len(aadf_products)
    products_with_form = sum(1 for p in all_products if p['form'])
    products_with_stage = sum(1 for p in all_products if p['life_stage'])
    products_with_price = sum(1 for p in all_products if p['price_per_kg_eur'])
    
    print(f"Total staged products: {total_products}")
    print(f"Products with form: {products_with_form} ({100*products_with_form/total_products:.1f}%)")
    print(f"Products with life_stage: {products_with_stage} ({100*products_with_stage/total_products:.1f}%)")
    print(f"Products with price data: {products_with_price} ({100*products_with_price/total_products:.1f}%)")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()