#!/usr/bin/env python3
"""
Prompt 1: Ingredients Field Audit & Type Fix
Detect and fix ingredients_tokens type issues, standardize to JSONB
"""

import os
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from supabase import create_client
from dotenv import load_dotenv
from collections import Counter

load_dotenv()

# Initialize Supabase
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(url, key)

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

print("="*80)
print("INGREDIENTS FIELD AUDIT & TYPE FIX")
print("="*80)
print(f"Timestamp: {timestamp}")
print()

# Tables to audit
tables_to_audit = [
    'foods_canonical',
    'foods_published',
    'food_candidates',
    'food_candidates_sc'
]

audit_results = []
all_tokens = Counter()
total_fixed = 0

def analyze_ingredients_field(table_name):
    """Analyze ingredients_tokens field in a table"""
    print(f"\n{'='*60}")
    print(f"📊 AUDITING: {table_name}")
    print('='*60)
    
    results = {
        'table': table_name,
        'total_rows': 0,
        'has_ingredients': 0,
        'is_string': 0,
        'is_array': 0,
        'is_null': 0,
        'is_empty': 0,
        'needs_fix': 0,
        'tokens_collected': []
    }
    
    try:
        # Determine correct columns for each table
        if table_name in ['foods_canonical', 'foods_published']:
            select_cols = 'product_key, ingredients_tokens'
        elif table_name in ['food_candidates', 'food_candidates_sc']:
            select_cols = 'id, ingredients_tokens, ingredients_raw'
        else:
            select_cols = '*'
            
        # Get all data
        response = supabase.table(table_name).select(select_cols).execute()
        
        if not response.data:
            print(f"  ⚠️ No data found")
            return results
            
        df = pd.DataFrame(response.data)
        results['total_rows'] = len(df)
        print(f"  Total rows: {results['total_rows']:,}")
        
        # Analyze each row
        for idx, row in df.iterrows():
            ingredients = row.get('ingredients_tokens')
            
            if ingredients is None:
                results['is_null'] += 1
            elif isinstance(ingredients, str):
                results['is_string'] += 1
                results['needs_fix'] += 1
                # Try to parse if it's a JSON string
                try:
                    parsed = json.loads(ingredients)
                    if isinstance(parsed, list):
                        results['tokens_collected'].extend(parsed)
                except:
                    pass
            elif isinstance(ingredients, list):
                results['is_array'] += 1
                if len(ingredients) == 0:
                    results['is_empty'] += 1
                else:
                    results['has_ingredients'] += 1
                    results['tokens_collected'].extend(ingredients)
            else:
                print(f"  ❓ Unknown type at row {idx}: {type(ingredients)}")
        
        # Print analysis
        print(f"  ✅ Valid arrays: {results['is_array']:,} ({results['is_array']/results['total_rows']*100:.1f}%)")
        print(f"  ⚠️ String type: {results['is_string']:,} ({results['is_string']/results['total_rows']*100:.1f}%)")
        print(f"  ❌ NULL values: {results['is_null']:,} ({results['is_null']/results['total_rows']*100:.1f}%)")
        print(f"  📦 Empty arrays: {results['is_empty']:,} ({results['is_empty']/results['total_rows']*100:.1f}%)")
        
        if results['needs_fix'] > 0:
            print(f"  🔧 NEEDS FIX: {results['needs_fix']} rows")
        
        # Update global token counter
        all_tokens.update(results['tokens_collected'])
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        
    audit_results.append(results)
    return results

# Run audit on all tables
for table in tables_to_audit:
    analyze_ingredients_field(table)

# Generate SQL migrations
print("\n" + "="*80)
print("🔧 GENERATING SQL MIGRATIONS")
print("="*80)

migrations = []

# Create idempotent migrations for each table
for result in audit_results:
    if result['needs_fix'] > 0:
        table = result['table']
        
        migration = f"""
-- Migration for {table} - Fix ingredients_tokens type
-- Converts string arrays to JSONB, handles nulls and empties

-- Add metadata columns if they don't exist
ALTER TABLE {table} 
ADD COLUMN IF NOT EXISTS ingredients_tokens_version VARCHAR(10) DEFAULT 'v1',
ADD COLUMN IF NOT EXISTS ingredients_parsed_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS ingredients_source VARCHAR(50),
ADD COLUMN IF NOT EXISTS ingredients_language VARCHAR(10) DEFAULT 'en';

-- Fix stringified arrays (idempotent)
UPDATE {table}
SET 
    ingredients_tokens = CASE
        WHEN ingredients_tokens IS NULL THEN '[]'::jsonb
        WHEN jsonb_typeof(ingredients_tokens) = 'string' THEN
            CASE 
                WHEN ingredients_tokens::text LIKE '[%]' THEN
                    TRY_CAST(ingredients_tokens::text AS jsonb)
                ELSE '[]'::jsonb
            END
        WHEN jsonb_typeof(ingredients_tokens) = 'array' THEN ingredients_tokens
        ELSE '[]'::jsonb
    END,
    ingredients_parsed_at = NOW(),
    ingredients_tokens_version = 'v1.1'
WHERE 
    ingredients_tokens IS NULL 
    OR jsonb_typeof(ingredients_tokens) != 'array'
    OR jsonb_array_length(ingredients_tokens) = 0;

-- Verify the fix
SELECT 
    COUNT(*) as total,
    COUNT(CASE WHEN ingredients_tokens IS NOT NULL 
               AND jsonb_typeof(ingredients_tokens) = 'array' 
               AND jsonb_array_length(ingredients_tokens) > 0 THEN 1 END) as valid_arrays,
    COUNT(CASE WHEN ingredients_tokens IS NULL 
               OR jsonb_typeof(ingredients_tokens) != 'array' THEN 1 END) as still_invalid
FROM {table};
"""
        migrations.append(migration)
        print(f"✅ Generated migration for {table}")

