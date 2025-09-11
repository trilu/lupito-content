#!/usr/bin/env python3
"""
Full catalog scan for split-brand cases across all source tables
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import re
from collections import defaultdict, Counter
import glob

class FullCatalogScanner:
    def __init__(self):
        self.output_dir = Path("reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Data directories to scan
        self.data_dirs = [
            Path("data"),
            Path("reports/MANUF/PILOT/harvests"),
            Path("reports/MANUF/PRODUCTION"),
            Path(".")
        ]
        
        # Known split patterns to look for
        self.split_patterns = [
            ('Royal', 'Canin'),
            ('Hills', 'Science Plan'),
            ("Hill's", 'Science Plan'),
            ('Hills', 'Prescription Diet'),
            ("Hill's", 'Prescription Diet'),
            ('Purina', 'Pro Plan'),
            ('Purina', 'ONE'),
            ('Purina', 'Beta'),
            ('Farmina', 'N&D'),
            ('Taste', 'of the Wild'),
            ("Nature's", 'Variety'),
            ('Concept', 'for Life'),
            ('Happy', 'Dog'),
            ('Arden', 'Grange'),
            ('Burns', 'Pet'),
            ('James', 'Wellbeloved'),
            ("Lily's", 'Kitchen'),
            ('Barking', 'Heads'),
            ('Wellness', 'Core'),
            ('Wild', 'Freedom')
        ]
        
        # Orphan fragments to check
        self.orphan_fragments = [
            'Canin', 'Science Plan', 'Prescription Diet', 
            'Pro Plan', 'ONE', 'Beta', 'N&D',
            'Grange', 'Kitchen', 'Heads', 'Core', 'Freedom'
        ]
        
        self.findings = defaultdict(list)
        self.table_summaries = {}
        
    def find_all_tables(self):
        """Find all relevant CSV files and tables"""
        tables_found = []
        
        # Patterns to look for
        patterns = [
            '*food*.csv',
            '*brand*.csv',
            '*product*.csv',
            '*catalog*.csv',
            '*harvest*.csv',
            '*_fixed_*.csv',
            '*_pilot_*.csv'
        ]
        
        for data_dir in self.data_dirs:
            if not data_dir.exists():
                continue
                
            for pattern in patterns:
                for file_path in data_dir.rglob(pattern):
                    # Skip certain files
                    skip_patterns = ['brand_phrase_map.csv', 'gaps.csv', 'metrics.csv']
                    if any(skip in str(file_path) for skip in skip_patterns):
                        continue
                    
                    tables_found.append(file_path)
        
        # Deduplicate
        tables_found = list(set(tables_found))
        
        return sorted(tables_found)
    
    def scan_table(self, file_path):
        """Scan a single table/CSV for split brands"""
        try:
            df = pd.read_csv(file_path)
            
            if df.empty or 'brand' not in df.columns:
                return None
            
            table_findings = {
                'file': str(file_path),
                'total_rows': len(df),
                'split_patterns': defaultdict(list),
                'orphan_fragments': defaultdict(list),
                'samples': []
            }
            
            # Check for brand column variations
            brand_col = 'brand' if 'brand' in df.columns else None
            name_col = 'product_name' if 'product_name' in df.columns else 'name' if 'name' in df.columns else None
            
            if not brand_col or not name_col:
                return None
            
            # Scan for split patterns
            for idx, row in df.iterrows():
                brand = str(row.get(brand_col, '')).strip()
                product_name = str(row.get(name_col, '')).strip()
                
                if not brand or not product_name:
                    continue
                
                # Check known split patterns
                for brand_part, name_part in self.split_patterns:
                    if brand.lower() == brand_part.lower():
                        if product_name.lower().startswith(name_part.lower()):
                            pattern_key = f"{brand_part}|{name_part}"
                            table_findings['split_patterns'][pattern_key].append({
                                'index': idx,
                                'brand': brand,
                                'product_name': product_name,
                                'product_id': row.get('product_id', f'row_{idx}')
                            })
                
                # Check orphan fragments
                for fragment in self.orphan_fragments:
                    if product_name.startswith(fragment + ' '):
                        # Avoid false positives like "Canine" vs "Canin"
                        if fragment == 'Canin' and 'Canine' in product_name:
                            continue
                        
                        table_findings['orphan_fragments'][fragment].append({
                            'index': idx,
                            'brand': brand,
                            'product_name': product_name,
                            'product_id': row.get('product_id', f'row_{idx}')
                        })
            
            # Calculate totals
            total_splits = sum(len(v) for v in table_findings['split_patterns'].values())
            total_orphans = sum(len(v) for v in table_findings['orphan_fragments'].values())
            
            if total_splits > 0 or total_orphans > 0:
                table_findings['total_splits'] = total_splits
                table_findings['total_orphans'] = total_orphans
                
                # Collect samples (up to 20 per pattern)
                for pattern, instances in table_findings['split_patterns'].items():
                    for inst in instances[:20]:
                        table_findings['samples'].append({
                            'pattern': pattern,
                            'type': 'split',
                            **inst
                        })
                
                for fragment, instances in table_findings['orphan_fragments'].items():
                    for inst in instances[:5]:  # Fewer orphan samples
                        table_findings['samples'].append({
                            'pattern': fragment,
                            'type': 'orphan',
                            **inst
                        })
                
                return table_findings
            
        except Exception as e:
            print(f"  Error scanning {file_path}: {e}")
        
        return None
    
    def scan_all_tables(self):
        """Scan all found tables"""
        tables = self.find_all_tables()
        
        print(f"Found {len(tables)} tables to scan")
        
        for table_path in tables:
            print(f"  Scanning: {table_path.name}...")
            findings = self.scan_table(table_path)
            
            if findings and (findings.get('total_splits', 0) > 0 or findings.get('total_orphans', 0) > 0):
                self.findings[str(table_path)] = findings
                
                # Summary for this table
                self.table_summaries[table_path.name] = {
                    'path': str(table_path),
                    'splits': findings.get('total_splits', 0),
                    'orphans': findings.get('total_orphans', 0),
                    'total_rows': findings['total_rows']
                }
        
        return self.findings
    
    def generate_report(self):
        """Generate comprehensive split brand candidates report"""
        
        report = f"""# BRAND SPLIT CANDIDATES - FULL CATALOG SCAN

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Tables Scanned: {len(self.table_summaries)}
Tables with Issues: {len(self.findings)}

