#!/usr/bin/env python3
"""
Analyze and stage Chewy and AADF retailer datasets
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
    patterns = [
        (r'(\d+(?:\.\d+)?)\s*lb', 0.453592),  # pounds to kg
        (r'(\d+(?:\.\d+)?)\s*oz', 0.0283495),  # ounces to kg
        (r'(\d+(?:\.\d+)?)\s*kg', 1.0),        # already kg
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

def detect_form(text: str, specs: Dict = None) -> Optional[str]:
    """Detect product form from text and specifications"""
    if specs and specs.get('food_form'):
        form_text = specs['food_form'].lower()
        if 'dry' in form_text or 'kibble' in form_text:
            return 'dry'
        elif 'wet' in form_text or 'can' in form_text:
            return 'wet'
        elif 'raw' in form_text or 'freeze' in form_text:
            return 'raw'
    
    # Fallback to text analysis
    text_lower = (text or '').lower()
    if any(word in text_lower for word in ['dry food', 'kibble', 'dry dog']):
        return 'dry'
    elif any(word in text_lower for word in ['wet food', 'canned', 'pate', 'chunks']):
        return 'wet'
    elif any(word in text_lower for word in ['raw', 'freeze-dried', 'frozen']):
        return 'raw'
    elif any(word in text_lower for word in ['treat', 'topper', 'supplement']):
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
    elif 'all life' in text_lower or 'all stage' in text_lower:
        return 'all'
    
    return None

def analyze_chewy_dataset():
    """Analyze Chewy JSON dataset"""
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
    }
    
    for item in data:
        stats['total'] += 1
        
        # Check if it's a dog product
        name = item.get('name', '')
        url = item.get('url', '')
        if 'dog' not in url.lower() and 'dog' not in name.lower():
            continue
        
        stats['dog_products'] += 1
        
        # Extract brand (often in slogan or brand field)
        brand_raw = item.get('brand', {}).get('name') if isinstance(item.get('brand'), dict) else item.get('brand', '')
        if not brand_raw and item.get('slogan'):
            # Try to extract brand from slogan
            brand_raw = item['slogan'].split(',')[0] if ',' in item['slogan'] else ''
        
        if brand_raw:
            stats['has_brand'] += 1
            stats['brands'].add(brand_raw)
        
        # Normalize brand
        brand, brand_slug, brand_family = normalize_brand(brand_raw)
        
        # Parse specifications
        desc = item.get('description', '')
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
        weight_kg = None
        
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
        
        # Extract weight from name
        weight_kg = extract_weight_from_text(name)
        if weight_kg:
            stats['has_weight'] += 1
        
        # Calculate price per kg
        price_per_kg = None
        if price and weight_kg:
            price_float = float(price) if isinstance(price, (int, str)) else price
            price_per_kg = price_float / weight_kg
            # Convert USD to EUR (placeholder rate 0.92)
            if currency == 'USD':
                price_per_kg *= 0.92
        
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
            'ingredients_raw': None,  # Not in Chewy data
            'ingredients_tokens': json.dumps([]),
            'price_per_kg_eur': price_per_kg,
            'price_bucket': 'medium' if price_per_kg and 10 <= price_per_kg <= 50 else 'high' if price_per_kg and price_per_kg > 50 else 'low',
            'available_countries': json.dumps(['US']),
            'sources': json.dumps([{'type': 'retailer:chewy', 'url': url}]),
            'product_url': url,
            'staging_source': 'chewy',
            'staging_confidence': 0.7 if form and life_stage else 0.5,
        }
        
        products.append(product)
    
    return products, stats

def analyze_aadf_dataset():
    """Analyze AADF CSV dataset"""
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
        'brands': set(),
    }
    
    # Read CSV
    df = pd.read_csv("data/aadf/aadf-dataset.csv")
    stats['total'] = len(df)
    
    for _, row in df.iterrows():
        # Extract fields - adjust based on actual CSV structure
        link = row.get('link', '') if 'link' in row else ''
        
        # Try to extract product name from link
        product_name = ''
        if link:
            # Extract last part of URL path as product name
            parts = link.rstrip('/').split('/')
            if parts:
                product_name = parts[-1].replace('-', ' ').title()
        
        # If no link, try other fields
        if not product_name:
            product_name = row.get('title', '') if 'title' in row else row.get('product_name', '') if 'product_name' in row else ''
        
        if not product_name:
            continue
        
        # Check if dog product
        if 'dog' not in link.lower() and 'dog' not in product_name.lower():
            # Might be dog food even without 'dog' in URL
            pass  # Keep for now
        
        stats['dog_products'] += 1
        
        # Extract brand from link or other fields
        brand_raw = row.get('brand', '') if 'brand' in row else ''
        if not brand_raw and link:
            # Try to extract brand from URL structure
            parts = link.split('/')
            for i, part in enumerate(parts):
                if 'brand' in part.lower() and i+1 < len(parts):
                    brand_raw = parts[i+1].replace('-', ' ').title()
                    break
        
        if brand_raw:
            stats['has_brand'] += 1
            stats['brands'].add(brand_raw)
        
        # Normalize brand
        brand, brand_slug, brand_family = normalize_brand(brand_raw)
        
        # Detect form and life stage from product name
        form = detect_form(product_name)
        life_stage = detect_life_stage(product_name)
        
        if form:
            stats['has_form'] += 1
        if life_stage:
            stats['has_life_stage'] += 1
        
        # Check if treat/topper
        if form == 'treat' or any(word in product_name.lower() for word in ['topper', 'supplement', 'booster']):
            stats['treats_toppers'] += 1
        
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
            'ingredients_raw': None,
            'ingredients_tokens': json.dumps([]),
            'price_per_kg_eur': None,
            'price_bucket': None,
            'available_countries': json.dumps(['US']),
            'sources': json.dumps([{'type': 'retailer:aadf', 'url': link}]),
            'product_url': link,
            'staging_source': 'aadf',
            'staging_confidence': 0.5 if form or life_stage else 0.3,
        }
        
        products.append(product)
    
    return products, stats

def main():
    """Main execution"""
    print("="*80)
    print("RETAILER DATA AUDIT & STAGING")
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
    
    print("\nAADF Dataset:")
    print(f"  Total records: {aadf_stats['total']}")
    print(f"  Dog products: {aadf_stats['dog_products']}")
    print(f"  Treats/toppers: {aadf_stats['treats_toppers']}")
    print(f"  Has brand: {aadf_stats['has_brand']}")
    print(f"  Has form: {aadf_stats['has_form']}")
    print(f"  Has life_stage: {aadf_stats['has_life_stage']}")
    print(f"  Unique brands: {len(aadf_stats['brands'])}")
    
    # Show top brands
    print("\nTop 5 brands by product count:")
    all_products = chewy_products + aadf_products
    brand_counts = {}
    for p in all_products:
        brand = p['brand']
        brand_counts[brand] = brand_counts.get(brand, 0) + 1
    
    for brand, count in sorted(brand_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {brand}: {count} products")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()