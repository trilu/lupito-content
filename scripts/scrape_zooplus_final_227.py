#!/usr/bin/env python3
"""
Targeted Zooplus scraper for final 227 products missing ingredients
Reads from JSON file and saves to GCS using proven patterns
"""

import os
import sys
import json
import time
import random
import argparse
from datetime import datetime
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google.cloud import storage
import re

load_dotenv()

SCRAPINGBEE_API_KEY = os.getenv('SCRAPING_BEE')
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")

class Final227Scraper:
    def __init__(self, session_name: str = "default", start_idx: int = 0, end_idx: int = None):
        self.session_name = session_name
        self.start_idx = start_idx
        self.end_idx = end_idx
        
        # Session configuration based on name
        self.session_configs = {
            "us1": {"country_code": "us", "min_delay": 15, "max_delay": 25},
            "gb1": {"country_code": "gb", "min_delay": 20, "max_delay": 30},
            "de1": {"country_code": "de", "min_delay": 25, "max_delay": 35},
            "ca1": {"country_code": "ca", "min_delay": 30, "max_delay": 40},
            "fr1": {"country_code": "fr", "min_delay": 18, "max_delay": 28},
            "default": {"country_code": "us", "min_delay": 20, "max_delay": 30}
        }
        
        # Get config for this session
        config = self.session_configs.get(session_name, self.session_configs["default"])
        self.country_code = config["country_code"]
        self.min_delay = config["min_delay"]
        self.max_delay = config["max_delay"]
        
        # Initialize GCS
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(GCS_BUCKET)
        
        # Create session folder
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.gcs_folder = f"scraped/zooplus/final_227_{timestamp}_{session_name}"
        
        # Statistics
        self.stats = {
            'total': 0,
            'successful': 0,
            'with_ingredients': 0,
            'with_nutrition': 0,
            'errors': 0,
            'consecutive_errors': 0,
            'session_start': datetime.now()
        }
        
        print(f"🚀 FINAL 227 SCRAPER - Session: {session_name}")
        print(f"   Country: {self.country_code}")
        print(f"   Delays: {self.min_delay}-{self.max_delay}s")
        print(f"   GCS: gs://{GCS_BUCKET}/{self.gcs_folder}/")
        print("-" * 50)
    
    def load_products(self) -> List[Dict]:
        """Load the 227 products from JSON file"""
        json_file = "/Users/sergiubiris/Desktop/lupito-content/data/zooplus_missing_ingredients_20250913.json"
        
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            products = data.get('products', [])
            
            # Apply index filtering if specified
            if self.end_idx:
                products = products[self.start_idx:self.end_idx]
            elif self.start_idx > 0:
                products = products[self.start_idx:]
            
            print(f"📦 Loaded {len(products)} products to scrape")
            return products
            
        except Exception as e:
            print(f"❌ Error loading products: {e}")
            return []
    
    def scrape_product(self, url: str) -> Dict:
        """Scrape a single product with proven parameters"""
        
        # Clean URL
        if '?activeVariant=' in url:
            url = url.split('?activeVariant=')[0]
        
        # Use proven ScrapingBee parameters
        params = {
            'api_key': SCRAPINGBEE_API_KEY,
            'url': url,
            'render_js': 'true',
            'premium_proxy': 'true',
            'stealth_proxy': 'true',
            'country_code': self.country_code,
            'wait': '3000',
            'return_page_source': 'true'
        }
        
        try:
            response = requests.get(
                'https://app.scrapingbee.com/api/v1/',
                params=params,
                timeout=120
            )
            
            if response.status_code == 200:
                return self.parse_response(response.text, url)
            else:
                error_msg = f'HTTP {response.status_code}'
                if response.text:
                    error_msg += f': {response.text[:100]}'
                return {'url': url, 'error': error_msg}
                
        except Exception as e:
            return {'url': url, 'error': str(e)[:200]}
    
    def parse_response(self, html: str, url: str) -> Dict:
        """Parse HTML with all 8 extraction patterns including relaxed Pattern 8"""
        
        soup = BeautifulSoup(html, 'html.parser')
        page_text = soup.get_text(separator='\n', strip=True)
        
        result = {
            'url': url,
            'scraped_at': datetime.now().isoformat(),
            'session': self.session_name,
            'country_code': self.country_code
        }
        
        # Get product name
        h1 = soup.find('h1')
        if h1:
            result['product_name'] = h1.text.strip()
        
        # All 8 extraction patterns including the relaxed Pattern 8
        ingredients_patterns = [
            # Pattern 1: "Ingredients / composition" format
            r'Ingredients\s*/\s*composition\s*\n([^\n]+(?:\([^)]+\))?(?:[,.]?\s*[^\n]+(?:\([^)]+\))?)*?)(?:\n\nAdditives|\nAdditives|\nAnalytical|\n\n)',
            
            # Pattern 2: "Ingredients:" with optional product description
            r'Ingredients:\s*\n(?:[^\n]*?(?:wet food|complete|diet)[^\n]*\n)?(\d+%[^\n]+(?:[,.]?\s*[^\n]+)*?)(?:\n\nAdditives|\nAdditives)',
            
            # Pattern 3: "Ingredients:" with variant info
            r'Ingredients:\s*\n(?:\d+(?:\.\d+)?kg bags?:\s*\n)?([A-Z][^\n]+(?:[,.]?\s*[^\n]+)*?)(?:\n\d+(?:\.\d+)?kg bags?:|\n\nAdditives|\nAdditives)',
            
            # Pattern 4: Simple "Ingredients:" followed directly by ingredients
            r'Ingredients:\s*\n([A-Z][^\n]+(?:\([^)]+\))?[,.]?\s*)(?:\n\nAdditives per kg:|\nAdditives|\n\n)',
            
            # Pattern 5: General "Ingredients:" with multiline capture
            r'Ingredients:\s*\n([^\n]+(?:\([^)]+\))?(?:[,.]?\s*[^\n]+(?:\([^)]+\))?)*?)(?:\n\nAdditives|\nAdditives|\n\nAnalytical|\nAnalytical)',
            
            # Pattern 6: "Ingredients" (no colon) followed by meat/duck/chicken
            r'Ingredients\s*\n((?:Meat|Duck|Chicken)[^\n]+(?:\([^)]+\))?(?:[,.]?\s*[^\n]+)*)(?:\n\nAdditives|\nAdditives)',
            
            # Pattern 7: "Ingredients:" with specific protein starting
            r'Ingredients:\s*\n((?:Duck|Chicken|Meat|Lamb|Beef|Turkey|Salmon|Fish)[^\n]+(?:\([^)]+\))?(?:[,.]?\s*[^\n]+)*)(?:\n\nAdditives|\nAdditives)',
            
            # Pattern 8: RELAXED - Capture from "Go to analytical constituents" onwards
            r'Go to analytical constituents\s*\n(.*?)(?:Analytical constituents|$)',
            
            # Original patterns as fallback
            r'(?:Composition|Ingredients)[:\s]*\n?([^\n]{20,}?)(?:\n(?:Analytical|Additives|Nutritional)|$)',
            r'(?:Composition|Ingredients)[:\s]*([A-Za-z][^.]{30,}(?:\.[^.]{20,})*?)(?:Analytical|$)',
        ]
        
        # Try each pattern
        for i, pattern in enumerate(ingredients_patterns, 1):
            match = re.search(pattern, page_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match:
                ingredients = match.group(1).strip()
                
                # Skip navigation text
                if 'go to' in ingredients.lower() and 'constituent' in ingredients.lower():
                    continue
                
                # For Pattern 8, try to extract ingredients from the captured content
                if i == 8 and ingredients:
                    # Try to find ingredients within the relaxed capture
                    inner_match = re.search(
                        r'Ingredients:?\s*\n([^\n]+(?:\([^)]+\))?(?:[,.]?\s*[^\n]+)*?)(?:\n\nAdditives|\nAdditives|$)',
                        ingredients, 
                        re.IGNORECASE | re.MULTILINE
                    )
                    if inner_match:
                        ingredients = inner_match.group(1).strip()
                
                # Validate ingredients contain food-related words
                food_words = ['meat', 'chicken', 'beef', 'fish', 'rice', 'wheat', 
                             'maize', 'protein', 'poultry', 'lamb', 'turkey', 'salmon',
                             'duck', 'vegetables', 'cereals', 'meal', 'flour']
                
                if any(word in ingredients.lower() for word in food_words):
                    result['ingredients_raw'] = ingredients[:3000]
                    result['pattern_used'] = f"Pattern {i}"
                    self.stats['with_ingredients'] += 1
                    break
        
        # Extract nutrition data
        nutrition = {}
        nutrition_patterns = [
            (r'(?:Crude\s+)?Protein[:\s]+(\d+(?:\.\d+)?)\s*%', 'protein_percent'),
            (r'(?:Crude\s+)?(?:Fat|Oils)[:\s]+(\d+(?:\.\d+)?)\s*%', 'fat_percent'),
            (r'(?:Crude\s+)?Fib(?:re|er)[:\s]+(\d+(?:\.\d+)?)\s*%', 'fiber_percent'),
            (r'(?:Crude\s+)?Ash[:\s]+(\d+(?:\.\d+)?)\s*%', 'ash_percent'),
            (r'Moisture[:\s]+(\d+(?:\.\d+)?)\s*%', 'moisture_percent')
        ]
        
        for pattern, key in nutrition_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                nutrition[key] = float(match.group(1))
        
        if nutrition:
            result['nutrition'] = nutrition
            self.stats['with_nutrition'] += 1
        
        # Mark as successful if we got data
        if 'ingredients_raw' in result or nutrition:
            self.stats['successful'] += 1
            self.stats['consecutive_errors'] = 0
        else:
            self.stats['consecutive_errors'] += 1
        
        return result
    
    def save_to_gcs(self, product_key: str, data: Dict) -> bool:
        """Save scraped data to GCS"""
        try:
            # Clean product key for filename
            safe_key = product_key.replace('|', '_').replace('/', '_')
            filename = f"{self.gcs_folder}/{safe_key}.json"
            
            blob = self.bucket.blob(filename)
            blob.upload_from_string(
                json.dumps(data, indent=2, ensure_ascii=False),
                content_type='application/json'
            )
            return True
            
        except Exception as e:
            print(f"   ❌ GCS error: {str(e)[:100]}")
            return False
    
    def run(self):
        """Main execution loop"""
        
        # Load products
        products = self.load_products()
        if not products:
            print("❌ No products to scrape")
            return
        
        print(f"\n🎯 Starting scraping of {len(products)} products\n")
        
        # Process each product
        for i, product in enumerate(products, 1):
            # Check for too many consecutive errors
            if self.stats['consecutive_errors'] >= 5:
                print("\n⚠️ Stopping due to 5 consecutive errors")
                break
            
            # Progress indicator
            print(f"[{i}/{len(products)}] {product['product_name'][:50]}...")
            
            # Delay between requests (except first)
            if i > 1:
                delay = random.uniform(self.min_delay, self.max_delay)
                print(f"   ⏱️ Waiting {delay:.1f}s...")
                time.sleep(delay)
            
            self.stats['total'] += 1
            
            # Scrape the product
            result = self.scrape_product(product['product_url'])
            
            # Add product metadata
            result['product_key'] = product['product_key']
            result['brand'] = product.get('brand')
            
            # Show result
            if 'error' in result:
                print(f"   ❌ Error: {result['error']}")
                self.stats['errors'] += 1
            else:
                indicators = []
                if 'ingredients_raw' in result:
                    pattern = result.get('pattern_used', 'Unknown')
                    indicators.append(f"ingredients ({pattern})")
                if 'nutrition' in result:
                    indicators.append(f"nutrition ({len(result['nutrition'])} values)")
                
                if indicators:
                    print(f"   ✅ Found: {', '.join(indicators)}")
                else:
                    print(f"   ⚠️ No data extracted")
            
            # Save to GCS
            if self.save_to_gcs(product['product_key'], result):
                print(f"   💾 Saved to GCS")
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print session summary"""
        print("\n" + "=" * 50)
        print("📊 SCRAPING SESSION COMPLETE")
        print("=" * 50)
        
        elapsed = datetime.now() - self.stats['session_start']
        
        print(f"Session: {self.session_name}")
        print(f"Duration: {elapsed}")
        print(f"Total processed: {self.stats['total']}")
        print(f"Successful: {self.stats['successful']}")
        print(f"With ingredients: {self.stats['with_ingredients']}")
        print(f"With nutrition: {self.stats['with_nutrition']}")
        print(f"Errors: {self.stats['errors']}")
        
        if self.stats['total'] > 0:
            success_rate = self.stats['successful'] / self.stats['total'] * 100
            print(f"Success rate: {success_rate:.1f}%")
        
        print(f"\n📁 GCS folder: gs://{GCS_BUCKET}/{self.gcs_folder}/")
        print("=" * 50)

def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(description='Scrape final 227 Zooplus products')
    parser.add_argument('--session', type=str, default='default',
                       choices=['us1', 'gb1', 'de1', 'ca1', 'fr1', 'default'],
                       help='Session name (determines country and delays)')
    parser.add_argument('--start', type=int, default=0,
                       help='Start index in product list')
    parser.add_argument('--end', type=int, default=None,
                       help='End index in product list')
    
    args = parser.parse_args()
    
    # Create and run scraper
    scraper = Final227Scraper(
        session_name=args.session,
        start_idx=args.start,
        end_idx=args.end
    )
    scraper.run()

if __name__ == "__main__":
    main()