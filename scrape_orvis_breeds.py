#!/usr/bin/env python3
"""
Orvis Dog Breed Encyclopedia Scraper
Uses ScrapingBee for JavaScript-heavy pages
Extracts exercise, grooming, training, and care information
"""

import os
import re
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import requests
from bs4 import BeautifulSoup
from supabase import create_client, Client
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class OrvisBreedScraper:
    def __init__(self):
        """Initialize the Orvis scraper"""
        # Supabase setup
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

        # ScrapingBee setup
        self.api_key = os.getenv('SCRAPING_BEE')
        if not self.api_key:
            raise ValueError("SCRAPING_BEE API key not found")

        # Orvis base URL
        self.base_url = 'https://www.orvis.com'

        # Stats tracking
        self.stats = {
            'total': 0,
            'scraped': 0,
            'updated': 0,
            'failed': 0,
            'exercise_extracted': 0,
            'grooming_extracted': 0,
            'training_extracted': 0,
            'api_credits_used': 0
        }

    def get_breed_urls(self) -> List[Dict[str, str]]:
        """Get list of breed URLs from Orvis main page"""
        url = f"{self.base_url}/dog-breeds.html"

        try:
            # First try without ScrapingBee
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
            else:
                # Fall back to ScrapingBee
                soup = self.fetch_with_scrapingbee(url)

            breed_links = []

            # Find breed links - Orvis uses specific patterns
            for link in soup.find_all('a', href=True):
                href = link['href']
                breed_name = link.get_text(strip=True)

                # Skip navigation and non-breed links
                if not breed_name or len(breed_name) < 3:
                    continue
                if any(skip in breed_name.lower() for skip in [
                    'help', 'selector', 'your', 'winner', 'shop', 'guide',
                    'about', 'contact', 'privacy', 'terms', 'cart', 'account'
                ]):
                    continue

                # Look for breed-specific patterns in URL
                # Orvis breed pages often have patterns like /affenpinscher.html
                if href.endswith('.html') and '/' in href:
                    # Extract potential breed name from URL
                    url_parts = href.rstrip('.html').split('/')
                    potential_breed = url_parts[-1]

                    # Validate it looks like a breed name
                    if potential_breed and not any(char.isdigit() for char in potential_breed):
                        if not href.startswith('http'):
                            href = self.base_url + href if not href.startswith('/') else self.base_url + href

                        # Use URL-based name if text name seems wrong
                        if len(breed_name) > 50 or ' ' not in breed_name:
                            breed_name = potential_breed.replace('-', ' ').title()

                        breed_links.append({
                            'name': breed_name,
                            'url': href,
                            'slug': self.create_breed_slug(breed_name)
                        })

            # Deduplicate
            seen = set()
            unique_breeds = []
            for breed in breed_links:
                if breed['url'] not in seen:
                    seen.add(breed['url'])
                    unique_breeds.append(breed)

            logger.info(f"Found {len(unique_breeds)} breed URLs on Orvis")
            return unique_breeds[:150]  # Orvis claims 150+ breeds

        except Exception as e:
            logger.error(f"Error getting breed URLs: {e}")
            # Return a curated list of popular breeds as fallback
            return self.get_fallback_breed_list()

    def get_fallback_breed_list(self) -> List[Dict[str, str]]:
        """Fallback list of popular breeds on Orvis"""
        breeds = [
            'labrador-retriever', 'golden-retriever', 'german-shepherd',
            'french-bulldog', 'bulldog', 'poodle', 'beagle', 'rottweiler',
            'german-shorthaired-pointer', 'yorkshire-terrier', 'dachshund',
            'boxer', 'siberian-husky', 'great-dane', 'pug', 'boston-terrier',
            'shih-tzu', 'pomeranian', 'havanese', 'brittany', 'cocker-spaniel',
            'maltese', 'cavalier-king-charles-spaniel', 'bernese-mountain-dog',
            'vizsla', 'weimaraner', 'english-springer-spaniel', 'pointer',
            'irish-setter', 'gordon-setter', 'chesapeake-bay-retriever'
        ]

        return [
            {
                'name': breed.replace('-', ' ').title(),
                'url': f"{self.base_url}/{breed}.html",
                'slug': breed
            }
            for breed in breeds
        ]

    def create_breed_slug(self, breed_name: str) -> str:
        """Create consistent breed slug"""
        slug = breed_name.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[\s_]+', '-', slug)
        slug = re.sub(r'-+', '-', slug)
        return slug.strip('-')

    def fetch_with_scrapingbee(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch page using ScrapingBee API"""
        params = {
            'api_key': self.api_key,
            'url': url,
            'render_js': 'true',
            'premium_proxy': 'true',
            'country_code': 'us',
            'wait': '2000',
            'block_ads': 'true'
        }

        try:
            logger.info(f"Fetching {url} with ScrapingBee...")
            response = requests.get(
                'https://app.scrapingbee.com/api/v1/',
                params=params,
                timeout=45
            )

            self.stats['api_credits_used'] += 1

            if response.status_code == 200:
                logger.info(f"  ✓ Success ({len(response.content)/1024:.1f} KB)")
                return BeautifulSoup(response.text, 'html.parser')
            else:
                logger.warning(f"  ✗ HTTP {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"ScrapingBee error: {e}")
            return None

    def extract_breed_data(self, soup: BeautifulSoup, breed_info: Dict) -> Dict[str, Any]:
        """Extract breed data from Orvis page"""
        data = {
            'breed_slug': breed_info['slug'],
            'source': 'orvis',
            'url': breed_info['url']
        }

        # Extract exercise requirements
        exercise_text = self.extract_text_by_keywords(soup, [
            'exercise', 'activity', 'energy', 'walk', 'physical',
            'running', 'active', 'athletic', 'stamina'
        ])
        if exercise_text:
            data['exercise_needs_detail'] = exercise_text[:500]
            data['exercise_level'] = self.determine_exercise_level(exercise_text)
            self.stats['exercise_extracted'] += 1

        # Extract grooming needs
        grooming_text = self.extract_text_by_keywords(soup, [
            'grooming', 'groom', 'brush', 'coat', 'shedding',
            'maintenance', 'bath', 'trim', 'hair'
        ])
        if grooming_text:
            data['grooming_needs'] = grooming_text[:500]
            data['grooming_frequency'] = self.determine_grooming_frequency(grooming_text)
            self.stats['grooming_extracted'] += 1

        # Extract training information
        training_text = self.extract_text_by_keywords(soup, [
            'training', 'train', 'obedience', 'trainable',
            'intelligent', 'learn', 'command', 'teachable'
        ])
        if training_text:
            data['training_tips'] = training_text[:500]
            self.stats['training_extracted'] += 1

        # Extract temperament for child/pet compatibility
        temperament_text = self.extract_text_by_keywords(soup, [
            'temperament', 'personality', 'behavior', 'nature',
            'disposition', 'character', 'attitude'
        ])

        if temperament_text:
            compatibility = self.extract_compatibility(temperament_text)
            data.update(compatibility)

        # Extract health information if available
        health_text = self.extract_text_by_keywords(soup, [
            'health', 'disease', 'condition', 'medical',
            'genetic', 'hereditary', 'common problems'
        ])
        if health_text:
            data['health_issues'] = health_text[:500]

        return data

    def extract_text_by_keywords(self, soup: BeautifulSoup, keywords: List[str],
                                 max_length: int = 3) -> Optional[str]:
        """Extract text containing specific keywords"""
        relevant_sentences = []

        # Search all paragraphs and divs with text
        for element in soup.find_all(['p', 'div', 'li']):
            text = element.get_text(strip=True)
            if not text or len(text) < 20:
                continue

            text_lower = text.lower()
            if any(keyword in text_lower for keyword in keywords):
                # Clean up the text
                text = re.sub(r'\s+', ' ', text)
                text = text.strip()

                # Extract sentences containing keywords
                sentences = text.split('.')
                for sent in sentences:
                    sent_lower = sent.lower()
                    if any(keyword in sent_lower for keyword in keywords):
                        sent = sent.strip()
                        if sent and len(sent) > 15:
                            relevant_sentences.append(sent)
                            if len(relevant_sentences) >= max_length:
                                break

                if len(relevant_sentences) >= max_length:
                    break

        if relevant_sentences:
            result = '. '.join(relevant_sentences)
            if not result.endswith('.'):
                result += '.'
            return result

        return None

    def determine_exercise_level(self, text: str) -> Optional[str]:
        """Determine exercise level from text"""
        text_lower = text.lower()

        if any(word in text_lower for word in ['high energy', 'very active', 'extensive', 'vigorous', 'athletic']):
            return 'high'
        elif any(word in text_lower for word in ['moderate', 'regular walk', 'average']):
            return 'moderate'
        elif any(word in text_lower for word in ['low energy', 'minimal', 'short walk', 'couch']):
            return 'low'

        return None

    def determine_grooming_frequency(self, text: str) -> Optional[str]:
        """Determine grooming frequency from text"""
        text_lower = text.lower()

        if any(word in text_lower for word in ['daily', 'every day', 'each day']):
            return 'daily'
        elif any(word in text_lower for word in ['weekly', 'once a week', 'every week']):
            return 'weekly'
        elif any(word in text_lower for word in ['monthly', 'once a month']):
            return 'monthly'
        elif any(word in text_lower for word in ['minimal', 'occasionally', 'rarely']):
            return 'minimal'

        return None

    def extract_compatibility(self, text: str) -> Dict[str, Optional[bool]]:
        """Extract child and pet compatibility from text"""
        result = {}
        text_lower = text.lower()

        # Child compatibility
        if 'good with children' in text_lower or 'great with kids' in text_lower or 'family-friendly' in text_lower:
            result['good_with_children'] = True
        elif 'not good with children' in text_lower or 'not suitable for families' in text_lower:
            result['good_with_children'] = False

        # Pet compatibility
        if 'good with other' in text_lower or 'gets along' in text_lower or 'friendly with pets' in text_lower:
            result['good_with_pets'] = True
        elif 'aggressive' in text_lower or 'not good with other' in text_lower:
            result['good_with_pets'] = False

        return result

    def update_database(self, breed_data: Dict[str, Any]) -> bool:
        """Update breed data in database - only missing fields"""
        breed_slug = breed_data['breed_slug']

        # Remove metadata fields
        potential_updates = {k: v for k, v in breed_data.items()
                           if k not in ['breed_slug', 'source', 'url'] and v is not None}

        if not potential_updates:
            return False

        try:
            # Get existing record with all relevant fields
            existing = self.supabase.table('breeds_comprehensive_content').select(
                'id, exercise_needs_detail, training_tips, grooming_needs, '
                'grooming_frequency, exercise_level, health_issues, '
                'good_with_children, good_with_pets'
            ).eq('breed_slug', breed_slug).execute()

            if existing.data:
                # Only update fields that are missing/null/empty
                existing_record = existing.data[0]
                update_data = {}

                for field, new_value in potential_updates.items():
                    existing_value = existing_record.get(field)
                    # Update if field is null, empty string, or doesn't exist
                    if not existing_value or existing_value.strip() == '':
                        update_data[field] = new_value

                if update_data:
                    result = self.supabase.table('breeds_comprehensive_content').update(
                        update_data
                    ).eq('breed_slug', breed_slug).execute()

                    # Log which fields were actually updated
                    updated_fields = list(update_data.keys())
                    skipped_fields = [f for f in potential_updates.keys() if f not in update_data]

                    if updated_fields:
                        logger.info(f"✓ Updated {breed_slug}: {', '.join(updated_fields)}")
                    if skipped_fields:
                        logger.info(f"- Skipped existing data for {breed_slug}: {', '.join(skipped_fields)}")

                    return bool(result.data)
                else:
                    logger.info(f"- All data already exists for {breed_slug}")
                    return False
            else:
                # Insert new record with all data
                potential_updates['breed_slug'] = breed_slug
                result = self.supabase.table('breeds_comprehensive_content').insert(
                    potential_updates
                ).execute()

                if result.data:
                    logger.info(f"✓ Created new record for {breed_slug}: {', '.join(potential_updates.keys())}")
                    return True

            return False

        except Exception as e:
            logger.error(f"Database update error for {breed_slug}: {e}")
            return False

    def scrape_breed(self, breed_info: Dict[str, str]) -> bool:
        """Scrape a single breed"""
        try:
            # First try direct request
            response = requests.get(breed_info['url'], timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
            else:
                # Fall back to ScrapingBee
                soup = self.fetch_with_scrapingbee(breed_info['url'])
                if not soup:
                    return False

            # Extract data
            breed_data = self.extract_breed_data(soup, breed_info)

            # Update database if we found data (update_database now handles its own logging)
            if len(breed_data) > 3:  # More than just slug, source, url
                if self.update_database(breed_data):
                    self.stats['updated'] += 1
                    return True

            logger.info(f"- No new data found for {breed_info['slug']}")
            return False

        except Exception as e:
            logger.error(f"Error scraping {breed_info['slug']}: {e}")
            return False

    def scrape_all_breeds(self, limit: Optional[int] = None):
        """Scrape all Orvis breeds"""
        logger.info("Starting Orvis breed scraping...")

        # Get breed URLs
        breed_urls = self.get_breed_urls()

        if limit:
            breed_urls = breed_urls[:limit]

        self.stats['total'] = len(breed_urls)
        logger.info(f"Will scrape {self.stats['total']} breeds from Orvis")

        for i, breed_info in enumerate(breed_urls, 1):
            logger.info(f"\n[{i}/{self.stats['total']}] Scraping {breed_info['name']}...")

            if self.scrape_breed(breed_info):
                self.stats['scraped'] += 1
            else:
                self.stats['failed'] += 1

            # Rate limiting
            time.sleep(2)

            # Progress update every 10 breeds
            if i % 10 == 0:
                self.log_progress()

        self.log_final_stats()

    def log_progress(self):
        """Log current progress"""
        logger.info(f"""
        Progress: {self.stats['scraped']}/{self.stats['total']} breeds scraped
        Updated: {self.stats['updated']}
        - Exercise extracted: {self.stats['exercise_extracted']}
        - Grooming extracted: {self.stats['grooming_extracted']}
        - Training extracted: {self.stats['training_extracted']}
        ScrapingBee credits used: {self.stats['api_credits_used']}
        """)

    def log_final_stats(self):
        """Log final statistics"""
        logger.info(f"""
        ========================================
        ORVIS SCRAPING COMPLETE
        ========================================
        Total breeds: {self.stats['total']}
        Successfully scraped: {self.stats['scraped']}
        Database updated: {self.stats['updated']}
        Failed: {self.stats['failed']}

        Field Extraction:
        - Exercise: {self.stats['exercise_extracted']}
        - Grooming: {self.stats['grooming_extracted']}
        - Training: {self.stats['training_extracted']}

        ScrapingBee API credits used: {self.stats['api_credits_used']}
        ========================================
        """)

if __name__ == "__main__":
    import sys

    # Allow limiting for testing
    limit = None
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])
        logger.info(f"Limiting to {limit} breeds for testing")

    scraper = OrvisBreedScraper()
    scraper.scrape_all_breeds(limit=limit)