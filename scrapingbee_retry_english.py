#!/usr/bin/env python3
"""
Retry Bozita and Cotswold with English paths
Always try English paths for international sites
"""

import os
import sys
from pathlib import Path
from scrapingbee_harvester import ScrapingBeeHarvester, generate_blocked_sites_report

def retry_with_english_paths():
    """Retry failed brands with correct English paths"""
    
    # Brands to retry with proper paths
    retry_config = {
        'bozita': {
            'base_url': 'https://www.bozita.com',
            'product_paths': [
                '/dog',
                '/dog-food',
                '/products/dog',
                '/dog/dry-food',
                '/dog/wet-food',
                '/collections/dog-food'
            ],
            'country_code': 'us'  # Use US for English site
        },
        'cotswold': {
            'base_url': 'https://www.cotswoldraw.com',
            'product_paths': [
                '/collections/dog-food',
                '/collections/all',
                '/collections/raw-dog-food',
                '/collections/dog-treats',
                '/pages/products'
            ],
            'country_code': 'gb'
        }
    }
    
    print("="*80)
    print("RETRYING WITH ENGLISH PATHS")
    print("="*80)
    print("Rule: Always try English paths for international sites")
    print("="*80)
    
    all_stats = {}
    
    for brand, config in retry_config.items():
        print(f"\n{'='*40}")
        print(f"Processing {brand.upper()}")
        print(f"{'='*40}")
        print(f"Base URL: {config['base_url']}")
        print(f"Trying paths: {', '.join(config['product_paths'])}")
        
        try:
            # Create custom profile with English paths
            profile_path = Path(f'profiles/manufacturers/{brand}.yaml')
            
            # Initialize harvester with custom config
            harvester = ScrapingBeeHarvester(brand, profile_path)
            
            # Override base URL and country
            harvester.base_url = config['base_url']
            harvester.country_code = config['country_code']
            
            # Try each product path
            all_product_urls = set()
            
            for path in config['product_paths']:
                test_url = config['base_url'] + path
                print(f"\nTrying: {test_url}")
                
                try:
                    html_content = harvester.fetch_with_scrapingbee(test_url)
                    if html_content:
                        print(f"  ✓ Success! Found page at {path}")
                        
                        # Extract product URLs from this page
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(html_content, 'html.parser')
                        
                        # Common patterns for product links
                        product_selectors = [
                            'a[href*="/products/"]',
                            'a[href*="/collections/"][href*="/products/"]',
                            'a.product-link',
                            'a.product-item__link',
                            'h3.product-item__title a',
                            'div.product a[href]'
                        ]
                        
                        for selector in product_selectors:
                            links = soup.select(selector)
                            for link in links:
                                href = link.get('href', '')
                                if href and '/products/' in href:
                                    # Make absolute URL
                                    if href.startswith('/'):
                                        product_url = config['base_url'] + href
                                    elif href.startswith('http'):
                                        product_url = href
                                    else:
                                        product_url = config['base_url'] + '/' + href
                                    
                                    all_product_urls.add(product_url)
                        
                        print(f"  Found {len(all_product_urls)} product URLs so far")
                    else:
                        print(f"  ✗ Failed: {path}")
                        
                except Exception as e:
                    print(f"  ✗ Error on {path}: {e}")
            
            # Harvest the products we found
            if all_product_urls:
                print(f"\nHarvesting {len(all_product_urls)} products for {brand}")
                product_urls = list(all_product_urls)[:20]  # Limit to 20 for testing
                harvest_stats = harvester.harvest_products(product_urls)
                
                all_stats[brand] = {
                    'harvester': harvester.stats,
                    'harvest': harvest_stats,
                    'sample_urls': product_urls[:5]
                }
                
                print(f"\n✓ Completed {brand}:")
                print(f"  - API credits used: {harvester.stats['api_credits_used']}")
                print(f"  - Products found: {len(all_product_urls)}")
                print(f"  - Snapshots created: {harvest_stats['snapshots_created']}")
            else:
                print(f"\n✗ No products found for {brand}")
                all_stats[brand] = {
                    'error': 'No products found with English paths'
                }
                
        except Exception as e:
            print(f"\n✗ Failed to process {brand}: {e}")
            all_stats[brand] = {'error': str(e)}
    
    # Update the final report
    update_english_retry_report(all_stats)
    
    print("\n" + "="*80)
    print("ENGLISH RETRY COMPLETE")
    print("="*80)
    print("Report updated: BLOCKED_SITES_ENGLISH_RETRY.md")
    
    return all_stats

def update_english_retry_report(stats):
    """Create report for English retry attempts"""
    from datetime import datetime
    
    with open('BLOCKED_SITES_ENGLISH_RETRY.md', 'w') as f:
        f.write("# Blocked Sites English Retry Report\n\n")
        f.write(f"**Generated:** {datetime.now().isoformat()}\n")
        f.write(f"**Method:** ScrapingBee with English paths\n")
        f.write(f"**Brands:** bozita, cotswold\n\n")
        
        f.write("## Summary\n\n")
        f.write("**Key Learning:** Always try English paths for international sites\n\n")
        
        # Calculate totals
        total_products = 0
        total_snapshots = 0
        total_credits = 0
        
        for brand, data in stats.items():
            if 'harvester' in data:
                total_products += data['harvester'].get('products_found', 0)
                total_snapshots += data['harvest'].get('snapshots_created', 0)
                total_credits += data['harvester'].get('api_credits_used', 0)
        
        f.write(f"**Retry Results:**\n")
        f.write(f"- **API credits used:** {total_credits}\n")
        f.write(f"- **Total products found:** {total_products}\n")
        f.write(f"- **Total snapshots created:** {total_snapshots}\n\n")
        
        # Per-brand details
        f.write("## Per-Brand Results\n\n")
        
        for brand, data in stats.items():
            f.write(f"### {brand.upper()}\n")
            
            if 'error' in data:
                f.write(f"**Status:** ❌ Failed\n")
                f.write(f"**Error:** {data['error']}\n\n")
            elif 'harvester' in data:
                snapshots = data['harvest']['snapshots_created']
                if snapshots >= 20:
                    f.write(f"**Status:** ✅ Success\n")
                elif snapshots > 0:
                    f.write(f"**Status:** ⚠️ Partial\n")
                else:
                    f.write(f"**Status:** ❌ No products\n")
                
                f.write(f"- Products found: {data['harvester'].get('products_found', 0)}\n")
                f.write(f"- Snapshots created: {snapshots}\n")
                f.write(f"- API credits used: {data['harvester'].get('api_credits_used', 0)}\n\n")
                
                if data.get('sample_urls'):
                    f.write("**Sample URLs found:**\n")
                    for url in data['sample_urls'][:3]:
                        f.write(f"- {url}\n")
                    f.write("\n")

if __name__ == "__main__":
    retry_with_english_paths()