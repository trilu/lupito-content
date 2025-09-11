#!/usr/bin/env python3
"""
Manufacturer enrichment reconciliation pipeline
Merges manufacturer data into foods_published_v2 with field-level provenance
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from supabase import create_client
from dotenv import load_dotenv
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ManufacturerEnrichmentPipeline:
    def __init__(self):
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not found")
            
        self.supabase = create_client(supabase_url, supabase_key)
        self.report_dir = Path("reports/MANUF")
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
        # Field precedence order
        self.precedence = [
            'overrides',
            'enrichment_prices_v2',
            'enrichment_classify_v2', 
            'enrichment_manuf',
            'original_source',
            'default'
        ]
    
    def load_catalog(self) -> pd.DataFrame:
        """Load current catalog from foods_published"""
        logger.info("Loading catalog from foods_published...")
        
        response = self.supabase.table('foods_published').select("*").limit(5000).execute()
        df = pd.DataFrame(response.data)
        
        # Filter for dog products only
        if 'product_name' in df.columns:
            dog_mask = ~df['product_name'].str.lower().str.contains('cat|kitten|feline', na=False)
            df = df[dog_mask]
        
        logger.info(f"Loaded {len(df)} dog products")
        return df
    
    def load_manufacturer_data(self) -> pd.DataFrame:
        """Load harvested manufacturer data"""
        logger.info("Loading manufacturer enrichment data...")
        
        # Look for harvest output files
        harvest_dir = Path("reports/MANUF/harvests")
        harvest_files = list(harvest_dir.glob("*_harvest_*.csv"))
        
        if not harvest_files:
            logger.warning("No harvest files found")
            return pd.DataFrame()
        
        # Combine all harvest files
        dfs = []
        for file in harvest_files:
            df = pd.read_csv(file)
            # Filter for dog products
            if 'product_name' in df.columns:
                dog_mask = ~df['product_name'].str.lower().str.contains('cat|kitten|feline', na=False)
                df = df[dog_mask]
            dfs.append(df)
        
        manuf_df = pd.concat(dfs, ignore_index=True)
        logger.info(f"Loaded {len(manuf_df)} manufacturer records")
        
        return manuf_df
    
    def match_products(self, catalog_df: pd.DataFrame, manuf_df: pd.DataFrame) -> pd.DataFrame:
        """Match manufacturer data to catalog products"""
        logger.info("Matching manufacturer data to catalog...")
        
        matches = []
        
        for _, manuf_row in manuf_df.iterrows():
            # Try to match by brand and product name similarity
            brand_matches = catalog_df[
                catalog_df['brand_slug'] == manuf_row.get('brand_slug', '')
            ]
            
            if len(brand_matches) == 0:
                continue
            
            # Simple name matching (can be improved with fuzzy matching)
            manuf_name = str(manuf_row.get('product_name', '')).lower()
            
            for _, catalog_row in brand_matches.iterrows():
                catalog_name = str(catalog_row.get('product_name', '')).lower()
                
                # Check if significant overlap in product names
                manuf_tokens = set(manuf_name.split())
                catalog_tokens = set(catalog_name.split())
                
                if len(manuf_tokens & catalog_tokens) >= 2:
                    match = {
                        'product_key': catalog_row['product_key'],
                        'brand': catalog_row['brand'],
                        'catalog_name': catalog_row['product_name'],
                        'manuf_name': manuf_row.get('product_name'),
                        'match_confidence': 0.8
                    }
                    
                    # Add enrichment fields
                    for field in ['ingredients_tokens', 'allergen_groups', 'form', 'life_stage',
                                 'protein_percent', 'fat_percent', 'fiber_percent', 
                                 'kcal_per_100g', 'price', 'price_per_kg']:
                        if field in manuf_row and pd.notna(manuf_row[field]):
                            match[f'manuf_{field}'] = manuf_row[field]
                    
                    matches.append(match)
                    break
        
        matches_df = pd.DataFrame(matches)
        logger.info(f"Found {len(matches_df)} product matches")
        
        return matches_df
    
    def create_enrichment_table(self, matches_df: pd.DataFrame) -> pd.DataFrame:
        """Create foods_enrichment_manuf table"""
        logger.info("Creating manufacturer enrichment table...")
        
        enrichment_records = []
        
        for _, row in matches_df.iterrows():
            record = {
                'product_key': row['product_key'],
                'source': 'manufacturer',
                'fetched_at': datetime.now().isoformat(),
                'confidence': row['match_confidence']
            }
            
            # Map manufacturer fields to enrichment fields
            field_mapping = {
                'manuf_ingredients_tokens': 'ingredients_tokens',
                'manuf_allergen_groups': 'allergen_groups',
                'manuf_form': 'form',
                'manuf_life_stage': 'life_stage',
                'manuf_protein_percent': 'protein_percent',
                'manuf_fat_percent': 'fat_percent',
                'manuf_fiber_percent': 'fiber_percent',
                'manuf_kcal_per_100g': 'kcal_per_100g',
                'manuf_price': 'price_eur',
                'manuf_price_per_kg': 'price_per_kg_eur'
            }
            
            for manuf_field, enrich_field in field_mapping.items():
                if manuf_field in row and pd.notna(row[manuf_field]):
                    record[enrich_field] = row[manuf_field]
                    record[f'{enrich_field}_from'] = 'enrichment_manuf'
                    record[f'{enrich_field}_confidence'] = row['match_confidence'] * 0.9
            
            # Set ingredients_unknown
            if 'ingredients_tokens' in record and record['ingredients_tokens']:
                record['ingredients_unknown'] = False
            
            enrichment_records.append(record)
        
        enrichment_df = pd.DataFrame(enrichment_records)
        
        # Save to CSV
        output_file = self.report_dir / "foods_enrichment_manuf.csv"
        enrichment_df.to_csv(output_file, index=False)
        logger.info(f"Saved enrichment table to {output_file}")
        
        return enrichment_df
    
    def reconcile_v2(self, catalog_df: pd.DataFrame, enrichment_df: pd.DataFrame) -> pd.DataFrame:
        """Create foods_published_v2 with reconciled data"""
        logger.info("Reconciling to foods_published_v2...")
        
        # Start with catalog as base
        v2_df = catalog_df.copy()
        
        # Merge enrichment data
        enrichment_cols = [col for col in enrichment_df.columns if col != 'product_key']
        v2_df = v2_df.merge(
            enrichment_df[['product_key'] + enrichment_cols],
            on='product_key',
            how='left',
            suffixes=('', '_manuf')
        )
        
        # Apply precedence rules for each field
        fields_to_reconcile = ['form', 'life_stage', 'kcal_per_100g', 'ingredients_tokens', 'price_per_kg']
        
        for field in fields_to_reconcile:
            # Check if manufacturer has this field
            manuf_field = f'{field}_manuf'
            if manuf_field in v2_df.columns:
                # Update where original is missing but manufacturer has data
                mask = v2_df[field].isna() & v2_df[manuf_field].notna()
                v2_df.loc[mask, field] = v2_df.loc[mask, manuf_field]
                v2_df.loc[mask, f'{field}_from'] = 'enrichment_manuf'
        
        # Calculate price buckets
        if 'price_per_kg' in v2_df.columns:
            v2_df['price_bucket'] = pd.cut(
                v2_df['price_per_kg'],
                bins=[0, 5, 10, 20, 40, 100],
                labels=['budget', 'economy', 'mid', 'premium', 'super_premium']
            )
        
        # Save v2 table
        output_file = self.report_dir / "foods_published_v2.csv"
        v2_df.to_csv(output_file, index=False)
        logger.info(f"Saved foods_published_v2 to {output_file}")
        
        return v2_df
    
    def calculate_coverage_metrics(self, df: pd.DataFrame, name: str) -> Dict:
        """Calculate field coverage metrics"""
        metrics = {
            'total_products': len(df),
            'form_coverage': (~df['form'].isna()).mean() * 100 if 'form' in df else 0,
            'life_stage_coverage': (~df['life_stage'].isna()).mean() * 100 if 'life_stage' in df else 0,
            'ingredients_coverage': (~df['ingredients_tokens'].isna()).mean() * 100 if 'ingredients_tokens' in df else 0,
            'kcal_coverage': (~df['kcal_per_100g'].isna()).mean() * 100 if 'kcal_per_100g' in df else 0,
            'price_coverage': (~df['price_per_kg'].isna()).mean() * 100 if 'price_per_kg' in df else 0,
            'price_bucket_coverage': (~df['price_bucket'].isna()).mean() * 100 if 'price_bucket' in df else 0
        }
        
        # Check for kcal outliers
        if 'kcal_per_100g' in df:
            kcal_values = df['kcal_per_100g'].dropna()
            outliers = (kcal_values < 200) | (kcal_values > 600)
            metrics['kcal_outliers'] = outliers.sum()
        else:
            metrics['kcal_outliers'] = 0
        
        return metrics
    
    def check_quality_gates(self, before_metrics: Dict, after_metrics: Dict) -> Dict:
        """Check if quality gates pass"""
        gates = {
            'form_95': after_metrics['form_coverage'] >= 95,
            'life_stage_95': after_metrics['life_stage_coverage'] >= 95,
            'ingredients_85': after_metrics['ingredients_coverage'] >= 85,
            'price_bucket_70': after_metrics['price_bucket_coverage'] >= 70,
            'price_per_kg_50': after_metrics['price_coverage'] >= 50,
            'zero_kcal_outliers': after_metrics['kcal_outliers'] == 0,
            'all_passed': False
        }
        
        gates['all_passed'] = all([
            gates['form_95'],
            gates['life_stage_95'],
            gates['ingredients_85'],
            gates['price_bucket_70'],
            gates['zero_kcal_outliers']
        ])
        
        return gates
    
    def generate_reports(self, catalog_df: pd.DataFrame, v2_df: pd.DataFrame, 
                        enrichment_df: pd.DataFrame, gates: Dict):
        """Generate all required reports"""
        logger.info("Generating reports...")
        
        # Calculate metrics
        before_metrics = self.calculate_coverage_metrics(catalog_df, "Before")
        after_metrics = self.calculate_coverage_metrics(v2_df, "After")
        
        # Main coverage report
        coverage_report = f"""# MANUFACTURER ENRICHMENT COVERAGE REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Coverage Before Enrichment
