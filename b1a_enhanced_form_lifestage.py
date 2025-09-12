#!/usr/bin/env python3
"""
Enhanced B1A extractor that captures form, life_stage, and kcal in addition to ingredients
"""

import os
import re
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from google.cloud import storage
from supabase import create_client
from bs4 import BeautifulSoup
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()

# Initialize clients
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

GCS_BUCKET = 'lupito-content-raw-eu'
storage_client = storage.Client()
bucket = storage_client.bucket(GCS_BUCKET)

# Form detection patterns
FORM_PATTERNS = {
    'dry': ['dry', 'kibble', 'croquette', 'biscuit', 'pellet', 'crispy'],
    'wet': ['wet', 'can', 'canned', 'pouch', 'pate', 'terrine', 'chunks', 'gravy', 'jelly', 'sauce'],
    'raw': ['raw', 'fresh', 'frozen', 'freeze-dried', 'dehydrated'],
    'treat': ['treat', 'snack', 'chew', 'bone', 'stick', 'biscuit'],
}

# Life stage detection patterns
LIFE_STAGE_PATTERNS = {
    'puppy': ['puppy', 'junior', 'growth', 'young', 'welpe', 'valp'],
    'adult': ['adult', 'mature', 'maintenance', 'vuxen'],
    'senior': ['senior', 'mature', 'aging', 'older', 'aged', 'veteran'],
    'all': ['all life stages', 'all ages', 'family', 'complete'],
}

def detect_form(text: str) -> Optional[str]:
    """Detect product form from text"""
    text_lower = text.lower()
    
    # Check each form pattern
    for form, patterns in FORM_PATTERNS.items():
        for pattern in patterns:
            if pattern in text_lower:
                return form
    
    return None

def detect_life_stage(text: str) -> Optional[str]:
    """Detect life stage from text"""
    text_lower = text.lower()
    
    # Check each life stage pattern
    for stage, patterns in LIFE_STAGE_PATTERNS.items():
        for pattern in patterns:
            if pattern in text_lower:
                return stage
    
    return None

def extract_analytical_constituents(soup: BeautifulSoup) -> Dict:
    """Extract analytical constituents for kcal calculation"""
    constituents = {}
    
    # Common patterns for analytical constituents
    patterns = [
        r'protein[:\s]+([0-9.]+)\s*%',
        r'fat[:\s]+([0-9.]+)\s*%',
        r'fibre[:\s]+([0-9.]+)\s*%',
        r'fiber[:\s]+([0-9.]+)\s*%',
        r'ash[:\s]+([0-9.]+)\s*%',
        r'moisture[:\s]+([0-9.]+)\s*%',
        r'carbohydrate[:\s]+([0-9.]+)\s*%',
    ]
    
    text = soup.get_text()
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            if 'protein' in pattern.lower():
                constituents['protein_percent'] = value
            elif 'fat' in pattern.lower():
                constituents['fat_percent'] = value
            elif 'fib' in pattern.lower():
                constituents['fiber_percent'] = value
            elif 'ash' in pattern.lower():
                constituents['ash_percent'] = value
            elif 'moisture' in pattern.lower():
                constituents['moisture_percent'] = value
            elif 'carb' in pattern.lower():
                constituents['carbohydrate_percent'] = value
    
    return constituents

def calculate_kcal(constituents: Dict) -> Optional[float]:
    """Calculate kcal/100g from analytical constituents"""
    protein = constituents.get('protein_percent', 0)
    fat = constituents.get('fat_percent', 0)
    fiber = constituents.get('fiber_percent', 0)
    moisture = constituents.get('moisture_percent', 0)
    ash = constituents.get('ash_percent', 0)
    
    # Calculate carbohydrates if not provided
    carbs = constituents.get('carbohydrate_percent')
    if carbs is None and moisture > 0:
        # Carbs = 100 - (protein + fat + fiber + ash + moisture)
        carbs = max(0, 100 - (protein + fat + fiber + ash + moisture))
    
    if protein > 0 and fat > 0:
        # Modified Atwater formula for pet food
        # Protein: 3.5 kcal/g, Fat: 8.5 kcal/g, Carbs: 3.5 kcal/g
        kcal = (protein * 3.5) + (fat * 8.5) + ((carbs or 0) * 3.5)
        
        # Sanity check - pet food typically 200-600 kcal/100g
        if 200 <= kcal <= 600:
            return round(kcal, 1)
    
    return None

def extract_product_name(soup: BeautifulSoup) -> Optional[str]:
    """Extract product name from HTML"""
    # Try common product name selectors
    selectors = [
        'h1.product-title',
        'h1.product-name', 
        'h1[itemprop="name"]',
        'h1',
        '.product-title',
        '.product-name',
        '[itemprop="name"]'
    ]
    
    for selector in selectors:
        elem = soup.select_one(selector)
        if elem:
            name = elem.get_text(strip=True)
            if name and len(name) > 3:
                return name
    
    # Try meta tags
    meta_name = soup.find('meta', {'property': 'og:title'})
    if meta_name and meta_name.get('content'):
        return meta_name['content']
    
    # Try title tag
    title = soup.find('title')
    if title:
        title_text = title.get_text(strip=True)
        # Remove common suffixes
        title_text = re.sub(r'\s*[\|\-–]\s*.*$', '', title_text)
        if title_text and len(title_text) > 3:
            return title_text
    
    return None

