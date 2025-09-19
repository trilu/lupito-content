#!/usr/bin/env python3
"""
Fast AADF import - only check for duplicates among AADF products
"""

import os
import json
import re
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv
from supabase import create_client
from fuzzywuzzy import fuzz
import argparse

load_dotenv()

# Initialize Supabase
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_KEY')
)

class AADFImporterFast:
    """Fast AADF importer - only loads existing AADF products"""
    
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.stats = {
            'total': 0,
            'new_products': 0,
            'duplicates': 0,
            'fuzzy_matches': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0
        }
        self.import_log = []
        self.existing_aadf = {}
        self.load_existing_aadf()
    
    def load_existing_aadf(self):
        """Load only existing AADF products for matching"""
        print("📚 Loading existing AADF products...")
        
        # Only get AADF products
        aadf_products = supabase.table('foods_canonical')\
            .select('product_key, brand, product_name, product_url, ingredients_raw')\
            .ilike('product_url', '%allaboutdogfood%')\
            .execute()
        
        print(f"  Loaded {len(aadf_products.data)} existing AADF products")
        
        # Create lookup dictionary
        for product in aadf_products.data:
            if product['product_name']:
                clean_name = self.normalize_for_matching(product['product_name'])
                brand = (product['brand'] or '').lower()
                key = f"{brand}|{clean_name}"
                self.existing_aadf[key] = product
    
    def normalize_for_matching(self, name: str) -> str:
        """Normalize product name for matching"""
        if not name:
            return ""
        
        # Remove size/quantity patterns
        name = re.sub(r'\b\d+(?:\.\d+)?\s*(?:kg|g|lb|oz|ml|l)\b', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\b\d+\s*x\s*\d+(?:\.\d+)?(?:\s*(?:kg|g|lb|oz|ml|l|cans?|pouches?|tins?))?\b', '', name, flags=re.IGNORECASE)
        
        # Remove common suffixes
        name = re.sub(r'\s*(?:Economy|Saver|Trial|Value)\s*Pack\b', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s*Review\b', '', name, flags=re.IGNORECASE)
        
        # Clean up
        name = re.sub(r'[^\w\s]', ' ', name.lower())
        name = ' '.join(name.split())
        
        return name.strip()
    
    def find_duplicate(self, product: Dict) -> Optional[Dict]:
        """Quick check if product already exists"""
        
        # 1. Try exact product key match
        existing = supabase.table('foods_canonical')\
            .select('product_key')\
            .eq('product_key', product['product_key'])\
            .limit(1)\
            .execute()
        
        if existing.data:
            return {'type': 'exact', 'product_key': existing.data[0]['product_key']}
        
        # 2. Try normalized name match in AADF products only
        clean_name = self.normalize_for_matching(product['product_name'])
        brand = (product['brand'] or '').lower()
        lookup_key = f"{brand}|{clean_name}"
        
        if lookup_key in self.existing_aadf:
            return {'type': 'normalized', 'product_key': self.existing_aadf[lookup_key]['product_key']}
        
        # 3. Try fuzzy matching for same brand (only in AADF)
        if brand and brand != 'unknown':
            for key, existing in self.existing_aadf.items():
                if key.startswith(brand + '|'):
                    existing_clean = key.split('|', 1)[1]
                    score = fuzz.ratio(clean_name, existing_clean)
                    
                    if score > 90:  # Higher threshold for auto-match
                        return {'type': 'fuzzy', 'product_key': existing['product_key'], 'score': score}
        
        # 4. Check URL match
        if product.get('product_url'):
            existing = supabase.table('foods_canonical')\
                .select('product_key')\
                .eq('product_url', product['product_url'])\
                .limit(1)\
                .execute()
            
            if existing.data:
                return {'type': 'url', 'product_key': existing.data[0]['product_key']}
        
        return None
    
    def import_batch(self, products: List[Dict]):
        """Import products in batches"""
        print(f"\n🚀 Fast importing {len(products)} products...")
        
        new_products = []
        
        for i, product in enumerate(products):
            self.stats['total'] += 1
            
            # Skip products without essential data
            if not product.get('product_name'):
                self.stats['skipped'] += 1
                continue
            
            # Check for duplicates
            duplicate = self.find_duplicate(product)
            
            if duplicate:
                self.stats['duplicates'] += 1
                if duplicate['type'] == 'fuzzy':
                    self.stats['fuzzy_matches'] += 1
                
                self.import_log.append({
                    'action': 'duplicate',
                    'product_name': product['product_name'],
                    'match_type': duplicate['type'],
                    'matched_key': duplicate['product_key']
                })
            else:
                # New product - add to batch
                product['created_at'] = datetime.now().isoformat()
                product['updated_at'] = datetime.now().isoformat()
                new_products.append(product)
                self.stats['new_products'] += 1
                
                self.import_log.append({
                    'action': 'new',
                    'product_name': product['product_name'],
                    'brand': product['brand']
                })
            
            if (i + 1) % 100 == 0:
                print(f"  Checked {i + 1}/{len(products)} products...")
                print(f"    New: {self.stats['new_products']} | Duplicates: {self.stats['duplicates']}")
        
        # Batch insert new products
        if new_products and not self.dry_run:
            print(f"\n📝 Inserting {len(new_products)} new products to database...")
            
            # Insert in batches of 50
            for i in range(0, len(new_products), 50):
                batch = new_products[i:i+50]
                try:
                    supabase.table('foods_canonical').insert(batch).execute()
                    print(f"  Inserted batch {i//50 + 1}/{(len(new_products)-1)//50 + 1}")
                except Exception as e:
                    print(f"  Error inserting batch: {e}")
                    self.stats['errors'] += len(batch)
        
        print(f"\n✅ Import complete!")
    
    def print_summary(self):
        """Print import summary"""
        print("\n" + "=" * 80)
        print("📊 FAST IMPORT SUMMARY")
        print("=" * 80)
        print(f"Total products processed: {self.stats['total']}")
        print(f"New products imported: {self.stats['new_products']}")
        print(f"Duplicates found: {self.stats['duplicates']}")
        print(f"  - Fuzzy matches: {self.stats['fuzzy_matches']}")
        print(f"Products skipped: {self.stats['skipped']}")
        print(f"Errors: {self.stats['errors']}")
        
        if self.dry_run:
            print("\n⚠️  DRY RUN - No changes were made to the database")
    
    def save_log(self):
        """Save import log"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = f'data/aadf/import_log_fast_{timestamp}.json'
        
        with open(log_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'dry_run': self.dry_run,
                'statistics': self.stats,
                'sample_log': self.import_log[:100]  # Save first 100 entries
            }, f, indent=2)
        
        print(f"\n💾 Import log saved to: {log_file}")

def main():
    parser = argparse.ArgumentParser(description='Fast AADF import')
    parser.add_argument('--dry-run', action='store_true', help='Run without making changes')
    parser.add_argument('--input', default='data/aadf/aadf_prepared.json', help='Input file')
    
    args = parser.parse_args()
    
    print("⚡ FAST AADF DATASET IMPORTER")
    print("=" * 80)
    
    # Load prepared data
    with open(args.input, 'r') as f:
        products = json.load(f)
    
    print(f"Loaded {len(products)} prepared products")
    
    # Create importer
    importer = AADFImporterFast(dry_run=args.dry_run)
    
    # Import products
    importer.import_batch(products)
    
    # Print summary
    importer.print_summary()
    
    # Save log
    importer.save_log()
    
    # Final database check
    if not args.dry_run and importer.stats['new_products'] > 0:
        print("\n📈 Checking new database coverage...")
        
        # Total AADF products
        aadf_result = supabase.table('foods_canonical')\
            .select('count', count='exact')\
            .ilike('product_url', '%allaboutdogfood%')\
            .execute()
        
        print(f"  Total AADF products now: {aadf_result.count}")

if __name__ == "__main__":
    main()