#!/usr/bin/env python3
"""
Test 10 products with the updated orchestrator patterns
"""

import os
import sys
import json
import time
import random
from datetime import datetime
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google.cloud import storage
from supabase import create_client

load_dotenv()

SCRAPINGBEE_API_KEY = os.getenv('SCRAPING_BEE')
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")

def get_test_products(limit: int = 10) -> List[Dict]:
    """Get 10 products without ingredients to test"""
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        response = supabase.table('foods_canonical').select(
            'product_key, product_name, brand, product_url'
        ).ilike('product_url', '%zooplus.com%')\
        .is_('ingredients_raw', 'null')\
        .limit(limit).execute()
        
        products = response.data if response.data else []
        print(f"Found {len(products)} products to test")
        return products
    except Exception as e:
        print(f"Error fetching products: {e}")
        return []

def scrape_product(url: str) -> Dict:
    """Scrape with proven parameters"""
    
    # Clean URL
    if '?activeVariant=' in url:
        url = url.split('?activeVariant=')[0]
    
    # Use proven stealth parameters
    params = {
        'api_key': SCRAPINGBEE_API_KEY,
        'url': url,
        'render_js': 'true',
        'premium_proxy': 'true',
        'stealth_proxy': 'true',
        'country_code': 'gb',
        'wait': '3000',
        'return_page_source': 'true'
    }
    
    try:
        response = requests.get(
            'https://app.scrapingbee.com/api/v1/',
            params=params,
            timeout=120
        )
        
        if response.status_code == 200:
            return parse_response(response.text, url)
        else:
            error_msg = f'HTTP {response.status_code}'
            if response.text:
                error_msg += f': {response.text[:100]}'
            return {'url': url, 'error': error_msg}
            
    except Exception as e:
        return {'url': url, 'error': str(e)[:200]}

