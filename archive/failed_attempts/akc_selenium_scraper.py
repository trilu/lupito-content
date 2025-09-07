#!/usr/bin/env python3
"""
Selenium-based AKC Breed Scraper optimized for Cloud Run
Extracts comprehensive breed profiles including physical traits, history, personality, etc.
"""

import os
import sys
import json
import time
import re
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AKCSeleniumScraper:
    def __init__(self, headless=True, cloud_mode=False, output_dir="/app/results"):
        """Initialize the Selenium-based scraper
        
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
        
        # Sample AKC breed URLs for testing
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
                'breed_slug': 'akita',
                'display_name': 'Akita',
                'akc_url': 'https://www.akc.org/dog-breeds/akita/'
            },
            {
                'breed_slug': 'alaskan-malamute',
                'display_name': 'Alaskan Malamute',
                'akc_url': 'https://www.akc.org/dog-breeds/alaskan-malamute/'
            }
        ]
    
    def create_driver(self):
        """Create and configure Chrome WebDriver with Selenium"""
        logger.info("🌐 Setting up Chrome WebDriver...")
        
        options = Options()
        
        # Always use headless in cloud mode
        if self.headless or self.cloud_mode:
            options.add_argument('--headless')  # Use old headless mode for better compatibility
        
        # Essential options for Cloud Run - CRITICAL for DevToolsActivePort fix
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-web-security')
        options.add_argument('--disable-features=VizDisplayCompositor')
        options.add_argument('--disable-software-rasterizer')
        options.add_argument('--disable-setuid-sandbox')
        
        # Remove single-process and no-zygote as they can cause instability
        # Instead use these for better Chrome stability
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-backgrounding-occluded-windows')
        options.add_argument('--disable-renderer-backgrounding')
        
        # Explicit tmp directory for Chrome
        options.add_argument('--user-data-dir=/tmp/chrome-user-data')
        options.add_argument('--data-path=/tmp/chrome-data-path')
        options.add_argument('--disk-cache-dir=/tmp/chrome-cache')
        
        options.add_argument('--disable-extensions')
        
        # Memory optimization
        options.add_argument('--memory-pressure-off')
        options.add_argument('--max_old_space_size=4096')
        
        # Window size for consistency
        options.add_argument('--window-size=1920,1080')
        
        # Additional stealth options
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # User agent
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Disable images for faster loading (optional)
        if self.cloud_mode:
            prefs = {
                "profile.managed_default_content_settings.images": 2,
                "profile.default_content_setting_values.notifications": 2,
            }
            options.add_experimental_option("prefs", prefs)
        
        try:
            # Use system Chrome binary and explicit service
            if self.cloud_mode:
                options.binary_location = '/usr/bin/google-chrome'
                # Create service with explicit chrome driver path
                service = Service('/usr/bin/chromedriver')
                driver = webdriver.Chrome(service=service, options=options)
            else:
                # Local mode - let Selenium handle it
                driver = webdriver.Chrome(options=options)
            
            # Execute stealth scripts
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en']
                    });
                    window.chrome = {
                        runtime: {}
                    };
                    Object.defineProperty(navigator, 'permissions', {
                        get: () => ({
                            query: () => Promise.resolve({ state: 'granted' })
                        })
                    });
                '''
            })
            
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
            time.sleep(2)
            
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
                'breed_slug': breed_slug if 'breed_slug' in locals() else 'unknown',
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
            # Extract all text content sections
            sections = {
                'description': ["//h2[contains(text(), 'About')]/../following-sibling::div//p", "//div[@class='breed-hero__footer']//p"],
                'history': ["//h2[contains(text(), 'History')]/../following-sibling::div//p"],
                'personality': ["//h2[contains(text(), 'Personality')]/../following-sibling::div//p", "//h2[contains(text(), 'Temperament')]/../following-sibling::div//p"],
                'care_requirements': ["//h2[contains(text(), 'Care')]/../following-sibling::div//p", "//h2[contains(text(), 'Grooming')]/../following-sibling::div//p"],
                'health_info': ["//h2[contains(text(), 'Health')]/../following-sibling::div//p"],
                'training_info': ["//h2[contains(text(), 'Training')]/../following-sibling::div//p"],
                'exercise_needs': ["//h2[contains(text(), 'Exercise')]/../following-sibling::div//p"],
                'nutrition_info': ["//h2[contains(text(), 'Nutrition')]/../following-sibling::div//p"]
            }
            
            for field, xpaths in sections.items():
                content = []
                for xpath in xpaths:
                    try:
                        elements = driver.find_elements(By.XPATH, xpath)
                        for elem in elements:
                            text = elem.text.strip()
                            if text and len(text) > 20:  # Filter out very short snippets
                                content.append(text)
                    except:
                        pass
                
                if content:
                    profile[field] = ' '.join(content)
            
            # Extract structured data
            try:
                # Breed group
                group_elems = driver.find_elements(By.XPATH, "//*[contains(text(), 'Group:')]")
                for elem in group_elems:
                    parent_text = elem.find_element(By.XPATH, "..").text
                    if 'Group:' in parent_text:
                        profile['breed_group'] = parent_text.split('Group:')[1].strip().split('\n')[0]
                        break
            except:
                pass
            
            try:
                # Temperament
                temp_elems = driver.find_elements(By.XPATH, "//*[contains(text(), 'Temperament:')]")
                for elem in temp_elems:
                    parent_text = elem.find_element(By.XPATH, "..").text
                    if 'Temperament:' in parent_text:
                        profile['temperament'] = parent_text.split('Temperament:')[1].strip().split('\n')[0]
                        break
            except:
                pass
            
            # Extract any breed characteristics table/list
            try:
                char_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'breed-characteristic') or contains(@class, 'breed-trait')]")
                characteristics = []
                for elem in char_elements:
                    text = elem.text.strip()
                    if text and len(text) > 5:
                        characteristics.append(text)
                if characteristics:
                    profile['breed_characteristics'] = characteristics
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
        """Main scraping function - outputs to files"""
        
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
    
    parser = argparse.ArgumentParser(description='AKC Breed Scraper (Selenium-based)')
    parser.add_argument('--limit', type=int, help='Limit number of breeds to process')
    parser.add_argument('--headless', action='store_true', default=True, help='Run in headless mode')
    parser.add_argument('--cloud', action='store_true', help='Optimize for cloud environments')
    parser.add_argument('--output-dir', default='/app/results', help='Output directory for results')
    parser.add_argument('--breeds', nargs='+', help='Specific breed slugs to process')
    
    args = parser.parse_args()
    
    logger.info("🚀 Starting AKC Selenium Scraper")
    
    try:
        scraper = AKCSeleniumScraper(
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