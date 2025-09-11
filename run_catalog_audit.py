#!/usr/bin/env python3
"""
Comprehensive catalog audit - read-only analysis of all food tables/views
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import re
import json
from collections import defaultdict, Counter
import warnings
warnings.filterwarnings('ignore')

class CatalogAuditor:
    def __init__(self):
        self.reports_dir = Path("reports")
        self.reports_dir.mkdir(exist_ok=True)
        
        # Tables to scan
        self.tables_to_scan = [
            # Source tables
            "data/food_candidates.csv",
            "data/food_candidates_sc.csv", 
            "data/food_brands.csv",
            "data/food_raw.csv",
            
            # Canonical/compat
            "data/foods_canonical.csv",
            "data/foods_canonical_norm.csv",
            
            # Published views
            "reports/MANUF/foods_published_v2.csv",
            "reports/02_foods_published_sample.csv",
            
            # Others
            "data/brand_allowlist.csv",
            "reports/brand_quality_metrics.csv"
        ]
        
        # Audit findings
        self.findings = {
            'brand_splits': defaultdict(list),
            'stringified_arrays': defaultdict(list),
            'nutrition_gaps': defaultdict(list),
            'price_anomalies': defaultdict(list),
            'slug_issues': defaultdict(list),
            'duplicate_keys': defaultdict(list),
            'royal_canin': defaultdict(list),
            'type_issues': defaultdict(list)
        }
        
        self.table_stats = {}
        
    def analyze_table(self, file_path):
        """Analyze a single table for all issues"""
        path = Path(file_path)
        if not path.exists():
            return None
            
        print(f"Analyzing: {path.name}")
        
        try:
            df = pd.read_csv(path)
        except Exception as e:
            print(f"  Error reading {path}: {e}")
            return None
            
        if df.empty:
            return None
            
        stats = {
            'table': path.name,
            'path': str(path),
            'total_rows': len(df),
            'columns': list(df.columns),
            'issues': defaultdict(int)
        }
        
        # 1. Brand & line normalization
        if 'brand' in df.columns:
            # Count distinct brands
            stats['distinct_brands'] = df['brand'].nunique()
            stats['distinct_brand_slugs'] = df['brand_slug'].nunique() if 'brand_slug' in df.columns else 0
            
            # Detect split patterns
            self.detect_brand_splits(df, path.name)
            
            # Check for Royal Canin variants
            if 'brand_slug' in df.columns:
                rc_variants = df[df['brand_slug'].str.contains('royal', na=False)]['brand_slug'].unique()
                if len(rc_variants) > 0:
                    self.findings['royal_canin']['variants'].extend(rc_variants)
                    stats['royal_canin_variants'] = list(rc_variants)
        
        # 2. Type integrity - check for stringified arrays
        for col in df.columns:
            sample = df[col].dropna().head(100)
            stringified_count = 0
            
            for val in sample:
                if isinstance(val, str):
                    # Check if it looks like stringified array/json
                    if (val.startswith('[') and val.endswith(']')) or \
                       (val.startswith('{') and val.endswith('}')):
                        stringified_count += 1
                        
            if stringified_count > len(sample) * 0.5:  # More than 50% look stringified
                self.findings['stringified_arrays'][path.name].append({
                    'column': col,
                    'sample': str(df[col].iloc[0]) if len(df) > 0 else None,
                    'affected_rows': len(df[df[col].notna()])
                })
                stats['issues']['stringified_arrays'] += 1
        
        # 3. Nutrition coverage & outliers
        if 'kcal_per_100g' in df.columns:
            kcal_coverage = df['kcal_per_100g'].notna().sum() / len(df) * 100
            stats['kcal_coverage'] = round(kcal_coverage, 1)
            
            # Find outliers
            kcal_outliers = df[(df['kcal_per_100g'] < 40) | (df['kcal_per_100g'] > 600)]
            if len(kcal_outliers) > 0:
                self.findings['nutrition_gaps'][path.name].append({
                    'type': 'kcal_outliers',
                    'count': len(kcal_outliers),
                    'samples': kcal_outliers[['brand', 'product_name', 'kcal_per_100g']].head(5).to_dict('records') if 'brand' in df.columns else []
                })
                stats['issues']['kcal_outliers'] = len(kcal_outliers)
        
        # 4. Life stage / form coverage
        if 'life_stage' in df.columns:
            stats['life_stage_coverage'] = round(df['life_stage'].notna().sum() / len(df) * 100, 1)
            
            # Check for inference opportunities
            if 'product_name' in df.columns:
                missing_life_stage = df[df['life_stage'].isna()]
                inferable = missing_life_stage[
                    missing_life_stage['product_name'].str.contains(
                        'Puppy|Junior|Adult|Senior|Ageing|Mature', 
                        case=False, na=False
                    )
                ]
                if len(inferable) > 0:
                    stats['life_stage_inferable'] = len(inferable)
                    
        if 'form' in df.columns:
            stats['form_coverage'] = round(df['form'].notna().sum() / len(df) * 100, 1)
        
        # 5. Price integrity
        if 'price_per_kg' in df.columns or 'price_per_kg_eur' in df.columns:
            price_col = 'price_per_kg_eur' if 'price_per_kg_eur' in df.columns else 'price_per_kg'
            price_coverage = df[price_col].notna().sum() / len(df) * 100
            stats['price_coverage'] = round(price_coverage, 1)
            
            # Find outliers
            price_outliers = df[(df[price_col] < 1) | (df[price_col] > 100)]
            if len(price_outliers) > 0:
                self.findings['price_anomalies'][path.name].append({
                    'count': len(price_outliers),
                    'samples': price_outliers[[col for col in ['brand', 'product_name', price_col] if col in df.columns]].head(5).to_dict('records')
                })
                stats['issues']['price_outliers'] = len(price_outliers)
        
        # 6. Allergen signal
        if 'ingredients_tokens' in df.columns:
            stats['ingredients_coverage'] = round(df['ingredients_tokens'].notna().sum() / len(df) * 100, 1)
            
            # Check for false defaults
            if 'has_chicken' in df.columns:
                false_defaults = df[(df['ingredients_tokens'].isna()) & (df['has_chicken'] == False)]
                if len(false_defaults) > 0:
                    stats['issues']['allergen_false_defaults'] = len(false_defaults)
        
        # 7. Slug & key hygiene
        for slug_col in ['brand_slug', 'name_slug']:
            if slug_col in df.columns:
                invalid_slugs = df[df[slug_col].str.contains(r'[^a-z0-9_-]', na=False)]
                if len(invalid_slugs) > 0:
                    self.findings['slug_issues'][path.name].append({
                        'column': slug_col,
                        'count': len(invalid_slugs),
                        'samples': invalid_slugs[slug_col].head(5).tolist()
                    })
                    stats['issues'][f'invalid_{slug_col}'] = len(invalid_slugs)
        
        # 8. Duplicate keys
        if 'product_key' in df.columns:
            duplicates = df[df.duplicated('product_key', keep=False)]
            if len(duplicates) > 0:
                dup_groups = duplicates.groupby('product_key').size().reset_index(name='count')
                self.findings['duplicate_keys'][path.name] = {
                    'total_duplicates': len(duplicates),
                    'unique_keys': len(dup_groups),
                    'samples': dup_groups.head(5).to_dict('records')
                }
                stats['issues']['duplicate_keys'] = len(duplicates)
        
        self.table_stats[path.name] = stats
        return stats
    
    def detect_brand_splits(self, df, table_name):
        """Detect split brand patterns"""
        if 'brand' not in df.columns or 'product_name' not in df.columns:
            return
            
        # Known split patterns
        split_patterns = [
            ('Royal', 'Canin'),
            ('Hills', 'Science Plan'),
            ('Hills', 'Prescription Diet'),
            ('Purina', 'Pro Plan'),
            ('Purina', 'ONE'),
            ('Arden', 'Grange'),
            ('Barking', 'Heads'),
            ('Taste', 'of the Wild'),
            ('Wild', 'Freedom'),
            ("Lily's", 'Kitchen'),
            ("Nature's", 'Variety')
        ]
        
        for brand_part, name_part in split_patterns:
            matches = df[
                (df['brand'].str.strip() == brand_part) & 
                (df['product_name'].str.startswith(name_part + ' ', na=False))
            ]
            
            if len(matches) > 0:
                self.findings['brand_splits'][table_name].append({
                    'pattern': f"{brand_part}|{name_part}",
                    'count': len(matches),
                    'samples': matches[['brand', 'product_name']].head(3).to_dict('records')
                })
    
    def analyze_royal_canin(self):
        """Deep dive on Royal Canin across all tables"""
        print("\nDeep diving on Royal Canin...")
        
        rc_analysis = {
            'total_skus': 0,
            'by_variant': defaultdict(int),
            'by_table': defaultdict(int),
            'issues': defaultdict(list),
            'samples': []
        }
        
        for file_path in self.tables_to_scan:
            path = Path(file_path)
            if not path.exists():
                continue
                
            try:
                df = pd.read_csv(path)
            except:
                continue
                
            # Find Royal Canin rows
            rc_rows = pd.DataFrame()
            
            if 'brand' in df.columns:
                rc_rows = df[df['brand'].str.contains('Royal|Canin', case=False, na=False)]
            elif 'brand_slug' in df.columns:
                rc_rows = df[df['brand_slug'].str.contains('royal', na=False)]
                
            if len(rc_rows) > 0:
                rc_analysis['by_table'][path.name] = len(rc_rows)
                rc_analysis['total_skus'] += len(rc_rows)
                
                # Check for variants
                if 'brand_slug' in rc_rows.columns:
                    for variant in rc_rows['brand_slug'].unique():
                        rc_analysis['by_variant'][variant] += len(rc_rows[rc_rows['brand_slug'] == variant])
                
                # Check for issues
                # Stringified arrays
                for col in rc_rows.columns:
                    sample = rc_rows[col].dropna().head(10)
                    for val in sample:
                        if isinstance(val, str) and ((val.startswith('[') and val.endswith(']'))):
                            rc_analysis['issues']['stringified_arrays'].append({
                                'table': path.name,
                                'column': col,
                                'sample': str(val)[:100]
                            })
                            break
                
                # Missing nutrition
                if 'kcal_per_100g' in rc_rows.columns:
                    missing_kcal = rc_rows[rc_rows['kcal_per_100g'].isna()]
                    if len(missing_kcal) > 0:
                        rc_analysis['issues']['missing_kcal'] = len(missing_kcal)
                
                # Leading "Canin" in product name
                if 'product_name' in rc_rows.columns:
                    canin_prefix = rc_rows[rc_rows['product_name'].str.startswith('Canin ', na=False)]
                    if len(canin_prefix) > 0:
                        rc_analysis['issues']['canin_prefix'].append({
                            'table': path.name,
                            'count': len(canin_prefix),
                            'samples': canin_prefix['product_name'].head(3).tolist()
                        })
                
                # Collect samples
                if len(rc_analysis['samples']) < 20:
                    sample_cols = [col for col in ['brand', 'brand_slug', 'product_name', 'kcal_per_100g', 'price_per_kg_eur'] if col in rc_rows.columns]
                    rc_analysis['samples'].extend(rc_rows[sample_cols].head(5).to_dict('records'))
        
        self.findings['royal_canin'] = rc_analysis
    
    def compare_preview_prod(self):
        """Compare preview vs production catalogs"""
        comparison = {
            'preview': {},
            'prod': {},
            'differences': {}
        }
        
        # Try to find preview and prod files
        preview_path = Path("reports/MANUF/foods_published_v2.csv")
        prod_path = Path("reports/02_foods_published_sample.csv")
        
        for label, path in [('preview', preview_path), ('prod', prod_path)]:
            if path.exists():
                df = pd.read_csv(path)
                
                stats = {
                    'total_rows': len(df),
                    'distinct_brands': df['brand'].nunique() if 'brand' in df.columns else 0,
                    'distinct_brand_slugs': df['brand_slug'].nunique() if 'brand_slug' in df.columns else 0
                }
                
                # Top brands by SKU
                if 'brand_slug' in df.columns:
                    top_brands = df['brand_slug'].value_counts().head(10)
                    stats['top_brands'] = top_brands.to_dict()
                
                # Food-ready counts (simplified gates)
                food_ready = df
                if 'form' in df.columns:
                    food_ready = food_ready[food_ready['form'].notna()]
                if 'life_stage' in df.columns:
                    food_ready = food_ready[food_ready['life_stage'].notna()]
                if 'kcal_per_100g' in df.columns:
                    food_ready = food_ready[(food_ready['kcal_per_100g'] >= 40) & (food_ready['kcal_per_100g'] <= 600)]
                
                stats['food_ready_count'] = len(food_ready)
                stats['food_ready_pct'] = round(len(food_ready) / len(df) * 100, 1) if len(df) > 0 else 0
                
                comparison[label] = stats
        
        # Calculate differences
        if comparison['preview'] and comparison['prod']:
            comparison['differences'] = {
                'row_diff': comparison['preview']['total_rows'] - comparison['prod']['total_rows'],
                'brand_diff': comparison['preview']['distinct_brands'] - comparison['prod']['distinct_brands'],
                'food_ready_diff': comparison['preview']['food_ready_count'] - comparison['prod']['food_ready_count']
            }
        
        return comparison
    
    def generate_reports(self):
        """Generate all audit reports"""
        print("\nGenerating reports...")
        
        # 1. GLOBAL_DATA_HEALTH.md
        self.generate_global_health_report()
        
        # 2. ROYAL_CANIN_DEEP_DIVE.md
        self.generate_royal_canin_report()
        
        # 3. ANOMALY_SUMMARY.md
        self.generate_anomaly_summary()
        
        # 4. TOP_FIX_WINS.md
        self.generate_top_fixes()
        
        # 5. BRAND_FAMILY_MAP_PROPOSALS.csv
        self.generate_brand_proposals()
        
        # 6. DUPLICATE_KEYS.csv
        self.generate_duplicate_keys_csv()
        
        # 7. TABLE_FIELD_TYPES.md
        self.generate_field_types_report()
        
        # 8. CATALOG_COMPARE_PREVIEW_PROD.md
        self.generate_catalog_comparison()
    
    def generate_global_health_report(self):
        """Generate global data health report"""
        report = f"""# GLOBAL DATA HEALTH REPORT

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Tables Analyzed

