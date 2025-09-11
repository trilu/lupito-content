#!/usr/bin/env python3
"""
Create brand_sites.yaml with manufacturer website mapping and robots.txt compliance info
Part of Prompt A - Manufacturer Enrichment Sprint
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

load_dotenv()

class BrandSitesMapper:
    def __init__(self):
        # Load existing data
        self.websites_csv = Path("reports/MANUF/MANUFACTURER_WEBSITES.csv")
        self.output_path = Path("data/brand_sites.yaml")
        self.output_path.parent.mkdir(exist_ok=True)
        
        # Supabase connection
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase = create_client(url, key)
        
        # User agent for robots.txt checks
        self.user_agent = "Lupito-Content-Bot/1.0"
        
    def check_robots_txt(self, website_url):
        """Check robots.txt compliance for a website"""
        try:
            rp = RobotFileParser()
            robots_url = urlparse(website_url).scheme + "://" + urlparse(website_url).netloc + "/robots.txt"
            rp.set_url(robots_url)
            rp.read()
            
            # Check if we can fetch
            can_fetch = rp.can_fetch(self.user_agent, website_url)
            crawl_delay = rp.crawl_delay(self.user_agent) or 1.0
            
            return {
                'can_crawl': can_fetch,
                'crawl_delay': float(crawl_delay),
                'robots_url': robots_url,
                'checked_at': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'can_crawl': True,  # Default to allowed if can't check
                'crawl_delay': 2.0,  # Conservative default
                'robots_url': None,
                'error': str(e),
                'checked_at': datetime.now().isoformat()
            }
    
    def get_brand_completion_stats(self):
        """Get completion statistics for each brand from database"""
        try:
            # Get all products with their brand and field completeness
            response = self.supabase.table('foods_canonical').select(
                "brand_slug,form,life_stage,kcal_per_100g,ingredients_tokens,price_per_kg"
            ).execute()
            
            if not response.data:
                return {}
            
            df = pd.DataFrame(response.data)
            
            # Calculate completion by brand
            stats = {}
            for brand_slug in df['brand_slug'].unique():
                if not brand_slug:
                    continue
                    
                brand_df = df[df['brand_slug'] == brand_slug]
                total = len(brand_df)
                
                stats[brand_slug] = {
                    'sku_count': total,
                    'form_coverage': (brand_df['form'].notna().sum() / total * 100),
                    'life_stage_coverage': (brand_df['life_stage'].notna().sum() / total * 100),
                    'kcal_coverage': (brand_df['kcal_per_100g'].notna().sum() / total * 100),
                    'ingredients_coverage': (brand_df['ingredients_tokens'].notna().sum() / total * 100),
                    'price_coverage': (brand_df['price_per_kg'].notna().sum() / total * 100),
                    'overall_completion': 0  # Will calculate below
                }
                
                # Calculate overall completion (average of all coverages)
                coverages = [
                    stats[brand_slug]['form_coverage'],
                    stats[brand_slug]['life_stage_coverage'],
                    stats[brand_slug]['kcal_coverage'],
                    stats[brand_slug]['ingredients_coverage'],
                    stats[brand_slug]['price_coverage']
                ]
                stats[brand_slug]['overall_completion'] = sum(coverages) / len(coverages)
                
                # Calculate impact score: SKU count × (100 - completion%)
                stats[brand_slug]['impact_score'] = total * (100 - stats[brand_slug]['overall_completion'])
            
            return stats
        except Exception as e:
            print(f"Error getting completion stats: {e}")
            return {}
    
    def create_brand_sites_yaml(self):
        """Create comprehensive brand_sites.yaml"""
        print("="*70)
        print("CREATING BRAND_SITES.YAML")
        print("="*70)
        
        # Load existing website mappings
        websites_df = pd.read_csv(self.websites_csv)
        
        # Get completion stats
        print("\nFetching brand completion statistics...")
        completion_stats = self.get_brand_completion_stats()
        
        brand_sites = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_brands': 0,
                'brands_with_websites': 0,
                'brands_crawlable': 0,
                'user_agent': self.user_agent
            },
            'brands': {}
        }
        
        print("\nProcessing brands...")
        for _, row in websites_df.iterrows():
            brand_slug = row['brand_slug']
            website_url = row.get('website_url', '')
            
            brand_info = {
                'brand_name': row['brand'],
                'brand_slug': brand_slug,
                'website_url': website_url if pd.notna(website_url) else None,
                'has_website': row.get('has_website', False),
                'product_count': row.get('product_count', 0),
                'source': row.get('source', 'unknown')
            }
            
            # Add completion stats if available
            if brand_slug in completion_stats:
                brand_info['completion'] = completion_stats[brand_slug]
            else:
                brand_info['completion'] = {
                    'sku_count': row.get('product_count', 0),
                    'overall_completion': 0,
                    'impact_score': row.get('product_count', 0) * 100
                }
            
            # Check robots.txt if website exists
            if website_url and pd.notna(website_url):
                print(f"  Checking robots.txt for {brand_slug}...")
                robots_info = self.check_robots_txt(website_url)
                brand_info['robots'] = robots_info
                time.sleep(0.5)  # Be polite between checks
            else:
                brand_info['robots'] = {
                    'can_crawl': False,
                    'reason': 'no_website'
                }
            
            # Determine country/region
            if website_url:
                domain = urlparse(website_url).netloc.lower()
                if '.co.uk' in domain or '.uk' in domain:
                    brand_info['country'] = 'UK'
                elif '.de' in domain:
                    brand_info['country'] = 'DE'
                elif '.fr' in domain:
                    brand_info['country'] = 'FR'
                elif '.com' in domain:
                    brand_info['country'] = 'US'
                else:
                    brand_info['country'] = 'INT'
            else:
                brand_info['country'] = 'UNKNOWN'
            
            # Add notes
            notes = []
            if brand_info.get('has_website'):
                if brand_info['robots'].get('can_crawl'):
                    notes.append('crawlable')
                else:
                    notes.append('blocked_by_robots')
            else:
                notes.append('no_website_found')
            
            if brand_info['completion']['impact_score'] > 1000:
                notes.append('high_impact')
            elif brand_info['completion']['impact_score'] > 500:
                notes.append('medium_impact')
            else:
                notes.append('low_impact')
            
            brand_info['notes'] = notes
            
            brand_sites['brands'][brand_slug] = brand_info
        
        # Update metadata
        brand_sites['metadata']['total_brands'] = len(brand_sites['brands'])
        brand_sites['metadata']['brands_with_websites'] = sum(
            1 for b in brand_sites['brands'].values() if b.get('has_website')
        )
        brand_sites['metadata']['brands_crawlable'] = sum(
            1 for b in brand_sites['brands'].values() 
            if b.get('robots', {}).get('can_crawl', False)
        )
        
        # Sort brands by impact score
        sorted_brands = dict(sorted(
            brand_sites['brands'].items(),
            key=lambda x: x[1]['completion']['impact_score'],
            reverse=True
        ))
        brand_sites['brands'] = sorted_brands
        
        # Save to YAML
        with open(self.output_path, 'w') as f:
            yaml.dump(brand_sites, f, default_flow_style=False, sort_keys=False)
        
        print(f"\n✅ Created {self.output_path}")
        print(f"   Total brands: {brand_sites['metadata']['total_brands']}")
        print(f"   With websites: {brand_sites['metadata']['brands_with_websites']}")
        print(f"   Crawlable: {brand_sites['metadata']['brands_crawlable']}")
        
        # Print top 20 by impact score
        print("\n" + "="*70)
        print("TOP 20 BRANDS BY IMPACT SCORE")
        print("="*70)
        print(f"{'Rank':<5} {'Brand':<25} {'SKUs':<8} {'Completion':<12} {'Impact':<10} {'Website'}")
        print("-"*85)
        
        for i, (brand_slug, info) in enumerate(list(sorted_brands.items())[:20], 1):
            completion = info['completion']['overall_completion']
            impact = info['completion']['impact_score']
            has_site = '✓' if info.get('has_website') else '✗'
            can_crawl = '✓' if info.get('robots', {}).get('can_crawl') else '✗'
            
            print(f"{i:<5} {brand_slug:<25} {info['completion']['sku_count']:<8} "
                  f"{completion:<12.1f} {impact:<10.1f} Site:{has_site} Crawl:{can_crawl}")
        
        return brand_sites

def main():
    mapper = BrandSitesMapper()
    brand_sites = mapper.create_brand_sites_yaml()
    
    # Also create a priority list CSV for easy reference
    priority_df = []
    for brand_slug, info in list(brand_sites['brands'].items())[:20]:
        priority_df.append({
            'rank': len(priority_df) + 1,
            'brand_slug': brand_slug,
            'brand_name': info['brand_name'],
            'sku_count': info['completion']['sku_count'],
            'completion_pct': info['completion']['overall_completion'],
            'impact_score': info['completion']['impact_score'],
            'has_website': info.get('has_website', False),
            'can_crawl': info.get('robots', {}).get('can_crawl', False),
            'website_url': info.get('website_url', '')
        })
    
    priority_df = pd.DataFrame(priority_df)
    priority_path = Path("reports/MANUF/TOP20_PRIORITY.csv")
    priority_df.to_csv(priority_path, index=False)
    print(f"\n✅ Saved top 20 priority list to {priority_path}")

if __name__ == "__main__":
    main()