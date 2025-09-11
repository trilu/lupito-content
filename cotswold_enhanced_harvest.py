#!/usr/bin/env python3
"""
Enhanced Cotswold Harvester with Maximum Anti-Bot Bypass
Uses all available ScrapingBee features to bypass CloudFlare and other protections
"""

import os
import time
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import json
from pathlib import Path
from scrapingbee_harvester import ScrapingBeeHarvester

load_dotenv()

def discover_cotswold_with_max_protection():
    """Try Cotswold with maximum anti-bot protection bypass"""
    
    api_key = os.getenv('SCRAPING_BEE')
    base_url = 'https://www.cotswoldraw.com'
    
    print("="*80)
    print("COTSWOLD ENHANCED HARVEST - MAXIMUM PROTECTION BYPASS")
    print("="*80)
    
    # Different configurations with increasing bypass strength
    configs = [
        {
            'name': 'Stealth Browser Mode',
            'params': {
                'api_key': api_key,
                'url': f'{base_url}/collections/all',
                'render_js': 'true',
                'premium_proxy': 'true',
                'stealth_proxy': 'true',  # Stealth mode to avoid detection
                'country_code': 'gb',
                'wait': '5000',
                'wait_for': 'networkidle',
                'block_ads': 'true',
                'screenshot': 'false',
                'return_page_source': 'true',  # Get full rendered HTML
                'js_scenario': json.dumps({
                    "instructions": [
                        {"wait": 3000},
                        {"scroll": {"y": 500}},
                        {"wait": 2000},
                        {"scroll": {"y": 1000}},
                        {"wait": 2000},
                        {"evaluate": "document.querySelectorAll('a').length"},  # Trigger JS execution
                        {"wait": 1000}
                    ]
                })
            }
        },
        {
            'name': 'CloudFlare Bypass Special',
            'params': {
                'api_key': api_key,
                'url': f'{base_url}/collections/dog-food',
                'render_js': 'true',
                'premium_proxy': 'true',
                'stealth_proxy': 'true',
                'country_code': 'gb',
                'wait': '10000',  # Longer wait for CloudFlare
                'wait_for': 'domcontentloaded',
                'block_ads': 'true',
                'cookies': 'accept_all',  # Accept all cookies automatically
                'js_scenario': json.dumps({
                    "instructions": [
                        {"wait": 5000},  # Wait for CloudFlare check
                        {"wait_for_selector": "body"},
                        {"evaluate": "window.scrollTo(0, document.body.scrollHeight)"},
                        {"wait": 3000}
                    ]
                })
            }
        },
        {
            'name': 'Residential Proxy + User Agent',
            'params': {
                'api_key': api_key,
                'url': f'{base_url}/collections/raw-dog-food',
                'render_js': 'true',
                'premium_proxy': 'true',
                'stealth_proxy': 'true',
                'residential_proxy': 'true',  # Use residential IPs
                'country_code': 'gb',
                'wait': '7000',
                'wait_for': '.product, .product-item, article',
                'block_ads': 'true',
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'device': 'desktop',
                'window_width': '1920',
                'window_height': '1080'
            }
        },
        {
            'name': 'Session Mode',
            'params': {
                'api_key': api_key,
                'url': f'{base_url}',  # Start from homepage
                'render_js': 'true',
                'premium_proxy': 'true',
                'stealth_proxy': 'true',
                'country_code': 'gb',
                'wait': '5000',
                'session_id': 'cotswold_session_1',  # Maintain session
                'js_scenario': json.dumps({
                    "instructions": [
                        {"wait": 3000},
                        {"click": "a[href*='collection'], a[href*='dog']"},  # Try to click dog food link
                        {"wait": 5000},
                        {"wait_for_selector": ".product"},
                        {"evaluate": "Array.from(document.querySelectorAll('a[href*=\"/products/\"]')).map(a => a.href)"}
                    ]
                })
            }
        },
        {
            'name': 'Direct Product Pages',
            'params': {
                'api_key': api_key,
                'url': f'{base_url}/products/',  # Try direct products path
                'render_js': 'true',
                'premium_proxy': 'true',
                'stealth_proxy': 'true',
                'country_code': 'gb',
                'wait': '5000',
                'extract_rules': json.dumps({
                    "products": {
                        "selector": "a[href*='/products/']",
                        "type": "list",
                        "output": "@href"
                    }
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
            # Add timeout handling
            response = requests.get(
                'https://app.scrapingbee.com/api/v1/',
                params=config['params'],
                timeout=60
            )
            
            print(f"Status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                html_content = response.text
                print(f"Response size: {len(html_content)} bytes")
                
                # Check if we hit CloudFlare
                if 'cloudflare' in html_content.lower() or 'checking your browser' in html_content.lower():
                    print("  ⚠️ CloudFlare detected, trying next config...")
                    continue
                
                # Save for debugging
                with open(f'cotswold_{config["name"].replace(" ", "_").lower()}.html', 'w') as f:
                    f.write(html_content)
                
                # Parse and extract products
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Multiple selectors for Shopify sites
                product_selectors = [
                    'a[href*="/products/"]',
                    'a[href*="/collections/"][href*="/products/"]',
                    '.product-item a[href]',
                    '.product-card a[href]',
                    '.product__link',
                    'article.product-card a',
                    '.collection-product-card a',
                    '.product-grid-item a',
                    '[data-product-handle]',
                    'a.grid-product__link'
                ]
                
                for selector in product_selectors:
                    try:
                        links = soup.select(selector)
                        for link in links:
                            href = link.get('href', '')
                            if href and '/products/' in href:
                                if href.startswith('/'):
                                    product_url = base_url + href
                                elif href.startswith('http'):
                                    product_url = href
                                else:
                                    product_url = base_url + '/' + href
                                
                                all_products.add(product_url.split('?')[0])  # Remove query params
                    except Exception as e:
                        pass
                
                print(f"  ✓ Found {len(all_products)} unique products so far")
                
                # Try to find JSON data
                scripts = soup.find_all('script', type='application/json')
                for script in scripts:
                    try:
                        data = json.loads(script.string)
                        if 'products' in str(data):
                            # Extract product URLs from JSON
                            import re
                            urls = re.findall(r'"/products/[^"]+', str(data))
                            for url in urls:
                                all_products.add(base_url + url.strip('"'))
                    except:
                        pass
                
                # Check window.meta for Shopify data
                meta_scripts = soup.find_all('script')
                for script in meta_scripts:
                    if script.string and 'window.meta' in script.string:
                        import re
                        urls = re.findall(r'/products/[^\s"\']+', script.string)
                        for url in urls:
                            all_products.add(base_url + url)
                
                if len(all_products) > 0:
                    successful_config = config['name']
                    print(f"  ✅ SUCCESS with {config['name']}!")
                    
                    # Try to get more pages if successful
                    if len(all_products) < 20:
                        # Try pagination
                        for page in [2, 3, 4]:
                            page_url = config['params']['url'] + f'?page={page}'
                            config['params']['url'] = page_url
                            
                            try:
                                page_response = requests.get(
                                    'https://app.scrapingbee.com/api/v1/',
                                    params=config['params'],
                                    timeout=30
                                )
                                
                                if page_response.status_code == 200:
                                    page_soup = BeautifulSoup(page_response.text, 'html.parser')
                                    for selector in product_selectors:
                                        links = page_soup.select(selector)
                                        for link in links:
                                            href = link.get('href', '')
                                            if href and '/products/' in href:
                                                if href.startswith('/'):
                                                    all_products.add(base_url + href.split('?')[0])
                                                    
                                    print(f"    Page {page}: {len(all_products)} total products")
                            except:
                                break
                    
                    if len(all_products) >= 10:
                        break  # We found enough products
                    
            elif response.status_code == 403:
                print(f"  ✗ Access denied (403)")
            elif response.status_code == 429:
                print(f"  ✗ Rate limited (429)")
            else:
                print(f"  ✗ Failed: {response.status_code}")
                print(f"  Error: {response.text[:200]}")
                
        except Exception as e:
            print(f"  ✗ Exception: {e}")
    
    print(f"\n{'='*80}")
    print("DISCOVERY RESULTS")
    print(f"{'='*80}")
    
    if all_products:
        print(f"✅ Found {len(all_products)} unique product URLs")
        print(f"✅ Successful config: {successful_config}")
        print("\nSample URLs:")
        for url in list(all_products)[:10]:
            print(f"  - {url}")
        
        # Save URLs
        with open('cotswold_product_urls.txt', 'w') as f:
            for url in all_products:
                f.write(url + '\n')
        print(f"\n✓ Saved {len(all_products)} URLs to cotswold_product_urls.txt")
        
        # Now harvest the products
        if len(all_products) > 0:
            print(f"\n{'='*80}")
            print("HARVESTING PRODUCTS")
            print(f"{'='*80}")
            
            harvester = ScrapingBeeHarvester('cotswold', Path('profiles/manufacturers/cotswold.yaml'))
            
            # Use the config that worked
            if successful_config:
                # Apply the successful config settings
                harvester.stealth_mode = True
                harvester.residential_proxy = 'residential' in successful_config.lower()
            
            # Harvest products
            product_list = list(all_products)[:30]  # Limit to 30 for testing
            harvest_stats = harvester.harvest_products(product_list)
            
            print(f"\n✓ Harvested {harvest_stats['snapshots_created']} products")
            print(f"✓ Failed: {harvest_stats['failures']}")
            print(f"✓ API credits used: {harvester.stats['api_credits_used']}")
            
            return True
            
    else:
        print("❌ No products found despite trying all configurations")
        print("\nPossible reasons:")
        print("1. CloudFlare protection is too strong")
        print("2. Site requires authentication")
        print("3. Geographic restrictions")
        print("4. IP already blocked")
        
        return False

if __name__ == "__main__":
    success = discover_cotswold_with_max_protection()
    
    if not success:
        print("\n" + "="*80)
        print("ALTERNATIVE APPROACH NEEDED")
        print("="*80)
        print("\nRecommendations:")
        print("1. Try with a different ScrapingBee account")
        print("2. Use browser automation (Playwright/Selenium)")
        print("3. Check if site has an API or sitemap.xml")
        print("4. Contact brand directly for data access")