def process_snapshot(brand: str, blob_name: str) -> Optional[Dict]:
    """Process a single snapshot and extract all fields"""
    try:
        # Download snapshot
        blob = bucket.blob(blob_name)
        html_content = blob.download_as_text()
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract product name
        product_name = extract_product_name(soup)
        if not product_name:
            logger.warning(f"No product name found in {blob_name}")
            return None
        
        # Initialize result
        result = {
            'brand': brand,
            'brand_slug': brand.lower(),
            'product_name_raw': product_name,
            'name_slug': re.sub(r'[^a-z0-9]+', '_', product_name.lower()).strip('_'),
            'product_key_computed': f"{brand}_{hashlib.md5(product_name.encode()).hexdigest()[:8]}",
            'extracted_at': datetime.now().isoformat(),
            'run_id': f"form_lifestage_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'product_url': f"https://{brand}.com/product",  # Placeholder
            'debug_blob': blob_name
        }
        
        # Extract form from product name and page content
        form = detect_form(product_name)
        if not form:
            # Try full page text
            page_text = soup.get_text()[:1000]  # First 1000 chars
            form = detect_form(page_text)
        
        if form:
            result['form'] = form
            logger.info(f"Detected form '{form}' for {product_name}")
        
        # Extract life stage
        life_stage = detect_life_stage(product_name)
        if not life_stage:
            # Try full page text
            page_text = soup.get_text()[:1000]
            life_stage = detect_life_stage(page_text)
        
        if life_stage:
            result['life_stage'] = life_stage
            logger.info(f"Detected life_stage '{life_stage}' for {product_name}")
        
        # Extract analytical constituents and calculate kcal
        constituents = extract_analytical_constituents(soup)
        if constituents:
            result.update(constituents)
            
            kcal = calculate_kcal(constituents)
            if kcal:
                result['kcal_per_100g'] = kcal
                result['kcal_source'] = 'calculated'
                logger.info(f"Calculated kcal: {kcal} for {product_name}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing {blob_name}: {e}")
        return None

def process_brand(brand: str, limit: Optional[int] = None):
    """Process all snapshots for a brand"""
    logger.info(f"Processing {brand} snapshots...")
    
    # List snapshots in GCS
    prefix = f"manufacturers/{brand}/"
    blobs = list(bucket.list_blobs(prefix=prefix))
    
    if limit:
        blobs = blobs[:limit]
    
    logger.info(f"Found {len(blobs)} snapshots for {brand}")
    
    results = []
    for blob in blobs:
        result = process_snapshot(brand, blob.name)
        if result:
            results.append(result)
    
    return results

def update_database(records: List[Dict]):
    """Update foods_canonical with extracted data"""
    logger.info(f"Updating {len(records)} records in database...")
    
    for record in records:
        try:
            # Try to find existing product by key
            existing = supabase.table('foods_canonical').select('*').eq(
                'product_key_computed', record['product_key_computed']
            ).execute()
            
            if existing.data:
                # Update existing record
                update_data = {}
                if 'form' in record and not existing.data[0].get('form'):
                    update_data['form'] = record['form']
                if 'life_stage' in record and not existing.data[0].get('life_stage'):
                    update_data['life_stage'] = record['life_stage']
                if 'kcal_per_100g' in record and not existing.data[0].get('kcal_per_100g'):
                    update_data['kcal_per_100g'] = record['kcal_per_100g']
                    update_data['kcal_source'] = record.get('kcal_source', 'calculated')
                
                # Add analytical constituents if present
                for field in ['protein_percent', 'fat_percent', 'fiber_percent', 'ash_percent', 'moisture_percent']:
                    if field in record and not existing.data[0].get(field):
                        update_data[field] = record[field]
                
                if update_data:
                    supabase.table('foods_canonical').update(update_data).eq(
                        'product_key_computed', record['product_key_computed']
                    ).execute()
                    logger.info(f"Updated {record['product_name_raw']} with {list(update_data.keys())}")
            
        except Exception as e:
            logger.error(f"Error updating {record.get('product_name_raw')}: {e}")

def main():
    """Main execution"""
    print("="*80)
    print("ENHANCED B1A: FORM, LIFE_STAGE & KCAL EXTRACTION")
    print("="*80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Process each brand
    brands = ['bozita', 'belcando']  # Briantos already has good coverage
    
    all_results = []
    for brand in brands:
        results = process_brand(brand)
        all_results.extend(results)
        print(f"\n{brand.upper()}: Processed {len(results)} products")
        
        # Show sample results
        if results:
            sample = results[0]
            print(f"  Sample: {sample.get('product_name_raw')}")
            print(f"    Form: {sample.get('form', 'Not detected')}")
            print(f"    Life Stage: {sample.get('life_stage', 'Not detected')}")
            print(f"    Kcal: {sample.get('kcal_per_100g', 'Not calculated')}")
    
    # Update database
    if all_results:
        print(f"\nUpdating database with {len(all_results)} records...")
        update_database(all_results)
        print("✅ Database updated successfully")
    
    print("\n" + "="*80)
    print("EXTRACTION COMPLETE")
    print(f"Total records processed: {len(all_results)}")
    print("="*80)

if __name__ == "__main__":
    main()