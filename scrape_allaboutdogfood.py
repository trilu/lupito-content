#!/usr/bin/env python3
"""
Advanced scraper for allaboutdogfood.co.uk using ScrapingBee
Heavy JavaScript/AJAX site with anti-bot protection
"""

import os
import time
import requests
from bs4 import BeautifulSoup
import json
from dotenv import load_dotenv
from pathlib import Path
import re

load_dotenv()

class AllAboutDogFoodScraper:
    def __init__(self):
        self.api_key = os.getenv('SCRAPING_BEE')
        self.base_url = 'https://www.allaboutdogfood.co.uk'
        self.products = []
        self.session_data = {}
        
    def fetch_page_with_scrapingbee(self, page_num=1):
        """Fetch a page with maximum anti-bot bypass settings"""
        
        url = f'{self.base_url}/the-dog-food-directory'
        
        # Maximum protection settings for ScrapingBee
        params = {
            'api_key': self.api_key,
            'url': url,
            'render_js': 'true',
            'premium_proxy': 'true',  # Premium proxy for better success
            'stealth_proxy': 'true',  # Stealth mode to avoid detection
            'country_code': 'gb',     # UK proxy since it's a UK site
            'wait': '15000',          # 15 second wait as requested
            'wait_for': 'networkidle', # Wait for all network activity to finish
            'block_ads': 'true',
            'block_resources': 'false',  # Keep resources for full JS execution
            'return_page_source': 'true',
            'screenshot': 'false',
            'device': 'desktop',
            'window_width': '1920',
            'window_height': '1080',
        }
        
        # Add JavaScript scenario to handle pagination and scrolling
        if page_num > 1:
            # For pages after 1, we need to navigate via JavaScript
            # Modify URL to include page parameter
            params['url'] = f"{url}?page={page_num}"
            js_scenario = {
                "instructions": [
                    {"wait": 5000},
                    {"scroll": {"y": 500}},
                    {"wait": 2000},
                    {"scroll": {"y": 1000}},
                    {"wait": 2000},
                    {"scroll": {"y": 1500}},
                    {"wait": 3000}
                ]
            }
            params['js_scenario'] = json.dumps(js_scenario)
        else:
            # For first page, just scroll to load content
            js_scenario = {
                "instructions": [
                    {"wait": 5000},
                    {"scroll": {"y": 500}},
                    {"wait": 2000},
                    {"scroll": {"y": 1000}},
                    {"wait": 2000},
                    {"scroll": {"y": 1500}},
                    {"wait": 2000}
                ]
            }
            params['js_scenario'] = json.dumps(js_scenario)
        
        print(f"\n{'='*60}")
        print(f"Fetching page {page_num} with ScrapingBee (maximum protection)")
        print(f"{'='*60}")
        print(f"URL: {url}")
        print(f"Settings: Premium proxy, Stealth mode, 15s wait, UK location")
        
        try:
            response = requests.get(
                'https://app.scrapingbee.com/api/v1/',
                params=params,
                timeout=90  # Longer timeout for heavy JS
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"✓ Page {page_num} fetched successfully")
                print(f"Response size: {len(response.text)} bytes")
                
                # Save HTML for debugging
                with open(f'allaboutdogfood_page_{page_num}.html', 'w', encoding='utf-8') as f:
                    f.write(response.text)
                
                return response.text
            else:
                print(f"✗ Failed: {response.status_code}")
                print(f"Error: {response.text[:500]}")
                return None
                
        except Exception as e:
            print(f"✗ Exception: {e}")
            return None
    
    def extract_product_links(self, html):
        """Extract product links from the page"""
        soup = BeautifulSoup(html, 'html.parser')
        products = []
        
        # Multiple selectors for finding product links
        selectors = [
            'a[href*="/dog-food-reviews/"]',
            '.product-item a',
            '.food-item a',
            '[data-product] a',
            '.directory-item a',
            'article a[href*="/reviews/"]',
            'div.item a[href*="/dog-food"]'
        ]
        
        seen_urls = set()
        
        for selector in selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href', '')
                if href and '/dog-food-reviews/' in href:
                    # Make absolute URL
                    if href.startswith('/'):
                        full_url = self.base_url + href
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        full_url = self.base_url + '/' + href
                    
                    # Clean URL
                    full_url = full_url.split('#')[0].split('?')[0]
                    
                    if full_url not in seen_urls and 'allaboutdogfood.co.uk' in full_url:
                        seen_urls.add(full_url)
                        
                        # Try to extract product name
                        product_name = link.get_text(strip=True) or 'Unknown'
                        if not product_name or product_name == 'Unknown':
                            # Try to get from URL
                            product_name = href.split('/')[-1].replace('-', ' ').title()
                        
                        products.append({
                            'url': full_url,
                            'name': product_name
                        })
        
        return products
    
    def get_total_pages(self, html):
        """Try to extract total number of pages"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Look for pagination info
        patterns = [
            r'Page:\s*\d+\s*of\s*(\d+)',
            r'(\d+)\s*pages',
            r'page.*?(\d+)',
        ]
        
        text = soup.get_text()
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                try:
                    return int(match.group(1))
                except:
                    pass
        
        # Default to 88 as mentioned
        return 88
    
    def scrape_all_pages(self, max_pages=None):
        """Scrape all pages to get product links"""
        all_products = []
        
        # Start with page 1
        html = self.fetch_page_with_scrapingbee(1)
        if not html:
            print("Failed to fetch first page")
            return []
        
        # Extract products from first page
        products = self.extract_product_links(html)
        all_products.extend(products)
        print(f"Found {len(products)} products on page 1")
        
        # Get total pages
        total_pages = self.get_total_pages(html)
        if max_pages:
            total_pages = min(total_pages, max_pages)
        
        print(f"\nTotal pages to scrape: {total_pages}")
        
        # Scrape remaining pages
        for page in range(2, total_pages + 1):
            print(f"\n{'='*40}")
            print(f"Processing page {page}/{total_pages}")
            print(f"{'='*40}")
            
            # Wait between requests to avoid blocking
            print("Waiting 2 seconds before next request...")
            time.sleep(2)
            
            html = self.fetch_page_with_scrapingbee(page)
            if html:
                products = self.extract_product_links(html)
                all_products.extend(products)
                print(f"Found {len(products)} products on page {page}")
                print(f"Total products so far: {len(all_products)}")
            else:
                print(f"Failed to fetch page {page}, continuing...")
            
            # Save progress periodically
            if page % 10 == 0:
                self.save_products(all_products)
        
        return all_products
    
    def save_products(self, products):
        """Save product list to file"""
        # Save as JSON
        with open('allaboutdogfood_products.json', 'w') as f:
            json.dump(products, f, indent=2)
        
        # Save URLs only
        with open('allaboutdogfood_urls.txt', 'w') as f:
            for product in products:
                f.write(product['url'] + '\n')
        
        print(f"\n✓ Saved {len(products)} products to files")
    
    def test_first_pages(self):
        """Test with first 3 pages"""
        print("="*80)
        print("TESTING ALLABOUTDOGFOOD.CO.UK SCRAPER")
        print("Testing with first 3 pages")
        print("="*80)
        
        products = self.scrape_all_pages(max_pages=3)
        
        if products:
            self.save_products(products)
            
            print("\n" + "="*80)
            print("TEST RESULTS")
            print("="*80)
            print(f"✓ Found {len(products)} products in first 3 pages")
            print("\nSample products:")
            for product in products[:10]:
                print(f"  - {product['name'][:50]}: {product['url'][:60]}...")
            
            print(f"\n✓ Full list saved to allaboutdogfood_products.json")
            print(f"✓ URLs saved to allaboutdogfood_urls.txt")
            
            return True
        else:
            print("\n✗ Failed to scrape products")
            return False

def main():
    """Main function"""
    scraper = AllAboutDogFoodScraper()
    
    # Test with first 3 pages
    success = scraper.test_first_pages()
    
    if success:
        print("\n" + "="*80)
        print("NEXT STEPS")
        print("="*80)
        print("1. Review the extracted products")
        print("2. If successful, run full scrape with scraper.scrape_all_pages()")
        print("3. This will take ~3 minutes per page (88 pages = ~4.5 hours)")
        print("4. Consider running in batches to avoid issues")

if __name__ == "__main__":
    main()