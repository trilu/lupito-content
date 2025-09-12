#!/usr/bin/env python3
"""
Working Zooplus scraper with proper JavaScript execution
Clicks on tabs to reveal ingredients and nutrition data
"""

import os
import re
import json
import time
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

SCRAPINGBEE_API_KEY = os.getenv('SCRAPING_BEE')

def scrape_zooplus_product(url):
    """Scrape a Zooplus product with JavaScript to reveal content"""
    
    print(f"\nScraping: {url}")
    print("-" * 60)
    
    # Clean URL - remove activeVariant if present
    if '?activeVariant=' in url:
        url = url.split('?activeVariant=')[0]
    
    # ScrapingBee parameters with JavaScript execution
    params = {
        'api_key': SCRAPINGBEE_API_KEY,
        'url': url,
        
        # JavaScript rendering is critical
        'render_js': 'true',
        
        # Premium features for better success
        'premium_proxy': 'true',
        'stealth_proxy': 'true',
        'country_code': 'us',
        
        # Return full page
        'return_page_source': 'true',
        
        # JavaScript scenario to click tabs and wait for content
        'js_scenario': json.dumps({
            "instructions": [
                # Initial wait for page load
                {"wait": 3000},
                
                # Scroll down to trigger lazy loading
                {"scroll_y": 500},
                {"wait": 1000},
                
                # Try to click on "Details" or "Description" tab/button
                {"evaluate": """
                    // Look for and click on details/description tabs
                    const tabSelectors = [
                        'button:contains("Details")',
                        'button:contains("Description")',
                        '[data-testid*="detail"]',
                        '[data-testid*="description"]',
                        '.tab-button:contains("Details")',
                        '.product-details-tab',
                        '[aria-label*="Details"]',
                        '[aria-label*="Description"]'
                    ];
                    
                    for (let selector of tabSelectors) {
                        try {
                            let elem = document.querySelector(selector);
                            if (!elem && selector.includes(':contains')) {
                                // Handle :contains pseudo selector
                                let searchText = selector.match(/:contains\("([^"]+)"\)/)[1];
                                document.querySelectorAll('button, [role="tab"]').forEach(el => {
                                    if (el.textContent.includes(searchText)) {
                                        elem = el;
                                    }
                                });
                            }
                            if (elem) {
                                elem.click();
                                console.log('Clicked on:', selector);
                                break;
                            }
                        } catch(e) {}
                    }
                """},
                {"wait": 2000},
                
                # Scroll more to load everything
                {"scroll_y": 1000},
                {"wait": 2000},
                
                # Try to expand any collapsed sections
                {"evaluate": """
                    // Expand any collapsible sections
                    document.querySelectorAll('[aria-expanded="false"]').forEach(el => {
                        el.click();
                    });
                    
                    // Click on any "Show more" buttons
                    document.querySelectorAll('button').forEach(el => {
                        if (el.textContent.toLowerCase().includes('show more') || 
                            el.textContent.toLowerCase().includes('read more')) {
                            el.click();
                        }
                    });
                """},
                {"wait": 2000}
            ]
        })
    }
    
    try:
        response = requests.get(
            'https://app.scrapingbee.com/api/v1/',
            params=params,
            timeout=120
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            html = response.text
            print(f"Response size: {len(html)} bytes")
            
            # Parse HTML
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract text
            page_text = soup.get_text(separator='\n', strip=True)
            
            result = {'url': url, 'success': False}
            
            # Get product name
            h1 = soup.find('h1')
            if h1:
                result['name'] = h1.text.strip()
                print(f"Product: {result['name']}")
            
            # Search for ingredients with multiple patterns
            ingredients_found = False
            
            # Pattern 1: Standard Composition format
            patterns = [
                r'Composition[:\s]*\n?([^\n]{20,}?)(?:\n(?:Analytical|Additives|Nutritional|Feeding)|$)',
                r'Ingredients[:\s]*\n?([^\n]{20,}?)(?:\n(?:Analytical|Additives|Nutritional|Feeding)|$)',
                r'Composition[:\s]*([^.]{30,}(?:\.[^.]{20,})*?)(?:Analytical|Additives|$)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, page_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                if match:
                    ingredients = match.group(1).strip()
                    # Validate it contains food words
                    food_words = ['meat', 'chicken', 'beef', 'fish', 'rice', 'corn', 'meal', 'protein']
                    if any(word in ingredients.lower() for word in food_words):
                        result['ingredients'] = ingredients[:2000]
                        print(f"✓ Found ingredients: {ingredients[:100]}...")
                        ingredients_found = True
                        result['success'] = True
                        break
            
            if not ingredients_found:
                # Try to find in HTML structure
                for elem in soup.find_all(['div', 'section', 'p']):
                    text = elem.get_text(strip=True)
                    if text.startswith(('Composition:', 'Ingredients:')):
                        if len(text) > 50:
                            result['ingredients'] = text[:2000]
                            print(f"✓ Found in HTML element: {text[:100]}...")
                            ingredients_found = True
                            result['success'] = True
                            break
            
            if not ingredients_found:
                print("✗ No ingredients found")
                # Check what we have
                if 'chicken' in page_text.lower() or 'beef' in page_text.lower():
                    print("  (But found meat words in page)")
                if 'Protein' in page_text:
                    print("  (But found nutrition info)")
            
            # Extract nutrition data
            nutrition = {}
            
            # Protein
            match = re.search(r'(?:Crude\s+)?Protein[:\s]+(\d+(?:\.\d+)?)\s*%', page_text, re.I)
            if match:
                nutrition['protein'] = float(match.group(1))
                
            # Fat
            match = re.search(r'(?:Crude\s+)?(?:Fat|Oils)[:\s]+(\d+(?:\.\d+)?)\s*%', page_text, re.I)
            if match:
                nutrition['fat'] = float(match.group(1))
                
            # Fiber
            match = re.search(r'(?:Crude\s+)?Fib(?:re|er)[:\s]+(\d+(?:\.\d+)?)\s*%', page_text, re.I)
            if match:
                nutrition['fiber'] = float(match.group(1))
                
            # Ash
            match = re.search(r'(?:Crude\s+)?Ash[:\s]+(\d+(?:\.\d+)?)\s*%', page_text, re.I)
            if match:
                nutrition['ash'] = float(match.group(1))
                
            # Moisture
            match = re.search(r'Moisture[:\s]+(\d+(?:\.\d+)?)\s*%', page_text, re.I)
            if match:
                nutrition['moisture'] = float(match.group(1))
            
            if nutrition:
                result['nutrition'] = nutrition
                print(f"✓ Found nutrition: {nutrition}")
                result['success'] = True
            
            return result
            
        else:
            print(f"Error: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Exception: {str(e)[:200]}")
        return None

def test_scraping():
    """Test with different product URLs"""
    
    print("TESTING IMPROVED ZOOPLUS SCRAPING")
    print("=" * 60)
    
    # Test URLs - mix of different products
    test_urls = [
        # Simple product URL (no activeVariant)
        "https://www.zooplus.com/shop/dogs/dry_dog_food/royal_canin_size/royal_canin_medium/128332",
        
        # Hill's product
        "https://www.zooplus.com/shop/dogs/dry_dog_food/hills_prescription/gastrointestinal/168526",
        
        # Taste of the Wild (the problematic one)
        "https://www.zooplus.com/shop/dogs/dry_dog_food/taste_of_the_wild/ecopack/580296",
    ]
    
    results = []
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n[Test {i}/{len(test_urls)}]")
        
        if i > 1:
            print("Waiting 10 seconds to avoid rate limits...")
            time.sleep(10)
        
        result = scrape_zooplus_product(url)
        if result:
            results.append(result)
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    success_count = sum(1 for r in results if r and r.get('success'))
    ingredients_count = sum(1 for r in results if r and r.get('ingredients'))
    nutrition_count = sum(1 for r in results if r and r.get('nutrition'))
    
    print(f"Successful: {success_count}/{len(test_urls)}")
    print(f"With ingredients: {ingredients_count}/{len(test_urls)}")
    print(f"With nutrition: {nutrition_count}/{len(test_urls)}")
    
    if ingredients_count > 0:
        print("\n✅ SUCCESS! We can extract ingredients!")
        print("\nSuccessful extractions:")
        for r in results:
            if r and r.get('ingredients'):
                print(f"\n{r.get('name', 'Unknown')}:")
                print(f"  Ingredients: {r['ingredients'][:150]}...")
                if r.get('nutrition'):
                    print(f"  Nutrition: {r['nutrition']}")
    else:
        print("\n⚠️ Still having issues extracting ingredients")
        print("The content might be:")
        print("1. Behind authentication/regional restrictions")
        print("2. Loaded via AJAX after significant delay")
        print("3. In a format we're not detecting")
    
    # Save last result for debugging
    if results:
        with open('last_scrape_result.json', 'w') as f:
            json.dump(results[-1], f, indent=2)
        print("\nLast result saved to last_scrape_result.json")

if __name__ == "__main__":
    test_scraping()