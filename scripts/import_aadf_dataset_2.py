#!/usr/bin/env python3
"""
Import AADF dataset with deduplication and variant detection
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

class AADFImporter:
    """Import AADF products with deduplication"""
    
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
        self.existing_products = {}
        self.load_existing_products()
    
    def load_existing_products(self):
        """Load all existing products for matching"""
        print("📚 Loading existing products from database...")
        
        # Get all products
        all_products = []
        offset = 0
        batch_size = 1000
        
        while True:
            batch = supabase.table('foods_canonical')\
                .select('product_key, brand, product_name, product_url, ingredients_raw')\
                .range(offset, offset + batch_size - 1)\
                .execute()
            
            if not batch.data:
                break
            
            all_products.extend(batch.data)
            offset += batch_size
            
            if len(batch.data) < batch_size:
                break
        
        print(f"  Loaded {len(all_products)} existing products")
        
        # Create lookup dictionary
        for product in all_products:
            # Normalize for matching
            if product['product_name']:
                clean_name = self.normalize_for_matching(product['product_name'])
                brand = (product['brand'] or '').lower()
                key = f"{brand}|{clean_name}"
                self.existing_products[key] = product
    
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
    
    def find_existing_match(self, product: Dict) -> Optional[Dict]:
        """Find if product already exists in database"""
        
        # 1. Try exact product key match
        existing = supabase.table('foods_canonical')\
            .select('*')\
            .eq('product_key', product['product_key'])\
            .limit(1)\
            .execute()
        
        if existing.data:
            return {'type': 'exact', 'product': existing.data[0]}
        
        # 2. Try normalized name match
        clean_name = self.normalize_for_matching(product['product_name'])
        brand = (product['brand'] or '').lower()
        lookup_key = f"{brand}|{clean_name}"
        
        if lookup_key in self.existing_products:
            return {'type': 'normalized', 'product': self.existing_products[lookup_key]}
        
        # 3. Try fuzzy matching for same brand
        if brand and brand != 'unknown':
            best_match = None
            best_score = 0
            
            for key, existing in self.existing_products.items():
                if key.startswith(brand + '|'):
                    existing_clean = key.split('|', 1)[1]
                    score = fuzz.ratio(clean_name, existing_clean)
                    
                    if score > 85 and score > best_score:
                        best_score = score
                        best_match = existing
            
            if best_match:
                return {'type': 'fuzzy', 'product': best_match, 'score': best_score}
        
        # 4. Try URL match (for AADF products)
        if product.get('product_url'):
            existing = supabase.table('foods_canonical')\
                .select('*')\
                .eq('product_url', product['product_url'])\
                .limit(1)\
                .execute()
            
            if existing.data:
                return {'type': 'url', 'product': existing.data[0]}
        
        return None
    
    def should_update_existing(self, existing: Dict, new_product: Dict) -> Dict:
        """Check if existing product should be updated with new data"""
        updates = {}
        
        # Update if existing lacks ingredients but new has them
        if not existing.get('ingredients_raw') and new_product.get('ingredients_raw'):
            updates['ingredients_raw'] = new_product['ingredients_raw']
        
        # Update nutrition if missing
        if not existing.get('energy_kcal') and new_product.get('energy_kcal'):
            updates['energy_kcal'] = new_product['energy_kcal']
        
        # Update price if missing
        if not existing.get('price_per_day') and new_product.get('price_per_day'):
            updates['price_per_day'] = new_product['price_per_day']
        
        # Update metadata
        if new_product.get('type_of_food') and not existing.get('type_of_food'):
            updates['type_of_food'] = new_product['type_of_food']
        
        if new_product.get('dog_ages') and not existing.get('dog_ages'):
            updates['dog_ages'] = new_product['dog_ages']
        
        # Update URL if new one is AADF
        if new_product.get('product_url') and 'allaboutdogfood' in new_product['product_url']:
            if not existing.get('product_url') or 'allaboutdogfood' not in existing['product_url']:
                updates['product_url'] = new_product['product_url']
        
        if updates:
            updates['updated_at'] = datetime.now().isoformat()
        
        return updates
    
    def import_product(self, product: Dict) -> Dict:
        """Import or update a single product"""
        self.stats['total'] += 1
        
        try:
            # Check for existing match
            match = self.find_existing_match(product)
            
            if match:
                # Product exists
                existing = match['product']
                match_type = match['type']
                
                if match_type == 'fuzzy':
                    self.stats['fuzzy_matches'] += 1
                    log_entry = {
                        'action': 'fuzzy_match',
                        'product_key': product['product_key'],
                        'matched_key': existing['product_key'],
                        'score': match.get('score', 0),
                        'product_name': product['product_name']
                    }
                else:
                    self.stats['duplicates'] += 1
                    log_entry = {
                        'action': 'duplicate',
                        'product_key': product['product_key'],
                        'matched_key': existing['product_key'],
                        'match_type': match_type,
                        'product_name': product['product_name']
                    }
                
                # Check if we should update with new data
                updates = self.should_update_existing(existing, product)
                
                if updates and not self.dry_run:
                    # Update existing product
                    supabase.table('foods_canonical')\
                        .update(updates)\
                        .eq('product_key', existing['product_key'])\
                        .execute()
                    
                    self.stats['updated'] += 1
                    log_entry['updates'] = list(updates.keys())
                
                self.import_log.append(log_entry)
                return log_entry
            
            else:
                # New product
                if not self.dry_run:
                    # Insert to database
                    product['created_at'] = datetime.now().isoformat()
                    product['updated_at'] = datetime.now().isoformat()
                    
                    supabase.table('foods_canonical').insert(product).execute()
                
                self.stats['new_products'] += 1
                log_entry = {
                    'action': 'imported',
                    'product_key': product['product_key'],
                    'product_name': product['product_name'],
                    'brand': product['brand']
                }
                self.import_log.append(log_entry)
                return log_entry
                
        except Exception as e:
            self.stats['errors'] += 1
            log_entry = {
                'action': 'error',
                'product_key': product.get('product_key', 'unknown'),
                'error': str(e)[:200]
            }
            self.import_log.append(log_entry)
            return log_entry
    
    def import_batch(self, products: List[Dict]):
        """Import a batch of products"""
        print(f"\n🔄 Importing {len(products)} products...")
        
        for i, product in enumerate(products):
            # Skip products without essential data
            if not product.get('product_name'):
                self.stats['skipped'] += 1
                continue
            
            self.import_product(product)
            
            if (i + 1) % 100 == 0:
                print(f"  Processed {i + 1}/{len(products)} products...")
                self.print_progress()
        
        print(f"\n✅ Import complete!")
    
    def print_progress(self):
        """Print current progress statistics"""
        print(f"    New: {self.stats['new_products']} | "
              f"Duplicates: {self.stats['duplicates']} | "
              f"Fuzzy: {self.stats['fuzzy_matches']} | "
              f"Updated: {self.stats['updated']} | "
              f"Errors: {self.stats['errors']}")
    
    def print_summary(self):
        """Print import summary"""
        print("\n" + "=" * 80)
        print("📊 IMPORT SUMMARY")
        print("=" * 80)
        print(f"Total products processed: {self.stats['total']}")
        print(f"New products imported: {self.stats['new_products']}")
        print(f"Exact/normalized duplicates found: {self.stats['duplicates']}")
        print(f"Fuzzy matches found (>85%): {self.stats['fuzzy_matches']}")
        print(f"Existing products updated: {self.stats['updated']}")
        print(f"Products skipped: {self.stats['skipped']}")
        print(f"Errors: {self.stats['errors']}")
        
        if self.dry_run:
            print("\n⚠️  DRY RUN - No changes were made to the database")
        
        # Show sample matches
        if self.stats['fuzzy_matches'] > 0:
            print("\n🔍 Sample Fuzzy Matches:")
            fuzzy_logs = [log for log in self.import_log if log.get('action') == 'fuzzy_match']
            for log in fuzzy_logs[:5]:
                print(f"  '{log['product_name'][:50]}...'")
                print(f"    → Matched to: {log['matched_key']} (Score: {log.get('score', 'N/A')}%)")
        
        # Show sample new products
        if self.stats['new_products'] > 0:
            print("\n✨ Sample New Products:")
            new_logs = [log for log in self.import_log if log.get('action') == 'imported']
            for log in new_logs[:5]:
                print(f"  {log['brand']} - {log['product_name'][:50]}...")
    
    def save_log(self):
        """Save import log to file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = f'data/aadf/import_log_{timestamp}.json'
        
        with open(log_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'dry_run': self.dry_run,
                'statistics': self.stats,
                'log': self.import_log
            }, f, indent=2)
        
        print(f"\n💾 Import log saved to: {log_file}")

