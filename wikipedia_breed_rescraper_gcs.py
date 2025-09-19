#!/usr/bin/env python3
"""
Wikipedia Breed Re-scraper with Full GCS Storage
Scrapes all breeds from Wikipedia and stores complete HTML in GCS
"""

import os
import sys
import re
import json
import time
import random
import hashlib
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from supabase import create_client
from google.cloud import storage

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WikipediaBreedRescraperGCS:
    """Re-scraper for Wikipedia breed pages with full GCS backup"""

    def __init__(self, test_mode=False, test_limit=5):
        """Initialize scraper with Supabase and GCS connections"""
        load_dotenv()

        # Supabase setup
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase = create_client(self.supabase_url, self.supabase_key)

        # GCS setup
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/sergiubiris/Desktop/lupito-content/secrets/gcp-sa.json'
        self.storage_client = storage.Client()
        self.bucket_name = os.getenv('GCS_BUCKET', 'lupito-content-raw-eu')
        self.bucket = self.storage_client.bucket(self.bucket_name)

        # Session setup
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

        # Configuration
        self.test_mode = test_mode
        self.test_limit = test_limit
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.gcs_folder = f"scraped/wikipedia_breeds/{self.timestamp}"

        # Statistics
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'updated': 0,
            'errors': []
        }

        logger.info(f"Wikipedia Breed Re-scraper initialized")
        logger.info(f"Test mode: {test_mode}, GCS folder: {self.gcs_folder}")

    def get_breeds_to_scrape(self):
        """Get list of breeds to scrape from breeds_published"""
        query = self.supabase.table('breeds_published').select(
            'breed_slug, display_name, aliases'
        )

        if self.test_mode:
            query = query.limit(self.test_limit)

        response = query.execute()
        return response.data

    def build_wikipedia_url(self, breed_name: str) -> str:
        """Build Wikipedia URL from breed name"""
        # Clean up the breed name
        wiki_name = breed_name.replace(' ', '_')
        # Remove parenthetical additions
        wiki_name = re.sub(r'\s*\([^)]*\)', '', wiki_name)
        return f"https://en.wikipedia.org/wiki/{wiki_name}"

    def scrape_breed_page(self, breed_slug: str, display_name: str, aliases: List[str]) -> Optional[Dict]:
        """Scrape a single breed from Wikipedia"""
        urls_to_try = []

        # Try display name first
        urls_to_try.append(self.build_wikipedia_url(display_name))

        # Try aliases
        if aliases:
            for alias in aliases:
                if alias and alias != display_name:
                    urls_to_try.append(self.build_wikipedia_url(alias))

        # Try variations
        if 'Dog' not in display_name:
            urls_to_try.append(self.build_wikipedia_url(f"{display_name} Dog"))

        for url in urls_to_try:
            try:
                logger.info(f"Trying URL: {url}")
                response = self.session.get(url, timeout=10)

                # Check if page exists
                if response.status_code == 200 and 'Wikipedia does not have an article' not in response.text:
                    soup = BeautifulSoup(response.text, 'html.parser')

                    # Extract data
                    extracted_data = self.extract_breed_data(soup)

                    return {
                        'breed_slug': breed_slug,
                        'display_name': display_name,
                        'wikipedia_url': url,
                        'html_content': response.text,
                        'extracted_data': extracted_data,
                        'scraped_at': datetime.now().isoformat()
                    }

            except Exception as e:
                logger.debug(f"Failed to fetch {url}: {str(e)}")
                continue

        return None

    def extract_breed_data(self, soup: BeautifulSoup) -> Dict:
        """Extract ALL structured data from Wikipedia page for comprehensive breed profile"""
        data = {}

        # Extract from infobox
        infobox = soup.find('table', {'class': 'infobox'})
        if infobox:
            data.update(self.parse_infobox(infobox))

        # Extract from article content - ALL sections
        data.update(self.extract_from_content(soup))

        # Extract additional rich content for user experience
        data.update(self.extract_history(soup))
        data.update(self.extract_personality_traits(soup))
        data.update(self.extract_care_requirements(soup))
        data.update(self.extract_fun_facts(soup))
        data.update(self.extract_breed_standards(soup))

        return data

    def parse_infobox(self, infobox) -> Dict:
        """Parse Wikipedia infobox for breed data"""
        data = {}

        for row in infobox.find_all('tr'):
            header = row.find('th')
            if header:
                label = header.get_text(strip=True).lower()
                value_cell = row.find('td')
                if value_cell:
                    value = value_cell.get_text(strip=True)

                    # Map to our fields
                    if 'weight' in label:
                        data['weight_text'] = value
                        weights = self.parse_weight(value)
                        if weights:
                            data.update(weights)

                    elif 'height' in label:
                        data['height_text'] = value
                        heights = self.parse_height(value)
                        if heights:
                            data.update(heights)

                    elif 'life' in label and 'span' in label:
                        data['lifespan_text'] = value
                        lifespan = self.parse_lifespan(value)
                        if lifespan:
                            data.update(lifespan)

                    elif 'coat' in label:
                        data['coat'] = value

                    elif 'color' in label or 'colour' in label:
                        data['colors'] = value

                    elif 'temperament' in label or 'traits' in label:
                        data['temperament'] = value

                    elif 'origin' in label or 'country' in label:
                        data['origin'] = value

        return data

    def extract_from_content(self, soup) -> Dict:
        """Extract data from article content"""
        data = {}

        # Look for sections
        for heading in soup.find_all(['h2', 'h3']):
            heading_text = heading.get_text(strip=True).lower()

            if 'health' in heading_text:
                # Extract health issues
                health_section = []
                next_elem = heading.find_next_sibling()
                while next_elem and next_elem.name not in ['h2', 'h3']:
                    if next_elem.name == 'p':
                        health_section.append(next_elem.get_text(strip=True))
                    next_elem = next_elem.find_next_sibling()

                if health_section:
                    data['health_issues'] = ' '.join(health_section[:3])  # First 3 paragraphs

            elif 'temperament' in heading_text or 'personality' in heading_text:
                # Extract temperament
                next_p = heading.find_next_sibling('p')
                if next_p:
                    data['temperament_detail'] = next_p.get_text(strip=True)

            elif 'exercise' in heading_text or 'activity' in heading_text:
                # Extract exercise needs
                next_p = heading.find_next_sibling('p')
                if next_p:
                    text = next_p.get_text(strip=True).lower()
                    if 'high' in text or 'very active' in text:
                        data['energy_level'] = 'high'
                    elif 'moderate' in text or 'medium' in text:
                        data['energy_level'] = 'moderate'
                    elif 'low' in text or 'minimal' in text:
                        data['energy_level'] = 'low'

        return data

    def parse_weight(self, text: str) -> Optional[Dict]:
        """Parse weight text to extract min/max/avg in kg"""
        data = {}

        # Look for patterns like "20-30 kg" or "44-66 lb"
        kg_pattern = r'(\d+(?:\.\d+)?)\s*[-–to]\s*(\d+(?:\.\d+)?)\s*kg'
        lb_pattern = r'(\d+(?:\.\d+)?)\s*[-–to]\s*(\d+(?:\.\d+)?)\s*(?:lb|pound)'

        kg_match = re.search(kg_pattern, text, re.IGNORECASE)
        lb_match = re.search(lb_pattern, text, re.IGNORECASE)

        if kg_match:
            min_weight = float(kg_match.group(1))
            max_weight = float(kg_match.group(2))
            data['weight_min_kg'] = min_weight
            data['weight_max_kg'] = max_weight
            data['weight_avg_kg'] = (min_weight + max_weight) / 2
        elif lb_match:
            min_weight_lb = float(lb_match.group(1))
            max_weight_lb = float(lb_match.group(2))
            data['weight_min_kg'] = round(min_weight_lb * 0.453592, 1)
            data['weight_max_kg'] = round(max_weight_lb * 0.453592, 1)
            data['weight_avg_kg'] = round((data['weight_min_kg'] + data['weight_max_kg']) / 2, 1)

        return data if data else None

    def parse_height(self, text: str) -> Optional[Dict]:
        """Parse height text to extract min/max in cm"""
        data = {}

        # Look for patterns
        cm_pattern = r'(\d+(?:\.\d+)?)\s*[-–to]\s*(\d+(?:\.\d+)?)\s*cm'
        inch_pattern = r'(\d+(?:\.\d+)?)\s*[-–to]\s*(\d+(?:\.\d+)?)\s*(?:in|inch)'

        cm_match = re.search(cm_pattern, text, re.IGNORECASE)
        inch_match = re.search(inch_pattern, text, re.IGNORECASE)

        if cm_match:
            data['height_min_cm'] = float(cm_match.group(1))
            data['height_max_cm'] = float(cm_match.group(2))
        elif inch_match:
            min_height_in = float(inch_match.group(1))
            max_height_in = float(inch_match.group(2))
            data['height_min_cm'] = round(min_height_in * 2.54, 1)
            data['height_max_cm'] = round(max_height_in * 2.54, 1)

        return data if data else None

    def parse_lifespan(self, text: str) -> Optional[Dict]:
        """Parse lifespan text"""
        data = {}

        # Look for patterns like "10-12 years"
        pattern = r'(\d+)\s*[-–to]\s*(\d+)\s*year'
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            data['lifespan_min_years'] = int(match.group(1))
            data['lifespan_max_years'] = int(match.group(2))
            data['lifespan_avg_years'] = (data['lifespan_min_years'] + data['lifespan_max_years']) / 2

        return data if data else None

    def extract_history(self, soup) -> Dict:
        """Extract breed history and origin story"""
        data = {}

        # Look for History section
        history_sections = ['history', 'origin', 'origins', 'background']
        for section_name in history_sections:
            for heading in soup.find_all(['h2', 'h3']):
                heading_text = heading.get_text(strip=True).lower()
                if section_name in heading_text:
                    paragraphs = []
                    next_elem = heading.find_next_sibling()
                    while next_elem and next_elem.name not in ['h2', 'h3'] and len(paragraphs) < 5:
                        if next_elem.name == 'p':
                            text = next_elem.get_text(strip=True)
                            if text and len(text) > 50:  # Skip very short paragraphs
                                paragraphs.append(text)
                        next_elem = next_elem.find_next_sibling()

                    if paragraphs:
                        data['history'] = ' '.join(paragraphs[:3])  # First 3 paragraphs
                        data['history_brief'] = paragraphs[0][:500] if paragraphs else ''  # First 500 chars for quick display
                        break

        # Extract notable facts from introduction
        intro = soup.find('div', {'id': 'mw-content-text'})
        if intro:
            first_p = intro.find('p', recursive=False)
            if first_p:
                data['introduction'] = first_p.get_text(strip=True)[:1000]

        return data

    def extract_personality_traits(self, soup) -> Dict:
        """Extract detailed personality and temperament information"""
        data = {}
        traits = []

        # Look for temperament/personality sections
        personality_sections = ['temperament', 'personality', 'characteristics', 'behavior', 'behaviour', 'traits']
        for section_name in personality_sections:
            for heading in soup.find_all(['h2', 'h3']):
                heading_text = heading.get_text(strip=True).lower()
                if section_name in heading_text:
                    content = []
                    next_elem = heading.find_next_sibling()
                    while next_elem and next_elem.name not in ['h2', 'h3']:
                        if next_elem.name == 'p':
                            content.append(next_elem.get_text(strip=True))
                        elif next_elem.name == 'ul':
                            # Extract list items as traits
                            for li in next_elem.find_all('li'):
                                traits.append(li.get_text(strip=True))
                        next_elem = next_elem.find_next_sibling()

                    if content:
                        data['personality_description'] = ' '.join(content[:3])

        if traits:
            data['personality_traits'] = traits[:10]  # Top 10 traits

        # Extract specific behavioral keywords
        full_text = soup.get_text().lower()

        # Check for family friendliness
        if 'good with children' in full_text or 'family dog' in full_text or 'gentle with kids' in full_text:
            data['good_with_children'] = True
        elif 'not recommended for families' in full_text or 'not good with children' in full_text:
            data['good_with_children'] = False

        # Check for other pet compatibility
        if 'good with other dogs' in full_text or 'gets along with cats' in full_text:
            data['good_with_pets'] = True
        elif 'dog aggressive' in full_text or 'high prey drive' in full_text:
            data['good_with_pets'] = False

        # Intelligence indicators
        intelligence_keywords = ['intelligent', 'smart', 'clever', 'quick learner', 'highly trainable']
        for keyword in intelligence_keywords:
            if keyword in full_text:
                data['intelligence_noted'] = True
                break

        return data

    def extract_care_requirements(self, soup) -> Dict:
        """Extract grooming, exercise, and care needs"""
        data = {}

        # Look for care-related sections
        care_sections = ['care', 'grooming', 'exercise', 'training', 'maintenance']
        for section_name in care_sections:
            for heading in soup.find_all(['h2', 'h3']):
                heading_text = heading.get_text().lower()
                if section_name in heading_text:
                    content = []
                    next_elem = heading.find_next_sibling()
                    while next_elem and next_elem.name not in ['h2', 'h3'] and len(content) < 3:
                        if next_elem.name == 'p':
                            content.append(next_elem.get_text(strip=True))
                        next_elem = next_elem.find_next_sibling()

                    if content:
                        if 'grooming' in heading_text:
                            data['grooming_needs'] = ' '.join(content)
                        elif 'exercise' in heading_text:
                            data['exercise_needs_detail'] = ' '.join(content)
                        elif 'training' in heading_text:
                            data['training_tips'] = ' '.join(content)
                        elif 'care' in heading_text:
                            data['general_care'] = ' '.join(content)

        # Extract specific care indicators from text
        full_text = soup.get_text().lower()

        # Grooming frequency
        if 'daily brushing' in full_text or 'daily grooming' in full_text:
            data['grooming_frequency'] = 'daily'
        elif 'weekly brushing' in full_text:
            data['grooming_frequency'] = 'weekly'
        elif 'minimal grooming' in full_text or 'low maintenance coat' in full_text:
            data['grooming_frequency'] = 'minimal'

        # Exercise intensity
        if 'high energy' in full_text or 'very active' in full_text or 'needs lots of exercise' in full_text:
            data['exercise_level'] = 'high'
        elif 'moderate exercise' in full_text or 'moderate activity' in full_text:
            data['exercise_level'] = 'moderate'
        elif 'low energy' in full_text or 'minimal exercise' in full_text:
            data['exercise_level'] = 'low'

        return data

    def extract_fun_facts(self, soup) -> Dict:
        """Extract interesting trivia and fun facts about the breed"""
        data = {}
        fun_facts = []

        # Look for trivia, popular culture, famous dogs sections
        trivia_sections = ['trivia', 'popular culture', 'famous', 'notable', 'in media', 'cultural impact']
        for section_name in trivia_sections:
            for heading in soup.find_all(['h2', 'h3']):
                heading_text = heading.get_text(strip=True).lower()
                if section_name in heading_text:
                    next_elem = heading.find_next_sibling()
                    while next_elem and next_elem.name not in ['h2', 'h3']:
                        if next_elem.name == 'p':
                            fun_facts.append(next_elem.get_text(strip=True))
                        elif next_elem.name == 'ul':
                            for li in next_elem.find_all('li')[:5]:  # Limit to 5 facts
                                fun_facts.append(li.get_text(strip=True))
                        next_elem = next_elem.find_next_sibling()

        if fun_facts:
            data['fun_facts'] = fun_facts[:5]  # Top 5 fun facts

        # Extract any notable achievements or records
        full_text = soup.get_text()
        if 'world record' in full_text.lower() or 'guinness' in full_text.lower():
            data['has_world_records'] = True

        # Check if breed was used for specific work
        work_roles = ['police dog', 'military dog', 'service dog', 'therapy dog', 'search and rescue',
                     'hunting dog', 'herding dog', 'guard dog', 'sled dog', 'water rescue']
        found_roles = []
        for role in work_roles:
            if role in full_text.lower():
                found_roles.append(role)

        if found_roles:
            data['working_roles'] = found_roles

        return data

    def extract_breed_standards(self, soup) -> Dict:
        """Extract breed standard information and variations"""
        data = {}

        # Look for breed standard sections
        standard_sections = ['breed standard', 'standard', 'varieties', 'types', 'recognition']
        for section_name in standard_sections:
            for heading in soup.find_all(['h2', 'h3']):
                heading_text = heading.get_text(strip=True).lower()
                if section_name in heading_text:
                    content = []
                    next_elem = heading.find_next_sibling()
                    while next_elem and next_elem.name not in ['h2', 'h3'] and len(content) < 2:
                        if next_elem.name == 'p':
                            content.append(next_elem.get_text(strip=True))
                        next_elem = next_elem.find_next_sibling()

                    if content:
                        data['breed_standard'] = ' '.join(content)

        # Extract kennel club recognition
        full_text = soup.get_text()
        recognized_by = []
        kennel_clubs = ['AKC', 'American Kennel Club', 'UKC', 'United Kennel Club',
                       'FCI', 'The Kennel Club', 'Canadian Kennel Club', 'ANKC']

        for club in kennel_clubs:
            if club in full_text:
                recognized_by.append(club)

        if recognized_by:
            data['recognized_by'] = recognized_by

        # Check for color varieties
        color_section = soup.find(text=re.compile(r'Colo[u]?rs?', re.IGNORECASE))
        if color_section:
            parent = color_section.parent
            if parent and parent.name in ['th', 'td', 'b', 'strong']:
                next_elem = parent.find_next_sibling()
                if next_elem:
                    data['color_varieties'] = next_elem.get_text(strip=True)

        return data

    def save_to_gcs(self, breed_data: Dict):
        """Save breed data and HTML to GCS"""
        breed_slug = breed_data['breed_slug']

        # Save full HTML
        html_blob_name = f"{self.gcs_folder}/{breed_slug}.html"
        html_blob = self.bucket.blob(html_blob_name)
        html_blob.upload_from_string(
            breed_data['html_content'],
            content_type='text/html'
        )

        # Save extracted JSON (without HTML)
        json_data = {k: v for k, v in breed_data.items() if k != 'html_content'}
        json_blob_name = f"{self.gcs_folder}/{breed_slug}.json"
        json_blob = self.bucket.blob(json_blob_name)
        json_blob.upload_from_string(
            json.dumps(json_data, indent=2),
            content_type='application/json'
        )

        logger.info(f"Saved to GCS: {breed_slug}")
        return html_blob_name, json_blob_name

    def update_database(self, breed_data: Dict):
        """Update both breeds_details and comprehensive content table"""
        extracted = breed_data.get('extracted_data', {})

        if not extracted:
            return

        # Prepare update data
        update_data = {}

        # Weight data - Fixed column names for breeds_details table
        if 'weight_min_kg' in extracted:
            update_data['weight_kg_min'] = extracted['weight_min_kg']
        if 'weight_max_kg' in extracted:
            update_data['weight_kg_max'] = extracted['weight_max_kg']
        if 'weight_avg_kg' in extracted:
            update_data['adult_weight_avg_kg'] = extracted['weight_avg_kg']

        # Height data - Fixed column names for breeds_details table (convert to int)
        if 'height_min_cm' in extracted:
            update_data['height_cm_min'] = int(extracted['height_min_cm'])
        if 'height_max_cm' in extracted:
            update_data['height_cm_max'] = int(extracted['height_max_cm'])

        # Lifespan data - Fixed column names for breeds_details table (convert to int)
        if 'lifespan_min_years' in extracted:
            update_data['lifespan_years_min'] = int(extracted['lifespan_min_years'])
        if 'lifespan_max_years' in extracted:
            update_data['lifespan_years_max'] = int(extracted['lifespan_max_years'])
        if 'lifespan_avg_years' in extracted:
            update_data['lifespan_avg_years'] = extracted['lifespan_avg_years']

        # Energy level
        if 'energy_level' in extracted:
            update_data['energy'] = extracted['energy_level']

        # Additional fields - only add origin which exists in breeds_details
        if extracted.get('origin'):
            update_data['origin'] = extracted['origin']

        # Note: temperament and health_issues go to comprehensive_content table, not breeds_details

        # Mark source
        update_data['weight_from'] = 'wikipedia'
        update_data['height_from'] = 'wikipedia'
        update_data['lifespan_from'] = 'wikipedia'
        update_data['updated_at'] = datetime.now().isoformat()

        if update_data and not self.test_mode:
            try:
                # Update breeds_details (underlying table for breeds_published view)
                self.supabase.table('breeds_details').update(
                    update_data
                ).eq('breed_slug', breed_data['breed_slug']).execute()

                # Also update/insert comprehensive content
                comprehensive_data = {
                    'breed_slug': breed_data['breed_slug'],
                    'wikipedia_url': breed_data.get('wikipedia_url'),
                    'gcs_html_path': breed_data.get('gcs_html_path'),
                    'gcs_json_path': breed_data.get('gcs_json_path'),
                    'scraped_at': breed_data.get('scraped_at'),

                    # Rich content fields
                    'introduction': extracted.get('introduction'),
                    'history': extracted.get('history'),
                    'history_brief': extracted.get('history_brief'),
                    'personality_description': extracted.get('personality_description'),
                    'personality_traits': extracted.get('personality_traits'),
                    'temperament': extracted.get('temperament'),
                    'good_with_children': extracted.get('good_with_children'),
                    'good_with_pets': extracted.get('good_with_pets'),
                    'intelligence_noted': extracted.get('intelligence_noted'),
                    'grooming_needs': extracted.get('grooming_needs'),
                    'grooming_frequency': extracted.get('grooming_frequency'),
                    'exercise_needs_detail': extracted.get('exercise_needs_detail'),
                    'exercise_level': extracted.get('exercise_level'),
                    'training_tips': extracted.get('training_tips'),
                    'general_care': extracted.get('general_care'),
                    'fun_facts': extracted.get('fun_facts'),
                    'has_world_records': extracted.get('has_world_records'),
                    'working_roles': extracted.get('working_roles'),
                    'breed_standard': extracted.get('breed_standard'),
                    'recognized_by': extracted.get('recognized_by'),
                    'color_varieties': extracted.get('color_varieties'),
                    'health_issues': extracted.get('health_issues'),
                    'coat': extracted.get('coat'),
                    'colors': extracted.get('colors')
                }

                # Remove None values
                comprehensive_data = {k: v for k, v in comprehensive_data.items() if v is not None}

                # Upsert to breeds_comprehensive_content
                self.supabase.table('breeds_comprehensive_content').upsert(
                    comprehensive_data
                ).execute()

                logger.info(f"Updated database for {breed_data['breed_slug']}")
                self.stats['updated'] += 1
            except Exception as e:
                logger.error(f"Database update failed for {breed_data['breed_slug']}: {e}")

    def run(self):
        """Execute the re-scraping process"""
        logger.info("Starting Wikipedia breed re-scraping...")

        # Get breeds to scrape
        breeds = self.get_breeds_to_scrape()
        self.stats['total'] = len(breeds)

        logger.info(f"Found {self.stats['total']} breeds to scrape")

        results = []
        for i, breed in enumerate(breeds, 1):
            breed_slug = breed['breed_slug']
            display_name = breed['display_name']
            aliases = breed.get('aliases', [])

            logger.info(f"[{i}/{self.stats['total']}] Processing {display_name}")

            # Scrape breed
            breed_data = self.scrape_breed_page(breed_slug, display_name, aliases)

            if breed_data:
                # Save to GCS
                html_path, json_path = self.save_to_gcs(breed_data)
                breed_data['gcs_html_path'] = html_path
                breed_data['gcs_json_path'] = json_path

                # Skip database update - we'll process from GCS later
                # self.update_database(breed_data)
                logger.info(f"Skipping database update - GCS data saved for later processing")

                self.stats['success'] += 1
                results.append({
                    'breed_slug': breed_slug,
                    'display_name': display_name,
                    'extracted_fields': list(breed_data.get('extracted_data', {}).keys())
                })
            else:
                self.stats['failed'] += 1
                logger.warning(f"Failed to scrape {display_name}")

            # Rate limiting - be respectful to Wikipedia
            if i < self.stats['total']:
                # Take a longer break every 25 breeds
                if i % 25 == 0 and i > 0:
                    logger.info(f"Taking a 30-second break after {i} breeds...")
                    time.sleep(30)
                else:
                    # Random delay between 3-6 seconds to appear more human
                    delay = 3 + random.uniform(0, 3)
                    time.sleep(delay)

        # Save summary report
        self.save_summary_report(results)

        # Print summary
        print("\n" + "="*60)
        print("WIKIPEDIA RE-SCRAPING COMPLETE")
        print("="*60)
        print(f"Total breeds: {self.stats['total']}")
        print(f"Successfully scraped: {self.stats['success']}")
        print(f"Failed: {self.stats['failed']}")
        print(f"Database updates: {self.stats['updated']}")
        print(f"GCS folder: {self.gcs_folder}")

        return self.stats

    def save_summary_report(self, results):
        """Save summary report"""
        report = {
            'timestamp': self.timestamp,
            'stats': self.stats,
            'gcs_folder': self.gcs_folder,
            'results': results
        }

        report_path = f"wikipedia_rescrape_report_{self.timestamp}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"Report saved to {report_path}")

if __name__ == "__main__":
    # Check for test mode
    test_mode = '--test' in sys.argv

    scraper = WikipediaBreedRescraperGCS(test_mode=test_mode)
    scraper.run()