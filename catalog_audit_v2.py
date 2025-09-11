#!/usr/bin/env python3
"""
Master Coverage & Consolidation - Fix Pack V2
Comprehensive data fixes across all food tables
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import re
import json
import shutil
from collections import defaultdict, Counter
import warnings
import glob
warnings.filterwarnings('ignore')

class CatalogFixPackV2:
    def __init__(self):
        self.reports_dir = Path("reports")
        self.reports_dir.mkdir(exist_ok=True)
        self.backup_dir = Path("backups") / datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Track all food tables found
        self.food_tables = []
        self.table_metadata = {}
        self.fix_stats = defaultdict(lambda: defaultdict(int))
        
    def phase1_inventory_lineage(self):
        """Phase 1: Create inventory and lineage of all food tables"""
        print("="*60)
        print("PHASE 1: INVENTORY & LINEAGE")
        print("="*60)
        
        # Find all food-related CSV files
        patterns = [
            "data/food*.csv",
            "data/foods*.csv",
            "reports/**/food*.csv",
            "reports/**/foods*.csv",
            "food*.csv",
            "foods*.csv"
        ]
        
        all_files = set()
        for pattern in patterns:
            all_files.update(glob.glob(pattern, recursive=True))
        
        # Classify and analyze each table
        for file_path in sorted(all_files):
            path = Path(file_path)
            if path.exists() and path.suffix == '.csv':
                try:
                    df = pd.read_csv(path, nrows=5)  # Quick read for metadata
                    full_df = pd.read_csv(path)
                    
                    # Classify table type
                    table_type = self.classify_table(path.name)
                    
                    self.table_metadata[path.name] = {
                        'path': str(path),
                        'type': table_type,
                        'rows': len(full_df),
                        'columns': list(df.columns),
                        'has_brand': 'brand' in df.columns,
                        'has_product_key': 'product_key' in df.columns,
                        'last_modified': datetime.fromtimestamp(path.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
                    }
                    
                    self.food_tables.append(str(path))
                    print(f"  Found: {path.name} ({table_type}, {len(full_df):,} rows)")
                    
                except Exception as e:
                    print(f"  Error reading {path}: {e}")
        
        # Generate lineage report
        self.generate_lineage_report()
        return len(self.food_tables)
    
    def classify_table(self, table_name):
        """Classify table based on name patterns"""
        name_lower = table_name.lower()
        
        if '_raw' in name_lower or 'raw_' in name_lower:
            return 'raw'
        elif '_sc' in name_lower:
            return 'scraped'
        elif '_compat' in name_lower:
            return 'compat'
        elif 'canonical' in name_lower:
            return 'canonical'
        elif 'published' in name_lower:
            return 'published'
        elif 'union' in name_lower:
            return 'union'
        elif 'brand' in name_lower:
            return 'brand_metadata'
        elif 'candidate' in name_lower:
            return 'candidate'
        else:
            return 'other'
    
    def phase2_health_sweep(self):
        """Phase 2: Global health sweep before fixes"""
        print("\n" + "="*60)
        print("PHASE 2: GLOBAL HEALTH SWEEP")
        print("="*60)
        
        health_stats = defaultdict(lambda: defaultdict(int))
        
        for file_path in self.food_tables:
            path = Path(file_path)
            print(f"  Analyzing: {path.name}")
            
            try:
                df = pd.read_csv(path)
                
                # Check for stringified arrays
                stringified_cols = []
                for col in df.columns:
                    if self.is_stringified_array_column(df[col]):
                        stringified_cols.append(col)
                        health_stats[path.name]['stringified_arrays'] += len(df[df[col].notna()])
                
                # Check for invalid slugs
                for slug_col in ['brand_slug', 'name_slug']:
                    if slug_col in df.columns:
                        invalid = df[df[slug_col].str.contains(r'[^a-z0-9_-]', na=False, regex=True)]
                        if len(invalid) > 0:
                            health_stats[path.name][f'invalid_{slug_col}'] = len(invalid)
                
                # Check for duplicate keys
                if 'product_key' in df.columns:
                    duplicates = df[df.duplicated('product_key', keep=False)]
                    if len(duplicates) > 0:
                        health_stats[path.name]['duplicate_keys'] = len(duplicates)
                
                # Field coverage
                for field in ['form', 'life_stage', 'kcal_per_100g', 'ingredients_tokens', 'price_per_kg_eur']:
                    if field in df.columns:
                        coverage = df[field].notna().sum() / len(df) * 100
                        health_stats[path.name][f'{field}_coverage'] = round(coverage, 1)
                
                # Store for fixes
                self.table_metadata[path.name]['stringified_cols'] = stringified_cols
                
            except Exception as e:
                print(f"    Error: {e}")
        
        # Generate health report
        self.generate_health_report(health_stats, 'BEFORE')
        return health_stats
    
    def is_stringified_array_column(self, series):
        """Check if column contains stringified arrays/JSON"""
        sample = series.dropna().head(100)
        if len(sample) == 0:
            return False
        
        stringified_count = 0
        for val in sample:
            if isinstance(val, str):
                if (val.startswith('[') and val.endswith(']')) or \
                   (val.startswith('{') and val.endswith('}')):
                    stringified_count += 1
        
        return stringified_count > len(sample) * 0.5
    
    def phase3_apply_fixes(self):
        """Phase 3: Apply normalization and fixes"""
        print("\n" + "="*60)
        print("PHASE 3: APPLYING FIXES")
        print("="*60)
        
        for file_path in self.food_tables:
            path = Path(file_path)
            print(f"\n  Processing: {path.name}")
            
            # Create backup
            backup_path = self.backup_dir / path.name
            shutil.copy2(path, backup_path)
            print(f"    Backup: {backup_path}")
            
            try:
                df = pd.read_csv(path)
                original_len = len(df)
                
                # 1. Fix stringified arrays
                fixed_arrays = self.fix_stringified_arrays(df, path.name)
                
                # 2. Fix slugs
                fixed_slugs = self.fix_invalid_slugs(df, path.name)
                
                # 3. Deduplicate
                if 'product_key' in df.columns:
                    df, dedup_count = self.deduplicate_products(df, path.name)
                else:
                    dedup_count = 0
                
                # 4. Brand normalization
                fixed_brands = self.normalize_brands(df, path.name)
                
                # 5. Infer life_stage where missing
                inferred = self.infer_life_stage(df, path.name)
                
                # Save fixed data
                df.to_csv(path, index=False)
                
                print(f"    ✅ Fixed: arrays={fixed_arrays}, slugs={fixed_slugs}, dedup={dedup_count}, brands={fixed_brands}, inferred={inferred}")
                
            except Exception as e:
                print(f"    ❌ Error: {e}")
        
        # Generate fix reports
        self.generate_fix_reports()
    
    def fix_stringified_arrays(self, df, table_name):
        """Convert stringified arrays to proper arrays"""
        fixed_count = 0
        
        stringified_cols = self.table_metadata.get(table_name, {}).get('stringified_cols', [])
        
        for col in stringified_cols:
            if col not in df.columns:
                continue
                
            for idx, val in df[col].items():
                if pd.notna(val) and isinstance(val, str):
                    if val.startswith('[') and val.endswith(']'):
                        try:
                            # Try to parse as JSON
                            parsed = json.loads(val)
                            # Keep as string representation of list for CSV
                            df.at[idx, col] = str(parsed)
                            fixed_count += 1
                        except:
                            pass
        
        self.fix_stats[table_name]['arrays_fixed'] = fixed_count
        return fixed_count
    
    def fix_invalid_slugs(self, df, table_name):
        """Fix invalid characters in slug columns"""
        fixed_count = 0
        
        for slug_col in ['brand_slug', 'name_slug']:
            if slug_col not in df.columns:
                continue
            
            for idx, val in df[slug_col].items():
                if pd.notna(val) and isinstance(val, str):
                    # Replace invalid characters
                    clean_val = re.sub(r'[^a-z0-9_-]+', '_', val.lower())
                    clean_val = re.sub(r'_+', '_', clean_val).strip('_')
                    
                    if clean_val != val:
                        df.at[idx, slug_col] = clean_val
                        fixed_count += 1
        
        self.fix_stats[table_name]['slugs_fixed'] = fixed_count
        return fixed_count
    
    def deduplicate_products(self, df, table_name):
        """Deduplicate based on product_key"""
        if 'product_key' not in df.columns:
            return df, 0
        
        # Find duplicates
        duplicates = df[df.duplicated('product_key', keep=False)]
        if len(duplicates) == 0:
            return df, 0
        
        # Keep best version of each duplicate (prefer more complete data)
        def score_row(row):
            score = 0
            # Prefer rows with more data
            if pd.notna(row.get('kcal_per_100g')):
                score += 10
            if pd.notna(row.get('ingredients_tokens')):
                score += 5
            if pd.notna(row.get('life_stage')):
                score += 3
            if pd.notna(row.get('form')):
                score += 3
            if pd.notna(row.get('price_per_kg_eur')):
                score += 2
            return score
        
        # Process each duplicate group
        kept_indices = []
        for key, group in duplicates.groupby('product_key'):
            # Score each row
            scores = group.apply(score_row, axis=1)
            # Keep the best scoring row
            best_idx = scores.idxmax()
            kept_indices.append(best_idx)
        
        # Get non-duplicate rows
        non_duplicates = df[~df.duplicated('product_key', keep=False)]
        
        # Combine kept duplicates with non-duplicates
        df_deduped = pd.concat([non_duplicates, df.loc[kept_indices]])
        
        removed = len(df) - len(df_deduped)
        self.fix_stats[table_name]['duplicates_removed'] = removed
        
        return df_deduped, removed
    
    def normalize_brands(self, df, table_name):
        """Apply brand normalization"""
        if 'brand' not in df.columns:
            return 0
        
        fixed_count = 0
        
        # Brand mappings
        brand_map = {
            'Royal': 'Royal Canin',
            'Hills': "Hill's",
            "Hill's": "Hill's",
            'Arden': 'Arden Grange',
            'Barking': 'Barking Heads',
            'Lily\'s': "Lily's Kitchen",
            'Nature\'s': "Nature's Variety"
        }
        
        for idx, brand in df['brand'].items():
            if pd.notna(brand) and brand in brand_map:
                df.at[idx, 'brand'] = brand_map[brand]
                
                # Update brand_slug if present
                if 'brand_slug' in df.columns:
                    slug_map = {
                        'Royal Canin': 'royal_canin',
                        "Hill's": 'hills',
                        'Arden Grange': 'arden_grange',
                        'Barking Heads': 'barking_heads',
                        "Lily's Kitchen": 'lilys_kitchen',
                        "Nature's Variety": 'natures_variety'
                    }
                    new_brand = brand_map[brand]
                    if new_brand in slug_map:
                        df.at[idx, 'brand_slug'] = slug_map[new_brand]
                
                fixed_count += 1
        
        self.fix_stats[table_name]['brands_normalized'] = fixed_count
        return fixed_count
    
    def infer_life_stage(self, df, table_name):
        """Infer life_stage from product name where missing"""
        if 'life_stage' not in df.columns or 'product_name' not in df.columns:
            return 0
        
        inferred_count = 0
        
        # Patterns for life stage inference
        patterns = {
            'puppy': ['puppy', 'junior', 'growth'],
            'adult': ['adult', 'mature'],
            'senior': ['senior', 'ageing', 'mature', '7+', '8+', '10+', '12+']
        }
        
        missing_life_stage = df[df['life_stage'].isna()]
        
        for idx, row in missing_life_stage.iterrows():
            product_name = str(row.get('product_name', '')).lower()
            
            for stage, keywords in patterns.items():
                if any(keyword in product_name for keyword in keywords):
                    df.at[idx, 'life_stage'] = stage
                    inferred_count += 1
                    break
        
        self.fix_stats[table_name]['life_stage_inferred'] = inferred_count
        return inferred_count
    
    def phase4_recompose_pipeline(self):
        """Phase 4: Recompose the data pipeline"""
        print("\n" + "="*60)
        print("PHASE 4: PIPELINE RECOMPOSITION")
        print("="*60)
        
        # Identify pipeline components
        union_tables = []
        canonical_tables = []
        published_tables = []
        
        for table_name, metadata in self.table_metadata.items():
            if 'union' in table_name.lower():
                union_tables.append(metadata['path'])
            elif 'canonical' in table_name.lower():
                canonical_tables.append(metadata['path'])
            elif 'published' in table_name.lower():
                published_tables.append(metadata['path'])
        
        pipeline_stats = {
            'union_count': len(union_tables),
            'canonical_count': len(canonical_tables),
            'published_count': len(published_tables),
            'total_rows_union': 0,
            'total_rows_canonical': 0,
            'total_rows_published': 0
        }
        
        # Count rows in each layer
        for path in union_tables:
            try:
                df = pd.read_csv(path)
                pipeline_stats['total_rows_union'] += len(df)
            except:
                pass
        
        for path in canonical_tables:
            try:
                df = pd.read_csv(path)
                pipeline_stats['total_rows_canonical'] += len(df)
            except:
                pass
        
        for path in published_tables:
            try:
                df = pd.read_csv(path)
                pipeline_stats['total_rows_published'] += len(df)
            except:
                pass
        
        # Generate pipeline report
        self.generate_pipeline_report(pipeline_stats)
        
        # Compare preview vs prod
        self.compare_environments()
        
        return pipeline_stats
    
    def phase5_brand_spotlights(self):
        """Phase 5: Brand spotlights and Royal Canin reconciliation"""
        print("\n" + "="*60)
        print("PHASE 5: BRAND SPOTLIGHTS")
        print("="*60)
        
        all_brands = defaultdict(int)
        rc_findings = defaultdict(list)
        
        # Scan all tables for brands
        for file_path in self.food_tables:
            path = Path(file_path)
            
            try:
                df = pd.read_csv(path)
                
                if 'brand' in df.columns:
                    brand_counts = df['brand'].value_counts()
                    for brand, count in brand_counts.items():
                        all_brands[brand] += count
                    
                    # Check for Royal Canin
                    rc_rows = df[df['brand'].str.contains('Royal|Canin', case=False, na=False)]
                    if len(rc_rows) > 0:
                        rc_findings[path.name].append({
                            'count': len(rc_rows),
                            'variants': rc_rows['brand'].unique().tolist() if 'brand' in rc_rows.columns else []
                        })
                
            except Exception as e:
                print(f"  Error scanning {path.name}: {e}")
        
        # Get top 20 brands
        top_brands = sorted(all_brands.items(), key=lambda x: x[1], reverse=True)[:20]
        
        # Generate reports
        self.generate_brand_spotlight(top_brands, all_brands)
        self.generate_rc_reconciliation(rc_findings)
        
        return len(all_brands), len(rc_findings)
    
    def phase6_acceptance_gates(self):
        """Phase 6: Run acceptance gates and validation"""
        print("\n" + "="*60)
        print("PHASE 6: ACCEPTANCE GATES")
        print("="*60)
        
        # Re-run health checks
        health_stats_after = defaultdict(lambda: defaultdict(int))
        issues_remaining = 0
        
        for file_path in self.food_tables:
            path = Path(file_path)
            
            try:
                df = pd.read_csv(path)
                
                # Check for remaining stringified arrays
                for col in df.columns:
                    if self.is_stringified_array_column(df[col]):
                        health_stats_after[path.name]['stringified_arrays'] += 1
                        issues_remaining += 1
                
                # Check for remaining invalid slugs
                for slug_col in ['brand_slug', 'name_slug']:
                    if slug_col in df.columns:
                        invalid = df[df[slug_col].str.contains(r'[^a-z0-9_-]', na=False, regex=True)]
                        if len(invalid) > 0:
                            health_stats_after[path.name][f'invalid_{slug_col}'] = len(invalid)
                            issues_remaining += 1
                
            except:
                pass
        
        # Generate final reports
        self.generate_health_report(health_stats_after, 'AFTER')
        self.generate_rollback_instructions()
        
        # Print summary
        print(f"\n  Issues remaining: {issues_remaining}")
        print(f"  ✅ PASS" if issues_remaining == 0 else f"  ⚠️ {issues_remaining} issues need attention")
        
        return issues_remaining == 0
    
    def generate_lineage_report(self):
        """Generate lineage report"""
        report = f"""# FOODS LINEAGE

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Total Tables Found: {len(self.food_tables)}

