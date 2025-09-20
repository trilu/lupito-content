#!/usr/bin/env python3
"""
Popular Breeds ScrapingBee Search - High Success Rate Strategy
Focuses on the top 100 most popular breeds where authority sources have the best coverage
Uses ScrapingBee for maximum success on blocked sources
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

class PopularBreedsScrapingBee:
    def __init__(self, limit: Optional[int] = None):
        """Initialize with focus on popular breeds for maximum success"""
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('popular_breeds_scrapingbee.log'),
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

        # Most popular dog breeds (high success rate on authority sites)
        self.popular_breeds = [
            'labrador-retriever', 'golden-retriever', 'german-shepherd', 'bulldog',
            'poodle', 'beagle', 'rottweiler', 'yorkshire-terrier', 'dachshund',
            'siberian-husky', 'boxer', 'boston-terrier', 'shih-tzu', 'pomeranian',
            'australian-shepherd', 'cavalier-king-charles-spaniel', 'french-bulldog',
            'border-collie', 'cocker-spaniel', 'great-dane', 'chihuahua',
            'german-shorthaired-pointer', 'mastiff', 'bernese-mountain-dog',
            'weimaraner', 'vizsla', 'newfoundland', 'rhodesian-ridgeback',
            'west-highland-white-terrier', 'bloodhound', 'irish-setter',
            'basset-hound', 'afghan-hound', 'whippet', 'saint-bernard',
            'akita', 'alaskan-malamute', 'dalmatian', 'english-springer-spaniel',
            'brittany', 'portuguese-water-dog', 'bichon-frise', 'havanese',
            'maltese', 'papillon', 'collie', 'shetland-sheepdog',
            'australian-cattle-dog', 'doberman-pinscher', 'great-pyrenees',
            'irish-wolfhound', 'standard-schnauzer', 'bull-terrier',
            'staffordshire-bull-terrier', 'american-staffordshire-terrier',
            'english-setter', 'gordon-setter', 'pointer', 'wire-fox-terrier',
            'smooth-fox-terrier', 'jack-russell-terrier', 'parson-russell-terrier',
            'cairn-terrier', 'scottish-terrier', 'airedale-terrier',
            'welsh-terrier', 'lakeland-terrier', 'bedlington-terrier',
            'skye-terrier', 'dandie-dinmont-terrier', 'border-terrier',
            'norfolk-terrier', 'norwich-terrier', 'australian-terrier',
            'silky-terrier', 'manchester-terrier', 'toy-manchester-terrier',
            'english-toy-spaniel', 'japanese-chin', 'pekingese', 'pug',
            'chinese-crested', 'xoloitzcuintli', 'italian-greyhound',
            'miniature-pinscher', 'toy-poodle', 'miniature-poodle',
            'standard-poodle', 'keeshond', 'finnish-spitz', 'chow-chow',
            'shar-pei', 'shiba-inu', 'basenji', 'pharaoh-hound',
            'ibizan-hound', 'norwegian-elkhound', 'black-and-tan-coonhound',
            'bluetick-coonhound', 'redbone-coonhound', 'american-foxhound',
            'english-foxhound', 'harrier', 'bearded-collie', 'old-english-sheepdog',
            'polish-lowland-sheepdog', 'belgian-malinois', 'belgian-tervuren',
            'belgian-sheepdog', 'bouvier-des-flandres', 'briard', 'german-pinscher',
            'giant-schnauzer', 'miniature-schnauzer', 'affenpinscher',
            'brussels-griffon', 'toy-fox-terrier', 'rat-terrier'
        ]

        # Critical fields we're targeting
        self.critical_fields = [
            'grooming_frequency',  # 7.7% - CRITICAL
            'good_with_children',  # 12.7% - CRITICAL
            'good_with_pets',      # 13.9% - CRITICAL
        ]

        # High-success sources for popular breeds
        self.sources = {
            'akc': {
                'base_url': 'https://www.akc.org/dog-breeds/',
                'fields': ['grooming_frequency', 'good_with_children', 'good_with_pets', 'exercise_level'],
                'requires_scrapingbee': False,  # AKC usually accessible
                'selectors': {
                    'grooming_frequency': [
                        '.breed-trait-grooming p', '.grooming-section p', '.care-grooming p',
                        '.breed-traits .grooming', 'div[data-trait="grooming"] p'
                    ],
                    'good_with_children': [
                        '.breed-trait-children p', '.family-section p', '.children-section p',
                        '.breed-traits .children', 'div[data-trait="children"] p'
                    ],
                    'good_with_pets': [
                        '.breed-trait-dogs p', '.other-dogs-section p', '.dogs-section p',
                        '.breed-traits .dogs', 'div[data-trait="dogs"] p'
                    ],
                    'exercise_level': [
                        '.breed-trait-energy p', '.energy-section p', '.exercise-section p',
                        '.breed-traits .energy', 'div[data-trait="energy"] p'
                    ]
                }
            },
            'dogtime': {
                'base_url': 'https://dogtime.com/dog-breeds/',
                'fields': ['good_with_children', 'good_with_pets', 'exercise_level', 'personality_traits'],
                'requires_scrapingbee': True,  # Often blocks
                'selectors': {
                    'good_with_children': [
                        '.characteristic-stars-block:contains("Kid-Friendly") .stars',
                        '.breed-characteristic:contains("Kid") .rating',
                        'div[data-characteristic="kid-friendly"] .stars'
                    ],
                    'good_with_pets': [
                        '.characteristic-stars-block:contains("Dog Friendly") .stars',
                        '.breed-characteristic:contains("Dog") .rating',
                        'div[data-characteristic="dog-friendly"] .stars'
                    ],
                    'exercise_level': [
                        '.characteristic-stars-block:contains("Energy Level") .stars',
                        '.breed-characteristic:contains("Energy") .rating',
                        'div[data-characteristic="energy"] .stars'
                    ],
                    'personality_traits': [
                        '.breed-overview p', '.temperament-section p', '.personality-overview p'
                    ]
                }
            },
            'hillspet': {
                'base_url': 'https://www.hillspet.com/dog-care/dog-breeds/',
                'fields': ['grooming_frequency', 'exercise_level', 'personality_traits'],
                'requires_scrapingbee': True,  # Blocks frequently
                'selectors': {
                    'grooming_frequency': [
                        '.breed-info .grooming p', '.care-section .grooming p',
                        'section[data-breed="grooming"] p'
                    ],
                    'exercise_level': [
                        '.breed-info .exercise p', '.activity-section .exercise p',
                        'section[data-breed="exercise"] p'
                    ],
                    'personality_traits': [
                        '.breed-info .personality p', '.temperament-section p',
                        'section[data-breed="personality"] p'
                    ]
                }
            },
            'rover': {
                'base_url': 'https://www.rover.com/blog/dog-breeds/',
                'fields': ['grooming_frequency', 'personality_traits', 'good_with_children'],
                'requires_scrapingbee': True,  # Heavy blocking
                'selectors': {
                    'grooming_frequency': [
                        '.breed-care .grooming-section p', '.grooming-needs p',
                        'section[data-section="grooming"] p'
                    ],
                    'personality_traits': [
                        '.breed-personality p', '.temperament-overview p',
                        'section[data-section="personality"] p'
                    ],
                    'good_with_children': [
                        '.breed-compatibility .children p', '.family-life p',
                        'section[data-section="family"] p'
                    ]
                }
            }
        }

        # Statistics
        self.stats = {
            'total_processed': 0,
            'total_updated': 0,
            'fields_populated': 0,
            'source_success': {source: 0 for source in self.sources.keys()},
            'field_success': {field: 0 for field in self.critical_fields},
            'critical_gaps_filled': 0,
            'scrapingbee_credits_used': 0,
            'popular_breed_hits': 0
        }

    def fetch_with_scrapingbee(self, url: str) -> Tuple[Optional[str], bool]:
        """Fetch using ScrapingBee with maximum protection settings"""
        try:
            # Maximum protection ScrapingBee parameters
            params = {
                'api_key': self.scrapingbee_api_key,
                'url': url,
                'render_js': 'true',
                'premium_proxy': 'true',
                'stealth_proxy': 'true',
                'country_code': 'us',
                'wait': '8000',  # Longer wait for complete loading
                'block_ads': 'true',
                'return_page_source': 'true',
                'device': 'desktop',
                'window_width': '1920',
                'window_height': '1080',
            }

            # Enhanced JavaScript scenario for maximum compatibility
            js_scenario = {
                "instructions": [
                    {"wait": 3000},
                    {"scroll": {"direction": "down", "amount": 800}},
                    {"wait": 2000},
                    {"scroll": {"direction": "up", "amount": 400}},
                    {"wait": 2000},
                    {"scroll": {"direction": "down", "amount": 400}},
                    {"wait": 1000}
                ]
            }
            params['js_scenario'] = json.dumps(js_scenario)

            response = requests.get(self.scrapingbee_endpoint, params=params, timeout=90)

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
        """Fetch using basic requests for sources that don't typically block"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)

            if response.status_code == 200:
                return response.text, True
            elif response.status_code == 403:
                self.logger.info(f"- Direct request blocked (403) for {url}")
                return None, False
            elif response.status_code == 404:
                self.logger.info(f"- Direct request not found (404) for {url}")
                return None, False
            else:
                self.logger.warning(f"- Direct request failed ({response.status_code}) for {url}")
                return None, False

        except Exception as e:
            self.logger.warning(f"Basic request failed for {url}: {e}")
            return None, False

    def smart_fetch(self, url: str, requires_scrapingbee: bool) -> Tuple[Optional[str], bool]:
        """Smart fetching strategy based on source characteristics"""
        if requires_scrapingbee:
            # Use ScrapingBee for known blocking sources
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
                breed_slug = breed['breed_slug']

                # Check if this is a popular breed
                is_popular = breed_slug in self.popular_breeds

                missing_fields = []
                for field in self.critical_fields:
                    value = breed.get(field)
                    if not value or value == '' or value == [] or value is None:
                        missing_fields.append(field)

                if missing_fields:
                    breed['missing_fields'] = missing_fields
                    breed['is_popular'] = is_popular
                    # Higher priority for popular breeds
                    breed['priority_score'] = len(missing_fields) * (3 if is_popular else 1)
                    popular_with_gaps.append(breed)

            # Sort by priority (popular breeds with more missing fields first)
            popular_with_gaps.sort(key=lambda x: x['priority_score'], reverse=True)

            # Limit if specified
            if self.limit:
                popular_with_gaps = popular_with_gaps[:self.limit]

            popular_count = sum(1 for breed in popular_with_gaps if breed['is_popular'])
            self.logger.info(f"Loaded {len(popular_with_gaps)} breeds with critical gaps")
            self.logger.info(f"Including {popular_count} popular breeds (higher success rate expected)")
            return popular_with_gaps

        except Exception as e:
            self.logger.error(f"Error loading breeds: {e}")
            return []

    def create_source_url(self, source: str, breed_slug: str) -> str:
        """Create source-specific URL for breed"""
        base_url = self.sources[source]['base_url']
        return f"{base_url}{breed_slug}"

    def extract_rating_from_stars(self, element) -> Optional[bool]:
        """Extract boolean rating from star rating systems"""
        try:
            # Look for filled stars, star counts, or rating text
            stars_text = element.get_text().strip()

            # Count filled stars (★) vs empty stars (☆)
            filled_stars = stars_text.count('★') + stars_text.count('⭐')
            total_stars = filled_stars + stars_text.count('☆')

            if total_stars >= 3:  # 5-star system
                return filled_stars >= 3  # 3+ stars = True
            elif total_stars >= 2:  # 3-star system
                return filled_stars >= 2  # 2+ stars = True

            # Look for rating numbers
            import re
            rating_match = re.search(r'(\d+(?:\.\d+)?)\s*/\s*(\d+)', stars_text)
            if rating_match:
                rating = float(rating_match.group(1))
                max_rating = float(rating_match.group(2))
                return rating >= (max_rating * 0.6)  # 60%+ = True

            # Look for class names indicating rating
            classes = ' '.join(element.get('class', []))
            if any(cls in classes for cls in ['high', 'good', 'excellent', 'star-4', 'star-5']):
                return True
            elif any(cls in classes for cls in ['low', 'poor', 'star-1', 'star-2']):
                return False

        except Exception:
            pass

        return None

    def extract_field_data(self, soup: BeautifulSoup, field: str, selectors: List[str]) -> Optional[str]:
        """Extract field data with special handling for rating systems"""
        for selector in selectors:
            try:
                elements = soup.select(selector)
                if elements:
                    for elem in elements:
                        # Special handling for star ratings
                        if 'stars' in selector or 'rating' in selector:
                            rating = self.extract_rating_from_stars(elem)
                            if rating is not None:
                                return 'good' if rating else 'poor'

                        # Regular text extraction
                        text = elem.get_text().strip()
                        if (len(text) > 10 and
                            len(text) < 800 and
                            not text.startswith('©') and
                            not any(word in text.lower() for word in
                                   ['advertisement', 'subscribe', 'cookie', 'privacy', 'terms'])):
                            return text
            except Exception:
                continue

        return None

    def normalize_field_value(self, field: str, value: str, source: str) -> Any:
        """Normalize extracted values to proper data types"""
        if not value or len(value.strip()) < 3:
            return None

        value_lower = value.lower()

        # Boolean fields
        if field in ['good_with_children', 'good_with_pets']:
            # Handle rating-based responses first
            if value_lower in ['good', 'excellent', 'high']:
                return True
            elif value_lower in ['poor', 'low', 'bad']:
                return False

            # Strong positive indicators
            positive_strong = [
                'excellent with', 'great with', 'wonderful with', 'loves children',
                'child-friendly', 'kid-friendly', 'gentle with children', 'very good with'
            ]

            # Negative indicators
            negative_indicators = [
                'not suitable', 'not recommended', 'not good', 'poor with',
                'aggressive toward', 'avoid', 'caution with', 'not appropriate'
            ]

            # Moderate positive indicators
            positive_moderate = [
                'good with', 'suitable for', 'appropriate for', 'compatible',
                'friendly', 'patient', 'generally good'
            ]

            if any(indicator in value_lower for indicator in positive_strong):
                return True
            elif any(indicator in value_lower for indicator in negative_indicators):
                return False
            elif any(indicator in value_lower for indicator in positive_moderate):
                return True
            else:
                self.logger.info(f"  Unclear {field} value from {source}: {value[:50]}...")
                return None

        # Grooming frequency
        elif field == 'grooming_frequency':
            if any(freq in value_lower for freq in ['daily', 'every day', 'once a day']):
                return 'daily'
            elif any(freq in value_lower for freq in ['weekly', 'once a week', '2-3 times']):
                return 'weekly'
            elif any(freq in value_lower for freq in ['minimal', 'rarely', 'low maintenance']):
                return 'minimal'
            else:
                return value.strip()[:200]

        # Text fields
        else:
            cleaned_value = value.strip()
            if len(cleaned_value) >= 10:
                return cleaned_value[:600]

        return None

    def scrape_source_data(self, source: str, breed_slug: str, display_name: str,
                          missing_fields: List[str]) -> Dict[str, Any]:
        """Scrape data from specific source using optimal strategy"""
        url = self.create_source_url(source, breed_slug)
        source_config = self.sources[source]
        extracted_data = {}

        # Use smart fetching based on source characteristics
        html_content, success = self.smart_fetch(url, source_config['requires_scrapingbee'])

        if not success:
            self.logger.info(f"- {source.upper()}: {breed_slug} failed to fetch")
            return {}

        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Extract data for targetable missing fields
            targetable_fields = [f for f in missing_fields if f in source_config['fields']]

            for field in targetable_fields:
                if field in source_config['selectors']:
                    field_data = self.extract_field_data(soup, field, source_config['selectors'][field])
                    if field_data:
                        normalized_value = self.normalize_field_value(field, field_data, source)
                        if normalized_value:
                            extracted_data[field] = normalized_value

            if extracted_data:
                found_fields = list(extracted_data.keys())
                self.logger.info(f"✓ {source.upper()}: {breed_slug} - found {found_fields}")
                self.stats['source_success'][source] += 1

                for field in found_fields:
                    self.stats['field_success'][field] += 1
                    self.stats['critical_gaps_filled'] += 1
            else:
                self.logger.info(f"- {source.upper()}: {breed_slug} no useful data found")

            return extracted_data

        except Exception as e:
            self.logger.error(f"Error processing {source} content for {breed_slug}: {e}")
            return {}

    def update_breed_database(self, breed_slug: str, extracted_data: Dict[str, Any]) -> bool:
        """Update breed in database with extracted data"""
        try:
            # Get existing record
            response = self.supabase.table('breeds_comprehensive_content').select(
                'id,' + ','.join(self.critical_fields)
            ).eq('breed_slug', breed_slug).execute()

            if not response.data:
                self.logger.warning(f"No existing record found for {breed_slug}")
                return False

            existing_record = response.data[0]

            # Only update truly missing fields
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
        """Process a single breed across relevant sources"""
        breed_slug = breed['breed_slug']
        display_name = breed['display_name']
        missing_fields = breed['missing_fields']
        is_popular = breed['is_popular']

        self.logger.info(f"\n[{self.stats['total_processed'] + 1}] Processing {display_name}")
        popularity_indicator = "🔥 POPULAR" if is_popular else "💎 RARE"
        self.logger.info(f"  {popularity_indicator} breed - Target fields: {', '.join(missing_fields)}")

        if is_popular:
            self.stats['popular_breed_hits'] += 1

        all_extracted_data = {}

        # Source priority based on breed popularity and field coverage
        source_priority = ['akc', 'dogtime', 'hillspet', 'rover']

        for source in source_priority:
            # Only process sources that can target the missing fields
            source_fields = [f for f in missing_fields if f in self.sources[source]['fields']]
            if not source_fields:
                continue

            # Skip if we already have all the fields this source provides
            needed_fields = [f for f in source_fields if f not in all_extracted_data]
            if not needed_fields:
                continue

            source_data = self.scrape_source_data(source, breed_slug, display_name, missing_fields)

            # Merge data with conflict resolution
            for field, value in source_data.items():
                if field not in all_extracted_data:
                    all_extracted_data[field] = value

            # Add delay between source requests
            time.sleep(4)

            # Break early if we found all critical fields
            if len(all_extracted_data) >= len(missing_fields):
                self.logger.info(f"  Complete data found - stopping source iteration")
                break

        # Update database if we found any data
        if all_extracted_data:
            success = self.update_breed_database(breed_slug, all_extracted_data)
            if success:
                self.stats['total_updated'] += 1
                return True
        else:
            self.logger.info(f"  - No useful data found for {display_name}")

        return False

    def run_popular_breeds_search(self):
        """Execute the popular breeds ScrapingBee search"""
        self.logger.info("Starting Popular Breeds ScrapingBee Search")
        self.logger.info("Strategy: Focus on popular breeds for maximum success rate")
        self.logger.info("Target: grooming_frequency (7.7%), good_with_children (12.7%), good_with_pets (13.9%)")

        # Load breeds prioritized by popularity and gaps
        breeds_to_process = self.load_popular_breeds_with_gaps()

        if not breeds_to_process:
            self.logger.error("No breeds to process")
            return

        self.logger.info(f"Processing {len(breeds_to_process)} breeds (popular breeds prioritized)")

        start_time = time.time()

        for i, breed in enumerate(breeds_to_process):
            self.stats['total_processed'] += 1

            try:
                self.process_breed(breed)

                # Progress update every 10 breeds
                if (i + 1) % 10 == 0:
                    self.logger.info(f"\n        Progress: {i + 1}/{len(breeds_to_process)}")
                    self.logger.info(f"        Breeds updated: {self.stats['total_updated']}")
                    self.logger.info(f"        Critical gaps filled: {self.stats['critical_gaps_filled']}")
                    self.logger.info(f"        Popular breed hits: {self.stats['popular_breed_hits']}")
                    self.logger.info(f"        ScrapingBee credits used: {self.stats['scrapingbee_credits_used']}")

                # Add delay between breeds
                time.sleep(5)

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
        """Generate final search report with success analysis"""
        self.logger.info(f"\n        ========================================")
        self.logger.info(f"        POPULAR BREEDS SCRAPINGBEE SEARCH COMPLETE")
        self.logger.info(f"        ========================================")
        self.logger.info(f"        Target breeds: {self.stats['total_processed']}")
        self.logger.info(f"        Successful updates: {self.stats['total_updated']}")
        self.logger.info(f"        Critical gaps filled: {self.stats['critical_gaps_filled']}")
        self.logger.info(f"        Popular breed hits: {self.stats['popular_breed_hits']}")
        self.logger.info(f"        Duration: {duration/60:.1f} minutes")
        self.logger.info(f"")
        self.logger.info(f"        ScrapingBee Usage:")
        self.logger.info(f"        - Credits used: {self.stats['scrapingbee_credits_used']}")
        self.logger.info(f"")
        self.logger.info(f"        Source Performance:")
        for source, count in self.stats['source_success'].items():
            self.logger.info(f"        - {source.upper()}: {count} breeds")
        self.logger.info(f"")
        self.logger.info(f"        Critical Field Success:")
        for field, count in self.stats['field_success'].items():
            self.logger.info(f"        - {field}: {count} breeds")
        self.logger.info(f"")
        success_rate = (self.stats['total_updated'] / self.stats['total_processed']) * 100 if self.stats['total_processed'] > 0 else 0
        popular_success_rate = (self.stats['total_updated'] / self.stats['popular_breed_hits']) * 100 if self.stats['popular_breed_hits'] > 0 else 0
        self.logger.info(f"        Overall success rate: {success_rate:.1f}%")
        self.logger.info(f"        Popular breed success rate: {popular_success_rate:.1f}%")
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

    scraper = PopularBreedsScrapingBee(limit=limit)
    scraper.run_popular_breeds_search()