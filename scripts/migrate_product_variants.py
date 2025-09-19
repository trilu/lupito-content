#!/usr/bin/env python3
"""
Migrate size and pack variants to product_variants table
Consolidates data to parent products
"""

import os
import json
import argparse
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

class VariantMigrator:
    def __init__(self, report_file: str, dry_run: bool = True):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.report_file = report_file
        self.dry_run = dry_run
        self.report = None
        
        # Statistics
        self.stats = {
            'groups_processed': 0,
            'variants_migrated': 0,
            'data_consolidated': 0,
            'errors': 0
        }
        
        print(f"🔄 VARIANT MIGRATION {'(DRY RUN)' if dry_run else ''}")
        print("=" * 60)
    
    def load_report(self):
        """Load the variant detection report"""
        print(f"Loading report from {self.report_file}...")
        
        with open(self.report_file, 'r') as f:
            self.report = json.load(f)
        
        print(f"✅ Loaded {len(self.report['groups'])} variant groups")
        return self.report
    
    def verify_backup(self):
        """Verify backup table exists and has data"""
        print("\n🔍 Verifying backup...")
        
        try:
            result = self.supabase.table('foods_canonical_backup_20241213').select(
                'product_key', count='exact'
            ).limit(1).execute()
            
            if result.count > 0:
                print(f"  ✅ Backup table exists with {result.count} products")
                return True
            else:
                print("  ❌ Backup table is empty!")
                return False
        except Exception as e:
            print(f"  ❌ Backup table not found: {e}")
            return False
    
    def consolidate_data(self, parent_key: str, variants: List[Dict]) -> Dict:
        """Consolidate data from variants to parent"""
        
        # Get current parent data
        parent_result = self.supabase.table('foods_canonical').select('*')\
            .eq('product_key', parent_key).execute()
        
        if not parent_result.data:
            raise Exception(f"Parent product not found: {parent_key}")
        
        parent = parent_result.data[0]
        updates = {}
        
        # Consolidate ingredients if parent doesn't have them
        if not parent.get('ingredients_raw'):
            for variant in variants:
                # Get variant data from database
                v_result = self.supabase.table('foods_canonical').select(
                    'ingredients_raw, ingredients_tokens, ingredients_source'
                ).eq('product_key', variant['product_key']).execute()
                
                if v_result.data and v_result.data[0].get('ingredients_raw'):
                    updates['ingredients_raw'] = v_result.data[0]['ingredients_raw']
                    updates['ingredients_tokens'] = v_result.data[0].get('ingredients_tokens')
                    updates['ingredients_source'] = v_result.data[0].get('ingredients_source', 'site')
                    print(f"    📝 Taking ingredients from variant: {variant['product_name'][:40]}")
                    break
        
        # Consolidate nutrition if parent doesn't have it
        nutrition_fields = ['protein_percent', 'fat_percent', 'fiber_percent', 
                          'ash_percent', 'moisture_percent', 'macros_source']
        
        if not parent.get('protein_percent'):
            for variant in variants:
                v_result = self.supabase.table('foods_canonical').select(
                    ','.join(nutrition_fields)
                ).eq('product_key', variant['product_key']).execute()
                
                if v_result.data and v_result.data[0].get('protein_percent'):
                    for field in nutrition_fields:
                        if v_result.data[0].get(field) is not None:
                            updates[field] = v_result.data[0][field]
                    print(f"    🥩 Taking nutrition from variant: {variant['product_name'][:40]}")
                    break
        
        # Normalize product name (remove size/pack indicators)
        import re
        normalized_name = parent['product_name']
        normalized_name = re.sub(r'\b\d+(?:\.\d+)?\s*(?:kg|g|lb|oz|ml|l)\b', '', normalized_name, flags=re.IGNORECASE)
        normalized_name = re.sub(r'\b\d+\s*x\s*\d+(?:\.\d+)?(?:\s*(?:kg|g|lb|oz|ml|l|cans?|pouches?))?\b', '', normalized_name, flags=re.IGNORECASE)
        normalized_name = re.sub(r'\s+', ' ', normalized_name).strip()
        normalized_name = re.sub(r'\s*[,\-]\s*$', '', normalized_name)
        
        if normalized_name != parent['product_name']:
            updates['product_name'] = normalized_name
            print(f"    📝 Normalized name: {normalized_name[:60]}")
        
        return updates
    
    def migrate_group(self, group: Dict):
        """Migrate a single variant group"""
        
        brand = group['brand']
        base_name = group['base_name']
        parent = group['selected_parent']
        variants = group['variants']
        
        print(f"\n📦 Processing: {brand} - {base_name[:40]}")
        print(f"   Parent: {parent['product_name'][:60]}")
        print(f"   Variants: {len(variants)}")
        
        try:
            # Log the group identification
            if not self.dry_run:
                self.supabase.table('variant_migration_log').insert({
                    'action_type': 'group_identified',
                    'brand': brand,
                    'base_name': base_name[:100],
                    'parent_product_key': parent['product_key'],
                    'variant_count': len(variants),
                    'notes': f"Group with {len(variants)} variants identified"
                }).execute()
            
            # Consolidate data to parent
            updates = self.consolidate_data(parent['product_key'], variants)
            
            if updates and not self.dry_run:
                # Update parent product
                self.supabase.table('foods_canonical').update(updates)\
                    .eq('product_key', parent['product_key']).execute()
                
                # Log consolidation
                self.supabase.table('variant_migration_log').insert({
                    'action_type': 'data_consolidated',
                    'parent_product_key': parent['product_key'],
                    'data_after': json.dumps(updates),
                    'notes': f"Consolidated data from {len(variants)} variants"
                }).execute()
                
                self.stats['data_consolidated'] += 1
            
            # Migrate non-parent variants
            variants_migrated = 0
            for variant in variants:
                if variant['product_key'] == parent['product_key']:
                    continue  # Skip parent
                
                if not self.dry_run:
                    # Get full product data
                    v_data = self.supabase.table('foods_canonical').select('*')\
                        .eq('product_key', variant['product_key']).execute()
                    
                    if not v_data.data:
                        print(f"    ⚠️ Variant not found: {variant['product_key']}")
                        continue
                    
                    original_data = v_data.data[0]
                    
                    # Create variant record
                    variant_record = {
                        'parent_product_key': parent['product_key'],
                        'variant_product_key': variant['product_key'],
                        'variant_type': variant['size_info']['variant_type'],
                        'size_value': variant['size_info'].get('size_value'),
                        'pack_value': variant['size_info'].get('pack_value'),
                        'product_name': variant['product_name'],
                        'product_url': original_data.get('product_url'),
                        'original_data': json.dumps(original_data, default=str)
                    }
                    
                    # Insert into variants table
                    self.supabase.table('product_variants').insert(variant_record).execute()
                    
                    # Delete from main table
                    self.supabase.table('foods_canonical').delete()\
                        .eq('product_key', variant['product_key']).execute()
                    
                    # Log migration
                    self.supabase.table('variant_migration_log').insert({
                        'action_type': 'variant_moved',
                        'parent_product_key': parent['product_key'],
                        'variant_product_key': variant['product_key'],
                        'notes': f"Moved to variants table"
                    }).execute()
                    
                    variants_migrated += 1
                else:
                    print(f"    Would migrate: {variant['product_name'][:50]}")
                    variants_migrated += 1
            
            self.stats['groups_processed'] += 1
            self.stats['variants_migrated'] += variants_migrated
            
            print(f"   ✅ Migrated {variants_migrated} variants")
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:100]}")
            self.stats['errors'] += 1
            
            if not self.dry_run:
                # Log error
                self.supabase.table('variant_migration_log').insert({
                    'action_type': 'error',
                    'brand': brand,
                    'base_name': base_name[:100],
                    'parent_product_key': parent['product_key'],
                    'notes': f"Error: {str(e)[:200]}"
                }).execute()
    
    def run_migration(self, limit: Optional[int] = None):
        """Run the full migration"""
        
        # Load report
        if not self.report:
            self.load_report()
        
        # Verify backup exists
        if not self.dry_run:
            if not self.verify_backup():
                print("\n❌ Cannot proceed without backup!")
                return False
        
        # Process groups
        groups_to_process = self.report['groups'][:limit] if limit else self.report['groups']
        
        print(f"\n🚀 Processing {len(groups_to_process)} variant groups...")
        
        for i, group in enumerate(groups_to_process, 1):
            print(f"\n[{i}/{len(groups_to_process)}]", end="")
            self.migrate_group(group)
            
            # Progress update every 10 groups
            if i % 10 == 0:
                print(f"\n📊 Progress: {i}/{len(groups_to_process)} groups processed")
        
        # Final summary
        self.print_summary()
        
        return self.stats['errors'] == 0
    
    def print_summary(self):
        """Print migration summary"""
        print("\n" + "=" * 60)
        print("📊 MIGRATION SUMMARY")
        print("=" * 60)
        
        print(f"Groups processed: {self.stats['groups_processed']}")
        print(f"Variants migrated: {self.stats['variants_migrated']}")
        print(f"Data consolidated: {self.stats['data_consolidated']}")
        print(f"Errors: {self.stats['errors']}")
        
        if self.dry_run:
            print("\n⚠️  This was a DRY RUN - no changes were made")
            print("Run with --execute to perform actual migration")
        else:
            print("\n✅ Migration complete!")
            
            # Check final database state
            try:
                total = self.supabase.table('foods_canonical').select('*', count='exact').execute()
                variants = self.supabase.table('product_variants').select('*', count='exact').execute()
                
                print(f"\nDatabase state:")
                print(f"  Main table: {total.count} products")
                print(f"  Variants table: {variants.count} variants")
            except:
                pass
    
    def rollback(self):
        """Rollback migration by restoring from backup"""
        print("\n⚠️  ROLLBACK MIGRATION")
        print("=" * 60)
        
        if self.dry_run:
            print("Cannot rollback in dry run mode")
            return
        
        response = input("This will restore from backup. Continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Rollback cancelled")
            return
        
        try:
            # Clear current tables
            print("Clearing current data...")
            self.supabase.table('foods_canonical').delete().neq('product_key', '').execute()
            self.supabase.table('product_variants').delete().neq('variant_id', 0).execute()
            
            # Restore from backup
            print("Restoring from backup...")
            # This would need to be done via SQL directly
            print("⚠️  Please run the following SQL in Supabase:")
            print("INSERT INTO foods_canonical SELECT * FROM foods_canonical_backup_20241213;")
            
            print("✅ Rollback instructions provided")
            
        except Exception as e:
            print(f"❌ Rollback error: {e}")

def main():
    parser = argparse.ArgumentParser(description='Migrate product variants')
    parser.add_argument('--report', default='data/variant_detection_report_20250913_120648.json',
                       help='Path to variant detection report')
    parser.add_argument('--execute', action='store_true',
                       help='Execute migration (default is dry run)')
    parser.add_argument('--limit', type=int,
                       help='Limit number of groups to process')
    parser.add_argument('--rollback', action='store_true',
                       help='Rollback migration')
    
    args = parser.parse_args()
    
    migrator = VariantMigrator(args.report, dry_run=not args.execute)
    
    if args.rollback:
        migrator.rollback()
    else:
        migrator.run_migration(limit=args.limit)

if __name__ == "__main__":
    main()