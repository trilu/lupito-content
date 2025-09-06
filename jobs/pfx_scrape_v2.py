#!/usr/bin/env python3
"""
PetFoodExpert scraper job v2 - API-first with HTML fallback
Fetches from JSON API when available, falls back to HTML for missing data
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
from etl.json_path import (
    resolve_path, resolve_multiple, extract_all, extract_values,
    safe_float, safe_bool
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


class PetFoodExpertScraperV2:
    def __init__(self, config_path: str = None, mode: str = None):
        """Initialize scraper with configuration"""
        self.config = self._load_config(config_path)
        self.profile = self._load_profile()
        self.mode = mode or self.profile.get('api', {}).get('mode', 'auto')
        self.session = self._setup_session()
        self.supabase = self._setup_supabase()
        self.gcs_client = self._setup_gcs()
        self.stats = {
            'scanned': 0,
            'new': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0,
            'api_hits': 0,
            'html_fallbacks': 0,
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
            'rate_limit': 0.5,
            'jitter': [0.5, 2.0],
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
            logger.warning(f"GCS client setup failed: {e}. Raw storage will be skipped.")
            return None
    
    def _respect_rate_limit(self, is_api: bool = False):
        """Apply rate limiting with jitter"""
        if is_api:
            # Use API rate limit from profile
            delay_ms = self.profile.get('api', {}).get('constraints', {}).get('rate_limit_ms', 800)
            time.sleep(delay_ms / 1000.0)
        else:
            # Use HTML rate limit
            delay_ms = self.profile['rate_limit'].get('default_delay_ms', 1500)
            jitter_ms = self.profile['rate_limit'].get('jitter_ms', 300)
            jitter = random.uniform(-jitter_ms, jitter_ms) / 1000.0
            time.sleep(max(0.1, (delay_ms / 1000.0) + jitter))
    
    def _extract_slug_from_url(self, url: str) -> Optional[str]:
        """Extract slug from product URL"""
        # Pattern: /product/slug, /food/slug or /api/products/slug
        match = re.search(r'/(?:product|food|api/products)/([^/]+)/?$', url)
        if match:
            return match.group(1)
        return None
    
    def _fetch_json_api(self, slug: str) -> Optional[Dict]:
        """Fetch product data from JSON API"""
        api_config = self.profile.get('api', {})
        if not api_config:
            return None
        
        # Build API URL
        detail_template = api_config['endpoints']['detail']
        api_url = detail_template.format(slug=slug)
        
        # Apply rate limiting
        self._respect_rate_limit(is_api=True)
        
        # Setup headers
        headers = self.session.headers.copy()
        headers.update(api_config.get('headers', {}))
        
        try:
            response = self.session.get(
                api_url,
                headers=headers,
                timeout=self.config['timeout']
            )
            response.raise_for_status()
            
            self.stats['api_hits'] += 1
            return response.json()
        except Exception as e:
            logger.warning(f"API fetch failed for slug {slug}: {e}")
            return None
    
    def _fetch_html(self, url: str) -> Optional[str]:
        """Fetch HTML page"""
        self._respect_rate_limit(is_api=False)
        
        for attempt in range(self.config['max_retries']):
            try:
                response = self.session.get(url, timeout=self.config['timeout'])
                response.raise_for_status()
                return response.text
            except Exception as e:
                logger.warning(f"HTML fetch failed (attempt {attempt + 1}): {url} - {e}")
                if attempt < self.config['max_retries'] - 1:
                    time.sleep(2 ** attempt)
        
        return None
    
    def _save_to_gcs(self, content: str, url: str, content_type: str = 'html') -> Optional[str]:
        """Save content to Google Cloud Storage"""
        if not self.gcs_client:
            return None
        
        try:
            date_str = datetime.utcnow().strftime('%Y-%m-%d')
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            
            # Different extensions for different content types
            extension = 'json' if content_type == 'json' else 'html'
            path = f"petfoodexpert/{date_str}/{url_hash}.{extension}"
            
            bucket = self.gcs_client.bucket(self.config['gcs_bucket'])
            blob = bucket.blob(path)
            
            # Set appropriate content type
            mime_type = 'application/json' if content_type == 'json' else 'text/html'
            blob.upload_from_string(content, content_type=mime_type)
            
            return f"gs://{self.config['gcs_bucket']}/{path}"
        except Exception as e:
            logger.error(f"GCS upload failed: {e}")
            return None
    
    def _parse_json_product(self, json_data: Dict, url: str) -> Optional[Dict]:
        """Parse product data from JSON API response"""
        api_mapping = self.profile['api']['mapping']
        
        # Extract basic fields using json_path resolver
        brand = resolve_path(json_data, api_mapping.get('brand_path'))
        product_name = resolve_path(json_data, api_mapping.get('name_path'))
        
        if not brand or not product_name:
            logger.warning(f"Missing required fields (brand/name) in JSON for {url}")
            return None
        
        # Extract other fields
        ingredients_raw = resolve_path(json_data, api_mapping.get('ingredients_path'))
        form_raw = resolve_path(json_data, api_mapping.get('form_path'))
        life_stage_raw = resolve_path(json_data, api_mapping.get('life_stage_path'))
        
        # Normalize form and life stage
        form = normalize_form(form_raw) or derive_form(product_name)
        life_stage = normalize_life_stage(life_stage_raw) or derive_life_stage(product_name)
        
        # Process ingredients
        ingredients_tokens = tokenize_ingredients(ingredients_raw) if ingredients_raw else []
        contains_chicken = check_contains_chicken(ingredients_tokens) or contains(ingredients_tokens, ['chicken', 'chicken fat', 'poultry'])
        
        # Extract pack sizes and prices
        variations = extract_all(json_data, api_mapping.get('packs_path', 'data.variations'))
        pack_sizes = []
        prices = []
        
        for variation in variations:
            weight_label = resolve_path(variation, 'weight_label')
            price = resolve_path(variation, 'variation_price')
            
            if weight_label:
                pack_sizes.append(weight_label)
            if price:
                prices.append(safe_float(price))
        
        # Get price and convert currency
        price_gbp = min(prices) if prices else None
        price_eur = None
        if price_gbp:
            rates = self.profile.get('currency_rates', {})
            normalized = normalize_currency(price_gbp, 'GBP', rates)
            price_eur = normalized['price_eur']
        
        # Extract nutrition (likely null from JSON)
        nutrition = {}
        for field in ['protein_pct', 'fat_pct', 'energy_kcal', 'fiber_pct', 'ash_pct', 'moisture_pct']:
            path = api_mapping.get(f"{field}_path")
            if path:
                value = resolve_path(json_data, path)
                if value is not None:
                    nutrition[field.replace('_pct', '_percent').replace('energy_kcal', 'kcal_per_100g')] = safe_float(value)
        
        # Check for grain-free and wheat-free flags
        grain_free = resolve_path(json_data, api_mapping.get('grain_free_path'))
        wheat_free = resolve_path(json_data, api_mapping.get('wheat_free_path'))
        
        # Generate fingerprint
        fingerprint = generate_fingerprint(brand, product_name, ingredients_raw)
        
        # Build product data
        product_data = {
            'source_domain': 'petfoodexpert.com',
            'source_url': url,
            'brand': brand,
            'product_name': product_name,
            'form': form,
            'life_stage': life_stage,
            'ingredients_raw': ingredients_raw,
            'ingredients_tokens': ingredients_tokens,
            'contains_chicken': contains_chicken,
            'pack_sizes': pack_sizes,
            'price_currency': 'GBP',
            'price_gbp': price_gbp,
            'price_eur': price_eur,
            'grain_free': grain_free == 'Y' if grain_free else None,
            'wheat_free': wheat_free == 'Y' if wheat_free else None,
            'fingerprint': fingerprint,
            'source_type': 'api',
            **nutrition
        }
        
        # Clean up None values
        return {k: v for k, v in product_data.items() if v is not None}
    
    def _extract_nutrition_from_html(self, html: str) -> Dict[str, Optional[float]]:
        """Extract nutrition data from HTML using robust parser"""
        # Use the new robust parser
        nutrition = parse_nutrition_from_html(html)
        
        # Add kcal_basis to stats if estimated
        if nutrition.get('kcal_basis') == 'estimated':
            self.stats['kcal_estimated'] = self.stats.get('kcal_estimated', 0) + 1
        
        return nutrition
    
    def scrape_url(self, url: str) -> bool:
        """Scrape a single product URL using API-first approach"""
        logger.info(f"Scraping: {url}")
        self.stats['scanned'] += 1
        
        # Extract slug for API
        slug = self._extract_slug_from_url(url)
        if not slug:
            logger.error(f"Could not extract slug from URL: {url}")
            self.stats['errors'] += 1
            return False
        
        product_data = None
        gcs_path = None
        raw_type = 'html'
        notes = []
        
        # Try API first if mode is 'api' or 'auto'
        if self.mode in ['api', 'auto']:
            json_data = self._fetch_json_api(slug)
            
            if json_data:
                # Save JSON to GCS
                gcs_path = self._save_to_gcs(
                    json.dumps(json_data, indent=2),
                    url,
                    content_type='json'
                )
                
                # Parse JSON data
                product_data = self._parse_json_product(json_data, url)
                raw_type = 'api'
                
                # Check if nutrition data is missing
                if product_data:
                    nutrition_fields = ['kcal_per_100g', 'protein_percent', 'fat_percent']
                    has_nutrition = any(product_data.get(field) for field in nutrition_fields)
                    
                    # If nutrition missing and mode is auto, try HTML fallback
                    if not has_nutrition and self.mode == 'auto':
                        logger.info(f"Nutrition missing from API, fetching HTML for: {url}")
                        html = self._fetch_html(url)
                        
                        if html:
                            self.stats['html_fallbacks'] += 1
                            nutrition = self._extract_nutrition_from_html(html)
                            
                            # Merge nutrition data
                            product_data.update(nutrition)
                            
                            # Check if we got macros
                            has_macros = bool(nutrition.get('protein_percent') or nutrition.get('fat_percent'))
                            if has_macros:
                                self.stats['products_with_macros'] = self.stats.get('products_with_macros', 0) + 1
                            
                            # Check if we got kcal
                            if nutrition.get('kcal_per_100g'):
                                self.stats['products_with_kcal'] = self.stats.get('products_with_kcal', 0) + 1
                            
                            # Check again if we got nutrition
                            has_nutrition = any(nutrition.get(field.replace('_percent', '_percent').replace('kcal_per_100g', 'kcal_per_100g')) 
                                              for field in nutrition_fields)
                            
                            if not has_nutrition:
                                notes.append('nutrition_missing')
                                self.stats['nutrition_missing'] += 1
                    elif not has_nutrition:
                        notes.append('nutrition_missing')
                        self.stats['nutrition_missing'] += 1
        
        # Fallback to HTML if API failed or mode is 'html'
        if not product_data and self.mode in ['html', 'auto']:
            html = self._fetch_html(url)
            
            if html:
                # Save HTML to GCS
                gcs_path = self._save_to_gcs(html, url, content_type='html')
                
                # Parse HTML (reuse existing method from original scraper)
                product_data = self._parse_html_product(html, url)
                raw_type = 'html'
                self.stats['html_fallbacks'] += 1
        
        if not product_data:
            logger.error(f"Failed to parse product data: {url}")
            self.stats['errors'] += 1
            return False
        
        # Add notes to product data
        if notes:
            product_data['notes'] = notes
        
        # Check fingerprint for changes
        existing = None
        if self.supabase:
            try:
                existing = self.supabase.table('food_raw').select('fingerprint, parsed_json').eq(
                    'source_url', url
                ).execute()
            except:
                pass
        
        # Check if nutrition data is new
        has_new_nutrition = False
        if existing and existing.data:
            # Check if we have nutrition that wasn't there before
            existing_parsed = existing.data[0].get('parsed_json', {}) if existing.data else {}
            for field in ['protein_percent', 'fat_percent', 'kcal_per_100g']:
                if product_data.get(field) and not existing_parsed.get(field):
                    has_new_nutrition = True
                    break
        
        if existing and existing.data and existing.data[0].get('fingerprint') == product_data['fingerprint'] and not has_new_nutrition:
            logger.info(f"Skipped (unchanged): {product_data['brand']} - {product_data['product_name']} [source: {raw_type}]")
            self.stats['skipped'] += 1
        else:
            # Save to database
            self._upsert_raw(url, gcs_path, product_data, raw_type)
            self._upsert_candidate(product_data)
            
            if existing and existing.data:
                logger.info(f"Updated: {product_data['brand']} - {product_data['product_name']} [source: {raw_type}]")
                self.stats['updated'] += 1
            else:
                logger.info(f"New: {product_data['brand']} - {product_data['product_name']} [source: {raw_type}]")
                self.stats['new'] += 1
        
        return True
    
    def _parse_html_product(self, html: str, url: str) -> Optional[Dict]:
        """Parse product from HTML (fallback method)"""
        soup = BeautifulSoup(html, 'html.parser')
        selectors = self.profile['selectors']
        
        # This is simplified - in reality would use the full HTML parsing logic
        brand = self._extract_field(soup, selectors.get('brand', {}))
        product_name = self._extract_field(soup, selectors.get('product_name', {}))
        
        if not brand or not product_name:
            return None
        
        # Extract all fields using existing logic
        ingredients_raw = self._extract_field(soup, selectors.get('ingredients', {}))
        
        # Get nutrition
        nutrition = self._extract_nutrition_from_html(html)
        
        # Process ingredients
        ingredients_tokens = tokenize_ingredients(ingredients_raw) if ingredients_raw else []
        contains_chicken = check_contains_chicken(ingredients_tokens)
        
        fingerprint = generate_fingerprint(brand, product_name, ingredients_raw)
        
        return {
            'source_domain': 'petfoodexpert.com',
            'source_url': url,
            'brand': brand,
            'product_name': product_name,
            'ingredients_raw': ingredients_raw,
            'ingredients_tokens': ingredients_tokens,
            'contains_chicken': contains_chicken,
            'fingerprint': fingerprint,
            'source_type': 'html',
            **nutrition
        }
    
    def _extract_field(self, soup: BeautifulSoup, selectors: Dict) -> Optional[str]:
        """Extract field using CSS selectors"""
        if 'css' in selectors:
            for selector in selectors['css']:
                element = soup.select_one(selector)
                if element:
                    return clean_text(element.get_text())
        return None
    
    def _upsert_raw(self, url: str, gcs_path: str, parsed_json: Dict, raw_type: str = 'html') -> bool:
        """Upsert to food_raw table with raw_type"""
        if not self.supabase:
            return False
        
        try:
            data = {
                'source_domain': 'petfoodexpert.com',
                'source_url': url,
                'html_gcs_path': gcs_path,
                'parsed_json': parsed_json,
                'fingerprint': parsed_json.get('fingerprint'),
                'last_seen_at': datetime.utcnow().isoformat(),
                'raw_type': raw_type  # New field
            }
            
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
            # Remove internal fields
            candidate_data = product_data.copy()
            candidate_data.pop('source_type', None)
            candidate_data.pop('notes', None)
            candidate_data.pop('grain_free', None)
            candidate_data.pop('wheat_free', None)
            candidate_data.pop('price_gbp', None)
            # Keep kcal_basis now that column exists in schema
            
            # Add timestamp
            candidate_data['last_seen_at'] = datetime.utcnow().isoformat()
            
            # Check if exists and what nutrition data it has
            existing = self.supabase.table('food_candidates').select(
                'id, protein_percent, fat_percent, kcal_per_100g'
            ).eq(
                'source_url', candidate_data['source_url']
            ).execute()
            
            if existing.data:
                # Always update if we have new nutrition data
                existing_row = existing.data[0]
                has_new_nutrition = False
                for field in ['protein_percent', 'fat_percent', 'kcal_per_100g']:
                    if candidate_data.get(field) and not existing_row.get(field):
                        has_new_nutrition = True
                        logger.info(f"  → New {field}: {candidate_data.get(field)}")
                
                result = self.supabase.table('food_candidates').update(
                    candidate_data
                ).eq('source_url', candidate_data['source_url']).execute()
            else:
                candidate_data['first_seen_at'] = candidate_data['last_seen_at']
                result = self.supabase.table('food_candidates').insert(
                    candidate_data
                ).execute()
            
            return True
        except Exception as e:
            logger.error(f"Failed to upsert candidate: {e}")
            return False
    
    def scrape_from_file(self, file_path: str, limit: int = None):
        """Scrape URLs from file"""
        with open(file_path) as f:
            urls = [line.strip() for line in f if line.strip()]
        
        # Apply limit
        max_items = min(
            limit or float('inf'),
            self.profile.get('api', {}).get('constraints', {}).get('max_per_run', 100)
        )
        urls = urls[:max_items]
        
        logger.info(f"Starting scrape of {len(urls)} URLs (mode: {self.mode})")
        
        for i, url in enumerate(urls, 1):
            logger.info(f"Progress: {i}/{len(urls)}")
            self.scrape_url(url)
        
        self._print_harvest_report()
    
    def scrape_from_sitemap(self, limit: int = None):
        """Scrape from sitemap"""
        # Simplified - would implement full sitemap logic
        logger.warning("Sitemap scraping not fully implemented in v2")
        self._print_harvest_report()
    
    def _print_harvest_report(self):
        """Print detailed harvest report"""
        logger.info("\n" + "="*60)
        logger.info("HARVEST REPORT")
        logger.info("="*60)
        logger.info(f"Pages scanned: {self.stats['scanned']}")
        logger.info(f"New items: {self.stats['new']}")
        logger.info(f"Updated items: {self.stats['updated']}")
        logger.info(f"Skipped (unchanged): {self.stats['skipped']}")
        logger.info(f"Errors: {self.stats['errors']}")
        logger.info("-"*60)
        logger.info(f"API hits: {self.stats['api_hits']}")
        logger.info(f"HTML fallbacks: {self.stats['html_fallbacks']}")
        logger.info(f"Products with macros: {self.stats.get('products_with_macros', 0)}")
        logger.info(f"Products with kcal: {self.stats.get('products_with_kcal', 0)}")
        logger.info(f"Kcal estimated: {self.stats.get('kcal_estimated', 0)}")
        logger.info(f"Nutrition missing: {self.stats['nutrition_missing']}")
        logger.info("="*60)
        
        # Show sample data if available
        if self.supabase and self.stats['scanned'] > 0:
            self._print_sample_data()
    
    def _print_sample_data(self):
        """Print 5-row sample of scraped data"""
        try:
            # Fetch recent items
            response = self.supabase.table('food_candidates').select(
                'brand, product_name, kcal_per_100g, protein_percent, '
                'fat_percent, contains_chicken'
            ).order('last_seen_at', desc=True).limit(5).execute()
            
            if response.data:
                logger.info("\nSAMPLE DATA (last 5 items):")
                logger.info("-"*60)
                logger.info(f"{'Brand':<15} {'Product':<25} {'kcal':<6} {'Prot%':<6} {'Fat%':<6} {'Chkn':<5}")
                logger.info("-"*60)
                
                for row in response.data:
                    brand = (row.get('brand') or '')[:15]
                    name = (row.get('product_name') or '')[:25]
                    kcal = str(row.get('kcal_per_100g') or 'null')[:6]
                    protein = str(row.get('protein_percent') or 'null')[:6]
                    fat = str(row.get('fat_percent') or 'null')[:6]
                    chicken = 'Yes' if row.get('contains_chicken') else 'No'
                    
                    logger.info(f"{brand:<15} {name:<25} {kcal:<6} {protein:<6} {fat:<6} {chicken:<5}")
        except Exception as e:
            logger.error(f"Could not fetch sample data: {e}")


def main():
    parser = argparse.ArgumentParser(description='PetFoodExpert scraper v2 - API-first')
    parser.add_argument('--config', help='Path to config file')
    parser.add_argument('--mode', choices=['api', 'html', 'auto'], 
                       help='Scraping mode (default: auto from profile)')
    parser.add_argument('--seed-list', help='File with URLs to scrape')
    parser.add_argument('--from-sitemap', action='store_true', help='Scrape from sitemap')
    parser.add_argument('--url', help='Scrape a single URL')
    parser.add_argument('--limit', type=int, help='Limit number of URLs (max 100 from profile)')
    
    args = parser.parse_args()
    
    # Initialize scraper
    scraper = PetFoodExpertScraperV2(
        config_path=args.config,
        mode=args.mode
    )
    
    # Run appropriate scraping method
    if args.url:
        scraper.scrape_url(args.url)
        scraper._print_harvest_report()
    elif args.seed_list:
        scraper.scrape_from_file(args.seed_list, args.limit)
    elif args.from_sitemap:
        scraper.scrape_from_sitemap(args.limit)
    else:
        logger.error("Please specify --url, --seed-list, or --from-sitemap")
        sys.exit(1)


if __name__ == '__main__':
    main()