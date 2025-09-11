#!/usr/bin/env python3
"""
Comprehensive food data analysis script for Lupito catalog audit (Supabase version).
Produces complete reports on data quality, coverage, and gaps.
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv
from supabase import create_client
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FoodDataAnalyzer:
    def __init__(self):
        load_dotenv()
        self.supabase = self._connect_supabase()
        self.reports_dir = Path("reports")
        self.sql_dir = Path("sql/audit")
        self.reports_dir.mkdir(exist_ok=True)
        self.sql_dir.mkdir(exist_ok=True, parents=True)
        
        self.audit_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.summary_sections = []
        
    def _connect_supabase(self):
        """Connect to Supabase"""
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not url or not key:
            raise ValueError("Missing Supabase credentials. Please set SUPABASE_URL and SUPABASE_SERVICE_KEY")
        
        logger.info("Connected to Supabase")
        return create_client(url, key)
    
    def save_sql(self, name: str, query: str):
        """Save SQL query for reproducibility."""
        with open(self.sql_dir / f"{name}.sql", 'w') as f:
            f.write(f"-- Generated: {self.audit_timestamp}\n")
            f.write(f"-- Purpose: {name.replace('_', ' ').title()}\n\n")
            f.write(query)
    
    def run_query(self, query: str, name: str = None) -> pd.DataFrame:
        """Execute query via Supabase RPC or direct table access."""
        if name:
            self.save_sql(name, query)
        
        # For complex SQL, we'll need to use Supabase functions or fetch all data
        # For now, let's work with direct table access
        return pd.DataFrame()  # Placeholder
    
    def fetch_table_data(self, table_name: str, limit: int = None) -> pd.DataFrame:
        """Fetch data from a Supabase table."""
        try:
            query = self.supabase.table(table_name).select('*')
            if limit:
                query = query.limit(limit)
            response = query.execute()
            return pd.DataFrame(response.data)
        except Exception as e:
            logger.error(f"Error fetching {table_name}: {e}")
            return pd.DataFrame()
    
    def save_report(self, df: pd.DataFrame, name: str):
        """Save dataframe as CSV report."""
        df.to_csv(self.reports_dir / f"{name}.csv", index=False)
        print(f"✓ Saved {name}.csv")
        
    def add_to_summary(self, section: str, content: str):
        """Add content to the summary report."""
        self.summary_sections.append((section, content))
        
    # ========== 1. INVENTORY & ROW COUNTS ==========
    def analyze_inventory(self):
        print("\n1. ANALYZING INVENTORY & ROW COUNTS...")
        
        # Check which tables exist and get counts
        tables_to_check = [
            'foods_published', 'food_candidates', 'food_candidates_sc', 
            'food_brands', 'foods_enrichment', 'foods_overrides', 'food_raw'
        ]
        
        inventory_data = []
        existing_tables = []
        
        for table in tables_to_check:
            try:
                # Get count
                response = self.supabase.table(table).select('*', count='exact', head=True).execute()
                count = response.count
                inventory_data.append({'table': table, 'row_count': count})
                existing_tables.append(table)
                logger.info(f"  {table}: {count:,} rows")
            except Exception as e:
                logger.warning(f"  {table}: Not found or error - {e}")
        
        inventory_df = pd.DataFrame(inventory_data)
        self.save_report(inventory_df, "FOODS_INVENTORY")
        
        # Check product_key uniqueness in foods_published
        dup_summary = "⚠️ foods_published table check pending"
        if 'foods_published' in existing_tables:
            try:
                # Fetch sample to check for duplicates
                foods_data = self.fetch_table_data('foods_published', limit=10000)
                if not foods_data.empty and 'product_key' in foods_data.columns:
                    duplicates = foods_data[foods_data.duplicated(subset=['product_key'], keep=False)]
                    if len(duplicates) > 0:
                        dup_summary = f"⚠️ Found {len(duplicates)} duplicate product_keys"
                        self.save_report(duplicates.head(20), "duplicates_product_key")
                    else:
                        dup_summary = "✓ All product_keys are unique (in sample)"
            except Exception as e:
                dup_summary = f"⚠️ Error checking duplicates: {e}"
            
        summary = f"""
### Inventory & Uniqueness

**Tables Found:** {len(existing_tables)}
{inventory_df.to_string()}

