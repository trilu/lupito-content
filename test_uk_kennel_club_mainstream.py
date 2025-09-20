#!/usr/bin/env python3
"""
Test UK Kennel Club scraper with mainstream breeds
"""

import logging
import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test with mainstream breeds UK Kennel Club definitely has
test_breeds = [
    'labrador-retriever',
    'golden-retriever',
    'german-shepherd',
    'border-collie',
    'bulldog'
]

base_url = "https://www.thekennelclub.org.uk/search/breeds-a-to-z/"

for breed in test_breeds:
    url = f"{base_url}{breed}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        logger.info(f"{breed}: {response.status_code}")

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for exercise info
            text = soup.get_text().lower()
            if 'exercise' in text:
                logger.info(f"  ✓ Has exercise info")
            if 'grooming' in text:
                logger.info(f"  ✓ Has grooming info")
            if 'temperament' in text:
                logger.info(f"  ✓ Has temperament info")

    except Exception as e:
        logger.error(f"Error for {breed}: {e}")