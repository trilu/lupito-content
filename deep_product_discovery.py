#!/usr/bin/env python3
"""
Deep Product Discovery for Brit, Alpha, and Forthglade
Implements multi-strategy discovery to find product URLs
"""

import os
import re
import json
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set, Optional
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

class DeepProductDiscovery:
    """Multi-strategy product URL discovery"""
    
    def __init__(self, brand: str, profile_path: Path):
        self.brand = brand
        self.profile = self._load_profile(profile_path)
        self.base_url = self.profile.get('website_url', self.profile.get('base_url', ''))
        self.discovered_urls = set()
        self.product_urls = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        
        # Statistics
        self.stats = {
            'pages_scanned': 0,
            'product_urls_found': 0,
            'discovery_methods': {},
            'errors': []
        }
    
    def _load_profile(self, profile_path: Path) -> Dict:
        """Load brand profile"""
        with open(profile_path, 'r') as f:
            return yaml.safe_load(f)
    
    def discover_products(self, max_products: int = 30) -> List[str]:
        """Main discovery method using multiple strategies"""
        logger.info(f"Starting deep discovery for {self.brand}")
        
        # Strategy 1: Parse category pages for product links
        self._discover_from_categories()
        
        # Strategy 2: Follow pagination
        self._discover_from_pagination()
        
        # Strategy 3: Parse JSON-LD structured data
        self._discover_from_structured_data()
        
        # Strategy 4: Sitemap parsing
        self._discover_from_sitemap()
        
        # Strategy 5: Search/filter pages
        self._discover_from_search()
        
        # Deduplicate and limit
        unique_products = list(set(self.product_urls))[:max_products]
        
        self.stats['product_urls_found'] = len(unique_products)
        logger.info(f"Discovered {len(unique_products)} product URLs for {self.brand}")
        
        return unique_products
    
    def _discover_from_categories(self):
        """Extract product URLs from category pages"""
        logger.info(f"Strategy 1: Discovering from category pages")
        
        category_urls = self.profile.get('category_urls', [])
        if not category_urls:
            # Try common patterns
            category_urls = [
                urljoin(self.base_url, '/products/'),
                urljoin(self.base_url, '/shop/'),
                urljoin(self.base_url, '/dog-food/'),
                urljoin(self.base_url, '/dog/'),
                urljoin(self.base_url, '/products/dog/'),
                urljoin(self.base_url, '/shop/dog/')
            ]
        
        for category_url in category_urls:
            try:
                response = self.session.get(category_url, timeout=10)
                if response.status_code == 200:
                    self.stats['pages_scanned'] += 1
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Common product link patterns
                    selectors = [
                        'a.product-link',
                        'a.product-title',
                        'a.product-item',
                        'div.product a',
                        'article.product a',
                        'li.product a',
                        '.product-grid a',
                        '.product-list a',
                        'a[href*="/product"]',
                        'a[href*="/products/"]',
                        'a[href*="/shop/"]'
                    ]
                    
                    for selector in selectors:
                        links = soup.select(selector)
                        for link in links:
                            href = link.get('href')
                            if href:
                                full_url = urljoin(category_url, href)
                                if self._is_product_url(full_url):
                                    self.product_urls.append(full_url)
                                    self.stats['discovery_methods']['category'] = \
                                        self.stats['discovery_methods'].get('category', 0) + 1
                    
                    logger.info(f"Found {len(self.product_urls)} products from {category_url}")
                    
            except Exception as e:
                logger.warning(f"Error fetching {category_url}: {e}")
                self.stats['errors'].append(f"Category fetch: {str(e)[:50]}")
            
            time.sleep(2)  # Rate limiting
    
    def _discover_from_pagination(self):
        """Follow pagination links to discover more products"""
        logger.info(f"Strategy 2: Following pagination")
        
        # Look for pagination in category pages
        category_urls = self.profile.get('category_urls', [
            urljoin(self.base_url, '/products/'),
            urljoin(self.base_url, '/shop/')
        ])
        
        for base_category in category_urls[:2]:  # Limit to avoid too many requests
            try:
                page = 1
                max_pages = 5  # Limit pagination depth
                
                while page <= max_pages:
                    # Try different pagination patterns
                    paginated_urls = [
                        f"{base_category}?page={page}",
                        f"{base_category}page/{page}/",
                        f"{base_category}?p={page}",
                        urljoin(base_category, f"?limit=50&page={page}")
                    ]
                    
                    for url in paginated_urls:
                        try:
                            response = self.session.get(url, timeout=10)
                            if response.status_code == 200:
                                self.stats['pages_scanned'] += 1
                                soup = BeautifulSoup(response.text, 'html.parser')
                                
                                # Extract product links
                                links = soup.find_all('a', href=True)
                                new_products = 0
                                
                                for link in links:
                                    href = link['href']
                                    full_url = urljoin(url, href)
                                    if self._is_product_url(full_url) and full_url not in self.product_urls:
                                        self.product_urls.append(full_url)
                                        new_products += 1
                                        self.stats['discovery_methods']['pagination'] = \
                                            self.stats['discovery_methods'].get('pagination', 0) + 1
                                
                                if new_products > 0:
                                    logger.info(f"Found {new_products} new products from page {page}")
                                    break  # Found products, move to next page
                                
                        except:
                            pass
                        
                        time.sleep(1)
                    
                    page += 1
                    
            except Exception as e:
                logger.warning(f"Pagination error: {e}")
                self.stats['errors'].append(f"Pagination: {str(e)[:50]}")
    
    def _discover_from_structured_data(self):
        """Extract product URLs from JSON-LD structured data"""
        logger.info(f"Strategy 3: Parsing structured data")
        
        # Check main pages for structured data
        pages_to_check = [
            self.base_url,
            urljoin(self.base_url, '/products/'),
            urljoin(self.base_url, '/shop/')
        ]
        
        for page_url in pages_to_check:
            try:
                response = self.session.get(page_url, timeout=10)
                if response.status_code == 200:
                    self.stats['pages_scanned'] += 1
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Find JSON-LD scripts
                    scripts = soup.find_all('script', type='application/ld+json')
                    
                    for script in scripts:
                        try:
                            data = json.loads(script.string)
                            
                            # Handle different JSON-LD structures
                            if isinstance(data, dict):
                                self._extract_products_from_jsonld(data)
                            elif isinstance(data, list):
                                for item in data:
                                    self._extract_products_from_jsonld(item)
                                    
                        except json.JSONDecodeError:
                            pass
                        
            except Exception as e:
                logger.warning(f"Structured data error: {e}")
                self.stats['errors'].append(f"JSON-LD: {str(e)[:50]}")
            
            time.sleep(1)
    
    def _extract_products_from_jsonld(self, data: Dict):
        """Extract product URLs from JSON-LD data"""
        if isinstance(data, dict):
            # Check if it's a Product
            if data.get('@type') == 'Product' and data.get('url'):
                url = data['url']
                if self._is_product_url(url):
                    self.product_urls.append(url)
                    self.stats['discovery_methods']['jsonld'] = \
                        self.stats['discovery_methods'].get('jsonld', 0) + 1
            
            # Check for ItemList
            elif data.get('@type') == 'ItemList' and data.get('itemListElement'):
                for item in data['itemListElement']:
                    if item.get('url'):
                        url = item['url']
                        if self._is_product_url(url):
                            self.product_urls.append(url)
                            self.stats['discovery_methods']['jsonld'] = \
                                self.stats['discovery_methods'].get('jsonld', 0) + 1
            
            # Recurse into nested structures
            for value in data.values():
                if isinstance(value, (dict, list)):
                    self._extract_products_from_jsonld(value)
    
    def _discover_from_sitemap(self):
        """Parse sitemap for product URLs"""
        logger.info(f"Strategy 4: Parsing sitemap")
        
        sitemap_urls = [
            urljoin(self.base_url, '/sitemap.xml'),
            urljoin(self.base_url, '/sitemap_index.xml'),
            urljoin(self.base_url, '/product-sitemap.xml'),
            urljoin(self.base_url, '/sitemap-products.xml')
        ]
        
        for sitemap_url in sitemap_urls:
            try:
                response = self.session.get(sitemap_url, timeout=10)
                if response.status_code == 200:
                    self.stats['pages_scanned'] += 1
                    
                    # Parse sitemap
                    soup = BeautifulSoup(response.content, 'xml')
                    urls = soup.find_all('url')
                    
                    for url in urls:
                        loc = url.find('loc')
                        if loc and loc.text:
                            if self._is_product_url(loc.text):
                                self.product_urls.append(loc.text)
                                self.stats['discovery_methods']['sitemap'] = \
                                    self.stats['discovery_methods'].get('sitemap', 0) + 1
                    
                    if len(urls) > 0:
                        logger.info(f"Found {len(urls)} URLs in sitemap")
                        break  # Found sitemap, no need to check others
                        
            except Exception as e:
                pass  # Sitemaps might not exist
            
            time.sleep(1)
    
    def _discover_from_search(self):
        """Try search/filter endpoints"""
        logger.info(f"Strategy 5: Trying search endpoints")
        
        # Common search patterns
        search_urls = [
            urljoin(self.base_url, '/search?q=dog+food'),
            urljoin(self.base_url, '/products?category=dog'),
            urljoin(self.base_url, '/shop?filter=dog-food'),
            urljoin(self.base_url, '/api/products?type=dog')
        ]
        
        for search_url in search_urls:
            try:
                response = self.session.get(search_url, timeout=10)
                if response.status_code == 200:
                    self.stats['pages_scanned'] += 1
                    
                    # Try parsing as HTML
                    if 'html' in response.headers.get('content-type', ''):
                        soup = BeautifulSoup(response.text, 'html.parser')
                        links = soup.find_all('a', href=True)
                        
                        for link in links:
                            href = link['href']
                            full_url = urljoin(search_url, href)
                            if self._is_product_url(full_url):
                                self.product_urls.append(full_url)
                                self.stats['discovery_methods']['search'] = \
                                    self.stats['discovery_methods'].get('search', 0) + 1
                    
                    # Try parsing as JSON
                    elif 'json' in response.headers.get('content-type', ''):
                        try:
                            data = response.json()
                            # Extract URLs from JSON response
                            self._extract_urls_from_json(data)
                        except:
                            pass
                            
            except Exception as e:
                pass  # Search endpoints might not exist
            
            time.sleep(1)
    
    def _extract_urls_from_json(self, data):
        """Recursively extract URLs from JSON data"""
        if isinstance(data, dict):
            for key, value in data.items():
                if key in ['url', 'href', 'link', 'product_url'] and isinstance(value, str):
                    if self._is_product_url(value):
                        self.product_urls.append(value)
                        self.stats['discovery_methods']['api'] = \
                            self.stats['discovery_methods'].get('api', 0) + 1
                elif isinstance(value, (dict, list)):
                    self._extract_urls_from_json(value)
        elif isinstance(data, list):
            for item in data:
                self._extract_urls_from_json(item)
    
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
            '/category/', '/categories/', '/collections/',
            '/pages/', '/blogs/', '/cart', '/checkout',
            '/account', '/login', '/register', '/search',
            '/about', '/contact', '/terms', '/privacy',
            '/sitemap', '.xml', '.pdf', '.jpg', '.png'
        ]
        
        url_lower = url.lower()
        for pattern in exclude_patterns:
            if pattern in url_lower:
                return False
        
        # Include product patterns
        include_patterns = [
            '/product/', '/products/', '/shop/', '/item/',
            '/p/', '-dog-food', 'dog-treats', 'puppy-food'
        ]
        
        for pattern in include_patterns:
            if pattern in url_lower:
                self.discovered_urls.add(url)
                return True
        
        # Check if URL ends with product-like slug
        path = parsed.path.rstrip('/')
        if path and '/' in path:
            last_part = path.split('/')[-1]
            if len(last_part) > 10 and '-' in last_part:
                self.discovered_urls.add(url)
                return True
        
        return False
    
    def snapshot_products(self, product_urls: List[str]) -> Dict:
        """Snapshot discovered product pages to GCS"""
        logger.info(f"Snapshotting {len(product_urls)} products for {self.brand}")
        
        date_str = datetime.now().strftime('%Y-%m-%d')
        snapshot_stats = {
            'snapshots_created': 0,
            'snapshots_failed': 0,
            'total_size_mb': 0
        }
        
        for i, url in enumerate(product_urls, 1):
            try:
                logger.info(f"[{i}/{len(product_urls)}] Fetching {url}")
                
                response = self.session.get(url, timeout=15)
                if response.status_code == 200:
                    # Generate filename from URL
                    parsed = urlparse(url)
                    path_parts = parsed.path.strip('/').split('/')
                    filename = '_'.join(path_parts[-2:]) if len(path_parts) > 1 else path_parts[-1]
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
                        'content_type': 'product_page'
                    }
                    
                    # Upload content
                    blob.upload_from_string(response.text, content_type='text/html')
                    
                    size_mb = len(response.content) / (1024 * 1024)
                    snapshot_stats['snapshots_created'] += 1
                    snapshot_stats['total_size_mb'] += size_mb
                    
                    logger.info(f"  ✓ Uploaded {filename} ({size_mb:.2f} MB)")
                else:
                    logger.warning(f"  ✗ HTTP {response.status_code}")
                    snapshot_stats['snapshots_failed'] += 1
                    
            except Exception as e:
                logger.error(f"  ✗ Error: {e}")
                snapshot_stats['snapshots_failed'] += 1
            
            # Rate limiting
            time.sleep(3)
        
        return snapshot_stats


