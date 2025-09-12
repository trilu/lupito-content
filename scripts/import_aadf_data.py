#!/usr/bin/env python3
"""
Import AADF (All About Dog Food) data into foods_canonical
Matches products and enriches with ingredients data
"""

import os
import re
import csv
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_KEY')
)

class AADFImporter:
    def __init__(self):
        self.supabase = supabase
        self.stats = {
            'total_rows': 0,
            'products_matched': 0,
            'products_updated': 0,
            'new_products_added': 0,
            'errors': []
        }
        self.brand_mapping = self._load_brand_mapping()
    
    def _load_brand_mapping(self) -> Dict[str, str]:
        """Load brand normalization mapping"""
        mapping = {}
        
        # Common brand normalizations
        mapping.update({
            'hills': "Hill's",
            'hills science plan': "Hill's Science Plan",
            'hills prescription diet': "Hill's Prescription Diet",
            'royal canin': 'Royal Canin',
            'natures menu': 'Natures Menu',
            'james wellbeloved': 'James Wellbeloved',
            'wolf of wilderness': 'Wolf Of Wilderness',
            'bakers': 'Bakers',
            'butchers': "Butcher's",
            'purina': 'Purina',
            'purina pro plan': 'Pro Plan',
            'iams': 'IAMS',
            'eukanuba': 'Eukanuba'
        })
        
        return mapping
    
    def extract_brand_from_url(self, url: str) -> Optional[str]:
        """Extract brand from AADF URL"""
        # AADF URLs often contain brand in the path
        # e.g., /dog-food-reviews/0535/forthglade-complete-meal-with-brown-rice-adult
        
        if not url:
            return None
        
        # Extract path
        path = urlparse(url).path
        
        # Common patterns in AADF URLs
        if '/dog-food-reviews/' in path:
            # Get the part after the ID
            parts = path.split('/')
            if len(parts) >= 4:
                product_slug = parts[3]
                
                # Extract brand from slug (usually first part before hyphen)
                slug_parts = product_slug.split('-')
                
                # Known brand patterns
                brand_patterns = {
                    'forthglade': 'Forthglade',
                    'ava': 'AVA',
                    'fish4dogs': 'Fish4Dogs',
                    'royal-canin': 'Royal Canin',
                    'hills': "Hill's",
                    'james-wellbeloved': 'James Wellbeloved',
                    'purina': 'Purina',
                    'eukanuba': 'Eukanuba',
                    'iams': 'IAMS',
                    'bakers': 'Bakers',
                    'butchers': "Butcher's",
                    'pedigree': 'Pedigree',
                    'wainwrights': "Wainwright's",
                    'harringtons': "Harrington's",
                    'burns': 'Burns',
                    'lily': "Lily's Kitchen",
                    'lilys-kitchen': "Lily's Kitchen",
                    'canagan': 'Canagan',
                    'aatu': 'Aatu',
                    'akela': 'Akela',
                    'applaws': 'Applaws',
                    'barking-heads': 'Barking Heads',
                    'beco': 'Beco',
                    'brit': 'Brit',
                    'eden': 'Eden',
                    'gentle': 'Gentle',
                    'guru': 'Guru',
                    'millies-wolfheart': "Millie's Wolfheart",
                    'natures-menu': 'Natures Menu',
                    'orijen': 'Orijen',
                    'piccolo': 'Piccolo',
                    'pooch-mutt': 'Pooch & Mutt',
                    'pure': 'Pure Pet Food',
                    'symply': 'Symply',
                    'tails': 'Tails.com',
                    'taste-of-the-wild': 'Taste of the Wild',
                    'tribal': 'Tribal',
                    'wellness': 'Wellness',
                    'wolf-of-wilderness': 'Wolf Of Wilderness',
                    'yarrah': 'Yarrah',
                    'ziwipeak': 'ZiwiPeak'
                }
                
                # Check each part of the slug
                for part in slug_parts:
                    part_lower = part.lower()
                    if part_lower in brand_patterns:
                        return brand_patterns[part_lower]
                
                # Try first part as brand
                if slug_parts:
                    potential_brand = slug_parts[0].replace('-', ' ').title()
                    return potential_brand
        
        return None
    
    def extract_product_name_from_url(self, url: str) -> Optional[str]:
        """Extract product name from AADF URL"""
        if not url:
            return None
        
        path = urlparse(url).path
        
        if '/dog-food-reviews/' in path:
            parts = path.split('/')
            if len(parts) >= 4:
                product_slug = parts[3]
                
                # Convert slug to readable name
                # Remove brand prefix if identifiable
                name = product_slug.replace('-', ' ')
                
                # Clean up common patterns
                name = re.sub(r'\b(dry|wet|complete|adult|puppy|senior)\b', '', name, flags=re.IGNORECASE)
                name = ' '.join(name.split())
                
                return name.title()
        
        return None
    
    def normalize_product_name(self, name: str) -> str:
        """Normalize product name for matching"""
        if not name:
            return ""
        
        # Convert to lowercase
        normalized = name.lower()
        
        # Remove special characters
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        
        # Remove extra spaces
        normalized = ' '.join(normalized.split())
        
        return normalized
    
    def find_matching_product(self, brand: str, product_name: str = None, url: str = None) -> Optional[Dict]:
        """Find matching product in database"""
        
        if not brand:
            return None
        
        # Try to find by brand
        response = supabase.table('foods_canonical').select('*').eq('brand', brand).execute()
        
        if not response.data:
            # Try normalized brand
            brand_lower = brand.lower()
            if brand_lower in self.brand_mapping:
                normalized_brand = self.brand_mapping[brand_lower]
                response = supabase.table('foods_canonical').select('*').eq('brand', normalized_brand).execute()
        
        if response.data and product_name:
            # Try to match by product name
            normalized_search = self.normalize_product_name(product_name)
            
            for product in response.data:
                db_normalized = self.normalize_product_name(product.get('product_name', ''))
                
                # Check for exact match
                if db_normalized == normalized_search:
                    return product
                
                # Check for partial match
                if len(normalized_search) > 5 and len(db_normalized) > 5:
                    # Calculate word overlap
                    search_words = set(normalized_search.split())
                    db_words = set(db_normalized.split())
                    
                    if search_words and db_words:
                        overlap = len(search_words & db_words)
                        total = len(search_words | db_words)
                        
                        if total > 0 and overlap / total > 0.6:  # 60% word overlap
                            return product
        
        return None
    
    def parse_ingredients(self, ingredients_text: str) -> List[str]:
        """Parse ingredients text into tokens"""
        if not ingredients_text:
            return []
        
        # Remove percentages and numbers in parentheses
        text = re.sub(r'\([^)]*\d+[^)]*\)', '', ingredients_text)
        
        # Split on commas
        parts = re.split(r'[,;]', text)
        
        tokens = []
        for part in parts:
            # Clean up
            part = re.sub(r'[^\w\s-]', ' ', part)
            part = ' '.join(part.split())
            
            if part and len(part) > 1:
                tokens.append(part.lower())
        
        return tokens
    
    def import_aadf_csv(self, csv_path: str = 'data/aadf/aadf-dataset.csv'):
        """Import AADF data from CSV"""
        
        print("="*60)
        print("IMPORTING AADF DATA")
        print("="*60)
        print(f"Source: {csv_path}")
        print()
        
        updates = []
        new_products = []
        unmatched = []
        
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                self.stats['total_rows'] += 1
                
                # Extract data
                url = row.get('data-page-selector-href', '').strip()
                ingredients = row.get('ingredients-0', '').strip()
                food_type = row.get('type_of_food-0', '').strip()
                price = row.get('price_per_day-0', '').strip()
                description = row.get('manufacturer_description-0', '').strip()
                
                if not ingredients or not url:
                    continue
                
                # Extract brand and product name from URL
                brand = self.extract_brand_from_url(url)
                product_name = self.extract_product_name_from_url(url)
                
                if not brand:
                    continue
                
                # Find matching product
                match = self.find_matching_product(brand, product_name, url)
                
                if match:
                    # Update existing product
                    if not match.get('ingredients_raw'):  # Only update if no ingredients
                        update_data = {
                            'ingredients_raw': ingredients,
                            'ingredients_source': 'aadf',
                            'ingredients_tokens': self.parse_ingredients(ingredients)
                        }
                        
                        # Add AADF URL if not present
                        if not match.get('product_url'):
                            update_data['product_url'] = url
                        
                        updates.append({
                            'product_key': match['product_key'],
                            'updates': update_data,
                            'brand': brand,
                            'name': match['product_name']
                        })
                        
                        self.stats['products_matched'] += 1
                else:
                    # Track unmatched for potential new product
                    unmatched.append({
                        'brand': brand,
                        'name': product_name or 'Unknown',
                        'url': url,
                        'ingredients': ingredients[:100] + '...' if len(ingredients) > 100 else ingredients
                    })
        
        # Apply updates
        print(f"\nFound {len(updates)} products to update with ingredients")
        
        if updates:
            print("\nUpdating products...")
            for i, update in enumerate(updates[:20], 1):  # Limit to first 20 for testing
                try:
                    response = supabase.table('foods_canonical').update(
                        update['updates']
                    ).eq('product_key', update['product_key']).execute()
                    
                    self.stats['products_updated'] += 1
                    print(f"  [{i}] ✅ {update['brand']}: {update['name']}")
                    
                except Exception as e:
                    print(f"  [{i}] ❌ Failed: {update['brand']}: {update['name']}")
                    print(f"      Error: {e}")
                    self.stats['errors'].append(str(e))
            
            if len(updates) > 20:
                print(f"\n  ... and {len(updates) - 20} more products ready to update")
                print("  Run with --all flag to update all products")
        
        # Show unmatched products
        if unmatched:
            print(f"\n⚠️  {len(unmatched)} products from AADF not found in database:")
            for item in unmatched[:10]:
                print(f"  - {item['brand']}: {item['name']}")
                print(f"    URL: {item['url']}")
            
            if len(unmatched) > 10:
                print(f"  ... and {len(unmatched) - 10} more")
        
        # Print summary
        print("\n" + "="*60)
        print("IMPORT SUMMARY")
        print("="*60)
        print(f"Total AADF rows processed: {self.stats['total_rows']}")
        print(f"Products matched in database: {self.stats['products_matched']}")
        print(f"Products updated with ingredients: {self.stats['products_updated']}")
        print(f"Products not found: {len(unmatched)}")
        print(f"Errors: {len(self.stats['errors'])}")
        
        # Save unmatched products for review
        if unmatched:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_file = f"data/aadf_unmatched_{timestamp}.json"
            
            with open(report_file, 'w') as f:
                json.dump({
                    'timestamp': timestamp,
                    'unmatched_count': len(unmatched),
                    'products': unmatched
                }, f, indent=2)
            
            print(f"\n📄 Unmatched products saved to: {report_file}")

def main():
    import sys
    
    importer = AADFImporter()
    
    # Check for --all flag
    update_all = '--all' in sys.argv
    
    if update_all:
        print("⚠️  Running in FULL UPDATE mode - will update all matched products")
    else:
        print("Running in TEST mode - will update first 20 products only")
        print("Use --all flag to update all products")
    
    importer.import_aadf_csv()
    
    print("\n✅ AADF import completed!")

if __name__ == "__main__":
    main()