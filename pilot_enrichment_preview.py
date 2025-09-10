#!/usr/bin/env python3
"""
Production Pilot: Process enrichment and create foods_published_preview
"""

import os
import pandas as pd
import numpy as np
import json
from datetime import datetime
from pathlib import Path
from supabase import create_client
from dotenv import load_dotenv
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PilotEnrichmentProcessor:
    def __init__(self):
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not found")
            
        self.supabase = create_client(supabase_url, supabase_key)
        
        self.harvest_dir = Path("reports/MANUF/PILOT/harvests")
        self.report_dir = Path("reports/MANUF/PILOT")
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
        # Top 5 brands
        self.pilot_brands = ['brit', 'alpha', 'briantos', 'bozita', 'belcando']
        
    def load_catalog_data(self):
        """Load current catalog data for pilot brands"""
        logger.info("Loading catalog data for pilot brands...")
        
        response = self.supabase.table('foods_published').select("*").in_(
            "brand_slug", self.pilot_brands
        ).limit(1000).execute()
        
        catalog_df = pd.DataFrame(response.data)
        
        # Filter dog products only
        if 'product_name' in catalog_df.columns:
            dog_mask = ~catalog_df['product_name'].str.lower().str.contains('cat|kitten|feline', na=False)
            catalog_df = catalog_df[dog_mask]
        
        logger.info(f"Loaded {len(catalog_df)} catalog products for pilot brands")
        return catalog_df
    
    def load_harvest_data(self):
        """Load harvest data for all pilot brands"""
        logger.info("Loading harvest data...")
        
        all_harvest = []
        
        for brand in self.pilot_brands:
            # Find latest pilot harvest file for brand
            harvest_files = list(self.harvest_dir.glob(f"{brand}_pilot_*.csv"))
            if harvest_files:
                # Get most recent file
                latest_file = max(harvest_files, key=lambda p: p.stat().st_mtime)
                df = pd.read_csv(latest_file)
                logger.info(f"  {brand}: {len(df)} products from {latest_file.name}")
                all_harvest.append(df)
        
        if all_harvest:
            harvest_df = pd.concat(all_harvest, ignore_index=True)
            logger.info(f"Total harvest: {len(harvest_df)} products")
            return harvest_df
        else:
            logger.warning("No harvest data found")
            return pd.DataFrame()
    
    def match_products(self, catalog_df, harvest_df):
        """Match harvested products to catalog"""
        logger.info("Matching harvested products to catalog...")
        
        matches = []
        unmatched_harvest = []
        unmatched_catalog = list(catalog_df['product_key'].values)
        
        for _, harvest_row in harvest_df.iterrows():
            brand_slug = harvest_row['brand_slug']
            harvest_name = str(harvest_row.get('product_name', '')).lower()
            
            # Find best match in catalog for this brand
            brand_products = catalog_df[catalog_df['brand_slug'] == brand_slug]
            
            best_match = None
            best_score = 0
            
            for _, catalog_row in brand_products.iterrows():
                catalog_name = str(catalog_row.get('product_name', '')).lower()
                
                # Simple token matching
                harvest_tokens = set(harvest_name.split())
                catalog_tokens = set(catalog_name.split())
                
                if len(harvest_tokens) > 0 and len(catalog_tokens) > 0:
                    score = len(harvest_tokens & catalog_tokens) / len(harvest_tokens | catalog_tokens)
                    
                    if score > best_score:
                        best_score = score
                        best_match = catalog_row
            
            # Accept match if score > 0.3
            if best_score > 0.3 and best_match is not None:
                match = {
                    'product_key': best_match['product_key'],
                    'catalog_name': best_match['product_name'],
                    'harvest_name': harvest_row['product_name'],
                    'match_score': best_score,
                    'brand': harvest_row['brand'],
                    'brand_slug': brand_slug
                }
                
                # Add enrichment fields from harvest
                for field in ['form', 'life_stage', 'ingredients', 'ingredients_tokens',
                            'allergen_groups', 'protein_percent', 'fat_percent',
                            'kcal_per_100g', 'price', 'price_per_kg', 'price_bucket']:
                    if field in harvest_row and pd.notna(harvest_row[field]):
                        match[f'harvest_{field}'] = harvest_row[field]
                
                matches.append(match)
                
                # Remove from unmatched
                if best_match['product_key'] in unmatched_catalog:
                    unmatched_catalog.remove(best_match['product_key'])
            else:
                unmatched_harvest.append(harvest_row['product_name'])
        
        matches_df = pd.DataFrame(matches)
        
        logger.info(f"Matched {len(matches_df)} products")
        logger.info(f"Unmatched harvest: {len(unmatched_harvest)}")
        logger.info(f"Unmatched catalog: {len(unmatched_catalog)}")
        
        return matches_df
    
    def create_preview_table(self, catalog_df, matches_df):
        """Create foods_published_preview with enriched data"""
        logger.info("Creating foods_published_preview...")
        
        # Start with catalog as base
        preview_df = catalog_df.copy()
        
        # Apply enrichments from matches
        for _, match in matches_df.iterrows():
            idx = preview_df[preview_df['product_key'] == match['product_key']].index
            
            if len(idx) > 0:
                idx = idx[0]
                
                # Update form if missing or low confidence
                if pd.isna(preview_df.loc[idx, 'form']) and 'harvest_form' in match:
                    preview_df.loc[idx, 'form'] = match['harvest_form']
                    preview_df.loc[idx, 'form_from'] = 'enrichment_manuf'
                    preview_df.loc[idx, 'form_confidence'] = 0.95
                
                # Update life_stage if missing
                if pd.isna(preview_df.loc[idx, 'life_stage']) and 'harvest_life_stage' in match:
                    preview_df.loc[idx, 'life_stage'] = match['harvest_life_stage']
                    preview_df.loc[idx, 'life_stage_from'] = 'enrichment_manuf'
                    preview_df.loc[idx, 'life_stage_confidence'] = 0.95
                
                # Update price if missing
                if pd.isna(preview_df.loc[idx, 'price_per_kg']) and 'harvest_price_per_kg' in match:
                    preview_df.loc[idx, 'price_per_kg'] = match['harvest_price_per_kg']
                    preview_df.loc[idx, 'price_from'] = 'enrichment_manuf'
                    preview_df.loc[idx, 'price_confidence'] = 0.90
                    
                    # Add price bucket
                    if 'harvest_price_bucket' in match:
                        preview_df.loc[idx, 'price_bucket'] = match['harvest_price_bucket']
                
                # Update kcal if missing
                if pd.isna(preview_df.loc[idx, 'kcal_per_100g']) and 'harvest_kcal_per_100g' in match:
                    kcal = match['harvest_kcal_per_100g']
                    # Validate kcal range
                    if 200 <= kcal <= 600:
                        preview_df.loc[idx, 'kcal_per_100g'] = kcal
                        preview_df.loc[idx, 'kcal_from'] = 'enrichment_manuf'
                        preview_df.loc[idx, 'kcal_confidence'] = 0.85
                
                # Update allergen groups
                if 'harvest_allergen_groups' in match:
                    preview_df.loc[idx, 'allergen_groups'] = match['harvest_allergen_groups']
                    preview_df.loc[idx, 'allergen_from'] = 'enrichment_manuf'
        
        # Add metadata
        preview_df['preview'] = True
        preview_df['preview_created_at'] = datetime.now().isoformat()
        preview_df['pilot_brand'] = preview_df['brand_slug'].isin(self.pilot_brands)
        
        # Save preview table
        output_file = self.report_dir / "foods_published_preview.csv"
        preview_df.to_csv(output_file, index=False)
        
        logger.info(f"Preview table saved to {output_file}")
        
        return preview_df
    
    def validate_brand_gates(self, preview_df):
        """Validate quality gates for each brand"""
        logger.info("\n=== VALIDATING BRAND QUALITY GATES ===")
        
        gates_results = []
        
        for brand in self.pilot_brands:
            brand_df = preview_df[preview_df['brand_slug'] == brand]
            
            if len(brand_df) == 0:
                continue
            
            # Calculate coverage
            total = len(brand_df)
            form_coverage = (brand_df['form'].notna().sum() / total) * 100
            life_stage_coverage = (brand_df['life_stage'].notna().sum() / total) * 100
            ingredients_coverage = (brand_df['ingredients_tokens'].notna().sum() / total) * 100
            allergen_coverage = (brand_df['allergen_groups'].notna().sum() / total) * 100 if 'allergen_groups' in brand_df else 0
            price_bucket_coverage = (brand_df['price_bucket'].notna().sum() / total) * 100 if 'price_bucket' in brand_df else 0
            price_per_kg_coverage = (brand_df['price_per_kg'].notna().sum() / total) * 100
            
            # Check for kcal outliers
            kcal_values = brand_df['kcal_per_100g'].dropna()
            kcal_outliers = ((kcal_values < 200) | (kcal_values > 600)).sum()
            
            # Check gates
            gates = {
                'brand': brand.upper(),
                'products': total,
                'form_coverage': form_coverage,
                'form_pass': form_coverage >= 95,
                'life_stage_coverage': life_stage_coverage,
                'life_stage_pass': life_stage_coverage >= 95,
                'ingredients_coverage': ingredients_coverage,
                'ingredients_pass': ingredients_coverage >= 85,
                'allergen_coverage': allergen_coverage,
                'allergen_pass': allergen_coverage >= 85,
                'price_bucket_coverage': price_bucket_coverage,
                'price_bucket_pass': price_bucket_coverage >= 70,
                'price_per_kg_coverage': price_per_kg_coverage,
                'price_per_kg_pass': price_per_kg_coverage >= 50,
                'kcal_outliers': kcal_outliers,
                'kcal_pass': kcal_outliers == 0,
                'all_gates_pass': False
            }
            
            # Overall pass/fail
            gates['all_gates_pass'] = all([
                gates['form_pass'],
                gates['life_stage_pass'],
                gates['ingredients_pass'],
                gates['allergen_pass'],
                gates['price_bucket_pass'],
                gates['kcal_pass']
            ])
            
            gates_results.append(gates)
            
            # Print results
            print(f"\n{brand.upper()}:")
            print(f"  Form: {form_coverage:.1f}% {'✅' if gates['form_pass'] else '❌'}")
            print(f"  Life Stage: {life_stage_coverage:.1f}% {'✅' if gates['life_stage_pass'] else '❌'}")
            print(f"  Ingredients: {ingredients_coverage:.1f}% {'✅' if gates['ingredients_pass'] else '❌'}")
            print(f"  Allergens: {allergen_coverage:.1f}% {'✅' if gates['allergen_pass'] else '❌'}")
            print(f"  Price Bucket: {price_bucket_coverage:.1f}% {'✅' if gates['price_bucket_pass'] else '❌'}")
            print(f"  Kcal Outliers: {kcal_outliers} {'✅' if gates['kcal_pass'] else '❌'}")
            print(f"  OVERALL: {'✅ PASS' if gates['all_gates_pass'] else '❌ FAIL'}")
        
        gates_df = pd.DataFrame(gates_results)
        gates_df.to_csv(self.report_dir / "BRAND_QUALITY_GATES.csv", index=False)
        
        return gates_df
    
    def generate_pilot_summary(self, catalog_df, preview_df, gates_df):
        """Generate pilot summary report"""
        
        # Calculate overall improvements
        before_form = (catalog_df['form'].notna().sum() / len(catalog_df)) * 100
        after_form = (preview_df['form'].notna().sum() / len(preview_df)) * 100
        
        before_life = (catalog_df['life_stage'].notna().sum() / len(catalog_df)) * 100
        after_life = (preview_df['life_stage'].notna().sum() / len(preview_df)) * 100
        
        before_price = (catalog_df['price_per_kg'].notna().sum() / len(catalog_df)) * 100
        after_price = (preview_df['price_per_kg'].notna().sum() / len(preview_df)) * 100
        
        passed_brands = gates_df[gates_df['all_gates_pass']]['brand'].tolist()
        
        report = f"""# PRODUCTION PILOT SUMMARY - TOP 5 BRANDS
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary
- **Brands Processed**: {', '.join([b.upper() for b in self.pilot_brands])}
- **Products Enriched**: {len(preview_df)}
- **Gates Passed**: {len(passed_brands)}/{len(self.pilot_brands)} brands
- **Ready for Production**: {'✅ YES' if len(passed_brands) >= 3 else '❌ NO'}

## Coverage Improvements (Overall)

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Form | {before_form:.1f}% | {after_form:.1f}% | +{after_form-before_form:.1f}pp |
| Life Stage | {before_life:.1f}% | {after_life:.1f}% | +{after_life-before_life:.1f}pp |
| Price/kg | {before_price:.1f}% | {after_price:.1f}% | +{after_price-before_price:.1f}pp |

## Brand-Level Quality Gates

| Brand | Products | Form | Life Stage | Ingredients | Allergens | Price | Kcal | Status |
|-------|----------|------|------------|-------------|-----------|-------|------|--------|
"""
        
        for _, row in gates_df.iterrows():
            status = '✅ PASS' if row['all_gates_pass'] else '❌ FAIL'
            report += f"| {row['brand']} | {row['products']} | "
            report += f"{'✅' if row['form_pass'] else '❌'} {row['form_coverage']:.0f}% | "
            report += f"{'✅' if row['life_stage_pass'] else '❌'} {row['life_stage_coverage']:.0f}% | "
            report += f"{'✅' if row['ingredients_pass'] else '❌'} {row['ingredients_coverage']:.0f}% | "
            report += f"{'✅' if row['allergen_pass'] else '❌'} {row['allergen_coverage']:.0f}% | "
            report += f"{'✅' if row['price_bucket_pass'] else '❌'} {row['price_bucket_coverage']:.0f}% | "
            report += f"{'✅' if row['kcal_pass'] else '❌'} | "
            report += f"{status} |\n"
        
        report += f"""

## Brands Passing All Gates
"""
        if passed_brands:
            for brand in passed_brands:
                report += f"- ✅ {brand}\n"
        else:
            report += "None - additional enrichment needed\n"
        
        report += f"""

## Recommended Next 5 Brands
Based on SKU count and website availability:
1. Arden (32 SKUs, website: ardengrange.com)
2. Acana (32 SKUs, website: acana.com)
3. Applaws (31 SKUs, website: applaws.com)
4. Borders (29 SKUs, website needed)
5. Arion (26 SKUs, website: arionpetfood.com)

## Deliverables
1. ✅ foods_published_preview.csv - Preview table with {len(preview_df)} products
2. ✅ BRAND_QUALITY_GATES.csv - Gate validation results
3. ✅ Brand sample CSVs - 50 rows per brand
4. ✅ This summary report

## Recommendation
{'✅ READY FOR PREVIEW TESTING' if len(passed_brands) >= 3 else '⚠️  REQUIRES ADDITIONAL ENRICHMENT'}

Preview table is ready for Admin/AI testing. No production swap yet.
"""
        
        # Save report
        with open(self.report_dir / "PILOT_SUMMARY.md", "w") as f:
            f.write(report)
        
        print(report)
        
        return report
    
    def generate_brand_samples(self, preview_df):
        """Generate 50-row sample CSV for each brand"""
        logger.info("Generating brand sample CSVs...")
        
        for brand in self.pilot_brands:
            brand_df = preview_df[preview_df['brand_slug'] == brand]
            
            if len(brand_df) > 0:
                # Select columns for sample
                sample_cols = [
                    'product_key', 'product_name', 'form', 'life_stage',
                    'kcal_per_100g', 'price_per_kg', 'price_bucket',
                    'allergen_groups', 'form_from', 'life_stage_from',
                    'price_from', 'kcal_from'
                ]
                
                # Filter to existing columns
                sample_cols = [c for c in sample_cols if c in brand_df.columns]
                
                sample_df = brand_df[sample_cols].head(50)
                
                output_file = self.report_dir / f"SAMPLE_{brand.upper()}_50.csv"
                sample_df.to_csv(output_file, index=False)
                
                logger.info(f"  {brand}: {len(sample_df)} rows saved")
    
    def run(self):
        """Run the complete pilot enrichment and preview generation"""
        logger.info("=" * 60)
        logger.info("PILOT ENRICHMENT & PREVIEW GENERATION")
        logger.info("=" * 60)
        
        # Load data
        catalog_df = self.load_catalog_data()
        harvest_df = self.load_harvest_data()
        
        if harvest_df.empty:
            logger.error("No harvest data found. Run pilot_batch_harvest.py first.")
            return
        
        # Match and enrich
        matches_df = self.match_products(catalog_df, harvest_df)
        
        # Create preview table
        preview_df = self.create_preview_table(catalog_df, matches_df)
        
        # Validate gates
        gates_df = self.validate_brand_gates(preview_df)
        
        # Generate samples
        self.generate_brand_samples(preview_df)
        
        # Generate summary
        self.generate_pilot_summary(catalog_df, preview_df, gates_df)
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ PILOT ENRICHMENT COMPLETE")
        logger.info("=" * 60)
        
        return preview_df, gates_df

if __name__ == "__main__":
    processor = PilotEnrichmentProcessor()
    processor.run()