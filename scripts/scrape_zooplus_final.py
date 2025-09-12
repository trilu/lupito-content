#!/usr/bin/env python3
"""
Final Zooplus scraper optimized for JavaScript content
Scrapes actual product pages and extracts ingredients from dynamic content
"""

import os
import json
import re
import time
import requests
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

SCRAPINGBEE_API_KEY = os.getenv('SCRAPING_BEE')

class ZooplusFinalScraper:
    def __init__(self):
        self.api_key = SCRAPINGBEE_API_KEY
        self.base_url = 'https://app.scrapingbee.com/api/v1/'
        self.stats = {
            'total': 0,
            'successful': 0,
            'with_ingredients': 0,
            'with_nutrition': 0
        }
        
    def scrape_product(self, url: str) -> Optional[Dict]:
        """Scrape a single product with optimal settings"""
        
        # Keep using .com domain as in our data
        # Remove activeVariant parameter if present (user said it works without it)
        if '?activeVariant=' in url:
            url = url.split('?activeVariant=')[0]
        
        params = {
            'api_key': self.api_key,
            'url': url,
            
            # JavaScript rendering - critical for Zooplus
            'render_js': 'true',
            'wait': '7000',  # Wait 7 seconds for JS content
            
            # Premium features for bot protection
            'premium_proxy': 'true',
            'stealth_proxy': 'true',
            'country_code': 'us',  # Use US for .com domain
            
            # Get full page
            'return_page_source': 'true',
        }
        
        try:
            print(f"  Scraping: {url}")
            
            response = requests.get(
                self.base_url,
                params=params,
                timeout=90
            )
            
            if response.status_code == 200:
                return self.parse_page(response.text, url)
            else:
                print(f"    Error {response.status_code}: {response.text[:200]}")
                return None
                
        except Exception as e:
            print(f"    Exception: {e}")
            return None
    
    def parse_page(self, html: str, url: str) -> Dict:
        """Parse the scraped page"""
        soup = BeautifulSoup(html, 'html.parser')
        
        product = {'url': url}
        
        # Get product name from multiple possible locations
        name_found = False
        for selector in ['h1', '.product-name', '[data-testid="product-name"]', '.product-title']:
            elem = soup.select_one(selector)
            if elem and elem.text.strip():
                name = elem.text.strip()
                if name != "Dry Dog Food" and name != "Wet Dog Food":
                    product['name'] = name
                    name_found = True
                    break
        
        if name_found:
            print(f"    Found: {product['name'][:50]}")
        
        # Search entire page for ingredients
        page_text = soup.get_text(separator='\n', strip=True)
        
        # Look for composition/ingredients
        ingredients = None
        
        # Pattern 1: Look for "Composition:" followed by ingredients
        comp_match = re.search(
            r'(?:Composition|Ingredients|Zusammensetzung)[:\s]*\n?([^\n]{20,}(?:\n[^\n]+)*?)(?:\n(?:Analytical|Feeding|Additives|Nutritional)|$)',
            page_text,
            re.IGNORECASE
        )
        
        if comp_match:
            ingredients_text = comp_match.group(1).strip()
            # Clean and validate
            if any(word in ingredients_text.lower() for word in ['meat', 'chicken', 'rice', 'protein', 'meal', 'fish']):
                ingredients = ingredients_text[:2000]
                product['ingredients_raw'] = ingredients
                product['ingredients_tokens'] = self.tokenize(ingredients)
                self.stats['with_ingredients'] += 1
                print(f"    ✅ Found ingredients: {ingredients[:80]}...")
        
        # Look for analytical constituents
        nutrition = {}
        
        # Search for nutrition patterns
        if 'Protein' in page_text:
            prot_match = re.search(r'(?:Crude\s+)?Protein[:\s]+(\d+\.?\d*)\s*%', page_text, re.I)
            if prot_match:
                nutrition['protein_percent'] = float(prot_match.group(1))
        
        if 'Fat' in page_text:
            fat_match = re.search(r'(?:Crude\s+)?Fat[:\s]+(\d+\.?\d*)\s*%', page_text, re.I)
            if fat_match:
                nutrition['fat_percent'] = float(fat_match.group(1))
        
        if 'Fibre' in page_text or 'Fiber' in page_text:
            fib_match = re.search(r'(?:Crude\s+)?Fib(?:re|er)[:\s]+(\d+\.?\d*)\s*%', page_text, re.I)
            if fib_match:
                nutrition['fiber_percent'] = float(fib_match.group(1))
        
        if 'Ash' in page_text:
            ash_match = re.search(r'(?:Crude\s+)?Ash[:\s]+(\d+\.?\d*)\s*%', page_text, re.I)
            if ash_match:
                nutrition['ash_percent'] = float(ash_match.group(1))
        
        if 'Moisture' in page_text:
            moist_match = re.search(r'Moisture[:\s]+(\d+\.?\d*)\s*%', page_text, re.I)
            if moist_match:
                nutrition['moisture_percent'] = float(moist_match.group(1))
        
        if nutrition:
            product.update(nutrition)
            self.stats['with_nutrition'] += 1
            print(f"    ✅ Found nutrition: Protein={nutrition.get('protein_percent')}%")
        
        self.stats['successful'] += 1
        return product
    
    def tokenize(self, text: str) -> List[str]:
        """Tokenize ingredients"""
        # Remove percentages and parentheses
        text = re.sub(r'\([^)]*\)', '', text)
        text = re.sub(r'\d+\.?\d*\s*%', '', text)
        
        # Split and clean
        tokens = []
        for part in re.split(r'[,;]', text)[:50]:
            part = re.sub(r'[^\\w\\s-]', ' ', part)
            part = ' '.join(part.split()).strip().lower()
            if part and 2 < len(part) < 50:
                tokens.append(part)
        
        return tokens
    
    def scrape_batch(self, product_list: List[Dict]) -> List[Dict]:
        """Scrape a batch of products"""
        results = []
        
        print(f"\nScraping {len(product_list)} products...")
        print("="*60)
        
        for i, product in enumerate(product_list, 1):
            print(f"\n[{i}/{len(product_list)}]")
            
            # Rate limiting - 3 seconds between requests
            if i > 1:
                print("  Waiting 3 seconds...")
                time.sleep(3)
            
            self.stats['total'] += 1
            
            url = product.get('url', '')
            if url:
                result = self.scrape_product(url)
                if result:
                    # Add original product info
                    result['original_name'] = product.get('name')
                    result['breadcrumbs'] = product.get('breadcrumbs')
                    results.append(result)
        
        return results

