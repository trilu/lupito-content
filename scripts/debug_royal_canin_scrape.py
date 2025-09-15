#!/usr/bin/env python3
"""
Debug scrape of Royal Canin product that has ingredients on page
"""

import os
import re
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

SCRAPINGBEE_API_KEY = os.getenv('SCRAPING_BEE')

url = 'https://www.zooplus.com/shop/dogs/dry_dog_food/royal_canin_vet_diet/1949350'

print("🔍 DEBUG SCRAPE: Royal Canin Product")
print("="*60)
print(f"URL: {url}")
print("\nKnown content from manual check:")
print("  - Has ingredients: Dried poultry protein, maize, barley...")
print("  - Has nutrition: protein 28%, fat 11%, fibre 7.2%...")
print()

# Scrape with ScrapingBee
params = {
    'api_key': SCRAPINGBEE_API_KEY,
    'url': url,
    'render_js': 'true',
    'premium_proxy': 'true', 
    'stealth_proxy': 'true',
    'country_code': 'gb',
    'wait': '5000',
    'return_page_source': 'true'
}

print("📡 Sending request to ScrapingBee...")
response = requests.get('https://app.scrapingbee.com/api/v1/', params=params, timeout=120)

if response.status_code == 200:
    print(f"✅ Success! Received {len(response.text):,} bytes")
    
    # Save HTML for inspection
    with open('/tmp/royal_canin_debug.html', 'w') as f:
        f.write(response.text)
    print("💾 Saved HTML to /tmp/royal_canin_debug.html")
    
    soup = BeautifulSoup(response.text, 'html.parser')
    page_text = soup.get_text(separator='\n', strip=True)
    
    # Search for the known ingredients text
    print("\n🔍 SEARCHING FOR KNOWN INGREDIENTS:")
    search_terms = ['Dried poultry protein', 'maize', 'barley', 'wheat gluten', 'Ingredients']
    
    for term in search_terms:
        if term in page_text:
            print(f"  ✅ Found '{term}' in page")
            # Find context
            lines = page_text.split('\n')
            for i, line in enumerate(lines):
                if term in line:
                    print(f"    Line {i}: {line[:100]}...")
                    if i > 0:
                        print(f"    Previous: {lines[i-1][:100]}...")
                    if i < len(lines)-1:
                        print(f"    Next: {lines[i+1][:100]}...")
                    break
        else:
            print(f"  ❌ '{term}' NOT found in page")
    
    print("\n🔍 SEARCHING FOR PATTERNS:")
    
    # Pattern used by orchestrated_scraper
    patterns = [
        r'(?:Composition|Ingredients)[:\s]*\n?([^\n]{20,}?)(?:\n(?:Analytical|Additives|Nutritional)|$)',
        r'(?:Composition|Ingredients)[:\s]*([A-Za-z][^.]{30,}(?:\.[^.]{20,})*?)(?:Analytical|$)',
    ]
    
    for i, pattern in enumerate(patterns, 1):
        matches = re.findall(pattern, page_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if matches:
            print(f"  Pattern {i}: Found {len(matches)} matches")
            for match in matches[:2]:
                text = match if isinstance(match, str) else match[0]
                print(f"    Match: {text[:100]}...")
        else:
            print(f"  Pattern {i}: No matches")
    
    # Check page structure
    print("\n🔍 PAGE STRUCTURE ANALYSIS:")
    
    # Look for product description sections
    product_sections = soup.find_all(['div', 'section'], class_=re.compile('product|description|detail|info'))
    print(f"  Found {len(product_sections)} product sections")
    
    # Look for tabs
    tabs = soup.find_all(class_=re.compile('tab'))
    print(f"  Found {len(tabs)} tab elements")
    
    # Look for accordions
    accordions = soup.find_all(class_=re.compile('accordion|collapse'))
    print(f"  Found {len(accordions)} accordion elements")
    
    # Sample of page text
    print("\n📄 FIRST 500 CHARS OF PAGE TEXT:")
    print(page_text[:500])
    
    print("\n📄 SEARCHING FOR 'INGREDIENTS' SECTION:")
    if 'Ingredients' in page_text:
        idx = page_text.index('Ingredients')
        print(f"Found at position {idx}")
        print("Context (200 chars before and after):")
        print(page_text[max(0, idx-200):min(len(page_text), idx+500)])
    
else:
    print(f"❌ HTTP {response.status_code}")
    print(response.text[:500])