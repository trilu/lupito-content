#!/usr/bin/env python3
"""
FINAL Gap Analysis - Using ACTUAL breeds_unified_api columns (65 total)
"""

import os
import json
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class FinalGapAnalysisReport:
    def __init__(self):
        """Initialize gap analysis system"""
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

        # Exclude system/metadata columns from completeness calculation
        self.system_columns = [
            'id', 'breed_slug', 'created_at', 'updated_at', 'scraped_at',
            'content_updated_at', 'content_completeness_score', 'data_quality_grade',
            'conflict_flags', 'override_reason', 'care_content_word_count',
            'has_rich_content', 'has_world_records', 'intelligence_noted'
        ]

        # Content fields that matter for user experience
        self.content_fields = [
            'display_name', 'origin', 'size_category', 'size_category_display',
            'adult_weight_avg_kg', 'adult_weight_max_kg', 'adult_weight_min_kg',
            'height_max_cm', 'height_min_cm', 'lifespan_avg_years',
            'lifespan_max_years', 'lifespan_min_years', 'temperament',
            'personality_traits', 'personality_description', 'energy',
            'energy_level_display', 'exercise_level', 'exercise_needs_detail',
            'grooming_frequency', 'grooming_needs', 'good_with_children',
            'good_with_pets', 'friendliness_to_dogs', 'friendliness_to_humans',
            'trainability', 'training_tips', 'health_issues', 'coat',
            'coat_length', 'colors', 'color_varieties', 'shedding',
            'bark_level', 'aliases', 'recognized_by', 'working_roles',
            'introduction', 'history', 'history_brief', 'fun_facts',
            'general_care', 'breed_standard', 'wikipedia_url',
            'age_bounds_from', 'growth_end_months', 'senior_start_months',
            'height_from', 'weight_from', 'size_from', 'lifespan_from'
        ]

    def analyze_current_state(self):
        """Get comprehensive analysis of current completeness"""
        print("\n" + "="*80)
        print("FINAL BREED CONTENT GAP ANALYSIS - ACTUAL breeds_unified_api COLUMNS")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)

        # Get all breeds
        response = self.supabase.table('breeds_unified_api').select('*').execute()
        breeds_data = response.data
        total_breeds = len(breeds_data)

        print(f"\n📊 DATABASE OVERVIEW")
        print(f"Total breeds: {total_breeds}")
        print(f"Total columns: 65")
        print(f"Content fields (excluding system): {len(self.content_fields)}")

        # Get actual column list from first breed
        actual_columns = list(breeds_data[0].keys()) if breeds_data else []
        content_only_fields = [col for col in actual_columns if col not in self.system_columns]

        # Calculate completeness per content field
        field_stats = {}
        for field in content_only_fields:
            filled_count = sum(1 for breed in breeds_data if breed.get(field) not in [None, '', 0])
            percentage = (filled_count / total_breeds) * 100 if total_breeds > 0 else 0
            field_stats[field] = {
                'filled': filled_count,
                'missing': total_breeds - filled_count,
                'percentage': percentage
            }

        # Overall completeness (content fields only)
        total_possible = total_breeds * len(content_only_fields)
        total_filled = sum(stats['filled'] for stats in field_stats.values())
        overall_completeness = (total_filled / total_possible) * 100 if total_possible > 0 else 0

        print(f"\n🎯 OVERALL COMPLETENESS: {overall_completeness:.1f}%")
        print(f"   Content fields possible: {total_possible:,}")
        print(f"   Content fields filled: {total_filled:,}")
        print(f"   Content fields missing: {total_possible - total_filled:,}")
        print(f"   Gap to 95% target: {95 - overall_completeness:.1f}%")

        # ScrapingBee assault impact
        assault_fields = ['grooming_frequency', 'good_with_children', 'good_with_pets']
        print(f"\n🚀 SCRAPINGBEE ASSAULT IMPACT")
        print("-" * 60)
        for field in assault_fields:
            if field in field_stats:
                stats = field_stats[field]
                print(f"{field:<25} {stats['percentage']:>6.1f}% ({stats['filled']}/{total_breeds})")

        # Field completeness ranking
        print(f"\n📊 FIELD COMPLETENESS RANKING")
        print("-" * 80)
        sorted_fields = sorted(field_stats.items(), key=lambda x: x[1]['percentage'], reverse=True)

        print("TOP 15 MOST COMPLETE FIELDS:")
        for field, stats in sorted_fields[:15]:
            status = "✅" if stats['percentage'] >= 90 else "🟡" if stats['percentage'] >= 50 else "🔴"
            bar = "█" * int(stats['percentage'] / 5) + "░" * (20 - int(stats['percentage'] / 5))
            print(f"{status} {field:<30} {bar} {stats['percentage']:>6.1f}%")

        print("\nBOTTOM 15 LEAST COMPLETE FIELDS:")
        for field, stats in sorted_fields[-15:]:
            status = "✅" if stats['percentage'] >= 90 else "🟡" if stats['percentage'] >= 50 else "🔴"
            bar = "█" * int(stats['percentage'] / 5) + "░" * (20 - int(stats['percentage'] / 5))
            print(f"{status} {field:<30} {bar} {stats['percentage']:>6.1f}%")

        # Strategy for 95%
        fields_under_50 = [(f, s) for f, s in field_stats.items() if s['percentage'] < 50]
        fields_50_to_90 = [(f, s) for f, s in field_stats.items() if 50 <= s['percentage'] < 90]
        fields_90_plus = [(f, s) for f, s in field_stats.items() if s['percentage'] >= 90]

        print(f"\n📋 STRATEGIC PATH TO 95% COMPLETENESS")
        print("="*80)

        print(f"\n✅ ALREADY EXCELLENT (90%+): {len(fields_90_plus)} fields")
        for field, stats in sorted(fields_90_plus, key=lambda x: x[1]['percentage'], reverse=True)[:10]:
            print(f"   • {field}: {stats['percentage']:.1f}%")

        print(f"\n🟡 GOOD PROGRESS (50-90%): {len(fields_50_to_90)} fields")
        for field, stats in sorted(fields_50_to_90, key=lambda x: x[1]['missing'], reverse=True)[:10]:
            print(f"   • {field}: {stats['percentage']:.1f}% ({stats['missing']} missing)")

        print(f"\n🔴 CRITICAL GAPS (<50%): {len(fields_under_50)} fields")
        for field, stats in sorted(fields_under_50, key=lambda x: x[1]['missing'], reverse=True)[:10]:
            print(f"   • {field}: {stats['percentage']:.1f}% ({stats['missing']} missing)")

        # Calculate effort for 95%
        fields_needed_for_95 = int(total_possible * 0.95) - total_filled
        print(f"\n🎯 EFFORT TO REACH 95%")
        print(f"   Fields needed: {fields_needed_for_95:,}")
        print(f"   Average per breed: {fields_needed_for_95/total_breeds:.1f}")

        # Top recommendations
        print(f"\n🚀 TOP RECOMMENDATIONS")
        print("-" * 60)
        print("1. Focus on fields with 50-90% completion first (easier wins)")
        print("2. Target most popular breeds for manual curation")
        print("3. Use breed standards/kennel clubs for physical data")
        print("4. Generate personality descriptions from existing traits")
        print("5. Complete the 'good_with_pets' field (only 11.7%!)")

        # Save report
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'overall_completeness': overall_completeness,
            'total_breeds': total_breeds,
            'content_fields_count': len(content_only_fields),
            'field_statistics': field_stats,
            'assault_impact': {field: field_stats.get(field, {}) for field in assault_fields},
            'gap_to_95': 95 - overall_completeness,
            'fields_needed': fields_needed_for_95
        }

        with open('gap_analysis_final.json', 'w') as f:
            json.dump(report_data, f, indent=2)

        print(f"\n✅ Complete report saved to gap_analysis_final.json")
        return overall_completeness, field_stats

if __name__ == "__main__":
    analyzer = FinalGapAnalysisReport()
    completeness, stats = analyzer.analyze_current_state()