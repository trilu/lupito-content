#!/usr/bin/env python3
"""
Scrape Zooplus with the CORRECT URL format (using activeVariant parameter)
This should finally work!
"""

import os
import re
import time
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

SCRAPINGBEE_API_KEY = os.getenv('SCRAPING_BEE')

def scrape_with_correct_url():
    """Test with URLs that have activeVariant parameter"""
    
    print("SCRAPING ZOOPLUS WITH CORRECT URL FORMAT")
    print("="*60)
    
    # Use URLs with activeVariant parameter - these should work!
    test_urls = [
        # Rocco with variant
        "https://www.zooplus.co.uk/shop/dogs/canned_dog_food/rocco/rocco_classic/154458?activeVariant=154458.23",
        
        # Another product with variant
        "https://www.zooplus.co.uk/shop/dogs/dry_dog_food/royal_canin_size/royal_canin_medium/466802?activeVariant=466802.4",
        
        # Hill's with variant
        "https://www.zooplus.co.uk/shop/dogs/dry_dog_food/hills_science_plan/hills_healthy_mobility/711514?activeVariant=711514.1",
    ]
    
    results = []
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n[Product {i}]")
        print(f"URL: {url}")
        print("-"*40)
        
        if i > 1:
            print("Waiting 5 seconds...")
            time.sleep(5)
        
        # ScrapingBee parameters
        params = {
            'api_key': SCRAPINGBEE_API_KEY,
            'url': url,
            
            # JavaScript rendering with wait
            'render_js': 'true',
            'wait': '7000',  # 7 seconds should be enough
            
            # Premium proxy
            'premium_proxy': 'true',
            'stealth_proxy': 'true',
            'country_code': 'gb',
            
            # Get full page
            'return_page_source': 'true',
        }
        
        try:
            response = requests.get(
                'https://app.scrapingbee.com/api/v1/',
                params=params,
                timeout=90
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                html = response.text
                print(f"Response size: {len(html)} bytes")
                
                # Parse HTML
                soup = BeautifulSoup(html, 'html.parser')
                
                product = {'url': url}
                
                # Get title
                title = soup.find('title')
                if title:
                    print(f"Title: {title.text[:80]}")
                
                # Get product name (h1)
                h1 = soup.find('h1')
                if h1:
                    product['name'] = h1.text.strip()
                    print(f"Product name: {product['name'][:50]}")
                
                # Search for ingredients
                page_text = soup.get_text()
                
                # Look for Composition
                print("\nSearching for ingredients...")
                
                # Method 1: Direct search in text
                if 'Composition:' in page_text:
                    print("  ✓ Found 'Composition:' in page")
                    
                    # Extract composition
                    comp_match = re.search(
                        r'Composition[:\s]+([^\n]{20,}?)(?:Analytical|Additives|Feeding|Nutritional|\n\n)',
                        page_text,
                        re.IGNORECASE | re.MULTILINE
                    )
                    
                    if comp_match:
                        ingredients = comp_match.group(1).strip()[:500]
                        product['ingredients'] = ingredients
                        print(f"  ✓ Extracted ingredients: {ingredients[:100]}...")
                else:
                    print("  ✗ 'Composition:' not found")
                
                # Method 2: Look in all divs
                comp_divs = soup.find_all(text=re.compile('Composition:', re.I))
                if comp_divs:
                    print(f"  ✓ Found {len(comp_divs)} elements with 'Composition:'")
                    for div in comp_divs[:1]:
                        parent = div.parent
                        if parent:
                            text = parent.get_text(strip=True)
                            if len(text) > 50:
                                product['ingredients_alt'] = text[:200]
                                print(f"  Alternative extraction: {text[:100]}...")
                
                # Look for nutritional data
                if 'Analytical' in page_text or 'Protein' in page_text:
                    print("\nSearching for nutrition...")
                    
                    protein_match = re.search(r'Protein[:\s]+(\d+\.?\d*)\s*%', page_text, re.I)
                    if protein_match:
                        product['protein'] = float(protein_match.group(1))
                        print(f"  ✓ Protein: {product['protein']}%")
                    
                    fat_match = re.search(r'Fat[:\s]+(\d+\.?\d*)\s*%', page_text, re.I)
                    if fat_match:
                        product['fat'] = float(fat_match.group(1))
                        print(f"  ✓ Fat: {product['fat']}%")
                
                results.append(product)
                
                # Save HTML for first product
                if i == 1:
                    with open('correct_url_test.html', 'w', encoding='utf-8') as f:
                        f.write(html[:50000])
                    print("\nSaved HTML to correct_url_test.html for inspection")
                
        except Exception as e:
            print(f"Error: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("RESULTS SUMMARY")
    print("="*60)
    
    success_count = sum(1 for r in results if 'ingredients' in r or 'ingredients_alt' in r)
    print(f"Products with ingredients: {success_count}/{len(results)}")
    
    nutrition_count = sum(1 for r in results if 'protein' in r)
    print(f"Products with nutrition: {nutrition_count}/{len(results)}")
    
    if success_count > 0:
        print("\n✅ SUCCESS! The activeVariant URLs work!")
        print("Solution: Use URLs with activeVariant parameter")
    else:
        print("\n⚠️ Still no ingredients found")
        print("The content might be:")
        print("1. Loaded after page load via AJAX")
        print("2. In a different language")
        print("3. Behind a tab/accordion that needs clicking")
    
    return results

if __name__ == "__main__":
    results = scrape_with_correct_url()
    
    if results:
        print("\nProducts scraped:")
        for r in results:
            print(f"\n{r.get('name', 'Unknown')}")
            if 'ingredients' in r:
                print(f"  Ingredients: {r['ingredients'][:100]}...")
            if 'protein' in r:
                print(f"  Nutrition: Protein={r['protein']}%")