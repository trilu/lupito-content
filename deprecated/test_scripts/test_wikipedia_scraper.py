#!/usr/bin/env python3
"""
Test Wikipedia scraper to identify parsing issues
"""

import requests
from bs4 import BeautifulSoup
import re
from typing import Dict, Any

def test_wikipedia_extraction(breed_name: str, url: str):
    """Test extraction from Wikipedia for a single breed"""
    print(f"\n{'='*60}")
    print(f"Testing: {breed_name}")
    print(f"URL: {url}")
    print('='*60)
    
    # Fetch page
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find infobox - try different selectors
    infobox = soup.find('table', {'class': 'infobox'})
    if not infobox:
        # Try alternative selectors
        infobox = soup.find('table', class_=lambda x: x and 'infobox' in x)
    
    if not infobox:
        # Look for any table with breed info
        for table in soup.find_all('table'):
            if 'breed' in str(table).lower() or 'weight' in str(table).lower():
                print(f"Found potential table: {table.get('class')}")
                
        print("No infobox found! Checking page structure...")
        # Check if page exists
        if 'Wikipedia does not have an article' in response.text:
            print("Page does not exist!")
        else:
            # Look for weight/height in paragraphs
            for p in soup.find_all('p')[:5]:
                text = p.get_text()
                if 'weight' in text.lower() or 'kg' in text.lower() or 'pound' in text.lower():
                    print(f"Found weight info in paragraph: {text[:200]}...")
                    break
        return
    
    # Extract all rows and print them
    print("\nINFOBOX CONTENT:")
    for row in infobox.find_all('tr'):
        header = row.find('th')
        if not header:
            continue
        
        header_text = header.get_text(strip=True)
        cell = row.find('td')
        if not cell:
            continue
        
        cell_text = cell.get_text(separator=' ', strip=True)
        print(f"  {header_text}: {cell_text}")
        
        # Specifically look for weight/height
        if 'weight' in header_text.lower():
            print(f"    -> RAW WEIGHT TEXT: '{cell_text}'")
            
            # Test current parsing logic
            text = cell_text.lower()
            numbers = re.findall(r'(\d+(?:\.\d+)?)', text)
            print(f"    -> NUMBERS FOUND: {numbers}")
            
            # Look for kg values
            kg_matches = re.findall(r'(\d+(?:\.\d+)?)\s*(?:kg|kilogram)', text)
            print(f"    -> KG MATCHES: {kg_matches}")
            
            # Look for lb values
            lb_matches = re.findall(r'(\d+(?:\.\d+)?)\s*(?:lb|pound)', text)
            print(f"    -> LB MATCHES: {lb_matches}")
            
        if 'height' in header_text.lower():
            print(f"    -> RAW HEIGHT TEXT: '{cell_text}'")

# Test with known breeds
test_cases = [
    ('Labrador Retriever', 'https://en.wikipedia.org/wiki/Labrador_Retriever'),
    ('German Shepherd', 'https://en.wikipedia.org/wiki/German_Shepherd'),
    ('Chihuahua', 'https://en.wikipedia.org/wiki/Chihuahua_(dog)'),
]

for breed_name, url in test_cases:
    test_wikipedia_extraction(breed_name, url)