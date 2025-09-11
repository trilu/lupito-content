#!/usr/bin/env python3
"""Test ScrapingBee with simplified configuration"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_scrapingbee():
    api_key = os.getenv('SCRAPING_BEE')
    
    # Test with Cotswold homepage first
    test_url = 'https://www.cotswoldraw.com/'
    
    params = {
        'api_key': api_key,
        'url': test_url,
        'render_js': 'true',
        'premium_proxy': 'true',
        'country_code': 'gb'
    }
    
    print(f"Testing ScrapingBee with: {test_url}")
    print(f"Parameters: {params}")
    
    try:
        response = requests.get(
            'https://app.scrapingbee.com/api/v1/',
            params=params,
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print(f"Success! Response size: {len(response.content)} bytes")
            
            # Save to file for inspection
            with open('test_scrapingbee_output.html', 'w') as f:
                f.write(response.text)
            print("Saved to test_scrapingbee_output.html")
            
            # Check if we got product links
            if 'product' in response.text.lower():
                print("✓ Found 'product' in response")
            if 'collections/dog-food' in response.text:
                print("✓ Page loaded correctly")
                
        else:
            print(f"Error: {response.text[:500]}")
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_scrapingbee()