#!/usr/bin/env python3
"""
Analyze content gaps in the unified breed view
Identify which breeds lack what information
"""

import os
from supabase import create_client
from dotenv import load_dotenv
import json
from collections import defaultdict

load_dotenv()

def analyze_content_gaps():
    # Initialize Supabase
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    supabase = create_client(url, key)

    print("="*80)
    print("ANALYZING CONTENT GAPS IN BREED DATA")
    print("="*80)

    # Get all breeds with their completeness scores
    try:
        response = supabase.table('breeds_unified_api').select(
            'breed_slug, display_name, content_completeness_score, '
            'personality_description, general_care, health_issues, '
            'fun_facts, working_roles, grooming_needs, exercise_needs_detail, '
            'training_tips, history, introduction, temperament, '
            'good_with_children, good_with_pets, coat, colors'
        ).execute()

        breeds = response.data
        total_breeds = len(breeds)

        print(f"\n📊 Total breeds analyzed: {total_breeds}")

        # Categorize breeds by completeness
        low_quality = []  # < 40%
        medium_quality = []  # 40-70%
        high_quality = []  # > 70%

        # Track missing fields
        missing_fields_count = defaultdict(int)
        critical_missing = defaultdict(list)  # Track which breeds miss critical fields

        for breed in breeds:
            score = breed.get('content_completeness_score', 0) or 0

            # Categorize by score
            if score < 40:
                low_quality.append(breed)
            elif score < 70:
                medium_quality.append(breed)
            else:
                high_quality.append(breed)

            # Check each field
            fields_to_check = {
                'personality_description': 'Personality Description',
                'general_care': 'Care Content',
                'health_issues': 'Health Information',
                'fun_facts': 'Fun Facts',
                'working_roles': 'Working Roles',
                'grooming_needs': 'Grooming Needs',
                'exercise_needs_detail': 'Exercise Details',
                'training_tips': 'Training Tips',
                'history': 'History',
                'introduction': 'Introduction',
                'temperament': 'Temperament',
                'good_with_children': 'Good with Children',
                'good_with_pets': 'Good with Pets'
            }

            for field, field_name in fields_to_check.items():
                value = breed.get(field)

                # Check if field is missing or empty
                is_missing = False
                if value is None:
                    is_missing = True
                elif isinstance(value, str) and len(value.strip()) < 10:
                    is_missing = True
                elif isinstance(value, list) and len(value) == 0:
                    is_missing = True

                if is_missing:
                    missing_fields_count[field_name] += 1

                    # Track critical missing fields for low-scoring breeds
                    if score < 50 and field in ['personality_description', 'general_care', 'introduction']:
                        critical_missing[breed['display_name']].append(field_name)

        # Print summary statistics
        print("\n" + "="*80)
        print("COMPLETENESS SCORE DISTRIBUTION")
        print("-"*60)
        print(f"🔴 Low Quality (<40%): {len(low_quality)} breeds ({len(low_quality)*100/total_breeds:.1f}%)")
        print(f"🟡 Medium Quality (40-70%): {len(medium_quality)} breeds ({len(medium_quality)*100/total_breeds:.1f}%)")
        print(f"🟢 High Quality (>70%): {len(high_quality)} breeds ({len(high_quality)*100/total_breeds:.1f}%)")

        # Print missing fields statistics
        print("\n" + "="*80)
        print("MISSING CONTENT BY FIELD")
        print("-"*60)

        # Sort by most missing
        sorted_missing = sorted(missing_fields_count.items(), key=lambda x: x[1], reverse=True)

        for field_name, count in sorted_missing:
            percentage = (count / total_breeds) * 100
            bar_length = int(percentage / 2)
            bar = "█" * bar_length + "░" * (50 - bar_length)
            print(f"{field_name:25} {bar} {count:3} breeds ({percentage:.1f}%)")

        # Print worst performing breeds
        print("\n" + "="*80)
        print("LOWEST QUALITY BREEDS (Need Immediate Attention)")
        print("-"*60)

        # Sort by completeness score
        low_quality_sorted = sorted(low_quality, key=lambda x: x.get('content_completeness_score', 0))

        print("\nBottom 20 breeds by completeness score:")
        for i, breed in enumerate(low_quality_sorted[:20], 1):
            score = breed.get('content_completeness_score', 0) or 0
            missing = critical_missing.get(breed['display_name'], [])
            print(f"{i:2}. {breed['display_name']:30} (Score: {score:4.1f}%) - Missing: {', '.join(missing[:3]) if missing else 'Multiple fields'}")

        # Popular breeds with low scores (high priority)
        print("\n" + "="*80)
        print("POPULAR BREEDS WITH LOW CONTENT SCORES")
        print("-"*60)

        popular_breeds = [
            'labrador-retriever', 'german-shepherd', 'golden-retriever',
            'french-bulldog', 'bulldog', 'poodle', 'beagle', 'rottweiler',
            'yorkshire-terrier', 'dachshund', 'boxer', 'siberian-husky',
            'great-dane', 'pug', 'boston-terrier', 'shih-tzu', 'pomeranian',
            'havanese', 'cavalier-king-charles-spaniel', 'maltese'
        ]

        print("\nPopular breeds that need content improvement:")
        for breed in breeds:
            if breed['breed_slug'] in popular_breeds:
                score = breed.get('content_completeness_score', 0) or 0
                if score < 70:
                    missing_critical = []
                    if not breed.get('personality_description') or len(str(breed.get('personality_description', '')).strip()) < 10:
                        missing_critical.append('Personality')
                    if not breed.get('general_care') or len(str(breed.get('general_care', '')).strip()) < 10:
                        missing_critical.append('Care')
                    if not breed.get('health_issues') or len(str(breed.get('health_issues', '')).strip()) < 10:
                        missing_critical.append('Health')

                    print(f"  ⚠️ {breed['display_name']:30} (Score: {score:4.1f}%) - Missing: {', '.join(missing_critical)}")

        # Specific recommendations
        print("\n" + "="*80)
        print("RECOMMENDATIONS FOR IMPROVEMENT")
        print("-"*60)

        print("\n1. CRITICAL GAPS (Affecting most breeds):")
        for field_name, count in sorted_missing[:5]:
            percentage = (count / total_breeds) * 100
            if percentage > 30:
                print(f"   - {field_name}: Missing in {count} breeds ({percentage:.1f}%)")

        print("\n2. QUICK WINS (Easy fields to populate):")
        quick_win_fields = ['good_with_children', 'good_with_pets', 'temperament']
        for field in quick_win_fields:
            field_display = field.replace('_', ' ').title()
            if field_display in missing_fields_count:
                count = missing_fields_count[field_display]
                if count > 0:
                    print(f"   - {field_display}: Can be inferred for {count} breeds")

        print("\n3. CONTENT ENRICHMENT PRIORITIES:")
        print("   - Focus on personality_description for all breeds")
        print("   - Ensure general_care is comprehensive")
        print("   - Add health_issues for breeds prone to conditions")
        print("   - Populate fun_facts for engagement")

        # Save detailed report
        report = {
            'summary': {
                'total_breeds': total_breeds,
                'average_completeness': sum(b.get('content_completeness_score', 0) or 0 for b in breeds) / total_breeds,
                'low_quality_count': len(low_quality),
                'medium_quality_count': len(medium_quality),
                'high_quality_count': len(high_quality)
            },
            'missing_fields': dict(sorted_missing),
            'low_quality_breeds': [
                {
                    'breed': b['display_name'],
                    'slug': b['breed_slug'],
                    'score': b.get('content_completeness_score', 0) or 0
                }
                for b in low_quality_sorted[:50]
            ]
        }

        with open('breed_content_gaps_report.json', 'w') as f:
            json.dump(report, f, indent=2)

        print("\n" + "="*80)
        print("📁 Detailed report saved to: breed_content_gaps_report.json")

    except Exception as e:
        print(f"❌ Error analyzing content: {e}")

if __name__ == "__main__":
    analyze_content_gaps()