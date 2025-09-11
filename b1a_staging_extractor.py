#!/usr/bin/env python3
"""
B1A: Staging-based ingredient extractor
Modified B1 to INSERT only into foods_ingestion_staging for server-side merge
"""

import os
import re
import json
import yaml
import uuid
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

# Brand-specific selector maps (unchanged from B1)
BRAND_SELECTORS = {
    'bozita': {
        'language': 'swedish',
        'keywords': {
            'ingredients': ['sammansättning', 'ingredienser', 'innehåll'],
            'nutrition': ['analytiska beståndsdelar', 'näringsinnehåll', 'energi'],
        },
        'selectors': [
            {'type': 'json_ld', 'key': 'nutrition'},
            {'type': 'json_ld', 'key': 'ingredients'},
            {'tag': 'div', 'class': 'product-ingredients'},
            {'tag': 'div', 'class': 'ingredients-content'},
            {'tag': 'section', 'class': 'product-nutrition'},
            {'tag': 'div', 'id': 'ingredients'},
            {'tag': 'div', 'id': 'nutrition'},
            {'tag': 'div', 'id': 'composition'},
            {'tag': 'div', 'class': 'tab-pane'},
            {'tag': 'div', 'class': 'tab-content'},
            {'tag': 'div', 'class': 'content'},
            {'tag': 'section', 'class': 'content'},
            {'tag': 'div', 'class': 'product-info'},
            {'tag': 'div', 'class': 'product-details'},
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
            {'type': 'json_ld', 'key': 'nutrition'},
            {'type': 'json_ld', 'key': 'ingredients'},
            {'tag': 'div', 'class': 'zusammensetzung'},
            {'tag': 'div', 'class': 'inhaltsstoffe'},
            {'tag': 'div', 'class': 'analytische-bestandteile'},
            {'tag': 'section', 'class': 'produkt-details'},
            {'tag': 'div', 'class': 'product-ingredients'},
            {'tag': 'div', 'class': 'ingredients-content'},
            {'tag': 'section', 'class': 'product-nutrition'},
            {'tag': 'div', 'id': 'zusammensetzung'},
            {'tag': 'div', 'id': 'inhaltsstoffe'},
            {'tag': 'div', 'id': 'analytische-bestandteile'},
            {'tag': 'div', 'class': 'tab-pane'},
            {'tag': 'div', 'class': 'tab-content'},
            {'tag': 'div', 'class': 'content'},
            {'tag': 'section', 'class': 'content'},
            {'tag': 'div', 'class': 'product-info'},
            {'tag': 'div', 'class': 'product-details'},
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
            {'type': 'json_ld', 'key': 'nutrition'},
            {'type': 'json_ld', 'key': 'ingredients'},
            {'tag': 'div', 'class': 'composition'},
            {'tag': 'div', 'class': 'ingredients'},
            {'tag': 'div', 'class': 'analytical-constituents'},
            {'tag': 'div', 'class': 'product-ingredients'},
            {'tag': 'div', 'class': 'ingredients-content'},
            {'tag': 'section', 'class': 'product-nutrition'},
            {'tag': 'div', 'id': 'ingredients'},
            {'tag': 'div', 'id': 'composition'},
            {'tag': 'div', 'id': 'nutrition'},
            {'tag': 'div', 'class': 'tab-pane'},
            {'tag': 'div', 'class': 'tab-content'},
            {'tag': 'div', 'class': 'content'},
            {'tag': 'section', 'class': 'content'},
            {'tag': 'div', 'class': 'product-info'},
            {'tag': 'div', 'class': 'product-details'},
            {'type': 'text_search', 'keywords': ['composition', 'ingredients']},
        ]
    }
}

# Global run ID for this extraction batch
RUN_ID = f"b1a_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# Statistics tracking
stats = {}

