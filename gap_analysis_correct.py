#!/usr/bin/env python3
"""
Gap Analysis Report - Analyze remaining missing fields in breeds_unified_api
The correct table that feeds the API
"""

import os
import json
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class GapAnalysisReport:
    def __init__(self):
        """Initialize gap analysis system"""
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

        # Fields in breeds_unified_api table
        self.all_fields = [
            'display_name', 'breed_slug', 'description', 'origin', 'image_url',
            'size_category', 'weight_range', 'height_range', 'life_expectancy',
            'temperament', 'energy_level', 'exercise_needs', 'grooming_frequency',
            'trainability', 'health_issues', 'good_with_children', 'good_with_pets',
            'space_requirements', 'dietary_needs', 'coat_type', 'color_variations',
            'recognition_status', 'breed_group', 'exercise_needs_detail', 'training_tips',
            'grooming_needs', 'personality_traits'
        ]

        # Critical fields for user experience
        self.critical_fields = [
            'description', 'image_url', 'size_category', 'temperament',
            'grooming_frequency', 'good_with_children', 'good_with_pets',
            'exercise_needs', 'energy_level', 'personality_traits',
            'health_issues', 'trainability', 'space_requirements'
        ]

    def analyze_current_state(self):
        """Get comprehensive analysis of current completeness"""
        print("\n" + "="*80)
        print("BREED CONTENT GAP ANALYSIS REPORT - breeds_unified_api")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)

        # Get all breeds from the CORRECT table - breeds_unified_api
        response = self.supabase.table('breeds_unified_api').select('*').execute()
        breeds_data = response.data

        print(f"\n📊 OVERALL STATISTICS")
        print(f"Total breeds in database: {len(breeds_data)}")

        # Calculate completeness per field
        field_stats = {}
        breed_completeness = {}

        for field in self.all_fields:
            if field in ['breed_slug']:  # This should always exist
                continue
            filled_count = sum(1 for breed in breeds_data if breed.get(field))
            percentage = (filled_count / len(breeds_data)) * 100 if breeds_data else 0
            field_stats[field] = {
                'filled': filled_count,
                'missing': len(breeds_data) - filled_count,
                'percentage': percentage
            }

        # Calculate per-breed completeness
        for breed in breeds_data:
            filled = sum(1 for field in self.all_fields if breed.get(field) and field not in ['breed_slug'])
            total = len(self.all_fields) - 1  # Exclude breed_slug
            breed_completeness[breed['breed_slug']] = {
                'display_name': breed.get('display_name', breed['breed_slug']),
                'filled': filled,
                'total': total,
                'percentage': (filled / total) * 100 if total > 0 else 0
            }

        # Overall completeness
        total_possible = len(breeds_data) * (len(self.all_fields) - 1)
        total_filled = sum(stats['filled'] for stats in field_stats.values())
        overall_completeness = (total_filled / total_possible) * 100 if total_possible > 0 else 0

        print(f"\n🎯 OVERALL COMPLETENESS: {overall_completeness:.1f}%")
        print(f"   Total fields possible: {total_possible:,}")
        print(f"   Total fields filled: {total_filled:,}")
        print(f"   Total fields missing: {total_possible - total_filled:,}")
        print(f"   Gap to 95% target: {95 - overall_completeness:.1f}%")

        # After ScrapingBee assault analysis
        print(f"\n📈 SCRAPINGBEE ASSAULT IMPACT")
        print("-" * 60)
        print(f"{'Field':<25} {'Before':<12} {'After':<12} {'Gain':<10}")
        print("-" * 60)

        # These are the fields we targeted in the assault
        assault_fields = ['grooming_frequency', 'good_with_children', 'good_with_pets']
        for field in assault_fields:
            if field in field_stats:
                stats = field_stats[field]
                # Estimate before (we know we added 661 fields across these 3)
                print(f"{field:<25} {'~10%':<12} {stats['percentage']:.1f}%{'':>7} +{stats['percentage']-10:.1f}%")

        # Critical fields analysis
        print(f"\n🔴 CRITICAL FIELDS STATUS (Priority for User Experience)")
        print("-" * 60)
        print(f"{'Field':<25} {'Filled':<10} {'Missing':<10} {'Coverage':<10}")
        print("-" * 60)

        critical_gaps = []
        for field in self.critical_fields:
            if field in field_stats:
                stats = field_stats[field]
                status = "✅" if stats['percentage'] >= 90 else "🟡" if stats['percentage'] >= 50 else "🔴"
                print(f"{status} {field:<22} {stats['filled']:<10} {stats['missing']:<10} {stats['percentage']:.1f}%")
                if stats['percentage'] < 90:
                    critical_gaps.append({
                        'field': field,
                        'missing': stats['missing'],
                        'percentage': stats['percentage']
                    })

        # All fields ranking
        print(f"\n📊 ALL FIELDS COMPLETENESS RANKING")
        print("-" * 60)
        sorted_fields = sorted(field_stats.items(), key=lambda x: x[1]['percentage'], reverse=True)

        for field, stats in sorted_fields:
            status = "✅" if stats['percentage'] >= 90 else "🟡" if stats['percentage'] >= 70 else "🔴"
            bar = "█" * int(stats['percentage'] / 5) + "░" * (20 - int(stats['percentage'] / 5))
            print(f"{status} {field:<25} {bar} {stats['percentage']:>6.1f}%")

        # Breeds with most gaps
        print(f"\n🐕 TOP 20 BREEDS WITH MOST GAPS")
        print("-" * 60)
        sorted_breeds = sorted(breed_completeness.items(), key=lambda x: x[1]['percentage'])

        for breed_slug, data in sorted_breeds[:20]:
            missing_fields = 26 - data['filled']
            print(f"{data['display_name']:<35} {data['percentage']:>5.1f}% complete ({missing_fields} fields missing)")

        # Strategy recommendations
        print(f"\n📋 STRATEGIC PATH TO 95% COMPLETENESS")
        print("="*60)

        fields_under_50 = [(f, s) for f, s in field_stats.items() if s['percentage'] < 50]
        fields_50_to_80 = [(f, s) for f, s in field_stats.items() if 50 <= s['percentage'] < 80]
        fields_80_to_95 = [(f, s) for f, s in field_stats.items() if 80 <= s['percentage'] < 95]

        print(f"\n🔥 PHASE 1: Critical Gaps (<50% complete) - {len(fields_under_50)} fields")
        for field, stats in sorted(fields_under_50, key=lambda x: x[1]['missing'], reverse=True)[:10]:
            print(f"   • {field}: {stats['percentage']:.1f}% ({stats['missing']} breeds need this)")

        print(f"\n⚡ PHASE 2: Major Gaps (50-80% complete) - {len(fields_50_to_80)} fields")
        for field, stats in sorted(fields_50_to_80, key=lambda x: x[1]['missing'], reverse=True)[:5]:
            print(f"   • {field}: {stats['percentage']:.1f}% ({stats['missing']} breeds need this)")

        print(f"\n✨ PHASE 3: Final Push (80-95% complete) - {len(fields_80_to_95)} fields")
        for field, stats in sorted(fields_80_to_95, key=lambda x: x[1]['missing'], reverse=True)[:5]:
            print(f"   • {field}: {stats['percentage']:.1f}% ({stats['missing']} breeds need this)")

        # Calculate effort required
        fields_needed_for_95 = int(total_possible * 0.95) - total_filled
        print(f"\n🎯 EFFORT METRICS TO REACH 95%")
        print(f"   Total fields needed: {fields_needed_for_95:,}")
        print(f"   Average fields per breed: {fields_needed_for_95/len(breeds_data):.1f}")

        # Estimate based on assault success
        if fields_needed_for_95 > 0:
            print(f"\n   If we maintain 46% success rate from ScrapingBee assault:")
            print(f"   • Need to attempt: {int(fields_needed_for_95 / 0.46):,} field searches")
            print(f"   • Estimated time: {int(fields_needed_for_95 / 0.46 / 300):.0f} hours of processing")

        # Top priority actions
        print(f"\n🚀 RECOMMENDED NEXT ACTIONS")
        print("-" * 60)
        print("1. Import structured data from Dog API for physical characteristics")
        print("2. Generate descriptions using GPT-4 based on existing data")
        print("3. Complete 'good_with_pets' field (only 11.6% complete!)")
        print("4. Fill size_category, weight_range, height_range from breed standards")
        print("5. Add breed_group and origin from kennel club databases")

        # Save detailed report
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'overall_completeness': overall_completeness,
            'total_breeds': len(breeds_data),
            'field_statistics': field_stats,
            'critical_gaps': critical_gaps,
            'gap_to_95_target': 95 - overall_completeness,
            'fields_needed': fields_needed_for_95
        }

        with open('gap_analysis_correct.json', 'w') as f:
            json.dump(report_data, f, indent=2)

        print(f"\n✅ Detailed report saved to gap_analysis_correct.json")

        return overall_completeness, field_stats, breed_completeness

if __name__ == "__main__":
    analyzer = GapAnalysisReport()
    completeness, field_stats, breed_stats = analyzer.analyze_current_state()