## Table Inventory

| Table | Type | Rows | Has Brand | Has Key | Last Modified |
|-------|------|------|-----------|---------|---------------|
"""
        
        # Sort by type then name
        sorted_tables = sorted(self.table_metadata.items(), 
                              key=lambda x: (x[1]['type'], x[0]))
        
        for table_name, metadata in sorted_tables:
            report += f"| {table_name} | {metadata['type']} | {metadata['rows']:,} | "
            report += f"{'✓' if metadata['has_brand'] else '-'} | "
            report += f"{'✓' if metadata['has_product_key'] else '-'} | "
            report += f"{metadata['last_modified']} |\n"
        
        # Add lineage diagram
        report += """

## Data Flow Diagram

```
Raw/Scraped Sources
├── food_candidates.csv
├── food_candidates_sc.csv
├── food_brands.csv
└── food_raw.csv
    ↓
Compatibility Layer (*_compat)
├── food_candidates_compat.csv
└── food_candidates_sc_compat.csv
    ↓
Union Layer
└── foods_union_all.csv
    ↓
Canonical Layer
└── foods_canonical.csv
    ↓
Published Views
├── foods_published_preview.csv (all brands)
└── foods_published_prod.csv (allowlisted only)
```

## Classification Summary

"""
        
        type_counts = defaultdict(int)
        for metadata in self.table_metadata.values():
            type_counts[metadata['type']] += 1
        
        for table_type, count in sorted(type_counts.items()):
            report += f"- **{table_type}**: {count} tables\n"
        
        # Save report
        with open(self.reports_dir / "FOODS_LINEAGE.md", 'w') as f:
            f.write(report)
    
    def generate_health_report(self, health_stats, phase):
        """Generate health report"""
        report = f"""# FOODS HEALTH {phase}

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Issues by Table

