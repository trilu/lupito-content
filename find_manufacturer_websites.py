#!/usr/bin/env python3
"""
Find manufacturer websites by checking multiple sources
"""

import os
import time
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime
import logging
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ManufacturerWebsiteFinder:
    def __init__(self):
        self.report_dir = Path("reports/MANUF")
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
        # Headers for web requests
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Load brand priority data
        self.brands_df = pd.read_csv(self.report_dir / "MANUF_BRAND_PRIORITY.csv")
        
    def search_duckduckgo(self, brand_name):
        """Search DuckDuckGo for brand website - DISABLED for speed"""
        # Skip DuckDuckGo for now to avoid timeouts
        return None
    
    def search_google_programmatic(self, brand_name):
        """Try common URL patterns for the brand"""
        common_patterns = [
            f"https://www.{brand_name.lower()}.com",
            f"https://www.{brand_name.lower()}.co.uk",
            f"https://www.{brand_name.lower()}-petfood.com",
            f"https://www.{brand_name.lower()}petfood.com",
            f"https://www.{brand_name.lower().replace(' ', '')}.com",
            f"https://www.{brand_name.lower().replace('-', '')}.com",
        ]
        
        for url in common_patterns:
            try:
                response = requests.head(url, headers=self.headers, timeout=3, allow_redirects=True)
                if response.status_code == 200:
                    # Check if it's actually a pet food site
                    full_response = requests.get(url, headers=self.headers, timeout=5)
                    content = full_response.text.lower()
                    if any(word in content for word in ['dog', 'pet', 'food', 'nutrition']):
                        return url
            except:
                continue
        
        return None
    
    def verify_website(self, url):
        """Verify that a website is accessible and relevant"""
        try:
            response = requests.get(url, headers=self.headers, timeout=5)
            if response.status_code == 200:
                content = response.text.lower()
                # Check for pet/dog food indicators
                pet_indicators = ['dog food', 'pet food', 'dog nutrition', 'canine', 'puppy']
                if any(indicator in content for indicator in pet_indicators):
                    return True
        except:
            pass
        
        return False
    
    def find_websites(self):
        """Find websites for top brands"""
        results = []
        
        # Focus on top 30 brands
        top_brands = self.brands_df.head(30)
        
        for _, row in top_brands.iterrows():
            brand = row['brand']
            brand_slug = row['brand_slug']
            
            logger.info(f"Searching for {brand} website...")
            
            # Skip if we already have a website
            if pd.notna(row.get('website_url')):
                results.append({
                    'brand': brand,
                    'brand_slug': brand_slug,
                    'website_url': row['website_url'],
                    'source': 'existing',
                    'verified': True
                })
                continue
            
            # Source 1: Try common patterns
            url1 = self.search_google_programmatic(brand_slug)
            
            # Source 2: Skip DuckDuckGo for speed
            url2 = None
            
            # Determine final URL
            final_url = None
            source = None
            
            if url1 and url2:
                # Both sources found something - verify both
                if url1 == url2:
                    final_url = url1
                    source = 'both'
                elif self.verify_website(url1):
                    final_url = url1
                    source = 'pattern'
                elif self.verify_website(url2):
                    final_url = url2
                    source = 'search'
            elif url1:
                if self.verify_website(url1):
                    final_url = url1
                    source = 'pattern'
            elif url2:
                if self.verify_website(url2):
                    final_url = url2
                    source = 'search'
            
            # Manual mappings for known brands
            if not final_url:
                manual_mappings = {
                    'brit': 'https://www.brit-petfood.com',
                    'alpha': 'https://www.alphapetfoods.com',
                    'bozita': 'https://www.bozita.com',
                    'belcando': 'https://www.belcando.de',
                    'arden': 'https://www.ardengrange.com',
                    'barking': 'https://www.barkingheads.co.uk',
                    'briantos': 'https://www.briantos.de',
                    'bosch': 'https://www.bosch-tiernahrung.de',
                    'acana': 'https://www.acana.com',
                    'advance': 'https://www.advance-pet.com',
                    'affinity': 'https://www.affinity.com',
                    'bakers': 'https://www.bakerspetfood.co.uk',
                    'burns': 'https://burnspet.co.uk',
                    'eukanuba': 'https://www.eukanuba.com',
                    'hills': 'https://www.hillspet.com',
                    'iams': 'https://www.iams.com',
                    'pedigree': 'https://www.pedigree.com',
                    'purina': 'https://www.purina.co.uk',
                    'royal-canin': 'https://www.royalcanin.com',
                    'whiskas': 'https://www.whiskas.co.uk'
                }
                
                if brand_slug in manual_mappings:
                    final_url = manual_mappings[brand_slug]
                    source = 'manual'
            
            results.append({
                'brand': brand,
                'brand_slug': brand_slug,
                'website_url': final_url,
                'source': source,
                'verified': final_url is not None
            })
            
            logger.info(f"  Found: {final_url} (source: {source})")
        
        # Create results DataFrame
        results_df = pd.DataFrame(results)
        
        # Save results
        output_file = self.report_dir / "MANUFACTURER_WEBSITES.csv"
        results_df.to_csv(output_file, index=False)
        
        # Generate report
        report = f"""# MANUFACTURER WEBSITE DISCOVERY REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary
- Brands Checked: {len(results_df)}
- Websites Found: {results_df['verified'].sum()}
- Success Rate: {results_df['verified'].sum() / len(results_df) * 100:.1f}%

## Discovery Sources
- Both Sources Agree: {(results_df['source'] == 'both').sum()}
- Pattern Match Only: {(results_df['source'] == 'pattern').sum()}
- Search Only: {(results_df['source'] == 'search').sum()}
- Manual Mapping: {(results_df['source'] == 'manual').sum()}
- Existing: {(results_df['source'] == 'existing').sum()}
- Not Found: {(~results_df['verified']).sum()}

## Verified Websites

| Brand | Website | Source |
|-------|---------|--------|
"""
        
        for _, row in results_df[results_df['verified']].iterrows():
            report += f"| {row['brand']} | {row['website_url']} | {row['source']} |\n"
        
        report += f"""

## Brands Without Websites

| Brand | Slug |
|-------|------|
"""
        
        for _, row in results_df[~results_df['verified']].iterrows():
            report += f"| {row['brand']} | {row['brand_slug']} |\n"
        
        report += """

## Next Steps
1. Create profiles for brands with verified websites
2. Manually research brands without websites
3. Consider reaching out to manufacturers directly
4. Check parent company websites for brand information
"""
        
        report_file = self.report_dir / "MANUFACTURER_WEBSITES.md"
        with open(report_file, "w") as f:
            f.write(report)
        
        print(report)
        
        return results_df

if __name__ == "__main__":
    finder = ManufacturerWebsiteFinder()
    finder.find_websites()