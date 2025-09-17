#!/usr/bin/env python3
"""
Extract rich content from Wikipedia HTML stored in GCS
Processes HTML files to extract personality, history, care info, and other text content
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

class RichContentExtractor:
    def __init__(self, gcs_folder: str = None):
        """Initialize the rich content extractor"""
        # Initialize Supabase
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

        # Initialize GCS
        self.storage_client = storage.Client(project='careful-drummer-468512-p0')
        self.bucket = self.storage_client.bucket('lupito-content-raw-eu')

        # Set folder
        self.gcs_folder = gcs_folder or 'scraped/wikipedia_breeds/20250917_162810'

        # Stats
        self.stats = {
            'total': 0,
            'processed': 0,
            'with_personality': 0,
            'with_history': 0,
            'with_care': 0,
            'with_health': 0,
            'with_training': 0,
            'with_facts': 0,
            'failed': 0
        }

    def extract_section_text(self, soup: BeautifulSoup, heading_text: str,
                            max_paragraphs: int = 3) -> Optional[str]:
        """Extract text from a specific section"""
        # Try to find the heading - exact match or contains
        for heading in soup.find_all(['h2', 'h3']):
            heading_content = heading.get_text().lower().strip()
            if heading_text.lower() == heading_content or heading_text.lower() in heading_content:
                paragraphs = []

                # Start from the parent container (handles wrapped headings)
                parent = heading.parent
                if parent and parent.name == 'div':
                    current = parent.find_next_sibling()
                else:
                    current = heading.find_next_sibling()

                # Collect paragraphs until we hit another heading
                while current:
                    # Stop at next heading (including wrapped ones)
                    if current.name in ['h2', 'h3']:
                        break
                    if current.name == 'div' and current.find(['h2', 'h3']):
                        break

                    # Extract text from paragraphs
                    if current.name == 'p':
                        text = current.get_text(strip=True)
                        # Clean up citations like [1], [2], etc.
                        text = re.sub(r'\[\d+\]', '', text)
                        text = re.sub(r'\s+', ' ', text)
                        if text and len(text) > 50:  # Skip very short paragraphs
                            paragraphs.append(text)
                            if len(paragraphs) >= max_paragraphs:
                                break

                    # Also check for paragraphs inside divs or other containers
                    elif current.name in ['div', 'section']:
                        for p in current.find_all('p', recursive=False):
                            text = p.get_text(strip=True)
                            text = re.sub(r'\[\d+\]', '', text)
                            text = re.sub(r'\s+', ' ', text)
                            if text and len(text) > 50:
                                paragraphs.append(text)
                                if len(paragraphs) >= max_paragraphs:
                                    break

                    current = current.find_next_sibling()

                if paragraphs:
                    return ' '.join(paragraphs)
        return None

    def extract_introduction(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract the introduction/lead section"""
        content = soup.find('div', {'id': 'mw-content-text'})
        if not content:
            return None

        # Find all paragraphs before the first h2
        paragraphs = []
        for elem in content.find_all(['p', 'h2'], recursive=True):
            if elem.name == 'h2':
                break
            if elem.name == 'p':
                # Skip if it's inside a table or infobox
                if elem.find_parent('table'):
                    continue
                text = elem.get_text(strip=True)
                # Clean up
                text = re.sub(r'\[\d+\]', '', text)
                text = re.sub(r'\s+', ' ', text)
                if text and len(text) > 100:
                    paragraphs.append(text)
                    if len(paragraphs) >= 2:  # Get first 2 paragraphs
                        break

        return ' '.join(paragraphs) if paragraphs else None

    def extract_personality_traits(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract personality and temperament information"""
        result = {
            'personality_description': None,
            'temperament': None,
            'personality_traits': [],
            'good_with_children': None,
            'good_with_pets': None,
            'friendliness': None,
            'trainability_desc': None
        }

        # Look for temperament/personality sections
        for heading_text in ['Temperament', 'Personality', 'Characteristics', 'Behavior', 'Nature', 'Description', 'Character', 'Traits']:
            text = self.extract_section_text(soup, heading_text)
            if text:
                result['personality_description'] = text

                # Extract specific traits
                if 'friendly' in text.lower():
                    result['personality_traits'].append('friendly')
                if 'loyal' in text.lower():
                    result['personality_traits'].append('loyal')
                if 'intelligent' in text.lower():
                    result['personality_traits'].append('intelligent')
                if 'playful' in text.lower():
                    result['personality_traits'].append('playful')
                if 'gentle' in text.lower():
                    result['personality_traits'].append('gentle')
                if 'protective' in text.lower():
                    result['personality_traits'].append('protective')
                if 'energetic' in text.lower() or 'active' in text.lower():
                    result['personality_traits'].append('energetic')
                if 'calm' in text.lower():
                    result['personality_traits'].append('calm')

                # Check compatibility
                if 'children' in text.lower():
                    if 'good with children' in text.lower() or 'excellent with children' in text.lower():
                        result['good_with_children'] = True
                    elif 'not recommended' in text.lower() or 'not suitable' in text.lower():
                        result['good_with_children'] = False

                if 'other pets' in text.lower() or 'other dogs' in text.lower():
                    if 'gets along' in text.lower() or 'good with' in text.lower():
                        result['good_with_pets'] = True
                    elif 'aggressive' in text.lower() or 'not good' in text.lower():
                        result['good_with_pets'] = False

                break

        # Remove duplicates from traits
        result['personality_traits'] = list(set(result['personality_traits']))

        return result

    def extract_history(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract history and origin information"""
        result = {
            'history': None,
            'history_brief': None,
            'origin_story': None
        }

        # Look for history sections
        for heading_text in ['History', 'Origin', 'Development', 'Background', 'Origins', 'Breed history']:
            text = self.extract_section_text(soup, heading_text, max_paragraphs=3)
            if text:
                result['history'] = text
                # Create a brief version (first 500 chars)
                result['history_brief'] = text[:500] + '...' if len(text) > 500 else text
                break

        return result

    def extract_care_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract care and maintenance information"""
        result = {
            'general_care': None,
            'grooming_needs': None,
            'grooming_frequency': None,
            'exercise_needs_detail': None,
            'exercise_level': None,
            'training_tips': None,
            'feeding_guidelines': None
        }

        # Care section
        care_text = self.extract_section_text(soup, 'Care', max_paragraphs=2)
        if not care_text:
            # Try alternative headings
            care_text = self.extract_section_text(soup, 'Maintenance', max_paragraphs=2)
        if care_text:
            result['general_care'] = care_text

        # Grooming section
        grooming_text = self.extract_section_text(soup, 'Grooming', max_paragraphs=2)
        if grooming_text:
            result['grooming_needs'] = grooming_text
            # Try to extract frequency
            if 'daily' in grooming_text.lower():
                result['grooming_frequency'] = 'daily'
            elif 'weekly' in grooming_text.lower():
                result['grooming_frequency'] = 'weekly'
            elif 'monthly' in grooming_text.lower():
                result['grooming_frequency'] = 'monthly'

        # Exercise section
        exercise_text = self.extract_section_text(soup, 'Exercise', max_paragraphs=2)
        if exercise_text:
            result['exercise_needs_detail'] = exercise_text
            # Try to determine level
            if 'high energy' in exercise_text.lower() or 'very active' in exercise_text.lower():
                result['exercise_level'] = 'high'
            elif 'moderate' in exercise_text.lower():
                result['exercise_level'] = 'moderate'
            elif 'minimal' in exercise_text.lower() or 'low' in exercise_text.lower():
                result['exercise_level'] = 'low'

        # Training section
        training_text = self.extract_section_text(soup, 'Training', max_paragraphs=2)
        if training_text:
            result['training_tips'] = training_text

        return result

    def extract_health_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract health information"""
        result = {
            'health_issues': None,
            'lifespan_notes': None
        }

        # Health section
        health_text = self.extract_section_text(soup, 'Health', max_paragraphs=3)
        if not health_text:
            # Try alternative headings
            health_text = self.extract_section_text(soup, 'Health concerns', max_paragraphs=3)
        if health_text:
            result['health_issues'] = health_text

        return result

    def extract_fun_facts(self, soup: BeautifulSoup) -> List[str]:
        """Extract interesting facts and trivia"""
        facts = []

        # Look for trivia or interesting facts sections
        for heading_text in ['Trivia', 'Notable', 'Famous', 'Pop culture', 'In popular culture']:
            text = self.extract_section_text(soup, heading_text, max_paragraphs=2)
            if text:
                # Split into sentences and take interesting ones
                sentences = text.split('.')
                for sentence in sentences[:3]:  # Take up to 3 facts
                    sentence = sentence.strip()
                    if sentence and len(sentence) > 30:
                        facts.append(sentence + '.')

        # Also check for record mentions in the introduction
        intro = self.extract_introduction(soup)
        if intro:
            if 'first' in intro.lower() or 'record' in intro.lower() or 'famous' in intro.lower():
                # Extract the sentence with the record/fame mention
                sentences = intro.split('.')
                for sentence in sentences:
                    if any(word in sentence.lower() for word in ['first', 'record', 'famous', 'popular']):
                        facts.append(sentence.strip() + '.')
                        break

        return facts[:5]  # Return max 5 facts

    def extract_working_roles(self, soup: BeautifulSoup) -> List[str]:
        """Extract working and activity roles"""
        roles = set()

        # Get all text content
        text = soup.get_text().lower()

        # Define role patterns
        role_patterns = {
            'guide dog': ['guide dog', 'seeing eye'],
            'therapy dog': ['therapy dog', 'therapy work'],
            'service dog': ['service dog', 'assistance dog'],
            'police dog': ['police dog', 'police work', 'k9', 'k-9'],
            'military dog': ['military dog', 'military work', 'war dog'],
            'search and rescue': ['search and rescue', 'sar dog'],
            'hunting dog': ['hunting dog', 'gun dog', 'bird dog', 'retriever work'],
            'herding dog': ['herding dog', 'sheep dog', 'cattle dog', 'stock dog'],
            'guard dog': ['guard dog', 'watchdog', 'protection dog'],
            'sled dog': ['sled dog', 'sledding', 'mushing'],
            'racing dog': ['racing dog', 'racing breed'],
            'detection dog': ['detection dog', 'drug detection', 'explosive detection']
        }

        for role, patterns in role_patterns.items():
            for pattern in patterns:
                if pattern in text:
                    roles.add(role)
                    break

        return list(roles)

    def process_html(self, html_content: str, breed_slug: str) -> Dict[str, Any]:
        """Process HTML content and extract all rich content"""
        soup = BeautifulSoup(html_content, 'html.parser')

        # Extract all components
        intro = self.extract_introduction(soup)
        personality = self.extract_personality_traits(soup)
        history = self.extract_history(soup)
        care = self.extract_care_info(soup)
        health = self.extract_health_info(soup)
        fun_facts = self.extract_fun_facts(soup)
        working_roles = self.extract_working_roles(soup)

        # Compile results
        result = {
            'breed_slug': breed_slug,
            'introduction': intro,
            'updated_at': datetime.now().isoformat()
        }

        # Merge all extracted data
        result.update(personality)
        result.update(history)
        result.update(care)
        result.update(health)
        result['fun_facts'] = fun_facts if fun_facts else None
        result['working_roles'] = working_roles if working_roles else None

        # Update stats
        if personality['personality_description']:
            self.stats['with_personality'] += 1
        if history['history']:
            self.stats['with_history'] += 1
        if care['general_care'] or care['grooming_needs']:
            self.stats['with_care'] += 1
        if health['health_issues']:
            self.stats['with_health'] += 1
        if care['training_tips']:
            self.stats['with_training'] += 1
        if fun_facts:
            self.stats['with_facts'] += 1

        return result

    def update_database(self, content_data: Dict[str, Any]) -> bool:
        """Update the breeds_comprehensive_content table"""
        # Remove None values
        content_data = {k: v for k, v in content_data.items() if v is not None}

        # Remove empty lists
        for key, value in list(content_data.items()):
            if isinstance(value, list) and len(value) == 0:
                del content_data[key]

        if content_data.get('breed_slug'):
            try:
                # Upsert to breeds_comprehensive_content
                response = self.supabase.table('breeds_comprehensive_content').upsert(
                    content_data,
                    on_conflict='breed_slug'
                ).execute()
                logger.info(f"Updated content for {content_data['breed_slug']}")
                return True
            except Exception as e:
                logger.error(f"Failed to update {content_data['breed_slug']}: {e}")
                return False
        return False

    def process_all(self, test_mode: bool = False):
        """Process all HTML files from GCS"""
        logger.info(f"Starting rich content extraction from {self.gcs_folder}")

        # List all HTML files
        prefix = self.gcs_folder + '/'
        blobs = list(self.bucket.list_blobs(prefix=prefix))
        html_files = [b for b in blobs if b.name.endswith('.html')]

        self.stats['total'] = len(html_files)
        logger.info(f"Found {self.stats['total']} HTML files to process")

        # Process limit for test mode
        if test_mode:
            html_files = html_files[:5]
            logger.info("TEST MODE: Processing only first 5 breeds")

        # Process each file
        for i, blob in enumerate(html_files, 1):
            breed_slug = blob.name.split('/')[-1].replace('.html', '')
            logger.info(f"[{i}/{len(html_files)}] Processing {breed_slug}")

            try:
                # Download HTML
                html_content = blob.download_as_text()

                # Extract rich content
                content_data = self.process_html(html_content, breed_slug)

                # Update database
                if self.update_database(content_data):
                    self.stats['processed'] += 1
                else:
                    self.stats['failed'] += 1

            except Exception as e:
                logger.error(f"Failed to process {breed_slug}: {e}")
                self.stats['failed'] += 1

        # Print summary
        self.print_summary()
        return self.stats

    def print_summary(self):
        """Print processing summary"""
        logger.info("=" * 60)
        logger.info("RICH CONTENT EXTRACTION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total HTML files: {self.stats['total']}")
        logger.info(f"Successfully processed: {self.stats['processed']}")
        logger.info(f"Failed: {self.stats['failed']}")
        logger.info("")
        logger.info("Content Coverage:")
        logger.info(f"  With personality: {self.stats['with_personality']} ({self.stats['with_personality']*100//max(1, self.stats['processed'])}%)")
        logger.info(f"  With history: {self.stats['with_history']} ({self.stats['with_history']*100//max(1, self.stats['processed'])}%)")
        logger.info(f"  With care info: {self.stats['with_care']} ({self.stats['with_care']*100//max(1, self.stats['processed'])}%)")
        logger.info(f"  With health info: {self.stats['with_health']} ({self.stats['with_health']*100//max(1, self.stats['processed'])}%)")
        logger.info(f"  With training tips: {self.stats['with_training']} ({self.stats['with_training']*100//max(1, self.stats['processed'])}%)")
        logger.info(f"  With fun facts: {self.stats['with_facts']} ({self.stats['with_facts']*100//max(1, self.stats['processed'])}%)")

def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description='Extract rich content from Wikipedia HTML in GCS')
    parser.add_argument('--folder', type=str,
                       default='scraped/wikipedia_breeds/20250917_162810',
                       help='GCS folder path')
    parser.add_argument('--test', action='store_true',
                       help='Test mode - process only first 5 breeds')

    args = parser.parse_args()

    extractor = RichContentExtractor(gcs_folder=args.folder)
    extractor.process_all(test_mode=args.test)

if __name__ == "__main__":
    main()