#!/usr/bin/env python3
"""
Enrich products directly from manufacturer websites using ScrapingBee
Focus on high-value brands with many products
"""

import os
import re
import json
import time
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse, quote
from bs4 import BeautifulSoup
from supabase import create_client
from dotenv import load_dotenv
from google.cloud import storage

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_KEY')
)

# GCS setup for storing raw HTML
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = './secrets/gcp-sa.json'
try:
    storage_client = storage.Client()
    bucket = storage_client.bucket('lupito-content-raw-eu')
except:
    bucket = None
    print("Warning: GCS not configured, will not store raw HTML")

class ManufacturerEnricher:
    def __init__(self, brand: str, base_url: str):
        self.brand = brand
        self.base_url = base_url
        self.api_key = os.getenv('SCRAPING_BEE')
        self.session = requests.Session()
        self.discovered_products = []
        self.stats = {
            'products_found': 0,
            'products_enriched': 0,
            'new_products_added': 0,
            'errors': []
        }
    
    def search_product_on_site(self, product_name: str) -> Optional[str]:
        """Search for a product on the manufacturer's website"""
        
        # Clean product name for search
        search_query = re.sub(r'[^\w\s]', ' ', product_name)
        search_query = ' '.join(search_query.split())
        
        # Common search URL patterns
        search_patterns = [
            f"{self.base_url}/search?q={quote(search_query)}",
            f"{self.base_url}/search/{quote(search_query)}",
            f"{self.base_url}/?s={quote(search_query)}",
            f"{self.base_url}/products?search={quote(search_query)}"
        ]
        
        for search_url in search_patterns:
            html = self.fetch_page(search_url)
            if html:
                # Look for product links in search results
                soup = BeautifulSoup(html, 'html.parser')
                product_links = self._find_product_links(soup, product_name)
                if product_links:
                    return product_links[0]  # Return first match
        
        return None
    
    def _find_product_links(self, soup: BeautifulSoup, product_name: str) -> List[str]:
        """Find product links that match the product name"""
        links = []
        name_words = product_name.lower().split()
        
        # Look for links containing product name
        for link in soup.find_all('a', href=True):
            href = link['href']
            link_text = link.get_text(strip=True).lower()
            
            # Check if link text contains most of the product name words
            matches = sum(1 for word in name_words if word in link_text)
            if matches >= len(name_words) * 0.7:  # 70% match
                full_url = urljoin(self.base_url, href)
                if full_url not in links:
                    links.append(full_url)
        
        return links
    
    def fetch_page(self, url: str) -> Optional[str]:
        """Fetch page with ScrapingBee for JS-heavy sites"""
        
        if not self.api_key:
            # Fallback to direct fetch
            try:
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    return response.text
            except:
                pass
            return None
        
        # Use ScrapingBee
        params = {
            'api_key': self.api_key,
            'url': url,
            'render_js': 'true',
            'premium_proxy': 'true',
            'wait': '3000'
        }
        
        # Set country based on brand
        country_map = {
            'bozita': 'se',
            'belcando': 'de',
            'brit': 'cz',
            'burns': 'gb',
            'royal canin': 'gb'
        }
        params['country_code'] = country_map.get(self.brand.lower(), 'gb')
        
        try:
            response = requests.get(
                'https://app.scrapingbee.com/api/v1/',
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                # Store raw HTML in GCS if available
                if bucket:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    blob_name = f"manufacturers/{self.brand}/{timestamp}_{urlparse(url).path.replace('/', '_')}.html"
                    blob = bucket.blob(blob_name)
                    blob.upload_from_string(response.text, content_type='text/html')
                
                return response.text
            else:
                print(f"  ScrapingBee error {response.status_code}")
                return None
                
        except Exception as e:
            print(f"  Error fetching {url}: {e}")
            return None
    
    def extract_product_data(self, html: str) -> Dict:
        """Extract product data from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        
        data = {
            'ingredients': None,
            'protein': None,
            'fat': None,
            'fiber': None,
            'ash': None,
            'moisture': None,
            'description': None
        }
        
        # Extract ingredients
        ingredients = self._extract_ingredients(soup)
        if ingredients:
            data['ingredients'] = ingredients
        
        # Extract nutritional values
        nutrition = self._extract_nutrition(soup)
        data.update(nutrition)
        
        # Extract description
        description = self._extract_description(soup)
        if description:
            data['description'] = description
        
        return data
    
    def _extract_ingredients(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract ingredients from page"""
        
        # Strategy 1: Look for ingredients section
        keywords = ['ingredients', 'composition', 'zutaten', 'sammansättning', 'složení']
        
        for keyword in keywords:
            # Check headings
            for tag in ['h2', 'h3', 'h4', 'strong']:
                elements = soup.find_all(tag, string=re.compile(keyword, re.IGNORECASE))
                for elem in elements:
                    # Get next element
                    next_elem = elem.find_next_sibling()
                    if next_elem:
                        text = next_elem.get_text(strip=True)
                        if len(text) > 50 and not text.startswith('http'):
                            return text
                    
                    # Or get parent's next element
                    parent = elem.parent
                    if parent:
                        text = parent.get_text(strip=True)
                        if len(text) > 100 and keyword.lower() in text.lower():
                            # Extract part after keyword
                            parts = text.lower().split(keyword.lower())
                            if len(parts) > 1:
                                ingredients = parts[1].strip()
                                if len(ingredients) > 50:
                                    return ingredients
        
        # Strategy 2: Look for common patterns in divs/sections
        for elem in soup.find_all(['div', 'section', 'p']):
            text = elem.get_text(strip=True)
            if len(text) > 100 and len(text) < 2000:
                text_lower = text.lower()
                # Check if it contains ingredient-like content
                if ('meat' in text_lower or 'chicken' in text_lower or 'rice' in text_lower) and \
                   ('protein' in text_lower or '%' in text_lower or 'vitamin' in text_lower):
                    return text
        
        return None
    
    def _extract_nutrition(self, soup: BeautifulSoup) -> Dict:
        """Extract nutritional values"""
        nutrition = {}
        
        # Look for analytical constituents / guaranteed analysis
        text = soup.get_text()
        
        # Patterns for extracting percentages
        patterns = {
            'protein': r'(?:crude\s+)?protein[:\s]+([0-9.]+)\s*%',
            'fat': r'(?:crude\s+)?fat[:\s]+([0-9.]+)\s*%',
            'fiber': r'(?:crude\s+)?fib(?:re|er)[:\s]+([0-9.]+)\s*%',
            'ash': r'(?:crude\s+)?ash[:\s]+([0-9.]+)\s*%',
            'moisture': r'moisture[:\s]+([0-9.]+)\s*%'
        }
        
        for nutrient, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value = float(match.group(1))
                    nutrition[nutrient] = value
                except:
                    pass
        
        return nutrition
    
    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract product description"""
        
        # Look for description meta tag first
        meta = soup.find('meta', attrs={'name': 'description'})
        if meta:
            content = meta.get('content', '')
            if len(content) > 50:
                return content
        
        # Look for product description section
        for elem in soup.find_all(['div', 'section'], class_=re.compile('description|product-info', re.IGNORECASE)):
            text = elem.get_text(strip=True)
            if len(text) > 100 and len(text) < 1000:
                return text
        
        return None
    
    def enrich_products(self, limit: int = None):
        """Enrich products for this brand"""
        
        print(f"\n=== ENRICHING {self.brand.upper()} ===")
        print(f"Base URL: {self.base_url}")
        
        # Get products needing enrichment
        response = supabase.table('foods_canonical').select('*').eq('brand', self.brand).execute()
        products = response.data
        
        # Filter to products missing ingredients
        candidates = [
            p for p in products 
            if not p.get('ingredients_raw')
        ]
        
        if limit:
            candidates = candidates[:limit]
        
        print(f"Found {len(candidates)} products needing enrichment")
        
        for i, product in enumerate(candidates, 1):
            name = product['product_name']
            print(f"\n[{i}/{len(candidates)}] {name}")
            
            # Add delay to be respectful
            if i > 1:
                time.sleep(3)
            
            # Search for product on manufacturer site
            product_url = self.search_product_on_site(name)
            
            if not product_url:
                print("  ❌ Product not found on manufacturer site")
                continue
            
            print(f"  Found: {product_url}")
            
            # Fetch product page
            html = self.fetch_page(product_url)
            if not html:
                print("  ❌ Failed to fetch product page")
                continue
            
            # Extract data
            data = self.extract_product_data(html)
            
            # Update database if we found useful data
            updates = {}
            
            if data['ingredients']:
                updates['ingredients_raw'] = data['ingredients']
                updates['ingredients_source'] = 'manufacturer'
                print(f"  ✅ Ingredients: {data['ingredients'][:100]}...")
            
            if data['protein']:
                updates['protein_percent'] = data['protein']
            if data['fat']:
                updates['fat_percent'] = data['fat']
            if data['fiber']:
                updates['fiber_percent'] = data['fiber']
            if data['ash']:
                updates['ash_percent'] = data['ash']
            if data['moisture']:
                updates['moisture_percent'] = data['moisture']
            
            if not updates.get('product_url'):
                updates['product_url'] = product_url
            
            if updates:
                try:
                    response = supabase.table('foods_canonical').update(updates).eq(
                        'product_key', product['product_key']
                    ).execute()
                    
                    self.stats['products_enriched'] += 1
                    print(f"  ✅ Updated with {len(updates)} fields")
                except Exception as e:
                    print(f"  ❌ Update failed: {e}")
                    self.stats['errors'].append(str(e))
        
        # Print summary
        print(f"\n=== SUMMARY FOR {self.brand} ===")
        print(f"Products enriched: {self.stats['products_enriched']}/{len(candidates)}")
        print(f"Errors: {len(self.stats['errors'])}")
        
        return self.stats

def main():
    # Priority brands with their official websites
    brands = [
        ('Bozita', 'https://www.bozita.com'),
        ('Belcando', 'https://www.belcando.de'),
        ('Brit', 'https://www.brit-petfood.com'),
        ('Burns', 'https://burnspet.co.uk'),
        ('Royal Canin', 'https://www.royalcanin.com/uk')
    ]
    
    import sys
    
    # Check for specific brand
    if len(sys.argv) > 1:
        brand_name = sys.argv[1]
        brands = [(b, u) for b, u in brands if b.lower() == brand_name.lower()]
    
    # Check for limit
    limit = 5  # Default small limit for testing
    if '--all' in sys.argv:
        limit = None
    
    print("="*60)
    print("MANUFACTURER ENRICHMENT")
    print("="*60)
    print(f"Brands to process: {[b for b, _ in brands]}")
    print(f"Limit: {limit if limit else 'No limit'}")
    
    for brand, url in brands:
        enricher = ManufacturerEnricher(brand, url)
        enricher.enrich_products(limit=limit)
        
        # Add delay between brands
        if len(brands) > 1:
            time.sleep(5)
    
    print("\n✅ Enrichment completed!")

if __name__ == "__main__":
    main()