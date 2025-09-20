#!/usr/bin/env python3
"""
Check the breeds table for existing physical measurement data
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY'))

print("Checking 'breeds' table for physical measurements...")
print("=" * 60)

# Get sample from breeds table
try:
    response = supabase.table('breeds').select('*').limit(10).execute()

    if response.data:
        # Check first breed to see columns
        first_breed = response.data[0]
        print("Columns in 'breeds' table:")
        for col in sorted(first_breed.keys()):
            print(f"  - {col}")

        print("\n" + "=" * 60)
        print("Sample data from 'breeds' table:")
        print("-" * 40)

        for breed in response.data[:5]:
            print(f"\n{breed.get('name', 'Unknown')}:")
            print(f"  avg_height_cm: {breed.get('avg_height_cm')}")
            print(f"  avg_male_weight_kg: {breed.get('avg_male_weight_kg')}")
            print(f"  avg_female_weight_kg: {breed.get('avg_female_weight_kg')}")
            print(f"  avg_lifespan_years: {breed.get('avg_lifespan_years')}")

        # Count how many have data
        all_breeds = supabase.table('breeds').select('*').execute()

        with_height = sum(1 for b in all_breeds.data if b.get('avg_height_cm'))
        with_weight = sum(1 for b in all_breeds.data if b.get('avg_male_weight_kg'))
        with_lifespan = sum(1 for b in all_breeds.data if b.get('avg_lifespan_years'))

        print("\n" + "=" * 60)
        print("Data coverage in 'breeds' table:")
        print(f"  Total breeds: {len(all_breeds.data)}")
        print(f"  With height data: {with_height} ({with_height/len(all_breeds.data)*100:.1f}%)")
        print(f"  With weight data: {with_weight} ({with_weight/len(all_breeds.data)*100:.1f}%)")
        print(f"  With lifespan data: {with_lifespan} ({with_lifespan/len(all_breeds.data)*100:.1f}%)")

        # Check if this feeds the view
        print("\n" + "=" * 60)
        print("Checking breeds_unified_api view to see if it uses breeds table...")

        # Get a sample from the view
        view_response = supabase.table('breeds_unified_api').select('*').limit(1).execute()
        if view_response.data:
            view_breed = view_response.data[0]
            print(f"\nSample from view for breed: {view_breed.get('display_name')}")
            print(f"  avg_height_cm (from view): {view_breed.get('avg_height_cm')}")
            print(f"  avg_male_weight_kg (from view): {view_breed.get('avg_male_weight_kg')}")
            print(f"  height_min_cm (from view): {view_breed.get('height_min_cm')}")
            print(f"  weight_min_kg (from view): {view_breed.get('weight_min_kg')}")

            # Try to match with breeds table
            breed_name = view_breed.get('display_name')
            breeds_match = supabase.table('breeds').select('*').ilike('name', f'%{breed_name}%').limit(1).execute()
            if breeds_match.data:
                matched = breeds_match.data[0]
                print(f"\nMatching breed in 'breeds' table:")
                print(f"  avg_height_cm (from breeds): {matched.get('avg_height_cm')}")
                print(f"  avg_male_weight_kg (from breeds): {matched.get('avg_male_weight_kg')}")

        print("\n🔍 KEY INSIGHT:")
        print("The 'breeds' table has avg values (avg_height_cm, avg_male_weight_kg)")
        print("The 'breeds_comprehensive_content' table has min/max values (height_min_cm, height_max_cm)")
        print("The view likely combines both tables!")

except Exception as e:
    print(f"Error: {e}")