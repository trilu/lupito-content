#!/usr/bin/env python3
"""
Wave 1 Snapshot Harvester - Captures HTML and PDFs to GCS
No parsing, just raw content storage
"""

import os
import time
import random
import hashlib
import requests
import yaml
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urljoin, quote
from urllib.robotparser import RobotFileParser
from google.cloud import storage
from bs4 import BeautifulSoup
import logging
from typing import Dict, List, Optional, Set
import json
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up GCS credentials
if 'GOOGLE_APPLICATION_CREDENTIALS' not in os.environ:
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = './secrets/gcp-sa.json'

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Wave1SnapshotHarvester:
    def __init__(self, brand_slug: str, profile_path: Path):
        self.brand_slug = brand_slug
        self.profile_path = profile_path
        
        # Load profile
        with open(profile_path, 'r') as f:
            self.profile = yaml.safe_load(f)
        
        # GCS configuration
        self.bucket_name = 'lupito-content-raw-eu'
        self.date_str = datetime.now().strftime('%Y-%m-%d')
        self.gcs_prefix = f"manufacturers/{brand_slug}/{self.date_str}"
        
        # Initialize GCS client
        try:
            self.storage_client = storage.Client()
            self.bucket = self.storage_client.bucket(self.bucket_name)
            logger.info(f"Connected to GCS bucket: {self.bucket_name}")
        except Exception as e:
            logger.error(f"Failed to connect to GCS: {e}")
            raise
        
        # Setup session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.profile['rate_limits'].get('user_agent', 
                'Mozilla/5.0 (compatible; LupitoBot/1.0; +https://lupito.com/bot)')
        })
        
        # Setup robots parser
        self.robots = None
        if self.profile['rate_limits'].get('respect_robots', True):
            self.setup_robots()
        
        # Statistics
        self.stats = {
            'pages_fetched': 0,
            'pages_uploaded': 0,
            'pdfs_found': 0,
            'pdfs_uploaded': 0,
            'failures': {},
            'total_size_mb': 0,
            'urls_visited': set()
        }
        
        # Track visited URLs to avoid duplicates
        self.visited_urls = set()
        self.pdf_urls = set()
    
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
    
    def generate_stable_filename(self, url: str, content_type: str = 'html') -> str:
        """Generate stable filename from URL"""
        # Parse URL
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        
        if path:
            # Use path as base for filename
            filename = path.replace('/', '_')
            # Remove extension if present
            filename = re.sub(r'\.\w+$', '', filename)
        else:
            # Use URL hash for homepage or parameterized URLs
            filename = hashlib.md5(url.encode()).hexdigest()[:12]
        
        # Add appropriate extension
        if content_type == 'pdf':
            filename += '.pdf'
        else:
            filename += '.html'
        
        # Ensure filename is safe for GCS
        filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
        
        return filename
    
    def upload_to_gcs(self, content: bytes, filename: str, metadata: Dict) -> bool:
        """Upload content to GCS"""
        try:
            blob_path = f"{self.gcs_prefix}/{filename}"
            blob = self.bucket.blob(blob_path)
            
            # Set metadata
            blob.metadata = metadata
            
            # Upload content
            blob.upload_from_string(content)
            
            # Track size
            self.stats['total_size_mb'] += len(content) / (1024 * 1024)
            
            logger.info(f"Uploaded to GCS: {blob_path} ({len(content)/1024:.1f} KB)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload {filename}: {e}")
            return False
    
    def fetch_and_store(self, url: str, is_pdf: bool = False) -> bool:
        """Fetch URL and store to GCS"""
        # Skip if already visited
        if url in self.visited_urls:
            return True
        
        # Check robots.txt
        if not self.can_fetch(url):
            logger.warning(f"Robots.txt disallows: {url}")
            self.stats['failures']['robots_blocked'] = self.stats['failures'].get('robots_blocked', 0) + 1
            return False
        
        # Rate limiting
        delay = self.profile['rate_limits']['delay_seconds']
        jitter = self.profile['rate_limits'].get('jitter_seconds', 1)
        time.sleep(delay + random.random() * jitter)
        
        try:
            # Fetch content
            response = self.session.get(url, timeout=30, allow_redirects=True)
            response.raise_for_status()
            
            self.stats['pages_fetched'] += 1
            self.visited_urls.add(url)
            
            # Determine content type
            content_type = response.headers.get('content-type', '').lower()
            
            if 'pdf' in content_type or url.lower().endswith('.pdf'):
                # PDF content
                filename = self.generate_stable_filename(url, 'pdf')
                self.stats['pdfs_found'] += 1
                is_pdf = True
            else:
                # HTML content
                filename = self.generate_stable_filename(url, 'html')
            
            # Prepare metadata
            metadata = {
                'url': url,
                'brand': self.brand_slug,
                'content_type': content_type,
                'status_code': str(response.status_code),
                'fetched_at': datetime.now().isoformat(),
                'size_bytes': str(len(response.content))
            }
            
            # Upload to GCS
            if self.upload_to_gcs(response.content, filename, metadata):
                if is_pdf:
                    self.stats['pdfs_uploaded'] += 1
                else:
                    self.stats['pages_uploaded'] += 1
                return True
            
        except requests.HTTPError as e:
            status_code = e.response.status_code if e.response else 'unknown'
            self.stats['failures'][f'http_{status_code}'] = self.stats['failures'].get(f'http_{status_code}', 0) + 1
            logger.error(f"HTTP error {status_code} for {url}")
            
        except Exception as e:
            self.stats['failures']['other'] = self.stats['failures'].get('other', 0) + 1
            logger.error(f"Failed to fetch {url}: {e}")
        
        return False
    
    def discover_product_urls(self) -> List[str]:
        """Discover product URLs using profile configuration"""
        urls = []
        
        # Try sitemap first
        if self.profile['discovery'].get('sitemap_url'):
            logger.info(f"Checking sitemap: {self.profile['discovery']['sitemap_url']}")
            if self.fetch_and_store(self.profile['discovery']['sitemap_url']):
                # Note: In production, we'd parse the sitemap from GCS
                # For now, fetch again to parse
                try:
                    response = self.session.get(self.profile['discovery']['sitemap_url'], timeout=10)
                    soup = BeautifulSoup(response.text, 'xml')
                    
                    for loc in soup.find_all('loc'):
                        url = loc.text.strip()
                        # Filter for dog products
                        if any(pattern in url for pattern in self.profile['discovery']['product_url_patterns']):
                            if not any(exclude in url for exclude in self.profile['discovery']['exclude_patterns']):
                                urls.append(url)
                except:
                    pass
        
        # Try category pages
        for category_url in self.profile['discovery'].get('category_urls', []):
            logger.info(f"Checking category: {category_url}")
            if self.fetch_and_store(category_url):
                # Note: In production, we'd parse from GCS
                # For now, fetch again to find product links
                try:
                    response = self.session.get(category_url, timeout=10)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Use listing selectors from profile
                    for css_selector in self.profile['listing_selectors']['product_links']['css']:
                        for link in soup.select(css_selector):
                            href = link.get('href')
                            if href:
                                full_url = urljoin(category_url, href)
                                if full_url not in urls:
                                    urls.append(full_url)
                except:
                    pass
        
        return urls[:50]  # Limit to 50 products for snapshot
    
    def extract_pdf_links(self, url: str, html_content: str) -> List[str]:
        """Extract PDF links from HTML"""
        pdf_urls = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Use PDF selectors from profile
            for css_selector in self.profile['pdp_selectors']['pdf_links']['css']:
                for link in soup.select(css_selector):
                    href = link.get('href')
                    if href and ('.pdf' in href.lower() or 'download' in href.lower()):
                        full_url = urljoin(url, href)
                        if full_url not in self.pdf_urls:
                            pdf_urls.append(full_url)
                            self.pdf_urls.add(full_url)
        except:
            pass
        
        return pdf_urls
    
    def harvest_snapshot(self) -> Dict:
        """Main harvest function - snapshot only"""
        logger.info(f"Starting snapshot harvest for {self.brand_slug}")
        logger.info(f"GCS path: gs://{self.bucket_name}/{self.gcs_prefix}/")
        
        # Discover product URLs
        product_urls = self.discover_product_urls()
        logger.info(f"Discovered {len(product_urls)} product URLs")
        
        # Fetch each product page
        for i, url in enumerate(product_urls, 1):
            logger.info(f"Processing {i}/{len(product_urls)}: {url}")
            
            if self.fetch_and_store(url):
                # Try to fetch content again to look for PDFs
                # In production, we'd read from GCS
                try:
                    response = self.session.get(url, timeout=10)
                    pdf_links = self.extract_pdf_links(url, response.text)
                    
                    # Fetch PDFs
                    for pdf_url in pdf_links:
                        logger.info(f"  Found PDF: {pdf_url}")
                        self.fetch_and_store(pdf_url, is_pdf=True)
                except:
                    pass
        
        # Add URL count to stats
        self.stats['urls_visited'] = list(self.visited_urls)
        self.stats['total_urls'] = len(self.visited_urls)
        
        return self.stats

