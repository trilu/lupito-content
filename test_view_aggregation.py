#!/usr/bin/env python3
"""
Test script to verify the view aggregation fix
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY'))

print("=" * 60)
print("TESTING VIEW AGGREGATION FIX")
print("=" * 60)

# Test 1: Check if breeds table has data
print("\n1. Checking breeds table for physical data...")
breeds_data = supabase.table('breeds').select('name_en, avg_height_cm, avg_male_weight_kg, avg_female_weight_kg').limit(5).execute()

if breeds_data.data:
    print(f"   Found {len(breeds_data.data)} breeds with data:")
    for breed in breeds_data.data[:3]:
        print(f"   - {breed.get('name_en', 'Unknown')}: height={breed.get('avg_height_cm')}, male_weight={breed.get('avg_male_weight_kg')}")

# Test 2: Check current view data (the view doesn't have avg columns yet)
print("\n2. Checking current breeds_unified_api view...")
view_data = supabase.table('breeds_unified_api').select('breed_slug, display_name, height_min_cm, height_max_cm, adult_weight_min_kg, adult_weight_max_kg').limit(5).execute()

if view_data.data:
    print(f"   Current view data for {len(view_data.data)} breeds:")
    for breed in view_data.data[:3]:
        print(f"   - {breed.get('display_name')}: height_min={breed.get('height_min_cm')}, weight_min={breed.get('adult_weight_min_kg')}")

# Test 3: Check if we can match breeds
print("\n3. Testing breed matching between tables...")
test_breeds = ['golden-retriever', 'german-shepherd', 'labrador-retriever', 'french-bulldog', 'beagle']

for breed_slug in test_breeds:
    # Check breeds_published
    bp_data = supabase.table('breeds_published').select('display_name').eq('breed_slug', breed_slug).limit(1).execute()

    if bp_data.data:
        display_name = bp_data.data[0].get('display_name')

        # Try to find in breeds table by name match
        # The breeds table doesn't have breed_slug, only name_en
        b_data = supabase.table('breeds').select('avg_height_cm, avg_male_weight_kg').ilike('name_en', f'%{display_name}%').limit(1).execute()

        if b_data.data:
            print(f"   ✓ {breed_slug}: Found match with height={b_data.data[0].get('avg_height_cm')}")
        else:
            print(f"   ✗ {breed_slug}: No match found")

# Test 4: Count coverage
print("\n4. Analyzing data coverage...")

# Count breeds table coverage
all_breeds = supabase.table('breeds').select('avg_height_cm, avg_male_weight_kg').execute()
with_height = sum(1 for b in all_breeds.data if b.get('avg_height_cm'))
with_weight = sum(1 for b in all_breeds.data if b.get('avg_male_weight_kg'))

print(f"   Breeds table coverage:")
print(f"   - Total: {len(all_breeds.data)}")
print(f"   - With height: {with_height} ({with_height/len(all_breeds.data)*100:.1f}%)")
print(f"   - With weight: {with_weight} ({with_weight/len(all_breeds.data)*100:.1f}%)")

# Count view coverage (current view doesn't have avg columns, only min/max)
view_all = supabase.table('breeds_unified_api').select('height_min_cm, adult_weight_min_kg').execute()
view_with_height = sum(1 for b in view_all.data if b.get('height_min_cm'))
view_with_weight = sum(1 for b in view_all.data if b.get('adult_weight_min_kg'))

print(f"\n   Current view coverage:")
print(f"   - Total: {len(view_all.data)}")
print(f"   - With height: {view_with_height} ({view_with_height/len(view_all.data)*100:.1f}% if view_all.data else 0)")
print(f"   - With weight: {view_with_weight} ({view_with_weight/len(view_all.data)*100:.1f}% if view_all.data else 0)")

print("\n" + "=" * 60)
print("EXPECTED IMPROVEMENT AFTER FIX:")
print(f"Height data: {view_with_height} → {with_height} breeds (+{with_height - view_with_height})")
print(f"Weight data: {view_with_weight} → {with_weight} breeds (+{with_weight - view_with_weight})")
print("=" * 60)

print("\n📋 SQL script created: fix_breeds_view_aggregation.sql")
print("   Run this script to fix the view aggregation!")