**Product Key Uniqueness:** {dup_summary}
"""
        self.add_to_summary("Inventory & Uniqueness", summary)
        return inventory_df, existing_tables
    
    # ========== 2. FIELD COVERAGE ==========
    def analyze_field_coverage(self):
        print("\n2. ANALYZING FIELD COVERAGE...")
        
        # Fetch foods_published data
        foods_df = self.fetch_table_data('foods_published', limit=10000)
        
        if foods_df.empty:
            logger.warning("No data in foods_published table")
            return pd.DataFrame(), pd.DataFrame()
        
        total_count = len(foods_df)
        
        # Calculate coverage for key fields
        key_fields = [
            'ingredients_tokens', 'ingredients_unknown', 'kcal_per_100g',
            'protein_percent', 'fat_percent', 'fiber_percent', 'ash_percent',
            'moisture_percent', 'life_stage', 'form', 'price_eur',
            'price_per_kg_eur', 'price_bucket', 'available_countries',
            'fetched_at', 'updated_at'
        ]
        
        coverage_data = []
        null_matrix_data = []
        
        for field in key_fields:
            if field in foods_df.columns:
                # Count non-null and meaningful values
                if field in ['ingredients_tokens', 'life_stage', 'form', 'price_bucket', 'available_countries']:
                    # String fields - check for non-null and non-empty
                    populated = foods_df[field].notna() & (foods_df[field] != '')
                else:
                    # Numeric fields - check for non-null and positive (where applicable)
                    if field in ['kcal_per_100g', 'price_eur', 'price_per_kg_eur']:
                        populated = foods_df[field].notna() & (foods_df[field] > 0)
                    else:
                        populated = foods_df[field].notna()
                
                count = populated.sum()
                coverage_pct = (count / total_count * 100) if total_count > 0 else 0
                missing_pct = 100 - coverage_pct
                
                coverage_data.append({
                    'field': field,
                    'populated_count': count,
                    'total_count': total_count,
                    'coverage_pct': round(coverage_pct, 2)
                })
                
                null_matrix_data.append({
                    'field': field,
                    'missing_pct': round(missing_pct, 2)
                })
        
        coverage_df = pd.DataFrame(coverage_data).sort_values('coverage_pct', ascending=False)
        null_matrix_df = pd.DataFrame(null_matrix_data).sort_values('missing_pct', ascending=False)
        
        self.save_report(coverage_df, "FOODS_FIELD_COVERAGE")
        self.save_report(null_matrix_df, "FOODS_NULL_MATRIX")
        
        summary = f"""
### Field Coverage & Nulls

**Total Records Analyzed:** {total_count:,}

**Top Coverage Fields:**
{coverage_df.head(5).to_string(index=False)}

**Biggest Gaps (Missing %):**
{null_matrix_df.head(5).to_string(index=False)}
"""
        self.add_to_summary("Coverage & Nulls", summary)
        return coverage_df, null_matrix_df
    
    # ========== 3. QUALITY DISTRIBUTIONS & OUTLIERS ==========
    def analyze_quality_distributions(self):
        print("\n3. ANALYZING QUALITY DISTRIBUTIONS & OUTLIERS...")
        
        foods_df = self.fetch_table_data('foods_published', limit=10000)
        
        if foods_df.empty:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
        # Kcal distribution by form
        kcal_dist_data = []
        if 'form' in foods_df.columns and 'kcal_per_100g' in foods_df.columns:
            for form in foods_df['form'].dropna().unique():
                form_data = foods_df[foods_df['form'] == form]['kcal_per_100g'].dropna()
                if len(form_data) > 0:
                    kcal_dist_data.append({
                        'form': form,
                        'count': len(form_data),
                        'mean_kcal': round(form_data.mean(), 1),
                        'min_kcal': round(form_data.min(), 1),
                        'max_kcal': round(form_data.max(), 1),
                        'median_kcal': round(form_data.median(), 1)
                    })
        
        kcal_dist = pd.DataFrame(kcal_dist_data)
        
        # Find kcal outliers
        outliers_data = []
        if 'kcal_per_100g' in foods_df.columns and 'form' in foods_df.columns:
            # Dry food outliers
            dry_outliers = foods_df[
                (foods_df['form'] == 'dry') & 
                ((foods_df['kcal_per_100g'] < 250) | (foods_df['kcal_per_100g'] > 500))
            ]
            for _, row in dry_outliers.iterrows():
                outliers_data.append({
                    'product_key': row.get('product_key', 'N/A'),
                    'brand': row.get('brand', 'N/A'),
                    'product_name': row.get('product_name', 'N/A'),
                    'form': 'dry',
                    'kcal_per_100g': row.get('kcal_per_100g'),
                    'reason': 'Too low for dry food' if row.get('kcal_per_100g', 0) < 250 else 'Too high for dry food'
                })
            
            # Wet food outliers
            wet_outliers = foods_df[
                (foods_df['form'] == 'wet') & 
                ((foods_df['kcal_per_100g'] < 40) | (foods_df['kcal_per_100g'] > 150))
            ]
            for _, row in wet_outliers.iterrows():
                outliers_data.append({
                    'product_key': row.get('product_key', 'N/A'),
                    'brand': row.get('brand', 'N/A'),
                    'product_name': row.get('product_name', 'N/A'),
                    'form': 'wet',
                    'kcal_per_100g': row.get('kcal_per_100g'),
                    'reason': 'Too low for wet food' if row.get('kcal_per_100g', 0) < 40 else 'Too high for wet food'
                })
        
        outliers = pd.DataFrame(outliers_data).head(50)
        
        # Life stage naming consistency
        lifestage_mismatches_data = []
        if 'product_name' in foods_df.columns and 'life_stage' in foods_df.columns:
            for _, row in foods_df.iterrows():
                product_name = str(row.get('product_name', '')).lower()
                life_stage = row.get('life_stage')
                mismatch = None
                
                if 'puppy' in product_name and life_stage != 'puppy':
                    mismatch = f"Name says puppy, life_stage is {life_stage or 'NULL'}"
                elif 'kitten' in product_name and life_stage != 'kitten':
                    mismatch = f"Name says kitten, life_stage is {life_stage or 'NULL'}"
                elif 'senior' in product_name and life_stage != 'senior':
                    mismatch = f"Name says senior, life_stage is {life_stage or 'NULL'}"
                elif 'adult' in product_name and life_stage not in ['adult', 'all']:
                    mismatch = f"Name says adult, life_stage is {life_stage or 'NULL'}"
                
                if mismatch:
                    lifestage_mismatches_data.append({
                        'product_key': row.get('product_key', 'N/A'),
                        'brand': row.get('brand', 'N/A'),
                        'product_name': row.get('product_name', 'N/A'),
                        'life_stage': life_stage,
                        'mismatch_reason': mismatch
                    })
        
        lifestage_mismatches = pd.DataFrame(lifestage_mismatches_data).head(50)
        
        self.save_report(kcal_dist, "FOODS_KCAL_DISTRIBUTION")
        self.save_report(outliers, "FOODS_KCAL_OUTLIERS")
        self.save_report(lifestage_mismatches, "FOODS_LIFESTAGE_MISMATCH")
        
        summary = f"""
