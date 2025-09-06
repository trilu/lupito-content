#!/usr/bin/env python3
"""
PetFoodExpert scraper job
Crawls product URLs, saves raw HTML to GCS, parses data, and upserts to Supabase
"""
import os
import sys
import json
import time
import random
import hashlib
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
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

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PetFoodExpertScraper:
    def __init__(self, config_path: str = None):
        """Initialize scraper with configuration"""
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
            'errors': 0
        }
        
    def _load_config(self, config_path: str = None) -> Dict:
        """Load configuration from file or environment"""
        if config_path and Path(config_path).exists():
            with open(config_path) as f:
                return yaml.safe_load(f)
        
        # Default configuration
        return {
            'gcs_bucket': os.getenv('GCS_BUCKET', 'lupito-content-raw-eu'),
            'supabase_url': os.getenv('SUPABASE_URL'),
            'supabase_key': os.getenv('SUPABASE_SERVICE_KEY'),
            'rate_limit': 0.5,  # requests per second
            'jitter': [0.5, 2.0],  # random delay range
            'timeout': 30,
            'max_retries': 3
        }
    
    def _load_profile(self) -> Dict:
        """Load scraping profile for petfoodexpert"""
        profile_path = Path(__file__).parent.parent / 'profiles' / 'pfx_profile.yaml'
        with open(profile_path) as f:
            return yaml.safe_load(f)
    
    def _setup_session(self) -> requests.Session:
        """Setup requests session with headers"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': self.profile.get('user_agent', 
                'Mozilla/5.0 (compatible; LupitoBot/1.0)')
        })
        return session
    
    def _setup_supabase(self) -> Optional[Client]:
        """Setup Supabase client"""
        url = self.config.get('supabase_url')
        key = self.config.get('supabase_key')
        
        if not url or not key:
            logger.warning("Supabase credentials not found. DB operations will be skipped.")
            return None
        
        return create_client(url, key)
    
    def _setup_gcs(self) -> Optional[storage.Client]:
        """Setup Google Cloud Storage client"""
        try:
            return storage.Client()
        except Exception as e:
            logger.warning(f"GCS client setup failed: {e}. Raw HTML storage will be skipped.")
            return None
    
    def _respect_rate_limit(self, custom_delay_ms: int = None):
        """Apply rate limiting with jitter"""
        if custom_delay_ms:
            # Use custom delay with jitter
            jitter_ms = self.profile['rate_limit'].get('jitter_ms', 300)
            delay = custom_delay_ms / 1000.0
            jitter = random.uniform(-jitter_ms, jitter_ms) / 1000.0
            time.sleep(max(0.1, delay + jitter))
        else:
            # Use default rate limiting
            base_delay = 1.0 / self.config['rate_limit']
            jitter = random.uniform(*self.config['jitter'])
            time.sleep(base_delay + jitter)
    
    def _fetch_page(self, url: str) -> Optional[str]:
        """Fetch a page with retries and rate limiting"""
        self._respect_rate_limit()
        
        for attempt in range(self.config['max_retries']):
            try:
                response = self.session.get(
                    url, 
                    timeout=self.config['timeout']
                )
                response.raise_for_status()
                return response.text
            except Exception as e:
                logger.warning(f"Fetch failed (attempt {attempt + 1}): {url} - {e}")
                if attempt < self.config['max_retries'] - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
        
        return None
    
    def _save_to_gcs(self, html: str, url: str) -> Optional[str]:
        """Save HTML to Google Cloud Storage"""
        if not self.gcs_client:
            return None
        
        try:
            # Generate path with date hierarchy
            parsed = urlparse(url)
            date_str = datetime.utcnow().strftime('%Y-%m-%d')
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            path = f"petfoodexpert/{date_str}/{url_hash}.html"
            
            # Upload to GCS
            bucket = self.gcs_client.bucket(self.config['gcs_bucket'])
            blob = bucket.blob(path)
            blob.upload_from_string(html, content_type='text/html')
            
            return f"gs://{self.config['gcs_bucket']}/{path}"
        except Exception as e:
            logger.error(f"GCS upload failed: {e}")
            return None
    
    def _extract_field(self, soup: BeautifulSoup, selectors: Dict) -> Optional[str]:
        """Extract field using CSS/XPath selectors"""
        # Try CSS selectors
        if 'css' in selectors:
            for selector in selectors['css']:
                element = soup.select_one(selector)
                if element:
                    return clean_text(element.get_text())
        
        # Note: XPath would require lxml, keeping CSS for simplicity
        return None
    
    def _extract_nutrition(self, soup: BeautifulSoup) -> Dict[str, Optional[float]]:
        """Extract nutrition information from page"""
        nutrition = {}
        nutrition_config = self.profile['selectors']['nutrition']
        
        # Find nutrition table
        table = None
        for selector in nutrition_config.get('table_css', []):
            table = soup.select_one(selector)
            if table:
                break
        
        if not table:
            return nutrition
        
        # Extract rows
        rows = table.select('tr')
        for row in rows:
            cells = row.select('td, th')
            if len(cells) >= 2:
                label = cells[0].get_text().lower()
                value = cells[1].get_text()
                
                # Match against patterns
                if 'kcal' in label or 'energy' in label or 'calor' in label:
                    nutrition['kcal_per_100g'] = parse_energy(value)
                elif 'protein' in label:
                    nutrition['protein_percent'] = parse_percent(value)
                elif 'fat' in label:
                    nutrition['fat_percent'] = parse_percent(value)
                elif 'fiber' in label or 'fibre' in label:
                    nutrition['fiber_percent'] = parse_percent(value)
                elif 'ash' in label:
                    nutrition['ash_percent'] = parse_percent(value)
                elif 'moisture' in label or 'water' in label:
                    nutrition['moisture_percent'] = parse_percent(value)
        
        return nutrition
    
    def _parse_product(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        """Parse product data from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        selectors = self.profile['selectors']
        
        # Extract basic fields
        brand = self._extract_field(soup, selectors.get('brand', {}))
        product_name = self._extract_field(soup, selectors.get('product_name', {}))
        
        if not brand or not product_name:
            logger.warning(f"Missing required fields (brand/name) for {url}")
            return None
        
        # Extract other fields
        form_raw = self._extract_field(soup, selectors.get('form', {}))
        life_stage_raw = self._extract_field(soup, selectors.get('life_stage', {}))
        
        # Derive form and life stage if not explicit
        form = normalize_form(form_raw) or derive_form(product_name)
        life_stage = normalize_life_stage(life_stage_raw) or derive_life_stage(product_name)
        ingredients_raw = self._extract_field(soup, selectors.get('ingredients', {}))
        gtin = self._extract_field(soup, selectors.get('gtin', {}))
        
        # Extract nutrition
        nutrition = self._extract_nutrition(soup)
        
        # Extract price
        price_str = self._extract_field(soup, selectors.get('price', {}))
        price_data = parse_price(price_str) if price_str else None
        
        # Extract pack sizes
        pack_sizes = []
        pack_elements = soup.select(','.join(selectors.get('pack_sizes', {}).get('css', [])))
        for elem in pack_elements:
            size_data = parse_pack_size(elem.get_text())
            if size_data:
                pack_sizes.append(size_data['display'])
        
        # Process ingredients
        ingredients_tokens = tokenize_ingredients(ingredients_raw) if ingredients_raw else []
        contains_chicken = check_contains_chicken(ingredients_tokens) or contains(ingredients_tokens, ['chicken', 'chicken fat', 'poultry'])
        
        # Generate fingerprint
        fingerprint = generate_fingerprint(brand, product_name, ingredients_raw)
        
        # Build product data
        product_data = {
            'source_domain': 'petfoodexpert.com',
            'source_url': url,
            'brand': brand,
            'product_name': product_name,
            'form': normalize_form(form),
            'life_stage': normalize_life_stage(life_stage),
            'ingredients_raw': ingredients_raw,
            'ingredients_tokens': ingredients_tokens,
            'contains_chicken': contains_chicken,
            'pack_sizes': pack_sizes,
            'gtin': extract_gtin(gtin) if gtin else None,
            'fingerprint': fingerprint,
            **nutrition
        }
        
        # Add price if available
        if price_data:
            # Use currency rates from profile
            rates = self.profile.get('currency_rates', {})
            normalized = normalize_currency(price_data['amount'], price_data['currency'], rates)
            product_data['price_currency'] = price_data['currency']
            product_data['price_eur'] = normalized['price_eur']
        
        # Estimate kcal if not provided but we have analytical data
        if not nutrition.get('kcal_per_100g'):
            estimated_kcal = estimate_kcal_from_analytical(
                nutrition.get('protein_percent'),
                nutrition.get('fat_percent'),
                nutrition.get('fiber_percent'),
                nutrition.get('ash_percent'),
                nutrition.get('moisture_percent')
            )
            if estimated_kcal:
                product_data['kcal_per_100g'] = estimated_kcal
                product_data['kcal_estimated'] = True
        
        return product_data
    
    def _upsert_raw(self, url: str, gcs_path: str, parsed_json: Dict) -> bool:
        """Upsert to food_raw table"""
        if not self.supabase:
            return False
        
        try:
            data = {
                'source_domain': 'petfoodexpert.com',
                'source_url': url,
                'html_gcs_path': gcs_path,
                'parsed_json': parsed_json,
                'fingerprint': parsed_json.get('fingerprint'),
                'last_seen_at': datetime.utcnow().isoformat()
            }
            
            # Upsert (insert or update based on source_url)
            result = self.supabase.table('food_raw').upsert(
                data,
                on_conflict='source_url'
            ).execute()
            
            return True
        except Exception as e:
            logger.error(f"Failed to upsert raw data: {e}")
            return False
    
    def _upsert_candidate(self, product_data: Dict) -> bool:
        """Upsert to food_candidates table"""
        if not self.supabase:
            return False
        
        try:
            # Add timestamp
            product_data['last_seen_at'] = datetime.utcnow().isoformat()
            
            # Check if exists
            existing = self.supabase.table('food_candidates').select('id').eq(
                'source_url', product_data['source_url']
            ).execute()
            
            if existing.data:
                # Update existing
                result = self.supabase.table('food_candidates').update(
                    product_data
                ).eq('source_url', product_data['source_url']).execute()
            else:
                # Insert new
                product_data['first_seen_at'] = product_data['last_seen_at']
                result = self.supabase.table('food_candidates').insert(
                    product_data
                ).execute()
            
            return True
        except Exception as e:
            logger.error(f"Failed to upsert candidate: {e}")
            return False
    
    def scrape_url(self, url: str, delay_ms: int = None) -> bool:
        """Scrape a single product URL"""
        logger.info(f"Scraping: {url}")
        self.stats['scanned'] += 1
        
        # Apply rate limiting
        self._respect_rate_limit(delay_ms)
        
        # Fetch page
        html = self._fetch_page(url)
        if not html:
            logger.error(f"Failed to fetch: {url}")
            self.stats['errors'] += 1
            return False
        
        # Save to GCS
        gcs_path = self._save_to_gcs(html, url)
        
        # Parse product data
        product_data = self._parse_product(html, url)
        if not product_data:
            logger.warning(f"Failed to parse: {url}")
            return False
        
        # Check if product changed (using fingerprint)
        existing = None
        if self.supabase:
            try:
                existing = self.supabase.table('food_raw').select('fingerprint').eq(
                    'source_url', url
                ).execute()
            except:
                pass
        
        if existing and existing.data and existing.data[0].get('fingerprint') == product_data['fingerprint']:
            logger.info(f"Skipped (unchanged): {product_data['brand']} - {product_data['product_name']}")
            self.stats['skipped'] += 1
        else:
            # Save to database
            self._upsert_raw(url, gcs_path, product_data)
            self._upsert_candidate(product_data)
            
            if existing and existing.data:
                logger.info(f"Updated: {product_data['brand']} - {product_data['product_name']}")
                self.stats['updated'] += 1
            else:
                logger.info(f"New: {product_data['brand']} - {product_data['product_name']}")
                self.stats['new'] += 1
        
        return True
    
    def scrape_from_file(self, file_path: str, limit: int = None, delay_ms: int = None):
        """Scrape URLs from a file (one per line)"""
        with open(file_path) as f:
            urls = [line.strip() for line in f if line.strip()]
        
        if limit:
            urls = urls[:limit]
        
        logger.info(f"Starting scrape of {len(urls)} URLs")
        
        for i, url in enumerate(urls, 1):
            logger.info(f"Progress: {i}/{len(urls)}")
            self.scrape_url(url, delay_ms)
        
        self._print_harvest_report()
    
    def scrape_from_sitemap(self, limit: int = None, delay_ms: int = None):
        """Scrape products from sitemap"""
        sitemap_urls = self.profile['crawl_patterns']['sitemap_urls']
        base_url = self.profile['base_url']
        
        product_urls = []
        
        for sitemap_path in sitemap_urls:
            sitemap_url = urljoin(base_url, sitemap_path)
            logger.info(f"Fetching sitemap: {sitemap_url}")
            
            xml = self._fetch_page(sitemap_url)
            if not xml:
                continue
            
            soup = BeautifulSoup(xml, 'xml')
            for loc in soup.find_all('loc'):
                url = loc.get_text()
                # Check if it matches product pattern
                if '/product/' in url or '/item/' in url or '/p/' in url:
                    product_urls.append(url)
        
        if limit:
            product_urls = product_urls[:limit]
        
        logger.info(f"Found {len(product_urls)} product URLs in sitemap")
        
        for i, url in enumerate(product_urls, 1):
            logger.info(f"Progress: {i}/{len(product_urls)}")
            self.scrape_url(url, delay_ms)
        
        self._print_harvest_report()
    
    def _print_harvest_report(self):
        """Print harvest report with statistics"""
        logger.info("\n" + "="*50)
        logger.info("HARVEST REPORT")
        logger.info("="*50)
        logger.info(f"Pages scanned: {self.stats['scanned']}")
        logger.info(f"New items: {self.stats['new']}")
        logger.info(f"Updated items: {self.stats['updated']}")
        logger.info(f"Skipped (unchanged): {self.stats['skipped']}")
        logger.info(f"Errors: {self.stats['errors']}")
        logger.info("="*50)


def main():
    parser = argparse.ArgumentParser(description='PetFoodExpert scraper')
    parser.add_argument('--config', help='Path to config file')
    parser.add_argument('--seed-list', help='File with URLs to scrape (one per line)')
    parser.add_argument('--from-sitemap', action='store_true', help='Scrape from sitemap')
    parser.add_argument('--url', help='Scrape a single URL')
    parser.add_argument('--limit', type=int, help='Limit number of URLs to scrape')
    parser.add_argument('--delay-ms', type=int, default=1500, help='Delay between requests in milliseconds (default: 1500)')
    
    args = parser.parse_args()
    
    # Initialize scraper
    scraper = PetFoodExpertScraper(config_path=args.config)
    
    # Run appropriate scraping method
    if args.url:
        scraper.scrape_url(args.url, args.delay_ms)
        scraper._print_harvest_report()
    elif args.seed_list:
        scraper.scrape_from_file(args.seed_list, args.limit, args.delay_ms)
    elif args.from_sitemap:
        scraper.scrape_from_sitemap(args.limit, args.delay_ms)
    else:
        logger.error("Please specify --url, --seed-list, or --from-sitemap")
        sys.exit(1)


if __name__ == '__main__':
    main()