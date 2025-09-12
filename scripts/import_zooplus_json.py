#!/usr/bin/env python3
"""
Import Zooplus products from existing JSON file
Applies brand normalization and handles variants
"""

import os
import json
import re
from datetime import datetime
from typing import Dict, List, Optional
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_KEY')
)

class ZooplusImporter:
    def __init__(self):
        self.supabase = supabase
        self.stats = {
            'total_processed': 0,
            'products_added': 0,
            'products_updated': 0,
            'products_skipped': 0,
            'brands_found': set(),
            'errors': []
        }
        self.existing_products = {}
        self.brand_normalizations = {
            # Major brands
            'royal canin': 'Royal Canin',
            'hills': "Hill's Science Plan",
            'hills prescription diet': "Hill's Prescription Diet",
            'hills science plan': "Hill's Science Plan",
            'purina pro plan': 'Pro Plan',
            'purina one': 'Purina ONE',
            'eukanuba': 'Eukanuba',
            'iams': 'IAMS',
            
            # Premium brands
            'orijen': 'Orijen',
            'acana': 'Acana',
            'taste of the wild': 'Taste of the Wild',
            'wellness': 'Wellness',
            'wellness core': 'Wellness CORE',
            'natural balance': 'Natural Balance',
            'nutro': 'Nutro',
            
            # European brands
            'wolf of wilderness': 'Wolf Of Wilderness',
            'lukullus': 'Lukullus',
            'rocco': 'Rocco',
            'briantos': 'Briantos',
            'bozita': 'Bozita',
            'josera': 'Josera',
            'bosch': 'Bosch',
            'happy dog': 'Happy Dog',
            'belcando': 'Belcando',
            'animonda': 'Animonda',
            
            # Store brands
            'purizon': 'Purizon',
            'concept for life': 'Concept for Life',
            'greenwoods': 'Greenwoods',
            'rosies farm': "Rosie's Farm",
            
            # UK brands
            'james wellbeloved': 'James Wellbeloved',
            'burns': 'Burns',
            'arden grange': 'Arden Grange',
            'barking heads': 'Barking Heads',
            'lilys kitchen': "Lily's Kitchen",
            'natures menu': "Nature's Menu",
            'wainwrights': "Wainwright's",
            'harringtons': "Harrington's",
            'butchers': "Butcher's",
        }
        
    def load_existing_products(self):
        """Load all existing products for duplicate checking"""
        print("Loading existing products...")
        
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
    
    def normalize_brand(self, brand: str) -> str:
        """Normalize brand name"""
        if not brand:
            return ""
        
        brand_lower = brand.lower().strip()
        
        # Check exact matches first
        if brand_lower in self.brand_normalizations:
            return self.brand_normalizations[brand_lower]
        
        # Check partial matches
        for key, value in self.brand_normalizations.items():
            if key in brand_lower:
                return value
        
        # Title case for unknown brands
        return brand.title()
    
    def extract_brand_from_breadcrumbs(self, breadcrumbs: List[str]) -> str:
        """Extract brand from breadcrumbs array"""
        if not breadcrumbs or len(breadcrumbs) < 3:
            return ""
        
        # Usually brand is at index 2 (Dog > Wet Dog Food > Brand > Product)
        brand_candidate = breadcrumbs[2] if len(breadcrumbs) > 2 else ""
        
        # Clean up brand
        brand_candidate = brand_candidate.replace('_', ' ').strip()
        
        return self.normalize_brand(brand_candidate)
    
    def extract_form(self, category: str, breadcrumbs: List[str], moisture: Optional[float]) -> str:
        """Determine product form (dry/wet)"""
        category_lower = category.lower() if category else ""
        breadcrumb_text = ' '.join(breadcrumbs).lower() if breadcrumbs else ""
        
        # Check explicit mentions
        if 'wet' in category_lower or 'wet' in breadcrumb_text:
            return 'wet'
        if 'dry' in category_lower or 'dry' in breadcrumb_text:
            return 'dry'
        if 'canned' in category_lower or 'tin' in breadcrumb_text:
            return 'wet'
        
        # Use moisture content as indicator
        if moisture:
            if moisture > 60:
                return 'wet'
            elif moisture < 20:
                return 'dry'
        
        return 'dry'  # Default to dry
    
    def extract_pack_size(self, name: str) -> Optional[str]:
        """Extract pack size from product name"""
        # Look for patterns like "6 x 400g", "12kg", "2 x 12kg"
        patterns = [
            r'(\d+\s*x\s*\d+\.?\d*\s*[kg|g|ml|l])',
            r'(\d+\.?\d*\s*[kg|g|ml|l])',
            r'(\d+\s*x\s*\d+\.?\d*[kg|g|ml|l])'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def clean_product_name(self, name: str, brand: str) -> str:
        """Clean product name by removing brand and pack size"""
        if not name:
            return ""
        
        # Remove brand from beginning if present
        if brand and name.lower().startswith(brand.lower()):
            name = name[len(brand):].strip()
        
        # Remove pack size
        pack_size = self.extract_pack_size(name)
        if pack_size:
            name = name.replace(pack_size, '').strip()
        
        # Clean up extra spaces and punctuation
        name = re.sub(r'\s+', ' ', name)
        name = name.strip(' -,')
        
        return name
    
    def create_product_key(self, brand: str, product_name: str, form: str = '') -> str:
        """Create unique product key"""
        brand_slug = re.sub(r'[^a-z0-9]', '', brand.lower())
        name_slug = re.sub(r'[^a-z0-9]', '', product_name.lower())
        form_slug = form.lower() if form else ''
        
        return f"{brand_slug}|{name_slug}|{form_slug}"
    
    def parse_ingredients(self, description: str) -> Optional[List[str]]:
        """Extract ingredients from description"""
        if not description:
            return None
        
        # Look for composition section
        patterns = [
            r'Composition:([^.]+)\.',
            r'Ingredients:([^.]+)\.',
            r'Composition\s*:?\s*([^.]+)\.',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                ingredients_text = match.group(1).strip()
                
                # Parse into tokens
                ingredients = []
                parts = re.split(r'[,;]', ingredients_text)
                
                for part in parts[:50]:  # Limit to 50 ingredients
                    part = re.sub(r'\([^)]*\)', '', part)  # Remove parentheses
                    part = re.sub(r'[^\\w\\s-]', ' ', part)
                    part = ' '.join(part.split())
                    
                    if part and len(part) > 1:
                        ingredients.append(part.lower().strip())
                
                return ingredients if ingredients else None
        
        return None
    
    def process_zooplus_product(self, product: Dict) -> Optional[Dict]:
        """Process a single Zooplus product"""
        # Extract brand
        brand = self.extract_brand_from_breadcrumbs(product.get('breadcrumbs', []))
        if not brand or brand == 'zooplus logo':
            return None
        
        self.stats['brands_found'].add(brand)
        
        # Extract product info
        name = product.get('name', '')
        if not name:
            return None
        
        # Extract nutrition from attributes
        attributes = product.get('attributes', {})
        protein = None
        fat = None
        fiber = None
        ash = None
        moisture = None
        
        if attributes:
            try:
                protein = float(attributes.get('protein', '').replace('%', '').strip()) if attributes.get('protein') else None
                fat = float(attributes.get('fat', '').replace('%', '').strip()) if attributes.get('fat') else None
                fiber = float(attributes.get('fibre', '').replace('%', '').strip()) if attributes.get('fibre') else None
                ash = float(attributes.get('ash', '').replace('%', '').strip()) if attributes.get('ash') else None
                moisture = float(attributes.get('moisture', '').replace('%', '').strip()) if attributes.get('moisture') else None
            except:
                pass
        
        # Determine form
        form = self.extract_form(
            product.get('category'),
            product.get('breadcrumbs', []),
            moisture
        )
        
        # Clean product name
        clean_name = self.clean_product_name(name, brand)
        
        # Extract pack size
        pack_size = self.extract_pack_size(name)
        
        # Create product key
        product_key = self.create_product_key(brand, clean_name, form)
        
        # Parse ingredients from description
        ingredients = self.parse_ingredients(product.get('description', ''))
        
        # Build product data
        product_data = {
            'product_key': product_key,
            'brand': brand,
            'product_name': clean_name,
            'form': form,
            'product_url': product.get('url'),
            'image_url': product.get('main_image'),
            'retailer_price': product.get('price'),
            'pack_sizes': pack_size,
        }
        
        # Add nutrition if available
        if protein is not None:
            product_data['protein_percent'] = protein
        if fat is not None:
            product_data['fat_percent'] = fat
        if fiber is not None:
            product_data['fiber_percent'] = fiber
        if ash is not None:
            product_data['ash_percent'] = ash
        if moisture is not None:
            product_data['moisture_percent'] = moisture
        
        # Add macros source if we have any nutrition
        if any([protein, fat, fiber, ash, moisture]):
            product_data['macros_source'] = 'site'
        
        # Add ingredients if found
        if ingredients:
            product_data['ingredients_raw'] = product.get('description', '')[:2000]  # Store raw for reference
            product_data['ingredients_tokens'] = ingredients
            product_data['ingredients_source'] = 'site'
        
        return product_data
    
    def import_zooplus_data(self, json_path: str = 'data/zooplus/Zooplus.json'):
        """Main import function"""
        print("\\n" + "="*60)
        print("IMPORTING ZOOPLUS PRODUCTS FROM JSON")
        print("="*60)
        
        self.load_existing_products()
        
        # Load JSON data
        print(f"\\nLoading data from: {json_path}")
        with open(json_path, 'r') as f:
            zooplus_products = json.load(f)
        
        print(f"Found {len(zooplus_products)} products in JSON")
        
        products_to_add = []
        products_to_update = []
        
        # Process each product
        for idx, raw_product in enumerate(zooplus_products):
            if idx % 100 == 0:
                print(f"  Processing product {idx}/{len(zooplus_products)}...", end='\\r')
            
            self.stats['total_processed'] += 1
            
            # Process product
            product_data = self.process_zooplus_product(raw_product)
            if not product_data:
                self.stats['products_skipped'] += 1
                continue
            
            # Check if exists
            if product_data['product_key'] in self.existing_products:
                existing = self.existing_products[product_data['product_key']]
                
                # Only update if we have new data
                update_needed = False
                update_data = {'product_key': product_data['product_key']}
                
                # Check if we can add missing nutrition
                if existing.get('protein_percent') is None and product_data.get('protein_percent'):
                    update_data['protein_percent'] = product_data['protein_percent']
                    update_needed = True
                if existing.get('fat_percent') is None and product_data.get('fat_percent'):
                    update_data['fat_percent'] = product_data['fat_percent']
                    update_needed = True
                if existing.get('fiber_percent') is None and product_data.get('fiber_percent'):
                    update_data['fiber_percent'] = product_data['fiber_percent']
                    update_needed = True
                if existing.get('ash_percent') is None and product_data.get('ash_percent'):
                    update_data['ash_percent'] = product_data['ash_percent']
                    update_needed = True
                if existing.get('moisture_percent') is None and product_data.get('moisture_percent'):
                    update_data['moisture_percent'] = product_data['moisture_percent']
                    update_needed = True
                
                # Check ingredients
                if existing.get('ingredients_raw') is None and product_data.get('ingredients_raw'):
                    update_data['ingredients_raw'] = product_data['ingredients_raw']
                    update_data['ingredients_tokens'] = product_data['ingredients_tokens']
                    update_data['ingredients_source'] = 'site'
                    update_needed = True
                
                if update_needed:
                    products_to_update.append(update_data)
                else:
                    self.stats['products_skipped'] += 1
            else:
                # New product
                products_to_add.append(product_data)
        
        print(f"\\n\\nReady to import:")
        print(f"  New products: {len(products_to_add)}")
        print(f"  Products to update: {len(products_to_update)}")
        print(f"  Unique brands found: {len(self.stats['brands_found'])}")
        
        # Show sample of brands
        print("\\nTop brands found:")
        for brand in sorted(self.stats['brands_found'])[:20]:
            print(f"  - {brand}")
        
        # Import new products
        if products_to_add:
            print(f"\\nAdding {len(products_to_add)} new products...")
            
            # Import in batches
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
                    
                    # Try individual inserts
                    for product in batch:
                        try:
                            response = supabase.table('foods_canonical').insert(product).execute()
                            self.stats['products_added'] += 1
                        except:
                            self.stats['products_skipped'] += 1
        
        # Update existing products
        if products_to_update:
            print(f"\\nUpdating {len(products_to_update)} existing products...")
            
            for product in products_to_update[:100]:  # Limit updates for safety
                try:
                    key = product.pop('product_key')
                    response = supabase.table('foods_canonical').update(product).eq('product_key', key).execute()
                    self.stats['products_updated'] += 1
                    
                except Exception as e:
                    self.stats['errors'].append(str(e))
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print import summary"""
        print("\\n" + "="*60)
        print("IMPORT SUMMARY")
        print("="*60)
        print(f"Total processed: {self.stats['total_processed']}")
        print(f"Products added: {self.stats['products_added']}")
        print(f"Products updated: {self.stats['products_updated']}")
        print(f"Products skipped: {self.stats['products_skipped']}")
        print(f"Unique brands: {len(self.stats['brands_found'])}")
        
        if self.stats['errors']:
            print(f"\\nErrors encountered: {len(self.stats['errors'])}")
        
        # Check new totals
        print("\\nVerifying database totals...")
        total = supabase.table('foods_canonical').select('*', count='exact').execute()
        with_fiber = supabase.table('foods_canonical').select('*', count='exact').not_.is_('fiber_percent', 'null').execute()
        with_ingredients = supabase.table('foods_canonical').select('*', count='exact').not_.is_('ingredients_raw', 'null').execute()
        
        print(f"\\nDatabase Status:")
        print(f"  Total products: {total.count}")
        print(f"  With fiber: {with_fiber.count} ({with_fiber.count/total.count*100:.1f}%)")
        print(f"  With ingredients: {with_ingredients.count} ({with_ingredients.count/total.count*100:.1f}%)")

def main():
    importer = ZooplusImporter()
    importer.import_zooplus_data()
    print("\\n✅ Zooplus import completed!")

if __name__ == "__main__":
    main()