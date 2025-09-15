#!/usr/bin/env python3
"""
Verify data integrity before and after variant migration
Ensures no data loss occurs
"""

import os
from dotenv import load_dotenv
from supabase import create_client
from typing import Dict, Set

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

class DataVerifier:
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.before_stats = {}
        self.after_stats = {}
    
    def collect_stats(self, table_name: str = 'foods_canonical') -> Dict:
        """Collect comprehensive statistics from a table"""
        
        print(f"📊 Collecting stats from {table_name}...")
        
        stats = {
            'table': table_name,
            'total_products': 0,
            'products_with_ingredients': 0,
            'products_with_nutrition': 0,
            'products_with_complete_nutrition': 0,
            'unique_brands': set(),
            'unique_ingredients': set(),
            'total_protein_values': 0,
            'total_fat_values': 0,
            'product_keys': set(),
            'product_urls': set()
        }
        
        # Get all products in batches
        offset = 0
        batch_size = 1000
        
        while True:
            batch = self.supabase.table(table_name).select(
                'product_key, brand, product_name, product_url, '
                'ingredients_raw, protein_percent, fat_percent, '
                'fiber_percent, ash_percent, moisture_percent'
            ).range(offset, offset + batch_size - 1).execute()
            
            if not batch.data:
                break
            
            for product in batch.data:
                stats['total_products'] += 1
                stats['product_keys'].add(product['product_key'])
                
                if product.get('product_url'):
                    stats['product_urls'].add(product['product_url'])
                
                if product.get('brand'):
                    stats['unique_brands'].add(product['brand'])
                
                if product.get('ingredients_raw'):
                    stats['products_with_ingredients'] += 1
                    # Store first 100 chars as signature
                    stats['unique_ingredients'].add(product['ingredients_raw'][:100])
                
                if product.get('protein_percent') is not None:
                    stats['products_with_nutrition'] += 1
                    stats['total_protein_values'] += product['protein_percent']
                
                if product.get('fat_percent') is not None:
                    stats['total_fat_values'] += product['fat_percent']
                
                # Check complete nutrition
                if all(product.get(field) is not None for field in 
                      ['protein_percent', 'fat_percent', 'fiber_percent', 
                       'ash_percent', 'moisture_percent']):
                    stats['products_with_complete_nutrition'] += 1
            
            offset += batch_size
            
            if offset % 5000 == 0:
                print(f"  Processed {offset} products...")
        
        # Convert sets to counts for display
        stats['unique_brands_count'] = len(stats['unique_brands'])
        stats['unique_ingredients_count'] = len(stats['unique_ingredients'])
        stats['unique_product_keys'] = len(stats['product_keys'])
        stats['unique_urls'] = len(stats['product_urls'])
        
        print(f"  ✅ Collected stats for {stats['total_products']} products")
        
        return stats
    
    def compare_stats(self, before: Dict, after_main: Dict, after_variants: Dict = None) -> Dict:
        """Compare statistics before and after migration"""
        
        comparison = {
            'data_preserved': True,
            'issues': [],
            'improvements': []
        }
        
        # Calculate combined after stats
        after_total = after_main['total_products']
        if after_variants:
            after_total += after_variants['total_products']
        
        # Check total product count
        if abs(before['total_products'] - after_total) > 0:
            diff = after_total - before['total_products']
            if diff > 0:
                comparison['issues'].append(f"Product count increased by {diff}")
            else:
                comparison['improvements'].append(f"Product count reduced by {-diff} (variants consolidated)")
        
        # Check ingredients preservation
        if after_main['products_with_ingredients'] < before['products_with_ingredients']:
            diff = before['products_with_ingredients'] - after_main['products_with_ingredients']
            comparison['issues'].append(f"Lost ingredients from {diff} products")
            comparison['data_preserved'] = False
        elif after_main['products_with_ingredients'] > before['products_with_ingredients']:
            diff = after_main['products_with_ingredients'] - before['products_with_ingredients']
            comparison['improvements'].append(f"Added ingredients to {diff} products (consolidation)")
        
        # Check nutrition preservation
        if after_main['products_with_nutrition'] < before['products_with_nutrition']:
            diff = before['products_with_nutrition'] - after_main['products_with_nutrition']
            comparison['issues'].append(f"Lost nutrition from {diff} products")
            comparison['data_preserved'] = False
        elif after_main['products_with_nutrition'] > before['products_with_nutrition']:
            diff = after_main['products_with_nutrition'] - before['products_with_nutrition']
            comparison['improvements'].append(f"Added nutrition to {diff} products (consolidation)")
        
        # Check brand preservation
        if after_main['unique_brands_count'] < before['unique_brands_count']:
            comparison['issues'].append(f"Lost some brands")
        
        # Check URL preservation (should be same total)
        total_urls_after = after_main['unique_urls']
        if after_variants:
            total_urls_after += after_variants['unique_urls']
        
        if total_urls_after < before['unique_urls']:
            comparison['issues'].append(f"Lost {before['unique_urls'] - total_urls_after} URLs")
            comparison['data_preserved'] = False
        
        return comparison
    
    def print_report(self, stats: Dict, title: str):
        """Print a statistics report"""
        
        print(f"\n{'=' * 60}")
        print(f"📊 {title}")
        print(f"{'=' * 60}")
        
        print(f"Total products: {stats['total_products']:,}")
        print(f"Unique brands: {stats['unique_brands_count']}")
        print(f"Products with ingredients: {stats['products_with_ingredients']:,} ({stats['products_with_ingredients']/stats['total_products']*100:.1f}%)")
        print(f"Products with nutrition: {stats['products_with_nutrition']:,} ({stats['products_with_nutrition']/stats['total_products']*100:.1f}%)")
        print(f"Products with complete nutrition: {stats['products_with_complete_nutrition']:,}")
        print(f"Unique ingredients patterns: {stats['unique_ingredients_count']}")
        print(f"Unique URLs: {stats['unique_urls']:,}")
        
        if stats['products_with_nutrition'] > 0:
            avg_protein = stats['total_protein_values'] / stats['products_with_nutrition']
            avg_fat = stats['total_fat_values'] / stats['products_with_nutrition']
            print(f"Average protein: {avg_protein:.1f}%")
            print(f"Average fat: {avg_fat:.1f}%")
    
    def verify_before_migration(self):
        """Verify data before migration"""
        
        print("\n🔍 VERIFYING DATA BEFORE MIGRATION")
        print("=" * 60)
        
        # Collect current stats
        self.before_stats = self.collect_stats('foods_canonical')
        
        # Check backup table
        try:
            backup_stats = self.collect_stats('foods_canonical_backup_20241213')
            
            # Compare with backup
            if backup_stats['total_products'] != self.before_stats['total_products']:
                print("\n⚠️  Warning: Backup has different product count!")
                print(f"   Current: {self.before_stats['total_products']}")
                print(f"   Backup: {backup_stats['total_products']}")
        except:
            print("\n⚠️  Backup table not found or empty")
        
        # Print current state
        self.print_report(self.before_stats, "CURRENT DATABASE STATE")
        
        return self.before_stats
    
    def verify_after_migration(self):
        """Verify data after migration"""
        
        print("\n🔍 VERIFYING DATA AFTER MIGRATION")
        print("=" * 60)
        
        # Collect stats from main table
        main_stats = self.collect_stats('foods_canonical')
        
        # Collect stats from variants table
        try:
            variant_stats = self.collect_stats('product_variants')
        except:
            variant_stats = None
            print("  Variants table not found or empty")
        
        # Print new state
        self.print_report(main_stats, "MAIN TABLE AFTER MIGRATION")
        
        if variant_stats:
            print(f"\n📦 VARIANTS TABLE")
            print(f"  Total variants: {variant_stats['total_products']}")
        
        # Compare before and after
        print("\n🔄 COMPARISON")
        print("=" * 60)
        
        comparison = self.compare_stats(self.before_stats, main_stats, variant_stats)
        
        if comparison['data_preserved']:
            print("✅ All data preserved!")
        else:
            print("⚠️  Data preservation issues detected!")
        
        if comparison['improvements']:
            print("\n💚 Improvements:")
            for improvement in comparison['improvements']:
                print(f"  - {improvement}")
        
        if comparison['issues']:
            print("\n⚠️  Issues:")
            for issue in comparison['issues']:
                print(f"  - {issue}")
        
        return comparison

def main():
    verifier = DataVerifier()
    
    # Run verification
    verifier.verify_before_migration()
    
    print("\n" + "=" * 60)
    print("📝 VERIFICATION COMPLETE")
    print("=" * 60)
    print("\nThis verification shows the current state.")
    print("Run again after migration to compare.")

if __name__ == "__main__":
    main()