#!/usr/bin/env python3
"""
B1: Audit all breed sources and produce consolidation report
"""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime
from collections import Counter, defaultdict
from dotenv import load_dotenv
from supabase import create_client
import logging
import re

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BreedsAuditor:
    def __init__(self):
        load_dotenv()
        self.supabase = self._connect_supabase()
        self.breed_tables = {}
        self.dogs_data = None
        
    def _connect_supabase(self):
        """Connect to Supabase"""
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not url or not key:
            raise ValueError("Missing Supabase credentials")
        
        return create_client(url, key)
    
    def discover_breed_tables(self):
        """Discover all breed-related tables"""
        logger.info("Discovering breed tables...")
        
        # Tables to check
        potential_tables = [
            'breed_catalog',
            'breeds_scraped', 
            'breed_raw',
            'breeds',
            'breed_data',
            'akc_breeds',
            'bark_breeds',
            'wikipedia_breeds',
            'dogs'  # Also check dogs table for breed info
        ]
        
        discovered = {}
        
        for table in potential_tables:
            try:
                response = self.supabase.table(table).select('*', count='exact').limit(1).execute()
                
                if response:
                    count = response.count
                    columns = list(response.data[0].keys()) if response.data else []
                    
                    discovered[table] = {
                        'count': count,
                        'columns': columns,
                        'sample': response.data[0] if response.data else None
                    }
                    
                    logger.info(f"  ✓ {table}: {count} rows, {len(columns)} columns")
                    
            except Exception as e:
                if '404' not in str(e) and 'does not exist' not in str(e):
                    logger.debug(f"  ✗ {table}: {str(e)[:50]}")
        
        self.breed_tables = discovered
        return discovered
    
    def analyze_field_coverage(self, table_name, df):
        """Analyze field coverage for a specific table"""
        coverage = {}
        
        # Check for size-related fields
        size_fields = ['size_category', 'size', 'weight', 'height', 'size_group']
        for field in size_fields:
            if field in df.columns:
                coverage[field] = {
                    'present': df[field].notna().sum(),
                    'percent': df[field].notna().sum() / len(df) * 100,
                    'unique_values': df[field].nunique()
                }
        
        # Check for age-related fields
        age_fields = ['growth_end_months', 'senior_start_months', 'life_expectancy', 
                     'maturity_age', 'senior_age']
        for field in age_fields:
            if field in df.columns:
                coverage[field] = {
                    'present': df[field].notna().sum(),
                    'percent': df[field].notna().sum() / len(df) * 100,
                    'stats': {
                        'min': df[field].min(),
                        'median': df[field].median(),
                        'max': df[field].max()
                    } if df[field].notna().any() else None
                }
        
        # Check for activity/energy fields
        activity_fields = ['activity_baseline', 'activity_level', 'energy_level', 
                          'exercise_needs', 'energy_factor_mod']
        for field in activity_fields:
            if field in df.columns:
                coverage[field] = {
                    'present': df[field].notna().sum(),
                    'percent': df[field].notna().sum() / len(df) * 100
                }
                
                if df[field].dtype == 'object':
                    coverage[field]['distribution'] = df[field].value_counts().to_dict()
        
        # Check for breed name fields
        name_fields = ['breed_name', 'name', 'breed', 'breed_slug']
        for field in name_fields:
            if field in df.columns:
                coverage[field] = {
                    'present': df[field].notna().sum(),
                    'percent': df[field].notna().sum() / len(df) * 100,
                    'unique': df[field].nunique()
                }
        
        return coverage
    
    def find_breed_aliases(self):
        """Find potential breed aliases across all tables"""
        logger.info("Finding breed aliases and duplicates...")
        
        all_breed_names = []
        
        # Collect all breed names from all tables
        for table_name, info in self.breed_tables.items():
            if info['count'] > 0 and table_name != 'dogs':
                try:
                    response = self.supabase.table(table_name).select('*').execute()
                    
                    if response.data:
                        df = pd.DataFrame(response.data)
                        
                        # Look for breed name columns
                        name_cols = [col for col in df.columns if 
                                    'breed' in col.lower() or 'name' in col.lower()]
                        
                        for col in name_cols:
                            if df[col].dtype == 'object':
                                names = df[col].dropna().tolist()
                                all_breed_names.extend([(name, table_name) for name in names])
                                
                except Exception as e:
                    logger.debug(f"Could not fetch data from {table_name}: {e}")
        
        # Create normalized versions and find clusters
        normalized_map = defaultdict(list)
        
        for name, source in all_breed_names:
            # Normalize: lowercase, strip, remove punctuation
            normalized = re.sub(r'[^\w\s]', '', name.lower().strip())
            normalized = ' '.join(normalized.split())  # Collapse whitespace
            
            normalized_map[normalized].append((name, source))
        
        # Find clusters with multiple variants
        alias_clusters = {}
        for normalized, variants in normalized_map.items():
            if len(variants) > 1 or normalized != variants[0][0].lower():
                unique_names = list(set([v[0] for v in variants]))
                if len(unique_names) > 1:
                    alias_clusters[normalized] = unique_names
        
        return alias_clusters
    
    def analyze_dogs_linkage(self):
        """Analyze how well dogs table links to breed data"""
        logger.info("Analyzing dogs table breed linkage...")
        
        try:
            # Get dogs data
            dogs_response = self.supabase.table('dogs').select('*').execute()
            
            if dogs_response.data:
                dogs_df = pd.DataFrame(dogs_response.data)
                self.dogs_data = dogs_df
                
                total_dogs = len(dogs_df)
                
                # Check for breed fields
                breed_fields = [col for col in dogs_df.columns if 'breed' in col.lower()]
                
                linkage_stats = {
                    'total_dogs': total_dogs,
                    'breed_fields': breed_fields
                }
                
                for field in breed_fields:
                    has_value = dogs_df[field].notna().sum()
                    linkage_stats[f'{field}_present'] = has_value
                    linkage_stats[f'{field}_percent'] = has_value / total_dogs * 100
                    
                    if has_value > 0:
                        # Get unique breed values
                        unique_breeds = dogs_df[field].dropna().unique()
                        linkage_stats[f'{field}_unique'] = len(unique_breeds)
                        
                        # Show top unmapped breeds (placeholder for now)
                        top_breeds = dogs_df[field].value_counts().head(10)
                        linkage_stats[f'{field}_top'] = top_breeds.to_dict()
                
                return linkage_stats
            
        except Exception as e:
            logger.error(f"Could not analyze dogs linkage: {e}")
            return None
    
    def generate_report(self):
        """Generate the complete audit report"""
        
        # Discover tables
        tables = self.discover_breed_tables()
        
        # Analyze each table
        table_analyses = {}
        total_rows = 0
        
        for table_name, info in tables.items():
            if info['count'] > 0 and table_name != 'dogs':
                total_rows += info['count']
                
                try:
                    # Get full data for analysis
                    response = self.supabase.table(table_name).select('*').limit(1000).execute()
                    
                    if response.data:
                        df = pd.DataFrame(response.data)
                        coverage = self.analyze_field_coverage(table_name, df)
                        
                        table_analyses[table_name] = {
                            'count': info['count'],
                            'columns': len(info['columns']),
                            'coverage': coverage
                        }
                        
                except Exception as e:
                    logger.error(f"Could not analyze {table_name}: {e}")
        
        # Find aliases
        alias_clusters = self.find_breed_aliases()
        
        # Analyze dogs linkage
        dogs_linkage = self.analyze_dogs_linkage()
        
        # Generate markdown report
        report = f"""# Breeds Consolidation — Audit Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## 0) Executive Summary

- Sources inspected: {', '.join([f'`{t}`' for t in tables.keys() if t != 'dogs'])}
- Total raw rows across sources: {total_rows:,}
- Unique breed name clusters found: {len(alias_clusters)}
- Dogs table analysis:
  - Total dogs: {dogs_linkage.get('total_dogs', 0) if dogs_linkage else 0:,}
  - With breed data: {dogs_linkage.get('breed_present', 0) if dogs_linkage else 0:,}
  
## 1) Source Inventory

| Source | Type | Rows | Key Columns Found | Notes |
|---|---|---:|---|---|
"""
        
        for table_name, info in tables.items():
            if table_name != 'dogs':
                key_cols = []
                if info['columns']:
                    # Identify key columns
                    for col in info['columns']:
                        if any(k in col.lower() for k in ['breed', 'name', 'size', 'weight', 'activity']):
                            key_cols.append(col)
                
                report += f"| `{table_name}` | table | {info['count']:,} | {', '.join(key_cols[:5])} | - |\n"
        
        # Add field coverage analysis
        report += "\n## 2) Field Coverage per Source\n\n"
        
        for table_name, analysis in table_analyses.items():
            report += f"### Source: `{table_name}`\n"
            report += f"- Rows: {analysis['count']:,}\n"
            report += "- Coverage:\n"
            
            for field, stats in analysis.get('coverage', {}).items():
                if 'percent' in stats:
                    report += f"  - {field}: {stats['percent']:.1f}%"
                    if 'unique_values' in stats:
                        report += f" ({stats['unique_values']} unique)"
                    report += "\n"
        
        # Add alias clusters
        report += "\n## 3) Alias & Duplicate Analysis\n\n"
        report += f"Found {len(alias_clusters)} potential alias clusters.\n\n"
        report += "**Example clusters (first 10):**\n"
        
        for i, (normalized, variants) in enumerate(list(alias_clusters.items())[:10], 1):
            report += f"{i}. `{normalized}` → {', '.join([f'"{v}"' for v in variants[:3]])}\n"
        
        # Add dogs linkage
        if dogs_linkage:
            report += "\n## 4) Dogs Table Linkage\n\n"
            report += "| Metric | Value |\n"
            report += "|---|---:|\n"
            report += f"| Dog records total | {dogs_linkage['total_dogs']:,} |\n"
            
            for field in dogs_linkage.get('breed_fields', []):
                present = dogs_linkage.get(f'{field}_present', 0)
                percent = dogs_linkage.get(f'{field}_percent', 0)
                report += f"| With {field} present | {present:,} ({percent:.1f}%) |\n"
        
        report += "\n## Next Steps\n\n"
        report += "1. Create breed_aliases mapping table\n"
        report += "2. Build compatibility views for each source\n"
        report += "3. Create breeds_canonical table with deduplication\n"
        report += "4. Verify dogs linkage and coverage targets\n"
        
        return report, {
            'tables': tables,
            'analyses': table_analyses,
            'aliases': alias_clusters,
            'dogs_linkage': dogs_linkage
        }
    
    def run(self):
        """Execute the complete audit"""
        logger.info("Starting Breeds Consolidation Audit...")
        
        report, data = self.generate_report()
        
        # Save report
        output_path = '/Users/sergiubiris/Desktop/lupito-content/docs/BREEDS-AUDIT-REPORT.md'
        with open(output_path, 'w') as f:
            f.write(report)
        
        logger.info(f"Report saved to: {output_path}")
        
        # Also save data as JSON for next steps
        data_path = '/Users/sergiubiris/Desktop/lupito-content/breeds_audit_data.json'
        with open(data_path, 'w') as f:
            # Convert any non-serializable objects
            json.dump({
                'tables': data['tables'],
                'aliases': data['aliases'],
                'dogs_linkage': data['dogs_linkage']
            }, f, indent=2, default=str)
        
        print("\n" + "="*80)
        print("✅ Breeds Audit Complete!")
        print(f"   Report: {output_path}")
        print(f"   Data: {data_path}")
        print("="*80)
        
        return data

if __name__ == "__main__":
    auditor = BreedsAuditor()
    auditor.run()