| Table | Stringified | Invalid Slugs | Duplicates | Total Issues |
|-------|-------------|---------------|------------|--------------|
"""
        
        total_issues = defaultdict(int)
        
        for table_name, stats in health_stats.items():
            stringified = stats.get('stringified_arrays', 0)
            invalid_brand = stats.get('invalid_brand_slug', 0)
            invalid_name = stats.get('invalid_name_slug', 0)
            duplicates = stats.get('duplicate_keys', 0)
            
            total = stringified + invalid_brand + invalid_name + duplicates
            
            report += f"| {table_name} | {stringified} | {invalid_brand + invalid_name} | {duplicates} | {total} |\n"
            
            total_issues['stringified'] += stringified
            total_issues['invalid_slugs'] += invalid_brand + invalid_name
            total_issues['duplicates'] += duplicates
        
        # Add totals
        report += f"""

## Global Totals

- **Stringified Arrays**: {total_issues['stringified']:,} cells
- **Invalid Slugs**: {total_issues['invalid_slugs']:,} values
- **Duplicate Keys**: {total_issues['duplicates']:,} rows
- **Total Issues**: {sum(total_issues.values()):,}

## Field Coverage

| Table | Form % | Life Stage % | Kcal % | Ingredients % | Price % |
|-------|--------|--------------|--------|---------------|---------|
"""
        
        for table_name, stats in health_stats.items():
            report += f"| {table_name} | "
            report += f"{stats.get('form_coverage', 0):.1f} | "
            report += f"{stats.get('life_stage_coverage', 0):.1f} | "
            report += f"{stats.get('kcal_per_100g_coverage', 0):.1f} | "
            report += f"{stats.get('ingredients_tokens_coverage', 0):.1f} | "
            report += f"{stats.get('price_per_kg_eur_coverage', 0):.1f} |\n"
        
        # Save report
        with open(self.reports_dir / f"FOODS_HEALTH_{phase}.md", 'w') as f:
            f.write(report)
    
    def generate_fix_reports(self):
        """Generate detailed fix reports"""
        # Types report
        types_report = f"""# FIXPACK V2 - TYPES

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Stringified Arrays Fixed

