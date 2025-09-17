#!/usr/bin/env python3
"""
Test AADF scraping to understand HTML structure
"""
import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

SCRAPINGBEE_API_KEY = os.getenv('SCRAPING_BEE')

def scrape_with_scrapingbee(url):
    """Scrape using ScrapingBee to bypass Cloudflare"""
    params = {
        'api_key': SCRAPINGBEE_API_KEY,
        'url': url,
        'render_js': 'false',
        'premium_proxy': 'true',
        'country_code': 'gb'
    }

    response = requests.get(
        'https://app.scrapingbee.com/api/v1/',
        params=params,
        timeout=30
    )

    if response.status_code == 200:
        return response.text
    else:
        print(f"Error: {response.status_code}")
        return None

# Test with one AADF URL
test_url = "https://www.allaboutdogfood.co.uk/dog-food-reviews/1328/essential-stamina"
print(f"Testing URL: {test_url}")

html = scrape_with_scrapingbee(test_url)
if html:
    # Save HTML for analysis
    with open('/tmp/aadf_test.html', 'w') as f:
        f.write(html)
    print("HTML saved to /tmp/aadf_test.html")

    # Try to find ingredients and nutrition
    soup = BeautifulSoup(html, 'html.parser')

    # Look for any text containing "Composition" or "Ingredients"
    text = soup.get_text()

    # Find composition section
    import re
    comp_match = re.search(r'Composition[:\s]*([^.]{20,500})', text, re.IGNORECASE)
    if comp_match:
        print("\nFound Composition:")
        print(comp_match.group(1)[:200])

    # Find analytical constituents
    anal_match = re.search(r'Analytical [Cc]onstituents[:\s]*([^.]{20,500})', text, re.IGNORECASE)
    if anal_match:
        print("\nFound Analytical Constituents:")
        print(anal_match.group(1)[:200])

    # Check for specific divs/sections
    print("\n\nLooking for specific elements:")

    # Find all h2, h3, h4 headers
    headers = soup.find_all(['h2', 'h3', 'h4'])
    for h in headers[:10]:
        print(f"Header: {h.text.strip()}")

    # Look for tables
    tables = soup.find_all('table')
    print(f"\nFound {len(tables)} tables")

    # Look for definition lists
    dls = soup.find_all('dl')
    print(f"Found {len(dls)} definition lists")