- Total Products: {before_metrics['total_products']}
- Form: {before_metrics['form_coverage']:.1f}%
- Life Stage: {before_metrics['life_stage_coverage']:.1f}%
- Ingredients: {before_metrics['ingredients_coverage']:.1f}%
- Kcal: {before_metrics['kcal_coverage']:.1f}%
- Price per kg: {before_metrics['price_coverage']:.1f}%
- Price Bucket: {before_metrics['price_bucket_coverage']:.1f}%
- Kcal Outliers: {before_metrics['kcal_outliers']}

## Coverage After Enrichment
- Total Products: {after_metrics['total_products']}
- Form: {after_metrics['form_coverage']:.1f}% (+{after_metrics['form_coverage']-before_metrics['form_coverage']:.1f}pp)
- Life Stage: {after_metrics['life_stage_coverage']:.1f}% (+{after_metrics['life_stage_coverage']-before_metrics['life_stage_coverage']:.1f}pp)
- Ingredients: {after_metrics['ingredients_coverage']:.1f}% (+{after_metrics['ingredients_coverage']-before_metrics['ingredients_coverage']:.1f}pp)
- Kcal: {after_metrics['kcal_coverage']:.1f}% (+{after_metrics['kcal_coverage']-before_metrics['kcal_coverage']:.1f}pp)
- Price per kg: {after_metrics['price_coverage']:.1f}% (+{after_metrics['price_coverage']-before_metrics['price_coverage']:.1f}pp)
- Price Bucket: {after_metrics['price_bucket_coverage']:.1f}% (+{after_metrics['price_bucket_coverage']-before_metrics['price_bucket_coverage']:.1f}pp)
- Kcal Outliers: {after_metrics['kcal_outliers']}