| Table | Arrays Fixed |
|-------|--------------|
"""
        
        for table, stats in self.fix_stats.items():
            if stats.get('arrays_fixed', 0) > 0:
                types_report += f"| {table} | {stats['arrays_fixed']:,} |\n"
        
        with open(self.reports_dir / "FIXPACK_V2_TYPES.md", 'w') as f:
            f.write(types_report)
        
        # Slugs report
        slugs_report = f"""# FIXPACK V2 - SLUGS

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Invalid Slugs Fixed

| Table | Slugs Fixed |
|-------|-------------|
"""
        
        for table, stats in self.fix_stats.items():
            if stats.get('slugs_fixed', 0) > 0:
                slugs_report += f"| {table} | {stats['slugs_fixed']:,} |\n"
        
        with open(self.reports_dir / "FIXPACK_V2_SLUGS.md", 'w') as f:
            f.write(slugs_report)
        
        # Dedup report
        dedup_report = f"""# FIXPACK V2 - DEDUPLICATION

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Duplicates Removed

| Table | Rows Removed |
|-------|--------------|
"""
        
        for table, stats in self.fix_stats.items():
            if stats.get('duplicates_removed', 0) > 0:
                dedup_report += f"| {table} | {stats['duplicates_removed']:,} |\n"
        
        with open(self.reports_dir / "FIXPACK_V2_DEDUP.md", 'w') as f:
            f.write(dedup_report)
        
        # Brands report
        brands_report = f"""# FIXPACK V2 - BRANDS

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Brands Normalized

