#!/usr/bin/env python3
"""
Prompt 0: Safety & Snapshot
Run a read-only snapshot before any changes
"""

import os
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Initialize Supabase
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(url, key)

# Create backup directory
backup_dir = Path("/Users/sergiubiris/Desktop/lupito-content/backups/ingredients_preflight")
backup_dir.mkdir(parents=True, exist_ok=True)

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

print("="*80)
print("SAFETY SNAPSHOT - READ-ONLY")
print("="*80)
print(f"Timestamp: {timestamp}")
print(f"Backup location: {backup_dir}")
print()

# Tables to check
tables_to_check = [
    'foods_canonical',
    'foods_published', 
    'foods_published_preview',
    'foods_published_prod',
    'foods_union_all',
    'food_candidates',
    'food_candidates_sc',
    'food_brands',
    'food_raw'
]

# Columns of interest
columns_of_interest = [
    'brand', 'brand_slug', 'product_name', 'name_slug',
    'ingredients_raw', 'ingredients_tokens', 'kcal_per_100g',
    'protein_percent', 'fat_percent', 'life_stage', 'form',
    'sources', 'available_countries'
]

snapshot_summary = []

for table_name in tables_to_check:
    print(f"\n{'='*60}")
    print(f"📊 TABLE: {table_name}")
    print('='*60)
    
    try:
        # Get row count
        count_response = supabase.table(table_name).select('*', count='exact').execute()
        row_count = count_response.count
        
        if row_count == 0:
            print(f"  ⚠️ Table exists but is EMPTY")
            snapshot_summary.append({
                'table': table_name,
                'status': 'EMPTY',
                'row_count': 0
            })
            continue
            
        print(f"  ✅ Row count: {row_count:,}")
        
        # Get sample data
        sample_response = supabase.table(table_name).select('*').limit(10).execute()
        
        if sample_response.data:
            df = pd.DataFrame(sample_response.data)
            
            # Check which columns exist
            existing_cols = [col for col in columns_of_interest if col in df.columns]
            print(f"  📋 Available columns: {', '.join(existing_cols[:5])}...")
            
            # Get last updated if available
            if 'updated_at' in df.columns:
                try:
                    # Get most recent update
                    latest_response = supabase.table(table_name).select('updated_at').order('updated_at', desc=True).limit(1).execute()
                    if latest_response.data:
                        last_updated = latest_response.data[0]['updated_at']
                        print(f"  🕐 Last updated: {last_updated}")
                except:
                    pass
            
            # Check ingredients_tokens type
            if 'ingredients_tokens' in df.columns:
                sample_val = df['ingredients_tokens'].iloc[0] if len(df) > 0 else None
                if sample_val is not None:
                    val_type = type(sample_val).__name__
                    if val_type == 'str':
                        print(f"  ⚠️ ingredients_tokens is STRING (needs conversion)")
                    elif val_type == 'list':
                        print(f"  ✅ ingredients_tokens is LIST/JSONB")
                    else:
                        print(f"  ❓ ingredients_tokens type: {val_type}")
            
            # Save backup CSV
            backup_file = backup_dir / f"{table_name}_{timestamp}.csv"
            
            # Get full data for backup (limit to 10000 for large tables)
            if row_count > 10000:
                print(f"  📦 Large table - backing up first 10,000 rows")
                full_response = supabase.table(table_name).select('*').limit(10000).execute()
            else:
                full_response = supabase.table(table_name).select('*').execute()
            
            if full_response.data:
                backup_df = pd.DataFrame(full_response.data)
                backup_df.to_csv(backup_file, index=False)
                print(f"  💾 Backup saved: {backup_file.name}")
                
                # Add to summary
                snapshot_summary.append({
                    'table': table_name,
                    'status': 'OK',
                    'row_count': row_count,
                    'backed_up': len(backup_df),
                    'columns': len(backup_df.columns),
                    'has_ingredients': 'ingredients_tokens' in backup_df.columns,
                    'backup_file': backup_file.name
                })
            
            # Show sample data
            print(f"\n  📝 Sample data (first 3 rows):")
            for idx, row in df.head(3).iterrows():
                if 'product_name' in row:
                    print(f"    - {row.get('brand_slug', 'N/A')}: {row['product_name'][:50]}")
                    if 'ingredients_tokens' in row and row['ingredients_tokens']:
                        if isinstance(row['ingredients_tokens'], list):
                            print(f"      Ingredients: {row['ingredients_tokens'][:3]}...")
                        else:
                            print(f"      Ingredients: {str(row['ingredients_tokens'])[:50]}...")
                            
    except Exception as e:
        error_msg = str(e)
        if 'does not exist' in error_msg:
            print(f"  ❌ Table does NOT exist")
            snapshot_summary.append({
                'table': table_name,
                'status': 'NOT_EXISTS',
                'row_count': 0
            })
        else:
            print(f"  ❌ Error: {error_msg[:100]}")
            snapshot_summary.append({
                'table': table_name,
                'status': 'ERROR',
                'error': error_msg[:100]
            })

# Write PRECHECK.md
precheck_file = backup_dir / "PRECHECK.md"
with open(precheck_file, 'w') as f:
    f.write(f"# Ingredients Safety Snapshot\n\n")
    f.write(f"**Timestamp:** {timestamp}\n\n")
    f.write(f"## Table Summary\n\n")
    f.write("| Table | Status | Row Count | Backed Up | Has Ingredients |\n")
    f.write("|-------|--------|-----------|-----------|----------------|\n")
    
    total_rows = 0
    total_backed_up = 0
    
    for item in snapshot_summary:
        status = item['status']
        row_count = item.get('row_count', 0)
        backed_up = item.get('backed_up', 0)
        has_ingredients = '✅' if item.get('has_ingredients') else '❌'
        
        if status == 'NOT_EXISTS':
            f.write(f"| {item['table']} | ❌ NOT EXISTS | - | - | - |\n")
        elif status == 'EMPTY':
            f.write(f"| {item['table']} | ⚠️ EMPTY | 0 | - | - |\n")
        elif status == 'ERROR':
            f.write(f"| {item['table']} | ❌ ERROR | - | - | - |\n")
        else:
            f.write(f"| {item['table']} | ✅ OK | {row_count:,} | {backed_up:,} | {has_ingredients} |\n")
            total_rows += row_count
            total_backed_up += backed_up
    
    f.write(f"\n**Total Rows:** {total_rows:,}\n")
    f.write(f"**Total Backed Up:** {total_backed_up:,}\n\n")
    
    f.write("## Backup Files\n\n")
    for item in snapshot_summary:
        if 'backup_file' in item:
            f.write(f"- `{item['backup_file']}`\n")
    
    f.write(f"\n## Next Steps\n\n")
    f.write(f"1. Review backup files in `{backup_dir}`\n")
    f.write(f"2. Proceed with Prompt 1: Ingredients Field Audit\n")
    f.write(f"3. All operations are READ-ONLY - no data modified\n")

print("\n" + "="*80)
print("SNAPSHOT COMPLETE")
print("="*80)
print(f"✅ Backup files saved to: {backup_dir}")
print(f"✅ Summary saved to: {precheck_file}")
print(f"✅ Total tables checked: {len(snapshot_summary)}")
print(f"✅ Total rows backed up: {total_backed_up:,}")
print("\n🔒 All operations were READ-ONLY - no data modified")
print("Ready to proceed with Prompt 1: Ingredients Field Audit")