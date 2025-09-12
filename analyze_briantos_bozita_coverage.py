#!/usr/bin/env python3
"""
Production Coverage Analysis for Briantos and Bozita Brands
Analyzes production coverage metrics for specified brands using production tables.
"""

import os
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv
import pandas as pd
import json

load_dotenv()

class BrandCoverageAnalyzer:
    def __init__(self):
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase: Client = create_client(url, key)
        self.timestamp = datetime.now()
        
        # Target brands for analysis
        self.target_brands = ['briantos', 'bozita']
        
        print("="*80)
        print("PRODUCTION COVERAGE ANALYSIS: BRIANTOS & BOZITA")
        print("="*80)
        print(f"Timestamp: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print("Target brands: {}, {}".format(*self.target_brands))
        print("="*80)
    
    def get_brand_production_data(self, brand_slug):
        """Get production data for a specific brand"""
        try:
            # Use foods_published_prod for individual SKU data
            response = self.supabase.table('foods_published_prod').select("*").eq('brand_slug', brand_slug).execute()
            if response.data:
                print(f"✅ Found {len(response.data)} records in foods_published_prod for {brand_slug}")
                return response.data
            
            print(f"⚠️ No data found for {brand_slug} in production tables")
            return []
            
        except Exception as e:
            print(f"❌ Error fetching data for {brand_slug}: {e}")
            return []
    
    def analyze_coverage(self, brand_data, brand_slug):
        """Analyze coverage metrics for a brand"""
        if not brand_data:
            return {
                'brand_slug': brand_slug,
                'total_skus': 0,
                'coverage': {},
                'missing_skus': {},
                'suspected_reasons': {}
            }
        
        total_skus = len(brand_data)
        
        # Calculate coverage for each field
        coverage_metrics = {}
        missing_skus = {}
        
        # Ingredients tokens coverage (non-empty)
        ingredients_valid = []
        ingredients_missing = []
        for item in brand_data:
            sku_id = item.get('product_key') or item.get('name_slug')  # Use product_key as ID
            ingredients_tokens = item.get('ingredients_tokens')
            # Check if ingredients_tokens is a non-empty list
            if ingredients_tokens and isinstance(ingredients_tokens, list) and len(ingredients_tokens) > 0:
                ingredients_valid.append(sku_id)
            else:
                ingredients_missing.append(sku_id)
        
        coverage_metrics['ingredients_tokens'] = len(ingredients_valid) / total_skus * 100 if total_skus > 0 else 0
        missing_skus['ingredients_tokens'] = ingredients_missing[:25]
        
        # Form coverage
        form_valid = []
        form_missing = []
        for item in brand_data:
            sku_id = item.get('product_key') or item.get('name_slug')
            form = item.get('form')
            if form and form.strip():
                form_valid.append(sku_id)
            else:
                form_missing.append(sku_id)
        
        coverage_metrics['form'] = len(form_valid) / total_skus * 100 if total_skus > 0 else 0
        missing_skus['form'] = form_missing[:25]
        
        # Life stage coverage
        life_stage_valid = []
        life_stage_missing = []
        for item in brand_data:
            sku_id = item.get('product_key') or item.get('name_slug')
            life_stage = item.get('life_stage')
            if life_stage and life_stage.strip():
                life_stage_valid.append(sku_id)
            else:
                life_stage_missing.append(sku_id)
        
        coverage_metrics['life_stage'] = len(life_stage_valid) / total_skus * 100 if total_skus > 0 else 0
        missing_skus['life_stage'] = life_stage_missing[:25]
        
        # Kcal valid range (100-800)
        kcal_valid = []
        kcal_missing = []
        for item in brand_data:
            sku_id = item.get('product_key') or item.get('name_slug')
            kcal = item.get('kcal_per_100g')
            if kcal and isinstance(kcal, (int, float)) and 100 <= kcal <= 800:
                kcal_valid.append(sku_id)
            else:
                kcal_missing.append(sku_id)
        
        coverage_metrics['kcal_valid_range'] = len(kcal_valid) / total_skus * 100 if total_skus > 0 else 0
        missing_skus['kcal_valid_range'] = kcal_missing[:25]
        
        # Calculate "food-ready" count (meets all gates)
        food_ready_count = 0
        for item in brand_data:
            ingredients_tokens = item.get('ingredients_tokens')
            form = item.get('form')
            life_stage = item.get('life_stage')
            kcal = item.get('kcal_per_100g')
            
            ingredients_ok = ingredients_tokens and isinstance(ingredients_tokens, list) and len(ingredients_tokens) > 0
            form_ok = form and form.strip()
            life_stage_ok = life_stage and life_stage.strip()
            kcal_ok = kcal and isinstance(kcal, (int, float)) and 100 <= kcal <= 800
            
            if ingredients_ok and form_ok and life_stage_ok and kcal_ok:
                food_ready_count += 1
        
        # Analyze suspected reasons for missing data
        suspected_reasons = self.analyze_missing_reasons(brand_data, brand_slug)
        
        return {
            'brand_slug': brand_slug,
            'total_skus': total_skus,
            'food_ready_count': food_ready_count,
            'coverage': coverage_metrics,
            'missing_skus': missing_skus,
            'suspected_reasons': suspected_reasons
        }
    
    def analyze_missing_reasons(self, brand_data, brand_slug):
        """Analyze suspected reasons for missing data"""
        reasons = {
            'ingredients_tokens': {},
            'form': {},
            'life_stage': {},
            'kcal_valid_range': {}
        }
        
        for item in brand_data:
            # Check for snapshot vs parser issues
            has_url = bool(item.get('product_url'))
            sources = item.get('sources', {})
            has_html_snapshot = 'manufacturer_harvest' in sources if isinstance(sources, dict) else False
            has_pdf_only = False  # We'll assume PDF detection based on source type
            
            # Ingredients tokens analysis  
            ingredients_tokens = item.get('ingredients_tokens')
            if not (ingredients_tokens and isinstance(ingredients_tokens, list) and len(ingredients_tokens) > 0):
                if has_html_snapshot and not ingredients_tokens:
                    reasons['ingredients_tokens']['snapshot_exists_parser_no_match'] = reasons['ingredients_tokens'].get('snapshot_exists_parser_no_match', 0) + 1
                elif has_pdf_only:
                    reasons['ingredients_tokens']['pdf_only'] = reasons['ingredients_tokens'].get('pdf_only', 0) + 1
                elif not has_html_snapshot:
                    reasons['ingredients_tokens']['no_snapshot'] = reasons['ingredients_tokens'].get('no_snapshot', 0) + 1
                else:
                    reasons['ingredients_tokens']['unknown'] = reasons['ingredients_tokens'].get('unknown', 0) + 1
            
            # Form analysis
            form = item.get('form')
            if not (form and form.strip()):
                if has_html_snapshot:
                    reasons['form']['snapshot_exists_parser_no_match'] = reasons['form'].get('snapshot_exists_parser_no_match', 0) + 1
                elif has_pdf_only:
                    reasons['form']['pdf_only'] = reasons['form'].get('pdf_only', 0) + 1
                else:
                    reasons['form']['no_snapshot'] = reasons['form'].get('no_snapshot', 0) + 1
            
            # Life stage analysis
            life_stage = item.get('life_stage')
            if not (life_stage and life_stage.strip()):
                if has_html_snapshot:
                    reasons['life_stage']['snapshot_exists_parser_no_match'] = reasons['life_stage'].get('snapshot_exists_parser_no_match', 0) + 1
                elif has_pdf_only:
                    reasons['life_stage']['pdf_only'] = reasons['life_stage'].get('pdf_only', 0) + 1
                else:
                    reasons['life_stage']['no_snapshot'] = reasons['life_stage'].get('no_snapshot', 0) + 1
            
            # Kcal analysis
            kcal = item.get('kcal_per_100g')
            if not (kcal and isinstance(kcal, (int, float)) and 100 <= kcal <= 800):
                if has_html_snapshot:
                    reasons['kcal_valid_range']['snapshot_exists_parser_no_match'] = reasons['kcal_valid_range'].get('snapshot_exists_parser_no_match', 0) + 1
                elif has_pdf_only:
                    reasons['kcal_valid_range']['pdf_only'] = reasons['kcal_valid_range'].get('pdf_only', 0) + 1
                else:
                    reasons['kcal_valid_range']['no_snapshot'] = reasons['kcal_valid_range'].get('no_snapshot', 0) + 1
        
        return reasons
    
    def generate_detailed_report(self, all_results):
        """Generate detailed coverage report"""
        
        print("\n" + "="*80)
        print("DETAILED COVERAGE ANALYSIS")
        print("="*80)
        
        for result in all_results:
            brand = result['brand_slug']
            total = result['total_skus']
            food_ready = result['food_ready_count']
            coverage = result['coverage']
            
            print(f"\n🔍 {brand.upper()} ANALYSIS")
            print("-" * 50)
            print(f"Total SKUs: {total}")
            print(f"Food-ready SKUs: {food_ready} ({food_ready/total*100:.1f}% if total > 0 else 0)")
            
            print("\nCoverage Metrics:")
            for field, percentage in coverage.items():
                print(f"  {field}: {percentage:.1f}%")
            
            print("\nMissing SKU Samples (max 25 per field):")
            for field, missing_list in result['missing_skus'].items():
                if missing_list:
                    print(f"  {field}: {len(missing_list)} missing")
                    print(f"    Sample IDs: {missing_list[:10]}")
            
            print("\nSuspected Reasons for Missing Data:")
            for field, reasons in result['suspected_reasons'].items():
                if reasons:
                    print(f"  {field}:")
                    for reason, count in reasons.items():
                        print(f"    {reason}: {count}")
        
        return self.format_structured_output(all_results)
    
    def format_structured_output(self, all_results):
        """Format results as structured data"""
        
        structured_data = {
            'timestamp': self.timestamp.isoformat(),
            'analysis_summary': {
                'target_brands': self.target_brands,
                'total_analyzed': len(all_results)
            },
            'brand_results': {}
        }
        
        for result in all_results:
            brand = result['brand_slug']
            structured_data['brand_results'][brand] = {
                'total_skus': result['total_skus'],
                'food_ready_count': result['food_ready_count'],
                'food_ready_percentage': result['food_ready_count'] / result['total_skus'] * 100 if result['total_skus'] > 0 else 0,
                'coverage_percentages': result['coverage'],
                'problematic_skus': {
                    field: {
                        'count': len(missing_list),
                        'sample_ids': missing_list[:25]
                    }
                    for field, missing_list in result['missing_skus'].items()
                },
                'suspected_reasons': result['suspected_reasons']
            }
        
        return structured_data

def main():
    analyzer = BrandCoverageAnalyzer()
    
    print("\n🔄 Fetching production data...")
    
    all_results = []
    
    for brand_slug in analyzer.target_brands:
        print(f"\n📊 Analyzing {brand_slug}...")
        
        # Get production data
        brand_data = analyzer.get_brand_production_data(brand_slug)
        
        # Analyze coverage
        result = analyzer.analyze_coverage(brand_data, brand_slug)
        all_results.append(result)
    
    # Generate detailed report
    structured_data = analyzer.generate_detailed_report(all_results)
    
    print("\n" + "="*80)
    print("STRUCTURED OUTPUT")
    print("="*80)
    print(json.dumps(structured_data, indent=2))
    
    print("\n✅ Analysis complete!")

if __name__ == "__main__":
    main()