def main():
    """Run deep product discovery for target brands"""
    
    brands = ['brit', 'alpha', 'forthglade']
    all_stats = {}
    
    print("="*80)
    print("DEEP PRODUCT DISCOVERY")
    print("="*80)
    print(f"Brands: {', '.join(brands)}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("="*80)
    
    for brand in brands:
        print(f"\n{'='*40}")
        print(f"Processing {brand.upper()}")
        print(f"{'='*40}")
        
        profile_path = Path(f'profiles/manufacturers/{brand}.yaml')
        if not profile_path.exists():
            logger.warning(f"Profile not found for {brand}")
            continue
        
        try:
            # Initialize discovery
            discovery = DeepProductDiscovery(brand, profile_path)
            
            # Discover product URLs
            product_urls = discovery.discover_products(max_products=30)
            
            # Snapshot products to GCS
            snapshot_stats = discovery.snapshot_products(product_urls)
            
            # Store results
            all_stats[brand] = {
                'discovery': discovery.stats,
                'snapshot': snapshot_stats,
                'product_urls': product_urls[:10]  # Sample for report
            }
            
            print(f"\n✓ Completed {brand}:")
            print(f"  - Pages scanned: {discovery.stats['pages_scanned']}")
            print(f"  - Products found: {discovery.stats['product_urls_found']}")
            print(f"  - Snapshots created: {snapshot_stats['snapshots_created']}")
            
        except Exception as e:
            logger.error(f"Failed to process {brand}: {e}")
            all_stats[brand] = {'error': str(e)}
    
    # Generate report
    generate_discovery_report(all_stats)
    
    print("\n" + "="*80)
    print("DISCOVERY COMPLETE")
    print("="*80)
    print("Report saved to: DISCOVERY_REPORT.md")
    
    return all_stats


def generate_discovery_report(stats: Dict):
    """Generate discovery report"""
    
    with open('DISCOVERY_REPORT.md', 'w') as f:
        f.write("# Deep Product Discovery Report\n\n")
        f.write(f"**Generated:** {datetime.now().isoformat()}\n")
        f.write(f"**Brands:** brit, alpha, forthglade\n\n")
        
        f.write("## Summary\n\n")
        
        total_pages = sum(s['discovery']['pages_scanned'] for s in stats.values() if 'discovery' in s)
        total_products = sum(s['discovery']['product_urls_found'] for s in stats.values() if 'discovery' in s)
        total_snapshots = sum(s['snapshot']['snapshots_created'] for s in stats.values() if 'snapshot' in s)
        
        f.write(f"- **Total pages scanned:** {total_pages}\n")
        f.write(f"- **Total product URLs found:** {total_products}\n")
        f.write(f"- **Total snapshots created:** {total_snapshots}\n\n")
        
        for brand, brand_stats in stats.items():
            f.write(f"## {brand.upper()}\n\n")
            
            if 'error' in brand_stats:
                f.write(f"**Error:** {brand_stats['error']}\n\n")
                continue
            
            discovery = brand_stats['discovery']
            snapshot = brand_stats['snapshot']
            
            f.write("### Discovery Statistics\n")
            f.write(f"- Pages scanned: {discovery['pages_scanned']}\n")
            f.write(f"- Product URLs found: {discovery['product_urls_found']}\n")
            
            if discovery['discovery_methods']:
                f.write("\n**Discovery Methods:**\n")
                for method, count in discovery['discovery_methods'].items():
                    f.write(f"- {method}: {count} products\n")
            
            f.write("\n### Snapshot Statistics\n")
            f.write(f"- Snapshots created: {snapshot['snapshots_created']}\n")
            f.write(f"- Snapshots failed: {snapshot['snapshots_failed']}\n")
            f.write(f"- Total size: {snapshot['total_size_mb']:.1f} MB\n")
            
            if brand_stats.get('product_urls'):
                f.write("\n### Sample Product URLs\n")
                for url in brand_stats['product_urls'][:5]:
                    f.write(f"- {url}\n")
            
            f.write("\n")
        
        f.write("## Next Steps\n\n")
        f.write("1. Parse the new snapshots for ingredients and macros\n")
        f.write("2. Update foods_canonical with extracted data\n")
        f.write("3. Verify coverage improvements\n")
        f.write("4. Generate coverage metrics report\n")


if __name__ == "__main__":
    main()