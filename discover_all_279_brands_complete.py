#!/usr/bin/env python3
"""
Discover websites for ALL 279 brands from ALL-BRANDS.md
Complete brand website discovery including all known brands
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

class UltimateBrandDiscovery:
    def __init__(self):
        # Supabase connection
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase = create_client(url, key)
        
        # Paths
        self.all_brands_file = Path("docs/ALL-BRANDS.md")
        self.output_yaml = Path("data/brand_sites.yaml")
        self.output_csv = Path("reports/MANUF/ALL_279_BRAND_WEBSITES.csv")
        self.output_csv.parent.mkdir(parents=True, exist_ok=True)
        
        # User agent
        self.user_agent = "Lupito-Content-Bot/1.0"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Load all brand names from ALL-BRANDS.md
        self.all_brand_names = self.load_all_brands_list()
        
        # Load existing mappings
        self.existing_mappings = self.load_existing_mappings()
    
    def load_all_brands_list(self):
        """Load the complete list of 279 brands from ALL-BRANDS.md"""
        brands = []
        if self.all_brands_file.exists():
            with open(self.all_brands_file, 'r') as f:
                for line in f:
                    brand = line.strip()
                    if brand and not brand.startswith('#'):
                        brands.append(brand)
        print(f"Loaded {len(brands)} brands from ALL-BRANDS.md")
        return brands
    
    def load_existing_mappings(self):
        """Load existing website mappings from all sources"""
        mappings = {}
        
        # Check all existing CSVs
        csv_files = [
            "reports/MANUF/MANUFACTURER_WEBSITES.csv",
            "reports/MANUF/ALL_BRAND_WEBSITES.csv",
            "reports/MANUF/ALL_175_BRAND_WEBSITES.csv"
        ]
        
        for csv_file in csv_files:
            if Path(csv_file).exists():
                df = pd.read_csv(csv_file)
                for _, row in df.iterrows():
                    if pd.notna(row.get('website_url')):
                        # Try both brand_slug and brand name
                        if 'brand_slug' in row:
                            mappings[row['brand_slug']] = row['website_url']
                        if 'brand' in row:
                            slug = self.brand_to_slug(row['brand'])
                            mappings[slug] = row['website_url']
        
        # Load from existing YAML
        if self.output_yaml.exists():
            with open(self.output_yaml, 'r') as f:
                data = yaml.safe_load(f)
                if data and 'brands' in data:
                    for slug, info in data['brands'].items():
                        if info.get('website_url'):
                            mappings[slug] = info['website_url']
        
        print(f"Loaded {len(mappings)} existing website mappings")
        return mappings
    
    def brand_to_slug(self, brand_name):
        """Convert brand name to slug format"""
        return re.sub(r'[^a-z0-9]+', '_', brand_name.lower()).strip('_')
    
    def get_brand_stats_from_db(self):
        """Get product counts and stats for brands from database"""
        stats = {}
        
        tables = ['foods_canonical', 'foods_published', 'foods_union_all', 'foods_published_preview']
        
        for table in tables:
            try:
                response = self.supabase.table(table).select("*").execute()
                
                if response.data:
                    df = pd.DataFrame(response.data)
                    
                    for _, row in df.iterrows():
                        brand = row.get('brand', '')
                        brand_slug = row.get('brand_slug', '')
                        
                        # Use brand_slug if available, otherwise generate from brand name
                        if not brand_slug and brand:
                            brand_slug = self.brand_to_slug(brand)
                        
                        if not brand_slug:
                            continue
                        
                        if brand_slug not in stats:
                            stats[brand_slug] = {
                                'product_count': 0,
                                'form_count': 0,
                                'life_stage_count': 0,
                                'kcal_count': 0,
                                'ingredients_count': 0,
                                'price_count': 0,
                                'sources': set()
                            }
                        
                        stats[brand_slug]['product_count'] += 1
                        stats[brand_slug]['sources'].add(table)
                        
                        # Count completeness
                        if pd.notna(row.get('form')):
                            stats[brand_slug]['form_count'] += 1
                        if pd.notna(row.get('life_stage')):
                            stats[brand_slug]['life_stage_count'] += 1
                        if pd.notna(row.get('kcal_per_100g')):
                            stats[brand_slug]['kcal_count'] += 1
                        if pd.notna(row.get('ingredients_tokens')):
                            stats[brand_slug]['ingredients_count'] += 1
                        if pd.notna(row.get('price_per_kg')) or pd.notna(row.get('price_per_kg_eur')):
                            stats[brand_slug]['price_count'] += 1
            
            except Exception as e:
                print(f"Error reading {table}: {str(e)[:100]}")
        
        return stats
    
    def try_website_discovery(self, brand_name, brand_slug):
        """Try to discover website for a brand"""
        # Clean names
        clean_name = re.sub(r'[^a-z0-9]', '', brand_name.lower())
        slug_clean = re.sub(r'[^a-z0-9]', '', brand_slug.replace('_', ''))
        slug_hyphen = brand_slug.replace('_', '-')
        
        # Known brand websites (expanded list)
        known_websites = {
            'royal_canin': 'https://www.royalcanin.com',
            'hills_prescription_diet': 'https://www.hillspet.com',
            'hills_science_plan': 'https://www.hillspet.com',
            'purina': 'https://www.purina.co.uk',
            'pro_plan': 'https://www.purina-proplan.co.uk',
            'taste_of_the_wild': 'https://www.tasteofthewild.com',
            'iams': 'https://www.iams.com',
            'eukanuba': 'https://www.eukanuba.com',
            'pedigree': 'https://www.pedigree.com',
            'cesar': 'https://www.cesar.com',
            'whiskas': 'https://www.whiskas.co.uk',
            'james_wellbeloved': 'https://www.wellpet.com',
            'wellness': 'https://www.wellnesspetfood.com',
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
            'webbox': 'https://www.webbox.co.uk',
            'wagg': 'https://www.waggfoods.com',
            'bakers': 'https://www.bakerscomplete.com',
            'butchers': 'https://www.butcherspetcare.com',
            'forthglade': 'https://www.forthglade.com',
            'naturediet': 'https://www.naturediet.co.uk',
            'natures_harvest': 'https://www.naturesharvestpetfood.co.uk',
            'skinners': 'https://www.skinnerspetfoods.co.uk',
            'barking_heads': 'https://www.barkingheads.co.uk',
            'pooch_mutt': 'https://www.poochandmutt.com',
            'scrumbles': 'https://www.scrumbles.co.uk',
            'edgard_cooper': 'https://www.edgardcooper.com',
            'tails_com': 'https://tails.com',
            'butternut_box': 'https://butternutbox.com',
            'different_dog': 'https://www.differentdog.com',
            'pure_pet_food': 'https://www.purepetfood.com',
            'bella_duke': 'https://www.bellaandduke.com',
            'akela': 'https://www.akelaspetfood.co.uk',
            'millies_wolfheart': 'https://www.millieswolfheart.co.uk',
            'eden': 'https://www.edenpetfoods.com',
            'orijen': 'https://www.orijen.ca',
            'acana': 'https://www.acana.com',
            'carnilove': 'https://www.carnilove.cz',
            'canidae': 'https://www.canidae.com',
            'merrick': 'https://www.merrickpetcare.com',
            'nutro': 'https://www.nutro.com',
            'natural_balance': 'https://www.naturalbalanceinc.com',
            'blue_buffalo': 'https://www.bluebuffalo.com',
            'fromm': 'https://www.frommfamily.com',
            'victor': 'https://www.victorpetfood.com',
            'diamond': 'https://www.diamondpet.com',
            'solid_gold': 'https://www.solidgoldpet.com',
            'earthborn': 'https://www.earthbornholisticpetfood.com',
            'zignature': 'https://www.zignature.com',
            'nulo': 'https://www.nulo.com',
            'instinct': 'https://www.instinctpetfood.com',
            'go': 'https://www.petcurean.com',
            'now': 'https://www.petcurean.com',
            'gather': 'https://www.petcurean.com',
            'farmina': 'https://www.farmina.com',
            'brit': 'https://www.brit-petfood.com',
            'happy_dog': 'https://www.happydog.de',
            'josera': 'https://www.josera.de',
            'wolfsblut': 'https://www.wolfsblut.com',
            'bosch': 'https://www.bosch-tiernahrung.de',
            'belcando': 'https://www.belcando.de',
            'animonda': 'https://www.animonda.de',
            'select_gold': 'https://www.selectgold.de',
            'rinti': 'https://www.rinti.de',
            'macs': 'https://www.macs-tiernahrung.de',
            'yarrah': 'https://www.yarrah.com',
            'almo_nature': 'https://www.almonature.com',
            'schesir': 'https://www.schesir.com',
            'lily_s_kitchen': 'https://www.lilyskitchen.co.uk',
            'greenies': 'https://www.greenies.com',
            'dentastix': 'https://www.pedigree.com',
            'dreambone': 'https://www.dreambone.com',
            'rachael_ray': 'https://www.rachaelray.com',
            'beneful': 'https://www.beneful.com',
            'alpo': 'https://www.alpo.com',
            'kibbles_n_bits': 'https://www.kibblesnbits.com',
            'gravy_train': 'https://www.gravytrain.com',
            'ol_roy': 'https://www.walmart.com',
            'purina_one': 'https://www.purina.com/one',
            'fancy_feast': 'https://www.purina.com/fancy-feast',
            'friskies': 'https://www.purina.com/friskies',
            'kit_kat': 'https://www.purina.com/kit-kat',
            'tesco': 'https://www.tesco.com',
            'sainsburys': 'https://www.sainsburys.co.uk',
            'asda': 'https://www.asda.com',
            'morrisons': 'https://www.morrisons.com',
            'waitrose': 'https://www.waitrose.com',
            'aldi': 'https://www.aldi.co.uk',
            'lidl': 'https://www.lidl.co.uk',
            'pets_at_home': 'https://www.petsathome.com',
            'zooplus': 'https://www.zooplus.co.uk',
            'amazon': 'https://www.amazon.co.uk',
            'chewy': 'https://www.chewy.com',
            'petco': 'https://www.petco.com',
            'petsmart': 'https://www.petsmart.com'
        }
        
        # Check known websites first
        if brand_slug in known_websites:
            return known_websites[brand_slug], 'known_website'
        
        # Try URL patterns
        patterns = [
            f"https://www.{clean_name}.com",
            f"https://www.{clean_name}.co.uk",
            f"https://www.{clean_name}.de",
            f"https://www.{clean_name}.fr",
            f"https://www.{slug_clean}.com",
            f"https://www.{slug_clean}.co.uk",
            f"https://www.{slug_hyphen}.com",
            f"https://www.{slug_hyphen}.co.uk",
            f"https://www.{clean_name}petfood.com",
            f"https://www.{clean_name}-petfood.com",
            f"https://www.{clean_name}pet.com",
            f"https://www.{clean_name}pets.com",
            f"https://www.{clean_name}dogfood.com",
            f"https://www.{slug_hyphen}-pet-food.com",
            f"https://{clean_name}.com",
            f"https://www.{clean_name}nutrition.com"
        ]
        
        for url in patterns[:5]:  # Limit attempts to avoid too many requests
            try:
                response = requests.head(url, headers=self.headers, timeout=1, allow_redirects=True)
                if response.status_code == 200:
                    return response.url if hasattr(response, 'url') else url, 'pattern_match'
            except:
                continue
        
        return None, None
    
    def check_robots_compliance(self, website_url):
        """Quick robots.txt check"""
        try:
            rp = RobotFileParser()
            robots_url = urlparse(website_url).scheme + "://" + urlparse(website_url).netloc + "/robots.txt"
            rp.set_url(robots_url)
            rp.read()
            
            can_fetch = rp.can_fetch(self.user_agent, website_url)
            crawl_delay = rp.crawl_delay(self.user_agent) or 1.0
            
            return {
                'can_crawl': can_fetch,
                'crawl_delay': float(crawl_delay)
            }
        except:
            return {
                'can_crawl': True,
                'crawl_delay': 2.0
            }
    
    def discover_all_279_brands(self):
        """Discover websites for all 279 brands"""
        print("="*70)
        print("ULTIMATE BRAND WEBSITE DISCOVERY (279 BRANDS)")
        print("="*70)
        
        # Get stats from database
        db_stats = self.get_brand_stats_from_db()
        print(f"Found {len(db_stats)} brands with products in database")
        
        # Process all 279 brands
        all_brand_data = []
        discovered_count = 0
        existing_count = 0
        no_website_count = 0
        
        print(f"\nProcessing {len(self.all_brand_names)} brands...")
        print("-"*70)
        
        for idx, brand_name in enumerate(self.all_brand_names):
            brand_slug = self.brand_to_slug(brand_name)
            
            # Show progress every 20 brands
            if idx % 20 == 0 and idx > 0:
                print(f"\nProgress: {idx}/{len(self.all_brand_names)} brands processed...")
            
            # Get stats if available
            stats = db_stats.get(brand_slug, {})
            product_count = stats.get('product_count', 0)
            
            # Calculate completion if we have products
            if product_count > 0:
                form_pct = (stats['form_count'] / product_count * 100) if product_count else 0
                life_pct = (stats['life_stage_count'] / product_count * 100) if product_count else 0
                kcal_pct = (stats['kcal_count'] / product_count * 100) if product_count else 0
                ing_pct = (stats['ingredients_count'] / product_count * 100) if product_count else 0
                price_pct = (stats['price_count'] / product_count * 100) if product_count else 0
                overall_completion = (form_pct + life_pct + kcal_pct + ing_pct + price_pct) / 5
                impact_score = product_count * (100 - overall_completion)
            else:
                overall_completion = 0
                impact_score = 0
            
            brand_data = {
                'brand': brand_name,
                'brand_slug': brand_slug,
                'product_count': product_count,
                'in_database': product_count > 0,
                'sources': ', '.join(sorted(stats.get('sources', set()))),
                'overall_completion': overall_completion,
                'impact_score': impact_score,
                'website_url': None,
                'has_website': False,
                'discovery_source': None,
                'can_crawl': False,
                'crawl_delay': 2.0
            }
            
            # Check for existing mapping
            if brand_slug in self.existing_mappings:
                brand_data['website_url'] = self.existing_mappings[brand_slug]
                brand_data['has_website'] = True
                brand_data['discovery_source'] = 'existing'
                existing_count += 1
            else:
                # Try to discover
                url, source = self.try_website_discovery(brand_name, brand_slug)
                
                if url:
                    brand_data['website_url'] = url
                    brand_data['has_website'] = True
                    brand_data['discovery_source'] = source
                    discovered_count += 1
                    if product_count > 5:  # Only show significant brands
                        print(f"  ✓ {brand_name}: {url}")
                else:
                    no_website_count += 1
                    if product_count > 10:  # Show missing websites for significant brands
                        print(f"  ✗ {brand_name}: No website found ({product_count} products)")
            
            # Check robots if we have a website
            if brand_data['website_url']:
                robots = self.check_robots_compliance(brand_data['website_url'])
                brand_data['can_crawl'] = robots['can_crawl']
                brand_data['crawl_delay'] = robots['crawl_delay']
            
            all_brand_data.append(brand_data)
            
            # Rate limit
            if idx % 10 == 0:
                time.sleep(0.2)
        
        # Create DataFrame and sort by impact
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
        print(f"Brands in database: {result_df['in_database'].sum()}")
        print(f"Brands with websites: {result_df['has_website'].sum()}")
        print(f"  - From existing mappings: {existing_count}")
        print(f"  - Newly discovered: {discovered_count}")
        print(f"Brands without websites: {no_website_count}")
        print(f"Crawlable websites: {result_df['can_crawl'].sum()}")
        
        # Top 20 by impact (with products)
        print("\n" + "="*70)
        print("TOP 20 BRANDS BY IMPACT SCORE (IN DATABASE)")
        print("="*70)
        print(f"{'Rank':<5} {'Brand':<25} {'SKUs':<6} {'Compl%':<8} {'Impact':<8} {'Website':<8} {'Crawl'}")
        print("-"*75)
        
        top_20 = result_df[result_df['in_database']].head(20)
        for rank, (_, row) in enumerate(top_20.iterrows(), 1):
            website = '✓' if row['has_website'] else '✗'
            crawl = '✓' if row['can_crawl'] else '✗'
            brand_display = row['brand'][:25]
            print(f"{rank:<5} {brand_display:<25} {row['product_count']:<6} "
                  f"{row['overall_completion']:<8.1f} {row['impact_score']:<8.0f} "
                  f"{website:<8} {crawl}")
        
        # Brands not in database but have websites
        not_in_db = result_df[~result_df['in_database'] & result_df['has_website']]
        if len(not_in_db) > 0:
            print("\n" + "="*70)
            print(f"BRANDS WITH WEBSITES NOT IN DATABASE ({len(not_in_db)} brands)")
            print("="*70)
            for _, row in not_in_db.head(10).iterrows():
                print(f"  - {row['brand']}: {row['website_url']}")
        
        return result_df
    
    def create_yaml_file(self, df):
        """Create comprehensive brand_sites.yaml"""
        brand_sites = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_brands': len(df),
                'brands_in_database': df['in_database'].sum(),
                'brands_with_websites': df['has_website'].sum(),
                'brands_crawlable': df['can_crawl'].sum(),
                'user_agent': self.user_agent,
                'source': 'Complete catalog from ALL-BRANDS.md (279 brands)'
            },
            'brands': {}
        }
        
        for _, row in df.iterrows():
            notes = []
            
            # Determine notes
            if row['impact_score'] > 1000:
                notes.append('high_impact')
            elif row['impact_score'] > 500:
                notes.append('medium_impact')
            elif row['in_database'] and row['impact_score'] > 0:
                notes.append('low_impact')
            
            if not row['in_database']:
                notes.append('not_in_database')
            
            if row['has_website']:
                if row['can_crawl']:
                    notes.append('ready_to_crawl')
                else:
                    notes.append('blocked_by_robots')
            else:
                notes.append('no_website')
            
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
                    'in_database': row['in_database'],
                    'product_count': int(row['product_count']),
                    'completion_pct': float(row['overall_completion']),
                    'impact_score': float(row['impact_score']),
                    'sources': row['sources'] if row['sources'] else 'none'
                },
                'notes': ', '.join(notes)
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
        elif '.cz' in domain:
            return 'CZ'
        elif '.ca' in domain:
            return 'CA'
        elif '.com' in domain:
            return 'US'
        else:
            return 'INT'

def main():
    discoverer = UltimateBrandDiscovery()
    results = discoverer.discover_all_279_brands()
    
    print("\n✅ Ultimate brand website discovery complete!")
    print(f"   All 279 brands processed")
    print(f"   Results saved to:")
    print(f"   - {discoverer.output_csv}")
    print(f"   - {discoverer.output_yaml}")
    
    # Create MANUF_SOURCES.md report
    report_path = Path("reports/MANUF/MANUF_SOURCES.md")
    with open(report_path, 'w') as f:
        f.write(f"# MANUFACTURER SOURCES REPORT\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n\n")
        f.write(f"## Summary\n")
        f.write(f"- Total brands: 279 (from ALL-BRANDS.md)\n")
        f.write(f"- Brands with websites: {results['has_website'].sum()}\n")
        f.write(f"- Brands crawlable: {results['can_crawl'].sum()}\n")
        f.write(f"- Brands in database: {results['in_database'].sum()}\n\n")
        f.write(f"## Files Generated\n")
        f.write(f"- `data/brand_sites.yaml` - Complete brand website mapping\n")
        f.write(f"- `reports/MANUF/ALL_279_BRAND_WEBSITES.csv` - Detailed CSV with all data\n")
    
    print(f"   - {report_path}")

if __name__ == "__main__":
    main()