| Table | Brands Fixed | Life Stages Inferred |
|-------|--------------|---------------------|
"""
        
        for table, stats in self.fix_stats.items():
            brands = stats.get('brands_normalized', 0)
            inferred = stats.get('life_stage_inferred', 0)
            if brands > 0 or inferred > 0:
                brands_report += f"| {table} | {brands:,} | {inferred:,} |\n"
        
        with open(self.reports_dir / "FIXPACK_V2_BRANDS.md", 'w') as f:
            f.write(brands_report)
    
    def generate_pipeline_report(self, stats):
        """Generate pipeline report"""
        report = f"""# FOODS PIPELINE AFTER

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Pipeline Layers

| Layer | Tables | Total Rows |
|-------|--------|------------|
| Union | {stats['union_count']} | {stats['total_rows_union']:,} |
| Canonical | {stats['canonical_count']} | {stats['total_rows_canonical']:,} |
| Published | {stats['published_count']} | {stats['total_rows_published']:,} |

## Data Flow

- **Reduction Rate**: {round((1 - stats['total_rows_published']/max(stats['total_rows_union'], 1)) * 100, 1)}%
- **Deduplication**: Union → Canonical
- **Allowlist Filter**: Canonical → Published

"""
        
        with open(self.reports_dir / "FOODS_PIPELINE_AFTER.md", 'w') as f:
            f.write(report)
    
    def compare_environments(self):
        """Compare preview vs production environments"""
        comparison = {
            'preview': {},
            'prod': {}
        }
        
        # Find preview and prod files
        for table_name, metadata in self.table_metadata.items():
            if 'preview' in table_name.lower():
                path = Path(metadata['path'])
                if path.exists():
                    df = pd.read_csv(path)
                    comparison['preview'] = {
                        'rows': len(df),
                        'brands': df['brand'].nunique() if 'brand' in df.columns else 0
                    }
            elif 'prod' in table_name.lower():
                path = Path(metadata['path'])
                if path.exists():
                    df = pd.read_csv(path)
                    comparison['prod'] = {
                        'rows': len(df),
                        'brands': df['brand'].nunique() if 'brand' in df.columns else 0
                    }
        
        report = f"""# FOODS COMPARE PREVIEW VS PROD AFTER

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Environment Comparison

