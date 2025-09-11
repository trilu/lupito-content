#!/usr/bin/env python3
"""
Discover websites for ALL 200+ brands in the database
Expand beyond the initial 70 to cover the full catalog
"""

import os
import yaml
import pandas as pd
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
import requests
import time
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv
import re

load_dotenv()

class ComprehensiveBrandWebsiteDiscovery:
    def __init__(self):
        # Supabase connection
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase = create_client(url, key)
        
        # Paths
        self.existing_websites = Path("reports/MANUF/MANUFACTURER_WEBSITES.csv")
        self.output_yaml = Path("data/brand_sites.yaml")
        self.output_csv = Path("reports/MANUF/ALL_BRAND_WEBSITES.csv")
        
        # User agent
        self.user_agent = "Lupito-Content-Bot/1.0"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Load existing mappings if available
        self.existing_mappings = {}
        if self.existing_websites.exists():
            df = pd.read_csv(self.existing_websites)
            for _, row in df.iterrows():
                if pd.notna(row.get('website_url')):
                    self.existing_mappings[row['brand_slug']] = row['website_url']
    
    def get_all_brands_from_db(self):
        """Get ALL unique brands from the database"""
        print("Fetching all brands from database...")
        
        try:
            # Get all unique brands with product counts and completion stats
            response = self.supabase.table('foods_canonical').select(
                "brand,brand_slug,form,life_stage,kcal_per_100g,ingredients_tokens,price_per_kg"
            ).execute()
            
            if not response.data:
                return pd.DataFrame()
            
            df = pd.DataFrame(response.data)
            
            # Group by brand to get stats
            brand_stats = []
            for brand_slug in df['brand_slug'].unique():
                if not brand_slug:
                    continue
                
                brand_df = df[df['brand_slug'] == brand_slug]
                brand_name = brand_df['brand'].iloc[0] if not brand_df.empty else brand_slug
                total = len(brand_df)
                
                # Calculate completion percentages
                form_pct = (brand_df['form'].notna().sum() / total * 100) if total > 0 else 0
                life_pct = (brand_df['life_stage'].notna().sum() / total * 100) if total > 0 else 0
                kcal_pct = (brand_df['kcal_per_100g'].notna().sum() / total * 100) if total > 0 else 0
                ing_pct = (brand_df['ingredients_tokens'].notna().sum() / total * 100) if total > 0 else 0
                price_pct = (brand_df['price_per_kg'].notna().sum() / total * 100) if total > 0 else 0
                
                overall_completion = (form_pct + life_pct + kcal_pct + ing_pct + price_pct) / 5
                impact_score = total * (100 - overall_completion)
                
                brand_stats.append({
                    'brand': brand_name,
                    'brand_slug': brand_slug,
                    'product_count': total,
                    'form_coverage': form_pct,
                    'life_stage_coverage': life_pct,
                    'kcal_coverage': kcal_pct,
                    'ingredients_coverage': ing_pct,
                    'price_coverage': price_pct,
                    'overall_completion': overall_completion,
                    'impact_score': impact_score
                })
            
            brands_df = pd.DataFrame(brand_stats)
            brands_df = brands_df.sort_values('impact_score', ascending=False)
            
            print(f"Found {len(brands_df)} unique brands in database")
            return brands_df
            
        except Exception as e:
            print(f"Error fetching brands: {e}")
            return pd.DataFrame()
    
    def try_common_patterns(self, brand_name, brand_slug):
        """Try common URL patterns to find brand website"""
        # Clean brand name for URL
        clean_name = re.sub(r'[^a-z0-9]', '', brand_name.lower())
        slug_clean = re.sub(r'[^a-z0-9]', '', brand_slug.replace('_', ''))
        
        patterns = [
            # Direct brand URLs
            f"https://www.{clean_name}.com",
            f"https://www.{clean_name}.co.uk",
            f"https://www.{clean_name}.de",
            f"https://www.{clean_name}.fr",
            f"https://www.{slug_clean}.com",
            f"https://www.{slug_clean}.co.uk",
            
            # Pet food specific
            f"https://www.{clean_name}petfood.com",
            f"https://www.{clean_name}-petfood.com",
            f"https://www.{clean_name}pet.com",
            f"https://www.{slug_clean}petfood.com",
            
            # Variations
            f"https://{clean_name}.com",
            f"https://www.{clean_name}nutrition.com",
            f"https://www.{clean_name}pets.com",
            
            # Hyphenated versions
            f"https://www.{brand_slug.replace('_', '-')}.com",
            f"https://www.{brand_slug.replace('_', '-')}.co.uk",
        ]
        
        # Add special cases for known patterns
        if 'royal' in clean_name and 'canin' in clean_name:
            patterns.insert(0, "https://www.royalcanin.com")
        if 'hill' in clean_name:
            patterns.insert(0, "https://www.hillspet.com")
            patterns.insert(1, "https://www.hillspet.co.uk")
        if 'purina' in clean_name:
            patterns.insert(0, "https://www.purina.co.uk")
            patterns.insert(1, "https://www.purina.com")
        if 'taste' in clean_name and 'wild' in clean_name:
            patterns.insert(0, "https://www.tasteofthewild.com")
        
        for url in patterns:
            try:
                response = requests.head(url, headers=self.headers, timeout=3, allow_redirects=True)
                if response.status_code == 200:
                    # Verify it's actually a pet/dog food site
                    final_url = response.url if hasattr(response, 'url') else url
                    return final_url, 'pattern_match'
            except:
                continue
        
        return None, None
    
    def check_robots_compliance(self, website_url):
        """Check if we can crawl this website"""
        try:
            rp = RobotFileParser()
            robots_url = urlparse(website_url).scheme + "://" + urlparse(website_url).netloc + "/robots.txt"
            rp.set_url(robots_url)
            rp.read()
            
            can_fetch = rp.can_fetch(self.user_agent, website_url)
            crawl_delay = rp.crawl_delay(self.user_agent) or 1.0
            
            return {
                'can_crawl': can_fetch,
                'crawl_delay': float(crawl_delay),
                'robots_url': robots_url
            }
        except:
            return {
                'can_crawl': True,
                'crawl_delay': 2.0,
                'robots_url': None
            }
    
    def discover_all_websites(self):
        """Discover websites for all brands"""
        print("="*70)
        print("COMPREHENSIVE BRAND WEBSITE DISCOVERY")
        print("="*70)
        
        # Get all brands from database
        brands_df = self.get_all_brands_from_db()
        
        if brands_df.empty:
            print("No brands found in database")
            return
        
        # Process each brand
        all_brand_data = []
        discovered_count = 0
        existing_count = 0
        
        print(f"\nProcessing {len(brands_df)} brands...")
        print("-"*70)
        
        for idx, row in brands_df.iterrows():
            brand_slug = row['brand_slug']
            brand_name = row['brand']
            
            brand_data = {
                'brand': brand_name,
                'brand_slug': brand_slug,
                'product_count': row['product_count'],
                'overall_completion': row['overall_completion'],
                'impact_score': row['impact_score'],
                'website_url': None,
                'has_website': False,
                'source': None,
                'can_crawl': False,
                'crawl_delay': 2.0
            }
            
            # Check if we already have a website
            if brand_slug in self.existing_mappings:
                brand_data['website_url'] = self.existing_mappings[brand_slug]
                brand_data['has_website'] = True
                brand_data['source'] = 'existing'
                existing_count += 1
            else:
                # Try to discover website
                print(f"  Discovering website for {brand_slug}...")
                url, source = self.try_common_patterns(brand_name, brand_slug)
                
                if url:
                    brand_data['website_url'] = url
                    brand_data['has_website'] = True
                    brand_data['source'] = source
                    discovered_count += 1
                    print(f"    ✓ Found: {url}")
                else:
                    print(f"    ✗ No website found")
            
            # Check robots.txt if we have a website
            if brand_data['website_url']:
                robots = self.check_robots_compliance(brand_data['website_url'])
                brand_data['can_crawl'] = robots['can_crawl']
                brand_data['crawl_delay'] = robots['crawl_delay']
            
            all_brand_data.append(brand_data)
            
            # Be polite between discovery attempts
            if idx % 10 == 0 and idx > 0:
                print(f"\n  Progress: {idx}/{len(brands_df)} brands processed...")
                time.sleep(1)
        
        # Create DataFrame with all brand data
        result_df = pd.DataFrame(all_brand_data)
        
        # Save to CSV
        self.output_csv.parent.mkdir(parents=True, exist_ok=True)
        result_df.to_csv(self.output_csv, index=False)
        
        # Create YAML file
        self.create_yaml_file(result_df)
        
        # Print summary
        print("\n" + "="*70)
        print("DISCOVERY SUMMARY")
        print("="*70)
        print(f"Total brands processed: {len(result_df)}")
        print(f"Brands with websites: {result_df['has_website'].sum()}")
        print(f"  - Existing mappings used: {existing_count}")
        print(f"  - Newly discovered: {discovered_count}")
        print(f"Brands without websites: {(~result_df['has_website']).sum()}")
        print(f"Crawlable websites: {result_df['can_crawl'].sum()}")
        
        # Show top 20 by impact score
        print("\n" + "="*70)
        print("TOP 20 BRANDS BY IMPACT SCORE")
        print("="*70)
        print(f"{'Rank':<5} {'Brand':<25} {'SKUs':<8} {'Complete%':<12} {'Impact':<10} {'Website':<8} {'Crawl'}")
        print("-"*85)
        
        top_20 = result_df.nlargest(20, 'impact_score')
        for rank, (_, row) in enumerate(top_20.iterrows(), 1):
            website = '✓' if row['has_website'] else '✗'
            crawl = '✓' if row['can_crawl'] else '✗'
            print(f"{rank:<5} {row['brand_slug']:<25} {row['product_count']:<8} "
                  f"{row['overall_completion']:<12.1f} {row['impact_score']:<10.0f} "
                  f"{website:<8} {crawl}")
        
        return result_df
    
    def create_yaml_file(self, df):
        """Create brand_sites.yaml file"""
        brand_sites = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_brands': len(df),
                'brands_with_websites': df['has_website'].sum(),
                'brands_crawlable': df['can_crawl'].sum(),
                'user_agent': self.user_agent
            },
            'brands': {}
        }
        
        # Sort by impact score
        df_sorted = df.sort_values('impact_score', ascending=False)
        
        for _, row in df_sorted.iterrows():
            brand_sites['brands'][row['brand_slug']] = {
                'brand_name': row['brand'],
                'website_url': row['website_url'] if row['has_website'] else None,
                'domain': urlparse(row['website_url']).netloc if row['website_url'] else None,
                'country': self.guess_country(row['website_url']) if row['website_url'] else 'UNKNOWN',
                'has_website': row['has_website'],
                'robots': {
                    'can_crawl': row['can_crawl'],
                    'crawl_delay': row['crawl_delay']
                },
                'stats': {
                    'product_count': int(row['product_count']),
                    'completion_pct': float(row['overall_completion']),
                    'impact_score': float(row['impact_score'])
                },
                'notes': self.generate_notes(row)
            }
        
        # Save YAML
        self.output_yaml.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_yaml, 'w') as f:
            yaml.dump(brand_sites, f, default_flow_style=False, sort_keys=False)
        
        print(f"\n✅ Created {self.output_yaml}")
    
    def guess_country(self, url):
        """Guess country from URL"""
        if not url:
            return 'UNKNOWN'
        domain = urlparse(url).netloc.lower()
        if '.co.uk' in domain or '.uk' in domain:
            return 'UK'
        elif '.de' in domain:
            return 'DE'
        elif '.fr' in domain:
            return 'FR'
        elif '.es' in domain:
            return 'ES'
        elif '.it' in domain:
            return 'IT'
        elif '.com' in domain:
            return 'US'
        else:
            return 'INT'
    
    def generate_notes(self, row):
        """Generate notes for a brand"""
        notes = []
        
        if row['impact_score'] > 1000:
            notes.append('high_impact')
        elif row['impact_score'] > 500:
            notes.append('medium_impact')
        else:
            notes.append('low_impact')
        
        if row['has_website']:
            if row['can_crawl']:
                notes.append('ready_to_crawl')
            else:
                notes.append('blocked_by_robots')
        else:
            notes.append('needs_website_discovery')
        
        if row['overall_completion'] < 30:
            notes.append('very_low_completion')
        elif row['overall_completion'] < 60:
            notes.append('low_completion')
        
        return ', '.join(notes)

def main():
    discoverer = ComprehensiveBrandWebsiteDiscovery()
    results = discoverer.discover_all_websites()
    
    print("\n✅ Website discovery complete!")
    print(f"   Results saved to:")
    print(f"   - {discoverer.output_csv}")
    print(f"   - {discoverer.output_yaml}")

if __name__ == "__main__":
    main()