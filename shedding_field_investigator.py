#!/usr/bin/env python3

import os
from supabase import create_client, Client
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(url, key)

def check_shedding_in_table(table_name: str):
    """Check for shedding fields in a specific table"""
    try:
        print(f"\n🔍 Checking table: {table_name}")

        # Get sample data to see field structure
        result = supabase.table(table_name).select("*").limit(3).execute()

        if not result.data:
            print(f"  ❌ No data found in {table_name}")
            return {}

        sample_record = result.data[0]
        fields = list(sample_record.keys())

        # Look for shedding-related fields
        shedding_fields = [f for f in fields if 'shed' in f.lower()]

        if shedding_fields:
            print(f"  🎯 FOUND SHEDDING FIELDS: {shedding_fields}")

            # Get all data to check completeness
            all_result = supabase.table(table_name).select("*").execute()
            records = all_result.data
            total_count = len(records)

            shedding_analysis = {}
            for field in shedding_fields:
                filled_count = 0
                sample_values = []

                for record in records:
                    value = record.get(field)
                    if value is not None and str(value).strip() not in ['', 'null', 'None']:
                        filled_count += 1
                        if len(sample_values) < 5:  # Collect sample values
                            sample_values.append(str(value))

                percentage = (filled_count / total_count) * 100 if total_count > 0 else 0

                shedding_analysis[field] = {
                    'filled_count': filled_count,
                    'total_count': total_count,
                    'percentage': percentage,
                    'sample_values': sample_values
                }

                print(f"    - {field}: {filled_count}/{total_count} ({percentage:.1f}%)")
                print(f"      Sample values: {sample_values[:3]}")

            return shedding_analysis
        else:
            print(f"  ✓ No shedding fields found")
            # Show some field names for reference
            print(f"    Available fields: {fields[:10]}...")
            return {}

    except Exception as e:
        print(f"  ❌ Error accessing {table_name}: {str(e)[:200]}")
        return {}

def check_specific_shedding_fields():
    """Check specific fields that might contain shedding info across all tables"""

    tables_to_check = [
        'breeds_unified_api',
        'breeds',
        'breed_care_content',
        'breed_standards',
        'breed_health',
        'breed_grooming'
    ]

    print("🔍 SHEDDING FIELD INVESTIGATION")
    print("=" * 50)

    all_shedding_data = {}

    for table in tables_to_check:
        shedding_info = check_shedding_in_table(table)
        if shedding_info:
            all_shedding_data[table] = shedding_info

    # Also check for fields that might indirectly relate to shedding
    print(f"\n🔍 Checking for indirect shedding-related fields...")

    coat_related_fields = ['coat', 'grooming', 'maintenance', 'fur']

    for table in tables_to_check:
        try:
            result = supabase.table(table).select("*").limit(1).execute()
            if result.data:
                fields = list(result.data[0].keys())
                related_fields = [f for f in fields if any(keyword in f.lower() for keyword in coat_related_fields)]

                if related_fields:
                    print(f"  {table}: Found coat-related fields: {related_fields}")

                    # Sample a few values from these fields
                    sample_result = supabase.table(table).select(','.join(related_fields)).limit(3).execute()
                    if sample_result.data:
                        print(f"    Sample data: {sample_result.data[0]}")

        except Exception as e:
            continue

    # Final summary
    print(f"\n" + "=" * 50)
    print(f"📊 SHEDDING ANALYSIS SUMMARY")
    print(f"=" * 50)

    if all_shedding_data:
        print(f"✅ FOUND SHEDDING FIELDS IN {len(all_shedding_data)} TABLES:")
        for table, fields in all_shedding_data.items():
            print(f"\n  {table}:")
            for field, info in fields.items():
                print(f"    - {field}: {info['filled_count']}/{info['total_count']} ({info['percentage']:.1f}%)")
                if info['sample_values']:
                    print(f"      Values: {info['sample_values'][:3]}")
    else:
        print(f"❌ NO EXPLICIT SHEDDING FIELDS FOUND")
        print(f"This indicates the user was correct - there may be shedding data in other tables or fields not checked.")

if __name__ == "__main__":
    check_specific_shedding_fields()