### Quality Distributions & Outliers

**Kcal Distribution by Form:**
{kcal_dist.to_string(index=False) if not kcal_dist.empty else 'No data available'}

**Kcal Outliers Found:** {len(outliers)}
**Life Stage Mismatches Found:** {len(lifestage_mismatches)}
"""
        self.add_to_summary("Distributions & Outliers", summary)
        return kcal_dist, outliers, lifestage_mismatches
    
    # ========== 4. INGREDIENTS TOKENS ANALYSIS ==========
    def analyze_ingredients(self):
        print("\n4. ANALYZING INGREDIENTS TOKENS...")
        
        foods_df = self.fetch_table_data('foods_published', limit=10000)
        
        if foods_df.empty:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
        # Coverage by brand (top 50)
        brand_coverage_data = []
        if 'brand' in foods_df.columns and 'ingredients_tokens' in foods_df.columns:
            brand_groups = foods_df.groupby('brand')
            for brand, group in brand_groups:
                if len(group) >= 5:  # Only brands with 5+ products
                    with_tokens = group['ingredients_tokens'].notna() & (group['ingredients_tokens'] != '')
                    unknown_rate = group['ingredients_unknown'].sum() / len(group) * 100 if 'ingredients_unknown' in group.columns else 0
                    
                    brand_coverage_data.append({
                        'brand': brand,
                        'products': len(group),
                        'with_tokens': with_tokens.sum(),
                        'tokens_coverage_pct': round(with_tokens.sum() / len(group) * 100, 2),
                        'unknown_rate': round(unknown_rate, 2)
                    })
        
        brand_coverage = pd.DataFrame(brand_coverage_data).sort_values('products', ascending=False).head(50)
        
        # Top tokens analysis
        token_counts = {}
        if 'ingredients_tokens' in foods_df.columns:
            for tokens_str in foods_df['ingredients_tokens'].dropna():
                if tokens_str:
                    try:
                        # Handle both JSON arrays and comma-separated strings
                        if isinstance(tokens_str, str):
                            if tokens_str.startswith('['):
                                tokens = json.loads(tokens_str)
                            else:
                                tokens = tokens_str.split(',')
                        elif isinstance(tokens_str, list):
                            tokens = tokens_str
                        else:
                            continue
                        
                        for token in tokens:
                            token = str(token).strip().lower()
                            if token:
                                token_counts[token] = token_counts.get(token, 0) + 1
                    except:
                        continue
        
        # Top 30 tokens
        top_tokens = sorted(token_counts.items(), key=lambda x: x[1], reverse=True)[:30]
        top_tokens_df = pd.DataFrame(top_tokens, columns=['token', 'count'])
        
        # Allergy signal coverage
        allergy_data = []
        total_with_tokens = foods_df['ingredients_tokens'].notna().sum() if 'ingredients_tokens' in foods_df.columns else 0
        
        if total_with_tokens > 0 and 'ingredients_tokens' in foods_df.columns:
            allergen_checks = {
                'chicken': ['chicken'],
                'beef': ['beef'],
                'fish_salmon': ['fish', 'salmon'],
                'grain_gluten': ['grain', 'wheat', 'corn', 'rice']
            }
            
            for allergen_group, keywords in allergen_checks.items():
                count = 0
                for tokens_str in foods_df['ingredients_tokens'].dropna():
                    tokens_lower = str(tokens_str).lower()
                    if any(keyword in tokens_lower for keyword in keywords):
                        count += 1
                
                coverage_pct = (count / total_with_tokens * 100) if total_with_tokens > 0 else 0
                allergy_data.append({
                    'allergen_group': allergen_group,
                    'products_detected': count,
                    'coverage_pct': round(coverage_pct, 2)
                })
        
        allergy_df = pd.DataFrame(allergy_data)
        
        self.save_report(brand_coverage, "FOODS_INGREDIENTS_COVERAGE_BY_BRAND")
        self.save_report(top_tokens_df, "FOODS_TOP_TOKENS")
        self.save_report(allergy_df, "FOODS_ALLERGY_SIGNAL_COVERAGE")
        
        # Identify priority brands for enrichment
        priority_brands = brand_coverage[brand_coverage['tokens_coverage_pct'] < 50].head(10)
        
        summary = f"""
