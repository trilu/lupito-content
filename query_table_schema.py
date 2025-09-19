#!/usr/bin/env python3
"""
Direct SQL Query to Check Table Schema
=====================================

Uses the Supabase REST API to run SQL queries and check table structure.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

def query_table_schema():
    """Query table schema using Supabase REST API"""

    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')

    if not supabase_url or not supabase_key:
        raise ValueError("Missing Supabase credentials")

    # SQL query to get column information
    sql_query = """
    SELECT
        column_name,
        data_type,
        is_nullable,
        column_default
    FROM information_schema.columns
    WHERE table_name = 'breeds_details'
    AND table_schema = 'public'
    ORDER BY ordinal_position;
    """

    # Make direct SQL query via Supabase REST API
    headers = {
        'apikey': supabase_key,
        'Authorization': f'Bearer {supabase_key}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation'
    }

    # Use the SQL endpoint
    url = f"{supabase_url}/rest/v1/rpc/exec_sql"
    data = {'sql': sql_query}

    try:
        response = requests.post(url, headers=headers, json=data)

        if response.status_code == 200:
            result = response.json()
            print("✅ Table schema query successful:")
            print("=" * 80)
            print(f"{'Column Name':<25} {'Data Type':<20} {'Nullable':<10} {'Default':<15}")
            print("-" * 80)

            columns = []
            for row in result:
                col_name = row['column_name']
                data_type = row['data_type']
                nullable = row['is_nullable']
                default = row['column_default'] or 'None'
                columns.append(col_name)
                print(f"{col_name:<25} {data_type:<20} {nullable:<10} {str(default):<15}")

            print("=" * 80)
            print(f"Total columns: {len(columns)}")
            return columns

        else:
            print(f"❌ Query failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return []

    except Exception as e:
        print(f"❌ Error executing SQL query: {e}")
        return []

if __name__ == "__main__":
    print("Querying breeds_details table schema via SQL...")
    print()

    columns = query_table_schema()

    if columns:
        print(f"\nColumn names: {columns}")
    else:
        print("\n❌ Could not retrieve table schema")