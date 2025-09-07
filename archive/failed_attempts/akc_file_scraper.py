#!/usr/bin/env python3
"""
File-Based AKC Breed Scraper with Undetected ChromeDriver
Outputs to JSON files instead of database for reliability
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

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class AKCFileScraper:
    def __init__(self, headless=True, cloud_mode=False, output_dir="/app/results"):
        """Initialize the file-based scraper
        
        Args:
            headless: Run browser in headless mode
            cloud_mode: Optimize for cloud environments (Cloud Run, etc)
            output_dir: Directory to save result files
        """
        self.headless = headless
        self.cloud_mode = cloud_mode
        self.output_dir = output_dir
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Statistics
        self.stats = {
            'processed': 0,
            'extracted': 0,
            'failed': 0,
            'updated': 0
        }
        
        # Results storage
        self.results = []
        
        # Sample AKC breed URLs for testing (since we don't have DB access)
        self.sample_breeds = [
            {
                'breed_slug': 'affenpinscher',
                'display_name': 'Affenpinscher',
                'akc_url': 'https://www.akc.org/dog-breeds/affenpinscher/'
            },
            {
                'breed_slug': 'afghan-hound',
                'display_name': 'Afghan Hound',
                'akc_url': 'https://www.akc.org/dog-breeds/afghan-hound/'
            },
            {
                'breed_slug': 'airedale-terrier',
                'display_name': 'Airedale Terrier',
                'akc_url': 'https://www.akc.org/dog-breeds/airedale-terrier/'
            },
            {
                'breed_slug': 'akbash',
                'display_name': 'Akbash',
                'akc_url': 'https://www.akc.org/dog-breeds/akbash/'
            },
            {
                'breed_slug': 'american-bulldog',
                'display_name': 'American Bulldog',
                'akc_url': 'https://www.akc.org/dog-breeds/american-bulldog/'
            }
        ]
    
    def create_driver(self):
        """Create and configure Chrome WebDriver"""
        logger.info("🌐 Setting up Chrome WebDriver...")
        
        options = uc.ChromeOptions()
        
        if self.headless:
            options.add_argument('--headless=new')
            
        # Cloud-optimized Chrome options - CRITICAL for Cloud Run
        if self.cloud_mode:
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-plugins')
            options.add_argument('--memory-pressure-off')
            options.add_argument('--max_old_space_size=4096')
            # Additional options for Cloud Run
            options.add_argument('--disable-setuid-sandbox')
            options.add_argument('--single-process')
            options.add_argument('--no-zygote')
        
        # Additional stealth options
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        try:
            # Create driver with undetected-chromedriver
            # Use headless=True for cloud mode to ensure proper initialization
            driver = uc.Chrome(options=options, version_main=None, headless=self.headless, use_subprocess=False)
            
            # Execute script to hide webdriver property
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("✅ Chrome WebDriver created successfully")
            return driver
            
        except Exception as e:
            logger.error(f"Failed to create driver: {e}")
            raise

    def extract_breed_data(self, driver, url: str) -> Dict[str, Any]:
        """Extract comprehensive breed data from AKC page"""
        try:
            logger.info(f"🔍 Extracting from: {url}")
            
            # Navigate to the page
            driver.get(url)
            
            # Wait for page to load
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "main")))
            
            # Give JavaScript time to render
            time.sleep(3)
            
            # Get page text for parsing
            page_text = driver.page_source.lower()
            
            # Extract breed slug from URL
            breed_slug = url.split('/')[-2] if url.endswith('/') else url.split('/')[-1]
            
            # Initialize breed data
            breed_data = {
                'breed_slug': breed_slug,
                'display_name': breed_slug.replace('-', ' ').title(),
                'akc_url': url,
                'extraction_status': 'failed',
                'extraction_timestamp': datetime.now().isoformat(),
                'has_physical_data': False,
                'has_profile_data': False
            }
            
            # Extract physical traits
            traits = self._extract_traits_from_page(driver, page_text)
            if traits:
                breed_data.update(traits)
                breed_data['has_physical_data'] = bool(
                    traits.get('height_cm_min') or 
                    traits.get('weight_kg_min') or 
                    traits.get('life_span_years_min')
                )
            
            # Extract comprehensive profile data
            profile = self._extract_full_profile(driver)
            if profile:
                breed_data.update(profile)
                breed_data['has_profile_data'] = True
            
            # Mark as successful if we got any data
            if traits or profile:
                breed_data['extraction_status'] = 'success'
                logger.info(f"✅ Extracted data for {breed_data['display_name']}: Physical={breed_data['has_physical_data']}, Profile={breed_data['has_profile_data']}")
            else:
                logger.warning(f"⚠️ No data extracted for {breed_data['display_name']}")
                
            return breed_data
            
        except Exception as e:
            logger.error(f"Error extracting breed data: {e}")
            return {
                'breed_slug': breed_slug,
                'extraction_status': 'failed',
                'extraction_timestamp': datetime.now().isoformat(),
                'error': str(e)
            }

    def _extract_traits_from_page(self, driver, page_text: str) -> Dict[str, Any]:
        """Extract physical traits from page content"""
        traits = {}
        
        try:
            # Method 1: Look for breed standards section
            standards_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Height') or contains(text(), 'Weight') or contains(text(), 'Life')]")
            
            for element in standards_elements:
                text = element.get_attribute('textContent') or element.text
                if text:
                    # Parse height
                    height_match = re.search(r'height[:\s]*(\d+(?:\.\d+)?)\s*(?:to|-)\s*(\d+(?:\.\d+)?)\s*(?:inches?|in)', text.lower())
                    if height_match:
                        min_height = float(height_match.group(1))
                        max_height = float(height_match.group(2))
                        traits.update({
                            'height_cm_min': round(min_height * 2.54, 1),
                            'height_cm_max': round(max_height * 2.54, 1)
                        })
                    
                    # Parse weight
                    weight_match = re.search(r'weight[:\s]*(\d+(?:\.\d+)?)\s*(?:to|-)\s*(\d+(?:\.\d+)?)\s*(?:pounds?|lbs?|lb)', text.lower())
                    if weight_match:
                        min_weight = float(weight_match.group(1))
                        max_weight = float(weight_match.group(2))
                        traits.update({
                            'weight_kg_min': round(min_weight * 0.453592, 1),
                            'weight_kg_max': round(max_weight * 0.453592, 1)
                        })
                    
                    # Parse life span
                    life_match = re.search(r'(?:life\s*span|lifespan)[:\s]*(\d+)\s*(?:to|-)\s*(\d+)\s*years?', text.lower())
                    if life_match:
                        traits.update({
                            'life_span_years_min': int(life_match.group(1)),
                            'life_span_years_max': int(life_match.group(2))
                        })
            
            # Method 2: Parse from page text with regex patterns
            if not traits:
                traits.update(self._parse_height(page_text))
                traits.update(self._parse_weight(page_text))
                traits.update(self._parse_lifespan(page_text))
            
        except Exception as e:
            logger.error(f"Error extracting traits: {e}")
        
        return traits

    def _parse_height(self, text: str) -> Dict[str, Any]:
        """Parse height information"""
        height_patterns = [
            r'height[:\s]*(\d+(?:\.\d+)?)\s*(?:to|-)\s*(\d+(?:\.\d+)?)\s*(?:inches?|in)',
            r'(\d+(?:\.\d+)?)\s*(?:to|-)\s*(\d+(?:\.\d+)?)\s*(?:inches?|in)\s*(?:tall|height)',
            r'stands?\s*(\d+(?:\.\d+)?)\s*(?:to|-)\s*(\d+(?:\.\d+)?)\s*(?:inches?|in)',
        ]
        
        for pattern in height_patterns:
            match = re.search(pattern, text.lower())
            if match:
                min_height = float(match.group(1))
                max_height = float(match.group(2))
                return {
                    'height_cm_min': round(min_height * 2.54, 1),
                    'height_cm_max': round(max_height * 2.54, 1)
                }
        return {}

    def _parse_weight(self, text: str) -> Dict[str, Any]:
        """Parse weight information"""
        weight_patterns = [
            r'weight[:\s]*(\d+(?:\.\d+)?)\s*(?:to|-)\s*(\d+(?:\.\d+)?)\s*(?:pounds?|lbs?|lb)',
            r'(\d+(?:\.\d+)?)\s*(?:to|-)\s*(\d+(?:\.\d+)?)\s*(?:pounds?|lbs?|lb)\s*(?:weight|heavy)',
            r'weighs?\s*(\d+(?:\.\d+)?)\s*(?:to|-)\s*(\d+(?:\.\d+)?)\s*(?:pounds?|lbs?|lb)',
        ]
        
        for pattern in weight_patterns:
            match = re.search(pattern, text.lower())
            if match:
                min_weight = float(match.group(1))
                max_weight = float(match.group(2))
                return {
                    'weight_kg_min': round(min_weight * 0.453592, 1),
                    'weight_kg_max': round(max_weight * 0.453592, 1)
                }
        return {}

    def _parse_lifespan(self, text: str) -> Dict[str, Any]:
        """Parse lifespan information"""
        lifespan_patterns = [
            r'(?:life\s*span|lifespan)[:\s]*(\d+)\s*(?:to|-)\s*(\d+)\s*years?',
            r'lives?\s*(\d+)\s*(?:to|-)\s*(\d+)\s*years?',
            r'(\d+)\s*(?:to|-)\s*(\d+)\s*years?\s*(?:life|lifespan)',
        ]
        
        for pattern in lifespan_patterns:
            match = re.search(pattern, text.lower())
            if match:
                return {
                    'life_span_years_min': int(match.group(1)),
                    'life_span_years_max': int(match.group(2))
                }
        return {}
    
    def _extract_full_profile(self, driver) -> Dict[str, Any]:
        """Extract comprehensive breed profile including history, personality, care, etc."""
        profile = {}
        
        try:
            # Extract breed group
            try:
                group_elem = driver.find_element(By.XPATH, "//span[contains(text(), 'Group:')]/following-sibling::*")
                profile['breed_group'] = group_elem.text.strip()
            except:
                pass
            
            # Extract temperament/personality
            try:
                temp_elem = driver.find_element(By.XPATH, "//*[contains(text(), 'Temperament:')]/following-sibling::*")
                profile['temperament'] = temp_elem.text.strip()
            except:
                pass
            
            # Extract description/about section
            try:
                about_sections = driver.find_elements(By.XPATH, "//h2[contains(text(), 'About')]/../following-sibling::div//p | //div[@class='breed-hero__footer']//p")
                if about_sections:
                    profile['description'] = ' '.join([p.text.strip() for p in about_sections if p.text.strip()])
            except:
                pass
            
            # Extract history
            try:
                history_sections = driver.find_elements(By.XPATH, "//h2[contains(text(), 'History')]/../following-sibling::div//p")
                if history_sections:
                    profile['history'] = ' '.join([p.text.strip() for p in history_sections if p.text.strip()])
            except:
                pass
            
            # Extract care/grooming requirements
            try:
                care_sections = driver.find_elements(By.XPATH, "//h2[contains(text(), 'Care') or contains(text(), 'Grooming')]/../following-sibling::div//p")
                if care_sections:
                    profile['care_requirements'] = ' '.join([p.text.strip() for p in care_sections if p.text.strip()])
            except:
                pass
            
            # Extract health information
            try:
                health_sections = driver.find_elements(By.XPATH, "//h2[contains(text(), 'Health')]/../following-sibling::div//p")
                if health_sections:
                    profile['health_info'] = ' '.join([p.text.strip() for p in health_sections if p.text.strip()])
            except:
                pass
            
            # Extract training information
            try:
                training_sections = driver.find_elements(By.XPATH, "//h2[contains(text(), 'Training')]/../following-sibling::div//p")
                if training_sections:
                    profile['training_info'] = ' '.join([p.text.strip() for p in training_sections if p.text.strip()])
            except:
                pass
            
            # Extract exercise requirements
            try:
                exercise_sections = driver.find_elements(By.XPATH, "//h2[contains(text(), 'Exercise')]/../following-sibling::div//p")
                if exercise_sections:
                    profile['exercise_needs'] = ' '.join([p.text.strip() for p in exercise_sections if p.text.strip()])
            except:
                pass
            
            # Extract nutrition information
            try:
                nutrition_sections = driver.find_elements(By.XPATH, "//h2[contains(text(), 'Nutrition')]/../following-sibling::div//p")
                if nutrition_sections:
                    profile['nutrition_info'] = ' '.join([p.text.strip() for p in nutrition_sections if p.text.strip()])
            except:
                pass
            
            # Extract breed traits/characteristics (often in a list or table)
            try:
                trait_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'breed-trait') or contains(@class, 'characteristic')]")
                traits_list = []
                for elem in trait_elements:
                    trait_text = elem.text.strip()
                    if trait_text:
                        traits_list.append(trait_text)
                if traits_list:
                    profile['breed_traits'] = traits_list
            except:
                pass
            
            # Extract coat information
            try:
                coat_elem = driver.find_element(By.XPATH, "//*[contains(text(), 'Coat:')]/following-sibling::* | //*[contains(text(), 'Coat Type:')]/following-sibling::*")
                profile['coat_type'] = coat_elem.text.strip()
            except:
                pass
            
            # Extract color information
            try:
                color_elem = driver.find_element(By.XPATH, "//*[contains(text(), 'Color:')]/following-sibling::* | //*[contains(text(), 'Colors:')]/following-sibling::*")
                profile['colors'] = color_elem.text.strip()
            except:
                pass
            
            # Extract any ratings (energy level, trainability, etc.)
            try:
                rating_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'rating') or contains(@class, 'star')]/..")
                ratings = {}
                for elem in rating_elements:
                    text = elem.text.strip()
                    if ':' in text:
                        key, value = text.split(':', 1)
                        ratings[key.strip().lower().replace(' ', '_')] = value.strip()
                if ratings:
                    profile['ratings'] = ratings
            except:
                pass
            
            # Clean up empty strings
            profile = {k: v for k, v in profile.items() if v}
            
            if profile:
                logger.info(f"📚 Extracted profile data with {len(profile)} fields")
            
        except Exception as e:
            logger.error(f"Error extracting profile data: {e}")
        
        return profile

    def save_results(self, filename: str = None):
        """Save results to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"akc_breeds_{timestamp}.json"
        
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"💾 Results saved to: {filepath}")
        return filepath

    def scrape_breeds(self, limit: Optional[int] = None, specific_breeds: Optional[List[str]] = None):
        """Main scraping function - outputs to files instead of database"""
        
        # Use sample breeds for testing
        breeds_to_update = self.sample_breeds.copy()
        
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
                        self.results.append(breed_data)
                        self.stats['updated'] += 1
                    else:
                        self.stats['failed'] += 1
                        # Still save failed attempts for debugging
                        self.results.append(breed_data)
                        
                except Exception as e:
                    logger.error(f"Error processing {breed['display_name']}: {e}")
                    self.stats['failed'] += 1
                
                self.stats['processed'] += 1
                
                # Rate limiting
                time.sleep(2)
            
            # Save results
            output_file = self.save_results()
            
            # Print summary
            logger.info("\n" + "="*50)
            logger.info("📊 SCRAPING SUMMARY")
            logger.info("="*50)
            logger.info(f"Processed: {self.stats['processed']}")
            logger.info(f"Extracted: {self.stats['extracted']}")
            logger.info(f"Failed: {self.stats['failed']}")
            logger.info(f"Results saved to: {output_file}")
            logger.info("="*50)
            
            return output_file
            
        finally:
            if driver:
                try:
                    driver.quit()
                    logger.info("🔒 Chrome driver closed")
                except:
                    pass


def main():
    """Command line entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='AKC Breed Scraper (File Output)')
    parser.add_argument('--limit', type=int, help='Limit number of breeds to process')
    parser.add_argument('--headless', action='store_true', default=True, help='Run in headless mode')
    parser.add_argument('--cloud', action='store_true', help='Optimize for cloud environments')
    parser.add_argument('--output-dir', default='/app/results', help='Output directory for results')
    parser.add_argument('--breeds', nargs='+', help='Specific breed slugs to process')
    
    args = parser.parse_args()
    
    logger.info("🚀 Starting AKC File Scraper")
    
    try:
        scraper = AKCFileScraper(
            headless=args.headless, 
            cloud_mode=args.cloud,
            output_dir=args.output_dir
        )
        
        output_file = scraper.scrape_breeds(
            limit=args.limit,
            specific_breeds=args.breeds
        )
        
        logger.info(f"✅ Scraping completed! Results: {output_file}")
        
    except Exception as e:
        logger.error(f"❌ Scraping failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()