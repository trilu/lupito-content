#!/usr/bin/env python3
"""
Popular Breeds ScrapingBee Search - FIXED VERSION
High Success Rate Strategy with corrected ScrapingBee configuration
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import requests
from bs4 import BeautifulSoup
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class PopularBreedsScrapingBeeFix:
    def __init__(self, limit: Optional[int] = None):
        """Initialize with focus on popular breeds for maximum success"""
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('popular_breeds_scrapingbee_fixed.log'),
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
        self.limit = limit

        # ScrapingBee setup
        self.scrapingbee_api_key = os.getenv('SCRAPING_BEE')
        if not self.scrapingbee_api_key:
            raise ValueError("ScrapingBee API key required for this implementation")

        self.scrapingbee_endpoint = "https://app.scrapingbee.com/api/v1/"

        # Stats tracking
        self.stats = {
            'breeds_processed': 0,
            'breeds_updated': 0,
            'critical_gaps_filled': 0,
            'scrapingbee_credits_used': 0,
            'popular_breed_hits': 0
        }

        # Popular breeds list (most likely to have data on authority sites)
        self.popular_breeds = [
            'golden-retriever', 'labrador-retriever', 'german-shepherd',
            'french-bulldog', 'bulldog', 'poodle', 'beagle', 'rottweiler',
            'german-shorthaired-pointer', 'yorkshire-terrier', 'dachshund',
            'siberian-husky', 'great-dane', 'doberman-pinscher',
            'australian-shepherd', 'miniature-schnauzer', 'boxer',
            'border-collie', 'australian-cattle-dog', 'cocker-spaniel',
            'boston-terrier', 'pomeranian', 'shih-tzu', 'chihuahua',
            'brittany', 'english-springer-spaniel', 'mastiff',
            'cane-corso', 'weimaraner', 'bernese-mountain-dog'
        ]

        # Critical fields we're targeting
        self.critical_fields = [
            'grooming_frequency',  # 7.7% - CRITICAL
            'good_with_children',  # 12.7% - CRITICAL
            'good_with_pets',      # 13.9% - CRITICAL
        ]

        # Sources with optimized ScrapingBee approach
        self.sources = {
            'akc': {
                'base_url': 'https://www.akc.org/dog-breeds/',
                'fields': ['grooming_frequency', 'good_with_children', 'good_with_pets'],
                'requires_scrapingbee': False
            },
            'dogtime': {
                'base_url': 'https://dogtime.com/dog-breeds/',
                'fields': ['grooming_frequency', 'good_with_children', 'good_with_pets'],
                'requires_scrapingbee': True
            },
            'hillspet': {
                'base_url': 'https://www.hillspet.com/dog-care/dog-breeds/',
                'fields': ['grooming_frequency', 'good_with_children', 'good_with_pets'],
                'requires_scrapingbee': True
            },
            'rover': {
                'base_url': 'https://www.rover.com/blog/dog-breeds/',
                'fields': ['grooming_frequency', 'good_with_children', 'good_with_pets'],
                'requires_scrapingbee': True
            }
        }

    def fetch_with_scrapingbee(self, url: str) -> Tuple[Optional[str], bool]:
        """Fetch using ScrapingBee with CORRECTED and simplified configuration"""
        try:
            # Simplified ScrapingBee parameters - remove problematic js_scenario
            params = {
                'api_key': self.scrapingbee_api_key,
                'url': url,
                'render_js': 'true',
                'premium_proxy': 'true',
                'stealth_proxy': 'true',
                'country_code': 'us',
                'wait': '3000',  # Reduced wait time
                'block_ads': 'true',
                'return_page_source': 'true'
            }

            # NO JavaScript scenario - this was causing the 400 errors!

            response = requests.get(self.scrapingbee_endpoint, params=params, timeout=60)

            if response.status_code == 200:
                self.stats['scrapingbee_credits_used'] += 1
                self.logger.info(f"✓ ScrapingBee success for {url}")
                return response.text, True
            else:
                self.logger.warning(f"ScrapingBee failed ({response.status_code}) for {url}")
                return None, False

        except Exception as e:
            self.logger.error(f"ScrapingBee error for {url}: {e}")
            return None, False

    def fetch_with_basic_request(self, url: str) -> Tuple[Optional[str], bool]:
        """Try basic request first (free, fast)"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                return response.text, True
            else:
                return None, False

        except Exception as e:
            self.logger.debug(f"Basic request failed for {url}: {e}")
            return None, False

    def smart_fetch(self, url: str, requires_scrapingbee: bool) -> Tuple[Optional[str], bool]:
        """Smart fetching with optimized fallback strategy"""
        if requires_scrapingbee:
            # For known blocked sources, go straight to ScrapingBee
            return self.fetch_with_scrapingbee(url)
        else:
            # Try basic request first, fallback to ScrapingBee if blocked
            html_content, success = self.fetch_with_basic_request(url)
            if success:
                return html_content, True
            else:
                self.logger.info(f"Falling back to ScrapingBee for {url}")
                return self.fetch_with_scrapingbee(url)

    def load_popular_breeds_with_gaps(self) -> List[Dict[str, Any]]:
        """Load popular breeds that have missing critical fields"""
        if self.limit:
            self.logger.info(f"Limiting to {self.limit} breeds for testing")

        try:
            # Query breeds missing critical fields, prioritizing popular ones
            fields_to_select = ['breed_slug', 'display_name'] + self.critical_fields
            response = self.supabase.table('breeds_unified_api').select(
                ','.join(fields_to_select)
            ).execute()

            if not response.data:
                self.logger.error("No breeds found in database")
                return []

            # Filter for popular breeds with missing critical fields
            popular_with_gaps = []

            for breed in response.data:
                breed_slug = breed.get('breed_slug', '').lower()

                # Check if it's a popular breed
                if breed_slug in self.popular_breeds:
                    # Check if it has missing critical fields
                    missing_fields = []
                    for field in self.critical_fields:
                        value = breed.get(field)
                        if not value or value == '' or value == [] or value is None:
                            missing_fields.append(field)

                    if missing_fields:
                        breed['missing_fields'] = missing_fields
                        popular_with_gaps.append(breed)

            # Sort by number of missing fields (most gaps first) and then by popularity
            popular_with_gaps.sort(key=lambda x: (
                -len(x['missing_fields']),  # More missing fields first
                self.popular_breeds.index(x['breed_slug']) if x['breed_slug'] in self.popular_breeds else 999
            ))

            if self.limit:
                popular_with_gaps = popular_with_gaps[:self.limit]

            self.logger.info(f"Loaded {len(popular_with_gaps)} breeds with critical gaps")
            self.logger.info(f"Including {len([b for b in popular_with_gaps if b['breed_slug'] in self.popular_breeds])} popular breeds (higher success rate expected)")

            return popular_with_gaps

        except Exception as e:
            self.logger.error(f"Error loading breeds: {e}")
            return []

    def extract_akc_data(self, soup: BeautifulSoup, breed_name: str) -> Dict[str, Any]:
        """Extract data from AKC breed pages"""
        data = {}

        try:
            # AKC has breed characteristics section - look for compatibility info
            characteristics = soup.find_all('div', class_=['breed-trait', 'trait-level'])

            for char in characteristics:
                trait_name = char.get_text().lower()
                if 'good with children' in trait_name or 'family' in trait_name:
                    # Look for rating indicators
                    rating_elem = char.find_next(['span', 'div'], class_=['rating', 'stars', 'level'])
                    if rating_elem:
                        rating_text = rating_elem.get_text()
                        data['good_with_children'] = 'high' in rating_text.lower() or '4' in rating_text or '5' in rating_text

                if 'good with pets' in trait_name or 'other dogs' in trait_name:
                    rating_elem = char.find_next(['span', 'div'], class_=['rating', 'stars', 'level'])
                    if rating_elem:
                        rating_text = rating_elem.get_text()
                        data['good_with_pets'] = 'high' in rating_text.lower() or '4' in rating_text or '5' in rating_text

            # Look for grooming information
            grooming_section = soup.find('div', text=lambda x: x and 'grooming' in x.lower())
            if grooming_section:
                grooming_text = grooming_section.find_parent().get_text().lower()
                if 'daily' in grooming_text:
                    data['grooming_frequency'] = 'daily'
                elif 'weekly' in grooming_text:
                    data['grooming_frequency'] = 'weekly'
                elif 'minimal' in grooming_text or 'low' in grooming_text:
                    data['grooming_frequency'] = 'minimal'

        except Exception as e:
            self.logger.debug(f"AKC extraction error for {breed_name}: {e}")

        return data

    def process_breed(self, breed: Dict[str, Any]) -> bool:
        """Process a single breed through all sources"""
        breed_slug = breed['breed_slug']
        breed_name = breed['display_name']
        missing_fields = breed.get('missing_fields', self.critical_fields)

        self.stats['breeds_processed'] += 1

        # Track if this is a popular breed
        is_popular = breed_slug in self.popular_breeds
        if is_popular:
            self.stats['popular_breed_hits'] += 1

        self.logger.info(f"\n[{self.stats['breeds_processed']}] Processing {breed_name}")
        self.logger.info(f"  {'🔥 POPULAR' if is_popular else '📍 STANDARD'} breed - Target fields: {', '.join(missing_fields)}")

        extracted_data = {}

        # Try each source
        for source_name, source_config in self.sources.items():
            if not extracted_data:  # Only continue if we haven't found data yet
                url = source_config['base_url'] + breed_slug

                # Smart fetching based on source requirements
                html_content, success = self.smart_fetch(url, source_config['requires_scrapingbee'])

                if success and html_content:
                    soup = BeautifulSoup(html_content, 'html.parser')

                    # Extract data using source-specific method
                    if source_name == 'akc':
                        source_data = self.extract_akc_data(soup, breed_name)
                    else:
                        # For other sources, use generic extraction
                        source_data = self.extract_generic_data(soup, breed_name)

                    if source_data:
                        extracted_data.update(source_data)
                        self.logger.info(f"- {source_name.upper()}: {breed_slug} found {len(source_data)} fields")
                    else:
                        self.logger.info(f"- {source_name.upper()}: {breed_slug} no useful data found")
                else:
                    self.logger.info(f"- {source_name.upper()}: {breed_slug} failed to fetch")

                # Rate limiting
                time.sleep(3)

        # Update database if we found data
        if extracted_data:
            success = self.update_database(breed_slug, extracted_data)
            if success:
                self.stats['breeds_updated'] += 1
                self.stats['critical_gaps_filled'] += len(extracted_data)
                return True

        self.logger.info(f"  - No useful data found for {breed_name}")
        time.sleep(5)  # Longer delay when no data found
        return False

    def extract_generic_data(self, soup: BeautifulSoup, breed_name: str) -> Dict[str, Any]:
        """Generic data extraction for non-AKC sources"""
        data = {}
        text_content = soup.get_text().lower()

        # Look for children compatibility
        if any(phrase in text_content for phrase in ['good with children', 'great with kids', 'family friendly']):
            data['good_with_children'] = True
        elif any(phrase in text_content for phrase in ['not good with children', 'not suitable for children']):
            data['good_with_children'] = False

        # Look for pet compatibility
        if any(phrase in text_content for phrase in ['good with other dogs', 'good with pets', 'social with other animals']):
            data['good_with_pets'] = True
        elif any(phrase in text_content for phrase in ['not good with other dogs', 'aggressive with other pets']):
            data['good_with_pets'] = False

        # Look for grooming frequency
        if any(phrase in text_content for phrase in ['daily grooming', 'daily brushing']):
            data['grooming_frequency'] = 'daily'
        elif any(phrase in text_content for phrase in ['weekly grooming', 'weekly brushing']):
            data['grooming_frequency'] = 'weekly'
        elif any(phrase in text_content for phrase in ['minimal grooming', 'low maintenance']):
            data['grooming_frequency'] = 'minimal'

        return data

    def update_database(self, breed_slug: str, data: Dict[str, Any]) -> bool:
        """Update database with extracted data (only missing fields)"""
        try:
            # Get existing record to check what's missing
            existing = self.supabase.table('breeds_comprehensive_content').select(
                'id, ' + ', '.join(self.critical_fields)
            ).eq('breed_slug', breed_slug).execute()

            if existing.data:
                existing_record = existing.data[0]

                # Only update fields that are actually missing
                update_data = {}
                for field, new_value in data.items():
                    existing_value = existing_record.get(field)
                    if not existing_value or existing_value == '' or existing_value == []:
                        update_data[field] = new_value

                if update_data:
                    self.supabase.table('breeds_comprehensive_content').update(
                        update_data
                    ).eq('breed_slug', breed_slug).execute()

                    self.logger.info(f"✓ Updated {breed_slug}: {list(update_data.keys())}")
                    return True
                else:
                    self.logger.info(f"- {breed_slug}: No new data to update")
                    return False
            else:
                self.logger.warning(f"Breed {breed_slug} not found in database")
                return False

        except Exception as e:
            self.logger.error(f"Database update error for {breed_slug}: {e}")
            return False

    def run(self):
        """Execute the popular breeds ScrapingBee search"""
        self.logger.info("Starting Popular Breeds ScrapingBee Search - FIXED VERSION")
        self.logger.info("Strategy: Focus on popular breeds for maximum success rate")
        self.logger.info("Target: grooming_frequency (7.7%), good_with_children (12.7%), good_with_pets (13.9%)")
        if self.limit:
            self.logger.info(f"Limiting to {self.limit} breeds for testing")

        start_time = time.time()

        # Load breeds with gaps
        breeds_to_process = self.load_popular_breeds_with_gaps()

        if not breeds_to_process:
            self.logger.error("No breeds to process!")
            return

        self.logger.info(f"Processing {len(breeds_to_process)} breeds (popular breeds prioritized)")

        # Process each breed
        for i, breed in enumerate(breeds_to_process, 1):
            try:
                success = self.process_breed(breed)

                # Progress reporting every 10 breeds
                if i % 10 == 0:
                    self.logger.info(f"\n        Progress: {i}/{len(breeds_to_process)}")
                    self.logger.info(f"        Breeds updated: {self.stats['breeds_updated']}")
                    self.logger.info(f"        Critical gaps filled: {self.stats['critical_gaps_filled']}")
                    self.logger.info(f"        Popular breed hits: {self.stats['popular_breed_hits']}")
                    self.logger.info(f"        ScrapingBee credits used: {self.stats['scrapingbee_credits_used']}")

            except KeyboardInterrupt:
                self.logger.info("Process interrupted by user")
                break
            except Exception as e:
                self.logger.error(f"Error processing breed {breed.get('display_name', 'unknown')}: {e}")
                continue

        # Final summary
        duration = (time.time() - start_time) / 60
        self.logger.info(f"""
        ========================================
        POPULAR BREEDS SCRAPINGBEE SEARCH COMPLETE - FIXED
        ========================================
        Target breeds: {len(breeds_to_process)}
        Successful updates: {self.stats['breeds_updated']}
        Critical gaps filled: {self.stats['critical_gaps_filled']}
        Popular breed hits: {self.stats['popular_breed_hits']}
        Duration: {duration:.1f} minutes

        ScrapingBee Usage:
        - Credits used: {self.stats['scrapingbee_credits_used']}

        Source Performance:
        - AKC: {self.stats['breeds_updated']} breeds
        - Total success rate: {(self.stats['breeds_updated']/len(breeds_to_process)*100):.1f}%
        """)

if __name__ == "__main__":
    import sys

    # Get limit from command line argument
    limit = None
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            print("Invalid limit argument. Using default (no limit)")

    scraper = PopularBreedsScrapingBeeFix(limit=limit)
    scraper.run()