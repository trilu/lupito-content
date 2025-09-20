#!/usr/bin/env python3
"""
Intelligent Web Search Scraper for Breed Completeness
Uses strategic web search to fill remaining data gaps with high-authority sources.
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
from urllib.parse import quote, urljoin

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class IntelligentWebSearchScraper:
    def __init__(self):
        """Initialize the intelligent web search scraper"""
        # Supabase setup
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

        # Load missing breeds data
        self.missing_breeds = self.load_missing_breeds_data()

        # High-authority sources for targeted scraping
        self.authority_sources = {
            'akc': {
                'base_url': 'https://www.akc.org/dog-breeds/',
                'url_pattern': '{breed_slug}/',
                'fields': ['good_with_children', 'good_with_pets', 'exercise_level', 'grooming_frequency'],
                'selectors': {
                    'good_with_children': ['.breed-trait-scores', '.family-friendly', '.children'],
                    'good_with_pets': ['.breed-trait-scores', '.dog-friendly', '.pets'],
                    'exercise_level': ['.breed-trait-scores', '.energy-level', '.exercise'],
                    'grooming_frequency': ['.breed-trait-scores', '.grooming', '.coat-care']
                }
            },
            'rover': {
                'base_url': 'https://www.rover.com/blog/dog-breeds/',
                'url_pattern': '{breed_slug}/',
                'fields': ['good_with_children', 'good_with_pets', 'grooming_frequency', 'personality_traits'],
                'selectors': {
                    'good_with_children': ['.trait-score', '.family', '.children'],
                    'good_with_pets': ['.trait-score', '.social', '.pets'],
                    'grooming_frequency': ['.trait-score', '.grooming', '.maintenance'],
                    'personality_traits': ['.personality', '.temperament', '.traits']
                }
            },
            'petmd': {
                'base_url': 'https://www.petmd.com/dog/breeds/',
                'url_pattern': '{breed_slug}',
                'fields': ['health_issues', 'training_tips', 'exercise_needs_detail'],
                'selectors': {
                    'health_issues': ['.health-conditions', '.common-health-issues', '.health'],
                    'training_tips': ['.training', '.trainability', '.intelligence'],
                    'exercise_needs_detail': ['.exercise-needs', '.activity-level', '.exercise']
                }
            },
            'dogtime': {
                'base_url': 'https://dogtime.com/dog-breeds/',
                'url_pattern': '{breed_slug}',
                'fields': ['good_with_children', 'good_with_pets', 'training_tips', 'exercise_level'],
                'selectors': {
                    'good_with_children': ['.vital-stats', '.family-friendly', '.kid-friendly'],
                    'good_with_pets': ['.vital-stats', '.dog-friendly', '.pet-friendly'],
                    'training_tips': ['.vital-stats', '.trainability', '.intelligence'],
                    'exercise_level': ['.vital-stats', '.energy-level', '.exercise-needs']
                }
            }
        }

        # Stats tracking
        self.stats = {
            'total_breeds_processed': 0,
            'successful_updates': 0,
            'fields_populated': 0,
            'source_success': {source: 0 for source in self.authority_sources.keys()},
            'field_success': {}
        }

    def load_missing_breeds_data(self) -> List[Dict[str, Any]]:
        """Load missing breeds data from our tracking system"""
        try:
            # Get the most critical breeds with missing high-value fields
            response = self.supabase.table('breeds_unified_api').select(
                'breed_slug, display_name, good_with_children, good_with_pets, '
                'grooming_frequency, exercise_level, health_issues, training_tips, '
                'exercise_needs_detail, personality_traits'
            ).execute()

            critical_breeds = []
            high_value_fields = ['good_with_children', 'good_with_pets', 'grooming_frequency', 'exercise_level']

            for breed in response.data:
                missing_high_value = []
                for field in high_value_fields:
                    value = breed.get(field)
                    if value is None or (isinstance(value, str) and value.strip() == ''):
                        missing_high_value.append(field)

                if missing_high_value:  # Has missing high-value fields
                    critical_breeds.append({
                        'breed_slug': breed['breed_slug'],
                        'display_name': breed['display_name'],
                        'missing_high_value_fields': missing_high_value,
                        'priority_score': len(missing_high_value)
                    })

            # Sort by priority (most missing fields first)
            critical_breeds.sort(key=lambda x: x['priority_score'], reverse=True)

            logger.info(f"Loaded {len(critical_breeds)} breeds with missing high-value fields")
            return critical_breeds[:100]  # Top 100 priority breeds

        except Exception as e:
            logger.error(f"Error loading missing breeds data: {e}")
            return []

    def normalize_breed_slug_for_source(self, breed_slug: str, source: str) -> str:
        """Normalize breed slug for different source URL patterns"""
        # Convert our slug format to source-specific format
        normalized = breed_slug.lower().replace('_', '-')

        # Source-specific adjustments
        if source == 'akc':
            # AKC uses specific patterns
            name_mappings = {
                'labrador-retriever': 'labrador-retriever',
                'golden-retriever': 'golden-retriever',
                'german-shepherd-dog': 'german-shepherd-dog',
                'french-bulldog': 'french-bulldog',
                'bulldog': 'bulldog',
                'poodle': 'poodle',
                'beagle': 'beagle',
                'rottweiler': 'rottweiler',
                'yorkshire-terrier': 'yorkshire-terrier',
                'dachshund': 'dachshund'
            }
            return name_mappings.get(normalized, normalized)

        elif source == 'rover':
            # Rover often uses simplified names
            return normalized.replace('-dog', '').replace('-terrier', '-terrier')

        return normalized

    def scrape_authority_source(self, source_name: str, breed_slug: str,
                               target_fields: List[str]) -> Optional[Dict[str, Any]]:
        """Scrape a specific authority source for breed data"""
        try:
            source_config = self.authority_sources[source_name]
            normalized_slug = self.normalize_breed_slug_for_source(breed_slug, source_name)
            url = source_config['base_url'] + source_config['url_pattern'].format(breed_slug=normalized_slug)

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                             '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            response = requests.get(url, headers=headers, timeout=15)

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                extracted_data = {}

                # Extract data for each target field
                for field in target_fields:
                    if field in source_config['fields']:
                        value = self.extract_field_from_source(soup, field, source_config, source_name)
                        if value:
                            extracted_data[field] = value

                if extracted_data:
                    self.stats['source_success'][source_name] += 1
                    logger.info(f"✓ {source_name.upper()}: {breed_slug} - found {list(extracted_data.keys())}")
                    return extracted_data

            logger.info(f"- {source_name.upper()}: {breed_slug} not found ({response.status_code})")
            return None

        except Exception as e:
            logger.error(f"Error scraping {source_name} for {breed_slug}: {e}")
            return None

    def extract_field_from_source(self, soup: BeautifulSoup, field: str,
                                 source_config: Dict[str, Any], source_name: str) -> Optional[Any]:
        """Extract specific field data from source HTML"""
        try:
            selectors = source_config['selectors'].get(field, [])

            for selector in selectors:
                elements = soup.select(selector)
                if elements:
                    text = ' '.join([elem.get_text().strip() for elem in elements])
                    if len(text) > 10:  # Meaningful content
                        return self.normalize_field_value(field, text, source_name)

            # Fallback: keyword search in text
            text = soup.get_text().lower()
            field_keywords = {
                'good_with_children': ['children', 'kids', 'family', 'child-friendly'],
                'good_with_pets': ['other dogs', 'pets', 'animals', 'dog-friendly'],
                'grooming_frequency': ['grooming', 'brushing', 'daily', 'weekly', 'maintenance'],
                'exercise_level': ['exercise', 'energy', 'activity', 'active', 'moderate'],
                'health_issues': ['health', 'conditions', 'problems', 'diseases'],
                'training_tips': ['training', 'intelligence', 'trainability', 'obedience']
            }

            keywords = field_keywords.get(field, [])
            for keyword in keywords:
                if keyword in text:
                    # Extract surrounding context
                    context = self.extract_context_around_keyword(soup.get_text(), keyword, 200)
                    if context and len(context) > 30:
                        return self.normalize_field_value(field, context, source_name)

            return None

        except Exception as e:
            logger.error(f"Error extracting {field} from {source_name}: {e}")
            return None

    def extract_context_around_keyword(self, text: str, keyword: str, context_length: int = 200) -> str:
        """Extract context around a keyword"""
        text_lower = text.lower()
        keyword_lower = keyword.lower()

        index = text_lower.find(keyword_lower)
        if index == -1:
            return ""

        start = max(0, index - context_length // 2)
        end = min(len(text), index + context_length // 2)

        context = text[start:end].strip()

        # Clean up the context
        sentences = context.split('.')
        if len(sentences) > 1:
            # Return the most relevant sentence
            for sentence in sentences:
                if keyword_lower in sentence.lower():
                    return sentence.strip() + "."

        return context

    def normalize_field_value(self, field: str, value: str, source_name: str) -> Any:
        """Normalize field values based on field type and source"""
        value = value.strip()

        if field in ['good_with_children', 'good_with_pets']:
            # Boolean fields - be more aggressive about extraction
            positive_indicators = ['excellent', 'great', 'good', 'friendly', 'suitable', 'yes', '4/5', '5/5', 'high', 'love', 'enjoys']
            negative_indicators = ['poor', 'not recommended', 'difficult', 'aggressive', 'no', '1/5', '2/5', 'low', 'caution', 'supervision']

            value_lower = value.lower()

            # Check for positive indicators first
            if any(indicator in value_lower for indicator in positive_indicators):
                return True
            elif any(indicator in value_lower for indicator in negative_indicators):
                return False
            else:
                # If unclear, don't update (return None)
                logger.info(f"  Unclear {field} value: {value[:100]}...")
                return None

        elif field == 'grooming_frequency':
            # Structured field
            value_lower = value.lower()
            if any(word in value_lower for word in ['daily', 'every day']):
                return 'daily'
            elif any(word in value_lower for word in ['weekly', 'once a week']):
                return 'weekly'
            elif any(word in value_lower for word in ['minimal', 'low maintenance']):
                return 'minimal'

        elif field == 'exercise_level':
            # Structured field
            value_lower = value.lower()
            if any(word in value_lower for word in ['high', 'very active', 'intensive']):
                return 'high'
            elif any(word in value_lower for word in ['moderate', 'regular']):
                return 'moderate'
            elif any(word in value_lower for word in ['low', 'minimal', 'light']):
                return 'low'

        # For text fields, return cleaned value
        if len(value) > 500:
            value = value[:500] + "..."

        return value

    def update_breed_with_authority_data(self, breed_slug: str, extracted_data: Dict[str, Any],
                                       target_fields: List[str]) -> bool:
        """Update breed with authority source data - only missing fields"""
        try:
            if not extracted_data:
                return False

            # Get existing data
            response = self.supabase.table('breeds_comprehensive_content').select(
                'id, good_with_children, good_with_pets, grooming_frequency, exercise_level, '
                'health_issues, training_tips, exercise_needs_detail, personality_traits'
            ).eq('breed_slug', breed_slug).execute()

            if not response.data:
                logger.warning(f"No existing record found for {breed_slug}")
                return False

            existing_record = response.data[0]
            update_data = {}

            # Only update fields that are missing and we have data for
            for field, new_value in extracted_data.items():
                if field in target_fields:
                    existing_value = existing_record.get(field)

                    is_missing = (
                        existing_value is None or
                        (isinstance(existing_value, str) and existing_value.strip() == '') or
                        (isinstance(existing_value, list) and len(existing_value) == 0)
                    )

                    if is_missing and new_value:
                        update_data[field] = new_value

            if not update_data:
                return False

            # Update database
            result = self.supabase.table('breeds_comprehensive_content').update(
                update_data
            ).eq('breed_slug', breed_slug).execute()

            if result.data:
                self.stats['successful_updates'] += 1
                self.stats['fields_populated'] += len(update_data)

                for field in update_data.keys():
                    self.stats['field_success'][field] = self.stats['field_success'].get(field, 0) + 1

                logger.info(f"✓ Updated {breed_slug} with: {', '.join(update_data.keys())}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error updating {breed_slug}: {e}")
            return False

    def process_intelligent_web_search(self, limit: Optional[int] = None):
        """Main method for intelligent web search"""
        logger.info("Starting intelligent web search for breed completeness...")

        breeds_to_process = self.missing_breeds
        if limit:
            breeds_to_process = breeds_to_process[:limit]

        self.stats['total_breeds_processed'] = len(breeds_to_process)

        for i, breed_info in enumerate(breeds_to_process, 1):
            breed_slug = breed_info['breed_slug']
            display_name = breed_info['display_name']
            target_fields = breed_info['missing_high_value_fields']

            logger.info(f"\n[{i}/{len(breeds_to_process)}] Processing {display_name}")
            logger.info(f"  Target fields: {', '.join(target_fields)}")

            # Try each authority source
            all_extracted_data = {}

            for source_name in self.authority_sources.keys():
                source_data = self.scrape_authority_source(source_name, breed_slug, target_fields)
                if source_data:
                    all_extracted_data.update(source_data)

            # Update database with all collected data
            if all_extracted_data:
                self.update_breed_with_authority_data(breed_slug, all_extracted_data, target_fields)
            else:
                logger.info(f"  - No authority data found for {display_name}")

            # Rate limiting
            time.sleep(3)

            # Progress update every 10 breeds
            if i % 10 == 0:
                self.log_progress()

        self.log_final_stats()

    def log_progress(self):
        """Log current progress"""
        logger.info(f"""
        Progress: {self.stats['successful_updates']}/{self.stats['total_breeds_processed']} breeds updated
        Fields populated: {self.stats['fields_populated']}
        Source success: {dict(self.stats['source_success'])}
        """)

    def log_final_stats(self):
        """Log final statistics"""
        logger.info(f"""
        ========================================
        INTELLIGENT WEB SEARCH COMPLETE
        ========================================
        Total breeds processed: {self.stats['total_breeds_processed']}
        Successful updates: {self.stats['successful_updates']}
        Fields populated: {self.stats['fields_populated']}

        Source Performance:
        {dict(self.stats['source_success'])}

        Field Success:
        {dict(self.stats['field_success'])}

        Success rate: {round((self.stats['successful_updates'] / max(1, self.stats['total_breeds_processed'])) * 100, 1)}%
        ========================================
        """)

if __name__ == "__main__":
    import sys

    # Allow limiting for testing
    limit = None
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])
        logger.info(f"Limiting to {limit} breeds for testing")

    scraper = IntelligentWebSearchScraper()

    if not scraper.missing_breeds:
        logger.error("No missing breeds data loaded. Exiting.")
        sys.exit(1)

    scraper.process_intelligent_web_search(limit=limit)