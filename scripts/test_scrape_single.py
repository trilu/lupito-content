#!/usr/bin/env python3
"""
Test scraping a single Zooplus product
Simpler version to debug issues
"""

import os
import re
import time
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SCRAPINGBEE_API_KEY = os.getenv('SCRAPING_BEE')
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def main():
    print("TEST SINGLE ZOOPLUS SCRAPE")
    print("="*60)
    
    # Connect to database
    print("\n1. Connecting to database...")
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Get one product
    print("2. Fetching a product without ingredients...")
    response = supabase.table('foods_canonical').select(
        'product_key, product_name, product_url'
    ).ilike('product_url', '%zooplus%').is_('ingredients_raw', 'null').limit(1).execute()
    
    if not response.data:
        print("No products found")
        return
    
    product = response.data[0]
    print(f"   Found: {product['product_name']}")
    print(f"   URL: {product['product_url']}")
    
    # Scrape the product
    print("\n3. Scraping product page...")
    
    url = product['product_url']
    # Remove activeVariant if present
    if '?activeVariant=' in url:
        url = url.split('?activeVariant=')[0]
    
    params = {
        'api_key': SCRAPINGBEE_API_KEY,
        'url': url,
        'render_js': 'true',
        'wait': '7000',
        'premium_proxy': 'true',
        'stealth_proxy': 'true',
        'country_code': 'us',
        'return_page_source': 'true',
    }
    
    print("   Sending request to ScrapingBee...")
    try:
        response = requests.get(
            'https://app.scrapingbee.com/api/v1/',
            params=params,
            timeout=90
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            html = response.text
            print(f"   Got {len(html)} bytes")
            
            # Parse
            soup = BeautifulSoup(html, 'html.parser')
            page_text = soup.get_text(separator='\n', strip=True)
            
            # Save HTML for debugging
            with open('debug_zooplus_page.html', 'w', encoding='utf-8') as f:
                f.write(html[:200000])  # Save first 200KB
            print("   Saved to debug_zooplus_page.html")
            
            # Check for ingredients
            print("\n4. Searching for ingredients...")
            
            # Also check for common ingredient words
            ingredient_words = ['chicken', 'beef', 'meat', 'rice', 'corn', 'wheat']
            for word in ingredient_words:
                if word in page_text.lower():
                    print(f"   ✓ Found '{word}' in page")
                    break
            
            if 'Composition' in page_text:
                print("   ✓ Found 'Composition' in page")
                
                # Extract
                match = re.search(
                    r'(?:Composition|Ingredients)[:\s]*\n?([^\n]{20,}?)(?:\nAnalytical|\nAdditives|\nFeeding|\n\n)',
                    page_text,
                    re.IGNORECASE | re.MULTILINE
                )
                
                if match:
                    ingredients = match.group(1).strip()
                    print(f"   ✓ Extracted: {ingredients[:100]}...")
                    
                    # Update database
                    print("\n5. Updating database...")
                    update_data = {
                        'ingredients_raw': ingredients[:2000],
                        'ingredients_source': 'site'
                    }
                    
                    supabase.table('foods_canonical').update(
                        update_data
                    ).eq('product_key', product['product_key']).execute()
                    
                    print("   ✓ Database updated!")
                else:
                    print("   ✗ Could not extract ingredients")
            else:
                print("   ✗ 'Composition' not found in page")
            
            # Check for nutrition
            print("\n6. Searching for nutrition...")
            nutrition_found = False
            
            if 'Protein' in page_text:
                match = re.search(r'Protein[:\s]+(\d+\.?\d*)\s*%', page_text, re.I)
                if match:
                    print(f"   ✓ Protein: {match.group(1)}%")
                    nutrition_found = True
            
            if 'Fat' in page_text:
                match = re.search(r'Fat[:\s]+(\d+\.?\d*)\s*%', page_text, re.I)
                if match:
                    print(f"   ✓ Fat: {match.group(1)}%")
                    nutrition_found = True
            
            if not nutrition_found:
                print("   ✗ No nutrition data found")
                
    except Exception as e:
        print(f"   Error: {str(e)[:200]}")
    
    print("\n" + "="*60)
    print("TEST COMPLETE")

if __name__ == "__main__":
    main()