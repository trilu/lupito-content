#!/usr/bin/env python3
"""
Web Search Strategy for Breed Completeness
Uses targeted web search to fill remaining gaps in breed data.
"""

import os
import json
import time
import logging
from typing import Dict, Any, List, Optional
from supabase import create_client, Client
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class WebSearchCompletenessStrategy:
    def __init__(self):
        """Initialize the web search strategy"""
        # Supabase setup
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

    def analyze_current_completeness(self) -> Dict[str, Any]:
        """Analyze current completeness after all scraping efforts"""
        try:
            # Get current state from breeds_unified_api
            response = self.supabase.table('breeds_unified_api').select(
                'breed_slug, display_name, exercise_needs_detail, training_tips, '
                'grooming_needs, temperament, personality_traits, health_issues, '
                'good_with_children, good_with_pets, grooming_frequency, exercise_level'
            ).execute()

            target_fields = [
                'exercise_needs_detail', 'training_tips', 'grooming_needs',
                'temperament', 'personality_traits', 'health_issues',
                'good_with_children', 'good_with_pets', 'grooming_frequency', 'exercise_level'
            ]

            analysis = {
                'total_breeds': len(response.data),
                'field_gaps': {},
                'critical_gaps': [],
                'completion_by_category': {},
                'search_priorities': []
            }

            # Analyze gaps by field
            for field in target_fields:
                missing_count = 0
                missing_breeds = []

                for breed in response.data:
                    value = breed.get(field)
                    is_missing = (
                        value is None or
                        (isinstance(value, str) and value.strip() == '') or
                        (isinstance(value, list) and len(value) == 0)
                    )

                    if is_missing:
                        missing_count += 1
                        missing_breeds.append({
                            'breed_slug': breed['breed_slug'],
                            'display_name': breed['display_name']
                        })

                gap_percentage = (missing_count / analysis['total_breeds']) * 100
                analysis['field_gaps'][field] = {
                    'missing_count': missing_count,
                    'gap_percentage': gap_percentage,
                    'missing_breeds': missing_breeds[:10]  # Sample
                }

                # Fields with >80% gaps are critical
                if gap_percentage > 80:
                    analysis['critical_gaps'].append(field)

            # Identify web search priorities
            analysis['search_priorities'] = self._identify_search_priorities(analysis['field_gaps'])

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing completeness: {e}")
            return {}

    def _identify_search_priorities(self, field_gaps: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify which fields and breeds to prioritize for web search"""
        priorities = []

        # High-impact fields (compatibility and structured data)
        high_impact_fields = ['good_with_children', 'good_with_pets', 'grooming_frequency', 'exercise_level']

        for field in high_impact_fields:
            if field in field_gaps and field_gaps[field]['gap_percentage'] > 70:
                priorities.append({
                    'field': field,
                    'strategy': 'targeted_search',
                    'gap_percentage': field_gaps[field]['gap_percentage'],
                    'search_queries': self._generate_search_queries(field),
                    'expected_sources': self._get_expected_sources(field)
                })

        return priorities

    def _generate_search_queries(self, field: str) -> List[str]:
        """Generate effective search queries for specific fields"""
        query_templates = {
            'good_with_children': [
                '{breed_name} good with children kids family friendly',
                '{breed_name} child safety temperament around kids',
                '{breed_name} family dog children compatibility'
            ],
            'good_with_pets': [
                '{breed_name} good with other dogs pets animals',
                '{breed_name} dog aggression social other pets',
                '{breed_name} multi-pet household compatibility'
            ],
            'grooming_frequency': [
                '{breed_name} grooming requirements frequency daily weekly',
                '{breed_name} coat care brushing schedule maintenance',
                '{breed_name} grooming needs how often brush'
            ],
            'exercise_level': [
                '{breed_name} exercise requirements daily needs high moderate low',
                '{breed_name} activity level energy exercise amount',
                '{breed_name} exercise time minutes hours daily'
            ],
            'health_issues': [
                '{breed_name} common health problems issues conditions',
                '{breed_name} genetic health concerns hereditary diseases',
                '{breed_name} health screening tests problems'
            ],
            'training_tips': [
                '{breed_name} training difficulty intelligence trainability',
                '{breed_name} how to train tips methods techniques',
                '{breed_name} obedience training challenges tips'
            ]
        }

        return query_templates.get(field, [f'{field.replace("_", " ")}'])

    def _get_expected_sources(self, field: str) -> List[str]:
        """Get expected high-quality sources for specific fields"""
        source_mapping = {
            'good_with_children': [
                'akc.org', 'aspca.org', 'rover.com', 'petfinder.com',
                'dogtime.com', 'vetstreet.com', 'petmd.com'
            ],
            'good_with_pets': [
                'akc.org', 'aspca.org', 'dogtime.com', 'petfinder.com',
                'vetstreet.com', 'rover.com'
            ],
            'grooming_frequency': [
                'akc.org', 'petco.com', 'petsmart.com', 'rover.com',
                'dogtime.com', 'groomers.com'
            ],
            'exercise_level': [
                'akc.org', 'rover.com', 'dogtime.com', 'petmd.com',
                'aspca.org', 'vetstreet.com'
            ],
            'health_issues': [
                'akc.org', 'petmd.com', 'aspca.org', 'avma.org',
                'vetstreet.com', 'ofa.org'
            ],
            'training_tips': [
                'akc.org', 'rover.com', 'petmd.com', 'dogtime.com',
                'cesar.com', 'zak.com'
            ]
        }

        return source_mapping.get(field, ['akc.org', 'petmd.com', 'rover.com'])

    def generate_web_search_plan(self) -> Dict[str, Any]:
        """Generate a comprehensive web search plan"""
        logger.info("Analyzing current completeness for web search strategy...")

        analysis = self.analyze_current_completeness()
        if not analysis:
            return {}

        plan = {
            'analysis_date': '2025-09-19',
            'current_completeness': analysis,
            'search_strategies': [],
            'implementation_phases': []
        }

        # Strategy 1: Critical Gap Filling
        if analysis['critical_gaps']:
            plan['search_strategies'].append({
                'name': 'Critical Gap Filling',
                'target_fields': analysis['critical_gaps'],
                'approach': 'Systematic web search for fields with >80% gaps',
                'priority': 'HIGH',
                'expected_impact': 'Fill 50-70% of critical gaps'
            })

        # Strategy 2: High-Value Source Mining
        plan['search_strategies'].append({
            'name': 'High-Value Source Mining',
            'target_sources': ['akc.org', 'aspca.org', 'petmd.com', 'rover.com'],
            'approach': 'Dedicated scrapers for authoritative sources',
            'priority': 'HIGH',
            'expected_impact': 'Fill 30-50% of remaining gaps'
        })

        # Strategy 3: Intelligent Query Generation
        plan['search_strategies'].append({
            'name': 'Intelligent Query Generation',
            'approach': 'AI-powered query generation for specific breed-field combinations',
            'target': 'Rare breeds with multiple missing fields',
            'priority': 'MEDIUM',
            'expected_impact': 'Fill 20-30% of remaining gaps'
        })

        # Strategy 4: Breed Community Forums
        plan['search_strategies'].append({
            'name': 'Breed Community Forums',
            'target_sources': ['breed-specific forums', 'reddit.com/r/dogs', 'specialty breed sites'],
            'approach': 'Community knowledge extraction',
            'priority': 'MEDIUM',
            'expected_impact': 'Fill gaps for rare/exotic breeds'
        })

        # Implementation phases
        plan['implementation_phases'] = [
            {
                'phase': 1,
                'focus': 'AKC and ASPCA systematic scraping',
                'duration': '2-3 hours',
                'target_fields': ['good_with_children', 'good_with_pets', 'exercise_level'],
                'expected_completion_gain': '15-20%'
            },
            {
                'phase': 2,
                'focus': 'Rover and PetMD data extraction',
                'duration': '2-3 hours',
                'target_fields': ['grooming_frequency', 'health_issues', 'training_tips'],
                'expected_completion_gain': '10-15%'
            },
            {
                'phase': 3,
                'focus': 'Intelligent web search for remaining gaps',
                'duration': '3-4 hours',
                'target_fields': 'All remaining gaps',
                'expected_completion_gain': '10-15%'
            }
        ]

        return plan

    def save_search_plan(self, plan: Dict[str, Any], filename: str = 'web_search_completeness_plan.json'):
        """Save the web search plan"""
        try:
            with open(filename, 'w') as f:
                json.dump(plan, f, indent=2)
            logger.info(f"Web search plan saved to {filename}")

            # Generate summary
            if 'current_completeness' in plan:
                total_breeds = plan['current_completeness']['total_breeds']
                critical_gaps = len(plan['current_completeness']['critical_gaps'])

                logger.info(f"""
                ========================================
                WEB SEARCH COMPLETENESS STRATEGY
                ========================================
                Total breeds: {total_breeds}
                Critical gaps (>80% missing): {critical_gaps} fields

                Expected completion gains:
                - Phase 1: +15-20% (AKC/ASPCA)
                - Phase 2: +10-15% (Rover/PetMD)
                - Phase 3: +10-15% (Intelligent search)

                Total expected gain: +35-50% completeness
                ========================================
                """)

        except Exception as e:
            logger.error(f"Error saving plan: {e}")

if __name__ == "__main__":
    strategy = WebSearchCompletenessStrategy()
    plan = strategy.generate_web_search_plan()

    if plan:
        strategy.save_search_plan(plan)
    else:
        logger.error("Failed to generate web search plan")