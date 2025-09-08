#!/usr/bin/env python3
"""
Enhanced AKC Breed Scraper with Selenium for Dynamic Content
Extracts complete breed data including JavaScript-rendered characteristics
"""

import os
import sys
import json
import time
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlparse
from dotenv import load_dotenv
from supabase import create_client, Client
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import requests
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()

class EnhancedAKCBreedScraper:
    def __init__(self):
        """Initialize the enhanced scraper with Selenium"""
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Missing Supabase credentials in .env file")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Setup Chrome options for headless operation
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--disable-gpu')
        self.chrome_options.add_argument('--window-size=1920,1080')
        
        # Statistics
        self.stats = {
            'processed': 0,
            'new_breeds': 0,
            'updated': 0,
            'skipped': 0,
            'extraction_success': 0,
            'extraction_failed': 0,
            'errors': 0
        }
        
        # QA tracking
        self.qa_report = []
        
        # Configuration
        self.config = {
            'rate_limit_seconds': 3,  # Slightly longer for Selenium
            'max_retries': 3,
            'timeout': 15
        }

    def get_driver(self):
        """Create a new Chrome driver instance"""
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=self.chrome_options)

    def extract_breed_data_selenium(self, url: str) -> Dict[str, Any]:
        """Extract breed data using Selenium for JavaScript content"""
        driver = None
        try:
            driver = self.get_driver()
            driver.get(url)
            
            # Wait for the page to load
            wait = WebDriverWait(driver, self.config['timeout'])
            
            # Wait for breed info to load (usually in a specific container)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "main")))
            time.sleep(2)  # Additional wait for JS rendering
            
            breed_data = {
                'akc_url': url,
                'extraction_status': 'success'
            }
            
            # Extract breed name
            try:
                breed_name = driver.find_element(By.CSS_SELECTOR, "h1").text
                breed_data['display_name'] = breed_name.strip()
                breed_data['breed_slug'] = url.rstrip('/').split('/')[-1]
            except:
                breed_data['display_name'] = 'Unknown'
                breed_data['breed_slug'] = url.rstrip('/').split('/')[-1]
            
            # Extract breed traits from the traits section
            traits = self._extract_traits_selenium(driver)
            breed_data['raw_traits'] = traits
            
            # Extract breed group
            try:
                group_elem = driver.find_element(By.XPATH, "//span[contains(text(), 'Group:')]/following-sibling::span")
                breed_data['breed_group'] = group_elem.text.strip()
            except:
                breed_data['breed_group'] = None
            
            # Extract physical characteristics
            physical_data = self._extract_physical_data_selenium(driver)
            breed_data.update(physical_data)
            
            # Extract temperament scores
            temperament_data = self._extract_temperament_selenium(driver)
            breed_data.update(temperament_data)
            
            # Extract comprehensive content
            content = self._extract_content_selenium(driver)
            breed_data['comprehensive_content'] = content
            
            # Map extracted data to schema
            mapped_data = self._map_to_schema(breed_data)
            
            return mapped_data
            
        except Exception as e:
            print(f"      ❌ Selenium extraction error: {e}")
            return {
                'akc_url': url,
                'breed_slug': url.rstrip('/').split('/')[-1],
                'extraction_status': 'failed',
                'extraction_notes': str(e)
            }
        finally:
            if driver:
                driver.quit()

    def _extract_traits_selenium(self, driver) -> Dict[str, Any]:
        """Extract breed traits using Selenium"""
        traits = {}
        
        try:
            # Method 1: Look for traits in data attributes or specific divs
            trait_elements = driver.find_elements(By.CSS_SELECTOR, "[data-trait], .breed-trait, .trait-item")
            for elem in trait_elements:
                trait_name = elem.get_attribute('data-trait') or elem.find_element(By.CSS_SELECTOR, ".trait-name").text
                trait_value = elem.get_attribute('data-value') or elem.find_element(By.CSS_SELECTOR, ".trait-value").text
                if trait_name and trait_value:
                    traits[trait_name] = trait_value
            
            # Method 2: Look for specific patterns in the page
            # Height
            try:
                height_elem = driver.find_element(By.XPATH, "//*[contains(text(), 'Height')]/following-sibling::*[1]")
                traits['Height'] = height_elem.text.strip()
            except:
                pass
            
            # Weight  
            try:
                weight_elem = driver.find_element(By.XPATH, "//*[contains(text(), 'Weight')]/following-sibling::*[1]")
                traits['Weight'] = weight_elem.text.strip()
            except:
                pass
            
            # Life Expectancy
            try:
                life_elem = driver.find_element(By.XPATH, "//*[contains(text(), 'Life Expectancy') or contains(text(), 'Life Span')]/following-sibling::*[1]")
                traits['Life Expectancy'] = life_elem.text.strip()
            except:
                pass
            
            # Breed Group
            try:
                group_elem = driver.find_element(By.XPATH, "//*[contains(text(), 'Group')]/following-sibling::*[1]")
                traits['Group'] = group_elem.text.strip()
            except:
                pass
            
            # Method 3: Check for trait cards or info boxes
            info_cards = driver.find_elements(By.CSS_SELECTOR, ".breed-info-card, .trait-card, .info-box")
            for card in info_cards:
                try:
                    label = card.find_element(By.CSS_SELECTOR, ".label, .title, h3, h4").text.strip()
                    value = card.find_element(By.CSS_SELECTOR, ".value, .content, p").text.strip()
                    if label and value:
                        traits[label] = value
                except:
                    continue
            
        except Exception as e:
            print(f"        Warning: Could not extract traits: {e}")
        
        return traits

    def _extract_physical_data_selenium(self, driver) -> Dict[str, Any]:
        """Extract physical characteristics using Selenium"""
        data = {}
        
        try:
            # Extract from traits if available
            traits = self._extract_traits_selenium(driver)
            
            # Height processing
            height_text = traits.get('Height', '')
            if height_text:
                height_min, height_max = self._parse_height(height_text)
                data['height_cm_min'] = height_min
                data['height_cm_max'] = height_max
            
            # Weight processing
            weight_text = traits.get('Weight', '')
            if weight_text:
                weight_min, weight_max = self._parse_weight(weight_text)
                data['weight_kg_min'] = weight_min
                data['weight_kg_max'] = weight_max
            
            # Life expectancy processing
            life_text = traits.get('Life Expectancy', '') or traits.get('Life Span', '')
            if life_text:
                life_min, life_max = self._parse_lifespan(life_text)
                data['lifespan_years_min'] = life_min
                data['lifespan_years_max'] = life_max
            
            # Size determination
            if 'weight_kg_max' in data:
                data['size'] = self._determine_size(data.get('weight_kg_max', 0))
            
        except Exception as e:
            print(f"        Warning: Could not extract physical data: {e}")
        
        return data

    def _extract_temperament_selenium(self, driver) -> Dict[str, Any]:
        """Extract temperament and behavioral traits using Selenium"""
        data = {}
        
        try:
            # Look for rating systems (stars, bars, numbers)
            rating_elements = driver.find_elements(By.CSS_SELECTOR, ".rating, .star-rating, .trait-rating")
            for elem in rating_elements:
                try:
                    trait_name = elem.find_element(By.XPATH, "./preceding-sibling::*[1]").text.lower()
                    # Count filled stars or extract number
                    filled_stars = len(elem.find_elements(By.CSS_SELECTOR, ".filled, .active, [aria-checked='true']"))
                    
                    if 'friendly' in trait_name and 'dog' in trait_name:
                        data['friendliness_to_dogs'] = filled_stars
                    elif 'friendly' in trait_name and ('people' in trait_name or 'human' in trait_name):
                        data['friendliness_to_humans'] = filled_stars
                    elif 'energy' in trait_name:
                        data['energy'] = self._normalize_energy(filled_stars)
                    elif 'shed' in trait_name:
                        data['shedding'] = self._normalize_level(filled_stars)
                    elif 'train' in trait_name:
                        data['trainability'] = self._normalize_trainability(filled_stars)
                    elif 'bark' in trait_name:
                        data['bark_level'] = self._normalize_level(filled_stars)
                except:
                    continue
            
            # Look for text-based traits
            trait_texts = driver.find_elements(By.CSS_SELECTOR, ".trait-text, .characteristic")
            for elem in trait_texts:
                try:
                    text = elem.text.lower()
                    if 'energy' in text:
                        if 'high' in text:
                            data['energy'] = 'high'
                        elif 'moderate' in text or 'medium' in text:
                            data['energy'] = 'moderate'
                        elif 'low' in text:
                            data['energy'] = 'low'
                except:
                    continue
                    
        except Exception as e:
            print(f"        Warning: Could not extract temperament: {e}")
        
        return data

    def _extract_content_selenium(self, driver) -> Dict[str, Any]:
        """Extract comprehensive content sections using Selenium"""
        content = {}
        
        try:
            # Look for tabbed content or sections
            sections = driver.find_elements(By.CSS_SELECTOR, "section, .tab-content, .breed-section")
            
            for section in sections:
                try:
                    # Get section title
                    title_elem = section.find_element(By.CSS_SELECTOR, "h2, h3, .section-title")
                    title = title_elem.text.lower().strip()
                    
                    # Get section content
                    content_elem = section.find_element(By.CSS_SELECTOR, ".content, .text, p")
                    text = content_elem.text.strip()
                    
                    # Map to our schema
                    if 'history' in title:
                        content['history'] = text
                    elif 'personality' in title or 'temperament' in title:
                        content['personality'] = text
                    elif 'health' in title:
                        content['health'] = text
                    elif 'care' in title:
                        content['care'] = text
                    elif 'feeding' in title or 'nutrition' in title:
                        content['feeding'] = text
                    elif 'grooming' in title:
                        content['grooming'] = text
                    elif 'exercise' in title:
                        content['exercise'] = text
                    elif 'training' in title:
                        content['training'] = text
                    else:
                        content['about'] = content.get('about', '') + ' ' + text
                        
                except:
                    continue
            
            # If no structured content found, get all text
            if not content:
                main_elem = driver.find_element(By.TAG_NAME, "main")
                all_text = main_elem.text
                content['about'] = all_text[:5000]  # Limit length
                
        except Exception as e:
            print(f"        Warning: Could not extract content: {e}")
        
        return content

    def _parse_height(self, height_text: str) -> Tuple[Optional[float], Optional[float]]:
        """Parse height text and convert to cm"""
        try:
            # Look for patterns like "22-26 inches" or "22 to 26 inches"
            numbers = re.findall(r'(\d+(?:\.\d+)?)', height_text)
            if len(numbers) >= 2:
                min_inches = float(numbers[0])
                max_inches = float(numbers[1])
                return min_inches * 2.54, max_inches * 2.54
            elif len(numbers) == 1:
                inches = float(numbers[0])
                return inches * 2.54, inches * 2.54
        except:
            pass
        return None, None

    def _parse_weight(self, weight_text: str) -> Tuple[Optional[float], Optional[float]]:
        """Parse weight text and convert to kg"""
        try:
            # Look for patterns like "50-90 pounds" or "50 to 90 lbs"
            numbers = re.findall(r'(\d+(?:\.\d+)?)', weight_text)
            if len(numbers) >= 2:
                min_lbs = float(numbers[0])
                max_lbs = float(numbers[1])
                return min_lbs * 0.453592, max_lbs * 0.453592
            elif len(numbers) == 1:
                lbs = float(numbers[0])
                return lbs * 0.453592, lbs * 0.453592
        except:
            pass
        return None, None

    def _parse_lifespan(self, life_text: str) -> Tuple[Optional[int], Optional[int]]:
        """Parse lifespan text"""
        try:
            numbers = re.findall(r'(\d+)', life_text)
            if len(numbers) >= 2:
                return int(numbers[0]), int(numbers[1])
            elif len(numbers) == 1:
                years = int(numbers[0])
                return years, years
        except:
            pass
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

    def _normalize_energy(self, level: int) -> str:
        """Normalize energy level"""
        if level <= 1:
            return 'low'
        elif level <= 2:
            return 'moderate'
        elif level <= 4:
            return 'high'
        else:
            return 'very high'

    def _normalize_level(self, level: int) -> str:
        """Normalize general level (shedding, barking)"""
        if level <= 2:
            return 'low'
        elif level <= 3:
            return 'moderate'
        else:
            return 'high'

    def _normalize_trainability(self, level: int) -> str:
        """Normalize trainability"""
        if level >= 4:
            return 'easy'
        elif level >= 2:
            return 'moderate'
        else:
            return 'challenging'

    def _map_to_schema(self, breed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map extracted data to database schema"""
        # Already mostly mapped, just ensure all fields are present
        return breed_data

    def save_breed(self, breed_data: Dict[str, Any]) -> bool:
        """Save breed to akc_breeds table"""
        try:
            # Check if breed already exists
            existing = self.supabase.table('akc_breeds').select('id').eq('breed_slug', breed_data['breed_slug']).execute()
            
            if existing.data:
                # Update existing breed
                result = self.supabase.table('akc_breeds').update(breed_data).eq('breed_slug', breed_data['breed_slug']).execute()
                self.stats['updated'] += 1
                print(f"    ✅ Updated: {breed_data.get('display_name', 'Unknown')}")
            else:
                # Insert new breed
                result = self.supabase.table('akc_breeds').insert(breed_data).execute()
                self.stats['new_breeds'] += 1
                print(f"    ✅ Added: {breed_data.get('display_name', 'Unknown')}")
            
            # Track for QA report
            self.qa_report.append({
                'breed_name': breed_data.get('display_name', 'Unknown'),
                'breed_slug': breed_data.get('breed_slug', ''),
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

    def scrape_breed(self, url: str) -> bool:
        """Scrape a single breed URL"""
        try:
            print(f"  🔍 Scraping: {url}")
            
            # Extract breed data using Selenium
            breed_data = self.extract_breed_data_selenium(url)
            
            if breed_data and breed_data.get('extraction_status') == 'success':
                self.stats['extraction_success'] += 1
                # Save to database
                return self.save_breed(breed_data)
            else:
                self.stats['extraction_failed'] += 1
                print(f"    ⚠️ Extraction failed for {url}")
                return False
                
        except Exception as e:
            print(f"    ❌ Error scraping {url}: {e}")
            self.stats['errors'] += 1
            return False

    def run(self, urls: List[str], limit: Optional[int] = None):
        """Run the scraper on a list of URLs"""
        print("🚀 Starting Enhanced AKC Breed Scraper with Selenium")
        print("=" * 60)
        
        # Limit URLs if specified
        if limit:
            urls = urls[:limit]
            print(f"📊 Limited to {limit} breeds")
        
        print(f"📋 Processing {len(urls)} breed URLs\n")
        
        for idx, url in enumerate(urls, 1):
            print(f"[{idx}/{len(urls)}] Processing breed {idx}")
            
            # Scrape the breed
            self.scrape_breed(url)
            self.stats['processed'] += 1
            
            # Rate limiting
            if idx < len(urls):
                time.sleep(self.config['rate_limit_seconds'])
            
            # Progress update every 10 breeds
            if idx % 10 == 0:
                self._print_progress()
        
        # Final report
        self._print_final_report()
        
        # Save QA report
        self._save_qa_report()

    def _print_progress(self):
        """Print progress update"""
        print(f"\n📊 Progress Update:")
        print(f"  Processed: {self.stats['processed']}")
        print(f"  New breeds: {self.stats['new_breeds']}")
        print(f"  Updated: {self.stats['updated']}")
        print(f"  Extraction success: {self.stats['extraction_success']}")
        print()

    def _print_final_report(self):
        """Print final scraping report"""
        print("\n" + "=" * 60)
        print("🎯 ENHANCED AKC BREED SCRAPER REPORT")
        print("=" * 60)
        print(f"URLs processed: {self.stats['processed']}")
        print(f"New breeds added: {self.stats['new_breeds']}")
        print(f"Breeds updated: {self.stats['updated']}")
        print(f"Breeds skipped: {self.stats['skipped']}")
        print(f"Extraction success: {self.stats['extraction_success']}")
        print(f"Extraction failed: {self.stats['extraction_failed']}")
        print(f"Errors: {self.stats['errors']}")
        
        success_rate = (self.stats['extraction_success'] / max(self.stats['processed'], 1)) * 100
        print(f"Success rate: {success_rate:.1f}%")
        print("=" * 60)

    def _save_qa_report(self):
        """Save QA report to CSV"""
        import csv
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"akc_breed_qa_report_enhanced_{timestamp}.csv"
        
        with open(filename, 'w', newline='') as f:
            if self.qa_report:
                fieldnames = self.qa_report[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.qa_report)
        
        print(f"📄 QA report saved to: {filename}")


def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced AKC Breed Scraper with Selenium')
    parser.add_argument('--test', action='store_true', help='Run test with 5 breeds')
    parser.add_argument('--limit', type=int, help='Limit number of breeds to scrape')
    parser.add_argument('--urls-file', type=str, help='File containing breed URLs')
    parser.add_argument('--url', type=str, help='Scrape a single breed URL')
    
    args = parser.parse_args()
    
    # Initialize scraper
    scraper = EnhancedAKCBreedScraper()
    
    # Determine URLs to scrape
    if args.url:
        # Single URL
        urls = [args.url]
    elif args.urls_file:
        # Load from file
        with open(args.urls_file, 'r') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    elif args.test:
        # Test URLs
        urls = [
            'https://www.akc.org/dog-breeds/german-shepherd-dog/',
            'https://www.akc.org/dog-breeds/golden-retriever/',
            'https://www.akc.org/dog-breeds/french-bulldog/',
            'https://www.akc.org/dog-breeds/labrador-retriever/',
            'https://www.akc.org/dog-breeds/siberian-husky/'
        ]
    else:
        print("Please specify --url, --urls-file, or --test")
        sys.exit(1)
    
    # Run scraper
    scraper.run(urls, limit=args.limit)


if __name__ == "__main__":
    main()