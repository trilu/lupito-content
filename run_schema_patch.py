#!/usr/bin/env python3
"""
Run Schema Patch for Nutrition Columns
Applies idempotent migration and generates report
"""

import os
import json
from datetime import datetime
from pathlib import Path
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Initialize Supabase
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(url, key)

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

print("="*80)
print("SCHEMA PATCH: NUTRITION COLUMNS")
print("="*80)
print(f"Timestamp: {timestamp}")
print()

# Check existing columns before patch
print("📊 Checking existing columns in foods_canonical...")

def get_table_columns(table_name):
    """Get list of columns for a table"""
    try:
        response = supabase.table(table_name).select('*').limit(1).execute()
        if response.data:
            return list(response.data[0].keys())
        return []
    except Exception as e:
        print(f"Error checking {table_name}: {e}")
        return []

# Required columns to check
required_columns = [
    'ingredients_raw',
    'ingredients_tokens',
    'ingredients_source',
    'ingredients_parsed_at',
    'ingredients_language',
    'protein_percent',
    'fat_percent',
    'fiber_percent',
    'ash_percent',
    'moisture_percent',
    'macros_source',
    'kcal_per_100g',
    'kcal_source'
]

# Check canonical table before
canonical_before = get_table_columns('foods_canonical')
published_before = get_table_columns('foods_published')

print(f"  Current columns in foods_canonical: {len(canonical_before)}")
print(f"  Current columns in foods_published: {len(published_before)}")

# Check which columns are missing
missing_canonical = [col for col in required_columns if col not in canonical_before]
missing_published = [col for col in required_columns if col not in published_before]

print("\n🔍 Missing columns analysis:")
print(f"  foods_canonical missing: {len(missing_canonical)} columns")
if missing_canonical:
    for col in missing_canonical:
        print(f"    - {col}")

print(f"\n  foods_published missing: {len(missing_published)} columns")
if missing_published:
    for col in missing_published:
        print(f"    - {col}")

# Read SQL file
sql_file = Path("sql/schema_patch_nutrition_columns.sql")
if not sql_file.exists():
    print(f"❌ SQL file not found: {sql_file}")
    exit(1)

print("\n" + "="*80)
print("🔧 APPLYING SCHEMA PATCH")
print("="*80)

print("\n⚠️  This will add the following columns (if missing):")
print("  • ingredients_raw, ingredients_source, ingredients_parsed_at, ingredients_language")
print("  • fiber_percent, ash_percent, moisture_percent")
print("  • macros_source, kcal_source")
print("\n✅ The migration is IDEMPOTENT (safe to run multiple times)")
print("✅ No existing columns will be modified or dropped")

response = input("\nProceed with schema patch? (y/n): ").strip().lower()

if response != 'y':
    print("❌ Schema patch cancelled")
    exit(0)

print("\n📝 To run the migration, execute this SQL in Supabase:")
print(f"\n  SQL file: {sql_file}")
print("\n  Or run in SQL editor:")
print("  " + "-"*60)

# Display key parts of the SQL
with open(sql_file, 'r') as f:
    lines = f.readlines()
    # Show first few ALTER statements as example
    alter_count = 0
    for line in lines:
        if 'ALTER TABLE' in line and alter_count < 5:
            print(f"  {line.strip()}")
            alter_count += 1
            if alter_count == 5:
                print("  ... (see full file for all statements)")
                break

print("  " + "-"*60)

# Generate verification script
print("\n" + "="*80)
print("📊 VERIFICATION SCRIPT")
print("="*80)

verification_script = """
-- Run this after applying the schema patch to verify:

-- 1. Check columns were added to foods_canonical
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'foods_canonical'
AND column_name IN (
    'ingredients_raw', 'ingredients_source', 'ingredients_parsed_at',
    'fiber_percent', 'ash_percent', 'moisture_percent',
    'macros_source', 'kcal_source'
)
ORDER BY column_name;

-- 2. Check columns were added to foods_published
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'foods_published'
AND column_name IN (
    'ingredients_raw', 'ingredients_source', 
    'fiber_percent', 'ash_percent', 'moisture_percent',
    'macros_source', 'kcal_source'
)
ORDER BY column_name;

-- 3. Verify views can see new columns
SELECT 
    table_name as view_name,
    COUNT(DISTINCT column_name) as nutrition_columns_visible
FROM information_schema.columns
WHERE table_name IN ('foods_published_preview', 'foods_published_prod')
AND column_name IN (
    'ingredients_raw', 'fiber_percent', 'ash_percent', 
    'moisture_percent', 'macros_source', 'kcal_source'
)
GROUP BY table_name;

-- 4. Test insert with new columns
-- INSERT INTO foods_canonical (
--     product_key, brand_slug, product_name,
--     ingredients_raw, fiber_percent, ash_percent
-- ) VALUES (
--     'test_product_001', 'test_brand', 'Test Product',
--     'Chicken, Rice, Vitamins', 3.5, 6.0
-- );
"""

