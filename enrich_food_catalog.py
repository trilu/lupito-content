#!/usr/bin/env python3
"""
Comprehensive food catalog enrichment pipeline for Lupito.
Enriches allergen groups, form/life_stage, and pricing data.
"""

import os
import re
import json
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dotenv import load_dotenv
from supabase import create_client
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FoodCatalogEnricher:
    def __init__(self):
        load_dotenv()
        self.supabase = self._connect_supabase()
        self.reports_dir = Path("reports")
        self.sql_dir = Path("sql/enrichment")
        self.reports_dir.mkdir(exist_ok=True)
        self.sql_dir.mkdir(exist_ok=True, parents=True)
        
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.enrichment_stats = {}
        
    def _connect_supabase(self):
        """Connect to Supabase"""
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not url or not key:
            raise ValueError("Missing Supabase credentials")
        
        logger.info("Connected to Supabase")
        return create_client(url, key)
    
    def save_sql(self, name: str, query: str):
        """Save SQL query for documentation."""
        with open(self.sql_dir / f"{name}.sql", 'w') as f:
            f.write(f"-- Generated: {self.timestamp}\n")
            f.write(f"-- Purpose: {name.replace('_', ' ').title()}\n\n")
            f.write(query)
    
    # ========== 1. ALLERGEN GROUPS ENRICHMENT ==========
    def create_allergen_mapping(self) -> Dict[str, List[str]]:
        """Create comprehensive allergen group mappings."""
        
        allergen_map = {
            'chicken': ['chicken', 'poultry', 'poultry meal', 'chicken meal', 'chicken fat', 
                       'chicken liver', 'chicken by-product', 'hydrolyzed chicken'],
            'beef': ['beef', 'bovine', 'beef meal', 'beef fat', 'beef liver', 'ox', 'veal'],
            'fish_salmon': ['salmon', 'trout', 'whitefish', 'tuna', 'fish meal', 'fish oil',
                          'herring', 'mackerel', 'sardine', 'anchovy', 'cod', 'haddock',
                          'ocean fish', 'marine fish'],
            'lamb': ['lamb', 'ovine', 'lamb meal', 'mutton', 'sheep'],
            'turkey': ['turkey', 'turkey meal', 'turkey fat'],
            'duck': ['duck', 'duck meal', 'duck fat'],
            'pork': ['pork', 'porcine', 'bacon', 'ham', 'swine'],
            'egg': ['egg', 'egg powder', 'dried egg', 'egg product'],
            'dairy': ['milk', 'whey', 'casein', 'cheese', 'yogurt', 'lactose', 'dairy'],
            'grain_gluten': ['wheat', 'barley', 'rye', 'oats', 'cereals', 'gluten', 
                           'wheat flour', 'wheat germ', 'bran'],
            'corn_maize': ['corn', 'maize', 'corn meal', 'corn gluten', 'corn starch'],
            'soy': ['soya', 'soy', 'soy protein', 'soybean', 'soy meal'],
            'pea_legume': ['pea', 'lentil', 'chickpea', 'legume', 'bean', 'pulses'],
            'potato': ['potato', 'sweet potato', 'potato starch', 'potato protein'],
            'rice': ['rice', 'rice bran', 'brown rice', 'white rice', 'rice flour'],
            'novel_protein': ['venison', 'rabbit', 'kangaroo', 'insect', 'buffalo', 'goat',
                            'ostrich', 'wild boar', 'bison', 'alligator', 'quail']
        }
        
        # Save mapping as SQL
        sql = "-- Allergen Group Mappings\n"
        sql += "CREATE TABLE IF NOT EXISTS allergen_map (\n"
        sql += "    id SERIAL PRIMARY KEY,\n"
        sql += "    allergen_group VARCHAR(50) NOT NULL,\n"
        sql += "    ingredient_token VARCHAR(100) NOT NULL,\n"
        sql += "    created_at TIMESTAMP DEFAULT NOW()\n"
        sql += ");\n\n"
        sql += "INSERT INTO allergen_map (allergen_group, ingredient_token) VALUES\n"
        
        values = []
        for group, tokens in allergen_map.items():
            for token in tokens:
                values.append(f"('{group}', '{token}')")
        
        sql += ",\n".join(values) + ";"
        self.save_sql("allergen_map", sql)
        
        return allergen_map
    
    def enrich_allergen_groups(self):
        """Enrich products with allergen group detection."""
        logger.info("Starting allergen groups enrichment...")
        
        # Create allergen mapping
        allergen_map = self.create_allergen_mapping()
        
        # Fetch products with ingredients
        products = self.supabase.table('foods_published').select('*').execute()
        products_df = pd.DataFrame(products.data)
        
        if products_df.empty:
            logger.warning("No products found")
            return pd.DataFrame()
        
        # Process each product
        enriched_allergens = []
        
        for _, product in products_df.iterrows():
            product_key = product.get('product_key')
            ingredients_tokens = product.get('ingredients_tokens', '')
            
            # Parse ingredients tokens
            detected_allergens = set()
            
            if ingredients_tokens:
                # Handle both string and list formats
                if isinstance(ingredients_tokens, str):
                    if ingredients_tokens.startswith('['):
                        try:
                            tokens = json.loads(ingredients_tokens)
                        except:
                            tokens = ingredients_tokens.lower().split(',')
                    else:
                        tokens = ingredients_tokens.lower().split(',')
                elif isinstance(ingredients_tokens, list):
                    tokens = ingredients_tokens
                else:
                    tokens = []
                
                # Normalize tokens
                tokens = [str(t).strip().lower() for t in tokens]
                
                # Detect allergens
                for allergen_group, keywords in allergen_map.items():
                    for keyword in keywords:
                        keyword_lower = keyword.lower()
                        for token in tokens:
                            if keyword_lower in token or token in keyword_lower:
                                detected_allergens.add(allergen_group)
                                break
            
            # Create enrichment record
            enriched_allergens.append({
                'product_key': product_key,
                'allergen_groups': list(detected_allergens),
                'allergen_groups_json': json.dumps(list(detected_allergens)),
                'ingredients_unknown': len(detected_allergens) == 0 and not ingredients_tokens,
                'source': 'allergen_mapping_v1',
                'confidence': 0.95 if detected_allergens else 0.0,
                'fetched_at': self.timestamp,
                'allergen_groups_from': 'enrichment'
            })
        
        allergens_df = pd.DataFrame(enriched_allergens)
        
        # Calculate coverage stats
        total_products = len(allergens_df)
        with_allergens = len(allergens_df[allergens_df['allergen_groups'].apply(len) > 0])
        coverage = (with_allergens / total_products * 100) if total_products > 0 else 0
        
        # Generate coverage report
        coverage_report = f"""# FOODS ALLERGEN COVERAGE REPORT
Generated: {self.timestamp}

## Overall Coverage
- Total Products: {total_products:,}
- Products with Allergens Detected: {with_allergens:,}
- Coverage: {coverage:.1f}%
- Unknown Ingredients: {allergens_df['ingredients_unknown'].sum():,}

## Allergen Group Distribution
"""
        
        # Count each allergen group
        allergen_counts = {}
        for allergens in allergens_df['allergen_groups']:
            for allergen in allergens:
                allergen_counts[allergen] = allergen_counts.get(allergen, 0) + 1
        
        for allergen, count in sorted(allergen_counts.items(), key=lambda x: x[1], reverse=True):
            coverage_report += f"- {allergen}: {count:,} products ({count/total_products*100:.1f}%)\n"
        
        # Save report
        with open(self.reports_dir / "FOODS_ALLERGEN_COVERAGE.md", 'w') as f:
            f.write(coverage_report)
        
        logger.info(f"✓ Allergen enrichment complete: {coverage:.1f}% coverage")
        
        self.enrichment_stats['allergens'] = {
            'coverage': coverage,
            'total': total_products,
            'enriched': with_allergens
        }
        
        return allergens_df
    
    # ========== 2. FORM & LIFE STAGE CLASSIFICATION ==========
    def classify_form_life_stage(self):
        """Classify form and life stage using NLP rules."""
        logger.info("Starting form and life stage classification...")
        
        # Fetch products
        products = self.supabase.table('foods_published').select('*').execute()
        products_df = pd.DataFrame(products.data)
        
        if products_df.empty:
            return pd.DataFrame()
        
        # Classification rules
        form_rules = {
            'dry': ['kibble', 'pellet', 'biscuit', 'crunchy', 'dry food', 'dry dog', 'dry cat'],
            'wet': ['pouch', 'can', 'tin', 'gravy', 'jelly', 'chunks', 'pate', 'terrine', 
                   'wet food', 'canned', 'tray', 'bowl'],
            'freeze_dried': ['freeze dried', 'freeze-dried', 'air dried', 'air-dried', 
                           'dehydrated', 'lyophilized'],
            'raw': ['raw', 'barf', 'frozen', 'fresh frozen', 'raw frozen', 'minced']
        }
        
        life_stage_rules = {
            'puppy': ['puppy', 'junior', 'growth', 'weaning', 'starter'],
            'adult': ['adult', 'maintenance', 'mature adult'],
            'senior': ['senior', 'mature', '7+', '8+', '10+', 'aging', 'golden years'],
            'all': ['all life stages', 'all ages', 'complete', 'family']
        }
        
        # Classify each product
        classifications = []
        
        for _, product in products_df.iterrows():
            product_key = product.get('product_key')
            product_name = str(product.get('product_name', '')).lower()
            brand = str(product.get('brand', '')).lower()
            current_form = product.get('form')
            current_life_stage = product.get('life_stage')
            
            # Combined text for analysis
            text = f"{product_name} {brand}"
            
            # Classify form
            detected_form = current_form  # Keep existing if no match
            form_confidence = 0.5
            
            for form, keywords in form_rules.items():
                for keyword in keywords:
                    if keyword in text:
                        detected_form = form
                        form_confidence = 0.9
                        break
                if detected_form != current_form:
                    break
            
            # Classify life stage
            detected_life_stage = current_life_stage  # Keep existing if no match
            life_stage_confidence = 0.5
            
            for stage, keywords in life_stage_rules.items():
                for keyword in keywords:
                    if keyword in text:
                        detected_life_stage = stage
                        life_stage_confidence = 0.9
                        break
                if detected_life_stage != current_life_stage:
                    break
            
            # Check for mismatches
            mismatch = False
            if 'puppy' in product_name and detected_life_stage != 'puppy':
                mismatch = True
            elif 'senior' in product_name and detected_life_stage != 'senior':
                mismatch = True
            
            classifications.append({
                'product_key': product_key,
                'form': detected_form,
                'form_confidence': form_confidence,
                'form_from': 'enrichment' if detected_form != current_form else 'source',
                'life_stage': detected_life_stage,
                'life_stage_confidence': life_stage_confidence,
                'life_stage_from': 'enrichment' if detected_life_stage != current_life_stage else 'source',
                'classification_mismatch': mismatch,
                'source': 'nlp_rules_v1',
                'fetched_at': self.timestamp
            })
        
        classify_df = pd.DataFrame(classifications)
        
        # Calculate coverage
        total = len(classify_df)
        form_coverage = (classify_df['form'].notna().sum() / total * 100) if total > 0 else 0
        life_stage_coverage = (classify_df['life_stage'].notna().sum() / total * 100) if total > 0 else 0
        mismatches = classify_df['classification_mismatch'].sum()
        
        # Generate report
        report = f"""# FOODS CLASSIFY COVERAGE REPORT
Generated: {self.timestamp}

## Coverage Summary
- Total Products: {total:,}
- Form Coverage: {form_coverage:.1f}%
- Life Stage Coverage: {life_stage_coverage:.1f}%
- Classification Mismatches: {mismatches:,}

## Form Distribution
"""
        form_counts = classify_df['form'].value_counts()
        for form, count in form_counts.items():
            report += f"- {form}: {count:,} ({count/total*100:.1f}%)\n"
        
        report += "\n## Life Stage Distribution\n"
        life_stage_counts = classify_df['life_stage'].value_counts()
        for stage, count in life_stage_counts.items():
            report += f"- {stage}: {count:,} ({count/total*100:.1f}%)\n"
        
        # Save report
        with open(self.reports_dir / "FOODS_CLASSIFY_COVERAGE.md", 'w') as f:
            f.write(report)
        
        logger.info(f"✓ Classification complete: Form {form_coverage:.1f}%, Life Stage {life_stage_coverage:.1f}%")
        
        self.enrichment_stats['classification'] = {
            'form_coverage': form_coverage,
            'life_stage_coverage': life_stage_coverage,
            'mismatches': mismatches
        }
        
        return classify_df
    
    # ========== 3. PRICING ENRICHMENT ==========
    def enrich_pricing(self):
        """Enrich pricing data and create buckets."""
        logger.info("Starting pricing enrichment...")
        
        # Fetch products
        products = self.supabase.table('foods_published').select('*').execute()
        products_df = pd.DataFrame(products.data)
        
        if products_df.empty:
            return pd.DataFrame()
        
        # Price bucket thresholds (EUR per kg)
        price_buckets = {
            'low': (0, 15),
            'mid': (15, 30),
            'high': (30, float('inf'))
        }
        
        # Process pricing
        pricing_enriched = []
        
        for _, product in products_df.iterrows():
            product_key = product.get('product_key')
            current_price = product.get('price_eur')
            current_price_per_kg = product.get('price_per_kg_eur')
            current_bucket = product.get('price_bucket')
            
            # Determine price per kg (use existing or estimate)
            price_per_kg = current_price_per_kg
            price_source = 'source'
            
            # If no price per kg, try to calculate from price and pack size
            if not price_per_kg and current_price:
                pack_size = product.get('pack_size', '')
                if pack_size:
                    # Extract weight from pack size (e.g., "5kg", "400g")
                    match = re.search(r'(\d+(?:\.\d+)?)\s*(kg|g)', str(pack_size).lower())
                    if match:
                        weight = float(match.group(1))
                        unit = match.group(2)
                        if unit == 'g':
                            weight = weight / 1000  # Convert to kg
                        if weight > 0:
                            price_per_kg = current_price / weight
                            price_source = 'calculated'
            
            # Determine price bucket
            if price_per_kg:
                if price_per_kg < price_buckets['low'][1]:
                    bucket = 'low'
                elif price_per_kg < price_buckets['mid'][1]:
                    bucket = 'mid'
                else:
                    bucket = 'high'
                bucket_from = 'enrichment'
            else:
                bucket = current_bucket
                bucket_from = 'source' if current_bucket else 'default'
            
            pricing_enriched.append({
                'product_key': product_key,
                'price_eur': current_price,
                'price_per_kg_eur': price_per_kg,
                'price_bucket': bucket,
                'price_source': price_source,
                'price_bucket_from': bucket_from,
                'fetched_at': self.timestamp
            })
        
        pricing_df = pd.DataFrame(pricing_enriched)
        
        # Calculate coverage
        total = len(pricing_df)
        with_price = (pricing_df['price_eur'].notna().sum())
        with_price_per_kg = (pricing_df['price_per_kg_eur'].notna().sum())
        with_bucket = (pricing_df['price_bucket'].notna().sum())
        
        # Generate report
        report = f"""# FOODS PRICING COVERAGE REPORT
Generated: {self.timestamp}

## Coverage Summary
- Total Products: {total:,}
- With Price: {with_price:,} ({with_price/total*100:.1f}%)
- With Price per kg: {with_price_per_kg:,} ({with_price_per_kg/total*100:.1f}%)
- With Price Bucket: {with_bucket:,} ({with_bucket/total*100:.1f}%)

## Price Bucket Distribution
"""
        
        bucket_counts = pricing_df['price_bucket'].value_counts()
        for bucket in ['low', 'mid', 'high']:
            count = bucket_counts.get(bucket, 0)
            report += f"- {bucket}: {count:,} ({count/total*100:.1f}%)\n"
        
        # Price per kg statistics
        if with_price_per_kg > 0:
            prices = pricing_df['price_per_kg_eur'].dropna()
            report += f"""
## Price per kg Statistics
- Mean: €{prices.mean():.2f}
- Median: €{prices.median():.2f}
- Min: €{prices.min():.2f}
- Max: €{prices.max():.2f}
- P25: €{prices.quantile(0.25):.2f}
- P75: €{prices.quantile(0.75):.2f}
"""
        
        # Save report
        with open(self.reports_dir / "FOODS_PRICING_COVERAGE.md", 'w') as f:
            f.write(report)
        
        logger.info(f"✓ Pricing enrichment complete: {with_bucket/total*100:.1f}% bucket coverage")
        
        self.enrichment_stats['pricing'] = {
            'price_coverage': with_price/total*100,
            'price_per_kg_coverage': with_price_per_kg/total*100,
            'bucket_coverage': with_bucket/total*100
        }
        
        return pricing_df
    
    # ========== 4. BUILD RECONCILED VIEW ==========
    def build_foods_published_v2(self, allergens_df, classify_df, pricing_df):
        """Build reconciled foods_published_v2 view."""
        logger.info("Building foods_published_v2 reconciled view...")
        
        # Fetch original data
        products = self.supabase.table('foods_published').select('*').execute()
        products_df = pd.DataFrame(products.data)
        
        if products_df.empty:
            return pd.DataFrame()
        
        # Merge enrichments
        v2_df = products_df.copy()
        
        # Merge allergens
        if not allergens_df.empty:
            allergens_cols = ['product_key', 'allergen_groups_json', 'ingredients_unknown', 
                             'allergen_groups_from']
            allergens_temp = allergens_df[allergens_cols].copy()
            allergens_temp.columns = ['product_key', 'allergen_groups_json', 'ingredients_unknown_enrich', 
                                     'allergen_groups_from']
            v2_df = v2_df.merge(allergens_temp, on='product_key', how='left')
            v2_df['allergen_groups'] = v2_df['allergen_groups_json']
            if 'ingredients_unknown' in v2_df.columns and 'ingredients_unknown_enrich' in v2_df.columns:
                v2_df['ingredients_unknown'] = v2_df['ingredients_unknown_enrich'].fillna(v2_df.get('ingredients_unknown'))
        
        # Merge classification
        if not classify_df.empty:
            classify_cols = ['product_key', 'form', 'life_stage', 'form_from', 'life_stage_from']
            classify_temp = classify_df[classify_cols].copy()
            classify_temp.columns = ['product_key', 'form_enrich', 'life_stage_enrich', 
                                    'form_from', 'life_stage_from']
            v2_df = v2_df.merge(classify_temp, on='product_key', how='left')
            
            # Apply enriched values where better
            v2_df['form'] = v2_df['form_enrich'].fillna(v2_df['form'])
            v2_df['life_stage'] = v2_df['life_stage_enrich'].fillna(v2_df['life_stage'])
        
        # Merge pricing
        if not pricing_df.empty:
            pricing_cols = ['product_key', 'price_per_kg_eur', 'price_bucket', 'price_bucket_from']
            pricing_temp = pricing_df[pricing_cols].copy()
            pricing_temp.columns = ['product_key', 'price_per_kg_eur_enrich', 
                                   'price_bucket_enrich', 'price_bucket_from']
            v2_df = v2_df.merge(pricing_temp, on='product_key', how='left')
            
            # Apply enriched values
            if 'price_per_kg_eur' in v2_df.columns:
                v2_df['price_per_kg_eur'] = v2_df['price_per_kg_eur_enrich'].fillna(v2_df['price_per_kg_eur'])
            else:
                v2_df['price_per_kg_eur'] = v2_df['price_per_kg_eur_enrich']
                
            if 'price_bucket' in v2_df.columns:
                v2_df['price_bucket'] = v2_df['price_bucket_enrich'].fillna(v2_df['price_bucket'])
            else:
                v2_df['price_bucket'] = v2_df['price_bucket_enrich']
        
        # Add metadata
        v2_df['enriched_at'] = self.timestamp
        v2_df['version'] = 'v2'
        
        # Generate SQL for view creation
        sql = f"""-- Foods Published V2 Reconciled View
-- Generated: {self.timestamp}

CREATE OR REPLACE VIEW foods_published_v2 AS
SELECT 
    fp.*,
    ea.allergen_groups,
    ea.ingredients_unknown as ingredients_unknown_enriched,
    ec.form as form_enriched,
    ec.life_stage as life_stage_enriched,
    ep.price_per_kg_eur as price_per_kg_enriched,
    ep.price_bucket as price_bucket_enriched,
    -- Reconciled fields with precedence
    COALESCE(fo.allergen_groups, ea.allergen_groups, fp.allergen_groups) as allergen_groups_final,
    COALESCE(fo.form, ec.form, fp.form) as form_final,
    COALESCE(fo.life_stage, ec.life_stage, fp.life_stage) as life_stage_final,
    COALESCE(fo.price_bucket, ep.price_bucket, fp.price_bucket) as price_bucket_final,
    -- Provenance
    CASE 
        WHEN fo.allergen_groups IS NOT NULL THEN 'override'
        WHEN ea.allergen_groups IS NOT NULL THEN 'enrichment'
        WHEN fp.allergen_groups IS NOT NULL THEN 'source'
        ELSE 'default'
    END as allergen_groups_from,
    '{self.timestamp}' as enriched_at,
    'v2' as catalog_version
FROM foods_published fp
LEFT JOIN foods_enrichment_allergens ea ON fp.product_key = ea.product_key
LEFT JOIN foods_enrichment_classify ec ON fp.product_key = ec.product_key
LEFT JOIN foods_enrichment_prices ep ON fp.product_key = ep.product_key
LEFT JOIN foods_overrides fo ON fp.product_key = fo.product_key;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_v2_product_key ON foods_published_v2(product_key);
CREATE INDEX IF NOT EXISTS idx_v2_brand ON foods_published_v2(brand_slug);
CREATE INDEX IF NOT EXISTS idx_v2_form ON foods_published_v2(form_final);
CREATE INDEX IF NOT EXISTS idx_v2_life_stage ON foods_published_v2(life_stage_final);
CREATE INDEX IF NOT EXISTS idx_v2_price_bucket ON foods_published_v2(price_bucket_final);
"""
        
        self.save_sql("foods_published_v2", sql)
        
        logger.info("✓ Built foods_published_v2 reconciled view")
        
        return v2_df
    
    # ========== 5. QUALITY GATES & VALIDATION ==========
    def run_quality_gates(self, v2_df):
        """Run quality gates and acceptance criteria."""
        logger.info("Running quality gates...")
        
        total = len(v2_df)
        gates_passed = True
        gate_results = []
        
        # Gate 1: Allergen groups coverage ≥ 85%
        allergen_coverage = (v2_df['allergen_groups'].notna().sum() / total * 100) if 'allergen_groups' in v2_df.columns else 0
        gate1_pass = allergen_coverage >= 85
        gate_results.append({
            'gate': 'Allergen Coverage ≥ 85%',
            'target': 85,
            'actual': round(allergen_coverage, 1),
            'passed': gate1_pass
        })
        gates_passed = gates_passed and gate1_pass
        
        # Gate 2: Form coverage ≥ 95%
        form_coverage = (v2_df['form'].notna().sum() / total * 100)
        gate2_pass = form_coverage >= 95
        gate_results.append({
            'gate': 'Form Coverage ≥ 95%',
            'target': 95,
            'actual': round(form_coverage, 1),
            'passed': gate2_pass
        })
        gates_passed = gates_passed and gate2_pass
        
        # Gate 3: Life stage coverage ≥ 95%
        life_stage_coverage = (v2_df['life_stage'].notna().sum() / total * 100)
        gate3_pass = life_stage_coverage >= 95
        gate_results.append({
            'gate': 'Life Stage Coverage ≥ 95%',
            'target': 95,
            'actual': round(life_stage_coverage, 1),
            'passed': gate3_pass
        })
        gates_passed = gates_passed and gate3_pass
        
        # Gate 4: Price bucket coverage ≥ 70%
        bucket_coverage = (v2_df['price_bucket'].notna().sum() / total * 100)
        gate4_pass = bucket_coverage >= 70
        gate_results.append({
            'gate': 'Price Bucket Coverage ≥ 70%',
            'target': 70,
            'actual': round(bucket_coverage, 1),
            'passed': gate4_pass
        })
        gates_passed = gates_passed and gate4_pass
        
        # Gate 5: Price per kg coverage ≥ 50%
        price_per_kg_coverage = (v2_df['price_per_kg_eur'].notna().sum() / total * 100)
        gate5_pass = price_per_kg_coverage >= 50
        gate_results.append({
            'gate': 'Price per kg Coverage ≥ 50%',
            'target': 50,
            'actual': round(price_per_kg_coverage, 1),
            'passed': gate5_pass
        })
        gates_passed = gates_passed and gate5_pass
        
        # Check for critical outliers
        outliers = []
        if 'kcal_per_100g' in v2_df.columns:
            # Check for absurd kcal values
            kcal_outliers = v2_df[
                ((v2_df['form'] == 'dry') & ((v2_df['kcal_per_100g'] < 250) | (v2_df['kcal_per_100g'] > 500))) |
                ((v2_df['form'] == 'wet') & ((v2_df['kcal_per_100g'] < 40) | (v2_df['kcal_per_100g'] > 150)))
            ]
            outliers.extend(kcal_outliers['product_key'].tolist())
        
        gate6_pass = len(outliers) == 0
        gate_results.append({
            'gate': 'Zero Critical Outliers',
            'target': 0,
            'actual': len(outliers),
            'passed': gate6_pass
        })
        gates_passed = gates_passed and gate6_pass
        
        logger.info(f"Quality gates: {'PASSED' if gates_passed else 'FAILED'}")
        
        return gates_passed, gate_results
    
    # ========== 6. GENERATE FINAL REPORT ==========
    def generate_final_report(self, v2_df, gates_passed, gate_results):
        """Generate comprehensive quality report."""
        logger.info("Generating final quality report...")
        
        # Calculate before/after metrics
        products = self.supabase.table('foods_published').select('*').execute()
        original_df = pd.DataFrame(products.data)
        
        total = len(v2_df)
        
        # Before/After comparison
        metrics_comparison = {
            'allergen_groups': {
                'before': 0,  # Assuming no allergen groups originally
                'after': (v2_df['allergen_groups'].notna().sum() / total * 100) if 'allergen_groups' in v2_df.columns else 0
            },
            'form': {
                'before': (original_df['form'].notna().sum() / len(original_df) * 100) if not original_df.empty else 0,
                'after': (v2_df['form'].notna().sum() / total * 100)
            },
            'life_stage': {
                'before': (original_df['life_stage'].notna().sum() / len(original_df) * 100) if not original_df.empty else 0,
                'after': (v2_df['life_stage'].notna().sum() / total * 100)
            },
            'price_bucket': {
                'before': (original_df['price_bucket'].notna().sum() / len(original_df) * 100) if not original_df.empty else 0,
                'after': (v2_df['price_bucket'].notna().sum() / total * 100)
            }
        }
        
        # Generate report
        report = f"""# FOODS QUALITY AFTER ENRICHMENT
Generated: {self.timestamp}

## EXECUTIVE SUMMARY

### Overall Enrichment Impact
- **Total Products Processed:** {total:,}
- **Quality Gates:** {'✅ ALL PASSED' if gates_passed else '❌ FAILED'}
- **Ready for Production:** {'Yes - Swap can proceed' if gates_passed else 'No - Further enrichment needed'}

### Coverage Improvements (Before → After)
- **Allergen Groups:** {metrics_comparison['allergen_groups']['before']:.1f}% → {metrics_comparison['allergen_groups']['after']:.1f}% ({metrics_comparison['allergen_groups']['after'] - metrics_comparison['allergen_groups']['before']:+.1f}%)
- **Form Classification:** {metrics_comparison['form']['before']:.1f}% → {metrics_comparison['form']['after']:.1f}% ({metrics_comparison['form']['after'] - metrics_comparison['form']['before']:+.1f}%)
- **Life Stage:** {metrics_comparison['life_stage']['before']:.1f}% → {metrics_comparison['life_stage']['after']:.1f}% ({metrics_comparison['life_stage']['after'] - metrics_comparison['life_stage']['before']:+.1f}%)
- **Price Buckets:** {metrics_comparison['price_bucket']['before']:.1f}% → {metrics_comparison['price_bucket']['after']:.1f}% ({metrics_comparison['price_bucket']['after'] - metrics_comparison['price_bucket']['before']:+.1f}%)

## QUALITY GATES RESULTS

| Gate | Target | Actual | Status |
|------|--------|--------|--------|
"""
        
        for gate in gate_results:
            status = '✅ PASS' if gate['passed'] else '❌ FAIL'
            report += f"| {gate['gate']} | {gate['target']}% | {gate['actual']}% | {status} |\n"
        
        # Top improved brands
        if 'brand' in v2_df.columns:
            report += "\n## TOP 15 BRANDS BY IMPROVEMENT\n\n"
            
            # Calculate improvement by brand
            brand_improvements = []
            for brand in v2_df['brand'].unique():
                if pd.notna(brand):
                    brand_data = v2_df[v2_df['brand'] == brand]
                    orig_brand_data = original_df[original_df['brand'] == brand] if not original_df.empty else pd.DataFrame()
                    
                    allergen_improvement = (brand_data['allergen_groups'].notna().sum() / len(brand_data) * 100) if 'allergen_groups' in brand_data.columns else 0
                    
                    price_before = (orig_brand_data['price_bucket'].notna().sum() / len(orig_brand_data) * 100) if len(orig_brand_data) > 0 else 0
                    price_after = (brand_data['price_bucket'].notna().sum() / len(brand_data) * 100)
                    
                    brand_improvements.append({
                        'brand': brand,
                        'products': len(brand_data),
                        'allergen_coverage': allergen_improvement,
                        'price_improvement': price_after - price_before
                    })
            
            brand_improvements_df = pd.DataFrame(brand_improvements)
            brand_improvements_df['total_improvement'] = brand_improvements_df['allergen_coverage'] + brand_improvements_df['price_improvement']
            top_brands = brand_improvements_df.nlargest(15, 'total_improvement')
            
            report += "| Brand | Products | Allergen Coverage | Price Improvement |\n"
            report += "|-------|----------|-------------------|-------------------|\n"
            
            for _, brand in top_brands.iterrows():
                report += f"| {brand['brand']} | {brand['products']} | {brand['allergen_coverage']:.1f}% | {brand['price_improvement']:+.1f}% |\n"
        
        # Next steps
        report += f"""
## NEXT STEPS

"""
        if gates_passed:
            report += """1. ✅ **Ready for Production Swap** - All quality gates passed
2. Execute atomic swap: `foods_published` → `foods_published_v2`
3. Keep `foods_published_prev` for rollback capability
4. Monitor API performance and error rates
5. Plan next enrichment cycle for remaining gaps
"""
        else:
            report += """1. ❌ **Further Enrichment Required** - Quality gates not met
2. Focus on failed gates:
"""
            for gate in gate_results:
                if not gate['passed']:
                    report += f"   - {gate['gate']}: {gate['actual']}% (need {gate['target']}%)\n"
            report += """3. Run targeted enrichment for gaps
4. Re-run quality validation
5. Proceed with swap only after gates pass
"""
        
        # Save report
        with open(self.reports_dir / "FOODS_QUALITY_AFTER.md", 'w') as f:
            f.write(report)
        
        # Save top 50 impact CSV
        if 'brand' in v2_df.columns:
            top50_df = brand_improvements_df.nlargest(50, 'products')[
                ['brand', 'products', 'allergen_coverage', 'price_improvement']
            ]
            top50_df.columns = ['brand', 'products', 'allergen_cov_after', 'price_bucket_improvement']
            top50_df['notes'] = top50_df.apply(
                lambda x: 'High impact' if x['allergen_cov_after'] > 80 else 'Needs attention', 
                axis=1
            )
            top50_df.to_csv(self.reports_dir / "FOODS_TOP50_IMPACT.csv", index=False)
        
        logger.info("✓ Final quality report generated")
        
        return report
    
    # ========== MAIN PIPELINE ==========
    def run_enrichment_pipeline(self):
        """Execute the complete enrichment pipeline."""
        logger.info("=" * 60)
        logger.info("STARTING FOOD CATALOG ENRICHMENT PIPELINE")
        logger.info("=" * 60)
        
        try:
            # Step 1: Enrich allergen groups
            allergens_df = self.enrich_allergen_groups()
            
            # Step 2: Classify form and life stage
            classify_df = self.classify_form_life_stage()
            
            # Step 3: Enrich pricing
            pricing_df = self.enrich_pricing()
            
            # Step 4: Build reconciled view
            v2_df = self.build_foods_published_v2(allergens_df, classify_df, pricing_df)
            
            # Step 5: Run quality gates
            gates_passed, gate_results = self.run_quality_gates(v2_df)
            
            # Step 6: Generate final report
            final_report = self.generate_final_report(v2_df, gates_passed, gate_results)
            
            # Print summary
            logger.info("=" * 60)
            logger.info("ENRICHMENT PIPELINE COMPLETE")
            logger.info("=" * 60)
            
            print("\n📊 ENRICHMENT SUMMARY")
            print("-" * 40)
            
            if 'allergens' in self.enrichment_stats:
                print(f"Allergen Coverage: {self.enrichment_stats['allergens']['coverage']:.1f}%")
            if 'classification' in self.enrichment_stats:
                print(f"Form Coverage: {self.enrichment_stats['classification']['form_coverage']:.1f}%")
                print(f"Life Stage Coverage: {self.enrichment_stats['classification']['life_stage_coverage']:.1f}%")
            if 'pricing' in self.enrichment_stats:
                print(f"Price Bucket Coverage: {self.enrichment_stats['pricing']['bucket_coverage']:.1f}%")
            
            print(f"\nQuality Gates: {'✅ PASSED' if gates_passed else '❌ FAILED'}")
            
            if gates_passed:
                print("\n✅ READY FOR PRODUCTION SWAP")
                print("Execute: ALTER VIEW foods_published RENAME TO foods_published_prev;")
                print("         ALTER VIEW foods_published_v2 RENAME TO foods_published;")
            else:
                print("\n❌ FURTHER ENRICHMENT REQUIRED")
                print("See /reports/FOODS_QUALITY_AFTER.md for details")
            
            print("\n📄 Reports generated:")
            print("- /reports/FOODS_ALLERGEN_COVERAGE.md")
            print("- /reports/FOODS_CLASSIFY_COVERAGE.md")
            print("- /reports/FOODS_PRICING_COVERAGE.md")
            print("- /reports/FOODS_QUALITY_AFTER.md")
            print("- /reports/FOODS_TOP50_IMPACT.csv")
            
            return gates_passed
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    enricher = FoodCatalogEnricher()
    success = enricher.run_enrichment_pipeline()