def main():
    """Run snapshot harvest for Wave 1 brands"""
    
    # Wave 1 brands
    wave1_brands = [
        'alpha', 'brit', 'briantos', 'canagan', 'cotswold',
        'burns', 'barking', 'bozita', 'forthglade', 'belcando'
    ]
    
    # Results storage
    harvest_results = []
    
    # Process each brand
    for brand_slug in wave1_brands:
        profile_path = Path(f'profiles/manufacturers/{brand_slug}.yaml')
        
        if not profile_path.exists():
            logger.warning(f"Profile not found for {brand_slug}")
            continue
        
        logger.info(f"\n{'='*60}")
        logger.info(f"HARVESTING: {brand_slug}")
        logger.info('='*60)
        
        try:
            harvester = Wave1SnapshotHarvester(brand_slug, profile_path)
            stats = harvester.harvest_snapshot()
            
            harvest_results.append({
                'brand': brand_slug,
                'status': 'success',
                'stats': stats
            })
            
            logger.info(f"✅ Completed {brand_slug}: {stats['pages_uploaded']} pages, {stats['pdfs_uploaded']} PDFs")
            
        except Exception as e:
            logger.error(f"❌ Failed {brand_slug}: {e}")
            harvest_results.append({
                'brand': brand_slug,
                'status': 'failed',
                'error': str(e)
            })
    
    # Generate summary report
    report_path = Path('reports/WAVE_1_SNAPSHOT_SUMMARY.md')
    
    with open(report_path, 'w') as f:
        f.write("# Wave 1 Snapshot Harvest Summary\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Bucket:** gs://{harvest_results[0]['stats'].get('bucket_name', 'lupito-content-raw-eu') if harvest_results else 'lupito-content-raw-eu'}/\n")
        f.write(f"**Brands Processed:** {len(harvest_results)}\n\n")
        
        # Overall statistics
        total_pages = sum(r['stats']['pages_uploaded'] for r in harvest_results if r['status'] == 'success')
        total_pdfs = sum(r['stats']['pdfs_uploaded'] for r in harvest_results if r['status'] == 'success')
        total_size = sum(r['stats']['total_size_mb'] for r in harvest_results if r['status'] == 'success')
        
        f.write("## Overall Statistics\n\n")
        f.write(f"- **Total Pages Captured:** {total_pages}\n")
        f.write(f"- **Total PDFs Captured:** {total_pdfs}\n")
        f.write(f"- **Total Size:** {total_size:.1f} MB\n\n")
        
        f.write("## Per-Brand Results\n\n")
        f.write("| Brand | Status | Pages | PDFs | Size (MB) | Failures |\n")
        f.write("|-------|--------|-------|------|-----------|----------|\n")
        
        for result in harvest_results:
            if result['status'] == 'success':
                stats = result['stats']
                failures = ', '.join([f"{k}:{v}" for k,v in stats['failures'].items()]) or 'None'
                f.write(f"| {result['brand']} | ✅ | {stats['pages_uploaded']} | ")
                f.write(f"{stats['pdfs_uploaded']} | {stats['total_size_mb']:.1f} | {failures} |\n")
            else:
                f.write(f"| {result['brand']} | ❌ | - | - | - | {result.get('error', 'Unknown')} |\n")
        
        f.write("\n## Failure Breakdown\n\n")
        
        # Aggregate failures
        all_failures = {}
        for result in harvest_results:
            if result['status'] == 'success':
                for failure_type, count in result['stats']['failures'].items():
                    all_failures[failure_type] = all_failures.get(failure_type, 0) + count
        
        if all_failures:
            f.write("| Failure Type | Count |\n")
            f.write("|--------------|-------|\n")
            for failure_type, count in sorted(all_failures.items()):
                f.write(f"| {failure_type} | {count} |\n")
        else:
            f.write("No failures recorded.\n")
        
        f.write("\n## GCS Storage Structure\n\n")
        f.write("```\n")
        f.write("gs://lupito-content-raw-eu/\n")
        f.write("└── manufacturers/\n")
        for result in harvest_results:
            if result['status'] == 'success':
                f.write(f"    ├── {result['brand']}/\n")
                f.write(f"    │   └── {datetime.now().strftime('%Y-%m-%d')}/\n")
                f.write(f"    │       ├── *.html ({result['stats']['pages_uploaded']} files)\n")
                if result['stats']['pdfs_uploaded'] > 0:
                    f.write(f"    │       └── *.pdf ({result['stats']['pdfs_uploaded']} files)\n")
        f.write("```\n")
        
        f.write("\n## Next Steps\n\n")
        f.write("1. Verify GCS uploads via Console or gsutil\n")
        f.write("2. Run parsing pipeline on captured content\n")
        f.write("3. Extract structured data to foods_canonical\n")
        f.write("4. Compare with existing data for quality check\n")
    
    logger.info(f"\n✅ Snapshot harvest complete")
    logger.info(f"📄 Report saved to: {report_path}")

if __name__ == "__main__":
    main()