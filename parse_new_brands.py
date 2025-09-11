#!/usr/bin/env python3
"""
Parse newly harvested brands (Belcando and Bozita) from GCS
"""

import os
import logging
from datetime import datetime
from supabase import create_client, Client
from google.cloud import storage
from bs4 import BeautifulSoup
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize Supabase client
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(url, key)

# Initialize GCS client
gcs_client = storage.Client(project='lupito-ai')
bucket = gcs_client.bucket('lupito-content-raw-eu')

def parse_brand_snapshots(brand):
    """Parse snapshots for a specific brand"""
    stats = {
        'total_products': 0,
        'ingredients_extracted': 0,
        'macros_extracted': 0,
        'kcal_extracted': 0
    }
    
    # List all snapshots for this brand
    prefix = f"snapshots/{brand}/"
    blobs = list(bucket.list_blobs(prefix=prefix))
    
    # Get the most recent date folder
    date_folders = set()
    for blob in blobs:
        parts = blob.name.split('/')
        if len(parts) >= 3:
            date_folders.add(parts[2])
    
    if not date_folders:
        logging.warning(f"No snapshots found for {brand}")
        return stats
    
    latest_date = sorted(date_folders)[-1]
    logging.info(f"Found date folder: {latest_date}")
    logging.info(f"Using snapshots from {latest_date}")
    
    # Filter blobs for latest date
    dated_blobs = [b for b in blobs if f"/{latest_date}/" in b.name]
    
    for blob in dated_blobs:
        if not blob.name.endswith('.html'):
            continue
            
        stats['total_products'] += 1
        
        # Download and parse HTML
        html_content = blob.download_as_text()
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract product key from filename
        filename = blob.name.split('/')[-1]
        product_key = f"{brand}_" + filename.replace('.html', '')
        
        # Extract nutrition info
        nutrition_data = {}
        
        # Common patterns for ingredients
        ingredient_patterns = [
            r'ingredients?[:\s]+([^.]+)',
            r'composition[:\s]+([^.]+)',
            r'contains[:\s]+([^.]+)',
        ]
        
        for pattern in ingredient_patterns:
            elements = soup.find_all(text=re.compile(pattern, re.I))
            for elem in elements:
                match = re.search(pattern, str(elem), re.I)
                if match:
                    nutrition_data['ingredients_tokens'] = match.group(1).strip()
                    stats['ingredients_extracted'] += 1
                    break
            if 'ingredients_tokens' in nutrition_data:
                break
        
        # Extract macros
        macro_patterns = {
            'protein_percent': [r'protein[:\s]+(\d+[\.,]?\d*)\s*%', r'crude protein[:\s]+(\d+[\.,]?\d*)\s*%'],
            'fat_percent': [r'fat[:\s]+(\d+[\.,]?\d*)\s*%', r'crude fat[:\s]+(\d+[\.,]?\d*)\s*%'],
            'fibre_percent': [r'fib(?:re|er)[:\s]+(\d+[\.,]?\d*)\s*%', r'crude fib(?:re|er)[:\s]+(\d+[\.,]?\d*)\s*%'],
            'ash_percent': [r'ash[:\s]+(\d+[\.,]?\d*)\s*%', r'crude ash[:\s]+(\d+[\.,]?\d*)\s*%'],
            'moisture_percent': [r'moisture[:\s]+(\d+[\.,]?\d*)\s*%', r'water[:\s]+(\d+[\.,]?\d*)\s*%']
        }
        
        for macro, patterns in macro_patterns.items():
            for pattern in patterns:
                text = soup.get_text()
                match = re.search(pattern, text, re.I)
                if match:
                    value = match.group(1).replace(',', '.')
                    nutrition_data[macro] = float(value)
                    stats['macros_extracted'] += 1
                    break
        
        # Extract kcal
        kcal_patterns = [
            r'(\d+)\s*kcal/100\s*g',
            r'energy[:\s]+(\d+)\s*kcal',
            r'metaboli[sz]able energy[:\s]+(\d+)\s*kcal'
        ]
        
        for pattern in kcal_patterns:
            text = soup.get_text()
            match = re.search(pattern, text, re.I)
            if match:
                nutrition_data['kcal_per_100g'] = int(match.group(1))
                stats['kcal_extracted'] += 1
                break
        
        # Update database if we have data
        if nutrition_data:
            try:
                response = supabase.table('foods_canonical').update(nutrition_data).eq('product_key', product_key).execute()
                if not response.data:
                    logging.warning(f"No matching product for {product_key}")
            except Exception as e:
                logging.error(f"Error updating {product_key}: {e}")
    
    return stats

def main():
    """Main execution"""
    print("="*80)
    print("PARSING NEW BRANDS (BELCANDO & BOZITA)")
    print("="*80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    brands = ['belcando', 'bozita']
    total_stats = {
        'ingredients': 0,
        'macros': 0,
        'kcal': 0
    }
    
    for brand in brands:
        print(f"\nProcessing {brand}...")
        stats = parse_brand_snapshots(brand)
        print(f"  Processed {stats['total_products']} products")
        print(f"  Extracted ingredients: {stats['ingredients_extracted']}")
        print(f"  Extracted macros: {stats['macros_extracted']}")
        print(f"  Extracted kcal: {stats['kcal_extracted']}")
        
        total_stats['ingredients'] += stats['ingredients_extracted']
        total_stats['macros'] += stats['macros_extracted']
        total_stats['kcal'] += stats['kcal_extracted']
    
    print("\n" + "="*80)
    print("PARSING COMPLETE")
    print("="*80)
    print(f"\nTotal extractions:")
    print(f"  - Ingredients: {total_stats['ingredients']}")
    print(f"  - Macros: {total_stats['macros']}")
    print(f"  - Kcal: {total_stats['kcal']}")

if __name__ == "__main__":
    main()