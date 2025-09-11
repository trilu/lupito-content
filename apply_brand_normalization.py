#!/usr/bin/env python3
"""
Apply brand normalization rules (with dry-run mode)
Fixes split brands and normalizes product names
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import re
import hashlib

class BrandNormalizer:
    def __init__(self, dry_run=True):
        self.dry_run = dry_run
        self.data_dir = Path("data")
        self.harvest_dir = Path("reports/MANUF/PILOT/harvests")
        self.output_dir = Path("reports/MANUF/NORMALIZED") if not dry_run else Path("reports/MANUF/DRY_RUN")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load brand phrase map
        self.brand_map = self.load_brand_map()
        
        # Track changes
        self.changes = []
        self.merges = []
        
    def load_brand_map(self):
        """Load brand phrase map"""
        map_file = self.data_dir / "brand_phrase_map.csv"
        if map_file.exists():
            return pd.read_csv(map_file)
        return pd.DataFrame()
    
    def load_all_data(self):
        """Load all harvest data"""
        all_data = []
        
        for csv_file in self.harvest_dir.glob("*_pilot_*.csv"):
            df = pd.read_csv(csv_file)
            all_data.append(df)
        
        if all_data:
            return pd.concat(all_data, ignore_index=True)
        
        # Create test data with split brands if no real data
        return self.create_test_data()
    
    def create_test_data(self):
        """Create test data with split brand examples"""
        test_data = [
            # Royal Canin splits
            {'product_id': 'test_001', 'brand': 'Royal', 'brand_slug': 'royal', 
             'product_name': 'Canin Mini Adult', 'form': 'dry'},
            {'product_id': 'test_002', 'brand': 'Royal', 'brand_slug': 'royal',
             'product_name': 'Canin Maxi Puppy', 'form': 'dry'},
            
            # Hill's splits
            {'product_id': 'test_003', 'brand': 'Hills', 'brand_slug': 'hills',
             'product_name': 'Science Plan Adult Large Breed', 'form': 'dry'},
            {'product_id': 'test_004', 'brand': "Hill's", 'brand_slug': 'hills',
             'product_name': 'Prescription Diet c/d Urinary', 'form': 'wet'},
            
            # Purina splits
            {'product_id': 'test_005', 'brand': 'Purina', 'brand_slug': 'purina',
             'product_name': 'Pro Plan Adult Chicken', 'form': 'dry'},
            {'product_id': 'test_006', 'brand': 'Purina', 'brand_slug': 'purina',
             'product_name': 'ONE Senior 7+', 'form': 'dry'},
            
            # Orphaned fragments
            {'product_id': 'test_007', 'brand': 'Unknown', 'brand_slug': 'unknown',
             'product_name': 'Canin Special Formula', 'form': 'dry'},
            {'product_id': 'test_008', 'brand': 'Generic', 'brand_slug': 'generic',
             'product_name': 'Science Plan Sensitive Stomach', 'form': 'wet'},
            
            # Normal products (no fix needed)
            {'product_id': 'test_009', 'brand': 'Acana', 'brand_slug': 'acana',
             'product_name': 'Heritage Puppy Small Breed', 'form': 'dry'},
            {'product_id': 'test_010', 'brand': 'Orijen', 'brand_slug': 'orijen',
             'product_name': 'Original Adult', 'form': 'dry'},
        ]
        
        df = pd.DataFrame(test_data)
        
        # Add required fields
        df['ingredients'] = 'Chicken, rice, vegetables'
        df['life_stage'] = 'adult'
        df['price'] = 25.99
        
        return df
    
    def normalize_brand(self, row):
        """Normalize a single brand/product_name pair"""
        brand = str(row.get('brand', '')).strip()
        product_name = str(row.get('product_name', '')).strip()
        
        if not brand or not product_name:
            return row
        
        # Check brand map for matches
        for _, mapping in self.brand_map.iterrows():
            source_brand = mapping['source_brand']
            prefix = mapping['prefix_from_name']
            
            # Check if this mapping applies
            applies = False
            
            if source_brand == '*':
                # Orphan fragment - check if product_name starts with prefix
                if product_name.startswith(prefix + ' '):
                    applies = True
            elif brand.lower() == source_brand.lower():
                # Check if product_name starts with expected prefix
                if product_name.lower().startswith(prefix.lower()):
                    applies = True
            
            if applies:
                # Apply normalization
                change = {
                    'product_id': row.get('product_id'),
                    'old_brand': brand,
                    'old_product_name': product_name,
                    'new_brand': mapping['canonical_brand'],
                    'new_brand_slug': mapping['brand_slug'],
                    'brand_line': mapping['brand_line'],
                    'confidence': mapping['confidence']
                }
                
                # Clean product_name
                strip_regex = mapping['strip_prefix_regex']
                new_product_name = re.sub(strip_regex, '', product_name, flags=re.IGNORECASE).strip()
                
                # Guard against over-stripping
                if new_product_name and len(new_product_name) > 5:
                    change['new_product_name'] = new_product_name
                else:
                    # Don't strip if it would leave too little
                    change['new_product_name'] = product_name
                
                # Update row
                row = row.copy()
                row['brand'] = change['new_brand']
                row['brand_slug'] = change['new_brand_slug']
                row['product_name'] = change['new_product_name']
                
                if change['brand_line']:
                    row['brand_line'] = change['brand_line']
                
                # Track change
                self.changes.append(change)
                
                # Only apply first matching rule
                break
        
        return row
    
    def rebuild_product_key(self, row):
        """Rebuild product_key with canonical brand_slug"""
        brand_slug = str(row.get('brand_slug', 'unknown')).lower().replace(' ', '_')
        
        # Create name_slug from product_name
        product_name = str(row.get('product_name', ''))
        name_slug = re.sub(r'[^a-z0-9]+', '_', product_name.lower()).strip('_')
        
        # Get form or default
        form = str(row.get('form', 'unknown')).lower()
        
        # Build key
        product_key = f"{brand_slug}|{name_slug}|{form}"
        
        row['product_key'] = product_key
        row['name_slug'] = name_slug
        
        return row
    
    def detect_duplicates(self, df):
        """Detect duplicates after key rebuild"""
        key_counts = df['product_key'].value_counts()
        duplicates = key_counts[key_counts > 1]
        
        merge_candidates = []
        
        for key, count in duplicates.items():
            dupes = df[df['product_key'] == key]
            
            merge_candidates.append({
                'product_key': key,
                'count': count,
                'product_ids': list(dupes['product_id']),
                'brands': list(dupes['brand'].unique()),
                'names': list(dupes['product_name'].unique())[:2]  # Sample
            })
        
        return merge_candidates
    
    def apply_normalization(self, df):
        """Apply normalization to entire dataframe"""
        print(f"\n{'DRY RUN' if self.dry_run else 'APPLYING'} NORMALIZATION")
        print("-" * 40)
        
        # Store original for comparison
        df['original_brand'] = df['brand']
        df['original_product_name'] = df['product_name']
        
        # Apply normalization to each row
        normalized_rows = []
        for idx, row in df.iterrows():
            normalized = self.normalize_brand(row)
            normalized = self.rebuild_product_key(normalized)
            normalized_rows.append(normalized)
        
        df_normalized = pd.DataFrame(normalized_rows)
        
        # Detect duplicates
        self.merges = self.detect_duplicates(df_normalized)
        
        # If not dry run, deduplicate
        if not self.dry_run and self.merges:
            print(f"Deduplicating {len(self.merges)} product key groups...")
            df_normalized = df_normalized.drop_duplicates(subset=['product_key'], keep='first')
        
        return df_normalized
    
    def generate_qa_report(self, df_before, df_after):
        """Generate QA report"""
        
        report = f"""# BRAND NORMALIZATION {'DRY RUN' if self.dry_run else 'EXECUTION'} REPORT

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Mode: {'DRY RUN - No data modified' if self.dry_run else 'APPLIED - Data normalized'}

