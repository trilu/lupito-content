#!/usr/bin/env python3
"""
Scrape REAL Zooplus product pages (with SKUs) using ScrapingBee
Focus on high-value brands for ingredient extraction
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

class ZooplusProductScraper:
    def __init__(self):
        self.api_key = SCRAPINGBEE_API_KEY
        self.stats = {
            'total': 0,
            'successful': 0,
            'with_ingredients': 0,
            'with_nutrition': 0,
            'failed': []
        }
        
    def scrape_product(self, url: str, attempt: int = 1) -> Optional[Dict]:
        """Scrape a single product page"""
        
        # Convert to UK site
        if 'zooplus.com' in url:
            url = url.replace('zooplus.com', 'zooplus.co.uk')
        
        # ScrapingBee parameters optimized for Zooplus
        params = {
            'api_key': self.api_key,
            'url': url,
            
            # JavaScript rendering
            'render_js': 'true',
            'wait': '6000',  # Wait 6 seconds for content to load
            
            # Premium proxy with stealth
            'premium_proxy': 'true',
            'stealth_proxy': 'true',
            'country_code': 'gb',
            
            # Don't block anything
            'block_resources': 'false',
            
            # Return full HTML
            'return_page_source': 'true',
        }
        
        print(f"  Attempt {attempt}: {url[:80]}...")
        
        try:
            response = requests.get(
                'https://app.scrapingbee.com/api/v1/',
                params=params,
                timeout=90
            )
            
            if response.status_code == 200:
                print(f"    ✓ Got {len(response.text)} bytes")
                return self.parse_product_page(response.text, url)
            else:
                print(f"    ✗ Status {response.status_code}")
                if attempt < 2:  # One retry
                    time.sleep(3)
                    return self.scrape_product(url, attempt + 1)
                return None
                
        except Exception as e:
            print(f"    ✗ Exception: {e}")
            self.stats['failed'].append(url)
            return None
    
    def parse_product_page(self, html: str, url: str) -> Dict:
        """Extract product data from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        
        product = {'url': url}
        
        # Extract product name
        h1_tags = soup.find_all('h1')
        for h1 in h1_tags:
            name = h1.get_text(strip=True)
            if name and name not in ['Dry Dog Food', 'Wet Dog Food', 'Dog Food']:
                product['name'] = name
                print(f"    Name: {name[:50]}")
                break
        
        # Get all text from page
        page_text = soup.get_text(separator='\n', strip=True)
        
        # Method 1: Look for Composition section in text
        ingredients = None
        
        # Try multiple patterns
        patterns = [
            r'Composition[:\n\s]+([^\n]{20,}(?:\n[^\n]+)*?)(?:\nAnalytical|\nAdditives|\nFeeding|\n\n|$)',
            r'Ingredients[:\n\s]+([^\n]{20,}(?:\n[^\n]+)*?)(?:\nAnalytical|\nAdditives|\nFeeding|\n\n|$)',
            r'Zusammensetzung[:\n\s]+([^\n]{20,}(?:\n[^\n]+)*?)(?:\nAnalytische|\nZusatzstoffe|\n\n|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, page_text, re.IGNORECASE | re.MULTILINE)
            if match:
                ingredients_text = match.group(1).strip()
                
                # Validate it contains actual ingredients
                if any(word in ingredients_text.lower() for word in ['meat', 'chicken', 'rice', 'potato', 'fish', 'protein', 'meal', 'oil']):
                    ingredients = ingredients_text[:2000]
                    product['ingredients_raw'] = ingredients
                    product['ingredients_tokens'] = self.tokenize_ingredients(ingredients)
                    self.stats['with_ingredients'] += 1
                    print(f"    ✓ Found ingredients: {ingredients[:60]}...")
                    break
        
        # Method 2: Look in specific divs/sections
        if not ingredients:
            # Check for ingredient sections
            for section in soup.find_all(['div', 'section', 'article']):
                text = section.get_text(strip=True)
                if 'Composition:' in text or 'Ingredients:' in text:
                    comp_match = re.search(r'(?:Composition|Ingredients):\s*([^.]{20,})', text, re.I)
                    if comp_match:
                        ingredients_text = comp_match.group(1)
                        if any(word in ingredients_text.lower() for word in ['meat', 'chicken', 'rice', 'fish']):
                            product['ingredients_raw'] = ingredients_text[:2000]
                            product['ingredients_tokens'] = self.tokenize_ingredients(ingredients_text)
                            self.stats['with_ingredients'] += 1
                            print(f"    ✓ Found ingredients in section")
                            break
        
        # Extract nutritional data
        nutrition_found = False
        
        # Protein
        protein_match = re.search(r'(?:Crude\s+)?Protein[:\s]+(\d+\.?\d*)\s*%', page_text, re.I)
        if protein_match:
            product['protein_percent'] = float(protein_match.group(1))
            nutrition_found = True
        
        # Fat
        fat_match = re.search(r'(?:Crude\s+)?Fat(?:\s+content)?[:\s]+(\d+\.?\d*)\s*%', page_text, re.I)
        if fat_match:
            product['fat_percent'] = float(fat_match.group(1))
            nutrition_found = True
        
        # Fiber
        fiber_match = re.search(r'(?:Crude\s+)?Fib(?:re|er)[:\s]+(\d+\.?\d*)\s*%', page_text, re.I)
        if fiber_match:
            product['fiber_percent'] = float(fiber_match.group(1))
            nutrition_found = True
        
        # Ash
        ash_match = re.search(r'(?:Crude\s+)?Ash[:\s]+(\d+\.?\d*)\s*%', page_text, re.I)
        if ash_match:
            product['ash_percent'] = float(ash_match.group(1))
        
        # Moisture
        moisture_match = re.search(r'Moisture[:\s]+(\d+\.?\d*)\s*%', page_text, re.I)
        if moisture_match:
            product['moisture_percent'] = float(moisture_match.group(1))
        
        if nutrition_found:
            self.stats['with_nutrition'] += 1
            print(f"    ✓ Found nutrition: P={product.get('protein_percent')}% F={product.get('fat_percent')}%")
        
        self.stats['successful'] += 1
        
        # Save debug HTML for first few products
        if self.stats['successful'] <= 3:
            debug_file = f'debug_product_{self.stats["successful"]}.html'
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(html[:50000])
            print(f"    Saved debug to {debug_file}")
        
        return product
    
    def tokenize_ingredients(self, text: str) -> List[str]:
        """Convert ingredients text to tokens"""
        # Remove percentages and parentheses
        text = re.sub(r'\([^)]*\)', '', text)
        text = re.sub(r'\d+\.?\d*\s*%', '', text)
        
        # Split by comma or semicolon
        tokens = []
        for part in re.split(r'[,;]', text)[:50]:
            part = re.sub(r'[^\w\s-]', ' ', part)
            part = ' '.join(part.split()).strip().lower()
            
            if part and 2 < len(part) < 50:
                tokens.append(part)
        
        return tokens
    
    def scrape_batch(self, products: List[Dict]) -> List[Dict]:
        """Scrape a batch of products"""
        results = []
        
        print(f"\nScraping {len(products)} Zooplus products...")
        print("="*60)
        
        for i, product in enumerate(products, 1):
            print(f"\n[{i}/{len(products)}]")
            
            # Rate limiting - 5 seconds between requests
            if i > 1:
                print("  Waiting 5 seconds...")
                time.sleep(5)
            
            self.stats['total'] += 1
            
            url = product.get('url', '')
            result = self.scrape_product(url)
            
            if result:
                # Add original data
                result['sku'] = product.get('sku')
                result['original_name'] = product.get('name')
                result['breadcrumbs'] = product.get('breadcrumbs')
                results.append(result)
        
        return results

def main():
    """Scrape high-value Zooplus products"""
    
    print("ZOOPLUS REAL PRODUCT SCRAPING")
    print("="*60)
    
    # Load Zooplus data
    with open('data/zooplus/Zooplus.json', 'r') as f:
        data = json.load(f)
    
    # Find high-value products with SKUs in URLs
    target_products = []
    target_brands = ['Hills Prescription Diet', 'Purizon', 'Royal Canin', 'Josera', 'Concept for Life']
    
    for product in data:
        if len(target_products) >= 5:
            break
            
        url = product.get('url', '')
        sku = product.get('sku', '')
        breadcrumbs = product.get('breadcrumbs', [])
        
        # Must have SKU in URL (individual product page)
        if sku and sku in url:
            # Check brand
            if len(breadcrumbs) > 2:
                brand = breadcrumbs[2]
                for target in target_brands:
                    if target.lower() in brand.lower():
                        target_products.append(product)
                        print(f"Selected: {product.get('name', 'Unknown')[:50]}")
                        break
    
    # If not enough, just get any products with SKUs
    if len(target_products) < 5:
        for product in data:
            if len(target_products) >= 5:
                break
            url = product.get('url', '')
            sku = product.get('sku', '')
            if sku and sku in url and product not in target_products:
                target_products.append(product)
    
    # Scrape the products
    scraper = ZooplusProductScraper()
    results = scraper.scrape_batch(target_products[:3])  # Just 3 for testing
    
    # Summary
    print("\n" + "="*60)
    print("SCRAPING SUMMARY")
    print("="*60)
    print(f"Total attempted: {scraper.stats['total']}")
    print(f"Successful: {scraper.stats['successful']}")
    print(f"With ingredients: {scraper.stats['with_ingredients']}")
    print(f"With nutrition: {scraper.stats['with_nutrition']}")
    
    if scraper.stats['total'] > 0:
        success_rate = (scraper.stats['with_ingredients'] / scraper.stats['total']) * 100
        print(f"\nIngredient extraction rate: {success_rate:.1f}%")
    
    # Show results
    if results:
        print("\nProducts scraped:")
        for r in results:
            print(f"\n{r.get('name', r.get('original_name', 'Unknown'))}")
            if r.get('ingredients_raw'):
                print(f"  ✓ Ingredients: {r['ingredients_raw'][:80]}...")
            if r.get('protein_percent'):
                print(f"  ✓ Nutrition: P={r['protein_percent']}% F={r.get('fat_percent')}%")
        
        # Save results
        with open('data/zooplus_real_products.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n✅ Saved {len(results)} results to data/zooplus_real_products.json")

if __name__ == "__main__":
    main()