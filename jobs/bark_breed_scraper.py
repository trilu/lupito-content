#!/usr/bin/env python3
"""
Bark Breed Scraper
Adapted from PFX scraper for breed content extraction
Scrapes breed data from external sources and stores in Supabase
"""
import os
import sys
import time
import random
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import hashlib
import csv

import requests
from supabase import create_client, Client
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from etl.normalize_breeds import (
    normalize_characteristic, extract_lifespan, extract_weight_range,
    extract_height_range, normalize_friendliness, resolve_breed_slug,
    generate_breed_fingerprint, parse_breed_sections,
    SIZE_MAPPING, ENERGY_MAPPING, COAT_LENGTH_MAPPING,
    SHEDDING_MAPPING, TRAINABILITY_MAPPING, BARK_LEVEL_MAPPING
)

load_dotenv()

class BarkBreedScraper:
    def __init__(self):
        """Initialize the Bark breed scraper"""
        self.session = self._setup_session()
        self.supabase = self._setup_supabase()
        
        # Configuration (inherited from PFX scraper patterns)
        self.config = {
            'rate_limit_seconds': 2.0,  # Be respectful to Dogo
            'timeout': 30,
            'batch_size': 5,  # Smaller batches for seed testing
            'storage_bucket': 'dog-food',  # Reuse existing bucket
            'image_timeout': 15
        }
        
        # Statistics tracking
        self.stats = {
            'urls_processed': 0,
            'breeds_new': 0,
            'breeds_updated': 0,
            'breeds_skipped': 0,
            'images_downloaded': 0,
            'images_failed': 0,
            'text_sections_parsed': 0,
            'vocab_mapping_failures': 0,
            'errors': 0
        }
        
        # QA tracking for report
        self.qa_data = []

    def _setup_session(self) -> requests.Session:
        """Setup requests session with headers"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; LupitoBreedBot/1.0; +https://lupito.pet)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        return session

    def _setup_supabase(self) -> Client:
        """Setup Supabase client"""
        return create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_KEY')
        )

    def load_breed_urls(self, urls_file: str) -> List[str]:
        """Load breed URLs from file"""
        urls = []
        try:
            with open(urls_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        urls.append(line)
            print(f"📋 Loaded {len(urls)} breed URLs from {urls_file}")
        except FileNotFoundError:
            print(f"❌ URLs file not found: {urls_file}")
        
        return urls

    def extract_breed_characteristics(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract ALL breed characteristics and content from Dogo page"""
        breed_data = {}
        
        try:
            # Extract breed name from URL or page title
            breed_name = url.split('/')[-1].replace('-', ' ').title()
            page_title = soup.find('title')
            if page_title:
                title_text = page_title.get_text()
                if 'dog breed' in title_text.lower():
                    breed_name = title_text.split(' - ')[0].strip()
            
            breed_data['breed_name'] = breed_name
            
            # Extract ALL content sections for comprehensive storage
            comprehensive_content = self._extract_all_content_sections(soup)
            
            # Extract structured quick facts
            quick_facts = self._extract_quick_facts(soup)
            
            # Use quick facts to populate normalized fields
            characteristics = {}
            
            # Size extraction from quick facts or content
            if 'size' in quick_facts:
                characteristics['size'] = quick_facts['size']
            elif 'Size' in comprehensive_content.get('quick_facts', {}):
                characteristics['size'] = comprehensive_content['quick_facts']['Size']
            
            # Energy extraction
            if 'energy_level' in quick_facts:
                characteristics['energy'] = quick_facts['energy_level']
            elif 'Energy Level' in comprehensive_content.get('quick_facts', {}):
                characteristics['energy'] = comprehensive_content['quick_facts']['Energy Level']
            
            # Coat length extraction
            if 'coat_length' in quick_facts:
                characteristics['coat_length'] = quick_facts['coat_length']
            elif 'Coat Length' in comprehensive_content.get('quick_facts', {}):
                characteristics['coat_length'] = comprehensive_content['quick_facts']['Coat Length']
            
            # Shedding extraction
            if 'shedding_level' in quick_facts:
                characteristics['shedding'] = quick_facts['shedding_level']
            elif 'Shedding Level' in comprehensive_content.get('quick_facts', {}):
                characteristics['shedding'] = comprehensive_content['quick_facts']['Shedding Level']
            
            # Training extraction
            if 'training_difficulty' in quick_facts:
                characteristics['trainability'] = quick_facts['training_difficulty']
            elif 'Training Difficulty' in comprehensive_content.get('quick_facts', {}):
                characteristics['trainability'] = comprehensive_content['quick_facts']['Training Difficulty']
            
            # Barking extraction - look for watchdog ability as proxy
            if 'watchdog_ability' in quick_facts:
                characteristics['bark_level'] = quick_facts['watchdog_ability']
            elif 'Watchdog Ability' in comprehensive_content.get('quick_facts', {}):
                characteristics['bark_level'] = comprehensive_content['quick_facts']['Watchdog Ability']
            
            # If structured data not found, try to extract from full text
            if not characteristics:
                full_text = soup.get_text().lower()
                
                # Size patterns
                size_text = self._extract_nearby_text(full_text, ['size:', 'small', 'medium', 'large', 'giant', 'toy'])
                if size_text:
                    characteristics['size'] = size_text
                
                # Energy patterns  
                energy_text = self._extract_nearby_text(full_text, ['energy:', 'energy level:', 'activity:', 'exercise:'])
                if energy_text:
                    characteristics['energy'] = energy_text
            
            # Normalize characteristics using controlled vocabularies
            breed_data.update({
                'size': normalize_characteristic(characteristics.get('size', ''), SIZE_MAPPING),
                'energy': normalize_characteristic(characteristics.get('energy', ''), ENERGY_MAPPING),
                'coat_length': normalize_characteristic(characteristics.get('coat_length', ''), COAT_LENGTH_MAPPING),
                'shedding': normalize_characteristic(characteristics.get('shedding', ''), SHEDDING_MAPPING),
                'trainability': normalize_characteristic(characteristics.get('trainability', ''), TRAINABILITY_MAPPING),
                'bark_level': normalize_characteristic(characteristics.get('bark_level', ''), BARK_LEVEL_MAPPING),
            })
            
            # Extract numeric ranges from physical characteristics
            physical_chars = comprehensive_content.get('physical_characteristics', {})
            full_text = soup.get_text()
            
            # Try to extract from structured content first
            if 'Height' in physical_chars:
                height_min, height_max = extract_height_range(physical_chars['Height'])
            else:
                height_min, height_max = extract_height_range(full_text)
            
            if 'Weight' in physical_chars:
                weight_min, weight_max = extract_weight_range(physical_chars['Weight'])
            else:
                weight_min, weight_max = extract_weight_range(full_text)
            
            if 'Lifespan' in quick_facts:
                lifespan_min, lifespan_max = extract_lifespan(quick_facts.get('Lifespan', ''))
            else:
                lifespan_min, lifespan_max = extract_lifespan(full_text)
            
            breed_data.update({
                'lifespan_years_min': lifespan_min,
                'lifespan_years_max': lifespan_max,
                'weight_kg_min': weight_min,
                'weight_kg_max': weight_max,
                'height_cm_min': height_min,
                'height_cm_max': height_max,
                'friendliness_to_dogs': normalize_friendliness(self._extract_nearby_text(full_text, ['dog friendly', 'other dogs'])),
                'friendliness_to_humans': normalize_friendliness(self._extract_nearby_text(full_text, ['people friendly', 'strangers', 'family']))
            })
            
            # Add comprehensive content to breed_data for storage
            breed_data['comprehensive_content'] = comprehensive_content
            
            # Track vocab mapping success
            mapped_fields = [v for v in [breed_data.get('size'), breed_data.get('energy'), 
                                       breed_data.get('trainability')] if v]
            if len(mapped_fields) < 2:  # Less than 2 successful mappings
                self.stats['vocab_mapping_failures'] += 1
            
        except Exception as e:
            print(f"    ⚠️  Error extracting characteristics: {e}")
            breed_data['breed_name'] = url.split('/')[-1].replace('-', ' ').title()
        
        return breed_data

    def _extract_nearby_text(self, full_text: str, keywords: List[str], context_chars: int = 100) -> str:
        """Extract text near keywords for characteristic detection"""
        for keyword in keywords:
            pos = full_text.lower().find(keyword.lower())
            if pos != -1:
                start = max(0, pos - context_chars//2)
                end = min(len(full_text), pos + len(keyword) + context_chars//2)
                return full_text[start:end]
        return ""
    
    def _extract_all_content_sections(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract ALL content sections from the page"""
        content = {
            'quick_facts': {},
            'physical_characteristics': {},
            'temperament': {},
            'exercise_requirements': {},
            'grooming': {},
            'health': {},
            'training': {},
            'history': {},
            'living_conditions': {},
            'nutrition': {},
            'popular_names': [],
            'raw_sections': {}  # Store any other sections we find
        }
        
        try:
            # Look for all section headers and their content
            headers = soup.find_all(['h1', 'h2', 'h3', 'h4'])
            
            for header in headers:
                header_text = header.get_text().strip()
                section_content = self._extract_section_content(header)
                
                # Map to appropriate category
                header_lower = header_text.lower()
                
                if 'quick fact' in header_lower or 'key fact' in header_lower:
                    content['quick_facts'] = self._parse_key_value_section(section_content)
                elif 'physical' in header_lower or 'appearance' in header_lower:
                    content['physical_characteristics'] = self._parse_key_value_section(section_content)
                elif 'temperament' in header_lower or 'personality' in header_lower:
                    content['temperament'] = section_content
                elif 'exercise' in header_lower or 'activity' in header_lower:
                    content['exercise_requirements'] = section_content
                elif 'grooming' in header_lower or 'maintenance' in header_lower:
                    content['grooming'] = section_content
                elif 'health' in header_lower:
                    content['health'] = section_content
                elif 'training' in header_lower:
                    content['training'] = section_content
                elif 'history' in header_lower or 'origin' in header_lower:
                    content['history'] = section_content
                elif 'living' in header_lower or 'environment' in header_lower:
                    content['living_conditions'] = section_content
                elif 'nutrition' in header_lower or 'feeding' in header_lower or 'diet' in header_lower:
                    content['nutrition'] = section_content
                elif 'name' in header_lower:
                    content['popular_names'] = self._extract_list_items(header)
                else:
                    # Store any other sections we find
                    content['raw_sections'][header_text] = section_content
            
            # Also look for specific data elements
            # Quick facts often in tables or definition lists
            tables = soup.find_all('table')
            for table in tables:
                facts = self._parse_table_facts(table)
                if facts:
                    content['quick_facts'].update(facts)
            
            # Definition lists
            dl_elements = soup.find_all('dl')
            for dl in dl_elements:
                facts = self._parse_definition_list(dl)
                if facts:
                    content['quick_facts'].update(facts)
            
        except Exception as e:
            print(f"      ⚠️  Error extracting content sections: {e}")
        
        return content
    
    def _extract_section_content(self, header_element) -> str:
        """Extract all text content following a header until the next header"""
        content = []
        current = header_element.next_sibling
        
        while current:
            if hasattr(current, 'name'):
                # Stop at next header
                if current.name in ['h1', 'h2', 'h3', 'h4']:
                    break
                # Get text from element
                text = current.get_text().strip()
                if text:
                    content.append(text)
            elif isinstance(current, str):
                text = current.strip()
                if text:
                    content.append(text)
            
            current = current.next_sibling
        
        return ' '.join(content)
    
    def _parse_key_value_section(self, text: str) -> Dict[str, str]:
        """Parse text that contains key:value pairs"""
        result = {}
        lines = text.split('\n')
        
        for line in lines:
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    if key and value:
                        result[key] = value
        
        return result
    
    def _extract_list_items(self, header_element) -> List[str]:
        """Extract list items following a header"""
        items = []
        current = header_element.next_sibling
        
        while current:
            if hasattr(current, 'name'):
                if current.name in ['h1', 'h2', 'h3', 'h4']:
                    break
                elif current.name in ['ul', 'ol']:
                    list_items = current.find_all('li')
                    for li in list_items:
                        text = li.get_text().strip()
                        if text:
                            items.append(text)
            current = current.next_sibling
        
        return items
    
    def _parse_table_facts(self, table) -> Dict[str, str]:
        """Parse facts from a table element"""
        facts = {}
        rows = table.find_all('tr')
        
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                key = cells[0].get_text().strip()
                value = cells[1].get_text().strip()
                if key and value:
                    facts[key] = value
        
        return facts
    
    def _parse_definition_list(self, dl) -> Dict[str, str]:
        """Parse facts from a definition list"""
        facts = {}
        terms = dl.find_all('dt')
        definitions = dl.find_all('dd')
        
        for term, definition in zip(terms, definitions):
            key = term.get_text().strip()
            value = definition.get_text().strip()
            if key and value:
                facts[key] = value
        
        return facts
    
    def _extract_quick_facts(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract quick facts in a structured way"""
        facts = {}
        
        try:
            # Look for common patterns in Dogo pages
            # Try to find quick facts section
            quick_facts_selectors = [
                '.quick-facts',
                '[class*="quick-fact"]',
                '[class*="breed-fact"]',
                '.breed-info',
                '[class*="characteristic"]'
            ]
            
            for selector in quick_facts_selectors:
                elements = soup.select(selector)
                for elem in elements:
                    # Try to extract key-value pairs
                    text = elem.get_text()
                    parsed = self._parse_key_value_section(text)
                    facts.update(parsed)
            
            # Also check for specific data attributes or meta tags
            meta_tags = soup.find_all('meta', attrs={'property': True})
            for meta in meta_tags:
                prop = meta.get('property', '')
                content = meta.get('content', '')
                if 'breed' in prop.lower() or 'dog' in prop.lower():
                    key = prop.split(':')[-1].replace('_', ' ').title()
                    facts[key] = content
        
        except Exception as e:
            print(f"      ⚠️  Error extracting quick facts: {e}")
        
        return facts

    def extract_breed_image(self, soup: BeautifulSoup, url: str) -> Optional[str]:
        """Extract hero breed image from page"""
        try:
            # Look for breed images
            image_selectors = [
                'img[alt*="breed"]',
                'img[src*="breed"]',
                '.hero img',
                '.breed-image img',
                'main img:first-of-type'
            ]
            
            for selector in image_selectors:
                img = soup.select_one(selector)
                if img:
                    src = img.get('src') or img.get('data-src')
                    if src:
                        # Make absolute URL
                        if src.startswith('//'):
                            src = 'https:' + src
                        elif src.startswith('/'):
                            src = 'https://dogo.app' + src
                        
                        return src
            
            return None
            
        except Exception as e:
            print(f"    ⚠️  Error extracting image: {e}")
            return None

    def download_and_store_image(self, image_url: str, breed_slug: str) -> Optional[str]:
        """Download image and store in Supabase bucket"""
        try:
            filename = f"{breed_slug}.jpg"
            
            print(f"    📥 Downloading image: {image_url}")
            
            # Check if file already exists
            try:
                existing = self.supabase.storage.from_(self.config['storage_bucket']).list(path="breeds/")
                if any(file.get('name', '') == filename for file in existing):
                    print(f"    🔄 Image already exists: {filename}")
                    bucket_url = self.supabase.storage.from_(self.config['storage_bucket']).get_public_url(f"breeds/{filename}")
                    return bucket_url
            except:
                pass
            
            # Download image
            response = self.session.get(image_url, timeout=self.config['image_timeout'])
            response.raise_for_status()
            
            if len(response.content) == 0:
                print(f"    ⚠️  Empty image file")
                return None
            
            self.stats['images_downloaded'] += 1
            
            # Upload to Supabase storage in breeds/ folder
            upload_result = self.supabase.storage.from_(self.config['storage_bucket']).upload(
                f"breeds/{filename}",
                response.content,
                file_options={
                    'content-type': 'image/jpeg',
                    'cache-control': '3600'
                }
            )
            
            # Get public URL
            bucket_url = self.supabase.storage.from_(self.config['storage_bucket']).get_public_url(f"breeds/{filename}")
            print(f"    ✅ Image uploaded: {bucket_url}")
            
            return bucket_url
            
        except Exception as e:
            print(f"    ❌ Image processing failed: {e}")
            self.stats['images_failed'] += 1
            return None

    def process_breed(self, breed_url: str) -> bool:
        """Process a single breed URL"""
        try:
            print(f"  🐕 Processing: {breed_url}")
            
            # Rate limiting
            time.sleep(self.config['rate_limit_seconds'] + random.uniform(-0.3, 0.3))
            
            # Fetch HTML
            response = self.session.get(breed_url, timeout=self.config['timeout'])
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Generate fingerprint
            raw_fingerprint = hashlib.md5(response.text.encode()).hexdigest()
            
            # Check if already processed
            existing_raw = self.supabase.table('breed_raw')\
                .select('fingerprint')\
                .eq('source_url', breed_url)\
                .execute()
            
            if existing_raw.data and existing_raw.data[0]['fingerprint'] == raw_fingerprint:
                print(f"    ⏭️  Already processed (same fingerprint)")
                self.stats['breeds_skipped'] += 1
                return True
            
            # Extract breed characteristics
            breed_data = self.extract_breed_characteristics(soup, breed_url)
            
            # Resolve breed slug and aliases
            breed_slug, display_name, aliases = resolve_breed_slug(breed_data['breed_name'])
            breed_data.update({
                'breed_slug': breed_slug,
                'display_name': display_name,
                'aliases': aliases
            })
            
            # Parse narrative sections
            sections = parse_breed_sections(response.text)
            self.stats['text_sections_parsed'] += len([s for s in sections.values() if s])
            
            # Skip image extraction and downloading per user request
            image_public_url = None
            # image_url = self.extract_breed_image(soup, breed_url)
            # if image_url:
            #     image_public_url = self.download_and_store_image(image_url, breed_slug)
            
            # Save to database with comprehensive content
            self._save_breed_data(breed_url, response.text, raw_fingerprint, breed_data, sections, image_public_url)
            
            # Add to QA data
            self.qa_data.append({
                'breed_slug': breed_slug,
                'display_name': display_name,
                'size': breed_data.get('size'),
                'energy': breed_data.get('energy'),
                'sections_count': sum(1 for s in sections.values() if s),
                'has_image': bool(image_public_url),
                'url': breed_url
            })
            
            print(f"    ✅ Processed breed: {display_name}")
            self.stats['urls_processed'] += 1
            return True
            
        except Exception as e:
            print(f"    ❌ Error processing breed: {e}")
            self.stats['errors'] += 1
            return False

    def _save_breed_data(self, url: str, html: str, fingerprint: str, breed_data: Dict, 
                        sections: Dict, image_url: Optional[str]):
        """Save breed data to database tables including comprehensive content"""
        try:
            # Extract comprehensive content for storage
            comprehensive_content = breed_data.pop('comprehensive_content', {})
            
            # FIRST: Save normalized breed data to breeds_details table (must exist before breed_raw)
            breeds_details_data = {
                'breed_slug': breed_data['breed_slug'],
                'display_name': breed_data['display_name'],
                'aliases': breed_data['aliases'],
                'size': breed_data.get('size'),
                'energy': breed_data.get('energy'),
                'coat_length': breed_data.get('coat_length'),
                'shedding': breed_data.get('shedding'),
                'trainability': breed_data.get('trainability'),
                'bark_level': breed_data.get('bark_level'),
                'lifespan_years_min': breed_data.get('lifespan_years_min'),
                'lifespan_years_max': breed_data.get('lifespan_years_max'),
                'weight_kg_min': breed_data.get('weight_kg_min'),
                'weight_kg_max': breed_data.get('weight_kg_max'),
                'height_cm_min': breed_data.get('height_cm_min'),
                'height_cm_max': breed_data.get('height_cm_max'),
                'origin': breed_data.get('origin'),
                'friendliness_to_dogs': breed_data.get('friendliness_to_dogs'),
                'friendliness_to_humans': breed_data.get('friendliness_to_humans'),
                'comprehensive_content': comprehensive_content,  # Store ALL extracted content
                'updated_at': datetime.now().isoformat()
            }
            
            # Check if breed exists in breeds_details
            existing_breed = self.supabase.table('breeds_details')\
                .select('breed_slug')\
                .eq('breed_slug', breed_data['breed_slug'])\
                .execute()
            
            if existing_breed.data:
                # Update existing
                self.supabase.table('breeds_details')\
                    .update(breeds_details_data)\
                    .eq('breed_slug', breed_data['breed_slug'])\
                    .execute()
                self.stats['breeds_updated'] += 1
            else:
                # Insert new
                self.supabase.table('breeds_details')\
                    .insert(breeds_details_data)\
                    .execute()
                self.stats['breeds_new'] += 1
            
            # SECOND: Save raw HTML (now that breeds_details exists)
            raw_data = {
                'source_url': url,
                'raw_html': html,
                'fingerprint': fingerprint,
                'breed_slug': breed_data['breed_slug'],
                'last_seen_at': datetime.now().isoformat()
            }
            
            # Upsert raw data
            self.supabase.table('breed_raw')\
                .upsert(raw_data, on_conflict='source_url')\
                .execute()
            
            # Save text content as draft version with enhanced sections
            # Merge parsed sections with comprehensive content
            enhanced_sections = sections.copy()
            
            # Add comprehensive content sections to the text version
            if comprehensive_content:
                enhanced_sections.update({
                    'quick_facts': comprehensive_content.get('quick_facts', {}),
                    'exercise_requirements': comprehensive_content.get('exercise_requirements', ''),
                    'living_conditions': comprehensive_content.get('living_conditions', ''),
                    'nutrition': comprehensive_content.get('nutrition', ''),
                    'history': comprehensive_content.get('history', ''),
                    'physical_characteristics': comprehensive_content.get('physical_characteristics', {}),
                    'popular_names': comprehensive_content.get('popular_names', []),
                    'raw_sections': comprehensive_content.get('raw_sections', {})
                })
            
            text_data = {
                'breed_slug': breed_data['breed_slug'],
                'language': 'en',
                'sections': enhanced_sections,
                'status': 'draft',
                'source': 'bark',
                'created_at': datetime.now().isoformat()
            }
            
            self.supabase.table('breed_text_versions')\
                .insert(text_data)\
                .execute()
            
            # Save image if available
            if image_url:
                image_data = {
                    'breed_slug': breed_data['breed_slug'],
                    'image_public_url': image_url,
                    'attribution': 'bark',
                    'is_primary': True,
                    'created_at': datetime.now().isoformat()
                }
                
                self.supabase.table('breed_images')\
                    .insert(image_data)\
                    .execute()
            
        except Exception as e:
            print(f"    ❌ Database save failed: {e}")
            raise

    def generate_qa_report(self, output_file: str = 'breed_qa_report.csv'):
        """Generate QA report CSV"""
        try:
            with open(output_file, 'w', newline='') as f:
                if not self.qa_data:
                    return
                
                writer = csv.DictWriter(f, fieldnames=self.qa_data[0].keys())
                writer.writeheader()
                
                # Limit to 10 rows as requested
                for row in self.qa_data[:10]:
                    writer.writerow(row)
            
            print(f"📊 QA report saved: {output_file}")
            
        except Exception as e:
            print(f"❌ QA report failed: {e}")

    def run_harvest(self, urls_file: str):
        """Run the breed harvesting process"""
        print("🚀 Starting Bark Breed Harvest")
        print("=" * 60)
        
        # Load URLs
        urls = self.load_breed_urls(urls_file)
        if not urls:
            print("❌ No URLs to process")
            return
        
        print(f"\n📋 Processing {len(urls)} breed URLs...")
        print("=" * 60)
        
        # Process each breed
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}]", end=" ")
            self.process_breed(url)
        
        # Generate reports
        self._print_final_report()
        self.generate_qa_report()

    def _print_final_report(self):
        """Print harvest summary report"""
        print("\n" + "=" * 60)
        print("🎯 BARK BREED HARVEST REPORT")
        print("=" * 60)
        print(f"URLs processed:          {self.stats['urls_processed']}")
        print(f"Breeds new:              {self.stats['breeds_new']}")
        print(f"Breeds updated:          {self.stats['breeds_updated']}")
        print(f"Breeds skipped:          {self.stats['breeds_skipped']}")
        print(f"Images downloaded:       {self.stats['images_downloaded']}")
        print(f"Images failed:           {self.stats['images_failed']}")
        print(f"Text sections parsed:    {self.stats['text_sections_parsed']}")
        print(f"Vocab mapping failures:  {self.stats['vocab_mapping_failures']}")
        print(f"Errors encountered:      {self.stats['errors']}")
        
        if self.stats['urls_processed'] > 0:
            success_rate = (self.stats['urls_processed'] / len(self.qa_data)) * 100 if self.qa_data else 0
            image_rate = (self.stats['images_downloaded'] / self.stats['urls_processed']) * 100
            vocab_rate = 100 - (self.stats['vocab_mapping_failures'] / self.stats['urls_processed']) * 100
            
            print(f"\nProcessing success rate: {success_rate:.1f}%")
            print(f"Image download rate:     {image_rate:.1f}%")
            print(f"Vocab mapping rate:      {vocab_rate:.1f}%")
        
        print("=" * 60)

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Scrape breed data from Dogo.app')
    parser.add_argument('--urls', required=True, help='File containing breed URLs')
    
    args = parser.parse_args()
    
    scraper = BarkBreedScraper()
    scraper.run_harvest(args.urls)

if __name__ == '__main__':
    main()