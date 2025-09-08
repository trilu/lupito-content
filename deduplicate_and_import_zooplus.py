#!/usr/bin/env python3
"""
Deduplicate and import Zooplus data
Keeps the best version of each product (most nutrition data, all pack sizes)
"""
import json
import re
import sys
from datetime import datetime
from typing import Dict, List, Optional
import logging
from supabase import create_client, Client
import os
from collections import defaultdict

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Supabase configuration
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://cibjeqgftuxuezarjsdl.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNpYmplcWdmdHV4dWV6YXJqc2RsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1Mzg1NTY2NywiZXhwIjoyMDY5NDMxNjY3fQ.ngzgvYr2zXisvkz03F86zNWPRHP0tEMX0gQPBm2z_jk')


def extract_brand(product: Dict) -> Optional[str]:
    """Extract real brand name from product data"""
    breadcrumbs = product.get('breadcrumbs', [])
    if len(breadcrumbs) > 2:
        brand = breadcrumbs[2]
        if brand and not any(skip in brand.lower() for skip in ['x ', 'kg', 'ml', 'g)', 'pack']):
            return brand
    
    brand_field = product.get('brand', '')
    if brand_field and 'logo' not in brand_field.lower():
        return brand_field
    
    name = product.get('name', '')
    known_brands = [
        'Royal Canin', 'Hill\'s', 'Purina', 'Eukanuba', 'Pro Plan',
        'Rocco', 'Wolf of Wilderness', 'Lukullus', 'Animonda', 
        'Almo Nature', 'Concept for Life', 'James Wellbeloved',
        'Affinity', 'Advance', 'Ultima', 'Acana', 'Orijen',
        'RINTI', 'MAC\'s', 'GranataPet', 'Smilla', 'Feringa'
    ]
    
    for brand in known_brands:
        if name.startswith(brand):
            return brand
    
    return None


def get_product_base_key(product: Dict) -> str:
    """Get a base key for the product without size/pack info"""
    brand = extract_brand(product)
    if not brand:
        return None
    
    name = product.get('name', '')
    
    # Remove pack size information
    base_name = re.sub(r'\d+\s*x\s*\d+[gkml]', '', name, flags=re.IGNORECASE)
    base_name = re.sub(r'saver pack|mega pack', '', base_name, flags=re.IGNORECASE)
    base_name = re.sub(r'\d+\.?\d*\s*(kg|g|ml|l)\b', '', base_name, flags=re.IGNORECASE)
    base_name = re.sub(r'\s+', ' ', base_name).strip()
    
    # Remove trailing dashes or colons
    base_name = re.sub(r'[-:]\s*$', '', base_name).strip()
    
    return f"{brand}||{base_name}"


def parse_nutrition_value(value: str) -> Optional[float]:
    """Parse nutrition percentage from string"""
    if not value:
        return None
    value = value.replace('%', '').strip().replace(',', '.')
    try:
        return float(value)
    except ValueError:
        return None


def extract_all_pack_sizes(products: List[Dict]) -> List[str]:
    """Extract all unique pack sizes from a list of product variants"""
    sizes = set()
    
    for product in products:
        name = product.get('name', '')
        
        # Multi-pack pattern: 6 x 400g
        multi_pack = re.findall(r'(\d+)\s*x\s*(\d+(?:\.\d+)?)\s*(kg|g|ml|l)', name, re.IGNORECASE)
        for match in multi_pack:
            sizes.add(f"{match[0]} x {match[1]}{match[2].lower()}")
        
        # Single pack pattern: 2.5kg
        single_pack = re.findall(r'(\d+(?:\.\d+)?)\s*(kg|g|ml|l)(?:\s|$)', name, re.IGNORECASE)
        for match in single_pack:
            # Skip if it's part of a multi-pack
            if not any(f"x {match[0]}" in str(m) for m in multi_pack):
                sizes.add(f"{match[0]}{match[1].lower()}")
    
    return sorted(list(sizes))


