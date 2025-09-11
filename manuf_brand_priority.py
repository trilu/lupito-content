#!/usr/bin/env python3
"""
Generate brand priority report for manufacturer data harvesting
"""

import os
import pandas as pd
from supabase import create_client
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
import requests
from urllib.parse import urlparse
import time

load_dotenv()

class BrandPrioritizer:
    def __init__(self):
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not found")
            
        self.supabase = create_client(supabase_url, supabase_key)
        self.report_dir = Path("reports/MANUF")
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
        # Known manufacturer websites (to be expanded)
        self.brand_websites = {
            'royal-canin': 'https://www.royalcanin.com',
            'hills': 'https://www.hillspet.com',
            'purina': 'https://www.purina.co.uk',
            'pedigree': 'https://www.pedigree.com',
            'whiskas': 'https://www.whiskas.co.uk',
            'iams': 'https://www.iams.com',
            'eukanuba': 'https://www.eukanuba.com',
            'advance': 'https://www.advance-pet.com',
            'acana': 'https://www.acana.com',
            'orijen': 'https://www.orijen.ca',
            'taste-of-the-wild': 'https://www.tasteofthewild.com',
            'nutro': 'https://www.nutro.com',
            'blue-buffalo': 'https://www.bluebuffalo.com',
            'wellness': 'https://www.wellnesspetfood.com',
            'merrick': 'https://www.merrickpetcare.com',
            'canidae': 'https://www.canidae.com',
            'natural-balance': 'https://www.naturalbalanceinc.com',
            'fromm': 'https://www.frommfamily.com',
            'victor': 'https://www.victorpetfood.com',
            'diamond': 'https://www.diamondpet.com',
            'rachael-ray': 'https://www.rachaelray.com/nutrish',
            'natures-variety': 'https://www.instinctpetfood.com',
            'solid-gold': 'https://www.solidgoldpet.com',
            'earthborn': 'https://www.earthbornholisticpetfood.com',
            'zignature': 'https://www.zignature.com',
            'applaws': 'https://www.applaws.com',
            'lily-s-kitchen': 'https://www.lilyskitchen.co.uk',
            'burns': 'https://burnspet.co.uk',
            'harringtons': 'https://www.harringtonspetfood.com',
            'beco': 'https://www.becopets.com'
        }
        
    def fetch_brand_data(self):
        """Fetch brand statistics from foods_published"""
        print("Fetching brand data from foods_published...")
        
        # Get brand counts
        response = self.supabase.table('foods_published').select(
            "brand,brand_slug,product_key,product_name,form,life_stage,kcal_per_100g,ingredients_tokens,price_per_kg"
        ).limit(5000).execute()
        
        df = pd.DataFrame(response.data)
        print(f"Fetched {len(df)} products")
        
        # Calculate brand statistics
        brand_stats = df.groupby(['brand', 'brand_slug']).agg({
            'product_key': 'count',
            'form': lambda x: (~x.isna()).sum(),
            'life_stage': lambda x: (~x.isna()).sum(),
            'kcal_per_100g': lambda x: (~x.isna()).sum(),
            'ingredients_tokens': lambda x: (~x.isna()).sum(),
            'price_per_kg': lambda x: (~x.isna()).sum()
        }).rename(columns={
            'product_key': 'product_count',
            'form': 'has_form',
            'life_stage': 'has_life_stage',
            'kcal_per_100g': 'has_kcal',
            'ingredients_tokens': 'has_ingredients',
            'price_per_kg': 'has_price'
        })
        
        brand_stats = brand_stats.reset_index()
        brand_stats = brand_stats.sort_values('product_count', ascending=False)
        
        return df, brand_stats
    
    def check_website_features(self, url):
        """Check website for robots.txt, JSON-LD, and other features"""
        features = {
            'website_url': url,
            'robots_txt': False,
            'robots_allow': True,
            'has_sitemap': False,
            'response_time': None,
            'status_code': None
        }
        
        if not url:
            return features
            
        try:
            # Check main page
            start = time.time()
            response = requests.get(url, timeout=5, headers={
                'User-Agent': 'Mozilla/5.0 (compatible; LupitoBot/1.0)'
            })
            features['response_time'] = round(time.time() - start, 2)
            features['status_code'] = response.status_code
            
            # Check robots.txt
            robots_url = f"{url}/robots.txt"
            try:
                robots_response = requests.get(robots_url, timeout=3)
                if robots_response.status_code == 200:
                    features['robots_txt'] = True
                    # Simple check for sitemap
                    if 'sitemap' in robots_response.text.lower():
                        features['has_sitemap'] = True
                    # Check if we're disallowed
                    if 'disallow: /' in robots_response.text.lower():
                        features['robots_allow'] = False
            except:
                pass
                
        except Exception as e:
            print(f"Error checking {url}: {e}")
            
        return features
    
    def generate_priority_report(self, df, brand_stats):
        """Generate brand priority report"""
        print("\n=== Generating Brand Priority Report ===")
        
        # Add website info
        brand_stats['website_url'] = brand_stats['brand_slug'].map(self.brand_websites)
        
        # Check top 30 brands for website features
        print("Checking website features for top brands...")
        website_features = []
        
        for idx, row in brand_stats.head(30).iterrows():
            if pd.notna(row['website_url']) and row['website_url']:
                print(f"Checking {row['brand_slug']}...")
                features = self.check_website_features(row['website_url'])
                features['brand'] = row['brand']
                features['brand_slug'] = row['brand_slug']
                website_features.append(features)
                time.sleep(1)  # Rate limiting
            else:
                # Add empty features for brands without websites
                features = {
                    'brand': row['brand'],
                    'brand_slug': row['brand_slug'],
                    'website_url': None,
                    'robots_txt': False,
                    'robots_allow': False,
                    'has_sitemap': False,
                    'response_time': None,
                    'status_code': None
                }
                website_features.append(features)
        
        website_df = pd.DataFrame(website_features) if website_features else pd.DataFrame()
        
        # Merge with brand stats
        if not website_df.empty:
            brand_priority = brand_stats.merge(
                website_df[['brand_slug', 'robots_txt', 'robots_allow', 'has_sitemap', 'status_code']],
                on='brand_slug',
                how='left'
            )
        else:
            brand_priority = brand_stats.copy()
            brand_priority['robots_txt'] = None
            brand_priority['robots_allow'] = None
            brand_priority['has_sitemap'] = None
            brand_priority['status_code'] = None
        
        # Calculate data gaps
        brand_priority['data_gap_score'] = (
            (brand_priority['product_count'] - brand_priority['has_form']) * 0.3 +
            (brand_priority['product_count'] - brand_priority['has_life_stage']) * 0.3 +
            (brand_priority['product_count'] - brand_priority['has_ingredients']) * 0.2 +
            (brand_priority['product_count'] - brand_priority['has_price']) * 0.2
        )
        
        # Sort by priority (high product count + high data gaps)
        brand_priority['priority_score'] = brand_priority['product_count'] * 0.5 + brand_priority['data_gap_score'] * 0.5
        brand_priority = brand_priority.sort_values('priority_score', ascending=False)
        
        # Save CSV
        brand_priority.to_csv(self.report_dir / "MANUF_BRAND_PRIORITY.csv", index=False)
        
        # Get top 500 SKUs (by brand frequency since product_key is string)
        # Use brand product counts to get top products
        top_brands = brand_priority.head(20)['brand_slug'].tolist()
        top_skus = df[df['brand_slug'].isin(top_brands)].head(500)
        top_skus = top_skus[['product_key', 'brand', 'product_name', 'form', 'life_stage', 'ingredients_tokens']]
        top_skus.to_csv(self.report_dir / "MANUF_TOP_500_SKUS.csv", index=False)
        
        return brand_priority, top_skus
    
    def generate_markdown_report(self, brand_priority, top_skus):
        """Generate markdown report"""
        report = f"""# MANUFACTURER BRAND PRIORITY REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary
- Total Brands Analyzed: {len(brand_priority)}
- Brands with Websites: {brand_priority['website_url'].notna().sum()}
- Brands with Robots.txt: {brand_priority['robots_txt'].sum() if 'robots_txt' in brand_priority else 0}
- Brands with Sitemaps: {brand_priority['has_sitemap'].sum() if 'has_sitemap' in brand_priority else 0}

## Top 30 Priority Brands

| Rank | Brand | Products | Website | Robots | Sitemap | Form Gap | Life Stage Gap | Ingredients Gap | Price Gap | Priority Score |
|------|-------|----------|---------|--------|---------|----------|----------------|-----------------|-----------|----------------|
"""
        
        for idx, row in brand_priority.head(30).iterrows():
            website = '✓' if row.get('website_url') else '✗'
            robots = '✓' if row.get('robots_txt') else '✗' if row.get('website_url') else '-'
            sitemap = '✓' if row.get('has_sitemap') else '✗' if row.get('website_url') else '-'
            
            form_gap = row['product_count'] - row['has_form']
            life_gap = row['product_count'] - row['has_life_stage']
            ingredients_gap = row['product_count'] - row['has_ingredients']
            price_gap = row['product_count'] - row['has_price']
            
            report += f"| {idx+1} | {row['brand']} | {row['product_count']} | {website} | {robots} | {sitemap} | "
            report += f"{form_gap} | {life_gap} | {ingredients_gap} | {price_gap} | {row['priority_score']:.0f} |\n"
        
        report += f"""

## Data Coverage Gaps

### Current Coverage
- Products with Form: {brand_priority['has_form'].sum()} / {brand_priority['product_count'].sum()} ({brand_priority['has_form'].sum()/brand_priority['product_count'].sum()*100:.1f}%)
- Products with Life Stage: {brand_priority['has_life_stage'].sum()} / {brand_priority['product_count'].sum()} ({brand_priority['has_life_stage'].sum()/brand_priority['product_count'].sum()*100:.1f}%)
- Products with Ingredients: {brand_priority['has_ingredients'].sum()} / {brand_priority['product_count'].sum()} ({brand_priority['has_ingredients'].sum()/brand_priority['product_count'].sum()*100:.1f}%)
- Products with Price: {brand_priority['has_price'].sum()} / {brand_priority['product_count'].sum()} ({brand_priority['has_price'].sum()/brand_priority['product_count'].sum()*100:.1f}%)

### Recommended Harvest Order
"""
        
        # Group brands by harvest difficulty
        easy_brands = brand_priority[
            (brand_priority['website_url'].notna()) & 
            (brand_priority['robots_allow'] == True) &
            (brand_priority['has_sitemap'] == True)
        ].head(10)
        
        medium_brands = brand_priority[
            (brand_priority['website_url'].notna()) & 
            (brand_priority['robots_allow'] == True) &
            (brand_priority['has_sitemap'] != True)
        ].head(10)
        
        if len(easy_brands) > 0:
            report += "\n#### Easy Targets (has sitemap, allows robots):\n"
            for _, row in easy_brands.iterrows():
                report += f"- **{row['brand']}** ({row['product_count']} products) - {row['website_url']}\n"
        
        if len(medium_brands) > 0:
            report += "\n#### Medium Difficulty (no sitemap but allows robots):\n"
            for _, row in medium_brands.iterrows():
                report += f"- **{row['brand']}** ({row['product_count']} products) - {row['website_url']}\n"
        
        report += f"""

## Top 500 SKUs Summary
- Total SKUs: {len(top_skus)}
- SKUs with Form: {top_skus['form'].notna().sum()} ({top_skus['form'].notna().sum()/len(top_skus)*100:.1f}%)
- SKUs with Life Stage: {top_skus['life_stage'].notna().sum()} ({top_skus['life_stage'].notna().sum()/len(top_skus)*100:.1f}%)
- SKUs with Ingredients: {top_skus['ingredients_tokens'].notna().sum()} ({top_skus['ingredients_tokens'].notna().sum()/len(top_skus)*100:.1f}%)

## Next Steps
1. Create harvest profiles for top 10 "easy" brands
2. Implement scraping infrastructure with robots.txt compliance
3. Build parsers for HTML, JSON-LD, and PDF content
4. Set up GCS caching for harvested content
5. Create enrichment pipeline with field-level provenance

## Notes
- Priority Score = 0.5 × Product Count + 0.5 × Data Gap Score
- Data Gap Score weighted: Form (30%), Life Stage (30%), Ingredients (20%), Price (20%)
- Websites checked with 5-second timeout and 1-second delay between requests
"""
        
        with open(self.report_dir / "MANUF_BRAND_PRIORITY.md", "w") as f:
            f.write(report)
        
        print(f"Report saved to {self.report_dir / 'MANUF_BRAND_PRIORITY.md'}")
    
    def run(self):
        """Run the brand prioritization analysis"""
        print("Starting Brand Prioritization Analysis")
        print("=" * 50)
        
        # Fetch data
        df, brand_stats = self.fetch_brand_data()
        
        # Generate priority report
        brand_priority, top_skus = self.generate_priority_report(df, brand_stats)
        
        # Generate markdown report
        self.generate_markdown_report(brand_priority, top_skus)
        
        print("\n" + "=" * 50)
        print("Brand Prioritization Complete!")
        print(f"Reports saved to {self.report_dir}")
        
        return brand_priority, top_skus

if __name__ == "__main__":
    prioritizer = BrandPrioritizer()
    prioritizer.run()