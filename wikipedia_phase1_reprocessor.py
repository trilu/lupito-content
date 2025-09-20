#!/usr/bin/env python3
"""
Reprocess existing Wikipedia content for Phase 1 target fields
Specifically designed to extract data for breeds that failed on mainstream pet sites
"""

import os
import re
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Set
from google.cloud import storage
from bs4 import BeautifulSoup
from supabase import create_client, Client
from dotenv import load_dotenv
from collections import defaultdict

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class WikipediaPhase1Reprocessor:
    def __init__(self):
        """Initialize the reprocessor targeting Phase 1 fields"""
        # Initialize Supabase
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

        # Initialize GCS
        self.storage_client = storage.Client(project='careful-drummer-468512-p0')
        self.bucket = self.storage_client.bucket('lupito-content-raw-eu')

        # Use the latest Wikipedia scrape folder
        self.gcs_folder = 'scraped/wikipedia_breeds/20250917_162810'

        # Target fields from Phase 1 analysis (quick wins + critical)
        self.target_fields = {
            'health_issues': 0,      # 45.6% complete - critical
            'grooming_needs': 0,     # 65.5% complete - quick win
            'grooming_frequency': 0, # 48.4% complete - quick win
            'training_tips': 0,      # 65.9% complete - quick win
            'exercise_needs_detail': 0, # 66.7% complete - quick win
            'color_varieties': 0,    # 47.0% complete - quick win
            'fun_facts': 0,          # 66.4% complete - quick win
            'history': 0,            # 47.8% complete - quick win
            'temperament': 0,        # 14.6% complete - critical
            'personality_traits': 0, # 14.8% complete - critical
        }

        # Stats tracking
        self.stats = {
            'total_processed': 0,
            'breeds_updated': 0,
            'fields_filled': defaultdict(int),
            'skipped_breeds': [],
            'error_breeds': []
        }

        # Load breeds that need work (failed in Phase 1 or have missing fields)
        self.breeds_to_process = self.get_breeds_needing_work()

    def get_breeds_needing_work(self) -> List[Dict]:
        """Get breeds that have missing Phase 1 fields"""
        logger.info("Fetching breeds with missing Phase 1 fields...")

        # Query breeds directly from the view
        response = self.supabase.table('breeds_unified_api').select(
            "breed_slug, display_name, health_issues, grooming_needs, grooming_frequency, "
            "training_tips, exercise_needs_detail, color_varieties, fun_facts, "
            "history, temperament, personality_traits"
        ).execute()

        all_breeds = response.data if response.data else []

        # Filter breeds that have at least one missing target field
        breeds = []
        for breed in all_breeds:
            missing_fields = []

            # Check each target field
            if not breed.get('health_issues'):
                missing_fields.append('health_issues')
            if not breed.get('grooming_needs'):
                missing_fields.append('grooming_needs')
            if not breed.get('grooming_frequency'):
                missing_fields.append('grooming_frequency')
            if not breed.get('training_tips'):
                missing_fields.append('training_tips')
            if not breed.get('exercise_needs_detail'):
                missing_fields.append('exercise_needs_detail')
            if not breed.get('color_varieties') or len(breed.get('color_varieties', [])) == 0:
                missing_fields.append('color_varieties')
            if not breed.get('fun_facts') or len(breed.get('fun_facts', [])) == 0:
                missing_fields.append('fun_facts')
            if not breed.get('history'):
                missing_fields.append('history')
            if not breed.get('temperament'):
                missing_fields.append('temperament')
            if not breed.get('personality_traits') or len(breed.get('personality_traits', [])) == 0:
                missing_fields.append('personality_traits')

            if missing_fields:
                breed['missing_fields'] = missing_fields
                breeds.append(breed)

        logger.info(f"Found {len(breeds)} breeds needing Phase 1 field completion")
        return breeds

    def extract_health_issues(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract health issues from Wikipedia content"""
        patterns = [
            r'(?:health|medical|disease|condition|disorder|problem)s?',
            r'(?:prone to|susceptible to|affected by)',
            r'(?:genetic|hereditary|congenital)',
            r'hip dysplasia|elbow dysplasia|eye problems|heart disease'
        ]

        health_info = []

        # Search all paragraphs for health-related content
        for p in soup.find_all(['p', 'li']):
            text = p.get_text(strip=True)
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    # Extract the sentence containing health info
                    sentences = text.split('.')
                    for sentence in sentences:
                        if re.search(pattern, sentence, re.IGNORECASE):
                            health_info.append(sentence.strip())
                    break

        if health_info:
            # Combine and clean up
            combined = '. '.join(health_info[:5])  # Limit to 5 sentences
            return combined if len(combined) > 20 else None

        return None

    def extract_grooming_info(self, soup: BeautifulSoup) -> Dict[str, Optional[str]]:
        """Extract grooming needs and frequency"""
        grooming_patterns = [
            r'groom(?:ing)?|brush(?:ing)?|coat (?:care|maintenance)',
            r'shed(?:ding)?|molt(?:ing)?',
            r'bath(?:ing)?|wash(?:ing)?',
            r'trim(?:ming)?|clip(?:ping)?'
        ]

        grooming_info = {
            'grooming_needs': None,
            'grooming_frequency': None
        }

        grooming_text = []

        for p in soup.find_all(['p', 'li']):
            text = p.get_text(strip=True)
            for pattern in grooming_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    grooming_text.append(text)
                    break

        if grooming_text:
            combined = ' '.join(grooming_text[:3])

            # Extract grooming needs
            grooming_info['grooming_needs'] = combined[:500] if len(combined) > 20 else None

            # Try to extract frequency
            freq_patterns = [
                r'daily|every day',
                r'weekly|once a week',
                r'monthly|once a month',
                r'regularly|frequent(?:ly)?',
                r'occasional(?:ly)?|as needed'
            ]

            for pattern in freq_patterns:
                if re.search(pattern, combined, re.IGNORECASE):
                    match = re.search(pattern, combined, re.IGNORECASE)
                    grooming_info['grooming_frequency'] = match.group()
                    break

        return grooming_info

    def extract_training_tips(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract training tips and advice"""
        patterns = [
            r'train(?:ing|able|ability)',
            r'obedien(?:ce|t)',
            r'command(?:s)?|trick(?:s)?',
            r'sociali(?:z|s)ation',
            r'positive reinforcement|reward',
            r'stubborn|independent|eager to please'
        ]

        training_info = []

        for p in soup.find_all(['p', 'li']):
            text = p.get_text(strip=True)
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    training_info.append(text)
                    break

        if training_info:
            combined = ' '.join(training_info[:3])
            return combined[:500] if len(combined) > 20 else None

        return None

    def extract_exercise_needs(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract exercise needs and requirements"""
        patterns = [
            r'exercise|physical activity|walk(?:ing|s)?',
            r'active|energetic|energy level',
            r'run(?:ning)?|jog(?:ging)?|hik(?:ing|e)',
            r'play(?:ing|ful)?|game(?:s)?',
            r'mental stimulation|enrichment'
        ]

        exercise_info = []

        for p in soup.find_all(['p', 'li']):
            text = p.get_text(strip=True)
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    exercise_info.append(text)
                    break

        if exercise_info:
            combined = ' '.join(exercise_info[:3])
            return combined[:500] if len(combined) > 20 else None

        return None

    def extract_color_varieties(self, soup: BeautifulSoup) -> Optional[List[str]]:
        """Extract color varieties and coat colors"""
        color_patterns = [
            r'colou?r(?:s|ing)?|coat colou?r',
            r'black|white|brown|red|cream|gold(?:en)?',
            r'tan|fawn|brindle|merle|sable',
            r'blue|gray|grey|silver',
            r'tri-?colou?r|bi-?colou?r|parti-?colou?r'
        ]

        colors = set()

        for p in soup.find_all(['p', 'li']):
            text = p.get_text(strip=True)
            for pattern in color_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    colors.update([m.lower() for m in matches])

        # Filter out generic terms
        colors.discard('colour')
        colors.discard('color')
        colors.discard('colours')
        colors.discard('colors')
        colors.discard('coat colour')
        colors.discard('coat color')

        return list(colors) if colors else None

    def extract_fun_facts(self, soup: BeautifulSoup) -> Optional[List[str]]:
        """Extract interesting facts about the breed"""
        facts = []

        # Look for interesting patterns
        interesting_patterns = [
            r'famous for|known for|renowned for',
            r'originally|historically|traditionally',
            r'unique(?:ly)?|unusual(?:ly)?|distinctive',
            r'record|first|largest|smallest',
            r'popular(?:ity)?|favor(?:ite|ed)',
            r'royal|noble|aristocrat'
        ]

        for p in soup.find_all(['p', 'li']):
            text = p.get_text(strip=True)
            for pattern in interesting_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    # Extract the sentence
                    sentences = text.split('.')
                    for sentence in sentences:
                        if re.search(pattern, sentence, re.IGNORECASE) and len(sentence) > 30:
                            facts.append(sentence.strip() + '.')
                            break

        # Deduplicate and limit
        seen = set()
        unique_facts = []
        for fact in facts:
            if fact not in seen:
                seen.add(fact)
                unique_facts.append(fact)
                if len(unique_facts) >= 5:
                    break

        return unique_facts if unique_facts else None

    def extract_history(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract breed history"""
        history_sections = ['History', 'Origin', 'Origins', 'Background', 'Development']

        for section_name in history_sections:
            # Try to find section heading
            for heading in soup.find_all(['h2', 'h3']):
                if section_name.lower() in heading.get_text().lower():
                    # Get content after this heading
                    history_text = []
                    element = heading.find_next_sibling()

                    while element and element.name not in ['h2', 'h3']:
                        if element.name == 'p':
                            history_text.append(element.get_text(strip=True))
                        element = element.find_next_sibling()

                    if history_text:
                        combined = ' '.join(history_text[:3])
                        return combined[:800] if len(combined) > 50 else None

        return None

    def extract_temperament(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract temperament information"""
        temp_patterns = [
            r'temperament|disposition|nature|character',
            r'personality|behavior|behaviour',
            r'friendly|aggressive|gentle|calm',
            r'loyal|devoted|independent|aloof',
            r'playful|energetic|laid-back|relaxed'
        ]

        temperament_info = []

        for p in soup.find_all(['p', 'li']):
            text = p.get_text(strip=True)
            for pattern in temp_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    temperament_info.append(text)
                    break

        if temperament_info:
            combined = ' '.join(temperament_info[:2])
            return combined[:400] if len(combined) > 20 else None

        return None

    def extract_personality_traits(self, soup: BeautifulSoup) -> Optional[List[str]]:
        """Extract list of personality traits"""
        trait_words = [
            'friendly', 'loyal', 'intelligent', 'playful', 'energetic',
            'gentle', 'calm', 'alert', 'protective', 'independent',
            'affectionate', 'stubborn', 'eager', 'confident', 'brave',
            'patient', 'devoted', 'adaptable', 'sociable', 'reserved'
        ]

        traits = set()

        for p in soup.find_all(['p', 'li']):
            text = p.get_text(strip=True).lower()
            for trait in trait_words:
                if trait in text:
                    traits.add(trait.capitalize())

        return list(traits) if traits else None

    def process_wikipedia_content(self, breed_slug: str, html_content: str) -> Dict[str, Any]:
        """Process Wikipedia HTML content and extract Phase 1 fields"""
        soup = BeautifulSoup(html_content, 'html.parser')

        extracted_data = {}

        # Extract each target field
        health = self.extract_health_issues(soup)
        if health:
            extracted_data['health_issues'] = health
            self.stats['fields_filled']['health_issues'] += 1

        grooming = self.extract_grooming_info(soup)
        if grooming['grooming_needs']:
            extracted_data['grooming_needs'] = grooming['grooming_needs']
            self.stats['fields_filled']['grooming_needs'] += 1
        if grooming['grooming_frequency']:
            extracted_data['grooming_frequency'] = grooming['grooming_frequency']
            self.stats['fields_filled']['grooming_frequency'] += 1

        training = self.extract_training_tips(soup)
        if training:
            extracted_data['training_tips'] = training
            self.stats['fields_filled']['training_tips'] += 1

        exercise = self.extract_exercise_needs(soup)
        if exercise:
            extracted_data['exercise_needs_detail'] = exercise
            self.stats['fields_filled']['exercise_needs_detail'] += 1

        colors = self.extract_color_varieties(soup)
        if colors:
            extracted_data['color_varieties'] = colors
            self.stats['fields_filled']['color_varieties'] += 1

        facts = self.extract_fun_facts(soup)
        if facts:
            extracted_data['fun_facts'] = facts
            self.stats['fields_filled']['fun_facts'] += 1

        history = self.extract_history(soup)
        if history:
            extracted_data['history'] = history
            self.stats['fields_filled']['history'] += 1

        temperament = self.extract_temperament(soup)
        if temperament:
            extracted_data['temperament'] = temperament
            self.stats['fields_filled']['temperament'] += 1

        traits = self.extract_personality_traits(soup)
        if traits:
            extracted_data['personality_traits'] = traits
            self.stats['fields_filled']['personality_traits'] += 1

        return extracted_data

    def update_breed_content(self, breed_slug: str, extracted_data: Dict) -> bool:
        """Update breed content in database"""
        if not extracted_data:
            return False

        try:
            # Add metadata
            extracted_data['breed_slug'] = breed_slug
            extracted_data['updated_at'] = datetime.now().isoformat()

            # Upsert into breeds_comprehensive_content
            response = self.supabase.table('breeds_comprehensive_content').upsert(
                extracted_data,
                on_conflict='breed_slug'
            ).execute()

            if response.data:
                logger.info(f"✓ Updated {breed_slug}: {len(extracted_data)-2} fields")
                return True

        except Exception as e:
            logger.error(f"Error updating {breed_slug}: {str(e)}")
            self.stats['error_breeds'].append(breed_slug)

        return False

    def process_breed(self, breed: Dict) -> bool:
        """Process a single breed's Wikipedia content"""
        breed_slug = breed['breed_slug']

        # Check what fields are already filled
        existing_fields = []
        for field in self.target_fields.keys():
            value = breed.get(field)
            if value and (isinstance(value, list) and len(value) > 0 or
                         isinstance(value, str) and len(value) > 10):
                existing_fields.append(field)

        if len(existing_fields) == len(self.target_fields):
            logger.debug(f"Skipping {breed_slug}: all target fields already filled")
            self.stats['skipped_breeds'].append(breed_slug)
            return False

        # Try to fetch Wikipedia content from GCS
        blob_path = f"{self.gcs_folder}/{breed_slug}.html"

        try:
            blob = self.bucket.blob(blob_path)
            if not blob.exists():
                logger.debug(f"No Wikipedia content for {breed_slug}")
                self.stats['skipped_breeds'].append(breed_slug)
                return False

            # Download and process content
            html_content = blob.download_as_text()
            extracted_data = self.process_wikipedia_content(breed_slug, html_content)

            # Only update fields that are currently missing
            filtered_data = {}
            for field, value in extracted_data.items():
                existing = breed.get(field)
                if not existing or (isinstance(existing, list) and len(existing) == 0):
                    filtered_data[field] = value

            if filtered_data:
                if self.update_breed_content(breed_slug, filtered_data):
                    self.stats['breeds_updated'] += 1
                    return True
            else:
                logger.debug(f"No new data extracted for {breed_slug}")

        except Exception as e:
            logger.error(f"Error processing {breed_slug}: {str(e)}")
            self.stats['error_breeds'].append(breed_slug)

        return False

    def run(self, test_mode: bool = False, limit: int = None):
        """Run the reprocessor"""
        breeds = self.breeds_to_process[:limit] if limit else self.breeds_to_process

        if test_mode:
            # Test with 5 breeds that failed in Phase 1
            test_breeds = ['africanis', 'aidi', 'akbash', 'aksaray-malaklisi', 'alano-espanol']
            breeds = [b for b in breeds if b['breed_slug'] in test_breeds][:5]
            logger.info(f"TEST MODE: Processing {len(breeds)} breeds")

        logger.info(f"Starting Wikipedia reprocessing for {len(breeds)} breeds")
        logger.info(f"Target fields: {', '.join(self.target_fields.keys())}")

        for idx, breed in enumerate(breeds, 1):
            logger.info(f"[{idx}/{len(breeds)}] Processing {breed['breed_slug']}...")
            self.process_breed(breed)
            self.stats['total_processed'] += 1

            # Progress update every 10 breeds
            if idx % 10 == 0:
                self.print_progress()

        self.print_final_summary()

    def print_progress(self):
        """Print progress update"""
        logger.info(f"""
        === PROGRESS UPDATE ===
        Processed: {self.stats['total_processed']}
        Updated: {self.stats['breeds_updated']}
        Fields filled: {sum(self.stats['fields_filled'].values())}
        """)

    def print_final_summary(self):
        """Print final summary"""
        print("\n" + "="*80)
        print("WIKIPEDIA REPROCESSING COMPLETE")
        print("="*80)
        print(f"Total breeds processed: {self.stats['total_processed']}")
        print(f"Breeds updated: {self.stats['breeds_updated']}")
        print(f"Breeds skipped: {len(self.stats['skipped_breeds'])}")
        print(f"Breeds with errors: {len(self.stats['error_breeds'])}")

        print(f"\nTotal fields filled: {sum(self.stats['fields_filled'].values())}")
        print("\nFields filled by type:")
        for field, count in sorted(self.stats['fields_filled'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {field}: {count}")

        if self.stats['breeds_updated'] > 0:
            success_rate = (self.stats['breeds_updated'] / self.stats['total_processed']) * 100
            print(f"\nSuccess rate: {success_rate:.1f}%")

            # Estimate completeness gain
            total_possible = len(self.breeds_to_process) * len(self.target_fields)
            fields_filled = sum(self.stats['fields_filled'].values())
            estimated_gain = (fields_filled / total_possible) * 100
            print(f"Estimated completeness gain: +{estimated_gain:.2f}%")

        print("="*80)


if __name__ == "__main__":
    import sys

    reprocessor = WikipediaPhase1Reprocessor()

    # Check for test mode
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        print("Running in TEST MODE (5 breeds)...")
        reprocessor.run(test_mode=True)
    else:
        # Confirm before full run
        print(f"Ready to reprocess Wikipedia content for {len(reprocessor.breeds_to_process)} breeds")
        print("Target fields: health_issues, grooming_needs, training_tips, exercise_needs_detail, etc.")
        response = input("Continue with full run? (yes/no): ")
        if response.lower() == 'yes':
            reprocessor.run()
        else:
            print("Aborted. Run with 'test' argument to test with 5 breeds.")