#!/usr/bin/env python3
"""
Brand Harvest Job - Scrapes manufacturer websites respecting robots.txt
"""

import os
import yaml
import json
import time
import random
import hashlib
import requests
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
import pandas as pd
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BrandHarvester:
    def __init__(self, brand_slug: str):
        self.brand_slug = brand_slug
        self.profile_path = Path(f"profiles/brands/{brand_slug}.yaml")
        
        if not self.profile_path.exists():
            raise ValueError(f"Profile not found: {self.profile_path}")
        
        # Load profile
        with open(self.profile_path, 'r') as f:
            self.profile = yaml.safe_load(f)
        
        # Setup paths
        self.cache_dir = Path(f"cache/brands/{brand_slug}")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.report_dir = Path("reports/MANUF/harvests")
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; LupitoBot/1.0; +https://lupito.com/bot)'
        })
        
        # Setup robots parser
        self.robots = None
        if self.profile['rate_limits'].get('respect_robots', True):
            self.setup_robots()
        
        # Stats
        self.stats = {
            'urls_discovered': 0,
            'pages_fetched': 0,
            'pages_cached': 0,
            'pages_skipped': 0,
            'pages_failed': 0,
            'pdfs_fetched': 0,
            'jsonld_found': 0
        }
    
    def setup_robots(self):
        """Setup robots.txt parser"""
        try:
            robots_url = urljoin(self.profile['website_url'], '/robots.txt')
            self.robots = RobotFileParser()
            self.robots.set_url(robots_url)
            self.robots.read()
            logger.info(f"Loaded robots.txt from {robots_url}")
        except Exception as e:
            logger.warning(f"Could not load robots.txt: {e}")
            self.robots = None
    
    def can_fetch(self, url: str) -> bool:
        """Check if URL can be fetched according to robots.txt"""
        if not self.robots:
            return True
        return self.robots.can_fetch("*", url)
    
    def get_cache_path(self, url: str, ext: str = 'html') -> Path:
        """Generate cache file path for URL"""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return self.cache_dir / f"{url_hash}.{ext}"
    
    def is_cached(self, url: str, max_age_days: int = 7) -> bool:
        """Check if URL is cached and fresh"""
        cache_path = self.get_cache_path(url)
        if not cache_path.exists():
            return False
        
        # Check age
        age = time.time() - cache_path.stat().st_mtime
        return age < (max_age_days * 24 * 3600)
    
    def fetch_url(self, url: str, force: bool = False) -> Optional[Dict]:
        """Fetch URL with caching and rate limiting"""
        # Check cache
        if not force and self.is_cached(url):
            self.stats['pages_cached'] += 1
            cache_path = self.get_cache_path(url)
            
            # Load metadata
            meta_path = cache_path.with_suffix('.meta.json')
            if meta_path.exists():
                with open(meta_path, 'r') as f:
                    metadata = json.load(f)
            else:
                metadata = {'cached': True}
            
            # Load content
            with open(cache_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                'url': url,
                'content': content,
                'metadata': metadata,
                'from_cache': True
            }
        
        # Check robots
        if not self.can_fetch(url):
            logger.warning(f"Robots.txt disallows: {url}")
            self.stats['pages_skipped'] += 1
            return None
        
        # Rate limiting
        delay = self.profile['rate_limits']['delay_seconds']
        jitter = self.profile['rate_limits'].get('jitter_seconds', 1)
        time.sleep(delay + random.random() * jitter)
        
        # Fetch
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            self.stats['pages_fetched'] += 1
            
            # Save to cache
            cache_path = self.get_cache_path(url)
            with open(cache_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            # Save metadata
            metadata = {
                'url': url,
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'fetched_at': datetime.now().isoformat(),
                'content_type': response.headers.get('content-type', '')
            }
            
            meta_path = cache_path.with_suffix('.meta.json')
            with open(meta_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            return {
                'url': url,
                'content': response.text,
                'metadata': metadata,
                'from_cache': False
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            self.stats['pages_failed'] += 1
            return None
    
    def discover_product_urls(self) -> List[str]:
        """Discover product URLs based on profile method"""
        urls = []
        method = self.profile['discovery']['method']
        
        if method == 'sitemap':
            urls = self.discover_from_sitemap()
        elif method == 'category_pages':
            urls = self.discover_from_categories()
        else:
            logger.warning(f"Unknown discovery method: {method}")
        
        self.stats['urls_discovered'] = len(urls)
        logger.info(f"Discovered {len(urls)} product URLs")
        return urls
    
    def discover_from_sitemap(self) -> List[str]:
        """Discover URLs from sitemap"""
        sitemap_url = self.profile['discovery'].get('sitemap_url')
        if not sitemap_url:
            return []
        
        result = self.fetch_url(sitemap_url)
        if not result:
            return []
        
        soup = BeautifulSoup(result['content'], 'xml')
        urls = []
        
        for loc in soup.find_all('loc'):
            url = loc.text.strip()
            # Filter for DOG product pages only
            if ('/product' in url or '/dog/' in url) and '/cat/' not in url and 'kitten' not in url.lower():
                urls.append(url)
        
        return urls
    
    def discover_from_categories(self) -> List[str]:
        """Discover URLs from category pages"""
        urls = []
        
        for category_url in self.profile['discovery'].get('category_urls', []):
            result = self.fetch_url(category_url)
            if not result:
                continue
            
            soup = BeautifulSoup(result['content'], 'html.parser')
            
            # Look for product links
            for link in soup.find_all('a', href=True):
                href = link['href']
                if '/product' in href:
                    full_url = urljoin(category_url, href)
                    if full_url not in urls:
                        urls.append(full_url)
        
        return urls
    
    def extract_jsonld(self, html: str) -> Optional[Dict]:
        """Extract JSON-LD from HTML"""
        if not self.profile['jsonld'].get('enabled', False):
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        scripts = soup.find_all('script', type='application/ld+json')
        
        for script in scripts:
            try:
                data = json.loads(script.string)
                
                # Check if it's a Product type
                if '@type' in data and data['@type'] in self.profile['jsonld']['types']:
                    self.stats['jsonld_found'] += 1
                    return data
                    
            except json.JSONDecodeError:
                continue
        
        return None
    
    def extract_product_data(self, url: str, html: str) -> Dict:
        """Extract product data from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        data = {
            'url': url,
            'scraped_at': datetime.now().isoformat()
        }
        
        # Extract using selectors
        selectors = self.profile['pdp_selectors']
        
        for field, selector_config in selectors.items():
            value = None
            
            # Try CSS selector
            if 'css' in selector_config:
                element = soup.select_one(selector_config['css'])
                if element:
                    value = element.get_text(strip=True)
            
            # Try keywords
            if not value and 'keywords' in selector_config:
                text = soup.get_text().lower()
                for keyword in selector_config['keywords']:
                    if keyword in text:
                        value = keyword
                        break
            
            if value:
                data[field] = value
        
        # Extract JSON-LD if available
        jsonld = self.extract_jsonld(html)
        if jsonld:
            data['jsonld'] = jsonld
        
        return data
    
    def harvest_products(self, limit: Optional[int] = None) -> pd.DataFrame:
        """Main harvest function"""
        logger.info(f"Starting harvest for {self.brand_slug}")
        
        # Discover URLs
        urls = self.discover_product_urls()
        
        if limit:
            urls = urls[:limit]
        
        # Harvest each URL
        products = []
        
        for i, url in enumerate(urls, 1):
            logger.info(f"Processing {i}/{len(urls)}: {url}")
            
            result = self.fetch_url(url)
            if not result:
                continue
            
            # Extract data
            product_data = self.extract_product_data(url, result['content'])
            product_data['brand'] = self.profile['brand']
            product_data['brand_slug'] = self.brand_slug
            product_data['from_cache'] = result['from_cache']
            
            products.append(product_data)
        
        # Create DataFrame
        df = pd.DataFrame(products)
        
        # Save results
        output_file = self.report_dir / f"{self.brand_slug}_harvest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(output_file, index=False)
        
        logger.info(f"Harvest complete. Saved {len(df)} products to {output_file}")
        
        return df
    
    def generate_report(self):
        """Generate harvest report"""
        report = f"""# HARVEST REPORT: {self.brand_slug.upper()}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Statistics
- URLs Discovered: {self.stats['urls_discovered']}
- Pages Fetched: {self.stats['pages_fetched']}
- Pages from Cache: {self.stats['pages_cached']}
- Pages Skipped (robots): {self.stats['pages_skipped']}
- Pages Failed: {self.stats['pages_failed']}
- PDFs Downloaded: {self.stats['pdfs_fetched']}
- JSON-LD Found: {self.stats['jsonld_found']}

## Configuration
- Website: {self.profile['website_url']}
- Discovery Method: {self.profile['discovery']['method']}
- Rate Limit: {self.profile['rate_limits']['delay_seconds']}s delay
- Robots.txt Respected: {self.profile['rate_limits'].get('respect_robots', True)}

## Cache Status
- Cache Directory: {self.cache_dir}
- Cache Size: {sum(f.stat().st_size for f in self.cache_dir.glob('*')) / 1024 / 1024:.1f} MB
- Cached Files: {len(list(self.cache_dir.glob('*.html')))}
"""
        
        report_path = self.report_dir / f"{self.brand_slug}_report_{datetime.now().strftime('%Y%m%d')}.md"
        with open(report_path, 'w') as f:
            f.write(report)
        
        logger.info(f"Report saved to {report_path}")
        print(report)
        
        return report

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Harvest brand product data')
    parser.add_argument('brand', help='Brand slug to harvest')
    parser.add_argument('--limit', type=int, help='Limit number of products')
    parser.add_argument('--force', action='store_true', help='Force refresh (ignore cache)')
    
    args = parser.parse_args()
    
    try:
        harvester = BrandHarvester(args.brand)
        df = harvester.harvest_products(limit=args.limit)
        harvester.generate_report()
        
        print(f"\n✅ Harvest complete: {len(df)} products")
        
    except Exception as e:
        logger.error(f"Harvest failed: {e}")
        raise

if __name__ == "__main__":
    main()