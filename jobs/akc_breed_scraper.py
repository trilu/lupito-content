#!/usr/bin/env python3
"""
AKC Breed Scraper
Scrapes breed data from American Kennel Club website to improve breed coverage
Adapted from bark_breed_scraper.py for AKC-specific structure
"""
import os
import sys
import time
import random
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import hashlib
import re

import requests
from supabase import create_client, Client
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from etl.normalize_breeds import (
    normalize_characteristic, extract_lifespan, extract_weight_range,
    extract_height_range, normalize_friendliness, 
    generate_breed_fingerprint,
    SIZE_MAPPING, ENERGY_MAPPING, COAT_LENGTH_MAPPING,
    SHEDDING_MAPPING, TRAINABILITY_MAPPING, BARK_LEVEL_MAPPING
)

load_dotenv()

class AKCBreedScraper:
    def __init__(self):
        """Initialize the AKC breed scraper"""
        self.session = self._setup_session()
        self.supabase = self._setup_supabase()
        
        # Configuration
        self.config = {
            'base_url': 'https://www.akc.org/dog-breeds/',
            'rate_limit_seconds': 2.0,  # Be respectful to AKC
            'timeout': 30,
            'batch_size': 10,
            'storage_bucket': 'dog-breeds',  # Use breed-specific bucket
            'image_timeout': 15
        }
        
        # Statistics tracking
        self.stats = {
            'urls_processed': 0,
            'breeds_new': 0,
            'breeds_updated': 0,
            'breeds_skipped': 0,
            'breeds_matched': 0,
            'extraction_success': 0,
            'extraction_failed': 0,
            'errors': 0
        }
        
        # QA tracking
        self.qa_data = []

    def _setup_session(self) -> requests.Session:
        """Setup requests session with headers"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; LupitoBreedBot/1.0)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
        return session

    def _setup_supabase(self) -> Client:
        """Setup Supabase client"""
        return create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_KEY')
        )

    def extract_akc_breed_data(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract breed data from AKC page structure"""
        breed_data = {}
        
        try:
            # Extract breed name from URL or page title
            breed_slug = url.rstrip('/').split('/')[-1]
            breed_name = breed_slug.replace('-', ' ').title()
            
            # Try to get proper name from page title
            title_elem = soup.find('title')
            if title_elem:
                title_text = title_elem.get_text()
                # AKC format: "Breed Name - American Kennel Club"
                if ' - American Kennel Club' in title_text:
                    breed_name = title_text.split(' - American Kennel Club')[0].strip()
            
            breed_data['display_name'] = breed_name
            breed_data['breed_slug'] = breed_slug
            
            # Extract breed traits/characteristics
            traits = self._extract_breed_traits(soup)
            
            # Extract comprehensive content sections
            comprehensive_content = self._extract_content_sections(soup)
            
            # Map AKC traits to our schema
            breed_data.update(self._map_traits_to_schema(traits))
            
            # Add comprehensive content
            breed_data['comprehensive_content'] = comprehensive_content
            
            # Extract origin if available
            origin = self._extract_origin(soup)
            if origin:
                breed_data['origin'] = origin
            
            # Track extraction success
            if traits or comprehensive_content:
                self.stats['extraction_success'] += 1
            else:
                self.stats['extraction_failed'] += 1
            
        except Exception as e:
            print(f"    ⚠️  Error extracting AKC data: {e}")
            breed_data['display_name'] = breed_slug.replace('-', ' ').title()
            breed_data['breed_slug'] = breed_slug
            self.stats['extraction_failed'] += 1
        
        return breed_data

    def _extract_breed_traits(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract breed traits from AKC's structured data"""
        traits = {}
        
        try:
            # Look for breed traits section (common AKC patterns)
            # Pattern 1: Data attributes
            trait_elements = soup.find_all(['div', 'span', 'dd'], attrs={'class': re.compile('trait|characteristic|stat')})
            for elem in trait_elements:
                # Extract trait name and value
                name_elem = elem.find_previous(['dt', 'span', 'div'], string=True)
                if name_elem:
                    trait_name = name_elem.get_text(strip=True)
                    trait_value = elem.get_text(strip=True)
                    traits[trait_name] = trait_value
            
            # Pattern 2: Table-based traits
            tables = soup.find_all('table', class_=re.compile('breed|trait|characteristic'))
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        trait_name = cells[0].get_text(strip=True)
                        trait_value = cells[1].get_text(strip=True)
                        traits[trait_name] = trait_value
            
            # Pattern 3: Definition lists
            dl_elements = soup.find_all('dl')
            for dl in dl_elements:
                dt_elements = dl.find_all('dt')
                dd_elements = dl.find_all('dd')
                for dt, dd in zip(dt_elements, dd_elements):
                    trait_name = dt.get_text(strip=True)
                    trait_value = dd.get_text(strip=True)
                    traits[trait_name] = trait_value
            
            # Pattern 4: Specific AKC selectors
            # Height
            height_elem = soup.find(string=re.compile('Height:', re.I))
            if height_elem:
                height_value = height_elem.find_next().get_text(strip=True) if height_elem.find_next() else ""
                traits['Height'] = height_value
            
            # Weight
            weight_elem = soup.find(string=re.compile('Weight:', re.I))
            if weight_elem:
                weight_value = weight_elem.find_next().get_text(strip=True) if weight_elem.find_next() else ""
                traits['Weight'] = weight_value
            
            # Life Expectancy
            life_elem = soup.find(string=re.compile('Life Expectancy:|Life Span:', re.I))
            if life_elem:
                life_value = life_elem.find_next().get_text(strip=True) if life_elem.find_next() else ""
                traits['Life Expectancy'] = life_value
            
        except Exception as e:
            print(f"      Error extracting traits: {e}")
        
        return traits

    def _extract_content_sections(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract comprehensive content from AKC page"""
        content = {
            'about': '',
            'personality': '',
            'health': '',
            'care': '',
            'feeding': '',
            'grooming': '',
            'exercise': '',
            'training': '',
            'history': ''
        }
        
        try:
            # Look for main content sections
            main_content = soup.find('main') or soup.find('article') or soup
            
            # Extract text from different sections
            sections = main_content.find_all(['section', 'div'], class_=re.compile('breed|content|description'))
            
            for section in sections:
                section_text = section.get_text(separator=' ', strip=True)
                
                # Categorize content based on keywords
                lower_text = section_text.lower()
                
                if any(word in lower_text for word in ['personality', 'temperament', 'behavior']):
                    content['personality'] += section_text + ' '
                elif any(word in lower_text for word in ['health', 'disease', 'condition']):
                    content['health'] += section_text + ' '
                elif any(word in lower_text for word in ['care', 'maintain']):
                    content['care'] += section_text + ' '
                elif any(word in lower_text for word in ['feed', 'diet', 'nutrition']):
                    content['feeding'] += section_text + ' '
                elif any(word in lower_text for word in ['groom', 'coat', 'brush']):
                    content['grooming'] += section_text + ' '
                elif any(word in lower_text for word in ['exercise', 'activity', 'walk']):
                    content['exercise'] += section_text + ' '
                elif any(word in lower_text for word in ['train', 'obedience', 'socialize']):
                    content['training'] += section_text + ' '
                elif any(word in lower_text for word in ['history', 'origin', 'developed']):
                    content['history'] += section_text + ' '
                else:
                    content['about'] += section_text + ' '
            
            # Clean up content
            for key in content:
                content[key] = ' '.join(content[key].split())[:5000]  # Limit length and normalize whitespace
            
        except Exception as e:
            print(f"      Error extracting content: {e}")
        
        return content

    def _map_traits_to_schema(self, traits: Dict[str, str]) -> Dict[str, Any]:
        """Map AKC traits to our database schema"""
        mapped = {}
        
        try:
            # Extract numeric ranges
            height_text = traits.get('Height', '')
            weight_text = traits.get('Weight', '')
            life_text = traits.get('Life Expectancy', '') or traits.get('Life Span', '')
            
            # Height extraction (convert inches to cm)
            height_min, height_max = self._extract_height_inches_to_cm(height_text)
            mapped['height_cm_min'] = height_min
            mapped['height_cm_max'] = height_max
            
            # Weight extraction (convert lbs to kg)
            weight_min, weight_max = self._extract_weight_lbs_to_kg(weight_text)
            mapped['weight_kg_min'] = weight_min
            mapped['weight_kg_max'] = weight_max
            
            # Lifespan extraction
            life_min, life_max = extract_lifespan(life_text)
            mapped['lifespan_years_min'] = life_min
            mapped['lifespan_years_max'] = life_max
            
            # Map size based on weight/height
            if weight_max:
                if weight_max < 10:
                    mapped['size'] = 'small'
                elif weight_max < 25:
                    mapped['size'] = 'medium'
                elif weight_max < 45:
                    mapped['size'] = 'large'
                else:
                    mapped['size'] = 'giant'
            
            # Map other characteristics from traits
            for trait_name, trait_value in traits.items():
                lower_name = trait_name.lower()
                
                if 'energy' in lower_name:
                    mapped['energy'] = normalize_characteristic(trait_value, ENERGY_MAPPING)
                elif 'shed' in lower_name:
                    mapped['shedding'] = normalize_characteristic(trait_value, SHEDDING_MAPPING)
                elif 'train' in lower_name:
                    mapped['trainability'] = normalize_characteristic(trait_value, TRAINABILITY_MAPPING)
                elif 'bark' in lower_name or 'vocal' in lower_name:
                    mapped['bark_level'] = normalize_characteristic(trait_value, BARK_LEVEL_MAPPING)
                elif 'coat' in lower_name and 'length' in lower_name:
                    mapped['coat_length'] = normalize_characteristic(trait_value, COAT_LENGTH_MAPPING)
                elif 'friendly' in lower_name or 'social' in lower_name:
                    if 'dog' in lower_name:
                        mapped['friendliness_to_dogs'] = normalize_friendliness(trait_value)
                    else:
                        mapped['friendliness_to_humans'] = normalize_friendliness(trait_value)
            
        except Exception as e:
            print(f"      Error mapping traits: {e}")
        
        return mapped

    def _extract_height_inches_to_cm(self, text: str) -> tuple:
        """Extract height in inches and convert to cm"""
        if not text:
            return None, None
        
        try:
            # Look for patterns like "10-12 inches" or "10 to 12 inches"
            numbers = re.findall(r'(\d+(?:\.\d+)?)', text)
            if numbers:
                if len(numbers) >= 2:
                    min_inches = float(numbers[0])
                    max_inches = float(numbers[1])
                else:
                    min_inches = max_inches = float(numbers[0])
                
                # Convert inches to cm (1 inch = 2.54 cm)
                return round(min_inches * 2.54, 1), round(max_inches * 2.54, 1)
        except:
            pass
        
        return None, None

    def _extract_weight_lbs_to_kg(self, text: str) -> tuple:
        """Extract weight in pounds and convert to kg"""
        if not text:
            return None, None
        
        try:
            # Look for patterns like "50-70 pounds" or "50 to 70 lbs"
            numbers = re.findall(r'(\d+(?:\.\d+)?)', text)
            if numbers:
                if len(numbers) >= 2:
                    min_lbs = float(numbers[0])
                    max_lbs = float(numbers[1])
                else:
                    min_lbs = max_lbs = float(numbers[0])
                
                # Convert pounds to kg (1 lb = 0.453592 kg)
                return round(min_lbs * 0.453592, 1), round(max_lbs * 0.453592, 1)
        except:
            pass
        
        return None, None

    def _extract_origin(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract breed origin/country"""
        try:
            # Look for origin patterns
            origin_patterns = ['Origin:', 'Country:', 'Originated in', 'From']
            
            for pattern in origin_patterns:
                elem = soup.find(string=re.compile(pattern, re.I))
                if elem:
                    next_elem = elem.find_next()
                    if next_elem:
                        origin = next_elem.get_text(strip=True)
                        # Clean up and limit length
                        origin = origin.split('.')[0][:100]
                        return origin
            
            # Check in content for origin mentions
            text = soup.get_text()
            origin_match = re.search(r'originated in ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', text)
            if origin_match:
                return origin_match.group(1)
            
        except:
            pass
        
        return None

    def scrape_breed(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape a single breed page"""
        try:
            print(f"  🔍 Scraping: {url}")
            
            # Rate limiting
            time.sleep(self.config['rate_limit_seconds'] + random.uniform(-0.5, 0.5))
            
            # Fetch page
            response = self.session.get(url, timeout=self.config['timeout'])
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract breed data
            breed_data = self.extract_akc_breed_data(soup, url)
            
            # Add metadata
            breed_data['source_url'] = url
            breed_data['source_domain'] = 'akc.org'
            breed_data['scraped_at'] = datetime.now().isoformat()
            
            self.stats['urls_processed'] += 1
            
            return breed_data
            
        except Exception as e:
            print(f"    ❌ Error scraping {url}: {e}")
            self.stats['errors'] += 1
            return None

    def save_breed(self, breed_data: Dict[str, Any]) -> bool:
        """Save breed to akc_breeds table"""
        try:
            # Check if breed already exists
            existing = self.supabase.table('akc_breeds')\
                .select('id')\
                .eq('breed_slug', breed_data['breed_slug'])\
                .execute()
            
            # Determine extraction status
            extraction_status = 'success'
            extraction_notes = []
            
            if not breed_data.get('comprehensive_content'):
                extraction_status = 'partial'
                extraction_notes.append('No content extracted')
            if not (breed_data.get('height_cm_max') or breed_data.get('weight_kg_max')):
                extraction_status = 'partial'
                extraction_notes.append('No physical data extracted')
            
            # Prepare data for insertion/update
            db_data = {
                'breed_slug': breed_data['breed_slug'],
                'display_name': breed_data['display_name'],
                'akc_url': breed_data.get('source_url'),
                'comprehensive_content': breed_data.get('comprehensive_content', {}),
                'raw_traits': breed_data.get('raw_traits', {}),
                'origin': breed_data.get('origin'),
                'size': breed_data.get('size'),
                'energy': breed_data.get('energy'),
                'coat_length': breed_data.get('coat_length'),
                'shedding': breed_data.get('shedding'),
                'trainability': breed_data.get('trainability'),
                'bark_level': breed_data.get('bark_level'),
                'height_cm_min': breed_data.get('height_cm_min'),
                'height_cm_max': breed_data.get('height_cm_max'),
                'weight_kg_min': breed_data.get('weight_kg_min'),
                'weight_kg_max': breed_data.get('weight_kg_max'),
                'lifespan_years_min': breed_data.get('lifespan_years_min'),
                'lifespan_years_max': breed_data.get('lifespan_years_max'),
                'friendliness_to_dogs': breed_data.get('friendliness_to_dogs'),
                'friendliness_to_humans': breed_data.get('friendliness_to_humans'),
                'extraction_status': extraction_status,
                'extraction_notes': '; '.join(extraction_notes) if extraction_notes else None,
                'scraped_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # Remove None values
            db_data = {k: v for k, v in db_data.items() if v is not None}
            
            if existing.data:
                # Update existing
                self.supabase.table('akc_breeds')\
                    .update(db_data)\
                    .eq('breed_slug', breed_data['breed_slug'])\
                    .execute()
                
                self.stats['breeds_updated'] += 1
                print(f"    ✅ Updated: {breed_data['display_name']}")
            else:
                # Insert new
                db_data['created_at'] = datetime.now().isoformat()
                
                self.supabase.table('akc_breeds')\
                    .insert(db_data)\
                    .execute()
                
                self.stats['breeds_new'] += 1
                print(f"    ✅ Added: {breed_data['display_name']}")
            
            # Track for QA
            self.qa_data.append({
                'breed_name': breed_data['display_name'],
                'breed_slug': breed_data['breed_slug'],
                'status': 'updated' if existing.data else 'new',
                'has_size': breed_data.get('size') is not None,
                'has_weight': breed_data.get('weight_kg_max') is not None,
                'has_height': breed_data.get('height_cm_max') is not None,
                'has_lifespan': breed_data.get('lifespan_years_max') is not None,
                'source': 'akc.org'
            })
            
            return True
            
        except Exception as e:
            print(f"    ❌ Database error: {e}")
            self.stats['errors'] += 1
            return False

    def run_scraper(self, urls: List[str]):
        """Run the scraper on a list of URLs"""
        print("🚀 Starting AKC Breed Scraper")
        print("=" * 60)
        print(f"📋 Processing {len(urls)} breed URLs")
        print()
        
        for i, url in enumerate(urls, 1):
            print(f"[{i}/{len(urls)}] Processing breed {i}")
            
            # Scrape breed
            breed_data = self.scrape_breed(url)
            
            if breed_data:
                # Save to database
                self.save_breed(breed_data)
            else:
                self.stats['breeds_skipped'] += 1
            
            # Progress update
            if i % 10 == 0:
                self._print_progress()
        
        self._print_final_report()

    def _print_progress(self):
        """Print progress statistics"""
        print()
        print("📊 Progress Update:")
        print(f"  Processed: {self.stats['urls_processed']}")
        print(f"  New breeds: {self.stats['breeds_new']}")
        print(f"  Updated: {self.stats['breeds_updated']}")
        print(f"  Extraction success: {self.stats['extraction_success']}")
        print()

    def _print_final_report(self):
        """Print final scraping report"""
        print()
        print("=" * 60)
        print("🎯 AKC BREED SCRAPER REPORT")
        print("=" * 60)
        print(f"URLs processed: {self.stats['urls_processed']}")
        print(f"New breeds added: {self.stats['breeds_new']}")
        print(f"Breeds updated: {self.stats['breeds_updated']}")
        print(f"Breeds skipped: {self.stats['breeds_skipped']}")
        print(f"Extraction success: {self.stats['extraction_success']}")
        print(f"Extraction failed: {self.stats['extraction_failed']}")
        print(f"Errors: {self.stats['errors']}")
        
        if self.stats['urls_processed'] > 0:
            success_rate = (self.stats['extraction_success'] / self.stats['urls_processed']) * 100
            print(f"Success rate: {success_rate:.1f}%")
        
        print("=" * 60)
        
        # Save QA report
        if self.qa_data:
            self._save_qa_report()

    def _save_qa_report(self):
        """Save QA report to CSV"""
        import csv
        
        filename = f"akc_breed_qa_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        with open(filename, 'w', newline='') as f:
            if self.qa_data:
                writer = csv.DictWriter(f, fieldnames=self.qa_data[0].keys())
                writer.writeheader()
                writer.writerows(self.qa_data)
        
        print(f"📄 QA report saved to: {filename}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Scrape breed data from AKC')
    parser.add_argument('--urls-file', type=str, default='akc_breed_urls.txt',
                        help='File containing breed URLs to scrape')
    parser.add_argument('--limit', type=int, help='Limit number of breeds to scrape')
    parser.add_argument('--test', action='store_true', help='Run in test mode (5 breeds)')
    
    args = parser.parse_args()
    
    # Initialize scraper
    scraper = AKCBreedScraper()
    
    # Load URLs
    urls = []
    if os.path.exists(args.urls_file):
        with open(args.urls_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    urls.append(line)
    else:
        # Default test URLs
        urls = [
            'https://www.akc.org/dog-breeds/american-bulldog/',
            'https://www.akc.org/dog-breeds/australian-kelpie/',
            'https://www.akc.org/dog-breeds/cairn-terrier/',
            'https://www.akc.org/dog-breeds/german-shorthaired-pointer/',
            'https://www.akc.org/dog-breeds/beagle/'
        ]
        print(f"⚠️  URLs file not found, using {len(urls)} test URLs")
    
    # Apply limits
    if args.test:
        urls = urls[:5]
        print("🧪 Running in test mode (5 breeds)")
    elif args.limit:
        urls = urls[:args.limit]
        print(f"📊 Limited to {args.limit} breeds")
    
    # Run scraper
    scraper.run_scraper(urls)


if __name__ == '__main__':
    main()