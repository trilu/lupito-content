#!/usr/bin/env python3
"""
Validate brand normalization and run QA checks
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import re
from collections import Counter

class BrandNormalizationValidator:
    def __init__(self):
        self.normalized_tables = [
            "reports/MANUF/foods_published_v2.csv",
            "reports/02_foods_published_sample.csv", 
            "reports/MANUF/harvests/barking_harvest_20250910_190449.csv",
            "reports/MANUF/harvests/arden_harvest_20250910_190449.csv"
        ]
        
        self.validation_results = {
            'orphan_fragments': [],
            'split_patterns': [],
            'incomplete_slugs': [],
            'duplicate_keys': [],
            'canonical_brands': set()
        }
    
    def check_orphan_fragments(self, df):
        """Check for orphaned brand fragments in product names"""
        orphan_patterns = [
            ('Canin', 'royal_canin'),
            ('Science Plan', 'hills'),
            ('Prescription Diet', 'hills'),
            ('Pro Plan', 'purina'),
            ('ONE', 'purina'),
            ('Beta', 'purina'),
            ('Grange', 'arden_grange'),
            ('Heads', 'barking_heads'),
            ('Kitchen', 'lilys_kitchen'),
            ('Core', 'wellness'),
            ('Freedom', 'wild_freedom')
        ]
        
        issues = []
        for _, row in df.iterrows():
            product_name = str(row.get('product_name', '')).strip()
            brand_slug = str(row.get('brand_slug', '')).strip()
            
            for fragment, expected_slug in orphan_patterns:
                # Check if product name starts with fragment
                if re.match(f'^{re.escape(fragment)}\\s', product_name):
                    # Special case: "Canine" is not "Canin"
                    if fragment == 'Canin' and product_name.startswith('Canine '):
                        continue
                    
                    if brand_slug != expected_slug:
                        issues.append({
                            'brand': row.get('brand'),
                            'brand_slug': brand_slug,
                            'product_name': product_name,
                            'fragment': fragment,
                            'expected_slug': expected_slug
                        })
        
        return issues
    
    def check_split_patterns(self, df):
        """Check for split brand patterns"""
        split_checks = [
            ('Royal', '^Canin\\s'),
            ('Arden', '^Grange\\s'),
            ('Barking', '^Heads\\s'),
            ('Hills', '^Science Plan\\s'),
            ('Hills', '^Prescription Diet\\s'),
            ('Purina', '^Pro Plan\\s'),
            ('Purina', '^ONE\\s'),
            ('Taste', '^of the Wild\\s'),
            ('Wild', '^Freedom\\s'),
            ("Lily's", '^Kitchen\\s')
        ]
        
        issues = []
        for _, row in df.iterrows():
            brand = str(row.get('brand', '')).strip()
            product_name = str(row.get('product_name', '')).strip()
            
            for brand_fragment, name_pattern in split_checks:
                if brand == brand_fragment and re.match(name_pattern, product_name):
                    issues.append({
                        'brand': brand,
                        'product_name': product_name,
                        'pattern': f"{brand_fragment}|{name_pattern}"
                    })
        
        return issues
    
    def check_incomplete_slugs(self, df):
        """Check for incomplete brand slugs"""
        incomplete_slugs = [
            'royal',  # Should be 'royal_canin'
            'arden',  # Should be 'arden_grange'
            'barking',  # Should be 'barking_heads'
            'taste',  # Should be 'taste_of_the_wild'
            'lilys',  # Should be 'lilys_kitchen'
            'natures'  # Should be 'natures_variety'
        ]
        
        issues = []
        if 'brand_slug' in df.columns:
            for _, row in df.iterrows():
                slug = str(row.get('brand_slug', '')).strip()
                if slug in incomplete_slugs:
                    issues.append({
                        'brand': row.get('brand'),
                        'brand_slug': slug,
                        'product_name': row.get('product_name')
                    })
        
        return issues
    
    def check_duplicate_keys(self, df):
        """Check for duplicate product keys"""
        if 'product_key' not in df.columns:
            return []
        
        key_counts = df['product_key'].value_counts()
        duplicates = key_counts[key_counts > 1]
        
        duplicate_info = []
        for key, count in duplicates.items():
            duplicate_rows = df[df['product_key'] == key]
            duplicate_info.append({
                'product_key': key,
                'count': count,
                'brands': duplicate_rows['brand'].unique().tolist(),
                'product_names': duplicate_rows['product_name'].head(2).tolist()
            })
        
        return duplicate_info
    
    def validate_table(self, file_path):
        """Validate a single table"""
        path = Path(file_path)
        if not path.exists():
            return None
        
        df = pd.read_csv(path)
        
        validation = {
            'table': path.name,
            'total_rows': len(df),
            'orphan_fragments': self.check_orphan_fragments(df),
            'split_patterns': self.check_split_patterns(df),
            'incomplete_slugs': self.check_incomplete_slugs(df),
            'duplicate_keys': self.check_duplicate_keys(df)
        }
        
        # Collect canonical brands
        if 'brand' in df.columns:
            self.validation_results['canonical_brands'].update(
                df['brand'].dropna().unique()
            )
        
        return validation
    
    def run_validation(self):
        """Run validation on all normalized tables"""
        print("="*60)
        print("BRAND NORMALIZATION VALIDATION")
        print("="*60)
        
        all_results = []
        total_issues = 0
        
        for table_path in self.normalized_tables:
            print(f"\nValidating: {Path(table_path).name}")
            result = self.validate_table(table_path)
            
            if result:
                all_results.append(result)
                
                # Count issues
                orphans = len(result['orphan_fragments'])
                splits = len(result['split_patterns'])
                incomplete = len(result['incomplete_slugs'])
                duplicates = len(result['duplicate_keys'])
                
                table_issues = orphans + splits + incomplete
                total_issues += table_issues
                
                print(f"  Orphan fragments: {orphans}")
                print(f"  Split patterns: {splits}")
                print(f"  Incomplete slugs: {incomplete}")
                print(f"  Duplicate keys: {duplicates}")
                
                if table_issues == 0:
                    print(f"  ✅ PASS - No brand issues found")
                else:
                    print(f"  ❌ FAIL - {table_issues} issues found")
        
        return all_results, total_issues
    
    def generate_validation_report(self, results, total_issues):
        """Generate detailed validation report"""
        report = f"""# BRAND NORMALIZATION VALIDATION REPORT

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## OVERALL STATUS: {"✅ PASS" if total_issues == 0 else f"❌ FAIL ({total_issues} issues)"}

