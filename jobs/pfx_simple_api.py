#!/usr/bin/env python3
"""
Simple PFX API scraper to get all products quickly
No complex logic, just iterate through all pages
"""
import os
import sys
import json
import time
import requests
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))
from etl.normalize_foods import generate_fingerprint, clean_text
from etl.nutrition_parser import parse_nutrition_from_html

from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

def main():
    print("🚀 Starting Simple PFX API Scraper")
    
    # Setup
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (compatible; LupitoBot/1.0)',
        'Accept': 'application/json'
    })
    
    supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY'))
    
    # Discover all products
    all_products = []
    page = 1
    
    print("📄 Discovering products...")
    
    while page <= 200:  # Safety limit
        try:
            url = f"https://petfoodexpert.com/api/products?species=dog&page={page}"
            print(f"  Fetching page {page}...", end=" ")
            
            response = session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            products = data.get('data', [])
            
            if not products:
                print(f"EMPTY - stopping at page {page}")
                break
                
            all_products.extend(products)
            print(f"Found {len(products)} products. Total: {len(all_products)}")
            
            page += 1
            time.sleep(0.5)  # Small delay
            
        except Exception as e:
            print(f"ERROR: {e}")
            break
    
    print(f"\n🎯 Discovery complete: {len(all_products)} products found")
    
    # Process first 10 products as test
    print(f"\n📋 Processing first 10 products as test...")
    
    for i, product in enumerate(all_products[:10]):
        try:
            name = product.get('name', '')
            brand_data = product.get('brand', {})
            brand = brand_data.get('name', '') if brand_data else ''
            url = product.get('url', '')
            
            print(f"[{i+1}/10] {brand} {name}")
            
            # Extract nutrition from HTML
            if url:
                response = session.get(url, timeout=10)
                nutrition = parse_nutrition_from_html(response.text)
                print(f"    Nutrition: kcal={nutrition.get('kcal_per_100g') if nutrition else 'None'}")
            
            time.sleep(1)  # Rate limit
            
        except Exception as e:
            print(f"    ERROR: {e}")
    
    print(f"\n✅ Test complete. Full dataset has {len(all_products)} products ready for processing")
    
if __name__ == '__main__':
    main()