#!/usr/bin/env python3
"""
Universal Breed Scraper - Supports both BeautifulSoup and ScrapingBee
=======================================================================

This scraper can handle:
1. Static websites (BeautifulSoup + requests) - 0 credits cost
2. JavaScript-heavy sites (ScrapingBee API) - 5 credits per request

Features:
- Automatic fallback from BeautifulSoup to ScrapingBee
- Smart detection of JavaScript-dependent sites
- Cost optimization (tries free method first)
- Comprehensive error handling and logging
- Support for AKC breeds and future JavaScript sites

Usage:
    python universal_breed_scraper.py --urls-file urls.txt [--force-scrapingbee]
"""

import os
import sys
import time
import json
import logging
import argparse
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote, urljoin
import re

# Third-party imports
try:
    from bs4 import BeautifulSoup
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Missing required packages: {e}")
    print("Install with: pip install beautifulsoup4 python-dotenv requests")
    sys.exit(1)

# Load environment variables
load_dotenv()

class UniversalBreedScraper:
    def __init__(self):
        self.scrapingbee_api_key = os.getenv('SCRAPING_BEE')
        self.scrapingbee_endpoint = "https://app.scrapingbee.com/api/v1/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        # Tracking
        self.scrapingbee_requests = 0
        self.beautifulsoup_requests = 0
        self.total_cost_credits = 0
        
        self.setup_logging()
        
        if not self.scrapingbee_api_key:
            logging.warning("SCRAPING_BEE API key not found in environment. ScrapingBee features will be disabled.")
        else:
            logging.info(f"✅ ScrapingBee API key loaded: {self.scrapingbee_api_key[:8]}...")

    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('universal_scraper.log'),
                logging.StreamHandler()
            ]
        )

    def fetch_with_beautifulsoup(self, url: str, timeout: int = 30) -> Tuple[Optional[str], bool]:
        """
        Fetch URL using BeautifulSoup + requests (free method)
        
        Returns:
            Tuple[Optional[str], bool]: (HTML content, success)
        """
        try:
            logging.info(f"🔄 Trying BeautifulSoup method: {url}")
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            
            self.beautifulsoup_requests += 1
            
            # Check if content looks like it needs JavaScript
            if self.needs_javascript(response.text):
                logging.warning(f"⚠️  Page appears to need JavaScript rendering: {url}")
                return response.text, False  # Return content but mark as potentially incomplete
            
            logging.info(f"✅ BeautifulSoup success: {url}")
            return response.text, True
            
        except requests.RequestException as e:
            logging.error(f"❌ BeautifulSoup failed for {url}: {e}")
            return None, False

    def fetch_with_scrapingbee(self, url: str, render_js: bool = True, timeout: int = 30) -> Tuple[Optional[str], bool]:
        """
        Fetch URL using ScrapingBee API (paid method)
        
        Args:
            url: Target URL to scrape
            render_js: Enable JavaScript rendering (default: True, costs 5 credits)
            timeout: Request timeout in seconds
            
        Returns:
            Tuple[Optional[str], bool]: (HTML content, success)
        """
        if not self.scrapingbee_api_key:
            logging.error("❌ ScrapingBee API key not available")
            return None, False
            
        try:
            credits_cost = 5 if render_js else 1
            logging.info(f"🕷️  Using ScrapingBee (JS: {render_js}, Cost: {credits_cost} credits): {url}")
            
            params = {
                'api_key': self.scrapingbee_api_key,
                'url': url,
                'render_js': str(render_js).lower(),
                'premium_proxy': 'false',  # Save costs
                'block_resources': 'true',  # Block images/css to speed up
            }
            
            response = requests.get(self.scrapingbee_endpoint, params=params, timeout=timeout)
            
            if response.status_code == 200:
                self.scrapingbee_requests += 1
                self.total_cost_credits += credits_cost
                logging.info(f"✅ ScrapingBee success: {url} (Credits used: {credits_cost})")
                return response.text, True
            elif response.status_code == 422:
                logging.error(f"❌ ScrapingBee error 422: Invalid parameters for {url}")
                return None, False
            elif response.status_code == 401:
                logging.error(f"❌ ScrapingBee error 401: Invalid API key")
                return None, False
            else:
                logging.error(f"❌ ScrapingBee error {response.status_code}: {response.text[:200]}")
                return None, False
                
        except requests.RequestException as e:
            logging.error(f"❌ ScrapingBee request failed for {url}: {e}")
            return None, False

    def needs_javascript(self, html_content: str) -> bool:
        """
        Heuristic to detect if a page needs JavaScript rendering
        
        Args:
            html_content: Raw HTML content
            
        Returns:
            bool: True if page likely needs JavaScript
        """
        # Check for common indicators
        js_indicators = [
            'window.ReactDOM',
            'ng-app',  # Angular
            'vue.js',  # Vue.js
            'data-reactroot',  # React
            'window.angular',
            'document.createElement',
            'dynamically loaded',
            'Loading...',
            'Please enable JavaScript',
        ]
        
        # Check for very small body content (likely JS-rendered)
        soup = BeautifulSoup(html_content, 'html.parser')
        body = soup.find('body')
        if body:
            text_content = body.get_text(strip=True)
            if len(text_content) < 200:  # Very little content
                return True
        
        # Check for JS indicators
        for indicator in js_indicators:
            if indicator in html_content:
                return True
                
        return False

    def smart_fetch(self, url: str, force_scrapingbee: bool = False) -> Tuple[Optional[str], str]:
        """
        Smart fetching with automatic fallback
        
        Args:
            url: Target URL
            force_scrapingbee: Skip BeautifulSoup and use ScrapingBee directly
            
        Returns:
            Tuple[Optional[str], str]: (HTML content, method_used)
        """
        if force_scrapingbee and self.scrapingbee_api_key:
            html, success = self.fetch_with_scrapingbee(url)
            return html, "scrapingbee" if success else "failed"
        
        # Try BeautifulSoup first (free)
        html, success = self.fetch_with_beautifulsoup(url)
        if success:
            return html, "beautifulsoup"
        
        # Fallback to ScrapingBee if BeautifulSoup failed or needs JS
        if self.scrapingbee_api_key:
            logging.info(f"🔄 Falling back to ScrapingBee for: {url}")
            html, success = self.fetch_with_scrapingbee(url)
            if success:
                return html, "scrapingbee"
        
        return None, "failed"

    def extract_akc_breed_data(self, html: str, url: str) -> Dict:
        """
        Extract breed data from AKC breed pages
        (Same extraction logic as the original scraper)
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract breed name from URL
        breed_slug = url.rstrip('/').split('/')[-1]
        
        # Try to get display name from page
        display_name = None
        title_selectors = [
            'h1.breed-hero__title',
            'h1.hero-title',
            'h1',
            '.breed-name',
            'title'
        ]
        
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if text and 'AKC' not in text:
                    display_name = text.replace(' Dog Breed Information', '').strip()
                    break
        
        if not display_name:
            display_name = breed_slug.replace('-', ' ').title()
        
        breed_data = {
            'breed_slug': breed_slug,
            'display_name': display_name,
            'akc_url': url,
            'extraction_timestamp': datetime.now().isoformat(),
            'extraction_status': 'success',
            'has_physical_data': False,
            'has_profile_data': False,
        }
        
        # Extract physical characteristics
        self._extract_physical_traits(soup, breed_data)
        
        # Extract profile information
        self._extract_profile_data(soup, breed_data)
        
        return breed_data

    def _extract_physical_traits(self, soup: BeautifulSoup, breed_data: Dict):
        """Extract physical traits from the page"""
        try:
            # Extract comprehensive trait data
            traits = self._extract_trait_data(soup)
            
            if traits:
                breed_data['has_physical_data'] = True
                
                # Map traits to our schema
                mapped_traits = self._map_traits_to_schema(traits)
                breed_data.update(mapped_traits)
                
                # Store raw traits for debugging
                breed_data['raw_traits'] = traits
                
        except Exception as e:
            logging.error(f"Error extracting physical traits: {e}")

    def _extract_profile_data(self, soup: BeautifulSoup, breed_data: Dict):
        """Extract profile data from the page"""
        try:
            # Extract comprehensive content sections
            content = self._extract_content_sections(soup)
            
            if any(content.values()):
                breed_data['has_profile_data'] = True
                breed_data.update(content)
                
        except Exception as e:
            logging.error(f"Error extracting profile data: {e}")

    def _extract_trait_data(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract physical traits from various page patterns"""
        traits = {}
        
        try:
            # Pattern 1: Attribute lists (breed-specific-attributes, etc.)
            attr_sections = soup.find_all(['section', 'div'], class_=re.compile('breed.*attribute|trait|characteristic'))
            for section in attr_sections:
                items = section.find_all(['div', 'span', 'li'], class_=re.compile('trait|attribute|stat'))
                for item in items:
                    trait_name_elem = item.find(class_=re.compile('name|label|key'))
                    trait_value_elem = item.find(class_=re.compile('value|amount|level'))
                    
                    if trait_name_elem and trait_value_elem:
                        trait_name = trait_name_elem.get_text(strip=True)
                        trait_value = trait_value_elem.get_text(strip=True)
                        traits[trait_name] = trait_value
                    else:
                        # Try to extract from single element with pattern "Name: Value"
                        full_text = item.get_text(strip=True)
                        if ':' in full_text:
                            parts = full_text.split(':', 1)
                            if len(parts) == 2:
                                trait_name = parts[0].strip()
                                trait_value = parts[1].strip()
                                traits[trait_name] = trait_value

            # Pattern 2: Look for specific text patterns
            text_content = soup.get_text()
            
            # Height
            height_match = re.search(r'Height:?\s*([^\.]+)', text_content, re.I)
            if height_match:
                traits['Height'] = height_match.group(1).strip()
            
            # Weight
            weight_match = re.search(r'Weight:?\s*([^\.]+)', text_content, re.I)
            if weight_match:
                traits['Weight'] = weight_match.group(1).strip()
                
            # Life Expectancy
            life_match = re.search(r'Life\s+(?:Expectancy|Span):?\s*([^\.]+)', text_content, re.I)
            if life_match:
                traits['Life Expectancy'] = life_match.group(1).strip()

        except Exception as e:
            logging.error(f"Error extracting trait data: {e}")
        
        return traits

    def _extract_content_sections(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract comprehensive content from page"""
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
            sections = main_content.find_all(['section', 'div', 'p'], class_=re.compile('breed|content|description'))
            
            for section in sections:
                section_text = section.get_text(separator=' ', strip=True)
                if len(section_text) < 50:  # Skip very short sections
                    continue
                
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
                content[key] = ' '.join(content[key].split())[:2000]  # Limit length and normalize whitespace
                
        except Exception as e:
            logging.error(f"Error extracting content sections: {e}")
        
        return content

    def _map_traits_to_schema(self, traits: Dict[str, str]) -> Dict[str, any]:
        """Map AKC traits to structured data"""
        mapped = {}
        
        try:
            # Extract numeric ranges
            height_text = traits.get('Height', '')
            weight_text = traits.get('Weight', '')
            life_text = traits.get('Life Expectancy', '') or traits.get('Life Span', '')
            
            # Height extraction (convert inches to cm)
            height_min, height_max = self._extract_height_inches_to_cm(height_text)
            if height_min:
                mapped['height_cm_min'] = height_min
            if height_max:
                mapped['height_cm_max'] = height_max
            
            # Weight extraction (convert lbs to kg)
            weight_min, weight_max = self._extract_weight_lbs_to_kg(weight_text)
            if weight_min:
                mapped['weight_kg_min'] = weight_min
            if weight_max:
                mapped['weight_kg_max'] = weight_max
            
            # Lifespan extraction
            life_min, life_max = self._extract_lifespan(life_text)
            if life_min:
                mapped['lifespan_years_min'] = life_min
            if life_max:
                mapped['lifespan_years_max'] = life_max
            
            # Map size based on weight
            if weight_max:
                if weight_max < 10:
                    mapped['size'] = 'small'
                elif weight_max < 25:
                    mapped['size'] = 'medium'
                elif weight_max < 45:
                    mapped['size'] = 'large'
                else:
                    mapped['size'] = 'giant'
                    
        except Exception as e:
            logging.error(f"Error mapping traits: {e}")
        
        return mapped

    def _extract_height_inches_to_cm(self, text: str) -> tuple:
        """Extract height in inches and convert to cm"""
        if not text:
            return None, None
        
        try:
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

    def _extract_lifespan(self, text: str) -> tuple:
        """Extract lifespan in years"""
        if not text:
            return None, None
        
        try:
            numbers = re.findall(r'(\d+)', text)
            if numbers:
                if len(numbers) >= 2:
                    return int(numbers[0]), int(numbers[1])
                else:
                    return int(numbers[0]), int(numbers[0])
        except:
            pass
        
        return None, None

    def scrape_breeds_from_file(self, urls_file: str, limit: Optional[int] = None, 
                               force_scrapingbee: bool = False) -> List[Dict]:
        """
        Scrape breeds from a file containing URLs
        
        Args:
            urls_file: Path to file containing URLs (one per line)
            limit: Maximum number of URLs to process
            force_scrapingbee: Force use of ScrapingBee for all requests
            
        Returns:
            List[Dict]: Extracted breed data
        """
        if not os.path.exists(urls_file):
            logging.error(f"URLs file not found: {urls_file}")
            return []
        
        # Read URLs
        with open(urls_file, 'r') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        if limit:
            urls = urls[:limit]
        
        logging.info(f"🚀 Starting Universal Breed Scraper")
        logging.info(f"📋 Processing {len(urls)} breed URLs")
        logging.info(f"🕷️  ScrapingBee available: {'Yes' if self.scrapingbee_api_key else 'No'}")
        logging.info(f"💰 Force ScrapingBee: {force_scrapingbee}")
        print("=" * 60)
        
        results = []
        successful_extractions = 0
        
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] Processing breed {i}")
            print(f"  🔍 Scraping: {url}")
            
            # Fetch HTML
            html, method = self.smart_fetch(url, force_scrapingbee)
            
            if html:
                try:
                    # Extract breed data
                    breed_data = self.extract_akc_breed_data(html, url)
                    breed_data['scraping_method'] = method
                    breed_data['scrapingbee_cost'] = self.total_cost_credits
                    
                    results.append(breed_data)
                    successful_extractions += 1
                    
                    print(f"    ✅ Success: {breed_data['display_name']} (via {method})")
                    
                except Exception as e:
                    logging.error(f"    ❌ Extraction error for {url}: {e}")
                    error_data = {
                        'breed_slug': url.split('/')[-1],
                        'akc_url': url,
                        'extraction_status': 'extraction_failed',
                        'error': str(e),
                        'scraping_method': method
                    }
                    results.append(error_data)
            else:
                logging.error(f"    ❌ Failed to fetch: {url}")
                error_data = {
                    'breed_slug': url.split('/')[-1],
                    'akc_url': url,
                    'extraction_status': 'fetch_failed',
                    'scraping_method': method
                }
                results.append(error_data)
            
            # Progress update every 10 breeds
            if i % 10 == 0:
                print(f"\n📊 Progress Update:")
                print(f"  Processed: {i}")
                print(f"  Successful: {successful_extractions}")
                print(f"  BeautifulSoup requests: {self.beautifulsoup_requests}")
                print(f"  ScrapingBee requests: {self.scrapingbee_requests}")
                print(f"  Total credits used: {self.total_cost_credits}")
                
            # Rate limiting - be nice to both AKC and ScrapingBee
            time.sleep(2)
        
        # Final report
        print("\n" + "=" * 60)
        print("🎯 UNIVERSAL BREED SCRAPER REPORT")
        print("=" * 60)
        print(f"URLs processed: {len(urls)}")
        print(f"Successful extractions: {successful_extractions}")
        print(f"BeautifulSoup requests: {self.beautifulsoup_requests}")
        print(f"ScrapingBee requests: {self.scrapingbee_requests}")
        print(f"Total ScrapingBee credits used: {self.total_cost_credits}")
        print(f"Estimated cost: ${self.total_cost_credits * 0.001:.3f}")  # Rough estimate
        print(f"Success rate: {(successful_extractions/len(urls))*100:.1f}%")
        print("=" * 60)
        
        return results

    def save_results(self, results: List[Dict], output_file: Optional[str] = None) -> str:
        """Save results to JSON file"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"universal_breed_data_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logging.info(f"📄 Results saved to: {output_file}")
        return output_file


def main():
    parser = argparse.ArgumentParser(description='Universal Breed Scraper with ScrapingBee support')
    parser.add_argument('--urls-file', required=True, help='File containing URLs to scrape (one per line)')
    parser.add_argument('--limit', type=int, help='Maximum number of URLs to process')
    parser.add_argument('--force-scrapingbee', action='store_true', 
                       help='Force use of ScrapingBee for all requests (costs credits)')
    parser.add_argument('--output', help='Output JSON file path')
    
    args = parser.parse_args()
    
    # Initialize scraper
    scraper = UniversalBreedScraper()
    
    # Process URLs
    results = scraper.scrape_breeds_from_file(
        urls_file=args.urls_file,
        limit=args.limit,
        force_scrapingbee=args.force_scrapingbee
    )
    
    if results:
        # Save results
        output_file = scraper.save_results(results, args.output)
        print(f"✅ Results saved to: {output_file}")
    else:
        print("❌ No results to save")
        sys.exit(1)


if __name__ == '__main__':
    main()