#!/usr/bin/env python3
"""
Check which columns actually exist in breeds_comprehensive_content table
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY'))

# Try to fetch one record to see what columns are available
try:
    response = supabase.table('breeds_comprehensive_content').select('*').limit(1).execute()
    if response.data and len(response.data) > 0:
        columns = list(response.data[0].keys())
        print("Available columns in breeds_comprehensive_content:")
        print("=" * 60)

        # Group columns
        new_columns = ['height_min_cm', 'height_max_cm', 'weight_min_kg', 'weight_max_kg',
                      'lifespan_min_years', 'lifespan_max_years', 'lifespan_avg_years',
                      'personality_traits', 'exercise_needs_detail', 'training_tips', 'fun_facts',
                      'coat_length', 'coat_texture', 'energy_level_numeric', 'barking_tendency',
                      'drooling_tendency', 'ideal_owner', 'living_conditions', 'weather_tolerance',
                      'common_nicknames', 'breed_recognition']

        print("\nColumns we tried to add:")
        for col in new_columns:
            if col in columns:
                print(f"  ✅ {col} - EXISTS")
            else:
                print(f"  ❌ {col} - MISSING")

        print("\n\nAll existing columns:")
        for col in sorted(columns):
            print(f"  - {col}")

    else:
        print("No data found in table")

except Exception as e:
    print(f"Error: {e}")
    print("\nThis might mean the schema cache needs to be refreshed in Supabase")