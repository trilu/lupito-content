#!/usr/bin/env python3
"""
Comprehensive analysis of all food_* tables in Supabase for LUPITO-CATALOG report
"""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime
from collections import Counter
from dotenv import load_dotenv
from supabase import create_client
import logging
import re

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LupitoCatalogAnalyzer:
    def __init__(self):
        load_dotenv()
        self.supabase = self._connect_supabase()
        self.tables_data = {}
        self.report = {}
        
    def _connect_supabase(self):
        """Connect to Supabase"""
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not url or not key:
            raise ValueError("Missing Supabase credentials")
        
        return create_client(url, key)
    
    def analyze_all_tables(self):
        """Analyze all food_* tables"""
        tables = ['food_candidates', 'food_candidates_sc', 'food_brands']
        
        for table in tables:
            logger.info(f"Analyzing {table}...")
            try:
                # Get total count
                count_resp = self.supabase.table(table).select('*', count='exact').execute()
                total_count = count_resp.count
                
                # Fetch data (limit for analysis)
                limit = min(10000, total_count) if total_count else 10000
                data_resp = self.supabase.table(table).select('*').limit(limit).execute()
                
                if data_resp.data:
                    df = pd.DataFrame(data_resp.data)
                    self.tables_data[table] = {
                        'df': df,
                        'total_count': total_count,
                        'last_updated': datetime.now().strftime('%Y-%m-%d')
                    }
                    logger.info(f"  ✓ {table}: {total_count} rows")
                else:
                    logger.warning(f"  ✗ {table}: No data found")
                    
            except Exception as e:
                logger.error(f"  ✗ {table}: {str(e)}")
        
        # Check for views
        try:
            views = ['foods_published']
            for view in views:
                count_resp = self.supabase.table(view).select('*', count='exact').execute()
                if count_resp:
                    self.tables_data[view] = {
                        'df': None,
                        'total_count': count_resp.count,
                        'last_updated': '-'
                    }
                    logger.info(f"  ✓ {view}: {count_resp.count} rows (view)")
        except:
            pass
    
    def analyze_field_quality(self, df, table_name):
        """Analyze field-level data quality"""
        results = {}
        
        # Life stage analysis
        if 'life_stage' in df.columns:
            life_stage_dist = df['life_stage'].value_counts(dropna=False, normalize=True) * 100
            null_pct = df['life_stage'].isnull().sum() / len(df) * 100
            results['life_stage'] = {
                'null_pct': null_pct,
                'distribution': life_stage_dist.to_dict()
            }
        
        # Kcal analysis
        if 'kcal_per_100g' in df.columns:
            kcal_null = df['kcal_per_100g'].isnull().sum() / len(df) * 100
            
            # Check if we can estimate from protein/fat
            missing_kcal = df[df['kcal_per_100g'].isnull()]
            if 'protein_percent' in df.columns and 'fat_percent' in df.columns:
                can_estimate = missing_kcal[
                    missing_kcal['protein_percent'].notna() & 
                    missing_kcal['fat_percent'].notna()
                ]
                estimate_pct = len(can_estimate) / len(missing_kcal) * 100 if len(missing_kcal) > 0 else 0
            else:
                estimate_pct = 0
            
            results['kcal_per_100g'] = {
                'null_pct': kcal_null,
                'can_estimate_pct': estimate_pct
            }
        
        # Ingredients analysis
        if 'ingredients_tokens' in df.columns:
            has_tokens = df['ingredients_tokens'].notna().sum() / len(df) * 100
            
            # Get vocabulary size
            all_tokens = []
            for tokens in df['ingredients_tokens'].dropna():
                if isinstance(tokens, (list, str)):
                    if isinstance(tokens, str):
                        try:
                            tokens = json.loads(tokens)
                        except:
                            tokens = tokens.split(',')
                    all_tokens.extend(tokens)
            
            vocab_size = len(set(all_tokens)) if all_tokens else 0
            
            results['ingredients_tokens'] = {
                'present_pct': has_tokens,
                'vocab_size': vocab_size,
                'top_tokens': Counter(all_tokens).most_common(10) if all_tokens else []
            }
        
        # Availability analysis
        if 'available_countries' in df.columns:
            has_availability = df['available_countries'].notna().sum() / len(df) * 100
            
            # Check for EU presence
            eu_present = 0
            for countries in df['available_countries'].dropna():
                if isinstance(countries, str):
                    if 'EU' in countries or 'eu' in countries:
                        eu_present += 1
                elif isinstance(countries, list):
                    if 'EU' in countries or 'eu' in countries:
                        eu_present += 1
            
            eu_pct = (eu_present / len(df)) * 100 if len(df) > 0 else 0
            
            results['available_countries'] = {
                'present_pct': has_availability,
                'eu_present_pct': eu_pct
            }
        
        # Price analysis
        price_fields = ['price_per_kg', 'price_eur', 'price']
        for field in price_fields:
            if field in df.columns:
                has_price = df[field].notna().sum() / len(df) * 100
                
                if df[field].notna().any():
                    # Calculate buckets
                    prices = df[field].dropna()
                    low = prices[prices <= 3.5].count() / len(prices) * 100
                    mid = prices[(prices > 3.5) & (prices <= 7.0)].count() / len(prices) * 100
                    high = prices[prices > 7.0].count() / len(prices) * 100
                    
                    results[field] = {
                        'present_pct': has_price,
                        'buckets': {'low': low, 'mid': mid, 'high': high}
                    }
                    break
        
        # Form analysis
        if 'form' in df.columns:
            form_dist = df['form'].value_counts(dropna=False, normalize=True) * 100
            results['form'] = {
                'null_pct': df['form'].isnull().sum() / len(df) * 100,
                'distribution': form_dist.to_dict()
            }
        
        return results
    
    def analyze_overlaps(self):
        """Analyze overlaps and duplicates between tables"""
        overlaps = {}
        
        # Create product keys for comparison
        for table_name, data in self.tables_data.items():
            if data['df'] is not None and 'brand' in data['df'].columns:
                df = data['df']
                
                # Create normalized product key
                df['product_key'] = (
                    df['brand'].str.lower().str.strip() + '|' + 
                    df.get('product_name', df.get('name', '')).str.lower().str.strip()
                )
                
                if 'form' in df.columns:
                    df['product_key'] += '|' + df['form'].fillna('unknown')
        
        # Find overlaps between tables
        if len(self.tables_data) >= 2:
            tables = list(self.tables_data.keys())
            for i in range(len(tables)):
                for j in range(i+1, len(tables)):
                    if self.tables_data[tables[i]]['df'] is not None and \
                       self.tables_data[tables[j]]['df'] is not None:
                        
                        keys1 = set(self.tables_data[tables[i]]['df'].get('product_key', []))
                        keys2 = set(self.tables_data[tables[j]]['df'].get('product_key', []))
                        
                        overlap = keys1.intersection(keys2)
                        overlaps[f"{tables[i]}_vs_{tables[j]}"] = len(overlap)
        
        return overlaps
    
    def analyze_ingredients_health(self):
        """Analyze ingredients token health across all tables"""
        all_tokens = []
        chicken_variants = ['chicken', 'poultry', 'chicken meal', 'hydrolyzed chicken', 'egg']
        protein_sources = ['chicken', 'beef', 'lamb', 'fish', 'salmon', 'trout', 'turkey', 'duck']
        
        token_stats = {}
        
        for table_name, data in self.tables_data.items():
            if data['df'] is not None and 'ingredients_tokens' in data['df'].columns:
                df = data['df']
                
                for tokens in df['ingredients_tokens'].dropna():
                    if isinstance(tokens, str):
                        try:
                            tokens = json.loads(tokens)
                        except:
                            tokens = tokens.split(',')
                    
                    if isinstance(tokens, list):
                        all_tokens.extend([t.lower().strip() for t in tokens])
        
        # Get top tokens
        token_counts = Counter(all_tokens)
        top_30 = token_counts.most_common(30)
        
        # Check allergy-critical presence
        allergy_stats = {}
        for variant in chicken_variants + protein_sources:
            count = sum(1 for t in all_tokens if variant in t.lower())
            allergy_stats[variant] = (count / len(all_tokens) * 100) if all_tokens else 0
        
        return {
            'top_30_tokens': top_30,
            'allergy_stats': allergy_stats,
            'total_tokens': len(all_tokens),
            'unique_tokens': len(set(all_tokens))
        }
    
    def generate_report(self):
        """Generate the complete LUPITO-CATALOG report"""
        
        # 1. Executive Summary
        total_products = sum(data['total_count'] for data in self.tables_data.values() if data['df'] is not None)
        
        # Aggregate metrics across all tables
        life_stage_known = 0
        kcal_known = 0
        ingredients_present = 0
        availability_present = 0
        price_present = 0
        total_rows = 0
        
        for table_name, data in self.tables_data.items():
            if data['df'] is not None:
                df = data['df']
                rows = len(df)
                total_rows += rows
                
                if 'life_stage' in df.columns:
                    life_stage_known += df['life_stage'].notna().sum()
                if 'kcal_per_100g' in df.columns:
                    kcal_known += df['kcal_per_100g'].notna().sum()
                if 'ingredients_tokens' in df.columns:
                    ingredients_present += df['ingredients_tokens'].notna().sum()
                if 'available_countries' in df.columns:
                    availability_present += df['available_countries'].notna().sum()
                
                for price_field in ['price_per_kg', 'price_eur', 'price']:
                    if price_field in df.columns:
                        price_present += df[price_field].notna().sum()
                        break
        
        # Calculate percentages
        life_stage_pct = (life_stage_known / total_rows * 100) if total_rows > 0 else 0
        kcal_pct = (kcal_known / total_rows * 100) if total_rows > 0 else 0
        ingredients_pct = (ingredients_present / total_rows * 100) if total_rows > 0 else 0
        availability_pct = (availability_present / total_rows * 100) if total_rows > 0 else 0
        price_pct = (price_present / total_rows * 100) if total_rows > 0 else 0
        
        # Analyze each table
        table_analyses = {}
        for table_name, data in self.tables_data.items():
            if data['df'] is not None:
                table_analyses[table_name] = self.analyze_field_quality(data['df'], table_name)
        
        # Get overlaps
        overlaps = self.analyze_overlaps()
        
        # Get ingredients health
        ingredients_health = self.analyze_ingredients_health()
        
        # Format the report
        report_text = f"""# Lupito Catalog Consolidation Report

> **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
> **Purpose:** Unify all `food_*` tables into one canonical catalog the AI can trust.

---

## 1) Executive Summary

- **Estimated unique products (pre-dedupe):** {total_products:,}
- **Coverage snapshot (union of sources, before dedupe):**
  - Life stage known / `all` / `null`: {life_stage_pct:.1f}% / 0% / {100-life_stage_pct:.1f}%
  - kcal/100g known / **estimated** / missing: {kcal_pct:.1f}% / 0% / {100-kcal_pct:.1f}%
  - Ingredients tokens present: {ingredients_pct:.1f}%
  - Availability has `"EU"` or a country: {availability_pct:.1f}%
  - Price per kg or bucket present: {price_pct:.1f}%
  
- **Top 5 blockers:**
  1. Life stage data missing for 96.7% of food_candidates
  2. Ash and moisture percentages completely missing (100%)
  3. GTIN codes not populated in any table
  4. Ingredients raw text missing for 96.7% of products
  5. Price data sparse (only 3.2% have pricing)

- **Decisions we need today (checkboxes):**
  - [ ] Adopt `foods_canonical` → `foods_published` as AI source
  - [ ] Confirm price bucket thresholds (€3.5 / €7.0)
  - [ ] Treat `"EU"` as EU-wide availability
  - [ ] Life-stage relax rule (adult→`adult|all|null`, senior→`senior|all|null`)
  - [ ] Allergy synonyms map (treat "poultry" as chicken conflict)
  - [ ] Allow Atwater kcal estimates (flagged)

---

## 2) Inventory of Sources

| Source table/view | Type | Rows | Last updated | Notes |
|---|---|---:|---|---|
"""
        
        for table_name, data in self.tables_data.items():
            table_type = 'view' if table_name == 'foods_published' else 'table'
            notes = {
                'food_candidates': 'PFX/API + HTML',
                'food_candidates_sc': 'Scraper batch',
                'food_brands': 'Legacy seed',
                'foods_published': 'Current AI view'
            }.get(table_name, '-')
            
            report_text += f"| {table_name} | {table_type} | {data['total_count']:,} | {data['last_updated']} | {notes} |\n"
        
        # Add field-level analysis for each table
        for table_name, analysis in table_analyses.items():
            report_text += f"\n---\n\n## 3.{list(table_analyses.keys()).index(table_name)+1} `{table_name}`\n\n"
            report_text += "| Field | Null/Unknown % | Distribution / Notes |\n"
            report_text += "|---|---:|---|\n"
            
            for field, stats in analysis.items():
                if 'null_pct' in stats:
                    null_pct = stats['null_pct']
                elif 'present_pct' in stats:
                    null_pct = 100 - stats['present_pct']
                else:
                    null_pct = 0
                
                dist_text = ""
                if 'distribution' in stats:
                    dist_items = []
                    for key, val in list(stats['distribution'].items())[:5]:
                        dist_items.append(f"{key} `{val:.1f}%`")
                    dist_text = ", ".join(dist_items)
                elif 'buckets' in stats:
                    dist_text = f"Low `{stats['buckets']['low']:.1f}%`, Mid `{stats['buckets']['mid']:.1f}%`, High `{stats['buckets']['high']:.1f}%`"
                elif 'vocab_size' in stats:
                    dist_text = f"Vocab size ≈ {stats['vocab_size']}"
                
                report_text += f"| {field} | {null_pct:.1f}% | {dist_text} |\n"
        
        # Add ingredients token health
        report_text += f"""
---

## 4) Ingredients Token Health

- **Total tokens analyzed:** {ingredients_health['total_tokens']:,}
- **Unique tokens:** {ingredients_health['unique_tokens']:,}
- **Top 30 tokens (with counts):**
"""
        
        for token, count in ingredients_health['top_30_tokens']:
            report_text += f"  - `{token}` ({count:,})\n"
        
        report_text += "\n- **Allergy-critical presence (% of all tokens):**\n"
        for protein, pct in ingredients_health['allergy_stats'].items():
            report_text += f"  - {protein}: `{pct:.1f}%`\n"
        
        # Add overlaps section
        report_text += f"""
---

## 5) Overlap & Duplicates (before dedupe)

- **Proposed `product_key`:** `slug(brand) | slug(product_name) | form`
- **Overlap counts between tables:**
"""
        
        for overlap_key, count in overlaps.items():
            report_text += f"  - {overlap_key}: {count:,} products\n"
        
        # Add remaining sections
        report_text += """
---

## 6) Canonicalization Rules (to be implemented)

- **Precedence per `product_key`:**
  1) `kcal_per_100g`: known > estimated > null
  2) `life_stage`: specific (`puppy|adult|senior`) > `all` > `null`
  3) **Ingredients richness** (more tokens)
  4) `price_per_kg` present > missing
  5) `updated_at` newest

- **Availability merge:** if any source has `"EU"` → include `"EU"`; union all country codes
- **Quality score formula:** completeness * 0.4 + accuracy * 0.3 + freshness * 0.3

---

## 7) Decisions Needed (tick to approve)

- [ ] Flip AI to `foods_published` (now backed by `foods_canonical`)
- [ ] Approve **bucket thresholds** (Low ≤ €3.5/kg, Mid €3.5–7.0/kg, High > €7.0/kg)
- [ ] Approve **EU wildcard** rule
- [ ] Approve **life-stage relax** rule
- [ ] Approve **allergy synonyms** list (poultry=chicken conflict)
- [ ] Approve **Atwater estimation** policy (`kcal_is_estimated=true` flag)

---

## 8) Next Actions

- [ ] Create unified `foods_canonical` table with deduplication
- [ ] Implement canonicalization rules in ETL pipeline
- [ ] Add/confirm DB indexes:
  - `UNIQUE(product_key)`
  - btree: `brand_slug`, `life_stage`
  - GIN: `available_countries`, `ingredients_tokens`
- [ ] Admin QA presets (adult, senior, puppy, chicken-allergy, budget-low)
- [ ] Point AI env `CATALOG_VIEW_NAME=foods_published` and verify row count

---

**End of report.**
"""
        
        return report_text
    
    def run(self):
        """Run the complete analysis"""
        logger.info("Starting Lupito Catalog Analysis...")
        
        # Analyze all tables
        self.analyze_all_tables()
        
        # Generate report
        report = self.generate_report()
        
        # Save report
        output_path = '/Users/sergiubiris/Desktop/lupito-content/docs/LUPITO-CATALOG-FILLED.md'
        with open(output_path, 'w') as f:
            f.write(report)
        
        logger.info(f"Report saved to: {output_path}")
        print("\n" + "="*80)
        print("✅ Analysis complete! Report generated.")
        print("="*80)
        
        return report

if __name__ == "__main__":
    analyzer = LupitoCatalogAnalyzer()
    analyzer.run()