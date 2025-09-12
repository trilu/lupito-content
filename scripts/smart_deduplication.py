#!/usr/bin/env python3
"""
Smart Deduplication Script for Pet Food Database
Identifies duplicates and keeps the product with the most complete data
"""

import os
import json
import re
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Tuple
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_KEY')
)

class ProductDeduplicator:
    def __init__(self):
        self.supabase = supabase
        self.merge_log = []
        self.deletion_log = []
        self.stats = {
            'total_products': 0,
            'duplicate_groups': 0,
            'products_merged': 0,
            'products_deleted': 0,
            'suspicious_products': 0
        }
    
    def normalize_product_name(self, name: str) -> str:
        """Normalize product name for matching"""
        if not name:
            return ""
        
        # Convert to lowercase
        normalized = name.lower()
        
        # Remove special characters but keep spaces
        normalized = re.sub(r'[^\w\s]', '', normalized)
        
        # Remove extra spaces
        normalized = ' '.join(normalized.split())
        
        return normalized
    
    def create_product_key(self, product: Dict) -> str:
        """Create a key for grouping potential duplicates"""
        brand = (product.get('brand') or '').lower().replace(' ', '')
        name = self.normalize_product_name(product.get('product_name', ''))
        form = (product.get('form') or '').lower()
        
        # Remove brand from product name if it starts with it
        brand_words = (product.get('brand') or '').lower().split()
        for word in brand_words:
            if name.startswith(word + ' '):
                name = name[len(word)+1:]
        
        return f"{brand}|{name}|{form}"
    
    def score_product(self, product: Dict) -> int:
        """Score a product based on data completeness"""
        score = 0
        
        # Major data points
        if product.get('ingredients_raw'):
            score += 40
        
        # Check for complete macros
        macro_fields = ['protein_percent', 'fat_percent']
        if all(product.get(field) for field in macro_fields):
            score += 30
        
        # URL and image
        if product.get('product_url'):
            score += 20
        
        if product.get('image_url'):
            score += 10
        
        # Additional nutrition data
        if product.get('kcal_per_100g'):
            score += 15
        
        if product.get('fiber_percent'):
            score += 5
        
        if product.get('moisture_percent'):
            score += 5
        
        if product.get('ash_percent'):
            score += 5
        
        # Has price data
        if product.get('price_per_kg'):
            score += 10
        
        # Data source preference (newer sources might be better)
        source_scores = {
            'food_candidates': 1,
            'food_candidates_sc': 2,
            'food_brands': 3
        }
        score += source_scores.get(product.get('source'), 0)
        
        return score
    
    def merge_products(self, products: List[Dict]) -> Tuple[Dict, List[Dict]]:
        """
        Merge duplicate products, keeping the best one and merging unique data
        Returns: (winner_product, products_to_delete)
        """
        # Sort by score (highest first)
        scored_products = [(p, self.score_product(p)) for p in products]
        scored_products.sort(key=lambda x: x[1], reverse=True)
        
        # The winner is the highest scoring product
        winner = scored_products[0][0].copy()
        products_to_delete = []
        
        # Merge unique data from other products into winner
        for product, score in scored_products[1:]:
            # Track for deletion
            products_to_delete.append(product)
            
            # Merge data if winner is missing it
            fields_to_merge = [
                'ingredients_raw', 'ingredients_tokens', 'protein_percent', 
                'fat_percent', 'fiber_percent', 'moisture_percent', 
                'ash_percent', 'kcal_per_100g', 'product_url', 
                'image_url', 'price_per_kg', 'description'
            ]
            
            for field in fields_to_merge:
                if not winner.get(field) and product.get(field):
                    winner[field] = product[field]
                    self.merge_log.append({
                        'action': 'merged_field',
                        'field': field,
                        'from_product': product.get('product_key'),
                        'to_product': winner.get('product_key'),
                        'value': product[field]
                    })
        
        return winner, products_to_delete
    
    def identify_suspicious_products(self, products: List[Dict]) -> List[Dict]:
        """Identify products with suspicious names that might not be real"""
        suspicious = []
        
        for product in products:
            brand = product.get('brand', '')
            name = product.get('product_name', '')
            
            # Check if name is just the brand
            if name and brand and name.lower() == brand.lower():
                suspicious.append({
                    'product': product,
                    'reason': 'name_equals_brand'
                })
            
            # Check if name is too short
            elif name and len(name) < 5:
                suspicious.append({
                    'product': product,
                    'reason': 'name_too_short'
                })
            
            # Check if name is just a single generic word
            elif name and name.lower() in ['fish', 'beef', 'chicken', 'mini', 'adult', 'puppy', 'senior']:
                suspicious.append({
                    'product': product,
                    'reason': 'generic_name'
                })
        
        return suspicious
    
    def find_duplicates(self) -> Dict[str, List[Dict]]:
        """Find all duplicate products grouped by normalized key"""
        print("Loading all products from database...")
        
        # Load all products
        all_products = []
        offset = 0
        limit = 1000
        
        while True:
            response = self.supabase.table('foods_canonical').select('*').range(offset, offset + limit - 1).execute()
            batch = response.data
            if not batch:
                break
            all_products.extend(batch)
            offset += limit
            print(f"  Loaded {len(all_products)} products...", end='\r')
        
        print(f"  Loaded {len(all_products)} products... Done!")
        self.stats['total_products'] = len(all_products)
        
        # Group by normalized key
        print("\nGrouping products by normalized key...")
        product_groups = defaultdict(list)
        
        for product in all_products:
            key = self.create_product_key(product)
            product_groups[key].append(product)
        
        # Filter to only groups with duplicates
        duplicate_groups = {k: v for k, v in product_groups.items() if len(v) > 1}
        self.stats['duplicate_groups'] = len(duplicate_groups)
        
        print(f"Found {len(duplicate_groups)} groups with duplicates")
        
        return duplicate_groups, all_products
    
    def execute_deduplication(self, dry_run=True):
        """Execute the deduplication process"""
        print("\n" + "="*60)
        print("SMART DEDUPLICATION PROCESS")
        print("="*60)
        print(f"Mode: {'DRY RUN' if dry_run else 'LIVE EXECUTION'}")
        print()
        
        # Find duplicates
        duplicate_groups, all_products = self.find_duplicates()
        
        # Find suspicious products
        print("\nIdentifying suspicious products...")
        suspicious = self.identify_suspicious_products(all_products)
        self.stats['suspicious_products'] = len(suspicious)
        print(f"Found {len(suspicious)} suspicious products")
        
        # Process duplicates
        products_to_update = []
        products_to_delete = []
        
        print("\nProcessing duplicate groups...")
        for key, products in duplicate_groups.items():
            if len(products) > 1:
                winner, to_delete = self.merge_products(products)
                products_to_update.append(winner)
                products_to_delete.extend(to_delete)
                
                # Log the merge
                self.merge_log.append({
                    'group_key': key,
                    'products_merged': len(products),
                    'winner': winner.get('product_key'),
                    'deleted': [p.get('product_key') for p in to_delete]
                })
        
        self.stats['products_merged'] = len(products_to_update)
        self.stats['products_deleted'] = len(products_to_delete)
        
        # Generate report
        print("\n" + "="*60)
        print("DEDUPLICATION SUMMARY")
        print("="*60)
        print(f"Total products analyzed: {self.stats['total_products']}")
        print(f"Duplicate groups found: {self.stats['duplicate_groups']}")
        print(f"Products to be merged: {self.stats['products_merged']}")
        print(f"Products to be deleted: {self.stats['products_deleted']}")
        print(f"Suspicious products found: {self.stats['suspicious_products']}")
        
        # Show examples
        if duplicate_groups:
            print("\nExample duplicate groups:")
            for i, (key, products) in enumerate(list(duplicate_groups.items())[:3]):
                print(f"\n  Group {i+1}: {key}")
                for p in products[:3]:
                    score = self.score_product(p)
                    print(f"    - {p.get('product_name')} (Score: {score}, Source: {p.get('source')})")
        
        if suspicious:
            print("\nExample suspicious products:")
            for item in suspicious[:5]:
                p = item['product']
                print(f"  - Brand: \"{p.get('brand')}\", Name: \"{p.get('product_name')}\" ({item['reason']})")
        
        # Save audit trail
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        audit_file = f"data/deduplication_audit_{timestamp}.json"
        
        audit_data = {
            'timestamp': timestamp,
            'stats': self.stats,
            'merge_log': self.merge_log,
            'suspicious_products': [
                {
                    'brand': s['product'].get('brand'),
                    'name': s['product'].get('product_name'),
                    'key': s['product'].get('product_key'),
                    'reason': s['reason']
                }
                for s in suspicious
            ],
            'products_to_delete': [
                {
                    'brand': p.get('brand'),
                    'name': p.get('product_name'),
                    'key': p.get('product_key')
                }
                for p in products_to_delete
            ]
        }
        
        os.makedirs('data', exist_ok=True)
        with open(audit_file, 'w') as f:
            json.dump(audit_data, f, indent=2)
        
        print(f"\nAudit trail saved to: {audit_file}")
        
        if not dry_run:
            print("\n" + "="*60)
            print("EXECUTING DATABASE UPDATES")
            print("="*60)
            
            # Update merged products
            print(f"\nUpdating {len(products_to_update)} merged products...")
            for product in products_to_update:
                try:
                    # Remove fields that shouldn't be updated
                    update_data = {k: v for k, v in product.items() 
                                 if k not in ['created_at', 'updated_at']}
                    
                    response = self.supabase.table('foods_canonical').update(update_data).eq(
                        'product_key', product['product_key']
                    ).execute()
                    
                    print(f"  Updated: {product.get('product_name')}")
                except Exception as e:
                    print(f"  Error updating {product.get('product_key')}: {e}")
            
            # Delete duplicate products
            print(f"\nDeleting {len(products_to_delete)} duplicate products...")
            for product in products_to_delete:
                try:
                    response = self.supabase.table('foods_canonical').delete().eq(
                        'product_key', product['product_key']
                    ).execute()
                    
                    print(f"  Deleted: {product.get('product_name')}")
                except Exception as e:
                    print(f"  Error deleting {product.get('product_key')}: {e}")
            
            print("\nDatabase updates completed!")
        else:
            print("\n⚠️  DRY RUN - No changes made to database")
            print("Run with --execute flag to apply changes")
        
        return audit_data

def main():
    import sys
    
    # Check for execute flag
    dry_run = '--execute' not in sys.argv
    
    # Create deduplicator and run
    deduplicator = ProductDeduplicator()
    audit_data = deduplicator.execute_deduplication(dry_run=dry_run)
    
    print("\n✅ Deduplication process completed!")

if __name__ == "__main__":
    main()