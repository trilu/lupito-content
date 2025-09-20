#!/usr/bin/env python3
"""
PHASE 2: CRITICAL UX FIELDS
Auto-generate fields from existing data and enhance Wikipedia extraction
Target: +7% completeness gain (80% → 87%)
"""

import os
import re
import json
import logging
from typing import Dict, Optional, List, Any
from dotenv import load_dotenv
from supabase import create_client
from google.cloud import storage
from bs4 import BeautifulSoup
import sys

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('phase2_critical_ux.log'),
        logging.StreamHandler()
    ]
)

class Phase2CriticalUX:
    def __init__(self, test_mode=False, test_limit=5):
        """Initialize Phase 2 processor"""
        self.supabase = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_KEY')
        )
        self.gcs_client = storage.Client()
        self.bucket = self.gcs_client.bucket('lupito_breed_images')
        self.test_mode = test_mode
        self.test_limit = test_limit

        # Statistics tracking
        self.stats = {
            'breeds_processed': 0,
            'breeds_updated': 0,
            'fields_generated': {},
            'fields_extracted': {},
            'total_fields_filled': 0,
            'errors': []
        }

        # Energy level mapping for auto-generation
        self.energy_mapping = {
            'Very Low': 1,
            'Low': 2,
            'Moderate': 3,
            'High': 4,
            'Very High': 5
        }

        # Alternative energy mappings (for variations)
        self.energy_text_mapping = {
            'very low': 1, 'extremely low': 1, 'minimal': 1,
            'low': 2, 'below average': 2, 'calm': 2,
            'moderate': 3, 'medium': 3, 'average': 3, 'balanced': 3,
            'high': 4, 'above average': 4, 'active': 4, 'energetic': 4,
            'very high': 5, 'extremely high': 5, 'hyperactive': 5, 'intense': 5
        }

    def get_breeds_needing_phase2(self) -> List[Dict]:
        """Get breeds that need Phase 2 field completion"""
        logging.info("Fetching breeds needing Phase 2 fields...")

        # Get all breeds with their current field values
        response = self.supabase.table('breeds_unified_api').select(
            'breed_slug, display_name, energy, coat, coat_texture, coat_length_text, '
            'energy_level_numeric, good_with_pets, intelligence_noted, exercise_level, '
            'grooming_frequency, barking_tendency, drooling_tendency, temperament, '
            'grooming_needs, trainability'
        ).execute()

        breeds = response.data

        # Filter breeds that need Phase 2 fields
        breeds_needing_update = []
        for breed in breeds:
            needs_update = False

            # Check if critical fields are missing
            if not breed.get('energy_level_numeric') and breed.get('energy'):
                needs_update = True
            if not breed.get('coat_texture') and breed.get('coat'):
                needs_update = True
            if not breed.get('coat_length_text') and breed.get('coat'):
                needs_update = True
            if not breed.get('good_with_pets'):
                needs_update = True
            if not breed.get('intelligence_noted'):
                needs_update = True
            if not breed.get('exercise_level'):
                needs_update = True
            if not breed.get('grooming_frequency') and breed.get('grooming_needs'):
                needs_update = True
            if not breed.get('barking_tendency'):
                needs_update = True
            if not breed.get('drooling_tendency'):
                needs_update = True

            if needs_update:
                breeds_needing_update.append(breed)

        logging.info(f"Found {len(breeds_needing_update)} breeds needing Phase 2 fields")

        if self.test_mode:
            return breeds_needing_update[:self.test_limit]
        return breeds_needing_update

    def generate_energy_level_numeric(self, energy_text: str) -> Optional[int]:
        """Generate numeric energy level from text"""
        if not energy_text:
            return None

        # Clean the text
        energy_lower = energy_text.lower().strip()

        # Try direct mapping first
        if energy_text in self.energy_mapping:
            return self.energy_mapping[energy_text]

        # Try alternative mappings
        for key, value in self.energy_text_mapping.items():
            if key in energy_lower:
                return value

        # Default based on keywords
        if any(word in energy_lower for word in ['very high', 'extremely high', 'hyperactive']):
            return 5
        elif any(word in energy_lower for word in ['high', 'active', 'energetic']):
            return 4
        elif any(word in energy_lower for word in ['moderate', 'medium', 'average']):
            return 3
        elif any(word in energy_lower for word in ['low', 'calm', 'relaxed']):
            return 2
        elif any(word in energy_lower for word in ['very low', 'minimal', 'sedentary']):
            return 1

        return 3  # Default to moderate if unclear

    def extract_coat_attributes(self, coat_text: str) -> Dict[str, str]:
        """Extract coat texture and length from coat description"""
        attributes = {}

        if not coat_text:
            return attributes

        coat_lower = coat_text.lower()

        # Extract texture
        texture_patterns = {
            'smooth': ['smooth', 'sleek', 'fine'],
            'wiry': ['wiry', 'wire', 'harsh', 'coarse'],
            'silky': ['silky', 'silk', 'soft'],
            'rough': ['rough', 'shaggy'],
            'curly': ['curly', 'curled', 'wavy'],
            'fluffy': ['fluffy', 'plush', 'dense'],
            'double': ['double coat', 'double-coat', 'undercoat']
        }

        for texture, keywords in texture_patterns.items():
            if any(kw in coat_lower for kw in keywords):
                attributes['coat_texture'] = texture
                break

        # Extract length
        length_patterns = {
            'hairless': ['hairless', 'no hair', 'bald'],
            'short': ['short', 'close'],
            'medium': ['medium', 'moderate'],
            'long': ['long', 'flowing']
        }

        for length, keywords in length_patterns.items():
            if any(kw in coat_lower for kw in keywords):
                attributes['coat_length_text'] = length
                break

        return attributes

    def derive_exercise_level(self, energy: str, breed_info: Dict) -> Optional[str]:
        """Derive exercise level from energy and other breed characteristics"""
        if not energy:
            return None

        energy_lower = energy.lower()

        # Check for working breed indicators
        temperament = breed_info.get('temperament', '')
        if temperament is None:
            temperament = ''

        is_working = any([
            breed_info.get('display_name', '').lower() in ['shepherd', 'retriever', 'pointer', 'setter'],
            'working' in temperament.lower(),
            'hunting' in temperament.lower()
        ])

        if 'very high' in energy_lower or 'extremely high' in energy_lower:
            return 'Very High - 2+ hours daily'
        elif 'high' in energy_lower or is_working:
            return 'High - 1-2 hours daily'
        elif 'moderate' in energy_lower or 'medium' in energy_lower:
            return 'Moderate - 30-60 minutes daily'
        elif 'low' in energy_lower:
            return 'Low - 20-30 minutes daily'
        elif 'very low' in energy_lower:
            return 'Minimal - 15-20 minutes daily'

        return 'Moderate - 30-60 minutes daily'  # Default

    def extract_grooming_frequency(self, grooming_needs: str) -> Optional[str]:
        """Extract grooming frequency from grooming needs description"""
        if not grooming_needs:
            return None

        grooming_lower = grooming_needs.lower()

        # Frequency patterns
        if any(word in grooming_lower for word in ['daily', 'every day', 'everyday']):
            return 'Daily'
        elif any(word in grooming_lower for word in ['weekly', 'once a week', 'every week']):
            return 'Weekly'
        elif any(word in grooming_lower for word in ['bi-weekly', 'biweekly', 'twice a month']):
            return 'Bi-weekly'
        elif any(word in grooming_lower for word in ['monthly', 'once a month']):
            return 'Monthly'
        elif any(word in grooming_lower for word in ['occasional', 'minimal', 'low maintenance']):
            return 'Occasional'
        elif any(word in grooming_lower for word in ['regular', 'frequent']):
            return 'Weekly'
        elif any(word in grooming_lower for word in ['professional', 'groomer']):
            return 'Monthly (Professional)'

        return None

    def get_wikipedia_content(self, breed_slug: str) -> Optional[BeautifulSoup]:
        """Fetch Wikipedia content from GCS"""
        try:
            blob_name = f"wikipedia/{breed_slug}_wikipedia.html"
            blob = self.bucket.blob(blob_name)

            if blob.exists():
                content = blob.download_as_text()
                return BeautifulSoup(content, 'html.parser')
        except Exception as e:
            logging.debug(f"Could not fetch Wikipedia for {breed_slug}: {e}")

        return None

    def extract_intelligence_from_wikipedia(self, soup: BeautifulSoup, temperament: str = '') -> Optional[str]:
        """Extract intelligence information from Wikipedia"""
        if not soup and not temperament:
            return None

        intelligence_keywords = [
            'intelligent', 'smart', 'clever', 'quick learner', 'trainable',
            'bright', 'sharp', 'keen', 'obedient', 'responsive'
        ]

        intelligence_level = None

        # Check temperament first
        if temperament:
            temp_lower = temperament.lower()
            if any(kw in temp_lower for kw in intelligence_keywords):
                if any(word in temp_lower for word in ['very intelligent', 'extremely intelligent', 'highly intelligent']):
                    intelligence_level = 'Very High'
                elif 'intelligent' in temp_lower:
                    intelligence_level = 'High'
                elif any(word in temp_lower for word in ['trainable', 'obedient']):
                    intelligence_level = 'Above Average'

        # Check Wikipedia content
        if soup and not intelligence_level:
            text = soup.get_text().lower()

            # Look for Stanley Coren rankings
            if 'stanley coren' in text or 'intelligence of dogs' in text:
                if any(phrase in text for phrase in ['top 10', 'top ten', 'brightest']):
                    intelligence_level = 'Very High'
                elif any(phrase in text for phrase in ['above average', 'excellent working']):
                    intelligence_level = 'High'
                elif 'average' in text:
                    intelligence_level = 'Average'
                elif any(phrase in text for phrase in ['fair', 'below average']):
                    intelligence_level = 'Below Average'

            # General intelligence mentions
            if not intelligence_level:
                for para in soup.find_all('p'):
                    para_text = para.get_text().lower()
                    if any(kw in para_text for kw in intelligence_keywords):
                        if 'very intelligent' in para_text or 'highly intelligent' in para_text:
                            intelligence_level = 'Very High'
                        elif 'intelligent' in para_text:
                            intelligence_level = 'High'
                        elif 'average intelligence' in para_text:
                            intelligence_level = 'Average'
                        break

        return intelligence_level

    def extract_social_traits_from_wikipedia(self, soup: BeautifulSoup, temperament: str = '') -> Dict[str, str]:
        """Extract good_with_pets and social traits from Wikipedia"""
        traits = {}

        # Combine sources
        text_sources = []
        if temperament:
            text_sources.append(temperament.lower())
        if soup:
            text_sources.append(soup.get_text().lower())

        for text in text_sources:
            # Good with pets patterns
            if not traits.get('good_with_pets'):
                if any(phrase in text for phrase in [
                    'good with other pets', 'friendly with other animals',
                    'gets along with cats', 'cat-friendly', 'good with cats',
                    'sociable with other dogs', 'dog-friendly'
                ]):
                    traits['good_with_pets'] = 'Yes'
                elif any(phrase in text for phrase in [
                    'not good with cats', 'chase cats', 'prey drive',
                    'aggressive toward other dogs', 'dog aggressive',
                    'not suitable for homes with other pets'
                ]):
                    traits['good_with_pets'] = 'No'
                elif any(phrase in text for phrase in [
                    'early socialization', 'requires socialization',
                    'can learn to live with', 'depends on socialization'
                ]):
                    traits['good_with_pets'] = 'With Proper Socialization'

            # Barking tendency
            if not traits.get('barking_tendency'):
                if any(phrase in text for phrase in ['excessive barking', 'barks a lot', 'vocal breed', 'prone to barking']):
                    traits['barking_tendency'] = 'High'
                elif any(phrase in text for phrase in ['moderate barker', 'barks when necessary', 'alert barker']):
                    traits['barking_tendency'] = 'Moderate'
                elif any(phrase in text for phrase in ['quiet', 'rarely barks', 'not a barker', 'silent']):
                    traits['barking_tendency'] = 'Low'

            # Drooling tendency
            if not traits.get('drooling_tendency'):
                if any(phrase in text for phrase in ['heavy drooler', 'drools a lot', 'slobber', 'excessive drooling']):
                    traits['drooling_tendency'] = 'High'
                elif any(phrase in text for phrase in ['some drooling', 'moderate drooler', 'occasional drool']):
                    traits['drooling_tendency'] = 'Moderate'
                elif any(phrase in text for phrase in ['minimal drooling', 'dry mouth', 'no drooling']):
                    traits['drooling_tendency'] = 'Low'

        return traits

    def process_breed(self, breed: Dict) -> Dict[str, Any]:
        """Process a single breed for Phase 2 fields"""
        breed_slug = breed['breed_slug']
        updates = {}

        # A. Auto-generate from existing data

        # 1. Generate energy_level_numeric
        if not breed.get('energy_level_numeric') and breed.get('energy'):
            energy_numeric = self.generate_energy_level_numeric(breed['energy'])
            if energy_numeric:
                updates['energy_level_numeric'] = energy_numeric
                self.stats['fields_generated']['energy_level_numeric'] = \
                    self.stats['fields_generated'].get('energy_level_numeric', 0) + 1

        # 2. Extract coat attributes
        if breed.get('coat'):
            coat_attrs = self.extract_coat_attributes(breed['coat'])
            if 'coat_texture' in coat_attrs and not breed.get('coat_texture'):
                updates['coat_texture'] = coat_attrs['coat_texture']
                self.stats['fields_generated']['coat_texture'] = \
                    self.stats['fields_generated'].get('coat_texture', 0) + 1
            if 'coat_length_text' in coat_attrs and not breed.get('coat_length_text'):
                updates['coat_length_text'] = coat_attrs['coat_length_text']
                self.stats['fields_generated']['coat_length_text'] = \
                    self.stats['fields_generated'].get('coat_length_text', 0) + 1

        # 3. Derive exercise level
        if not breed.get('exercise_level') and breed.get('energy'):
            exercise_level = self.derive_exercise_level(breed['energy'], breed)
            if exercise_level:
                updates['exercise_level'] = exercise_level
                self.stats['fields_generated']['exercise_level'] = \
                    self.stats['fields_generated'].get('exercise_level', 0) + 1

        # 4. Extract grooming frequency
        if not breed.get('grooming_frequency') and breed.get('grooming_needs'):
            grooming_freq = self.extract_grooming_frequency(breed['grooming_needs'])
            if grooming_freq:
                updates['grooming_frequency'] = grooming_freq
                self.stats['fields_generated']['grooming_frequency'] = \
                    self.stats['fields_generated'].get('grooming_frequency', 0) + 1

        # B. Enhanced Wikipedia extraction

        # Get Wikipedia content if we need to extract more fields
        wikipedia_soup = None
        if not breed.get('intelligence_noted') or not breed.get('good_with_pets') or \
           not breed.get('barking_tendency') or not breed.get('drooling_tendency'):
            wikipedia_soup = self.get_wikipedia_content(breed_slug)

        # 5. Extract intelligence
        if not breed.get('intelligence_noted'):
            intelligence = self.extract_intelligence_from_wikipedia(
                wikipedia_soup, breed.get('temperament', '')
            )
            if intelligence:
                updates['intelligence_noted'] = intelligence
                self.stats['fields_extracted']['intelligence_noted'] = \
                    self.stats['fields_extracted'].get('intelligence_noted', 0) + 1

        # 6. Extract social traits
        social_traits = self.extract_social_traits_from_wikipedia(
            wikipedia_soup, breed.get('temperament', '')
        )

        if not breed.get('good_with_pets') and social_traits.get('good_with_pets'):
            updates['good_with_pets'] = social_traits['good_with_pets']
            self.stats['fields_extracted']['good_with_pets'] = \
                self.stats['fields_extracted'].get('good_with_pets', 0) + 1

        if not breed.get('barking_tendency') and social_traits.get('barking_tendency'):
            updates['barking_tendency'] = social_traits['barking_tendency']
            self.stats['fields_extracted']['barking_tendency'] = \
                self.stats['fields_extracted'].get('barking_tendency', 0) + 1

        if not breed.get('drooling_tendency') and social_traits.get('drooling_tendency'):
            updates['drooling_tendency'] = social_traits['drooling_tendency']
            self.stats['fields_extracted']['drooling_tendency'] = \
                self.stats['fields_extracted'].get('drooling_tendency', 0) + 1

        return updates

    def update_database(self, breed_slug: str, updates: Dict) -> bool:
        """Update breed in database"""
        if not updates:
            return False

        # Separate fields for different tables
        # Note: coat_length_text doesn't exist in any table, skip it
        comprehensive_fields = ['energy_level_numeric', 'good_with_pets', 'intelligence_noted',
                               'exercise_level', 'grooming_frequency', 'barking_tendency',
                               'drooling_tendency', 'coat_texture', 'coat_length_text']
        published_fields = []

        comprehensive_updates = {k: v for k, v in updates.items() if k in comprehensive_fields}
        published_updates = {k: v for k, v in updates.items() if k in published_fields}

        success = False
        fields_updated = 0

        try:
            # Update breeds_comprehensive_content if we have relevant fields
            if comprehensive_updates:
                self.supabase.table('breeds_comprehensive_content').upsert({
                    'breed_slug': breed_slug,
                    **comprehensive_updates
                }, on_conflict='breed_slug').execute()
                fields_updated += len(comprehensive_updates)

            # Update breeds_published if we have relevant fields
            if published_updates:
                self.supabase.table('breeds_published').upsert({
                    'breed_slug': breed_slug,
                    **published_updates
                }, on_conflict='breed_slug').execute()
                fields_updated += len(published_updates)

            if fields_updated > 0:
                self.stats['total_fields_filled'] += fields_updated
                logging.info(f"✓ Updated {breed_slug}: {fields_updated} fields")
                success = True

        except Exception as e:
            logging.error(f"Failed to update {breed_slug}: {e}")
            self.stats['errors'].append(f"{breed_slug}: {str(e)}")

        return success

    def run(self):
        """Run Phase 2 processing"""
        logging.info("=" * 80)
        logging.info("PHASE 2: CRITICAL UX FIELDS")
        logging.info("=" * 80)

        if self.test_mode:
            logging.info(f"Running in TEST MODE ({self.test_limit} breeds)...")

        # Get breeds needing updates
        breeds = self.get_breeds_needing_phase2()
        total_breeds = len(breeds)

        logging.info(f"Processing {total_breeds} breeds for Phase 2 fields")
        logging.info("Target fields: energy_level_numeric, coat_texture, coat_length_text, "
                    "exercise_level, grooming_frequency, intelligence_noted, good_with_pets, "
                    "barking_tendency, drooling_tendency")

        # Process each breed
        for idx, breed in enumerate(breeds, 1):
            breed_slug = breed['breed_slug']
            logging.info(f"[{idx}/{total_breeds}] Processing {breed_slug}...")

            self.stats['breeds_processed'] += 1

            # Generate and extract fields
            updates = self.process_breed(breed)

            # Update database if we have new data
            if updates:
                if self.update_database(breed_slug, updates):
                    self.stats['breeds_updated'] += 1
            else:
                logging.info(f"  No new fields generated for {breed_slug}")

        # Print final summary
        self.print_summary()

        # Calculate success metrics
        if self.stats['breeds_processed'] > 0:
            success_rate = (self.stats['breeds_updated'] / self.stats['breeds_processed']) * 100
            estimated_gain = (self.stats['total_fields_filled'] / (583 * 68)) * 100

            logging.info(f"\nSuccess rate: {success_rate:.1f}%")
            logging.info(f"Estimated completeness gain: +{estimated_gain:.2f}%")

    def print_summary(self):
        """Print processing summary"""
        logging.info("\n" + "=" * 80)
        logging.info("PHASE 2 COMPLETE")
        logging.info("=" * 80)

        logging.info(f"Total breeds processed: {self.stats['breeds_processed']}")
        logging.info(f"Breeds updated: {self.stats['breeds_updated']}")
        logging.info(f"Total fields filled: {self.stats['total_fields_filled']}")

        if self.stats['fields_generated']:
            logging.info("\nFields auto-generated:")
            for field, count in sorted(self.stats['fields_generated'].items()):
                logging.info(f"  {field}: {count}")

        if self.stats['fields_extracted']:
            logging.info("\nFields extracted from Wikipedia:")
            for field, count in sorted(self.stats['fields_extracted'].items()):
                logging.info(f"  {field}: {count}")

        if self.stats['errors']:
            logging.info(f"\nErrors encountered: {len(self.stats['errors'])}")
            for error in self.stats['errors'][:5]:
                logging.info(f"  {error}")

def main():
    """Main execution"""
    # Check for test mode
    test_mode = '--test' in sys.argv or '-t' in sys.argv

    if test_mode:
        print("\n" + "=" * 80)
        print("PHASE 2: TEST MODE (5 breeds)")
        print("=" * 80)
        processor = Phase2CriticalUX(test_mode=True, test_limit=5)
    else:
        # Confirm before full run
        print("\n" + "=" * 80)
        print("PHASE 2: CRITICAL UX FIELDS - FULL RUN")
        print("=" * 80)
        print("\nThis will process ALL breeds needing Phase 2 fields.")
        print("Expected outcome: +7% completeness gain")

        confirm = input("\nProceed with full run? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("Operation cancelled.")
            return

        processor = Phase2CriticalUX(test_mode=False)

    # Run processing
    processor.run()

if __name__ == "__main__":
    main()