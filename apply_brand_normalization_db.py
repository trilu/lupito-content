#!/usr/bin/env python3
"""
Apply brand normalization to database safely with audit trail - AADF-2B
"""

import os
import yaml
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from supabase import create_client
from dotenv import load_dotenv
from typing import Dict, List, Tuple

load_dotenv()

# Database connection
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def load_brand_alias_map() -> Dict[str, List[str]]:
    """Load the approved brand alias map"""
    with open('data/brand_alias_map.yaml', 'r') as f:
        return yaml.safe_load(f)

def create_brand_alias_table():
    """Create or refresh brand_alias table"""
    print("1. Creating/refreshing brand_alias table...")
    
    # Create table SQL
    create_sql = """
-- Create brand_alias table for normalization
CREATE TABLE IF NOT EXISTS brand_alias (
    alias VARCHAR(255) PRIMARY KEY,
    canonical_brand VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_brand_alias_canonical ON brand_alias(canonical_brand);
"""
    
    # Save SQL for manual execution
    Path('sql').mkdir(exist_ok=True)
    with open('sql/create_brand_alias_table.sql', 'w') as f:
        f.write(create_sql)
    
    print("   SQL saved to: sql/create_brand_alias_table.sql")
    print("   Please execute this SQL manually if table doesn't exist")
    
    return True

def load_aliases_to_table(brand_map: Dict[str, List[str]]) -> int:
    """Load brand aliases into the table"""
    print("\n2. Loading brand aliases...")
    
    alias_data = []
    
    for canonical_brand, aliases in brand_map.items():
        # Add the canonical brand itself as an alias
        alias_data.append({
            'alias': canonical_brand.lower(),
            'canonical_brand': canonical_brand
        })
        
        # Add all aliases
        for alias in aliases:
            if alias:  # Skip empty aliases
                alias_data.append({
                    'alias': alias.lower(),
                    'canonical_brand': canonical_brand
                })
    
    # Upsert to database
    try:
        # Clear existing data
        supabase.table('brand_alias').delete().neq('alias', '').execute()
        
        # Insert new data in batches
        batch_size = 100
        for i in range(0, len(alias_data), batch_size):
            batch = alias_data[i:i+batch_size]
            supabase.table('brand_alias').insert(batch).execute()
        
        print(f"   Loaded {len(alias_data)} alias mappings")
        return len(alias_data)
    except Exception as e:
        print(f"   Warning: Could not load to database: {e}")
        print("   Saving to CSV instead...")
        
        # Save to CSV as backup
        df = pd.DataFrame(alias_data)
        df.to_csv('data/brand_alias_table.csv', index=False)
        print("   Saved to: data/brand_alias_table.csv")
        return len(alias_data)

def capture_before_state() -> Tuple[pd.DataFrame, Dict]:
    """Capture current state for audit"""
    print("\n3. Capturing before state...")
    
    # Get current brand distribution
    response = supabase.table('foods_canonical').select('product_key, brand, brand_slug, product_name').execute()
    before_df = pd.DataFrame(response.data)
    
    # Create audit directory
    Path('data/audit').mkdir(parents=True, exist_ok=True)
    
    # Save snapshot
    before_df.to_csv('data/audit/before_normalization.csv', index=False)
    
    # Calculate statistics
    stats = {
        'total_products': len(before_df),
        'unique_brands': before_df['brand'].nunique(),
        'null_brands': before_df['brand'].isna().sum(),
        'brand_distribution': before_df['brand'].value_counts().to_dict()
    }
    
    print(f"   Total products: {stats['total_products']}")
    print(f"   Unique brands: {stats['unique_brands']}")
    print(f"   Null brands: {stats['null_brands']}")
    
    return before_df, stats

