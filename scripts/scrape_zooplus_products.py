#!/usr/bin/env python3
"""
Scrape Zooplus product pages using ScrapingBee
Handles JavaScript/AJAX content and bot protection
"""

import os
import json
import re
import time
import requests
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Initialize clients
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_KEY')
)

SCRAPINGBEE_API_KEY = os.getenv('SCRAPING_BEE')

class ZooplusScrapingBee:
    def __init__(self):
        self.api_key = SCRAPINGBEE_API_KEY
        self.base_url = 'https://app.scrapingbee.com/api/v1/'
        self.stats = {
            'total_scraped': 0,
            'successful': 0,
            'failed': 0,
            'ingredients_found': 0,
            'samples': []
        }
        
    def scrape_product_page(self, url: str) -> Optional[Dict]:
        """Scrape a single Zooplus product page"""
        
        # Optimal ScrapingBee settings for Zooplus
        params = {
            'api_key': self.api_key,
            'url': url,
            
            # JavaScript rendering - essential for Zooplus
            'render_js': 'true',
            'wait': '3000',  # Wait 3 seconds for content to load
            'wait_for': 'networkidle',  # Wait until network is idle
            
            # Bot protection bypass
            'premium_proxy': 'true',  # Use premium proxies
            'stealth_proxy': 'true',  # Maximum stealth mode
            'country_code': 'gb',  # UK proxy for zooplus.co.uk
            
            # Browser settings
            'device': 'desktop',
            'window_width': '1920',
            'window_height': '1080',
            
            # Additional headers for authenticity
            'forward_headers': 'true',
            'block_resources': 'false',  # Don't block resources, we need JS
            
            # Return format
            'return_page_source': 'true',  # Get full HTML after JS execution
        }
        
        # Custom headers to appear more legitimate
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-GB,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
        }
        
        try:
            print(f"  Scraping: {url}")
            response = requests.get(
                self.base_url,
                params=params,
                headers=headers,
                timeout=60  # Longer timeout for JS rendering
            )
            
            if response.status_code == 200:
                self.stats['successful'] += 1
                return self.parse_product_page(response.text, url)
            else:
                print(f"    ❌ Failed with status {response.status_code}")
                print(f"    Response: {response.text[:500]}")
                self.stats['failed'] += 1
                return None
                
        except Exception as e:
            print(f"    ❌ Exception: {e}")
            self.stats['failed'] += 1
            return None
    
    def parse_product_page(self, html: str, url: str) -> Optional[Dict]:
        """Parse the scraped HTML to extract product data"""
        soup = BeautifulSoup(html, 'html.parser')
        
        product_data = {'url': url}
        
        # Extract product name
        name_elem = soup.find('h1', class_='product-name') or \
                   soup.find('h1', {'data-testid': 'product-name'}) or \
                   soup.find('h1')
        
        if name_elem:
            product_data['name'] = name_elem.get_text(strip=True)
        
        # Extract ingredients - multiple possible locations
        ingredients = None
        
        # Method 1: Look for "Composition" section
        composition_patterns = [
            ('div', {'class': re.compile('composition', re.I)}),
            ('div', {'class': re.compile('ingredients', re.I)}),
            ('section', {'class': re.compile('composition', re.I)}),
            ('div', {'data-testid': 'composition'}),
            ('div', {'id': re.compile('composition', re.I)}),
        ]
        
        for tag, attrs in composition_patterns:
            elem = soup.find(tag, attrs)
            if elem:
                text = elem.get_text(separator=' ', strip=True)
                if 'Composition:' in text or 'Ingredients:' in text:
                    ingredients = self.extract_ingredients_from_text(text)
                    if ingredients:
                        break
        
        # Method 2: Look in product description tabs
        if not ingredients:
            # Check for tabbed content
            tabs = soup.find_all('div', class_=re.compile('tab-content|product-tab|description-tab'))
            for tab in tabs:
                text = tab.get_text(separator=' ', strip=True)
                if 'Composition:' in text or 'Ingredients:' in text:
                    ingredients = self.extract_ingredients_from_text(text)
                    if ingredients:
                        break
        
        # Method 3: Search entire page for composition patterns
        if not ingredients:
            full_text = soup.get_text(separator=' ', strip=True)
            ingredients = self.extract_ingredients_from_text(full_text)
        
        if ingredients:
            product_data['ingredients_raw'] = ingredients['raw']
            product_data['ingredients_tokens'] = ingredients['tokens']
            self.stats['ingredients_found'] += 1
        
        # Extract nutritional analysis
        nutrition = self.extract_nutrition(soup)
        if nutrition:
            product_data.update(nutrition)
        
        # Extract brand
        brand_elem = soup.find('a', class_='brand-link') or \
                    soup.find('span', class_='brand-name') or \
                    soup.find('div', {'data-testid': 'brand-name'})
        
        if brand_elem:
            product_data['brand'] = brand_elem.get_text(strip=True)
        
        # Add to samples if interesting
        if ingredients and len(self.stats['samples']) < 3:
            self.stats['samples'].append({
                'name': product_data.get('name', 'Unknown'),
                'ingredients': ingredients['raw'][:200]
            })
        
        return product_data
    
    def extract_ingredients_from_text(self, text: str) -> Optional[Dict]:
        """Extract ingredients from text"""
        if not text:
            return None
        
        # Look for composition/ingredients section
        patterns = [
            r'Composition:\s*([^.]{20,}?)(?:Analytical|Additives|Nutritional|Feeding|$)',
            r'Ingredients:\s*([^.]{20,}?)(?:Analytical|Additives|Nutritional|Feeding|$)',
            r'Zusammensetzung:\s*([^.]{20,}?)(?:Analytische|Zusatzstoffe|$)',  # German
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                ingredients_text = match.group(1).strip()
                
                # Clean up
                ingredients_text = re.sub(r'\s+', ' ', ingredients_text)
                ingredients_text = ingredients_text[:2000]  # Limit length
                
                # Tokenize
                tokens = self.tokenize_ingredients(ingredients_text)
                
                if tokens and len(tokens) > 2:  # Must have at least 3 ingredients
                    return {
                        'raw': ingredients_text,
                        'tokens': tokens
                    }
        
        return None
    
    def tokenize_ingredients(self, text: str) -> List[str]:
        """Convert ingredients text to tokens"""
        if not text:
            return []
        
        # Remove percentages and parentheses
        text = re.sub(r'\([^)]*\)', '', text)
        text = re.sub(r'\d+\.?\d*\s*%', '', text)
        
        # Split by comma or semicolon
        parts = re.split(r'[,;]', text)
        
        tokens = []
        for part in parts[:50]:  # Limit to 50 ingredients
            # Clean the part
            part = re.sub(r'[^\\w\\s-]', ' ', part)
            part = ' '.join(part.split())
            part = part.strip().lower()
            
            # Skip very short or very long tokens
            if part and 2 < len(part) < 50:
                # Skip common non-ingredients
                if part not in ['and', 'with', 'contains', 'including']:
                    tokens.append(part)
        
        return tokens
    
    def extract_nutrition(self, soup: BeautifulSoup) -> Dict:
        """Extract nutritional data from page"""
        nutrition = {}
        
        # Look for analytical constituents
        patterns = [
            r'Protein[:\s]+(\d+\.?\d*)\s*%',
            r'Fat content[:\s]+(\d+\.?\d*)\s*%',
            r'Crude fat[:\s]+(\d+\.?\d*)\s*%',
            r'Crude fibre[:\s]+(\d+\.?\d*)\s*%',
            r'Crude ash[:\s]+(\d+\.?\d*)\s*%',
            r'Moisture[:\s]+(\d+\.?\d*)\s*%',
        ]
        
        text = soup.get_text()
        
        if re.search(r'Protein[:\s]+\d+', text, re.IGNORECASE):
            match = re.search(r'Protein[:\s]+(\d+\.?\d*)\s*%', text, re.IGNORECASE)
            if match:
                nutrition['protein_percent'] = float(match.group(1))
        
        if re.search(r'Fat|Fett', text, re.IGNORECASE):
            match = re.search(r'(?:Fat content|Crude fat|Fat)[:\s]+(\d+\.?\d*)\s*%', text, re.IGNORECASE)
            if match:
                nutrition['fat_percent'] = float(match.group(1))
        
        if re.search(r'Fibre|Fiber', text, re.IGNORECASE):
            match = re.search(r'(?:Crude fibre|Fibre|Fiber)[:\s]+(\d+\.?\d*)\s*%', text, re.IGNORECASE)
            if match:
                nutrition['fiber_percent'] = float(match.group(1))
        
        if re.search(r'Ash', text, re.IGNORECASE):
            match = re.search(r'(?:Crude ash|Ash)[:\s]+(\d+\.?\d*)\s*%', text, re.IGNORECASE)
            if match:
                nutrition['ash_percent'] = float(match.group(1))
        
        if re.search(r'Moisture', text, re.IGNORECASE):
            match = re.search(r'Moisture[:\s]+(\d+\.?\d*)\s*%', text, re.IGNORECASE)
            if match:
                nutrition['moisture_percent'] = float(match.group(1))
        
        return nutrition
    
    def scrape_batch(self, urls: List[str]) -> List[Dict]:
        """Scrape a batch of URLs"""
        results = []
        
        print(f"\nScraping {len(urls)} product pages...")
        print("-"*40)
        
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}]")
            
            # Rate limiting - ScrapingBee has limits
            if i > 1:
                time.sleep(2)  # 2 second delay between requests
            
            self.stats['total_scraped'] += 1
            
            # Scrape the page
            product_data = self.scrape_product_page(url)
            
            if product_data:
                results.append(product_data)
                
                # Show progress
                if product_data.get('ingredients_raw'):
                    print(f"    ✅ Found ingredients!")
                else:
                    print(f"    ⚠️  No ingredients found")
        
        return results
    
    def test_scraping(self):
        """Test with a small batch of high-value products"""
        
        print("="*60)
        print("ZOOPLUS SCRAPINGBEE TEST")
        print("="*60)
        print(f"API Key: {self.api_key[:10]}...")
        
        # Test URLs - high value products we want ingredients for
        test_urls = [
            # Hill's Prescription Diet
            "https://www.zooplus.co.uk/shop/dogs/dry_dog_food/hills_prescription_diet/gastro_intestinal/1073843",
            
            # Purizon
            "https://www.zooplus.co.uk/shop/dogs/dry_dog_food/purizon/purizon_adult/776886",
            
            # Josera
            "https://www.zooplus.co.uk/shop/dogs/dry_dog_food/josera/320633",
            
            # Concept for Life
            "https://www.zooplus.co.uk/shop/dogs/dry_dog_food/concept_for_life_size/large_adult/764618",
            
            # Royal Canin
            "https://www.zooplus.co.uk/shop/dogs/dry_dog_food/royal_canin_size/royal_canin_medium/718470",
        ]
        
        # Scrape the batch
        results = self.scrape_batch(test_urls[:3])  # Start with just 3 to test
        
        # Print results
        print("\n" + "="*60)
        print("SCRAPING RESULTS")
        print("="*60)
        print(f"Total scraped: {self.stats['total_scraped']}")
        print(f"Successful: {self.stats['successful']}")
        print(f"Failed: {self.stats['failed']}")
        print(f"With ingredients: {self.stats['ingredients_found']}")
        
        if self.stats['samples']:
            print("\nSample ingredients found:")
            print("-"*40)
            for sample in self.stats['samples']:
                print(f"\n{sample['name']}")
                print(f"Ingredients: {sample['ingredients']}...")
        
        # Save results for inspection
        if results:
            output_file = 'data/zooplus_scraped_test.json'
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\n✅ Saved {len(results)} results to {output_file}")
        
        return results

def main():
    scraper = ZooplusScrapingBee()
    results = scraper.test_scraping()
    
    if results:
        print("\n✅ ScrapingBee test successful!")
        print(f"   Successfully scraped {len(results)} products")
        print(f"   Found ingredients in {scraper.stats['ingredients_found']} products")
    else:
        print("\n❌ ScrapingBee test failed - no results")

if __name__ == "__main__":
    main()