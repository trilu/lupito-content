#!/usr/bin/env python3
"""
Smart AADF import with efficient duplicate detection
Strategy: Build in-memory index of key fields for fast matching
"""

import os
import json
import re
from datetime import datetime
from typing import Dict, List, Set, Tuple
from dotenv import load_dotenv
from supabase import create_client
import argparse

load_dotenv()

# Initialize Supabase
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_KEY')
)

class SmartAADFImporter:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.stats = {
            'total': 0,
            'new': 0,
            'key_duplicates': 0,
            'name_duplicates': 0,
            'url_duplicates': 0,
            'inserted': 0,
            'errors': 0
        }
        
        # In-memory indexes for fast lookup
        self.existing_keys = set()
        self.existing_names = {}  # brand|normalized_name -> product_key
        self.existing_urls = set()
        
        self.load_existing_indexes()
    
    def normalize_name(self, name: str) -> str:
        """Normalize product name for matching"""
        if not name:
            return ""
        
        # Remove size/quantity
        name = re.sub(r'\b\d+(?:\.\d+)?\s*(?:kg|g|lb|oz|ml|l)\b', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\b\d+\s*x\s*\d+[^\s]*', '', name, flags=re.IGNORECASE)
        
        # Remove pack types
        name = re.sub(r'\b(?:economy|saver|trial|value|mega|jumbo)\s*pack\b', '', name, flags=re.IGNORECASE)
        
        # Remove review suffix
        name = re.sub(r'\s*review\s*$', '', name, flags=re.IGNORECASE)
        
        # Clean and normalize
        name = re.sub(r'[^\w\s]', ' ', name.lower())
        name = ' '.join(name.split())
        
        return name.strip()
    
    def load_existing_indexes(self):
        """Load existing product indexes for fast duplicate detection"""
        print("📚 Building duplicate detection indexes...")
        
        # Load in batches for efficiency
        offset = 0
        batch_size = 1000
        total_loaded = 0
        
        while True:
            # Only load essential fields
            batch = supabase.table('foods_canonical')\
                .select('product_key, brand, product_name, product_url')\
                .range(offset, offset + batch_size - 1)\
                .execute()
            
            if not batch.data:
                break
            
            for product in batch.data:
                # Index product keys
                self.existing_keys.add(product['product_key'])
                
                # Index normalized names by brand
                if product['product_name']:
                    normalized = self.normalize_name(product['product_name'])
                    brand = (product.get('brand') or 'unknown').lower()
                    name_key = f"{brand}|{normalized}"
                    self.existing_names[name_key] = product['product_key']
                
                # Index URLs
                if product.get('product_url'):
                    self.existing_urls.add(product['product_url'])
            
            total_loaded += len(batch.data)
            offset += batch_size
            
            if len(batch.data) < batch_size:
                break
            
            if total_loaded % 5000 == 0:
                print(f"  Indexed {total_loaded} products...")
        
        print(f"  ✅ Indexed {total_loaded} products")
        print(f"     - {len(self.existing_keys)} product keys")
        print(f"     - {len(self.existing_names)} unique name combinations")
        print(f"     - {len(self.existing_urls)} URLs")
    
    def check_duplicate(self, product: Dict) -> Tuple[bool, str]:
        """
        Fast duplicate check using in-memory indexes
        Returns: (is_duplicate, duplicate_type)
        """
        
        # 1. Check product key
        if product['product_key'] in self.existing_keys:
            return True, 'key'
        
        # 2. Check normalized name + brand
        normalized = self.normalize_name(product['product_name'])
        brand = (product.get('brand') or 'unknown').lower()
        name_key = f"{brand}|{normalized}"
        
        if name_key in self.existing_names:
            return True, 'name'
        
        # 3. Check URL
        if product.get('product_url') and product['product_url'] in self.existing_urls:
            return True, 'url'
        
        return False, None
    
    def process_products(self, products: List[Dict]):
        """Process products with fast duplicate detection"""
        print(f"\n🔍 Processing {len(products)} products...")
        
        new_products = []
        duplicate_log = []
        
        for i, product in enumerate(products):
            self.stats['total'] += 1
            
            # Skip invalid products
            if not product.get('product_name'):
                continue
            
            # Check for duplicates
            is_duplicate, dup_type = self.check_duplicate(product)
            
            if is_duplicate:
                if dup_type == 'key':
                    self.stats['key_duplicates'] += 1
                elif dup_type == 'name':
                    self.stats['name_duplicates'] += 1
                elif dup_type == 'url':
                    self.stats['url_duplicates'] += 1
                
                duplicate_log.append({
                    'product': product['product_name'][:50],
                    'brand': product.get('brand'),
                    'type': dup_type
                })
            else:
                # New product - prepare for insert
                self.stats['new'] += 1
                
                # Clean up fields
                clean_product = {
                    'product_key': product['product_key'],
                    'brand': product.get('brand'),
                    'product_name': product['product_name'],
                    'ingredients_raw': product.get('ingredients_raw'),
                    'product_url': product.get('product_url'),
                    'form': product.get('form', 'unknown'),
                    'source': product.get('source', 'allaboutdogfood')
                }
                
                # Skip kcal for now due to constraint issues
                # We'll update these in a separate step
                # Skip fields that don't exist in database:
                # energy_kcal, price_per_day, type_of_food, dog_ages
                
                new_products.append(clean_product)
                
                # Update indexes for subsequent checks
                self.existing_keys.add(product['product_key'])
                normalized = self.normalize_name(product['product_name'])
                brand = (product.get('brand') or 'unknown').lower()
                self.existing_names[f"{brand}|{normalized}"] = product['product_key']
                if product.get('product_url'):
                    self.existing_urls.add(product['product_url'])
            
            if (i + 1) % 100 == 0:
                print(f"  Processed {i + 1}/{len(products)}")
                print(f"    New: {self.stats['new']} | Duplicates: {self.stats['key_duplicates'] + self.stats['name_duplicates'] + self.stats['url_duplicates']}")
        
        # Show sample duplicates
        if duplicate_log:
            print(f"\n📋 Sample duplicates found:")
            for dup in duplicate_log[:5]:
                print(f"  • {dup['brand']} - {dup['product']}: {dup['type']} match")
        
        return new_products
    
    def insert_products(self, products: List[Dict]):
        """Insert new products in batches"""
        if not products:
            print("\n✅ No new products to insert")
            return
        
        if self.dry_run:
            print(f"\n⚠️  DRY RUN - Would insert {len(products)} products")
            return
        
        print(f"\n📝 Inserting {len(products)} new products...")
        
        # Insert in batches of 50
        batch_size = 50
        for i in range(0, len(products), batch_size):
            batch = products[i:i+batch_size]
            try:
                supabase.table('foods_canonical').insert(batch).execute()
                self.stats['inserted'] += len(batch)
                print(f"  Inserted batch {i//batch_size + 1}/{(len(products)-1)//batch_size + 1}")
            except Exception as e:
                print(f"  Error in batch {i//batch_size + 1}: {str(e)[:100]}")
                self.stats['errors'] += len(batch)
    
    def print_summary(self):
        """Print import summary"""
        print("\n" + "=" * 80)
        print("📊 IMPORT SUMMARY")
        print("=" * 80)
        print(f"Total processed: {self.stats['total']}")
        print(f"New products found: {self.stats['new']}")
        print(f"Duplicates found: {self.stats['key_duplicates'] + self.stats['name_duplicates'] + self.stats['url_duplicates']}")
        print(f"  - By product key: {self.stats['key_duplicates']}")
        print(f"  - By name/brand: {self.stats['name_duplicates']}")
        print(f"  - By URL: {self.stats['url_duplicates']}")
        
        if not self.dry_run:
            print(f"\nSuccessfully inserted: {self.stats['inserted']}")
            print(f"Errors: {self.stats['errors']}")
            
            # Check new total
            aadf_count = supabase.table('foods_canonical')\
                .select('count', count='exact')\
                .ilike('product_url', '%allaboutdogfood%')\
                .execute()
            print(f"\nTotal AADF products in database: {aadf_count.count}")
        else:
            print("\n⚠️  DRY RUN - No changes made")

def main():
    parser = argparse.ArgumentParser(description='Smart AADF import')
    parser.add_argument('--dry-run', action='store_true', help='Run without making changes')
    parser.add_argument('--input', default='data/aadf/aadf_prepared.json', help='Input file')
    
    args = parser.parse_args()
    
    print("🧠 SMART AADF IMPORTER")
    print("=" * 80)
    
    # Load prepared data
    with open(args.input, 'r') as f:
        products = json.load(f)
    
    print(f"Loaded {len(products)} prepared products")
    
    # Create importer
    importer = SmartAADFImporter(dry_run=args.dry_run)
    
    # Process products
    new_products = importer.process_products(products)
    
    # Insert if not dry run
    importer.insert_products(new_products)
    
    # Print summary
    importer.print_summary()

if __name__ == "__main__":
    main()