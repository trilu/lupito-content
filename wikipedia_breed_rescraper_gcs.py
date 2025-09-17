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
        """Extract structured data from Wikipedia page"""
        data = {}

        # Extract from infobox
        infobox = soup.find('table', {'class': 'infobox'})
        if infobox:
            data.update(self.parse_infobox(infobox))

        # Extract from article content
        data.update(self.extract_from_content(soup))

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
        """Update breeds_enrichment table (create if needed)"""
        extracted = breed_data.get('extracted_data', {})

        if not extracted:
            return

        # Prepare update data
        update_data = {}

        # Weight data
        if 'weight_min_kg' in extracted:
            update_data['adult_weight_min_kg'] = extracted['weight_min_kg']
        if 'weight_max_kg' in extracted:
            update_data['adult_weight_max_kg'] = extracted['weight_max_kg']
        if 'weight_avg_kg' in extracted:
            update_data['adult_weight_avg_kg'] = extracted['weight_avg_kg']

        # Height data
        if 'height_min_cm' in extracted:
            update_data['height_min_cm'] = extracted['height_min_cm']
        if 'height_max_cm' in extracted:
            update_data['height_max_cm'] = extracted['height_max_cm']

        # Lifespan data
        if 'lifespan_min_years' in extracted:
            update_data['lifespan_min_years'] = extracted['lifespan_min_years']
        if 'lifespan_max_years' in extracted:
            update_data['lifespan_max_years'] = extracted['lifespan_max_years']
        if 'lifespan_avg_years' in extracted:
            update_data['lifespan_avg_years'] = extracted['lifespan_avg_years']

        # Energy level
        if 'energy_level' in extracted:
            update_data['energy'] = extracted['energy_level']

        # Additional fields
        if extracted.get('temperament'):
            update_data['temperament'] = extracted['temperament']
        if extracted.get('health_issues'):
            update_data['health_issues'] = extracted['health_issues']
        if extracted.get('origin'):
            update_data['origin'] = extracted['origin']

        # Mark source
        update_data['weight_from'] = 'wikipedia'
        update_data['height_from'] = 'wikipedia'
        update_data['lifespan_from'] = 'wikipedia'
        update_data['updated_at'] = datetime.now().isoformat()

        if update_data and not self.test_mode:
            try:
                # Update breeds_published
                self.supabase.table('breeds_published').update(
                    update_data
                ).eq('breed_slug', breed_data['breed_slug']).execute()

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
                self.save_to_gcs(breed_data)

                # Update database
                self.update_database(breed_data)

                self.stats['success'] += 1
                results.append({
                    'breed_slug': breed_slug,
                    'display_name': display_name,
                    'extracted_fields': list(breed_data.get('extracted_data', {}).keys())
                })
            else:
                self.stats['failed'] += 1
                logger.warning(f"Failed to scrape {display_name}")

            # Rate limiting
            if i < self.stats['total']:
                time.sleep(2)

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