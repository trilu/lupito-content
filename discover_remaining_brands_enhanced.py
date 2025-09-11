#!/usr/bin/env python3
"""
Enhanced Brand Website Discovery Script
Uses multiple strategies including ScrapingBee to find websites for all 278 brands
"""

import os
import yaml
import json
import time
import requests
import re
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, quote
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

class EnhancedBrandWebsiteDiscovery:
    def __init__(self):
        # ScrapingBee configuration
        self.scrapingbee_api_key = os.getenv('SCRAPING_BEE')
        self.scrapingbee_endpoint = "https://app.scrapingbee.com/api/v1/"
        
        # File paths
        self.all_brands_file = Path("docs/ALL-BRANDS.md")
        self.brand_sites_yaml = Path("data/brand_sites.yaml")
        self.output_file = Path("data/brand_sites_complete.yaml")
        
        # Load existing brand sites
        self.existing_sites = {}
        if self.brand_sites_yaml.exists():
            try:
                with open(self.brand_sites_yaml, 'r') as f:
                    # Use unsafe_load to handle numpy objects, but we'll clean them
                    data = yaml.unsafe_load(f)
                    if data and 'brands' in data:
                        # Clean the data - convert numpy types to Python types
                        for brand_slug, brand_data in data['brands'].items():
                            if isinstance(brand_data, dict):
                                # Clean up numpy types in stats
                                if 'stats' in brand_data:
                                    for key, val in brand_data['stats'].items():
                                        if hasattr(val, 'item'):  # numpy scalar
                                            brand_data['stats'][key] = val.item()
                                self.existing_sites[brand_slug] = brand_data
            except Exception as e:
                print(f"⚠️ Warning: Could not load existing sites (will start fresh): {e}")
                self.existing_sites = {}
        
        # Statistics
        self.stats = {
            'total_processed': 0,
            'websites_found': 0,
            'websites_verified': 0,
            'scrapingbee_credits_used': 0,
            'discovery_methods': {}
        }
        
        print(f"✅ ScrapingBee API key loaded: {'Yes' if self.scrapingbee_api_key else 'No'}")
        print(f"📊 Existing brand sites loaded: {len(self.existing_sites)} brands")
    
    def load_all_brands(self) -> List[str]:
        """Load all 278 brands from ALL-BRANDS.md"""
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
    
    def search_with_scrapingbee(self, brand_name: str) -> Optional[str]:
        """Use ScrapingBee to search Google for brand website"""
        if not self.scrapingbee_api_key:
            return None
        
        # Search query
        query = f"{brand_name} dog food official website"
        search_url = f"https://www.google.com/search?q={quote(query)}"
        
        params = {
            'api_key': self.scrapingbee_api_key,
            'url': search_url,
            'render_js': 'false',  # Google search doesn't need JS
            'premium_proxy': 'false',
            'block_resources': 'true',
        }
        
        try:
            print(f"  🔍 ScrapingBee searching Google for: {brand_name}")
            response = requests.get(self.scrapingbee_endpoint, params=params, timeout=30)
            
            if response.status_code == 200:
                self.stats['scrapingbee_credits_used'] += 1
                html = response.text
                
                # Parse Google search results
                soup = BeautifulSoup(html, 'html.parser')
                
                # Look for official website in search results
                # Google often shows the official site in the first few results
                links = soup.find_all('a', href=True)
                
                for link in links:
                    href = link.get('href', '')
                    # Skip Google's own links
                    if 'google.com' in href or '/search?' in href:
                        continue
                    
                    # Extract actual URL from Google's redirect
                    if '/url?q=' in href:
                        import urllib.parse
                        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                        if 'q' in parsed:
                            url = parsed['q'][0]
                            # Check if it looks like a brand website
                            if self.is_likely_brand_website(url, brand_name):
                                print(f"    ✅ Found via ScrapingBee: {url}")
                                return url
                
                # Also check for direct domain mentions in text
                brand_slug = self.create_brand_slug(brand_name)
                patterns = [
                    f"{brand_slug}.com",
                    f"{brand_slug}petfood.com",
                    f"{brand_slug}.co.uk",
                    f"{brand_slug}-pets.com"
                ]
                
                for pattern in patterns:
                    if pattern in html.lower():
                        url = f"https://www.{pattern}"
                        if self.verify_website(url, brand_name):
                            print(f"    ✅ Found domain in results: {url}")
                            return url
                            
        except Exception as e:
            print(f"    ⚠️ ScrapingBee error: {e}")
        
        return None
    
    def try_domain_patterns(self, brand_name: str) -> Optional[str]:
        """Try common domain patterns for the brand"""
        brand_slug = self.create_brand_slug(brand_name)
        brand_clean = brand_name.lower().replace(' ', '').replace('-', '').replace('&', 'and')
        
        patterns = [
            # Primary patterns
            f"https://www.{brand_slug}.com",
            f"https://www.{brand_clean}.com",
            f"https://{brand_slug}.com",
            f"https://{brand_clean}.com",
            
            # Pet food specific
            f"https://www.{brand_slug}petfood.com",
            f"https://www.{brand_slug}-petfood.com",
            f"https://www.{brand_slug}dogfood.com",
            f"https://www.{brand_slug}-dogfood.com",
            f"https://www.{brand_slug}pets.com",
            f"https://www.{brand_slug}-pets.com",
            
            # Regional variants
            f"https://www.{brand_slug}.co.uk",
            f"https://www.{brand_slug}.de",
            f"https://www.{brand_slug}.eu",
            f"https://www.{brand_slug}.fr",
            f"https://www.{brand_slug}.es",
            f"https://www.{brand_slug}.it",
            
            # Alternative formats
            f"https://www.{brand_slug}pet.com",
            f"https://www.{brand_slug}food.com",
            f"https://www.{brand_slug}nutrition.com",
        ]
        
        print(f"  🔗 Trying domain patterns for: {brand_name}")
        
        for url in patterns:
            if self.verify_website(url, brand_name):
                print(f"    ✅ Found via pattern: {url}")
                return url
        
        return None
    
    def verify_website(self, url: str, brand_name: str = None, timeout: int = 5) -> bool:
        """Verify if a URL is accessible and likely a brand website"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; BrandDiscoveryBot/1.0)'
            }
            
            # First check if domain exists
            response = requests.head(url, headers=headers, timeout=timeout, allow_redirects=True)
            
            # Check if we get a successful response
            if response.status_code not in [200, 301, 302, 303, 307, 308]:
                return False
            
            # For redirects, check the final URL
            if response.status_code in [301, 302, 303, 307, 308] and 'location' in response.headers:
                final_url = response.headers['location']
                # Make sure we're not redirected to a generic page
                if any(site in final_url for site in ['facebook.com', 'instagram.com', 'godaddy.com', 'squarespace.com']):
                    return False
            
            # For very generic brand names, do a content check
            if brand_name and len(brand_name) <= 4:  # Short names like "Ava", "Able"
                try:
                    # Fetch actual content to verify it's pet-related
                    content_response = requests.get(url, headers=headers, timeout=timeout)
                    if content_response.status_code == 200:
                        content_lower = content_response.text.lower()
                        # Check for pet food keywords
                        pet_keywords = ['dog food', 'pet food', 'dog nutrition', 'pet nutrition', 
                                      'puppy', 'canine', 'pet products', 'animal feed']
                        if not any(keyword in content_lower for keyword in pet_keywords):
                            return False
                except:
                    # If we can't verify content, be conservative
                    return False
            
            return True
                
        except (requests.RequestException, Exception):
            pass
        
        return False
    
    def is_likely_brand_website(self, url: str, brand_name: str) -> bool:
        """Check if URL is likely the official brand website"""
        if not url:
            return False
        
        # Skip social media and marketplaces
        skip_domains = [
            'facebook.com', 'instagram.com', 'twitter.com', 'youtube.com',
            'amazon.com', 'amazon.co.uk', 'chewy.com', 'petco.com', 'petsmart.com',
            'walmart.com', 'target.com', 'ebay.com', 'wikipedia.org'
        ]
        
        parsed = urlparse(url.lower())
        domain = parsed.netloc
        
        # Skip if it's a known marketplace or social media
        for skip in skip_domains:
            if skip in domain:
                return False
        
        # Check if brand name is in domain
        brand_clean = brand_name.lower().replace(' ', '').replace('-', '').replace('&', 'and')
        if brand_clean in domain:
            return True
        
        # Check for common pet food domains
        pet_keywords = ['pet', 'dog', 'food', 'nutrition', 'feed']
        if any(keyword in domain for keyword in pet_keywords):
            # Verify it's accessible
            return self.verify_website(url, brand_name)
        
        return False
    
    def use_duckduckgo_instant(self, brand_name: str) -> Optional[str]:
        """Use DuckDuckGo Instant Answer API (free, no auth needed)"""
        try:
            query = f"{brand_name} dog food official website"
            url = f"https://api.duckduckgo.com/?q={quote(query)}&format=json&no_html=1"
            
            print(f"  🦆 Searching DuckDuckGo for: {brand_name}")
            
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Check Abstract URL (often contains official website)
                if data.get('AbstractURL'):
                    url = data['AbstractURL']
                    if self.is_likely_brand_website(url, brand_name):
                        print(f"    ✅ Found via DuckDuckGo: {url}")
                        return url
                
                # Check related topics
                for topic in data.get('RelatedTopics', []):
                    if isinstance(topic, dict) and topic.get('FirstURL'):
                        url = topic['FirstURL']
                        if self.is_likely_brand_website(url, brand_name):
                            print(f"    ✅ Found via DuckDuckGo: {url}")
                            return url
                            
        except Exception as e:
            print(f"    ⚠️ DuckDuckGo error: {e}")
        
        return None
    
    def check_robots_txt(self, website_url: str) -> Dict:
        """Check robots.txt for crawl permissions"""
        robots_info = {
            'can_crawl': True,
            'crawl_delay': 1.0,
            'disallow': []
        }
        
        try:
            parsed = urlparse(website_url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            
            response = requests.get(robots_url, timeout=5)
            if response.status_code == 200:
                content = response.text
                
                # Simple robots.txt parsing
                for line in content.split('\n'):
                    line = line.strip()
                    if line.lower().startswith('crawl-delay:'):
                        delay = line.split(':')[1].strip()
                        try:
                            robots_info['crawl_delay'] = float(delay)
                        except:
                            pass
                    elif line.lower().startswith('disallow:'):
                        path = line.split(':')[1].strip()
                        if path == '/':
                            robots_info['can_crawl'] = False
                        robots_info['disallow'].append(path)
                        
        except:
            pass
        
        return robots_info
    
    def discover_brand_website(self, brand_name: str) -> Dict:
        """Main method to discover a brand's website using multiple strategies"""
        brand_slug = self.create_brand_slug(brand_name)
        
        # Check if we already have this brand
        if brand_slug in self.existing_sites:
            print(f"⏭️ Skipping {brand_name} - already processed")
            return self.existing_sites[brand_slug]
        
        print(f"\n🔎 Processing: {brand_name}")
        
        result = {
            'brand_name': brand_name,
            'website_url': None,
            'website_status': 'unknown',
            'discovery_method': None,
            'confidence_score': 0.0,
            'has_website': False,
            'robots': {'can_crawl': False, 'crawl_delay': 1.0},
            'validation': {
                'dns_valid': False,
                'ssl_valid': False,
                'content_valid': False,
                'last_checked': datetime.now().isoformat()
            },
            'notes': ''
        }
        
        # Strategy 1: Try domain patterns (fastest, free)
        website = self.try_domain_patterns(brand_name)
        if website:
            result['website_url'] = website
            result['discovery_method'] = 'pattern'
            result['confidence_score'] = 0.9
        
        # Strategy 2: DuckDuckGo Instant Answer (free)
        if not website:
            website = self.use_duckduckgo_instant(brand_name)
            if website:
                result['website_url'] = website
                result['discovery_method'] = 'duckduckgo'
                result['confidence_score'] = 0.8
        
        # Strategy 3: ScrapingBee Google Search (costs credits but most effective)
        if not website:
            website = self.search_with_scrapingbee(brand_name)
            if website:
                result['website_url'] = website
                result['discovery_method'] = 'scrapingbee'
                result['confidence_score'] = 0.95
        
        # If we found a website, verify and get additional info
        if website:
            result['has_website'] = True
            result['website_status'] = 'active'
            
            # Check robots.txt
            robots_info = self.check_robots_txt(website)
            result['robots'] = robots_info
            
            # Parse domain info
            parsed = urlparse(website)
            result['domain'] = parsed.netloc
            
            # Detect country from TLD
            tld = parsed.netloc.split('.')[-1]
            country_map = {
                'com': 'US', 'co.uk': 'UK', 'de': 'DE', 'fr': 'FR',
                'es': 'ES', 'it': 'IT', 'ca': 'CA', 'au': 'AU'
            }
            result['country'] = country_map.get(tld, 'US')
            
            # Validation
            result['validation']['dns_valid'] = True
            result['validation']['ssl_valid'] = website.startswith('https')
            result['validation']['content_valid'] = True
            
            self.stats['websites_found'] += 1
            self.stats['websites_verified'] += 1
            
            # Track discovery method
            method = result['discovery_method']
            self.stats['discovery_methods'][method] = self.stats['discovery_methods'].get(method, 0) + 1
            
            print(f"  ✅ Website found: {website}")
            print(f"     Method: {result['discovery_method']}")
            print(f"     Confidence: {result['confidence_score']}")
            print(f"     Can crawl: {result['robots']['can_crawl']}")
        else:
            result['website_status'] = 'not_found'
            result['notes'] = 'No website found after trying all strategies'
            print(f"  ❌ No website found for {brand_name}")
        
        self.stats['total_processed'] += 1
        
        return result
    
    def process_all_brands(self):
        """Process all 278 brands to find their websites"""
        print("="*80)
        print("ENHANCED BRAND WEBSITE DISCOVERY")
        print("="*80)
        
        # Load all brands
        all_brands = self.load_all_brands()
        print(f"📚 Loaded {len(all_brands)} brands from ALL-BRANDS.md")
        
        # Initialize results
        results = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_brands': len(all_brands),
                'brands_with_websites': 0,
                'brands_crawlable': 0,
                'scrapingbee_credits_used': 0,
                'discovery_methods': {}
            },
            'brands': {}
        }
        
        # Add existing sites to results
        results['brands'].update(self.existing_sites)
        
        # Process each brand
        brands_to_process = []
        for brand in all_brands:
            brand_slug = self.create_brand_slug(brand)
            if brand_slug not in self.existing_sites:
                brands_to_process.append(brand)
        
        print(f"📊 Already mapped: {len(self.existing_sites)} brands")
        print(f"🎯 Need to process: {len(brands_to_process)} brands")
        
        if not brands_to_process:
            print("✅ All brands already mapped!")
            return
        
        print("\n" + "="*80)
        print("STARTING DISCOVERY")
        print("="*80)
        
        # Process in batches to monitor progress
        batch_size = 10
        for i in range(0, len(brands_to_process), batch_size):
            batch = brands_to_process[i:i+batch_size]
            
            print(f"\n📦 Processing batch {i//batch_size + 1} ({i+1}-{min(i+batch_size, len(brands_to_process))} of {len(brands_to_process)})")
            print("-"*40)
            
            for brand in batch:
                brand_slug = self.create_brand_slug(brand)
                brand_data = self.discover_brand_website(brand)
                results['brands'][brand_slug] = brand_data
                
                # Rate limiting
                time.sleep(1)
            
            # Update metadata
            results['metadata']['brands_with_websites'] = sum(
                1 for b in results['brands'].values() if b.get('has_website')
            )
            results['metadata']['brands_crawlable'] = sum(
                1 for b in results['brands'].values() 
                if b.get('has_website') and b.get('robots', {}).get('can_crawl', False)
            )
            results['metadata']['scrapingbee_credits_used'] = self.stats['scrapingbee_credits_used']
            results['metadata']['discovery_methods'] = self.stats['discovery_methods']
            
            # Save progress after each batch
            with open(self.output_file, 'w') as f:
                yaml.dump(results, f, default_flow_style=False, sort_keys=False)
            
            print(f"\n💾 Progress saved to {self.output_file}")
            print(f"📊 Stats: {results['metadata']['brands_with_websites']}/{len(all_brands)} with websites")
            print(f"💳 ScrapingBee credits used: {self.stats['scrapingbee_credits_used']}")
        
        # Final report
        print("\n" + "="*80)
        print("DISCOVERY COMPLETE")
        print("="*80)
        print(f"✅ Total brands processed: {self.stats['total_processed']}")
        print(f"🌐 Websites found: {self.stats['websites_found']}")
        print(f"✓ Websites verified: {self.stats['websites_verified']}")
        print(f"💳 ScrapingBee credits used: {self.stats['scrapingbee_credits_used']}")
        print(f"💰 Estimated cost: ${self.stats['scrapingbee_credits_used'] * 0.001:.2f}")
        
        print("\n📈 Discovery methods used:")
        for method, count in self.stats['discovery_methods'].items():
            print(f"  - {method}: {count} brands")
        
        print(f"\n📁 Results saved to: {self.output_file}")
        
        # Calculate coverage
        coverage = (results['metadata']['brands_with_websites'] / len(all_brands)) * 100
        print(f"\n🎯 COVERAGE: {coverage:.1f}% ({results['metadata']['brands_with_websites']}/{len(all_brands)} brands)")