def parse_response(html: str, url: str) -> Dict:
    """Parse HTML response with updated patterns"""
    
    soup = BeautifulSoup(html, 'html.parser')
    page_text = soup.get_text(separator='\n', strip=True)
    
    result = {
        'url': url,
        'scraped_at': datetime.now().isoformat()
    }
    
    # Product name
    h1 = soup.find('h1')
    if h1:
        result['product_name'] = h1.text.strip()
    
    # Extract ingredients with UPDATED patterns
    import re
    ingredients_patterns = [
        # Pattern 1: "Ingredients / composition" followed by ingredients on next line
        r'Ingredients\s*/\s*composition\s*\n([^\n]+(?:\([^)]+\))?(?:[,.]?\s*[^\n]+(?:\([^)]+\))?)*?)(?:\n\nAdditives|\nAdditives|\nAnalytical|\n\n)',
        
        # Pattern 2: "Ingredients:" with optional product description, then ingredients
        r'Ingredients:\s*\n(?:[^\n]*?(?:wet food|complete|diet)[^\n]*\n)?(\d+%[^\n]+(?:[,.]?\s*[^\n]+)*?)(?:\n\nAdditives|\nAdditives)',
        
        # Pattern 3: "Ingredients:" with variant info (e.g., "1.5kg bags:")
        r'Ingredients:\s*\n(?:\d+(?:\.\d+)?kg bags?:\s*\n)?([A-Z][^\n]+(?:[,.]?\s*[^\n]+)*?)(?:\n\d+(?:\.\d+)?kg bags?:|\n\nAdditives|\nAdditives)',
        
        # Pattern 4: Simple "Ingredients:" followed directly by ingredients
        r'Ingredients:\s*\n([A-Z][^\n]+(?:\([^)]+\))?[,.]?\s*)(?:\n\nAdditives per kg:|\nAdditives|\n\n)',
        
        # Pattern 5: General "Ingredients:" with multiline capture
        r'Ingredients:\s*\n([^\n]+(?:\([^)]+\))?(?:[,.]?\s*[^\n]+(?:\([^)]+\))?)*?)(?:\n\nAdditives|\nAdditives|\n\nAnalytical|\nAnalytical)',
        
        # Pattern 6: "Ingredients" (no colon) followed by meat/duck/chicken
        r'Ingredients\s*\n((?:Meat|Duck|Chicken)[^\n]+(?:\([^)]+\))?(?:[,.]?\s*[^\n]+)*)(?:\n\nAdditives|\nAdditives)',
        
        # Pattern 7: "Ingredients:" with Duck/Chicken/Meat starting
        r'Ingredients:\s*\n((?:Duck|Chicken|Meat|Lamb|Beef|Turkey|Salmon|Fish)[^\n]+(?:\([^)]+\))?(?:[,.]?\s*[^\n]+)*)(?:\n\nAdditives|\nAdditives)',
        
        # Original patterns as fallback
        r'(?:Composition|Ingredients)[:\s]*\n?([^\n]{20,}?)(?:\n(?:Analytical|Additives|Nutritional)|$)',
        r'(?:Composition|Ingredients)[:\s]*([A-Za-z][^.]{30,}(?:\.[^.]{20,})*?)(?:Analytical|$)',
    ]
    
    for pattern in ingredients_patterns:
        match = re.search(pattern, page_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if match:
            ingredients = match.group(1).strip()
            # Skip if it's navigation text
            if 'go to' in ingredients.lower() or 'constituent' in ingredients.lower():
                continue
            if any(word in ingredients.lower() for word in ['meat', 'chicken', 'beef', 'fish', 'rice', 'wheat', 'maize', 'protein', 'poultry']):
                result['ingredients_raw'] = ingredients[:3000]
                break
    
    # Extract nutrition
    nutrition = {}
    patterns = [
        (r'(?:Crude\s+)?Protein[:\s]+(\d+(?:\.\d+)?)\s*%', 'protein_percent'),
        (r'(?:Crude\s+)?(?:Fat|Oils)[:\s]+(\d+(?:\.\d+)?)\s*%', 'fat_percent'),
        (r'(?:Crude\s+)?Fib(?:re|er)[:\s]+(\d+(?:\.\d+)?)\s*%', 'fiber_percent'),
        (r'(?:Crude\s+)?Ash[:\s]+(\d+(?:\.\d+)?)\s*%', 'ash_percent'),
        (r'Moisture[:\s]+(\d+(?:\.\d+)?)\s*%', 'moisture_percent')
    ]
    
    for pattern, key in patterns:
        match = re.search(pattern, page_text, re.IGNORECASE)
        if match:
            nutrition[key] = float(match.group(1))
    
    if nutrition:
        result['nutrition'] = nutrition
    
    return result

def main():
    """Run test of 10 products"""
    print("=" * 60)
    print("TESTING 10 PRODUCTS WITH UPDATED PATTERNS")
    print("=" * 60)
    
    # Get test products
    products = get_test_products(10)
    if not products:
        print("No products to test")
        return
    
    # Track results
    stats = {
        'total': 0,
        'with_ingredients': 0,
        'with_nutrition': 0,
        'errors': 0
    }
    
    # Test each product
    for i, product in enumerate(products, 1):
        print(f"\n[{i}/10] Testing: {product['product_name'][:50]}...")
        print(f"URL: {product['product_url']}")
        
        # Delay between requests
        if i > 1:
            delay = random.uniform(15, 25)
            print(f"Waiting {delay:.1f}s...")
            time.sleep(delay)
        
        stats['total'] += 1
        
        # Scrape
        result = scrape_product(product['product_url'])
        
        # Show results
        if 'error' in result:
            print(f"❌ Error: {result['error']}")
            stats['errors'] += 1
        else:
            if 'ingredients_raw' in result:
                print(f"✅ Found ingredients: {result['ingredients_raw'][:100]}...")
                stats['with_ingredients'] += 1
            else:
                print(f"⚠️ No ingredients found")
            
            if 'nutrition' in result:
                print(f"✅ Found nutrition: {result['nutrition']}")
                stats['with_nutrition'] += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"Total tested: {stats['total']}")
    print(f"With ingredients: {stats['with_ingredients']} ({stats['with_ingredients']/stats['total']*100:.1f}%)")
    print(f"With nutrition: {stats['with_nutrition']} ({stats['with_nutrition']/stats['total']*100:.1f}%)")
    print(f"Errors: {stats['errors']}")
    
    if stats['with_ingredients'] > 0:
        print(f"\n🎉 SUCCESS RATE: {stats['with_ingredients']/stats['total']*100:.1f}%")
    else:
        print("\n⚠️ No ingredients extracted - patterns may need adjustment")

if __name__ == "__main__":
    main()