def get_price_range(products: List[Dict]) -> Dict:
    """Get min and max prices from product variants"""
    prices = [p.get('price', 0) for p in products if p.get('price')]
    if not prices:
        return {'min': None, 'max': None, 'median': None}
    
    prices.sort()
    return {
        'min': prices[0],
        'max': prices[-1],
        'median': prices[len(prices)//2]
    }


def merge_product_variants(products: List[Dict]) -> Dict:
    """Merge multiple variants into a single product with all information"""
    if not products:
        return None
    
    # Sort by completeness (products with more nutrition data first)
    def completeness_score(p):
        score = 0
        attrs = p.get('attributes', {})
        if attrs.get('protein'): score += 1
        if attrs.get('fat'): score += 1
        if attrs.get('fibre'): score += 1
        if attrs.get('ash'): score += 1
        if attrs.get('moisture'): score += 1
        if p.get('description'): score += 1
        if p.get('rating_value'): score += 1
        return score
    
    products.sort(key=completeness_score, reverse=True)
    
    # Use the most complete product as base
    best = products[0]
    
    # Merge information from all variants
    merged = {
        'brand': extract_brand(best),
        'product_name': best.get('name', ''),
        'category': best.get('category', ''),
        'description': best.get('description', ''),
        'attributes': best.get('attributes', {}),
        'main_image': best.get('main_image', ''),
        'images': best.get('images', []),
        'url': best.get('url', ''),
        'sku': best.get('sku', ''),
        'currency': best.get('currency', 'EUR'),
        'scraped_at': best.get('scraped_at'),
        'features': best.get('features', []),
        
        # Aggregate fields
        'pack_sizes': extract_all_pack_sizes(products),
        'price_range': get_price_range(products),
        'variants_count': len(products),
        
        # Use max values for ratings
        'rating_value': max((p.get('rating_value') or 0 for p in products), default=0),
        'review_count': max((p.get('review_count') or 0 for p in products), default=0),
    }
    
    # Clean up product name (remove pack size from name)
    base_name = re.sub(r'\d+\s*x\s*\d+[gkml].*$', '', merged['product_name'], flags=re.IGNORECASE)
    base_name = re.sub(r'\d+\.?\d*\s*(kg|g|ml|l)\s*$', '', base_name, flags=re.IGNORECASE)
    merged['product_name'] = base_name.strip()
    
    # Use median price as the main price
    merged['price'] = merged['price_range']['median']
    
    return merged


def determine_form(product: Dict) -> str:
    """Determine product form (dry, wet, raw, etc.)"""
    category = product.get('category', '').lower()
    name = product.get('product_name', '').lower()
    
    if 'dry' in category or 'kibble' in name:
        return 'dry'
    elif 'wet' in category or 'canned' in category or 'can' in name or 'pouch' in name:
        return 'wet'
    elif 'raw' in category or 'raw' in name:
        return 'raw'
    else:
        moisture = product.get('attributes', {}).get('moisture')
        if moisture:
            moisture_val = parse_nutrition_value(moisture)
            if moisture_val:
                if moisture_val > 60:
                    return 'wet'
                elif moisture_val < 20:
                    return 'dry'
    
    return 'dry'


def transform_to_database_format(product: Dict) -> Dict:
    """Transform merged product to database format"""
    attributes = product.get('attributes', {})
    
    record = {
        # Basic info
        'brand': product['brand'],
        'product_name': product['product_name'],
        'form': determine_form(product),
        
        # Nutrition
        'protein_percent': parse_nutrition_value(attributes.get('protein')),
        'fat_percent': parse_nutrition_value(attributes.get('fat')),
        'fiber_percent': parse_nutrition_value(attributes.get('fibre')),
        'ash_percent': parse_nutrition_value(attributes.get('ash')),
        'moisture_percent': parse_nutrition_value(attributes.get('moisture')),
        
        # Ingredients (description contains ingredient info)
        'ingredients_raw': product.get('description', ''),
        
        # Package info - store as JSONB array
        'pack_sizes': product.get('pack_sizes', []),
        
        # Retailer info
        'retailer_source': 'zooplus',
        'retailer_url': product.get('url', ''),
        'retailer_product_id': product.get('sku', ''),
        'retailer_sku': product.get('sku', ''),
        'retailer_price_eur': product.get('price'),
        'retailer_original_price_eur': product['price_range']['max'] if product.get('price_range') else None,
        'retailer_currency': product.get('currency', 'EUR'),
        'retailer_rating': product.get('rating_value'),
        'retailer_review_count': product.get('review_count'),
        
        # Images
        'image_url': product.get('main_image'),
        'image_urls': product.get('images', []),
        
        # Metadata
        'data_source': 'scraper',
        'last_scraped_at': product.get('scraped_at'),
        
        # Data quality
        'data_complete': False
    }
    
    # Check if data is complete
    has_nutrition = any([
        record['protein_percent'],
        record['fat_percent'],
        record['fiber_percent']
    ])
    
    record['data_complete'] = (
        bool(record['brand']) and
        bool(record['product_name']) and
        has_nutrition and
        bool(record['retailer_price_eur'])
    )
    
    return record


def main():
    """Main entry point"""
    json_file = 'docs/dataset_zooplus-scraper_2025-09-08_15-48-47-523.json'
    
    if not os.path.exists(json_file):
        logger.error(f"File not found: {json_file}")
        sys.exit(1)
    
    # Load data
    logger.info(f"Loading data from {json_file}")
    with open(json_file, 'r', encoding='utf-8') as f:
        products = json.load(f)
    logger.info(f"Loaded {len(products)} products")
    
    # Group products by base key
    logger.info("Grouping products by base key...")
    product_groups = defaultdict(list)
    skipped = 0
    
    for product in products:
        key = get_product_base_key(product)
        if key:
            product_groups[key].append(product)
        else:
            skipped += 1
    
    logger.info(f"Found {len(product_groups)} unique products ({skipped} skipped)")
    
    # Merge variants and transform
    logger.info("Merging variants and transforming...")
    final_products = []
    brands = set()
    with_nutrition = 0
    
    for key, variants in product_groups.items():
        merged = merge_product_variants(variants)
        if merged and merged['brand']:
            record = transform_to_database_format(merged)
            final_products.append(record)
            brands.add(record['brand'])
            
            if any([record['protein_percent'], record['fat_percent'], record['fiber_percent']]):
                with_nutrition += 1
    
    logger.info(f"Prepared {len(final_products)} unique products for import")
    logger.info(f"Products with nutrition: {with_nutrition}")
    logger.info(f"Unique brands: {len(brands)}")
    
    # Connect to Supabase
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Delete existing Zooplus products first (clean slate)
    logger.info("Cleaning existing Zooplus products...")
    try:
        supabase.table('food_candidates_sc').delete().eq('retailer_source', 'zooplus').execute()
        logger.info("Cleared existing Zooplus products")
    except Exception as e:
        logger.warning(f"Could not clear existing products: {e}")
    
    # Import in batches
    batch_size = 50
    total_imported = 0
    total_errors = 0
    
    logger.info("Starting import...")
    
    for i in range(0, len(final_products), batch_size):
        batch = final_products[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(final_products) + batch_size - 1) // batch_size
        
        try:
            response = supabase.table('food_candidates_sc').insert(batch).execute()
            total_imported += len(batch)
            logger.info(f"Batch {batch_num}/{total_batches}: Imported {len(batch)} products")
            
        except Exception as e:
            logger.error(f"Batch {batch_num} error: {str(e)[:200]}")
            # Try individual inserts
            for record in batch:
                try:
                    supabase.table('food_candidates_sc').insert(record).execute()
                    total_imported += 1
                except Exception as e2:
                    total_errors += 1
                    logger.debug(f"Failed: {record['brand']} - {record['product_name'][:30]}")
    
    # Print summary
    print("\n" + "="*60)
    print("DEDUPLICATION AND IMPORT SUMMARY")
    print("="*60)
    print(f"Original products in file: {len(products)}")
    print(f"Unique products after deduplication: {len(final_products)}")
    print(f"Successfully imported: {total_imported}")
    print(f"Failed: {total_errors}")
    print(f"Products with nutrition: {with_nutrition}")
    print(f"Unique brands: {len(brands)}")
    
    if brands:
        print(f"\nTop brands imported:")
        brand_list = sorted(brands)[:20]
        for brand in brand_list:
            print(f"  - {brand}")
    
    success_rate = (total_imported / len(final_products) * 100) if len(final_products) > 0 else 0
    print(f"\nSuccess rate: {success_rate:.1f}%")
    print("="*60)


if __name__ == "__main__":
    main()