# Save migrations
migrations_dir = Path("sql/migrations")
migrations_dir.mkdir(parents=True, exist_ok=True)
migration_file = migrations_dir / f"fix_ingredients_types_{timestamp}.sql"

with open(migration_file, 'w') as f:
    f.write("-- Ingredients Type Fix Migrations\n")
    f.write(f"-- Generated: {datetime.now().isoformat()}\n")
    f.write("-- Run these in order on your database\n\n")
    
    for migration in migrations:
        f.write(migration)
        f.write("\n")

print(f"💾 Migrations saved to: {migration_file}")

# Generate report
print("\n" + "="*80)
print("📊 GENERATING REPORT")
print("="*80)

# Get top tokens
top_tokens = all_tokens.most_common(50)

report_dir = Path("reports")
report_dir.mkdir(exist_ok=True)
report_file = report_dir / "INGREDIENTS_TYPE_FIX.md"

with open(report_file, 'w') as f:
    f.write("# Ingredients Type Fix Report\n\n")
    f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
    
    f.write("## Audit Summary\n\n")
    f.write("| Table | Total Rows | Valid Arrays | Strings | NULLs | Empty | Needs Fix |\n")
    f.write("|-------|------------|--------------|---------|-------|-------|----------|\n")
    
    total_all = 0
    total_needs_fix = 0
    
    for r in audit_results:
        total_all += r['total_rows']
        total_needs_fix += r['needs_fix']
        
        valid_pct = r['is_array'] / r['total_rows'] * 100 if r['total_rows'] > 0 else 0
        
        f.write(f"| {r['table']} | {r['total_rows']:,} | {r['is_array']:,} ({valid_pct:.1f}%) | ")
        f.write(f"{r['is_string']:,} | {r['is_null']:,} | {r['is_empty']:,} | {r['needs_fix']:,} |\n")
    
    f.write(f"\n**Total rows to fix:** {total_needs_fix:,}\n")
    f.write(f"**Total rows analyzed:** {total_all:,}\n\n")
    
    f.write("## Coverage After Fix\n\n")
    f.write("Expected improvements after running migrations:\n\n")
    
    for r in audit_results:
        if r['total_rows'] > 0:
            current_coverage = (r['has_ingredients'] / r['total_rows'] * 100)
            expected_coverage = ((r['has_ingredients'] + r['is_string']) / r['total_rows'] * 100)
            f.write(f"- **{r['table']}**: {current_coverage:.1f}% → {expected_coverage:.1f}%\n")
    
    f.write("\n## Top 50 Most Common Ingredients\n\n")
    f.write("After standardization, the most common ingredient tokens are:\n\n")
    f.write("| Rank | Ingredient | Count |\n")
    f.write("|------|------------|-------|\n")
    
    for i, (token, count) in enumerate(top_tokens, 1):
        f.write(f"| {i} | {token} | {count:,} |\n")
    
    f.write("\n## Metadata Fields Added\n\n")
    f.write("The following metadata fields were added to track processing:\n\n")
    f.write("- `ingredients_tokens_version`: Version of tokenization (default: 'v1')\n")
    f.write("- `ingredients_parsed_at`: Timestamp of last parsing\n")
    f.write("- `ingredients_source`: Source of ingredients (label|html|pdf|manual)\n")
    f.write("- `ingredients_language`: Language code (default: 'en')\n")
    
    f.write("\n## Migration Files\n\n")
    f.write(f"SQL migrations saved to: `{migration_file}`\n\n")
    
    f.write("## Next Steps\n\n")
    f.write("1. Review and run the SQL migrations\n")
    f.write("2. Refresh any affected views/materialized views\n")
    f.write("3. Proceed to Prompt 2: Tokenize + Canonicalize\n")

print(f"✅ Report saved to: {report_file}")

# Sanity check
print("\n" + "="*80)
print("🔍 SANITY CHECK")
print("="*80)
print(f"Total unique tokens found: {len(all_tokens):,}")
print(f"Total token occurrences: {sum(all_tokens.values()):,}")

if top_tokens:
    print("\nTop 10 ingredients:")
    for token, count in top_tokens[:10]:
        print(f"  - {token}: {count:,}")

print("\n✅ AUDIT COMPLETE")
print(f"📄 Full report: {report_file}")
print(f"📝 SQL migrations: {migration_file}")
print("\n⚠️ Review migrations before running on production!")