#!/usr/bin/env python3
"""
Enhanced Universal Breed Scraper with ScrapingBee Integration
=============================================================

Comprehensive breed data extraction with smart BeautifulSoup → ScrapingBee fallback.
Extracts all physical traits, temperament scores, and detailed content sections.

Usage:
    python3 jobs/universal_breed_scraper_enhanced.py --url https://www.akc.org/dog-breeds/golden-retriever/
"""

import os
import sys
import json
import time
import logging
import re
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
from urllib.parse import quote, urljoin
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import helper functions from existing scraper
try:
    from utils.breed_utils import (
        extract_lifespan,
        normalize_characteristic,
        normalize_friendliness,
        ENERGY_MAPPING,
        SHEDDING_MAPPING,
        TRAINABILITY_MAPPING,
        BARK_LEVEL_MAPPING,
        COAT_LENGTH_MAPPING
    )
except ImportError:
    # Define them locally if import fails
    def extract_lifespan(text: str) -> tuple:
        """Extract lifespan range from text"""
        if not text:
            return None, None
        numbers = re.findall(r'(\d+)', text)
        if numbers:
            if len(numbers) >= 2:
                return int(numbers[0]), int(numbers[1])
            else:
                return int(numbers[0]), int(numbers[0])
        return None, None
    
    def normalize_characteristic(value: str, mapping: dict) -> str:
        """Normalize characteristic value"""
        if not value:
            return None
        value_lower = value.lower()
        for normalized, patterns in mapping.items():
            if any(pattern in value_lower for pattern in patterns):
                return normalized
        return None
    
    def normalize_friendliness(value: str) -> str:
        """Normalize friendliness value"""
        if not value:
            return None
        value_lower = value.lower()
        if any(word in value_lower for word in ['high', 'excellent', 'great']):
            return 'high'
        elif any(word in value_lower for word in ['moderate', 'medium', 'average']):
            return 'medium'
        elif any(word in value_lower for word in ['low', 'poor', 'minimal']):
            return 'low'
        return None
    
    # Default mappings
    ENERGY_MAPPING = {
        'low': ['low', 'calm', 'relaxed'],
        'medium': ['moderate', 'medium', 'average'],
        'high': ['high', 'energetic', 'active'],
        'very_high': ['very high', 'extremely active']
    }
    
    SHEDDING_MAPPING = {
        'minimal': ['minimal', 'low', 'light'],
        'moderate': ['moderate', 'medium', 'average'],
        'heavy': ['heavy', 'high', 'frequent'],
        'seasonal': ['seasonal']
    }
    
    TRAINABILITY_MAPPING = {
        'easy': ['easy', 'high', 'excellent'],
        'moderate': ['moderate', 'medium', 'average'],
        'challenging': ['challenging', 'difficult', 'stubborn']
    }
    
    BARK_LEVEL_MAPPING = {
        'quiet': ['quiet', 'low', 'minimal'],
        'moderate': ['moderate', 'medium', 'average'],
        'vocal': ['vocal', 'high', 'frequent']
    }
    
    COAT_LENGTH_MAPPING = {
        'hairless': ['hairless'],
        'short': ['short'],
        'medium': ['medium'],
        'long': ['long']
    }


