#!/usr/bin/env python3
"""
Harvest batch of products from PetFoodExpert listing API
"""
import os
import sys
import json
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime

import requests
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Load environment
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def fetch_listing_page(page: int = 1, species: str = 'dog') -> dict:
    """Fetch a page of products from the listing API"""
    url = f"https://petfoodexpert.com/api/products?species={species}&page={page}"
    headers = {
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (compatible; LupitoBot/1.0; +https://lupito.app)'
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def harvest_pages(start_page: int = 1, end_page: int = 5, species: str = 'dog', limit: int = 100):
    """Harvest multiple pages of products and extract URLs"""
    all_urls = []
    total_available = 0
    
    for page in range(start_page, end_page + 1):
        logger.info(f"Fetching page {page}...")
        
        try:
            # Rate limit
            time.sleep(0.8)
            
            # Fetch page
            data = fetch_listing_page(page, species)
            
            # Extract product URLs
            products = data.get('data', [])
            for product in products:
                url = product.get('url')
                if url:
                    all_urls.append(url)
            
            # Get total count
            pagination = data.get('meta', {}).get('pagination', {})
            total_available = pagination.get('total', 0)
            
            logger.info(f"Page {page}: Found {len(products)} products")
            
            # Check if we have enough
            if len(all_urls) >= limit:
                all_urls = all_urls[:limit]
                break
                
        except Exception as e:
            logger.error(f"Failed to fetch page {page}: {e}")
    
    logger.info(f"\nHarvest complete!")
    logger.info(f"Total products available: {total_available}")
    logger.info(f"URLs collected: {len(all_urls)}")
    
    return all_urls


def save_urls_to_file(urls: list, filename: str = 'harvest_urls.txt'):
    """Save URLs to a file for processing"""
    with open(filename, 'w') as f:
        for url in urls:
            f.write(url + '\n')
    logger.info(f"Saved {len(urls)} URLs to {filename}")


def main():
    parser = argparse.ArgumentParser(description='Harvest product URLs from PetFoodExpert')
    parser.add_argument('--start-page', type=int, default=1, help='Start page')
    parser.add_argument('--end-page', type=int, default=5, help='End page')
    parser.add_argument('--species', default='dog', help='Species to filter')
    parser.add_argument('--limit', type=int, default=100, help='Maximum URLs to collect')
    parser.add_argument('--output', default='harvest_urls.txt', help='Output file')
    
    args = parser.parse_args()
    
    # Harvest URLs
    urls = harvest_pages(
        start_page=args.start_page,
        end_page=args.end_page,
        species=args.species,
        limit=args.limit
    )
    
    # Save to file
    if urls:
        save_urls_to_file(urls, args.output)
        print(f"\nReady to scrape! Run:")
        print(f"python3 jobs/pfx_scrape_v2.py --seed-list {args.output} --mode auto --limit {len(urls)}")


if __name__ == '__main__':
    main()