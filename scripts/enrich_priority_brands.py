#!/usr/bin/env python3
"""
Enrich top priority brands by fetching data from their official websites
Focus on Royal Canin, Hill's, Eukanuba, and other high-impact brands
"""

import os
import re
import json
import time
import requests
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse, quote
from bs4 import BeautifulSoup
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_KEY')
)

class PriorityBrandEnricher:
    def __init__(self):
        self.supabase = supabase
        self.api_key = os.getenv('SCRAPING_BEE')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def analyze_brand_needs(self) -> List[Dict]:
        """Analyze which brands need the most enrichment"""
        
        print("Analyzing brand enrichment needs...")
        
        # Get all products grouped by brand
        response = supabase.table('foods_canonical').select('brand, ingredients_raw, protein_percent, product_url').execute()
        
        brand_stats = {}
        
        for product in response.data:
            brand = product.get('brand')
            if not brand:
                continue
            
            if brand not in brand_stats:
                brand_stats[brand] = {
                    'total': 0,
                    'has_ingredients': 0,
                    'has_protein': 0,
                    'has_url': 0
                }
            
            brand_stats[brand]['total'] += 1
            
            if product.get('ingredients_raw'):
                brand_stats[brand]['has_ingredients'] += 1
            if product.get('protein_percent'):
                brand_stats[brand]['has_protein'] += 1
            if product.get('product_url'):
                brand_stats[brand]['has_url'] += 1
        
        # Calculate needs score (products without ingredients)
        brand_needs = []
        
        for brand, stats in brand_stats.items():
            if stats['total'] >= 20:  # Only brands with significant products
                needs_ingredients = stats['total'] - stats['has_ingredients']
                needs_score = needs_ingredients * (stats['total'] / 100)  # Weight by total products
                
                brand_needs.append({
                    'brand': brand,
                    'total_products': stats['total'],
                    'missing_ingredients': needs_ingredients,
                    'missing_protein': stats['total'] - stats['has_protein'],
                    'missing_url': stats['total'] - stats['has_url'],
                    'needs_score': needs_score,
                    'completion_rate': stats['has_ingredients'] / stats['total'] if stats['total'] > 0 else 0
                })
        
        # Sort by needs score
        brand_needs.sort(key=lambda x: x['needs_score'], reverse=True)
        
        return brand_needs
    
    def enrich_royal_canin(self):
        """Special handler for Royal Canin products"""
        
        print("\n=== ENRICHING ROYAL CANIN ===")
        
        # Royal Canin has a structured website with product data
        base_url = "https://www.royalcanin.com/uk/dogs/products"
        
        # Get Royal Canin products needing enrichment
        response = supabase.table('foods_canonical').select('*').eq('brand', 'Royal Canin').execute()
        products = response.data
        
        needs_enrichment = [p for p in products if not p.get('ingredients_raw')]
        
        print(f"Found {len(needs_enrichment)} products needing enrichment")
        
        updated = 0
        
        for product in needs_enrichment[:10]:  # Limit for testing
            name = product['product_name']
            print(f"\nProcessing: {name}")
            
            # Build search URL
            search_name = re.sub(r'[^\w\s]', '', name).lower()
            search_url = f"{base_url}/search?q={quote(search_name)}"
            
            # For Royal Canin, we can often build direct URLs
            # Pattern: /uk/dogs/products/[product-line]/[product-name]
            if 'Adult' in name:
                product_line = 'breed-health-nutrition'
            elif 'Puppy' in name or 'Junior' in name:
                product_line = 'puppy'
            elif 'Veterinary' in name or 'Prescription' in name:
                product_line = 'veterinary-health-nutrition'
            else:
                product_line = 'size-health-nutrition'
            
            # Create slug from product name
            slug = re.sub(r'[^\w\s-]', '', name.lower())
            slug = re.sub(r'\s+', '-', slug)
            
            product_url = f"https://www.royalcanin.com/uk/dogs/products/{product_line}/{slug}"
            
            # Try to fetch the page
            try:
                response = self.session.get(product_url, timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract ingredients
                    ingredients = self._extract_royal_canin_ingredients(soup)
                    
                    if ingredients:
                        # Update database
                        update_data = {
                            'ingredients_raw': ingredients,
                            'ingredients_source': 'manufacturer',
                            'product_url': product_url
                        }
                        
                        # Also extract nutrition if available
                        nutrition = self._extract_royal_canin_nutrition(soup)
                        update_data.update(nutrition)
                        
                        try:
                            response = supabase.table('foods_canonical').update(update_data).eq(
                                'product_key', product['product_key']
                            ).execute()
                            
                            updated += 1
                            print(f"  ✅ Updated with ingredients")
                        except Exception as e:
                            print(f"  ❌ Update failed: {e}")
                else:
                    print(f"  ⚠️  Product page not found")
                    
            except Exception as e:
                print(f"  ❌ Error fetching: {e}")
            
            # Be respectful
            time.sleep(2)
        
        print(f"\n✅ Updated {updated} Royal Canin products")
    
    def _extract_royal_canin_ingredients(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract ingredients from Royal Canin product page"""
        
        # Royal Canin patterns
        patterns = [
            # Look for ingredients section
            lambda: soup.find('div', class_='ingredients'),
            lambda: soup.find('section', id='ingredients'),
            lambda: soup.find('div', class_='product-ingredients'),
            # Look for composition
            lambda: soup.find('div', class_='composition'),
            # Look in product details
            lambda: soup.find('div', class_='product-details')
        ]
        
        for pattern in patterns:
            elem = pattern()
            if elem:
                text = elem.get_text(strip=True)
                if len(text) > 50 and ('chicken' in text.lower() or 'meat' in text.lower() or 'rice' in text.lower()):
                    return text
        
        # Look for "Composition" or "Ingredients" heading
        for heading in soup.find_all(['h2', 'h3', 'h4']):
            if 'composition' in heading.get_text().lower() or 'ingredients' in heading.get_text().lower():
                next_elem = heading.find_next_sibling()
                if next_elem:
                    text = next_elem.get_text(strip=True)
                    if len(text) > 50:
                        return text
        
        return None
    
    def _extract_royal_canin_nutrition(self, soup: BeautifulSoup) -> Dict:
        """Extract nutritional values from Royal Canin page"""
        
        nutrition = {}
        
        # Look for analytical constituents
        text = soup.get_text()
        
        patterns = {
            'protein_percent': r'protein[:\s]+([0-9.]+)\s*%',
            'fat_percent': r'fat content[:\s]+([0-9.]+)\s*%',
            'fiber_percent': r'crude fibres?[:\s]+([0-9.]+)\s*%',
            'ash_percent': r'crude ash[:\s]+([0-9.]+)\s*%',
            'moisture_percent': r'moisture[:\s]+([0-9.]+)\s*%'
        }
        
        for field, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    nutrition[field] = float(match.group(1))
                except:
                    pass
        
        return nutrition
    
    def enrich_hills(self):
        """Special handler for Hill's products"""
        
        print("\n=== ENRICHING HILL'S ===")
        
        # Hill's has two main lines with different websites
        science_plan_url = "https://www.hillspet.co.uk/dog-food"
        prescription_url = "https://www.hillspet.co.uk/prescription-diet/dog-food"
        
        # Get Hill's products
        response = supabase.table('foods_canonical').select('*').eq('brand', "Hill's Science Plan").execute()
        products = response.data
        
        response2 = supabase.table('foods_canonical').select('*').eq('brand', "Hill's Prescription Diet").execute()
        products.extend(response2.data)
        
        needs_enrichment = [p for p in products if not p.get('ingredients_raw')]
        
        print(f"Found {len(needs_enrichment)} Hill's products needing enrichment")
        
        # Similar approach to Royal Canin...
        # (Implementation would follow similar pattern)
    
    def run_enrichment(self, limit_per_brand: int = 10):
        """Run enrichment for priority brands"""
        
        print("="*60)
        print("PRIORITY BRAND ENRICHMENT")
        print("="*60)
        
        # Analyze needs
        brand_needs = self.analyze_brand_needs()
        
        print("\nTop 10 brands needing enrichment:")
        print(f"{'Brand':<30} {'Total':<8} {'Missing':<10} {'Completion'}")
        print("-"*60)
        
        for brand in brand_needs[:10]:
            print(f"{brand['brand']:<30} {brand['total_products']:<8} "
                  f"{brand['missing_ingredients']:<10} "
                  f"{brand['completion_rate']*100:.1f}%")
        
        # Focus on top brands
        priority_brands = ['Royal Canin', "Hill's Science Plan", "Hill's Prescription Diet"]
        
        for brand_name in priority_brands:
            if brand_name == 'Royal Canin':
                self.enrich_royal_canin()
            elif 'Hill' in brand_name:
                self.enrich_hills()
            
            # Add more brand-specific handlers as needed
        
        print("\n✅ Priority brand enrichment completed!")

def main():
    enricher = PriorityBrandEnricher()
    enricher.run_enrichment()

if __name__ == "__main__":
    main()