#!/usr/bin/env python3
"""
Seed the existing brand_alias table with data
"""

import os
import yaml
from supabase import create_client
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def main():
    print("=== SEEDING BRAND_ALIAS TABLE ===\n")
    
    # Load brand alias map
    yaml_path = Path('data/brand_alias_map.yaml')
    if not yaml_path.exists():
        print(f"❌ Error: {yaml_path} not found")
        return 1
    
    with open(yaml_path, 'r') as f:
        brand_map = yaml.safe_load(f)
    
    print(f"Loaded {len(brand_map)} canonical brands from YAML")
    
    # Prepare alias data
    alias_data = []
    
    for canonical_brand, aliases in brand_map.items():
        # Add canonical brand as self-reference
        alias_data.append({
            'alias': canonical_brand.lower(),
            'canonical_brand': canonical_brand
        })
        
        # Add all aliases
        if aliases:
            for alias in aliases:
                if alias and alias.strip():
                    alias_data.append({
                        'alias': alias.lower().strip(),
                        'canonical_brand': canonical_brand
                    })
    
    print(f"Prepared {len(alias_data)} total mappings")
    
    # Clear any existing data
    print("\nClearing existing data...")
    try:
        supabase.table('brand_alias').delete().neq('alias', '').execute()
        print("✅ Existing data cleared")
    except Exception as e:
        print(f"⚠️  Could not clear data: {e}")
    
    # Insert in batches
    print("\nInserting brand aliases...")
    batch_size = 50  # Smaller batch size for safety
    inserted = 0
    failed = 0
    
    for i in range(0, len(alias_data), batch_size):
        batch = alias_data[i:i+batch_size]
        try:
            supabase.table('brand_alias').insert(batch).execute()
            inserted += len(batch)
            print(f"  Batch {i//batch_size + 1}: {len(batch)} records inserted")
        except Exception as e:
            print(f"  ❌ Batch {i//batch_size + 1} failed: {e}")
            failed += len(batch)
    
    # Verify the seeding
    print("\nVerifying...")
    try:
        result = supabase.table('brand_alias').select('*', count='exact').limit(0).execute()
        total = result.count if hasattr(result, 'count') else 0
        print(f"✅ Total aliases in table: {total}")
        
        # Show some examples
        samples = supabase.table('brand_alias').select('*').limit(5).execute()
        if samples.data:
            print("\nSample mappings:")
            for row in samples.data:
                print(f"  '{row['alias']}' → '{row['canonical_brand']}'")
    except Exception as e:
        print(f"❌ Verification failed: {e}")
    
    print("\n" + "="*50)
    if inserted > 0:
        print(f"✅ SUCCESS: {inserted} aliases loaded")
        if failed > 0:
            print(f"⚠️  WARNING: {failed} aliases failed to load")
    else:
        print("❌ FAILED: No aliases were loaded")
    
    return 0 if inserted > 0 else 1

if __name__ == "__main__":
    exit(main())