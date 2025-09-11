#!/usr/bin/env python3
"""
Parse GCS snapshots for burns and barking brands
Extract ingredients and macros to foods_canonical
"""

import os
import re
import json
import yaml
from datetime import datetime, timezone
from pathlib import Path
from google.cloud import storage
from bs4 import BeautifulSoup
from supabase import create_client
from dotenv import load_dotenv
import logging
from typing import Dict, List, Optional, Tuple
import langdetect

# Setup
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize clients
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = './secrets/gcp-sa.json'
storage_client = storage.Client()
bucket = storage_client.bucket('lupito-content-raw-eu')

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(url, key)

# Load canonical map
canonical_map_file = Path("data/ingredients_canonical_map.yaml")
if canonical_map_file.exists():
    with open(canonical_map_file, 'r') as f:
        canonical_data = yaml.safe_load(f)
        CANONICAL_MAP = canonical_data.get('canonical_map', {})
        ALLERGEN_GROUPS = canonical_data.get('allergen_groups', {})
else:
    CANONICAL_MAP = {}
    ALLERGEN_GROUPS = {}

# Statistics tracking
stats = {
    'burns': {
        'total_products': 0,
        'ingredients_extracted': 0,
        'macros_extracted': 0,
        'kcal_extracted': 0,
        'fields_improved': {},
        'failures': []
    },
    'barking': {
        'total_products': 0,
        'ingredients_extracted': 0,
        'macros_extracted': 0,
        'kcal_extracted': 0,
        'fields_improved': {},
        'failures': []
    }
}

def detect_language(text: str) -> str:
    """Detect language of text"""
    try:
        lang = langdetect.detect(text)
        return lang
    except:
        return 'en'

def tokenize_ingredients(raw_text: str) -> List[str]:
    """Tokenize ingredients using canonical map"""
    if not raw_text:
        return []
    
    text = raw_text.lower()
    # Remove percentages and numbers
    text = re.sub(r'\([^)]*\d+[^)]*\)', '', text)
    text = re.sub(r'\d+\.?\d*\s*%', '', text)
    
    # Split on commas and common separators
    parts = re.split(r'[,;]|\sand\s|\s&\s', text)
    
    tokens = []
    for part in parts:
        # Clean the part
        part = re.sub(r'[^a-z\s-]', ' ', part)
        part = ' '.join(part.split()).strip()
        
        if part and len(part) > 1:
            # Apply canonical mapping
            canonical = CANONICAL_MAP.get(part, part)
            if canonical and canonical not in tokens:
                tokens.append(canonical)
    
    return tokens

