#!/usr/bin/env python3
"""
Check actual column structure of breed tables in Supabase
"""

import os
from supabase import create_client
from dotenv import load_dotenv
import json

load_dotenv()

def check_breed_tables():
    # Initialize Supabase
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    supabase = create_client(url, key)

    print("="*80)
    print("CHECKING BREED TABLES/VIEWS IN SUPABASE")
    print("="*80)

    tables_to_check = [
        'breeds_published',
        'breeds_comprehensive_content',
        'breeds_details',
        'breeds_unified_api',  # Check if this already exists
        'breeds_complete_profile'  # Check if this exists
    ]

    results = {}

    for table_name in tables_to_check:
        print(f"\n📊 Checking {table_name}:")
        print("-" * 60)

        try:
            # Fetch one row to see all columns
            response = supabase.table(table_name).select('*').limit(1).execute()

            if response.data and len(response.data) > 0:
                columns = list(response.data[0].keys())
                columns.sort()

                print(f"  ✓ Table/View exists with {len(columns)} columns")
                print(f"\n  Columns found:")

                results[table_name] = {
                    'exists': True,
                    'columns': columns,
                    'sample_data': {}
                }

                # Show first 10 columns with types
                for col in columns[:10]:
                    sample_value = response.data[0][col]
                    value_type = type(sample_value).__name__

                    # Handle None values
                    if sample_value is None:
                        value_display = "NULL"
                    elif isinstance(sample_value, str) and len(str(sample_value)) > 50:
                        value_display = f"{str(sample_value)[:50]}..."
                    elif isinstance(sample_value, list):
                        value_display = f"[{len(sample_value)} items]"
                    else:
                        value_display = str(sample_value)

                    print(f"    - {col}: {value_type} (sample: {value_display})")
                    results[table_name]['sample_data'][col] = value_type

                if len(columns) > 10:
                    print(f"    ... and {len(columns) - 10} more columns")
                    print(f"\n  All columns: {', '.join(columns)}")

            else:
                print(f"  ⚠️ Table/View exists but is empty")
                results[table_name] = {
                    'exists': True,
                    'columns': [],
                    'empty': True
                }

        except Exception as e:
            error_msg = str(e)
            if 'relation' in error_msg and 'does not exist' in error_msg:
                print(f"  ✗ Table/View does not exist")
                results[table_name] = {'exists': False}
            else:
                print(f"  ❌ Error: {error_msg}")
                results[table_name] = {'exists': False, 'error': error_msg}

    # Check for specific important columns in breeds_published
    print("\n" + "="*80)
    print("VERIFYING KEY COLUMNS IN breeds_published:")
    print("-" * 60)

    if 'breeds_published' in results and results['breeds_published'].get('exists'):
        important_cols = [
            'breed_slug', 'display_name', 'size_category', 'energy',
            'adult_weight_avg_kg', 'data_quality_grade', 'comprehensive_content',
            'trainability', 'bark_level', 'shedding', 'coat_length'
        ]

        actual_cols = set(results['breeds_published'].get('columns', []))

        for col in important_cols:
            if col in actual_cols:
                print(f"  ✓ {col}: EXISTS")
            else:
                print(f"  ✗ {col}: MISSING")

    # Check for specific important columns in breeds_comprehensive_content
    print("\n" + "="*80)
    print("VERIFYING KEY COLUMNS IN breeds_comprehensive_content:")
    print("-" * 60)

    if 'breeds_comprehensive_content' in results and results['breeds_comprehensive_content'].get('exists'):
        important_cols = [
            'breed_slug', 'introduction', 'personality_description',
            'general_care', 'grooming_needs', 'exercise_needs_detail',
            'training_tips', 'fun_facts', 'working_roles', 'health_issues'
        ]

        actual_cols = set(results['breeds_comprehensive_content'].get('columns', []))

        for col in important_cols:
            if col in actual_cols:
                print(f"  ✓ {col}: EXISTS")
            else:
                print(f"  ✗ {col}: MISSING")

    # Save results to file for reference
    with open('breed_tables_structure.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print("\n" + "="*80)
    print("✅ Full structure saved to breed_tables_structure.json")

    return results

if __name__ == "__main__":
    results = check_breed_tables()