## 📊 SUMMARY

### Tables with Split-Brand Issues

| Table | Total Rows | Split Patterns | Orphan Fragments | Impact |
|-------|------------|----------------|------------------|--------|
"""
        
        # Sort by impact (splits + orphans)
        sorted_tables = sorted(self.table_summaries.items(), 
                              key=lambda x: x[1]['splits'] + x[1]['orphans'], 
                              reverse=True)
        
        for table_name, summary in sorted_tables:
            total_issues = summary['splits'] + summary['orphans']
            impact = "🔴 HIGH" if total_issues > 50 else "🟡 MEDIUM" if total_issues > 10 else "🟢 LOW"
            
            report += f"| {table_name} | {summary['total_rows']} | "
            report += f"{summary['splits']} | {summary['orphans']} | {impact} |\n"
        
        # Pattern frequency across all tables
        all_patterns = Counter()
        all_orphans = Counter()
        
        for findings in self.findings.values():
            for pattern, instances in findings['split_patterns'].items():
                all_patterns[pattern] += len(instances)
            for fragment, instances in findings['orphan_fragments'].items():
                all_orphans[fragment] += len(instances)
        
        report += f"""

## 🔍 PATTERN ANALYSIS

### Most Common Split Patterns

| Pattern | Total Occurrences | Tables Affected |
|---------|-------------------|-----------------|
"""
        
        for pattern, count in all_patterns.most_common(10):
            tables_with = sum(1 for f in self.findings.values() if pattern in f['split_patterns'])
            report += f"| **{pattern}** | {count} | {tables_with} |\n"
        
        report += f"""

### Orphan Fragments Found

| Fragment | Total Occurrences | Likely Brand |
|----------|-------------------|--------------|
"""
        
        for fragment, count in all_orphans.most_common(10):
            likely_brand = self.guess_brand_for_fragment(fragment)
            report += f"| {fragment} | {count} | {likely_brand} |\n"
        
        # Detailed samples per pattern
        report += """

## 📋 SAMPLE ROWS (20 per pattern)

"""
        
        # Group samples by pattern
        pattern_samples = defaultdict(list)
        
        for table_path, findings in self.findings.items():
            table_name = Path(table_path).name
            for sample in findings['samples']:
                pattern_samples[sample['pattern']].append({
                    'table': table_name,
                    **sample
                })
        
        # Show top patterns with samples
        for pattern, samples in sorted(pattern_samples.items(), 
                                      key=lambda x: len(x[1]), 
                                      reverse=True)[:5]:
            
            report += f"""### Pattern: {pattern}
**Total instances**: {len(samples)}