def init_brand_stats(brand: str):
    """Initialize stats for a brand"""
    stats[brand] = {
        'total_products': 0,
        'ingredients_extracted': 0,
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

def generate_name_slug(product_name: str) -> str:
    """Generate a slug from product name"""
    slug = product_name.lower()
    slug = re.sub(r'[^a-z0-9]+', '_', slug)
    slug = re.sub(r'_+', '_', slug).strip('_')
    return slug

def detect_language(text: str) -> str:
    """Detect language of text"""
    try:
        lang = langdetect.detect(text)
        return lang
    except:
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
    
    json_scripts = soup.find_all('script', {'type': 'application/ld+json'})
    
    for script in json_scripts:
        try:
            json_data = json.loads(script.string)
            
            if isinstance(json_data, list):
                json_data = json_data[0] if json_data else {}
            
            if 'nutrition' in json_data:
                data['nutrition'] = json_data['nutrition']
            
            if 'ingredients' in json_data:
                data['ingredients'] = json_data['ingredients']
                
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
        elements = soup.find_all(string=re.compile(keyword, re.I))
        
        for elem in elements:
            if elem.parent:
                parent = elem.parent
                
                for level in range(3):
                    if parent:
                        text = parent.get_text(strip=True)
                        
                        if len(text) > 100 and keyword.lower() in text.lower():
                            return text
                        
                        parent = parent.parent
    
    return None

def extract_ingredients_enhanced(soup: BeautifulSoup, brand: str, filename: str) -> Optional[Dict]:
    """Enhanced ingredient extraction using brand-specific selectors (unchanged from B1)"""
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
                continue
            
            if selector_config.get('type') == 'text_search':
                keywords = selector_config.get('keywords', [])
                text = extract_with_text_search(soup, keywords)
                if text:
                    ingredients_text = text
                    selector_used = f"text_search_{keywords[0]}"
                    break
            else:
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
                    
                    keywords = brand_config.get('keywords', {}).get('ingredients', [])
                    if any(keyword.lower() in text.lower() for keyword in keywords):
                        if len(text) > 50:
                            ingredients_text = text
                            selector_used = f"{tag}.{class_name or id_name}"
                            break
                
                if ingredients_text:
                    break
    
    # If still no luck, try aggressive text search
    if not ingredients_text:
        all_text = soup.get_text()
        
        protein_indicators = ['chicken', 'beef', 'lamb', 'salmon', 'duck', 'turkey',
                            'kyckling', 'nötkött', 'lam', 'lax', 'anka',
                            'huhn', 'rind', 'lamm', 'lachs', 'ente']
        
        for indicator in protein_indicators:
            if indicator.lower() in all_text.lower():
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
        
        # Extract from the first reasonable section
        sections = ingredients_text.split('\n\n')
        best_section = None
        
        for section in sections:
            if re.search(r'^\s*\d+[.,]\d*\s*%', section.strip()):
                continue
            if len(re.findall(r'\d+', section)) > len(section.split()) * 0.3:
                continue
            if len(section) > 50:
                best_section = section
                break
        
        if best_section:
            ingredients_text = best_section
        
        # Clean and parse ingredients
        ingredients_text = re.sub(r'^[^:]*:', '', ingredients_text).strip()
        
        raw_ingredients = re.split(r'[,;]', ingredients_text)
        
        # Tokenize and canonicalize
        tokens = []
        for ing in raw_ingredients:
            ing = re.sub(r'\([^)]+\)', '', ing).strip()
            ing = re.sub(r'\d+[.,]?\d*\s*%?', '', ing).strip()
            
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

def process_brand_snapshots_staging(brand: str) -> List[Dict]:
    """Process all snapshots for a brand using staging workflow"""
    init_brand_stats(brand)
    staging_records = []
    
    # Find latest snapshot folder
    prefix = f"manufacturers/{brand}/2025-09-11/"
    blobs = list(bucket.list_blobs(prefix=prefix))
    
    if not blobs:
        logger.warning(f"No snapshots found for {brand}")
        return staging_records
    
    logger.info(f"Processing {len(blobs)} snapshots for {brand} with staging workflow")
    
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
            name_slug = generate_name_slug(product_name)
            stats[brand]['total_products'] += 1
            
            # Extract ingredients using enhanced method (same as B1)
            ingredients = extract_ingredients_enhanced(soup, brand, filename)
            
            if ingredients:
                # Create staging record
                staging_record = {
                    'run_id': RUN_ID,
                    'brand': brand,
                    'brand_slug': brand,
                    'product_name_raw': product_name,
                    'name_slug': name_slug,
                    'product_key_computed': product_key,
                    'product_url': f"gs://lupito-content-raw-eu/{blob.name}",  # Reference to source
                    **ingredients,
                    'extracted_at': datetime.now(timezone.utc).isoformat(),
                    'debug_blob': {
                        'filename': filename,
                        'selector_used': list(stats[brand]['selectors_used'])[-1] if stats[brand]['selectors_used'] else 'unknown',
                        'tokens_count': len(ingredients.get('ingredients_tokens', [])),
                        'raw_length': len(ingredients.get('ingredients_raw', '')),
                    }
                }
                
                staging_records.append(staging_record)
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
            
        except Exception as e:
            logger.error(f"Error processing {blob.name}: {e}")
            stats[brand]['failed_pages'].append({
                'filename': filename,
                'reason': f'Processing error: {str(e)}'
            })
    
    return staging_records

def insert_staging_records(staging_records: List[Dict]) -> int:
    """Insert all staging records into foods_ingestion_staging"""
    if not staging_records:
        return 0
    
    try:
        response = supabase.table('foods_ingestion_staging').insert(staging_records).execute()
        inserted_count = len(response.data)
        logger.info(f"Successfully inserted {inserted_count} records into staging")
        return inserted_count
    except Exception as e:
        logger.error(f"Failed to insert staging records: {e}")
        return 0

def main():
    """Main execution for B1A"""
    print("="*80)
    print("B1A: STAGING-BASED INGREDIENT EXTRACTION")
    print("="*80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Run ID: {RUN_ID}")
    
    brands = ['bozita', 'belcando', 'briantos']
    
    # Process each brand and collect staging records
    all_staging_records = []
    
    for brand in brands:
        print(f"\nProcessing {brand} with staging workflow...")
        brand_records = process_brand_snapshots_staging(brand)
        all_staging_records.extend(brand_records)
        
        print(f"  Snapshots processed: {stats[brand]['total_products']}")
        print(f"  Ingredients extracted: {stats[brand]['ingredients_extracted']}")
        print(f"  Success pages: {len(stats[brand]['success_pages'])}")
        print(f"  Failed pages: {len(stats[brand]['failed_pages'])}")
        print(f"  Selectors used: {', '.join(stats[brand]['selectors_used'])}")
        print(f"  Staging records created: {len(brand_records)}")
    
    print(f"\nTotal staging records: {len(all_staging_records)}")
    
    # Insert all staging records
    if all_staging_records:
        inserted_count = insert_staging_records(all_staging_records)
        print(f"Inserted {inserted_count} records into foods_ingestion_staging")
        
        # Health check
        if len(all_staging_records) >= 50 and inserted_count == 0:
            logger.error("HEALTH CHECK FAILED: Extracted ≥50 but inserted 0 - aborting")
            return
        
        print(f"\n✅ B1A completed successfully")
        print(f"   Run ID: {RUN_ID}")
        print(f"   Records staged: {inserted_count}")
        print(f"   Ready for server-side merge")
        
    else:
        logger.warning("No staging records created - check extraction logic")

if __name__ == "__main__":
    main()