#!/usr/bin/env python3
"""
Debug ScrapingBee for a single Zooplus product page
Identify exactly what we're getting and what's missing
"""

import os
import re
import json
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

SCRAPINGBEE_API_KEY = os.getenv('SCRAPING_BEE')

def debug_single_product():
    """Debug scraping of a single product with detailed output"""
    
    # Use a specific product URL that should have ingredients
    # This is Rocco Sensitive which should be a simple product
    url = "https://www.zooplus.co.uk/shop/dogs/canned_dog_food/rocco/rocco_sensible/128773"
    
    print("DEBUGGING SINGLE ZOOPLUS PRODUCT")
    print("="*60)
    print(f"URL: {url}")
    print("="*60)
    
    # Try different ScrapingBee configurations
    configurations = [
        {
            "name": "Basic with JS",
            "params": {
                'api_key': SCRAPINGBEE_API_KEY,
                'url': url,
                'render_js': 'true',
                'wait': '3000',
            }
        },
        {
            "name": "Premium with long wait",
            "params": {
                'api_key': SCRAPINGBEE_API_KEY,
                'url': url,
                'render_js': 'true',
                'wait': '8000',  # 8 seconds
                'premium_proxy': 'true',
                'country_code': 'gb',
            }
        },
        {
            "name": "With wait_for selector",
            "params": {
                'api_key': SCRAPINGBEE_API_KEY,
                'url': url,
                'render_js': 'true',
                'wait_for': '.product-description, .ingredients, .composition, [data-testid="product-details"]',
                'timeout': '20000',
                'premium_proxy': 'true',
            }
        },
        {
            "name": "With JavaScript execution",
            "params": {
                'api_key': SCRAPINGBEE_API_KEY,
                'url': url,
                'render_js': 'true',
                'wait': '5000',
                'js_scenario': json.dumps({
                    "instructions": [
                        {"wait": 2000},
                        {"scroll_y": 500},
                        {"wait": 1000},
                        {"scroll_y": 1000},
                        {"wait": 2000},
                        {"evaluate": "document.querySelectorAll('button, [role=\"tab\"]').forEach(el => { if(el.textContent.includes('Composition') || el.textContent.includes('Ingredients') || el.textContent.includes('Details')) el.click(); })"},
                        {"wait": 2000}
                    ]
                }),
                'premium_proxy': 'true',
            }
        }
    ]
    
    for i, config in enumerate(configurations, 1):
        print(f"\n[Attempt {i}] {config['name']}")
        print("-"*40)
        
        try:
            response = requests.get(
                'https://app.scrapingbee.com/api/v1/',
                params=config['params'],
                timeout=60
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                html = response.text
                print(f"Response size: {len(html)} bytes")
                
                # Save HTML for inspection
                filename = f"debug_attempt_{i}.html"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(html)
                print(f"Saved to: {filename}")
                
                # Parse and analyze
                soup = BeautifulSoup(html, 'html.parser')
                
                # Check what we got
                print("\nContent Analysis:")
                
                # 1. Check page title
                title = soup.find('title')
                if title:
                    print(f"  Title: {title.text[:50]}")
                
                # 2. Check for product name
                h1 = soup.find('h1')
                if h1:
                    print(f"  H1: {h1.text.strip()[:50]}")
                
                # 3. Search for key terms
                page_text = soup.get_text()
                
                keywords = ['Composition', 'Ingredients', 'Analytical', 'meat', 'chicken', 'rice']
                print("\n  Keyword presence:")
                for keyword in keywords:
                    if keyword in page_text:
                        print(f"    ✓ '{keyword}' found")
                        # Show context
                        idx = page_text.find(keyword)
                        context = page_text[max(0, idx-50):idx+200].replace('\n', ' ')
                        print(f"      Context: ...{context}...")
                    else:
                        print(f"    ✗ '{keyword}' NOT found")
                
                # 4. Check for specific elements
                print("\n  Element search:")
                
                # Look for any divs with relevant classes
                relevant_classes = ['product', 'description', 'details', 'ingredients', 'composition', 'tab', 'panel']
                for class_name in relevant_classes:
                    elements = soup.find_all(class_=re.compile(class_name, re.I))
                    if elements:
                        print(f"    Found {len(elements)} elements with class containing '{class_name}'")
                
                # Look for data attributes
                data_elements = soup.find_all(attrs={'data-testid': True})
                if data_elements:
                    print(f"    Found {len(data_elements)} elements with data-testid")
                    for elem in data_elements[:5]:
                        print(f"      - data-testid='{elem.get('data-testid')}'")
                
                # 5. Check if it's a product page or category page
                if 'products' in page_text.lower() and 'filter' in page_text.lower():
                    print("\n  ⚠️ This looks like a CATEGORY page (has 'products' and 'filter')")
                else:
                    print("\n  ✓ This looks like a PRODUCT page")
                
                # 6. Try to extract any composition/ingredients
                print("\n  Attempting extraction:")
                
                # Method 1: Direct search
                comp_match = re.search(r'Composition[:\s]+([^.]{20,})', page_text, re.I)
                if comp_match:
                    print(f"    ✓ Found Composition: {comp_match.group(1)[:100]}...")
                
                # Method 2: Look in all text blocks
                text_blocks = soup.find_all(['p', 'div', 'span'])
                for block in text_blocks:
                    text = block.get_text(strip=True)
                    if 'Composition:' in text or 'Ingredients:' in text:
                        print(f"    ✓ Found in {block.name}: {text[:100]}...")
                        break
                
                # Success criteria
                if config['name'] == "With JavaScript execution" and response.status_code == 200:
                    return html  # Return the best attempt
                    
            else:
                print(f"Error: {response.status_code}")
                print(f"Response: {response.text[:200]}")
                
        except Exception as e:
            print(f"Exception: {e}")
    
    return None

def main():
    """Run the debug process"""
    
    result = debug_single_product()
    
    print("\n" + "="*60)
    print("DIAGNOSIS")
    print("="*60)
    
    if result:
        print("✓ Successfully fetched page")
        
        # Final analysis
        if 'Composition' in result:
            print("✓ Ingredients section found in HTML")
            print("\nPROBLEM: Parsing/extraction issue")
            print("SOLUTION: Need better regex patterns or HTML parsing")
        else:
            print("✗ Ingredients section NOT in HTML")
            print("\nPROBLEM: Content loaded dynamically after page load")
            print("SOLUTION: Need to:")
            print("  1. Wait longer for AJAX to complete")
            print("  2. Click on tabs/accordions to reveal content")
            print("  3. Use different URL parameters")
            print("  4. Or use browser automation (Selenium/Playwright)")
    else:
        print("✗ Failed to fetch page properly")
        print("\nPROBLEM: ScrapingBee configuration or Zooplus blocking")
        print("SOLUTION: Try different proxy locations or user agents")
    
    print("\nPlease check the saved HTML files (debug_attempt_*.html) to see what we're getting.")

if __name__ == "__main__":
    main()