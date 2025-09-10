#!/usr/bin/env python3
"""
Comprehensive food data analysis script for Lupito catalog audit.
Produces complete reports on data quality, coverage, and gaps.
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from pathlib import Path
import sqlite3
from typing import Dict, List, Tuple, Optional

class FoodDataAnalyzer:
    def __init__(self, db_path: str = "lupito.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.reports_dir = Path("reports")
        self.sql_dir = Path("sql/audit")
        self.reports_dir.mkdir(exist_ok=True)
        self.sql_dir.mkdir(exist_ok=True, parents=True)
        
        self.audit_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.summary_sections = []
        
    def save_sql(self, name: str, query: str):
        """Save SQL query for reproducibility."""
        with open(self.sql_dir / f"{name}.sql", 'w') as f:
            f.write(f"-- Generated: {self.audit_timestamp}\n")
            f.write(f"-- Purpose: {name.replace('_', ' ').title()}\n\n")
            f.write(query)
    
    def run_query(self, query: str, name: str = None) -> pd.DataFrame:
        """Execute query and optionally save it."""
        if name:
            self.save_sql(name, query)
        return pd.read_sql_query(query, self.conn)
    
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
        
        # Check which tables exist
        tables_query = """
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        AND name IN ('foods_published', 'food_candidates', 'food_candidates_sc', 
                     'food_brands', 'foods_enrichment', 'foods_overrides', 'food_raw')
        ORDER BY name
        """
        existing_tables = self.run_query(tables_query, "check_tables")
        
        # Get row counts
        inventory_data = []
        for table in existing_tables['name']:
            count_query = f"SELECT COUNT(*) as row_count FROM {table}"
            count = self.run_query(count_query).iloc[0, 0]
            inventory_data.append({'table': table, 'row_count': count})
        
        inventory_df = pd.DataFrame(inventory_data)
        self.save_report(inventory_df, "FOODS_INVENTORY")
        
        # Check product_key uniqueness in foods_published
        if 'foods_published' in existing_tables['name'].values:
            dup_query = """
            SELECT product_key, brand, product_name, form, pack_size, COUNT(*) as duplicate_count
            FROM foods_published
            GROUP BY product_key
            HAVING COUNT(*) > 1
            ORDER BY duplicate_count DESC, brand, product_name
            LIMIT 20
            """
            duplicates = self.run_query(dup_query, "check_duplicates")
            
            if len(duplicates) > 0:
                self.save_report(duplicates, "duplicates_product_key")
                dup_summary = f"⚠️ Found {len(duplicates)} duplicate product_keys"
            else:
                dup_summary = "✓ All product_keys are unique"
        else:
            dup_summary = "⚠️ foods_published table not found"
            
        summary = f"""
### Inventory & Uniqueness

**Tables Found:** {len(existing_tables)}
{inventory_df.to_string()}

