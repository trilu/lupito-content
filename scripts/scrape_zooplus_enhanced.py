#!/usr/bin/env python3
"""
Enhanced Zooplus scraper with better success rate
Uses rotating proxies and advanced ScrapingBee settings
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

class ZooplusEnhancedScraper:
    def __init__(self):
        self.api_key = SCRAPINGBEE_API_KEY
        self.base_url = 'https://app.scrapingbee.com/api/v1/'
        self.stats = {
            'total_scraped': 0,
            'successful': 0,
            'failed': 0,
            'ingredients_found': 0,
        }
        
    def scrape_with_retry(self, url: str, attempt: int = 1) -> Optional[str]:
        """Scrape with retry logic and rotating settings"""
        
        # Different strategies for each attempt
        strategies = [
            {
                # Strategy 1: Maximum stealth with long wait
                'render_js': 'true',
                'wait': '5000',
                'wait_for': '.product-details, #product-info, .ingredients-section',
                'premium_proxy': 'true',
                'stealth_proxy': 'true',
                'country_code': 'gb',
                'device': 'desktop',
                'block_ads': 'true',
                'screenshot': 'false',
                'javascript_snippet': '''
                    // Scroll to load lazy content
                    window.scrollTo(0, document.body.scrollHeight/2);
                    await new Promise(r => setTimeout(r, 1000));
                    window.scrollTo(0, document.body.scrollHeight);
                    await new Promise(r => setTimeout(r, 1000));
                    
                    // Click on composition tab if exists
                    const tabs = document.querySelectorAll('[data-tab*="composition"], [data-tab*="ingredients"], .tab-header');
                    for(let tab of tabs) {
                        if(tab.textContent.toLowerCase().includes('composition') || 
                           tab.textContent.toLowerCase().includes('ingredients')) {
                            tab.click();
                            await new Promise(r => setTimeout(r, 500));
                        }
                    }
                '''
            },
            {
                # Strategy 2: Different proxy location
                'render_js': 'true',
                'wait': '7000',
                'premium_proxy': 'true',
                'country_code': 'de',  # Try German proxy
                'device': 'desktop',
                'window_width': '1920',
                'window_height': '1080',
            },
            {
                # Strategy 3: Mobile device
                'render_js': 'true',
                'wait': '4000',
                'premium_proxy': 'true',
                'country_code': 'gb',
                'device': 'mobile',
            }
        ]
        
        if attempt > len(strategies):
            return None
        
        strategy = strategies[attempt - 1]
        
        # Base parameters
        params = {
            'api_key': self.api_key,
            'url': url,
            'return_page_source': 'true',
        }
        params.update(strategy)
        
        try:
            print(f"    Attempt {attempt}: Using strategy {attempt}")
            
            response = requests.get(
                self.base_url,
                params=params,
                timeout=90
            )
            
            if response.status_code == 200:
                # Check if we got real content
                if len(response.text) > 10000 and 'product' in response.text.lower():
                    self.stats['successful'] += 1
                    return response.text
                else:
                    print(f"      Got response but content seems incomplete ({len(response.text)} chars)")
                    if attempt < 3:
                        time.sleep(3)  # Wait before retry
                        return self.scrape_with_retry(url, attempt + 1)
            else:
                print(f"      Status {response.status_code}: {response.text[:200]}")
                if attempt < 3 and response.status_code != 402:  # Don't retry if out of credits
                    time.sleep(5)  # Longer wait on error
                    return self.scrape_with_retry(url, attempt + 1)
                    
        except Exception as e:
            print(f"      Exception: {e}")
            if attempt < 3:
                time.sleep(5)
                return self.scrape_with_retry(url, attempt + 1)
        
        self.stats['failed'] += 1
        return None
    
    def extract_product_data(self, html: str, url: str) -> Dict:
        """Enhanced extraction with multiple methods"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Save HTML for debugging
        debug_file = f"debug_zooplus_{self.stats['total_scraped']}.html"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(html[:50000])  # First 50k chars
        print(f"      Saved debug HTML to {debug_file}")
        
        product_data = {'url': url}
        
        # Extract product name - multiple selectors
        name_selectors = [
            'h1.product-name',
            'h1[data-testid="product-name"]',
            'h1[itemprop="name"]',
            '.product-title h1',
            '.product-header h1',
            'h1'
        ]
        
        for selector in name_selectors:
            elem = soup.select_one(selector)
            if elem and elem.text.strip() and elem.text.strip() != "Dry Dog Food":
                product_data['name'] = elem.text.strip()
                print(f"      Found name: {product_data['name'][:50]}")
                break
        
        # Look for ingredients in multiple ways
        ingredients_found = False
        
        # Method 1: Look for composition in text blocks
        text_blocks = soup.find_all(['div', 'section', 'p', 'span'])
        for block in text_blocks:
            text = block.get_text(separator=' ', strip=True)
            if len(text) > 100 and ('Composition:' in text or 'Ingredients:' in text or 'Zusammensetzung:' in text):
                ingredients = self.extract_ingredients_from_text(text)
                if ingredients:
                    product_data['ingredients_raw'] = ingredients['raw']
                    product_data['ingredients_tokens'] = ingredients['tokens']
                    self.stats['ingredients_found'] += 1
                    ingredients_found = True
                    print(f"      ✅ Found ingredients: {ingredients['raw'][:100]}...")
                    break
        
        # Method 2: Look in data attributes
        if not ingredients_found:
            elements_with_data = soup.find_all(attrs={'data-content': True})
            for elem in elements_with_data:
                text = elem.get('data-content', '')
                if 'Composition:' in text or 'Ingredients:' in text:
                    ingredients = self.extract_ingredients_from_text(text)
                    if ingredients:
                        product_data['ingredients_raw'] = ingredients['raw']
                        product_data['ingredients_tokens'] = ingredients['tokens']
                        self.stats['ingredients_found'] += 1
                        ingredients_found = True
                        print(f"      ✅ Found ingredients in data attribute")
                        break
        
        # Method 3: Check JSON-LD structured data
        if not ingredients_found:
            json_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        # Check description field
                        if 'description' in data:
                            ingredients = self.extract_ingredients_from_text(data['description'])
                            if ingredients:
                                product_data['ingredients_raw'] = ingredients['raw']
                                product_data['ingredients_tokens'] = ingredients['tokens']
                                self.stats['ingredients_found'] += 1
                                ingredients_found = True
                                print(f"      ✅ Found ingredients in JSON-LD")
                                break
                except:
                    pass
        
        # Extract analytical constituents
        analytical_text = soup.get_text()
        
        # Protein
        protein_match = re.search(r'(?:Crude\s+)?Protein[:\s]+(\d+\.?\d*)\s*%', analytical_text, re.IGNORECASE)
        if protein_match:
            product_data['protein_percent'] = float(protein_match.group(1))
            print(f"      Found protein: {product_data['protein_percent']}%")
        
        # Fat
        fat_match = re.search(r'(?:Crude\s+)?Fat(?:\s+content)?[:\s]+(\d+\.?\d*)\s*%', analytical_text, re.IGNORECASE)
        if fat_match:
            product_data['fat_percent'] = float(fat_match.group(1))
        
        # Fiber
        fiber_match = re.search(r'(?:Crude\s+)?Fib(?:re|er)[:\s]+(\d+\.?\d*)\s*%', analytical_text, re.IGNORECASE)
        if fiber_match:
            product_data['fiber_percent'] = float(fiber_match.group(1))
        
        # Ash
        ash_match = re.search(r'(?:Crude\s+)?Ash[:\s]+(\d+\.?\d*)\s*%', analytical_text, re.IGNORECASE)
        if ash_match:
            product_data['ash_percent'] = float(ash_match.group(1))
        
        # Moisture
        moisture_match = re.search(r'Moisture[:\s]+(\d+\.?\d*)\s*%', analytical_text, re.IGNORECASE)
        if moisture_match:
            product_data['moisture_percent'] = float(moisture_match.group(1))
        
        return product_data
    
    def extract_ingredients_from_text(self, text: str) -> Optional[Dict]:
        """Extract ingredients with improved patterns"""
        if not text or len(text) < 20:
            return None
        
        # More flexible patterns
        patterns = [
            # English
            r'Composition[:\s]*([^.]{20,}?)(?:Analytical|Additives|Feeding|Nutritional|$)',
            r'Ingredients[:\s]*([^.]{20,}?)(?:Analytical|Additives|Feeding|Nutritional|$)',
            # German
            r'Zusammensetzung[:\s]*([^.]{20,}?)(?:Analytische|Zusatzstoffe|$)',
            # With line breaks
            r'Composition[:\s]*\n([^\n]{20,})',
            r'Ingredients[:\s]*\n([^\n]{20,})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                ingredients_text = match.group(1).strip()
                
                # Clean up
                ingredients_text = re.sub(r'\s+', ' ', ingredients_text)
                ingredients_text = re.sub(r'\n', ' ', ingredients_text)
                
                # Must contain actual ingredients (not just marketing text)
                if any(word in ingredients_text.lower() for word in ['meat', 'chicken', 'beef', 'fish', 'rice', 'potato', 'vegetable', 'protein', 'meal']):
                    
                    # Tokenize
                    tokens = []
                    parts = re.split(r'[,;]', ingredients_text)
                    
                    for part in parts[:50]:
                        part = re.sub(r'\([^)]*\)', '', part)
                        part = re.sub(r'\d+\.?\d*\s*%', '', part)
                        part = re.sub(r'[^\\w\\s-]', ' ', part)
                        part = ' '.join(part.split()).strip().lower()
                        
                        if part and len(part) > 2 and len(part) < 50:
                            tokens.append(part)
                    
                    if len(tokens) >= 3:  # At least 3 ingredients
                        return {
                            'raw': ingredients_text[:2000],
                            'tokens': tokens
                        }
        
        return None
    
    def scrape_products(self, urls: List[str]) -> List[Dict]:
        """Scrape multiple products with rate limiting"""
        results = []
        
        print(f"\nScraping {len(urls)} Zooplus products with enhanced settings...")
        print("="*60)
        
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] {url}")
            
            # Rate limiting - be nice to ScrapingBee
            if i > 1:
                wait_time = 5  # 5 seconds between requests
                print(f"  Waiting {wait_time} seconds before next request...")
                time.sleep(wait_time)
            
            self.stats['total_scraped'] += 1
            
            # Scrape with retry
            html = self.scrape_with_retry(url)
            
            if html:
                product_data = self.extract_product_data(html, url)
                results.append(product_data)
                
                if product_data.get('ingredients_raw'):
                    print(f"  ✅ SUCCESS: Found ingredients and nutrition!")
                elif product_data.get('name') and product_data.get('name') != 'Dry Dog Food':
                    print(f"  ⚠️  PARTIAL: Got product name but no ingredients")
                else:
                    print(f"  ❌ FAILED: Could not extract product data")
            else:
                print(f"  ❌ FAILED: Could not scrape page after 3 attempts")
        
        return results
    
    def test_enhanced_scraping(self):
        """Test with high-value products"""
        
        print("="*60)
        print("ENHANCED ZOOPLUS SCRAPING TEST")
        print("="*60)
        print("Using advanced ScrapingBee settings with retry logic")
        print("Rate limiting: 5 seconds between requests")
        print("-"*60)
        
        # High-value product URLs
        test_urls = [
            # Try direct product pages (not category pages)
            "https://www.zooplus.co.uk/shop/dogs/dry_dog_food/hills_prescription_diet/gastro_intestinal/711554",  # Hill's i/d
            "https://www.zooplus.co.uk/shop/dogs/dry_dog_food/purizon/purizon_adult/652555",  # Purizon Adult Chicken & Fish
            "https://www.zooplus.co.uk/shop/dogs/dry_dog_food/royal_canin_vet_diet/gastro_intestinal/302817",  # Royal Canin Gastro
        ]
        
        # Scrape products
        results = self.scrape_products(test_urls)
        
        # Summary
        print("\n" + "="*60)
        print("SCRAPING SUMMARY")
        print("="*60)
        print(f"Total attempted: {self.stats['total_scraped']}")
        print(f"Successful scrapes: {self.stats['successful']}")
        print(f"Failed scrapes: {self.stats['failed']}")
        print(f"Products with ingredients: {self.stats['ingredients_found']}")
        
        # Save results
        if results:
            output_file = 'data/zooplus_enhanced_test.json'
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"\n✅ Saved {len(results)} results to {output_file}")
            
            # Show what we got
            for r in results:
                print(f"\n{r.get('name', 'Unknown')}:")
                if r.get('ingredients_raw'):
                    print(f"  Ingredients: {r['ingredients_raw'][:100]}...")
                if r.get('protein_percent'):
                    print(f"  Protein: {r['protein_percent']}%")
        
        return results

def main():
    scraper = ZooplusEnhancedScraper()
    results = scraper.test_enhanced_scraping()
    
    success_rate = (scraper.stats['ingredients_found'] / scraper.stats['total_scraped'] * 100) if scraper.stats['total_scraped'] > 0 else 0
    
    print(f"\n{'✅' if success_rate > 50 else '⚠️'} Ingredient extraction rate: {success_rate:.1f}%")

if __name__ == "__main__":
    main()