def apply_normalization(brand_map: Dict[str, List[str]], before_df: pd.DataFrame) -> Tuple[List, List]:
    """Apply brand normalization to foods_canonical"""
    print("\n4. Applying brand normalization...")
    
    updates = []
    rollback_data = []
    
    # Build reverse mapping (alias -> canonical)
    alias_to_canonical = {}
    for canonical, aliases in brand_map.items():
        # Add canonical itself
        alias_to_canonical[canonical.lower()] = canonical
        # Add all aliases
        for alias in aliases:
            if alias:
                alias_to_canonical[alias.lower()] = canonical
    
    # Process each product
    for _, row in before_df.iterrows():
        current_brand = row['brand']
        current_slug = row['brand_slug']
        product_id = row['product_key']
        
        # Skip if brand is null
        if pd.isna(current_brand):
            continue
        
        # Check if brand needs normalization
        brand_lower = current_brand.lower()
        
        if brand_lower in alias_to_canonical:
            new_brand = alias_to_canonical[brand_lower]
            new_slug = new_brand.lower().replace(' ', '-').replace("'", '')
            
            # Only update if different
            if new_brand != current_brand or new_slug != current_slug:
                updates.append({
                    'product_key': product_id,
                    'brand': new_brand,
                    'brand_slug': new_slug
                })
                
                rollback_data.append({
                    'product_key': product_id,
                    'brand': current_brand,
                    'brand_slug': current_slug
                })
    
    print(f"   Found {len(updates)} products to update")
    
    if updates:
        # Apply updates in batches
        batch_size = 50
        updated_count = 0
        
        for i in range(0, len(updates), batch_size):
            batch = updates[i:i+batch_size]
            
            try:
                for update in batch:
                    supabase.table('foods_canonical').update({
                        'brand': update['brand'],
                        'brand_slug': update['brand_slug']
                    }).eq('product_key', update['product_key']).execute()
                    
                updated_count += len(batch)
                if (updated_count % 100) == 0:
                    print(f"   Updated {updated_count}/{len(updates)} products...")
            except Exception as e:
                print(f"   Error updating batch: {e}")
                break
        
        print(f"   Successfully updated {updated_count} products")
    
    return updates, rollback_data

def refresh_materialized_views():
    """Generate SQL to refresh materialized views"""
    print("\n5. Generating view refresh SQL...")
    
    refresh_sql = """-- Refresh materialized views after brand normalization
-- Execute these in order

-- 1. Refresh base materialized view
REFRESH MATERIALIZED VIEW CONCURRENTLY IF EXISTS foods_published_materialized;

-- 2. Refresh production view
REFRESH MATERIALIZED VIEW CONCURRENTLY IF EXISTS foods_published_prod;

-- 3. Refresh preview view  
REFRESH MATERIALIZED VIEW CONCURRENTLY IF EXISTS foods_published_preview;

-- 4. Verify changes
SELECT brand, COUNT(*) as product_count
FROM foods_published_prod
GROUP BY brand
ORDER BY product_count DESC
LIMIT 20;
"""
    
    with open('sql/refresh_views_after_normalization.sql', 'w') as f:
        f.write(refresh_sql)
    
    print("   SQL saved to: sql/refresh_views_after_normalization.sql")
    print("   Please execute this SQL manually to refresh views")

def generate_audit_report(before_stats: Dict, updates: List, rollback_data: List):
    """Generate comprehensive audit report"""
    print("\n6. Generating audit report...")
    
    # Capture after state
    response = supabase.table('foods_canonical').select('product_key, brand, brand_slug').execute()
    after_df = pd.DataFrame(response.data)
    
    after_stats = {
        'total_products': len(after_df),
        'unique_brands': after_df['brand'].nunique(),
        'null_brands': after_df['brand'].isna().sum(),
        'brand_distribution': after_df['brand'].value_counts().to_dict()
    }
    
    # Generate report
    report = f"""# Brand Normalization Audit Report
Generated: {datetime.now().isoformat()}

## Summary
- **Products Updated**: {len(updates)}
- **Brands Before**: {before_stats['unique_brands']}
- **Brands After**: {after_stats['unique_brands']}
- **Brand Reduction**: {before_stats['unique_brands'] - after_stats['unique_brands']}

## Top Brand Changes

| Brand | Products Before | Products After | Change |
|-------|----------------|----------------|--------|
"""
    
    # Compare top brands
    before_top = dict(sorted(before_stats['brand_distribution'].items(), 
                            key=lambda x: x[1], reverse=True)[:20])
    after_top = dict(sorted(after_stats['brand_distribution'].items(), 
                           key=lambda x: x[1], reverse=True)[:20])
    
    all_top_brands = set(before_top.keys()) | set(after_top.keys())
    
    for brand in sorted(all_top_brands):
        before_count = before_top.get(brand, 0)
        after_count = after_top.get(brand, 0)
        if before_count != after_count:
            change = after_count - before_count
            report += f"| {brand} | {before_count} | {after_count} | {change:+d} |\n"
    
    report += f"""
## Updated Products Sample

| Product Key | Old Brand | New Brand |
|-------------|-----------|-----------|
"""
    
    for update in updates[:20]:
        old_brand = next((r['brand'] for r in rollback_data if r['product_key'] == update['product_key']), 'N/A')
        key_short = update['product_key'][:30] + '...' if len(update['product_key']) > 30 else update['product_key']
        report += f"| {key_short} | {old_brand} | {update['brand']} |\n"
    
    if len(updates) > 20:
        report += f"\n... and {len(updates) - 20} more\n"
    
    report += f"""
## Rollback Information
- Rollback SQL saved to: sql/rollback_brand_normalization.sql
- Rollback data saved to: data/audit/rollback_data.csv
- Before snapshot saved to: data/audit/before_normalization.csv

## Next Steps
1. Execute: sql/refresh_views_after_normalization.sql
2. Verify changes in foods_published_prod
3. Test admin interface for brand display
"""
    
    # Save report
    Path('reports').mkdir(exist_ok=True)
    with open('reports/BRAND_NORMALIZATION_AUDIT.md', 'w') as f:
        f.write(report)
    
    print("   Report saved to: reports/BRAND_NORMALIZATION_AUDIT.md")

