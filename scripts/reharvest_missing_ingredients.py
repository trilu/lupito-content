#!/usr/bin/env python3
"""
Re-harvest missing ingredients data for brands with partial enrichment
Focuses on Bozita, Belcando, Brit which have URLs but missing ingredients
"""

import os
import re
import json
import time
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from supabase import create_client
from dotenv import load_dotenv
import yaml

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_KEY')
)

class IngredientsHarvester:
    def __init__(self, brand: str):
        self.brand = brand
        self.profile = self._load_profile(brand)
        self.api_key = os.getenv('SCRAPING_BEE')
        self.stats = {
            'products_checked': 0,
            'ingredients_found': 0,
            'ingredients_updated': 0,
            'errors': []
        }
    
    def _load_profile(self, brand: str) -> Dict:
        """Load brand profile"""
        profile_path = Path(f"profiles/manufacturers/{brand.lower()}.yaml")
        if profile_path.exists():
            with open(profile_path, 'r') as f:
                return yaml.safe_load(f)
        return {}
    
    def fetch_with_scrapingbee(self, url: str) -> Optional[str]:
        """Fetch page using ScrapingBee API for JavaScript-heavy sites"""
        
        # Determine if we need ScrapingBee based on brand
        needs_js = self.brand.lower() in ['bozita', 'belcando']
        
        if needs_js and self.api_key:
            # Use ScrapingBee for JS-heavy sites
            params = {
                'api_key': self.api_key,
                'url': url,
                'render_js': 'true',
                'premium_proxy': 'true',
                'country_code': 'de' if self.brand.lower() in ['belcando'] else 'gb',
                'wait': '2000'
            }
            
            try:
                response = requests.get(
                    'https://app.scrapingbee.com/api/v1/',
                    params=params,
                    timeout=30
                )
                
                if response.status_code == 200:
                    return response.text
                else:
                    print(f"    ScrapingBee error {response.status_code} for {url}")
                    return None
            except Exception as e:
                print(f"    ScrapingBee exception: {e}")
                return None
        else:
            # Direct fetch for simple sites
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    return response.text
                return None
            except Exception as e:
                print(f"    Direct fetch error: {e}")
                return None
    
    def extract_ingredients(self, html: str, url: str) -> Optional[str]:
        """Extract ingredients from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # First check for downloadable files (PDF, CSV)
        download_link = self._find_download_link(soup, url)
        if download_link:
            print(f"    Found download link: {download_link}")
            # For now, just note it - could implement PDF parsing later
            
        # Try profile-specific selectors first
        if self.profile and 'pdp_selectors' in self.profile:
            ingredients_selectors = self.profile['pdp_selectors'].get('ingredients', {})
            
            # Try CSS selectors
            for selector in ingredients_selectors.get('css', []):
                elements = soup.select(selector)
                for elem in elements:
                    text = elem.get_text(strip=True)
                    # Better validation - must contain common ingredient words
                    if text and len(text) > 50 and self._is_likely_ingredients(text):
                        return text
        
        # Fallback: Common patterns
        patterns = [
            # Look for "Ingredients" heading followed by content
            lambda: self._find_by_heading(soup, ['ingredients', 'composition', 'zutaten', 'sammansättning', 'analytical constituents']),
            # Look for specific class/id patterns
            lambda: self._find_by_class_patterns(soup),
            # Look for tables with ingredients
            lambda: self._find_in_tables(soup),
            # Look for meta descriptions with ingredients
            lambda: self._find_in_meta(soup)
        ]
        
        for pattern in patterns:
            result = pattern()
            if result and len(result) > 50 and self._is_likely_ingredients(result):
                return result
        
        return None
    
    def _find_by_heading(self, soup: BeautifulSoup, keywords: List[str]) -> Optional[str]:
        """Find ingredients by looking for heading keywords"""
        for keyword in keywords:
            # Check h2, h3, h4 headings
            for tag in ['h2', 'h3', 'h4', 'strong', 'b']:
                headings = soup.find_all(tag, string=re.compile(keyword, re.IGNORECASE))
                for heading in headings:
                    # Get next sibling or parent's next element
                    next_elem = heading.find_next_sibling()
                    if not next_elem:
                        parent = heading.parent
                        if parent:
                            next_elem = parent.find_next_sibling()
                    
                    if next_elem:
                        text = next_elem.get_text(strip=True)
                        if text and len(text) > 50:
                            return text
        return None
    
    def _find_by_class_patterns(self, soup: BeautifulSoup) -> Optional[str]:
        """Find ingredients by common class patterns"""
        patterns = [
            'ingredients', 'composition', 'product-ingredients',
            'product-composition', 'analytical-constituents'
        ]
        
        for pattern in patterns:
            # Check divs and paragraphs
            for tag in ['div', 'p', 'span', 'section']:
                elements = soup.find_all(tag, class_=re.compile(pattern, re.IGNORECASE))
                for elem in elements:
                    text = elem.get_text(strip=True)
                    if text and len(text) > 50 and not text.startswith('http'):
                        return text
        
        return None
    
    def _find_download_link(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """Find downloadable files with product information"""
        # Look for PDF/CSV download links
        for link in soup.find_all('a', href=True):
            href = link['href'].lower()
            text = link.get_text(lower=True)
            
            if any(ext in href for ext in ['.pdf', '.csv', '.xlsx']):
                if any(word in text for word in ['download', 'datasheet', 'specification', 'info']):
                    return urljoin(base_url, link['href'])
        
        return None
    
    def _is_likely_ingredients(self, text: str) -> bool:
        """Check if text is likely to contain ingredients"""
        text_lower = text.lower()
        
        # Must NOT start with common non-ingredient phrases
        bad_starts = ['free delivery', 'contact us', 'my account', 'shopping cart', 
                      'cookie', 'privacy', 'terms', 'copyright', 'menu', 'search']
        if any(text_lower.startswith(phrase) for phrase in bad_starts):
            return False
        
        # Should contain common ingredient indicators
        ingredient_words = ['meat', 'chicken', 'beef', 'lamb', 'fish', 'rice', 'wheat',
                          'protein', 'fat', 'fiber', 'ash', 'moisture', 'vitamin',
                          'mineral', 'corn', 'barley', 'vegetable', '%', 'mg/kg']
        
        matches = sum(1 for word in ingredient_words if word in text_lower)
        return matches >= 2  # At least 2 ingredient-related words
    
    def _find_in_tables(self, soup: BeautifulSoup) -> Optional[str]:
        """Find ingredients in tables"""
        tables = soup.find_all('table')
        
        for table in tables:
            # Check if table contains ingredient-related headers
            headers = table.find_all(['th', 'td'])
            header_text = ' '.join(h.get_text(lower=True) for h in headers[:5])
            
            if any(word in header_text for word in ['ingredient', 'composition', 'analysis']):
                # Extract all table content
                rows = table.find_all('tr')
                content = []
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    row_text = ' '.join(cell.get_text(strip=True) for cell in cells)
                    if row_text:
                        content.append(row_text)
                
                full_text = '; '.join(content)
                if len(full_text) > 50:
                    return full_text
        
        return None
    
    def _find_in_meta(self, soup: BeautifulSoup) -> Optional[str]:
        """Find ingredients in meta tags or structured data"""
        # Check meta description
        meta = soup.find('meta', attrs={'name': 'description'})
        if meta:
            content = meta.get('content', '')
            if 'ingredients:' in content.lower() or 'composition:' in content.lower():
                return content
        
        # Check structured data
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    # Check for ingredients in various fields
                    for key in ['description', 'ingredients', 'composition']:
                        if key in data and len(str(data[key])) > 50:
                            return str(data[key])
            except:
                continue
        
        return None
    
    def harvest_missing_ingredients(self, limit: int = None):
        """Harvest missing ingredients for products with URLs"""
        
        print(f"\n=== HARVESTING INGREDIENTS FOR {self.brand.upper()} ===")
        
        # Get products missing ingredients but having URLs
        response = supabase.table('foods_canonical').select('*').eq('brand', self.brand).execute()
        products = response.data
        
        # Filter to products with URL but no ingredients
        candidates = [
            p for p in products 
            if p.get('product_url') and not p.get('ingredients_raw')
        ]
        
        if limit:
            candidates = candidates[:limit]
        
        print(f"Found {len(candidates)} products needing ingredients")
        
        updates = []
        
        for i, product in enumerate(candidates, 1):
            url = product['product_url']
            name = product['product_name']
            
            print(f"\n[{i}/{len(candidates)}] {name}")
            print(f"  URL: {url}")
            
            self.stats['products_checked'] += 1
            
            # Add delay to be respectful
            if i > 1:
                time.sleep(2)
            
            # Fetch page
            html = self.fetch_with_scrapingbee(url)
            
            if not html:
                print("  ❌ Failed to fetch page")
                self.stats['errors'].append(f"Fetch failed: {url}")
                continue
            
            # Extract ingredients
            ingredients = self.extract_ingredients(html, url)
            
            if ingredients:
                print(f"  ✅ Found ingredients: {ingredients[:100]}...")
                self.stats['ingredients_found'] += 1
                
                updates.append({
                    'product_key': product['product_key'],
                    'ingredients_raw': ingredients,
                    'ingredients_source': 'manufacturer',  # Changed to valid value
                    'ingredients_language': 'en'
                })
            else:
                print("  ⚠️  No ingredients found")
        
        # Update database
        if updates:
            print(f"\n=== UPDATING DATABASE ===")
            print(f"Updating {len(updates)} products with ingredients...")
            
            for update in updates:
                try:
                    response = supabase.table('foods_canonical').update({
                        'ingredients_raw': update['ingredients_raw'],
                        'ingredients_source': update['ingredients_source'],
                        'ingredients_language': update['ingredients_language']
                    }).eq('product_key', update['product_key']).execute()
                    
                    self.stats['ingredients_updated'] += 1
                    print(f"  Updated: {update['product_key']}")
                except Exception as e:
                    print(f"  Error updating {update['product_key']}: {e}")
                    self.stats['errors'].append(f"Update failed: {update['product_key']}")
        
        # Print summary
        print(f"\n=== SUMMARY FOR {self.brand} ===")
        print(f"Products checked: {self.stats['products_checked']}")
        print(f"Ingredients found: {self.stats['ingredients_found']}")
        print(f"Products updated: {self.stats['ingredients_updated']}")
        print(f"Errors: {len(self.stats['errors'])}")
        
        return self.stats

def main():
    import sys
    
    # Brands to process
    brands = ['Bozita', 'Belcando', 'Brit']
    
    # Check if specific brand requested
    if len(sys.argv) > 1:
        requested_brand = sys.argv[1]
        if requested_brand in brands:
            brands = [requested_brand]
    
    # Check for limit
    limit = None
    if '--limit' in sys.argv:
        try:
            idx = sys.argv.index('--limit')
            limit = int(sys.argv[idx + 1])
        except:
            limit = 5
    
    print("="*60)
    print("INGREDIENTS RE-HARVESTING")
    print("="*60)
    print(f"Brands to process: {', '.join(brands)}")
    if limit:
        print(f"Limit: {limit} products per brand")
    print()
    
    all_stats = {}
    
    for brand in brands:
        harvester = IngredientsHarvester(brand)
        stats = harvester.harvest_missing_ingredients(limit=limit)
        all_stats[brand] = stats
    
    # Final summary
    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)
    
    total_updated = sum(s['ingredients_updated'] for s in all_stats.values())
    total_checked = sum(s['products_checked'] for s in all_stats.values())
    
    for brand, stats in all_stats.items():
        print(f"\n{brand}:")
        print(f"  Updated: {stats['ingredients_updated']}/{stats['products_checked']}")
    
    print(f"\nTotal products updated: {total_updated}/{total_checked}")
    print("\n✅ Re-harvesting completed!")

if __name__ == "__main__":
    main()