#!/usr/bin/env python3
"""Test the enhanced Wikipedia breed scraper"""

import requests
from bs4 import BeautifulSoup
import json

# Test with Golden Retriever
url = 'https://en.wikipedia.org/wiki/Golden_Retriever'
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')

# Check structure
print("Wikipedia Page Structure for Golden Retriever")
print("=" * 50)

# Find all h2 headings
h2_headings = soup.find_all('h2')
print(f"\nFound {len(h2_headings)} H2 sections:")
for h in h2_headings[:10]:
    # Get the text from the span with class mw-headline
    headline = h.find('span', {'class': 'mw-headline'})
    if headline:
        print(f"  - {headline.get_text(strip=True)}")

# Find the first paragraph
content = soup.find('div', {'id': 'mw-content-text'})
if content:
    # Find the first paragraph that's not in a table or infobox
    for p in content.find_all('p', recursive=False):
        text = p.get_text(strip=True)
        if len(text) > 100:  # Skip short paragraphs
            print(f"\nFirst paragraph:\n{text[:300]}...")
            break

# Check for specific sections
print("\n\nChecking for key sections:")
for section_name in ['History', 'Temperament', 'Health', 'Appearance', 'Training']:
    found = False
    for heading in soup.find_all(['h2', 'h3']):
        headline = heading.find('span', {'class': 'mw-headline'})
        if headline and section_name.lower() in headline.get_text().lower():
            print(f"  ✓ Found: {headline.get_text()}")
            found = True
            break
    if not found:
        print(f"  ✗ Not found: {section_name}")

# Extract from infobox
infobox = soup.find('table', {'class': 'infobox'})
if infobox:
    print("\n\nInfobox data found:")
    for row in infobox.find_all('tr')[:10]:
        th = row.find('th')
        td = row.find('td')
        if th and td:
            label = th.get_text(strip=True)
            value = td.get_text(strip=True)[:50]
            print(f"  {label}: {value}")