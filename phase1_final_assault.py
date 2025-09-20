#!/usr/bin/env python3
"""
PHASE 1 FINAL ASSAULT - LAST CHANCE TO HIT 80% COMPLETENESS
Target: 70.4% → 80% by focusing on QUICK WIN fields (40-80% complete)
Strategy: Comprehensive scraping with detailed logging of all skips/failures
"""

import os
import json
import time
import logging
import requests
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import re
from bs4 import BeautifulSoup
from supabase import create_client, Client
from dotenv import load_dotenv
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from urllib.parse import quote_plus

# Load environment variables
load_dotenv()

class Phase1FinalAssault:
    def __init__(self, test_mode: bool = False):
        """Initialize the final assault system"""

        # Setup detailed logging
        log_format = '%(asctime)s - %(levelname)s - [%(funcName)s] - %(message)s'
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler('phase1_final_assault.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

        # Supabase setup
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Missing Supabase credentials")

        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

        # ScrapingBee setup
        self.scrapingbee_api_key = os.getenv('SCRAPING_BEE')
        if not self.scrapingbee_api_key:
            self.logger.warning("No ScrapingBee API key - will use direct requests only")

        self.test_mode = test_mode

        # Statistics tracking
        self.stats = {
            'breeds_processed': 0,
            'fields_filled': 0,
            'breeds_skipped': 0,
            'breeds_updated': 0,
            'field_success': {},
            'source_success': {},
            'skip_reasons': {}
        }

        # Lock for thread-safe stats updates
        self.stats_lock = threading.Lock()

        # QUICK WIN target fields (40-80% complete)
        self.target_fields = {
            'health_issues': {
                'current': 45.6,
                'missing': 317,
                'patterns': ['health issues', 'health problems', 'health concerns', 'common diseases']
            },
            'color_varieties': {
                'current': 47.0,
                'missing': 309,
                'patterns': ['color variations', 'coat colors', 'color patterns', 'colors available']
            },
            'grooming_frequency': {
                'current': 48.4,
                'missing': 301,
                'patterns': ['grooming frequency', 'how often to groom', 'grooming schedule', 'grooming needs']
            },
            'good_with_children': {
                'current': 49.9,
                'missing': 292,
                'patterns': ['good with children', 'child friendly', 'kids friendly', 'family dog']
            },
            'coat': {
                'current': 50.6,
                'missing': 288,
                'patterns': ['coat type', 'coat texture', 'fur type', 'hair type']
            },
            'grooming_needs': {
                'current': 53.5,
                'missing': 271,
                'patterns': ['grooming needs', 'grooming requirements', 'grooming care', 'grooming routine']
            },
            'colors': {
                'current': 54.5,
                'missing': 265,
                'patterns': ['colors', 'coat colors', 'color patterns']
            },
            'lifespan_min_years': {
                'current': 59.2,
                'missing': 238,
                'patterns': ['life expectancy', 'lifespan', 'life span', 'lives']
            },
            'lifespan_max_years': {
                'current': 59.2,
                'missing': 238,
                'patterns': ['life expectancy', 'lifespan', 'life span', 'lives']
            },
            'lifespan_avg_years': {
                'current': 59.2,
                'missing': 238,
                'patterns': ['life expectancy', 'lifespan', 'life span', 'lives']
            },
            'training_tips': {
                'current': 61.2,
                'missing': 226,
                'patterns': ['training tips', 'training advice', 'how to train', 'training methods']
            }
        }

        # Data sources with proven success
        self.sources = [
            {
                'name': 'akc',
                'url_template': 'https://www.akc.org/dog-breeds/{breed_slug}/',
                'requires_scrapingbee': True,
                'selectors': {
                    'health_issues': ['.breed-health', '.health-issues', 'h2:contains("Health") + p'],
                    'grooming_needs': ['.grooming-needs', '.breed-grooming', 'h2:contains("Grooming") + p'],
                    'good_with_children': ['.breed-traits', '.temperament', 'h2:contains("Children") + p'],
                    'training_tips': ['.training-section', 'h2:contains("Training") + p'],
                    'lifespan': ['.breed-lifespan', '.life-expectancy', 'dt:contains("Life") + dd']
                }
            },
            {
                'name': 'hillspet',
                'url_template': 'https://www.hillspet.com/dog-care/dog-breeds/{breed_slug}',
                'requires_scrapingbee': False,
                'selectors': {
                    'health_issues': ['.health-concerns', 'h2:contains("Health") + div'],
                    'grooming_frequency': ['.grooming-section', 'h3:contains("Grooming") + p'],
                    'coat': ['.coat-type', '.appearance-section'],
                    'colors': ['.breed-colors', '.appearance-section'],
                    'lifespan': ['.breed-stats', '.lifespan']
                }
            },
            {
                'name': 'petmd',
                'url_template': 'https://www.petmd.com/dog/breeds/{breed_slug}',
                'requires_scrapingbee': False,
                'selectors': {
                    'health_issues': ['#health', '.health-section'],
                    'grooming_needs': ['#grooming', '.grooming-section'],
                    'good_with_children': ['#temperament', '.family-friendly'],
                    'training_tips': ['#training', '.training-section'],
                    'colors': ['#appearance', '.colors-section']
                }
            },
            {
                'name': 'dogtime',
                'url_template': 'https://dogtime.com/dog-breeds/{breed_slug}',
                'requires_scrapingbee': False,
                'selectors': {
                    'health_issues': ['.health-issues', 'h2:contains("Health") + ul'],
                    'grooming_frequency': ['.grooming-needs'],
                    'good_with_children': ['.child-friendly', '.kid-friendly'],
                    'coat': ['.coat-characteristics'],
                    'training_tips': ['.training-tips', 'h2:contains("Training") + div']
                }
            }
        ]

    def log_breed_attempt(self, breed_slug: str, source: str, status: str, details: str = ""):
        """Comprehensive logging for each breed attempt"""
        log_entry = f"[BREED: {breed_slug}] [SOURCE: {source}] [STATUS: {status}]"
        if details:
            log_entry += f" [DETAILS: {details}]"

        if status == "SUCCESS":
            self.logger.info(log_entry)
        elif status == "SKIP":
            self.logger.warning(log_entry)
            with self.stats_lock:
                self.stats['skip_reasons'][details] = self.stats['skip_reasons'].get(details, 0) + 1
        else:
            self.logger.error(log_entry)

    def fetch_with_scrapingbee(self, url: str) -> Optional[str]:
        """Fetch URL using ScrapingBee for JavaScript-heavy sites"""
        if not self.scrapingbee_api_key:
            return None

        params = {
            'api_key': self.scrapingbee_api_key,
            'url': url,
            'render_js': 'true',
            'premium_proxy': 'true',
            'country_code': 'us',
            'wait': '3000'
        }

        try:
            response = requests.get(
                'https://app.scrapingbee.com/api/v1',
                params=params,
                timeout=30
            )

            if response.status_code == 200:
                return response.text
            else:
                self.logger.warning(f"ScrapingBee returned {response.status_code} for {url}")
                return None

        except Exception as e:
            self.logger.error(f"ScrapingBee error for {url}: {e}")
            return None

    def fetch_direct(self, url: str) -> Optional[str]:
        """Fetch URL directly with requests"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.text
            else:
                return None
        except Exception as e:
            self.logger.debug(f"Direct fetch failed for {url}: {e}")
            return None

    def extract_field_value(self, soup: BeautifulSoup, field: str, selectors: List[str]) -> Optional[Any]:
        """Extract field value using multiple selectors"""
        for selector in selectors:
            try:
                # Try CSS selector
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(strip=True)
                    if text and len(text) > 10:  # Ensure meaningful content
                        return self.parse_field_value(field, text)

                # Try text search with patterns
                if field in self.target_fields:
                    for pattern in self.target_fields[field]['patterns']:
                        # Case-insensitive search
                        pattern_element = soup.find(text=re.compile(pattern, re.I))
                        if pattern_element:
                            parent = pattern_element.parent
                            if parent:
                                text = parent.get_text(strip=True)
                                if text and len(text) > 10:
                                    return self.parse_field_value(field, text)

            except Exception as e:
                self.logger.debug(f"Selector {selector} failed: {e}")
                continue

        return None

    def parse_field_value(self, field: str, text: str) -> Any:
        """Parse extracted text into appropriate field value"""
        text = text.strip()

        # Special handling for different field types
        if field == 'good_with_children':
            text_lower = text.lower()
            if any(word in text_lower for word in ['excellent', 'great', 'good', 'yes']):
                return True
            elif any(word in text_lower for word in ['not good', 'poor', 'no', 'avoid']):
                return False
            else:
                return None

        elif field == 'grooming_frequency':
            text_lower = text.lower()
            if 'daily' in text_lower:
                return 'daily'
            elif 'weekly' in text_lower or 'week' in text_lower:
                return 'weekly'
            elif 'monthly' in text_lower or 'month' in text_lower:
                return 'monthly'
            elif 'occasional' in text_lower or 'rarely' in text_lower:
                return 'occasionally'
            else:
                return text[:100]  # Return first 100 chars as description

        elif field in ['lifespan_min_years', 'lifespan_max_years', 'lifespan_avg_years']:
            # Extract numbers from lifespan text
            numbers = re.findall(r'\d+', text)
            if numbers:
                numbers = [int(n) for n in numbers if 5 <= int(n) <= 20]  # Reasonable dog lifespan
                if numbers:
                    if field == 'lifespan_min_years':
                        return min(numbers)
                    elif field == 'lifespan_max_years':
                        return max(numbers)
                    else:  # avg
                        return sum(numbers) / len(numbers)
            return None

        elif field == 'colors' or field == 'color_varieties':
            # Extract color lists
            colors = []
            color_words = ['black', 'white', 'brown', 'red', 'blue', 'gray', 'grey',
                          'cream', 'fawn', 'brindle', 'sable', 'tan', 'gold', 'golden',
                          'liver', 'chocolate', 'merle', 'spotted', 'tricolor']
            text_lower = text.lower()
            for color in color_words:
                if color in text_lower:
                    colors.append(color)
            return colors if colors else [text[:50]]

        else:
            # For other text fields, return cleaned text
            return text[:500] if len(text) > 500 else text

    def scrape_breed(self, breed: Dict) -> Dict[str, Any]:
        """Scrape data for a single breed from multiple sources"""
        breed_slug = breed['breed_slug']
        breed_name = breed['display_name']

        self.log_breed_attempt(breed_slug, "START", "INFO", f"Processing {breed_name}")

        # Check what fields this breed is missing
        missing_fields = []
        for field in self.target_fields.keys():
            if not breed.get(field):
                missing_fields.append(field)

        if not missing_fields:
            self.log_breed_attempt(breed_slug, "COMPLETE", "SKIP", "All target fields already filled")
            return {}

        self.log_breed_attempt(breed_slug, "MISSING", "INFO", f"Missing fields: {', '.join(missing_fields)}")

        extracted_data = {}
        sources_tried = []

        # Try each source
        for source in self.sources:
            source_name = source['name']
            sources_tried.append(source_name)

            # Build URL
            url = source['url_template'].format(breed_slug=breed_slug)

            # Fetch content
            html = None
            if source['requires_scrapingbee']:
                html = self.fetch_with_scrapingbee(url)
            else:
                html = self.fetch_direct(url)
                if not html and self.scrapingbee_api_key:
                    # Fallback to ScrapingBee if direct fails
                    html = self.fetch_with_scrapingbee(url)

            if not html:
                self.log_breed_attempt(breed_slug, source_name, "SKIP", "Failed to fetch content")
                continue

            # Parse HTML
            soup = BeautifulSoup(html, 'html.parser')

            # Extract fields
            fields_found = []
            for field in missing_fields:
                if field in extracted_data:
                    continue  # Already found this field

                selectors = source['selectors'].get(field, [])
                if field.startswith('lifespan'):
                    selectors = source['selectors'].get('lifespan', [])

                value = self.extract_field_value(soup, field, selectors)
                if value:
                    extracted_data[field] = value
                    fields_found.append(field)

            if fields_found:
                self.log_breed_attempt(breed_slug, source_name, "SUCCESS",
                                     f"Found: {', '.join(fields_found)}")

                # Track source success
                with self.stats_lock:
                    self.stats['source_success'][source_name] = \
                        self.stats['source_success'].get(source_name, 0) + len(fields_found)
            else:
                self.log_breed_attempt(breed_slug, source_name, "SKIP", "No fields extracted")

            # Stop if we've found most fields
            if len(extracted_data) >= len(missing_fields) * 0.7:
                break

        # Log final results for this breed
        if extracted_data:
            self.log_breed_attempt(breed_slug, "FINAL", "SUCCESS",
                                 f"Extracted {len(extracted_data)} fields from {sources_tried}")
        else:
            self.log_breed_attempt(breed_slug, "FINAL", "SKIP",
                                 f"No data extracted after trying {sources_tried}")

        return extracted_data

    def update_breed_in_db(self, breed_slug: str, data: Dict) -> bool:
        """Update breed in breeds_comprehensive_content table"""
        if not data:
            return False

        try:
            # Check if breed exists
            existing = self.supabase.table('breeds_comprehensive_content')\
                .select('breed_slug')\
                .eq('breed_slug', breed_slug)\
                .execute()

            data['updated_at'] = datetime.now().isoformat()

            if existing.data:
                # Update existing
                result = self.supabase.table('breeds_comprehensive_content')\
                    .update(data)\
                    .eq('breed_slug', breed_slug)\
                    .execute()
            else:
                # Insert new
                data['breed_slug'] = breed_slug
                data['created_at'] = datetime.now().isoformat()
                result = self.supabase.table('breeds_comprehensive_content')\
                    .insert(data)\
                    .execute()

            return True

        except Exception as e:
            self.logger.error(f"Database error for {breed_slug}: {e}")
            return False

    def process_breed_batch(self, breeds: List[Dict]) -> None:
        """Process a batch of breeds in parallel"""
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(self.process_single_breed, breed): breed
                      for breed in breeds}

            for future in as_completed(futures):
                breed = futures[future]
                try:
                    future.result()
                except Exception as e:
                    self.logger.error(f"Error processing {breed['breed_slug']}: {e}")

    def process_single_breed(self, breed: Dict) -> None:
        """Process a single breed"""
        breed_slug = breed['breed_slug']

        # Scrape data
        extracted_data = self.scrape_breed(breed)

        # Update statistics
        with self.stats_lock:
            self.stats['breeds_processed'] += 1

            if extracted_data:
                self.stats['fields_filled'] += len(extracted_data)
                self.stats['breeds_updated'] += 1

                # Track field success
                for field in extracted_data.keys():
                    self.stats['field_success'][field] = \
                        self.stats['field_success'].get(field, 0) + 1

                # Save to database
                if self.update_breed_in_db(breed_slug, extracted_data):
                    self.logger.info(f"✓ Updated {breed_slug} with {len(extracted_data)} fields")
                else:
                    self.logger.error(f"✗ Failed to save {breed_slug}")
            else:
                self.stats['breeds_skipped'] += 1

        # Progress update every 10 breeds
        if self.stats['breeds_processed'] % 10 == 0:
            self.print_progress()

    def print_progress(self):
        """Print current progress"""
        print(f"\n{'='*60}")
        print(f"PROGRESS UPDATE - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*60}")
        print(f"Breeds processed: {self.stats['breeds_processed']}")
        print(f"Breeds updated: {self.stats['breeds_updated']}")
        print(f"Breeds skipped: {self.stats['breeds_skipped']}")
        print(f"Fields filled: {self.stats['fields_filled']}")

        if self.stats['field_success']:
            print("\nTop fields filled:")
            for field, count in sorted(self.stats['field_success'].items(),
                                      key=lambda x: x[1], reverse=True)[:5]:
                print(f"  - {field}: {count}")

        if self.stats['source_success']:
            print("\nSource effectiveness:")
            for source, count in sorted(self.stats['source_success'].items(),
                                       key=lambda x: x[1], reverse=True):
                print(f"  - {source}: {count} fields")

        print(f"{'='*60}\n")

    def run_test(self):
        """Run test with 5 diverse breeds"""
        print("\n" + "="*60)
        print("PHASE 1 FINAL ASSAULT - TEST MODE")
        print("Testing with 5 diverse breeds")
        print("="*60)

        test_breeds = [
            'golden-retriever',
            'shih-tzu',
            'basenji',
            'irish-wolfhound',
            'pug'
        ]

        # Fetch test breeds from database
        breeds_to_test = []
        for breed_slug in test_breeds:
            result = self.supabase.table('breeds_unified_api')\
                .select('*')\
                .eq('breed_slug', breed_slug)\
                .execute()

            if result.data:
                breeds_to_test.append(result.data[0])
                print(f"✓ Found breed: {breed_slug}")
            else:
                print(f"✗ Breed not found: {breed_slug}")

        if not breeds_to_test:
            print("No test breeds found!")
            return

        print(f"\nProcessing {len(breeds_to_test)} test breeds...\n")

        # Process test breeds
        for breed in breeds_to_test:
            self.process_single_breed(breed)

        # Print final test results
        self.print_final_results()

    def run_full_assault(self):
        """Run full assault on all breeds"""
        print("\n" + "="*60)
        print("PHASE 1 FINAL ASSAULT - FULL RUN")
        print("Target: 70.4% → 80% completeness")
        print("="*60)

        # Fetch all breeds from unified view
        print("Fetching all breeds...")
        result = self.supabase.table('breeds_unified_api')\
            .select('*')\
            .order('display_name')\
            .execute()

        if not result.data:
            print("Failed to fetch breeds!")
            return

        all_breeds = result.data
        print(f"Found {len(all_breeds)} total breeds")

        # Filter breeds that need updates
        breeds_to_process = []
        for breed in all_breeds:
            missing_any = False
            for field in self.target_fields.keys():
                if not breed.get(field):
                    missing_any = True
                    break

            if missing_any:
                breeds_to_process.append(breed)

        print(f"Found {len(breeds_to_process)} breeds missing target fields")
        print(f"Starting parallel processing with 10 workers...\n")

        # Process in batches of 50
        batch_size = 50
        for i in range(0, len(breeds_to_process), batch_size):
            batch = breeds_to_process[i:i+batch_size]
            print(f"\nProcessing batch {i//batch_size + 1}/{(len(breeds_to_process) + batch_size - 1)//batch_size}")
            self.process_breed_batch(batch)

        # Print final results
        self.print_final_results()

    def print_final_results(self):
        """Print final assault results"""
        print("\n" + "="*80)
        print("PHASE 1 FINAL ASSAULT - COMPLETE")
        print("="*80)
        print(f"Total breeds processed: {self.stats['breeds_processed']}")
        print(f"Breeds successfully updated: {self.stats['breeds_updated']}")
        print(f"Breeds skipped: {self.stats['breeds_skipped']}")
        print(f"Total fields filled: {self.stats['fields_filled']}")

        if self.stats['breeds_processed'] > 0:
            success_rate = (self.stats['breeds_updated'] / self.stats['breeds_processed']) * 100
            print(f"Success rate: {success_rate:.1f}%")

        if self.stats['fields_filled'] > 0:
            # Estimate completeness gain
            total_possible_fields = 583 * len(self.target_fields) * 51  # 51 total fields in view
            gain = (self.stats['fields_filled'] / total_possible_fields) * 100
            print(f"Estimated completeness gain: +{gain:.2f}%")

        print("\nField success breakdown:")
        for field, count in sorted(self.stats['field_success'].items(),
                                  key=lambda x: x[1], reverse=True):
            original_missing = self.target_fields[field]['missing']
            filled_pct = (count / original_missing) * 100 if original_missing > 0 else 0
            print(f"  {field:25s}: {count:3d} filled ({filled_pct:5.1f}% of missing)")

        print("\nSource effectiveness:")
        for source, count in sorted(self.stats['source_success'].items(),
                                   key=lambda x: x[1], reverse=True):
            print(f"  {source:15s}: {count:4d} fields extracted")

        if self.stats['skip_reasons']:
            print("\nTop skip reasons:")
            for reason, count in sorted(self.stats['skip_reasons'].items(),
                                       key=lambda x: x[1], reverse=True)[:5]:
                print(f"  {reason}: {count}")

        print("="*80)
        print("Check phase1_final_assault.log for detailed logs")
        print("="*80)


def main():
    """Main execution"""
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        print("Running in TEST MODE...")
        assault = Phase1FinalAssault(test_mode=True)
        assault.run_test()
    else:
        print("Running FULL ASSAULT...")
        response = input("This will process ALL breeds. Continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted.")
            return

        assault = Phase1FinalAssault(test_mode=False)
        assault.run_full_assault()


if __name__ == "__main__":
    main()