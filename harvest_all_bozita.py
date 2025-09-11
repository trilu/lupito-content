#!/usr/bin/env python3
"""
Harvest ALL Bozita products (no limit)
"""

import os
from pathlib import Path
from scrapingbee_harvester import ScrapingBeeHarvester

def harvest_all_bozita():
    """Harvest all Bozita products from saved URLs"""
    
    print("="*80)
    print("HARVESTING ALL BOZITA PRODUCTS")
    print("="*80)
    
    # Read all product URLs from file
    with open('bozita_product_urls.txt', 'r') as f:
        all_products = [line.strip() for line in f if line.strip()]
    
    print(f"Found {len(all_products)} products to harvest")
    
    # Initialize harvester
    harvester = ScrapingBeeHarvester('bozita', Path('profiles/manufacturers/bozita.yaml'))
    
    # Harvest ALL products (no limit)
    print(f"\nStarting harvest of ALL {len(all_products)} products...")
    harvest_stats = harvester.harvest_products(all_products)
    
    print(f"\n{'='*80}")
    print("HARVEST COMPLETE")
    print(f"{'='*80}")
    print(f"✓ Products harvested: {harvest_stats['snapshots_created']}")
    print(f"✓ Failures: {harvest_stats['failures']}")
    print(f"✓ API credits used: {harvester.stats['api_credits_used']}")
    print(f"✓ Success rate: {(harvest_stats['snapshots_created'] / len(all_products) * 100):.1f}%")
    
    return harvest_stats

if __name__ == "__main__":
    harvest_all_bozita()