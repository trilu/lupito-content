#!/usr/bin/env python3

import os
from supabase import create_client, Client
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Initialize Supabase client
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(url, key)

def analyze_field_variants():
    """Analyze field completeness considering text/boolean variants"""

    print("🔍 CORRECTED FIELD COMPLETENESS ANALYSIS")
    print("=" * 60)

    # Get all data from breeds_unified_api
    result = supabase.table('breeds_unified_api').select("*").execute()
    breeds = result.data
    total_breeds = len(breeds)

    print(f"Total breeds: {total_breeds}")

    # Get all field names
    if not breeds:
        print("No data found!")
        return

    all_fields = list(breeds[0].keys())
    print(f"Total fields: {len(all_fields)}")

    # Group related fields by base name
    field_groups = {}
    processed_fields = set()

    for field in all_fields:
        if field in processed_fields:
            continue

        base_name = field
        # Remove common suffixes to find base name
        for suffix in ['_text', '_level', '_score', '_noted', '_category']:
            if field.endswith(suffix):
                base_name = field[:-len(suffix)]
                break

        # Find all variants of this field
        variants = [f for f in all_fields if f.startswith(base_name)]

        if len(variants) > 1:
            field_groups[base_name] = variants
            processed_fields.update(variants)
        else:
            # Single field, no variants
            field_groups[field] = [field]
            processed_fields.add(field)

    # Analyze completeness for each field group
    field_analysis = {}

    for group_name, field_variants in field_groups.items():
        group_analysis = {
            'variants': field_variants,
            'completeness': {},
            'best_variant': None,
            'best_percentage': 0.0,
            'effective_completeness': 0.0
        }

        for field in field_variants:
            filled_count = 0
            sample_values = []

            for breed in breeds:
                value = breed.get(field)
                if value is not None and str(value).strip() not in ['', 'null', 'None', 'false', 'False']:
                    filled_count += 1
                    if len(sample_values) < 3:
                        sample_values.append(str(value))

            percentage = (filled_count / total_breeds) * 100

            group_analysis['completeness'][field] = {
                'filled_count': filled_count,
                'percentage': percentage,
                'sample_values': sample_values
            }

            if percentage > group_analysis['best_percentage']:
                group_analysis['best_percentage'] = percentage
                group_analysis['best_variant'] = field

        # Effective completeness is the best variant's completeness
        group_analysis['effective_completeness'] = group_analysis['best_percentage']
        field_analysis[group_name] = group_analysis

    # Sort by effective completeness (lowest first - these need attention)
    sorted_groups = sorted(field_analysis.items(),
                          key=lambda x: x[1]['effective_completeness'])

    print(f"\n📊 FIELD GROUP ANALYSIS")
    print("=" * 60)

    total_effective_completeness = 0
    completely_empty_groups = []
    high_impact_missing = []
    already_complete = []

    for group_name, analysis in sorted_groups:
        effective = analysis['effective_completeness']
        total_effective_completeness += effective

        best_variant = analysis['best_variant']
        if best_variant is None:
            # Handle case where all variants are empty
            best_variant = analysis['variants'][0]
        best_data = analysis['completeness'][best_variant]

        status = "🔴 EMPTY" if effective == 0 else "🟡 PARTIAL" if effective < 95 else "🟢 COMPLETE"

        print(f"\n{status} {group_name} ({effective:.1f}%)")

        if len(analysis['variants']) > 1:
            print(f"  Variants: {analysis['variants']}")
            for variant in analysis['variants']:
                var_data = analysis['completeness'][variant]
                marker = "👑" if variant == best_variant else "  "
                print(f"  {marker} {variant}: {var_data['filled_count']}/{total_breeds} ({var_data['percentage']:.1f}%)")
                if var_data['sample_values']:
                    print(f"     Samples: {var_data['sample_values']}")
        else:
            print(f"  {best_data['filled_count']}/{total_breeds} records")
            if best_data['sample_values']:
                print(f"  Samples: {best_data['sample_values']}")

        # Categorize for action planning
        if effective == 0:
            completely_empty_groups.append(group_name)
        elif effective < 80:  # High impact potential
            high_impact_missing.append((group_name, effective))
        elif effective >= 95:
            already_complete.append(group_name)

    # Calculate overall completeness
    overall_completeness = total_effective_completeness / len(field_analysis)

    print(f"\n" + "=" * 60)
    print(f"📈 OVERALL COMPLETENESS SUMMARY")
    print(f"=" * 60)
    print(f"Current completeness: {overall_completeness:.2f}%")
    print(f"Target: 95.00%")
    print(f"Gap to close: {95.0 - overall_completeness:.2f}%")

    print(f"\n🟢 Already complete (≥95%): {len(already_complete)} groups")
    print(f"🟡 High-impact missing (<80%): {len(high_impact_missing)} groups")
    print(f"🔴 Completely empty: {len(completely_empty_groups)} groups")

    # Show corrected insights
    print(f"\n🎯 KEY CORRECTIONS FROM PREVIOUS ANALYSIS:")
    print("=" * 60)

    # Check specific fields that were misanalyzed
    shedding_group = field_analysis.get('shedding', {})
    if shedding_group:
        print(f"✅ SHEDDING: {shedding_group['effective_completeness']:.1f}% complete")
        if 'shedding_text' in shedding_group['completeness']:
            text_data = shedding_group['completeness']['shedding_text']
            print(f"   - shedding_text: {text_data['percentage']:.1f}% (FULLY POPULATED)")
        if 'shedding' in shedding_group['completeness']:
            bool_data = shedding_group['completeness']['shedding']
            print(f"   - shedding (bool): {bool_data['percentage']:.1f}% (WAS INCORRECTLY TARGETED)")

    # Identify truly high-impact opportunities
    print(f"\n🚀 TRUE HIGH-IMPACT OPPORTUNITIES:")
    print("=" * 60)

    high_impact_missing.sort(key=lambda x: (100 - x[1]) * total_breeds, reverse=True)

    for group_name, current_pct in high_impact_missing[:10]:
        gap = 100 - current_pct
        potential_records = int(gap * total_breeds / 100)
        print(f"  {group_name}: {current_pct:.1f}% → +{potential_records} records possible")

    # Save detailed results
    with open('corrected_field_analysis.json', 'w') as f:
        json.dump({
            'overall_completeness': overall_completeness,
            'total_field_groups': len(field_analysis),
            'already_complete': already_complete,
            'high_impact_missing': high_impact_missing,
            'completely_empty': completely_empty_groups,
            'detailed_analysis': {k: v for k, v in field_analysis.items()}
        }, f, indent=2, default=str)

    print(f"\n💾 Detailed results saved to corrected_field_analysis.json")

    return {
        'overall_completeness': overall_completeness,
        'field_analysis': field_analysis,
        'high_impact_missing': high_impact_missing
    }

if __name__ == "__main__":
    analyze_field_variants()