#!/usr/bin/env python3
"""
Diagnose why we're getting HTTP 400 errors
Test different approaches to bypass blocking
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

SCRAPINGBEE_API_KEY = os.getenv('SCRAPING_BEE')

def test_scraping_approaches():
    """Test different scraping configurations"""
    
    # Test URL that worked before
    test_url = "https://www.zooplus.com/shop/dogs/dry_dog_food/royal_canin_size/royal_canin_medium/128332"
    
    print("🔍 DIAGNOSING SCRAPING ISSUES")
    print("=" * 60)
    print(f"Test URL: {test_url}")
    print()
    
    configs = [
        {
            "name": "Basic (No JS)",
            "params": {
                'api_key': SCRAPINGBEE_API_KEY,
                'url': test_url,
                'render_js': 'false',
                'return_page_source': 'true'
            }
        },
        {
            "name": "Basic + Premium Proxy",
            "params": {
                'api_key': SCRAPINGBEE_API_KEY,
                'url': test_url,
                'render_js': 'false',
                'premium_proxy': 'true',
                'return_page_source': 'true'
            }
        },
        {
            "name": "JavaScript Rendering",
            "params": {
                'api_key': SCRAPINGBEE_API_KEY,
                'url': test_url,
                'render_js': 'true',
                'wait': '3000',
                'return_page_source': 'true'
            }
        },
        {
            "name": "Stealth Mode",
            "params": {
                'api_key': SCRAPINGBEE_API_KEY,
                'url': test_url,
                'render_js': 'true',
                'premium_proxy': 'true',
                'stealth_proxy': 'true',
                'country_code': 'us',
                'wait': '3000',
                'return_page_source': 'true'
            }
        },
        {
            "name": "Different Country (Germany)",
            "params": {
                'api_key': SCRAPINGBEE_API_KEY,
                'url': test_url.replace('.com', '.de'),
                'render_js': 'true',
                'premium_proxy': 'true',
                'stealth_proxy': 'true',
                'country_code': 'de',
                'wait': '3000',
                'return_page_source': 'true'
            }
        },
        {
            "name": "UK Site",
            "params": {
                'api_key': SCRAPINGBEE_API_KEY,
                'url': test_url.replace('.com', '.co.uk'),
                'render_js': 'true',
                'premium_proxy': 'true',
                'stealth_proxy': 'true',
                'country_code': 'gb',
                'wait': '3000',
                'return_page_source': 'true'
            }
        }
    ]
    
    for i, config in enumerate(configs, 1):
        print(f"[{i}/6] Testing: {config['name']}")
        print(f"URL: {config['params']['url']}")
        
        try:
            response = requests.get(
                'https://app.scrapingbee.com/api/v1/',
                params=config['params'],
                timeout=60
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                # Check what we got
                html = response.text
                print(f"Response size: {len(html)} bytes")
                
                # Check for success indicators
                if 'royal canin' in html.lower()[:5000]:
                    print("✅ SUCCESS: Found 'Royal Canin' in content")
                    
                    # Check for ingredients
                    if 'composition' in html.lower():
                        print("✅ Found 'Composition' - can extract ingredients")
                    if 'protein' in html.lower():
                        print("✅ Found 'Protein' - can extract nutrition")
                        
                    # Save successful response
                    with open(f'success_test_{i}.html', 'w') as f:
                        f.write(html[:100000])
                    print(f"✅ Saved sample to success_test_{i}.html")
                    
                elif 'zooplus' in html.lower()[:2000]:
                    print("⚠️ Got Zooplus page but wrong content")
                else:
                    print("❌ Got unexpected content")
                    
            elif response.status_code == 400:
                print("❌ HTTP 400 - Bad Request")
                print(f"Response: {response.text[:200]}")
            elif response.status_code == 422:
                print("❌ HTTP 422 - ScrapingBee parameter error")
                print(f"Response: {response.text[:200]}")
            elif response.status_code == 429:
                print("❌ HTTP 429 - Rate limited")
            else:
                print(f"❌ HTTP {response.status_code}")
                print(f"Response: {response.text[:200]}")
                
        except Exception as e:
            print(f"❌ Exception: {str(e)[:100]}")
        
        print("-" * 40)
    
    print("\n🎯 RECOMMENDATIONS:")
    print("1. Try different Zooplus domains (.co.uk, .de, .fr)")
    print("2. Use different country codes in ScrapingBee")
    print("3. Consider reducing request frequency")
    print("4. Check if Zooplus has new bot detection")
    print("5. Try without JavaScript first")

if __name__ == "__main__":
    test_scraping_approaches()