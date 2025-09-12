#!/usr/bin/env python3
"""
Analyze database views and tables to fix SQL scripts
"""

import os
from supabase import create_client
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def check_tables_and_views():
    """Check what tables and views exist in the database"""
    print("=== DATABASE STRUCTURE ANALYSIS ===\n")
    
    # Check main tables
    tables_to_check = [
        'foods_canonical',
        'foods_published_prod',
        'foods_published_preview',
        'foods_published_materialized',
        'brand_alias',
        'foods_ingestion_staging'
    ]
    
    print("1. Checking Tables/Views:")
    print("-" * 40)
    
    existing_objects = []
    
    for table in tables_to_check:
        try:
            # Try to query with limit 0 to check existence
            result = supabase.table(table).select('*').limit(0).execute()
            print(f"✅ {table:30} EXISTS")
            existing_objects.append(table)
            
            # Try to get count
            try:
                result = supabase.table(table).select('*', count='exact').limit(1).execute()
                if hasattr(result, 'count'):
                    print(f"   └─ Row count: {result.count}")
            except:
                pass
                
        except Exception as e:
            error_code = str(e)
            if '42P01' in error_code:
                print(f"❌ {table:30} NOT FOUND")
            else:
                print(f"⚠️  {table:30} ERROR: {str(e)[:50]}")
    
    # Check if these are materialized views or regular views
    print("\n2. Checking View Types:")
    print("-" * 40)
    
    # Try to get information about view types using PostgreSQL information schema
    # Since we can't run raw SQL, we'll try different operations to infer view types
    
    for view_name in ['foods_published_prod', 'foods_published_preview', 'foods_published_materialized']:
        if view_name in existing_objects:
            print(f"\n{view_name}:")
            try:
                # Try to get columns
                result = supabase.table(view_name).select('*').limit(1).execute()
                if result.data:
                    columns = list(result.data[0].keys())
                    print(f"  Columns ({len(columns)}): {', '.join(columns[:5])}...")
            except Exception as e:
                print(f"  Error getting columns: {e}")
    
    return existing_objects

def generate_fixed_refresh_sql(existing_objects):
    """Generate corrected SQL for refreshing views"""
    print("\n3. Generating Corrected SQL:")
    print("-" * 40)
    
    # PostgreSQL doesn't support IF EXISTS with REFRESH MATERIALIZED VIEW
    # We need to use the correct syntax
    
    refresh_sql = """-- Refresh materialized views after brand normalization
-- Execute these in order
-- Note: PostgreSQL doesn't support IF EXISTS with REFRESH MATERIALIZED VIEW

"""
    
    views_to_refresh = []
    
    # Check which views exist and need refresh
    if 'foods_published_materialized' in existing_objects:
        views_to_refresh.append('foods_published_materialized')
    if 'foods_published_prod' in existing_objects:
        views_to_refresh.append('foods_published_prod')
    if 'foods_published_preview' in existing_objects:
        views_to_refresh.append('foods_published_preview')
    
    if not views_to_refresh:
        refresh_sql += "-- No materialized views found to refresh\n"
        refresh_sql += "-- The views might be regular views (not materialized) which don't need refresh\n\n"
    else:
        for i, view in enumerate(views_to_refresh, 1):
            refresh_sql += f"-- {i}. Refresh {view}\n"
            # Use CONCURRENTLY only if the view has a unique index
            # Without IF EXISTS clause which is not supported
            refresh_sql += f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view};\n\n"
    
    # Add verification query
    refresh_sql += """-- Verify changes in brand distribution
SELECT 
    brand,
    COUNT(*) as product_count,
    COUNT(DISTINCT brand_slug) as unique_slugs
FROM foods_canonical
WHERE brand IS NOT NULL
GROUP BY brand
ORDER BY product_count DESC
LIMIT 20;

-- Check if brand_alias table was created and populated
SELECT 
    COUNT(*) as total_aliases,
    COUNT(DISTINCT canonical_brand) as unique_brands
FROM brand_alias;
"""
    
    # Save the corrected SQL
    with open('sql/refresh_views_fixed.sql', 'w') as f:
        f.write(refresh_sql)
    
    print("✅ Created: sql/refresh_views_fixed.sql")
    
    # Also create a safer version without CONCURRENTLY
    safe_refresh_sql = """-- Safe refresh of materialized views (without CONCURRENTLY)
-- Use this if the CONCURRENTLY version fails

"""
    
    for view in views_to_refresh:
        safe_refresh_sql += f"-- Refresh {view}\n"
        safe_refresh_sql += f"REFRESH MATERIALIZED VIEW {view};\n\n"
    
    safe_refresh_sql += """-- Verify the refresh worked
SELECT 
    brand,
    COUNT(*) as product_count
FROM foods_canonical
GROUP BY brand
ORDER BY product_count DESC
LIMIT 10;
"""
    
    with open('sql/refresh_views_safe.sql', 'w') as f:
        f.write(safe_refresh_sql)
    
    print("✅ Created: sql/refresh_views_safe.sql")
    
    return refresh_sql

