#!/usr/bin/env python3
"""
Start Manufacturer Data Harvesting
Uses discovered websites to harvest product data from top brands
"""

import os
import yaml
import json
import subprocess
import time
from pathlib import Path
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

class ManufacturerHarvester:
    def __init__(self):
        # Supabase connection
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase = create_client(url, key)
        
        # Load brand sites
        self.brand_sites_file = Path("data/brand_sites_final.yaml")
        with open(self.brand_sites_file, 'r') as f:
            self.brand_sites = yaml.unsafe_load(f)
        
        # Directories
        self.profiles_dir = Path("profiles/brands")
        self.harvests_dir = Path("reports/MANUF/harvests")
        self.harvests_dir.mkdir(parents=True, exist_ok=True)
        
        self.stats = {
            'brands_processed': 0,
            'profiles_created': 0,
            'harvests_successful': 0,
            'products_found': 0
        }
    
    def get_brand_impact_scores(self):
        """Calculate impact scores for brands with websites"""
        brands_with_impact = []
        
        for brand_slug, brand_data in self.brand_sites['brands'].items():
            if not brand_data.get('has_website'):
                continue
            
            # Get product count from database
            response = self.supabase.table('foods_canonical').select(
                'product_key,form,life_stage,kcal_per_100g,ingredients_tokens,price_per_kg'
            ).eq('brand_slug', brand_slug).execute()
            
            if response.data:
                products = response.data
                total = len(products)
                
                # Calculate completion percentage
                fields_complete = 0
                for product in products:
                    if product.get('form'):
                        fields_complete += 0.2
                    if product.get('life_stage'):
                        fields_complete += 0.2
                    if product.get('kcal_per_100g'):
                        fields_complete += 0.2
                    if product.get('ingredients_tokens'):
                        fields_complete += 0.2
                    if product.get('price_per_kg'):
                        fields_complete += 0.2
                
                completion_pct = (fields_complete / total) * 100 if total > 0 else 0
                impact_score = total * (100 - completion_pct)
                
                brands_with_impact.append({
                    'brand_slug': brand_slug,
                    'brand_name': brand_data['brand_name'],
                    'website_url': brand_data.get('website_url'),
                    'product_count': total,
                    'completion_pct': completion_pct,
                    'impact_score': impact_score,
                    'can_crawl': brand_data.get('robots', {}).get('can_crawl', True)
                })
        
        # Sort by impact score
        brands_with_impact.sort(key=lambda x: x['impact_score'], reverse=True)
        return brands_with_impact
    
    def create_brand_profile(self, brand_info):
        """Create or update brand profile for harvesting"""
        brand_slug = brand_info['brand_slug']
        profile_path = self.profiles_dir / f"{brand_slug}.yaml"
        
        # Check if profile already exists
        if profile_path.exists():
            print(f"  ✓ Profile exists: {profile_path}")
            return True
        
        # Create new profile
        profile = {
            'brand': brand_info['brand_name'],
            'brand_slug': brand_slug,
            'website_url': brand_info['website_url'],
            'status': 'active',
            'last_updated': datetime.now().strftime('%Y-%m-%d'),
            'rate_limits': {
                'delay_seconds': 2,
                'jitter_seconds': 1,
                'max_concurrent': 1,
                'respect_robots': True
            },
            'discovery': {
                'method': 'sitemap_or_category',
                'category_urls': [
                    f"{brand_info['website_url']}/products/",
                    f"{brand_info['website_url']}/dog-food/",
                    f"{brand_info['website_url']}/shop/dog/",
                    f"{brand_info['website_url']}/en/dogs/",
                    f"{brand_info['website_url']}/products/dogs/"
                ],
                'sitemap_urls': [
                    f"{brand_info['website_url']}/sitemap.xml",
                    f"{brand_info['website_url']}/sitemap_index.xml"
                ]
            },
            'pdp_selectors': {
                'product_name': {
                    'css': 'h1.product-title, h1.product-name, h1[itemprop="name"], .product h1, h1.page-title',
                    'xpath': '//h1[@class="product-title" or @class="product-name" or @itemprop="name"]'
                },
                'ingredients': {
                    'css': '.ingredients, .composition, .product-ingredients, [itemprop="ingredients"], .tab-content',
                    'xpath': '//div[contains(@class, "ingredients") or contains(@class, "composition")]',
                    'regex': r'(?:Composition|Ingredients?|Zutaten):\s*([^.]+)'
                },
                'analytical_constituents': {
                    'css': '.analytical, .nutrition, .analysis, .constituents, .tab-content',
                    'xpath': '//div[contains(@class, "analytical") or contains(@class, "nutrition")]',
                    'regex': r'(?:Protein|Crude Protein|Fat|Crude Fat|Fibre|Crude Fibre|Ash|Crude Ash|Moisture):\s*([\d.]+)%'
                },
                'price': {
                    'css': '.price, .product-price, [itemprop="price"], .current-price, .price-now',
                    'xpath': '//span[@class="price" or @itemprop="price"]',
                    'regex': r'[£€$]\s*([\d.]+)'
                },
                'pack_size': {
                    'css': '.size, .weight, .pack-size, .product-weight',
                    'xpath': '//span[contains(@class, "size") or contains(@class, "weight")]',
                    'regex': r'(\d+(?:\.\d+)?)\s*(kg|g|lb|oz)'
                },
                'life_stage': {
                    'css': '.life-stage, .age-group',
                    'keywords': ['puppy', 'junior', 'adult', 'senior', 'all life stages']
                },
                'form': {
                    'css': '.product-type, .food-type',
                    'keywords': ['dry', 'wet', 'raw', 'freeze-dried', 'dehydrated']
                }
            }
        }
        
        # Save profile
        with open(profile_path, 'w') as f:
            yaml.dump(profile, f, default_flow_style=False, sort_keys=False)
        
        print(f"  ✓ Created profile: {profile_path}")
        self.stats['profiles_created'] += 1
        return True
    
    def run_harvest_job(self, brand_info):
        """Run the harvest job for a brand"""
        brand_slug = brand_info['brand_slug']
        
        print(f"\n📦 Harvesting: {brand_info['brand_name']}")
        print(f"  Website: {brand_info['website_url']}")
        print(f"  Products in DB: {brand_info['product_count']}")
        print(f"  Completion: {brand_info['completion_pct']:.1f}%")
        print(f"  Impact score: {brand_info['impact_score']:.0f}")
        
        # Create/update profile
        if not self.create_brand_profile(brand_info):
            return False
        
        # Run harvest command
        print(f"  🕷️ Starting harvest...")
        
        try:
            # Use existing brand_harvest.py
            cmd = [
                'python3', 'jobs/brand_harvest.py',
                brand_slug,
                '--output-dir', str(self.harvests_dir)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                print(f"  ✅ Harvest completed successfully")
                self.stats['harvests_successful'] += 1
                
                # Check for output file
                harvest_files = list(self.harvests_dir.glob(f"{brand_slug}_*.csv"))
                if harvest_files:
                    # Count products found
                    import pandas as pd
                    df = pd.read_csv(harvest_files[-1])
                    products_found = len(df)
                    self.stats['products_found'] += products_found
                    print(f"  📊 Products found: {products_found}")
                
                return True
            else:
                print(f"  ❌ Harvest failed: {result.stderr[:200] if result.stderr else 'Unknown error'}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"  ⏱️ Harvest timed out")
            return False
        except Exception as e:
            print(f"  ❌ Error: {e}")
            return False
    
    def harvest_top_brands(self, limit=20, auto_confirm=False):
        """Harvest data from top brands by impact score"""
        print("="*80)
        print("MANUFACTURER DATA HARVESTING")
        print("="*80)
        
        # Get brands with impact scores
        print("\n📊 Calculating impact scores...")
        brands_with_impact = self.get_brand_impact_scores()
        
        if not brands_with_impact:
            print("No brands with websites and products found!")
            return
        
        # Filter to only crawlable brands
        crawlable_brands = [b for b in brands_with_impact if b['can_crawl']]
        
        print(f"\n🎯 Found {len(crawlable_brands)} crawlable brands")
        print(f"Processing top {limit} by impact score...")
        
        # Show top brands
        print("\n📈 Top brands by impact score:")
        print(f"{'Rank':<5} {'Brand':<30} {'Products':<10} {'Complete':<12} {'Impact':<10}")
        print("-"*80)
        
        for i, brand in enumerate(crawlable_brands[:limit], 1):
            print(f"{i:<5} {brand['brand_slug']:<30} {brand['product_count']:<10} "
                  f"{brand['completion_pct']:<12.1f} {brand['impact_score']:<10.0f}")
        
        # Ask for confirmation unless in auto mode
        if not auto_confirm:
            print(f"\n⚠️ This will harvest data from {min(limit, len(crawlable_brands))} brand websites")
            response = input("Proceed? (y/n): ").strip().lower()
            
            if response != 'y':
                print("Cancelled")
                return
        else:
            print(f"\n✅ Auto-confirm enabled - proceeding with {min(limit, len(crawlable_brands))} brands")
        
        # Process brands
        print("\n" + "="*80)
        print("STARTING HARVEST")
        print("="*80)
        
        for brand_info in crawlable_brands[:limit]:
            self.stats['brands_processed'] += 1
            success = self.run_harvest_job(brand_info)
            
            # Rate limiting between brands
            time.sleep(2)
            
            # Save progress report
            if self.stats['brands_processed'] % 5 == 0:
                self.generate_progress_report()
        
        # Final report
        self.generate_final_report()
    
    def generate_progress_report(self):
        """Generate progress report"""
        print("\n" + "-"*40)
        print("PROGRESS REPORT")
        print("-"*40)
        print(f"Brands processed: {self.stats['brands_processed']}")
        print(f"Profiles created: {self.stats['profiles_created']}")
        print(f"Successful harvests: {self.stats['harvests_successful']}")
        print(f"Total products found: {self.stats['products_found']}")
        print("-"*40 + "\n")
    
    def generate_final_report(self):
        """Generate final harvest report"""
        print("\n" + "="*80)
        print("HARVEST COMPLETE")
        print("="*80)
        
        print(f"\n📊 Final Statistics:")
        print(f"  Brands processed: {self.stats['brands_processed']}")
        print(f"  New profiles created: {self.stats['profiles_created']}")
        print(f"  Successful harvests: {self.stats['harvests_successful']}")
        print(f"  Failed harvests: {self.stats['brands_processed'] - self.stats['harvests_successful']}")
        print(f"  Total products found: {self.stats['products_found']}")
        
        if self.stats['brands_processed'] > 0:
            success_rate = (self.stats['harvests_successful'] / self.stats['brands_processed']) * 100
            print(f"  Success rate: {success_rate:.1f}%")
        
        print(f"\n📁 Output location: {self.harvests_dir}")
        
        print("\n🎯 Next steps:")
        print("1. Review harvest results in reports/MANUF/harvests/")
        print("2. Run normalization script to process harvested data")
        print("3. Match and merge with foods_published_preview")
        print("4. Validate against quality gates")
        print("5. Promote qualifying brands to production")

def main():
    """Main execution"""
    import sys
    
    harvester = ManufacturerHarvester()
    
    print("="*80)
    print("MANUFACTURER DATA HARVESTING")
    print("="*80)
    print("\nThis will harvest product data from brand websites")
    print("Using robots.txt compliant scraping with rate limiting")
    
    # Check for command line argument
    if len(sys.argv) > 1 and sys.argv[1] == '--auto':
        print("\nRunning in AUTO mode - harvesting top 20 brands")
        harvester.harvest_top_brands(20, auto_confirm=True)
    else:
        # Ask how many brands to process
        print("\nHow many brands to harvest?")
        print("1. Test with 3 brands")
        print("2. Top 10 brands")
        print("3. Top 20 brands")
        print("4. Custom number")
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == '1':
            harvester.harvest_top_brands(3)
        elif choice == '2':
            harvester.harvest_top_brands(10)
        elif choice == '3':
            harvester.harvest_top_brands(20)
        elif choice == '4':
            num = input("Enter number of brands: ").strip()
            try:
                harvester.harvest_top_brands(int(num))
            except:
                print("Invalid number")
        else:
            print("Invalid option")

if __name__ == "__main__":
    main()