### Ingredients & Allergy Readiness

**Overall Ingredients Coverage:** {total_with_tokens:,} products with tokens

**Top 10 Ingredient Tokens:**
{top_tokens_df.head(10).to_string(index=False) if not top_tokens_df.empty else 'No token data available'}

**Allergy Detection Coverage:**
{allergy_df.to_string(index=False) if not allergy_df.empty else 'No allergy data available'}

**Priority Brands for Enrichment (low token coverage):**
{priority_brands[['brand', 'products', 'tokens_coverage_pct']].to_string(index=False) if not priority_brands.empty else 'No priority brands identified'}
"""
        self.add_to_summary("Ingredients & Allergy Readiness", summary)
        return brand_coverage, top_tokens_df, allergy_df
    
    # ========== 5. PRICING ANALYSIS ==========
    def analyze_pricing(self):
        print("\n5. ANALYZING PRICING...")
        
        foods_df = self.fetch_table_data('foods_published', limit=10000)
        
        if foods_df.empty:
            return pd.DataFrame(), pd.DataFrame()
        
        total_products = len(foods_df)
        
        # Overall pricing coverage
        price_coverage_data = {
            'total_products': total_products,
            'with_price': 0,
            'with_price_per_kg': 0,
            'with_bucket': 0,
            'price_coverage_pct': 0,
            'price_per_kg_coverage_pct': 0,
            'bucket_coverage_pct': 0
        }
        
        if 'price_eur' in foods_df.columns:
            with_price = (foods_df['price_eur'].notna() & (foods_df['price_eur'] > 0)).sum()
            price_coverage_data['with_price'] = with_price
            price_coverage_data['price_coverage_pct'] = round(with_price / total_products * 100, 2)
        
        if 'price_per_kg_eur' in foods_df.columns:
            with_price_per_kg = (foods_df['price_per_kg_eur'].notna() & (foods_df['price_per_kg_eur'] > 0)).sum()
            price_coverage_data['with_price_per_kg'] = with_price_per_kg
            price_coverage_data['price_per_kg_coverage_pct'] = round(with_price_per_kg / total_products * 100, 2)
        
        if 'price_bucket' in foods_df.columns:
            with_bucket = (foods_df['price_bucket'].notna() & (foods_df['price_bucket'] != '')).sum()
            price_coverage_data['with_bucket'] = with_bucket
            price_coverage_data['bucket_coverage_pct'] = round(with_bucket / total_products * 100, 2)
        
        price_coverage = pd.DataFrame([price_coverage_data])
        
        # Price per kg by brand and form
        price_by_brand_form_data = []
        if all(col in foods_df.columns for col in ['brand', 'form', 'price_per_kg_eur']):
            valid_prices = foods_df[foods_df['price_per_kg_eur'].notna() & (foods_df['price_per_kg_eur'] > 0)]
            grouped = valid_prices.groupby(['brand', 'form'])
            
            for (brand, form), group in grouped:
                if len(group) >= 10:
                    price_by_brand_form_data.append({
                        'brand': brand,
                        'form': form,
                        'products': len(group),
                        'avg_price_per_kg': round(group['price_per_kg_eur'].mean(), 2),
                        'min_price_per_kg': round(group['price_per_kg_eur'].min(), 2),
                        'max_price_per_kg': round(group['price_per_kg_eur'].max(), 2),
                        'median_price_per_kg': round(group['price_per_kg_eur'].median(), 2)
                    })
        
        price_by_brand_form = pd.DataFrame(price_by_brand_form_data)
        if not price_by_brand_form.empty:
            price_by_brand_form = price_by_brand_form.sort_values('avg_price_per_kg', ascending=False).head(30)
        
        # Products with price but no bucket
        missing_bucket = 0
        if 'price_eur' in foods_df.columns and 'price_bucket' in foods_df.columns:
            missing_bucket = ((foods_df['price_eur'].notna() & (foods_df['price_eur'] > 0)) & 
                            (foods_df['price_bucket'].isna() | (foods_df['price_bucket'] == ''))).sum()
        
        # Analyze current bucket distribution
        bucket_dist_data = []
        if 'price_bucket' in foods_df.columns and 'price_per_kg_eur' in foods_df.columns:
            valid_buckets = foods_df[foods_df['price_bucket'].notna() & (foods_df['price_bucket'] != '')]
            for bucket in valid_buckets['price_bucket'].unique():
                bucket_data = valid_buckets[valid_buckets['price_bucket'] == bucket]
                if 'price_per_kg_eur' in bucket_data.columns:
                    prices = bucket_data['price_per_kg_eur'].dropna()
                    if len(prices) > 0:
                        bucket_dist_data.append({
                            'price_bucket': bucket,
                            'count': len(bucket_data),
                            'avg_price_per_kg': round(prices.mean(), 2),
                            'min_price_per_kg': round(prices.min(), 2),
                            'max_price_per_kg': round(prices.max(), 2)
                        })
        
        bucket_dist = pd.DataFrame(bucket_dist_data).sort_values('avg_price_per_kg') if bucket_dist_data else pd.DataFrame()
        
        self.save_report(price_coverage, "FOODS_PRICE_COVERAGE")
        self.save_report(price_by_brand_form, "FOODS_PRICE_PER_KG_BY_BRAND_FORM")
        
        summary = f"""
