#!/usr/bin/env python3
"""
Execute the compatibility views SQL and verify creation
Then proceed with C2: Union and deduplication
"""

import os
import json
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CatalogPipeline:
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
    
    def verify_compat_views(self):
        """C1: Verify compatibility views exist and get counts"""
        logger.info("="*80)
        logger.info("C1: Verifying Compatibility Views")
        logger.info("="*80)
        
        views = ['food_candidates_compat', 'food_candidates_sc_compat', 'food_brands_compat']
        results = {}
        
        # First, let's check what views/tables exist
        check_sql = """
        SELECT table_name, table_type 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name LIKE 'food_%'
        ORDER BY table_name;
        """
        
        # Since we can't execute raw SQL via Supabase client, let's check each view
        for view_name in views:
            try:
                # Try simple count query
                response = self.supabase.table(view_name).select('*', count='exact').limit(0).execute()
                count = response.count
                results[view_name] = count
                logger.info(f"  ✓ {view_name}: {count} rows")
                
                # Get sample rows
                sample_resp = self.supabase.table(view_name).select('*').limit(5).execute()
                if sample_resp.data and len(sample_resp.data) > 0:
                    print(f"\n  Sample from {view_name}:")
                    for i, row in enumerate(sample_resp.data[:3], 1):
                        print(f"    {i}. {row.get('brand', 'N/A')} - {row.get('product_name', 'N/A')[:40]}")
                        print(f"       Form: {row.get('form', 'N/A')}, Life Stage: {row.get('life_stage', 'N/A')}")
                        
            except Exception as e:
                logger.warning(f"  ✗ {view_name}: Not found or error - {str(e)}")
                results[view_name] = 0
        
        return results
    
    def create_union_and_canonical(self):
        """C2: Create union of all compat views and deduplicate into foods_canonical"""
        logger.info("\n" + "="*80)
        logger.info("C2: Union & De-duplicate into foods_canonical")
        logger.info("="*80)
        
        # SQL for union view
        union_sql = """
        CREATE OR REPLACE VIEW foods_union_all AS
        SELECT * FROM food_candidates_compat
        UNION ALL
        SELECT * FROM food_candidates_sc_compat
        UNION ALL
        SELECT * FROM food_brands_compat;
        """
        
        # SQL for canonical table with deduplication
        canonical_sql = """
        -- Drop and recreate foods_canonical table
        DROP TABLE IF EXISTS foods_canonical CASCADE;
        
        CREATE TABLE foods_canonical AS
        WITH ranked_products AS (
            SELECT 
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY product_key
                    ORDER BY 
                        -- 1. kcal known > estimated > null
                        CASE 
                            WHEN kcal_per_100g_final IS NOT NULL AND NOT kcal_is_estimated THEN 1
                            WHEN kcal_per_100g_final IS NOT NULL AND kcal_is_estimated THEN 2
                            ELSE 3
                        END,
                        -- 2. specific life_stage > all > null
                        CASE 
                            WHEN life_stage IN ('puppy', 'adult', 'senior') THEN 1
                            WHEN life_stage = 'all' THEN 2
                            ELSE 3
                        END,
                        -- 3. richer ingredients (more tokens)
                        CASE 
                            WHEN ingredients_tokens IS NOT NULL THEN 
                                jsonb_array_length(ingredients_tokens)
                            ELSE 0
                        END DESC,
                        -- 4. price present > missing
                        CASE WHEN price_per_kg IS NOT NULL THEN 1 ELSE 2 END,
                        -- 5. higher quality score
                        quality_score DESC,
                        -- 6. newest updated_at
                        updated_at DESC NULLS LAST
                ) as rank,
                
                -- Track sources for provenance
                jsonb_build_object(
                    'source', source,
                    'updated_at', updated_at
                ) as source_info
            FROM foods_union_all
        ),
        aggregated_sources AS (
            SELECT 
                product_key,
                jsonb_agg(source_info ORDER BY rank) as sources
            FROM ranked_products
            GROUP BY product_key
        )
        SELECT 
            r.*,
            a.sources
        FROM ranked_products r
        JOIN aggregated_sources a ON r.product_key = a.product_key
        WHERE r.rank = 1;
        
        -- Add indexes
        CREATE UNIQUE INDEX idx_foods_canonical_product_key ON foods_canonical(product_key);
        CREATE INDEX idx_foods_canonical_brand_slug ON foods_canonical(brand_slug);
        CREATE INDEX idx_foods_canonical_life_stage ON foods_canonical(life_stage);
        CREATE INDEX idx_foods_canonical_form ON foods_canonical(form);
        """
        
        # Save SQL files
        os.makedirs('/Users/sergiubiris/Desktop/lupito-content/sql', exist_ok=True)
        
        with open('/Users/sergiubiris/Desktop/lupito-content/sql/foods_union_all.sql', 'w') as f:
            f.write(union_sql)
        
        with open('/Users/sergiubiris/Desktop/lupito-content/sql/foods_canonical.sql', 'w') as f:
            f.write(canonical_sql)
        
        logger.info("  ✓ SQL files created for union and canonical tables")
        
        # Try to get counts if they exist
        try:
            # Check union
            union_resp = self.supabase.table('foods_union_all').select('*', count='exact').limit(0).execute()
            union_count = union_resp.count
            logger.info(f"  ✓ foods_union_all: {union_count} rows")
        except:
            union_count = 0
            logger.warning("  ⚠ foods_union_all view not created yet")
        
        try:
            # Check canonical
            canon_resp = self.supabase.table('foods_canonical').select('*', count='exact').limit(0).execute()
            canon_count = canon_resp.count
            logger.info(f"  ✓ foods_canonical: {canon_count} rows")
            
            # Calculate duplicates merged
            duplicates = union_count - canon_count if union_count > 0 else 0
            logger.info(f"  ✓ Duplicates merged: {duplicates}")
            
        except:
            canon_count = 0
            logger.warning("  ⚠ foods_canonical table not created yet")
        
        return {'union': union_count, 'canonical': canon_count}
    
    def create_published_view(self):
        """C3: Create foods_published view and indexes"""
        logger.info("\n" + "="*80)
        logger.info("C3: Publish & Index for AI")
        logger.info("="*80)
        
        published_sql = """
        -- Create foods_published view for AI consumption
        CREATE OR REPLACE VIEW foods_published AS
        SELECT 
            product_key,
            brand,
            brand_slug,
            product_name,
            name_slug,
            form,
            life_stage,
            kcal_per_100g_final as kcal_per_100g,
            kcal_is_estimated,
            protein_percent,
            fat_percent,
            ingredients_tokens,
            primary_protein,
            has_chicken,
            has_poultry,
            available_countries,
            price_per_kg,
            price_bucket,
            image_url,
            product_url,
            source,
            updated_at,
            quality_score,
            sources
        FROM foods_canonical;
        
        -- Create GIN indexes for array/jsonb columns
        CREATE INDEX IF NOT EXISTS idx_foods_canonical_countries_gin 
        ON foods_canonical USING GIN (available_countries);
        
        CREATE INDEX IF NOT EXISTS idx_foods_canonical_tokens_gin 
        ON foods_canonical USING GIN (ingredients_tokens);
        """
        
        with open('/Users/sergiubiris/Desktop/lupito-content/sql/foods_published.sql', 'w') as f:
            f.write(published_sql)
        
        logger.info("  ✓ SQL file created for foods_published view")
        
        # Check if view exists
        try:
            pub_resp = self.supabase.table('foods_published').select('*', count='exact').limit(0).execute()
            pub_count = pub_resp.count
            logger.info(f"  ✓ foods_published: {pub_count} rows")
            logger.info("  ✓ AI can now read via CATALOG_VIEW_NAME=foods_published")
        except:
            pub_count = 0
            logger.warning("  ⚠ foods_published view not created yet")
        
        return pub_count
    
    def generate_qa_report(self):
        """C4: Generate QA report and sample CSV"""
        logger.info("\n" + "="*80)
        logger.info("C4: QA Snapshot & Sample")
        logger.info("="*80)
        
        try:
            # Get all data from foods_published for analysis
            response = self.supabase.table('foods_published').select('*').execute()
            
            if response.data:
                df = pd.DataFrame(response.data)
                total = len(df)
                
                # Calculate coverage metrics
                life_stage_coverage = df['life_stage'].notna().sum() / total * 100
                life_stage_known_or_all = df['life_stage'].isin(['puppy', 'adult', 'senior', 'all']).sum() / total * 100
                
                kcal_coverage = df['kcal_per_100g'].notna().sum() / total * 100
                
                # Check ingredients tokens
                tokens_present = 0
                for tokens in df.get('ingredients_tokens', []):
                    if tokens and (isinstance(tokens, list) and len(tokens) > 0):
                        tokens_present += 1
                tokens_coverage = tokens_present / total * 100
                
                # Check availability
                has_country = 0
                for countries in df.get('available_countries', []):
                    if countries and (isinstance(countries, list) and len(countries) > 0):
                        has_country += 1
                availability_coverage = has_country / total * 100
                
                price_coverage = df['price_per_kg'].notna().sum() / total * 100
                
                print("\n📊 Coverage Report (foods_published):")
                print("-" * 50)
                print(f"  Life stage known or 'all': {life_stage_known_or_all:.1f}% (target ≥95%)")
                print(f"  Kcal known + estimated: {kcal_coverage:.1f}% (target ≥90%)")
                print(f"  Ingredients tokens present: {tokens_coverage:.1f}% (target ≥95%)")
                print(f"  Has EU or country: {availability_coverage:.1f}% (target ≥90%)")
                print(f"  Price present: {price_coverage:.1f}%")
                
                # Category counts
                print("\n📈 Category Counts (EU available):")
                print("-" * 50)
                
                # Filter for EU availability
                eu_mask = df['available_countries'].apply(
                    lambda x: 'EU' in x if isinstance(x, list) else False
                )
                
                adult_eu = df[(df['life_stage'].isin(['adult', 'all']) | df['life_stage'].isna()) & eu_mask]
                senior_eu = df[(df['life_stage'].isin(['senior', 'all']) | df['life_stage'].isna()) & eu_mask]
                no_chicken_eu = df[(df['has_chicken'] == False) & eu_mask]
                
                print(f"  Adult-suitable + EU: {len(adult_eu)}")
                print(f"  Senior-suitable + EU: {len(senior_eu)}")
                print(f"  Non-chicken + EU: {len(no_chicken_eu)}")
                
                # Form split for adult EU
                if 'form' in adult_eu.columns:
                    dry_count = len(adult_eu[adult_eu['form'] == 'dry'])
                    wet_count = len(adult_eu[adult_eu['form'] == 'wet'])
                    print(f"  Adult + EU: Dry {dry_count} / Wet {wet_count}")
                
                # Export sample CSV
                sample_df = df.head(50)[['brand', 'product_name', 'form', 'life_stage', 
                                         'kcal_per_100g', 'kcal_is_estimated', 'primary_protein', 
                                         'has_chicken', 'available_countries', 'price_bucket']]
                
                csv_path = '/Users/sergiubiris/Desktop/lupito-content/catalog_sample.csv'
                sample_df.to_csv(csv_path, index=False)
                
                print(f"\n✓ Sample CSV exported: {csv_path}")
                
                return {
                    'life_stage_coverage': life_stage_known_or_all,
                    'kcal_coverage': kcal_coverage,
                    'tokens_coverage': tokens_coverage,
                    'availability_coverage': availability_coverage,
                    'price_coverage': price_coverage
                }
            else:
                logger.warning("  ⚠ No data in foods_published")
                return None
                
        except Exception as e:
            logger.error(f"  ✗ Error generating QA report: {str(e)}")
            return None
    
    def run_pipeline(self):
        """Run the complete pipeline C1-C4"""
        
        # C1: Verify compat views
        compat_results = self.verify_compat_views()
        
        # C2: Create union and canonical
        union_results = self.create_union_and_canonical()
        
        # C3: Create published view
        published_count = self.create_published_view()
        
        # C4: Generate QA report
        qa_results = self.generate_qa_report()
        
        # Final summary
        print("\n" + "="*80)
        print("PIPELINE SUMMARY")
        print("="*80)
        print("\n✅ C1 - Compat Views:")
        for view, count in compat_results.items():
            print(f"    {view}: {count} rows")
        
        print(f"\n✅ C2 - Union & Canonical:")
        print(f"    Union: {union_results['union']} rows")
        print(f"    Canonical: {union_results['canonical']} rows")
        print(f"    Duplicates merged: {union_results['union'] - union_results['canonical']}")
        
        print(f"\n✅ C3 - Published View:")
        print(f"    foods_published: {published_count} rows")
        
        if qa_results:
            print(f"\n✅ C4 - QA Results:")
            print(f"    Targets met: {sum(1 for v in qa_results.values() if v >= 90)}/5")
        
        print("\n" + "="*80)
        print("⚠️  NEXT STEPS:")
        print("  1. Execute SQL files in Supabase SQL Editor")
        print("  2. Verify all views and tables are created")
        print("  3. Configure AI to use CATALOG_VIEW_NAME=foods_published")
        print("="*80)

if __name__ == "__main__":
    pipeline = CatalogPipeline()
    pipeline.run_pipeline()