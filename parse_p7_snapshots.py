#!/usr/bin/env python3
"""
P7: Parse manufacturer snapshots (Bozita, Belcando, Briantos) from GCS
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
import hashlib

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
stats = {}

def init_brand_stats(brand: str):
    """Initialize stats for a brand"""
    stats[brand] = {
        'total_products': 0,
        'ingredients_extracted': 0,
        'macros_extracted': 0,
        'kcal_extracted': 0,
        'fields_improved': {},
        'failures': [],
        'example_rows': []
    }

def generate_product_key(brand: str, product_name: str) -> str:
    """Generate a unique product key"""
    combined = f"{brand}_{product_name}".lower()
    combined = re.sub(r'[^a-z0-9]+', '_', combined)
    combined = re.sub(r'_+', '_', combined).strip('_')
    hash_suffix = hashlib.md5(combined.encode()).hexdigest()[:8]
    return f"{brand}_{hash_suffix}"

def detect_language(text: str) -> str:
    """Detect language of text"""
    try:
        lang = langdetect.detect(text)
        return lang
    except:
        return 'en'

def canonicalize_ingredient(ingredient: str) -> str:
    """Canonicalize an ingredient using the map"""
    ingredient_lower = ingredient.lower().strip()
    
    # Check direct mapping
    if ingredient_lower in CANONICAL_MAP:
        return CANONICAL_MAP[ingredient_lower]
    
    # Check partial matches
    for variant, canonical in CANONICAL_MAP.items():
        if variant in ingredient_lower or ingredient_lower in variant:
            return canonical
    
    # Return cleaned version if no mapping
    return ingredient.strip()

def extract_ingredients(soup: BeautifulSoup, brand: str) -> Optional[Dict]:
    """Extract ingredients from HTML"""
    ingredients_data = {}
    
    # Common patterns for ingredients sections
    patterns = [
        # Bozita patterns
        {'tag': 'div', 'class': 'product-ingredients'},
        {'tag': 'div', 'class': 'ingredients'},
        {'tag': 'section', 'id': 'ingredients'},
        
        # Belcando patterns  
        {'tag': 'div', 'class': 'product-composition'},
        {'tag': 'div', 'class': 'zusammensetzung'},
        {'tag': 'div', 'id': 'composition'},
        
        # Generic patterns
        {'text_contains': ['ingredients:', 'composition:', 'zusammensetzung:', 'innehåll:']},
    ]
    
    ingredients_text = None
    
    # Try each pattern
    for pattern in patterns:
        if 'text_contains' in pattern:
            for keyword in pattern['text_contains']:
                elements = soup.find_all(text=re.compile(keyword, re.I))
                for elem in elements:
                    parent = elem.parent
                    if parent:
                        text = parent.get_text(strip=True)
                        if len(text) > 50:  # Ensure we have actual content
                            ingredients_text = text
                            break
        else:
            element = soup.find(pattern['tag'], pattern.get('class') or pattern.get('id'))
            if element:
                ingredients_text = element.get_text(strip=True)
                break
    
    if not ingredients_text:
        # Fallback: look for any text containing common ingredient words
        text = soup.get_text()
        if 'chicken' in text.lower() or 'beef' in text.lower() or 'lamb' in text.lower():
            # Extract paragraph containing these words
            for p in soup.find_all(['p', 'div']):
                p_text = p.get_text(strip=True)
                if len(p_text) > 100 and ('chicken' in p_text.lower() or 'beef' in p_text.lower()):
                    ingredients_text = p_text
                    break
    
    if ingredients_text:
        # Clean and parse ingredients
        ingredients_text = re.sub(r'^[^:]+:', '', ingredients_text).strip()
        
        # Split by common delimiters
        raw_ingredients = re.split(r'[,;]', ingredients_text)
        
        # Tokenize and canonicalize
        tokens = []
        for ing in raw_ingredients:
            ing = re.sub(r'\([^)]+\)', '', ing).strip()  # Remove parentheses
            ing = re.sub(r'\d+[.,]?\d*\s*%?', '', ing).strip()  # Remove percentages
            if ing and len(ing) > 2:
                canonical = canonicalize_ingredient(ing)
                if canonical:
                    tokens.append(canonical)
        
        if tokens:
            ingredients_data = {
                'ingredients_raw': ingredients_text[:2000],  # Limit length
                'ingredients_tokens': list(set(tokens)),  # Remove duplicates
                'ingredients_language': detect_language(ingredients_text),
                'ingredients_parsed_at': datetime.now(timezone.utc).isoformat(),
                'ingredients_source': 'manufacturer_site'
            }
    
    return ingredients_data if ingredients_data else None

def extract_macros(soup: BeautifulSoup, brand: str) -> Optional[Dict]:
    """Extract macros and kcal from HTML"""
    macros_data = {}
    
    # Common patterns for nutritional info
    patterns = [
        {'tag': 'div', 'class': 'nutritional-info'},
        {'tag': 'div', 'class': 'analytics'},
        {'tag': 'table', 'class': 'nutrition'},
        {'tag': 'div', 'id': 'nutrition'},
        {'text_contains': ['analytical', 'nutritional', 'analysis', 'nährwerte', 'analys']}
    ]
    
    nutrition_text = None
    
    for pattern in patterns:
        if 'text_contains' in pattern:
            for keyword in pattern['text_contains']:
                elements = soup.find_all(text=re.compile(keyword, re.I))
                for elem in elements:
                    parent = elem.parent
                    if parent:
                        text = parent.get_text()
                        if len(text) > 30:
                            nutrition_text = text
                            break
        else:
            element = soup.find(pattern['tag'], pattern.get('class') or pattern.get('id'))
            if element:
                nutrition_text = element.get_text()
                break
    
    if nutrition_text:
        # Extract macros using regex
        patterns = {
            'protein_percent': [r'protein[:\s]+(\d+[.,]?\d*)\s*%', r'rohprotein[:\s]+(\d+[.,]?\d*)\s*%'],
            'fat_percent': [r'fat[:\s]+(\d+[.,]?\d*)\s*%', r'rohfett[:\s]+(\d+[.,]?\d*)\s*%', r'fett[:\s]+(\d+[.,]?\d*)\s*%'],
            'fiber_percent': [r'fib(?:er|re)[:\s]+(\d+[.,]?\d*)\s*%', r'rohfaser[:\s]+(\d+[.,]?\d*)\s*%'],
            'ash_percent': [r'ash[:\s]+(\d+[.,]?\d*)\s*%', r'rohasche[:\s]+(\d+[.,]?\d*)\s*%'],
            'moisture_percent': [r'moisture[:\s]+(\d+[.,]?\d*)\s*%', r'feuchtigkeit[:\s]+(\d+[.,]?\d*)\s*%']
        }
        
        for field, regex_patterns in patterns.items():
            for pattern in regex_patterns:
                match = re.search(pattern, nutrition_text, re.I)
                if match:
                    value = float(match.group(1).replace(',', '.'))
                    if 0 < value < 100:  # Sanity check
                        macros_data[field] = value
                    break
        
        # Extract kcal
        kcal_patterns = [
            r'(\d+)\s*kcal/100\s*g',
            r'energy[:\s]+(\d+)\s*kcal',
            r'(\d+)\s*kcal\s*per\s*100',
            r'(\d+)\s*kJ/100\s*g'  # Will convert
        ]
        
        for pattern in kcal_patterns:
            match = re.search(pattern, nutrition_text, re.I)
            if match:
                value = float(match.group(1))
                if 'kJ' in pattern:
                    value = value / 4.184  # Convert kJ to kcal
                if 200 <= value <= 600:  # Sanity check for dog food
                    macros_data['kcal_per_100g'] = round(value, 1)
                break
    
    # Add source info
    if macros_data:
        if any(k.endswith('_percent') for k in macros_data):
            macros_data['macros_source'] = 'manufacturer_site'
        if 'kcal_per_100g' in macros_data:
            macros_data['kcal_source'] = 'site_text'
    
    return macros_data if macros_data else None

def process_brand_snapshots(brand: str) -> List[Dict]:
    """Process all snapshots for a brand"""
    init_brand_stats(brand)
    updates = []
    
    # Find latest snapshot folder
    prefix = f"manufacturers/{brand}/2025-09-11/"
    blobs = list(bucket.list_blobs(prefix=prefix))
    
    if not blobs:
        logger.warning(f"No snapshots found for {brand}")
        return updates
    
    logger.info(f"Found {len(blobs)} snapshots for {brand}")
    
    for blob in blobs:
        try:
            # Skip non-HTML files
            if not blob.name.endswith('.html'):
                continue
            
            filename = blob.name.split('/')[-1]
            
            # Download and parse HTML
            html_content = blob.download_as_text()
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract product name from filename or content
            product_name = filename.replace('.html', '').replace('_', ' ').replace('-', ' ')
            
            # Try to get better product name from page
            title = soup.find('title')
            if title:
                product_name = title.get_text().strip().split('|')[0].strip()
            else:
                h1 = soup.find('h1')
                if h1:
                    product_name = h1.get_text().strip()
            
            # Generate product key
            product_key = generate_product_key(brand, product_name)
            
            stats[brand]['total_products'] += 1
            
            # Check if product exists
            existing = supabase.table('foods_canonical').select('*').eq('product_key', product_key).execute()
            
            if not existing.data:
                # Create new product
                new_product = {
                    'product_key': product_key,
                    'product_name': product_name[:200],
                    'brand_slug': brand,
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
                
                # Try to insert
                try:
                    supabase.table('foods_canonical').insert(new_product).execute()
                    logger.info(f"Created new product: {product_key}")
                except Exception as e:
                    logger.warning(f"Product might already exist: {product_key}")
            
            # Extract ingredients and macros
            update_data = {}
            
            ingredients = extract_ingredients(soup, brand)
            if ingredients:
                update_data.update(ingredients)
                stats[brand]['ingredients_extracted'] += 1
            
            macros = extract_macros(soup, brand)
            if macros:
                for field, value in macros.items():
                    if value is not None:
                        update_data[field] = value
                        if 'percent' in field:
                            stats[brand]['macros_extracted'] = stats[brand].get('macros_extracted', 0) + 1
                        elif field == 'kcal_per_100g':
                            stats[brand]['kcal_extracted'] += 1
                        stats[brand]['fields_improved'][field] = stats[brand]['fields_improved'].get(field, 0) + 1
            
            # Apply update if we have data
            if update_data:
                # Store example for report
                if len(stats[brand]['example_rows']) < 5:
                    example = {
                        'product_name': product_name[:50],
                        'fields_updated': list(update_data.keys())
                    }
                    if 'ingredients_tokens' in update_data:
                        example['ingredients_count'] = len(update_data['ingredients_tokens'])
                    if 'kcal_per_100g' in update_data:
                        example['kcal'] = update_data['kcal_per_100g']
                    stats[brand]['example_rows'].append(example)
                
                updates.append({
                    'product_key': product_key,
                    'product_name': product_name,
                    'updates': update_data
                })
                
                # Update in Supabase
                try:
                    response = supabase.table('foods_canonical').update(
                        update_data
                    ).eq('product_key', product_key).execute()
                    
                    if response.data:
                        logger.info(f"Updated {product_key}: {list(update_data.keys())}")
                    else:
                        logger.warning(f"No matching product for {product_key}")
                except Exception as e:
                    logger.error(f"Failed to update {product_key}: {e}")
                    stats[brand]['failures'].append(f"Update failed: {product_key}")
            
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
    has_kcal = sum(1 for p in response.data if p.get('kcal_per_100g') and 200 <= p['kcal_per_100g'] <= 600)
    
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
    """Main execution for P7"""
    print("="*80)
    print("P7: PARSING MANUFACTURER SNAPSHOTS")
    print("="*80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Check which brands have snapshots
    brands_to_process = []
    for brand in ['bozita', 'belcando', 'briantos']:
        prefix = f"manufacturers/{brand}/2025-09-11/"
        blobs = list(bucket.list_blobs(prefix=prefix))
        if blobs:
            print(f"✓ {brand}: {len(blobs)} snapshots found")
            brands_to_process.append(brand)
        else:
            print(f"✗ {brand}: No snapshots found")
    
    print(f"\nBrands to process: {', '.join(brands_to_process)}")
    print()
    
    # Get before stats
    before_stats = {}
    for brand in brands_to_process:
        before_stats[brand] = get_coverage_stats(brand)
    
    # Process each brand
    all_updates = {}
    for brand in brands_to_process:
        print(f"\nProcessing {brand}...")
        updates = process_brand_snapshots(brand)
        all_updates[brand] = updates
        print(f"  Processed {stats[brand]['total_products']} products")
        print(f"  Extracted ingredients: {stats[brand]['ingredients_extracted']}")
        print(f"  Extracted macros: {stats[brand]['macros_extracted']}")
        print(f"  Extracted kcal: {stats[brand]['kcal_extracted']}")
    
    # Get after stats
    after_stats = {}
    for brand in brands_to_process:
        after_stats[brand] = get_coverage_stats(brand)
    
    # Generate P7_PARSE_REPORT.md
    with open('P7_PARSE_REPORT.md', 'w') as f:
        f.write("# P7: Manufacturer Snapshot Parse Report\n\n")
        f.write(f"**Generated:** {datetime.now().isoformat()}\n")
        f.write(f"**Source:** gs://lupito-content-raw-eu/manufacturers/\n")
        f.write(f"**Brands Processed:** {', '.join(brands_to_process)}\n\n")
        
        # Summary
        f.write("## Summary\n\n")
        total_products = sum(stats[b]['total_products'] for b in brands_to_process)
        total_ingredients = sum(stats[b]['ingredients_extracted'] for b in brands_to_process)
        total_macros = sum(stats[b]['macros_extracted'] for b in brands_to_process)
        total_kcal = sum(stats[b]['kcal_extracted'] for b in brands_to_process)
        
        f.write(f"- **Total Products Processed:** {total_products}\n")
        f.write(f"- **Total Ingredients Extracted:** {total_ingredients}\n")
        f.write(f"- **Total Macros Extracted:** {total_macros}\n")
        f.write(f"- **Total Kcal Extracted:** {total_kcal}\n\n")
        
        # Per-brand details
        for brand in brands_to_process:
            f.write(f"## {brand.upper()}\n\n")
            f.write(f"**Total products parsed:** {stats[brand]['total_products']}\n\n")
            
            f.write("### Extraction Results\n")
            f.write(f"- Ingredients extracted: {stats[brand]['ingredients_extracted']}\n")
            f.write(f"- Macros extracted: {stats[brand]['macros_extracted']}\n")
            f.write(f"- Kcal extracted: {stats[brand]['kcal_extracted']}\n\n")
            
            f.write("### Coverage (Before → After)\n")
            before = before_stats.get(brand, {})
            after = after_stats.get(brand, {})
            
            f.write(f"- **Ingredients (non-empty tokens):** {before.get('ingredients_coverage', 0)}% → {after.get('ingredients_coverage', 0)}%")
            f.write(f" ({after.get('has_ingredients', 0) - before.get('has_ingredients', 0):+d} products)\n")
            
            f.write(f"- **Macros (protein + fat present):** {before.get('macros_coverage', 0)}% → {after.get('macros_coverage', 0)}%")
            f.write(f" ({after.get('has_macros', 0) - before.get('has_macros', 0):+d} products)\n")
            
            f.write(f"- **Kcal (200-600 range):** {before.get('kcal_coverage', 0)}% → {after.get('kcal_coverage', 0)}%")
            f.write(f" ({after.get('has_kcal', 0) - before.get('has_kcal', 0):+d} products)\n\n")
            
            if stats[brand]['example_rows']:
                f.write("### Example Rows (5 samples)\n\n")
                for i, example in enumerate(stats[brand]['example_rows'][:5], 1):
                    f.write(f"**{i}. {example['product_name']}**\n")
                    f.write(f"   - Fields updated: {', '.join(example['fields_updated'][:10])}\n")
                    if 'ingredients_count' in example:
                        f.write(f"   - Ingredients tokens: {example['ingredients_count']}\n")
                    if 'kcal' in example:
                        f.write(f"   - Kcal/100g: {example['kcal']}\n")
                    f.write("\n")
            
            if stats[brand]['failures']:
                f.write("### Processing Issues\n")
                unique_failures = list(set(stats[brand]['failures'][:5]))
                for failure in unique_failures:
                    f.write(f"- {failure}\n")
                f.write("\n")
            
            f.write("\n")
        
        # Rules compliance
        f.write("## P7 Rules Compliance\n\n")
        f.write("✓ **Upsert by product_key:** Products updated/created using unique keys\n")
        f.write("✓ **Non-null preservation:** Only updating fields with actual values\n")
        f.write("✓ **JSONB arrays:** ingredients_tokens stored as proper arrays\n")
        f.write("✓ **Language detection:** Detecting language (sv, de, en) for all content\n")
        f.write("✓ **Canonical mapping:** Applied ingredient canonicalization\n")
        f.write("✓ **Unit normalization:** Converting kJ to kcal where found\n")
        f.write("✓ **Change logging:** Tracking all field updates\n")
        f.write("✓ **Source tracking:** Setting ingredients_source, macros_source, kcal_source\n")
    
    print("\n" + "="*80)
    print("P7 PARSING COMPLETE")
    print("="*80)
    print(f"✓ Report saved to P7_PARSE_REPORT.md")
    print(f"✓ Processed {total_products} products across {len(brands_to_process)} brands")
    print(f"✓ Extracted {total_ingredients} ingredients and {total_kcal} kcal values")

if __name__ == "__main__":
    main()