def extract_ingredients_from_html(html: str, brand: str) -> Optional[Dict]:
    """Extract ingredients from HTML"""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Try multiple selectors
    selectors = [
        # Common patterns
        ('div.ingredients', 'text'),
        ('div.composition', 'text'),
        ('div.product-ingredients', 'text'),
        ('div#ingredients', 'text'),
        ('[itemprop="ingredients"]', 'text'),
        
        # Label patterns
        ('dt:contains("Ingredients")', 'next_dd'),
        ('dt:contains("Composition")', 'next_dd'),
        ('h3:contains("Ingredients")', 'next_p'),
        ('h4:contains("Composition")', 'next_p'),
        
        # Table patterns
        ('td:contains("Ingredients")', 'next_td'),
        ('th:contains("Composition")', 'next_td'),
    ]
    
    ingredients_text = None
    
    for selector, method in selectors:
        try:
            if ':contains(' in selector:
                # Use regex for contains selector
                pattern = selector.split(':contains("')[1].split('")')[0]
                elements = soup.find_all(text=re.compile(pattern, re.I))
                for elem in elements:
                    parent = elem.parent
                    if method == 'next_dd':
                        sibling = parent.find_next_sibling('dd')
                        if sibling:
                            ingredients_text = sibling.get_text(strip=True)
                            break
                    elif method == 'next_p':
                        sibling = parent.find_next_sibling('p')
                        if sibling:
                            ingredients_text = sibling.get_text(strip=True)
                            break
                    elif method == 'next_td':
                        sibling = parent.find_next_sibling('td')
                        if sibling:
                            ingredients_text = sibling.get_text(strip=True)
                            break
            else:
                elements = soup.select(selector)
                if elements:
                    ingredients_text = elements[0].get_text(strip=True)
                    break
        except:
            continue
    
    # Fallback: search for text patterns
    if not ingredients_text:
        text = soup.get_text()
        patterns = [
            r'Ingredients?:?\s*([^\.]{20,500})',
            r'Composition:?\s*([^\.]{20,500})',
            r'Contains:?\s*([^\.]{20,500})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                ingredients_text = match.group(1).strip()
                break
    
    if ingredients_text and len(ingredients_text) > 10:
        # Clean up
        ingredients_text = re.sub(r'\s+', ' ', ingredients_text)
        ingredients_text = ingredients_text.replace('\n', ' ').replace('\r', ' ')
        
        # Detect language
        lang = detect_language(ingredients_text)
        
        # Tokenize
        tokens = tokenize_ingredients(ingredients_text)
        
        if tokens:
            return {
                'ingredients_raw': ingredients_text[:2000],  # Limit length
                'ingredients_tokens': tokens,
                'ingredients_language': lang,
                'ingredients_parsed_at': datetime.now(timezone.utc).isoformat(),
                'ingredients_source': 'manufacturer_site'
            }
    
    return None

def extract_macros_from_html(html: str) -> Optional[Dict]:
    """Extract macronutrients from HTML"""
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text()
    
    macros = {}
    
    # Patterns for each macro
    patterns = {
        'protein_percent': [
            r'(?:Crude\s+)?Protein[:\s]+([0-9]+\.?[0-9]*)\s*%',
            r'Protein[:\s]+min\.?\s*([0-9]+\.?[0-9]*)\s*%',
            r'Analytical constituents.*?Protein[:\s]+([0-9]+\.?[0-9]*)\s*%',
        ],
        'fat_percent': [
            r'(?:Crude\s+)?Fat[:\s]+([0-9]+\.?[0-9]*)\s*%',
            r'Fat\s+content[:\s]+([0-9]+\.?[0-9]*)\s*%',
            r'Oils?\s+(?:and\s+)?fats?[:\s]+([0-9]+\.?[0-9]*)\s*%',
        ],
        'fiber_percent': [
            r'(?:Crude\s+)?Fib(?:re|er)[:\s]+([0-9]+\.?[0-9]*)\s*%',
            r'Dietary\s+fib(?:re|er)[:\s]+([0-9]+\.?[0-9]*)\s*%',
        ],
        'ash_percent': [
            r'(?:Crude\s+)?Ash[:\s]+([0-9]+\.?[0-9]*)\s*%',
            r'Inorganic\s+matter[:\s]+([0-9]+\.?[0-9]*)\s*%',
        ],
        'moisture_percent': [
            r'Moisture[:\s]+([0-9]+\.?[0-9]*)\s*%',
            r'Water[:\s]+([0-9]+\.?[0-9]*)\s*%',
        ]
    }
    
    for macro, pattern_list in patterns.items():
        for pattern in pattern_list:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                try:
                    value = float(match.group(1))
                    if 0 < value < 100:  # Sanity check
                        macros[macro] = value
                        break
                except:
                    pass
    
    # Extract kcal
    kcal_patterns = [
        r'([0-9]+\.?[0-9]*)\s*kcal/100\s*g',
        r'([0-9]+\.?[0-9]*)\s*kcal\s+per\s+100\s*g',
        r'Energy[:\s]+([0-9]+\.?[0-9]*)\s*kcal/100\s*g',
        r'Metaboli[sz]able\s+energy[:\s]+([0-9]+\.?[0-9]*)\s*kcal/100\s*g',
    ]
    
    kcal = None
    for pattern in kcal_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                kcal = float(match.group(1))
                if 100 < kcal < 800:  # Sanity check for dog food
                    macros['kcal_per_100g'] = kcal
                    macros['kcal_source'] = 'site_text'
                    break
            except:
                pass
    
    # If no kcal but have macros, derive it
    if not kcal and 'protein_percent' in macros and 'fat_percent' in macros:
        # Modified Atwater factors for pet food
        protein_kcal = macros['protein_percent'] * 3.5
        fat_kcal = macros['fat_percent'] * 8.5
        # Estimate carbs (100 - protein - fat - fiber - ash - moisture)
        carbs = 100
        for m in ['protein_percent', 'fat_percent', 'fiber_percent', 'ash_percent', 'moisture_percent']:
            if m in macros:
                carbs -= macros[m]
        carbs = max(0, carbs)
        carbs_kcal = carbs * 3.5
        
        derived_kcal = protein_kcal + fat_kcal + carbs_kcal
        if 100 < derived_kcal < 800:
            macros['kcal_per_100g'] = round(derived_kcal, 1)
            macros['kcal_source'] = 'derived'
    
    if macros:
        macros['macros_source'] = 'site_text'
        return macros
    
    return None

def get_product_from_url(url: str, brand: str) -> Optional[Dict]:
    """Get product info from Supabase based on URL pattern"""
    # Extract product slug from URL
    slug_match = re.search(r'/products?/([^/]+?)(?:\.html)?$', url)
    if not slug_match:
        return None
    
    slug = slug_match.group(1)
    
    # Try to find product in foods_canonical
    # First try exact match on product name
    response = supabase.table('foods_canonical').select(
        'product_key, product_name, brand_slug, ingredients_raw, ingredients_tokens, '
        'protein_percent, fat_percent, fiber_percent, ash_percent, moisture_percent, kcal_per_100g'
    ).eq('brand_slug', brand).execute()
    
    if response.data:
        # Try to match by slug in product name
        slug_parts = slug.replace('-', ' ').lower()
        for product in response.data:
            product_name = product.get('product_name', '').lower()
            if slug_parts in product_name or all(part in product_name for part in slug_parts.split()[:3]):
                return product
    
    return None

def process_brand_snapshots(brand: str) -> Dict:
    """Process all snapshots for a brand"""
    logger.info(f"Processing {brand} snapshots...")
    
    # Get latest date folder
    prefix = f"manufacturers/{brand}/"
    
    # List all prefixes (folders) under the brand
    iterator = bucket.list_blobs(prefix=prefix, delimiter='/')
    blobs = list(iterator)  # Consume the iterator to get blobs
    prefixes = list(iterator.prefixes)  # Get the prefixes (folders)
    
    # Find date folders
    dates = []
    for prefix_path in prefixes:
        # Extract the folder name (last part before /)
        parts = prefix_path.rstrip('/').split('/')
        if parts:
            date_part = parts[-1]
            if re.match(r'\d{4}-\d{2}-\d{2}', date_part):
                dates.append(date_part)
                logger.info(f"Found date folder: {date_part}")
    
    if not dates:
        logger.warning(f"No date folders found for {brand}")
        return {}
    
    latest_date = sorted(dates)[-1]
    logger.info(f"Using snapshots from {latest_date}")
    
    # Process each HTML file
    snapshot_prefix = f"manufacturers/{brand}/{latest_date}/"
    updates = []
    
    for blob in bucket.list_blobs(prefix=snapshot_prefix):
        if not blob.name.endswith('.html'):
            continue
        
        # Skip non-product pages
        filename = blob.name.split('/')[-1]
        if filename in ['sitemap.html', 'products.html', 'shop.html', 'dog-food.html', 'dog.html']:
            continue
        
        stats[brand]['total_products'] += 1
        
        try:
            # Download and parse HTML
            html = blob.download_as_text()
            
            # Extract URL from metadata
            metadata = blob.metadata or {}
            url = metadata.get('url', '')
            
            # Try to match with existing product
            product = get_product_from_url(blob.name, brand)
            if not product:
                # Try to extract product name from HTML
                soup = BeautifulSoup(html, 'html.parser')
                title = soup.find('h1') or soup.find('title')
                if title:
                    product_name = title.get_text(strip=True)
                    # Create minimal product record
                    product = {
                        'product_key': f"{brand}_{filename.replace('.html', '')}",
                        'product_name': product_name
                    }
                else:
                    logger.warning(f"Could not identify product for {blob.name}")
                    stats[brand]['failures'].append(f"No product match: {filename}")
                    continue
            
            # Extract ingredients
            update_data = {}
            ingredients_data = extract_ingredients_from_html(html, brand)
            if ingredients_data:
                # Only update if current data is empty or missing
                if not product.get('ingredients_tokens') or len(product.get('ingredients_tokens', [])) == 0:
                    update_data.update(ingredients_data)
                    stats[brand]['ingredients_extracted'] += 1
                    stats[brand]['fields_improved']['ingredients'] = stats[brand]['fields_improved'].get('ingredients', 0) + 1
            
            # Extract macros
            macros_data = extract_macros_from_html(html)
            if macros_data:
                # Only update if current data is missing
                for field, value in macros_data.items():
                    if field != 'macros_source' and field != 'kcal_source':
                        if not product.get(field):
                            update_data[field] = value
                            if 'percent' in field:
                                stats[brand]['macros_extracted'] = stats[brand].get('macros_extracted', 0) + 1
                            elif field == 'kcal_per_100g':
                                stats[brand]['kcal_extracted'] = stats[brand].get('kcal_extracted', 0) + 1
                            stats[brand]['fields_improved'][field] = stats[brand]['fields_improved'].get(field, 0) + 1
                
                # Add source fields
                if 'protein_percent' in update_data or 'fat_percent' in update_data:
                    update_data['macros_source'] = macros_data.get('macros_source', 'site_text')
                if 'kcal_per_100g' in update_data:
                    update_data['kcal_source'] = macros_data.get('kcal_source', 'site_text')
            
            # Apply update if we have data
            if update_data:
                updates.append({
                    'product_key': product['product_key'],
                    'product_name': product.get('product_name', 'Unknown'),
                    'updates': update_data
                })
                
                # Update in Supabase
                try:
                    response = supabase.table('foods_canonical').update(
                        update_data
                    ).eq('product_key', product['product_key']).execute()
                    
                    if response.data:
                        logger.info(f"Updated {product['product_key']}: {list(update_data.keys())}")
                    else:
                        logger.warning(f"No matching product for {product['product_key']}")
                except Exception as e:
                    logger.error(f"Failed to update {product['product_key']}: {e}")
                    stats[brand]['failures'].append(f"Update failed: {product['product_key']}")
            
        except Exception as e:
            logger.error(f"Error processing {blob.name}: {e}")
            stats[brand]['failures'].append(f"Processing error: {filename}")
    
    return updates

def get_coverage_stats(brand: str) -> Dict:
    """Get coverage statistics for a brand"""
    response = supabase.table('foods_canonical').select(
        'product_key, ingredients_tokens, protein_percent, fat_percent, kcal_per_100g'
    ).eq('brand_slug', brand).execute()
    
    if not response.data:
        return {}
    
    total = len(response.data)
    has_ingredients = sum(1 for p in response.data if p.get('ingredients_tokens') and len(p['ingredients_tokens']) > 0)
    has_macros = sum(1 for p in response.data if p.get('protein_percent') and p.get('fat_percent'))
    has_kcal = sum(1 for p in response.data if p.get('kcal_per_100g'))
    
    return {
        'total': total,
        'ingredients_coverage': round(has_ingredients / total * 100, 1) if total > 0 else 0,
        'macros_coverage': round(has_macros / total * 100, 1) if total > 0 else 0,
        'kcal_coverage': round(has_kcal / total * 100, 1) if total > 0 else 0,
        'has_ingredients': has_ingredients,
        'has_macros': has_macros,
        'has_kcal': has_kcal
    }

def main():
    """Main execution"""
    print("="*80)
    print("PARSING GCS SNAPSHOTS")
    print("="*80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Brands: burns, barking")
    print()
    
    # Get before stats
    before_stats = {
        'burns': get_coverage_stats('burns'),
        'barking': get_coverage_stats('barking')
    }
    
    # Process each brand
    all_updates = {}
    for brand in ['burns', 'barking']:
        print(f"\nProcessing {brand}...")
        updates = process_brand_snapshots(brand)
        all_updates[brand] = updates
        print(f"  Processed {stats[brand]['total_products']} products")
        print(f"  Extracted ingredients: {stats[brand]['ingredients_extracted']}")
        print(f"  Extracted macros: {stats[brand]['macros_extracted']}")
        print(f"  Extracted kcal: {stats[brand]['kcal_extracted']}")
    
    # Get after stats
    after_stats = {
        'burns': get_coverage_stats('burns'),
        'barking': get_coverage_stats('barking')
    }
    
    # Generate PARSE_REPORT.md
    with open('PARSE_REPORT.md', 'w') as f:
        f.write("# GCS Snapshot Parse Report\n\n")
        f.write(f"**Generated:** {datetime.now().isoformat()}\n")
        f.write(f"**Source:** gs://lupito-content-raw-eu/manufacturers/\n\n")
        
        for brand in ['burns', 'barking']:
            f.write(f"## {brand.upper()}\n\n")
            f.write(f"**Total products parsed:** {stats[brand]['total_products']}\n\n")
            
            f.write("### Fields Improved\n")
            if stats[brand]['fields_improved']:
                for field, count in sorted(stats[brand]['fields_improved'].items()):
                    f.write(f"- {field}: {count}\n")
            else:
                f.write("- No improvements\n")
            
            f.write("\n### Coverage Deltas\n")
            before = before_stats.get(brand, {})
            after = after_stats.get(brand, {})
            
            f.write(f"- Ingredients: {before.get('ingredients_coverage', 0)}% → {after.get('ingredients_coverage', 0)}%")
            f.write(f" ({after.get('has_ingredients', 0) - before.get('has_ingredients', 0):+d})\n")
            
            f.write(f"- Macros: {before.get('macros_coverage', 0)}% → {after.get('macros_coverage', 0)}%")
            f.write(f" ({after.get('has_macros', 0) - before.get('has_macros', 0):+d})\n")
            
            f.write(f"- Kcal: {before.get('kcal_coverage', 0)}% → {after.get('kcal_coverage', 0)}%")
            f.write(f" ({after.get('has_kcal', 0) - before.get('has_kcal', 0):+d})\n")
            
            if stats[brand]['failures']:
                f.write("\n### Top Parsing Failures\n")
                failure_counts = {}
                for failure in stats[brand]['failures'][:10]:
                    reason = failure.split(':')[0]
                    failure_counts[reason] = failure_counts.get(reason, 0) + 1
                
                for reason, count in sorted(failure_counts.items(), key=lambda x: x[1], reverse=True):
                    f.write(f"- {reason}: {count}\n")
            
            f.write("\n")
    
    # Generate INGREDIENTS_MACROS_AFTER.md
    with open('INGREDIENTS_MACROS_AFTER.md', 'w') as f:
        f.write("# Ingredients & Macros Coverage After Parsing\n\n")
        f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
        
        for brand in ['burns', 'barking']:
            f.write(f"## {brand.upper()}\n\n")
            
            after = after_stats.get(brand, {})
            f.write(f"**Total Products:** {after.get('total', 0)}\n")
            f.write(f"**Ingredients Coverage:** {after.get('has_ingredients', 0)}/{after.get('total', 0)} ")
            f.write(f"({after.get('ingredients_coverage', 0)}%)\n")
            f.write(f"**Macros Coverage:** {after.get('has_macros', 0)}/{after.get('total', 0)} ")
            f.write(f"({after.get('macros_coverage', 0)}%)\n")
            f.write(f"**Kcal Coverage:** {after.get('has_kcal', 0)}/{after.get('total', 0)} ")
            f.write(f"({after.get('kcal_coverage', 0)}%)\n\n")
            
            # Show example rows
            response = supabase.table('foods_canonical').select(
                'product_name, ingredients_tokens, protein_percent, fat_percent, kcal_per_100g'
            ).eq('brand_slug', brand).limit(3).execute()
            
            if response.data:
                f.write("### Example Rows\n\n")
                for i, row in enumerate(response.data, 1):
                    f.write(f"**Product {i}:** {row['product_name']}\n")
                    if row.get('ingredients_tokens'):
                        f.write(f"- Tokens: {', '.join(row['ingredients_tokens'][:5])}...")
                        if len(row['ingredients_tokens']) > 5:
                            f.write(f" ({len(row['ingredients_tokens'])} total)")
                        f.write("\n")
                    if row.get('protein_percent'):
                        f.write(f"- Protein: {row['protein_percent']}%\n")
                    if row.get('fat_percent'):
                        f.write(f"- Fat: {row['fat_percent']}%\n")
                    if row.get('kcal_per_100g'):
                        f.write(f"- Kcal/100g: {row['kcal_per_100g']}\n")
                    f.write("\n")
            
            f.write("\n")
    
    print("\n" + "="*80)
    print("PARSING COMPLETE")
    print("="*80)
    print("Reports generated:")
    print("  - PARSE_REPORT.md")
    print("  - INGREDIENTS_MACROS_AFTER.md")
    
    # Summary
    total_ingredients = sum(s['ingredients_extracted'] for s in stats.values())
    total_macros = sum(s['macros_extracted'] for s in stats.values())
    total_kcal = sum(s['kcal_extracted'] for s in stats.values())
    
    print(f"\nTotal extractions:")
    print(f"  - Ingredients: {total_ingredients}")
    print(f"  - Macros: {total_macros}")
    print(f"  - Kcal: {total_kcal}")

if __name__ == "__main__":
    main()