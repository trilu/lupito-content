#!/usr/bin/env python3
"""
Rescrape the remaining 160 products from the final 227 that still don't have ingredients
Uses improved patterns and robust error handling
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

class Remaining160Scraper:
    def __init__(self, session_name: str = "session1", start_idx: int = 0, end_idx: int = None):
        self.session_name = session_name
        self.start_idx = start_idx
        self.end_idx = end_idx
        
        # Configure delays based on session to avoid conflicts
        if session_name == "session1":
            self.country_code = "us"
            self.min_delay = 20
            self.max_delay = 30
        else:  # session2
            self.country_code = "gb"
            self.min_delay = 25
            self.max_delay = 35
        
        # Initialize GCS
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(GCS_BUCKET)
        
        # Create session folder
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.gcs_folder = f"scraped/zooplus/rescrape_160_{timestamp}_{session_name}"
        
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
        
        print(f"🚀 REMAINING 160 RESCRAPER - Session: {session_name}")
        print(f"   Country: {self.country_code}")
        print(f"   Delays: {self.min_delay}-{self.max_delay}s")
        print(f"   GCS: gs://{GCS_BUCKET}/{self.gcs_folder}/")
        print("-" * 50)
    
    def load_products(self) -> List[Dict]:
        """Load the 160 remaining products from JSON file"""
        json_file = "data/zooplus_still_missing_after_scrape.json"
        
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            products = data.get('products', [])
            
            # Apply index filtering for session splitting
            if self.end_idx:
                products = products[self.start_idx:self.end_idx]
            elif self.start_idx > 0:
                products = products[self.start_idx:]
            
            print(f"📦 Loaded {len(products)} products to scrape")
            return products
            
        except Exception as e:
            print(f"❌ Error loading products: {e}")
            return []
    
    def scrape_product(self, url: str, retry_count: int = 0) -> Dict:
        """Scrape a single product with retry logic"""
        
        # Clean URL
        if '?activeVariant=' in url:
            base_url = url.split('?activeVariant=')[0]
            # Try with activeVariant first, then without if it fails
            urls_to_try = [url, base_url] if '?activeVariant=' in url else [url]
        else:
            urls_to_try = [url]
        
        for attempt_url in urls_to_try:
            # Use proven ScrapingBee parameters
            params = {
                'api_key': SCRAPINGBEE_API_KEY,
                'url': attempt_url,
                'render_js': 'true',
                'premium_proxy': 'true',
                'stealth_proxy': 'true',
                'country_code': self.country_code,
                'wait': '5000',  # Increased wait time
                'return_page_source': 'true',
                'block_resources': 'false',  # Don't block any resources
                'javascript_snippet': 'window.scrollTo(0, document.body.scrollHeight);'  # Scroll to load all content
            }
            
            try:
                response = requests.get(
                    'https://app.scrapingbee.com/api/v1/',
                    params=params,
                    timeout=150  # Increased timeout
                )
                
                if response.status_code == 200:
                    result = self.parse_response(response.text, attempt_url)
                    if 'ingredients_raw' in result:
                        return result
                    # If no ingredients found, try next URL variant
                    continue
                elif response.status_code == 429 and retry_count < 3:
                    # Rate limited, wait and retry
                    wait_time = 60 * (retry_count + 1)
                    print(f"   ⏳ Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    return self.scrape_product(url, retry_count + 1)
                else:
                    error_msg = f'HTTP {response.status_code}'
                    if response.text:
                        error_msg += f': {response.text[:100]}'
                    # Try next URL variant
                    continue
                    
            except Exception as e:
                # Try next URL variant
                continue
        
        # If all attempts failed
        return {'url': url, 'error': 'All URL variants failed'}
    
    def parse_response(self, html: str, url: str) -> Dict:
        """Parse HTML with all extraction patterns including relaxed patterns"""
        
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
        
        # Extended extraction patterns - including more relaxed ones
        ingredients_patterns = [
            # Pattern 1-7: Standard patterns
            r'Ingredients\s*/\s*composition\s*\n([^\n]+(?:\([^)]+\))?(?:[,.]?\s*[^\n]+(?:\([^)]+\))?)*?)(?:\n\nAdditives|\nAdditives|\nAnalytical|\n\n)',
            r'Ingredients:\s*\n(?:[^\n]*?(?:wet food|complete|diet)[^\n]*\n)?(\d+%[^\n]+(?:[,.]?\s*[^\n]+)*?)(?:\n\nAdditives|\nAdditives)',
            r'Ingredients:\s*\n(?:\d+(?:\.\d+)?kg bags?:\s*\n)?([A-Z][^\n]+(?:[,.]?\s*[^\n]+)*?)(?:\n\d+(?:\.\d+)?kg bags?:|\n\nAdditives|\nAdditives)',
            r'Ingredients:\s*\n([A-Z][^\n]+(?:\([^)]+\))?[,.]?\s*)(?:\n\nAdditives per kg:|\nAdditives|\n\n)',
            r'Ingredients:\s*\n([^\n]+(?:\([^)]+\))?(?:[,.]?\s*[^\n]+(?:\([^)]+\))?)*?)(?:\n\nAdditives|\nAdditives|\n\nAnalytical|\nAnalytical)',
            r'Ingredients\s*\n((?:Meat|Duck|Chicken)[^\n]+(?:\([^)]+\))?(?:[,.]?\s*[^\n]+)*)(?:\n\nAdditives|\nAdditives)',
            r'Ingredients:\s*\n((?:Duck|Chicken|Meat|Lamb|Beef|Turkey|Salmon|Fish)[^\n]+(?:\([^)]+\))?(?:[,.]?\s*[^\n]+)*)(?:\n\nAdditives|\nAdditives)',
            
            # Pattern 8: Relaxed - Capture from "Go to analytical constituents"
            r'Go to analytical constituents\s*\n(.*?)(?:Analytical constituents|$)',
            
            # Pattern 9: Even more relaxed - anything after Ingredients
            r'Ingredients[:\s]*\n([^\n]+(?:\n[^\n]+){0,5})(?:\n\n|\nAnalytical|\nAdditives|$)',
            
            # Pattern 10: Look for Composition instead
            r'Composition[:\s]*\n([^\n]+(?:\([^)]+\))?(?:[,.]?\s*[^\n]+(?:\([^)]+\))?)*?)(?:\n\nAdditives|\nAdditives|\nAnalytical|\n\n)',
            
            # Pattern 11: Super relaxed - find any text with food ingredients
            r'(?:Ingredients|Composition)[:\s]*([^.]{30,500}?)(?:Analytical|Additives|Nutritional|$)',
            
            # Pattern 12: Look for specific ingredient patterns anywhere
            r'(\d+%\s*(?:fresh|dried|dehydrated)?\s*(?:chicken|beef|lamb|fish|salmon|turkey|duck|meat)[^.]{20,300})',
            
            # Original fallback patterns
            r'(?:Composition|Ingredients)[:\s]*\n?([^\n]{20,}?)(?:\n(?:Analytical|Additives|Nutritional)|$)',
            r'(?:Composition|Ingredients)[:\s]*([A-Za-z][^.]{30,}(?:\.[^.]{20,})*?)(?:Analytical|$)',
        ]
        
        # Try each pattern
        for i, pattern in enumerate(ingredients_patterns, 1):
            match = re.search(pattern, page_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match:
                ingredients = match.group(1).strip()
                
                # Skip navigation text
                if 'go to' in ingredients.lower() and i != 8:  # Unless it's pattern 8
                    continue
                
                # For Pattern 8, try to extract ingredients from the captured content
                if i == 8 and ingredients:
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
                             'duck', 'vegetables', 'cereals', 'meal', 'flour', 'fresh',
                             'dried', 'dehydrated', '%', 'oil', 'fat', 'potato', 'pea']
                
                if any(word in ingredients.lower() for word in food_words):
                    # Clean up the ingredients
                    ingredients = re.sub(r'\s+', ' ', ingredients)  # Normalize whitespace
                    ingredients = ingredients.strip()
                    
                    if len(ingredients) > 30:  # Ensure it's substantial
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
        
        print(f"\n🎯 Starting rescraping of {len(products)} products\n")
        
        # Process each product
        for i, product in enumerate(products, 1):
            # Check for too many consecutive errors
            if self.stats['consecutive_errors'] >= 10:
                print("\n⚠️ Stopping due to 10 consecutive errors")
                print("   Waiting 5 minutes before continuing...")
                time.sleep(300)  # Wait 5 minutes
                self.stats['consecutive_errors'] = 0
            
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
            
            # Every 10 products, print a mini summary
            if i % 10 == 0:
                elapsed = datetime.now() - self.stats['session_start']
                if self.stats['total'] > 0:
                    success_rate = self.stats['with_ingredients'] / self.stats['total'] * 100
                    print(f"\n   --- Progress: {i}/{len(products)} | Success rate: {success_rate:.1f}% | Elapsed: {elapsed} ---\n")
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print session summary"""
        print("\n" + "=" * 50)
        print("📊 RESCRAPING SESSION COMPLETE")
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
            success_rate = self.stats['with_ingredients'] / self.stats['total'] * 100
            print(f"Success rate: {success_rate:.1f}%")
        
        print(f"\n📁 GCS folder: gs://{GCS_BUCKET}/{self.gcs_folder}/")
        print("=" * 50)

def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(description='Rescrape remaining 160 Zooplus products')
    parser.add_argument('--session', type=str, default='session1',
                       choices=['session1', 'session2'],
                       help='Session name')
    parser.add_argument('--start', type=int, default=0,
                       help='Start index in product list')
    parser.add_argument('--end', type=int, default=None,
                       help='End index in product list')
    
    args = parser.parse_args()
    
    # Create and run scraper
    scraper = Remaining160Scraper(
        session_name=args.session,
        start_idx=args.start,
        end_idx=args.end
    )
    scraper.run()

if __name__ == "__main__":
    main()