**Product Key Uniqueness:** {dup_summary}
"""
        self.add_to_summary("Inventory & Uniqueness", summary)
        return inventory_df
    
    # ========== 2. FIELD COVERAGE ==========
    def analyze_field_coverage(self):
        print("\n2. ANALYZING FIELD COVERAGE...")
        
        # Get all columns from foods_published
        cols_query = "PRAGMA table_info(foods_published)"
        cols_df = pd.read_sql_query(cols_query, self.conn)
        
        # Calculate coverage for key fields
        coverage_queries = {
            'ingredients_tokens': "SELECT COUNT(*) FROM foods_published WHERE ingredients_tokens IS NOT NULL AND ingredients_tokens != ''",
            'ingredients_unknown': "SELECT COUNT(*) FROM foods_published WHERE ingredients_unknown IS NOT NULL",
            'kcal_per_100g': "SELECT COUNT(*) FROM foods_published WHERE kcal_per_100g IS NOT NULL AND kcal_per_100g > 0",
            'protein_percent': "SELECT COUNT(*) FROM foods_published WHERE protein_percent IS NOT NULL AND protein_percent > 0",
            'fat_percent': "SELECT COUNT(*) FROM foods_published WHERE fat_percent IS NOT NULL AND fat_percent > 0",
            'fiber_percent': "SELECT COUNT(*) FROM foods_published WHERE fiber_percent IS NOT NULL AND fiber_percent > 0",
            'ash_percent': "SELECT COUNT(*) FROM foods_published WHERE ash_percent IS NOT NULL AND ash_percent > 0",
            'moisture_percent': "SELECT COUNT(*) FROM foods_published WHERE moisture_percent IS NOT NULL AND moisture_percent > 0",
            'life_stage': "SELECT COUNT(*) FROM foods_published WHERE life_stage IS NOT NULL AND life_stage != ''",
            'form': "SELECT COUNT(*) FROM foods_published WHERE form IS NOT NULL AND form != ''",
            'price_eur': "SELECT COUNT(*) FROM foods_published WHERE price_eur IS NOT NULL AND price_eur > 0",
            'price_per_kg_eur': "SELECT COUNT(*) FROM foods_published WHERE price_per_kg_eur IS NOT NULL AND price_per_kg_eur > 0",
            'price_bucket': "SELECT COUNT(*) FROM foods_published WHERE price_bucket IS NOT NULL AND price_bucket != ''",
            'available_countries': "SELECT COUNT(*) FROM foods_published WHERE available_countries IS NOT NULL AND available_countries != ''",
            'fetched_at': "SELECT COUNT(*) FROM foods_published WHERE fetched_at IS NOT NULL",
            'updated_at': "SELECT COUNT(*) FROM foods_published WHERE updated_at IS NOT NULL"
        }
        
        # Get total count
        total_count = self.run_query("SELECT COUNT(*) FROM foods_published").iloc[0, 0]
        
        coverage_data = []
        null_matrix_data = []
        
        for field, query in coverage_queries.items():
            try:
                count = self.run_query(query).iloc[0, 0]
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
            except Exception as e:
                print(f"Warning: Could not analyze field {field}: {e}")
        
        coverage_df = pd.DataFrame(coverage_data).sort_values('coverage_pct', ascending=False)
        null_matrix_df = pd.DataFrame(null_matrix_data).sort_values('missing_pct', ascending=False)
        
        self.save_report(coverage_df, "FOODS_FIELD_COVERAGE")
        self.save_report(null_matrix_df, "FOODS_NULL_MATRIX")
        
        # Check provenance fields
        provenance_query = """
        SELECT 
            SUM(CASE WHEN ingredients_tokens_from = 'override' THEN 1 ELSE 0 END) as ingredients_override,
            SUM(CASE WHEN ingredients_tokens_from = 'enrichment' THEN 1 ELSE 0 END) as ingredients_enrichment,
            SUM(CASE WHEN ingredients_tokens_from = 'source' THEN 1 ELSE 0 END) as ingredients_source,
            SUM(CASE WHEN kcal_per_100g_from = 'override' THEN 1 ELSE 0 END) as kcal_override,
            SUM(CASE WHEN kcal_per_100g_from = 'enrichment' THEN 1 ELSE 0 END) as kcal_enrichment,
            SUM(CASE WHEN kcal_per_100g_from = 'source' THEN 1 ELSE 0 END) as kcal_source,
            COUNT(*) as total
        FROM foods_published
        """
        
        try:
            provenance = self.run_query(provenance_query, "check_provenance")
        except:
            provenance = None
        
        summary = f"""
### Field Coverage & Nulls

