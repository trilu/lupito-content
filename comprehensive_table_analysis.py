#!/usr/bin/env python3

import os
from supabase import create_client, Client
from typing import Dict, List, Any, Optional
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(url, key)

def get_all_tables():
    """Get list of all tables in the database"""
    try:
        # Query information_schema to get all table names
        query = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_type = 'BASE TABLE'
        ORDER BY table_name;
        """
        result = supabase.rpc('get_table_names').execute()

        # If that doesn't work, try direct queries on known tables
        known_tables = [
            'breeds', 'breeds_unified_api', 'breed_care_content',
            'breed_standards', 'breed_health', 'breed_nutrition',
            'breed_training', 'breed_grooming', 'breed_history'
        ]

        existing_tables = []
        for table in known_tables:
            try:
                result = supabase.table(table).select("*").limit(1).execute()
                existing_tables.append(table)
                print(f"✓ Found table: {table}")
            except Exception as e:
                print(f"✗ Table {table} not accessible: {str(e)[:100]}")

        return existing_tables

    except Exception as e:
        print(f"Error getting table list: {e}")
        return []

def analyze_table_structure(table_name: str):
    """Analyze the structure and data completeness of a table"""
    try:
        print(f"\n=== ANALYZING TABLE: {table_name} ===")

        # Get sample data to understand structure
        result = supabase.table(table_name).select("*").limit(5).execute()

        if not result.data:
            print(f"No data found in {table_name}")
            return {}

        sample_record = result.data[0]
        fields = list(sample_record.keys())

        print(f"Fields found: {len(fields)}")
        print(f"Sample fields: {fields[:10]}...")

        # Get total record count
        count_result = supabase.table(table_name).select("*", count="exact").execute()
        total_records = count_result.count if hasattr(count_result, 'count') else len(result.data)

        print(f"Total records: {total_records}")

        # For each field, check completeness
        field_completeness = {}

        # Get all data for analysis (if table is reasonably sized)
        if total_records <= 1000:
            all_data_result = supabase.table(table_name).select("*").execute()
            all_records = all_data_result.data

            for field in fields:
                non_null_count = 0
                non_empty_count = 0

                for record in all_records:
                    value = record.get(field)
                    if value is not None:
                        non_null_count += 1
                        if str(value).strip() not in ['', 'null', 'None']:
                            non_empty_count += 1

                null_percentage = (non_null_count / total_records) * 100
                filled_percentage = (non_empty_count / total_records) * 100

                field_completeness[field] = {
                    'null_percentage': null_percentage,
                    'filled_percentage': filled_percentage,
                    'non_null_count': non_null_count,
                    'non_empty_count': non_empty_count
                }

        return {
            'table_name': table_name,
            'total_records': total_records,
            'total_fields': len(fields),
            'fields': fields,
            'field_completeness': field_completeness,
            'sample_record': sample_record
        }

    except Exception as e:
        print(f"Error analyzing table {table_name}: {e}")
        return {}

def find_shedding_fields():
    """Specifically look for shedding-related fields across all tables"""
    print("\n🔍 SEARCHING FOR SHEDDING FIELDS...")

    tables = get_all_tables()
    shedding_info = {}

    for table in tables:
        try:
            result = supabase.table(table).select("*").limit(1).execute()
            if result.data:
                fields = list(result.data[0].keys())

                # Look for shedding-related fields
                shedding_fields = [f for f in fields if 'shed' in f.lower()]

                if shedding_fields:
                    print(f"🎯 FOUND SHEDDING FIELDS in {table}: {shedding_fields}")

                    # Get completeness for these fields
                    all_result = supabase.table(table).select("*").execute()
                    records = all_result.data

                    for field in shedding_fields:
                        filled_count = sum(1 for r in records if r.get(field) and str(r.get(field)).strip() not in ['', 'null', 'None'])
                        total_count = len(records)
                        percentage = (filled_count / total_count) * 100 if total_count > 0 else 0

                        shedding_info[f"{table}.{field}"] = {
                            'filled_count': filled_count,
                            'total_count': total_count,
                            'percentage': percentage
                        }

                        print(f"  - {field}: {filled_count}/{total_count} ({percentage:.1f}%)")

        except Exception as e:
            print(f"Error checking {table} for shedding fields: {e}")

    return shedding_info

def main():
    print("🔍 COMPREHENSIVE DATABASE TABLE ANALYSIS")
    print("=" * 50)

    # Get all tables
    tables = get_all_tables()
    print(f"\nFound {len(tables)} accessible tables")

    # Specifically search for shedding fields first
    shedding_results = find_shedding_fields()

    # Analyze each table
    all_analyses = {}
    for table in tables:
        analysis = analyze_table_structure(table)
        if analysis:
            all_analyses[table] = analysis

    # Summary
    print("\n" + "=" * 50)
    print("📊 ANALYSIS SUMMARY")
    print("=" * 50)

    print(f"\nTables analyzed: {len(all_analyses)}")

    if shedding_results:
        print(f"\n🎯 SHEDDING FIELD SUMMARY:")
        for field_path, info in shedding_results.items():
            print(f"  {field_path}: {info['filled_count']}/{info['total_count']} ({info['percentage']:.1f}%)")
    else:
        print("\n❌ NO SHEDDING FIELDS FOUND")

    # Show field counts by table
    print(f"\n📋 FIELD COUNTS BY TABLE:")
    for table, analysis in all_analyses.items():
        print(f"  {table}: {analysis.get('total_fields', 0)} fields, {analysis.get('total_records', 0)} records")

    # Save detailed results
    with open('comprehensive_table_analysis.json', 'w') as f:
        json.dump({
            'shedding_analysis': shedding_results,
            'table_analyses': all_analyses
        }, f, indent=2, default=str)

    print(f"\n💾 Detailed results saved to comprehensive_table_analysis.json")

if __name__ == "__main__":
    main()