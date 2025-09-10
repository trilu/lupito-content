#!/usr/bin/env python3
"""Test single URL scraping with nutrition"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from jobs.pfx_scrape_v2 import PetFoodExpertScraperV2
import logging

logging.basicConfig(level=logging.DEBUG)

# Test URL
url = "https://petfoodexpert.com/food/aatu-chicken-dry-dog"

scraper = PetFoodExpertScraperV2(mode='auto')
result = scraper.scrape_url(url)

print("\nFinal stats:")
print(scraper.stats)