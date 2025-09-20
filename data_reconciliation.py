#!/usr/bin/env python3
"""
Data Reconciliation Script - Handle conflicts and quality scoring
Implements authority hierarchy and conflict resolution for breed data
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DataReconciliation:
    def __init__(self):
        """Initialize data reconciliation system"""
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('data_reconciliation.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

        # Supabase setup
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Missing Supabase credentials in environment")

        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

        # Authority hierarchy (higher value = more trusted)
        self.source_authority = {
            'akc': 95,                    # American Kennel Club - Official registry
            'aspca': 90,                  # ASPCA - Veterinary backing
            'petmd': 85,                  # PetMD - Veterinary platform
            'hillspet': 80,               # Hills Pet - Veterinary nutrition
            'rover': 75,                  # Rover - Real owner experiences
            'dogtime': 70,                # DogTime - Popular breed site
            'orvis': 65,                  # Orvis - Breed encyclopedia
            'purina': 60,                 # Purina - Pet food manufacturer
            'wikipedia': 50,              # Wikipedia - General encyclopedia
            'api_ninja': 45,              # API Ninja - Third-party API
            'dog_api': 40,                # Dog API - Third-party API
            'unknown': 30                 # Unknown/unspecified source
        }

        # Field importance weights
        self.field_importance = {
            'grooming_frequency': 95,     # CRITICAL gap
            'good_with_children': 95,     # CRITICAL gap
            'good_with_pets': 95,         # CRITICAL gap
            'exercise_level': 85,         # HIGH priority
            'health_issues': 80,          # MEDIUM priority
            'personality_traits': 75,     # MEDIUM priority
            'training_tips': 70,          # MEDIUM priority
            'exercise_needs_detail': 65,  # MEDIUM priority
            'grooming_needs': 60,         # MEDIUM priority
            'temperament': 55             # LOWER priority
        }

        # Stats tracking
        self.stats = {
            'breeds_processed': 0,
            'conflicts_resolved': 0,
            'quality_scores_updated': 0,
            'source_conflicts': {},
            'field_conflicts': {}
        }

    def get_source_from_field_name(self, field_name: str) -> str:
        """Infer source from field naming patterns"""
        # Look for source indicators in field names or metadata
        if 'akc' in field_name.lower():
            return 'akc'
        elif 'aspca' in field_name.lower():
            return 'aspca'
        elif 'petmd' in field_name.lower():
            return 'petmd'
        elif 'hills' in field_name.lower():
            return 'hillspet'
        elif 'rover' in field_name.lower():
            return 'rover'
        elif 'dogtime' in field_name.lower():
            return 'dogtime'
        elif 'orvis' in field_name.lower():
            return 'orvis'
        elif 'purina' in field_name.lower():
            return 'purina'
        elif 'wikipedia' in field_name.lower():
            return 'wikipedia'
        else:
            return 'unknown'

    def calculate_quality_score(self, breed_data: Dict[str, Any]) -> float:
        """Calculate overall quality score for breed data"""
        total_weight = 0
        weighted_score = 0

        for field, value in breed_data.items():
            if field in self.field_importance:
                field_weight = self.field_importance[field]
                total_weight += field_weight

                # Score based on data completeness and source authority
                if value and value != '' and value != []:
                    # Base score for having data
                    field_score = 70

                    # Bonus for high-importance fields
                    if field_weight >= 95:
                        field_score += 20
                    elif field_weight >= 85:
                        field_score += 15
                    elif field_weight >= 75:
                        field_score += 10

                    # Source authority bonus (if we can determine source)
                    source = self.get_source_from_field_name(field)
                    source_bonus = (self.source_authority.get(source, 30) - 30) / 10
                    field_score += source_bonus

                    weighted_score += field_score * field_weight
                else:
                    # Penalty for missing critical fields
                    if field_weight >= 95:
                        weighted_score += 0 * field_weight  # No points for missing critical
                    else:
                        weighted_score += 20 * field_weight  # Small points for missing non-critical

        if total_weight == 0:
            return 0.0

        final_score = (weighted_score / total_weight) / 100
        return min(max(final_score, 0.0), 1.0)  # Clamp to 0-1 range

    def resolve_field_conflicts(self, breed_slug: str, field_name: str,
                               current_value: Any, new_value: Any,
                               current_source: str = 'unknown',
                               new_source: str = 'unknown') -> Any:
        """Resolve conflicts between current and new field values"""
        current_authority = self.source_authority.get(current_source.lower(), 30)
        new_authority = self.source_authority.get(new_source.lower(), 30)

        # Track conflict statistics
        conflict_key = f"{current_source}_vs_{new_source}"
        self.stats['field_conflicts'][field_name] = self.stats['field_conflicts'].get(field_name, 0) + 1
        self.stats['source_conflicts'][conflict_key] = self.stats['source_conflicts'].get(conflict_key, 0) + 1

        # Resolution logic
        if new_authority > current_authority:
            self.logger.info(f"✓ Conflict resolved for {breed_slug}.{field_name}: {new_source} ({new_authority}) > {current_source} ({current_authority})")
            self.stats['conflicts_resolved'] += 1
            return new_value
        elif new_authority == current_authority:
            # Equal authority - prefer non-empty values
            if current_value and not new_value:
                self.logger.info(f"= Conflict tied for {breed_slug}.{field_name}: keeping existing (non-empty)")
                return current_value
            elif new_value and not current_value:
                self.logger.info(f"= Conflict tied for {breed_slug}.{field_name}: using new (non-empty)")
                self.stats['conflicts_resolved'] += 1
                return new_value
            else:
                # Both have values or both empty - keep current
                self.logger.info(f"= Conflict tied for {breed_slug}.{field_name}: keeping existing (default)")
                return current_value
        else:
            self.logger.info(f"✗ Conflict resolved for {breed_slug}.{field_name}: keeping {current_source} ({current_authority}) > {new_source} ({new_authority})")
            return current_value

    def process_breed_reconciliation(self, breed_slug: str) -> bool:
        """Process data reconciliation for a single breed"""
        try:
            # Get current breed data
            response = self.supabase.table('breeds_comprehensive_content').select('*').eq('breed_slug', breed_slug).execute()

            if not response.data:
                self.logger.warning(f"Breed {breed_slug} not found")
                return False

            breed_data = response.data[0]
            original_data = breed_data.copy()

            # Calculate quality score
            quality_score = self.calculate_quality_score(breed_data)

            # Update quality score if changed
            if 'data_quality_score' not in breed_data or abs(breed_data.get('data_quality_score', 0) - quality_score) > 0.01:
                self.supabase.table('breeds_comprehensive_content').update({
                    'data_quality_score': quality_score,
                    'last_quality_check': datetime.now().isoformat()
                }).eq('breed_slug', breed_slug).execute()

                self.stats['quality_scores_updated'] += 1
                self.logger.info(f"✓ Updated quality score for {breed_slug}: {quality_score:.3f}")

            self.stats['breeds_processed'] += 1
            return True

        except Exception as e:
            self.logger.error(f"Error processing {breed_slug}: {e}")
            return False

    def run_reconciliation(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """Run data reconciliation across all breeds"""
        self.logger.info("Starting Data Reconciliation Process")
        if limit:
            self.logger.info(f"Processing limited to {limit} breeds")

        try:
            # Get all breeds with comprehensive content
            query = self.supabase.table('breeds_comprehensive_content').select('breed_slug')
            if limit:
                query = query.limit(limit)

            response = query.execute()
            breeds = [breed['breed_slug'] for breed in response.data]

            self.logger.info(f"Processing {len(breeds)} breeds for data reconciliation")

            # Process each breed
            for i, breed_slug in enumerate(breeds, 1):
                try:
                    success = self.process_breed_reconciliation(breed_slug)

                    # Progress reporting
                    if i % 50 == 0:
                        self.logger.info(f"Progress: {i}/{len(breeds)} breeds processed")
                        self.logger.info(f"Quality scores updated: {self.stats['quality_scores_updated']}")
                        self.logger.info(f"Conflicts resolved: {self.stats['conflicts_resolved']}")

                except Exception as e:
                    self.logger.error(f"Error processing breed {breed_slug}: {e}")
                    continue

            # Final summary
            self.logger.info(f"""
        ========================================
        DATA RECONCILIATION COMPLETE
        ========================================
        Breeds processed: {self.stats['breeds_processed']}
        Quality scores updated: {self.stats['quality_scores_updated']}
        Conflicts resolved: {self.stats['conflicts_resolved']}

        Top field conflicts:
        {json.dumps(dict(sorted(self.stats['field_conflicts'].items(), key=lambda x: x[1], reverse=True)[:5]), indent=2)}

        Source conflicts:
        {json.dumps(dict(sorted(self.stats['source_conflicts'].items(), key=lambda x: x[1], reverse=True)[:5]), indent=2)}
        """)

            return self.stats

        except Exception as e:
            self.logger.error(f"Reconciliation process failed: {e}")
            return {}

    def get_reconciliation_report(self) -> Dict[str, Any]:
        """Generate reconciliation status report"""
        try:
            # Get overall statistics
            total_breeds = self.supabase.table('breeds_comprehensive_content').select('breed_slug', count='exact').execute()

            # Get quality score distribution
            quality_scores = self.supabase.table('breeds_comprehensive_content').select('data_quality_score').execute()

            scores = [float(breed.get('data_quality_score', 0)) for breed in quality_scores.data if breed.get('data_quality_score')]

            report = {
                'total_breeds': len(total_breeds.data) if total_breeds.data else 0,
                'breeds_with_quality_scores': len(scores),
                'average_quality_score': sum(scores) / len(scores) if scores else 0,
                'high_quality_breeds': len([s for s in scores if s >= 0.8]),
                'medium_quality_breeds': len([s for s in scores if 0.6 <= s < 0.8]),
                'low_quality_breeds': len([s for s in scores if s < 0.6]),
                'processing_stats': self.stats
            }

            return report

        except Exception as e:
            self.logger.error(f"Error generating report: {e}")
            return {}

if __name__ == "__main__":
    import sys

    # Get limit from command line argument
    limit = None
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            print("Invalid limit argument. Using default (no limit)")

    reconciler = DataReconciliation()
    results = reconciler.run_reconciliation(limit=limit)

    # Generate final report
    report = reconciler.get_reconciliation_report()
    if report:
        print(f"\n📊 RECONCILIATION REPORT:")
        print(f"Total breeds: {report['total_breeds']}")
        print(f"Average quality score: {report['average_quality_score']:.3f}")
        print(f"High quality (≥80%): {report['high_quality_breeds']}")
        print(f"Medium quality (60-80%): {report['medium_quality_breeds']}")
        print(f"Low quality (<60%): {report['low_quality_breeds']}")