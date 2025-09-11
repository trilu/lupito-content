#!/usr/bin/env python3
"""
B1: Brand-specific HTML/JSON-LD extractor for Bozita, Belcando, Briantos
Enhanced selector-based ingredient extraction using existing GCS snapshots
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

# Brand-specific selector maps with language support
BRAND_SELECTORS = {
    'bozita': {
        'language': 'swedish',
        'keywords': {
            'ingredients': ['sammansättning', 'ingredienser', 'innehåll'],
            'nutrition': ['analytiska beståndsdelar', 'näringsinnehåll', 'energi'],
        },
        'selectors': [
            # JSON-LD structured data
            {'type': 'json_ld', 'key': 'nutrition'},
            {'type': 'json_ld', 'key': 'ingredients'},
            
            # Common ingredient containers
            {'tag': 'div', 'class': 'product-ingredients'},
            {'tag': 'div', 'class': 'ingredients-content'},
            {'tag': 'section', 'class': 'product-nutrition'},
            {'tag': 'div', 'id': 'ingredients'},
            {'tag': 'div', 'id': 'nutrition'},
            {'tag': 'div', 'id': 'composition'},
            
            # Tab content
            {'tag': 'div', 'class': 'tab-pane'},
            {'tag': 'div', 'class': 'tab-content'},
            
            # Generic content containers
            {'tag': 'div', 'class': 'content'},
            {'tag': 'section', 'class': 'content'},
            {'tag': 'div', 'class': 'product-info'},
            {'tag': 'div', 'class': 'product-details'},
            
            # Text-based search
            {'type': 'text_search', 'keywords': ['sammansättning', 'ingredienser']},
        ]
    },
    
    'belcando': {
        'language': 'german',
        'keywords': {
            'ingredients': ['zusammensetzung', 'inhaltsstoffe', 'zutaten'],
            'nutrition': ['analytische bestandteile', 'nährwerte', 'energie'],
        },
        'selectors': [
            # JSON-LD structured data
            {'type': 'json_ld', 'key': 'nutrition'},
            {'type': 'json_ld', 'key': 'ingredients'},
            
            # German-specific containers
            {'tag': 'div', 'class': 'zusammensetzung'},
            {'tag': 'div', 'class': 'inhaltsstoffe'},
            {'tag': 'div', 'class': 'analytische-bestandteile'},
            {'tag': 'section', 'class': 'produkt-details'},
            
            # Common containers
            {'tag': 'div', 'class': 'product-ingredients'},
            {'tag': 'div', 'class': 'ingredients-content'},
            {'tag': 'section', 'class': 'product-nutrition'},
            {'tag': 'div', 'id': 'zusammensetzung'},
            {'tag': 'div', 'id': 'inhaltsstoffe'},
            {'tag': 'div', 'id': 'analytische-bestandteile'},
            
            # Tab content
            {'tag': 'div', 'class': 'tab-pane'},
            {'tag': 'div', 'class': 'tab-content'},
            
            # Generic content containers  
            {'tag': 'div', 'class': 'content'},
            {'tag': 'section', 'class': 'content'},
            {'tag': 'div', 'class': 'product-info'},
            {'tag': 'div', 'class': 'product-details'},
            
            # Text-based search
            {'type': 'text_search', 'keywords': ['zusammensetzung', 'inhaltsstoffe']},
        ]
    },
    
    'briantos': {
        'language': 'english',
        'keywords': {
            'ingredients': ['composition', 'ingredients', 'contents'],
            'nutrition': ['analytical constituents', 'nutritional information', 'energy'],
        },
        'selectors': [
            # JSON-LD structured data
            {'type': 'json_ld', 'key': 'nutrition'},
            {'type': 'json_ld', 'key': 'ingredients'},
            
            # English containers
            {'tag': 'div', 'class': 'composition'},
            {'tag': 'div', 'class': 'ingredients'},
            {'tag': 'div', 'class': 'analytical-constituents'},
            
            # Common containers
            {'tag': 'div', 'class': 'product-ingredients'},
            {'tag': 'div', 'class': 'ingredients-content'},
            {'tag': 'section', 'class': 'product-nutrition'},
            {'tag': 'div', 'id': 'ingredients'},
            {'tag': 'div', 'id': 'composition'},
            {'tag': 'div', 'id': 'nutrition'},
            
            # Tab content
            {'tag': 'div', 'class': 'tab-pane'},
            {'tag': 'div', 'class': 'tab-content'},
            
            # Generic content containers
            {'tag': 'div', 'class': 'content'},
            {'tag': 'section', 'class': 'content'},
            {'tag': 'div', 'class': 'product-info'},
            {'tag': 'div', 'class': 'product-details'},
            
            # Text-based search
            {'type': 'text_search', 'keywords': ['composition', 'ingredients']},
        ]
    }
}

# Statistics tracking
stats = {}

def init_brand_stats(brand: str):
    """Initialize stats for a brand"""
    stats[brand] = {
        'total_products': 0,
        'ingredients_extracted': 0,
        'macros_extracted': 0,
        'kcal_extracted': 0,
        'success_pages': [],
        'failed_pages': [],
        'selectors_used': set()
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
        # Fallback based on brand
        brand_lang_map = {'bozita': 'sv', 'belcando': 'de', 'briantos': 'en'}
        return 'en'  # Default

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

def extract_json_ld_data(soup: BeautifulSoup) -> Dict:
    """Extract structured data from JSON-LD"""
    data = {}
    
    # Find all JSON-LD scripts
    json_scripts = soup.find_all('script', {'type': 'application/ld+json'})
    
    for script in json_scripts:
        try:
            json_data = json.loads(script.string)
            
            # Handle arrays
            if isinstance(json_data, list):
                json_data = json_data[0] if json_data else {}
            
            # Look for nutrition or ingredient data
            if 'nutrition' in json_data:
                data['nutrition'] = json_data['nutrition']
            
            if 'ingredients' in json_data:
                data['ingredients'] = json_data['ingredients']
                
            # Check for product schema
            if json_data.get('@type') == 'Product':
                if 'nutrition' in json_data:
                    data['nutrition'] = json_data['nutrition']
                if 'ingredients' in json_data:
                    data['ingredients'] = json_data['ingredients']
                    
        except (json.JSONDecodeError, KeyError):
            continue
    
    return data

def extract_with_text_search(soup: BeautifulSoup, keywords: List[str]) -> Optional[str]:
    """Search for text containing keywords and return surrounding content"""
    for keyword in keywords:
        # Find elements containing the keyword
        elements = soup.find_all(string=re.compile(keyword, re.I))
        
        for elem in elements:
            if elem.parent:
                # Try to find the content container
                parent = elem.parent
                
                # Look for content in siblings or parent containers
                for level in range(3):  # Check up to 3 levels up
                    if parent:
                        text = parent.get_text(strip=True)
                        
                        # Check if we found substantial content
                        if len(text) > 100 and keyword.lower() in text.lower():
                            return text
                        
                        parent = parent.parent
    
    return None

def extract_ingredients_enhanced(soup: BeautifulSoup, brand: str, filename: str) -> Optional[Dict]:
    """Enhanced ingredient extraction using brand-specific selectors"""
    brand_config = BRAND_SELECTORS.get(brand, {})
    selectors = brand_config.get('selectors', [])
    
    ingredients_data = {}
    ingredients_text = None
    selector_used = None
    
    # Try JSON-LD first
    json_data = extract_json_ld_data(soup)
    if json_data.get('ingredients'):
        ingredients_text = str(json_data['ingredients'])
        selector_used = 'json_ld_ingredients'
    
    # If no JSON-LD, try CSS selectors
    if not ingredients_text:
        for selector_config in selectors:
            if selector_config.get('type') == 'json_ld':
                continue  # Already handled above
            
            if selector_config.get('type') == 'text_search':
                keywords = selector_config.get('keywords', [])
                text = extract_with_text_search(soup, keywords)
                if text:
                    ingredients_text = text
                    selector_used = f"text_search_{keywords[0]}"
                    break
            else:
                # Regular CSS selector
                tag = selector_config.get('tag')
                class_name = selector_config.get('class')
                id_name = selector_config.get('id')
                
                if class_name:
                    elements = soup.find_all(tag, class_=re.compile(class_name, re.I))
                elif id_name:
                    elements = soup.find_all(tag, id=re.compile(id_name, re.I))
                else:
                    elements = soup.find_all(tag)
                
                for element in elements:
                    text = element.get_text(strip=True)
                    
                    # Check if this looks like ingredients
                    keywords = brand_config.get('keywords', {}).get('ingredients', [])
                    if any(keyword.lower() in text.lower() for keyword in keywords):
                        if len(text) > 50:  # Ensure substantial content
                            ingredients_text = text
                            selector_used = f"{tag}.{class_name or id_name}"
                            break
                
                if ingredients_text:
                    break
    
    # If still no luck, try aggressive text search
    if not ingredients_text:
        # Look for any text with common ingredient words
        all_text = soup.get_text()
        
        # Common protein sources across languages
        protein_indicators = ['chicken', 'beef', 'lamb', 'salmon', 'duck', 'turkey',
                            'kyckling', 'nötkött', 'lam', 'lax', 'anka',  # Swedish
                            'huhn', 'rind', 'lamm', 'lachs', 'ente']      # German
        
        for indicator in protein_indicators:
            if indicator.lower() in all_text.lower():
                # Try to extract the relevant paragraph
                for p in soup.find_all(['p', 'div', 'section']):
                    p_text = p.get_text(strip=True)
                    if indicator.lower() in p_text.lower() and len(p_text) > 100:
                        ingredients_text = p_text
                        selector_used = f"text_protein_{indicator}"
                        break
                
                if ingredients_text:
                    break
    
    if ingredients_text:
        # Record which selector worked
        stats[brand]['selectors_used'].add(selector_used)
        
        # Extract from the first reasonable section (before macros/nutrition)
        sections = ingredients_text.split('\n\n')
        best_section = None
        
        for section in sections:
            # Skip sections that are purely nutritional values
            if re.search(r'^\s*\d+[.,]\d*\s*%', section.strip()):
                continue
            # Skip sections with lots of numbers (likely nutrition facts)
            if len(re.findall(r'\d+', section)) > len(section.split()) * 0.3:
                continue
            # Look for ingredient-like content
            if len(section) > 50:
                best_section = section
                break
        
        if best_section:
            ingredients_text = best_section
        
        # Clean and parse ingredients  
        ingredients_text = re.sub(r'^[^:]*:', '', ingredients_text).strip()
        
        # Split by common delimiters
        raw_ingredients = re.split(r'[,;]', ingredients_text)
        
        # Tokenize and canonicalize
        tokens = []
        for ing in raw_ingredients:
            # Remove parentheses and percentages
            ing = re.sub(r'\([^)]+\)', '', ing).strip()
            ing = re.sub(r'\d+[.,]?\d*\s*%?', '', ing).strip()
            
            # Remove common non-ingredient words
            stop_words = ['och', 'und', 'and', 'med', 'mit', 'with', 'av', 'von', 'of']
            ing_words = ing.split()
            ing_words = [w for w in ing_words if w.lower() not in stop_words]
            ing = ' '.join(ing_words)
            
            if ing and len(ing) > 2:
                canonical = canonicalize_ingredient(ing)
                if canonical:
                    tokens.append(canonical)
        
        if tokens:
            ingredients_data = {
                'ingredients_raw': ingredients_text[:2000],
                'ingredients_tokens': list(set(tokens)),
                'ingredients_language': detect_language(ingredients_text),
                'ingredients_parsed_at': datetime.now(timezone.utc).isoformat(),
                'ingredients_source': 'site_text'
            }
            
            return ingredients_data
    
    return None

def extract_macros_enhanced(soup: BeautifulSoup, brand: str) -> Optional[Dict]:
    """Enhanced macro extraction using brand-specific patterns"""
    brand_config = BRAND_SELECTORS.get(brand, {})
    nutrition_keywords = brand_config.get('keywords', {}).get('nutrition', [])
    
    macros_data = {}
    
    # Try JSON-LD first
    json_data = extract_json_ld_data(soup)
    if json_data.get('nutrition'):
        nutrition_data = json_data['nutrition']
        # Parse JSON nutrition data
        for key, value in nutrition_data.items():
            if 'protein' in key.lower():
                macros_data['protein_percent'] = float(value)
            elif 'fat' in key.lower():
                macros_data['fat_percent'] = float(value)
            # ... handle other macros
    
    # Extract from visible text
    all_text = soup.get_text()
    
    # Look for nutrition sections
    nutrition_text = None
    for keyword in nutrition_keywords:
        if keyword.lower() in all_text.lower():
            # Find the section containing nutrition info
            for element in soup.find_all(['div', 'section', 'table']):
                element_text = element.get_text()
                if keyword.lower() in element_text.lower():
                    nutrition_text = element_text
                    break
            if nutrition_text:
                break
    
    if not nutrition_text:
        nutrition_text = all_text
    
    # Extract macros using enhanced patterns
    patterns = {
        'protein_percent': [
            r'protein[:\s]+(\d+[.,]?\d*)\s*%',
            r'rohprotein[:\s]+(\d+[.,]?\d*)\s*%',
            r'protein[:\s]+(\d+[.,]?\d*)',
            r'(\d+[.,]?\d*)\s*%\s*protein'
        ],
        'fat_percent': [
            r'fat[:\s]+(\d+[.,]?\d*)\s*%',
            r'fett[:\s]+(\d+[.,]?\d*)\s*%',
            r'rohfett[:\s]+(\d+[.,]?\d*)\s*%',
            r'(\d+[.,]?\d*)\s*%\s*fat'
        ],
        'fiber_percent': [
            r'fib(?:er|re)[:\s]+(\d+[.,]?\d*)\s*%',
            r'rohfaser[:\s]+(\d+[.,]?\d*)\s*%',
            r'crude\s+fib(?:er|re)[:\s]+(\d+[.,]?\d*)\s*%'
        ],
        'ash_percent': [
            r'ash[:\s]+(\d+[.,]?\d*)\s*%',
            r'asche[:\s]+(\d+[.,]?\d*)\s*%',
            r'rohasche[:\s]+(\d+[.,]?\d*)\s*%'
        ],
        'moisture_percent': [
            r'moisture[:\s]+(\d+[.,]?\d*)\s*%',
            r'feuchtigkeit[:\s]+(\d+[.,]?\d*)\s*%',
            r'fuktighet[:\s]+(\d+[.,]?\d*)\s*%'
        ]
    }
    
    for field, regex_patterns in patterns.items():
        for pattern in regex_patterns:
            match = re.search(pattern, nutrition_text, re.I)
            if match:
                value = float(match.group(1).replace(',', '.'))
                if 0 < value < 100:
                    macros_data[field] = value
                break
    
    # Extract kcal with enhanced patterns
    kcal_patterns = [
        r'(\d+)\s*kcal/100\s*g',
        r'(\d+)\s*kcal\s*per\s*100',
        r'energi[:\s]+(\d+)\s*kcal',
        r'energy[:\s]+(\d+)\s*kcal',
        r'(\d+)\s*kJ/100\s*g',  # Convert from kJ
        r'(\d+)\s*kJ\s*per\s*100'
    ]
    
    for pattern in kcal_patterns:
        match = re.search(pattern, nutrition_text, re.I)
        if match:
            value = float(match.group(1))
            if 'kJ' in pattern:
                value = value / 4.184  # Convert kJ to kcal
            if 200 <= value <= 600:
                macros_data['kcal_per_100g'] = round(value, 1)
            break
    
    # Add source info
    if macros_data:
        if any(k.endswith('_percent') for k in macros_data):
            macros_data['macros_source'] = 'site_text'
        if 'kcal_per_100g' in macros_data:
            macros_data['kcal_source'] = 'site_text'
    
    return macros_data if macros_data else None

def process_brand_snapshots_enhanced(brand: str) -> List[Dict]:
    """Process all snapshots for a brand with enhanced extraction"""
    init_brand_stats(brand)
    updates = []
    
    # Find latest snapshot folder
    prefix = f"manufacturers/{brand}/2025-09-11/"
    blobs = list(bucket.list_blobs(prefix=prefix))
    
    if not blobs:
        logger.warning(f"No snapshots found for {brand}")
        return updates
    
    logger.info(f"Processing {len(blobs)} snapshots for {brand}")
    
    for blob in blobs:
        try:
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
                title_text = title.get_text().strip()
                if ' - ' in title_text:
                    product_name = title_text.split(' - ')[0].strip()
                else:
                    product_name = title_text
            else:
                h1 = soup.find('h1')
                if h1:
                    product_name = h1.get_text().strip()
            
            product_key = generate_product_key(brand, product_name)
            stats[brand]['total_products'] += 1
            
            # Check if product exists and get current data
            existing = supabase.table('foods_canonical').select('*').eq('product_key', product_key).execute()
            
            update_data = {}
            
            # Extract ingredients using enhanced method
            ingredients = extract_ingredients_enhanced(soup, brand, filename)
            if ingredients:
                # Only update if we don't already have ingredients or if new data is better
                should_update = True
                if existing.data and existing.data[0].get('ingredients_tokens'):
                    existing_tokens = existing.data[0]['ingredients_tokens']
                    new_tokens = ingredients['ingredients_tokens']
                    # Update if new extraction has more tokens
                    should_update = len(new_tokens) > len(existing_tokens)
                
                if should_update:
                    update_data.update(ingredients)
                    stats[brand]['ingredients_extracted'] += 1
                    
                    # Record success
                    stats[brand]['success_pages'].append({
                        'filename': filename,
                        'reason': f'Extracted {len(ingredients["ingredients_tokens"])} ingredients',
                        'selector': list(stats[brand]['selectors_used'])[-1] if stats[brand]['selectors_used'] else 'unknown'
                    })
            else:
                # Record failure
                stats[brand]['failed_pages'].append({
                    'filename': filename,
                    'reason': 'No ingredients found in HTML'
                })
            
            # Extract macros
            macros = extract_macros_enhanced(soup, brand)
            if macros:
                for field, value in macros.items():
                    # Only update non-null values
                    if value is not None and (not existing.data or not existing.data[0].get(field)):
                        update_data[field] = value
                        if 'percent' in field:
                            stats[brand]['macros_extracted'] = stats[brand].get('macros_extracted', 0) + 1
                        elif field == 'kcal_per_100g':
                            stats[brand]['kcal_extracted'] += 1
            
            # Apply update if we have new data
            if update_data:
                updates.append({
                    'product_key': product_key,
                    'product_name': product_name,
                    'updates': update_data
                })
                
                # Create product if it doesn't exist
                if not existing.data:
                    new_product = {
                        'product_key': product_key,
                        'product_name': product_name[:200],
                        'brand_slug': brand,
                        'created_at': datetime.now(timezone.utc).isoformat()
                    }
                    try:
                        supabase.table('foods_canonical').insert(new_product).execute()
                        logger.info(f"Created new product: {product_key}")
                    except Exception as e:
                        logger.warning(f"Product creation failed (might exist): {product_key}")
                
                # Update product
                try:
                    response = supabase.table('foods_canonical').update(
                        update_data
                    ).eq('product_key', product_key).execute()
                    
                    if response.data:
                        logger.info(f"Updated {product_key}: {list(update_data.keys())}")
                    else:
                        logger.warning(f"Update returned no data for {product_key}")
                except Exception as e:
                    logger.error(f"Failed to update {product_key}: {e}")
            
        except Exception as e:
            logger.error(f"Error processing {blob.name}: {e}")
            stats[brand]['failed_pages'].append({
                'filename': filename,
                'reason': f'Processing error: {str(e)}'
            })
    
    return updates

def get_coverage_stats(brand: str) -> Dict:
    """Get coverage statistics for a brand"""
    response = supabase.table('foods_canonical').select(
        'product_key, ingredients_tokens, protein_percent, fat_percent, kcal_per_100g'
    ).eq('brand_slug', brand).execute()
    
    if not response.data:
        return {'total': 0, 'ingredients_coverage': 0, 'macros_coverage': 0, 'kcal_coverage': 0}
    
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
    """Main execution for B1"""
    print("="*80)
    print("B1: BRAND-SPECIFIC ENHANCED EXTRACTION")
    print("="*80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    brands = ['bozita', 'belcando', 'briantos']
    
    # Get before stats
    before_stats = {}
    for brand in brands:
        before_stats[brand] = get_coverage_stats(brand)
        print(f"BEFORE {brand}: {before_stats[brand]['ingredients_coverage']}% ingredients")
    
    print()
    
    # Process each brand
    all_updates = {}
    for brand in brands:
        print(f"\nProcessing {brand} with enhanced selectors...")
        updates = process_brand_snapshots_enhanced(brand)
        all_updates[brand] = updates
        
        print(f"  Snapshots processed: {stats[brand]['total_products']}")
        print(f"  Ingredients extracted: {stats[brand]['ingredients_extracted']}")
        print(f"  Success pages: {len(stats[brand]['success_pages'])}")
        print(f"  Failed pages: {len(stats[brand]['failed_pages'])}")
        print(f"  Selectors used: {', '.join(stats[brand]['selectors_used'])}")
    
    # Get after stats
    after_stats = {}
    for brand in brands:
        after_stats[brand] = get_coverage_stats(brand)
    
    # Generate B1 report
    with open('NUTRITION_PASS1_REPORT.md', 'w') as f:
        f.write("# B1: Brand-Specific HTML Extraction Report\n\n")
        f.write(f"**Generated:** {datetime.now().isoformat()}\n")
        f.write(f"**Brands:** {', '.join(brands)}\n")
        f.write(f"**Method:** Enhanced selector-based extraction\n\n")
        
        # Per-brand results
        for brand in brands:
            f.write(f"## {brand.upper()}\n\n")
            
            before = before_stats[brand]
            after = after_stats[brand]
            
            # Coverage before/after
            f.write("### Coverage Results\n")
            f.write(f"- **Products:** {after['total']}\n")
            f.write(f"- **Ingredients:** {before['ingredients_coverage']}% → {after['ingredients_coverage']}% ")
            f.write(f"(+{after['ingredients_coverage'] - before['ingredients_coverage']}%)\n")
            f.write(f"- **Macros:** {before['macros_coverage']}% → {after['macros_coverage']}%\n")
            f.write(f"- **Kcal:** {before['kcal_coverage']}% → {after['kcal_coverage']}%\n\n")
            
            # Success examples
            f.write("### Successful Extractions (10 examples)\n")
            for i, page in enumerate(stats[brand]['success_pages'][:10], 1):
                f.write(f"{i}. **{page['filename']}** - {page['reason']} (selector: {page['selector']})\n")
            
            f.write("\n### Failed Extractions (5 examples)\n")
            for i, page in enumerate(stats[brand]['failed_pages'][:5], 1):
                f.write(f"{i}. **{page['filename']}** - {page['reason']}\n")
            
            f.write(f"\n### Selectors Used\n")
            for selector in stats[brand]['selectors_used']:
                f.write(f"- `{selector}`\n")
            
            f.write("\n")
        
        # Acceptance gate
        f.write("## Acceptance Gate Results\n\n")
        for brand in brands:
            after = after_stats[brand]
            if after['ingredients_coverage'] >= 60:
                f.write(f"✅ **{brand.upper()}**: {after['ingredients_coverage']}% ≥ 60% - PASSED\n")
            else:
                f.write(f"❌ **{brand.upper()}**: {after['ingredients_coverage']}% < 60% - NEEDS B2/B3\n")
                
                # Identify PDF/JS-only pages
                pdf_js_pages = []
                for page in stats[brand]['failed_pages']:
                    if 'pdf' in page['reason'].lower() or 'javascript' in page['reason'].lower():
                        pdf_js_pages.append(page['filename'])
                
                if pdf_js_pages:
                    f.write(f"   **PDF/JS-only pages:** {', '.join(pdf_js_pages[:10])}\n")
        
        f.write(f"\n## Next Steps\n")
        f.write("- For brands passing 60%: Continue to next phase\n")
        f.write("- For brands <60%: Implement B2 (JavaScript rendering) and B3 (PDF extraction)\n")
    
    print(f"\n✓ Report saved to NUTRITION_PASS1_REPORT.md")
    
    # Print summary
    for brand in brands:
        after = after_stats[brand]
        print(f"{brand}: {after['ingredients_coverage']}% ingredients coverage")

if __name__ == "__main__":
    main()