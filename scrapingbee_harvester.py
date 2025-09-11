#!/usr/bin/env python3
"""
ScrapingBee Harvester for Blocked Sites
Handles brands that require JavaScript rendering or have anti-bot measures
"""

import os
import re
import json
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from google.cloud import storage
from dotenv import load_dotenv
import yaml

# Setup
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# GCS setup
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = './secrets/gcp-sa.json'
storage_client = storage.Client()
bucket = storage_client.bucket('lupito-content-raw-eu')

class ScrapingBeeHarvester:
    """Harvester using ScrapingBee for blocked sites"""
    
    def __init__(self, brand: str, profile_path: Path):
        self.brand = brand
        self.profile = self._load_profile(profile_path)
        self.base_url = self.profile.get('website_url', '')
        self.api_key = os.getenv('SCRAPING_BEE')
        
        if not self.api_key:
            raise ValueError("SCRAPING_BEE API key not found in environment")
        
        self.discovered_urls = set()
        self.product_urls = []
        
        # Statistics
        self.stats = {
            'pages_fetched': 0,
            'products_found': 0,
            'snapshots_created': 0,
            'errors': [],
            'api_credits_used': 0
        }
    
    def _load_profile(self, profile_path: Path) -> Dict:
        """Load brand profile"""
        with open(profile_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _get_country_code(self) -> str:
        """Get country code for ScrapingBee based on brand"""
        country_map = {
            'briantos': 'de',  # German brand
            'belcando': 'de',  # German brand
            'bozita': 'se',   # Swedish brand
            'cotswold': 'gb'  # UK brand
        }
        return country_map.get(self.brand, 'de')
    
    def fetch_with_scrapingbee(self, url: str) -> Optional[str]:
        """Fetch page using ScrapingBee API"""
        # Create clean params for each request
        params = {
            'api_key': self.api_key,
            'url': url,
            'render_js': 'true',  # Enable JavaScript rendering
            'premium_proxy': 'true',  # Use premium proxies
            'country_code': self._get_country_code(),  # Set country
            'wait': '2000',  # Wait 2 seconds for JS
            'block_ads': 'true',  # Block ads
        }
        
        try:
            logger.info(f"Fetching {url} with ScrapingBee...")
            # Don't use forward_headers, just make simple request
            response = requests.get(
                'https://app.scrapingbee.com/api/v1/',
                params=params,
                timeout=45
            )
            
            self.stats['api_credits_used'] += 1
            
            if response.status_code == 200:
                self.stats['pages_fetched'] += 1
                logger.info(f"  ✓ Success ({len(response.content)/1024:.1f} KB)")
                return response.text
            else:
                logger.warning(f"  ✗ HTTP {response.status_code}: {response.text[:100]}")
                self.stats['errors'].append(f"HTTP {response.status_code}: {url}")
                return None
                
        except Exception as e:
            logger.error(f"  ✗ Error: {e}")
            self.stats['errors'].append(f"Exception: {str(e)[:50]}")
            return None
    
    def discover_product_urls(self) -> List[str]:
        """Discover product URLs from the website"""
        logger.info(f"Discovering products for {self.brand}")
        
        # Start with category pages
        category_urls = self._get_category_urls()
        
        for category_url in category_urls[:3]:  # Limit to save API credits
            html = self.fetch_with_scrapingbee(category_url)
            if html:
                self._extract_product_links(html, category_url)
            time.sleep(2)  # Be nice to ScrapingBee
        
        # If not enough products, try pagination
        if len(self.product_urls) < 20:
            self._discover_with_pagination()
        
        # Deduplicate and limit
        unique_products = list(set(self.product_urls))[:30]
        self.stats['products_found'] = len(unique_products)
        
        logger.info(f"Found {len(unique_products)} product URLs")
        return unique_products
    
    def _get_category_urls(self) -> List[str]:
        """Get category URLs to check"""
        # Use profile-specific URLs if available
        if 'category_urls' in self.profile:
            return self.profile['category_urls']
        
        # Default patterns for German/EU pet food sites
        patterns = [
            '/produkte/',
            '/products/',
            '/shop/',
            '/hundefutter/',
            '/dog-food/',
            '/sortiment/',
            '/artikel/',
            '/hundenahrung/'
        ]
        
        category_urls = []
        for pattern in patterns:
            category_urls.append(urljoin(self.base_url, pattern))
        
        return category_urls
    
    def _extract_product_links(self, html: str, base_url: str):
        """Extract product links from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Common product link selectors
        selectors = [
            'a.product-link',
            'a.product-title',
            'h2.product-name a',
            'h3.product-title a',
            'div.product-item a',
            'article.product a',
            '.product-grid a',
            '.product-list-item a',
            'a[href*="/produkt"]',
            'a[href*="/product"]',
            'a[href*="/artikel"]',
            'a[class*="product"]'
        ]
        
        for selector in selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href:
                    full_url = urljoin(base_url, href)
                    if self._is_product_url(full_url):
                        self.product_urls.append(full_url)
                        logger.debug(f"  Found product: {full_url}")
    
    def _is_product_url(self, url: str) -> bool:
        """Check if URL is likely a product page"""
        if not url or url in self.discovered_urls:
            return False
        
        # Must be from same domain
        parsed = urlparse(url)
        base_parsed = urlparse(self.base_url)
        if parsed.netloc != base_parsed.netloc:
            return False
        
        # Exclude non-product pages
        exclude_patterns = [
            '/category/', '/kategorien/', '/collections/',
            '/pages/', '/seiten/', '/blogs/', '/cart', '/warenkorb',
            '/account', '/konto/', '/login', '/register',
            '/about', '/uber-uns/', '/kontakt', '/contact',
            '/agb/', '/datenschutz/', '/impressum/',
            '.pdf', '.jpg', '.png'
        ]
        
        url_lower = url.lower()
        for pattern in exclude_patterns:
            if pattern in url_lower:
                return False
        
        # Include product patterns (German and English)
        include_patterns = [
            '/produkt/', '/product/', '/artikel/',
            '/item/', '/p/', 
            'hundefutter', 'trockenfutter', 'nassfutter',
            'dog-food', 'dry-food', 'wet-food'
        ]
        
        for pattern in include_patterns:
            if pattern in url_lower:
                self.discovered_urls.add(url)
                return True
        
        # Check for product-like URL structure
        path = parsed.path.rstrip('/')
        if path and '/' in path:
            parts = path.split('/')
            last_part = parts[-1]
            # Product URLs often have slugs with hyphens
            if len(last_part) > 10 and '-' in last_part:
                self.discovered_urls.add(url)
                return True
        
        return False
    
    def _discover_with_pagination(self):
        """Try to discover more products through pagination"""
        logger.info("Attempting pagination discovery...")
        
        base_category = urljoin(self.base_url, '/produkte/')
        
        for page in range(2, 5):  # Check pages 2-4
            # Try different pagination patterns
            pagination_urls = [
                f"{base_category}?page={page}",
                f"{base_category}?seite={page}",
                f"{base_category}page/{page}/",
                f"{base_category}seite/{page}/"
            ]
            
            for url in pagination_urls:
                if len(self.product_urls) >= 20:
                    return
                
                html = self.fetch_with_scrapingbee(url)
                if html:
                    before_count = len(self.product_urls)
                    self._extract_product_links(html, url)
                    after_count = len(self.product_urls)
                    
                    if after_count > before_count:
                        logger.info(f"  Found {after_count - before_count} products on page {page}")
                        break
                
                time.sleep(2)
    
    def harvest_products(self, product_urls: List[str]) -> Dict:
        """Harvest product pages to GCS"""
        logger.info(f"Harvesting {len(product_urls)} products for {self.brand}")
        
        date_str = datetime.now().strftime('%Y-%m-%d')
        harvest_stats = {
            'snapshots_created': 0,
            'snapshots_failed': 0,
            'total_size_mb': 0
        }
        
        for i, url in enumerate(product_urls, 1):
            logger.info(f"[{i}/{len(product_urls)}] Fetching {url}")
            
            html = self.fetch_with_scrapingbee(url)
            
            if html:
                # Generate filename
                parsed = urlparse(url)
                path_parts = parsed.path.strip('/').split('/')
                filename = '_'.join(path_parts[-2:]) if len(path_parts) > 1 else path_parts[-1] if path_parts else 'product'
                filename = re.sub(r'[^a-z0-9_-]', '_', filename.lower())
                filename = f"{filename}.html"
                
                # Upload to GCS
                blob_path = f"manufacturers/{self.brand}/{date_str}/{filename}"
                blob = bucket.blob(blob_path)
                
                # Set metadata
                blob.metadata = {
                    'url': url,
                    'brand': self.brand,
                    'fetched_at': datetime.now().isoformat(),
                    'fetched_with': 'scrapingbee',
                    'content_type': 'product_page'
                }
                
                # Upload content
                blob.upload_from_string(html, content_type='text/html')
                
                size_mb = len(html.encode()) / (1024 * 1024)
                harvest_stats['snapshots_created'] += 1
                harvest_stats['total_size_mb'] += size_mb
                self.stats['snapshots_created'] += 1
                
                logger.info(f"  ✓ Uploaded {filename} ({size_mb:.2f} MB)")
            else:
                harvest_stats['snapshots_failed'] += 1
                logger.warning(f"  ✗ Failed to fetch")
            
            # Rate limiting for API
            time.sleep(3)
        
        return harvest_stats


def main():
    """Process blocked brands with ScrapingBee"""
    
    brands = ['briantos', 'belcando', 'bozita', 'cotswold']
    all_stats = {}
    
    print("="*80)
    print("SCRAPINGBEE HARVESTER FOR BLOCKED SITES")
    print("="*80)
    print(f"Brands: {', '.join(brands)}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("="*80)
    
    for brand in brands:
        print(f"\n{'='*40}")
        print(f"Processing {brand.upper()}")
        print(f"{'='*40}")
        
        profile_path = Path(f'profiles/manufacturers/{brand}.yaml')
        
        # Create profile if it doesn't exist
        if not profile_path.exists():
            logger.info(f"Creating profile for {brand}")
            profile_data = get_brand_profile(brand)
            profile_path.parent.mkdir(parents=True, exist_ok=True)
            with open(profile_path, 'w') as f:
                yaml.dump(profile_data, f)
        
        try:
            # Initialize harvester
            harvester = ScrapingBeeHarvester(brand, profile_path)
            
            # Discover product URLs
            product_urls = harvester.discover_product_urls()
            
            # Harvest products
            harvest_stats = harvester.harvest_products(product_urls)
            
            # Store results
            all_stats[brand] = {
                'harvester': harvester.stats,
                'harvest': harvest_stats,
                'sample_urls': product_urls[:5]
            }
            
            print(f"\n✓ Completed {brand}:")
            print(f"  - API credits used: {harvester.stats['api_credits_used']}")
            print(f"  - Products found: {harvester.stats['products_found']}")
            print(f"  - Snapshots created: {harvest_stats['snapshots_created']}")
            
        except Exception as e:
            logger.error(f"Failed to process {brand}: {e}")
            all_stats[brand] = {'error': str(e)}
    
    # Generate report
    generate_blocked_sites_report(all_stats)
    
    print("\n" + "="*80)
    print("HARVEST COMPLETE")
    print("="*80)
    print("Report saved to: BLOCKED_SITES_REPORT.md")
    
    return all_stats


def get_brand_profile(brand: str) -> Dict:
    """Get brand profile data"""
    profiles = {
        'briantos': {
            'brand': 'Briantos',
            'brand_slug': 'briantos',
            'website_url': 'https://www.briantos.de',
            'country': 'DE',
            'language': 'de',
            'platform': 'Custom',
            'category_urls': [
                'https://www.briantos.de/hunde/hundefutter/',
                'https://www.briantos.de/hunde/trockenfutter/',
                'https://www.briantos.de/produkte/'
            ]
        },
        'belcando': {
            'brand': 'Belcando',
            'brand_slug': 'belcando',
            'website_url': 'https://www.belcando.de',
            'country': 'DE',
            'language': 'de',
            'platform': 'Custom',
            'category_urls': [
                'https://www.belcando.de/hund/trockenfutter/',
                'https://www.belcando.de/hund/nassfutter/',
                'https://www.belcando.de/produkte/'
            ]
        },
        'bozita': {
            'brand': 'Bozita',
            'brand_slug': 'bozita',
            'website_url': 'https://www.bozita.com',
            'country': 'SE',
            'language': 'en',
            'platform': 'Custom',
            'category_urls': [
                'https://www.bozita.com/products/dog/',
                'https://www.bozita.com/en/products/',
                'https://www.bozita.com/dog-food/'
            ]
        },
        'cotswold': {
            'brand': 'Cotswold RAW',
            'brand_slug': 'cotswold',
            'website_url': 'https://www.cotswoldraw.com',
            'country': 'GB',
            'language': 'en',
            'platform': 'Shopify',
            'category_urls': [
                'https://www.cotswoldraw.com/collections/dog-food',
                'https://www.cotswoldraw.com/collections/all',
                'https://www.cotswoldraw.com/products/'
            ]
        }
    }
    
    return profiles.get(brand, {
        'brand': brand.title(),
        'brand_slug': brand,
        'website_url': f'https://www.{brand}.com',
        'country': 'DE',
        'language': 'en'
    })


def generate_blocked_sites_report(stats: Dict):
    """Generate report for blocked sites harvest"""
    
    with open('BLOCKED_SITES_REPORT.md', 'w') as f:
        f.write("# Blocked Sites Harvest Report\n\n")
        f.write(f"**Generated:** {datetime.now().isoformat()}\n")
        f.write(f"**Method:** ScrapingBee with JS rendering\n")
        f.write(f"**Brands:** briantos, belcando, bozita, cotswold\n\n")
        
        f.write("## Summary\n\n")
        
        total_credits = sum(s['harvester']['api_credits_used'] for s in stats.values() if 'harvester' in s)
        total_products = sum(s['harvester']['products_found'] for s in stats.values() if 'harvester' in s)
        total_snapshots = sum(s['harvest']['snapshots_created'] for s in stats.values() if 'harvest' in s)
        
        f.write(f"- **API credits used:** {total_credits}\n")
        f.write(f"- **Total products found:** {total_products}\n")
        f.write(f"- **Total snapshots created:** {total_snapshots}\n\n")
        
        # Success rate
        successful_brands = sum(1 for s in stats.values() if 'harvest' in s and s['harvest']['snapshots_created'] >= 20)
        f.write(f"- **Success rate:** {successful_brands}/4 brands with ≥20 products\n\n")
        
        for brand, brand_stats in stats.items():
            f.write(f"## {brand.upper()}\n\n")
            
            if 'error' in brand_stats:
                f.write(f"**Status:** ❌ Failed\n")
                f.write(f"**Error:** {brand_stats['error']}\n\n")
                continue
            
            harvester = brand_stats['harvester']
            harvest = brand_stats['harvest']
            
            # Determine status
            if harvest['snapshots_created'] >= 20:
                status = "✅ Success"
            elif harvest['snapshots_created'] >= 10:
                status = "⚠️ Partial"
            else:
                status = "❌ Blocked"
            
            f.write(f"**Status:** {status}\n\n")
            
            f.write("### Harvest Statistics\n")
            f.write(f"- Pages fetched: {harvester['pages_fetched']}\n")
            f.write(f"- Products found: {harvester['products_found']}\n")
            f.write(f"- Snapshots created: {harvest['snapshots_created']}\n")
            f.write(f"- Snapshots failed: {harvest['snapshots_failed']}\n")
            f.write(f"- Total size: {harvest['total_size_mb']:.1f} MB\n")
            f.write(f"- API credits used: {harvester['api_credits_used']}\n")
            
            if harvester.get('errors'):
                f.write("\n### Errors\n")
                for error in harvester['errors'][:5]:
                    f.write(f"- {error}\n")
            
            if brand_stats.get('sample_urls'):
                f.write("\n### Sample URLs\n")
                for url in brand_stats['sample_urls']:
                    f.write(f"- {url}\n")
            
            f.write("\n")
        
        f.write("## Remaining Blocks\n\n")
        blocked = [b for b, s in stats.items() if 'harvest' not in s or s['harvest']['snapshots_created'] < 20]
        if blocked:
            for brand in blocked:
                f.write(f"- **{brand}**: ")
                if 'error' in stats[brand]:
                    f.write(f"Error - {stats[brand]['error'][:50]}\n")
                elif 'harvest' in stats[brand]:
                    f.write(f"Only {stats[brand]['harvest']['snapshots_created']} products captured\n")
                else:
                    f.write("Unknown issue\n")
        else:
            f.write("None - all brands successfully harvested!\n")
        
        f.write("\n## Proposed Next Steps\n\n")
        f.write("1. Parse the captured snapshots for ingredients and macros\n")
        f.write("2. For remaining blocked sites:\n")
        f.write("   - Try different ScrapingBee settings (longer wait, different country)\n")
        f.write("   - Consider using Playwright/Selenium for local browser automation\n")
        f.write("   - Manual inspection to understand blocking mechanism\n")
        f.write("3. Update foods_canonical with extracted data\n")
        f.write("4. Verify data quality and coverage improvements\n")


if __name__ == "__main__":
    main()