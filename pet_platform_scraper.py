#!/usr/bin/env python3
"""
Pet Platform Data Mining - Phase 2 of Web Search Implementation
Targets Rover.com and PetMD.com for remaining breed data gaps
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import requests
from bs4 import BeautifulSoup
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class PetPlatformScraper:
    def __init__(self, limit: Optional[int] = None):
        """Initialize the pet platform scraper"""
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('pet_platform_scraping.log'),
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

        # Target fields for pet platforms
        self.target_fields = [
            'grooming_frequency', 'personality_traits', 'good_with_children',
            'good_with_pets', 'health_issues', 'training_tips', 'exercise_needs_detail'
        ]

        # Platform configurations
        self.platforms = {
            'rover': {
                'base_url': 'https://www.rover.com/blog/dog-breeds/',
                'target_fields': ['grooming_frequency', 'personality_traits', 'good_with_children'],
                'selectors': {
                    'grooming_frequency': [
                        'div[data-testid="grooming-section"] p',
                        '.grooming-content p',
                        'h2:contains("Grooming") + p',
                        'h3:contains("grooming") + p'
                    ],
                    'personality_traits': [
                        'div[data-testid="personality-section"] p',
                        '.personality-content p',
                        'h2:contains("Personality") + p',
                        'h3:contains("temperament") + p'
                    ],
                    'good_with_children': [
                        'div[data-testid="family-section"] p',
                        '.family-content p',
                        'h2:contains("Family") + p',
                        'h3:contains("children") + p'
                    ]
                }
            },
            'petmd': {
                'base_url': 'https://www.petmd.com/dog/breeds/',
                'target_fields': ['health_issues', 'training_tips', 'exercise_needs_detail'],
                'selectors': {
                    'health_issues': [
                        '.health-section p',
                        '.common-health-issues p',
                        'h2:contains("Health") + p',
                        'h3:contains("health") + p'
                    ],
                    'training_tips': [
                        '.training-section p',
                        '.training-content p',
                        'h2:contains("Training") + p',
                        'h3:contains("training") + p'
                    ],
                    'exercise_needs_detail': [
                        '.exercise-section p',
                        '.exercise-content p',
                        'h2:contains("Exercise") + p',
                        'h3:contains("exercise") + p'
                    ]
                }
            }
        }

        # Statistics
        self.stats = {
            'total_processed': 0,
            'total_updated': 0,
            'fields_populated': 0,
            'platform_success': {platform: 0 for platform in self.platforms.keys()},
            'field_success': {field: 0 for field in self.target_fields}
        }

    def load_breeds_with_missing_fields(self) -> List[Dict[str, Any]]:
        """Load breeds that still have missing high-value fields after Phase 1"""
        if self.limit:
            self.logger.info(f"Limiting to {self.limit} breeds for testing")

        try:
            # Query breeds with missing fields that pet platforms can fill
            fields_to_select = ['breed_slug', 'display_name'] + self.target_fields

            response = self.supabase.table('breeds_unified_api').select(
                ','.join(fields_to_select)
            ).execute()

            if not response.data:
                self.logger.error("No breeds found in database")
                return []

            # Filter breeds with missing fields targetable by pet platforms
            missing_breeds = []
            for breed in response.data:
                missing_fields = []
                for field in self.target_fields:
                    value = breed.get(field)
                    if not value or value == '' or value == [] or value is None:
                        missing_fields.append(field)

                if missing_fields:
                    breed['missing_fields'] = missing_fields
                    missing_breeds.append(breed)

            # Limit if specified
            if self.limit:
                missing_breeds = missing_breeds[:self.limit]

            self.logger.info(f"Loaded {len(missing_breeds)} breeds with missing pet platform targetable fields")
            return missing_breeds

        except Exception as e:
            self.logger.error(f"Error loading breeds: {e}")
            return []

    def create_breed_url(self, platform: str, breed_slug: str) -> str:
        """Create platform-specific URL for breed"""
        base_url = self.platforms[platform]['base_url']
        # Convert breed slug format for each platform
        if platform == 'rover':
            # Rover uses hyphens and may have different slug format
            return f"{base_url}{breed_slug}/"
        elif platform == 'petmd':
            # PetMD might use underscores or different format
            return f"{base_url}{breed_slug}"

        return f"{base_url}{breed_slug}"

    def scrape_platform_data(self, platform: str, breed_slug: str, display_name: str,
                           missing_fields: List[str]) -> Dict[str, Any]:
        """Scrape data from specific platform"""
        url = self.create_breed_url(platform, breed_slug)
        platform_config = self.platforms[platform]
        extracted_data = {}

        try:
            # Make request with appropriate headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 404:
                self.logger.info(f"- {platform.upper()}: {breed_slug} not found (404)")
                return {}
            elif response.status_code != 200:
                self.logger.warning(f"- {platform.upper()}: {breed_slug} returned {response.status_code}")
                return {}

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract data for each missing field this platform can provide
            targetable_fields = [f for f in missing_fields if f in platform_config['target_fields']]

            for field in targetable_fields:
                if field in platform_config['selectors']:
                    field_data = self.extract_field_data(soup, field, platform_config['selectors'][field])
                    if field_data:
                        # Normalize the extracted data
                        normalized_value = self.normalize_field_value(field, field_data, platform)
                        if normalized_value:
                            extracted_data[field] = normalized_value

            if extracted_data:
                found_fields = list(extracted_data.keys())
                self.logger.info(f"✓ {platform.upper()}: {breed_slug} - found {found_fields}")
                self.stats['platform_success'][platform] += 1

                for field in found_fields:
                    self.stats['field_success'][field] += 1
            else:
                self.logger.info(f"- {platform.upper()}: {breed_slug} no useful data found")

            return extracted_data

        except Exception as e:
            self.logger.error(f"Error scraping {platform} for {breed_slug}: {e}")
            return {}

    def extract_field_data(self, soup: BeautifulSoup, field: str, selectors: List[str]) -> Optional[str]:
        """Extract field data using CSS selectors"""
        for selector in selectors:
            try:
                if ':contains(' in selector:
                    # Handle pseudo-selectors manually
                    parts = selector.split(':contains(')
                    if len(parts) == 2:
                        base_selector = parts[0]
                        search_text = parts[1].rstrip(')').strip('"\'')
                        elements = soup.select(base_selector)
                        for elem in elements:
                            if search_text.lower() in elem.get_text().lower():
                                # Get next sibling paragraph
                                next_p = elem.find_next_sibling('p')
                                if next_p:
                                    return next_p.get_text().strip()
                else:
                    elements = soup.select(selector)
                    if elements:
                        # Get text from first matching element
                        text = elements[0].get_text().strip()
                        if len(text) > 20:  # Ensure we have substantial content
                            return text
            except Exception as e:
                continue

        return None

    def normalize_field_value(self, field: str, value: str, platform: str) -> Any:
        """Normalize extracted values to proper data types"""
        if not value or len(value.strip()) < 10:
            return None

        value_lower = value.lower()

        # Boolean fields (good_with_children, good_with_pets)
        if field in ['good_with_children', 'good_with_pets']:
            positive_indicators = [
                'excellent', 'great', 'good', 'friendly', 'suitable', 'appropriate',
                'well-suited', 'compatible', 'gentle', 'patient', 'loving'
            ]
            negative_indicators = [
                'not suitable', 'not recommended', 'poor', 'difficult', 'aggressive',
                'not good', 'problematic', 'avoid'
            ]

            if any(indicator in value_lower for indicator in positive_indicators):
                return True
            elif any(indicator in value_lower for indicator in negative_indicators):
                return False
            else:
                # If unclear, log for manual review but don't store
                self.logger.info(f"  Unclear {field} value: {value[:100]}...")
                return None

        # Frequency field (grooming_frequency)
        elif field == 'grooming_frequency':
            if any(freq in value_lower for freq in ['daily', 'every day', 'once a day']):
                return 'daily'
            elif any(freq in value_lower for freq in ['weekly', 'once a week', 'few times a week']):
                return 'weekly'
            elif any(freq in value_lower for freq in ['minimal', 'rarely', 'occasional', 'low maintenance']):
                return 'minimal'
            else:
                # Return the cleaned text for manual review
                return value.strip()[:500]  # Limit length

        # Text fields (personality_traits, health_issues, training_tips, exercise_needs_detail)
        else:
            # Clean and return substantial text content
            cleaned_value = value.strip()
            if len(cleaned_value) >= 10:
                return cleaned_value[:1000]  # Limit to reasonable length

        return None

    def update_breed_database(self, breed_slug: str, extracted_data: Dict[str, Any]) -> bool:
        """Update breed in database with extracted data"""
        try:
            # Get existing record to check what's missing
            response = self.supabase.table('breeds_comprehensive_content').select(
                'id,' + ','.join(self.target_fields)
            ).eq('breed_slug', breed_slug).execute()

            if not response.data:
                self.logger.warning(f"No existing record found for {breed_slug}")
                return False

            existing_record = response.data[0]

            # Only update fields that are actually missing
            update_data = {}
            for field, new_value in extracted_data.items():
                existing_value = existing_record.get(field)
                if not existing_value or existing_value == '' or existing_value == [] or existing_value is None:
                    update_data[field] = new_value

            if not update_data:
                self.logger.info(f"  No missing fields to update for {breed_slug}")
                return False

            # Update the record
            update_response = self.supabase.table('breeds_comprehensive_content').update(
                update_data
            ).eq('breed_slug', breed_slug).execute()

            if update_response.data:
                updated_fields = list(update_data.keys())
                self.logger.info(f"✓ Updated {breed_slug} with: {', '.join(updated_fields)}")
                self.stats['fields_populated'] += len(updated_fields)
                return True
            else:
                self.logger.error(f"Failed to update {breed_slug}")
                return False

        except Exception as e:
            self.logger.error(f"Database error for {breed_slug}: {e}")
            return False

    def process_breed(self, breed: Dict[str, Any]) -> bool:
        """Process a single breed across all platforms"""
        breed_slug = breed['breed_slug']
        display_name = breed['display_name']
        missing_fields = breed['missing_fields']

        self.logger.info(f"\n[{self.stats['total_processed'] + 1}] Processing {display_name}")
        self.logger.info(f"  Target fields: {', '.join(missing_fields)}")

        all_extracted_data = {}

        # Try each platform
        for platform in self.platforms.keys():
            # Only process platforms that can target the missing fields
            platform_fields = [f for f in missing_fields if f in self.platforms[platform]['target_fields']]
            if not platform_fields:
                continue

            platform_data = self.scrape_platform_data(platform, breed_slug, display_name, missing_fields)

            # Merge data with conflict resolution (first wins for now)
            for field, value in platform_data.items():
                if field not in all_extracted_data:
                    all_extracted_data[field] = value

            # Add delay between platform requests
            time.sleep(2)

        # Update database if we found any data
        if all_extracted_data:
            success = self.update_breed_database(breed_slug, all_extracted_data)
            if success:
                self.stats['total_updated'] += 1
                return True
        else:
            self.logger.info(f"  - No useful data found for {display_name}")

        return False

    def run_pet_platform_mining(self):
        """Execute the complete pet platform data mining process"""
        self.logger.info("Starting Pet Platform Data Mining - Phase 2")
        self.logger.info("Target platforms: Rover.com, PetMD.com")

        # Load breeds with missing fields
        breeds_to_process = self.load_breeds_with_missing_fields()

        if not breeds_to_process:
            self.logger.error("No breeds to process")
            return

        self.logger.info(f"Processing {len(breeds_to_process)} breeds")

        start_time = time.time()

        for i, breed in enumerate(breeds_to_process):
            self.stats['total_processed'] += 1

            try:
                self.process_breed(breed)

                # Progress update every 10 breeds
                if (i + 1) % 10 == 0:
                    self.logger.info(f"\n        Progress: {i + 1}/{len(breeds_to_process)}")
                    self.logger.info(f"        Breeds updated: {self.stats['total_updated']}")
                    self.logger.info(f"        Fields populated: {self.stats['fields_populated']}")
                    self.logger.info(f"        Platform success: {self.stats['platform_success']}")

                # Add delay between breeds
                time.sleep(3)

            except KeyboardInterrupt:
                self.logger.info("\nStopping due to keyboard interrupt...")
                break
            except Exception as e:
                self.logger.error(f"Error processing breed {i+1}: {e}")
                continue

        # Final report
        duration = time.time() - start_time
        self.generate_final_report(duration)

    def generate_final_report(self, duration: float):
        """Generate final mining report"""
        self.logger.info(f"\n        ========================================")
        self.logger.info(f"        PET PLATFORM DATA MINING COMPLETE")
        self.logger.info(f"        ========================================")
        self.logger.info(f"        Target breeds: {self.stats['total_processed']}")
        self.logger.info(f"        Successful updates: {self.stats['total_updated']}")
        self.logger.info(f"        Fields populated: {self.stats['fields_populated']}")
        self.logger.info(f"        Duration: {duration/60:.1f} minutes")
        self.logger.info(f"")
        self.logger.info(f"        Platform Performance:")
        for platform, count in self.stats['platform_success'].items():
            self.logger.info(f"        - {platform.title()}: {count} breeds")
        self.logger.info(f"")
        self.logger.info(f"        Field Success:")
        for field, count in self.stats['field_success'].items():
            self.logger.info(f"        - {field}: {count} breeds")
        self.logger.info(f"")
        success_rate = (self.stats['total_updated'] / self.stats['total_processed']) * 100 if self.stats['total_processed'] > 0 else 0
        self.logger.info(f"        Success rate: {success_rate:.1f}%")
        self.logger.info(f"        ========================================")

if __name__ == "__main__":
    import sys

    # Get limit from command line argument
    limit = None
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            print("Invalid limit argument. Using no limit.")

    scraper = PetPlatformScraper(limit=limit)
    scraper.run_pet_platform_mining()