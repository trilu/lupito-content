#!/usr/bin/env python3
"""
Create and seed the brand_alias table in Supabase
"""

import os
import yaml
import pandas as pd
from supabase import create_client
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# Database connection
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def create_table():
    """Create the brand_alias table using raw SQL"""
    print("Creating brand_alias table...")
    
    # The Supabase Python client doesn't support raw SQL execution directly
    # So we'll check if table exists by trying to query it
    try:
        # Try to query the table
        result = supabase.table('brand_alias').select('*').limit(1).execute()
        print("  Table 'brand_alias' already exists")
        
        # Clear existing data for fresh seed
        print("  Clearing existing data...")
        supabase.table('brand_alias').delete().neq('alias', '').execute()
        print("  Existing data cleared")
        return True
    except Exception as e:
        if '42P01' in str(e):  # Table doesn't exist
            print("  Table doesn't exist. Please create it manually using:")
            print("  sql/create_brand_alias_table.sql")
            print("\n  Creating table via Supabase API...")
            
            # Since we can't execute raw SQL, we'll need to create via Supabase dashboard
            # or use the SQL editor. For now, we'll return False to indicate manual action needed
            return False
        else:
            print(f"  Error checking table: {e}")
            return False

def load_brand_alias_map():
    """Load the brand alias map from YAML"""
    yaml_path = Path('data/brand_alias_map.yaml')
    
    if not yaml_path.exists():
        print(f"Error: {yaml_path} not found")
        return None
    
    with open(yaml_path, 'r') as f:
        return yaml.safe_load(f)

def seed_aliases(brand_map):
    """Seed the brand_alias table with data"""
    print("\nSeeding brand_alias table...")
    
    alias_data = []
    
    # Process each brand and its aliases
    for canonical_brand, aliases in brand_map.items():
        # Add the canonical brand itself as an alias (self-reference)
        alias_data.append({
            'alias': canonical_brand.lower(),
            'canonical_brand': canonical_brand
        })
        
        # Add all aliases
        if aliases:  # Check if aliases list exists and is not empty
            for alias in aliases:
                if alias and alias.strip():  # Skip empty aliases
                    alias_data.append({
                        'alias': alias.lower().strip(),
                        'canonical_brand': canonical_brand
                    })
    
    print(f"  Prepared {len(alias_data)} alias mappings")
    
    # Insert in batches
    batch_size = 100
    inserted = 0
    errors = 0
    
    for i in range(0, len(alias_data), batch_size):
        batch = alias_data[i:i+batch_size]
        try:
            result = supabase.table('brand_alias').insert(batch).execute()
            inserted += len(batch)
            print(f"  Inserted batch {i//batch_size + 1}/{(len(alias_data) + batch_size - 1)//batch_size}")
        except Exception as e:
            print(f"  Error inserting batch: {e}")
            errors += len(batch)
    
    print(f"\n  Successfully inserted: {inserted} aliases")
    if errors > 0:
        print(f"  Failed to insert: {errors} aliases")
    
    return inserted, errors

def verify_seeding():
    """Verify the seeding was successful"""
    print("\nVerifying seeded data...")
    
    try:
        # Count total aliases
        result = supabase.table('brand_alias').select('*', count='exact').execute()
        total_count = result.count if hasattr(result, 'count') else len(result.data)
        print(f"  Total aliases in table: {total_count}")
        
        # Get sample canonical brands
        result = supabase.table('brand_alias').select('canonical_brand').limit(1000).execute()
        canonical_brands = set(row['canonical_brand'] for row in result.data)
        print(f"  Unique canonical brands: {len(canonical_brands)}")
        
        # Show some examples
        print("\n  Sample mappings:")
        samples = supabase.table('brand_alias').select('*').limit(10).execute()
        for row in samples.data[:5]:
            print(f"    '{row['alias']}' → '{row['canonical_brand']}'")
        
        return True
    except Exception as e:
        print(f"  Error verifying data: {e}")
        return False

def main():
    print("="*60)
    print("BRAND ALIAS TABLE SEEDING")
    print("="*60)
    
    # Load brand map
    brand_map = load_brand_alias_map()
    if not brand_map:
        print("Failed to load brand alias map")
        return 1
    
    print(f"Loaded {len(brand_map)} canonical brands from brand_alias_map.yaml")
    
    # Check/create table
    table_exists = create_table()
    
    if not table_exists:
        print("\n⚠️  MANUAL ACTION REQUIRED:")
        print("Please execute the following SQL in Supabase SQL editor:")
        print("-"*40)
        with open('sql/create_brand_alias_table.sql', 'r') as f:
            print(f.read())
        print("-"*40)
        print("\nThen run this script again to seed the data.")
        
        # Try to proceed anyway in case table was created manually
        response = input("\nHas the table been created? (y/n): ")
        if response.lower() != 'y':
            return 1
    
    # Seed the data
    inserted, errors = seed_aliases(brand_map)
    
    if inserted > 0:
        # Verify the seeding
        if verify_seeding():
            print("\n✅ SUCCESS: Brand alias table seeded successfully!")
            print(f"   {inserted} aliases loaded into brand_alias table")
            
            # Save a CSV backup
            print("\n📁 Creating CSV backup...")
            try:
                result = supabase.table('brand_alias').select('*').execute()
                df = pd.DataFrame(result.data)
                df.to_csv('data/brand_alias_table_seeded.csv', index=False)
                print("   Backup saved to: data/brand_alias_table_seeded.csv")
            except Exception as e:
                print(f"   Could not save backup: {e}")
        else:
            print("\n⚠️  WARNING: Seeding completed but verification failed")
    else:
        print("\n❌ ERROR: Failed to seed brand alias table")
        return 1
    
    print("\n" + "="*60)
    return 0

if __name__ == "__main__":
    exit(main())