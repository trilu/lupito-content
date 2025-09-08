#!/usr/bin/env python3
"""
Fast import of Zooplus scraped data using batch operations
"""
import json
import re
import sys
from datetime import datetime
from typing import Dict, List, Optional
import logging
from supabase import create_client, Client
import os

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
    # First try breadcrumbs (most reliable)
    breadcrumbs = product.get('breadcrumbs', [])
    if len(breadcrumbs) > 2:
        # Third element is usually the brand
        brand = breadcrumbs[2]
        # Clean up brand name
        if brand and not any(skip in brand.lower() for skip in ['x ', 'kg', 'ml', 'g)', 'pack']):
            return brand
    
    # Fallback to brand field if not "zooplus logo"
    brand_field = product.get('brand', '')
    if brand_field and 'logo' not in brand_field.lower():
        return brand_field
    
    # Try to extract from product name
    name = product.get('name', '')
    # Common brand patterns at start of name
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


def parse_nutrition_value(value: str) -> Optional[float]:
    """Parse nutrition percentage from string like '10.2 %'"""
    if not value:
        return None
    
    # Remove % and whitespace
    value = value.replace('%', '').strip()
    
    # Handle comma as decimal separator
    value = value.replace(',', '.')
    
    try:
        return float(value)
    except ValueError:
        return None


def extract_pack_sizes(name: str) -> List[str]:
    """Extract pack sizes from product name"""
    sizes = []
    
    # Pattern: 6 x 400g, 24 x 800g, 2.5kg, etc.
    patterns = [
        r'(\d+)\s*x\s*(\d+(?:\.\d+)?)\s*(kg|g|ml|l)',  # 6 x 400g
        r'(\d+(?:\.\d+)?)\s*(kg|g|ml|l)(?:\s|$)',      # 2.5kg
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, name, re.IGNORECASE)
        for match in matches:
            if len(match) == 3:  # Multi-pack
                sizes.append(f"{match[0]} x {match[1]}{match[2]}")
            elif len(match) == 2:  # Single pack
                sizes.append(f"{match[0]}{match[1]}")
    
    return sizes


def determine_form(product: Dict) -> str:
    """Determine product form (dry, wet, raw, etc.)"""
    category = product.get('category', '').lower()
    name = product.get('name', '').lower()
    
    if 'dry' in category or 'kibble' in name:
        return 'dry'
    elif 'wet' in category or 'canned' in category or 'can' in name or 'pouch' in name:
        return 'wet'
    elif 'raw' in category or 'raw' in name:
        return 'raw'
    else:
        # Default based on moisture content if available
        moisture = product.get('attributes', {}).get('moisture')
        if moisture:
            moisture_val = parse_nutrition_value(moisture)
            if moisture_val:
                if moisture_val > 60:
                    return 'wet'
                elif moisture_val < 20:
                    return 'dry'
    
    return 'dry'  # Default to dry


def transform_product(product: Dict) -> Optional[Dict]:
    """Transform Zooplus product to database format"""
    # Extract brand
    brand = extract_brand(product)
    if not brand:
        return None
    
    # Get nutrition data
    attributes = product.get('attributes', {})
    
    # Build database record
    record = {
        # Basic info
        'brand': brand,
        'product_name': product.get('name', ''),
        'form': determine_form(product),
        
        # Nutrition
        'protein_percent': parse_nutrition_value(attributes.get('protein')),
        'fat_percent': parse_nutrition_value(attributes.get('fat')),
        'fiber_percent': parse_nutrition_value(attributes.get('fibre')),
        'ash_percent': parse_nutrition_value(attributes.get('ash')),
        'moisture_percent': parse_nutrition_value(attributes.get('moisture')),
        
        # Ingredients (description contains ingredient info)
        'ingredients_raw': product.get('description', ''),
        
        # Package info
        'pack_sizes': extract_pack_sizes(product.get('name', '')),
        'gtin': product.get('gtin'),
        
        # Retailer info
        'retailer_source': 'zooplus',
        'retailer_url': product.get('url', ''),
        'retailer_product_id': product.get('sku', ''),
        'retailer_sku': product.get('sku', ''),
        'retailer_price_eur': product.get('price'),
        'retailer_original_price_eur': product.get('regular_price') if product.get('regular_price', 0) > 0 else None,
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
        'data_complete': False  # Will update after checking
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
    """Main entry point - fast batch import"""
    json_file = 'docs/dataset_zooplus-scraper_2025-09-08_15-48-47-523.json'
    
    if not os.path.exists(json_file):
        logger.error(f"File not found: {json_file}")
        sys.exit(1)
    
    logger.info(f"Loading data from {json_file}")
    with open(json_file, 'r', encoding='utf-8') as f:
        products = json.load(f)
    
    logger.info(f"Loaded {len(products)} products")
    
    # Transform all products
    logger.info("Transforming products...")
    records = []
    skipped = 0
    brands = set()
    with_nutrition = 0
    
    for product in products:
        record = transform_product(product)
        if record:
            records.append(record)
            brands.add(record['brand'])
            if any([record['protein_percent'], record['fat_percent'], record['fiber_percent']]):
                with_nutrition += 1
        else:
            skipped += 1
    
    logger.info(f"Transformed {len(records)} products, skipped {skipped}")
    logger.info(f"Products with nutrition: {with_nutrition}")
    logger.info(f"Unique brands: {len(brands)}")
    
    # Connect to Supabase
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Insert in batches using upsert
    batch_size = 50
    total_inserted = 0
    total_errors = 0
    
    logger.info("Starting batch import...")
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(records) + batch_size - 1) // batch_size
        
        try:
            # Use upsert to handle duplicates
            response = supabase.table('food_candidates_sc').upsert(
                batch,
                on_conflict='brand,product_name,retailer_source'
            ).execute()
            
            total_inserted += len(batch)
            logger.info(f"Batch {batch_num}/{total_batches}: Imported {len(batch)} products")
            
        except Exception as e:
            error_msg = str(e)
            if 'duplicate' in error_msg.lower():
                # Try individual inserts for this batch
                logger.warning(f"Batch {batch_num} has duplicates, trying individual inserts...")
                for record in batch:
                    try:
                        supabase.table('food_candidates_sc').upsert(
                            record,
                            on_conflict='brand,product_name,retailer_source'
                        ).execute()
                        total_inserted += 1
                    except Exception as e2:
                        total_errors += 1
                        logger.debug(f"Failed: {record['brand']} - {record['product_name'][:30]}")
            else:
                logger.error(f"Batch {batch_num} error: {error_msg[:200]}")
                total_errors += len(batch)
    
    # Print summary
    print("\n" + "="*60)
    print("IMPORT SUMMARY")
    print("="*60)
    print(f"Total products in file: {len(products)}")
    print(f"Successfully imported/updated: {total_inserted}")
    print(f"Failed: {total_errors}")
    print(f"Skipped (no brand): {skipped}")
    print(f"Products with nutrition: {with_nutrition}")
    print(f"Unique brands: {len(brands)}")
    
    if brands:
        print(f"\nTop brands imported:")
        brand_list = sorted(brands)[:20]
        for brand in brand_list:
            print(f"  - {brand}")
    
    success_rate = (total_inserted / len(products) * 100) if len(products) > 0 else 0
    print(f"\nSuccess rate: {success_rate:.1f}%")
    print("="*60)


if __name__ == "__main__":
    main()