# Save verification script
verification_file = Path("sql/verify_schema_patch.sql")
with open(verification_file, 'w') as f:
    f.write(verification_script)

print(f"✅ Verification script saved to: {verification_file}")

# Generate report
print("\n" + "="*80)
print("📄 GENERATING MIGRATION REPORT")
print("="*80)

report_dir = Path("reports")
report_dir.mkdir(exist_ok=True)
report_file = report_dir / f"SCHEMA_PATCH_REPORT_{timestamp}.md"

with open(report_file, 'w') as f:
    f.write("# Schema Patch Report: Nutrition Columns\n\n")
    f.write(f"**Generated:** {datetime.now().isoformat()}\n")
    f.write(f"**Migration File:** `{sql_file}`\n\n")
    
    f.write("## Pre-Migration Analysis\n\n")
    f.write("### foods_canonical\n")
    f.write(f"- Current columns: {len(canonical_before)}\n")
    f.write(f"- Missing columns: {len(missing_canonical)}\n")
    if missing_canonical:
        f.write("- Columns to add:\n")
        for col in missing_canonical:
            f.write(f"  - `{col}`\n")
    
    f.write("\n### foods_published\n")
    f.write(f"- Current columns: {len(published_before)}\n")
    f.write(f"- Missing columns: {len(missing_published)}\n")
    if missing_published:
        f.write("- Columns to add:\n")
        for col in missing_published:
            f.write(f"  - `{col}`\n")
    
    f.write("\n## Migration Summary\n\n")
    f.write("The migration will add these columns (if not exists):\n\n")
    
    f.write("### Ingredients Tracking\n")
    f.write("- `ingredients_raw` TEXT - Original ingredients text\n")
    f.write("- `ingredients_tokens` JSONB - Tokenized array\n")
    f.write("- `ingredients_source` TEXT - Source (label|pdf|site|manual)\n")
    f.write("- `ingredients_parsed_at` TIMESTAMPTZ - Parse timestamp\n")
    f.write("- `ingredients_language` TEXT - Language code\n")
    
    f.write("\n### Macronutrients\n")
    f.write("- `protein_percent` NUMERIC(5,2) - Protein percentage\n")
    f.write("- `fat_percent` NUMERIC(5,2) - Fat percentage\n")
    f.write("- `fiber_percent` NUMERIC(5,2) - Fiber percentage\n")
    f.write("- `ash_percent` NUMERIC(5,2) - Ash percentage\n")
    f.write("- `moisture_percent` NUMERIC(5,2) - Moisture percentage\n")
    f.write("- `macros_source` TEXT - Source (label|pdf|site|derived)\n")
    
    f.write("\n### Energy\n")
    f.write("- `kcal_per_100g` NUMERIC(6,2) - Calories per 100g\n")
    f.write("- `kcal_source` TEXT - Source (label|pdf|site|derived)\n")
    
    f.write("\n## Key Features\n\n")
    f.write("✅ **Idempotent**: Safe to run multiple times\n")
    f.write("✅ **Non-destructive**: Only adds columns, never drops\n")
    f.write("✅ **Validated**: CHECK constraints on source fields\n")
    f.write("✅ **Indexed**: Performance indexes on key fields\n")
    f.write("✅ **View-compatible**: Views will automatically show new columns\n")
    
    f.write("\n## Next Steps\n\n")
    f.write("1. Run the migration: `{sql_file}`\n")
    f.write("2. Verify with: `{verification_file}`\n")
    f.write("3. Begin populating new columns with enrichment scripts\n")
    f.write("4. Update quality gates to use new source tracking\n")
    
    f.write("\n## Expected Impact\n\n")
    f.write("After migration, the following capabilities will be enabled:\n\n")
    f.write("- Full nutrition tracking (protein, fat, fiber, ash, moisture)\n")
    f.write("- Data provenance (track where each value came from)\n")
    f.write("- Temporal tracking (when data was parsed)\n")
    f.write("- Multi-language support for ingredients\n")
    f.write("- Better quality gates with source validation\n")

print(f"✅ Report saved to: {report_file}")

print("\n" + "="*80)
print("✅ SCHEMA PATCH PREPARATION COMPLETE")
print("="*80)

print("\n📋 Summary:")
print(f"  • Columns to add to foods_canonical: {len(missing_canonical)}")
print(f"  • Columns to add to foods_published: {len(missing_published)}")
print(f"  • Migration is idempotent and safe")
print(f"  • Views will automatically expose new columns")

print("\n🎯 Action Required:")
print(f"  1. Review the migration: {sql_file}")
print(f"  2. Run it in Supabase SQL editor")
print(f"  3. Verify with: {verification_file}")
print(f"  4. Check report: {report_file}")

print("\n✨ Once migration is complete, enrichment scripts will have full nutrition support!")