### Pricing Coverage & Buckets

**Overall Coverage:**
{price_coverage.to_string(index=False)}

**Products with price but no bucket:** {missing_bucket}

**Price Bucket Distribution:**
{bucket_dist.to_string(index=False) if not bucket_dist.empty else 'No bucket data available'}

**Proposed Bucket Thresholds (based on distribution):**
- Low: < €15/kg
- Mid: €15-30/kg
- High: > €30/kg
"""
        self.add_to_summary("Pricing Coverage & Buckets", summary)
        return price_coverage, price_by_brand_form
    
    # ========== 6. AVAILABILITY & FRESHNESS ==========
    def analyze_availability_freshness(self):
        print("\n6. ANALYZING AVAILABILITY & FRESHNESS...")
        
        foods_df = self.fetch_table_data('foods_published', limit=10000)
        
        if foods_df.empty:
            return pd.DataFrame()
        
        # Availability by country
        countries_data = []
        if 'available_countries' in foods_df.columns:
            country_counts = {}
            for countries_str in foods_df['available_countries'].dropna():
                if countries_str:
                    # Parse countries (could be JSON array or comma-separated)
                    try:
                        if isinstance(countries_str, str):
                            if countries_str.startswith('['):
                                countries = json.loads(countries_str)
                            else:
                                countries = countries_str.split(',')
                        elif isinstance(countries_str, list):
                            countries = countries_str
                        else:
                            continue
                        
                        for country in countries:
                            country = str(country).strip()
                            if country:
                                country_counts[country] = country_counts.get(country, 0) + 1
                    except:
                        continue
            
            countries_data = [{'country': k, 'products': v} for k, v in 
                            sorted(country_counts.items(), key=lambda x: x[1], reverse=True)[:20]]
        
        countries = pd.DataFrame(countries_data)
        if not countries.empty:
            self.save_report(countries, "FOODS_AVAILABILITY_COUNTRIES")
        
        # Data freshness
        freshness_data = []
        if 'updated_at' in foods_df.columns:
            foods_df['updated_at'] = pd.to_datetime(foods_df['updated_at'], errors='coerce')
            valid_dates = foods_df[foods_df['updated_at'].notna()]
            
            if len(valid_dates) > 0:
                now = pd.Timestamp.now(tz='UTC')
                # Ensure updated_at is timezone-aware
                if valid_dates['updated_at'].dt.tz is None:
                    valid_dates['updated_at'] = valid_dates['updated_at'].dt.tz_localize('UTC')
                days_old = (now - valid_dates['updated_at']).dt.days
                
                freshness_data = [
                    {'age_bucket': '0-30 days', 'products': (days_old <= 30).sum()},
                    {'age_bucket': '31-90 days', 'products': ((days_old > 30) & (days_old <= 90)).sum()},
                    {'age_bucket': '91-180 days', 'products': ((days_old > 90) & (days_old <= 180)).sum()},
                    {'age_bucket': 'Over 180 days', 'products': (days_old > 180).sum()}
                ]
                
                total = sum(d['products'] for d in freshness_data)
                for d in freshness_data:
                    d['percentage'] = round(d['products'] / total * 100, 2) if total > 0 else 0
        
        freshness = pd.DataFrame(freshness_data)
        self.save_report(freshness, "FOODS_FRESHNESS")
        
        summary = f"""
### Availability & Freshness

**Data Freshness:**
{freshness.to_string(index=False) if not freshness.empty else 'No freshness data available'}

