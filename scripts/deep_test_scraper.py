#!/usr/bin/env python3
"""
Deep Test Scraper - Thoroughly scrape and analyze 5 Zooplus products
to find missing ingredients and nutrition data
"""

import os
import json
import time
import re
from datetime import datetime
from typing import Dict, List, Optional
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

SCRAPINGBEE_API_KEY = os.getenv('SCRAPING_BEE')

class DeepTestScraper:
    def __init__(self):
        self.api_key = SCRAPINGBEE_API_KEY
        self.test_products = [
            {
                'name': 'Purizon Grain-free Trial Packs',
                'url': 'https://www.zooplus.com/shop/dogs/dry_dog_food/purizon/trial_packs/1191314',
                'missing': 'ingredients'
            },
            {
                'name': 'Royal Canin Expert Canine Neutered Adult Large Dog',
                'url': 'https://www.zooplus.com/shop/dogs/dry_dog_food/royal_canin_vet_diet/1949350',
                'missing': 'ingredients'
            },
            {
                'name': 'Advance Veterinary Diets Hypoallergenic Mini',
                'url': 'https://www.zooplus.com/shop/dogs/dry_dog_food/advance_vet_diets/2159368',
                'missing': 'ingredients'
            },
            {
                'name': 'Applaws Taste Toppers Mixed Pack',
                'url': 'https://www.zooplus.com/shop/dogs/canned_dog_food/applaws/applaws_cans/1325115',
                'missing': 'nutrition'
            },
            {
                'name': 'Bonzo Vitafit Maxi',
                'url': 'https://www.zooplus.com/shop/dogs/dry_dog_food/bonzo/1583528',
                'missing': 'nutrition'
            }
        ]
        
        self.results = []
        
    def scrape_with_enhanced_extraction(self, url: str) -> Dict:
        """Scrape with multiple extraction strategies"""
        
        # Clean URL
        clean_url = url.split('?activeVariant=')[0]
        
        print(f"\n{'='*60}")
        print(f"🔬 DEEP SCRAPING: {clean_url[:60]}...")
        print(f"{'='*60}")
        
        # Use proven ScrapingBee parameters
        params = {
            'api_key': self.api_key,
            'url': clean_url,
            'render_js': 'true',
            'premium_proxy': 'true',
            'stealth_proxy': 'true',
            'country_code': 'gb',
            'wait': '5000',  # Longer wait for full page load
            'return_page_source': 'true'
        }
        
        try:
            print("📡 Sending request to ScrapingBee...")
            response = requests.get(
                'https://app.scrapingbee.com/api/v1/',
                params=params,
                timeout=120
            )
            
            if response.status_code == 200:
                print(f"✅ Success! Received {len(response.text):,} bytes")
                return self.deep_parse(response.text, clean_url)
            else:
                print(f"❌ HTTP {response.status_code}: {response.text[:200]}")
                return {'url': clean_url, 'error': f'HTTP {response.status_code}'}
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return {'url': clean_url, 'error': str(e)}
    
    def deep_parse(self, html: str, url: str) -> Dict:
        """Enhanced parsing with multiple extraction strategies"""
        
        soup = BeautifulSoup(html, 'html.parser')
        page_text = soup.get_text(separator='\n', strip=True)
        
        result = {
            'url': url,
            'scraped_at': datetime.now().isoformat(),
            'page_size': len(html),
            'analysis': {}
        }
        
        # Product name
        h1 = soup.find('h1')
        if h1:
            result['product_name'] = h1.text.strip()
            print(f"📦 Product: {result['product_name']}")
        
        # Strategy 1: Look for ingredients in various patterns
        print("\n🔍 INGREDIENTS EXTRACTION:")
        ingredients_found = False
        
        # Extended patterns for ingredients
        ingredients_patterns = [
            # Standard patterns
            r'(?:Composition|Ingredients|Zusammensetzung|Ingrédients)[:\s]*\n?([^\n]{20,}?)(?:\n(?:Analytical|Additives|Nutritional|Analytische)|$)',
            r'(?:Composition|Ingredients)[:\s]*([A-Za-z][^.]{30,}(?:\.[^.]{20,})*?)(?:Analytical|$)',
            
            # German patterns
            r'(?:Zusammensetzung)[:\s]*\n?([^\n]{20,}?)(?:\n(?:Analytische|Zusatzstoffe)|$)',
            
            # French patterns
            r'(?:Ingrédients|Composition)[:\s]*\n?([^\n]{20,}?)(?:\n(?:Constituants|Additifs)|$)',
            
            # Look for common ingredient indicators
            r'(?:Contains|Enthält|Contient)[:\s]*([^.]{20,}(?:meat|chicken|beef|fish|rice|wheat|maize|corn)[^.]*)',
            
            # Broader pattern looking for ingredient-like text
            r'(?i)((?:fresh |dried |dehydrated )?(?:chicken|beef|lamb|fish|turkey|duck|rabbit|pork|salmon|tuna)[^.]*(?:meal|meat|protein)?[^.]{10,})',
        ]
        
        for i, pattern in enumerate(ingredients_patterns, 1):
            matches = re.findall(pattern, page_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if matches:
                for match in matches[:3]:  # Show first 3 matches
                    ingredients = match.strip() if isinstance(match, str) else match[0].strip()
                    # Validate it looks like ingredients
                    ingredient_words = ['meat', 'chicken', 'beef', 'fish', 'rice', 'wheat', 'maize', 'corn', 
                                       'protein', 'meal', 'oil', 'fat', 'vegetable', 'mineral', 'vitamin']
                    if any(word in ingredients.lower() for word in ingredient_words):
                        if not ingredients_found:
                            result['ingredients_raw'] = ingredients[:3000]
                            ingredients_found = True
                        print(f"  Pattern {i}: Found {len(ingredients)} chars")
                        print(f"    Preview: {ingredients[:100]}...")
        
        if not ingredients_found:
            print("  ❌ No ingredients found with any pattern")
            
            # Look for any text sections that might contain ingredients
            print("\n  🔎 Searching for ingredient-like sections:")
            for section in soup.find_all(['div', 'p', 'span', 'td']):
                text = section.get_text(strip=True)
                if len(text) > 50 and any(word in text.lower() for word in ['chicken', 'beef', 'meat', 'rice', 'protein']):
                    print(f"    Found potential section: {text[:80]}...")
                    result['analysis']['potential_ingredients'] = text[:500]
                    break
        
        # Strategy 2: Enhanced nutrition extraction
        print("\n🔍 NUTRITION EXTRACTION:")
        nutrition = {}
        nutrition_found = False
        
        # Extended patterns for nutrition
        nutrition_patterns = [
            # English patterns
            (r'(?:Crude\s+)?Protein[:\s]+(\d+(?:[.,]\d+)?)\s*%', 'protein_percent'),
            (r'(?:Crude\s+)?(?:Fat|Oils)[:\s]+(\d+(?:[.,]\d+)?)\s*%', 'fat_percent'),
            (r'(?:Crude\s+)?Fib(?:re|er)[:\s]+(\d+(?:[.,]\d+)?)\s*%', 'fiber_percent'),
            (r'(?:Crude\s+)?Ash[:\s]+(\d+(?:[.,]\d+)?)\s*%', 'ash_percent'),
            (r'Moisture[:\s]+(\d+(?:[.,]\d+)?)\s*%', 'moisture_percent'),
            
            # German patterns
            (r'(?:Roh)?protein[:\s]+(\d+(?:[.,]\d+)?)\s*%', 'protein_percent'),
            (r'(?:Roh)?fett[:\s]+(\d+(?:[.,]\d+)?)\s*%', 'fat_percent'),
            (r'(?:Roh)?faser[:\s]+(\d+(?:[.,]\d+)?)\s*%', 'fiber_percent'),
            (r'(?:Roh)?asche[:\s]+(\d+(?:[.,]\d+)?)\s*%', 'ash_percent'),
            (r'Feuchtigkeit[:\s]+(\d+(?:[.,]\d+)?)\s*%', 'moisture_percent'),
            
            # French patterns
            (r'Protéines\s+brutes?[:\s]+(\d+(?:[.,]\d+)?)\s*%', 'protein_percent'),
            (r'Matières\s+grasses[:\s]+(\d+(?:[.,]\d+)?)\s*%', 'fat_percent'),
            (r'Fibres\s+brutes?[:\s]+(\d+(?:[.,]\d+)?)\s*%', 'fiber_percent'),
            (r'Cendres\s+brutes?[:\s]+(\d+(?:[.,]\d+)?)\s*%', 'ash_percent'),
            (r'Humidité[:\s]+(\d+(?:[.,]\d+)?)\s*%', 'moisture_percent'),
        ]
        
        for pattern, key in nutrition_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                value = match.group(1).replace(',', '.')
                nutrition[key] = float(value)
                nutrition_found = True
                print(f"  ✅ {key}: {value}%")
        
        if nutrition:
            result['nutrition'] = nutrition
        else:
            print("  ❌ No nutrition data found")
            
            # Look for table structures that might contain nutrition
            print("\n  🔎 Searching for nutrition tables:")
            tables = soup.find_all('table')
            for table in tables[:3]:
                table_text = table.get_text()
                if 'protein' in table_text.lower() or 'protéines' in table_text.lower():
                    print(f"    Found potential nutrition table")
                    result['analysis']['potential_nutrition_table'] = table_text[:500]
                    break
        
        # Strategy 3: Look for product information sections
        print("\n🔍 SEARCHING PRODUCT INFO SECTIONS:")
        
        # Common section identifiers
        info_sections = soup.find_all(['div', 'section'], class_=re.compile('product-info|description|details|specifications'))
        if info_sections:
            print(f"  Found {len(info_sections)} product info sections")
            for section in info_sections[:3]:
                section_text = section.get_text(strip=True)
                if len(section_text) > 100:
                    print(f"    Section preview: {section_text[:100]}...")
                    if 'analysis' not in result:
                        result['analysis'] = {}
                    result['analysis']['info_section'] = section_text[:1000]
        
        # Strategy 4: Check for expandable/collapsible content
        print("\n🔍 CHECKING FOR HIDDEN CONTENT:")
        
        # Look for accordion, tabs, or expandable elements
        expandables = soup.find_all(['div', 'details'], class_=re.compile('accordion|tab|collapse|expand'))
        if expandables:
            print(f"  Found {len(expandables)} expandable sections")
            for exp in expandables[:3]:
                exp_text = exp.get_text(strip=True)
                if len(exp_text) > 50:
                    print(f"    Expandable: {exp_text[:80]}...")
        
        # Strategy 5: Search for variant/option selectors
        print("\n🔍 CHECKING FOR PRODUCT VARIANTS:")
        
        # Look for variant selectors that might affect displayed info
        variants = soup.find_all(['select', 'div'], class_=re.compile('variant|option|size|flavour'))
        if variants:
            print(f"  Found {len(variants)} variant selectors")
            result['analysis']['has_variants'] = True
            
            # Check if we need a specific variant selected
            variant_options = []
            for variant in variants[:3]:
                options = variant.find_all('option') if variant.name == 'select' else variant.find_all('a')
                for opt in options[:5]:
                    variant_options.append(opt.get_text(strip=True))
            
            if variant_options:
                result['analysis']['variant_options'] = variant_options[:10]
                print(f"    Variants available: {', '.join(variant_options[:5])}")
        
        # Summary
        print("\n📊 EXTRACTION SUMMARY:")
        print(f"  Ingredients found: {'✅' if 'ingredients_raw' in result else '❌'}")
        print(f"  Nutrition found: {'✅' if 'nutrition' in result else '❌'}")
        print(f"  Page size: {len(html):,} bytes")
        print(f"  Analysis sections: {len(result.get('analysis', {}))}")
        
        return result
    
    def run_deep_test(self):
        """Run deep test on all 5 products"""
        
        print("\n" + "="*60)
        print("🧪 DEEP TEST SCRAPER - ZOOPLUS PRODUCT ANALYSIS")
        print("="*60)
        print(f"Testing {len(self.test_products)} products with enhanced extraction")
        
        for i, product in enumerate(self.test_products, 1):
            print(f"\n[{i}/{len(self.test_products)}] Testing: {product['name']}")
            print(f"Missing: {product['missing']}")
            
            result = self.scrape_with_enhanced_extraction(product['url'])
            result['product_name'] = product['name']
            result['originally_missing'] = product['missing']
            
            self.results.append(result)
            
            # Delay between requests
            if i < len(self.test_products):
                delay = 20
                print(f"\n⏳ Waiting {delay} seconds before next request...")
                time.sleep(delay)
        
        self.print_final_report()
        self.save_results()
    
    def print_final_report(self):
        """Print comprehensive test report"""
        
        print("\n" + "="*60)
        print("📊 DEEP TEST FINAL REPORT")
        print("="*60)
        
        success_count = 0
        ingredients_found = 0
        nutrition_found = 0
        
        for result in self.results:
            print(f"\n{result['product_name']}:")
            print(f"  Originally missing: {result['originally_missing']}")
            
            if 'error' in result:
                print(f"  ❌ Error: {result['error']}")
            else:
                if 'ingredients_raw' in result:
                    print(f"  ✅ Ingredients: {len(result['ingredients_raw'])} chars")
                    ingredients_found += 1
                else:
                    print(f"  ❌ Ingredients: Not found")
                
                if 'nutrition' in result:
                    print(f"  ✅ Nutrition: {len(result['nutrition'])} values")
                    nutrition_found += 1
                else:
                    print(f"  ❌ Nutrition: Not found")
                
                if 'analysis' in result:
                    print(f"  📝 Analysis sections: {len(result['analysis'])}")
                    if 'has_variants' in result['analysis']:
                        print(f"  ⚠️  Product has variants - may need specific selection")
                
                success_count += 1
        
        print("\n" + "-"*60)
        print("SUMMARY:")
        print(f"  Successful scrapes: {success_count}/{len(self.test_products)}")
        print(f"  Ingredients found: {ingredients_found}/{len(self.test_products)}")
        print(f"  Nutrition found: {nutrition_found}/{len(self.test_products)}")
        
        print("\n💡 INSIGHTS:")
        
        # Analyze why data might be missing
        variants_issue = sum(1 for r in self.results if 'analysis' in r and 'has_variants' in r.get('analysis', {}))
        if variants_issue > 0:
            print(f"  - {variants_issue} products have variants that may affect displayed data")
        
        no_ingredients = [r for r in self.results if 'ingredients_raw' not in r and 'error' not in r]
        if no_ingredients:
            print(f"  - {len(no_ingredients)} products genuinely lack ingredients on page")
            for r in no_ingredients:
                if 'analysis' in r and 'potential_ingredients' in r['analysis']:
                    print(f"    • {r['product_name']}: Found potential text but not valid ingredients")
        
        no_nutrition = [r for r in self.results if 'nutrition' not in r and 'error' not in r]
        if no_nutrition:
            print(f"  - {len(no_nutrition)} products genuinely lack nutrition data on page")
    
    def save_results(self):
        """Save detailed results to file"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'data/deep_test_results_{timestamp}.json'
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved to: {filename}")

def main():
    if not SCRAPINGBEE_API_KEY:
        print("❌ Error: SCRAPING_BEE environment variable not set")
        return
    
    scraper = DeepTestScraper()
    scraper.run_deep_test()

if __name__ == "__main__":
    main()