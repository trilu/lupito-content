#!/usr/bin/env python3
"""
Targeted UK Kennel Club Breed Scraper
Only scrapes breeds that have missing fields targetable by UK Kennel Club.
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

class KennelClubUKTargetedScraper:
    def __init__(self):
        """Initialize the targeted scraper"""
        # Supabase setup
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

        # Load target breeds from tracking system
        self.target_breeds = self.load_target_breeds()

        # Stats tracking
        self.stats = {
            'total_targets': len(self.target_breeds),
            'processed': 0,
            'successful': 0,
            'fields_populated': 0,
            'breeds_updated': 0,
            'skipped_complete': 0
        }

        # UK Kennel Club base URL
        self.base_url = "https://www.thekennelclub.org.uk/search/breeds-a-to-z/"

    def load_target_breeds(self) -> List[Dict[str, Any]]:
        """Load target breeds from the tracking system"""
        try:
            with open('target_breeds_kennel_club_uk.json', 'r') as f:
                data = json.load(f)
                return data['breeds'][:30]  # Limit for initial run

        except FileNotFoundError:
            logger.error("Target breeds file not found. Run generate_missing_breeds_report.py first.")
            return []

    def normalize_breed_name_for_url(self, breed_slug: str) -> str:
        """Convert breed slug to UK Kennel Club URL format"""
        # UK Kennel Club uses specific formatting
        name = breed_slug.replace('-', ' ').title()

        # Handle special cases for UK Kennel Club
        name_mappings = {
            'German Shepherd Dog': 'German Shepherd',
            'Labrador Retriever': 'Labrador Retriever',
            'Golden Retriever': 'Golden Retriever',
            'Border Collie': 'Border Collie',
            'Yorkshire Terrier': 'Yorkshire Terrier',
            'Cocker Spaniel': 'Cocker Spaniel',
            'English Springer Spaniel': 'English Springer Spaniel',
            'Staffordshire Bull Terrier': 'Staffordshire Bull Terrier'
        }

        return name_mappings.get(name, name).lower().replace(' ', '-')

    def scrape_kennel_club_breed(self, breed_slug: str, target_fields: List[str]) -> Optional[Dict[str, Any]]:
        """Scrape breed data from UK Kennel Club"""
        try:
            url_name = self.normalize_breed_name_for_url(breed_slug)
            url = f"{self.base_url}{url_name}"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                             '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            response = requests.get(url, headers=headers, timeout=15)

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                return self.extract_kennel_club_data(soup, target_fields)
            else:
                logger.info(f"UK Kennel Club: {breed_slug} not found ({response.status_code})")
                return None

        except Exception as e:
            logger.error(f"Error scraping UK Kennel Club for {breed_slug}: {e}")
            return None

    def extract_kennel_club_data(self, soup: BeautifulSoup, target_fields: List[str]) -> Dict[str, Any]:
        """Extract breed data from UK Kennel Club page"""
        extracted_data = {}

        # Exercise level (UK Kennel Club has structured exercise requirements)
        if 'exercise_level' in target_fields:
            exercise_level = self.extract_exercise_level(soup)
            if exercise_level:
                extracted_data['exercise_level'] = exercise_level

        # Grooming frequency
        if 'grooming_frequency' in target_fields:
            grooming_freq = self.extract_grooming_frequency(soup)
            if grooming_freq:
                extracted_data['grooming_frequency'] = grooming_freq

        # Temperament
        if 'temperament' in target_fields:
            temperament_text = self.find_text_by_keywords(
                soup, ['temperament', 'personality', 'character', 'nature', 'disposition']
            )
            if temperament_text:
                extracted_data['temperament'] = f"{{{temperament_text}}}"

        # Health issues (UK Kennel Club has good health information)
        if 'health_issues' in target_fields:
            health_text = self.extract_health_information(soup)
            if health_text:
                extracted_data['health_issues'] = health_text

        return extracted_data

    def extract_exercise_level(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract exercise level from structured UK Kennel Club data"""
        # Look for exercise-related sections
        exercise_keywords = ['exercise', 'activity', 'energy', 'physical needs']

        # Check for structured data first
        for section in soup.find_all(['div', 'section'], class_=lambda x: x and 'exercise' in x.lower()):
            text = section.get_text().lower()
            if 'high' in text or 'very active' in text or 'lots of exercise' in text:
                return 'high'
            elif 'moderate' in text or 'regular' in text:
                return 'moderate'
            elif 'low' in text or 'minimal' in text or 'light' in text:
                return 'low'

        # Fallback to general text search
        text = soup.get_text().lower()
        if any(phrase in text for phrase in ['high energy', 'very active', 'intensive exercise']):
            return 'high'
        elif any(phrase in text for phrase in ['moderate exercise', 'regular walks']):
            return 'moderate'
        elif any(phrase in text for phrase in ['low exercise', 'minimal activity']):
            return 'low'

        return None

    def extract_grooming_frequency(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract grooming frequency from UK Kennel Club data"""
        # Look for grooming-related sections
        grooming_text = self.find_text_by_keywords(
            soup, ['grooming', 'brushing', 'coat care', 'maintenance']
        )

        if grooming_text:
            text_lower = grooming_text.lower()
            if any(phrase in text_lower for phrase in ['daily', 'every day', 'daily brushing']):
                return 'daily'
            elif any(phrase in text_lower for phrase in ['weekly', 'once a week', 'regular']):
                return 'weekly'
            elif any(phrase in text_lower for phrase in ['minimal', 'low maintenance', 'little grooming']):
                return 'minimal'

        return None

    def extract_health_information(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract health information from UK Kennel Club page"""
        # UK Kennel Club often has dedicated health sections
        health_sections = soup.find_all(['div', 'section'],
                                       text=lambda x: x and 'health' in x.lower())

        if health_sections:
            for section in health_sections:
                parent = section.find_parent()
                if parent:
                    health_text = parent.get_text().strip()
                    if len(health_text) > 50:
                        return health_text[:500]  # Limit length

        # Fallback to keyword search
        return self.find_text_by_keywords(
            soup, ['health', 'conditions', 'problems', 'issues', 'genetic', 'hereditary']
        )

    def find_text_by_keywords(self, soup: BeautifulSoup, keywords: List[str]) -> Optional[str]:
        """Find text containing specific keywords"""
        paragraphs = soup.find_all(['p', 'div', 'section'])

        for p in paragraphs:
            text = p.get_text().strip()
            if len(text) > 30:  # Meaningful content
                text_lower = text.lower()
                if any(keyword in text_lower for keyword in keywords):
                    # Return first relevant sentence
                    sentences = text.split('.')
                    for sentence in sentences:
                        if len(sentence.strip()) > 20:
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
                'id, exercise_level, grooming_frequency, temperament, health_issues'
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
        logger.info(f"Starting targeted UK Kennel Club scraping for {self.stats['total_targets']} breeds")

        breeds_to_process = self.target_breeds
        if limit:
            breeds_to_process = breeds_to_process[:limit]

        for i, breed_info in enumerate(breeds_to_process, 1):
            breed_slug = breed_info['breed_slug']
            display_name = breed_info['display_name']
            target_fields = breed_info['target_fields']

            logger.info(f"\n[{i}/{len(breeds_to_process)}] Processing {display_name}")
            logger.info(f"  Target fields: {', '.join(target_fields)}")

            # Scrape UK Kennel Club
            extracted_data = self.scrape_kennel_club_breed(breed_slug, target_fields)

            if extracted_data:
                self.stats['successful'] += 1
                logger.info(f"  ✓ UK Kennel Club data: {list(extracted_data.keys())}")
                self.update_database(breed_slug, extracted_data, target_fields)
            else:
                logger.info(f"  - No data found for {display_name}")

            self.stats['processed'] += 1

            # Rate limiting (respectful)
            time.sleep(3)

            # Progress update every 5 breeds
            if i % 5 == 0:
                self.log_progress()

        self.log_final_stats()

    def log_progress(self):
        """Log current progress"""
        logger.info(f"""
        Progress: {self.stats['processed']}/{self.stats['total_targets']}
        Breeds updated: {self.stats['breeds_updated']}
        Fields populated: {self.stats['fields_populated']}
        Success rate: {round((self.stats['successful'] / self.stats['processed']) * 100, 1)}%
        Skipped (complete): {self.stats['skipped_complete']}
        """)

    def log_final_stats(self):
        """Log final statistics"""
        logger.info(f"""
        ========================================
        UK KENNEL CLUB TARGETED SCRAPING COMPLETE
        ========================================
        Target breeds: {self.stats['total_targets']}
        Processed: {self.stats['processed']}
        Breeds updated: {self.stats['breeds_updated']}
        Fields populated: {self.stats['fields_populated']}
        Success rate: {round((self.stats['successful'] / self.stats['processed']) * 100, 1)}%

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

    scraper = KennelClubUKTargetedScraper()

    if not scraper.target_breeds:
        logger.error("No target breeds loaded. Exiting.")
        sys.exit(1)

    scraper.process_targeted_breeds(limit=limit)