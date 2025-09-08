#!/usr/bin/env python3
"""
Cloud-Ready AKC Breed Scraper with Undetected ChromeDriver
Designed for Google Cloud Run or any cloud environment
"""

import os
import sys
import json
import time
import re
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from supabase import create_client, Client

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class AKCCloudScraper:
    def __init__(self, headless=True, cloud_mode=False):
        """Initialize the cloud-ready scraper
        
        Args:
            headless: Run browser in headless mode
            cloud_mode: Optimize for cloud environments (Cloud Run, etc)
        """
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Missing Supabase credentials in environment")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        self.headless = headless
        self.cloud_mode = cloud_mode
        
        # Statistics
        self.stats = {
            'processed': 0,
            'extracted': 0,
            'updated': 0,
            'failed': 0
        }

    def create_driver(self):
        """Create undetected Chrome driver with optimal settings"""
        
        options = uc.ChromeOptions()
        
        if self.headless:
            options.add_argument('--headless=new')
        
        # Cloud optimization settings
        if self.cloud_mode:
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-features=VizDisplayCompositor')
            options.add_argument('--single-process')
            options.add_argument('--disable-setuid-sandbox')
        
        # General optimization
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-web-security')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--start-maximized')
        options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Performance settings
        prefs = {
            'profile.default_content_setting_values': {
                'images': 2,  # Disable images for faster loading
                'plugins': 2,
                'popups': 2,
                'geolocation': 2,
                'notifications': 2,
                'media_stream': 2,
            },
            'profile.managed_default_content_settings': {
                'images': 2
            }
        }
        options.add_experimental_option('prefs', prefs)
        
        # Create driver
        driver = uc.Chrome(options=options, version_main=None)
        
        # Additional stealth settings
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        return driver

    def extract_breed_data(self, driver, url: str) -> Dict[str, Any]:
        """Extract breed data from AKC page"""
        
        logger.info(f"Extracting from: {url}")
        breed_slug = url.rstrip('/').split('/')[-1]
        
        try:
            # Navigate to page
            driver.get(url)
            
            # Wait for content to load
            wait = WebDriverWait(driver, 15)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "main")))
            time.sleep(3)  # Additional wait for dynamic content
            
            breed_data = {
                'akc_url': url,
                'breed_slug': breed_slug,
                'extraction_status': 'success'
            }
            
            # Get breed name
            try:
                h1 = driver.find_element(By.TAG_NAME, "h1")
                breed_data['display_name'] = h1.text.strip()
            except:
                breed_data['display_name'] = breed_slug.replace('-', ' ').title()
            
            # Get page text
            page_text = driver.find_element(By.TAG_NAME, "body").text
            
            # Extract breed traits using multiple methods
            traits = self._extract_traits_from_page(driver, page_text)
            breed_data['raw_traits'] = traits
            
            # Parse physical characteristics
            if 'Height' in traits:
                height_min, height_max = self._parse_height(traits['Height'])
                if height_min:
                    breed_data['height_cm_min'] = height_min
                if height_max:
                    breed_data['height_cm_max'] = height_max
                logger.info(f"  ✅ Height: {traits['Height']}")
            
            if 'Weight' in traits:
                weight_min, weight_max = self._parse_weight(traits['Weight'])
                if weight_min:
                    breed_data['weight_kg_min'] = weight_min
                if weight_max:
                    breed_data['weight_kg_max'] = weight_max
                logger.info(f"  ✅ Weight: {traits['Weight']}")
            
            if 'Life Expectancy' in traits or 'Life Span' in traits:
                lifespan = traits.get('Life Expectancy') or traits.get('Life Span')
                life_min, life_max = self._parse_lifespan(lifespan)
                if life_min:
                    breed_data['lifespan_years_min'] = life_min
                if life_max:
                    breed_data['lifespan_years_max'] = life_max
                logger.info(f"  ✅ Lifespan: {lifespan}")
            
            # Determine size based on weight
            if 'weight_kg_max' in breed_data:
                breed_data['size'] = self._determine_size(breed_data['weight_kg_max'])
            
            # Extract breed characteristics
            characteristics = self._extract_characteristics(page_text)
            breed_data.update(characteristics)
            
            # Extract comprehensive content
            content = self._extract_content_sections(driver)
            breed_data['comprehensive_content'] = content
            
            return breed_data
            
        except Exception as e:
            logger.error(f"Extraction error for {url}: {e}")
            return {
                'akc_url': url,
                'breed_slug': breed_slug,
                'extraction_status': 'failed',
                'extraction_notes': str(e)
            }

    def _extract_traits_from_page(self, driver, page_text: str) -> Dict[str, str]:
        """Extract breed traits using multiple methods"""
        
        traits = {}
        
        # Method 1: Regex patterns in visible text
        patterns = {
            'Height': r'Height[:\s]*([0-9]+(?:\.[0-9]+)?(?:\s*[-–]\s*[0-9]+(?:\.[0-9]+)?)?)\s*inch',
            'Weight': r'Weight[:\s]*([0-9]+(?:\.[0-9]+)?(?:\s*[-–]\s*[0-9]+(?:\.[0-9]+)?)?)\s*(?:pound|lb)',
            'Life Expectancy': r'Life (?:Expectancy|Span)[:\s]*([0-9]+(?:\s*[-–]\s*[0-9]+)?)\s*year',
            'Group': r'Group[:\s]*([A-Za-z\s]+?)(?:\n|$)',
            'Origin': r'Origin[:\s]*([A-Za-z\s,]+?)(?:\n|$)'
        }
        
        for trait, pattern in patterns.items():
            match = re.search(pattern, page_text, re.IGNORECASE | re.MULTILINE)
            if match:
                traits[trait] = match.group(1).strip()
        
        # Method 2: Look for structured data in JavaScript
        try:
            js_data = driver.execute_script("""
                // Try to find breed data in various places
                const findBreedData = () => {
                    // Check for global variables
                    if (window.breedData) return window.breedData;
                    if (window.__INITIAL_STATE__) return window.__INITIAL_STATE__;
                    
                    // Check for data attributes
                    const elements = document.querySelectorAll('[data-breed-info]');
                    if (elements.length > 0) {
                        return JSON.parse(elements[0].getAttribute('data-breed-info'));
                    }
                    
                    // Look for specific trait elements
                    const traits = {};
                    const traitElements = document.querySelectorAll('.breed-trait, .breed-characteristic');
                    traitElements.forEach(el => {
                        const label = el.querySelector('.label, .trait-label');
                        const value = el.querySelector('.value, .trait-value');
                        if (label && value) {
                            traits[label.textContent.trim()] = value.textContent.trim();
                        }
                    });
                    
                    return traits;
                };
                
                return findBreedData();
            """)
            
            if js_data and isinstance(js_data, dict):
                traits.update(js_data)
        except:
            pass
        
        # Method 3: Try to find in meta tags or structured data
        try:
            meta_tags = driver.find_elements(By.TAG_NAME, "meta")
            for tag in meta_tags:
                prop = tag.get_attribute("property") or tag.get_attribute("name")
                content = tag.get_attribute("content")
                if prop and content:
                    if "height" in prop.lower():
                        traits['Height'] = content
                    elif "weight" in prop.lower():
                        traits['Weight'] = content
                    elif "life" in prop.lower():
                        traits['Life Expectancy'] = content
        except:
            pass
        
        return traits

    def _extract_characteristics(self, page_text: str) -> Dict[str, str]:
        """Extract breed characteristics like energy, shedding, etc."""
        
        characteristics = {}
        
        patterns = {
            'energy': (r'Energy (?:Level)?[:\s]*(\w+)', ['low', 'moderate', 'high', 'very high']),
            'shedding': (r'Shedding[:\s]*(\w+)', ['low', 'moderate', 'high']),
            'trainability': (r'Trainability[:\s]*(\w+)', ['easy', 'moderate', 'challenging']),
            'bark_level': (r'Bark(?:ing)? (?:Level)?[:\s]*(\w+)', ['low', 'moderate', 'high']),
            'coat_length': (r'Coat (?:Length)?[:\s]*(\w+)', ['short', 'medium', 'long'])
        }
        
        for char_name, (pattern, valid_values) in patterns.items():
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                value = match.group(1).lower()
                # Normalize to our controlled vocabulary
                if value in valid_values:
                    characteristics[char_name] = value
                elif 'minimal' in value or 'low' in value:
                    characteristics[char_name] = valid_values[0]
                elif 'average' in value or 'medium' in value or 'moderate' in value:
                    characteristics[char_name] = valid_values[1] if len(valid_values) > 1 else value
                elif 'high' in value or 'heavy' in value:
                    characteristics[char_name] = valid_values[-1]
                    
                if char_name in characteristics:
                    logger.info(f"  ✅ {char_name}: {characteristics[char_name]}")
        
        return characteristics

    def _extract_content_sections(self, driver) -> Dict[str, str]:
        """Extract comprehensive content sections"""
        
        content = {}
        
        try:
            # Look for main content sections
            sections = driver.find_elements(By.CSS_SELECTOR, "section, article, .breed-section, .content-section")
            
            for section in sections:
                try:
                    # Get section heading
                    heading = section.find_element(By.CSS_SELECTOR, "h2, h3, .section-title")
                    title = heading.text.lower().strip()
                    text = section.text[:5000]  # Limit length
                    
                    if 'history' in title:
                        content['history'] = text
                    elif 'personality' in title or 'temperament' in title:
                        content['personality'] = text
                    elif 'health' in title:
                        content['health'] = text
                    elif 'care' in title:
                        content['care'] = text
                    elif 'grooming' in title:
                        content['grooming'] = text
                    elif 'exercise' in title:
                        content['exercise'] = text
                    elif 'training' in title:
                        content['training'] = text
                    elif 'feeding' in title or 'nutrition' in title:
                        content['feeding'] = text
                except:
                    continue
            
            # If no structured content, get general text
            if not content:
                content['about'] = driver.find_element(By.TAG_NAME, "main").text[:10000]
        
        except Exception as e:
            logger.warning(f"Content extraction error: {e}")
            content['about'] = driver.find_element(By.TAG_NAME, "body").text[:10000]
        
        return content

    def _parse_height(self, height_text: str) -> Tuple[Optional[float], Optional[float]]:
        """Parse height and convert to cm"""
        numbers = re.findall(r'[0-9]+(?:\.[0-9]+)?', height_text)
        if len(numbers) >= 2:
            return round(float(numbers[0]) * 2.54, 1), round(float(numbers[1]) * 2.54, 1)
        elif len(numbers) == 1:
            height_cm = round(float(numbers[0]) * 2.54, 1)
            return height_cm, height_cm
        return None, None

    def _parse_weight(self, weight_text: str) -> Tuple[Optional[float], Optional[float]]:
        """Parse weight and convert to kg"""
        numbers = re.findall(r'[0-9]+(?:\.[0-9]+)?', weight_text)
        if len(numbers) >= 2:
            return round(float(numbers[0]) * 0.453592, 1), round(float(numbers[1]) * 0.453592, 1)
        elif len(numbers) == 1:
            weight_kg = round(float(numbers[0]) * 0.453592, 1)
            return weight_kg, weight_kg
        return None, None

    def _parse_lifespan(self, life_text: str) -> Tuple[Optional[int], Optional[int]]:
        """Parse lifespan"""
        numbers = re.findall(r'[0-9]+', life_text)
        if len(numbers) >= 2:
            return int(numbers[0]), int(numbers[1])
        elif len(numbers) == 1:
            years = int(numbers[0])
            return years, years
        return None, None

    def _determine_size(self, weight_kg: float) -> str:
        """Determine size category based on weight"""
        if weight_kg < 10:
            return 'small'
        elif weight_kg < 25:
            return 'medium'
        elif weight_kg < 45:
            return 'large'
        else:
            return 'giant'

    def update_breed(self, breed_data: Dict[str, Any]) -> bool:
        """Update breed in database"""
        try:
            result = self.supabase.table('akc_breeds').update(breed_data).eq(
                'breed_slug', breed_data['breed_slug']
            ).execute()
            
            if result.data:
                logger.info(f"✅ Updated: {breed_data.get('display_name')}")
                return True
            return False
        except Exception as e:
            logger.error(f"Database error: {e}")
            return False

    def scrape_breeds(self, limit: Optional[int] = None, specific_breeds: Optional[List[str]] = None):
        """Main scraping function
        
        Args:
            limit: Maximum number of breeds to process
            specific_breeds: List of specific breed slugs to update
        """
        
        # Get breeds to update
        if specific_breeds:
            breeds_to_update = []
            for slug in specific_breeds:
                result = self.supabase.table('akc_breeds').select('*').eq('breed_slug', slug).single().execute()
                if result.data:
                    breeds_to_update.append(result.data)
        else:
            # Get breeds without physical data
            result = self.supabase.table('akc_breeds').select('*').eq('has_physical_data', False).execute()
            breeds_to_update = result.data
        
        if limit:
            breeds_to_update = breeds_to_update[:limit]
        
        logger.info(f"📊 Processing {len(breeds_to_update)} breeds")
        
        # Create driver
        driver = None
        try:
            driver = self.create_driver()
            
            for idx, breed in enumerate(breeds_to_update, 1):
                logger.info(f"\n[{idx}/{len(breeds_to_update)}] Processing: {breed['display_name']}")
                
                try:
                    # Extract data
                    breed_data = self.extract_breed_data(driver, breed['akc_url'])
                    
                    if breed_data and breed_data.get('extraction_status') == 'success':
                        self.stats['extracted'] += 1
                        
                        # Update database
                        if self.update_breed(breed_data):
                            self.stats['updated'] += 1
                    else:
                        self.stats['failed'] += 1
                        
                except Exception as e:
                    logger.error(f"Error processing {breed['display_name']}: {e}")
                    self.stats['failed'] += 1
                
                self.stats['processed'] += 1
                
                # Rate limiting
                if idx < len(breeds_to_update):
                    time.sleep(3)
                
                # Progress update
                if idx % 5 == 0:
                    logger.info(f"Progress: Extracted={self.stats['extracted']}, Updated={self.stats['updated']}, Failed={self.stats['failed']}")
            
        finally:
            if driver:
                driver.quit()
        
        # Final report
        self._print_report()

    def _print_report(self):
        """Print final report"""
        logger.info("\n" + "=" * 60)
        logger.info("🎯 AKC CLOUD SCRAPER REPORT")
        logger.info("=" * 60)
        logger.info(f"Processed: {self.stats['processed']}")
        logger.info(f"Extracted: {self.stats['extracted']}")
        logger.info(f"Updated: {self.stats['updated']}")
        logger.info(f"Failed: {self.stats['failed']}")
        
        if self.stats['processed'] > 0:
            success_rate = (self.stats['extracted'] / self.stats['processed']) * 100
            logger.info(f"Success rate: {success_rate:.1f}%")
        logger.info("=" * 60)


def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Cloud-Ready AKC Breed Scraper')
    parser.add_argument('--limit', type=int, help='Limit number of breeds')
    parser.add_argument('--test', action='store_true', help='Test with 3 breeds')
    parser.add_argument('--cloud', action='store_true', help='Run in cloud mode')
    parser.add_argument('--breeds', nargs='+', help='Specific breed slugs to update')
    parser.add_argument('--headless', action='store_true', default=True, help='Run headless')
    
    args = parser.parse_args()
    
    # Initialize scraper
    scraper = AKCCloudScraper(headless=args.headless, cloud_mode=args.cloud)
    
    if args.test:
        # Test with a few breeds
        test_breeds = ['german-shepherd-dog', 'golden-retriever', 'french-bulldog']
        scraper.scrape_breeds(specific_breeds=test_breeds)
    elif args.breeds:
        scraper.scrape_breeds(specific_breeds=args.breeds)
    else:
        scraper.scrape_breeds(limit=args.limit)


if __name__ == "__main__":
    logger.info("🚀 Starting AKC Cloud Scraper")
    main()