| Table | Product ID | Current Brand | Product Name |
|-------|------------|---------------|--------------|
"""
            
            for sample in samples[:20]:
                name_preview = sample['product_name'][:40] + '...' if len(sample['product_name']) > 40 else sample['product_name']
                report += f"| {sample['table']} | {sample.get('product_id', 'N/A')} | "
                report += f"{sample['brand']} | {name_preview} |\n"
            
            report += "\n"
        
        # Specific brand analysis
        report += """## 🎯 SPECIFIC BRAND ANALYSIS

### Royal Canin
"""
        royal_count = all_patterns.get('Royal|Canin', 0)
        report += f"- Split instances found: {royal_count}\n"
        report += f"- Orphan 'Canin' fragments: {all_orphans.get('Canin', 0)}\n"
        
        report += """
### Hill's
"""
        hills_count = (all_patterns.get('Hills|Science Plan', 0) + 
                      all_patterns.get("Hill's|Science Plan", 0) +
                      all_patterns.get('Hills|Prescription Diet', 0) +
                      all_patterns.get("Hill's|Prescription Diet", 0))
        report += f"- Split instances found: {hills_count}\n"
        report += f"- Science Plan fragments: {all_orphans.get('Science Plan', 0)}\n"
        report += f"- Prescription Diet fragments: {all_orphans.get('Prescription Diet', 0)}\n"
        
        report += """
### Purina
"""
        purina_count = (all_patterns.get('Purina|Pro Plan', 0) + 
                       all_patterns.get('Purina|ONE', 0) +
                       all_patterns.get('Purina|Beta', 0))
        report += f"- Split instances found: {purina_count}\n"
        report += f"- Pro Plan fragments: {all_orphans.get('Pro Plan', 0)}\n"
        report += f"- ONE fragments: {all_orphans.get('ONE', 0)}\n"
        
        # Recommendations
        total_issues = sum(all_patterns.values()) + sum(all_orphans.values())
        
        report += f"""

## 🔧 RECOMMENDATIONS

### Priority Actions
1. **Total issues to fix**: {total_issues} rows across {len(self.findings)} tables
2. **High priority tables** (>50 issues):
"""
        
        for table_name, summary in sorted_tables:
            if summary['splits'] + summary['orphans'] > 50:
                report += f"   - {table_name}: {summary['splits'] + summary['orphans']} issues\n"
        
        report += """
3. **Apply normalization** to these tables first
4. **Set up guards** to prevent regression

### Next Steps
1. Take snapshots of affected tables
2. Run `apply_brand_normalization.py --apply` on affected tables
3. Rebuild product keys and run deduplication
4. Refresh materialized views
5. Run QA guards to verify fixes

---

**Note**: Word boundary checks will be applied to avoid false positives (e.g., "Canine" vs "Canin")
"""
        
        return report
    
    def guess_brand_for_fragment(self, fragment):
        """Guess the likely brand for an orphan fragment"""
        fragment_map = {
            'Canin': 'Royal Canin',
            'Science Plan': "Hill's",
            'Prescription Diet': "Hill's",
            'Pro Plan': 'Purina',
            'ONE': 'Purina',
            'Beta': 'Purina',
            'N&D': 'Farmina',
            'Grange': 'Arden Grange',
            'Kitchen': "Lily's Kitchen",
            'Heads': 'Barking Heads',
            'Core': 'Wellness',
            'Freedom': 'Wild Freedom'
        }
        return fragment_map.get(fragment, 'Unknown')

def main():
    scanner = FullCatalogScanner()
    
    print("="*60)
    print("FULL CATALOG SCAN FOR SPLIT BRANDS")
    print("="*60)
    
    # Scan all tables
    findings = scanner.scan_all_tables()
    
    print(f"\nFound issues in {len(findings)} tables")
    
    # Generate report
    report = scanner.generate_report()
    
    # Save report
    report_file = scanner.output_dir / "BRAND_SPLIT_CANDIDATES.md"
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"\n✅ Report saved to: {report_file}")
    
    # Print summary
    total_splits = sum(s.get('total_splits', 0) for s in scanner.findings.values())
    total_orphans = sum(s.get('total_orphans', 0) for s in scanner.findings.values())
    
    print("\n" + "="*60)
    print("SCAN SUMMARY")
    print("="*60)
    print(f"Tables scanned: {len(scanner.table_summaries)}")
    print(f"Tables with issues: {len(scanner.findings)}")
    print(f"Total split patterns: {total_splits}")
    print(f"Total orphan fragments: {total_orphans}")
    print(f"Total issues: {total_splits + total_orphans}")
    print("="*60)

if __name__ == "__main__":
    main()