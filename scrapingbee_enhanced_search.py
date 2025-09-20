#!/usr/bin/env python3
"""
ScrapingBee Enhanced Search for Critical Gaps
Integrates proven anti-blocking techniques from Zooplus/AADF scrapers
Targets critical breed data gaps using ScrapingBee fallback
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
from urllib.parse import quote

# Load environment variables
load_dotenv()

class ScrapingBeeEnhancedSearch:
    def __init__(self, limit: Optional[int] = None):
        """Initialize with robust ScrapingBee integration"""
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('scrapingbee_enhanced_search.log'),
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

        # ScrapingBee setup (proven from previous implementations)
        self.scrapingbee_api_key = os.getenv('SCRAPING_BEE')
        if not self.scrapingbee_api_key:
            self.logger.warning("ScrapingBee API key not found - will use basic requests only")

        self.scrapingbee_endpoint = "https://app.scrapingbee.com/api/v1/"

        # Request session with enhanced headers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })

        # Priority targeting based on current completeness gaps
        self.critical_fields = [
            'grooming_frequency',  # 7.7% - CRITICAL
            'good_with_children',  # 12.7% - CRITICAL
            'good_with_pets',      # 13.9% - CRITICAL
            'exercise_level',      # 34.1% - HIGH
            'personality_traits'   # 39.5% - MEDIUM
        ]

        # Enhanced source configuration with ScrapingBee fallback
        self.sources = {
            'vetstreet': {
                'base_url': 'https://www.vetstreet.com/dogs/',
                'fields': ['grooming_frequency', 'good_with_children', 'good_with_pets'],
                'requires_js': False,
                'selectors': {
                    'grooming_frequency': [
                        '.grooming-section p', '.coat-care p', '.maintenance p',
                        'div[data-testid="grooming"] p', '.grooming-content p'
                    ],
                    'good_with_children': [
                        '.family-section p', '.children-section p', '.kids p',
                        'div[data-testid="family"] p', '.family-content p'
                    ],
                    'good_with_pets': [
                        '.pets-section p', '.other-pets p', '.compatibility p',
                        'div[data-testid="pets"] p', '.pet-content p'
                    ]
                }
            },
            'hillspet': {
                'base_url': 'https://www.hillspet.com/dog-care/dog-breeds/',
                'fields': ['grooming_frequency', 'exercise_level', 'personality_traits'],
                'requires_js': True,  # Hills often blocks
                'selectors': {
                    'grooming_frequency': [
                        '.grooming-section p', '.care-section p', '.grooming-info p'
                    ],
                    'exercise_level': [
                        '.exercise-section p', '.activity-section p', '.exercise-info p'
                    ],
                    'personality_traits': [
                        '.personality-section p', '.temperament-section p', '.traits-section p'
                    ]
                }
            },
            'embracepetinsurance': {
                'base_url': 'https://www.embracepetinsurance.com/dog-breeds/',
                'fields': ['good_with_children', 'good_with_pets', 'grooming_frequency'],
                'requires_js': True,  # Often blocks
                'selectors': {
                    'good_with_children': [
                        '.family-life p', '.children-section p', '.kids-friendly p'
                    ],
                    'good_with_pets': [
                        '.other-pets p', '.pet-compatibility p', '.social-section p'
                    ],
                    'grooming_frequency': [
                        '.grooming-needs p', '.coat-care p', '.maintenance-section p'
                    ]
                }
            },
            'dogtime': {
                'base_url': 'https://dogtime.com/dog-breeds/',
                'fields': ['good_with_children', 'good_with_pets', 'exercise_level', 'personality_traits'],
                'requires_js': False,
                'selectors': {
                    'good_with_children': [
                        '.trait-kid-friendly p', '.family-friendly p', '.children-rating p'
                    ],
                    'good_with_pets': [
                        '.trait-dog-friendly p', '.pet-friendly p', '.social-rating p'
                    ],
                    'exercise_level': [
                        '.trait-energy-level p', '.exercise-rating p', '.activity-level p'
                    ],
                    'personality_traits': [
                        '.trait-temperament p', '.personality-section p', '.breed-traits p'
                    ]
                }
            },
            'rover': {
                'base_url': 'https://www.rover.com/blog/dog-breeds/',
                'fields': ['grooming_frequency', 'personality_traits', 'good_with_children'],
                'requires_js': True,  # Rover blocks heavily
                'selectors': {
                    'grooming_frequency': [
                        '.grooming-section p', '.coat-maintenance p', '.grooming-needs p'
                    ],
                    'personality_traits': [
                        '.personality-section p', '.temperament-info p', '.breed-traits p'
                    ],
                    'good_with_children': [
                        '.family-section p', '.children-info p', '.kid-friendly p'
                    ]
                }
            }
        }

        # Cost tracking (following Zooplus pattern)
        self.scrapingbee_credits_used = 0
        self.total_requests = 0
        self.fallback_requests = 0

        # Statistics
        self.stats = {
            'total_processed': 0,
            'total_updated': 0,
            'fields_populated': 0,
            'source_success': {source: 0 for source in self.sources.keys()},
            'field_success': {field: 0 for field in self.critical_fields},
            'critical_gaps_filled': 0,
            'scrapingbee_successes': 0,
            'direct_successes': 0
        }

    def needs_javascript(self, html_content: str) -> bool:
        """Detect if page needs JavaScript rendering (from universal scraper)"""
        js_indicators = [
            'window.ReactDOM', 'ng-app', 'vue.js', 'data-reactroot',
            'window.angular', 'Loading...', 'Please enable JavaScript',
            'window.Vue', 'window.React', '__NUXT__', 'data-react-helmet'
        ]

        # Check for very small body content (likely JS-rendered)
        soup = BeautifulSoup(html_content, 'html.parser')
        body = soup.find('body')
        if body and len(body.get_text(strip=True)) < 200:
            return True

        # Check for JS indicators
        return any(indicator in html_content for indicator in js_indicators)

    def fetch_with_basic_request(self, url: str) -> Tuple[Optional[str], bool]:
        """Fetch using basic requests (free method)"""
        try:
            response = self.session.get(url, timeout=15)

            if response.status_code == 403:
                self.logger.info(f"- Direct request blocked (403) for {url}")
                return None, False
            elif response.status_code == 404:
                self.logger.info(f"- Direct request not found (404) for {url}")
                return None, False
            elif response.status_code != 200:
                self.logger.warning(f"- Direct request failed ({response.status_code}) for {url}")
                return None, False

            return response.text, True

        except Exception as e:
            self.logger.warning(f"Basic request failed for {url}: {e}")
            return None, False

    def fetch_with_scrapingbee(self, url: str, require_js: bool = False) -> Tuple[Optional[str], bool]:
        """Fetch using ScrapingBee with enhanced settings (from AADF/Zooplus success)"""
        if not self.scrapingbee_api_key:
            return None, False

        try:
            # Enhanced ScrapingBee parameters based on successful implementations
            params = {
                'api_key': self.scrapingbee_api_key,
                'url': url,
                'render_js': 'true' if require_js else 'false',
                'premium_proxy': 'true',
                'stealth_proxy': 'true',
                'country_code': 'us',
                'wait': '5000',
                'block_ads': 'true',
                'return_page_source': 'true',
                'device': 'desktop',
                'window_width': '1920',
                'window_height': '1080',
            }

            # Add JavaScript scenario for heavily protected sites
            if require_js:
                js_scenario = {
                    "instructions": [
                        {"wait": 3000},
                        {"scroll": {"direction": "down", "amount": 500}},
                        {"wait": 2000},
                        {"scroll": {"direction": "up", "amount": 200}},
                        {"wait": 1000}
                    ]
                }
                params['js_scenario'] = json.dumps(js_scenario)

            response = requests.get(self.scrapingbee_endpoint, params=params, timeout=60)

            if response.status_code == 200:
                self.scrapingbee_credits_used += 1
                self.stats['scrapingbee_successes'] += 1
                self.logger.info(f"✓ ScrapingBee success for {url}")
                return response.text, True
            else:
                self.logger.warning(f"ScrapingBee failed ({response.status_code}) for {url}")
                return None, False

        except Exception as e:
            self.logger.error(f"ScrapingBee error for {url}: {e}")
            return None, False

    def smart_fetch(self, url: str, source_requires_js: bool = False) -> Tuple[Optional[str], bool]:
        """Smart fetching with ScrapingBee fallback (following proven pattern)"""
        self.total_requests += 1

        # Try direct request first for sources that typically don't block
        if not source_requires_js:
            html_content, success = self.fetch_with_basic_request(url)
            if success:
                # Check if content looks complete or needs JS
                if not self.needs_javascript(html_content):
                    self.stats['direct_successes'] += 1
                    return html_content, True
                else:
                    self.logger.info(f"Content appears to need JS rendering for {url}")

        # Use ScrapingBee for JS-heavy sites or when direct fails
        self.fallback_requests += 1
        return self.fetch_with_scrapingbee(url, require_js=source_requires_js)

    def load_breeds_with_critical_gaps(self) -> List[Dict[str, Any]]:
        """Load breeds with the most critical gaps prioritized"""
        if self.limit:
            self.logger.info(f"Limiting to {self.limit} breeds for testing")

        try:
            # Query breeds missing critical fields
            fields_to_select = ['breed_slug', 'display_name'] + self.critical_fields

            response = self.supabase.table('breeds_unified_api').select(
                ','.join(fields_to_select)
            ).execute()

            if not response.data:
                self.logger.error("No breeds found in database")
                return []

            # Prioritize breeds by critical field gaps
            critical_breeds = []
            for breed in response.data:
                missing_fields = []
                critical_missing = 0

                for field in self.critical_fields:
                    value = breed.get(field)
                    if not value or value == '' or value == [] or value is None:
                        missing_fields.append(field)
                        # Weight critical fields higher
                        if field in ['grooming_frequency', 'good_with_children', 'good_with_pets']:
                            critical_missing += 3
                        elif field == 'exercise_level':
                            critical_missing += 2
                        else:
                            critical_missing += 1

                if missing_fields:
                    breed['missing_fields'] = missing_fields
                    breed['critical_score'] = critical_missing
                    critical_breeds.append(breed)

            # Sort by critical score (highest first)
            critical_breeds.sort(key=lambda x: x['critical_score'], reverse=True)

            # Limit if specified
            if self.limit:
                critical_breeds = critical_breeds[:self.limit]

            self.logger.info(f"Loaded {len(critical_breeds)} breeds with critical gaps")
            self.logger.info(f"Using ScrapingBee fallback for blocked sources")
            return critical_breeds

        except Exception as e:
            self.logger.error(f"Error loading breeds: {e}")
            return []

    def create_source_url(self, source: str, breed_slug: str) -> str:
        """Create source-specific URL for breed"""
        base_url = self.sources[source]['base_url']

        # Source-specific URL patterns
        if source == 'vetstreet':
            return f"{base_url}{breed_slug}"
        elif source == 'hillspet':
            return f"{base_url}{breed_slug}"
        elif source == 'embracepetinsurance':
            return f"{base_url}{breed_slug}"
        elif source == 'dogtime':
            return f"{base_url}{breed_slug}"
        elif source == 'rover':
            return f"{base_url}{breed_slug}/"

        return f"{base_url}{breed_slug}"

    def extract_field_data(self, soup: BeautifulSoup, field: str, selectors: List[str]) -> Optional[str]:
        """Extract field data using CSS selectors with enhanced text analysis"""
        for selector in selectors:
            try:
                elements = soup.select(selector)
                if elements:
                    for elem in elements:
                        text = elem.get_text().strip()
                        # Enhanced text filtering
                        if (len(text) > 15 and
                            len(text) < 1000 and  # Reasonable length
                            not text.startswith('©') and  # Avoid copyright
                            not any(word in text.lower() for word in
                                   ['advertisement', 'subscribe', 'cookie', 'privacy policy', 'terms of service']) and
                            not text.isdigit()):  # Avoid pure numbers
                            return text
            except Exception as e:
                continue

        return None

    def normalize_field_value(self, field: str, value: str, source: str) -> Any:
        """Enhanced value normalization with better heuristics"""
        if not value or len(value.strip()) < 5:
            return None

        value_lower = value.lower()

        # Boolean fields with improved detection
        if field in ['good_with_children', 'good_with_pets']:
            # Strong positive indicators
            positive_strong = [
                'excellent with', 'great with', 'wonderful with', 'fantastic with',
                'loves children', 'loves kids', 'child-friendly', 'kid-friendly',
                'gentle with children', 'patient with kids', 'protective of children',
                'highly compatible', 'very good with'
            ]

            # Moderate positive indicators
            positive_moderate = [
                'good with', 'fine with', 'suitable for', 'appropriate for',
                'well-suited', 'compatible', 'gentle', 'patient', 'friendly',
                'generally good', 'usually good'
            ]

            # Negative indicators
            negative_indicators = [
                'not suitable', 'not recommended', 'not good', 'poor with',
                'aggressive toward', 'not ideal', 'avoid', 'dangerous with',
                'not appropriate', 'too rough', 'may harm', 'caution with'
            ]

            # Check for strong positives first
            if any(indicator in value_lower for indicator in positive_strong):
                return True
            # Then negatives
            elif any(indicator in value_lower for indicator in negative_indicators):
                return False
            # Then moderate positives
            elif any(indicator in value_lower for indicator in positive_moderate):
                return True
            else:
                # If unclear, don't store but log for manual review
                self.logger.info(f"  Unclear {field} value from {source}: {value[:80]}...")
                return None

        # Grooming frequency with better detection
        elif field == 'grooming_frequency':
            if any(freq in value_lower for freq in ['daily', 'every day', 'once a day', 'daily brushing']):
                return 'daily'
            elif any(freq in value_lower for freq in ['weekly', 'once a week', 'few times a week', '2-3 times']):
                return 'weekly'
            elif any(freq in value_lower for freq in ['minimal', 'rarely', 'occasional', 'low maintenance', 'easy to groom']):
                return 'minimal'
            else:
                # Return cleaned text for potential manual processing
                return value.strip()[:300]

        # Exercise level
        elif field == 'exercise_level':
            if any(level in value_lower for level in ['high energy', 'very active', 'intense exercise', 'vigorous']):
                return 'high'
            elif any(level in value_lower for level in ['moderate', 'medium', 'average exercise', 'regular walks']):
                return 'moderate'
            elif any(level in value_lower for level in ['low energy', 'minimal exercise', 'light activity', 'calm']):
                return 'low'
            else:
                return value.strip()[:300]

        # Text fields
        else:
            cleaned_value = value.strip()
            if len(cleaned_value) >= 10:
                return cleaned_value[:800]  # Reasonable length limit

        return None

    def scrape_source_data(self, source: str, breed_slug: str, display_name: str,
                          missing_fields: List[str]) -> Dict[str, Any]:
        """Scrape data from specific source with ScrapingBee fallback"""
        url = self.create_source_url(source, breed_slug)
        source_config = self.sources[source]
        extracted_data = {}

        # Use smart fetching with ScrapingBee fallback
        html_content, success = self.smart_fetch(url, source_config.get('requires_js', False))

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
                    if field in ['grooming_frequency', 'good_with_children', 'good_with_pets']:
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
        """Process a single breed across all relevant sources"""
        breed_slug = breed['breed_slug']
        display_name = breed['display_name']
        missing_fields = breed['missing_fields']
        critical_score = breed['critical_score']

        self.logger.info(f"\n[{self.stats['total_processed'] + 1}] Processing {display_name}")
        self.logger.info(f"  Critical score: {critical_score}")
        self.logger.info(f"  Target fields: {', '.join(missing_fields)}")

        all_extracted_data = {}

        # Try sources in order of success probability and relevance
        source_priority = [
            'dogtime',      # Usually accessible, good coverage
            'vetstreet',    # Generally reliable for family info
            'hillspet',     # Good for care requirements (may need ScrapingBee)
            'embracepetinsurance',  # Good for compatibility (may need ScrapingBee)
            'rover'         # Often blocks (will need ScrapingBee)
        ]

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

            # Merge data with conflict resolution (first reliable source wins)
            for field, value in source_data.items():
                if field not in all_extracted_data:
                    all_extracted_data[field] = value

            # Add delay between source requests
            time.sleep(3)

            # Break early if we found all critical fields
            critical_found = sum(1 for f in ['grooming_frequency', 'good_with_children', 'good_with_pets']
                               if f in all_extracted_data)
            if critical_found >= 2 and len(all_extracted_data) >= len(missing_fields) * 0.6:
                self.logger.info(f"  Early completion - found sufficient critical data")
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

    def run_enhanced_search(self):
        """Execute the ScrapingBee enhanced search process"""
        self.logger.info("Starting ScrapingBee Enhanced Search for Critical Gaps")
        self.logger.info("Using proven anti-blocking techniques from Zooplus/AADF scrapers")
        self.logger.info("Target: grooming_frequency (7.7%), good_with_children (12.7%), good_with_pets (13.9%)")

        # Load breeds prioritized by critical gaps
        breeds_to_process = self.load_breeds_with_critical_gaps()

        if not breeds_to_process:
            self.logger.error("No breeds to process")
            return

        self.logger.info(f"Processing {len(breeds_to_process)} breeds with critical gaps")

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
                    self.logger.info(f"        Critical gaps filled: {self.stats['critical_gaps_filled']}")
                    self.logger.info(f"        ScrapingBee credits used: {self.scrapingbee_credits_used}")
                    self.logger.info(f"        Direct vs ScrapingBee: {self.stats['direct_successes']}/{self.stats['scrapingbee_successes']}")

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
        """Generate final search report with cost analysis"""
        self.logger.info(f"\n        ========================================")
        self.logger.info(f"        SCRAPINGBEE ENHANCED SEARCH COMPLETE")
        self.logger.info(f"        ========================================")
        self.logger.info(f"        Target breeds: {self.stats['total_processed']}")
        self.logger.info(f"        Successful updates: {self.stats['total_updated']}")
        self.logger.info(f"        Fields populated: {self.stats['fields_populated']}")
        self.logger.info(f"        Critical gaps filled: {self.stats['critical_gaps_filled']}")
        self.logger.info(f"        Duration: {duration/60:.1f} minutes")
        self.logger.info(f"")
        self.logger.info(f"        ScrapingBee Usage:")
        self.logger.info(f"        - Credits used: {self.scrapingbee_credits_used}")
        self.logger.info(f"        - Direct successes: {self.stats['direct_successes']}")
        self.logger.info(f"        - ScrapingBee successes: {self.stats['scrapingbee_successes']}")
        self.logger.info(f"        - Fallback rate: {(self.fallback_requests/self.total_requests)*100:.1f}%")
        self.logger.info(f"")
        self.logger.info(f"        Source Performance:")
        for source, count in self.stats['source_success'].items():
            self.logger.info(f"        - {source.title()}: {count} breeds")
        self.logger.info(f"")
        self.logger.info(f"        Critical Field Success:")
        for field, count in self.stats['field_success'].items():
            priority = "CRITICAL" if field in ['grooming_frequency', 'good_with_children', 'good_with_pets'] else "HIGH" if field == 'exercise_level' else "MEDIUM"
            self.logger.info(f"        - {field} ({priority}): {count} breeds")
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

    scraper = ScrapingBeeEnhancedSearch(limit=limit)
    scraper.run_enhanced_search()