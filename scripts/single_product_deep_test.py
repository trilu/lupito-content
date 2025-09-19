#!/usr/bin/env python3
"""
Single Product Deep Test - Thoroughly test one Zooplus product
"""

import os
import re
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

SCRAPINGBEE_API_KEY = os.getenv('SCRAPING_BEE')

# Test product missing ingredients
test_url = 'https://www.zooplus.com/shop/dogs/dry_dog_food/purizon/trial_packs/1191314'

print("🧪 SINGLE PRODUCT DEEP TEST")
print("="*60)
print(f"URL: {test_url}")
print()

# Scrape with ScrapingBee
params = {
    'api_key': SCRAPINGBEE_API_KEY,
    'url': test_url,
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
    
    soup = BeautifulSoup(response.text, 'html.parser')
    page_text = soup.get_text(separator='\n', strip=True)
    
    # Save for analysis
    with open('data/single_test_page.html', 'w') as f:
        f.write(response.text)
    print("💾 Saved HTML to data/single_test_page.html")
    
    # Product name
    h1 = soup.find('h1')
    if h1:
        print(f"\n📦 Product: {h1.text.strip()}")
    
    # Search for ingredients
    print("\n🔍 SEARCHING FOR INGREDIENTS:")
    
    # Look for any text containing "Composition" or "Ingredients"
    for line in page_text.split('\n'):
        if any(word in line for word in ['Composition', 'Ingredients', 'Zusammensetzung']):
            print(f"  Found line: {line[:100]}...")
            
            # Get next few lines
            lines = page_text.split('\n')
            idx = lines.index(line)
            for i in range(idx, min(idx+5, len(lines))):
                if lines[i].strip():
                    print(f"    {lines[i][:100]}")
    
    # Search for nutrition
    print("\n🔍 SEARCHING FOR NUTRITION:")
    
    # Look for protein, fat, etc.
    nutrition_words = ['Protein', 'Fat', 'Fibre', 'Ash', 'Moisture', 'Analytical']
    for line in page_text.split('\n'):
        if any(word.lower() in line.lower() for word in nutrition_words):
            if '%' in line:
                print(f"  Found: {line[:100]}")
    
    # Check for variants
    print("\n🔍 CHECKING FOR VARIANTS:")
    
    selects = soup.find_all('select')
    for select in selects:
        name = select.get('name', 'unknown')
        options = select.find_all('option')
        if options:
            print(f"  Select '{name}': {len(options)} options")
            for opt in options[:3]:
                print(f"    - {opt.text.strip()}")
    
    # Check for tabs/accordions
    print("\n🔍 CHECKING FOR TABS/ACCORDIONS:")
    
    tabs = soup.find_all(class_=re.compile('tab|accordion|collapse'))
    if tabs:
        print(f"  Found {len(tabs)} tab/accordion elements")
        for tab in tabs[:3]:
            text = tab.get_text(strip=True)[:100]
            if text:
                print(f"    - {text}...")
    
    # Search for any divs with product info
    print("\n🔍 CHECKING PRODUCT INFO DIVS:")
    
    info_divs = soup.find_all('div', class_=re.compile('product-info|description|details'))
    if info_divs:
        print(f"  Found {len(info_divs)} product info divs")
        for div in info_divs[:3]:
            text = div.get_text(strip=True)[:200]
            if text:
                print(f"    - {text}...")
    
else:
    print(f"❌ HTTP {response.status_code}")
    print(response.text[:500])

print("\n" + "="*60)
print("Test complete. Check data/single_test_page.html for full HTML")