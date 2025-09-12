#!/usr/bin/env python3
"""
Test accessing Zooplus directly without ScrapingBee
To understand the URL structure and redirects
"""

import requests
from bs4 import BeautifulSoup

def test_direct_access():
    """Test what happens when we access Zooplus URLs directly"""
    
    print("TESTING ZOOPLUS URL BEHAVIOR")
    print("="*60)
    
    # Different URL formats to test
    test_urls = [
        # Original URL from our data
        ("Original SKU URL", "https://www.zooplus.co.uk/shop/dogs/canned_dog_food/rocco/rocco_sensible/128773"),
        
        # Try with product ID
        ("Product ID format", "https://www.zooplus.co.uk/shop/product/128773"),
        
        # Try search URL
        ("Search URL", "https://www.zooplus.co.uk/shop/search?q=rocco+sensitive"),
        
        # A simpler product URL
        ("Simple product", "https://www.zooplus.co.uk/shop/dogs/dry_dog_food/royal_canin/128332"),
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-GB,en;q=0.5',
    }
    
    for name, url in test_urls:
        print(f"\n[{name}]")
        print(f"URL: {url}")
        print("-"*40)
        
        try:
            # Don't follow redirects automatically
            response = requests.get(url, headers=headers, allow_redirects=False, timeout=10)
            
            print(f"Status: {response.status_code}")
            
            # Check for redirects
            if response.status_code in [301, 302, 303, 307, 308]:
                redirect_url = response.headers.get('Location', 'No location header')
                print(f"Redirects to: {redirect_url}")
                
                # Follow the redirect
                if redirect_url and redirect_url != 'No location header':
                    final_response = requests.get(redirect_url, headers=headers, timeout=10)
                    print(f"Final status: {final_response.status_code}")
                    print(f"Final URL: {final_response.url}")
                    
                    # Check what we got
                    soup = BeautifulSoup(final_response.text, 'html.parser')
                    title = soup.find('title')
                    if title:
                        print(f"Page title: {title.text[:50]}")
                    
                    # Check if it's a product page
                    if 'product' in final_response.text.lower()[:1000]:
                        print("✓ Contains 'product' in first 1000 chars")
                    if '128773' in final_response.text:
                        print("✓ Contains SKU 128773")
                    if 'rocco' in final_response.text.lower()[:5000]:
                        print("✓ Contains 'rocco' in first 5000 chars")
                        
            elif response.status_code == 200:
                print("Direct 200 OK response")
                
                # Check content
                soup = BeautifulSoup(response.text, 'html.parser')
                title = soup.find('title')
                if title:
                    print(f"Page title: {title.text[:50]}")
                
                # Save a sample
                if '128773' in url:
                    with open('direct_access_test.html', 'w') as f:
                        f.write(response.text[:10000])
                    print("Saved sample to direct_access_test.html")
                    
            else:
                print(f"Unexpected status: {response.status_code}")
                
        except Exception as e:
            print(f"Error: {e}")
    
    print("\n" + "="*60)
    print("CONCLUSION")
    print("="*60)
    print("The URLs might be:")
    print("1. Redirecting to homepage (bot detection)")
    print("2. Using different URL structure now")
    print("3. Requiring cookies/session to access")
    print("4. Blocking automated access")

def test_with_scrapingbee_redirect():
    """Test ScrapingBee with redirect following"""
    print("\n\nTESTING WITH SCRAPINGBEE REDIRECT HANDLING")
    print("="*60)
    
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv('SCRAPING_BEE')
    
    params = {
        'api_key': api_key,
        'url': 'https://www.zooplus.co.uk/shop/dogs/canned_dog_food/rocco/rocco_sensible/128773',
        'render_js': 'false',  # First try without JS to see raw response
        'return_page_source': 'true',
        'premium_proxy': 'true',
        'country_code': 'gb',
        # Add these to handle redirects
        'forward_headers': 'true',
        'custom_google': 'false',
    }
    
    response = requests.get('https://app.scrapingbee.com/api/v1/', params=params, timeout=30)
    
    print(f"ScrapingBee status: {response.status_code}")
    
    if response.status_code == 200:
        # Check response headers if available
        if 'Spb-Original-Status-Code' in response.headers:
            print(f"Original status: {response.headers['Spb-Original-Status-Code']}")
        
        # Check content
        if len(response.text) < 1000:
            print(f"Response is suspiciously short: {len(response.text)} bytes")
            print(f"Content preview: {response.text[:500]}")
        else:
            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.find('title')
            if title:
                print(f"Title: {title.text}")
            
            # Check for product indicators
            if 'rocco' in response.text.lower():
                print("✓ Found 'rocco' in response")
            if '128773' in response.text:
                print("✓ Found SKU in response")
            if 'composition' in response.text.lower():
                print("✓ Found 'composition' in response")

if __name__ == "__main__":
    test_direct_access()
    test_with_scrapingbee_redirect()