#!/usr/bin/env python3
"""
Scrape the final 160 Zooplus products using proven orchestrator infrastructure
Uses the same successful patterns as orchestrated_scraper.py
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

class Final160Scraper:
    def __init__(self, session_name: str = "us1", start_idx: int = 0, end_idx: int = None):
        self.session_name = session_name
        self.start_idx = start_idx
        self.end_idx = end_idx
        
        # Use proven session configurations from orchestrator
        session_configs = {
            "us1": {"country_code": "us", "min_delay": 15, "max_delay": 25},
            "gb1": {"country_code": "gb", "min_delay": 20, "max_delay": 30},
            "de1": {"country_code": "de", "min_delay": 25, "max_delay": 35},
            "ca1": {"country_code": "ca", "min_delay": 30, "max_delay": 40},
            "fr1": {"country_code": "fr", "min_delay": 18, "max_delay": 28}
        }
        
        config = session_configs.get(session_name, session_configs["us1"])
        self.country_code = config["country_code"]
        self.min_delay = config["min_delay"]
        self.max_delay = config["max_delay"]
        
        # Initialize GCS with service account
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/sergiubiris/Desktop/lupito-content/secrets/gcp-sa.json'
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(GCS_BUCKET)
        
        # Create session folder
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.gcs_folder = f"scraped/zooplus/final_160_{timestamp}_{session_name}"
        
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
        
        print(f"🚀 FINAL 160 SCRAPER - Session: {session_name}")
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
        """Scrape using proven ScrapingBee parameters from orchestrator"""
        
        # Use EXACT parameters from working orchestrator
        params = {
            'api_key': SCRAPINGBEE_API_KEY,
            'url': url,
            'render_js': 'true',
            'premium_proxy': 'true',
            'stealth_proxy': 'true',
            'country_code': self.country_code,
            'wait': '3000',  # Proven wait time
            'return_page_source': 'true'
            # NO block_resources, NO javascript_snippet - these cause errors!
        }
        
        try:
            response = requests.get(
                'https://app.scrapingbee.com/api/v1/',
                params=params,
                timeout=120  # Standard timeout
            )
            
            if response.status_code == 200:
                return self.parse_response(response.text, url)
            elif response.status_code == 429 and retry_count < 3:
                # Rate limited, wait and retry
                wait_time = 60 * (retry_count + 1)
                print(f"   ⏳ Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
                return self.scrape_product(url, retry_count + 1)
            else:
                return {'url': url, 'error': f'HTTP {response.status_code}'}
                
        except Exception as e:
            return {'url': url, 'error': str(e)[:100]}
    
    def parse_response(self, html: str, url: str) -> Dict:
        """Parse using all successful patterns including Pattern 8"""
        
        soup = BeautifulSoup(html, 'html.parser')
        page_text = soup.get_text(separator='\n', strip=True)
        
        result = {
            'url': url,
            'scraped_at': datetime.now().isoformat(),
            'session': self.session_name,
            'country_code': self.country_code
        }
        
        # CRITICAL: Check for 404/category pages before proceeding
        if any(indicator in html for indicator in ['404', 'Page not found', 'Seite nicht gefunden']):
            result['error'] = '404 - Page not found'
            result['skip_reason'] = 'Product page does not exist'
            return result
        
        # Check if this is a category/list page instead of product page
        if 'product-list' in html or 'category-grid' in html:
            result['error'] = 'Category page - not a product'
            result['skip_reason'] = 'Redirected to category page'
            return result
        
        # Check if Ingredients section exists at all
        if 'Ingredients' not in page_text:
            result['error'] = 'No ingredients section found'
            result['skip_reason'] = 'Page lacks ingredients information'
            return result
        
        # Get product name
        h1 = soup.find('h1')
        if h1:
            result['product_name'] = h1.text.strip()
        
        # All patterns from the working scrapers
        ingredients_patterns = [
            # Pattern 1: Standard Ingredients/composition
            r'Ingredients\s*/\s*composition\s*\n([^\n]+(?:\([^)]+\))?(?:[,.]?\s*[^\n]+(?:\([^)]+\))?)*?)(?:\n\nAdditives|\nAdditives|\nAnalytical|\n\n)',
            
            # Pattern 2: Ingredients with product description
            r'Ingredients:\s*\n(?:[^\n]*?(?:wet food|complete|diet)[^\n]*\n)?(\d+%[^\n]+(?:[,.]?\s*[^\n]+)*?)(?:\n\nAdditives|\nAdditives)',
            
            # Pattern 3: Ingredients with variant info
            r'Ingredients:\s*\n(?:\d+(?:\.\d+)?kg bags?:\s*\n)?([A-Z][^\n]+(?:[,.]?\s*[^\n]+)*?)(?:\n\d+(?:\.\d+)?kg bags?:|\n\nAdditives|\nAdditives)',
            
            # Pattern 4: Simple Ingredients: format
            r'Ingredients:\s*\n([A-Z][^\n]+(?:\([^)]+\))?[,.]?\s*)(?:\n\nAdditives per kg:|\nAdditives|\n\n)',
            
            # Pattern 5: Standard with parentheses
            r'Ingredients:\s*\n([^\n]+(?:\([^)]+\))?(?:[,.]?\s*[^\n]+(?:\([^)]+\))?)*?)(?:\n\nAdditives|\nAdditives|\n\nAnalytical|\nAnalytical)',
            
            # Pattern 6: Meat-starting ingredients
            r'Ingredients\s*\n((?:Meat|Duck|Chicken)[^\n]+(?:\([^)]+\))?(?:[,.]?\s*[^\n]+)*)(?:\n\nAdditives|\nAdditives)',
            
            # Pattern 7: Protein-starting ingredients
            r'Ingredients:\s*\n((?:Duck|Chicken|Meat|Lamb|Beef|Turkey|Salmon|Fish)[^\n]+(?:\([^)]+\))?(?:[,.]?\s*[^\n]+)*)(?:\n\nAdditives|\nAdditives)',
            
            # Pattern 8: Relaxed - Capture from "Go to analytical constituents"
            r'Go to analytical constituents\s*\n(.*?)(?:Analytical constituents|$)',
            
            # Pattern 9: New pattern for specific cases
            r'Ingredients[:\s]*\n([^\n]+(?:\n[^\n]+){0,3})(?:\n\n|\nAnalytical|\nAdditives|$)',
            
            # Pattern 10: Another new pattern
            r'Composition[:\s]*\n([^\n]+(?:\([^)]+\))?(?:[,.]?\s*[^\n]+(?:\([^)]+\))?)*?)(?:\n\nAdditives|\nAdditives|\nAnalytical|\n\n)'
        ]
        
        # Try each pattern
        for i, pattern in enumerate(ingredients_patterns, 1):
            match = re.search(pattern, page_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match:
                ingredients = match.group(1).strip()
                
                # Skip navigation text
                if 'go to' in ingredients.lower() and i != 8:
                    continue
                
                # For Pattern 8, extract from captured content
                if i == 8 and ingredients:
                    inner_match = re.search(
                        r'Ingredients:?\s*\n([^\n]+(?:\([^)]+\))?(?:[,.]?\s*[^\n]+)*?)(?:\n\nAdditives|\nAdditives|$)',
                        ingredients, 
                        re.IGNORECASE | re.MULTILINE
                    )
                    if inner_match:
                        ingredients = inner_match.group(1).strip()
                
                # Validate ingredients
                if len(ingredients) > 30 and any(word in ingredients.lower() for word in 
                    ['meat', 'chicken', 'beef', 'fish', 'rice', 'wheat', 'maize', 
                     'protein', 'poultry', 'lamb', 'turkey', 'salmon', 'duck', 
                     'vegetables', 'cereals', 'meal', 'flour', '%']):
                    
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
        """Save to GCS using proven method"""
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
        """Main execution with orchestrator-style flow"""
        
        # Load products
        products = self.load_products()
        if not products:
            print("❌ No products to scrape")
            return
        
        print(f"\n🎯 Starting scraping of {len(products)} products\n")
        
        # Process each product
        for i, product in enumerate(products, 1):
            # Check for too many consecutive errors
            if self.stats['consecutive_errors'] >= 10:
                print("\n⚠️ Stopping due to 10 consecutive errors")
                break
            
            # Progress indicator
            print(f"[{i}/{len(products)}] {product['product_name'][:50]}...")
            
            self.stats['total'] += 1
            
            # Scrape the product
            result = self.scrape_product(product['product_url'])
            
            # Smart delay: shorter for skipped pages, normal for successful scrapes
            if i > 1:
                if 'error' in result and ('404' in result['error'] or 'No ingredients' in result['error']):
                    # Much shorter delay for pages we're skipping
                    delay = random.uniform(2, 5)
                    print(f"   ⏱️ Quick skip delay {delay:.1f}s...")
                else:
                    # Normal delay for successful scrapes
                    delay = random.uniform(self.min_delay, self.max_delay)
                    print(f"   ⏱️ Waiting {delay:.1f}s...")
                time.sleep(delay)
            
            # Add product metadata
            result['product_key'] = product['product_key']
            result['brand'] = product.get('brand')
            
            # Show result
            if 'error' in result:
                error_msg = result['error']
                if '404' in error_msg or 'Category page' in error_msg or 'No ingredients' in error_msg:
                    print(f"   ⏭️ Skipping: {result.get('skip_reason', error_msg)}")
                    # Don't count these as errors, they're expected
                else:
                    print(f"   ❌ Error: {error_msg}")
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
            
            # Every 10 products, print mini summary
            if i % 10 == 0:
                elapsed = datetime.now() - self.stats['session_start']
                if self.stats['total'] > 0:
                    success_rate = self.stats['with_ingredients'] / self.stats['total'] * 100
                    print(f"\n   --- Progress: {i}/{len(products)} | Success: {success_rate:.1f}% | Elapsed: {elapsed} ---\n")
        
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
            success_rate = self.stats['with_ingredients'] / self.stats['total'] * 100
            print(f"Success rate: {success_rate:.1f}%")
        
        print(f"\n📁 GCS folder: gs://{GCS_BUCKET}/{self.gcs_folder}/")
        print("=" * 50)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Scrape final 160 Zooplus products')
    parser.add_argument('--session', type=str, default='us1',
                       choices=['us1', 'gb1', 'de1', 'ca1', 'fr1'],
                       help='Session name (country code)')
    parser.add_argument('--start', type=int, default=0,
                       help='Start index in product list')
    parser.add_argument('--end', type=int, default=None,
                       help='End index in product list')
    
    args = parser.parse_args()
    
    # Create and run scraper
    scraper = Final160Scraper(
        session_name=args.session,
        start_idx=args.start,
        end_idx=args.end
    )
    scraper.run()

if __name__ == "__main__":
    main()