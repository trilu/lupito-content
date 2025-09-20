#!/usr/bin/env python3
"""
Fixed Wikipedia reprocessor - searches all paragraphs for relevant content
instead of looking for specific section headings
"""

import os
import re
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from google.cloud import storage
from bs4 import BeautifulSoup
from supabase import create_client, Client
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class WikipediaReprocessorFixed:
    def __init__(self, gcs_folder: str = None):
        """Initialize the reprocessor"""
        # Initialize Supabase
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

        # Initialize GCS
        self.storage_client = storage.Client(project='careful-drummer-468512-p0')
        self.bucket = self.storage_client.bucket('lupito-content-raw-eu')

        # Set folder - use the latest Wikipedia scrape
        self.gcs_folder = gcs_folder or 'scraped/wikipedia_breeds/20250917_162810'

        # Stats
        self.stats = {
            'total': 0,
            'processed': 0,
            'exercise_extracted': 0,
            'training_extracted': 0,
            'grooming_extracted': 0,
            'children_extracted': 0,
            'pets_extracted': 0,
            'updated': 0,
            'failed': 0
        }

    def extract_exercise_needs(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract exercise requirements from all paragraphs"""
        exercise_keywords = [
            'exercise', 'activity', 'physical', 'energy', 'energetic',
            'walk', 'walks', 'walking', 'run', 'running', 'jog',
            'active', 'athletic', 'agility', 'stamina', 'endurance'
        ]

        exercise_info = []
        paragraphs = soup.find_all('p')

        for p in paragraphs:
            text = p.get_text(strip=True)
            # Clean citations
            text = re.sub(r'\[\d+\]', '', text)
            text = re.sub(r'\s+', ' ', text)

            # Check if paragraph contains exercise information
            text_lower = text.lower()
            if any(keyword in text_lower for keyword in exercise_keywords):
                # Extract relevant sentences
                sentences = text.split('.')
                for sent in sentences:
                    sent_lower = sent.lower()
                    if any(keyword in sent_lower for keyword in exercise_keywords):
                        clean_sent = sent.strip()
                        if clean_sent and len(clean_sent) > 20:  # Avoid very short fragments
                            exercise_info.append(clean_sent)

                        # Stop after finding 3 good sentences
                        if len(exercise_info) >= 3:
                            break

            if len(exercise_info) >= 3:
                break

        if exercise_info:
            # Join and clean up
            result = '. '.join(exercise_info[:3])
            if not result.endswith('.'):
                result += '.'
            return result

        return None

    def extract_training_tips(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract training information from all paragraphs"""
        training_keywords = [
            'train', 'training', 'trainable', 'trainability',
            'obedience', 'obedient', 'command', 'commands',
            'teach', 'teaching', 'learn', 'learning', 'intelligent',
            'intelligence', 'smart', 'stubborn', 'independent',
            'eager to please', 'easy to train', 'difficult to train'
        ]

        training_info = []
        paragraphs = soup.find_all('p')

        for p in paragraphs:
            text = p.get_text(strip=True)
            text = re.sub(r'\[\d+\]', '', text)
            text = re.sub(r'\s+', ' ', text)

            text_lower = text.lower()
            if any(keyword in text_lower for keyword in training_keywords):
                sentences = text.split('.')
                for sent in sentences:
                    sent_lower = sent.lower()
                    if any(keyword in sent_lower for keyword in training_keywords):
                        clean_sent = sent.strip()
                        if clean_sent and len(clean_sent) > 20:
                            training_info.append(clean_sent)

                        if len(training_info) >= 3:
                            break

            if len(training_info) >= 3:
                break

        if training_info:
            result = '. '.join(training_info[:3])
            if not result.endswith('.'):
                result += '.'
            return result

        return None

    def extract_grooming_needs(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract grooming requirements from all paragraphs"""
        grooming_keywords = [
            'groom', 'grooming', 'brush', 'brushing', 'brushed',
            'coat', 'coats', 'fur', 'hair', 'shed', 'shedding',
            'bath', 'bathing', 'trim', 'trimming', 'clip', 'clipping',
            'maintenance', 'mat', 'matting', 'tangle', 'comb', 'combing'
        ]

        grooming_info = []
        paragraphs = soup.find_all('p')

        for p in paragraphs:
            text = p.get_text(strip=True)
            text = re.sub(r'\[\d+\]', '', text)
            text = re.sub(r'\s+', ' ', text)

            text_lower = text.lower()
            if any(keyword in text_lower for keyword in grooming_keywords):
                sentences = text.split('.')
                for sent in sentences:
                    sent_lower = sent.lower()
                    # Look for grooming context (not just coat description)
                    if any(keyword in sent_lower for keyword in ['groom', 'brush', 'shed', 'maintenance', 'bath', 'trim']):
                        clean_sent = sent.strip()
                        if clean_sent and len(clean_sent) > 20:
                            grooming_info.append(clean_sent)

                        if len(grooming_info) >= 3:
                            break

            if len(grooming_info) >= 3:
                break

        if grooming_info:
            result = '. '.join(grooming_info[:3])
            if not result.endswith('.'):
                result += '.'
            return result

        return None

    def extract_child_pet_compatibility(self, soup: BeautifulSoup) -> Dict[str, Optional[bool]]:
        """Extract good_with_children and good_with_pets from all paragraphs"""
        result = {'good_with_children': None, 'good_with_pets': None}

        paragraphs = soup.find_all('p')

        # Children compatibility patterns
        positive_child_patterns = [
            'good with children', 'great with kids', 'excellent with children',
            'family-friendly', 'family friendly', 'gentle with children',
            'patient with children', 'loves children', 'excellent family',
            'wonderful with children', 'great family', 'ideal family',
            'child-friendly', 'child friendly', 'tolerant of children'
        ]

        negative_child_patterns = [
            'not recommended for children', 'not good with children',
            'may snap at children', 'not suitable for families with',
            'better without children', 'not ideal for children',
            'supervision with children', 'caution around children'
        ]

        # Pet compatibility patterns
        positive_pet_patterns = [
            'good with other dogs', 'gets along with pets',
            'friendly with other animals', 'sociable with dogs',
            'good with cats', 'compatible with other pets',
            'tolerates other pets', 'lives well with other',
            'peaceful with other', 'gentle with other animals'
        ]

        negative_pet_patterns = [
            'aggressive toward other dogs', 'not good with other pets',
            'may chase cats', 'dog aggressive', 'not suitable for multi-pet',
            'prey drive', 'high prey drive', 'chase small animals',
            'not recommended with cats', 'territorial with other'
        ]

        # Search through paragraphs
        for p in paragraphs[:30]:  # Check first 30 paragraphs
            text = p.get_text(strip=True)
            text = re.sub(r'\[\d+\]', '', text)
            text_lower = text.lower()

            # Check children compatibility
            if result['good_with_children'] is None:
                for pattern in positive_child_patterns:
                    if pattern in text_lower:
                        result['good_with_children'] = True
                        break

                if result['good_with_children'] is None:
                    for pattern in negative_child_patterns:
                        if pattern in text_lower:
                            result['good_with_children'] = False
                            break

            # Check pet compatibility
            if result['good_with_pets'] is None:
                for pattern in positive_pet_patterns:
                    if pattern in text_lower:
                        result['good_with_pets'] = True
                        break

                if result['good_with_pets'] is None:
                    for pattern in negative_pet_patterns:
                        if pattern in text_lower:
                            result['good_with_pets'] = False
                            break

            # Stop if both found
            if result['good_with_children'] is not None and result['good_with_pets'] is not None:
                break

        return result

    def determine_grooming_frequency(self, grooming_text: str) -> Optional[str]:
        """Determine grooming frequency from text"""
        if not grooming_text:
            return None

        text_lower = grooming_text.lower()

        if any(word in text_lower for word in ['daily', 'every day', 'each day']):
            return 'daily'
        elif any(word in text_lower for word in ['twice a week', 'several times a week', 'few times a week']):
            return 'bi-weekly'
        elif any(word in text_lower for word in ['weekly', 'once a week', 'every week']):
            return 'weekly'
        elif any(word in text_lower for word in ['monthly', 'once a month']):
            return 'monthly'
        elif any(word in text_lower for word in ['occasionally', 'minimal', 'low maintenance', 'rarely']):
            return 'minimal'

        return None

    def determine_exercise_level(self, exercise_text: str) -> Optional[str]:
        """Determine exercise level from text"""
        if not exercise_text:
            return None

        text_lower = exercise_text.lower()

        high_indicators = [
            'high energy', 'very active', 'extremely active',
            'extensive exercise', 'hours of exercise', 'vigorous',
            'athletic', 'very energetic', 'needs a lot of exercise',
            'requires substantial', 'highly active'
        ]

        low_indicators = [
            'minimal exercise', 'low energy', 'short walks',
            'sedentary', 'couch potato', 'lazy', 'inactive',
            'little exercise', 'not very active'
        ]

        # Check for high energy
        for indicator in high_indicators:
            if indicator in text_lower:
                return 'high'

        # Check for low energy
        for indicator in low_indicators:
            if indicator in text_lower:
                return 'low'

        # Default to moderate if exercise is mentioned but not specific
        if 'exercise' in text_lower or 'walk' in text_lower:
            return 'moderate'

        return None

    def process_breed_html(self, breed_slug: str, html_content: str) -> Dict[str, Any]:
        """Process a single breed's HTML to extract missing fields"""
        soup = BeautifulSoup(html_content, 'html.parser')

        extracted_data = {
            'breed_slug': breed_slug,
            'exercise_needs_detail': self.extract_exercise_needs(soup),
            'training_tips': self.extract_training_tips(soup),
            'grooming_needs': self.extract_grooming_needs(soup)
        }

        # Extract child/pet compatibility
        compatibility = self.extract_child_pet_compatibility(soup)
        extracted_data.update(compatibility)

        # Determine grooming frequency if we have grooming text
        if extracted_data.get('grooming_needs'):
            extracted_data['grooming_frequency'] = self.determine_grooming_frequency(
                extracted_data['grooming_needs']
            )

        # Determine exercise level if we have exercise text
        if extracted_data.get('exercise_needs_detail'):
            extracted_data['exercise_level'] = self.determine_exercise_level(
                extracted_data['exercise_needs_detail']
            )

        return extracted_data

    def update_database(self, extracted_data: Dict[str, Any]) -> bool:
        """Update the breeds_comprehensive_content table with new data"""
        breed_slug = extracted_data['breed_slug']

        # Remove breed_slug from update data and filter out None values
        update_data = {k: v for k, v in extracted_data.items()
                      if k != 'breed_slug' and v is not None}

        if not update_data:
            return False

        try:
            # Check if record exists
            existing = self.supabase.table('breeds_comprehensive_content').select(
                'id'
            ).eq('breed_slug', breed_slug).execute()

            if existing.data:
                # Update existing record
                result = self.supabase.table('breeds_comprehensive_content').update(
                    update_data
                ).eq('breed_slug', breed_slug).execute()
            else:
                # Insert new record
                update_data['breed_slug'] = breed_slug
                result = self.supabase.table('breeds_comprehensive_content').insert(
                    update_data
                ).execute()

            return bool(result.data)
        except Exception as e:
            logger.error(f"Error updating {breed_slug}: {e}")
            return False

    def process_all_breeds(self, limit: int = None):
        """Process all breeds from GCS"""
        logger.info(f"Starting reprocessing of Wikipedia data from {self.gcs_folder}")

        # List all HTML files in GCS
        prefix = self.gcs_folder + '/'
        blobs = list(self.bucket.list_blobs(prefix=prefix))

        # Filter HTML files
        html_blobs = [b for b in blobs if b.name.endswith('.html')]

        if limit:
            html_blobs = html_blobs[:limit]

        logger.info(f"Found {len(html_blobs)} HTML files to process")

        for blob in html_blobs:
            self.stats['total'] += 1

            # Extract breed slug from filename
            breed_slug = blob.name.split('/')[-1].replace('.html', '')

            try:
                # Download HTML
                html_content = blob.download_as_text()

                # Process HTML
                extracted_data = self.process_breed_html(breed_slug, html_content)

                # Track what we extracted
                fields_found = []
                if extracted_data.get('exercise_needs_detail'):
                    self.stats['exercise_extracted'] += 1
                    fields_found.append('exercise')
                if extracted_data.get('training_tips'):
                    self.stats['training_extracted'] += 1
                    fields_found.append('training')
                if extracted_data.get('grooming_needs'):
                    self.stats['grooming_extracted'] += 1
                    fields_found.append('grooming')
                if extracted_data.get('good_with_children') is not None:
                    self.stats['children_extracted'] += 1
                    fields_found.append('children')
                if extracted_data.get('good_with_pets') is not None:
                    self.stats['pets_extracted'] += 1
                    fields_found.append('pets')

                # Update database if we found anything
                if fields_found:
                    if self.update_database(extracted_data):
                        self.stats['updated'] += 1
                        logger.info(f"✓ Updated {breed_slug}: {', '.join(fields_found)}")
                    else:
                        logger.warning(f"⚠ Failed to update DB for {breed_slug}")
                else:
                    logger.debug(f"- No new data for {breed_slug}")

                self.stats['processed'] += 1

            except Exception as e:
                self.stats['failed'] += 1
                logger.error(f"✗ Failed to process {breed_slug}: {e}")

            # Log progress every 25 breeds
            if self.stats['total'] % 25 == 0:
                self.log_progress()

        self.log_final_stats()

    def log_progress(self):
        """Log current progress"""
        logger.info(f"""
        Progress: {self.stats['processed']}/{self.stats['total']} breeds
        Database updated: {self.stats['updated']}
        - Exercise: {self.stats['exercise_extracted']}
        - Training: {self.stats['training_extracted']}
        - Grooming: {self.stats['grooming_extracted']}
        - Children: {self.stats['children_extracted']}
        - Pets: {self.stats['pets_extracted']}
        """)

    def log_final_stats(self):
        """Log final statistics"""
        total = max(self.stats['total'], 1)
        logger.info(f"""
        ========================================
        REPROCESSING COMPLETE
        ========================================
        Total breeds: {self.stats['total']}
        Successfully processed: {self.stats['processed']}
        Database updated: {self.stats['updated']}
        Failed: {self.stats['failed']}

        Field Extraction Results:
        - Exercise needs: {self.stats['exercise_extracted']} ({self.stats['exercise_extracted']*100/total:.1f}%)
        - Training tips: {self.stats['training_extracted']} ({self.stats['training_extracted']*100/total:.1f}%)
        - Grooming needs: {self.stats['grooming_extracted']} ({self.stats['grooming_extracted']*100/total:.1f}%)
        - Good with children: {self.stats['children_extracted']} ({self.stats['children_extracted']*100/total:.1f}%)
        - Good with pets: {self.stats['pets_extracted']} ({self.stats['pets_extracted']*100/total:.1f}%)
        ========================================
        """)

if __name__ == "__main__":
    import sys

    # Allow limiting number of breeds for testing
    limit = None
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])
        logger.info(f"Processing limited to {limit} breeds")

    processor = WikipediaReprocessorFixed()
    processor.process_all_breeds(limit=limit)