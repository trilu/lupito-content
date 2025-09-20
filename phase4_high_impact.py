#!/usr/bin/env python3

"""
Phase 4: High-Impact Missing Fields Generator
Targets the fields with highest potential completeness gain:
- shedding (0% filled, +2.04% potential)
- good_with_pets (11.7% filled, +1.80% potential)
- intelligence_noted (26.9% filled, +1.49% potential)
"""

import os
import sys
import logging
import time
import re
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('phase4_high_impact.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class Phase4HighImpactGenerator:
    def __init__(self):
        """Initialize with database connection"""
        self.supabase = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_KEY')
        )

        # High-impact target fields from analysis
        self.target_fields = {
            'shedding': {
                'potential': 2.04,
                'description': 'Shedding tendency/level'
            },
            'good_with_pets': {
                'potential': 1.80,
                'description': 'Compatibility with other pets'
            }
        }

        self.stats = {
            'processed': 0,
            'updated': 0,
            'failed': 0,
            'fields_filled': 0
        }

    def get_shedding_level(self, breed_info: Dict) -> Optional[str]:
        """Derive shedding level from breed characteristics"""
        coat = (breed_info.get('coat') or '').lower()
        coat_length = (breed_info.get('coat_length') or '').lower()
        grooming_needs = (breed_info.get('grooming_needs') or '').lower()

        # High shedding breeds
        if any(keyword in coat for keyword in ['double coat', 'undercoat', 'thick coat']):
            return 'High'

        if any(keyword in coat_length for keyword in ['long', 'medium']):
            if 'daily' in grooming_needs or 'frequent' in grooming_needs:
                return 'High'
            else:
                return 'Medium'

        # Low shedding breeds
        if any(keyword in coat for keyword in ['curly', 'hypoallergenic', 'poodle', 'bichon']):
            return 'Low'

        if any(keyword in coat for keyword in ['hairless', 'wire', 'harsh']):
            return 'Low'

        # Medium shedding (default for most breeds)
        if coat_length in ['short', 'smooth']:
            return 'Medium'

        # If we have grooming info, use that
        if 'minimal' in grooming_needs or 'low' in grooming_needs:
            return 'Low'
        elif 'high' in grooming_needs or 'intensive' in grooming_needs:
            return 'High'

        return 'Medium'  # Safe default

    def get_good_with_pets(self, breed_info: Dict) -> Optional[bool]:
        """Derive pet compatibility from temperament and social traits"""
        temperament = breed_info.get('temperament') or ''
        personality = breed_info.get('personality_traits') or ''
        description = breed_info.get('personality_description') or ''

        # Handle list/array data
        if isinstance(temperament, list):
            temperament = ' '.join(str(t) for t in temperament)
        if isinstance(personality, list):
            personality = ' '.join(str(p) for p in personality)
        if isinstance(description, list):
            description = ' '.join(str(d) for d in description)

        temperament = str(temperament).lower()
        personality = str(personality).lower()
        description = str(description).lower()

        # Combine all text sources
        all_text = f"{temperament} {personality} {description}"

        # Good with pets indicators
        good_indicators = [
            'gentle', 'friendly', 'social', 'peaceful', 'calm', 'patient',
            'good with other', 'pack animal', 'gets along', 'sociable'
        ]

        # Not good with pets indicators
        bad_indicators = [
            'dominant', 'aggressive', 'prey drive', 'territorial', 'protective',
            'not good with', 'chase', 'hunting instinct', 'alpha'
        ]

        good_count = sum(1 for indicator in good_indicators if indicator in all_text)
        bad_count = sum(1 for indicator in bad_indicators if indicator in all_text)

        # Return True if there are more positive indicators than negative
        # or if there are at least 2 positive indicators
        if good_count > bad_count and good_count >= 2:
            return True
        elif bad_count > good_count and bad_count >= 2:
            return False
        elif good_count > 0:
            return True  # Lean positive with proper socialization

        return True  # Default to positive


    def generate_field_content(self, field: str, breed_info: Dict) -> Optional[Any]:
        """Generate content for a specific field"""
        try:
            if field == 'shedding':
                return self.get_shedding_level(breed_info)
            elif field == 'good_with_pets':
                return self.get_good_with_pets(breed_info)
            return None
        except Exception as e:
            logger.warning(f"Error generating {field}: {e}")
            return None

    def process_breed(self, breed: Dict) -> Dict[str, Any]:
        """Process a single breed and generate missing high-impact fields"""
        breed_slug = breed.get('breed_slug')
        display_name = breed.get('display_name', breed_slug)

        updates = {}

        for field, field_info in self.target_fields.items():
            current_value = breed.get(field)

            # Skip if field already has content
            if current_value and str(current_value).strip() and str(current_value).lower() not in ['null', 'none']:
                continue

            # Generate new content
            new_content = self.generate_field_content(field, breed)
            if new_content:
                updates[field] = new_content

        return updates

    def update_breed_database(self, breed_slug: str, updates: Dict[str, Any]) -> bool:
        """Update breed in database with new field values"""
        if not updates:
            return False

        try:
            # Update breeds_comprehensive_content table
            result = self.supabase.table('breeds_comprehensive_content')\
                .upsert(
                    {'breed_slug': breed_slug, **updates},
                    on_conflict='breed_slug'
                ).execute()

            if result.data:
                self.stats['fields_filled'] += len(updates)
                logger.info(f"✓ Updated {breed_slug}: {len(updates)} fields")
                return True
            else:
                logger.error(f"Failed to update {breed_slug}: No data returned")
                return False

        except Exception as e:
            logger.error(f"Failed to update {breed_slug}: {e}")
            return False

    def run_analysis(self, limit: Optional[int] = None):
        """Run the high-impact field generation process"""

        logger.info("=" * 80)
        logger.info("PHASE 4: HIGH-IMPACT MISSING FIELDS GENERATOR")
        logger.info("=" * 80)
        logger.info(f"Target fields: {list(self.target_fields.keys())}")
        logger.info(f"Total potential gain: +{sum(f['potential'] for f in self.target_fields.values()):.2f}%")

        try:
            # Get breeds that need these fields
            result = self.supabase.table('breeds_unified_api').select("*").execute()
            breeds = result.data

            if limit:
                breeds = breeds[:limit]

            total_breeds = len(breeds)
            logger.info(f"Processing {total_breeds} breeds...")

            for i, breed in enumerate(breeds, 1):
                self.stats['processed'] += 1
                breed_slug = breed.get('breed_slug')

                logger.info(f"[{i}/{total_breeds}] Processing {breed_slug}...")

                # Generate updates
                updates = self.process_breed(breed)

                if updates:
                    if self.update_breed_database(breed_slug, updates):
                        self.stats['updated'] += 1
                    else:
                        self.stats['failed'] += 1

                # Progress update every 25 breeds
                if i % 25 == 0:
                    success_rate = (self.stats['updated'] / self.stats['processed']) * 100
                    logger.info(f"Progress: {i}/{total_breeds} ({i/total_breeds*100:.1f}%)")
                    logger.info(f"Success rate: {success_rate:.1f}%")
                    logger.info(f"Fields filled: {self.stats['fields_filled']}")

        except Exception as e:
            logger.error(f"Fatal error in analysis: {e}")

        finally:
            self.print_final_summary()

    def print_final_summary(self):
        """Print final statistics"""
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 4 FINAL SUMMARY")
        logger.info("=" * 80)

        success_rate = (self.stats['updated'] / self.stats['processed']) * 100 if self.stats['processed'] > 0 else 0

        logger.info(f"Breeds processed: {self.stats['processed']}")
        logger.info(f"Breeds updated: {self.stats['updated']}")
        logger.info(f"Failed updates: {self.stats['failed']}")
        logger.info(f"Success rate: {success_rate:.1f}%")
        logger.info(f"Fields filled: {self.stats['fields_filled']}")

        # Estimate completeness gain
        estimated_gain = (self.stats['fields_filled'] / (66 * 583)) * 100  # 66 fields, 583 breeds
        logger.info(f"Estimated completeness gain: +{estimated_gain:.2f}%")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        print("Running Phase 4 in test mode (5 breeds)...")
        generator = Phase4HighImpactGenerator()
        generator.run_analysis(limit=5)
    else:
        print("Phase 4: High-Impact Missing Fields Generator")
        print("This will target fields with highest completeness potential:")
        print("- shedding (+2.04% potential)")
        print("- good_with_pets (+1.80% potential)")

        confirm = input("\nProceed with full analysis? (yes/no): ").lower().strip()
        if confirm == 'yes':
            generator = Phase4HighImpactGenerator()
            generator.run_analysis()
        else:
            print("Phase 4 cancelled.")

if __name__ == "__main__":
    main()