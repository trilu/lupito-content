#!/usr/bin/env python3
"""
Gap Analysis Report - Analyze remaining missing fields after ScrapingBee assault
Generate comprehensive report for strategy to reach 95% completeness
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

        # All fields we track
        self.all_fields = [
            'display_name', 'breed_slug', 'description', 'origin', 'image_url',
            'size_category', 'weight_range', 'height_range', 'life_expectancy',
            'temperament', 'energy_level', 'exercise_needs', 'grooming_frequency',
            'trainability', 'health_issues', 'good_with_children', 'good_with_pets',
            'space_requirements', 'dietary_needs', 'coat_type', 'color_variations',
            'recognition_status', 'breed_group', 'exercise_needs_detail', 'training_tips',
            'grooming_needs', 'personality_traits'
        ]

        # Critical fields for 95% target
        self.critical_fields = [
            'grooming_frequency', 'good_with_children', 'good_with_pets',
            'exercise_level', 'energy_level', 'personality_traits',
            'health_issues', 'trainability', 'space_requirements'
        ]

    def analyze_current_state(self):
        """Get comprehensive analysis of current completeness"""
        print("\n" + "="*80)
        print("BREED CONTENT GAP ANALYSIS REPORT")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)

        # Get all breeds from comprehensive content table
        response = self.supabase.table('breeds_comprehensive_content').select('*').execute()
        breeds_data = response.data

        print(f"\n📊 OVERALL STATISTICS")
        print(f"Total breeds in database: {len(breeds_data)}")

        # Calculate completeness per field
        field_stats = {}
        breed_completeness = {}

        for field in self.all_fields:
            if field in ['breed_slug', 'display_name']:  # These should always exist
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
            filled = sum(1 for field in self.all_fields if breed.get(field) and field not in ['breed_slug', 'display_name'])
            total = len(self.all_fields) - 2  # Exclude breed_slug and display_name
            breed_completeness[breed['breed_slug']] = {
                'display_name': breed.get('display_name', breed['breed_slug']),
                'filled': filled,
                'total': total,
                'percentage': (filled / total) * 100 if total > 0 else 0
            }

        # Overall completeness
        total_possible = len(breeds_data) * (len(self.all_fields) - 2)
        total_filled = sum(stats['filled'] for stats in field_stats.values())
        overall_completeness = (total_filled / total_possible) * 100 if total_possible > 0 else 0

        print(f"\n🎯 OVERALL COMPLETENESS: {overall_completeness:.1f}%")
        print(f"   Total fields possible: {total_possible:,}")
        print(f"   Total fields filled: {total_filled:,}")
        print(f"   Total fields missing: {total_possible - total_filled:,}")
        print(f"   Gap to 95% target: {95 - overall_completeness:.1f}%")

        # Critical fields analysis
        print(f"\n🔴 CRITICAL FIELDS STATUS (High Priority)")
        print("-" * 60)
        print(f"{'Field':<25} {'Filled':<10} {'Missing':<10} {'Coverage':<10}")
        print("-" * 60)

        critical_gaps = []
        for field in self.critical_fields:
            if field in field_stats:
                stats = field_stats[field]
                print(f"{field:<25} {stats['filled']:<10} {stats['missing']:<10} {stats['percentage']:.1f}%")
                if stats['percentage'] < 90:
                    critical_gaps.append({
                        'field': field,
                        'missing': stats['missing'],
                        'percentage': stats['percentage']
                    })

        # All fields ranking
        print(f"\n📊 ALL FIELDS RANKING (By Coverage)")
        print("-" * 60)
        sorted_fields = sorted(field_stats.items(), key=lambda x: x[1]['percentage'], reverse=True)

        for field, stats in sorted_fields[:10]:
            status = "✅" if stats['percentage'] >= 90 else "🟡" if stats['percentage'] >= 70 else "🔴"
            print(f"{status} {field:<25} {stats['percentage']:>6.1f}% ({stats['filled']}/{len(breeds_data)})")

        print("\n...")

        for field, stats in sorted_fields[-10:]:
            status = "✅" if stats['percentage'] >= 90 else "🟡" if stats['percentage'] >= 70 else "🔴"
            print(f"{status} {field:<25} {stats['percentage']:>6.1f}% ({stats['filled']}/{len(breeds_data)})")

        # Breeds with most gaps
        print(f"\n🐕 BREEDS WITH MOST GAPS (Target for manual curation)")
        print("-" * 60)
        sorted_breeds = sorted(breed_completeness.items(), key=lambda x: x[1]['percentage'])

        for breed_slug, data in sorted_breeds[:20]:
            print(f"{data['display_name']:<40} {data['percentage']:>5.1f}% ({data['filled']}/{data['total']} fields)")

        # Strategy recommendations
        print(f"\n📋 STRATEGIC RECOMMENDATIONS TO REACH 95%")
        print("="*60)

        fields_under_50 = [f for f, s in field_stats.items() if s['percentage'] < 50]
        fields_50_to_80 = [f for f, s in field_stats.items() if 50 <= s['percentage'] < 80]
        fields_80_to_95 = [f for f, s in field_stats.items() if 80 <= s['percentage'] < 95]

        print(f"\n1. IMMEDIATE PRIORITIES (Fields <50% complete): {len(fields_under_50)} fields")
        for field in fields_under_50[:5]:
            print(f"   - {field}: {field_stats[field]['percentage']:.1f}% ({field_stats[field]['missing']} breeds missing)")

        print(f"\n2. SECONDARY TARGETS (50-80% complete): {len(fields_50_to_80)} fields")
        for field in fields_50_to_80[:5]:
            print(f"   - {field}: {field_stats[field]['percentage']:.1f}% ({field_stats[field]['missing']} breeds missing)")

        print(f"\n3. FINAL PUSH (80-95% complete): {len(fields_80_to_95)} fields")
        for field in fields_80_to_95[:5]:
            print(f"   - {field}: {field_stats[field]['percentage']:.1f}% ({field_stats[field]['missing']} breeds missing)")

        # Calculate effort required
        fields_needed_for_95 = int(total_possible * 0.95) - total_filled
        print(f"\n🎯 EFFORT REQUIRED FOR 95%")
        print(f"   Fields needed: {fields_needed_for_95:,}")
        print(f"   Average per breed: {fields_needed_for_95/len(breeds_data):.1f}")

        # Save detailed report
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'overall_completeness': overall_completeness,
            'total_breeds': len(breeds_data),
            'field_statistics': field_stats,
            'breeds_with_gaps': sorted_breeds[:50],
            'critical_gaps': critical_gaps,
            'gap_to_target': 95 - overall_completeness
        }

        with open('gap_analysis_report.json', 'w') as f:
            json.dump(report_data, f, indent=2)

        print(f"\n✅ Detailed report saved to gap_analysis_report.json")

        return overall_completeness, field_stats, breed_completeness

if __name__ == "__main__":
    analyzer = GapAnalysisReport()
    completeness, field_stats, breed_stats = analyzer.analyze_current_state()