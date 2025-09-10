#!/usr/bin/env python3
"""Debug Great Dane Wikipedia parsing"""

import requests
from bs4 import BeautifulSoup
import re

url = 'https://en.wikipedia.org/wiki/Great_Dane'
response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
soup = BeautifulSoup(response.text, 'html.parser')

# Find infobox
infobox = soup.find('table', class_='infobox')
if not infobox:
    infobox = soup.find('table', class_=lambda x: x and 'infobox' in str(x))

if infobox:
    print("INFOBOX FOUND")
    print("="*60)
    
    for row in infobox.find_all('tr'):
        header = row.find('th')
        if header:
            header_text = header.get_text(strip=True)
            cells = row.find_all('td')
            if cells:
                cell_text = ' '.join([c.get_text(strip=True) for c in cells])
                print(f"{header_text}: {cell_text}")
                
                # Debug weight and lifespan parsing
                if 'weight' in header_text.lower():
                    print(f"  -> Analyzing weight text: '{cell_text}'")
                    # Try different patterns
                    patterns = [
                        r'(\d+)[\u2013\-](\d+)\s*kg',
                        r'(\d+)[\u2013\-](\d+)\s*lb',
                        r'(\d+)\s*kg',
                        r'(\d+)\s*lb',
                        r'(\d+(?:\.\d+)?)',
                    ]
                    for pattern in patterns:
                        matches = re.findall(pattern, cell_text)
                        if matches:
                            print(f"    Pattern '{pattern}' found: {matches}")
                
                if 'life' in header_text.lower():
                    print(f"  -> Analyzing lifespan text: '{cell_text}'")
                    year_patterns = [
                        r'(\d+)[\u2013\-](\d+)\s*year',
                        r'(\d+)\s*year',
                        r'(\d+(?:\.\d+)?)\s*year',
                    ]
                    for pattern in year_patterns:
                        matches = re.findall(pattern, cell_text.lower())
                        if matches:
                            print(f"    Pattern '{pattern}' found: {matches}")
else:
    print("NO INFOBOX FOUND")