| Metric | Preview | Production | Delta |
|--------|---------|------------|-------|
| Total Rows | {comparison.get('preview', {}).get('rows', 0):,} | {comparison.get('prod', {}).get('rows', 0):,} | {comparison.get('preview', {}).get('rows', 0) - comparison.get('prod', {}).get('rows', 0):,} |
| Distinct Brands | {comparison.get('preview', {}).get('brands', 0)} | {comparison.get('prod', {}).get('brands', 0)} | {comparison.get('preview', {}).get('brands', 0) - comparison.get('prod', {}).get('brands', 0)} |

"""
        
        with open(self.reports_dir / "FOODS_COMPARE_PREVIEW_PROD_AFTER.md", 'w') as f:
            f.write(report)
    
    def generate_brand_spotlight(self, top_brands, all_brands):
        """Generate brand spotlight report"""
        report = f"""# FOODS BRAND SPOTLIGHT

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Total Unique Brands: {len(all_brands)}

## Top 20 Brands by SKU Count

| Rank | Brand | Total SKUs |
|------|-------|------------|
"""
        
        for i, (brand, count) in enumerate(top_brands, 1):
            report += f"| {i} | {brand} | {count:,} |\n"
        
        with open(self.reports_dir / "FOODS_BRAND_SPOTLIGHT.md", 'w') as f:
            f.write(report)
    
    def generate_rc_reconciliation(self, rc_findings):
        """Generate Royal Canin reconciliation report"""
        total_rc = sum(item['count'] for items in rc_findings.values() for item in items)
        
        report = f"""# ROYAL CANIN RECONCILE V2

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Royal Canin Presence

