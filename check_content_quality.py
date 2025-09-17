#!/usr/bin/env python3
"""
Comprehensive content quality checker for breeds data
"""

import os
from supabase import create_client
from dotenv import load_dotenv
import json

load_dotenv()

# Initialize Supabase
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(supabase_url, supabase_key)

def calculate_quality_metrics():
    # Get all breeds data
    breeds = supabase.table('breeds_published').select('*').execute().data
    breeds_details = supabase.table('breeds_details').select('*').execute().data
    comprehensive = supabase.table('breeds_comprehensive_content').select('*').execute().data

    # Create lookup dicts
    details_dict = {b['breed_slug']: b for b in breeds_details}
    comp_dict = {b['breed_slug']: b for b in comprehensive}

    total_breeds = len(breeds)
    metrics = {
        'total_breeds': total_breeds,
        'critical_fields': {},
        'enrichment_fields': {},
        'content_fields': {},
        'overall_scores': {}
    }

    # Critical fields (MUST have for nutrition calculations)
    critical_checks = {
        'has_weight': 0,
        'has_size_category': 0,
        'has_life_stages': 0,
        'has_breed_slug': 0,
        'has_display_name': 0
    }

    # Enrichment fields (Important for accuracy)
    enrichment_checks = {
        'has_specific_weight': 0,  # Not default
        'has_height': 0,
        'has_energy_level': 0,  # Not default
        'has_lifespan': 0,
        'has_origin': 0,
        'has_coat_info': 0,
        'has_trainability': 0
    }

    # Content fields (For user experience)
    content_checks = {
        'has_personality': 0,
        'has_history': 0,
        'has_care_info': 0,
        'has_fun_facts': 0,
        'has_health_info': 0,
        'has_working_roles': 0,
        'has_good_with_children': 0,
        'has_good_with_pets': 0,
        'has_introduction': 0
    }

    for breed in breeds:
        slug = breed['breed_slug']
        detail = details_dict.get(slug, {})
        comp = comp_dict.get(slug, {})

        # Critical fields
        if breed.get('ideal_weight_min_kg') and breed.get('ideal_weight_max_kg'):
            critical_checks['has_weight'] += 1
        if breed.get('size_category'):
            critical_checks['has_size_category'] += 1
        if breed.get('growth_end_months') and breed.get('senior_start_months'):
            critical_checks['has_life_stages'] += 1
        if breed.get('breed_slug'):
            critical_checks['has_breed_slug'] += 1
        if breed.get('breed_name'):
            critical_checks['has_display_name'] += 1

        # Enrichment fields
        if breed.get('ideal_weight_min_kg') and breed['ideal_weight_min_kg'] != 15.0:  # Not default
            enrichment_checks['has_specific_weight'] += 1
        if detail.get('height_cm_min') or detail.get('height_cm_max'):
            enrichment_checks['has_height'] += 1
        if breed.get('activity_baseline') != 'moderate':  # Not default
            enrichment_checks['has_energy_level'] += 1
        if detail.get('lifespan_years_min') or detail.get('lifespan_years_max'):
            enrichment_checks['has_lifespan'] += 1
        if detail.get('origin'):
            enrichment_checks['has_origin'] += 1
        if detail.get('coat') or detail.get('coat_length'):
            enrichment_checks['has_coat_info'] += 1
        if detail.get('trainability'):
            enrichment_checks['has_trainability'] += 1

        # Content fields
        if comp.get('personality_description') or comp.get('personality_traits'):
            content_checks['has_personality'] += 1
        if comp.get('history') or comp.get('history_brief'):
            content_checks['has_history'] += 1
        if comp.get('general_care') or comp.get('grooming_needs'):
            content_checks['has_care_info'] += 1
        if comp.get('fun_facts'):
            content_checks['has_fun_facts'] += 1
        if comp.get('health_issues'):
            content_checks['has_health_info'] += 1
        if comp.get('working_roles'):
            content_checks['has_working_roles'] += 1
        if comp.get('good_with_children') is not None:
            content_checks['has_good_with_children'] += 1
        if comp.get('good_with_pets') is not None:
            content_checks['has_good_with_pets'] += 1
        if comp.get('introduction'):
            content_checks['has_introduction'] += 1

    # Calculate percentages
    for field, count in critical_checks.items():
        metrics['critical_fields'][field] = {
            'count': count,
            'percentage': round(count / total_breeds * 100, 1)
        }

    for field, count in enrichment_checks.items():
        metrics['enrichment_fields'][field] = {
            'count': count,
            'percentage': round(count / total_breeds * 100, 1)
        }

    for field, count in content_checks.items():
        metrics['content_fields'][field] = {
            'count': count,
            'percentage': round(count / total_breeds * 100, 1)
        }

    # Calculate overall scores
    critical_score = sum(c['percentage'] for c in metrics['critical_fields'].values()) / len(critical_checks)
    enrichment_score = sum(c['percentage'] for c in metrics['enrichment_fields'].values()) / len(enrichment_checks)
    content_score = sum(c['percentage'] for c in metrics['content_fields'].values()) / len(content_checks)

    # Weighted overall score
    overall_score = (
        critical_score * 0.5 +  # Critical fields are 50% of score
        enrichment_score * 0.3 +  # Enrichment is 30%
        content_score * 0.2  # Content is 20%
    )

    metrics['overall_scores'] = {
        'critical_score': round(critical_score, 1),
        'enrichment_score': round(enrichment_score, 1),
        'content_score': round(content_score, 1),
        'overall_weighted_score': round(overall_score, 1)
    }

    return metrics

