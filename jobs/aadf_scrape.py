#!/usr/bin/env python3
"""
All About Dog Food (AADF) scraper job
HTML-only scraping with polite rate limiting and comprehensive nutrition extraction
"""
import os
import sys
import json
import time
import random
import hashlib
import argparse
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urljoin, urlparse

import yaml
import requests
from bs4 import BeautifulSoup
from google.cloud import storage
from supabase import create_client, Client
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from etl.normalize_foods import (
    parse_energy, parse_percent, parse_pack_size,
    tokenize_ingredients, check_contains_chicken,
    parse_price, normalize_currency, generate_fingerprint,
    normalize_form, normalize_life_stage, extract_gtin, clean_text,
    estimate_kcal_from_analytical, contains, derive_form, derive_life_stage
)
from etl.nutrition_parser import parse_nutrition_from_html

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AADFScraper:
    def __init__(self, config_path: str = None):
        """Initialize AADF scraper with configuration"""
        self.config = self._load_config(config_path)
        self.profile = self._load_profile()
        self.session = self._setup_session()
        self.supabase = self._setup_supabase()
        self.gcs_client = self._setup_gcs()
        self.stats = {
            'scanned': 0,
            'new': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0,
            'nutrition_found': 0,
            'nutrition_missing': 0
        }
        
    def _load_config(self, config_path: str = None) -> Dict:
        """Load configuration from file or environment"""
        if config_path and Path(config_path).exists():
            with open(config_path) as f:
                return yaml.safe_load(f)
        
        return {
            'gcs_bucket': os.getenv('GCS_BUCKET', 'lupito-content-raw-eu'),
            'supabase_url': os.getenv('SUPABASE_URL'),
            'supabase_key': os.getenv('SUPABASE_SERVICE_KEY'),
            'rate_limit_ms': 2000,  # 2 seconds per request
            'jitter_ms': 300,       # ±300ms jitter
            'timeout': 30,
            'max_retries': 3
        }
    
    def _load_profile(self) -> Dict:
        """Load scraping profile for AADF"""
        profile_path = Path(__file__).parent.parent / 'profiles' / 'aadf_profile_simple.yaml'
        with open(profile_path) as f:
            return yaml.safe_load(f)
    
    def _setup_session(self) -> requests.Session:
        """Setup requests session with headers"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': self.profile.get('user_agent', 
                'Mozilla/5.0 (compatible; LupitoBot/1.0; +https://lupito.app; respects robots.txt)'),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive'
        })
        session.timeout = self.config.get('timeout', 30)
        return session
    
    def _setup_supabase(self) -> Client:
        """Setup Supabase client"""
        return create_client(
            self.config['supabase_url'],
            self.config['supabase_key']
        )
    
    def _setup_gcs(self) -> storage.Client:
        """Setup Google Cloud Storage client"""
        return storage.Client()
    
    def _rate_limit(self):
        """Apply rate limiting with jitter"""
        base_delay = self.config.get('rate_limit_ms', 2000) / 1000.0
        jitter = self.config.get('jitter_ms', 300) / 1000.0
        delay = base_delay + random.uniform(-jitter, jitter)
        time.sleep(max(0.1, delay))  # Minimum 100ms
    
    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse HTML page"""
        try:
            self._rate_limit()
            
            logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=self.config['timeout'])
            response.raise_for_status()
            
            # Save raw HTML to GCS
            self._save_raw_html(url, response.text)
            
            return BeautifulSoup(response.text, 'html.parser')
            
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            self.stats['errors'] += 1
            return None
    
    def _save_raw_html(self, url: str, html_content: str):
        """Save raw HTML to Google Cloud Storage"""
        try:
            # Generate consistent hash from URL
            url_hash = hashlib.md5(url.encode()).hexdigest()
            today = datetime.now().strftime('%Y-%m-%d')
            
            # Path: gs://bucket/aadf/YYYY-MM-DD/hash.html
            blob_path = f"aadf/{today}/{url_hash}.html"
            
            bucket = self.gcs_client.bucket(self.config['gcs_bucket'])
            blob = bucket.blob(blob_path)
            
            # Upload with metadata
            blob.metadata = {
                'source_url': url,
                'scraped_at': datetime.now().isoformat(),
                'scraper': 'aadf_scrape.py'
            }
            
            blob.upload_from_string(html_content, content_type='text/html')
            logger.debug(f"Saved raw HTML to: gs://{self.config['gcs_bucket']}/{blob_path}")
            
        except Exception as e:
            logger.warning(f"Failed to save raw HTML for {url}: {e}")
    
    def extract_with_selectors(self, soup: BeautifulSoup, field_config: Dict) -> Optional[str]:
        """Extract field using CSS/XPath selectors"""
        # Try CSS selectors first
        for css_sel in field_config.get('css', []):
            elements = soup.select(css_sel)
            if elements:
                text = elements[0].get_text(strip=True)
                if text:
                    return text
        
        # Try text-based extraction for special cases
        for text_css in field_config.get('text_css', []):
            elements = soup.select(text_css)
            if elements:
                text = elements[0].get_text(strip=True)
                if text:
                    return text
        
        return None
    
    def extract_brand_and_name(self, soup: BeautifulSoup, url: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract brand and product name from page"""
        # Try to find brand and name in title or header
        title = soup.find('title')
        if title:
            title_text = title.get_text(strip=True)
            # Pattern: "Brand Name Product - All About Dog Food"
            if ' - ' in title_text:
                product_part = title_text.split(' - ')[0].strip()
                # Try to split brand and product
                words = product_part.split()
                if len(words) >= 2:
                    brand = words[0]
                    product_name = ' '.join(words[1:])
                    return brand, product_name
        
        # Try h1 tag
        h1 = soup.find('h1')
        if h1:
            h1_text = h1.get_text(strip=True)
            words = h1_text.split()
            if len(words) >= 2:
                brand = words[0]
                product_name = ' '.join(words[1:])
                return brand, product_name
        
        # Fallback: extract from URL
        url_parts = url.rstrip('/').split('/')
        if url_parts:
            slug = url_parts[-1]
            # Convert slug to readable name
            name = slug.replace('-', ' ').title()
            words = name.split()
            if len(words) >= 2:
                return words[0], ' '.join(words[1:])
        
        return None, None
    
    def extract_nutrition(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract nutrition information from HTML"""
        nutrition_data = {}
        
        # First try the specialized nutrition parser
        try:
            parsed_nutrition = parse_nutrition_from_html(str(soup))
            if parsed_nutrition:
                nutrition_data.update(parsed_nutrition)
                logger.debug(f"Nutrition parser found: {parsed_nutrition}")
        except Exception as e:
            logger.warning(f"Nutrition parser failed: {e}")
        
        # Try manual extraction with selectors
        nutrition_config = self.profile['selectors']['nutrition']
        
        # Look for nutrition table
        for table_css in nutrition_config.get('table_css', []):
            table = soup.select_one(table_css)
            if table:
                nutrition_data.update(self._extract_from_table(table))
                break
        
        # Look for nutrition text sections
        if not nutrition_data:
            for text_css in nutrition_config.get('text_css', []):
                section = soup.select_one(text_css)
                if section:
                    nutrition_data.update(self._extract_from_text(section.get_text()))
                    break
        
        # Apply Atwater estimation if we have protein/fat but no energy
        if not nutrition_data.get('kcal_per_100g') and (
            nutrition_data.get('protein_percent') or nutrition_data.get('fat_percent')
        ):
            estimated_kcal = estimate_kcal_from_analytical(
                protein_pct=nutrition_data.get('protein_percent'),
                fat_pct=nutrition_data.get('fat_percent')
            )
            if estimated_kcal:
                nutrition_data['kcal_per_100g'] = estimated_kcal
                nutrition_data['kcal_basis'] = 'estimated'
        
        return nutrition_data
    
    def _extract_from_table(self, table) -> Dict[str, Any]:
        """Extract nutrition from HTML table"""
        data = {}
        rows = table.find_all('tr')
        
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                label = cells[0].get_text(strip=True).lower()
                value_text = cells[1].get_text(strip=True)
                
                # Extract percentage values
                percent_match = re.search(r'(\d+(?:\.\d+)?)\s*%', value_text)
                if percent_match:
                    percent_val = float(percent_match.group(1))
                    
                    if 'protein' in label:
                        data['protein_percent'] = percent_val
                    elif any(x in label for x in ['fat', 'oil']):
                        data['fat_percent'] = percent_val
                    elif any(x in label for x in ['fibre', 'fiber']):
                        data['fiber_percent'] = percent_val
                    elif 'ash' in label:
                        data['ash_percent'] = percent_val
                    elif 'moisture' in label:
                        data['moisture_percent'] = percent_val
                
                # Extract energy values
                kcal_match = re.search(r'(\d+(?:\.\d+)?)\s*kcal', value_text)
                if kcal_match and 'energy' in label:
                    data['kcal_per_100g'] = float(kcal_match.group(1))
                    data['kcal_basis'] = 'measured'
        
        return data
    
    def _extract_from_text(self, text: str) -> Dict[str, Any]:
        """Extract nutrition from text content"""
        data = {}
        
        # Define patterns for each nutrient
        patterns = {
            'protein_percent': [
                r'(?:Crude\s+)?Protein:?\s*(\d+(?:\.\d+)?)\s*%',
                r'Protein\s*(\d+(?:\.\d+)?)\s*%'
            ],
            'fat_percent': [
                r'(?:Crude\s+)?(?:Fat|Oil(?:s)?\s*(?:&|and)?\s*Fat(?:s)?):?\s*(\d+(?:\.\d+)?)\s*%',
                r'Fat\s*(?:Content)?:?\s*(\d+(?:\.\d+)?)\s*%'
            ],
            'fiber_percent': [
                r'(?:Crude\s+)?Fib(?:re|er):?\s*(\d+(?:\.\d+)?)\s*%'
            ],
            'ash_percent': [
                r'(?:Crude\s+)?Ash:?\s*(\d+(?:\.\d+)?)\s*%'
            ],
            'moisture_percent': [
                r'Moisture:?\s*(\d+(?:\.\d+)?)\s*%'
            ]
        }
        
        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    data[field] = float(match.group(1))
                    break
        
        # Extract energy
        kcal_match = re.search(r'(\d+(?:\.\d+)?)\s*kcal(?:/100g)?', text, re.IGNORECASE)
        if kcal_match:
            data['kcal_per_100g'] = float(kcal_match.group(1))
            data['kcal_basis'] = 'measured'
        
        return data
    
    def scrape_product(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape a single product page"""
        soup = self.fetch_page(url)
        if not soup:
            return None
        
        self.stats['scanned'] += 1
        
        # Extract basic product info
        brand, product_name = self.extract_brand_and_name(soup, url)
        if not brand or not product_name:
            logger.warning(f"Could not extract brand/name from {url}")
            return None
        
        # Extract ingredients
        ingredients_config = self.profile['selectors']['ingredients']
        ingredients_text = self.extract_with_selectors(soup, ingredients_config)
        
        # Extract nutrition
        nutrition_data = self.extract_nutrition(soup)
        if nutrition_data:
            self.stats['nutrition_found'] += 1
        else:
            self.stats['nutrition_missing'] += 1
        
        # Extract form and life_stage
        form_config = self.profile['selectors']['form']
        form_text = self.extract_with_selectors(soup, form_config)
        form = normalize_form(form_text) if form_text else derive_form(ingredients_text or '')
        
        life_stage_config = self.profile['selectors']['life_stage']
        life_stage_text = self.extract_with_selectors(soup, life_stage_config)
        life_stage = normalize_life_stage(life_stage_text) if life_stage_text else derive_life_stage(ingredients_text or '')
        
        # Extract rating
        rating_config = self.profile['selectors']['rating']
        rating_text = self.extract_with_selectors(soup, rating_config)
        rating = None
        if rating_text:
            rating_match = re.search(r'(\d+(?:\.\d+)?)', rating_text)
            if rating_match:
                rating = float(rating_match.group(1))
        
        # Build product data
        product_data = {
            'source_domain': self.profile['domain'],
            'source_url': url,
            'brand': clean_text(brand),
            'product_name': clean_text(product_name),
            'form': form,
            'life_stage': life_stage,
            'ingredients': clean_text(ingredients_text) if ingredients_text else None,
            'available_countries': ['UK', 'EU'],  # AADF focuses on UK market
            'quality_rating': rating,
            'scraped_at': datetime.now().isoformat()
        }
        
        # Add nutrition data
        product_data.update(nutrition_data)
        
        # Add derived fields
        if ingredients_text:
            product_data['ingredients_tokens'] = tokenize_ingredients(ingredients_text)
            product_data['contains_chicken'] = check_contains_chicken(ingredients_text)
        
        logger.info(f"Scraped: {brand} {product_name} - Nutrition: {bool(nutrition_data)}")
        return product_data
    
    def save_to_database(self, product_data: Dict[str, Any]) -> bool:
        """Save product data to database"""
        try:
            # Generate fingerprint for deduplication
            ingredients = product_data.get('ingredients', '')
            fingerprint = generate_fingerprint(
                product_data['brand'],
                product_data['product_name'],
                ingredients
            )
            
            # Save to food_raw
            raw_record = {
                'raw_type': 'html',
                'source_domain': product_data['source_domain'],
                'source_url': product_data['source_url'],
                'raw_data': json.dumps(product_data),
                'scraped_at': datetime.now().isoformat()
            }
            
            raw_result = self.supabase.table('food_raw').insert(raw_record).execute()
            raw_id = raw_result.data[0]['id'] if raw_result.data else None
            
            # Prepare candidate record
            candidate_data = {
                'raw_id': raw_id,
                'fingerprint': fingerprint,
                'source_domain': product_data['source_domain'],
                'source_url': product_data['source_url'],
                'brand': product_data['brand'],
                'product_name': product_data['product_name'],
                'form': product_data.get('form'),
                'life_stage': product_data.get('life_stage'),
                'ingredients': product_data.get('ingredients'),
                'ingredients_tokens': product_data.get('ingredients_tokens'),
                'contains_chicken': product_data.get('contains_chicken', False),
                'protein_percent': product_data.get('protein_percent'),
                'fat_percent': product_data.get('fat_percent'),
                'fiber_percent': product_data.get('fiber_percent'),
                'ash_percent': product_data.get('ash_percent'),
                'moisture_percent': product_data.get('moisture_percent'),
                'kcal_per_100g': product_data.get('kcal_per_100g'),
                'kcal_basis': product_data.get('kcal_basis'),
                'available_countries': product_data.get('available_countries'),
                'quality_rating': product_data.get('quality_rating'),
                'first_seen_at': datetime.now().isoformat(),
                'last_seen_at': datetime.now().isoformat()
            }
            
            # Check for existing record
            existing = self.supabase.table('food_candidates')\
                .select('*')\
                .eq('fingerprint', fingerprint)\
                .execute()
            
            if existing.data:
                # Update existing record
                update_data = {k: v for k, v in candidate_data.items() 
                              if k not in ['fingerprint', 'first_seen_at']}
                update_data['last_seen_at'] = datetime.now().isoformat()
                
                self.supabase.table('food_candidates')\
                    .update(update_data)\
                    .eq('fingerprint', fingerprint)\
                    .execute()
                
                self.stats['updated'] += 1
                logger.info(f"Updated existing record: {fingerprint}")
            else:
                # Insert new record
                self.supabase.table('food_candidates').insert(candidate_data).execute()
                self.stats['new'] += 1
                logger.info(f"Inserted new record: {fingerprint}")
            
            return True
            
        except Exception as e:
            logger.error(f"Database error: {e}")
            self.stats['errors'] += 1
            return False
    
    def run_from_seed_list(self, seed_file: str, limit: int = None):
        """Run scraper from seed URL list"""
        try:
            with open(seed_file, 'r') as f:
                urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            if limit:
                urls = urls[:limit]
            
            logger.info(f"Starting AADF scrape with {len(urls)} URLs")
            
            for i, url in enumerate(urls, 1):
                logger.info(f"Processing {i}/{len(urls)}: {url}")
                
                product_data = self.scrape_product(url)
                if product_data:
                    self.save_to_database(product_data)
                else:
                    self.stats['skipped'] += 1
                
                # Progress update every 10 items
                if i % 10 == 0:
                    self.print_stats()
            
            self.print_final_stats()
            
        except Exception as e:
            logger.error(f"Seed list processing failed: {e}")
            self.print_final_stats()
    
    def print_stats(self):
        """Print current statistics"""
        logger.info(f"Progress: {self.stats}")
    
    def print_final_stats(self):
        """Print final harvest report"""
        print("\n" + "="*50)
        print("AADF HARVEST REPORT")
        print("="*50)
        print(f"Scanned:          {self.stats['scanned']}")
        print(f"New records:      {self.stats['new']}")
        print(f"Updated records:  {self.stats['updated']}")
        print(f"Skipped:          {self.stats['skipped']}")
        print(f"Errors:           {self.stats['errors']}")
        print(f"Nutrition found:  {self.stats['nutrition_found']}")
        print(f"Nutrition missing:{self.stats['nutrition_missing']}")
        print("="*50)


def main():
    parser = argparse.ArgumentParser(description='AADF Scraper')
    parser.add_argument('--seed-list', required=True, help='Path to seed URL list')
    parser.add_argument('--limit', type=int, help='Limit number of URLs to process')
    parser.add_argument('--config', help='Path to config file')
    
    args = parser.parse_args()
    
    scraper = AADFScraper(config_path=args.config)
    scraper.run_from_seed_list(args.seed_list, limit=args.limit)


if __name__ == '__main__':
    main()