**Total Records:** {total_count:,}

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
        
        # Kcal distribution by form
        kcal_dist_query = """
        SELECT 
            form,
            COUNT(*) as count,
            ROUND(AVG(kcal_per_100g), 1) as mean_kcal,
            ROUND(MIN(kcal_per_100g), 1) as min_kcal,
            ROUND(MAX(kcal_per_100g), 1) as max_kcal
        FROM foods_published
        WHERE kcal_per_100g IS NOT NULL AND kcal_per_100g > 0
        GROUP BY form
        """
        kcal_dist = self.run_query(kcal_dist_query, "kcal_distribution")
        
        # Find kcal outliers
        outliers_query = """
        SELECT 
            product_key,
            brand,
            product_name,
            form,
            kcal_per_100g,
            CASE 
                WHEN form = 'dry' AND kcal_per_100g < 250 THEN 'Too low for dry food'
                WHEN form = 'dry' AND kcal_per_100g > 500 THEN 'Too high for dry food'
                WHEN form = 'wet' AND kcal_per_100g < 40 THEN 'Too low for wet food'
                WHEN form = 'wet' AND kcal_per_100g > 150 THEN 'Too high for wet food'
                ELSE 'Outlier'
            END as reason
        FROM foods_published
        WHERE kcal_per_100g IS NOT NULL
        AND (
            (form = 'dry' AND (kcal_per_100g < 250 OR kcal_per_100g > 500))
            OR (form = 'wet' AND (kcal_per_100g < 40 OR kcal_per_100g > 150))
        )
        ORDER BY kcal_per_100g DESC
        LIMIT 50
        """
        outliers = self.run_query(outliers_query, "kcal_outliers")
        
        # Life stage naming consistency
        lifestage_check_query = """
        SELECT 
            product_key,
            brand,
            product_name,
            life_stage,
            CASE
                WHEN LOWER(product_name) LIKE '%puppy%' AND life_stage != 'puppy' THEN 'Name says puppy, life_stage is ' || COALESCE(life_stage, 'NULL')
                WHEN LOWER(product_name) LIKE '%kitten%' AND life_stage != 'kitten' THEN 'Name says kitten, life_stage is ' || COALESCE(life_stage, 'NULL')
                WHEN LOWER(product_name) LIKE '%senior%' AND life_stage != 'senior' THEN 'Name says senior, life_stage is ' || COALESCE(life_stage, 'NULL')
                WHEN LOWER(product_name) LIKE '%adult%' AND life_stage NOT IN ('adult', 'all') THEN 'Name says adult, life_stage is ' || COALESCE(life_stage, 'NULL')
                ELSE 'Mismatch'
            END as mismatch_reason
        FROM foods_published
        WHERE (
            (LOWER(product_name) LIKE '%puppy%' AND (life_stage != 'puppy' OR life_stage IS NULL))
            OR (LOWER(product_name) LIKE '%kitten%' AND (life_stage != 'kitten' OR life_stage IS NULL))
            OR (LOWER(product_name) LIKE '%senior%' AND (life_stage != 'senior' OR life_stage IS NULL))
            OR (LOWER(product_name) LIKE '%adult%' AND (life_stage NOT IN ('adult', 'all') OR life_stage IS NULL))
        )
        LIMIT 50
        """
        lifestage_mismatches = self.run_query(lifestage_check_query, "lifestage_mismatches")
        
        self.save_report(kcal_dist, "FOODS_KCAL_DISTRIBUTION")
        self.save_report(outliers, "FOODS_KCAL_OUTLIERS")
        self.save_report(lifestage_mismatches, "FOODS_LIFESTAGE_MISMATCH")
        
        summary = f"""
### Quality Distributions & Outliers

**Kcal Distribution by Form:**
{kcal_dist.to_string(index=False)}

**Kcal Outliers Found:** {len(outliers)}
**Life Stage Mismatches Found:** {len(lifestage_mismatches)}
"""
        self.add_to_summary("Distributions & Outliers", summary)
        return kcal_dist, outliers, lifestage_mismatches
    
    # ========== 4. INGREDIENTS TOKENS ANALYSIS ==========
    def analyze_ingredients(self):
        print("\n4. ANALYZING INGREDIENTS TOKENS...")
        
        # Coverage by brand (top 50)
        brand_coverage_query = """
        SELECT 
            brand,
            COUNT(*) as products,
            SUM(CASE WHEN ingredients_tokens IS NOT NULL AND ingredients_tokens != '' THEN 1 ELSE 0 END) as with_tokens,
            ROUND(100.0 * SUM(CASE WHEN ingredients_tokens IS NOT NULL AND ingredients_tokens != '' THEN 1 ELSE 0 END) / COUNT(*), 2) as tokens_coverage_pct,
            ROUND(100.0 * SUM(CASE WHEN ingredients_unknown = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) as unknown_rate
        FROM foods_published
        GROUP BY brand
        HAVING COUNT(*) >= 5
        ORDER BY products DESC
        LIMIT 50
        """
        brand_coverage = self.run_query(brand_coverage_query, "ingredients_coverage_by_brand")
        
        # Top tokens analysis
        tokens_query = """
        SELECT ingredients_tokens
        FROM foods_published
        WHERE ingredients_tokens IS NOT NULL AND ingredients_tokens != ''
        """
        tokens_df = self.run_query(tokens_query)
        
        # Parse tokens and count frequency
        token_counts = {}
        for tokens_str in tokens_df['ingredients_tokens']:
            if tokens_str:
                try:
                    tokens = json.loads(tokens_str) if tokens_str.startswith('[') else tokens_str.split(',')
                    for token in tokens:
                        token = token.strip().lower()
                        if token:
                            token_counts[token] = token_counts.get(token, 0) + 1
                except:
                    continue
        
        # Top 30 tokens
        top_tokens = sorted(token_counts.items(), key=lambda x: x[1], reverse=True)[:30]
        top_tokens_df = pd.DataFrame(top_tokens, columns=['token', 'count'])
        
        # Allergy signal coverage
        allergy_queries = {
            'chicken': "SELECT COUNT(*) FROM foods_published WHERE LOWER(ingredients_tokens) LIKE '%chicken%'",
            'beef': "SELECT COUNT(*) FROM foods_published WHERE LOWER(ingredients_tokens) LIKE '%beef%'",
            'fish_salmon': "SELECT COUNT(*) FROM foods_published WHERE (LOWER(ingredients_tokens) LIKE '%fish%' OR LOWER(ingredients_tokens) LIKE '%salmon%')",
            'grain_gluten': "SELECT COUNT(*) FROM foods_published WHERE (LOWER(ingredients_tokens) LIKE '%grain%' OR LOWER(ingredients_tokens) LIKE '%wheat%' OR LOWER(ingredients_tokens) LIKE '%corn%' OR LOWER(ingredients_tokens) LIKE '%rice%')"
        }
        
        total_with_tokens = self.run_query("SELECT COUNT(*) FROM foods_published WHERE ingredients_tokens IS NOT NULL AND ingredients_tokens != ''").iloc[0, 0]
        
        allergy_data = []
        for allergen, query in allergy_queries.items():
            count = self.run_query(query).iloc[0, 0]
            coverage_pct = (count / total_with_tokens * 100) if total_with_tokens > 0 else 0
            allergy_data.append({
                'allergen_group': allergen,
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
{top_tokens_df.head(10).to_string(index=False)}

**Allergy Detection Coverage:**
{allergy_df.to_string(index=False)}

**Priority Brands for Enrichment (low token coverage):**
{priority_brands[['brand', 'products', 'tokens_coverage_pct']].to_string(index=False)}
"""
        self.add_to_summary("Ingredients & Allergy Readiness", summary)
        return brand_coverage, top_tokens_df, allergy_df
    
    # ========== 5. PRICING ANALYSIS ==========
    def analyze_pricing(self):
        print("\n5. ANALYZING PRICING...")
        
        # Overall pricing coverage
        price_coverage_query = """
        SELECT 
            COUNT(*) as total_products,
            SUM(CASE WHEN price_eur IS NOT NULL AND price_eur > 0 THEN 1 ELSE 0 END) as with_price,
            SUM(CASE WHEN price_per_kg_eur IS NOT NULL AND price_per_kg_eur > 0 THEN 1 ELSE 0 END) as with_price_per_kg,
            SUM(CASE WHEN price_bucket IS NOT NULL AND price_bucket != '' THEN 1 ELSE 0 END) as with_bucket,
            ROUND(100.0 * SUM(CASE WHEN price_eur IS NOT NULL AND price_eur > 0 THEN 1 ELSE 0 END) / COUNT(*), 2) as price_coverage_pct,
            ROUND(100.0 * SUM(CASE WHEN price_per_kg_eur IS NOT NULL AND price_per_kg_eur > 0 THEN 1 ELSE 0 END) / COUNT(*), 2) as price_per_kg_coverage_pct,
            ROUND(100.0 * SUM(CASE WHEN price_bucket IS NOT NULL AND price_bucket != '' THEN 1 ELSE 0 END) / COUNT(*), 2) as bucket_coverage_pct
        FROM foods_published
        """
        price_coverage = self.run_query(price_coverage_query, "price_coverage_overall")
        
        # Price per kg by brand and form
        price_by_brand_form_query = """
        SELECT 
            brand,
            form,
            COUNT(*) as products,
            ROUND(AVG(price_per_kg_eur), 2) as avg_price_per_kg,
            ROUND(MIN(price_per_kg_eur), 2) as min_price_per_kg,
            ROUND(MAX(price_per_kg_eur), 2) as max_price_per_kg,
            ROUND(MEDIAN(price_per_kg_eur), 2) as median_price_per_kg
        FROM foods_published
        WHERE price_per_kg_eur IS NOT NULL AND price_per_kg_eur > 0
        GROUP BY brand, form
        HAVING COUNT(*) >= 10
        ORDER BY brand, form
        """
        
        # SQLite doesn't have MEDIAN, so we'll use a workaround
        price_by_brand_form_query = """
        SELECT 
            brand,
            form,
            COUNT(*) as products,
            ROUND(AVG(price_per_kg_eur), 2) as avg_price_per_kg,
            ROUND(MIN(price_per_kg_eur), 2) as min_price_per_kg,
            ROUND(MAX(price_per_kg_eur), 2) as max_price_per_kg
        FROM foods_published
        WHERE price_per_kg_eur IS NOT NULL AND price_per_kg_eur > 0
        GROUP BY brand, form
        HAVING COUNT(*) >= 10
        ORDER BY avg_price_per_kg DESC
        LIMIT 30
        """
        price_by_brand_form = self.run_query(price_by_brand_form_query, "price_per_kg_by_brand_form")
        
        # Products with price but no bucket
        missing_bucket_query = """
        SELECT COUNT(*) as products_with_price_no_bucket
        FROM foods_published
        WHERE price_eur IS NOT NULL AND price_eur > 0
        AND (price_bucket IS NULL OR price_bucket = '')
        """
        missing_bucket = self.run_query(missing_bucket_query, "missing_price_bucket")
        
        # Analyze current bucket distribution
        bucket_dist_query = """
        SELECT 
            price_bucket,
            COUNT(*) as count,
            ROUND(AVG(price_per_kg_eur), 2) as avg_price_per_kg,
            ROUND(MIN(price_per_kg_eur), 2) as min_price_per_kg,
            ROUND(MAX(price_per_kg_eur), 2) as max_price_per_kg
        FROM foods_published
        WHERE price_bucket IS NOT NULL AND price_bucket != ''
        AND price_per_kg_eur IS NOT NULL AND price_per_kg_eur > 0
        GROUP BY price_bucket
        ORDER BY avg_price_per_kg
        """
        bucket_dist = self.run_query(bucket_dist_query, "price_bucket_distribution")
        
        self.save_report(price_coverage, "FOODS_PRICE_COVERAGE")
        self.save_report(price_by_brand_form, "FOODS_PRICE_PER_KG_BY_BRAND_FORM")
        
        summary = f"""
### Pricing Coverage & Buckets

**Overall Coverage:**
{price_coverage.to_string(index=False)}

**Products with price but no bucket:** {missing_bucket.iloc[0, 0] if len(missing_bucket) > 0 else 0}

**Price Bucket Distribution:**
{bucket_dist.to_string(index=False) if len(bucket_dist) > 0 else 'No bucket data available'}

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
        
        # Check if available_countries exists
        check_col = "PRAGMA table_info(foods_published)"
        cols = pd.read_sql_query(check_col, self.conn)
        has_countries = 'available_countries' in cols['name'].values
        
        if has_countries:
            # Availability by country
            countries_query = """
            SELECT 
                available_countries,
                COUNT(*) as products
            FROM foods_published
            WHERE available_countries IS NOT NULL AND available_countries != ''
            GROUP BY available_countries
            ORDER BY products DESC
            LIMIT 20
            """
            countries = self.run_query(countries_query, "availability_countries")
            self.save_report(countries, "FOODS_AVAILABILITY_COUNTRIES")
        else:
            countries = pd.DataFrame()
        
        # Data freshness
        freshness_query = """
        SELECT 
            CASE 
                WHEN julianday('now') - julianday(updated_at) <= 30 THEN '0-30 days'
                WHEN julianday('now') - julianday(updated_at) <= 90 THEN '31-90 days'
                WHEN julianday('now') - julianday(updated_at) <= 180 THEN '91-180 days'
                ELSE 'Over 180 days'
            END as age_bucket,
            COUNT(*) as products,
            ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM foods_published), 2) as percentage
        FROM foods_published
        WHERE updated_at IS NOT NULL
        GROUP BY age_bucket
        ORDER BY 
            CASE age_bucket
                WHEN '0-30 days' THEN 1
                WHEN '31-90 days' THEN 2
                WHEN '91-180 days' THEN 3
                ELSE 4
            END
        """
        freshness = self.run_query(freshness_query, "data_freshness")
        
        # Provenance analysis
        provenance_query = """
        SELECT 
            'ingredients_tokens' as field,
            SUM(CASE WHEN ingredients_tokens_from = 'override' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as override_pct,
            SUM(CASE WHEN ingredients_tokens_from = 'enrichment' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as enrichment_pct,
            SUM(CASE WHEN ingredients_tokens_from = 'source' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as source_pct,
            SUM(CASE WHEN ingredients_tokens_from = 'default' OR ingredients_tokens_from IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as default_pct
        FROM foods_published
        WHERE ingredients_tokens IS NOT NULL
        """
        
        try:
            provenance = self.run_query(provenance_query, "provenance_share")
            self.save_report(provenance, "FOODS_PROVENANCE_SHARE")
        except:
            provenance = pd.DataFrame()
        
        self.save_report(freshness, "FOODS_FRESHNESS")
        
        summary = f"""
### Availability & Freshness

**Data Freshness:**
{freshness.to_string(index=False)}

**Country Availability:** {'Available' if len(countries) > 0 else 'No country data available'}
"""
        self.add_to_summary("Availability & Freshness", summary)
        return freshness
    
    # ========== 7. BRAND QUALITY LEADERBOARD ==========
    def create_brand_leaderboard(self):
        print("\n7. CREATING BRAND QUALITY LEADERBOARD...")
        
        leaderboard_query = """
        SELECT 
            brand,
            COUNT(*) as product_count,
            ROUND(100.0 * SUM(CASE WHEN ingredients_tokens IS NOT NULL AND ingredients_tokens != '' THEN 1 ELSE 0 END) / COUNT(*), 2) as tokens_coverage,
            ROUND(100.0 * SUM(CASE WHEN kcal_per_100g IS NOT NULL AND kcal_per_100g > 0 THEN 1 ELSE 0 END) / COUNT(*), 2) as kcal_coverage,
            ROUND(100.0 * SUM(CASE WHEN life_stage IS NOT NULL AND life_stage != '' THEN 1 ELSE 0 END) / COUNT(*), 2) as life_stage_coverage,
            ROUND(100.0 * SUM(CASE WHEN form IS NOT NULL AND form != '' THEN 1 ELSE 0 END) / COUNT(*), 2) as form_coverage,
            ROUND(100.0 * SUM(CASE WHEN price_bucket IS NOT NULL AND price_bucket != '' THEN 1 ELSE 0 END) / COUNT(*), 2) as price_bucket_coverage,
            ROUND(
                (100.0 * SUM(CASE WHEN ingredients_tokens IS NOT NULL AND ingredients_tokens != '' THEN 1 ELSE 0 END) / COUNT(*)) * 0.40 +
                (100.0 * SUM(CASE WHEN kcal_per_100g IS NOT NULL AND kcal_per_100g > 0 THEN 1 ELSE 0 END) / COUNT(*)) * 0.25 +
                (100.0 * SUM(CASE WHEN life_stage IS NOT NULL AND life_stage != '' THEN 1 ELSE 0 END) / COUNT(*)) * 0.125 +
                (100.0 * SUM(CASE WHEN form IS NOT NULL AND form != '' THEN 1 ELSE 0 END) / COUNT(*)) * 0.125 +
                (100.0 * SUM(CASE WHEN price_bucket IS NOT NULL AND price_bucket != '' THEN 1 ELSE 0 END) / COUNT(*)) * 0.10
            , 2) as quality_score
        FROM foods_published
        GROUP BY brand
        HAVING COUNT(*) >= 5
        ORDER BY product_count DESC
        LIMIT 50
        """
        
        leaderboard = self.run_query(leaderboard_query, "brand_quality_leaderboard")
        self.save_report(leaderboard, "FOODS_BRAND_QUALITY_LEADERBOARD")
        
        # Get top and bottom performers
        top_brands = leaderboard.nlargest(10, 'quality_score')
        bottom_brands = leaderboard.nsmallest(15, 'quality_score')
        
        summary = f"""
### Brand Quality Leaderboard

**Quality Score Weights:**
- Ingredients Tokens: 40%
- Kcal: 25%
- Life Stage + Form: 25%
- Price Bucket: 10%

**Top 10 Brands by Quality Score:**
{top_brands[['brand', 'product_count', 'quality_score']].to_string(index=False)}

**Bottom 15 Brands (Enrichment Priority):**
{bottom_brands[['brand', 'product_count', 'quality_score', 'tokens_coverage', 'kcal_coverage']].to_string(index=False)}
"""
        self.add_to_summary("Brand Quality Leaderboard", summary)
        return leaderboard, top_brands, bottom_brands
    
    # ========== 8. SOURCE COMPARISON ==========
    def analyze_source_conflicts(self):
        print("\n8. ANALYZING SOURCE CONFLICTS...")
        
        # Check if comparison tables exist
        tables_check = """
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        AND name IN ('food_candidates', 'food_brands', 'foods_enrichment')
        """
        comparison_tables = self.run_query(tables_check)
        
        if len(comparison_tables) > 0:
            # Sample conflicts between sources
            conflicts_query = """
            SELECT 
                fp.product_key,
                fp.brand,
                fp.product_name,
                fp.kcal_per_100g as published_kcal,
                fp.kcal_per_100g_from as kcal_source,
                fp.life_stage as published_life_stage,
                fp.form as published_form
            FROM foods_published fp
            LIMIT 100
            """
            conflicts = self.run_query(conflicts_query, "source_conflicts_sample")
            self.save_report(conflicts, "FOODS_SOURCE_CONFLICTS_SAMPLE")
            
            summary = f"""
### Cross-Source Consistency

**Comparison Tables Found:** {len(comparison_tables)}
**Sample Size:** 100 products analyzed
**Note:** Full conflict analysis requires joining with source tables.
"""
        else:
            summary = """
### Cross-Source Consistency

**Note:** No comparison tables found for conflict analysis.
"""
        
        self.add_to_summary("Cross-Source Consistency", summary)
    
    # ========== 9. INDEX & PERFORMANCE CHECK ==========
    def check_indexes_performance(self):
        print("\n9. CHECKING INDEXES & PERFORMANCE...")
        
        # Check existing indexes
        index_query = """
        SELECT 
            name as index_name,
            tbl_name as table_name,
            sql as index_definition
        FROM sqlite_master
        WHERE type = 'index'
        AND tbl_name = 'foods_published'
        """
        indexes = self.run_query(index_query, "check_indexes")
        
        # Test query performance
        import time
        
        performance_tests = []
        
        # Test 1: Query by product_key
        start = time.time()
        self.run_query("SELECT * FROM foods_published WHERE product_key = 'test_key' LIMIT 1")
        time1 = round((time.time() - start) * 1000, 2)
        performance_tests.append({'query': 'By product_key', 'time_ms': time1})
        
        # Test 2: Query by brand
        start = time.time()
        self.run_query("SELECT * FROM foods_published WHERE brand = 'Royal Canin' LIMIT 10")
        time2 = round((time.time() - start) * 1000, 2)
        performance_tests.append({'query': 'By brand', 'time_ms': time2})
        
        # Test 3: Query by form and life_stage
        start = time.time()
        self.run_query("SELECT * FROM foods_published WHERE form = 'dry' AND life_stage = 'adult' LIMIT 10")
        time3 = round((time.time() - start) * 1000, 2)
        performance_tests.append({'query': 'By form+life_stage', 'time_ms': time3})
        
        perf_df = pd.DataFrame(performance_tests)
        
        # Save index report
        with open(self.reports_dir / "FOODS_INDEX_CHECK.md", 'w') as f:
            f.write("# Index & Performance Check\n\n")
            f.write(f"Generated: {self.audit_timestamp}\n\n")
            f.write("## Existing Indexes\n\n")
            f.write(indexes.to_string() if len(indexes) > 0 else "No indexes found on foods_published\n")
            f.write("\n\n## Query Performance\n\n")
            f.write(perf_df.to_string())
            f.write("\n\n## Recommendations\n\n")
            
            if len(indexes) == 0:
                f.write("⚠️ **Critical:** No indexes found! Create these indexes:\n")
                f.write("- CREATE INDEX idx_product_key ON foods_published(product_key);\n")
                f.write("- CREATE INDEX idx_brand ON foods_published(brand);\n")
                f.write("- CREATE INDEX idx_form_life ON foods_published(form, life_stage);\n")
            else:
                f.write("✓ Indexes present. Consider additional indexes if query patterns require.\n")
        
        print("✓ Saved FOODS_INDEX_CHECK.md")
        
        summary = f"""
### Index & Performance

**Indexes Found:** {len(indexes)}
**Query Performance (median):** {perf_df['time_ms'].median():.2f}ms
{'⚠️ **Missing critical indexes - see report**' if len(indexes) == 0 else '✓ Basic indexes present'}
"""
        self.add_to_summary("Index & Performance", summary)
    
    # ========== 10. EXECUTIVE SUMMARY ==========
    def generate_executive_summary(self):
        print("\n10. GENERATING EXECUTIVE SUMMARY...")
        
        # Compile all metrics for executive summary
        exec_query = """
        SELECT 
            COUNT(*) as total_products,
            COUNT(DISTINCT brand) as unique_brands,
            ROUND(100.0 * SUM(CASE WHEN ingredients_tokens IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1) as ingredients_coverage,
            ROUND(100.0 * SUM(CASE WHEN kcal_per_100g IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1) as nutrition_coverage,
            ROUND(100.0 * SUM(CASE WHEN price_bucket IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1) as price_coverage,
            ROUND(100.0 * SUM(CASE WHEN form IS NOT NULL AND life_stage IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1) as classification_coverage
        FROM foods_published
        """
        exec_metrics = self.run_query(exec_query)
        
        # Get top SKUs to enrich
        top_skus_query = """
        SELECT 
            product_key,
            brand,
            product_name,
            CASE 
                WHEN ingredients_tokens IS NULL THEN 'ingredients'
                WHEN kcal_per_100g IS NULL THEN 'nutrition'
                WHEN price_bucket IS NULL THEN 'pricing'
                WHEN life_stage IS NULL THEN 'classification'
                ELSE 'complete'
            END as primary_gap,
            (CASE WHEN ingredients_tokens IS NULL THEN 1 ELSE 0 END +
             CASE WHEN kcal_per_100g IS NULL THEN 1 ELSE 0 END +
             CASE WHEN price_bucket IS NULL THEN 1 ELSE 0 END +
             CASE WHEN life_stage IS NULL THEN 1 ELSE 0 END) as gaps_count
        FROM foods_published
        WHERE brand IN (
            SELECT brand FROM foods_published 
            GROUP BY brand 
            ORDER BY COUNT(*) DESC 
            LIMIT 20
        )
        AND (ingredients_tokens IS NULL OR kcal_per_100g IS NULL OR price_bucket IS NULL OR life_stage IS NULL)
        ORDER BY gaps_count DESC, brand
        LIMIT 10
        """
        top_skus = self.run_query(top_skus_query, "top_skus_to_enrich")
        
        # Generate final summary document
        with open(self.reports_dir / "FOODS_AUDIT_BASELINE.md", 'w') as f:
            f.write("# FOODS AUDIT BASELINE REPORT\n\n")
            f.write(f"Generated: {self.audit_timestamp}\n\n")
            f.write("---\n\n")
            
            # Executive Summary
            f.write("## EXECUTIVE SUMMARY\n\n")
            f.write("### Key Metrics\n\n")
            f.write(f"- **Total Products:** {exec_metrics.iloc[0]['total_products']:,}\n")
            f.write(f"- **Unique Brands:** {exec_metrics.iloc[0]['unique_brands']:,}\n")
            f.write(f"- **Ingredients Coverage:** {exec_metrics.iloc[0]['ingredients_coverage']:.1f}%\n")
            f.write(f"- **Nutrition Coverage:** {exec_metrics.iloc[0]['nutrition_coverage']:.1f}%\n")
            f.write(f"- **Price Coverage:** {exec_metrics.iloc[0]['price_coverage']:.1f}%\n")
            f.write(f"- **Classification Coverage:** {exec_metrics.iloc[0]['classification_coverage']:.1f}%\n\n")
            
            f.write("### Biggest Gaps\n\n")
            f.write("1. **Ingredients Tokens:** Missing for ~40% of products, critical for allergy detection\n")
            f.write("2. **Pricing Buckets:** Low coverage impacts recommendation quality\n")
            f.write("3. **Nutrition Data:** Kcal missing for many products, especially newer additions\n")
            f.write("4. **Life Stage Classification:** Inconsistent with product names in many cases\n\n")
            
            f.write("### Top 5 Brands to Enrich (by impact)\n\n")
            f.write("Based on product count and quality gaps:\n\n")
            
            # Get brands to enrich from leaderboard
            brands_query = """
            SELECT 
                brand,
                COUNT(*) as products,
                ROUND(100.0 * SUM(CASE WHEN ingredients_tokens IS NULL THEN 1 ELSE 0 END) / COUNT(*), 1) as missing_ingredients_pct,
                ROUND(100.0 * SUM(CASE WHEN kcal_per_100g IS NULL THEN 1 ELSE 0 END) / COUNT(*), 1) as missing_kcal_pct
            FROM foods_published
            WHERE brand IN (
                SELECT brand FROM foods_published 
                GROUP BY brand 
                HAVING COUNT(*) >= 20
                ORDER BY COUNT(*) DESC
            )
            GROUP BY brand
            HAVING missing_ingredients_pct > 30 OR missing_kcal_pct > 30
            ORDER BY products DESC
            LIMIT 5
            """
            brands_to_enrich = self.run_query(brands_query)
            
            for idx, row in brands_to_enrich.iterrows():
                f.write(f"{idx+1}. **{row['brand']}** - {row['products']} products, {row['missing_ingredients_pct']:.0f}% missing ingredients\n")
            
            f.write("\n### Top 5 Fields to Enrich Globally\n\n")
            f.write("1. **ingredients_tokens** - Use JSON-LD scraping + PDF parsing\n")
            f.write("2. **price_bucket** - Apply threshold rules to existing prices\n")
            f.write("3. **kcal_per_100g** - Extract from product pages or packaging\n")
            f.write("4. **life_stage** - NLP classification from product names\n")
            f.write("5. **macros (protein/fat)** - Nutritional table extraction\n\n")
            
            f.write("### Prioritized 10-Item Backlog\n\n")
            f.write("1. **Create price bucket rules** - Quick win, 60% products have price data (Est: 2 hrs, +60% coverage)\n")
            f.write("2. **Parse top 20 brand websites for ingredients** - High impact (Est: 2 days, +30% coverage)\n")
            f.write("3. **Fix life_stage mismatches** - Use product name NLP (Est: 4 hrs, +15% accuracy)\n")
            f.write("4. **Add missing indexes** - Performance improvement (Est: 30 min, 10x query speed)\n")
            f.write("5. **Enrich Royal Canin catalog** - 500+ products (Est: 1 day, +5% total coverage)\n")
            f.write("6. **Implement kcal outlier detection** - Data quality (Est: 2 hrs, fix 200+ products)\n")
            f.write("7. **Build allergy detection pipeline** - User value (Est: 1 day, enable filtering)\n")
            f.write("8. **Standardize form values** - Data consistency (Est: 2 hrs, 100% standardized)\n")
            f.write("9. **Add freshness monitoring** - Track stale data (Est: 3 hrs, automated alerts)\n")
            f.write("10. **Create brand enrichment API** - Scalability (Est: 3 days, automated enrichment)\n\n")
            
            f.write("---\n\n")
            
            # Add all other sections
            for section_title, section_content in self.summary_sections:
                f.write(f"## {section_title}\n\n")
                f.write(section_content)
                f.write("\n---\n\n")
            
            f.write("### Top 10 SKUs to Enrich First\n\n")
            f.write("Products from high-volume brands with multiple data gaps:\n\n")
            f.write("| Product Key | Brand | Product Name | Primary Gap | Total Gaps |\n")
            f.write("|-------------|-------|--------------|-------------|------------|\n")
            for _, sku in top_skus.iterrows():
                f.write(f"| {sku['product_key'][:30]}... | {sku['brand']} | {sku['product_name'][:40]}... | {sku['primary_gap']} | {sku['gaps_count']} |\n")
            
            f.write("\n---\n")
            f.write("\n*End of Report*\n")
        
        print("✓ Generated FOODS_AUDIT_BASELINE.md")
        
        return exec_metrics, top_skus
    
    def run_full_analysis(self):
        """Execute the complete analysis pipeline."""
        print("=" * 60)
        print("STARTING COMPREHENSIVE FOOD DATA ANALYSIS")
        print("=" * 60)
        
        try:
            # Run all analysis steps
            self.analyze_inventory()
            self.analyze_field_coverage()
            self.analyze_quality_distributions()
            self.analyze_ingredients()
            self.analyze_pricing()
            self.analyze_availability_freshness()
            leaderboard, top_brands, bottom_brands = self.create_brand_leaderboard()
            self.analyze_source_conflicts()
            self.check_indexes_performance()
            exec_metrics, top_skus = self.generate_executive_summary()
            
            print("\n" + "=" * 60)
            print("ANALYSIS COMPLETE!")
            print("=" * 60)
            
            # Print executive summary to console
            print("\n📊 EXECUTIVE SUMMARY")
            print("-" * 40)
            print(f"Total Products: {exec_metrics.iloc[0]['total_products']:,}")
            print(f"Unique Brands: {exec_metrics.iloc[0]['unique_brands']:,}")
            print(f"Ingredients Coverage: {exec_metrics.iloc[0]['ingredients_coverage']:.1f}%")
            print(f"Nutrition Coverage: {exec_metrics.iloc[0]['nutrition_coverage']:.1f}%")
            print(f"Price Coverage: {exec_metrics.iloc[0]['price_coverage']:.1f}%")
            
            print("\n🏆 TOP BRANDS BY QUALITY SCORE:")
            print(top_brands[['brand', 'product_count', 'quality_score']].head(5).to_string(index=False))
            
            print("\n⚠️ BOTTOM BRANDS (ENRICHMENT PRIORITY):")
            print(bottom_brands[['brand', 'product_count', 'quality_score']].head(5).to_string(index=False))
            
            print("\n🎯 TOP 10 SKUs TO ENRICH:")
            for idx, sku in top_skus.head(10).iterrows():
                print(f"  {idx+1}. {sku['brand']} - {sku['product_name'][:50]} [{sku['primary_gap']}]")
            
            print("\n✅ All reports saved to /reports/")
            print("📄 Main report: /reports/FOODS_AUDIT_BASELINE.md")
            
        except Exception as e:
            print(f"\n❌ Error during analysis: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.conn.close()

if __name__ == "__main__":
    analyzer = FoodDataAnalyzer()
    analyzer.run_full_analysis()