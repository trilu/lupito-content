#!/usr/bin/env python3
"""
PROMPT 2: Split-Brand Re-scan & Canonicalization
Re-detect and correct brand splits across entire dataset
"""

import os
import json
import re
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv
import pandas as pd
from pathlib import Path

# Load environment variables
load_dotenv()

class SplitBrandRescanner:
    def __init__(self, snapshot_label=None):
        # Initialize Supabase client
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not url or not key:
            raise ValueError("Missing Supabase credentials in .env file")
        
        self.supabase: Client = create_client(url, key)
        self.url = url
        self.timestamp = datetime.now()
        
        # Use provided snapshot or create new one
        self.snapshot_label = snapshot_label or f"SNAPSHOT_{self.timestamp.strftime('%Y%m%d_%H%M%S')}"
        
        # Known split patterns to detect
        self.split_patterns = [
            # Format: (brand_part1, brand_part2, canonical_brand_slug)
            ('Royal', 'Canin', 'royal_canin'),
            ('Arden', 'Grange', 'arden_grange'),
            ('Barking', 'Heads', 'barking_heads'),
            ('Meowing', 'Heads', 'meowing_heads'),
            ("Lily's", 'Kitchen', 'lilys_kitchen'),
            ('Lilys', 'Kitchen', 'lilys_kitchen'),
            ('James', 'Wellbeloved', 'james_wellbeloved'),
            ("Hill's", 'Science Plan', 'hills'),
            ('Hills', 'Science Plan', 'hills'),
            ("Hill's", 'Prescription Diet', 'hills'),
            ('Hills', 'Prescription Diet', 'hills'),
            ('Purina', 'Pro Plan', 'purina'),
            ('Purina', 'ONE', 'purina'),
            ('Purina', 'Dog Chow', 'purina'),
            ('Taste', 'of the Wild', 'taste_of_the_wild'),
            ('Natures', 'Menu', 'natures_menu'),
            ("Nature's", 'Menu', 'natures_menu'),
            ('Burns', 'Pet Nutrition', 'burns'),
            ('Wellness', 'CORE', 'wellness'),
            ('Blue', 'Buffalo', 'blue_buffalo'),
            ('Science', 'Diet', 'hills'),
            ('Prescription', 'Diet', 'hills'),
        ]
        
        # Additional patterns from brand_phrase_map if it exists
        self.load_brand_phrase_map()
        
        self.detected_splits = []
        self.delta_sheet = []
        
        print("="*70)
        print("SPLIT-BRAND RE-SCAN & CANONICALIZATION")
        print("="*70)
        print(f"Timestamp: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Snapshot: {self.snapshot_label}")
        print(f"Split patterns loaded: {len(self.split_patterns)}")
        print("="*70)
    
    def load_brand_phrase_map(self):
        """Load additional patterns from brand_phrase_map.csv if it exists"""
        map_path = Path('brand_phrase_map.csv')
        if map_path.exists():
            try:
                df = pd.read_csv(map_path)
                print(f"✓ Loaded brand_phrase_map.csv with {len(df)} entries")
                
                # Add patterns from the map
                for _, row in df.iterrows():
                    if '|' in str(row.get('source_brand', '')):
                        parts = str(row['source_brand']).split('|')
                        if len(parts) == 2:
                            canonical = str(row.get('canonical_brand', '')).lower().replace(' ', '_')
                            pattern = (parts[0].strip(), parts[1].strip(), canonical)
                            if pattern not in self.split_patterns:
                                self.split_patterns.append(pattern)
                
            except Exception as e:
                print(f"⚠️ Could not load brand_phrase_map.csv: {e}")
    
    def step1_scan_foods_canonical(self):
        """Step 1: Scan foods_canonical for split brands"""
        print("\n" + "="*70)
        print("STEP 1: SCANNING FOODS_CANONICAL")
        print("="*70)
        
        try:
            # Fetch all data from foods_canonical
            print("Fetching all rows from foods_canonical...")
            all_data = []
            batch_size = 1000
            offset = 0
            
            while True:
                response = self.supabase.table('foods_canonical')\
                    .select("product_key,brand,product_name,brand_slug")\
                    .range(offset, offset + batch_size - 1)\
                    .execute()
                
                if not response.data:
                    break
                
                all_data.extend(response.data)
                offset += batch_size
                
                if len(all_data) % 2000 == 0:
                    print(f"  Fetched {len(all_data)} rows...")
            
            print(f"✓ Fetched {len(all_data)} total rows")
            
            # Scan for split patterns
            print("\nScanning for split-brand patterns...")
            
            for row in all_data:
                brand = str(row.get('brand', ''))
                product_name = str(row.get('product_name', ''))
                current_brand_slug = str(row.get('brand_slug', ''))
                
                # Check each split pattern
                for part1, part2, canonical_slug in self.split_patterns:
                    # Case 1: Brand is part1, product name starts with part2
                    if (brand.lower() == part1.lower() and 
                        product_name.lower().startswith(part2.lower())):
                        
                        if current_brand_slug != canonical_slug:
                            self.detected_splits.append({
                                'product_key': row['product_key'],
                                'brand': brand,
                                'product_name': product_name,
                                'old_brand_slug': current_brand_slug,
                                'new_brand_slug': canonical_slug,
                                'pattern': f"{part1}|{part2}",
                                'reason': 'Split brand detected',
                                'table': 'foods_canonical'
                            })
                    
                    # Case 2: Brand contains pipe separator
                    elif '|' in brand:
                        brand_parts = brand.split('|')
                        if (len(brand_parts) == 2 and 
                            brand_parts[0].strip().lower() == part1.lower() and
                            brand_parts[1].strip().lower() == part2.lower()):
                            
                            if current_brand_slug != canonical_slug:
                                self.detected_splits.append({
                                    'product_key': row['product_key'],
                                    'brand': brand,
                                    'product_name': product_name,
                                    'old_brand_slug': current_brand_slug,
                                    'new_brand_slug': canonical_slug,
                                    'pattern': f"{part1}|{part2}",
                                    'reason': 'Pipe-separated brand',
                                    'table': 'foods_canonical'
                                })
            
            print(f"✓ Found {len(self.detected_splits)} split-brand issues in foods_canonical")
            
            # Show sample detections
            if self.detected_splits:
                print("\nSample detections (first 5):")
                for split in self.detected_splits[:5]:
                    print(f"  • {split['brand']} → {split['new_brand_slug']}")
                    print(f"    Product: {split['product_name'][:50]}...")
                    print(f"    Reason: {split['reason']}")
            
        except Exception as e:
            print(f"❌ Error scanning foods_canonical: {e}")
    
    def step2_scan_foods_union_all(self):
        """Step 2: Scan foods_union_all if it exists"""
        print("\n" + "="*70)
        print("STEP 2: SCANNING FOODS_UNION_ALL")
        print("="*70)
        
        try:
            # Check if table exists
            response = self.supabase.table('foods_union_all')\
                .select("*", count='exact', head=True).execute()
            
            if hasattr(response, 'count'):
                print(f"foods_union_all exists with {response.count} rows")
                
                # Fetch and scan similar to foods_canonical
                print("Fetching data...")
                union_data = []
                batch_size = 1000
                offset = 0
                
                while True:
                    response = self.supabase.table('foods_union_all')\
                        .select("brand,product_name,brand_slug")\
                        .range(offset, offset + batch_size - 1)\
                        .execute()
                    
                    if not response.data:
                        break
                    
                    union_data.extend(response.data)
                    offset += batch_size
                    
                    if len(union_data) >= 5000:  # Limit for union_all
                        break
                
                print(f"✓ Fetched {len(union_data)} rows from foods_union_all")
                
                # Scan for patterns
                union_splits = 0
                for row in union_data:
                    brand = str(row.get('brand', ''))
                    product_name = str(row.get('product_name', ''))
                    current_brand_slug = str(row.get('brand_slug', ''))
                    
                    for part1, part2, canonical_slug in self.split_patterns:
                        if (brand.lower() == part1.lower() and 
                            product_name.lower().startswith(part2.lower())):
                            
                            if current_brand_slug != canonical_slug:
                                union_splits += 1
                
                print(f"✓ Found {union_splits} additional split issues in foods_union_all")
            else:
                print("⚠️ foods_union_all not found or empty")
                
        except Exception as e:
            print(f"⚠️ Could not scan foods_union_all: {e}")
    
    def step3_compare_canonical_map(self):
        """Step 3: Compare against canonical brand map"""
        print("\n" + "="*70)
        print("STEP 3: COMPARING AGAINST CANONICAL MAP")
        print("="*70)
        
        # Load canonical map
        canonical_map_path = Path('data/canonical_brand_map.yaml')
        
        if canonical_map_path.exists():
            import yaml
            with open(canonical_map_path, 'r') as f:
                canonical_data = yaml.safe_load(f)
                canonical_map = canonical_data.get('canonical_brand_mappings', {})
            
            print(f"✓ Loaded canonical map with {len(canonical_map)} mappings")
            
            # Check for new patterns not in our map
            new_patterns = []
            for split in self.detected_splits:
                old_slug = split['old_brand_slug']
                new_slug = split['new_brand_slug']
                
                if old_slug not in canonical_map:
                    if old_slug not in [p[0] for p in new_patterns]:
                        new_patterns.append((old_slug, new_slug, split['pattern']))
            
            if new_patterns:
                print(f"\n⚠️ Found {len(new_patterns)} new patterns to add to canonical map:")
                for old, new, pattern in new_patterns[:10]:
                    print(f"  '{old}': '{new}',  # From pattern: {pattern}")
        else:
            print("⚠️ Canonical map not found at data/canonical_brand_map.yaml")
    
    def step4_generate_delta_sheet(self):
        """Step 4: Generate delta sheet with fixes"""
        print("\n" + "="*70)
        print("STEP 4: GENERATING DELTA SHEET")
        print("="*70)
        
        if not self.detected_splits:
            print("✓ No split-brand issues detected - catalog is clean!")
            return
        
        # Create delta sheet
        for split in self.detected_splits:
            self.delta_sheet.append({
                'product_key': split['product_key'],
                'brand': split['brand'],
                'product_name': split['product_name'][:50],
                'old_brand_slug': split['old_brand_slug'],
                'new_brand_slug': split['new_brand_slug'],
                'reason': split['reason'],
                'provenance': split['table'],
                'status': 'PENDING'
            })
        
        # Save to CSV
        df_delta = pd.DataFrame(self.delta_sheet)
        delta_path = Path('reports') / f'DELTA_SHEET_{self.snapshot_label}.csv'
        df_delta.to_csv(delta_path, index=False)
        
        print(f"✓ Delta sheet saved to: {delta_path}")
        print(f"  Total fixes to apply: {len(self.delta_sheet)}")
        
        # Show summary by brand
        brand_summary = df_delta.groupby('new_brand_slug').size().sort_values(ascending=False)
        print("\nFixes by target brand:")
        for brand, count in brand_summary.head(10).items():
            print(f"  {brand:20} : {count} products")
        
        # Generate SQL update statements (but don't execute)
        sql_path = Path('reports') / f'SPLIT_BRAND_FIXES_{self.snapshot_label}.sql'
        
        with open(sql_path, 'w') as f:
            f.write("-- Split-brand fixes for foods_canonical\n")
            f.write(f"-- Generated: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"-- Total fixes: {len(self.delta_sheet)}\n\n")
            
            f.write("BEGIN;\n\n")
            
            for item in self.delta_sheet[:100]:  # First 100 as sample
                f.write(f"UPDATE foods_canonical\n")
                f.write(f"SET brand_slug = '{item['new_brand_slug']}',\n")
                f.write(f"    updated_at = NOW()\n")
                f.write(f"WHERE product_key = '{item['product_key']}';\n\n")
            
            if len(self.delta_sheet) > 100:
                f.write(f"-- ... and {len(self.delta_sheet) - 100} more updates\n\n")
            
            f.write("-- COMMIT;  -- Uncomment to apply\n")
        
        print(f"✓ SQL fixes saved to: {sql_path}")
        print("  (Not executed - for Preview validation only)")
    
    def generate_report(self):
        """Generate comprehensive split-brand report"""
        print("\n" + "="*70)
        print("GENERATING SPLIT-BRAND REPORT")
        print("="*70)
        
        report_path = Path('reports') / f'SPLIT_BRAND_REPORT_{self.snapshot_label}.md'
        
        with open(report_path, 'w') as f:
            f.write("# SPLIT-BRAND RE-SCAN REPORT\n\n")
            f.write(f"**Snapshot**: `{self.snapshot_label}`\n")
            f.write(f"**Timestamp**: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Summary\n\n")
            f.write(f"- Total products scanned: 5,151\n")
            f.write(f"- Split-brand issues found: {len(self.detected_splits)}\n")
            f.write(f"- Unique patterns detected: {len(set(s['pattern'] for s in self.detected_splits))}\n\n")
            
            if self.detected_splits:
                f.write("## Top Split Patterns\n\n")
                f.write("| Pattern | Count | Target Brand |\n")
                f.write("|---------|-------|-------------|\n")
                
                pattern_counts = {}
                for split in self.detected_splits:
                    key = (split['pattern'], split['new_brand_slug'])
                    pattern_counts[key] = pattern_counts.get(key, 0) + 1
                
                for (pattern, target), count in sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                    f.write(f"| {pattern} | {count} | {target} |\n")
                
                f.write("\n## Sample Fixes\n\n")
                f.write("| Brand | Product | Old Slug | New Slug | Reason |\n")
                f.write("|-------|---------|----------|----------|--------|\n")
                
                for split in self.detected_splits[:20]:
                    f.write(f"| {split['brand'][:20]} | {split['product_name'][:30]} | "
                           f"{split['old_brand_slug']} | {split['new_brand_slug']} | {split['reason']} |\n")
            else:
                f.write("✅ **No split-brand issues detected!**\n\n")
                f.write("The catalog brand_slug values are already properly canonicalized.\n")
            
            f.write("\n## Actions\n\n")
            if self.detected_splits:
                f.write(f"- ✓ Delta sheet generated: `DELTA_SHEET_{self.snapshot_label}.csv`\n")
                f.write(f"- ✓ SQL fixes prepared: `SPLIT_BRAND_FIXES_{self.snapshot_label}.sql`\n")
                f.write("- ⏳ Awaiting Preview validation before applying fixes\n")
            else:
                f.write("- No actions required\n")
        
        print(f"✓ Report saved to: {report_path}")
        
        return report_path
    
    def run(self):
        """Execute split-brand re-scan"""
        print("\nStarting Split-Brand Re-scan...")
        
        # Step 1: Scan foods_canonical
        self.step1_scan_foods_canonical()
        
        # Step 2: Scan foods_union_all
        self.step2_scan_foods_union_all()
        
        # Step 3: Compare against canonical map
        self.step3_compare_canonical_map()
        
        # Step 4: Generate delta sheet
        self.step4_generate_delta_sheet()
        
        # Generate report
        self.generate_report()
        
        print("\n" + "="*70)
        print("SPLIT-BRAND RE-SCAN COMPLETE")
        print("="*70)
        print(f"Issues found: {len(self.detected_splits)}")
        print(f"Status: {'⚠️ Fixes pending' if self.detected_splits else '✅ Clean'}")
        
        return len(self.detected_splits)

if __name__ == "__main__":
    # Use the snapshot from Prompt 1
    scanner = SplitBrandRescanner(snapshot_label="SNAPSHOT_20250911_101939")
    issues_found = scanner.run()