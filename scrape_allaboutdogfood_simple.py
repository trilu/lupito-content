#!/usr/bin/env python3
"""
Simplified scraper for allaboutdogfood.co.uk using ScrapingBee
Starting with basic functionality, then we can add complexity
"""

import os
import time
import requests
from bs4 import BeautifulSoup
import json
from dotenv import load_dotenv
import re

load_dotenv()

class AllAboutDogFoodScraper:
    def __init__(self):
        self.api_key = os.getenv('SCRAPING_BEE')
        self.base_url = 'https://www.allaboutdogfood.co.uk'
        self.products = []
        
    def fetch_page_with_scrapingbee(self, page_num=1):
        """Fetch a page with maximum anti-bot bypass settings"""
        
        # Build URL with page parameter
        if page_num == 1:
            url = f'{self.base_url}/the-dog-food-directory'
        else:
            url = f'{self.base_url}/the-dog-food-directory?page={page_num}'
        
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
            'return_page_source': 'true',
            'device': 'desktop',
            'window_width': '1920',
            'window_height': '1080',
        }
        
        print(f"\n{'='*60}")
        print(f"Fetching page {page_num} with ScrapingBee")
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
        
        # Look for any links that might be product reviews
        all_links = soup.find_all('a', href=True)
        
        seen_urls = set()
        
        for link in all_links:
            href = link.get('href', '')
            
            # Check if it's a dog food review link
            if '/dog-food-reviews/' in href or '/reviews/' in href:
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
                    product_name = link.get_text(strip=True)
                    if not product_name:
                        # Try parent element
                        parent = link.find_parent(['div', 'article', 'li'])
                        if parent:
                            product_name = parent.get_text(strip=True)[:100]
                    
                    if not product_name:
                        # Get from URL
                        product_name = href.split('/')[-1].replace('-', ' ').title()
                    
                    products.append({
                        'url': full_url,
                        'name': product_name[:100]  # Limit length
                    })
        
        return products
    
    def test_single_page(self):
        """Test with just the first page"""
        print("="*80)
        print("TESTING ALLABOUTDOGFOOD.CO.UK SCRAPER")
        print("Testing with first page only")
        print("="*80)
        
        html = self.fetch_page_with_scrapingbee(1)
        
        if html:
            # Check what we got
            print("\n" + "="*60)
            print("ANALYZING RESPONSE")
            print("="*60)
            
            # Look for signs we got the right page
            if 'dog food directory' in html.lower():
                print("✓ Found 'dog food directory' in response")
            
            if 'results' in html.lower():
                print("✓ Found 'results' in response")
            
            # Look for pagination
            if 'page' in html.lower() and ('next' in html.lower() or 'previous' in html.lower()):
                print("✓ Found pagination elements")
            
            # Extract products
            products = self.extract_product_links(html)
            
            print(f"\n✓ Found {len(products)} product links")
            
            if products:
                print("\nFirst 10 products found:")
                for i, product in enumerate(products[:10], 1):
                    print(f"{i}. {product['name'][:50]}")
                    print(f"   URL: {product['url'][:70]}...")
                
                # Save products
                with open('allaboutdogfood_products_test.json', 'w') as f:
                    json.dump(products, f, indent=2)
                
                print(f"\n✓ Saved {len(products)} products to allaboutdogfood_products_test.json")
                
                return True
            else:
                print("\n⚠ No products found. The page might be:")
                print("  1. Behind CloudFlare protection")
                print("  2. Using dynamic loading that needs more wait time")
                print("  3. Using different HTML structure than expected")
                print("\nCheck allaboutdogfood_page_1.html for the actual content")
                
                # Show a sample of the HTML to debug
                soup = BeautifulSoup(html, 'html.parser')
                print("\nPage title:", soup.title.string if soup.title else "No title")
                print("\nFirst 500 chars of text content:")
                print(soup.get_text()[:500])
                
                return False
        else:
            print("\n✗ Failed to fetch page")
            return False

def main():
    """Main function"""
    scraper = AllAboutDogFoodScraper()
    
    # Test with single page first
    success = scraper.test_single_page()
    
    if success:
        print("\n" + "="*80)
        print("SUCCESS! Next steps:")
        print("="*80)
        print("1. Review the extracted products")
        print("2. If the structure is correct, we can proceed with multi-page scraping")
        print("3. The full scrape of 88 pages will take ~4-5 hours")

if __name__ == "__main__":
    main()