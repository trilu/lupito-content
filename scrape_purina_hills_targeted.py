#!/usr/bin/env python3
"""
Targeted Purina/Hills Breed Scraper
Only scrapes breeds that have missing fields targetable by these sources.
Uses the missing breeds tracking system to avoid unnecessary work.
"""

import os
import json
import time
import logging
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional
from supabase import create_client, Client
from dotenv import load_dotenv
from urllib.parse import urljoin, quote

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class PurinaHillsTargetedScraper:
    def __init__(self):
        """Initialize the targeted scraper"""
        # Supabase setup
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

        # ScrapingBee API key (optional)
        self.scrapingbee_key = os.getenv('SCRAPING_BEE')

        # Load target breeds from tracking system
        self.target_breeds = self.load_target_breeds()

        # Stats tracking
        self.stats = {
            'total_targets': len(self.target_breeds),
            'processed': 0,
            'successful_purina': 0,
            'successful_hills': 0,
            'fields_populated': 0,
            'breeds_updated': 0,
            'skipped_complete': 0
        }

        # URL patterns
        self.purina_base = "https://www.purina.com/dogs/dog-breeds/"
        self.hills_base = "https://www.hillspet.com/dog-care/dog-breeds/"

    def load_target_breeds(self) -> List[Dict[str, Any]]:
        """Load target breeds from the tracking system"""
        try:
            # Load Purina targets (Purina has better coverage)
            with open('target_breeds_purina.json', 'r') as f:
                purina_data = json.load(f)
                return purina_data['breeds'][:50]  # Limit for initial run

        except FileNotFoundError:
            logger.error("Target breeds file not found. Run generate_missing_breeds_report.py first.")
            return []

    def normalize_breed_name_for_url(self, breed_slug: str) -> str:
        """Convert breed slug to URL-friendly format"""
        # Most sites use the slug format already, but may need adjustments
        return breed_slug.replace('_', '-').lower()

    def scrape_purina_breed(self, breed_slug: str, target_fields: List[str]) -> Optional[Dict[str, Any]]:
        """Scrape breed data from Purina"""
        try:
            url_name = self.normalize_breed_name_for_url(breed_slug)
            url = f"{self.purina_base}{url_name}"

            # Try direct request first
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                return self.extract_purina_data(soup, target_fields)
            else:
                logger.info(f"Purina: {breed_slug} not found ({response.status_code})")
                return None

        except Exception as e:
            logger.error(f"Error scraping Purina for {breed_slug}: {e}")
            return None

    def scrape_hills_breed(self, breed_slug: str, target_fields: List[str]) -> Optional[Dict[str, Any]]:
        """Scrape breed data from Hill's Pet"""
        try:
            url_name = self.normalize_breed_name_for_url(breed_slug)
            url = f"{self.hills_base}{url_name}"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                return self.extract_hills_data(soup, target_fields)
            else:
                logger.info(f"Hills: {breed_slug} not found ({response.status_code})")
                return None

        except Exception as e:
            logger.error(f"Error scraping Hills for {breed_slug}: {e}")
            return None

    def extract_purina_data(self, soup: BeautifulSoup, target_fields: List[str]) -> Dict[str, Any]:
        """Extract breed data from Purina page"""
        extracted_data = {}

        # Exercise needs
        if 'exercise_needs_detail' in target_fields:
            exercise_text = self.find_text_by_keywords(
                soup, ['exercise', 'activity', 'energy', 'physical', 'daily walks']
            )
            if exercise_text:
                extracted_data['exercise_needs_detail'] = exercise_text

        # Training information
        if 'training_tips' in target_fields:
            training_text = self.find_text_by_keywords(
                soup, ['training', 'trainability', 'intelligence', 'obedience', 'learns']
            )
            if training_text:
                extracted_data['training_tips'] = training_text

        # Grooming needs
        if 'grooming_needs' in target_fields:
            grooming_text = self.find_text_by_keywords(
                soup, ['grooming', 'brushing', 'coat care', 'shedding', 'maintenance']
            )
            if grooming_text:
                extracted_data['grooming_needs'] = grooming_text

        # Temperament
        if 'temperament' in target_fields:
            temperament_text = self.find_text_by_keywords(
                soup, ['temperament', 'personality', 'nature', 'character', 'disposition']
            )
            if temperament_text:
                # Convert to PostgreSQL array format
                extracted_data['temperament'] = f"{{{temperament_text}}}"

        # Child and pet compatibility
        if 'good_with_children' in target_fields:
            child_text = self.find_text_by_keywords(
                soup, ['children', 'kids', 'family', 'child-friendly']
            )
            if child_text and any(word in child_text.lower() for word in ['good', 'great', 'excellent', 'friendly']):
                extracted_data['good_with_children'] = True
            elif child_text and any(word in child_text.lower() for word in ['not recommended', 'avoid', 'difficult']):
                extracted_data['good_with_children'] = False

        if 'good_with_pets' in target_fields:
            pet_text = self.find_text_by_keywords(
                soup, ['other dogs', 'pets', 'animals', 'social', 'dog-friendly']
            )
            if pet_text and any(word in pet_text.lower() for word in ['good', 'great', 'excellent', 'friendly']):
                extracted_data['good_with_pets'] = True
            elif pet_text and any(word in pet_text.lower() for word in ['not recommended', 'avoid', 'difficult']):
                extracted_data['good_with_pets'] = False

        return extracted_data

    def extract_hills_data(self, soup: BeautifulSoup, target_fields: List[str]) -> Dict[str, Any]:
        """Extract breed data from Hill's Pet page"""
        extracted_data = {}

        # Similar extraction logic for Hill's Pet
        if 'exercise_needs_detail' in target_fields:
            exercise_text = self.find_text_by_keywords(
                soup, ['exercise', 'activity', 'energy', 'physical needs']
            )
            if exercise_text:
                extracted_data['exercise_needs_detail'] = exercise_text

        if 'grooming_needs' in target_fields:
            grooming_text = self.find_text_by_keywords(
                soup, ['grooming', 'coat', 'brushing', 'care requirements']
            )
            if grooming_text:
                extracted_data['grooming_needs'] = grooming_text

        if 'temperament' in target_fields:
            temperament_text = self.find_text_by_keywords(
                soup, ['temperament', 'personality', 'behavior', 'traits']
            )
            if temperament_text:
                extracted_data['temperament'] = f"{{{temperament_text}}}"

        if 'health_issues' in target_fields:
            health_text = self.find_text_by_keywords(
                soup, ['health', 'conditions', 'issues', 'problems', 'concerns']
            )
            if health_text:
                extracted_data['health_issues'] = health_text

        return extracted_data

    def find_text_by_keywords(self, soup: BeautifulSoup, keywords: List[str]) -> Optional[str]:
        """Find text containing specific keywords"""
        all_text = soup.get_text()
        paragraphs = soup.find_all(['p', 'div', 'section'])

        for p in paragraphs:
            text = p.get_text().strip()
            if len(text) > 50:  # Meaningful content
                text_lower = text.lower()
                if any(keyword in text_lower for keyword in keywords):
                    # Return first relevant sentence
                    sentences = text.split('.')
                    for sentence in sentences:
                        if len(sentence.strip()) > 30:
                            sentence_lower = sentence.lower()
                            if any(keyword in sentence_lower for keyword in keywords):
                                return sentence.strip() + "."

        return None

    def update_database(self, breed_slug: str, extracted_data: Dict[str, Any],
                       target_fields: List[str]) -> bool:
        """Update database with extracted data - only missing fields"""
        try:
            if not extracted_data:
                return False

            # Get existing data to check what's actually missing
            response = self.supabase.table('breeds_comprehensive_content').select(
                'id, exercise_needs_detail, training_tips, grooming_needs, '
                'temperament, good_with_children, good_with_pets, health_issues'
            ).eq('breed_slug', breed_slug).execute()

            if not response.data:
                logger.warning(f"No existing record found for {breed_slug}")
                return False

            existing_record = response.data[0]
            update_data = {}

            # Only update fields that are actually missing and we have data for
            for field, new_value in extracted_data.items():
                if field in target_fields:
                    existing_value = existing_record.get(field)

                    # Check if field is truly missing
                    is_missing = (
                        existing_value is None or
                        (isinstance(existing_value, str) and existing_value.strip() == '') or
                        (isinstance(existing_value, list) and len(existing_value) == 0)
                    )

                    if is_missing and new_value:
                        update_data[field] = new_value

            if not update_data:
                logger.info(f"  No missing fields to update for {breed_slug}")
                self.stats['skipped_complete'] += 1
                return False

            # Update database
            result = self.supabase.table('breeds_comprehensive_content').update(
                update_data
            ).eq('breed_slug', breed_slug).execute()

            if result.data:
                self.stats['breeds_updated'] += 1
                self.stats['fields_populated'] += len(update_data)
                logger.info(f"✓ Updated {breed_slug} with: {', '.join(update_data.keys())}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error updating database for {breed_slug}: {e}")
            return False

    def process_targeted_breeds(self, limit: Optional[int] = None):
        """Process only breeds with missing targetable fields"""
        logger.info(f"Starting targeted Purina/Hills scraping for {self.stats['total_targets']} breeds")

        breeds_to_process = self.target_breeds
        if limit:
            breeds_to_process = breeds_to_process[:limit]

        for i, breed_info in enumerate(breeds_to_process, 1):
            breed_slug = breed_info['breed_slug']
            display_name = breed_info['display_name']
            target_fields = breed_info['target_fields']

            logger.info(f"\n[{i}/{len(breeds_to_process)}] Processing {display_name}")
            logger.info(f"  Target fields: {', '.join(target_fields)}")

            # Try Purina first
            purina_data = self.scrape_purina_breed(breed_slug, target_fields)
            if purina_data:
                self.stats['successful_purina'] += 1
                logger.info(f"  ✓ Purina data: {list(purina_data.keys())}")

            # Try Hills for additional data
            hills_data = self.scrape_hills_breed(breed_slug, target_fields)
            if hills_data:
                self.stats['successful_hills'] += 1
                logger.info(f"  ✓ Hills data: {list(hills_data.keys())}")

            # Merge data (Purina takes priority for conflicts)
            combined_data = {}
            if hills_data:
                combined_data.update(hills_data)
            if purina_data:
                combined_data.update(purina_data)

            # Update database
            if combined_data:
                self.update_database(breed_slug, combined_data, target_fields)
            else:
                logger.info(f"  - No data found for {display_name}")

            self.stats['processed'] += 1

            # Rate limiting
            time.sleep(2)

            # Progress update every 10 breeds
            if i % 10 == 0:
                self.log_progress()

        self.log_final_stats()

    def log_progress(self):
        """Log current progress"""
        logger.info(f"""
        Progress: {self.stats['processed']}/{self.stats['total_targets']}
        Breeds updated: {self.stats['breeds_updated']}
        Fields populated: {self.stats['fields_populated']}
        Purina success: {self.stats['successful_purina']}
        Hills success: {self.stats['successful_hills']}
        Skipped (complete): {self.stats['skipped_complete']}
        """)

    def log_final_stats(self):
        """Log final statistics"""
        logger.info(f"""
        ========================================
        PURINA/HILLS TARGETED SCRAPING COMPLETE
        ========================================
        Target breeds: {self.stats['total_targets']}
        Processed: {self.stats['processed']}
        Breeds updated: {self.stats['breeds_updated']}
        Fields populated: {self.stats['fields_populated']}

        Source Success Rates:
        - Purina: {self.stats['successful_purina']} breeds
        - Hills: {self.stats['successful_hills']} breeds

        Efficiency:
        - Skipped (already complete): {self.stats['skipped_complete']}
        - Update rate: {round((self.stats['breeds_updated'] / self.stats['processed']) * 100, 1)}%
        ========================================
        """)

if __name__ == "__main__":
    import sys

    # Allow limiting for testing
    limit = None
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])
        logger.info(f"Limiting to {limit} breeds for testing")

    scraper = PurinaHillsTargetedScraper()

    if not scraper.target_breeds:
        logger.error("No target breeds loaded. Exiting.")
        sys.exit(1)

    scraper.process_targeted_breeds(limit=limit)