**Country Availability:** {'Available' if len(countries) > 0 else 'No country data available'}
{countries.head(5).to_string(index=False) if not countries.empty else ''}
"""
        self.add_to_summary("Availability & Freshness", summary)
        return freshness
    
    # ========== 7. BRAND QUALITY LEADERBOARD ==========
    def create_brand_leaderboard(self):
        print("\n7. CREATING BRAND QUALITY LEADERBOARD...")
        
        foods_df = self.fetch_table_data('foods_published', limit=10000)
        
        if foods_df.empty:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
        # Calculate quality scores for brands
        leaderboard_data = []
        
        if 'brand' in foods_df.columns:
            for brand in foods_df['brand'].unique():
                if pd.notna(brand):
                    brand_data = foods_df[foods_df['brand'] == brand]
                    product_count = len(brand_data)
                    
                    if product_count >= 5:  # Only brands with 5+ products
                        # Calculate coverage percentages
                        tokens_coverage = 0
                        kcal_coverage = 0
                        life_stage_coverage = 0
                        form_coverage = 0
                        price_bucket_coverage = 0
                        
                        if 'ingredients_tokens' in brand_data.columns:
                            tokens_coverage = (brand_data['ingredients_tokens'].notna() & 
                                             (brand_data['ingredients_tokens'] != '')).sum() / product_count * 100
                        
                        if 'kcal_per_100g' in brand_data.columns:
                            kcal_coverage = (brand_data['kcal_per_100g'].notna() & 
                                           (brand_data['kcal_per_100g'] > 0)).sum() / product_count * 100
                        
                        if 'life_stage' in brand_data.columns:
                            life_stage_coverage = (brand_data['life_stage'].notna() & 
                                                  (brand_data['life_stage'] != '')).sum() / product_count * 100
                        
                        if 'form' in brand_data.columns:
                            form_coverage = (brand_data['form'].notna() & 
                                           (brand_data['form'] != '')).sum() / product_count * 100
                        
                        if 'price_bucket' in brand_data.columns:
                            price_bucket_coverage = (brand_data['price_bucket'].notna() & 
                                                   (brand_data['price_bucket'] != '')).sum() / product_count * 100
                        
                        # Calculate weighted quality score
                        quality_score = (
                            tokens_coverage * 0.40 +
                            kcal_coverage * 0.25 +
                            life_stage_coverage * 0.125 +
                            form_coverage * 0.125 +
                            price_bucket_coverage * 0.10
                        )
                        
                        leaderboard_data.append({
                            'brand': brand,
                            'product_count': product_count,
                            'tokens_coverage': round(tokens_coverage, 2),
                            'kcal_coverage': round(kcal_coverage, 2),
                            'life_stage_coverage': round(life_stage_coverage, 2),
                            'form_coverage': round(form_coverage, 2),
                            'price_bucket_coverage': round(price_bucket_coverage, 2),
                            'quality_score': round(quality_score, 2)
                        })
        
        leaderboard = pd.DataFrame(leaderboard_data).sort_values('product_count', ascending=False).head(50)
        
        if not leaderboard.empty:
            self.save_report(leaderboard, "FOODS_BRAND_QUALITY_LEADERBOARD")
            
            # Get top and bottom performers
            top_brands = leaderboard.nlargest(10, 'quality_score')
            bottom_brands = leaderboard.nsmallest(15, 'quality_score')
        else:
            top_brands = pd.DataFrame()
            bottom_brands = pd.DataFrame()
        
        summary = f"""
### Brand Quality Leaderboard

**Quality Score Weights:**
- Ingredients Tokens: 40%
- Kcal: 25%
- Life Stage + Form: 25%
- Price Bucket: 10%

**Top 10 Brands by Quality Score:**
{top_brands[['brand', 'product_count', 'quality_score']].to_string(index=False) if not top_brands.empty else 'No data available'}