## 📊 SUMMARY

### Before
- Total products: {len(df_before)}
- Unique brands: {df_before['brand'].nunique()}
- Unique brand_slugs: {df_before['brand_slug'].nunique() if 'brand_slug' in df_before else 'N/A'}

### After
- Total products: {len(df_after)}
- Unique brands: {df_after['brand'].nunique()}
- Unique brand_slugs: {df_after['brand_slug'].nunique()}
- Products changed: {len(self.changes)}
- Duplicate keys found: {len(self.merges)}

## 🔧 CHANGES APPLIED

Total changes: {len(self.changes)}

"""
        
        if self.changes:
            # Group changes by confidence
            confidence_groups = {}
            for change in self.changes:
                conf = change['confidence']
                if conf not in confidence_groups:
                    confidence_groups[conf] = []
                confidence_groups[conf].append(change)
            
            for confidence, group in sorted(confidence_groups.items()):
                report += f"""### {confidence.upper()} Confidence ({len(group)} changes)

| Product | Old Brand | New Brand | Old Name | New Name |
|---------|-----------|-----------|----------|----------|
"""
                
                for change in group[:5]:  # Show first 5
                    old_name = change['old_product_name'][:30] + '...' if len(change['old_product_name']) > 30 else change['old_product_name']
                    new_name = change['new_product_name'][:30] + '...' if len(change['new_product_name']) > 30 else change['new_product_name']
                    
                    report += f"| {change['product_id']} | {change['old_brand']} | "
                    report += f"**{change['new_brand']}** | {old_name} | {new_name} |\n"
                
                if len(group) > 5:
                    report += f"\n*... and {len(group)-5} more*\n"
                
                report += "\n"
        
        # Duplicate detection
        if self.merges:
            report += f"""## 🔄 DUPLICATE KEYS DETECTED

