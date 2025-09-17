#!/usr/bin/env python3
"""
Check breeds_details table columns in Supabase
==============================================

This script queries the Supabase database to get the exact column names
and data types in the breeds_details table.
"""

import os
import json
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

def check_breeds_details_columns():
    """Query the breeds_details table structure from Supabase"""

    # Get credentials from environment
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')

    if not supabase_url or not supabase_key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY required in .env")

    # Create Supabase client
    supabase: Client = create_client(supabase_url, supabase_key)

    try:
        # Query information_schema to get column details
        result = supabase.rpc('get_table_columns', {
            'table_name': 'breeds_details',
            'schema_name': 'public'
        }).execute()

        if result.data:
            print("✅ Found breeds_details table columns:")
            print("=" * 60)
            for col in result.data:
                print(f"Column: {col['column_name']:<25} Type: {col['data_type']}")
            print("=" * 60)
            return [col['column_name'] for col in result.data]
        else:
            print("❌ No column data returned from RPC function")

    except Exception as e:
        print(f"❌ RPC function not available: {e}")
        print("Trying direct SQL query...")

    # Fallback: Direct SQL query using raw SQL
    try:
        query = """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = 'breeds_details'
        AND table_schema = 'public'
        ORDER BY ordinal_position;
        """

        result = supabase.rpc('exec_sql', {'sql': query}).execute()

        if result.data:
            print("✅ Found breeds_details table columns:")
            print("=" * 80)
            print(f"{'Column Name':<25} {'Data Type':<20} {'Nullable':<10} {'Default':<15}")
            print("-" * 80)

            columns = []
            for row in result.data:
                col_name = row['column_name']
                data_type = row['data_type']
                nullable = row['is_nullable']
                default = row['column_default'] or 'None'
                columns.append(col_name)
                print(f"{col_name:<25} {data_type:<20} {nullable:<10} {default:<15}")

            print("=" * 80)
            print(f"\nTotal columns: {len(columns)}")
            print("\nColumn names only:")
            print(columns)
            return columns

    except Exception as e:
        print(f"❌ Direct SQL query failed: {e}")
        print("Trying simple table query...")

    # Fallback: Query the table directly to get structure
    try:
        # Get a single record to see the structure
        result = supabase.table('breeds_details').select('*').limit(1).execute()

        if result.data and len(result.data) > 0:
            columns = list(result.data[0].keys())
            print("✅ Found breeds_details table columns (from sample record):")
            print("=" * 60)
            for i, col in enumerate(columns, 1):
                print(f"{i:2d}. {col}")
            print("=" * 60)
            print(f"\nTotal columns: {len(columns)}")
            print("\nColumn names as list:")
            print(columns)
            return columns
        else:
            print("❌ No data found in breeds_details table")

    except Exception as e:
        print(f"❌ Table query failed: {e}")

    # Last resort: Check if table exists
    try:
        result = supabase.table('breeds_details').select('count', count='exact').execute()
        print(f"✅ Table exists with {result.count} records")
        print("❌ But unable to determine column structure")

    except Exception as e:
        print(f"❌ Table 'breeds_details' may not exist: {e}")

    return []

if __name__ == "__main__":
    print("Checking breeds_details table structure in Supabase...")
    print()

    columns = check_breeds_details_columns()

    if columns:
        print("\n" + "="*60)
        print("SUMMARY - Available columns in breeds_details:")
        print("="*60)
        for col in columns:
            print(f"  • {col}")
        print("="*60)
    else:
        print("\n❌ Unable to determine table structure")