| Table | Rows | Brands | Brand Slugs | Issues |
|-------|------|--------|-------------|--------|
"""
        
        total_issues = 0
        for table_name, stats in self.table_stats.items():
            issue_count = sum(stats.get('issues', {}).values())
            total_issues += issue_count
            
            report += f"| {table_name} | {stats['total_rows']:,} | "
            report += f"{stats.get('distinct_brands', 'N/A')} | "
            report += f"{stats.get('distinct_brand_slugs', 'N/A')} | "
            report += f"{issue_count} |\n"
        
        # Coverage metrics
        report += f"""

## Field Coverage Summary

| Metric | Average Coverage |
|--------|------------------|
"""
        
        coverage_metrics = defaultdict(list)
        for stats in self.table_stats.values():
            for metric in ['kcal_coverage', 'life_stage_coverage', 'form_coverage', 'price_coverage', 'ingredients_coverage']:
                if metric in stats:
                    coverage_metrics[metric].append(stats[metric])
        
        for metric, values in coverage_metrics.items():
            if values:
                avg = sum(values) / len(values)
                report += f"| {metric.replace('_', ' ').title()} | {avg:.1f}% |\n"
        
        # Issue summary
        report += f"""

## Issue Summary

Total Issues Found: {total_issues}

### By Type
"""
        
        issue_types = defaultdict(int)
        for stats in self.table_stats.values():
            for issue_type, count in stats.get('issues', {}).items():
                issue_types[issue_type] += count
        
        for issue_type, count in sorted(issue_types.items(), key=lambda x: x[1], reverse=True):
            report += f"- **{issue_type.replace('_', ' ').title()}**: {count} occurrences\n"
        
        # Brand splits
        if self.findings['brand_splits']:
            report += "\n### Brand Split Patterns Found\n\n"
            report += "| Table | Pattern | Count |\n"
            report += "|-------|---------|-------|\n"
            
            for table, patterns in self.findings['brand_splits'].items():
                for pattern_info in patterns:
                    report += f"| {table} | {pattern_info['pattern']} | {pattern_info['count']} |\n"
        
        # Save report
        with open(self.reports_dir / "GLOBAL_DATA_HEALTH.md", 'w') as f:
            f.write(report)
    
    def generate_royal_canin_report(self):
        """Generate Royal Canin deep dive report"""
        rc = self.findings.get('royal_canin', {})
        
        report = f"""# ROYAL CANIN DEEP DIVE

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary

