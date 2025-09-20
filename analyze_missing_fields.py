#!/usr/bin/env python3

"""
Analyze missing fields to identify opportunities for reaching 95% completeness
"""

import os
from dotenv import load_dotenv
from supabase import create_client
from collections import defaultdict

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_KEY')
)

def analyze_field_completeness():
    """Analyze which fields are most commonly missing"""

    # Get all breeds from unified view
    result = supabase.table('breeds_unified_api').select("*").execute()
    breeds = result.data

    total_breeds = len(breeds)
    field_stats = defaultdict(lambda: {'filled': 0, 'empty': 0, 'examples': []})

    # Critical fields to analyze
    critical_fields = [
        # Basic info
        'display_name', 'breed_slug', 'origin',

        # Physical characteristics
        'adult_weight_min_kg', 'adult_weight_max_kg', 'adult_weight_avg_kg',
        'height_min_cm', 'height_max_cm', 'avg_height_cm',
        'size_category', 'coat', 'colors', 'coat_length', 'coat_texture',

        # Lifespan
        'lifespan_min_years', 'lifespan_max_years', 'lifespan_avg_years',

        # Temperament & behavior
        'temperament', 'personality_traits', 'personality_description',
        'bark_level', 'barking_tendency', 'energy', 'energy_level_numeric',
        'trainability', 'intelligence_noted',

        # Social traits
        'good_with_children', 'good_with_pets',
        'friendliness_to_dogs', 'friendliness_to_humans',

        # Care requirements
        'exercise_level', 'exercise_needs_detail', 'recommended_daily_exercise_min',
        'grooming_needs', 'grooming_frequency', 'shedding', 'drooling_tendency',

        # Health & nutrition
        'health_issues', 'nutrition', 'weight_gain_risk_score',

        # Content
        'history', 'history_brief', 'introduction', 'fun_facts',
        'training_tips', 'general_care', 'working_roles',

        # Recognition
        'recognized_by', 'breed_standard'
    ]

    for breed in breeds:
        breed_name = breed.get('display_name', 'Unknown')

        for field in critical_fields:
            value = breed.get(field)

            if value and str(value).strip() and str(value).lower() not in ['null', 'none', '[]', '{}']:
                field_stats[field]['filled'] += 1
            else:
                field_stats[field]['empty'] += 1
                if len(field_stats[field]['examples']) < 5:
                    field_stats[field]['examples'].append(breed_name)

    return field_stats, total_breeds

def calculate_overall_completeness(field_stats, total_breeds):
    """Calculate overall database completeness"""

    total_fields = len(field_stats)
    total_possible_values = total_fields * total_breeds
    total_filled = sum(stats['filled'] for stats in field_stats.values())

    completeness = (total_filled / total_possible_values) * 100 if total_possible_values > 0 else 0

    return completeness, total_filled, total_possible_values

def identify_quick_wins(field_stats, total_breeds):
    """Identify fields that could be easily filled"""

    quick_wins = []

    for field, stats in field_stats.items():
        fill_rate = (stats['filled'] / total_breeds) * 100
        missing_count = stats['empty']

        # Fields that are mostly empty (good targets for automation)
        if fill_rate < 30 and missing_count > 100:
            quick_wins.append({
                'field': field,
                'fill_rate': fill_rate,
                'missing_count': missing_count,
                'potential_gain': (missing_count / (len(field_stats) * total_breeds)) * 100,
                'examples': stats['examples'][:3]
            })

    return sorted(quick_wins, key=lambda x: x['potential_gain'], reverse=True)

def main():
    print("=" * 80)
    print("MISSING FIELDS ANALYSIS FOR 95% COMPLETENESS")
    print("=" * 80)

    print("\nAnalyzing field completeness...")
    field_stats, total_breeds = analyze_field_completeness()

    # Calculate overall completeness
    completeness, total_filled, total_possible = calculate_overall_completeness(field_stats, total_breeds)

    print(f"\nTotal breeds: {total_breeds}")
    print(f"Total fields analyzed: {len(field_stats)}")
    print(f"Total possible values: {total_possible:,}")
    print(f"Total filled values: {total_filled:,}")
    print(f"\nCurrent completeness: {completeness:.2f}%")
    print(f"Gap to 95%: {95 - completeness:.2f}%")
    print(f"Fields needed to reach 95%: {int((0.95 * total_possible) - total_filled):,}")

    # Show field-by-field breakdown
    print("\n" + "=" * 80)
    print("FIELD COMPLETENESS BREAKDOWN")
    print("=" * 80)

    # Sort by fill rate
    sorted_fields = sorted(field_stats.items(), key=lambda x: x[1]['filled'] / total_breeds)

    print("\nLeast filled fields (best targets for improvement):")
    print("-" * 60)

    for field, stats in sorted_fields[:20]:
        fill_rate = (stats['filled'] / total_breeds) * 100
        if stats['examples']:
            examples = ", ".join(stats['examples'][:3])
            print(f"{field:35} {fill_rate:5.1f}% filled ({stats['empty']} missing)")
            print(f"  Examples: {examples}")

    # Identify quick wins
    print("\n" + "=" * 80)
    print("QUICK WIN OPPORTUNITIES")
    print("=" * 80)

    quick_wins = identify_quick_wins(field_stats, total_breeds)

    if quick_wins:
        print("\nFields with highest impact potential:")
        print("-" * 60)
        for win in quick_wins[:10]:
            print(f"\n{win['field']}:")
            print(f"  Current fill rate: {win['fill_rate']:.1f}%")
            print(f"  Missing in {win['missing_count']} breeds")
            print(f"  Potential completeness gain: +{win['potential_gain']:.2f}%")
            if win['examples']:
                print(f"  Example breeds: {', '.join(win['examples'])}")

    # Recommendations
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS TO REACH 95%")
    print("=" * 80)

    print("\n1. HIGH-IMPACT FIELDS TO TARGET:")
    for win in quick_wins[:5]:
        print(f"   - {win['field']} (+{win['potential_gain']:.2f}% potential)")

    print("\n2. AUTOMATION OPPORTUNITIES:")
    print("   - Generate 'introduction' from existing temperament + history")
    print("   - Derive 'training_tips' from trainability + temperament")
    print("   - Create 'fun_facts' from Wikipedia trivia sections")
    print("   - Extract 'working_roles' from breed history/purpose")

    print("\n3. DATA SOURCES TO LEVERAGE:")
    print("   - Wikipedia infoboxes for physical measurements")
    print("   - Breed club websites for breed standards")
    print("   - Veterinary databases for health issues")
    print("   - Training websites for exercise requirements")

    needed_gain = 95 - completeness
    print(f"\n4. TARGET: Fill approximately {int(needed_gain * total_possible / 100):,} more fields")
    print(f"   This is roughly {int(needed_gain * total_possible / 100 / total_breeds):.0f} fields per breed\n")

if __name__ == "__main__":
    main()
