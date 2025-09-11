#!/usr/bin/env python3
"""
Complete Brand Website Discovery Script
Continues from existing progress and uses ScrapingBee for blocked sites
"""

import os
import yaml
import json
import time
import requests
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, quote
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

class CompleteBrandDiscovery:
    def __init__(self):
        # ScrapingBee configuration
        self.scrapingbee_api_key = os.getenv('SCRAPING_BEE')
        self.scrapingbee_endpoint = "https://app.scrapingbee.com/api/v1/"
        
        # File paths
        self.all_brands_file = Path("docs/ALL-BRANDS.md")
        self.existing_output = Path("data/brand_sites_complete.yaml")
        self.final_output = Path("data/brand_sites_final.yaml")
        
        # Load existing progress
        self.results = self.load_existing_progress()
        
        # Statistics
        self.stats = {
            'scrapingbee_credits': 0,
            'new_websites_found': 0,
            'resumed_from': len(self.results['brands'])
        }
        
        print(f"✅ ScrapingBee API key loaded: {'Yes' if self.scrapingbee_api_key else 'No'}")
        print(f"📊 Resuming from: {len(self.results['brands'])} brands already processed")
    
    def load_existing_progress(self) -> Dict:
        """Load existing progress from previous run"""
        if self.existing_output.exists():
            try:
                with open(self.existing_output, 'r') as f:
                    return yaml.unsafe_load(f)
            except:
                pass
        
        # Initialize if no existing file
        return {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_brands': 0,
                'brands_with_websites': 0,
                'brands_crawlable': 0,
                'scrapingbee_credits_used': 0
            },
            'brands': {}
        }
    
    def load_all_brands(self) -> List[str]:
        """Load all 279 brands from ALL-BRANDS.md"""
        brands = []
        if self.all_brands_file.exists():
            with open(self.all_brands_file, 'r') as f:
                for line in f:
                    brand = line.strip()
                    if brand and not brand.startswith('#'):
                        brands.append(brand)
        return brands
    
    def create_brand_slug(self, brand_name: str) -> str:
        """Create a consistent brand slug"""
        return brand_name.lower().replace(' ', '_').replace('-', '_').replace('&', 'and').replace('.', '').replace("'", '')
    
    def quick_domain_check(self, brand_name: str) -> Optional[str]:
        """Quick check of most likely domain patterns"""
        brand_slug = self.create_brand_slug(brand_name)
        brand_clean = brand_name.lower().replace(' ', '').replace('-', '').replace('&', 'and')
        
        # Most likely patterns only
        patterns = [
            f"https://www.{brand_slug}.com",
            f"https://www.{brand_clean}.com",
            f"https://www.{brand_slug}petfood.com",
            f"https://www.{brand_slug}.co.uk",
        ]
        
        for url in patterns:
            try:
                response = requests.head(url, timeout=3, allow_redirects=True)
                if response.status_code in [200, 301, 302]:
                    return url
            except:
                continue
        
        return None
    
    def search_with_scrapingbee(self, brand_name: str) -> Optional[str]:
        """Use ScrapingBee to search for brand website"""
        if not self.scrapingbee_api_key:
            return None
        
        query = f'"{brand_name}" dog food official website'
        search_url = f"https://www.google.com/search?q={quote(query)}"
        
        params = {
            'api_key': self.scrapingbee_api_key,
            'url': search_url,
            'render_js': 'false',
            'premium_proxy': 'false',
            'block_resources': 'true',
        }
        
        try:
            response = requests.get(self.scrapingbee_endpoint, params=params, timeout=30)
            
            if response.status_code == 200:
                self.stats['scrapingbee_credits'] += 1
                html = response.text
                soup = BeautifulSoup(html, 'html.parser')
                
                # Look for URLs in search results
                for link in soup.find_all('a', href=True):
                    href = link.get('href', '')
                    
                    # Extract URL from Google redirect
                    if '/url?q=' in href:
                        import urllib.parse
                        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                        if 'q' in parsed:
                            url = parsed['q'][0]
                            # Check if it looks like a brand website
                            domain = urlparse(url).netloc.lower()
                            brand_clean = brand_name.lower().replace(' ', '').replace('-', '')
                            
                            # Skip social media and marketplaces
                            skip = ['facebook', 'instagram', 'amazon', 'chewy', 'wikipedia']
                            if any(s in domain for s in skip):
                                continue
                            
                            # Check if brand name is in domain
                            if brand_clean in domain or 'pet' in domain or 'dog' in domain:
                                return url
                
                # Check for direct domain mentions in text
                text = soup.get_text().lower()
                brand_slug = self.create_brand_slug(brand_name)
                patterns = [f"{brand_slug}.com", f"{brand_slug}.co.uk", f"{brand_slug}petfood.com"]
                
                for pattern in patterns:
                    if pattern in text:
                        return f"https://www.{pattern}"
                        
        except Exception as e:
            print(f"    ScrapingBee error: {e}")
        
        return None
    
    def check_robots_txt(self, website_url: str) -> Dict:
        """Quick robots.txt check"""
        try:
            parsed = urlparse(website_url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            
            response = requests.get(robots_url, timeout=3)
            if response.status_code == 200:
                content = response.text.lower()
                
                # Simple check for disallow all
                if 'disallow: /' in content and 'allow:' not in content:
                    return {'can_crawl': False, 'crawl_delay': 1.0}
                
                # Check for crawl delay
                delay = 1.0
                for line in content.split('\n'):
                    if 'crawl-delay:' in line:
                        try:
                            delay = float(line.split(':')[1].strip())
                        except:
                            pass
                
                return {'can_crawl': True, 'crawl_delay': delay}
        except:
            pass
        
        return {'can_crawl': True, 'crawl_delay': 1.0}
    
    def process_brand(self, brand_name: str) -> Dict:
        """Process a single brand"""
        brand_slug = self.create_brand_slug(brand_name)
        
        # Skip if already processed
        if brand_slug in self.results['brands']:
            return self.results['brands'][brand_slug]
        
        print(f"\n🔎 Processing: {brand_name}")
        
        result = {
            'brand_name': brand_name,
            'website_url': None,
            'discovery_method': None,
            'has_website': False,
            'robots': {'can_crawl': True, 'crawl_delay': 1.0},
            'scrapingbee_fallback': False
        }
        
        # Try quick domain check first
        website = self.quick_domain_check(brand_name)
        if website:
            result['website_url'] = website
            result['discovery_method'] = 'pattern'
            print(f"  ✅ Found via pattern: {website}")
        else:
            # Use ScrapingBee if pattern didn't work
            website = self.search_with_scrapingbee(brand_name)
            if website:
                result['website_url'] = website
                result['discovery_method'] = 'scrapingbee'
                print(f"  ✅ Found via ScrapingBee: {website}")
        
        # If we found a website, check robots.txt
        if website:
            result['has_website'] = True
            robots_info = self.check_robots_txt(website)
            result['robots'] = robots_info
            
            # If robots.txt blocks crawling, note for ScrapingBee usage
            if not robots_info['can_crawl']:
                result['scrapingbee_fallback'] = True
                print(f"  ⚠️ Robots.txt blocks crawling - will need ScrapingBee for content")
            
            self.stats['new_websites_found'] += 1
        else:
            print(f"  ❌ No website found")
        
        return result
    
    def complete_discovery(self):
        """Complete the brand discovery process"""
        print("="*80)
        print("COMPLETING BRAND WEBSITE DISCOVERY")
        print("="*80)
        
        # Load all brands
        all_brands = self.load_all_brands()
        print(f"📚 Total brands to process: {len(all_brands)}")
        
        # Find remaining brands
        processed_slugs = set(self.results['brands'].keys())
        remaining_brands = []
        
        for brand in all_brands:
            brand_slug = self.create_brand_slug(brand)
            if brand_slug not in processed_slugs:
                remaining_brands.append(brand)
        
        print(f"✅ Already processed: {len(processed_slugs)}")
        print(f"🎯 Remaining to process: {len(remaining_brands)}")
        
        if not remaining_brands:
            print("\n✅ All brands already processed!")
            self.generate_final_report()
            return
        
        # Process remaining brands in batches
        batch_size = 10
        for i in range(0, len(remaining_brands), batch_size):
            batch = remaining_brands[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(remaining_brands) + batch_size - 1) // batch_size
            
            print(f"\n📦 Batch {batch_num}/{total_batches} (Brands {i+1}-{min(i+batch_size, len(remaining_brands))})")
            print("-"*40)
            
            for brand in batch:
                brand_slug = self.create_brand_slug(brand)
                brand_data = self.process_brand(brand)
                self.results['brands'][brand_slug] = brand_data
                time.sleep(0.5)  # Rate limiting
            
            # Update metadata
            self.update_metadata()
            
            # Save progress
            self.save_progress()
            
            print(f"\n💾 Progress saved ({len(self.results['brands'])}/{len(all_brands)} brands)")
            print(f"💳 ScrapingBee credits used this session: {self.stats['scrapingbee_credits']}")
        
        # Generate final report
        self.generate_final_report()
    
    def update_metadata(self):
        """Update metadata statistics"""
        self.results['metadata']['total_brands'] = len(self.results['brands'])
        self.results['metadata']['brands_with_websites'] = sum(
            1 for b in self.results['brands'].values() if b.get('has_website')
        )
        self.results['metadata']['brands_crawlable'] = sum(
            1 for b in self.results['brands'].values() 
            if b.get('has_website') and b.get('robots', {}).get('can_crawl', True)
        )
        self.results['metadata']['brands_need_scrapingbee'] = sum(
            1 for b in self.results['brands'].values() 
            if b.get('has_website') and b.get('scrapingbee_fallback', False)
        )
        self.results['metadata']['scrapingbee_credits_used'] = self.stats['scrapingbee_credits']
        self.results['metadata']['last_updated'] = datetime.now().isoformat()
    
    def save_progress(self):
        """Save current progress"""
        with open(self.final_output, 'w') as f:
            yaml.dump(self.results, f, default_flow_style=False, sort_keys=False)
    
    def generate_final_report(self):
        """Generate final report"""
        print("\n" + "="*80)
        print("FINAL DISCOVERY REPORT")
        print("="*80)
        
        total = len(self.results['brands'])
        with_sites = self.results['metadata']['brands_with_websites']
        can_crawl = self.results['metadata']['brands_crawlable']
        need_sb = self.results['metadata'].get('brands_need_scrapingbee', 0)
        
        print(f"\n📊 Overall Statistics:")
        print(f"  Total brands: {total}")
        print(f"  Websites found: {with_sites} ({with_sites/total*100:.1f}%)")
        print(f"  Can crawl directly: {can_crawl} ({can_crawl/total*100:.1f}%)")
        print(f"  Need ScrapingBee for content: {need_sb}")
        print(f"  No website found: {total - with_sites}")
        
        print(f"\n💰 ScrapingBee Usage:")
        print(f"  Credits used for discovery: {self.stats['scrapingbee_credits']}")
        print(f"  Estimated credits for blocked sites: {need_sb * 5} (5 per page with JS)")
        print(f"  Total estimated cost: ${(self.stats['scrapingbee_credits'] + need_sb * 5) * 0.001:.2f}")
        
        # Discovery method breakdown
        methods = {}
        for brand_data in self.results['brands'].values():
            if brand_data.get('has_website'):
                method = brand_data.get('discovery_method', 'unknown')
                methods[method] = methods.get(method, 0) + 1
        
        print(f"\n🔍 Discovery Methods:")
        for method, count in methods.items():
            print(f"  {method}: {count} brands")
        
        print(f"\n📁 Results saved to: {self.final_output}")
        
        # List brands that need ScrapingBee for crawling
        if need_sb > 0:
            print(f"\n⚠️ Brands that need ScrapingBee for content scraping:")
            for slug, data in self.results['brands'].items():
                if data.get('scrapingbee_fallback'):
                    print(f"  - {data['brand_name']}: {data.get('website_url')}")

def main():
    """Main execution"""
    discovery = CompleteBrandDiscovery()
    discovery.complete_discovery()

if __name__ == "__main__":
    main()