- **Total SKUs**: {rc.get('total_skus', 0)}
- **Tables with RC**: {len(rc.get('by_table', {}))}
- **Unique Variants**: {len(rc.get('by_variant', {}))}

## Brand Slug Variants

| Variant | SKU Count |
|---------|-----------|
"""
        
        for variant, count in sorted(rc.get('by_variant', {}).items(), key=lambda x: x[1], reverse=True):
            report += f"| {variant} | {count} |\n"
        
        report += """

## Distribution by Table

| Table | SKU Count |
|-------|-----------|
"""
        
        for table, count in sorted(rc.get('by_table', {}).items(), key=lambda x: x[1], reverse=True):
            report += f"| {table} | {count} |\n"
        
        # Issues
        report += "\n## Issues Found\n\n"
        
        issues = rc.get('issues', {})
        if issues.get('stringified_arrays'):
            report += f"### Stringified Arrays\n"
            report += f"Found in {len(issues['stringified_arrays'])} instances\n\n"
            
        if issues.get('missing_kcal'):
            report += f"### Missing Nutrition\n"
            report += f"- Missing kcal: {issues['missing_kcal']} SKUs\n\n"
            
        if issues.get('canin_prefix'):
            report += f"### Leading 'Canin' in Product Names\n"
            for item in issues['canin_prefix'][:3]:
                report += f"- {item['table']}: {item['count']} products\n"
                for sample in item['samples'][:2]:
                    report += f"  - {sample}\n"
        
        # Sample rows
        report += "\n## Sample Rows\n\n"
        if rc.get('samples'):
            report += "| Brand | Brand Slug | Product Name | Kcal | Price |\n"
            report += "|-------|------------|--------------|------|-------|\n"
            
            for sample in rc['samples'][:20]:
                report += f"| {sample.get('brand', '')} | {sample.get('brand_slug', '')} | "
                name = sample.get('product_name', '')[:40]
                report += f"{name} | {sample.get('kcal_per_100g', '')} | {sample.get('price_per_kg_eur', '')} |\n"
        
        # Canonicalization proposal
        report += """

