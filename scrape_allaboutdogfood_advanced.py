#!/usr/bin/env python3
"""
Advanced scraper for allaboutdogfood.co.uk with enhanced JavaScript scenarios
Designed to handle AJAX-loaded content and heavy JavaScript protection
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
        
    def fetch_page_with_advanced_js(self, page_num=1):
        """Fetch with advanced JavaScript scenarios to trigger product loading"""
        
        # Build URL with page parameter
        if page_num == 1:
            url = f'{self.base_url}/the-dog-food-directory'
        else:
            url = f'{self.base_url}/the-dog-food-directory?page={page_num}'
        
        # Maximum protection settings
        params = {
            'api_key': self.api_key,
            'url': url,
            'render_js': 'true',
            'premium_proxy': 'true',
            'stealth_proxy': 'true',
            'country_code': 'gb',
            'wait': '20000',  # Even longer wait
            'block_ads': 'true',
            'return_page_source': 'true',
            'device': 'desktop',
            'window_width': '1920',
            'window_height': '1080',
        }
        
        # Complex JavaScript scenario to trigger AJAX loading
        js_scenario = {
            "instructions": [
                # Initial wait for page load
                {"wait": 5000},
                
                # Scroll to trigger lazy loading
                {"scroll": {"y": 300}},
                {"wait": 2000},
                {"scroll": {"y": 600}},
                {"wait": 2000},
                {"scroll": {"y": 900}},
                {"wait": 3000},
                
                # Try to click any "load more" or similar buttons
                {"click": "button:contains('Load'), button:contains('Show'), button:contains('More'), .load-more, .show-more"},
                {"wait": 3000},
                
                # Scroll more to ensure all content loads
                {"scroll": {"y": 1500}},
                {"wait": 3000},
                {"scroll": {"y": 2000}},
                {"wait": 3000},
                
                # Final scroll to bottom
                {"evaluate": "window.scrollTo(0, document.body.scrollHeight)"},
                {"wait": 5000}
            ]
        }
        params['js_scenario'] = json.dumps(js_scenario)
        
        print(f"\n{'='*60}")
        print(f"Fetching page {page_num} with ADVANCED JavaScript scenarios")
        print(f"{'='*60}")
        print(f"URL: {url}")
        print(f"Settings: Premium proxy, Stealth mode, 20s wait, scrolling + clicking")
        
        try:
            response = requests.get(
                'https://app.scrapingbee.com/api/v1/',
                params=params,
                timeout=120  # Even longer timeout
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"✓ Page {page_num} fetched successfully")
                print(f"Response size: {len(response.text)} bytes")
                
                # Save HTML
                with open(f'allaboutdogfood_advanced_page_{page_num}.html', 'w', encoding='utf-8') as f:
                    f.write(response.text)
                
                return response.text
            else:
                print(f"✗ Failed: {response.status_code}")
                print(f"Error: {response.text[:500]}")
                return None
                
        except Exception as e:
            print(f"✗ Exception: {e}")
            return None
    
    def fetch_with_wait_for_selector(self, page_num=1):
        """Try waiting for specific selectors that indicate products loaded"""
        
        if page_num == 1:
            url = f'{self.base_url}/the-dog-food-directory'
        else:
            url = f'{self.base_url}/the-dog-food-directory?page={page_num}'
        
        # Try different wait_for selectors
        selectors_to_try = [
            '.product-item',
            '.food-item', 
            '.directory-item',
            '[data-product]',
            '.result-item',
            '.food-card',
            'article.product',
            '.listing-item',
            '[class*="product"]',
            '[class*="food"]'
        ]
        
        for selector in selectors_to_try:
            print(f"\n{'='*40}")
            print(f"Trying with wait_for: {selector}")
            print(f"{'='*40}")
            
            params = {
                'api_key': self.api_key,
                'url': url,
                'render_js': 'true',
                'premium_proxy': 'true',
                'stealth_proxy': 'true',
                'country_code': 'gb',
                'wait_for': selector,  # Wait for specific selector
                'wait': '20000',  # Max wait time
                'block_ads': 'true',
                'return_page_source': 'true',
            }
            
            try:
                response = requests.get(
                    'https://app.scrapingbee.com/api/v1/',
                    params=params,
                    timeout=90
                )
                
                if response.status_code == 200:
                    print(f"✓ Success with selector: {selector}")
                    
                    # Check if we got products
                    if self.check_for_products(response.text):
                        print(f"✓✓ FOUND PRODUCTS with selector: {selector}")
                        return response.text
                    else:
                        print(f"⚠ No products found with this selector")
                else:
                    print(f"✗ Failed with {response.status_code}")
                    
            except Exception as e:
                print(f"✗ Error: {str(e)[:100]}")
            
            # Small delay between attempts
            time.sleep(1)
        
        return None
    
    def check_for_products(self, html):
        """Quick check if HTML contains product data"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Look for any links that might be products
        product_links = []
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if any(keyword in href for keyword in ['/reviews/', '/dog-food/', '/product/', '/brand/']):
                product_links.append(href)
        
        # Also check for text indicators
        text = soup.get_text().lower()
        has_product_text = any(word in text for word in ['rating', 'review', 'price', 'ingredients', 'protein', 'fat'])
        
        print(f"  Found {len(product_links)} potential product links")
        print(f"  Has product text: {has_product_text}")
        
        return len(product_links) > 5 or has_product_text
    
    def extract_all_links(self, html):
        """Extract ALL links from the page for analysis"""
        soup = BeautifulSoup(html, 'html.parser')
        all_links = []
        
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            if href and not href.startswith('#'):
                # Make absolute URL
                if href.startswith('/'):
                    full_url = self.base_url + href
                elif not href.startswith('http'):
                    full_url = self.base_url + '/' + href
                else:
                    full_url = href
                
                all_links.append({
                    'url': full_url,
                    'text': text[:100],
                    'original_href': href
                })
        
        return all_links
    
    def test_advanced_scraping(self):
        """Test with advanced techniques"""
        print("="*80)
        print("ADVANCED TESTING - ALLABOUTDOGFOOD.CO.UK")
        print("="*80)
        
        # Test 1: Advanced JS scenarios
        print("\n[TEST 1] Advanced JavaScript Scenarios")
        html = self.fetch_page_with_advanced_js(1)
        
        if html:
            links = self.extract_all_links(html)
            print(f"\n✓ Found {len(links)} total links")
            
            # Filter for potential product links
            product_links = [l for l in links if any(k in l['url'] for k in ['/reviews/', '/dog-food/', '/product/'])]
            print(f"✓ Found {len(product_links)} potential product links")
            
            if product_links:
                print("\nFirst 10 product links:")
                for link in product_links[:10]:
                    print(f"  - {link['text'][:40]}: {link['url'][:60]}...")
                
                # Save results
                with open('allaboutdogfood_advanced_links.json', 'w') as f:
                    json.dump(product_links, f, indent=2)
                
                return True
        
        # Test 2: Wait for selector
        print("\n[TEST 2] Wait for Specific Selectors")
        html = self.fetch_with_wait_for_selector(1)
        
        if html:
            links = self.extract_all_links(html)
            product_links = [l for l in links if any(k in l['url'] for k in ['/reviews/', '/dog-food/', '/product/'])]
            
            if product_links:
                print(f"\n✓✓ SUCCESS! Found {len(product_links)} product links")
                
                with open('allaboutdogfood_selector_links.json', 'w') as f:
                    json.dump(product_links, f, indent=2)
                
                return True
        
        print("\n" + "="*60)
        print("ANALYSIS")
        print("="*60)
        print("The site may be:")
        print("1. Using advanced anti-bot protection (Cloudflare Enterprise)")
        print("2. Loading content via WebSocket or Server-Sent Events")
        print("3. Requiring specific cookies or session state")
        print("4. Using fingerprinting to detect automated browsers")
        print("\nRecommendations:")
        print("- Try using Playwright or Selenium for real browser automation")
        print("- Check if there's an API endpoint we can access directly")
        print("- Look for sitemap.xml or robots.txt for alternative URLs")
        
        return False

def main():
    """Main function"""
    scraper = AllAboutDogFoodScraper()
    
    # Test with advanced techniques
    success = scraper.test_advanced_scraping()
    
    if success:
        print("\n" + "="*80)
        print("SUCCESS!")
        print("="*80)
        print("Found product links. Check the JSON files for results.")
    else:
        print("\n" + "="*80)
        print("ALTERNATIVE APPROACH NEEDED")
        print("="*80)
        print("ScrapingBee may not be sufficient for this site.")
        print("Consider browser automation or finding API endpoints.")

if __name__ == "__main__":
    main()