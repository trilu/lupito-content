#!/usr/bin/env python3

"""
Investigate database schema to understand table structure
"""

import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_KEY')
)

def get_table_columns(table_name):
    """Get columns from a table"""
    try:
        # Get just one row to see the columns
        result = supabase.table(table_name).select("*").limit(1).execute()
        if result.data:
            return list(result.data[0].keys())
        return []
    except Exception as e:
        print(f"Error getting columns from {table_name}: {e}")
        return []

def main():
    print("=" * 80)
    print("DATABASE SCHEMA INVESTIGATION")
    print("=" * 80)

    # Tables to investigate
    tables = [
        'breeds',
        'breeds_unified_api',
        'breeds_published',
        'breeds_comprehensive_content'
    ]

    for table in tables:
        print(f"\n{table}:")
        print("-" * 40)
        columns = get_table_columns(table)
        if columns:
            for col in sorted(columns):
                print(f"  - {col}")
        else:
            print("  (Could not retrieve columns)")

    print("\n" + "=" * 80)
    print("CHECKING SPECIFIC FIELDS FOR PHASE 3")
    print("=" * 80)

    # Check where Phase 3 target fields might exist
    phase3_fields = ['lifespan', 'colors', 'personality_traits', 'grooming_needs']

    for field in phase3_fields:
        print(f"\n{field}:")
        for table in tables:
            columns = get_table_columns(table)
            if field in columns:
                print(f"  ✓ Found in {table}")
            else:
                # Check for variations
                variations = [
                    field,
                    field.replace('_', ''),
                    field.replace('_', '-'),
                    field + '_text',
                    field[:-1] if field.endswith('s') else field + 's'
                ]
                found_variations = [v for v in variations if v in columns]
                if found_variations:
                    print(f"  ~ Found variations in {table}: {', '.join(found_variations)}")
                else:
                    print(f"  ✗ Not found in {table}")

if __name__ == "__main__":
    main()