## Quality Gates
- Form ≥95%: {'✅ PASS' if gates['form_95'] else '❌ FAIL'} ({after_metrics['form_coverage']:.1f}%)
- Life Stage ≥95%: {'✅ PASS' if gates['life_stage_95'] else '❌ FAIL'} ({after_metrics['life_stage_coverage']:.1f}%)
- Ingredients ≥85%: {'✅ PASS' if gates['ingredients_85'] else '❌ FAIL'} ({after_metrics['ingredients_coverage']:.1f}%)
- Price Bucket ≥70%: {'✅ PASS' if gates['price_bucket_70'] else '❌ FAIL'} ({after_metrics['price_bucket_coverage']:.1f}%)
- Price per kg ≥50%: {'✅ PASS' if gates['price_per_kg_50'] else '❌ FAIL'} ({after_metrics['price_coverage']:.1f}%)
- Zero Kcal Outliers: {'✅ PASS' if gates['zero_kcal_outliers'] else '❌ FAIL'} ({after_metrics['kcal_outliers']} outliers)

## Overall Status: {'✅ READY FOR PRODUCTION' if gates['all_passed'] else '❌ NOT READY'}

## Enrichment Summary
- Products Enriched: {len(enrichment_df)}
- Match Rate: {len(enrichment_df)/len(catalog_df)*100:.1f}%
"""
        
        with open(self.report_dir / "MANUF_FIELD_COVERAGE_AFTER.md", "w") as f:
            f.write(coverage_report)
        
        # Sample report
        sample_df = v2_df.sample(min(100, len(v2_df)))
        sample_df[['product_key', 'brand', 'product_name', 'form', 'life_stage', 
                  'kcal_per_100g', 'price_per_kg', 'price_bucket']].to_csv(
            self.report_dir / "MANUF_SAMPLE_100.csv", index=False
        )
        
        logger.info("Reports generated successfully")
        
        return coverage_report, gates
    
    def run(self):
        """Run the complete enrichment pipeline"""
        logger.info("Starting Manufacturer Enrichment Pipeline")
        logger.info("=" * 50)
        
        # Load data
        catalog_df = self.load_catalog()
        manuf_df = self.load_manufacturer_data()
        
        if manuf_df.empty:
            logger.warning("No manufacturer data available. Run harvest first.")
            return
        
        # Match and enrich
        matches_df = self.match_products(catalog_df, manuf_df)
        
        if matches_df.empty:
            logger.warning("No product matches found")
            return
        
        enrichment_df = self.create_enrichment_table(matches_df)
        
        # Reconcile
        v2_df = self.reconcile_v2(catalog_df, enrichment_df)
        
        # Check quality gates
        before_metrics = self.calculate_coverage_metrics(catalog_df, "Before")
        after_metrics = self.calculate_coverage_metrics(v2_df, "After")
        gates = self.check_quality_gates(before_metrics, after_metrics)
        
        # Generate reports
        report, gates = self.generate_reports(catalog_df, v2_df, enrichment_df, gates)
        
        print(report)
        
        logger.info("=" * 50)
        logger.info("Manufacturer Enrichment Pipeline Complete!")
        
        return v2_df, gates

if __name__ == "__main__":
    pipeline = ManufacturerEnrichmentPipeline()
    pipeline.run()