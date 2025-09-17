#!/usr/bin/env python3
"""
Debug extraction
"""

from bs4 import BeautifulSoup
import re

# Load the HTML
with open('/tmp/affenpinscher.html', 'r') as f:
    html_content = f.read()

soup = BeautifulSoup(html_content, 'html.parser')

# Find all h2 headings
print("All H2 headings found:")
for h2 in soup.find_all('h2'):
    print(f"  - {h2.get_text().strip()}")

print("\nTrying to extract History section:")
# Try exact method
for heading in soup.find_all(['h2', 'h3']):
    heading_content = heading.get_text().lower().strip()
    print(f"Checking heading: '{heading_content}'")
    if 'history' == heading_content or 'history' in heading_content:
        print(f"  Found matching heading!")
        # Get next siblings
        sibling = heading.find_next_sibling()
        paragraphs = []
        while sibling and sibling.name not in ['h2', 'h3']:
            if sibling.name == 'p':
                text = sibling.get_text(strip=True)
                text = re.sub(r'\[\d+\]', '', text)
                text = re.sub(r'\s+', ' ', text)
                if text and len(text) > 50:
                    paragraphs.append(text)
                    print(f"  Found paragraph: {text[:100]}...")
                    if len(paragraphs) >= 3:
                        break
            sibling = sibling.find_next_sibling()
        break