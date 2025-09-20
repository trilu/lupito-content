#!/usr/bin/env python3
"""
Missing Breeds Report Generator
Creates a comprehensive JSON file tracking which breeds need which specific fields,
enabling targeted scraping that avoids unnecessary work.
"""

import os
import json
import logging
from typing import Dict, Any, List, Set
from supabase import create_client, Client
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class MissingBreedsReportGenerator:
    def __init__(self):
        """Initialize the report generator"""
        # Supabase setup
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

        # Target fields for completeness
        self.target_fields = [
            'exercise_needs_detail',
            'training_tips',
            'grooming_needs',
            'temperament',
            'personality_traits',
            'health_issues',
            'good_with_children',
            'good_with_pets',
            'grooming_frequency',
            'exercise_level'
        ]

    def get_breeds_with_missing_data(self) -> Dict[str, Any]:
        """Get comprehensive report of breeds missing specific fields"""
        try:
            # Query the unified view for all breeds
            response = self.supabase.table('breeds_unified_api').select(
                f'breed_slug, display_name, {", ".join(self.target_fields)}'
            ).execute()

            missing_report = {
                'generation_date': '2025-09-19',
                'total_breeds': len(response.data),
                'target_fields': self.target_fields,
                'summary': {},
                'breeds': {}
            }

            field_stats = {field: {'missing_count': 0, 'missing_breeds': []} for field in self.target_fields}

            for breed in response.data:
                breed_slug = breed['breed_slug']
                display_name = breed['display_name']

                missing_fields = []

                for field in self.target_fields:
                    value = breed.get(field)

                    # Check if field is missing or empty
                    is_missing = (
                        value is None or
                        (isinstance(value, str) and value.strip() == '') or
                        (isinstance(value, list) and len(value) == 0)
                    )

                    if is_missing:
                        missing_fields.append(field)
                        field_stats[field]['missing_count'] += 1
                        field_stats[field]['missing_breeds'].append(breed_slug)

                if missing_fields:
                    missing_report['breeds'][breed_slug] = {
                        'display_name': display_name,
                        'missing_fields': missing_fields,
                        'missing_count': len(missing_fields),
                        'completeness_score': round(((10 - len(missing_fields)) / 10) * 100, 1)
                    }

            # Generate summary statistics
            missing_report['summary'] = {
                'breeds_with_missing_data': len(missing_report['breeds']),
                'breeds_complete': missing_report['total_breeds'] - len(missing_report['breeds']),
                'field_statistics': {}
            }

            for field, stats in field_stats.items():
                missing_report['summary']['field_statistics'][field] = {
                    'missing_count': stats['missing_count'],
                    'missing_percentage': round((stats['missing_count'] / missing_report['total_breeds']) * 100, 1),
                    'priority': self.get_field_priority(field, stats['missing_count'])
                }

            logger.info(f"Generated missing breeds report for {missing_report['total_breeds']} breeds")
            logger.info(f"Breeds needing data: {len(missing_report['breeds'])}")

            return missing_report

        except Exception as e:
            logger.error(f"Error generating missing breeds report: {e}")
            return {}

    def get_field_priority(self, field: str, missing_count: int) -> str:
        """Determine priority based on field importance and missing count"""
        if missing_count > 400:  # >70% missing
            return 'HIGH'
        elif missing_count > 200:  # >35% missing
            return 'MEDIUM'
        else:
            return 'LOW'

    def get_breeds_for_source(self, source: str) -> List[Dict[str, Any]]:
        """Get breeds that need data targetable by specific source"""

        # Define which fields each source can provide
        source_capabilities = {
            'purina': ['exercise_needs_detail', 'training_tips', 'grooming_needs',
                      'good_with_children', 'good_with_pets', 'temperament'],
            'hills': ['exercise_needs_detail', 'grooming_needs', 'temperament', 'health_issues'],
            'kennel_club_uk': ['exercise_level', 'grooming_frequency', 'temperament', 'health_issues'],
            'orvis': ['exercise_needs_detail', 'training_tips', 'grooming_needs', 'exercise_level']
        }

        if source not in source_capabilities:
            logger.error(f"Unknown source: {source}")
            return []

        try:
            # Load the missing breeds report
            if not os.path.exists('missing_breeds_report.json'):
                logger.error("missing_breeds_report.json not found. Run generate report first.")
                return []

            with open('missing_breeds_report.json', 'r') as f:
                report = json.load(f)

            source_fields = source_capabilities[source]
            targeted_breeds = []

            for breed_slug, breed_data in report['breeds'].items():
                missing_fields = breed_data['missing_fields']

                # Check if this source can provide any missing fields
                targetable_fields = list(set(missing_fields) & set(source_fields))

                if targetable_fields:
                    targeted_breeds.append({
                        'breed_slug': breed_slug,
                        'display_name': breed_data['display_name'],
                        'target_fields': targetable_fields,
                        'priority_score': len(targetable_fields)  # More missing fields = higher priority
                    })

            # Sort by priority (most missing fields first)
            targeted_breeds.sort(key=lambda x: x['priority_score'], reverse=True)

            logger.info(f"Found {len(targeted_breeds)} breeds targetable by {source}")
            return targeted_breeds

        except Exception as e:
            logger.error(f"Error getting breeds for source {source}: {e}")
            return []

    def save_report(self, report: Dict[str, Any], filename: str = 'missing_breeds_report.json'):
        """Save the missing breeds report to file"""
        try:
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"Saved missing breeds report to {filename}")

            # Also save summary for quick reference
            summary_filename = filename.replace('.json', '_summary.json')
            summary = {
                'generation_date': report['generation_date'],
                'total_breeds': report['total_breeds'],
                'breeds_needing_data': len(report['breeds']),
                'field_statistics': report['summary']['field_statistics']
            }

            with open(summary_filename, 'w') as f:
                json.dump(summary, f, indent=2)
            logger.info(f"Saved summary to {summary_filename}")

        except Exception as e:
            logger.error(f"Error saving report: {e}")

    def generate_source_targets(self):
        """Generate targeted breed lists for each source"""
        sources = ['purina', 'hills', 'kennel_club_uk', 'orvis']

        for source in sources:
            breeds = self.get_breeds_for_source(source)
            if breeds:
                filename = f'target_breeds_{source}.json'
                with open(filename, 'w') as f:
                    json.dump({
                        'source': source,
                        'generation_date': '2025-09-19',
                        'target_count': len(breeds),
                        'breeds': breeds
                    }, f, indent=2)
                logger.info(f"Saved {len(breeds)} target breeds for {source} to {filename}")

if __name__ == "__main__":
    generator = MissingBreedsReportGenerator()

    # Generate comprehensive missing breeds report
    logger.info("Generating comprehensive missing breeds report...")
    report = generator.get_breeds_with_missing_data()

    if report:
        # Save main report
        generator.save_report(report)

        # Generate source-specific target lists
        logger.info("Generating source-specific target lists...")
        generator.generate_source_targets()

        # Log key statistics
        logger.info(f"""
        ========================================
        MISSING BREEDS REPORT GENERATED
        ========================================
        Total breeds: {report['total_breeds']}
        Breeds needing data: {len(report['breeds'])}
        Completion rate: {round(((report['total_breeds'] - len(report['breeds'])) / report['total_breeds']) * 100, 1)}%

        Top missing fields:
        """)

        for field, stats in report['summary']['field_statistics'].items():
            if stats['missing_count'] > 100:
                logger.info(f"  - {field}: {stats['missing_count']} breeds ({stats['missing_percentage']}%)")

        logger.info("========================================")
    else:
        logger.error("Failed to generate missing breeds report")