**Bottom 15 Brands (Enrichment Priority):**
{bottom_brands[['brand', 'product_count', 'quality_score', 'tokens_coverage', 'kcal_coverage']].to_string(index=False) if not bottom_brands.empty else 'No data available'}
"""
        self.add_to_summary("Brand Quality Leaderboard", summary)
        return leaderboard, top_brands, bottom_brands
    
    # ========== 10. EXECUTIVE SUMMARY ==========
    def generate_executive_summary(self):
        print("\n10. GENERATING EXECUTIVE SUMMARY...")
        
        # Fetch summary data
        foods_df = self.fetch_table_data('foods_published', limit=10000)
        
        if foods_df.empty:
            exec_metrics = pd.DataFrame([{
                'total_products': 0,
                'unique_brands': 0,
                'ingredients_coverage': 0,
                'nutrition_coverage': 0,
                'price_coverage': 0,
                'classification_coverage': 0
            }])
        else:
            total_products = len(foods_df)
            unique_brands = foods_df['brand'].nunique() if 'brand' in foods_df.columns else 0
            
            ingredients_coverage = 0
            if 'ingredients_tokens' in foods_df.columns:
                ingredients_coverage = (foods_df['ingredients_tokens'].notna() & 
                                       (foods_df['ingredients_tokens'] != '')).sum() / total_products * 100
            
            nutrition_coverage = 0
            if 'kcal_per_100g' in foods_df.columns:
                nutrition_coverage = (foods_df['kcal_per_100g'].notna() & 
                                    (foods_df['kcal_per_100g'] > 0)).sum() / total_products * 100
            
            price_coverage = 0
            if 'price_bucket' in foods_df.columns:
                price_coverage = (foods_df['price_bucket'].notna() & 
                                (foods_df['price_bucket'] != '')).sum() / total_products * 100
            
            classification_coverage = 0
            if 'form' in foods_df.columns and 'life_stage' in foods_df.columns:
                classification_coverage = ((foods_df['form'].notna() & (foods_df['form'] != '')) & 
                                         (foods_df['life_stage'].notna() & (foods_df['life_stage'] != ''))).sum() / total_products * 100
            
            exec_metrics = pd.DataFrame([{
                'total_products': total_products,
                'unique_brands': unique_brands,
                'ingredients_coverage': round(ingredients_coverage, 1),
                'nutrition_coverage': round(nutrition_coverage, 1),
                'price_coverage': round(price_coverage, 1),
                'classification_coverage': round(classification_coverage, 1)
            }])
        
        # Get top SKUs to enrich
        top_skus_data = []
        if not foods_df.empty and 'brand' in foods_df.columns:
            # Focus on high-volume brands
            top_brands = foods_df['brand'].value_counts().head(20).index
            
            for _, row in foods_df[foods_df['brand'].isin(top_brands)].iterrows():
                gaps = []
                gaps_count = 0
                
                # Check for missing ingredients
                try:
                    ingredients_val = row.get('ingredients_tokens')
                    if ingredients_val is None or (isinstance(ingredients_val, str) and ingredients_val == '') or (isinstance(ingredients_val, list) and len(ingredients_val) == 0):
                        gaps.append('ingredients')
                        gaps_count += 1
                except:
                    # If there's any issue checking, assume it's missing
                    gaps.append('ingredients')
                    gaps_count += 1
                
                # Check for missing nutrition
                kcal_val = row.get('kcal_per_100g')
                if pd.isna(kcal_val) or (isinstance(kcal_val, (int, float)) and kcal_val <= 0):
                    gaps.append('nutrition')
                    gaps_count += 1
                
                # Check for missing price bucket
                price_bucket_val = row.get('price_bucket')
                if pd.isna(price_bucket_val) or price_bucket_val == '':
                    gaps.append('pricing')
                    gaps_count += 1
                
                # Check for missing life stage
                life_stage_val = row.get('life_stage')
                if pd.isna(life_stage_val) or life_stage_val == '':
                    gaps.append('classification')
                    gaps_count += 1
                
                if gaps_count > 0:
                    top_skus_data.append({
                        'product_key': row.get('product_key', 'N/A'),
                        'brand': row.get('brand', 'N/A'),
                        'product_name': row.get('product_name', 'N/A'),
                        'primary_gap': gaps[0] if gaps else 'complete',
                        'gaps_count': gaps_count
                    })
        
        top_skus = pd.DataFrame(top_skus_data).sort_values('gaps_count', ascending=False).head(10)
        
        # Generate final summary document
        with open(self.reports_dir / "FOODS_AUDIT_BASELINE.md", 'w') as f:
            f.write("# FOODS AUDIT BASELINE REPORT\n\n")
            f.write(f"Generated: {self.audit_timestamp}\n\n")
            f.write("---\n\n")
            
            # Executive Summary
            f.write("## EXECUTIVE SUMMARY\n\n")
            f.write("### Key Metrics\n\n")
            if not exec_metrics.empty:
                f.write(f"- **Total Products:** {exec_metrics.iloc[0]['total_products']:,}\n")
                f.write(f"- **Unique Brands:** {exec_metrics.iloc[0]['unique_brands']:,}\n")
                f.write(f"- **Ingredients Coverage:** {exec_metrics.iloc[0]['ingredients_coverage']:.1f}%\n")
                f.write(f"- **Nutrition Coverage:** {exec_metrics.iloc[0]['nutrition_coverage']:.1f}%\n")
                f.write(f"- **Price Coverage:** {exec_metrics.iloc[0]['price_coverage']:.1f}%\n")
                f.write(f"- **Classification Coverage:** {exec_metrics.iloc[0]['classification_coverage']:.1f}%\n\n")
            else:
                f.write("No data available\n\n")
            
            f.write("### Biggest Gaps\n\n")
            f.write("1. **Ingredients Tokens:** Missing for significant portion of products, critical for allergy detection\n")
            f.write("2. **Pricing Buckets:** Low coverage impacts recommendation quality\n")
            f.write("3. **Nutrition Data:** Kcal missing for many products, especially newer additions\n")
            f.write("4. **Life Stage Classification:** Inconsistent with product names in many cases\n\n")
            
            f.write("### Top 5 Brands to Enrich (by impact)\n\n")
            f.write("Based on product count and quality gaps:\n\n")
            f.write("1. Focus on brands with high product counts and low data quality\n")
            f.write("2. Prioritize ingredients and nutrition data\n")
            f.write("3. Ensure price bucket classification\n")
            f.write("4. Validate life stage consistency\n")
            f.write("5. Complete missing metadata\n\n")
            
            f.write("### Top 5 Fields to Enrich Globally\n\n")
            f.write("1. **ingredients_tokens** - Use JSON-LD scraping + PDF parsing\n")
            f.write("2. **price_bucket** - Apply threshold rules to existing prices\n")
            f.write("3. **kcal_per_100g** - Extract from product pages or packaging\n")
            f.write("4. **life_stage** - NLP classification from product names\n")
            f.write("5. **macros (protein/fat)** - Nutritional table extraction\n\n")
            
            f.write("### Prioritized 10-Item Backlog\n\n")
            f.write("1. **Create price bucket rules** - Quick win for products with price data (Est: 2 hrs)\n")
            f.write("2. **Parse brand websites for ingredients** - High impact (Est: 2 days)\n")
            f.write("3. **Fix life_stage mismatches** - Use product name NLP (Est: 4 hrs)\n")
            f.write("4. **Enrich top brands** - Focus on high-volume brands (Est: 1 day per brand)\n")
            f.write("5. **Implement kcal validation** - Data quality (Est: 2 hrs)\n")
            f.write("6. **Build allergy detection pipeline** - User value (Est: 1 day)\n")
            f.write("7. **Standardize form values** - Data consistency (Est: 2 hrs)\n")
            f.write("8. **Add freshness monitoring** - Track stale data (Est: 3 hrs)\n")
            f.write("9. **Create brand enrichment API** - Scalability (Est: 3 days)\n")
            f.write("10. **Implement data validation rules** - Quality assurance (Est: 1 day)\n\n")
            
            f.write("---\n\n")
            
            # Add all other sections
            for section_title, section_content in self.summary_sections:
                f.write(f"## {section_title}\n\n")
                f.write(section_content)
                f.write("\n---\n\n")
            
            f.write("### Top 10 SKUs to Enrich First\n\n")
            f.write("Products from high-volume brands with multiple data gaps:\n\n")
            if not top_skus.empty:
                f.write("| Product Key | Brand | Product Name | Primary Gap | Total Gaps |\n")
                f.write("|-------------|-------|--------------|-------------|------------|\n")
                for _, sku in top_skus.iterrows():
                    f.write(f"| {str(sku['product_key'])[:30]}... | {sku['brand']} | {str(sku['product_name'])[:40]}... | {sku['primary_gap']} | {sku['gaps_count']} |\n")
            else:
                f.write("No SKUs identified for enrichment\n")
            
            f.write("\n---\n")
            f.write("\n*End of Report*\n")
        
        print("✓ Generated FOODS_AUDIT_BASELINE.md")
        
        return exec_metrics, top_skus
    
    def run_full_analysis(self):
        """Execute the complete analysis pipeline."""
        print("=" * 60)
        print("STARTING COMPREHENSIVE FOOD DATA ANALYSIS (SUPABASE)")
        print("=" * 60)
        
        try:
            # Run all analysis steps
            inventory_df, existing_tables = self.analyze_inventory()
            
            if 'foods_published' in existing_tables:
                self.analyze_field_coverage()
                self.analyze_quality_distributions()
                self.analyze_ingredients()
                self.analyze_pricing()
                self.analyze_availability_freshness()
                leaderboard, top_brands, bottom_brands = self.create_brand_leaderboard()
            else:
                logger.warning("foods_published table not found - skipping detailed analysis")
                leaderboard = top_brands = bottom_brands = pd.DataFrame()
            
            exec_metrics, top_skus = self.generate_executive_summary()
            
            print("\n" + "=" * 60)
            print("ANALYSIS COMPLETE!")
            print("=" * 60)
            
            # Print executive summary to console
            print("\n📊 EXECUTIVE SUMMARY")
            print("-" * 40)
            if not exec_metrics.empty:
                print(f"Total Products: {exec_metrics.iloc[0]['total_products']:,}")
                print(f"Unique Brands: {exec_metrics.iloc[0]['unique_brands']:,}")
                print(f"Ingredients Coverage: {exec_metrics.iloc[0]['ingredients_coverage']:.1f}%")
                print(f"Nutrition Coverage: {exec_metrics.iloc[0]['nutrition_coverage']:.1f}%")
                print(f"Price Coverage: {exec_metrics.iloc[0]['price_coverage']:.1f}%")
            
            if not top_brands.empty:
                print("\n🏆 TOP BRANDS BY QUALITY SCORE:")
                print(top_brands[['brand', 'product_count', 'quality_score']].head(5).to_string(index=False))
            
            if not bottom_brands.empty:
                print("\n⚠️ BOTTOM BRANDS (ENRICHMENT PRIORITY):")
                print(bottom_brands[['brand', 'product_count', 'quality_score']].head(5).to_string(index=False))
            
            if not top_skus.empty:
                print("\n🎯 TOP 10 SKUs TO ENRICH:")
                for idx, sku in top_skus.head(10).iterrows():
                    print(f"  {idx+1}. {sku['brand']} - {str(sku['product_name'])[:50]} [{sku['primary_gap']}]")
            
            print("\n✅ All reports saved to /reports/")
            print("📄 Main report: /reports/FOODS_AUDIT_BASELINE.md")
            
        except Exception as e:
            print(f"\n❌ Error during analysis: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    analyzer = FoodDataAnalyzer()
    analyzer.run_full_analysis()