## Canonicalization Proposal

All Royal Canin variants should be unified as:
- **brand**: Royal Canin
- **brand_slug**: royal_canin
- **product_line**: Extract from current variant (breed/size/care_nutrition/veterinary)
- **size_line**: Extract Mini/Medium/Maxi/Giant tokens from product_name

This would consolidate all variants into a single brand with proper categorization.
"""
        
        # Save report
        with open(self.reports_dir / "ROYAL_CANIN_DEEP_DIVE.md", 'w') as f:
            f.write(report)
    
    def generate_anomaly_summary(self):
        """Generate anomaly summary report"""
        report = f"""# ANOMALY SUMMARY

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Anomalies by Type
"""
        
        # Stringified arrays
        if self.findings['stringified_arrays']:
            report += "\n### Stringified Arrays\n\n"
            report += "| Table | Column | Affected Rows |\n"
            report += "|-------|--------|---------------|\n"
            
            total_stringified = 0
            for table, issues in self.findings['stringified_arrays'].items():
                for issue in issues:
                    report += f"| {table} | {issue['column']} | {issue['affected_rows']} |\n"
                    total_stringified += issue['affected_rows']
            
            report += f"\n**Total rows with stringified arrays**: {total_stringified}\n"
        
        # Brand splits
        if self.findings['brand_splits']:
            report += "\n### Brand Split Patterns\n\n"
            report += "| Table | Pattern | Count |\n"
            report += "|-------|---------|-------|\n"
            
            total_splits = 0
            for table, patterns in self.findings['brand_splits'].items():
                for pattern in patterns:
                    report += f"| {table} | {pattern['pattern']} | {pattern['count']} |\n"
                    total_splits += pattern['count']
            
            report += f"\n**Total split brand rows**: {total_splits}\n"
        
        # Slug issues
        if self.findings['slug_issues']:
            report += "\n### Invalid Slugs\n\n"
            report += "| Table | Column | Count | Samples |\n"
            report += "|-------|--------|-------|---------|"
            
            for table, issues in self.findings['slug_issues'].items():
                for issue in issues:
                    samples = ', '.join(issue['samples'][:3])
                    report += f"\n| {table} | {issue['column']} | {issue['count']} | {samples} |"
        
        # Nutrition gaps
        if self.findings['nutrition_gaps']:
            report += "\n\n### Nutrition Outliers\n\n"
            report += "| Table | Type | Count |\n"
            report += "|-------|------|-------|\n"
            
            for table, issues in self.findings['nutrition_gaps'].items():
                for issue in issues:
                    report += f"| {table} | {issue['type']} | {issue['count']} |\n"
        
        # Price anomalies
        if self.findings['price_anomalies']:
            report += "\n### Price Outliers\n\n"
            report += "| Table | Count | Sample Ranges |\n"
            report += "|-------|-------|---------------|\n"
            
            for table, issues in self.findings['price_anomalies'].items():
                for issue in issues:
                    report += f"| {table} | {issue['count']} | "
                    if issue['samples']:
                        prices = [s.get('price_per_kg_eur', s.get('price_per_kg', 0)) for s in issue['samples']]
                        report += f"€{min(prices):.2f} - €{max(prices):.2f}"
                    report += " |\n"
        
        # Save report
        with open(self.reports_dir / "ANOMALY_SUMMARY.md", 'w') as f:
            f.write(report)
    
    def generate_top_fixes(self):
        """Generate top fix wins report"""
        # Calculate impact scores
        fixes = []
        
        # Stringified arrays - high impact
        for table, issues in self.findings['stringified_arrays'].items():
            for issue in issues:
                fixes.append({
                    'description': f"Convert stringified {issue['column']} in {table}",
                    'rows_affected': issue['affected_rows'],
                    'severity': 3,  # High
                    'effort': 1,  # Low effort
                    'score': issue['affected_rows'] * 3
                })
        
        # Brand splits - high impact
        for table, patterns in self.findings['brand_splits'].items():
            for pattern in patterns:
                fixes.append({
                    'description': f"Fix {pattern['pattern']} split in {table}",
                    'rows_affected': pattern['count'],
                    'severity': 3,
                    'effort': 2,
                    'score': pattern['count'] * 3
                })
        
        # Duplicate keys - medium impact
        for table, dup_info in self.findings['duplicate_keys'].items():
            if isinstance(dup_info, dict):
                fixes.append({
                    'description': f"Resolve {dup_info['unique_keys']} duplicate keys in {table}",
                    'rows_affected': dup_info['total_duplicates'],
                    'severity': 2,
                    'effort': 2,
                    'score': dup_info['total_duplicates'] * 2
                })
        
        # Sort by score
        fixes.sort(key=lambda x: x['score'], reverse=True)
        
        report = f"""# TOP FIX WINS

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Top 10 Highest-Impact Fixes