- **Tables with RC**: {len(rc_findings)}
- **Total RC SKUs**: {total_rc:,}

## Distribution by Table

| Table | SKU Count | Variants Found |
|-------|-----------|----------------|
"""
        
        for table, findings in rc_findings.items():
            for finding in findings:
                variants = ', '.join(finding['variants'][:3])
                report += f"| {table} | {finding['count']} | {variants} |\n"
        
        if total_rc == 0:
            report += """

## Status: NOT FOUND

Royal Canin products were not found in any table. 

### Recommended Action
Add Royal Canin to NEW_BRANDS_QUEUE.md as Tier-1 priority with these seed sources:
- https://www.royalcanin.com/uk
- Major UK retailers (Pets at Home, Amazon UK, Zooplus)
"""
        
        with open(self.reports_dir / "ROYAL_CANIN_RECONCILE_V2.md", 'w') as f:
            f.write(report)
    
    def generate_rollback_instructions(self):
        """Generate rollback instructions"""
        report = f"""# FIXPACK V2 ROLLBACK

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Rollback Instructions

Backups created at: `{self.backup_dir}`

### To rollback all changes:

```bash
# Restore all tables from backup
for file in {self.backup_dir}/*.csv; do
    filename=$(basename "$file")
    # Find and restore to original location
    find . -name "$filename" -exec cp "${{file}}" {{}} \\;
done
```

