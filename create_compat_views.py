#!/usr/bin/env python3
"""
C1: Create compatibility views to normalize each food source table
"""

import os
import re
import json
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CompatViewsCreator:
    def __init__(self):
        load_dotenv()
        self.supabase = self._connect_supabase()
        
    def _connect_supabase(self):
        """Connect to Supabase"""
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not url or not key:
            raise ValueError("Missing Supabase credentials")
        
        return create_client(url, key)
    
    def create_compat_views(self):
        """Create compatibility views for all food tables"""
        
        # SQL for food_candidates_compat
        food_candidates_compat_sql = """
        CREATE OR REPLACE VIEW food_candidates_compat AS
        SELECT 
            -- Product key
            LOWER(REPLACE(TRIM(brand), ' ', '_')) || '|' || 
            LOWER(REPLACE(TRIM(product_name), ' ', '_')) || '|' || 
            COALESCE(form, 'unknown') as product_key,
            
            -- Core fields
            brand,
            LOWER(REPLACE(TRIM(brand), ' ', '_')) as brand_slug,
            product_name,
            LOWER(REPLACE(TRIM(product_name), ' ', '_')) as name_slug,
            form,
            
            -- Life stage normalization
            CASE 
                WHEN life_stage IN ('puppy', 'junior', 'growth') THEN 'puppy'
                WHEN life_stage IN ('adult', 'maintenance') THEN 'adult'
                WHEN life_stage IN ('senior', 'mature', '7+', '8+', 'aging') THEN 'senior'
                WHEN life_stage = 'all' OR life_stage LIKE '%all%stages%' THEN 'all'
                WHEN product_name ~* '(senior|mature|7\+|8\+)' THEN 'senior'
                WHEN product_name ~* '(puppy|junior|growth)' THEN 'puppy'
                WHEN product_name ~* '(adult|maintenance)' THEN 'adult'
                WHEN product_name ~* 'all.?life.?stages?' THEN 'all'
                ELSE life_stage
            END as life_stage,
            
            -- Nutrition
            kcal_per_100g,
            CASE 
                WHEN kcal_per_100g IS NOT NULL THEN false
                WHEN protein_percent IS NOT NULL AND fat_percent IS NOT NULL THEN true
                ELSE false
            END as kcal_is_estimated,
            
            -- Calculate Atwater estimate if needed
            CASE 
                WHEN kcal_per_100g IS NOT NULL THEN kcal_per_100g
                WHEN protein_percent IS NOT NULL AND fat_percent IS NOT NULL THEN
                    (protein_percent * 3.5) + (fat_percent * 8.5) + 
                    ((100 - protein_percent - fat_percent - COALESCE(fiber_percent, 0) - 
                      COALESCE(ash_percent::numeric, 8) - COALESCE(moisture_percent::numeric, 10)) * 3.5)
                ELSE NULL
            END as kcal_per_100g_final,
            
            protein_percent,
            fat_percent,
            
            -- Ingredients
            ingredients_tokens,
            
            -- Derive primary protein from tokens
            CASE
                WHEN ingredients_tokens::text ~* 'chicken' THEN 'chicken'
                WHEN ingredients_tokens::text ~* 'beef' THEN 'beef'
                WHEN ingredients_tokens::text ~* 'lamb' THEN 'lamb'
                WHEN ingredients_tokens::text ~* 'salmon' THEN 'salmon'
                WHEN ingredients_tokens::text ~* 'fish' THEN 'fish'
                WHEN ingredients_tokens::text ~* 'turkey' THEN 'turkey'
                WHEN ingredients_tokens::text ~* 'duck' THEN 'duck'
                ELSE NULL
            END as primary_protein,
            
            contains_chicken as has_chicken,
            ingredients_tokens::text ~* 'poultry' as has_poultry,
            
            -- Availability
            available_countries,
            
            -- Price
            price_eur as price_per_kg,
            CASE 
                WHEN price_eur <= 3.5 THEN 'Low'
                WHEN price_eur > 3.5 AND price_eur <= 7.0 THEN 'Mid'
                WHEN price_eur > 7.0 THEN 'High'
                ELSE NULL
            END as price_bucket,
            
            -- Metadata
            image_url,
            source_url as product_url,
            'food_candidates' as source,
            last_seen_at as updated_at,
            
            -- Quality score
            (CASE WHEN life_stage IS NOT NULL THEN 1 ELSE 0 END +
             CASE WHEN kcal_per_100g IS NOT NULL OR 
                      (protein_percent IS NOT NULL AND fat_percent IS NOT NULL) THEN 1 ELSE 0 END +
             CASE WHEN ingredients_tokens IS NOT NULL THEN 1 ELSE 0 END +
             CASE WHEN form IS NOT NULL THEN 1 ELSE 0 END +
             CASE WHEN price_eur IS NOT NULL THEN 1 ELSE 0 END +
             CASE WHEN life_stage IN ('puppy', 'adult', 'senior') THEN 1 ELSE 0 END -
             CASE WHEN kcal_per_100g IS NULL AND protein_percent IS NOT NULL AND fat_percent IS NOT NULL THEN 1 ELSE 0 END
            ) as quality_score
            
        FROM food_candidates;
        """
        
        # SQL for food_candidates_sc_compat
        food_candidates_sc_compat_sql = """
        CREATE OR REPLACE VIEW food_candidates_sc_compat AS
        SELECT 
            -- Product key
            LOWER(REPLACE(TRIM(brand), ' ', '_')) || '|' || 
            LOWER(REPLACE(TRIM(product_name), ' ', '_')) || '|' || 
            COALESCE(form, 'unknown') as product_key,
            
            -- Core fields
            brand,
            LOWER(REPLACE(TRIM(brand), ' ', '_')) as brand_slug,
            product_name,
            LOWER(REPLACE(TRIM(product_name), ' ', '_')) as name_slug,
            form,
            
            -- Life stage normalization from product name
            CASE 
                WHEN product_name ~* '(senior|mature|7\+|8\+)' THEN 'senior'
                WHEN product_name ~* '(puppy|junior|growth)' THEN 'puppy'
                WHEN product_name ~* '(adult|maintenance)' THEN 'adult'
                WHEN product_name ~* 'all.?life.?stages?' THEN 'all'
                ELSE NULL
            END as life_stage,
            
            -- Nutrition (mostly null in this table)
            NULL::numeric as kcal_per_100g,
            false as kcal_is_estimated,
            NULL::numeric as kcal_per_100g_final,
            NULL::numeric as protein_percent,
            NULL::numeric as fat_percent,
            
            -- Ingredients (empty in this table)
            '[]'::jsonb as ingredients_tokens,
            NULL as primary_protein,
            false as has_chicken,
            false as has_poultry,
            
            -- Availability
            available_countries,
            
            -- Price
            NULL::numeric as price_per_kg,
            NULL as price_bucket,
            
            -- Metadata
            image_url,
            source_url as product_url,
            'food_candidates_sc' as source,
            last_seen_at as updated_at,
            
            -- Quality score (lower due to missing data)
            (CASE WHEN form IS NOT NULL THEN 1 ELSE 0 END) as quality_score
            
        FROM food_candidates_sc;
        """
        
        # SQL for food_brands_compat
        food_brands_compat_sql = """
        CREATE OR REPLACE VIEW food_brands_compat AS
        SELECT 
            -- Product key
            LOWER(REPLACE(TRIM(brand), ' ', '_')) || '|' || 
            LOWER(REPLACE(TRIM(name), ' ', '_')) || '|' || 
            'unknown' as product_key,
            
            -- Core fields
            brand,
            LOWER(REPLACE(TRIM(brand), ' ', '_')) as brand_slug,
            name as product_name,
            LOWER(REPLACE(TRIM(name), ' ', '_')) as name_slug,
            'unknown' as form,
            
            -- Life stage normalization
            CASE 
                WHEN life_stage IN ('puppy', 'junior', 'growth') THEN 'puppy'
                WHEN life_stage IN ('adult', 'maintenance') THEN 'adult'
                WHEN life_stage IN ('senior', 'mature', '7+', '8+', 'aging') THEN 'senior'
                WHEN life_stage = 'all' OR life_stage LIKE '%all%stages%' THEN 'all'
                WHEN life_stage = 'puppy and adult' THEN 'all'
                ELSE life_stage
            END as life_stage,
            
            -- Nutrition (not available)
            NULL::numeric as kcal_per_100g,
            false as kcal_is_estimated,
            NULL::numeric as kcal_per_100g_final,
            NULL::numeric as protein_percent,
            NULL::numeric as fat_percent,
            
            -- Ingredients (not available)
            '[]'::jsonb as ingredients_tokens,
            NULL as primary_protein,
            false as has_chicken,
            false as has_poultry,
            
            -- Availability (assume EU for legacy data)
            '["EU"]'::jsonb as available_countries,
            
            -- Price
            NULL::numeric as price_per_kg,
            NULL as price_bucket,
            
            -- Metadata
            NULL as image_url,
            NULL as product_url,
            'food_brands' as source,
            NOW() as updated_at,
            
            -- Quality score
            (CASE WHEN life_stage IS NOT NULL THEN 1 ELSE 0 END +
             CASE WHEN life_stage IN ('puppy', 'adult', 'senior') THEN 1 ELSE 0 END
            ) as quality_score
            
        FROM food_brands;
        """
        
        views = [
            ('food_candidates_compat', food_candidates_compat_sql),
            ('food_candidates_sc_compat', food_candidates_sc_compat_sql),
            ('food_brands_compat', food_brands_compat_sql)
        ]
        
        results = {}
        
        for view_name, sql in views:
            logger.info(f"Creating view: {view_name}")
            try:
                # Execute raw SQL to create view
                # Note: Supabase client doesn't support direct SQL execution
                # We'll need to use the REST API or create these views directly in Supabase
                
                # For now, save SQL to files
                sql_file = f"/Users/sergiubiris/Desktop/lupito-content/sql/{view_name}.sql"
                os.makedirs(os.path.dirname(sql_file), exist_ok=True)
                
                with open(sql_file, 'w') as f:
                    f.write(sql)
                
                logger.info(f"  ✓ SQL saved to {sql_file}")
                
                # Try to get count if view exists
                try:
                    count_resp = self.supabase.table(view_name).select('*', count='exact').execute()
                    results[view_name] = count_resp.count
                    logger.info(f"  ✓ View exists with {count_resp.count} rows")
                    
                    # Get sample data
                    sample_resp = self.supabase.table(view_name).select(
                        'brand, product_name, form, life_stage, kcal_per_100g_final, primary_protein, has_chicken, available_countries, price_bucket'
                    ).limit(5).execute()
                    
                    if sample_resp.data:
                        print(f"\nSample from {view_name}:")
                        for row in sample_resp.data:
                            print(f"  {row['brand']} | {row['product_name'][:30]} | {row['form']} | {row['life_stage']}")
                    
                except Exception as e:
                    logger.warning(f"  ⚠ View doesn't exist yet. Execute SQL in Supabase.")
                    results[view_name] = 0
                    
            except Exception as e:
                logger.error(f"  ✗ Error: {str(e)}")
                results[view_name] = 0
        
        return results
    
    def execute_sql_instructions(self):
        """Generate instructions for executing SQL in Supabase"""
        
        instructions = """
# Instructions to Create Compatibility Views in Supabase

1. Go to Supabase SQL Editor: https://supabase.com/dashboard/project/cibjeqgftuxuezarjsdl/sql

2. Execute each SQL file in order:
   - sql/food_candidates_compat.sql
   - sql/food_candidates_sc_compat.sql  
   - sql/food_brands_compat.sql

3. After creating views, run this verification query:

```sql
SELECT 
    'food_candidates_compat' as view_name, 
    COUNT(*) as row_count 
FROM food_candidates_compat
UNION ALL
SELECT 
    'food_candidates_sc_compat', 
    COUNT(*) 
FROM food_candidates_sc_compat
UNION ALL
SELECT 
    'food_brands_compat', 
    COUNT(*) 
FROM food_brands_compat;
```

4. Sample data query:

```sql
SELECT 
    brand, 
    product_name, 
    form, 
    life_stage, 
    kcal_per_100g_final,
    primary_protein,
    has_chicken,
    price_bucket
FROM food_candidates_compat
LIMIT 5;
```
"""
        
        with open('/Users/sergiubiris/Desktop/lupito-content/sql/CREATE_VIEWS_INSTRUCTIONS.md', 'w') as f:
            f.write(instructions)
        
        print(instructions)
    
    def run(self):
        """Run the compatibility views creation"""
        logger.info("="*80)
        logger.info("C1: Creating Compatibility Views")
        logger.info("="*80)
        
        # Create views
        results = self.create_compat_views()
        
        # Generate instructions
        self.execute_sql_instructions()
        
        # Summary
        print("\n" + "="*80)
        print("C1 Summary:")
        print("-"*80)
        for view_name, count in results.items():
            print(f"  {view_name}: {count} rows")
        print("="*80)
        
        print("\n⚠️  IMPORTANT: Execute the SQL files in Supabase SQL Editor!")
        print("   See sql/CREATE_VIEWS_INSTRUCTIONS.md for details")
        
        return results

if __name__ == "__main__":
    creator = CompatViewsCreator()
    creator.run()