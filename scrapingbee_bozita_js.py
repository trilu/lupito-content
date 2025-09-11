#!/usr/bin/env python3
"""
Retry Bozita with enhanced JavaScript/AJAX handling
"""

import os
import time
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import json

load_dotenv()

def fetch_bozita_with_enhanced_js():
    """Try Bozita with various JavaScript handling strategies"""
    
    api_key = os.getenv('SCRAPING_BEE')
    base_url = 'https://bozita.com'
    
    print("="*80)
    print("BOZITA ENHANCED JAVASCRIPT RETRY")
    print("="*80)
    
    # Different ScrapingBee configurations to try
    configs = [
        {
            'name': 'Extended Wait + Scroll',
            'params': {
                'api_key': api_key,
                'url': f'{base_url}/dog-food/',
                'render_js': 'true',
                'premium_proxy': 'true',
                'country_code': 'us',
                'wait': '5000',  # Wait 5 seconds for JS
                'wait_for': 'networkidle',  # Wait for network to be idle
                'js_scenario': json.dumps({
                    "instructions": [
                        {"wait": 2000},
                        {"scroll": {"y": 500}},
                        {"wait": 1000},
                        {"scroll": {"y": 1000}},
                        {"wait": 1000},
                        {"scroll": {"y": 1500}},
                        {"wait": 2000}
                    ]
                })
            }
        },
        {
            'name': 'Wait for Selector',
            'params': {
                'api_key': api_key,
                'url': f'{base_url}/dog-food/',
                'render_js': 'true',
                'premium_proxy': 'true',
                'country_code': 'us',
                'wait': '5000',
                'wait_for': '.product-item, .product-grid, .product-list, article',  # Wait for product elements
                'block_ads': 'true',
                'block_resources': 'false'  # Don't block resources, might break JS
            }
        },
        {
            'name': 'Click Load More',
            'params': {
                'api_key': api_key,
                'url': f'{base_url}/dog-food/',
                'render_js': 'true',
                'premium_proxy': 'true',
                'country_code': 'us',
                'wait': '3000',
                'js_scenario': json.dumps({
                    "instructions": [
                        {"wait": 2000},
                        {"click": "button:contains('Load More'), button:contains('Show More'), .load-more"},
                        {"wait": 3000},
                        {"scroll": {"y": 1000}},
                        {"wait": 2000}
                    ]
                })
            }
        },
        {
            'name': 'AJAX Intercept',
            'params': {
                'api_key': api_key,
                'url': f'{base_url}/dog-food/',
                'render_js': 'true',
                'premium_proxy': 'true',
                'country_code': 'us',
                'wait': '5000',
                'wait_for': 'networkidle2',  # Wait for max 2 network connections
                'intercept_request': json.dumps({
                    "patterns": [
                        {"url_pattern": "*api*"},
                        {"url_pattern": "*products*"},
                        {"url_pattern": "*graphql*"}
                    ]
                })
            }
        }
    ]
    
    all_products = set()
    successful_config = None
    
    for config in configs:
        print(f"\n{'='*40}")
        print(f"Trying: {config['name']}")
        print(f"{'='*40}")
        
        try:
            response = requests.get(
                'https://app.scrapingbee.com/api/v1/',
                params=config['params'],
                timeout=60
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                html_content = response.text
                print(f"Response size: {len(html_content)} bytes")
                
                # Save for debugging
                with open(f'bozita_{config["name"].replace(" ", "_").lower()}.html', 'w') as f:
                    f.write(html_content)
                
                # Parse and extract products
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Multiple selectors for different possible structures
                product_selectors = [
                    # Common e-commerce patterns
                    'a[href*="/product/"]',
                    'a[href*="/products/"]',
                    'a[href*="/shop/"]',
                    'a[href*="/item/"]',
                    
                    # Class-based selectors
                    '.product-item a[href]',
                    '.product-card a[href]',
                    '.product-link',
                    'article.product a[href]',
                    'div.product a[href]',
                    
                    # Specific Bozita patterns (guessing)
                    'a[href*="bozita.com"][href*="dog"]',
                    '.product-grid-item a',
                    '.collection-item a',
                    
                    # Data attributes
                    '[data-product-url]',
                    '[data-product-link]',
                    'a[data-product]'
                ]
                
                for selector in product_selectors:
                    try:
                        links = soup.select(selector)
                        for link in links:
                            href = link.get('href') or link.get('data-product-url') or link.get('data-product-link')
                            if href and '/dog' in href.lower():
                                # Make absolute URL
                                if href.startswith('/'):
                                    product_url = base_url + href
                                elif href.startswith('http'):
                                    product_url = href
                                else:
                                    product_url = base_url + '/' + href
                                
                                # Filter for actual products
                                if any(x in product_url.lower() for x in ['product', 'item', '/dog-food/', '/treats/']):
                                    all_products.add(product_url)
                    except Exception as e:
                        print(f"  Selector {selector} error: {e}")
                
                print(f"  ✓ Found {len(all_products)} unique products so far")
                
                # Also try to find JSON-LD structured data
                json_ld_scripts = soup.find_all('script', type='application/ld+json')
                for script in json_ld_scripts:
                    try:
                        data = json.loads(script.string)
                        if '@graph' in data:
                            for item in data['@graph']:
                                if item.get('@type') == 'Product' and item.get('url'):
                                    all_products.add(item['url'])
                        elif data.get('@type') == 'Product' and data.get('url'):
                            all_products.add(data['url'])
                    except:
                        pass
                
                # Check for AJAX data in script tags
                for script in soup.find_all('script'):
                    if script.string and 'products' in script.string.lower():
                        # Try to extract URLs from JavaScript
                        import re
                        url_pattern = r'https?://[^\s"\'\]]+/(?:product|dog)[^\s"\'\]]*'
                        urls = re.findall(url_pattern, script.string)
                        for url in urls:
                            if '/dog' in url.lower():
                                all_products.add(url.rstrip(',').rstrip(';'))
                
                if len(all_products) > 0:
                    successful_config = config['name']
                    print(f"  ✅ SUCCESS with {config['name']}!")
                    break
                    
            else:
                print(f"  ✗ Failed: {response.status_code}")
                print(f"  Error: {response.text[:200]}")
                
        except Exception as e:
            print(f"  ✗ Exception: {e}")
    
    print(f"\n{'='*80}")
    print("RESULTS")
    print(f"{'='*80}")
    
    if all_products:
        print(f"✅ Found {len(all_products)} unique product URLs")
        print(f"✅ Successful config: {successful_config}")
        print("\nSample URLs:")
        for url in list(all_products)[:10]:
            print(f"  - {url}")
        
        # Save URLs for harvesting
        with open('bozita_product_urls.txt', 'w') as f:
            for url in all_products:
                f.write(url + '\n')
        print(f"\n✓ Saved {len(all_products)} URLs to bozita_product_urls.txt")
        
        # Now harvest the products
        if len(all_products) > 0:
            print(f"\n{'='*80}")
            print("HARVESTING PRODUCTS")
            print(f"{'='*80}")
            
            from scrapingbee_harvester import ScrapingBeeHarvester
            from pathlib import Path
            
            harvester = ScrapingBeeHarvester('bozita', Path('profiles/manufacturers/bozita.yaml'))
            
            # Harvest up to 20 products
            product_list = list(all_products)[:20]
            harvest_stats = harvester.harvest_products(product_list)
            
            print(f"\n✓ Harvested {harvest_stats['snapshots_created']} products")
            print(f"✓ API credits used: {harvester.stats['api_credits_used']}")
            
    else:
        print("❌ No products found despite trying multiple configurations")
        print("\nThe site may be using:")
        print("- Server-side rendering only")
        print("- Advanced bot detection")
        print("- IP-based blocking")
        print("- Requires login/authentication")

if __name__ == "__main__":
    fetch_bozita_with_enhanced_js()