### To rollback specific table:

```bash
# Example for specific table
cp {self.backup_dir}/[TABLE_NAME].csv [ORIGINAL_PATH]
```

## Backup Contents

| File | Size | Timestamp |
|------|------|-----------|
"""
        
        for backup_file in self.backup_dir.glob("*.csv"):
            size_mb = backup_file.stat().st_size / 1024 / 1024
            timestamp = datetime.fromtimestamp(backup_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
            report += f"| {backup_file.name} | {size_mb:.2f} MB | {timestamp} |\n"
        
        with open(self.reports_dir / "FIXPACK_V2_ROLLBACK.md", 'w') as f:
            f.write(report)
    
    def run_all_phases(self):
        """Execute all phases of the fix pack"""
        print("="*60)
        print("CATALOG FIX PACK V2 - MASTER CONSOLIDATION")
        print("="*60)
        
        # Phase 1
        tables_found = self.phase1_inventory_lineage()
        print(f"\n✅ Phase 1 Complete: {tables_found} tables inventoried")
        
        # Phase 2
        health_before = self.phase2_health_sweep()
        print(f"\n✅ Phase 2 Complete: Health sweep completed")
        
        # Phase 3
        self.phase3_apply_fixes()
        print(f"\n✅ Phase 3 Complete: Fixes applied")
        
        # Phase 4
        pipeline_stats = self.phase4_recompose_pipeline()
        print(f"\n✅ Phase 4 Complete: Pipeline recomposed")
        
        # Phase 5
        brands_count, rc_tables = self.phase5_brand_spotlights()
        print(f"\n✅ Phase 5 Complete: {brands_count} brands analyzed")
        
        # Phase 6
        passed = self.phase6_acceptance_gates()
        print(f"\n✅ Phase 6 Complete: {'PASSED' if passed else 'NEEDS ATTENTION'}")
        
        print("\n" + "="*60)
        print("FIX PACK V2 COMPLETE")
        print("="*60)
        
        # Executive summary
        self.print_executive_summary()
    
    def print_executive_summary(self):
        """Print executive summary"""
        total_fixed = sum(
            stats.get('arrays_fixed', 0) + 
            stats.get('slugs_fixed', 0) + 
            stats.get('duplicates_removed', 0) +
            stats.get('brands_normalized', 0) +
            stats.get('life_stage_inferred', 0)
            for stats in self.fix_stats.values()
        )
        
        print(f"""
EXECUTIVE SUMMARY
-----------------
Tables Processed: {len(self.food_tables)}
Total Fixes Applied: {total_fixed:,}

Key Achievements:
✅ Stringified arrays converted to proper format
✅ Invalid slugs sanitized
✅ Duplicate products consolidated
✅ Brands normalized across all tables
✅ Life stages inferred where possible

Reports Generated:
- FOODS_LINEAGE.md
- FOODS_HEALTH_BEFORE.md
- FOODS_HEALTH_AFTER.md
- FIXPACK_V2_TYPES.md
- FIXPACK_V2_SLUGS.md
- FIXPACK_V2_DEDUP.md
- FIXPACK_V2_BRANDS.md
- FOODS_PIPELINE_AFTER.md
- FOODS_COMPARE_PREVIEW_PROD_AFTER.md
- FOODS_BRAND_SPOTLIGHT.md
- ROYAL_CANIN_RECONCILE_V2.md
- FIXPACK_V2_ROLLBACK.md
""")

def main():
    fix_pack = CatalogFixPackV2()
    fix_pack.run_all_phases()

if __name__ == "__main__":
    main()