class EnhancedUniversalBreedScraper:
    """Enhanced scraper with comprehensive data extraction"""
    
    def __init__(self):
        self.scrapingbee_api_key = os.getenv('SCRAPING_BEE')
        self.scrapingbee_endpoint = "https://app.scrapingbee.com/api/v1/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        self.total_cost_credits = 0
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        if self.scrapingbee_api_key:
            self.logger.info(f"✅ ScrapingBee API key loaded: {self.scrapingbee_api_key[:10]}...")
        else:
            self.logger.warning("⚠️ ScrapingBee API key not found - will use BeautifulSoup only")
    
    def needs_javascript(self, html_content: str) -> bool:
        """Detect if page needs JavaScript rendering"""
        js_indicators = [
            'window.ReactDOM', 'ng-app', 'vue.js', 'data-reactroot',
            'window.angular', 'Loading...', 'Please enable JavaScript',
            'window.Vue', 'window.React', '__NUXT__', 'window.__INITIAL_STATE__'
        ]
        
        # Check for very small body content (likely JS-rendered)
        soup = BeautifulSoup(html_content, 'html.parser')
        body = soup.find('body')
        if body:
            body_text = body.get_text(strip=True)
            if len(body_text) < 200:
                return True
            # Check if most content is in script tags
            scripts = body.find_all('script')
            script_text_len = sum(len(s.get_text()) for s in scripts)
            if script_text_len > len(body_text) * 0.7:
                return True
        
        # Check for JS indicators
        return any(indicator in html_content for indicator in js_indicators)
    
    def fetch_with_beautifulsoup(self, url: str) -> Tuple[Optional[str], bool]:
        """Fetch using BeautifulSoup (free method)"""
        try:
            self.logger.info(f"🔄 Trying BeautifulSoup method: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text, True
        except Exception as e:
            self.logger.warning(f"⚠️ BeautifulSoup failed for {url}: {e}")
            return None, False
    
    def fetch_with_scrapingbee(self, url: str, render_js: bool = True) -> Tuple[Optional[str], bool]:
        """Fetch using ScrapingBee with JavaScript rendering"""
        if not self.scrapingbee_api_key:
            self.logger.error("❌ ScrapingBee API key not found!")
            return None, False
        
        params = {
            'api_key': self.scrapingbee_api_key,
            'url': url,
            'render_js': 'true' if render_js else 'false',
            'premium_proxy': 'false',
            'block_resources': 'false',  # Don't block resources for better extraction
            'wait': '3000'  # Wait 3 seconds for content to load
        }
        
        try:
            self.logger.info(f"🕷️ Using ScrapingBee (JS: {render_js}, Cost: 5 credits): {url}")
            response = requests.get(self.scrapingbee_endpoint, params=params, timeout=60)
            if response.status_code == 200:
                cost = 5 if render_js else 1
                self.total_cost_credits += cost
                self.logger.info(f"✅ ScrapingBee success: {url} (Credits used: {cost})")
                return response.text, True
            else:
                self.logger.error(f"❌ ScrapingBee failed: {response.status_code}")
                return None, False
        except Exception as e:
            self.logger.error(f"❌ ScrapingBee error for {url}: {e}")
            return None, False
    
    def smart_fetch(self, url: str) -> Tuple[Optional[str], str]:
        """Smart fetch with automatic fallback"""
        # First try BeautifulSoup (free)
        html, success = self.fetch_with_beautifulsoup(url)
        
        if success and html:
            # Check if we need JavaScript
            if self.needs_javascript(html):
                self.logger.info(f"⚠️ Page appears to need JavaScript rendering: {url}")
                if self.scrapingbee_api_key:
                    self.logger.info(f"🔄 Falling back to ScrapingBee for: {url}")
                    html_sb, success_sb = self.fetch_with_scrapingbee(url)
                    if success_sb and html_sb:
                        return html_sb, "scrapingbee"
                    else:
                        self.logger.warning(f"⚠️ ScrapingBee also failed, using BeautifulSoup result")
                        return html, "beautifulsoup"
                else:
                    self.logger.warning(f"⚠️ Page needs JS but ScrapingBee not configured")
                    return html, "beautifulsoup"
            else:
                return html, "beautifulsoup"
        else:
            # BeautifulSoup failed, try ScrapingBee if available
            if self.scrapingbee_api_key:
                self.logger.info(f"🔄 BeautifulSoup failed, trying ScrapingBee: {url}")
                html_sb, success_sb = self.fetch_with_scrapingbee(url)
                if success_sb and html_sb:
                    return html_sb, "scrapingbee"
            return None, "failed"
    
    def extract_breed_traits(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract physical and temperament traits from AKC React page"""
        traits = {}
        
        try:
            # AKC React structure: Look for trait elements
            trait_elements = soup.find_all('div', class_=lambda x: x and 'trait' in x.lower() if x else False)
            
            for elem in trait_elements:
                # Extract trait name and value
                label_elem = elem.find(['span', 'div', 'p'], class_=lambda x: x and ('label' in x.lower() or 'title' in x.lower() or 'name' in x.lower()) if x else False)
                value_elem = elem.find(['span', 'div', 'p'], class_=lambda x: x and ('value' in x.lower() or 'level' in x.lower() or 'rating' in x.lower()) if x else False)
                
                if not label_elem:
                    # Try extracting from text content
                    text = elem.get_text(strip=True)
                    if ':' in text:
                        parts = text.split(':', 1)
                        if len(parts) == 2:
                            traits[parts[0].strip()] = parts[1].strip()
                elif label_elem and value_elem:
                    traits[label_elem.get_text(strip=True)] = value_elem.get_text(strip=True)
                elif label_elem:
                    # Value might be in sibling or parent
                    next_sibling = label_elem.find_next_sibling()
                    if next_sibling:
                        traits[label_elem.get_text(strip=True)] = next_sibling.get_text(strip=True)
            
            # Look for breed characteristics section with specific patterns
            breed_char_section = soup.find(['div', 'section'], class_=lambda x: x and ('breed-char' in x.lower() or 'character' in x.lower()) if x else False)
            if breed_char_section:
                # Extract all characteristic items
                char_items = breed_char_section.find_all(['div', 'li', 'span'])
                for item in char_items:
                    text = item.get_text(strip=True)
                    # Height pattern
                    height_match = re.search(r'Height[:\s]*(\d+(?:\.\d+)?)\s*[-to]*\s*(\d+(?:\.\d+)?)\s*inch', text, re.I)
                    if height_match:
                        traits['Height'] = f"{height_match.group(1)}-{height_match.group(2)} inches"
                    # Weight pattern
                    weight_match = re.search(r'Weight[:\s]*(\d+(?:\.\d+)?)\s*[-to]*\s*(\d+(?:\.\d+)?)\s*pound', text, re.I)
                    if weight_match:
                        traits['Weight'] = f"{weight_match.group(1)}-{weight_match.group(2)} pounds"
                    # Life Expectancy pattern
                    life_match = re.search(r'Life[\s]*(?:Expectancy|Span)[:\s]*(\d+)\s*[-to]*\s*(\d+)\s*year', text, re.I)
                    if life_match:
                        traits['Life Expectancy'] = f"{life_match.group(1)}-{life_match.group(2)} years"
                    # Breed Group pattern
                    group_match = re.search(r'Group[:\s]*([A-Za-z\s]+?)(?:\.|$|\n)', text, re.I)
                    if group_match:
                        traits['Breed Group'] = group_match.group(1).strip()
            
            # Extract specific React trait sliders/ratings
            sliders = soup.find_all(['div', 'span'], class_=lambda x: x and ('slider' in x.lower() or 'rating' in x.lower() or 'level' in x.lower()) if x else False)
            for slider in sliders:
                parent = slider.parent
                if parent:
                    parent_text = parent.get_text(strip=True)
                    # Energy Level
                    if 'energy' in parent_text.lower():
                        traits['Energy Level'] = parent_text
                    # Shedding
                    elif 'shed' in parent_text.lower():
                        traits['Shedding'] = parent_text
                    # Trainability
                    elif 'train' in parent_text.lower():
                        traits['Trainability'] = parent_text
                    # Barking
                    elif 'bark' in parent_text.lower():
                        traits['Barking Level'] = parent_text
                    # Friendliness
                    elif any(word in parent_text.lower() for word in ['friendly', 'affection', 'social']):
                        traits['Friendliness'] = parent_text
                    # Grooming
                    elif 'groom' in parent_text.lower():
                        traits['Grooming Needs'] = parent_text
            
        except Exception as e:
            self.logger.error(f"Error extracting traits: {e}")
        
        return traits
    
    def extract_content_sections(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract comprehensive content from AKC React breed page"""
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
            # AKC React structure: Look for sections with specific class patterns
            sections = soup.find_all(['div', 'section'], class_=lambda x: x and ('section' in x.lower() or 'content' in x.lower() or 'article' in x.lower()) if x else False)
            
            for section in sections:
                # Try to identify section by header or content
                header = section.find(['h1', 'h2', 'h3', 'h4', 'h5'])
                if header:
                    header_text = header.get_text(strip=True).lower()
                else:
                    # Try to identify by content
                    header_text = section.get_text(strip=True)[:50].lower()
                
                # Get all text content from section
                section_text = section.get_text(separator=' ', strip=True)
                
                # Skip if section is too short or looks like navigation
                if len(section_text) < 50 or any(skip in section_text.lower() for skip in ['menu', 'nav', 'footer', 'cookie']):
                    continue
                
                # Categorize content based on header or content keywords
                if any(word in header_text for word in ['about', 'overview', 'introduction', 'breed']):
                    content['about'] = (content['about'] + ' ' + section_text).strip()
                elif any(word in header_text for word in ['personality', 'temperament', 'behavior']):
                    content['personality'] = (content['personality'] + ' ' + section_text).strip()
                elif any(word in header_text for word in ['health', 'medical', 'disease', 'condition']):
                    content['health'] = (content['health'] + ' ' + section_text).strip()
                elif any(word in header_text for word in ['care', 'maintenance', 'needs']):
                    content['care'] = (content['care'] + ' ' + section_text).strip()
                elif any(word in header_text for word in ['feed', 'diet', 'nutrition', 'food']):
                    content['feeding'] = (content['feeding'] + ' ' + section_text).strip()
                elif any(word in header_text for word in ['groom', 'coat', 'brush', 'bath']):
                    content['grooming'] = (content['grooming'] + ' ' + section_text).strip()
                elif any(word in header_text for word in ['exercise', 'activity', 'physical', 'play']):
                    content['exercise'] = (content['exercise'] + ' ' + section_text).strip()
                elif any(word in header_text for word in ['train', 'obedience', 'socialize', 'teach']):
                    content['training'] = (content['training'] + ' ' + section_text).strip()
                elif any(word in header_text for word in ['history', 'origin', 'background', 'developed']):
                    content['history'] = (content['history'] + ' ' + section_text).strip()
                else:
                    # If no specific category, check content for keywords
                    if 'originally bred' in section_text.lower() or 'developed in' in section_text.lower():
                        content['history'] = (content['history'] + ' ' + section_text).strip()
                    elif 'training' in section_text.lower() or 'obedience' in section_text.lower():
                        content['training'] = (content['training'] + ' ' + section_text).strip()
                    elif 'health' in section_text.lower() or 'vet' in section_text.lower():
                        content['health'] = (content['health'] + ' ' + section_text).strip()
                    elif len(content['about']) < 500:  # Add to about if it's short
                        content['about'] = (content['about'] + ' ' + section_text).strip()
            
            # If still no content, try to extract from entire page
            if not any(content.values()):
                # Look for any text-rich containers
                text_containers = soup.find_all(['div', 'article', 'section'], recursive=True)
                all_text = []
                for container in text_containers:
                    text = container.get_text(separator=' ', strip=True)
                    if len(text) > 100 and not any(skip in text.lower() for skip in ['cookie', 'privacy', 'terms', 'copyright']):
                        all_text.append(text)
                
                if all_text:
                    combined_text = ' '.join(all_text)
                    content['about'] = combined_text[:2000]  # Limit to 2000 chars
            
            # Clean up content - normalize whitespace and limit length
            for key in content:
                content[key] = ' '.join(content[key].split())[:5000]
            
        except Exception as e:
            self.logger.error(f"Error extracting content sections: {e}")
        
        return content
    
    def map_traits_to_schema(self, traits: Dict[str, str]) -> Dict[str, Any]:
        """Map extracted traits to database schema"""
        mapped = {}
        
        try:
            # Extract height (convert inches to cm)
            height_text = traits.get('Height', '')
            if height_text:
                numbers = re.findall(r'(\d+(?:\.\d+)?)', height_text)
                if numbers:
                    if len(numbers) >= 2:
                        min_inches = float(numbers[0])
                        max_inches = float(numbers[1])
                    else:
                        min_inches = max_inches = float(numbers[0])
                    # Convert to cm (1 inch = 2.54 cm)
                    mapped['height_cm_min'] = round(min_inches * 2.54, 1)
                    mapped['height_cm_max'] = round(max_inches * 2.54, 1)
            
            # Extract weight (convert lbs to kg)
            weight_text = traits.get('Weight', '')
            if weight_text:
                numbers = re.findall(r'(\d+(?:\.\d+)?)', weight_text)
                if numbers:
                    if len(numbers) >= 2:
                        min_lbs = float(numbers[0])
                        max_lbs = float(numbers[1])
                    else:
                        min_lbs = max_lbs = float(numbers[0])
                    # Convert to kg (1 lb = 0.453592 kg)
                    mapped['weight_kg_min'] = round(min_lbs * 0.453592, 1)
                    mapped['weight_kg_max'] = round(max_lbs * 0.453592, 1)
            
            # Extract lifespan
            life_text = traits.get('Life Expectancy', '') or traits.get('Life Span', '')
            if life_text:
                life_min, life_max = extract_lifespan(life_text)
                mapped['lifespan_years_min'] = life_min
                mapped['lifespan_years_max'] = life_max
            
            # Determine size based on weight
            if 'weight_kg_max' in mapped:
                weight_max = mapped['weight_kg_max']
                if weight_max < 10:
                    mapped['size'] = 'small'
                elif weight_max < 25:
                    mapped['size'] = 'medium'
                elif weight_max < 45:
                    mapped['size'] = 'large'
                else:
                    mapped['size'] = 'giant'
            
            # Map temperament traits
            energy_text = traits.get('Energy Level', '')
            if energy_text:
                mapped['energy'] = normalize_characteristic(energy_text, ENERGY_MAPPING)
            
            shedding_text = traits.get('Shedding', '')
            if shedding_text:
                mapped['shedding'] = normalize_characteristic(shedding_text, SHEDDING_MAPPING)
            
            trainability_text = traits.get('Trainability', '')
            if trainability_text:
                mapped['trainability'] = normalize_characteristic(trainability_text, TRAINABILITY_MAPPING)
            
            barking_text = traits.get('Barking Level', '')
            if barking_text:
                mapped['bark_level'] = normalize_characteristic(barking_text, BARK_LEVEL_MAPPING)
            
            # Extract breed group
            mapped['breed_group'] = traits.get('Breed Group', '')
            
        except Exception as e:
            self.logger.error(f"Error mapping traits: {e}")
        
        return mapped
    
    def extract_comprehensive_breed_data(self, html: str, url: str) -> Dict[str, Any]:
        """Extract comprehensive breed data from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract breed slug and display name
        breed_slug = url.rstrip('/').split('/')[-1]
        
        # Try to get display name from page
        display_name = None
        title_elem = soup.find('title')
        if title_elem:
            title_text = title_elem.get_text()
            # AKC format: "Breed Name - American Kennel Club"
            if ' - American Kennel Club' in title_text:
                display_name = title_text.split(' - American Kennel Club')[0].strip()
        
        # Fallback to h1
        if not display_name:
            h1 = soup.find('h1')
            if h1:
                display_name = h1.get_text(strip=True)
        
        # Final fallback
        if not display_name:
            display_name = breed_slug.replace('-', ' ').title()
        
        # Extract traits
        traits = self.extract_breed_traits(soup)
        
        # Extract content sections
        content_sections = self.extract_content_sections(soup)
        
        # Map traits to schema
        mapped_traits = self.map_traits_to_schema(traits)
        
        # Build comprehensive data
        breed_data = {
            'breed_slug': breed_slug,
            'display_name': display_name,
            'akc_url': url,
            'extraction_timestamp': datetime.now().isoformat(),
            'extraction_status': 'success',
            
            # Physical traits
            'size': mapped_traits.get('size'),
            'height_cm_min': mapped_traits.get('height_cm_min'),
            'height_cm_max': mapped_traits.get('height_cm_max'),
            'weight_kg_min': mapped_traits.get('weight_kg_min'),
            'weight_kg_max': mapped_traits.get('weight_kg_max'),
            'lifespan_years_min': mapped_traits.get('lifespan_years_min'),
            'lifespan_years_max': mapped_traits.get('lifespan_years_max'),
            
            # Temperament traits
            'energy': mapped_traits.get('energy'),
            'shedding': mapped_traits.get('shedding'),
            'trainability': mapped_traits.get('trainability'),
            'bark_level': mapped_traits.get('bark_level'),
            'breed_group': mapped_traits.get('breed_group'),
            
            # Content sections
            'about': content_sections.get('about', ''),
            'personality': content_sections.get('personality', ''),
            'health': content_sections.get('health', ''),
            'care': content_sections.get('care', ''),
            'feeding': content_sections.get('feeding', ''),
            'grooming': content_sections.get('grooming', ''),
            'exercise': content_sections.get('exercise', ''),
            'training': content_sections.get('training', ''),
            'history': content_sections.get('history', ''),
            
            # Raw data for debugging
            'raw_traits': traits,
            
            # Metadata
            'has_physical_data': bool(mapped_traits.get('weight_kg_max') or mapped_traits.get('height_cm_max')),
            'has_temperament_data': bool(mapped_traits.get('energy') or mapped_traits.get('trainability')),
            'has_content': bool(any(content_sections.values())),
            
            # Combine all content for comprehensive field
            'comprehensive_content': json.dumps({
                'traits': traits,
                'content': content_sections,
                'mapped': mapped_traits
            }, indent=2)
        }
        
        return breed_data
    
    def scrape_breed(self, url: str) -> Optional[Dict[str, Any]]:
        """Main method to scrape a breed page - fetches and extracts all data"""
        try:
            # Fetch HTML using smart fetch with fallback
            html, method = self.smart_fetch(url)
            
            if not html:
                self.logger.error(f"Failed to fetch content from {url}")
                return None
            
            # Extract comprehensive breed data
            breed_data = self.extract_comprehensive_breed_data(html, url)
            
            # Add metadata
            breed_data['scraping_method'] = method
            breed_data['scrapingbee_cost'] = 5 if method == 'scrapingbee' else 0
            
            return breed_data
            
        except Exception as e:
            self.logger.error(f"Error scraping breed from {url}: {e}")
            return None


def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Enhanced Universal Breed Scraper with comprehensive extraction'
    )
    parser.add_argument('--url', required=True, help='Breed page URL to scrape')
    parser.add_argument('--output', help='Output JSON file (optional)')
    parser.add_argument('--force-scrapingbee', action='store_true',
                       help='Force use of ScrapingBee even if BeautifulSoup works')
    
    args = parser.parse_args()
    
    # Initialize scraper
    scraper = EnhancedUniversalBreedScraper()
    
    print(f"\n{'='*80}")
    print(f"🚀 ENHANCED UNIVERSAL BREED SCRAPER")
    print(f"{'='*80}")
    print(f"URL: {args.url}")
    print(f"ScrapingBee: {'✅ Configured' if scraper.scrapingbee_api_key else '❌ Not configured'}")
    print(f"{'='*80}\n")
    
    # Fetch content
    if args.force_scrapingbee and scraper.scrapingbee_api_key:
        html, method = scraper.fetch_with_scrapingbee(args.url)
        method = 'scrapingbee' if html else 'failed'
    else:
        html, method = scraper.smart_fetch(args.url)
    
    if not html:
        print(f"❌ Failed to fetch content from {args.url}")
        sys.exit(1)
    
    print(f"\n✅ Content fetched via: {method}")
    print(f"📊 HTML size: {len(html)} characters")
    
    # Extract breed data
    breed_data = scraper.extract_comprehensive_breed_data(html, args.url)
    breed_data['scraping_method'] = method
    breed_data['scrapingbee_cost'] = 5 if method == 'scrapingbee' else 0
    
    # Display results
    print(f"\n{'='*80}")
    print(f"📋 EXTRACTED BREED DATA")
    print(f"{'='*80}")
    
    print(f"\n🏷️ Basic Info:")
    print(f"  Breed: {breed_data['display_name']}")
    print(f"  Slug: {breed_data['breed_slug']}")
    print(f"  URL: {breed_data['akc_url']}")
    
    print(f"\n📏 Physical Traits:")
    if breed_data.get('height_cm_min'):
        print(f"  Height: {breed_data['height_cm_min']}-{breed_data['height_cm_max']} cm")
    if breed_data.get('weight_kg_min'):
        print(f"  Weight: {breed_data['weight_kg_min']}-{breed_data['weight_kg_max']} kg")
    if breed_data.get('lifespan_years_min'):
        print(f"  Lifespan: {breed_data['lifespan_years_min']}-{breed_data['lifespan_years_max']} years")
    if breed_data.get('size'):
        print(f"  Size: {breed_data['size']}")
    
    print(f"\n🐕 Temperament:")
    if breed_data.get('energy'):
        print(f"  Energy: {breed_data['energy']}")
    if breed_data.get('trainability'):
        print(f"  Trainability: {breed_data['trainability']}")
    if breed_data.get('shedding'):
        print(f"  Shedding: {breed_data['shedding']}")
    if breed_data.get('bark_level'):
        print(f"  Barking: {breed_data['bark_level']}")
    
    print(f"\n📝 Content Sections:")
    for section in ['about', 'personality', 'health', 'care', 'feeding', 'grooming', 'exercise', 'training', 'history']:
        content = breed_data.get(section, '')
        if content:
            print(f"  {section.title()}: {len(content)} characters")
    
    print(f"\n✅ Data Quality:")
    print(f"  Has Physical Data: {breed_data['has_physical_data']}")
    print(f"  Has Temperament Data: {breed_data['has_temperament_data']}")
    print(f"  Has Content: {breed_data['has_content']}")
    
    print(f"\n💰 Cost:")
    print(f"  ScrapingBee Credits: {breed_data['scrapingbee_cost']}")
    print(f"  Estimated Cost: ${breed_data['scrapingbee_cost'] * 0.001:.3f}")
    
    # Save to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(breed_data, f, indent=2)
        print(f"\n💾 Data saved to: {args.output}")
    
    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    main()