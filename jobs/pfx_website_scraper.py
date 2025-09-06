#!/usr/bin/env python3
"""
PetFoodExpert Website Scraper
Uses the correct website pagination structure to harvest all products
- All products: https://petfoodexpert.com/?page=X (317 pages)  
- Dry food: https://petfoodexpert.com/?moisture_level=dry&page=X (226 pages)
- Wet food: https://petfoodexpert.com/?moisture_level=wet&page=X (81 pages)
"""
import os
import sys
import json
import time
import random
import hashlib
import requests
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from urllib.parse import urljoin, urlparse

import yaml
from bs4 import BeautifulSoup
from supabase import create_client, Client
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from etl.normalize_foods import (
    parse_energy, parse_percent, parse_pack_size,
    tokenize_ingredients, check_contains_chicken,
    parse_price, normalize_currency, generate_fingerprint,
    normalize_form, normalize_life_stage, extract_gtin, clean_text,
    estimate_kcal_from_analytical, contains, derive_form, derive_life_stage
)
from etl.nutrition_parser import parse_nutrition_from_html

# Load environment variables
load_dotenv()

class PFXWebsiteScraper:
    def __init__(self):
        """Initialize the website scraper"""
        self.session = self._setup_session()
        self.supabase = self._setup_supabase()
        
        # Configuration
        self.config = {
            'base_url': 'https://petfoodexpert.com',
            'rate_limit_seconds': 2.0,  # Be respectful
            'timeout': 30,
            'max_pages_per_category': 50  # Start with smaller batch for testing
        }
        
        # Track discovered URLs to avoid duplicates
        self.discovered_urls: Set[str] = set()
        
        self.stats = {
            'pages_scraped': 0,
            'products_discovered': 0,
            'products_processed': 0,
            'products_new': 0,
            'products_updated': 0,
            'products_skipped': 0,
            'nutrition_extracted': 0,
            'errors': 0
        }

    def _setup_session(self) -> requests.Session:
        """Setup requests session with headers"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; LupitoBot/1.0)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive'
        })
        return session

    def _setup_supabase(self) -> Client:
        """Setup Supabase client"""
        return create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_KEY')
        )

    def _rate_limit(self):
        """Apply rate limiting"""
        time.sleep(self.config['rate_limit_seconds'] + random.uniform(-0.3, 0.3))

    def discover_product_urls_from_page(self, page_url: str) -> List[str]:
        """Extract product URLs from a listing page"""
        try:
            self._rate_limit()
            
            print(f"  📄 Scraping page: {page_url}")
            response = self.session.get(page_url, timeout=self.config['timeout'])
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            product_urls = []
            
            # Look for product links - adjust selectors based on PFX HTML structure
            # Common patterns for product links
            link_selectors = [
                'a[href*="/food/"]',  # Most likely pattern
                '.product-link',
                '.product-card a',
                'a[href*="/product/"]',
                '.food-item a'
            ]
            
            for selector in link_selectors:
                links = soup.select(selector)
                for link in links:
                    href = link.get('href')
                    if href:
                        # Convert relative URLs to absolute
                        if href.startswith('/'):
                            full_url = urljoin(self.config['base_url'], href)
                        elif href.startswith('http'):
                            full_url = href
                        else:
                            continue
                        
                        # Filter for product URLs
                        if '/food/' in full_url or '/product/' in full_url:
                            if full_url not in self.discovered_urls:
                                product_urls.append(full_url)
                                self.discovered_urls.add(full_url)
            
            self.stats['pages_scraped'] += 1
            self.stats['products_discovered'] += len(product_urls)
            
            print(f"    ✅ Found {len(product_urls)} new product URLs")
            return product_urls
            
        except Exception as e:
            print(f"    ❌ Error scraping page {page_url}: {e}")
            self.stats['errors'] += 1
            return []

    def discover_all_product_urls(self) -> List[str]:
        """Discover all product URLs from all categories"""
        print("🔍 Discovering product URLs from website pagination...")
        
        all_urls = []
        
        # Define categories to scrape
        categories = [
            {
                'name': 'All Products',
                'url_template': f"{self.config['base_url']}/?page={{page}}",
                'max_pages': min(self.config['max_pages_per_category'], 317)
            },
            # Uncomment these for full harvest later
            # {
            #     'name': 'Dry Food',
            #     'url_template': f"{self.config['base_url']}/?moisture_level=dry&page={{page}}",
            #     'max_pages': min(self.config['max_pages_per_category'], 226)
            # },
            # {
            #     'name': 'Wet Food', 
            #     'url_template': f"{self.config['base_url']}/?moisture_level=wet&page={{page}}",
            #     'max_pages': min(self.config['max_pages_per_category'], 81)
            # }
        ]
        
        for category in categories:
            print(f"\n📂 Discovering {category['name']} (max {category['max_pages']} pages)...")
            
            for page in range(1, category['max_pages'] + 1):
                page_url = category['url_template'].format(page=page)
                page_urls = self.discover_product_urls_from_page(page_url)
                all_urls.extend(page_urls)
                
                print(f"    📊 Page {page}/{category['max_pages']}: {len(page_urls)} products, Total: {len(self.discovered_urls)}")
                
                # Break if we find no products (reached end)
                if not page_urls:
                    print(f"    ✅ No products found on page {page}, stopping category")
                    break
        
        print(f"\n🎯 Discovery complete: {len(self.discovered_urls)} unique product URLs found")
        return list(self.discovered_urls)

    def scrape_product(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape a single product page"""
        try:
            self._rate_limit()
            
            response = self.session.get(url, timeout=self.config['timeout'])
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract brand and product name from title or headings
            title = soup.find('title')
            title_text = title.get_text(strip=True) if title else ''
            
            # Try to extract brand and name from page structure
            brand = None
            product_name = None
            
            # Look for common heading patterns
            h1 = soup.find('h1')
            if h1:
                h1_text = h1.get_text(strip=True)
                # Try to split into brand and name
                words = h1_text.split()
                if len(words) >= 2:
                    brand = words[0]
                    product_name = ' '.join(words[1:])
            
            # Fallback to title parsing
            if not brand or not product_name:
                # Remove "- PetFoodExpert" or similar suffixes
                clean_title = re.sub(r'\s*-\s*PetFoodExpert.*$', '', title_text, flags=re.IGNORECASE)
                words = clean_title.split()
                if len(words) >= 2:
                    brand = words[0]
                    product_name = ' '.join(words[1:])
            
            if not brand or not product_name:
                print(f"    ⚠️  Could not extract brand/name from {url}")
                return None
            
            # Extract nutrition using our parser
            nutrition_data = parse_nutrition_from_html(response.text)
            
            # Extract other product details from page content
            ingredients = None
            form = None
            life_stage = None
            
            # Look for ingredients text
            page_text = soup.get_text().lower()
            if 'ingredients:' in page_text or 'composition:' in page_text:
                # Extract ingredients section
                for pattern in ['ingredients:', 'composition:']:
                    if pattern in page_text:
                        start = page_text.find(pattern)
                        if start != -1:
                            # Extract next 500 characters and clean up
                            ingredients_text = page_text[start:start+500]
                            # Take until next major section
                            for end_marker in ['\n\n', 'analytical', 'nutritional', 'feeding']:
                                if end_marker in ingredients_text[20:]:  # Skip first 20 chars
                                    ingredients_text = ingredients_text[:ingredients_text.find(end_marker, 20)]
                                    break
                            ingredients = clean_text(ingredients_text.replace(pattern, ''))
                            break
            
            # Derive form and life stage
            if ingredients:
                form = derive_form(ingredients)
                life_stage = derive_life_stage(ingredients)
            
            # If still no form, try to derive from URL or title
            if not form:
                url_lower = url.lower()
                title_lower = title_text.lower()
                if 'dry' in url_lower or 'dry' in title_lower:
                    form = 'dry'
                elif 'wet' in url_lower or 'wet' in title_lower:
                    form = 'wet'
                elif 'raw' in url_lower or 'raw' in title_lower:
                    form = 'raw'
            
            # Build product data
            product_data = {
                'source_domain': 'petfoodexpert.com',
                'source_url': url,
                'brand': clean_text(brand),
                'product_name': clean_text(product_name),
                'form': form,
                'life_stage': life_stage,
                'ingredients_raw': ingredients,
                'available_countries': ['UK', 'EU']
            }
            
            # Add nutrition data
            if nutrition_data:
                product_data.update(nutrition_data)
                self.stats['nutrition_extracted'] += 1
                print(f"    ✅ Nutrition: kcal={nutrition_data.get('kcal_per_100g')}, protein={nutrition_data.get('protein_percent')}%")
            else:
                print(f"    ⚠️  No nutrition data found")
            
            # Add derived fields
            if ingredients:
                product_data['ingredients_tokens'] = tokenize_ingredients(ingredients)
                product_data['contains_chicken'] = check_contains_chicken(ingredients)
            
            return product_data
            
        except Exception as e:
            print(f"    ❌ Error scraping product {url}: {e}")
            self.stats['errors'] += 1
            return None

    def save_product(self, product_data: Dict[str, Any]) -> bool:
        """Save product to database"""
        try:
            # Generate fingerprint
            fingerprint = generate_fingerprint(
                product_data['brand'],
                product_data['product_name'],
                product_data.get('ingredients_raw', '')
            )
            product_data['fingerprint'] = fingerprint
            
            # Check for existing record
            existing = self.supabase.table('food_candidates')\
                .select('id')\
                .eq('fingerprint', fingerprint)\
                .execute()
            
            if existing.data:
                # Update existing
                update_data = {k: v for k, v in product_data.items() 
                              if k not in ['fingerprint', 'first_seen_at']}
                update_data['last_seen_at'] = datetime.now().isoformat()
                
                self.supabase.table('food_candidates')\
                    .update(update_data)\
                    .eq('fingerprint', fingerprint)\
                    .execute()
                
                self.stats['products_updated'] += 1
                print(f"    ✅ Updated existing product")
            else:
                # Insert new
                product_data['first_seen_at'] = datetime.now().isoformat()
                product_data['last_seen_at'] = datetime.now().isoformat()
                
                self.supabase.table('food_candidates').insert(product_data).execute()
                self.stats['products_new'] += 1
                print(f"    ✅ Added new product")
            
            self.stats['products_processed'] += 1
            return True
            
        except Exception as e:
            print(f"    ❌ Database error: {e}")
            self.stats['errors'] += 1
            return False

    def run_harvest(self):
        """Run the complete harvest"""
        print("🚀 Starting PetFoodExpert Website Harvest")
        print("="*60)
        
        # Discover all product URLs
        all_urls = self.discover_all_product_urls()
        
        if not all_urls:
            print("❌ No product URLs discovered. Exiting.")
            return
        
        print(f"\n📋 Processing {len(all_urls)} products...")
        print("="*60)
        
        # Process products
        for i, url in enumerate(all_urls, 1):
            print(f"[{i}/{len(all_urls)}] Processing: {url}")
            
            product_data = self.scrape_product(url)
            if product_data:
                self.save_product(product_data)
                print(f"  📦 {product_data['brand']} {product_data['product_name']}")
            else:
                self.stats['products_skipped'] += 1
            
            # Progress updates every 20 products
            if i % 20 == 0:
                self._print_progress()
        
        self._print_final_report()

    def _print_progress(self):
        """Print progress update"""
        print(f"\n📈 Progress: {self.stats['products_processed']} processed, "
              f"{self.stats['products_new']} new, {self.stats['products_updated']} updated, "
              f"{self.stats['nutrition_extracted']} with nutrition\n")

    def _print_final_report(self):
        """Print final harvest report"""
        print("\n" + "="*60)
        print("🎯 PETFOODEXPERT WEBSITE HARVEST REPORT")
        print("="*60)
        print(f"Pages scraped:          {self.stats['pages_scraped']}")
        print(f"Products discovered:    {self.stats['products_discovered']}")
        print(f"Products processed:     {self.stats['products_processed']}")
        print(f"New products added:     {self.stats['products_new']}")
        print(f"Products updated:       {self.stats['products_updated']}")
        print(f"Products skipped:       {self.stats['products_skipped']}")
        print(f"Nutrition extracted:    {self.stats['nutrition_extracted']}")
        print(f"Errors encountered:     {self.stats['errors']}")
        
        if self.stats['products_processed'] > 0:
            nutrition_rate = (self.stats['nutrition_extracted'] / self.stats['products_processed']) * 100
            print(f"Nutrition success rate: {nutrition_rate:.1f}%")
        
        print("="*60)

def main():
    scraper = PFXWebsiteScraper()
    scraper.run_harvest()

if __name__ == '__main__':
    main()