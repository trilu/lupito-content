#!/usr/bin/env python3
"""
Prompt 4: Recompose Preview views & refresh metrics
Goal: Make Preview the single source for validation, then compute brand metrics
"""

import os
import json
from datetime import datetime
import pandas as pd
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class PreviewRecomposer:
    def __init__(self):
        self.supabase = self._init_supabase()
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def _init_supabase(self) -> Client:
        """Initialize Supabase client"""
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
        return create_client(url, key)
    
    def rebuild_preview_view(self):
        """Generate SQL to rebuild foods_published_preview"""
        print("\n" + "="*60)
        print(f"PROMPT 4: RECOMPOSE PREVIEW VIEWS")
        print(f"Timestamp: {self.timestamp}")
        print("="*60)
        
        sql = """-- Rebuild foods_published_preview with updated canonical data
DROP VIEW IF EXISTS foods_published_preview CASCADE;

CREATE OR REPLACE VIEW foods_published_preview AS
SELECT 
    f.id,
    f.brand,
    f.product_name,
    f.brand_slug,
    f.product_variant,
    f.description,
    f.form,
    f.life_stage,
    f.special_needs,
    f.breed_size,
    
    -- Ensure arrays are JSONB
    f.ingredients_tokens::jsonb AS ingredients_tokens,
    f.available_countries::jsonb AS available_countries,
    f.sources::jsonb AS sources,
    COALESCE(f.allergens::jsonb, '[]'::jsonb) AS allergens,
    
    -- Nutrition & Pricing
    f.kcal_per_100g,
    f.protein_percent,
    f.fat_percent,
    f.fiber_percent,
    f.moisture_percent,
    f.price,
    f.price_per_kg,
    f.price_bucket,
    f.pack_size_raw,
    
    -- Metadata
    f.created_at,
    f.updated_at,
    f.data_source,
    
    -- Allowlist status
    COALESCE(ba.status, 'PENDING') AS allowlist_status,
    ba.updated_at AS allowlist_updated_at
FROM 
    foods_canonical f
LEFT JOIN 
    brand_allowlist ba ON f.brand_slug = ba.brand_slug
WHERE 
    -- Include ACTIVE and PENDING for preview
    (ba.status IN ('ACTIVE', 'PENDING') OR ba.status IS NULL);

-- Grant permissions
GRANT SELECT ON foods_published_preview TO authenticated;
GRANT SELECT ON foods_published_preview TO anon;
"""
        
        print("\n📋 SQL for rebuilding Preview view:")
        print("-" * 40)
        print(sql)
        
        sql_file = f"sql/rebuild_preview_view_{self.timestamp}.sql"
        os.makedirs("sql", exist_ok=True)
        with open(sql_file, 'w') as f:
            f.write(sql)
        
        print(f"\n✅ SQL saved to: {sql_file}")
        print("\n⚠️  Please run this SQL manually in Supabase")
        
        return sql_file
    
    def refresh_brand_quality_mv(self):
        """Generate SQL to refresh the brand quality materialized view"""
        print("\n📊 REFRESHING BRAND QUALITY METRICS")
        print("-" * 40)
        
        sql = """-- Refresh the brand quality materialized view for Preview
REFRESH MATERIALIZED VIEW CONCURRENTLY foods_brand_quality_preview_mv;

-- Verify the refresh
SELECT 
    brand_slug,
    brand_name,
    sku_count,
    form_coverage_pct,
    life_stage_coverage_pct,
    ingredients_coverage_pct,
    kcal_valid_pct,
    price_coverage_pct,
    completion_pct,
    last_updated
FROM 
    foods_brand_quality_preview_mv
ORDER BY 
    completion_pct DESC,
    sku_count DESC
LIMIT 5;
"""
        
        print("SQL for refreshing materialized view:")
        print(sql)
        
        sql_file = f"sql/refresh_brand_quality_{self.timestamp}.sql"
        with open(sql_file, 'w') as f:
            f.write(sql)
        
        print(f"\n✅ SQL saved to: {sql_file}")
        
        return sql_file
    
    def generate_brand_scoreboard(self):
        """Generate Brand Scoreboard from Preview data"""
        print("\n📈 GENERATING BRAND SCOREBOARD (PREVIEW)")
        print("-" * 40)
        
        try:
            # Fetch brand quality metrics from the materialized view
            response = self.supabase.table('foods_brand_quality_preview_mv').select('*').execute()
            metrics_df = pd.DataFrame(response.data)
            
            if len(metrics_df) == 0:
                print("⚠️  No data in foods_brand_quality_preview_mv")
                print("    Please refresh the materialized view first")
                return None
            
            # Sort by completion percentage and SKU count
            metrics_df = metrics_df.sort_values(['completion_pct', 'sku_count'], ascending=False)
            
            # Define gates
            gates = {
                'form': 90,
                'life_stage': 95,
                'ingredients': 85,
                'kcal': 90
            }
            
            # Assign status based on gates
            def get_status(row):
                if (row['form_coverage_pct'] >= gates['form'] and
                    row['life_stage_coverage_pct'] >= gates['life_stage'] and
                    row['ingredients_coverage_pct'] >= gates['ingredients'] and
                    row['kcal_valid_pct'] >= gates['kcal']):
                    return "✅ PASS"
                elif (row['form_coverage_pct'] >= gates['form'] * 0.9 and
                      row['life_stage_coverage_pct'] >= gates['life_stage'] * 0.9):
                    return "⚠️ NEAR"
                else:
                    return "❌ TODO"
            
            metrics_df['status'] = metrics_df.apply(get_status, axis=1)
            
            # Generate scoreboard report
            report_file = f"reports/BRAND_SCOREBOARD_PREVIEW_{self.timestamp}.md"
            os.makedirs("reports", exist_ok=True)
            
            content = f"""# BRAND SCOREBOARD (PREVIEW)

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Total Brands**: {len(metrics_df)}

## Coverage Gates
- Form: ≥90%
- Life Stage: ≥95%
- Ingredients: ≥85%
- Kcal Valid: ≥90%

## Top Brands by Completion

| Status | Brand | SKUs | Completion | Form | Life Stage | Ingredients | Kcal Valid |
|--------|-------|------|------------|------|------------|-------------|------------|
"""
            
            # Add top 20 brands
            for _, row in metrics_df.head(20).iterrows():
                content += (f"| {row['status']} | {row['brand_name'][:25]} | "
                          f"{row['sku_count']} | {row['completion_pct']:.1f}% | "
                          f"{row['form_coverage_pct']:.1f}% | "
                          f"{row['life_stage_coverage_pct']:.1f}% | "
                          f"{row['ingredients_coverage_pct']:.1f}% | "
                          f"{row['kcal_valid_pct']:.1f}% |\n")
            
            # Summary statistics
            passing = len(metrics_df[metrics_df['status'] == "✅ PASS"])
            near = len(metrics_df[metrics_df['status'] == "⚠️ NEAR"])
            todo = len(metrics_df[metrics_df['status'] == "❌ TODO"])
            
            content += f"""

## Summary

- **✅ PASS**: {passing} brands ({passing/len(metrics_df)*100:.1f}%)
- **⚠️ NEAR**: {near} brands ({near/len(metrics_df)*100:.1f}%)
- **❌ TODO**: {todo} brands ({todo/len(metrics_df)*100:.1f}%)

### Total SKUs by Status
- PASS brands: {metrics_df[metrics_df['status'] == "✅ PASS"]['sku_count'].sum():,} SKUs
- NEAR brands: {metrics_df[metrics_df['status'] == "⚠️ NEAR"]['sku_count'].sum():,} SKUs
- TODO brands: {metrics_df[metrics_df['status'] == "❌ TODO"]['sku_count'].sum():,} SKUs

## Brands Ready for Promotion

The following brands meet all coverage gates and can be promoted to Production:

"""
            
            ready_brands = metrics_df[metrics_df['status'] == "✅ PASS"]
            if len(ready_brands) > 0:
                for _, row in ready_brands.iterrows():
                    content += f"- **{row['brand_name']}**: {row['sku_count']} SKUs (completion: {row['completion_pct']:.1f}%)\n"
            else:
                content += "⚠️ No brands currently meet all gates for promotion.\n"
            
            # Write report
            with open(report_file, 'w') as f:
                f.write(content)
            
            print(f"✅ Scoreboard saved to: {report_file}")
            
            # Print summary to console
            print(f"\n📊 SCOREBOARD SUMMARY:")
            print(f"  Total brands: {len(metrics_df)}")
            print(f"  ✅ PASS: {passing} brands")
            print(f"  ⚠️ NEAR: {near} brands")
            print(f"  ❌ TODO: {todo} brands")
            
            return report_file
            
        except Exception as e:
            print(f"❌ Error generating scoreboard: {e}")
            
            # Create fallback query
            fallback_sql = """-- Query to generate brand scoreboard manually
SELECT 
    brand_slug,
    brand_name,
    sku_count,
    ROUND(completion_pct, 1) as completion_pct,
    ROUND(form_coverage_pct, 1) as form_pct,
    ROUND(life_stage_coverage_pct, 1) as life_stage_pct,
    ROUND(ingredients_coverage_pct, 1) as ingredients_pct,
    ROUND(kcal_valid_pct, 1) as kcal_pct,
    CASE 
        WHEN form_coverage_pct >= 90 
         AND life_stage_coverage_pct >= 95 
         AND ingredients_coverage_pct >= 85 
         AND kcal_valid_pct >= 90 
        THEN 'PASS'
        WHEN form_coverage_pct >= 81 
         AND life_stage_coverage_pct >= 85.5 
        THEN 'NEAR'
        ELSE 'TODO'
    END as status
FROM 
    foods_brand_quality_preview_mv
ORDER BY 
    completion_pct DESC,
    sku_count DESC;
"""
            
            print("\n📋 Fallback SQL query:")
            print(fallback_sql)
            
            sql_file = f"sql/brand_scoreboard_query_{self.timestamp}.sql"
            with open(sql_file, 'w') as f:
                f.write(fallback_sql)
            
            print(f"\n✅ Query saved to: {sql_file}")
            
            return None
    
    def run(self):
        """Execute Prompt 4 tasks"""
        print("\n" + "="*60)
        print("EXECUTING PROMPT 4: RECOMPOSE PREVIEW VIEWS")
        print("="*60)
        
        # Task 1: Rebuild Preview view
        view_sql = self.rebuild_preview_view()
        
        # Task 2: Refresh materialized view
        refresh_sql = self.refresh_brand_quality_mv()
        
        # Task 3: Generate scoreboard
        scoreboard = self.generate_brand_scoreboard()
        
        print("\n" + "="*60)
        print("PROMPT 4 COMPLETE")
        print("="*60)
        print("\n📋 Next Steps:")
        print("1. Run the SQL scripts in order:")
        print(f"   - {view_sql}")
        print(f"   - {refresh_sql}")
        print("2. Review the Brand Scoreboard")
        print("3. Proceed to Prompt 5 for acceptance gates")
        
        return {
            'view_sql': view_sql,
            'refresh_sql': refresh_sql,
            'scoreboard': scoreboard
        }

if __name__ == "__main__":
    recomposer = PreviewRecomposer()
    recomposer.run()