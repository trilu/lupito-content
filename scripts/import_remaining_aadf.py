#!/usr/bin/env python3
"""
Import remaining AADF products with better duplicate handling
Handles products that failed in the initial UK import
"""

import os
import re
import csv
import json
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlparse
from supabase import create_client
from dotenv import load_dotenv
from collections import defaultdict

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_KEY')
)

class RemainingAADFImporter:
    def __init__(self):
        self.supabase = supabase
        self.stats = {
            'total_processed': 0,
            'products_added': 0,
            'products_updated': 0,
            'products_skipped': 0,
            'duplicates_modified': 0,
            'errors': []
        }
        self.existing_products = {}
        self.imported_keys = set()
        
    def load_existing_data(self):
        """Load existing products and previously imported keys"""
        print("Loading existing products...")
        
        # Load all products
        all_products = []
        offset = 0
        limit = 1000
        
        while True:
            response = supabase.table('foods_canonical').select('*').range(offset, offset + limit - 1).execute()
            batch = response.data
            if not batch:
                break
            all_products.extend(batch)
            offset += limit
        
        # Create lookup by key
        for product in all_products:
            self.existing_products[product['product_key']] = product
        
        print(f"Loaded {len(all_products)} existing products")
        
        # Load previously imported keys
        try:
            with open('data/uk_import_rollback_20250912_182435.json', 'r') as f:
                rollback = json.load(f)
                self.imported_keys = set(rollback['product_keys'])
                print(f"Found {len(self.imported_keys)} previously imported keys")
        except:
            print("No previous import file found")
    
    def normalize_brand(self, brand_slug: str) -> str:
        """Normalize brand names"""
        brand_map = {
            'royal-canin': 'Royal Canin',
            'royal': 'Royal Canin',
            'hills': "Hill's Science Plan",
            'james-wellbeloved': 'James Wellbeloved',
            'james': 'James Wellbeloved',
            'natures-menu': "Nature's Menu",
            'natures': "Nature's Menu",
            'wainwrights': "Wainwright's",
            'millies-wolfheart': "Millie's Wolfheart",
            'millies': "Millie's Wolfheart",
            'wolf-of-wilderness': 'Wolf Of Wilderness',
            'wolf': 'Wolf Of Wilderness',
            'butchers': "Butcher's",
            'fish4dogs': 'Fish4Dogs',
            'barking-heads': 'Barking Heads',
            'barking': 'Barking Heads',
            'arden-grange': 'Arden Grange',
            'arden': 'Arden Grange',
            'pooch-mutt': 'Pooch & Mutt',
            'pooch': 'Pooch & Mutt',
            'harringtons': "Harrington's",
            'pro-plan': 'Pro Plan',
            'pro': 'Pro Plan',
            'concept': 'Concept for Life',
            'country': 'Country Value',
            'alpha-spirit': 'Alpha Spirit',
            'alpha': 'Alpha Spirit',
            'lilys-kitchen': "Lily's Kitchen",
            'lily': "Lily's Kitchen",
            'billy-margot': 'Billy + Margot',
            'taste-of-the-wild': 'Taste of the Wild',
            'vets-kitchen': "Vet's Kitchen",
            'wellness-core': 'Wellness CORE',
            'solid-gold': 'Solid Gold',
            'terra-canis': 'Terra Canis',
            'the-dogs-table': "The Dog's Table",
            'step-up': 'Step Up',
            'purina-one': 'Purina ONE',
        }
        
        return brand_map.get(brand_slug, brand_slug.replace('-', ' ').title())
    
    def extract_brand_from_url(self, url: str) -> Optional[str]:
        """Extract brand from URL with normalization"""
        if not url:
            return None
        
        path = urlparse(url).path.lower()
        
        if '/dog-food-reviews/' in path:
            parts = path.split('/')
            if len(parts) >= 4:
                slug = parts[3]
                # Get first part as potential brand
                brand_part = slug.split('-')[0]
                
                # Check if it needs normalization
                brand = self.normalize_brand(brand_part)
                
                # Special cases for compound brands
                if 'royal-canin' in slug:
                    return 'Royal Canin'
                elif 'hills' in slug:
                    return "Hill's Science Plan"
                elif 'james-wellbeloved' in slug:
                    return 'James Wellbeloved'
                elif 'natures-menu' in slug:
                    return "Nature's Menu"
                elif 'millies-wolfheart' in slug:
                    return "Millie's Wolfheart"
                elif 'wolf-of-wilderness' in slug:
                    return 'Wolf Of Wilderness'
                elif 'barking-heads' in slug:
                    return 'Barking Heads'
                elif 'arden-grange' in slug:
                    return 'Arden Grange'
                elif 'pooch-mutt' in slug:
                    return 'Pooch & Mutt'
                elif 'alpha-spirit' in slug:
                    return 'Alpha Spirit'
                elif 'fish4dogs' in slug:
                    return 'Fish4Dogs'
                
                return brand
        
        return None
    
    def extract_product_name(self, url: str, brand: str) -> Optional[str]:
        """Extract product name from URL"""
        if not url:
            return None
        
        path = urlparse(url).path
        
        if '/dog-food-reviews/' in path:
            parts = path.split('/')
            if len(parts) >= 4:
                slug = parts[3]
                
                # Remove brand prefix
                brand_slug = brand.lower().replace(' ', '-').replace("'", '').replace('+', '')
                
                # Try different brand slug variations
                if slug.startswith(brand_slug + '-'):
                    name_part = slug[len(brand_slug)+1:]
                elif '-' in slug:
                    # Skip first part (usually brand)
                    slug_parts = slug.split('-')
                    
                    # Special handling for compound brands
                    if brand == 'Royal Canin' and slug.startswith('royal-canin'):
                        name_part = '-'.join(slug_parts[2:])
                    elif brand == "Hill's Science Plan" and slug.startswith('hills'):
                        name_part = '-'.join(slug_parts[1:])
                    elif brand == "Nature's Menu" and slug.startswith('natures'):
                        name_part = '-'.join(slug_parts[2:]) if 'menu' in slug else '-'.join(slug_parts[1:])
                    else:
                        name_part = '-'.join(slug_parts[1:])
                else:
                    name_part = slug
                
                # Clean up name
                name = name_part.replace('-', ' ').title()
                
                # Remove common suffixes
                name = re.sub(r'\s+Dry$', '', name)
                name = re.sub(r'\s+Wet$', '', name)
                name = re.sub(r'\s+Dog\s+Food$', '', name)
                
                return name.strip()
        
        return None
    
    def create_product_key(self, brand: str, product_name: str, form: str = '') -> str:
        """Create unique product key"""
        brand_slug = re.sub(r'[^a-z0-9]', '', brand.lower())
        name_slug = re.sub(r'[^a-z0-9]', '', product_name.lower())
        form_slug = form.lower() if form else ''
        
        return f"{brand_slug}|{name_slug}|{form_slug}"
    
    def create_variant_key(self, base_key: str, variant: int) -> str:
        """Create variant key for duplicates"""
        parts = base_key.split('|')
        if len(parts) == 3:
            return f"{parts[0]}|{parts[1]}_v{variant}|{parts[2]}"
        return f"{base_key}_v{variant}"
    
    def extract_form(self, product_name: str, url: str) -> str:
        """Extract product form"""
        name_lower = product_name.lower() if product_name else ''
        url_lower = url.lower()
        
        if 'wet' in name_lower or 'tin' in name_lower or 'tray' in name_lower or 'pouch' in name_lower:
            return 'wet'
        elif 'dry' in name_lower or 'kibble' in name_lower:
            return 'dry'
        
        if 'wet' in url_lower or 'tin' in url_lower:
            return 'wet'
        
        return 'dry'
    
    def parse_ingredients(self, ingredients_text: str) -> List[str]:
        """Parse ingredients into tokens"""
        if not ingredients_text:
            return []
        
        text = re.sub(r'\([^)]*\d+[^)]*\)', '', ingredients_text)
        parts = re.split(r'[,;]', text)
        
        tokens = []
        for part in parts[:50]:
            part = re.sub(r'[^\w\s-]', ' ', part)
            part = ' '.join(part.split())
            
            if part and len(part) > 1:
                tokens.append(part.lower().strip())
        
        return tokens
    
    def process_remaining_products(self):
        """Process remaining AADF products"""
        print("\n" + "="*60)
        print("IMPORTING REMAINING AADF PRODUCTS")
        print("="*60)
        
        self.load_existing_data()
        
        products_to_add = []
        products_to_update = []
        
        print("\nProcessing AADF data...")
        
        with open('data/aadf/aadf-dataset.csv', 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            for row_num, row in enumerate(reader, 1):
                if row_num % 100 == 0:
                    print(f"  Processing row {row_num}...", end='\r')
                
                url = row.get('data-page-selector-href', '').strip()
                ingredients = row.get('ingredients-0', '').strip()
                
                if not url or not ingredients:
                    continue
                
                self.stats['total_processed'] += 1
                
                # Extract data
                brand = self.extract_brand_from_url(url)
                if not brand:
                    continue
                
                product_name = self.extract_product_name(url, brand)
                if not product_name:
                    continue
                
                form = self.extract_form(product_name, url)
                base_key = self.create_product_key(brand, product_name, form)
                
                # Skip if already imported in previous batch
                if base_key in self.imported_keys:
                    continue
                
                # Check if exists in database
                if base_key in self.existing_products:
                    existing = self.existing_products[base_key]
                    
                    # Update if no ingredients
                    if not existing.get('ingredients_raw'):
                        products_to_update.append({
                            'key': base_key,
                            'brand': brand,
                            'name': product_name,
                            'ingredients': ingredients,
                            'ingredients_tokens': self.parse_ingredients(ingredients)
                        })
                    else:
                        # Try variant keys
                        added = False
                        for variant in range(2, 10):
                            variant_key = self.create_variant_key(base_key, variant)
                            if variant_key not in self.existing_products:
                                products_to_add.append({
                                    'product_key': variant_key,
                                    'brand': brand,
                                    'product_name': f"{product_name} (Variant {variant})",
                                    'form': form,
                                    'ingredients_raw': ingredients,
                                    'ingredients_tokens': self.parse_ingredients(ingredients),
                                    'ingredients_source': 'site',
                                    'product_url': url
                                })
                                self.stats['duplicates_modified'] += 1
                                added = True
                                break
                        
                        if not added:
                            self.stats['products_skipped'] += 1
                else:
                    # New product
                    products_to_add.append({
                        'product_key': base_key,
                        'brand': brand,
                        'product_name': product_name,
                        'form': form,
                        'ingredients_raw': ingredients,
                        'ingredients_tokens': self.parse_ingredients(ingredients),
                        'ingredients_source': 'site',
                        'product_url': url
                    })
        
        print(f"\n\nProducts to add: {len(products_to_add)}")
        print(f"Products to update: {len(products_to_update)}")
        print(f"Duplicate variants created: {self.stats['duplicates_modified']}")
        
        # Update existing products
        if products_to_update:
            print(f"\nUpdating {len(products_to_update)} existing products...")
            for product in products_to_update[:50]:  # Limit for safety
                try:
                    response = supabase.table('foods_canonical').update({
                        'ingredients_raw': product['ingredients'],
                        'ingredients_tokens': product['ingredients_tokens'],
                        'ingredients_source': 'site'
                    }).eq('product_key', product['key']).execute()
                    
                    self.stats['products_updated'] += 1
                    print(f"  ✅ Updated: {product['brand']}: {product['name']}")
                    
                except Exception as e:
                    print(f"  ❌ Failed: {product['brand']}: {product['name']}")
                    self.stats['errors'].append(str(e))
        
        # Add new products
        if products_to_add:
            print(f"\nAdding {len(products_to_add)} new products...")
            
            # Add in smaller batches to avoid conflicts
            batch_size = 50
            for i in range(0, len(products_to_add), batch_size):
                batch = products_to_add[i:i+batch_size]
                
                try:
                    response = supabase.table('foods_canonical').insert(batch).execute()
                    self.stats['products_added'] += len(batch)
                    print(f"  Batch {i//batch_size + 1}: Added {len(batch)} products ✅")
                    
                except Exception as e:
                    print(f"  Batch {i//batch_size + 1}: Failed ❌")
                    print(f"    Error: {e}")
                    self.stats['errors'].append(str(e))
                    
                    # Try individual inserts for failed batch
                    for product in batch:
                        try:
                            response = supabase.table('foods_canonical').insert(product).execute()
                            self.stats['products_added'] += 1
                        except:
                            self.stats['products_skipped'] += 1
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print import summary"""
        print("\n" + "="*60)
        print("IMPORT SUMMARY")
        print("="*60)
        print(f"Total AADF rows processed: {self.stats['total_processed']}")
        print(f"Products added: {self.stats['products_added']}")
        print(f"Products updated: {self.stats['products_updated']}")
        print(f"Duplicate variants created: {self.stats['duplicates_modified']}")
        print(f"Products skipped: {self.stats['products_skipped']}")
        
        if self.stats['errors']:
            print(f"Errors encountered: {len(self.stats['errors'])}")
        
        # Check final status
        print("\nVerifying database status...")
        total = supabase.table('foods_canonical').select('*', count='exact').execute()
        with_ingredients = supabase.table('foods_canonical').select(
            '*', count='exact'
        ).not_.is_('ingredients_raw', 'null').execute()
        
        print(f"\nFinal Database Status:")
        print(f"  Total products: {total.count}")
        print(f"  Products with ingredients: {with_ingredients.count} ({with_ingredients.count/total.count*100:.1f}%)")

def main():
    importer = RemainingAADFImporter()
    importer.process_remaining_products()
    print("\n✅ Remaining AADF import completed!")

if __name__ == "__main__":
    main()