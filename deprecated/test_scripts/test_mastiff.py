#!/usr/bin/env python3
"""
Test scraping English Mastiff with the correct URL
"""

import sys
from pathlib import Path

# Add the jobs directory to the path
sys.path.insert(0, str(Path(__file__).parent / 'jobs'))

from wikipedia_breed_scraper_fixed import WikipediaBreedScraper

# Initialize scraper
scraper = WikipediaBreedScraper()

# Test English Mastiff
breed_name = "English Mastiff"
url = "https://en.wikipedia.org/wiki/English_Mastiff"

print(f"Testing: {breed_name}")
print(f"URL: {url}")
print("-" * 60)

try:
    scraper.scrape_breed(breed_name, url)
    print(f"✅ SUCCESS: Scraped {breed_name}")
except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()