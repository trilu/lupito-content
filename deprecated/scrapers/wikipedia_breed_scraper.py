#!/usr/bin/env python3
"""
Wikipedia Breed Scraper for breeds_details Table
=================================================
Scrapes breed data from Wikipedia and populates the breeds_details table
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

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WikipediaBreedScraper:
    """Scraper for Wikipedia breed pages"""
    
    def __init__(self):
        """Initialize scraper with Supabase connection"""
        load_dotenv()
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Missing Supabase credentials in .env file")
        
        self.supabase = create_client(self.supabase_url, self.supabase_key)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Educational Breed Data Scraper) Contact: research@example.com'
        })
        
        # Statistics tracking
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
    
    def scrape_breed(self, breed_name: str, url: str) -> Optional[Dict[str, Any]]:
        """Scrape a single breed from Wikipedia"""
        try:
            logger.info(f"Scraping {breed_name} from {url}")
            
            # Fetch page
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # Check if redirected to search or error page
            if 'Special:Search' in response.url or 'Wikipedia does not have an article' in response.text:
                logger.warning(f"No Wikipedia page for {breed_name}")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract data
            infobox_data = self._extract_infobox(soup)
            content_data = self._extract_content(soup)
            
            # Combine data
            breed_data = {
                'breed_slug': self._create_slug(breed_name),
                'display_name': breed_name,
                'raw_html': response.text[:50000],  # Store first 50k chars
                **infobox_data,
                **content_data
            }
            
            # Map to controlled vocabularies
            breed_data = self._map_to_controlled_vocab(breed_data)
            
            return breed_data
            
        except Exception as e:
            logger.error(f"Error scraping {breed_name}: {e}")
            self.stats['errors'].append(f"{breed_name}: {str(e)}")
            return None
    
    def _extract_infobox(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract data from Wikipedia infobox"""
        data = {}
        
        # Find infobox - try multiple selectors
        infobox = soup.find('table', {'class': 'infobox'})
        if not infobox:
            infobox = soup.find('table', class_=lambda x: x and 'infobox' in str(x))
        if not infobox:
            return data
        
        # Extract all rows
        for row in infobox.find_all('tr'):
            header = row.find('th')
            if not header:
                continue
            
            header_text = header.get_text(strip=True).lower()
            
            # For weight and height, get all td cells in the row
            cells = row.find_all('td')
            if not cells:
                continue
            
            # Combine text from all cells
            cell_text = ' '.join([cell.get_text(separator=' ', strip=True) for cell in cells])
            
            # Parse specific fields
            if 'height' in header_text:
                heights = self._parse_measurements(cell_text, 'height')
                data.update(heights)
            
            elif 'weight' in header_text:
                weights = self._parse_measurements(cell_text, 'weight')
                data.update(weights)
            
            elif 'life' in header_text and 'span' in header_text:
                lifespan = self._parse_lifespan(cell_text)
                data.update(lifespan)
            
            elif 'origin' in header_text or 'country' in header_text:
                data['origin'] = cell_text[:100]  # Limit length
            
            elif 'coat' in header_text:
                data['coat_info'] = cell_text[:200]
            
            elif 'color' in header_text or 'colour' in header_text:
                data['colors'] = cell_text[:200]
        
        return data
    
    def _parse_measurements(self, text: str, measure_type: str) -> Dict[str, Any]:
        """Parse height/weight measurements from text"""
        data = {}
        
        # Keep original text for better pattern matching
        text_lower = text.lower()
        
        # Find all numbers
        numbers = re.findall(r'(\d+(?:\.\d+)?)', text)
        
        if measure_type == 'height':
            # Look for range patterns with proper dash handling
            cm_pattern = r'(\d+)[–\-](\d+)\s*cm'
            inch_pattern = r'(\d+(?:\.\d+)?)[–\-](\d+(?:\.\d+)?)\s*in'
            
            cm_matches = re.findall(cm_pattern, text)
            inch_matches = re.findall(inch_pattern, text)
            
            if cm_matches:
                # Use cm values directly
                heights = []
                for match in cm_matches:
                    heights.extend([float(match[0]), float(match[1])])
                data['height_cm_min'] = int(min(heights))
                data['height_cm_max'] = int(max(heights))
            elif inch_matches:
                # Convert inches to cm
                heights = []
                for match in inch_matches:
                    heights.extend([float(match[0]) * 2.54, float(match[1]) * 2.54])
                data['height_cm_min'] = int(round(min(heights)))
                data['height_cm_max'] = int(round(max(heights)))
        
        elif measure_type == 'weight':
            # Look for range patterns with proper dash handling
            kg_pattern = r'(\d+)[–\-](\d+)\s*kg'
            lb_pattern = r'(\d+)[–\-](\d+)\s*lb'
            
            kg_matches = re.findall(kg_pattern, text)
            lb_matches = re.findall(lb_pattern, text)
            
            if kg_matches:
                # Use kg values directly
                weights = []
                for match in kg_matches:
                    weights.extend([float(match[0]), float(match[1])])
                data['weight_kg_min'] = min(weights)
                data['weight_kg_max'] = max(weights)
            elif lb_matches:
                # Convert lb to kg
                weights = []
                for match in lb_matches:
                    weights.extend([float(match[0]) * 0.453592, float(match[1]) * 0.453592])
                data['weight_kg_min'] = round(min(weights), 1)
                data['weight_kg_max'] = round(max(weights), 1)
            # Fallback: look for individual kg values
            elif re.search(r'\d+\s*kg', text_lower):
                kg_individual = re.findall(r'(\d+(?:\.\d+)?)\s*kg', text_lower)
                if kg_individual:
                    values = [float(x) for x in kg_individual]
                    data['weight_kg_min'] = min(values)
                    data['weight_kg_max'] = max(values)
        
        return data
    
    def _parse_lifespan(self, text: str) -> Dict[str, Any]:
        """Parse lifespan from text"""
        data = {}
        
        # Find year patterns
        years = re.findall(r'(\d+)[\s\-–to]+(\d+)\s*year', text.lower())
        if years:
            data['lifespan_years_min'] = int(years[0][0])
            data['lifespan_years_max'] = int(years[0][1])
        else:
            # Single value
            single = re.findall(r'(\d+)\s*year', text.lower())
            if single:
                avg_years = int(single[0])
                data['lifespan_years_min'] = avg_years - 1
                data['lifespan_years_max'] = avg_years + 1
        
        return data
    
    def _extract_content(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract content sections from Wikipedia article"""
        data = {}
        content_sections = {}
        
        # Find main content div
        content = soup.find('div', {'id': 'mw-content-text'})
        if not content:
            return data
        
        # Extract sections
        current_section = 'overview'
        current_text = []
        
        for elem in content.find_all(['h2', 'h3', 'p']):
            if elem.name in ['h2', 'h3']:
                # Save previous section
                if current_text:
                    content_sections[current_section] = ' '.join(current_text)[:2000]
                    current_text = []
                
                # Start new section
                section_title = elem.get_text(strip=True).lower()
                if 'temperament' in section_title or 'personality' in section_title:
                    current_section = 'temperament'
                elif 'health' in section_title:
                    current_section = 'health'
                elif 'care' in section_title or 'grooming' in section_title:
                    current_section = 'care'
                elif 'training' in section_title:
                    current_section = 'training'
                elif 'history' in section_title or 'origin' in section_title:
                    current_section = 'history'
                elif 'description' in section_title or 'appearance' in section_title:
                    current_section = 'appearance'
                else:
                    current_section = section_title[:50]
            
            elif elem.name == 'p' and len(current_text) < 5:  # Limit paragraphs per section
                text = elem.get_text(strip=True)
                if text and len(text) > 20:  # Skip very short paragraphs
                    current_text.append(text)
        
        # Save last section
        if current_text:
            content_sections[current_section] = ' '.join(current_text)[:2000]
        
        # Store as comprehensive content JSON
        if content_sections:
            data['comprehensive_content'] = json.dumps(content_sections)
        
        # Extract temperament keywords for trait inference
        temp_text = content_sections.get('temperament', '') + content_sections.get('overview', '')
        data['temperament_text'] = temp_text[:1000]
        
        return data
    
    def _map_to_controlled_vocab(self, breed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map extracted data to controlled vocabularies"""
        
        # Determine size based on weight
        if breed_data.get('weight_kg_max'):
            weight = breed_data['weight_kg_max']
            if weight < 5:
                breed_data['size'] = 'tiny'
            elif weight < 10:
                breed_data['size'] = 'small'
            elif weight < 25:
                breed_data['size'] = 'medium'
            elif weight < 45:
                breed_data['size'] = 'large'
            else:
                breed_data['size'] = 'giant'
        
        # Infer traits from temperament text
        temp_text = breed_data.get('temperament_text', '').lower()
        
        # Energy level
        if any(word in temp_text for word in ['high energy', 'very active', 'athletic', 'energetic']):
            breed_data['energy'] = 'high'
        elif any(word in temp_text for word in ['moderate energy', 'moderately active']):
            breed_data['energy'] = 'moderate'
        elif any(word in temp_text for word in ['calm', 'laid-back', 'low energy', 'lazy']):
            breed_data['energy'] = 'low'
        
        # Trainability
        if any(word in temp_text for word in ['intelligent', 'easy to train', 'trainable', 'obedient']):
            breed_data['trainability'] = 'easy'
        elif any(word in temp_text for word in ['stubborn', 'independent', 'difficult to train']):
            breed_data['trainability'] = 'challenging'
        else:
            breed_data['trainability'] = 'moderate'
        
        # Shedding (from coat info)
        coat_text = breed_data.get('coat_info', '').lower()
        if any(word in coat_text for word in ['heavy shed', 'sheds a lot', 'high shed']):
            breed_data['shedding'] = 'high'
        elif any(word in coat_text for word in ['moderate shed', 'average shed']):
            breed_data['shedding'] = 'moderate'
        elif any(word in coat_text for word in ['minimal shed', 'low shed', 'hypoallergenic']):
            breed_data['shedding'] = 'low'
        
        # Coat length
        if any(word in coat_text for word in ['long', 'flowing', 'lengthy']):
            breed_data['coat_length'] = 'long'
        elif any(word in coat_text for word in ['short', 'smooth']):
            breed_data['coat_length'] = 'short'
        else:
            breed_data['coat_length'] = 'medium'
        
        # Bark level
        if any(word in temp_text for word in ['vocal', 'barker', 'noisy', 'loud']):
            breed_data['bark_level'] = 'frequent'
        elif any(word in temp_text for word in ['quiet', 'rarely barks']):
            breed_data['bark_level'] = 'quiet'
        else:
            breed_data['bark_level'] = 'moderate'
        
        # Friendliness scores (1-5 scale)
        if any(word in temp_text for word in ['friendly', 'sociable', 'gentle', 'good with']):
            breed_data['friendliness_to_humans'] = 4
            breed_data['friendliness_to_dogs'] = 3
        elif any(word in temp_text for word in ['aloof', 'reserved', 'independent']):
            breed_data['friendliness_to_humans'] = 2
            breed_data['friendliness_to_dogs'] = 2
        
        # Remove temporary fields
        breed_data.pop('temperament_text', None)
        breed_data.pop('coat_info', None)
        breed_data.pop('colors', None)
        
        return breed_data
    
    def _create_slug(self, breed_name: str) -> str:
        """Create URL-safe slug from breed name"""
        slug = breed_name.lower()
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        slug = slug.strip('-')
        return slug
    
    def save_to_database(self, breed_data: Dict[str, Any]) -> bool:
        """Save breed data to breeds_details table"""
        try:
            # Extract raw HTML for breed_raw table
            raw_html = breed_data.pop('raw_html', '')
            breed_slug = breed_data['breed_slug']
            
            # Save raw HTML
            if raw_html:
                try:
                    fingerprint = hashlib.md5(raw_html.encode()).hexdigest()
                    raw_record = {
                        'source_domain': 'en.wikipedia.org',
                        'source_url': f'https://en.wikipedia.org/wiki/{breed_slug}',
                        'breed_slug': breed_slug,
                        'raw_html': raw_html,
                        'fingerprint': fingerprint,
                        'first_seen_at': datetime.utcnow().isoformat(),
                        'last_seen_at': datetime.utcnow().isoformat()
                    }
                    # Try to insert, ignore if already exists
                    self.supabase.table('breed_raw').insert(raw_record).execute()
                except Exception as e:
                    # Log but don't fail - raw HTML storage is optional
                    logger.debug(f"Could not save raw HTML for {breed_slug}: {e}")
            
            # Check if breed already exists in breeds_details
            existing = self.supabase.table('breeds_details').select('id').eq('breed_slug', breed_slug).execute()
            
            if existing.data:
                # Update existing record
                response = self.supabase.table('breeds_details').update(breed_data).eq('breed_slug', breed_slug).execute()
                logger.info(f"Updated breed in breeds_details: {breed_data['display_name']}")
            else:
                # Insert new record
                response = self.supabase.table('breeds_details').insert(breed_data).execute()
                logger.info(f"Inserted breed into breeds_details: {breed_data['display_name']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Database error for {breed_data.get('display_name')}: {e}")
            return False
    
    def process_breeds_from_file(self, filename: str = 'wikipedia_urls.txt', limit: int = None):
        """Process breeds from URL file"""
        # Load URLs
        with open(filename, 'r') as f:
            lines = f.readlines()
        
        if limit:
            lines = lines[:limit]
        
        logger.info(f"Processing {len(lines)} breeds from {filename}")
        
        # Process each breed
        for i, line in enumerate(lines):
            if '|' not in line:
                continue
            
            breed_name, url = line.strip().split('|', 1)
            self.stats['total'] += 1
            
            # Progress update
            if (i + 1) % 10 == 0:
                logger.info(f"Progress: {i+1}/{len(lines)} breeds processed")
                self._print_stats()
            
            # Check if already processed
            breed_slug = self._create_slug(breed_name)
            existing = self.supabase.table('breeds_details').select('id').eq('breed_slug', breed_slug).execute()
            if existing.data:
                logger.info(f"Skipping {breed_name} - already in database")
                self.stats['skipped'] += 1
                continue
            
            # Scrape breed
            breed_data = self.scrape_breed(breed_name, url)
            
            if breed_data:
                # Save to database
                if self.save_to_database(breed_data):
                    self.stats['success'] += 1
                else:
                    self.stats['failed'] += 1
            else:
                self.stats['failed'] += 1
            
            # Rate limiting
            time.sleep(1)
        
        # Final stats
        self._print_stats()
        self._generate_report()
    
    def _print_stats(self):
        """Print current statistics"""
        print(f"\n{'='*60}")
        print(f"SCRAPING PROGRESS")
        print(f"{'='*60}")
        print(f"Total processed: {self.stats['total']}")
        print(f"Success: {self.stats['success']}")
        print(f"Failed: {self.stats['failed']}")
        print(f"Skipped: {self.stats['skipped']}")
        if self.stats['total'] > 0:
            success_rate = (self.stats['success'] / self.stats['total']) * 100
            print(f"Success rate: {success_rate:.1f}%")
    
    def _generate_report(self):
        """Generate final scraping report"""
        report_file = f"wikipedia_scraping_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(report_file, 'w') as f:
            f.write("WIKIPEDIA BREED SCRAPING REPORT\n")
            f.write("="*60 + "\n\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")
            
            f.write("STATISTICS:\n")
            f.write(f"Total processed: {self.stats['total']}\n")
            f.write(f"Success: {self.stats['success']}\n")
            f.write(f"Failed: {self.stats['failed']}\n")
            f.write(f"Skipped: {self.stats['skipped']}\n")
            
            if self.stats['total'] > 0:
                success_rate = (self.stats['success'] / self.stats['total']) * 100
                f.write(f"Success rate: {success_rate:.1f}%\n")
            
            if self.stats['errors']:
                f.write("\nERRORS:\n")
                for error in self.stats['errors'][:50]:  # Limit to first 50 errors
                    f.write(f"  - {error}\n")
        
        logger.info(f"Report saved to {report_file}")


def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Wikipedia Breed Scraper')
    parser.add_argument('--urls-file', default='wikipedia_urls.txt', help='File containing breed URLs')
    parser.add_argument('--limit', type=int, help='Limit number of breeds to process')
    parser.add_argument('--test', action='store_true', help='Test mode - process only 5 breeds')
    
    args = parser.parse_args()
    
    # Initialize scraper
    scraper = WikipediaBreedScraper()
    
    # Set limit for test mode
    if args.test:
        args.limit = 5
        logger.info("TEST MODE - Processing only 5 breeds")
    
    # Process breeds
    scraper.process_breeds_from_file(args.urls_file, args.limit)


if __name__ == "__main__":
    main()