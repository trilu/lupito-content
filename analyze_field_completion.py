#!/usr/bin/env python3
"""
Analyze field completion rates in breeds_unified_api view
to determine which fields need work for Phase 1
"""

import os
from dotenv import load_dotenv
from supabase import create_client
from collections import defaultdict

load_dotenv()

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY'))

# Get all data from the unified view
print("Fetching data from breeds_unified_api view...")
response = supabase.table('breeds_unified_api').select('*').execute()
breeds = response.data

total_breeds = len(breeds)
print(f"Total breeds: {total_breeds}\n")

# Define the fields we care about for content completeness
content_fields = [
    # Physical characteristics
    'adult_weight_min_kg', 'adult_weight_max_kg', 'adult_weight_avg_kg',
    'height_min_cm', 'height_max_cm', 'avg_height_cm',
    'avg_male_weight_kg', 'avg_female_weight_kg',
    'lifespan_min_years', 'lifespan_max_years', 'lifespan_avg_years',

    # Appearance
    'coat', 'coat_texture', 'coat_length_text', 'colors', 'color_varieties',

    # Behavioral traits
    'energy', 'trainability', 'shedding_text', 'barking_tendency',
    'drooling_tendency', 'energy_level_numeric', 'bark_level',
    'friendliness_to_dogs', 'friendliness_to_humans',

    # Personality & temperament
    'personality_description', 'personality_traits', 'temperament',
    'good_with_children', 'good_with_pets', 'intelligence_noted',

    # Care requirements
    'general_care', 'grooming_needs', 'grooming_frequency',
    'exercise_needs_detail', 'exercise_level', 'training_tips',

    # Health & nutrition
    'health_issues', 'nutrition', 'weight_gain_risk_score', 'climate_tolerance',

    # Life stages
    'growth_end_months', 'senior_start_months',

    # Origin & history
    'origin', 'history', 'history_brief', 'introduction',

    # Fun & enrichment
    'fun_facts', 'has_world_records', 'working_roles',

    # Breed standards
    'breed_standard', 'recognized_by',

    # Activity
    'recommended_daily_exercise_min', 'activity_level_profile',

    # Care profile
    'care_profile'
]

# Calculate completion rates for each field
field_stats = {}
for field in content_fields:
    count = 0
    non_empty_count = 0

    for breed in breeds:
        value = breed.get(field)
        if value is not None:
            count += 1
            # Check for non-empty arrays, non-empty strings, and non-zero numbers
            if isinstance(value, list):
                if len(value) > 0:
                    non_empty_count += 1
            elif isinstance(value, str):
                if value.strip():
                    non_empty_count += 1
            elif isinstance(value, (int, float)):
                if value > 0:
                    non_empty_count += 1
            else:
                non_empty_count += 1

    completion_rate = (non_empty_count / total_breeds) * 100
    missing_count = total_breeds - non_empty_count
    field_stats[field] = {
        'filled': non_empty_count,
        'missing': missing_count,
        'completion_rate': completion_rate
    }

# Sort fields by completion rate
sorted_fields = sorted(field_stats.items(), key=lambda x: x[1]['completion_rate'])

print("=" * 80)
print("FIELD COMPLETION ANALYSIS")
print("=" * 80)

print("\n🔴 CRITICAL GAPS (0-25% complete) - HIGH PRIORITY:")
print("-" * 60)
for field, stats in sorted_fields:
    if stats['completion_rate'] <= 25:
        print(f"  {field:35s}: {stats['completion_rate']:5.1f}% ({stats['filled']:3}/{total_breeds}) - Missing: {stats['missing']}")

print("\n🟡 MODERATE GAPS (25-50% complete) - MEDIUM PRIORITY:")
print("-" * 60)
for field, stats in sorted_fields:
    if 25 < stats['completion_rate'] <= 50:
        print(f"  {field:35s}: {stats['completion_rate']:5.1f}% ({stats['filled']:3}/{total_breeds}) - Missing: {stats['missing']}")

print("\n🟢 PARTIAL COMPLETION (50-75% complete) - QUICK WINS:")
print("-" * 60)
for field, stats in sorted_fields:
    if 50 < stats['completion_rate'] <= 75:
        print(f"  {field:35s}: {stats['completion_rate']:5.1f}% ({stats['filled']:3}/{total_breeds}) - Missing: {stats['missing']}")

print("\n✅ NEAR COMPLETE (75-95% complete) - LOW PRIORITY:")
print("-" * 60)
for field, stats in sorted_fields:
    if 75 < stats['completion_rate'] <= 95:
        print(f"  {field:35s}: {stats['completion_rate']:5.1f}% ({stats['filled']:3}/{total_breeds}) - Missing: {stats['missing']}")

print("\n✨ FULLY COMPLETE (95-100% complete):")
print("-" * 60)
for field, stats in sorted_fields:
    if stats['completion_rate'] > 95:
        print(f"  {field:35s}: {stats['completion_rate']:5.1f}% ({stats['filled']:3}/{total_breeds})")

# Calculate potential impact
print("\n" + "=" * 80)
print("PHASE 1 RECOMMENDATIONS")
print("=" * 80)

# Focus on fields that are 40-80% complete for quick wins
quick_win_fields = [(f, s) for f, s in sorted_fields if 40 <= s['completion_rate'] <= 80]
critical_fields = [(f, s) for f, s in sorted_fields if s['completion_rate'] < 40]

print("\n📊 QUICK WIN TARGETS (40-80% complete):")
print("These fields can be completed most efficiently")
print("-" * 60)
total_missing = 0
for field, stats in quick_win_fields:
    print(f"  {field:35s}: Need {stats['missing']:3} more breeds ({stats['completion_rate']:5.1f}% → 100%)")
    total_missing += stats['missing']
print(f"\nTotal fields to fill for quick wins: {total_missing}")
estimated_gain = (total_missing / (total_breeds * len(content_fields))) * 100
print(f"Estimated completeness gain: +{estimated_gain:.1f}%")

print("\n🎯 HIGH-IMPACT CRITICAL FIELDS (<40% complete):")
print("These need more effort but are essential")
print("-" * 60)
critical_missing = 0
for field, stats in critical_fields[:10]:  # Top 10 critical
    print(f"  {field:35s}: Need {stats['missing']:3} more breeds ({stats['completion_rate']:5.1f}% → 100%)")
    critical_missing += stats['missing']
print(f"\nTotal fields to fill for critical: {critical_missing}")
critical_gain = (critical_missing / (total_breeds * len(content_fields))) * 100
print(f"Estimated completeness gain: +{critical_gain:.1f}%")

print("\n" + "=" * 80)
print("FINAL RECOMMENDATION FOR PHASE 1 RE-RUN")
print("=" * 80)
print("\nTarget these fields in priority order:")
print("\n1. QUICK WINS (Most efficient):")
for i, (field, stats) in enumerate(quick_win_fields[:5], 1):
    print(f"   {i}. {field} - Missing {stats['missing']} breeds")

print("\n2. CRITICAL GAPS (High impact):")
for i, (field, stats) in enumerate(critical_fields[:5], 1):
    print(f"   {i}. {field} - Missing {stats['missing']} breeds")

print("\n" + "=" * 80)