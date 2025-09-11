#!/usr/bin/env python3
"""
Harvest Briantos products using ScrapingBee with enhanced settings
Briantos is a German brand, so we'll use German proxy and settings
"""

import os
import time
import requests
from pathlib import Path
from scrapingbee_harvester import ScrapingBeeHarvester
from bs4 import BeautifulSoup
import json
from dotenv import load_dotenv

load_dotenv()

def discover_briantos_products():
    """Discover Briantos product URLs using ScrapingBee"""
    
    api_key = os.getenv('SCRAPING_BEE')
    base_url = 'https://www.briantos.de'
    
    print("="*80)
    print("DISCOVERING BRIANTOS PRODUCTS WITH SCRAPINGBEE")
    print("="*80)
    
    # Try different pages/categories
    urls_to_try = [
        f'{base_url}/hunde/hundefutter',
        f'{base_url}/hunde/trockenfutter',
        f'{base_url}/produkte',
        f'{base_url}/shop',
        base_url
    ]
    
    all_products = set()
    
    for url in urls_to_try:
        print(f"\n{'='*60}")
        print(f"Trying: {url}")
        print(f"{'='*60}")
        
        # ScrapingBee params with German settings
        params = {
            'api_key': api_key,
            'url': url,
            'render_js': 'true',
            'premium_proxy': 'true',
            'stealth_proxy': 'true',
            'country_code': 'de',  # German proxy
            'wait': '10000',
            'wait_for': 'networkidle',
            'block_ads': 'true',
            'return_page_source': 'true',
        }
        
        # Add JavaScript scenario to scroll and load products
        js_scenario = {
            "instructions": [
                {"wait": 3000},
                {"scroll": {"y": 500}},
                {"wait": 2000},
                {"scroll": {"y": 1000}},
                {"wait": 2000},
                {"scroll": {"y": 1500}},
                {"wait": 2000}
            ]
        }
        params['js_scenario'] = json.dumps(js_scenario)
        
        try:
            response = requests.get(
                'https://app.scrapingbee.com/api/v1/',
                params=params,
                timeout=60
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                html = response.text
                print(f"Response size: {len(html)} bytes")
                
                # Save for debugging
                with open(f'briantos_{url.split("/")[-1]}.html', 'w', encoding='utf-8') as f:
                    f.write(html)
                
                # Parse for product links
                soup = BeautifulSoup(html, 'html.parser')
                
                # Multiple selectors for finding products
                selectors = [
                    'a[href*="/produkt/"]',
                    'a[href*="/product/"]',
                    'a[href*="/artikel/"]',
                    '.product-item a',
                    '.product-card a',
                    '.product-link',
                    'article a[href]',
                    '[data-product] a'
                ]
                
                for selector in selectors:
                    links = soup.select(selector)
                    for link in links:
                        href = link.get('href', '')
                        if href:
                            if href.startswith('/'):
                                product_url = base_url + href
                            elif not href.startswith('http'):
                                product_url = base_url + '/' + href
                            else:
                                product_url = href
                            
                            # Clean and add
                            product_url = product_url.split('?')[0]
                            if 'briantos.de' in product_url:
                                all_products.add(product_url)
                
                print(f"Found {len(all_products)} products so far")
                
                # Also look for product data in JavaScript
                scripts = soup.find_all('script')
                for script in scripts:
                    if script.string and 'product' in script.string.lower():
                        # Try to extract URLs from JavaScript
                        import re
                        urls = re.findall(r'["\'](/produkt/[^"\']+)["\']', script.string)
                        for url in urls:
                            all_products.add(base_url + url)
                
            else:
                print(f"Failed with status {response.status_code}")
                if response.status_code == 403:
                    print("Access denied - site may be blocking ScrapingBee")
                
        except Exception as e:
            print(f"Error: {e}")
        
        # Wait between requests
        time.sleep(2)
    
    return list(all_products)

def harvest_briantos_with_scrapingbee():
    """Main function to harvest Briantos"""
    
    print("\n" + "="*80)
    print("BRIANTOS HARVEST WITH SCRAPINGBEE")
    print("="*80)
    
    # First, discover products
    product_urls = discover_briantos_products()
    
    if not product_urls:
        print("\n❌ No products discovered. Briantos may still be blocking.")
        print("Trying alternative approach...")
        
        # Try known product patterns
        print("\nTrying known URL patterns...")
        test_urls = [
            'https://www.briantos.de/produkt/briantos-adult-huhn-reis',
            'https://www.briantos.de/produkt/briantos-adult-lamm-reis',
            'https://www.briantos.de/produkt/briantos-junior',
        ]
        
        # Test if we can access individual products
        harvester = ScrapingBeeHarvester('briantos', Path('profiles/manufacturers/briantos.yaml'))
        harvester.stealth_mode = True
        
        for url in test_urls:
            print(f"\nTesting: {url}")
            html = harvester.fetch_with_scrapingbee(url)
            if html:
                print(f"✓ Successfully fetched {url}")
                product_urls.append(url)
            else:
                print(f"✗ Failed to fetch {url}")
        
        if not product_urls:
            print("\n❌ Briantos is still heavily protected against ScrapingBee")
            return False
    
    # Save discovered URLs
    if product_urls:
        with open('briantos_product_urls.txt', 'w') as f:
            for url in product_urls:
                f.write(url + '\n')
        
        print(f"\n✓ Found {len(product_urls)} product URLs")
        print("✓ Saved to briantos_product_urls.txt")
        
        # Now harvest products
        print(f"\n{'='*80}")
        print("HARVESTING PRODUCTS")
        print(f"{'='*80}")
        
        harvester = ScrapingBeeHarvester('briantos', Path('profiles/manufacturers/briantos.yaml'))
        harvester.stealth_mode = True
        harvester.country_code = 'de'  # Use German proxy
        
        # Harvest products (limit to 10 for testing)
        test_urls = product_urls[:10] if len(product_urls) > 10 else product_urls
        
        harvest_stats = harvester.harvest_products(test_urls)
        
        print(f"\n{'='*80}")
        print("HARVEST RESULTS")
        print(f"{'='*80}")
        print(f"✓ Products harvested: {harvest_stats.get('snapshots_created', 0)}")
        print(f"✗ Failures: {harvest_stats.get('failures', 0)}")
        print(f"💳 API credits used: {harvester.stats.get('api_credits_used', 0)}")
        
        if harvest_stats.get('snapshots_created', 0) > 0:
            print("\n✅ SUCCESS! Briantos can now be harvested with ScrapingBee")
            print(f"To harvest all {len(product_urls)} products, run:")
            print("  harvester.harvest_products(product_urls)")
            return True
        else:
            print("\n⚠️ Discovery worked but harvesting failed")
            return False
    
    return False

if __name__ == "__main__":
    success = harvest_briantos_with_scrapingbee()
    
    if not success:
        print("\n" + "="*80)
        print("BRIANTOS STILL PROTECTED")
        print("="*80)
        print("Despite ScrapingBee's advanced features, Briantos remains protected.")
        print("Possible reasons:")
        print("1. IP-based blocking specific to cloud providers")
        print("2. Advanced fingerprinting beyond ScrapingBee's stealth mode")
        print("3. Require specific German residential IPs")
        print("4. Cookie/session requirements")