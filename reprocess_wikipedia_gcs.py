#!/usr/bin/env python3
"""
Reprocess Wikipedia breed data from GCS with enhanced extraction
Focuses on extracting missing fields: exercise_needs_detail, training_tips,
grooming_needs, good_with_children, good_with_pets
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

class WikipediaReprocessor:
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
            'failed': 0
        }

    def extract_exercise_needs(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract exercise requirements from various sections"""
        exercise_keywords = ['exercise', 'activity', 'physical', 'energy', 'walk', 'run']
        sections = ['Exercise', 'Activity', 'Physical needs', 'Energy level', 'Care']

        for section in sections:
            heading = self.find_section_heading(soup, section)
            if heading:
                content = self.extract_section_content(heading)
                if content:
                    # Look for exercise-related sentences
                    sentences = content.split('.')
                    exercise_info = []
                    for sent in sentences:
                        if any(keyword in sent.lower() for keyword in exercise_keywords):
                            exercise_info.append(sent.strip())

                    if exercise_info:
                        return '. '.join(exercise_info[:3]) + '.'

        return None

    def extract_training_tips(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract training information"""
        training_keywords = ['train', 'obedience', 'command', 'teach', 'learn', 'intelligent']
        sections = ['Training', 'Temperament', 'Intelligence', 'Trainability']

        for section in sections:
            heading = self.find_section_heading(soup, section)
            if heading:
                content = self.extract_section_content(heading)
                if content:
                    sentences = content.split('.')
                    training_info = []
                    for sent in sentences:
                        if any(keyword in sent.lower() for keyword in training_keywords):
                            training_info.append(sent.strip())

                    if training_info:
                        return '. '.join(training_info[:3]) + '.'

        return None

    def extract_grooming_needs(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract grooming requirements"""
        grooming_keywords = ['groom', 'brush', 'coat', 'fur', 'shed', 'bath', 'trim', 'clip']
        sections = ['Grooming', 'Care', 'Coat', 'Appearance', 'Maintenance']

        for section in sections:
            heading = self.find_section_heading(soup, section)
            if heading:
                content = self.extract_section_content(heading)
                if content:
                    sentences = content.split('.')
                    grooming_info = []
                    for sent in sentences:
                        if any(keyword in sent.lower() for keyword in grooming_keywords):
                            grooming_info.append(sent.strip())

                    if grooming_info:
                        return '. '.join(grooming_info[:3]) + '.'

        return None

    def extract_child_pet_compatibility(self, soup: BeautifulSoup) -> Dict[str, Optional[bool]]:
        """Extract good_with_children and good_with_pets from temperament"""
        result = {'good_with_children': None, 'good_with_pets': None}

        # Look in temperament and personality sections
        sections = ['Temperament', 'Personality', 'Characteristics', 'Behavior']

        for section in sections:
            heading = self.find_section_heading(soup, section)
            if heading:
                content = self.extract_section_content(heading)
                if content:
                    content_lower = content.lower()

                    # Check for children compatibility
                    if result['good_with_children'] is None:
                        positive_child = ['good with children', 'great with kids', 'family-friendly',
                                        'gentle with children', 'patient with children', 'loves children',
                                        'excellent family', 'wonderful with children']
                        negative_child = ['not recommended for children', 'not good with children',
                                        'may snap at children', 'not suitable for families',
                                        'better without children']

                        for phrase in positive_child:
                            if phrase in content_lower:
                                result['good_with_children'] = True
                                break

                        if result['good_with_children'] is None:
                            for phrase in negative_child:
                                if phrase in content_lower:
                                    result['good_with_children'] = False
                                    break

                    # Check for pet compatibility
                    if result['good_with_pets'] is None:
                        positive_pets = ['good with other dogs', 'gets along with pets',
                                       'friendly with other animals', 'sociable with dogs',
                                       'good with cats', 'compatible with other pets']
                        negative_pets = ['aggressive toward other dogs', 'not good with other pets',
                                       'may chase cats', 'dog aggressive', 'not suitable for multi-pet']

                        for phrase in positive_pets:
                            if phrase in content_lower:
                                result['good_with_pets'] = True
                                break

                        if result['good_with_pets'] is None:
                            for phrase in negative_pets:
                                if phrase in content_lower:
                                    result['good_with_pets'] = False
                                    break

        return result

    def find_section_heading(self, soup: BeautifulSoup, section_name: str):
        """Find a section heading in the HTML"""
        for heading in soup.find_all(['h2', 'h3', 'h4']):
            if section_name.lower() in heading.get_text().lower():
                return heading
        return None

    def extract_section_content(self, heading, max_paragraphs: int = 3) -> Optional[str]:
        """Extract content after a heading"""
        paragraphs = []
        current = heading.find_next_sibling()

        while current and len(paragraphs) < max_paragraphs:
            if current.name in ['h2', 'h3', 'h4']:
                break

            if current.name == 'p':
                text = current.get_text(strip=True)
                # Clean citations
                text = re.sub(r'\[\d+\]', '', text)
                text = re.sub(r'\s+', ' ', text)
                if text and len(text) > 30:
                    paragraphs.append(text)

            current = current.find_next_sibling()

        return ' '.join(paragraphs) if paragraphs else None

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

        # Also try to extract grooming frequency if possible
        extracted_data['grooming_frequency'] = self.determine_grooming_frequency(
            extracted_data.get('grooming_needs', '')
        )

        # Extract exercise level
        extracted_data['exercise_level'] = self.determine_exercise_level(
            extracted_data.get('exercise_needs_detail', '')
        )

        return extracted_data

    def determine_grooming_frequency(self, grooming_text: str) -> Optional[str]:
        """Determine grooming frequency from text"""
        if not grooming_text:
            return None

        text_lower = grooming_text.lower()

        if any(word in text_lower for word in ['daily', 'every day', 'each day']):
            return 'daily'
        elif any(word in text_lower for word in ['weekly', 'once a week', 'every week']):
            return 'weekly'
        elif any(word in text_lower for word in ['monthly', 'once a month']):
            return 'monthly'
        elif any(word in text_lower for word in ['occasionally', 'minimal', 'low maintenance']):
            return 'minimal'

        return None

    def determine_exercise_level(self, exercise_text: str) -> Optional[str]:
        """Determine exercise level from text"""
        if not exercise_text:
            return None

        text_lower = exercise_text.lower()

        if any(word in text_lower for word in ['high energy', 'very active', 'extensive exercise',
                                               'hours of exercise', 'vigorous']):
            return 'high'
        elif any(word in text_lower for word in ['moderate exercise', 'regular walks',
                                                 'average activity']):
            return 'moderate'
        elif any(word in text_lower for word in ['minimal exercise', 'low energy',
                                                'short walks', 'sedentary']):
            return 'low'

        return None

    def update_database(self, extracted_data: Dict[str, Any]) -> bool:
        """Update the breeds_comprehensive_content table with new data"""
        breed_slug = extracted_data['breed_slug']

        # Remove breed_slug from update data
        update_data = {k: v for k, v in extracted_data.items()
                      if k != 'breed_slug' and v is not None}

        if not update_data:
            return False

        try:
            # Update breeds_comprehensive_content
            result = self.supabase.table('breeds_comprehensive_content').update(
                update_data
            ).eq('breed_slug', breed_slug).execute()

            return bool(result.data)
        except Exception as e:
            logger.error(f"Error updating {breed_slug}: {e}")
            return False

    def process_all_breeds(self):
        """Process all breeds from GCS"""
        logger.info(f"Starting reprocessing of Wikipedia data from {self.gcs_folder}")

        # List all HTML files in GCS
        prefix = self.gcs_folder + '/'
        blobs = self.bucket.list_blobs(prefix=prefix)

        for blob in blobs:
            if blob.name.endswith('.html'):
                self.stats['total'] += 1

                # Extract breed slug from filename
                breed_slug = blob.name.split('/')[-1].replace('.html', '')

                try:
                    # Download HTML
                    html_content = blob.download_as_text()

                    # Process HTML
                    extracted_data = self.process_breed_html(breed_slug, html_content)

                    # Track what we extracted
                    if extracted_data.get('exercise_needs_detail'):
                        self.stats['exercise_extracted'] += 1
                    if extracted_data.get('training_tips'):
                        self.stats['training_extracted'] += 1
                    if extracted_data.get('grooming_needs'):
                        self.stats['grooming_extracted'] += 1
                    if extracted_data.get('good_with_children') is not None:
                        self.stats['children_extracted'] += 1
                    if extracted_data.get('good_with_pets') is not None:
                        self.stats['pets_extracted'] += 1

                    # Update database
                    if self.update_database(extracted_data):
                        self.stats['processed'] += 1
                        logger.info(f"✓ Processed {breed_slug}")
                    else:
                        logger.warning(f"No new data for {breed_slug}")

                except Exception as e:
                    self.stats['failed'] += 1
                    logger.error(f"✗ Failed to process {breed_slug}: {e}")

                # Log progress every 50 breeds
                if self.stats['total'] % 50 == 0:
                    self.log_progress()

        self.log_final_stats()

    def log_progress(self):
        """Log current progress"""
        logger.info(f"""
        Progress: {self.stats['processed']}/{self.stats['total']} breeds processed
        - Exercise extracted: {self.stats['exercise_extracted']}
        - Training extracted: {self.stats['training_extracted']}
        - Grooming extracted: {self.stats['grooming_extracted']}
        - Child compatibility: {self.stats['children_extracted']}
        - Pet compatibility: {self.stats['pets_extracted']}
        """)

    def log_final_stats(self):
        """Log final statistics"""
        logger.info(f"""
        ========================================
        REPROCESSING COMPLETE
        ========================================
        Total breeds: {self.stats['total']}
        Successfully processed: {self.stats['processed']}
        Failed: {self.stats['failed']}

        Field Extraction Results:
        - Exercise needs: {self.stats['exercise_extracted']} ({self.stats['exercise_extracted']*100/max(self.stats['total'],1):.1f}%)
        - Training tips: {self.stats['training_extracted']} ({self.stats['training_extracted']*100/max(self.stats['total'],1):.1f}%)
        - Grooming needs: {self.stats['grooming_extracted']} ({self.stats['grooming_extracted']*100/max(self.stats['total'],1):.1f}%)
        - Good with children: {self.stats['children_extracted']} ({self.stats['children_extracted']*100/max(self.stats['total'],1):.1f}%)
        - Good with pets: {self.stats['pets_extracted']} ({self.stats['pets_extracted']*100/max(self.stats['total'],1):.1f}%)
        ========================================
        """)

if __name__ == "__main__":
    processor = WikipediaReprocessor()
    processor.process_all_breeds()