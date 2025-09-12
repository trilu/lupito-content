#!/usr/bin/env python3
"""
Import UK products from AADF dataset
Adds ~1,095 new UK-specific products to expand market coverage
"""

import os
import re
import csv
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple
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

class UKProductImporter:
    def __init__(self):
        self.supabase = supabase
        self.stats = {
            'total_processed': 0,
            'products_added': 0,
            'products_skipped': 0,
            'duplicates_found': 0,
            'errors': [],
            'new_brands': set(),
            'rollback_keys': []
        }
        self.brand_normalizations = self._load_brand_normalizations()
        self.existing_products = set()
        self.existing_brands = set()
        
    def _load_brand_normalizations(self) -> Dict[str, str]:
        """Load comprehensive brand normalization mappings"""
        return {
            'royal-canin': 'Royal Canin',
            'hills': "Hill's Science Plan",
            'james-wellbeloved': 'James Wellbeloved',
            'natures-menu': "Nature's Menu",
            'wainwrights': "Wainwright's",
            'millies-wolfheart': "Millie's Wolfheart",
            'wolf-of-wilderness': 'Wolf Of Wilderness',
            'butchers': "Butcher's",
            'lilys-kitchen': "Lily's Kitchen",
            'lily': "Lily's Kitchen",
            'pooch-mutt': 'Pooch & Mutt',
            'harringtons': "Harrington's",
            'barking-heads': 'Barking Heads',
            'arden-grange': 'Arden Grange',
            'fish4dogs': 'Fish4Dogs',
            'billy-margot': 'Billy + Margot',
            'alpha-spirit': 'Alpha Spirit',
            'country-value': 'Country Value',
            'ava': 'AVA',
            'aatu': 'Aatu',
            'akela': 'Akela',
            'applaws': 'Applaws',
            'beco': 'Beco',
            'brit': 'Brit',
            'eden': 'Eden',
            'gentle': 'Gentle',
            'guru': 'Guru',
            'orijen': 'Orijen',
            'piccolo': 'Piccolo',
            'pure': 'Pure Pet Food',
            'symply': 'Symply',
            'tails': 'Tails.com',
            'tribal': 'Tribal',
            'wellness': 'Wellness',
            'yarrah': 'Yarrah',
            'ziwipeak': 'ZiwiPeak',
            'acana': 'Acana',
            'advance': 'Advance',
            'arkwrights': 'Arkwrights',
            'autarky': 'Autarky',
            'benevo': 'Benevo',
            'beta': 'Beta',
            'blink': 'Blink',
            'burgess': 'Burgess',
            'cesar': 'Cesar',
            'chappie': 'Chappie',
            'encore': 'Encore',
            'greenies': 'Greenies',
            'hilife': 'HiLife',
            'husse': 'Husse',
            'josera': 'Josera',
            'lukullus': 'Lukullus',
            'merrick': 'Merrick',
            'naturediet': 'Nature Diet',
            'nutriment': 'Nutriment',
            'platinum': 'Platinum',
            'pro-plan': 'Pro Plan',
            'pro-pac': 'Pro Pac',
            'purina-one': 'Purina ONE',
            'purina': 'Purina',
            'rocco': 'Rocco',
            'scrumbles': 'Scrumbles',
            'skinners': 'Skinners',
            'solid-gold': 'Solid Gold',
            'step-up': 'Step Up',
            'terra-canis': 'Terra Canis',
            'the-dogs-table': "The Dog's Table",
            'thrive': 'Thrive',
            'vets-kitchen': "Vet's Kitchen",
            'wagg': 'Wagg',
            'webbox': 'Webbox',
            'wellness-core': 'Wellness CORE',
            'winalot': 'Winalot',
            'taste-of-the-wild': 'Taste of the Wild',
            'forthglade': 'Forthglade',
            'eukanuba': 'Eukanuba',
            'iams': 'IAMS',
            'pedigree': 'Pedigree',
            'bakers': 'Bakers',
            'burns': 'Burns',
            'canagan': 'Canagan',
            'lifestage': 'LifeStage',
            'leader': 'Leader',
            'trophy': 'Trophy',
            'collards': 'Collards',
            'concept': 'Concept for Life',
            'csj': 'CSJ',
            'denes': 'Denes',
            'country': 'Country Value',  # Common UK budget brand
            'natures': "Nature's Menu",  # Normalize variant
        }
        
    def _load_existing_products(self):
        """Load existing products to check for duplicates"""
        print("Loading existing products...")
        all_products = []
        offset = 0
        limit = 1000
        
        while True:
            response = supabase.table('foods_canonical').select(
                'product_key,brand,product_name'
            ).range(offset, offset + limit - 1).execute()
            
            batch = response.data
            if not batch:
                break
            all_products.extend(batch)
            offset += limit
        
        # Create lookup sets
        for product in all_products:
            self.existing_products.add(product['product_key'])
            if product.get('brand'):
                self.existing_brands.add(product['brand'])
        
        print(f"Loaded {len(all_products)} existing products")
        print(f"Found {len(self.existing_brands)} existing brands")
        
    def extract_brand_from_url(self, url: str) -> Optional[str]:
        """Extract and normalize brand from AADF URL"""
        if not url:
            return None
        
        path = urlparse(url).path.lower()
        
        # Check against known patterns
        for pattern, brand in self.brand_normalizations.items():
            if pattern in path:
                return brand
        
        # Extract from slug
        if '/dog-food-reviews/' in path:
            parts = path.split('/')
            if len(parts) >= 4:
                slug = parts[3]
                
                # Check if full slug matches a pattern
                for pattern, brand in self.brand_normalizations.items():
                    if slug.startswith(pattern):
                        return brand
                
                # Default: use first part as brand
                first_part = slug.split('-')[0]
                # Check if first part is in normalizations
                if first_part in self.brand_normalizations:
                    return self.brand_normalizations[first_part]
                
                # Title case as fallback
                return first_part.title()
        
        return None
    
    def extract_product_name_from_url(self, url: str, brand: str) -> Optional[str]:
        """Extract product name from URL"""
        if not url:
            return None
        
        path = urlparse(url).path
        
        if '/dog-food-reviews/' in path:
            parts = path.split('/')
            if len(parts) >= 4:
                slug = parts[3]
                
                # Remove brand prefix from slug
                brand_slug = brand.lower().replace(' ', '-').replace("'", '')
                if slug.startswith(brand_slug + '-'):
                    name_part = slug[len(brand_slug)+1:]
                else:
                    # Try to identify where brand ends in slug
                    slug_parts = slug.split('-')
                    # Skip first part (usually brand)
                    name_part = '-'.join(slug_parts[1:]) if len(slug_parts) > 1 else slug
                
                # Clean up name
                name = name_part.replace('-', ' ').title()
                
                # Clean common suffixes
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
    
    def extract_life_stage(self, product_name: str) -> Optional[str]:
        """Extract life stage from product name"""
        name_lower = product_name.lower()
        
        if 'puppy' in name_lower or 'junior' in name_lower:
            return 'puppy'
        elif 'senior' in name_lower or 'mature' in name_lower or 'older' in name_lower:
            return 'senior'
        elif 'adult' in name_lower:
            return 'adult'
        
        return None
    
    def extract_form(self, product_name: str, url: str) -> str:
        """Extract product form (dry/wet)"""
        name_lower = product_name.lower()
        url_lower = url.lower()
        
        # Check for explicit mentions
        if 'wet' in name_lower or 'tin' in name_lower or 'tray' in name_lower or 'pouch' in name_lower:
            return 'wet'
        elif 'dry' in name_lower or 'kibble' in name_lower or 'biscuit' in name_lower:
            return 'dry'
        
        # Check URL
        if 'wet' in url_lower or 'tin' in url_lower or 'can' in url_lower:
            return 'wet'
        elif 'dry' in url_lower or 'kibble' in url_lower:
            return 'dry'
        
        # Default to dry for most products
        return 'dry'
    
    def parse_ingredients(self, ingredients_text: str) -> List[str]:
        """Parse ingredients into tokens"""
        if not ingredients_text:
            return []
        
        # Remove percentages and numbers in parentheses
        text = re.sub(r'\([^)]*\d+[^)]*\)', '', ingredients_text)
        
        # Split on commas and semicolons
        parts = re.split(r'[,;]', text)
        
        tokens = []
        for part in parts[:50]:  # Limit to 50 ingredients
            # Clean up
            part = re.sub(r'[^\w\s-]', ' ', part)
            part = ' '.join(part.split())
            
            if part and len(part) > 1:
                tokens.append(part.lower().strip())
        
        return tokens
    
    def process_aadf_product(self, row: Dict) -> Optional[Dict]:
        """Process single AADF row into product data"""
        url = row.get('data-page-selector-href', '').strip()
        ingredients = row.get('ingredients-0', '').strip()
        
        if not url or not ingredients:
            return None
        
        # Extract brand
        brand = self.extract_brand_from_url(url)
        if not brand:
            return None
        
        # Extract product name
        product_name = self.extract_product_name_from_url(url, brand)
        if not product_name:
            return None
        
        # Extract form and create key
        form = self.extract_form(product_name, url)
        product_key = self.create_product_key(brand, product_name, form)
        
        # Check if already exists
        if product_key in self.existing_products:
            self.stats['duplicates_found'] += 1
            return None
        
        # Extract additional fields
        life_stage = self.extract_life_stage(product_name)
        
        # Track new brands
        if brand not in self.existing_brands:
            self.stats['new_brands'].add(brand)
        
        # Create product data
        product_data = {
            'product_key': product_key,
            'brand': brand,
            'product_name': product_name,
            'form': form,
            'ingredients_raw': ingredients,
            'ingredients_tokens': self.parse_ingredients(ingredients),
            'ingredients_source': 'site',
            'product_url': url
        }
        
        # Add optional fields
        if life_stage:
            product_data['life_stage'] = life_stage
        
        return product_data
    
    def import_uk_products(self, csv_path: str = 'data/aadf/aadf-dataset.csv'):
        """Main import function"""
        print("="*60)
        print("UK PRODUCTS IMPORT FROM AADF")
        print("="*60)
        
        # Load existing products
        self._load_existing_products()
        
        # Check what's already been imported
        print("\nChecking previously imported AADF products...")
        already_imported = supabase.table('foods_canonical').select(
            'product_key'
        ).eq('ingredients_source', 'site').like('product_url', '%allaboutdogfood%').execute()
        
        already_imported_keys = set(p['product_key'] for p in already_imported.data)
        print(f"Found {len(already_imported_keys)} products already imported from AADF")
        
        # Process CSV
        print(f"\nProcessing AADF data from: {csv_path}")
        products_to_add = []
        
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            for row_num, row in enumerate(reader, 1):
                if row_num % 100 == 0:
                    print(f"  Processing row {row_num}...", end='\r')
                
                self.stats['total_processed'] += 1
                
                # Process product
                product_data = self.process_aadf_product(row)
                
                if product_data:
                    # Check if already imported in previous runs
                    if product_data['product_key'] not in already_imported_keys:
                        products_to_add.append(product_data)
                    else:
                        self.stats['products_skipped'] += 1
                else:
                    self.stats['products_skipped'] += 1
        
        print(f"\n\nProducts ready to import: {len(products_to_add)}")
        print(f"Products skipped (duplicates/already imported): {self.stats['products_skipped']}")
        print(f"New brands found: {len(self.stats['new_brands'])}")
        
        if self.stats['new_brands']:
            print("\nSample new brands:")
            for brand in sorted(self.stats['new_brands'])[:10]:
                print(f"  - {brand}")
        
        # Import in batches
        if products_to_add:
            print(f"\nImporting {len(products_to_add)} products...")
            batch_size = 100
            
            for i in range(0, len(products_to_add), batch_size):
                batch = products_to_add[i:i+batch_size]
                
                try:
                    # Insert batch
                    response = supabase.table('foods_canonical').insert(batch).execute()
                    
                    # Track for rollback
                    for product in batch:
                        self.stats['rollback_keys'].append(product['product_key'])
                        self.stats['products_added'] += 1
                    
                    print(f"  Batch {i//batch_size + 1}: Added {len(batch)} products ✅")
                    
                except Exception as e:
                    print(f"  Batch {i//batch_size + 1}: Failed ❌")
                    print(f"    Error: {e}")
                    self.stats['errors'].append(str(e))
                    
                    # Stop on error
                    break
        
        # Save rollback file
        self._save_rollback_file()
        
        # Print summary
        self._print_summary()
    
    def _save_rollback_file(self):
        """Save rollback information"""
        if self.stats['rollback_keys']:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            rollback_file = f"data/uk_import_rollback_{timestamp}.json"
            
            rollback_data = {
                'timestamp': timestamp,
                'products_added': self.stats['products_added'],
                'product_keys': self.stats['rollback_keys'],
                'new_brands': sorted(self.stats['new_brands'])
            }
            
            with open(rollback_file, 'w') as f:
                json.dump(rollback_data, f, indent=2)
            
            print(f"\n📄 Rollback file saved: {rollback_file}")
    
    def _print_summary(self):
        """Print import summary"""
        print("\n" + "="*60)
        print("IMPORT SUMMARY")
        print("="*60)
        print(f"Total AADF rows processed: {self.stats['total_processed']}")
        print(f"Products added: {self.stats['products_added']}")
        print(f"Products skipped: {self.stats['products_skipped']}")
        print(f"Duplicates found: {self.stats['duplicates_found']}")
        print(f"New brands added: {len(self.stats['new_brands'])}")
        
        if self.stats['errors']:
            print(f"Errors encountered: {len(self.stats['errors'])}")
        
        # Check new database status
        print("\nVerifying database status...")
        total = supabase.table('foods_canonical').select('*', count='exact').execute()
        with_ingredients = supabase.table('foods_canonical').select(
            '*', count='exact'
        ).not_.is_('ingredients_raw', 'null').execute()
        
        print(f"\nDatabase Status:")
        print(f"  Total products: {total.count}")
        print(f"  Products with ingredients: {with_ingredients.count} ({with_ingredients.count/total.count*100:.1f}%)")
        
        if self.stats['products_added'] > 0:
            print(f"\n✅ Successfully imported {self.stats['products_added']} UK products!")
        else:
            print("\n⚠️ No new products were imported")

def main():
    import sys
    
    importer = UKProductImporter()
    
    # Check for dry run flag
    if '--dry-run' in sys.argv:
        print("DRY RUN MODE - No changes will be made")
        # Just analyze without importing
        importer._load_existing_products()
    else:
        importer.import_uk_products()
    
    print("\n✅ UK products import completed!")

if __name__ == "__main__":
    main()