Found {len(self.merges)} product keys with duplicates after normalization:

| Product Key | Count | Product IDs | Brands |
|-------------|-------|-------------|--------|
"""
            
            for merge in self.merges[:5]:
                key_short = merge['product_key'][:40] + '...' if len(merge['product_key']) > 40 else merge['product_key']
                report += f"| {key_short} | {merge['count']} | "
                report += f"{', '.join(merge['product_ids'][:2])} | "
                report += f"{', '.join(merge['brands'])} |\n"
        
        # Quality checks
        report += """## ✅ QUALITY CHECKS

### Guard Conditions
"""
        
        # Check for remaining split fragments
        fragments = ['Canin ', 'Science Plan ', 'Pro Plan ', 'Prescription Diet ']
        for fragment in fragments:
            count = len(df_after[df_after['product_name'].str.startswith(fragment)])
            status = '✅ PASS' if count == 0 else f'❌ FAIL ({count} found)'
            report += f"- No products starting with '{fragment}': {status}\n"
        
        # Check canonical brands
        canonical_brands = ['royal_canin', 'hills', 'purina']
        for brand_slug in canonical_brands:
            count = len(df_after[df_after['brand_slug'] == brand_slug])
            if count > 0:
                report += f"- {brand_slug}: {count} products consolidated ✅\n"
        
        report += f"""

## 📝 NEXT STEPS

"""
        
        if self.dry_run:
            report += """1. Review changes above
2. Check for false positives
3. Run with dry_run=False to apply changes
4. Refresh materialized views
"""
        else:
            report += """1. Changes have been applied
2. Refresh materialized views
3. Update allowlist if needed
4. Run validation queries
"""
        
        return report
    
    def save_results(self, df_normalized, report):
        """Save normalized data and report"""
        
        if self.dry_run:
            # Save dry run results
            output_file = self.output_dir / "dry_run_normalized.csv"
            report_file = self.output_dir / "DRY_RUN_REPORT.md"
        else:
            # Save actual normalized data
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = self.output_dir / f"normalized_{timestamp}.csv"
            report_file = self.output_dir / "NORMALIZATION_REPORT.md"
        
        df_normalized.to_csv(output_file, index=False)
        
        with open(report_file, 'w') as f:
            f.write(report)
        
        return output_file, report_file

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Apply brand normalization')
    parser.add_argument('--apply', action='store_true', help='Actually apply changes (default is dry-run)')
    args = parser.parse_args()
    
    dry_run = not args.apply
    
    normalizer = BrandNormalizer(dry_run=dry_run)
    
    print("="*60)
    print(f"BRAND NORMALIZATION {'DRY RUN' if dry_run else 'EXECUTION'}")
    print("="*60)
    
    # Load data
    df_before = normalizer.load_all_data()
    print(f"Loaded {len(df_before)} products")
    
    # Apply normalization
    df_after = normalizer.apply_normalization(df_before)
    
    print(f"\nChanges identified: {len(normalizer.changes)}")
    print(f"Duplicate keys found: {len(normalizer.merges)}")
    
    # Generate QA report
    report = normalizer.generate_qa_report(df_before, df_after)
    
    # Save results
    data_file, report_file = normalizer.save_results(df_after, report)
    
    print(f"\n✅ Results saved:")
    print(f"  Data: {data_file}")
    print(f"  Report: {report_file}")
    
    if dry_run:
        print("\n⚠️  This was a DRY RUN - no data was modified")
        print("   Run with --apply to actually apply changes")
    else:
        print("\n✅ Normalization applied successfully")
    
    print("="*60)

if __name__ == "__main__":
    main()