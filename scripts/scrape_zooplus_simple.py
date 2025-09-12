#!/usr/bin/env python3
"""
Simple Zooplus scraper with basic ScrapingBee settings
Focus on getting the content first, then parsing
"""

import os
import json
import re
import time
import requests
from typing import Dict, Optional
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

SCRAPINGBEE_API_KEY = os.getenv('SCRAPING_BEE')

def scrape_zooplus_product(url: str) -> Optional[Dict]:
    """Scrape a single Zooplus product page"""
    
    # Convert to UK site
    if 'zooplus.com' in url:
        url = url.replace('zooplus.com', 'zooplus.co.uk')
    
    # Simple but effective ScrapingBee params
    params = {
        'api_key': SCRAPINGBEE_API_KEY,
        'url': url,
        'render_js': 'true',
        'wait': '5000',
        'premium_proxy': 'true',
        'country_code': 'gb',
    }
    
    print(f"Scraping: {url}")
    
    try:
        response = requests.get(
            'https://app.scrapingbee.com/api/v1/',
            params=params,
            timeout=60
        )
        
        if response.status_code == 200:
            print(f"  Success! Got {len(response.text)} chars")
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract product data
            product = {'url': url}
            
            # Get product name
            h1 = soup.find('h1')
            if h1:
                product['name'] = h1.text.strip()
                print(f"  Name: {product['name'][:50]}")
            
            # Search for ingredients in the entire text
            page_text = soup.get_text()
            
            # Look for Composition
            if 'Composition:' in page_text:
                comp_idx = page_text.index('Composition:')
                # Get next 500 chars after "Composition:"
                comp_text = page_text[comp_idx:comp_idx+1000]
                
                # Extract until we hit another section
                comp_match = re.search(r'Composition:\s*([^\\n]{20,}?)(?:Analytical|Additives|Feeding|$)', comp_text, re.I)
                if comp_match:
                    ingredients = comp_match.group(1).strip()
                    product['ingredients_raw'] = ingredients[:500]
                    print(f"  ✅ Found ingredients: {ingredients[:80]}...")
            
            # Look for nutrition
            if 'Analytical' in page_text or 'Protein' in page_text:
                # Extract protein
                prot_match = re.search(r'Protein[:\s]+(\d+\.?\d*)\s*%', page_text, re.I)
                if prot_match:
                    product['protein_percent'] = float(prot_match.group(1))
                    print(f"  Protein: {product['protein_percent']}%")
                
                # Extract fat
                fat_match = re.search(r'Fat[:\s]+(\d+\.?\d*)\s*%', page_text, re.I)
                if fat_match:
                    product['fat_percent'] = float(fat_match.group(1))
                
                # Extract fiber
                fiber_match = re.search(r'Fib(?:re|er)[:\s]+(\d+\.?\d*)\s*%', page_text, re.I)
                if fiber_match:
                    product['fiber_percent'] = float(fiber_match.group(1))
            
            # Save HTML for debugging
            with open(f'debug_simple_{int(time.time())}.html', 'w') as f:
                f.write(response.text[:20000])
            
            return product
            
        else:
            print(f"  Error {response.status_code}")
            return None
            
    except Exception as e:
        print(f"  Exception: {e}")
        return None

def main():
    """Test with a few products"""
    
    print("SIMPLE ZOOPLUS SCRAPER TEST")
    print("="*60)
    
    # Test URLs - mix of different products
    test_urls = [
        "https://www.zooplus.com/shop/dogs/dry_dog_food/royal_canin_size/medium/128332",
        "https://www.zooplus.com/shop/dogs/dry_dog_food/purizon/purizon_grainfree/983630",
        "https://www.zooplus.com/shop/dogs/dry_dog_food/josera/320633",
    ]
    
    results = []
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n[{i}/{len(test_urls)}]")
        
        if i > 1:
            print("Waiting 5 seconds...")
            time.sleep(5)
        
        result = scrape_zooplus_product(url)
        if result:
            results.append(result)
    
    # Summary
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    
    for r in results:
        print(f"\n{r.get('name', 'Unknown')}")
        if 'ingredients_raw' in r:
            print(f"  Ingredients: YES ({len(r['ingredients_raw'])} chars)")
        if 'protein_percent' in r:
            print(f"  Nutrition: Protein={r['protein_percent']}%")
    
    # Save results
    with open('data/zooplus_simple_test.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    ingredients_found = sum(1 for r in results if 'ingredients_raw' in r)
    print(f"\n✅ Found ingredients in {ingredients_found}/{len(results)} products")

if __name__ == "__main__":
    main()