#!/usr/bin/env python3
"""
Discover websites for ALL 175+ brands across all tables
Including brands from foods_union_all that aren't in canonical yet
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

class CompleteBrandDiscovery:
    def __init__(self):
        # Supabase connection
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase = create_client(url, key)
        
        # Paths
        self.output_yaml = Path("data/brand_sites.yaml")
        self.output_csv = Path("reports/MANUF/ALL_175_BRAND_WEBSITES.csv")
        self.output_csv.parent.mkdir(parents=True, exist_ok=True)
        
        # User agent
        self.user_agent = "Lupito-Content-Bot/1.0"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Load existing mappings
        self.existing_mappings = self.load_existing_mappings()
    
    def load_existing_mappings(self):
        """Load any existing website mappings"""
        mappings = {}
        
        # Check existing CSV files
        csv_files = [
            "reports/MANUF/MANUFACTURER_WEBSITES.csv",
            "reports/MANUF/ALL_BRAND_WEBSITES.csv"
        ]
        
        for csv_file in csv_files:
            if Path(csv_file).exists():
                df = pd.read_csv(csv_file)
                for _, row in df.iterrows():
                    if pd.notna(row.get('website_url')):
                        slug = row.get('brand_slug', row.get('brand', '').lower().replace(' ', '_'))
                        mappings[slug] = row['website_url']
        
        # Also check if brand_sites.yaml exists
        if self.output_yaml.exists():
            with open(self.output_yaml, 'r') as f:
                data = yaml.safe_load(f)
                if data and 'brands' in data:
                    for slug, info in data['brands'].items():
                        if info.get('website_url'):
                            mappings[slug] = info['website_url']
        
        return mappings
    
    def get_all_brands_comprehensive(self):
        """Get ALL unique brands from ALL tables"""
        print("Fetching all brands from all tables...")
        
        all_brands_data = {}
        
        # Tables to check
        tables = ['foods_canonical', 'foods_published', 'foods_union_all', 'foods_published_preview']
        
        for table in tables:
            print(f"  Checking {table}...")
            try:
                # Get all data from table
                response = self.supabase.table(table).select("*").execute()
                
                if response.data:
                    df = pd.DataFrame(response.data)
                    
                    # Process each row
                    for _, row in df.iterrows():
                        # Get brand info
                        brand = row.get('brand', '')
                        brand_slug = row.get('brand_slug', '')
                        
                        # Generate slug if missing
                        if not brand_slug and brand:
                            brand_slug = re.sub(r'[^a-z0-9]+', '_', brand.lower()).strip('_')
                        
                        if not brand_slug:
                            continue
                        
                        # Initialize or update brand data
                        if brand_slug not in all_brands_data:
                            all_brands_data[brand_slug] = {
                                'brand': brand or brand_slug,
                                'brand_slug': brand_slug,
                                'product_count': 0,
                                'sources': set(),
                                'form_count': 0,
                                'life_stage_count': 0,
                                'kcal_count': 0,
                                'ingredients_count': 0,
                                'price_count': 0
                            }
                        
                        # Update counts
                        all_brands_data[brand_slug]['product_count'] += 1
                        all_brands_data[brand_slug]['sources'].add(table)
                        
                        # Count field completeness
                        if pd.notna(row.get('form')):
                            all_brands_data[brand_slug]['form_count'] += 1
                        if pd.notna(row.get('life_stage')):
                            all_brands_data[brand_slug]['life_stage_count'] += 1
                        if pd.notna(row.get('kcal_per_100g')):
                            all_brands_data[brand_slug]['kcal_count'] += 1
                        if pd.notna(row.get('ingredients_tokens')):
                            all_brands_data[brand_slug]['ingredients_count'] += 1
                        if pd.notna(row.get('price_per_kg')) or pd.notna(row.get('price_per_kg_eur')):
                            all_brands_data[brand_slug]['price_count'] += 1
                    
                    print(f"    Found {len(df['brand_slug'].dropna().unique())} unique brands")
            
            except Exception as e:
                print(f"    Error: {str(e)[:100]}")
        
        # Calculate completion percentages and impact scores
        brands_list = []
        for brand_slug, data in all_brands_data.items():
            total = data['product_count']
            
            # Calculate coverage percentages
            form_pct = (data['form_count'] / total * 100) if total > 0 else 0
            life_pct = (data['life_stage_count'] / total * 100) if total > 0 else 0
            kcal_pct = (data['kcal_count'] / total * 100) if total > 0 else 0
            ing_pct = (data['ingredients_count'] / total * 100) if total > 0 else 0
            price_pct = (data['price_count'] / total * 100) if total > 0 else 0
            
            overall_completion = (form_pct + life_pct + kcal_pct + ing_pct + price_pct) / 5
            impact_score = total * (100 - overall_completion)
            
            brands_list.append({
                'brand': data['brand'],
                'brand_slug': brand_slug,
                'product_count': total,
                'sources': ', '.join(sorted(data['sources'])),
                'form_coverage': form_pct,
                'life_stage_coverage': life_pct,
                'kcal_coverage': kcal_pct,
                'ingredients_coverage': ing_pct,
                'price_coverage': price_pct,
                'overall_completion': overall_completion,
                'impact_score': impact_score
            })
        
        brands_df = pd.DataFrame(brands_list)
        brands_df = brands_df.sort_values('impact_score', ascending=False)
        
        print(f"\nTotal unique brands found: {len(brands_df)}")
        return brands_df
    
    def try_website_patterns(self, brand_name, brand_slug):
        """Try various URL patterns to find brand website"""
        # Clean names for URLs
        clean_name = re.sub(r'[^a-z0-9]', '', brand_name.lower())
        slug_clean = re.sub(r'[^a-z0-9]', '', brand_slug.replace('_', ''))
        slug_hyphen = brand_slug.replace('_', '-')
        
        # Common pet food brand parent companies
        parent_companies = {
            'royal_canin': 'https://www.royalcanin.com',
            'royal_canin_veterinary': 'https://www.royalcanin.com',
            'hills': 'https://www.hillspet.com',
            'hill_s': 'https://www.hillspet.com',
            'purina': 'https://www.purina.co.uk',
            'purina_one': 'https://www.purina.co.uk',
            'purina_pro_plan': 'https://www.purina.co.uk',
            'taste_of_the_wild': 'https://www.tasteofthewild.com',
            'iams': 'https://www.iams.com',
            'eukanuba': 'https://www.eukanuba.com',
            'pedigree': 'https://www.pedigree.com',
            'whiskas': 'https://www.whiskas.co.uk',
            'cesar': 'https://www.cesar.com',
            'sheba': 'https://www.sheba.com',
            'nutro': 'https://www.nutro.com',
            'greenies': 'https://www.greenies.com',
            'james_wellbeloved': 'https://www.wellpet.com',
            'wellness': 'https://www.wellnesspetfood.com',
            'lily_s_kitchen': 'https://www.lilyskitchen.co.uk',
            'lilys_kitchen': 'https://www.lilyskitchen.co.uk',
            'natures_menu': 'https://www.naturesmenu.co.uk',
            'burns': 'https://www.burnspet.co.uk',
            'arden_grange': 'https://www.ardengrange.com',
            'symply': 'https://www.symplypetfoods.com',
            'canagan': 'https://www.canagan.com',
            'applaws': 'https://www.applaws.com',
            'encore': 'https://www.encorpetfoods.com',
            'harringtons': 'https://www.harringtonspetfood.com',
            'wainwrights': 'https://www.petsathome.com/shop/en/pets/wainwrights',
            'avx': 'https://www.petsathome.com/shop/en/pets/avx',
            'webbox': 'https://www.webbox.co.uk'
        }
        
        # Check parent companies first
        if brand_slug in parent_companies:
            return parent_companies[brand_slug], 'parent_company'
        
        # Try various patterns
        patterns = [
            # Direct brand URLs
            f"https://www.{clean_name}.com",
            f"https://www.{clean_name}.co.uk",
            f"https://www.{clean_name}.de",
            f"https://www.{clean_name}.fr",
            f"https://www.{slug_clean}.com",
            f"https://www.{slug_clean}.co.uk",
            f"https://www.{slug_hyphen}.com",
            f"https://www.{slug_hyphen}.co.uk",
            
            # Pet food specific
            f"https://www.{clean_name}petfood.com",
            f"https://www.{clean_name}-petfood.com",
            f"https://www.{clean_name}pet.com",
            f"https://www.{clean_name}pets.com",
            f"https://www.{slug_clean}petfood.com",
            f"https://www.{slug_hyphen}-pet-food.com",
            
            # Variations
            f"https://{clean_name}.com",
            f"https://www.{clean_name}nutrition.com",
            f"https://www.{clean_name}dogfood.com",
            f"https://www.{clean_name}-nutrition.com"
        ]
        
        for url in patterns:
            try:
                response = requests.head(url, headers=self.headers, timeout=2, allow_redirects=True)
                if response.status_code == 200:
                    return response.url if hasattr(response, 'url') else url, 'pattern_match'
            except:
                continue
        
        return None, None
    
    def check_robots_compliance(self, website_url):
        """Check robots.txt compliance"""
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
        """Discover websites for all 175+ brands"""
        print("="*70)
        print("COMPLETE BRAND WEBSITE DISCOVERY (175+ BRANDS)")
        print("="*70)
        
        # Get all brands
        brands_df = self.get_all_brands_comprehensive()
        
        if brands_df.empty:
            print("No brands found")
            return
        
        # Process each brand
        all_brand_data = []
        discovered_count = 0
        existing_count = 0
        no_website_count = 0
        
        print(f"\nProcessing {len(brands_df)} brands for website discovery...")
        print("-"*70)
        
        for idx, row in brands_df.iterrows():
            brand_slug = row['brand_slug']
            brand_name = row['brand']
            
            # Show progress
            if idx % 20 == 0:
                print(f"\nProgress: {idx}/{len(brands_df)} brands...")
            
            brand_data = {
                'brand': brand_name,
                'brand_slug': brand_slug,
                'product_count': row['product_count'],
                'sources': row['sources'],
                'overall_completion': row['overall_completion'],
                'impact_score': row['impact_score'],
                'website_url': None,
                'has_website': False,
                'discovery_source': None,
                'can_crawl': False,
                'crawl_delay': 2.0
            }
            
            # Check existing mappings first
            if brand_slug in self.existing_mappings:
                brand_data['website_url'] = self.existing_mappings[brand_slug]
                brand_data['has_website'] = True
                brand_data['discovery_source'] = 'existing'
                existing_count += 1
            else:
                # Try to discover website
                url, source = self.try_website_patterns(brand_name, brand_slug)
                
                if url:
                    brand_data['website_url'] = url
                    brand_data['has_website'] = True
                    brand_data['discovery_source'] = source
                    discovered_count += 1
                    print(f"  ✓ {brand_slug}: {url}")
                else:
                    no_website_count += 1
                    if row['product_count'] > 10:  # Only show brands with significant products
                        print(f"  ✗ {brand_slug}: No website found ({row['product_count']} products)")
            
            # Check robots.txt
            if brand_data['website_url']:
                robots = self.check_robots_compliance(brand_data['website_url'])
                brand_data['can_crawl'] = robots['can_crawl']
                brand_data['crawl_delay'] = robots['crawl_delay']
            
            all_brand_data.append(brand_data)
            
            # Rate limit discovery attempts
            if idx % 10 == 0:
                time.sleep(0.5)
        
        # Create result DataFrame
        result_df = pd.DataFrame(all_brand_data)
        result_df = result_df.sort_values('impact_score', ascending=False)
        
        # Save CSV
        result_df.to_csv(self.output_csv, index=False)
        
        # Create YAML
        self.create_yaml_file(result_df)
        
        # Print summary
        print("\n" + "="*70)
        print("DISCOVERY SUMMARY")
        print("="*70)
        print(f"Total brands processed: {len(result_df)}")
        print(f"Brands with websites: {result_df['has_website'].sum()}")
        print(f"  - From existing mappings: {existing_count}")
        print(f"  - Newly discovered: {discovered_count}")
        print(f"Brands without websites: {no_website_count}")
        print(f"Crawlable websites: {result_df['can_crawl'].sum()}")
        
        # Top 20 by impact
        print("\n" + "="*70)
        print("TOP 20 BRANDS BY IMPACT SCORE")
        print("="*70)
        print(f"{'Rank':<5} {'Brand':<20} {'SKUs':<6} {'Compl%':<8} {'Impact':<8} {'Sources':<20} {'Website':<8} {'Crawl'}")
        print("-"*100)
        
        top_20 = result_df.head(20)
        for rank, (_, row) in enumerate(top_20.iterrows(), 1):
            website = '✓' if row['has_website'] else '✗'
            crawl = '✓' if row['can_crawl'] else '✗'
            sources = row['sources'][:18] + '..' if len(row['sources']) > 20 else row['sources']
            print(f"{rank:<5} {row['brand_slug'][:20]:<20} {row['product_count']:<6} "
                  f"{row['overall_completion']:<8.1f} {row['impact_score']:<8.0f} "
                  f"{sources:<20} {website:<8} {crawl}")
        
        return result_df
    
    def create_yaml_file(self, df):
        """Create comprehensive brand_sites.yaml"""
        brand_sites = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_brands': len(df),
                'brands_with_websites': df['has_website'].sum(),
                'brands_crawlable': df['can_crawl'].sum(),
                'user_agent': self.user_agent,
                'note': 'Complete catalog including all tables (canonical, published, union_all)'
            },
            'brands': {}
        }
        
        for _, row in df.iterrows():
            brand_sites['brands'][row['brand_slug']] = {
                'brand_name': row['brand'],
                'website_url': row['website_url'] if row['has_website'] else None,
                'domain': urlparse(row['website_url']).netloc if row['website_url'] else None,
                'country': self.guess_country(row['website_url']) if row['website_url'] else 'UNKNOWN',
                'has_website': row['has_website'],
                'discovery_source': row.get('discovery_source'),
                'robots': {
                    'can_crawl': row['can_crawl'],
                    'crawl_delay': row['crawl_delay']
                },
                'stats': {
                    'product_count': int(row['product_count']),
                    'completion_pct': float(row['overall_completion']),
                    'impact_score': float(row['impact_score']),
                    'sources': row['sources']
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
        elif '.nl' in domain:
            return 'NL'
        elif '.com' in domain:
            return 'US'
        else:
            return 'INT'
    
    def generate_notes(self, row):
        """Generate notes for a brand"""
        notes = []
        
        # Impact level
        if row['impact_score'] > 1000:
            notes.append('high_impact')
        elif row['impact_score'] > 500:
            notes.append('medium_impact')
        else:
            notes.append('low_impact')
        
        # Website status
        if row['has_website']:
            if row['can_crawl']:
                notes.append('ready_to_crawl')
            else:
                notes.append('blocked_by_robots')
        else:
            notes.append('needs_website_discovery')
        
        # Completion level
        if row['overall_completion'] < 30:
            notes.append('very_low_completion')
        elif row['overall_completion'] < 60:
            notes.append('low_completion')
        elif row['overall_completion'] > 90:
            notes.append('high_completion')
        
        # Source info
        if 'union_all' in row['sources'] and 'canonical' not in row['sources']:
            notes.append('not_in_canonical')
        
        return ', '.join(notes)

def main():
    discoverer = CompleteBrandDiscovery()
    results = discoverer.discover_all_websites()
    
    print("\n✅ Complete brand website discovery finished!")
    print(f"   Results saved to:")
    print(f"   - {discoverer.output_csv}")
    print(f"   - {discoverer.output_yaml}")

if __name__ == "__main__":
    main()