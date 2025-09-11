#!/usr/bin/env python3
"""
Enhanced Brand Discovery with Google Custom Search API
Completes the remaining brands using Google's powerful search
"""

import os
import yaml
import json
import time
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()

class GoogleSearchBrandDiscovery:
    def __init__(self):
        # Google Custom Search configuration
        self.google_api_key = None
        self.google_cse_id = None
        
        # Try to get from environment first
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        self.google_cse_id = os.getenv('GOOGLE_CSE_ID')
        
        # If not in env, we'll need to set them up
        if not self.google_api_key:
            print("⚠️ GOOGLE_API_KEY not found in .env")
            print("Please add it or we'll use gcloud auth")
        
        if not self.google_cse_id:
            print("⚠️ GOOGLE_CSE_ID not found in .env")
            print("You can create one at: https://programmablesearchengine.google.com/")
        
        # ScrapingBee as fallback
        self.scrapingbee_api_key = os.getenv('SCRAPING_BEE')
        
        # File paths
        self.all_brands_file = Path("docs/ALL-BRANDS.md")
        self.existing_results = Path("data/brand_sites_final.yaml")
        self.output_file = Path("data/brand_sites_google.yaml")
        
        # Load existing results
        self.results = self.load_existing_results()
        
        # Statistics
        self.stats = {
            'google_searches': 0,
            'new_websites_found': 0,
            'scrapingbee_fallbacks': 0
        }
        
        print(f"✅ Google API configured: {'Yes' if self.google_api_key else 'Needs setup'}")
        print(f"✅ ScrapingBee fallback: {'Yes' if self.scrapingbee_api_key else 'No'}")
        print(f"📊 Existing brands: {len(self.results['brands'])} already processed")
    
    def setup_google_api(self):
        """Set up Google Custom Search API"""
        print("\n" + "="*60)
        print("GOOGLE CUSTOM SEARCH API SETUP")
        print("="*60)
        
        if not self.google_api_key:
            print("\nTo use Google Custom Search, you need:")
            print("1. API Key from Google Cloud Console")
            print("2. Custom Search Engine ID")
            
            # Try to get from gcloud
            try:
                import subprocess
                # Get the API key from gcloud
                print("\nTrying to get API key from gcloud...")
                
                # First, ensure APIs are enabled
                project_id = "careful-drummer-468512-p0"
                
                print(f"Using project: {project_id}")
                
                # Create an API key if needed
                api_key = input("\nEnter your Google API Key (or press Enter to skip): ").strip()
                if api_key:
                    self.google_api_key = api_key
                    # Save to .env for future use
                    with open('.env', 'a') as f:
                        f.write(f"\nGOOGLE_API_KEY={api_key}\n")
                    print("✅ API Key saved to .env")
                
            except Exception as e:
                print(f"Could not set up automatically: {e}")
        
        if not self.google_cse_id:
            print("\nFor Custom Search Engine ID:")
            print("1. Go to: https://programmablesearchengine.google.com/")
            print("2. Create a new search engine")
            print("3. Set it to 'Search the entire web'")
            print("4. Copy the Search Engine ID")
            
            cse_id = input("\nEnter your Custom Search Engine ID (or press Enter to skip): ").strip()
            if cse_id:
                self.google_cse_id = cse_id
                # Save to .env
                with open('.env', 'a') as f:
                    f.write(f"GOOGLE_CSE_ID={cse_id}\n")
                print("✅ CSE ID saved to .env")
        
        return bool(self.google_api_key and self.google_cse_id)
    
    def load_existing_results(self) -> Dict:
        """Load existing results"""
        if self.existing_results.exists():
            try:
                with open(self.existing_results, 'r') as f:
                    return yaml.unsafe_load(f)
            except:
                pass
        
        return {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_brands': 0,
                'brands_with_websites': 0,
                'google_searches_used': 0
            },
            'brands': {}
        }
    
    def load_all_brands(self) -> List[str]:
        """Load all brands from ALL-BRANDS.md"""
        brands = []
        if self.all_brands_file.exists():
            with open(self.all_brands_file, 'r') as f:
                for line in f:
                    brand = line.strip()
                    if brand and not brand.startswith('#'):
                        brands.append(brand)
        return brands
    
    def create_brand_slug(self, brand_name: str) -> str:
        """Create consistent brand slug"""
        return brand_name.lower().replace(' ', '_').replace('-', '_').replace('&', 'and').replace('.', '').replace("'", '')
    
    def google_search(self, brand_name: str) -> Optional[str]:
        """Search for brand website using Google Custom Search API"""
        if not self.google_api_key or not self.google_cse_id:
            return None
        
        try:
            # Build the service
            service = build("customsearch", "v1", developerKey=self.google_api_key)
            
            # Search query
            query = f'"{brand_name}" dog food official website'
            
            print(f"  🔍 Google searching: {query}")
            
            # Execute search
            result = service.cse().list(
                q=query,
                cx=self.google_cse_id,
                num=5  # Get top 5 results
            ).execute()
            
            self.stats['google_searches'] += 1
            
            if 'items' in result:
                for item in result['items']:
                    link = item.get('link', '')
                    display_link = item.get('displayLink', '').lower()
                    title = item.get('title', '').lower()
                    snippet = item.get('snippet', '').lower()
                    
                    # Skip social media and marketplaces
                    skip_domains = ['facebook', 'instagram', 'amazon', 'chewy', 'wikipedia', 'youtube']
                    if any(skip in display_link for skip in skip_domains):
                        continue
                    
                    # Check if it looks like the brand's website
                    brand_clean = brand_name.lower().replace(' ', '').replace('-', '')
                    
                    # Strong indicators it's the right site
                    if (brand_clean in display_link or 
                        'official' in title or 
                        'official' in snippet or
                        ('dog food' in snippet and brand_clean in snippet)):
                        
                        # Clean up the URL
                        if not link.startswith('http'):
                            link = 'https://' + link
                        
                        print(f"    ✅ Found via Google: {link}")
                        return link
            
        except HttpError as e:
            print(f"    ⚠️ Google API error: {e}")
        except Exception as e:
            print(f"    ⚠️ Error: {e}")
        
        return None
    
    def scrapingbee_search(self, brand_name: str) -> Optional[str]:
        """Fallback to ScrapingBee if Google API fails"""
        if not self.scrapingbee_api_key:
            return None
        
        print(f"  🐝 Trying ScrapingBee fallback...")
        
        query = f'"{brand_name}" dog food official website'
        search_url = f"https://www.google.com/search?q={requests.utils.quote(query)}"
        
        params = {
            'api_key': self.scrapingbee_api_key,
            'url': search_url,
            'render_js': 'false',
            'premium_proxy': 'false',
        }
        
        try:
            response = requests.get('https://app.scrapingbee.com/api/v1/', params=params, timeout=30)
            
            if response.status_code == 200:
                self.stats['scrapingbee_fallbacks'] += 1
                # Simple extraction from HTML
                text = response.text.lower()
                brand_slug = self.create_brand_slug(brand_name)
                
                # Look for domain patterns in the response
                patterns = [f"{brand_slug}.com", f"{brand_slug}.co.uk", f"{brand_slug}petfood.com"]
                
                for pattern in patterns:
                    if pattern in text:
                        url = f"https://www.{pattern}"
                        print(f"    ✅ Found via ScrapingBee: {url}")
                        return url
        except:
            pass
        
        return None
    
    def process_brand(self, brand_name: str) -> Dict:
        """Process a single brand"""
        brand_slug = self.create_brand_slug(brand_name)
        
        # Skip if already processed
        if brand_slug in self.results['brands']:
            if self.results['brands'][brand_slug].get('has_website'):
                return self.results['brands'][brand_slug]
        
        print(f"\n🔎 Processing: {brand_name}")
        
        result = {
            'brand_name': brand_name,
            'website_url': None,
            'discovery_method': None,
            'has_website': False,
            'confidence_score': 0.0
        }
        
        # Try Google Custom Search first
        if self.google_api_key and self.google_cse_id:
            website = self.google_search(brand_name)
            if website:
                result['website_url'] = website
                result['discovery_method'] = 'google_search'
                result['has_website'] = True
                result['confidence_score'] = 0.95
                self.stats['new_websites_found'] += 1
                return result
        
        # Fallback to ScrapingBee
        website = self.scrapingbee_search(brand_name)
        if website:
            result['website_url'] = website
            result['discovery_method'] = 'scrapingbee'
            result['has_website'] = True
            result['confidence_score'] = 0.85
            self.stats['new_websites_found'] += 1
            return result
        
        print(f"  ❌ No website found")
        return result
    
    def complete_discovery(self):
        """Complete the brand discovery using Google Search"""
        print("\n" + "="*60)
        print("GOOGLE-POWERED BRAND DISCOVERY")
        print("="*60)
        
        # Set up Google API if needed
        if not self.google_api_key or not self.google_cse_id:
            if not self.setup_google_api():
                print("\n⚠️ Google API not configured. Using ScrapingBee only.")
        
        # Load all brands
        all_brands = self.load_all_brands()
        print(f"\n📚 Total brands: {len(all_brands)}")
        
        # Find brands without websites
        brands_without_sites = []
        for brand in all_brands:
            brand_slug = self.create_brand_slug(brand)
            if brand_slug not in self.results['brands'] or not self.results['brands'][brand_slug].get('has_website'):
                brands_without_sites.append(brand)
        
        print(f"🎯 Brands without websites: {len(brands_without_sites)}")
        
        if not brands_without_sites:
            print("✅ All brands have websites!")
            return
        
        print(f"\nProcessing {len(brands_without_sites)} brands...")
        print("-"*40)
        
        # Process each brand
        for i, brand in enumerate(brands_without_sites, 1):
            if i % 10 == 0:
                print(f"\n📊 Progress: {i}/{len(brands_without_sites)}")
                print(f"💡 New websites found: {self.stats['new_websites_found']}")
            
            brand_slug = self.create_brand_slug(brand)
            brand_data = self.process_brand(brand)
            self.results['brands'][brand_slug] = brand_data
            
            # Rate limiting
            time.sleep(1)
            
            # Save progress every 10 brands
            if i % 10 == 0:
                self.save_results()
        
        # Final save
        self.save_results()
        self.generate_report()
    
    def save_results(self):
        """Save current results"""
        # Update metadata
        self.results['metadata']['total_brands'] = len(self.results['brands'])
        self.results['metadata']['brands_with_websites'] = sum(
            1 for b in self.results['brands'].values() if b.get('has_website')
        )
        self.results['metadata']['google_searches_used'] = self.stats['google_searches']
        self.results['metadata']['last_updated'] = datetime.now().isoformat()
        
        # Save to file
        with open(self.output_file, 'w') as f:
            yaml.dump(self.results, f, default_flow_style=False, sort_keys=False)
    
    def generate_report(self):
        """Generate final report"""
        print("\n" + "="*60)
        print("GOOGLE SEARCH DISCOVERY COMPLETE")
        print("="*60)
        
        total = len(self.results['brands'])
        with_sites = sum(1 for b in self.results['brands'].values() if b.get('has_website'))
        
        print(f"\n📊 Final Results:")
        print(f"  Total brands: {total}")
        print(f"  Websites found: {with_sites} ({with_sites/total*100:.1f}%)")
        print(f"  New websites this session: {self.stats['new_websites_found']}")
        
        print(f"\n🔍 API Usage:")
        print(f"  Google searches: {self.stats['google_searches']}")
        print(f"  ScrapingBee fallbacks: {self.stats['scrapingbee_fallbacks']}")
        
        print(f"\n💰 Estimated Costs:")
        # Google gives 100 free searches per day
        google_cost = max(0, (self.stats['google_searches'] - 100) * 0.005)
        scrapingbee_cost = self.stats['scrapingbee_fallbacks'] * 0.001
        print(f"  Google API: ${google_cost:.2f} (first 100/day free)")
        print(f"  ScrapingBee: ${scrapingbee_cost:.2f}")
        print(f"  Total: ${(google_cost + scrapingbee_cost):.2f}")
        
        print(f"\n📁 Results saved to: {self.output_file}")

def main():
    """Main execution"""
    discovery = GoogleSearchBrandDiscovery()
    discovery.complete_discovery()

if __name__ == "__main__":
    main()