def main():
    """Main execution"""
    discovery = EnhancedBrandWebsiteDiscovery()
    
    print("\n" + "="*80)
    print("OPTIONS:")
    print("="*80)
    print("1. Process ALL remaining brands (recommended)")
    print("2. Process a test batch (5 brands)")
    print("3. Process specific brand")
    print("="*80)
    
    choice = input("\nSelect option (1-3): ").strip()
    
    if choice == '1':
        discovery.process_all_brands()
    elif choice == '2':
        # Test with 5 brands
        all_brands = discovery.load_all_brands()
        test_brands = []
        for brand in all_brands[:20]:  # Check first 20 for unmapped ones
            brand_slug = discovery.create_brand_slug(brand)
            if brand_slug not in discovery.existing_sites:
                test_brands.append(brand)
            if len(test_brands) >= 5:
                break
        
        print(f"\n🧪 Testing with {len(test_brands)} brands:")
        for brand in test_brands:
            print(f"  - {brand}")
        
        results = {}
        for brand in test_brands:
            brand_slug = discovery.create_brand_slug(brand)
            brand_data = discovery.discover_brand_website(brand)
            results[brand_slug] = brand_data
            time.sleep(1)
        
        print("\n📊 Test Results:")
        for slug, data in results.items():
            if data['has_website']:
                print(f"  ✅ {data['brand_name']}: {data['website_url']}")
            else:
                print(f"  ❌ {data['brand_name']}: Not found")
        
        print(f"\n💳 ScrapingBee credits used: {discovery.stats['scrapingbee_credits_used']}")
        
    elif choice == '3':
        brand_name = input("Enter brand name: ").strip()
        if brand_name:
            result = discovery.discover_brand_website(brand_name)
            print("\n📋 Result:")
            print(yaml.dump({discovery.create_brand_slug(brand_name): result}, default_flow_style=False))
    else:
        print("Invalid option")

if __name__ == "__main__":
    main()