## Summary by Table

| Table | Orphans | Splits | Incomplete | Status |
|-------|---------|--------|------------|--------|
"""
        
        for result in results:
            orphans = len(result['orphan_fragments'])
            splits = len(result['split_patterns'])
            incomplete = len(result['incomplete_slugs'])
            issues = orphans + splits + incomplete
            
            status = "✅ PASS" if issues == 0 else f"❌ {issues} issues"
            report += f"| {result['table']} | {orphans} | {splits} | {incomplete} | {status} |\n"
        
        # QA Guards Status
        report += f"""

## QA Guards Status

1. **No orphan fragments**: {"✅ PASS" if all(len(r['orphan_fragments']) == 0 for r in results) else "❌ FAIL"}
2. **No split patterns**: {"✅ PASS" if all(len(r['split_patterns']) == 0 for r in results) else "❌ FAIL"}
3. **No incomplete slugs**: {"✅ PASS" if all(len(r['incomplete_slugs']) == 0 for r in results) else "❌ FAIL"}

## Canonical Brands Found

Total unique brands: {len(self.validation_results['canonical_brands'])}

| Brand |
|-------|
"""
        
        for brand in sorted(self.validation_results['canonical_brands'])[:20]:
            report += f"| {brand} |\n"
        
        # Specific brand checks
        report += """

## Specific Brand Validation

### Arden Grange
"""
        arden_found = 'Arden Grange' in self.validation_results['canonical_brands']
        arden_split = any('Arden' in str(i.get('brand', '')) for r in results for i in r['split_patterns'])
        report += f"- Unified as 'Arden Grange': {'✅ YES' if arden_found else '❌ NO'}\n"
        report += f"- No 'Arden|Grange' splits: {'✅ PASS' if not arden_split else '❌ FAIL'}\n"
        
        report += """
### Barking Heads
"""
        barking_found = 'Barking Heads' in self.validation_results['canonical_brands']
        barking_split = any('Barking' in str(i.get('brand', '')) for r in results for i in r['split_patterns'])
        report += f"- Unified as 'Barking Heads': {'✅ YES' if barking_found else '❌ NO'}\n"
        report += f"- No 'Barking|Heads' splits: {'✅ PASS' if not barking_split else '❌ FAIL'}\n"
        
        # Duplicate keys analysis
        all_duplicates = []
        for result in results:
            all_duplicates.extend(result['duplicate_keys'])
        
        if all_duplicates:
            report += f"""

## Duplicate Product Keys

Found {len(all_duplicates)} product keys with duplicates:

| Product Key | Count | Brands |
|-------------|-------|--------|
"""
            for dup in all_duplicates[:10]:
                key_preview = dup['product_key'][:50] + '...' if len(dup['product_key']) > 50 else dup['product_key']
                brands = ', '.join(dup['brands'])
                report += f"| {key_preview} | {dup['count']} | {brands} |\n"
        
        # Conclusion
        if total_issues == 0:
            report += """

## ✅ VALIDATION PASSED

All brand normalization checks passed successfully:
- No orphaned brand fragments in product names
- No split brand patterns detected
- All brand slugs are complete and canonical
- Brand unification completed successfully
"""
        else:
            report += f"""

## ❌ VALIDATION FAILED

Found {total_issues} issues that need attention:
- Review the issues listed above
- Run normalization again if needed
- Check for edge cases in the normalization logic
"""
        
        return report

def main():
    validator = BrandNormalizationValidator()
    
    # Run validation
    results, total_issues = validator.run_validation()
    
    # Generate report
    report = validator.generate_validation_report(results, total_issues)
    
    # Save report
    report_path = Path("reports/BRAND_NORMALIZATION_VALIDATION.md")
    with open(report_path, 'w') as f:
        f.write(report)
    
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    print(f"Total issues found: {total_issues}")
    print(f"Report saved to: {report_path}")
    
    if total_issues == 0:
        print("\n✅ ALL VALIDATION CHECKS PASSED")
        return 0
    else:
        print(f"\n❌ VALIDATION FAILED WITH {total_issues} ISSUES")
        return 1

if __name__ == "__main__":
    exit(main())