def check_brand_alias_requirements():
    """Check what's needed for brand_alias table"""
    print("\n4. Brand Alias Table Requirements:")
    print("-" * 40)
    
    try:
        # Check if brand_alias exists
        result = supabase.table('brand_alias').select('*').limit(1).execute()
        print("✅ brand_alias table EXISTS")
        
        # Get count
        result = supabase.table('brand_alias').select('*', count='exact').limit(0).execute()
        count = result.count if hasattr(result, 'count') else 0
        print(f"   Current row count: {count}")
        
        if count == 0:
            print("   ⚠️  Table is empty - needs seeding")
        
    except Exception as e:
        if '42P01' in str(e):
            print("❌ brand_alias table DOES NOT EXIST")
            print("\n   Required SQL to create:")
            print("   " + "-"*35)
            
            create_sql = """   CREATE TABLE brand_alias (
       alias VARCHAR(255) PRIMARY KEY,
       canonical_brand VARCHAR(255) NOT NULL,
       created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
       updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
   );
   
   CREATE INDEX idx_brand_alias_canonical 
   ON brand_alias(canonical_brand);"""
            
            print(create_sql)
            print("   " + "-"*35)
            
            # Save this as a standalone SQL file
            with open('sql/create_brand_alias_only.sql', 'w') as f:
                f.write("""-- Create brand_alias table only (no IF NOT EXISTS)
CREATE TABLE brand_alias (
    alias VARCHAR(255) PRIMARY KEY,
    canonical_brand VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_brand_alias_canonical 
ON brand_alias(canonical_brand);
""")
            print("\n   ✅ Saved to: sql/create_brand_alias_only.sql")

def main():
    # Check what exists
    existing_objects = check_tables_and_views()
    
    # Generate fixed SQL
    generate_fixed_refresh_sql(existing_objects)
    
    # Check brand_alias requirements
    check_brand_alias_requirements()
    
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    
    print("\n📁 Generated Files:")
    print("  - sql/refresh_views_fixed.sql    (corrected syntax)")
    print("  - sql/refresh_views_safe.sql     (without CONCURRENTLY)")
    print("  - sql/create_brand_alias_only.sql (if table missing)")
    
    print("\n⚠️  IMPORTANT:")
    print("  1. The error 'syntax error at or near EXISTS' happens because")
    print("     PostgreSQL doesn't support 'IF EXISTS' with REFRESH MATERIALIZED VIEW")
    print("  2. Use sql/refresh_views_fixed.sql for the corrected version")
    print("  3. If CONCURRENTLY fails, use sql/refresh_views_safe.sql instead")
    
    print("\n🔧 Next Steps:")
    print("  1. If brand_alias doesn't exist, run: sql/create_brand_alias_only.sql")
    print("  2. Run the seeding script to populate brand_alias")
    print("  3. Execute: sql/refresh_views_fixed.sql (or _safe.sql if needed)")

if __name__ == "__main__":
    main()