def main():
    """Test with real Zooplus products"""
    
    print("FINAL ZOOPLUS SCRAPING TEST")
    print("="*60)
    
    # Load Zooplus data
    with open('data/zooplus/Zooplus.json', 'r') as f:
        data = json.load(f)
    
    # Find high-value products to test
    test_products = []
    
    # Get a mix of brands
    brands_wanted = ['Purizon', 'Hill\'s Prescription Diet', 'Royal Canin', 'Josera', 'Concept for Life']
    
    for product in data:
        if len(test_products) >= 5:
            break
        
        breadcrumbs = product.get('breadcrumbs', [])
        if len(breadcrumbs) > 2:
            brand = breadcrumbs[2]
            
            for wanted in brands_wanted:
                if wanted.lower() in brand.lower() and product not in test_products:
                    test_products.append(product)
                    break
    
    # Scrape the products
    scraper = ZooplusFinalScraper()
    results = scraper.scrape_batch(test_products[:3])  # Just 3 for testing
    
    # Summary
    print("\n" + "="*60)
    print("RESULTS SUMMARY")
    print("="*60)
    print(f"Total scraped: {scraper.stats['total']}")
    print(f"Successful: {scraper.stats['successful']}")
    print(f"With ingredients: {scraper.stats['with_ingredients']}")
    print(f"With nutrition: {scraper.stats['with_nutrition']}")
    
    success_rate = (scraper.stats['with_ingredients'] / scraper.stats['total'] * 100) if scraper.stats['total'] > 0 else 0
    print(f"\nIngredient extraction rate: {success_rate:.1f}%")
    
    # Save results
    if results:
        with open('data/zooplus_final_test.json', 'w') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n✅ Saved {len(results)} results to data/zooplus_final_test.json")

if __name__ == "__main__":
    main()