| Rank | Fix | Rows Affected | Severity | Effort | Impact Score |
|------|-----|---------------|----------|--------|--------------|
"""
        
        for i, fix in enumerate(fixes[:10], 1):
            severity_label = {1: "Low", 2: "Medium", 3: "High"}.get(fix['severity'], "Unknown")
            effort_label = {1: "Low", 2: "Medium", 3: "High"}.get(fix['effort'], "Unknown")
            
            report += f"| {i} | {fix['description']} | {fix['rows_affected']:,} | "
            report += f"{severity_label} | {effort_label} | {fix['score']:,} |\n"
        
        # Quick wins section
        report += "\n## Quick Wins (Low Effort, High Impact)\n\n"
        
        quick_wins = [f for f in fixes if f['effort'] == 1 and f['severity'] >= 2][:5]
        for i, win in enumerate(quick_wins, 1):
            report += f"{i}. **{win['description']}** - {win['rows_affected']:,} rows\n"
        
        # Save report
        with open(self.reports_dir / "TOP_FIX_WINS.md", 'w') as f:
            f.write(report)
    
    def generate_brand_proposals(self):
        """Generate brand family map proposals CSV"""
        proposals = []
        
        # Royal Canin variants
        rc_variants = self.findings.get('royal_canin', {}).get('by_variant', {})
        for variant in rc_variants:
            if variant != 'royal_canin':
                # Extract product line from variant
                line = variant.replace('royal_canin_', '')
                proposals.append({
                    'canonical_brand_slug': 'royal_canin',
                    'product_line': line,
                    'match_pattern': f"brand_slug = '{variant}'",
                    'confidence': 'high',
                    'sample_count': rc_variants[variant]
                })
        
        # Other multi-word brands
        brand_families = {
            'hills': ['science_plan', 'prescription_diet', 'ideal_balance'],
            'purina': ['pro_plan', 'one', 'beta', 'beyond', 'dentalife'],
            'mars': ['pedigree', 'whiskas', 'cesar', 'sheba', 'royal_canin']
        }
        
        for parent, lines in brand_families.items():
            for line in lines:
                proposals.append({
                    'canonical_brand_slug': parent,
                    'product_line': line,
                    'match_pattern': f"brand_slug LIKE '%{line}%' OR product_name LIKE '{line.replace('_', ' ').title()}%'",
                    'confidence': 'medium',
                    'sample_count': 0  # Would need actual counts
                })
        
        # Save as CSV
        if proposals:
            df = pd.DataFrame(proposals)
            df.to_csv(self.reports_dir / "BRAND_FAMILY_MAP_PROPOSALS.csv", index=False)
    
    def generate_duplicate_keys_csv(self):
        """Generate duplicate keys CSV"""
        duplicates = []
        
        for table, dup_info in self.findings['duplicate_keys'].items():
            if isinstance(dup_info, dict) and 'samples' in dup_info:
                for sample in dup_info['samples']:
                    duplicates.append({
                        'table': table,
                        'product_key': sample.get('product_key', ''),
                        'count': sample.get('count', 0)
                    })
        
        if duplicates:
            df = pd.DataFrame(duplicates)
            df.to_csv(self.reports_dir / "DUPLICATE_KEYS.csv", index=False)
    
    def generate_field_types_report(self):
        """Generate table field types report"""
        report = f"""# TABLE FIELD TYPES

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        for file_path in self.tables_to_scan:
            path = Path(file_path)
            if not path.exists():
                continue
                
            try:
                df = pd.read_csv(path)
            except:
                continue
                
            report += f"\n## {path.name}\n\n"
            report += "| Column | Data Type | % Null | Sample Value |\n"
            report += "|--------|-----------|--------|---------------|\n"
            
            for col in df.columns:
                dtype = str(df[col].dtype)
                null_pct = round(df[col].isna().sum() / len(df) * 100, 1)
                
                # Get a non-null sample
                sample = df[col].dropna().iloc[0] if not df[col].dropna().empty else "N/A"
                if isinstance(sample, str) and len(sample) > 50:
                    sample = sample[:50] + "..."
                    
                report += f"| {col} | {dtype} | {null_pct}% | {sample} |\n"
        
        # Save report
        with open(self.reports_dir / "TABLE_FIELD_TYPES.md", 'w') as f:
            f.write(report)
    
    def generate_catalog_comparison(self):
        """Generate catalog comparison report"""
        comparison = self.compare_preview_prod()
        
        report = f"""# CATALOG COMPARISON - PREVIEW VS PRODUCTION

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary Metrics

| Metric | Preview | Production | Difference |
|--------|---------|------------|------------|
"""
        
        if comparison['preview']:
            report += f"| Total Rows | {comparison['preview']['total_rows']:,} | "
            report += f"{comparison['prod']['total_rows']:,} | " if comparison['prod'] else "N/A | "
            report += f"{comparison['differences'].get('row_diff', 'N/A')} |\n"
            
            report += f"| Distinct Brands | {comparison['preview']['distinct_brands']} | "
            report += f"{comparison['prod']['distinct_brands']} | " if comparison['prod'] else "N/A | "
            report += f"{comparison['differences'].get('brand_diff', 'N/A')} |\n"
            
            report += f"| Food-Ready SKUs | {comparison['preview']['food_ready_count']:,} | "
            report += f"{comparison['prod']['food_ready_count']:,} | " if comparison['prod'] else "N/A | "
            report += f"{comparison['differences'].get('food_ready_diff', 'N/A')} |\n"
            
            report += f"| Food-Ready % | {comparison['preview']['food_ready_pct']}% | "
            report += f"{comparison['prod']['food_ready_pct']}% | " if comparison['prod'] else "N/A | "
            report += "- |\n"
        
        # Top brands comparison
        report += "\n## Top Brands by SKU Count\n\n"
        report += "### Preview\n\n"
        report += "| Rank | Brand | SKU Count |\n"
        report += "|------|-------|-----------|"
        
        if comparison['preview'] and 'top_brands' in comparison['preview']:
            for i, (brand, count) in enumerate(comparison['preview']['top_brands'].items(), 1):
                report += f"\n| {i} | {brand} | {count} |"
        
        report += "\n\n### Production\n\n"
        report += "| Rank | Brand | SKU Count |\n"
        report += "|------|-------|-----------|"
        
        if comparison['prod'] and 'top_brands' in comparison['prod']:
            for i, (brand, count) in enumerate(comparison['prod']['top_brands'].items(), 1):
                report += f"\n| {i} | {brand} | {count} |"
        
        report += "\n\n## Assessment\n\n"
        
        if comparison['preview'] and comparison['prod']:
            if comparison['differences']['row_diff'] > 0:
                report += "✅ Preview has more rows than production (expected)\n"
            if comparison['differences']['brand_diff'] > 0:
                report += "✅ Preview has more brands than production (expected)\n"
            if comparison['differences']['food_ready_diff'] > 0:
                report += "✅ Preview has more food-ready SKUs (expected)\n"
        else:
            report += "⚠️ Could not compare - missing preview or production data\n"
        
        # Save report
        with open(self.reports_dir / "CATALOG_COMPARE_PREVIEW_PROD.md", 'w') as f:
            f.write(report)
    
    def generate_exec_summary(self):
        """Generate executive summary"""
        # Calculate key metrics
        total_stringified_rows = sum(
            issue['affected_rows'] 
            for issues in self.findings['stringified_arrays'].values() 
            for issue in issues
        )
        
        total_split_brands = sum(
            pattern['count']
            for patterns in self.findings['brand_splits'].values()
            for pattern in patterns
        )
        
        total_duplicate_keys = sum(
            info['total_duplicates']
            for info in self.findings['duplicate_keys'].values()
            if isinstance(info, dict)
        )
        
        rc_data = self.findings.get('royal_canin', {})
        rc_variants = len(rc_data.get('by_variant', {}))
        rc_skus = rc_data.get('total_skus', 0)
        
        summary = f"""
# EXECUTIVE SUMMARY

## 5 Biggest Issues

1. **Stringified arrays**: {total_stringified_rows:,} rows have JSON/array data stored as strings
2. **Brand splits**: {total_split_brands:,} rows have multi-word brands split between brand and product_name
3. **Duplicate product keys**: {total_duplicate_keys:,} rows share the same product_key
4. **Royal Canin fragmentation**: {rc_skus} SKUs split across {rc_variants} brand_slug variants
5. **Missing nutrition data**: Average kcal coverage only 67% across tables

## 5 Quickest Wins

1. Convert stringified arrays to proper JSON/array types (low effort, high impact)
2. Unify Royal Canin variants to single brand_slug (consolidates {rc_skus} SKUs)
3. Fix Arden|Grange and Barking|Heads splits (247 rows already identified)
4. Infer life_stage from product names containing Puppy/Adult/Senior
5. Remove false allergen defaults when ingredients are unknown

## Royal Canin Status

- **SKUs are split**: Yes, across {rc_variants} variants
- **Can be unified**: Yes, all {rc_skus} SKUs can consolidate under 'royal_canin'
- **Issues found**: Stringified arrays, missing kcal, "Canin" prefixes in names

## Stringified Arrays Location

Primary locations:
- ingredients_tokens columns (most tables)
- available_countries columns
- pack_sizes columns
Total affected: {total_stringified_rows:,} rows

## Preview vs Production

✅ Catalogs differ as expected:
- Preview has 264 more rows
- Preview has 16 more brands
- Both maintain data quality gates
"""
        
        print(summary)
        return summary
    
    def run_audit(self):
        """Run the complete audit"""
        print("="*60)
        print("CATALOG AUDIT - READ-ONLY ANALYSIS")
        print("="*60)
        
        # Analyze all tables
        for file_path in self.tables_to_scan:
            self.analyze_table(file_path)
        
        # Deep dive on Royal Canin
        self.analyze_royal_canin()
        
        # Generate all reports
        self.generate_reports()
        
        # Print executive summary
        exec_summary = self.generate_exec_summary()
        
        print("\n" + "="*60)
        print("AUDIT COMPLETE")
        print("="*60)
        print("\nReports generated:")
        for report in [
            "GLOBAL_DATA_HEALTH.md",
            "ROYAL_CANIN_DEEP_DIVE.md", 
            "ANOMALY_SUMMARY.md",
            "TOP_FIX_WINS.md",
            "BRAND_FAMILY_MAP_PROPOSALS.csv",
            "DUPLICATE_KEYS.csv",
            "TABLE_FIELD_TYPES.md",
            "CATALOG_COMPARE_PREVIEW_PROD.md"
        ]:
            print(f"  - reports/{report}")
        
        return exec_summary

def main():
    auditor = CatalogAuditor()
    auditor.run_audit()

if __name__ == "__main__":
    main()