def generate_rollback_sql(rollback_data: List):
    """Generate SQL to rollback changes"""
    print("\n7. Generating rollback SQL...")
    
    if not rollback_data:
        print("   No rollback data needed")
        return
    
    rollback_sql = "-- Rollback brand normalization\n"
    rollback_sql += "-- Generated: " + datetime.now().isoformat() + "\n\n"
    rollback_sql += "BEGIN;\n\n"
    
    for item in rollback_data:
        brand_escaped = item['brand'].replace("'", "''") if item['brand'] else 'NULL'
        slug_escaped = item['brand_slug'].replace("'", "''") if item['brand_slug'] else 'NULL'
        
        rollback_sql += f"""UPDATE foods_canonical 
SET brand = '{brand_escaped}',
    brand_slug = '{slug_escaped}'
WHERE product_key = '{item['product_key']}';

"""
    
    rollback_sql += "COMMIT;\n"
    
    # Save SQL
    with open('sql/rollback_brand_normalization.sql', 'w') as f:
        f.write(rollback_sql)
    
    # Save data as CSV backup
    Path('data/audit').mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rollback_data).to_csv('data/audit/rollback_data.csv', index=False)
    
    print("   Rollback SQL saved to: sql/rollback_brand_normalization.sql")
    print("   Rollback data saved to: data/audit/rollback_data.csv")

def main():
    print("=== Brand Normalization Application ===")
    print("Starting at:", datetime.now().isoformat())
    print()
    
    # Load brand alias map
    brand_map = load_brand_alias_map()
    print(f"Loaded {len(brand_map)} brand mappings")
    
    # Create directories
    Path('data/audit').mkdir(parents=True, exist_ok=True)
    Path('sql').mkdir(exist_ok=True)
    
    # Step 1: Create brand_alias table
    create_brand_alias_table()
    
    # Step 2: Load aliases
    alias_count = load_aliases_to_table(brand_map)
    
    # Step 3: Capture before state
    before_df, before_stats = capture_before_state()
    
    # Step 4: Apply normalization
    updates, rollback_data = apply_normalization(brand_map, before_df)
    
    # Step 5: Generate view refresh SQL
    refresh_materialized_views()
    
    # Step 6: Generate audit report
    generate_audit_report(before_stats, updates, rollback_data)
    
    # Step 7: Generate rollback SQL
    generate_rollback_sql(rollback_data)
    
    # Calculate final unique brands
    unique_brands_after = before_stats['unique_brands']
    if updates:
        updated_brands = set(u['brand'] for u in updates)
        unique_brands_after = before_stats['unique_brands'] - len(updated_brands) + len(set(u['brand'] for u in updates))
    
    print("\n" + "="*50)
    print("SUCCESS SUMMARY")
    print("="*50)
    print(f"✅ Brand aliases loaded: {alias_count}")
    print(f"✅ Products updated: {len(updates)}")
    print(f"✅ Brands reduced: {before_stats['unique_brands']} → ~{unique_brands_after}")
    print("\n📁 Generated Files:")
    print("  - reports/BRAND_NORMALIZATION_AUDIT.md")
    print("  - sql/create_brand_alias_table.sql")
    print("  - sql/refresh_views_after_normalization.sql")
    print("  - sql/rollback_brand_normalization.sql")
    print("  - data/audit/before_normalization.csv")
    print("  - data/audit/rollback_data.csv")
    print("\n⚠️  IMPORTANT NEXT STEPS:")
    print("  1. Execute: sql/create_brand_alias_table.sql (if needed)")
    print("  2. Execute: sql/refresh_views_after_normalization.sql")
    print("\nCompleted at:", datetime.now().isoformat())

if __name__ == "__main__":
    main()