#!/usr/bin/env python3
"""
Find websites for brands that don't have them yet using Google Search and ScrapingBee
"""

import os
import yaml
import time
import requests
from pathlib import Path
from datetime import datetime
from urllib.parse import quote
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

class FindMissingBrandWebsites:
    def __init__(self):
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        self.scrapingbee_api_key = os.getenv('SCRAPING_BEE')
        
        # Load existing results
        self.results_file = Path("data/brand_sites_final.yaml")
        with open(self.results_file, 'r') as f:
            self.data = yaml.unsafe_load(f)
        
        # Output for enhanced results
        self.output_file = Path("data/brand_sites_enhanced.yaml")
        
        self.stats = {
            'brands_without_sites': 0,
            'new_websites_found': 0,
            'scrapingbee_credits': 0
        }
    
    def find_brands_without_websites(self):
        """Get list of brands without websites"""
        missing = []
        for slug, brand_data in self.data['brands'].items():
            if not brand_data.get('has_website'):
                missing.append({
                    'slug': slug,
                    'name': brand_data['brand_name']
                })
        return missing
    
    def search_with_scrapingbee(self, brand_name: str) -> str:
        """Use ScrapingBee to search Google for brand website"""
        query = f'"{brand_name}" dog food official website UK'
        search_url = f"https://www.google.com/search?q={quote(query)}"
        
        params = {
            'api_key': self.scrapingbee_api_key,
            'url': search_url,
            'render_js': 'false',
            'premium_proxy': 'false',
            'country_code': 'gb',  # Focus on UK results
        }
        
        try:
            print(f"    🐝 ScrapingBee searching for: {brand_name}")
            response = requests.get('https://app.scrapingbee.com/api/v1/', params=params, timeout=30)
            
            if response.status_code == 200:
                self.stats['scrapingbee_credits'] += 1
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for official website in search results
                for link in soup.find_all('a', href=True):
                    href = link.get('href', '')
                    
                    # Extract URL from Google redirect
                    if '/url?q=' in href:
                        import urllib.parse
                        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                        if 'q' in parsed:
                            url = parsed['q'][0]
                            
                            # Skip social media and marketplaces
                            skip_domains = ['facebook', 'instagram', 'amazon', 'chewy', 'wikipedia', 
                                          'twitter', 'youtube', 'tesco', 'sainsburys', 'asda']
                            domain = urllib.parse.urlparse(url).netloc.lower()
                            
                            if any(skip in domain for skip in skip_domains):
                                continue
                            
                            # Check if it looks pet-related
                            text = link.get_text().lower()
                            parent_text = link.parent.get_text().lower() if link.parent else ""
                            
                            pet_keywords = ['dog food', 'pet food', 'official', brand_name.lower()]
                            if any(keyword in text + parent_text for keyword in pet_keywords):
                                return url
                
                # Try to find domain mentions in snippets
                brand_clean = brand_name.lower().replace(' ', '').replace("'", '').replace('-', '')
                text = soup.get_text().lower()
                
                # Look for domain patterns
                import re
                patterns = [
                    rf"{brand_clean}\.co\.uk",
                    rf"{brand_clean}\.com",
                    rf"{brand_clean}petfood\.com",
                    rf"{brand_clean}-?pets?\.co\.uk"
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, text)
                    if match:
                        domain = match.group()
                        return f"https://www.{domain}"
                        
        except Exception as e:
            print(f"      Error: {e}")
        
        return None
    
    def verify_website(self, url: str) -> bool:
        """Quick check if website is valid"""
        try:
            response = requests.head(url, timeout=5, allow_redirects=True)
            return response.status_code in [200, 301, 302]
        except:
            return False
    
    def process_missing_brands(self):
        """Process brands without websites"""
        missing = self.find_brands_without_websites()
        self.stats['brands_without_sites'] = len(missing)
        
        print(f"📊 Found {len(missing)} brands without websites")
        print("="*60)
        
        # Process each brand
        for i, brand_info in enumerate(missing, 1):
            slug = brand_info['slug']
            name = brand_info['name']
            
            print(f"\n[{i}/{len(missing)}] Searching for: {name}")
            
            # Search with ScrapingBee
            website = self.search_with_scrapingbee(name)
            
            if website:
                # Verify it works
                if self.verify_website(website):
                    print(f"    ✅ Found: {website}")
                    
                    # Update data
                    self.data['brands'][slug]['website_url'] = website
                    self.data['brands'][slug]['has_website'] = True
                    self.data['brands'][slug]['discovery_method'] = 'scrapingbee_google'
                    self.data['brands'][slug]['discovered_at'] = datetime.now().isoformat()
                    
                    self.stats['new_websites_found'] += 1
                else:
                    print(f"    ⚠️ Found but not accessible: {website}")
            else:
                print(f"    ❌ No website found")
            
            # Rate limiting
            time.sleep(1)
            
            # Save progress every 10 brands
            if i % 10 == 0:
                self.save_progress()
                print(f"\n💾 Progress saved: {self.stats['new_websites_found']} new websites found")
        
        # Final save
        self.save_progress()
        self.generate_report()
    
    def save_progress(self):
        """Save current progress"""
        # Update metadata
        self.data['metadata']['brands_with_websites'] = sum(
            1 for b in self.data['brands'].values() if b.get('has_website')
        )
        self.data['metadata']['last_enhanced'] = datetime.now().isoformat()
        self.data['metadata']['scrapingbee_credits_used'] = self.stats['scrapingbee_credits']
        
        # Save to file
        with open(self.output_file, 'w') as f:
            yaml.dump(self.data, f, default_flow_style=False, sort_keys=False)
    
    def generate_report(self):
        """Generate final report"""
        print("\n" + "="*60)
        print("ENHANCED DISCOVERY COMPLETE")
        print("="*60)
        
        total = len(self.data['brands'])
        with_sites = sum(1 for b in self.data['brands'].values() if b.get('has_website'))
        
        print(f"\n📊 Final Results:")
        print(f"  Total brands: {total}")
        print(f"  Brands with websites: {with_sites} ({with_sites/total*100:.1f}%)")
        print(f"  New websites found: {self.stats['new_websites_found']}")
        print(f"  Still missing: {total - with_sites}")
        
        print(f"\n💰 Cost:")
        print(f"  ScrapingBee credits: {self.stats['scrapingbee_credits']}")
        print(f"  Estimated cost: ${self.stats['scrapingbee_credits'] * 0.001:.2f}")
        
        print(f"\n📁 Results saved to: {self.output_file}")
        
        # List some brands still without websites
        still_missing = []
        for slug, brand_data in self.data['brands'].items():
            if not brand_data.get('has_website'):
                still_missing.append(brand_data['brand_name'])
        
        if still_missing:
            print(f"\n❌ Brands still without websites ({len(still_missing)}):")
            for name in still_missing[:20]:
                print(f"  - {name}")
            if len(still_missing) > 20:
                print(f"  ... and {len(still_missing) - 20} more")

def main():
    """Main execution"""
    finder = FindMissingBrandWebsites()
    
    print("="*60)
    print("FIND MISSING BRAND WEBSITES")
    print("="*60)
    print(f"Using ScrapingBee to search Google for missing websites")
    print(f"This will use approximately 1 credit per brand")
    print()
    
    # Ask for confirmation
    missing = finder.find_brands_without_websites()
    print(f"Found {len(missing)} brands without websites")
    print(f"Estimated cost: ${len(missing) * 0.001:.2f}")
    
    response = input("\nProceed? (y/n): ").strip().lower()
    if response == 'y':
        finder.process_missing_brands()
    else:
        print("Cancelled")

if __name__ == "__main__":
    main()