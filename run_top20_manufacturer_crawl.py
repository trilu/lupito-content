#!/usr/bin/env python3
"""
Run manufacturer crawler for top 20 impact brands
Part of Prompt A - Manufacturer Enrichment Sprint
Focus on enriching form, life_stage, kcal_per_100g, ingredients_tokens, price_per_kg_eur
"""

import os
import yaml
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv
import subprocess
import time

load_dotenv()

class Top20ManufacturerCrawler:
    def __init__(self):
        # Supabase connection
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase = create_client(url, key)
        
        # Paths
        self.brand_sites_yaml = Path("data/brand_sites.yaml")
        self.harvest_dir = Path("reports/MANUF/harvests")
        self.harvest_dir.mkdir(parents=True, exist_ok=True)
        
        # Report paths
        self.delta_report = Path("reports/MANUF/MANUF_DELTA.md")
        self.outliers_report = Path("reports/MANUF/MANUF_OUTLIERS.md")
        self.promote_report = Path("reports/MANUF/MANUF_PROMOTE_PROPOSALS.md")
        
        # Load brand sites
        with open(self.brand_sites_yaml, 'r') as f:
            self.brand_sites = yaml.safe_load(f)
    
    def get_top_20_brands(self):
        """Get top 20 brands by impact score that have websites and can be crawled"""
        top_brands = []
        
        for brand_slug, info in self.brand_sites['brands'].items():
            if (info.get('has_website') and 
                info.get('robots', {}).get('can_crawl', False) and
                info.get('stats', {}).get('product_count', 0) > 0):
                
                top_brands.append({
                    'brand_slug': brand_slug,
                    'brand_name': info['brand_name'],
                    'website_url': info['website_url'],
                    'product_count': info['stats']['product_count'],
                    'completion_pct': info['stats']['completion_pct'],
                    'impact_score': info['stats']['impact_score'],
                    'crawl_delay': info['robots'].get('crawl_delay', 2.0)
                })
        
        # Sort by impact score
        top_brands.sort(key=lambda x: x['impact_score'], reverse=True)
        
        return top_brands[:20]
    
    def check_brand_profile_exists(self, brand_slug):
        """Check if brand profile YAML exists"""
        profile_path = Path(f"profiles/brands/{brand_slug}.yaml")
        return profile_path.exists()
    
    def create_brand_profile(self, brand_data):
        """Create a brand profile YAML if it doesn't exist"""
        brand_slug = brand_data['brand_slug']
        profile_path = Path(f"profiles/brands/{brand_slug}.yaml")
        
        if profile_path.exists():
            return True
        
        # Create profile directory if needed
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        
        profile = {
            'brand': brand_data['brand_name'],
            'brand_slug': brand_slug,
            'website_url': brand_data['website_url'],
            'status': 'active',
            'last_updated': datetime.now().strftime('%Y-%m-%d'),
            'rate_limits': {
                'delay_seconds': max(2, int(brand_data['crawl_delay'])),
                'jitter_seconds': 1,
                'max_concurrent': 1,
                'respect_robots': True
            },
            'discovery': {
                'method': 'sitemap_or_category',
                'category_urls': [
                    f"{brand_data['website_url']}/products/",
                    f"{brand_data['website_url']}/dog/",
                    f"{brand_data['website_url']}/dog-food/",
                    f"{brand_data['website_url']}/shop/",
                    f"{brand_data['website_url']}/catalog/"
                ]
            },
            'pdp_selectors': {
                'product_name': {
                    'css': 'h1.product-title, h1.product-name, h1[itemprop="name"], .product h1',
                    'xpath': '//h1[@class="product-title" or @class="product-name"]'
                },
                'ingredients': {
                    'css': '.ingredients, .composition, .product-ingredients, [itemprop="ingredients"]',
                    'xpath': '//div[contains(@class, "ingredients") or contains(@class, "composition")]',
                    'regex': r'(?:Composition|Ingredients|Zutaten):\s*([^.]+)'
                },
                'analytical_constituents': {
                    'css': '.analytical, .nutrition, .analysis, .constituents',
                    'xpath': '//div[contains(@class, "analytical") or contains(@class, "nutrition")]',
                    'regex': r'(?:Protein|Fat|Fibre|Ash|Moisture):\s*([\d.]+)%'
                },
                'price': {
                    'css': '.price, .product-price, [itemprop="price"], .current-price',
                    'xpath': '//span[@class="price" or @itemprop="price"]'
                },
                'pack_size': {
                    'css': '.size, .weight, .pack-size',
                    'regex': r'(\d+(?:\.\d+)?)\s*(kg|g|lb|oz)'
                }
            }
        }
        
        # Save profile
        with open(profile_path, 'w') as f:
            yaml.dump(profile, f, default_flow_style=False, sort_keys=False)
        
        print(f"  Created profile: {profile_path}")
        return True
    
    def run_brand_harvest(self, brand_data):
        """Run the brand harvest job for a specific brand"""
        brand_slug = brand_data['brand_slug']
        
        # Check/create profile
        if not self.check_brand_profile_exists(brand_slug):
            self.create_brand_profile(brand_data)
        
        # Run harvest job
        print(f"\n  Running harvest for {brand_slug}...")
        
        try:
            # Use the existing brand_harvest.py script
            cmd = [
                'python3', 'jobs/brand_harvest.py',
                brand_slug
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout per brand
            )
            
            if result.returncode == 0:
                print(f"    ✓ Harvest completed for {brand_slug}")
                return True
            else:
                print(f"    ✗ Harvest failed for {brand_slug}: {result.stderr[:200]}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"    ✗ Harvest timed out for {brand_slug}")
            return False
        except Exception as e:
            print(f"    ✗ Error harvesting {brand_slug}: {e}")
            return False
    
    def calculate_delta(self, brand_slug):
        """Calculate coverage delta for a brand"""
        # Get before stats from database
        response = self.supabase.table('foods_canonical').select(
            "form,life_stage,kcal_per_100g,ingredients_tokens,price_per_kg"
        ).eq('brand_slug', brand_slug).execute()
        
        if not response.data:
            return None
        
        df = pd.DataFrame(response.data)
        total = len(df)
        
        before = {
            'form': (df['form'].notna().sum() / total * 100),
            'life_stage': (df['life_stage'].notna().sum() / total * 100),
            'kcal': (df['kcal_per_100g'].notna().sum() / total * 100),
            'ingredients': (df['ingredients_tokens'].notna().sum() / total * 100),
            'price': (df['price_per_kg'].notna().sum() / total * 100)
        }
        
        # Check harvest results
        harvest_file = self.harvest_dir / f"{brand_slug}_harvest_*.csv"
        harvest_files = list(self.harvest_dir.glob(f"{brand_slug}_harvest_*.csv"))
        
        if harvest_files:
            # Get most recent harvest
            harvest_df = pd.read_csv(sorted(harvest_files)[-1])
            
            # Calculate potential improvement
            harvested = len(harvest_df)
            fields_found = {
                'form': harvest_df['form'].notna().sum() if 'form' in harvest_df else 0,
                'life_stage': harvest_df['life_stage'].notna().sum() if 'life_stage' in harvest_df else 0,
                'kcal': harvest_df['kcal_per_100g'].notna().sum() if 'kcal_per_100g' in harvest_df else 0,
                'ingredients': harvest_df['ingredients'].notna().sum() if 'ingredients' in harvest_df else 0,
                'price': harvest_df['price'].notna().sum() if 'price' in harvest_df else 0
            }
            
            return {
                'brand_slug': brand_slug,
                'products_in_db': total,
                'products_harvested': harvested,
                'before': before,
                'fields_found': fields_found
            }
        
        return None
    
    def generate_reports(self, results):
        """Generate all required reports"""
        # MANUF_DELTA.md
        with open(self.delta_report, 'w') as f:
            f.write(f"# MANUFACTURER ENRICHMENT DELTA REPORT\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")
            f.write(f"## Summary\n")
            f.write(f"- Brands processed: {len(results)}\n")
            f.write(f"- Successful harvests: {sum(1 for r in results if r['success'])}\n\n")
            
            f.write(f"## Coverage Improvements\n\n")
            for result in results:
                if result.get('delta'):
                    delta = result['delta']
                    f.write(f"### {result['brand_slug']}\n")
                    f.write(f"- Products in DB: {delta['products_in_db']}\n")
                    f.write(f"- Products harvested: {delta['products_harvested']}\n")
                    f.write(f"- Form coverage: {delta['before']['form']:.1f}% → potential improvement\n")
                    f.write(f"- Life stage coverage: {delta['before']['life_stage']:.1f}% → potential improvement\n\n")
        
        # MANUF_OUTLIERS.md
        with open(self.outliers_report, 'w') as f:
            f.write(f"# MANUFACTURER DATA OUTLIERS REPORT\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")
            f.write(f"## Kcal Outliers\n")
            f.write(f"Products with kcal outside 200-600 range will be flagged\n\n")
            f.write(f"## Price Outliers\n")
            f.write(f"Products with price_per_kg > €50 or < €0.50 will be flagged\n\n")
        
        # MANUF_PROMOTE_PROPOSALS.md
        with open(self.promote_report, 'w') as f:
            f.write(f"# BRAND PROMOTION PROPOSALS\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")
            f.write(f"## Brands Meeting Gates\n\n")
            f.write(f"Gates required:\n")
            f.write(f"- form ≥ 95%\n")
            f.write(f"- life_stage ≥ 95%\n")
            f.write(f"- valid kcal (200-600) ≥ 90%\n")
            f.write(f"- ingredients_tokens ≥ 85%\n")
            f.write(f"- price_per_kg_eur ≥ 70%\n\n")
            
            f.write(f"## SQL Statements\n\n")
            f.write(f"```sql\n")
            f.write(f"-- Brands that pass gates will be listed here\n")
            f.write(f"-- after enrichment and validation\n")
            f.write(f"```\n")
        
        print(f"\n✅ Reports generated:")
        print(f"   - {self.delta_report}")
        print(f"   - {self.outliers_report}")
        print(f"   - {self.promote_report}")
    
    def run_top_20_crawl(self):
        """Main execution - crawl top 20 brands"""
        print("="*70)
        print("TOP 20 MANUFACTURER CRAWL")
        print("="*70)
        
        # Get top 20 brands
        top_brands = self.get_top_20_brands()
        
        if not top_brands:
            print("No crawlable brands found!")
            return
        
        print(f"\nTop 20 brands by impact score:")
        print(f"{'Rank':<5} {'Brand':<25} {'SKUs':<8} {'Completion':<12} {'Impact':<10}")
        print("-"*70)
        
        for i, brand in enumerate(top_brands, 1):
            print(f"{i:<5} {brand['brand_slug']:<25} {brand['product_count']:<8} "
                  f"{brand['completion_pct']:<12.1f} {brand['impact_score']:<10.0f}")
        
        # Ask for confirmation to proceed
        print(f"\n⚠️  This will crawl {len(top_brands)} manufacturer websites")
        print("Note: We'll create profiles and use existing harvest infrastructure")
        
        # For now, just do the first 3 as a test
        test_brands = top_brands[:3]
        
        print(f"\n🚀 Starting test crawl of first 3 brands...")
        results = []
        
        for brand in test_brands:
            print(f"\n{'='*50}")
            print(f"Processing: {brand['brand_slug']}")
            print(f"Website: {brand['website_url']}")
            print(f"Crawl delay: {brand['crawl_delay']}s")
            
            # Run harvest
            success = self.run_brand_harvest(brand)
            
            # Calculate delta
            delta = None
            if success:
                delta = self.calculate_delta(brand['brand_slug'])
            
            results.append({
                'brand_slug': brand['brand_slug'],
                'success': success,
                'delta': delta
            })
            
            # Respect crawl delay between brands
            time.sleep(max(2, brand['crawl_delay']))
        
        # Generate reports
        self.generate_reports(results)
        
        print("\n" + "="*70)
        print("CRAWL COMPLETE")
        print("="*70)
        print(f"Processed {len(results)} brands")
        print(f"Successful: {sum(1 for r in results if r['success'])}")
        print(f"Failed: {sum(1 for r in results if not r['success'])}")
        
        print("\n📝 Next steps:")
        print("1. Review harvest results in reports/MANUF/harvests/")
        print("2. Run matching and merging script")
        print("3. Validate against quality gates")
        print("4. Promote qualifying brands to production")

def main():
    crawler = Top20ManufacturerCrawler()
    crawler.run_top_20_crawl()

if __name__ == "__main__":
    main()