def main():
    parser = argparse.ArgumentParser(description='Import AADF dataset')
    parser.add_argument('--dry-run', action='store_true', help='Run without making changes')
    parser.add_argument('--input', default='data/aadf/aadf_prepared.json', help='Input file')
    parser.add_argument('--limit', type=int, help='Limit number of products to import')
    
    args = parser.parse_args()
    
    print("📦 AADF DATASET IMPORTER")
    print("=" * 80)
    
    # Load prepared data
    with open(args.input, 'r') as f:
        products = json.load(f)
    
    print(f"Loaded {len(products)} prepared products")
    
    if args.limit:
        products = products[:args.limit]
        print(f"Limited to {len(products)} products")
    
    # Create importer
    importer = AADFImporter(dry_run=args.dry_run)
    
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
        
        # AADF with ingredients
        aadf_ingredients = supabase.table('foods_canonical')\
            .select('count', count='exact')\
            .ilike('product_url', '%allaboutdogfood%')\
            .not_.is_('ingredients_raw', 'null')\
            .execute()
        
        print(f"  Total AADF products: {aadf_result.count}")
        print(f"  With ingredients: {aadf_ingredients.count} ({aadf_ingredients.count/aadf_result.count*100:.1f}%)")

if __name__ == "__main__":
    main()