def print_report(metrics):
    print("\n" + "="*60)
    print("COMPREHENSIVE CONTENT QUALITY REPORT")
    print("="*60)

    print(f"\nTotal Breeds Analyzed: {metrics['total_breeds']}")

    print("\n1. CRITICAL FIELDS (Required for nutrition)")
    print("-" * 40)
    for field, data in metrics['critical_fields'].items():
        status = "✅" if data['percentage'] >= 95 else "⚠️" if data['percentage'] >= 80 else "❌"
        print(f"  {status} {field}: {data['percentage']}% ({data['count']}/{metrics['total_breeds']})")

    print("\n2. ENRICHMENT FIELDS (For accuracy)")
    print("-" * 40)
    for field, data in metrics['enrichment_fields'].items():
        status = "✅" if data['percentage'] >= 80 else "⚠️" if data['percentage'] >= 50 else "❌"
        print(f"  {status} {field}: {data['percentage']}% ({data['count']}/{metrics['total_breeds']})")

    print("\n3. CONTENT FIELDS (User experience)")
    print("-" * 40)
    for field, data in metrics['content_fields'].items():
        status = "✅" if data['percentage'] >= 50 else "⚠️" if data['percentage'] >= 20 else "❌"
        print(f"  {status} {field}: {data['percentage']}% ({data['count']}/{metrics['total_breeds']})")

    print("\n" + "="*60)
    print("OVERALL QUALITY SCORES")
    print("="*60)
    scores = metrics['overall_scores']
    print(f"  Critical Fields Score: {scores['critical_score']}%")
    print(f"  Enrichment Score: {scores['enrichment_score']}%")
    print(f"  Content Score: {scores['content_score']}%")
    print(f"\n  🎯 OVERALL QUALITY: {scores['overall_weighted_score']}%")

    target = 95
    if scores['overall_weighted_score'] >= target:
        print(f"  ✅ TARGET MET! (>= {target}%)")
    else:
        gap = target - scores['overall_weighted_score']
        print(f"  ❌ Gap to {target}%: {gap:.1f}%")

    # Recommendations
    print("\n" + "="*60)
    print("PRIORITY IMPROVEMENTS TO REACH 95%")
    print("="*60)

    issues = []
    for field, data in metrics['critical_fields'].items():
        if data['percentage'] < 95:
            issues.append((f"Critical: {field}", data['percentage'], 95 - data['percentage']))

    for field, data in metrics['enrichment_fields'].items():
        if data['percentage'] < 80:
            issues.append((f"Enrichment: {field}", data['percentage'], 80 - data['percentage']))

    # Sort by gap
    issues.sort(key=lambda x: x[2], reverse=True)

    print("\nTop Issues to Fix:")
    for i, (field, current, gap) in enumerate(issues[:5], 1):
        print(f"  {i}. {field}: {current}% (need +{gap:.1f}%)")

    # Save to file
    with open('content_quality_report.json', 'w') as f:
        json.dump(metrics, f, indent=2)
    print("\nFull metrics saved to content_quality_report.json")

if __name__ == "__main__":
    metrics = calculate_quality_metrics()
    print_report(metrics)