#!/usr/bin/env python3
"""
Debug Wolf of Wilderness page text to see actual structure
"""

import requests
import os
import re
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

url = "https://www.zooplus.com/shop/dogs/canned_dog_food/wolf_of_wilderness/wolf_of_wilderness_red/1958908"

# Scrape with ScrapingBee
params = {
    'api_key': os.getenv('SCRAPING_BEE'),
    'url': url,
    'render_js': 'true',
    'premium_proxy': 'true',
    'stealth_proxy': 'true',
    'country_code': 'gb',
    'wait': '3000',
    'return_page_source': 'true'
}

print("🔍 DEBUGGING WOLF OF WILDERNESS PAGE STRUCTURE")
print("="*60)

try:
    response = requests.get('https://app.scrapingbee.com/api/v1/', params=params, timeout=120)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text(separator='\n', strip=True)
        
        # Find the section around "Go to analytical constituents"
        lines = page_text.split('\n')
        
        print("Looking for ingredients section...")
        for i, line in enumerate(lines):
            if 'go to analytical' in line.lower():
                print(f"\n📍 Found 'Go to analytical constituents' at line {i}")
                print("Context (10 lines before and after):")
                print("-" * 40)
                start = max(0, i-10)
                end = min(len(lines), i+15)
                for j in range(start, end):
                    marker = ">>> " if j == i else "    "
                    print(f"{marker}{j:3}: {lines[j]}")
                break
        
        # Also search for "Ingredients" sections
        print("\n" + "="*60)
        print("Looking for 'Ingredients' sections...")
        for i, line in enumerate(lines):
            if line.strip().lower() == 'ingredients' or line.strip().lower() == 'ingredients:':
                print(f"\n📍 Found 'Ingredients' at line {i}: '{line}'")
                print("Context (5 lines before and after):")
                print("-" * 40)
                start = max(0, i-5)
                end = min(len(lines), i+10)
                for j in range(start, end):
                    marker = ">>> " if j == i else "    "
                    print(f"{marker}{j:3}: {lines[j]}")
        
    else:
        print(f"❌ HTTP {response.status_code}: {response.text[:200]}")
        
except Exception as e:
    print(f"❌ Error: {e}")