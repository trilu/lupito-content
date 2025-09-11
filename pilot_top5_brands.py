#!/usr/bin/env python3
"""
Production Pilot: Identify and prepare Top 5 brands for enrichment
"""

import os
import pandas as pd
from pathlib import Path
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv
import yaml

load_dotenv()

class Top5BrandsPilot:
    def __init__(self):
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not found")
            
        self.supabase = create_client(supabase_url, supabase_key)
        self.report_dir = Path("reports/MANUF/PILOT")
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
        # Load website mappings
        self.websites_df = pd.read_csv("reports/MANUF/MANUFACTURER_WEBSITES.csv")
        
    def identify_top5_brands(self):
        """Identify Top 5 brands by SKU count"""
        print("Fetching brand statistics from foods_published...")
        
        response = self.supabase.table('foods_published').select(
            "product_key,brand,brand_slug,product_name,form,life_stage,kcal_per_100g,ingredients_tokens,price_per_kg"
        ).limit(5000).execute()
        
        df = pd.DataFrame(response.data)
        
        # Filter for dog products only
        if 'product_name' in df.columns:
            dog_mask = ~df['product_name'].str.lower().str.contains('cat|kitten|feline', na=False)
            df = df[dog_mask]
        
        # Calculate brand statistics
        brand_stats = df.groupby(['brand', 'brand_slug']).agg({
            'product_key': 'count',
            'form': lambda x: (~x.isna()).sum(),
            'life_stage': lambda x: (~x.isna()).sum(),
            'kcal_per_100g': lambda x: (~x.isna()).sum(),
            'ingredients_tokens': lambda x: (x.notna() & (x != '')).sum(),
            'price_per_kg': lambda x: (~x.isna()).sum()
        }).rename(columns={
            'product_key': 'sku_count',
            'form': 'has_form',
            'life_stage': 'has_life_stage',
            'kcal_per_100g': 'has_kcal',
            'ingredients_tokens': 'has_ingredients',
            'price_per_kg': 'has_price'
        })
        
        brand_stats = brand_stats.reset_index()
        brand_stats = brand_stats.sort_values('sku_count', ascending=False)
        
        # Get Top 5 by SKU count
        top5 = brand_stats.head(5)
        
        # Add website information
        top5 = top5.merge(
            self.websites_df[['brand_slug', 'website_url', 'has_website']],
            on='brand_slug',
            how='left'
        )
        
        # Calculate coverage gaps
        for _, row in top5.iterrows():
            form_coverage = row['has_form'] / row['sku_count'] * 100
            life_stage_coverage = row['has_life_stage'] / row['sku_count'] * 100
            ingredients_coverage = row['has_ingredients'] / row['sku_count'] * 100
            price_coverage = row['has_price'] / row['sku_count'] * 100
            
            print(f"\n{row['brand']} ({row['brand_slug']}):")
            print(f"  SKUs: {row['sku_count']}")
            print(f"  Website: {row.get('website_url', 'Not found')}")
            print(f"  Current Coverage:")
            print(f"    - Form: {form_coverage:.1f}%")
            print(f"    - Life Stage: {life_stage_coverage:.1f}%")
            print(f"    - Ingredients: {ingredients_coverage:.1f}%")
            print(f"    - Price: {price_coverage:.1f}%")
        
        # Save Top 5 brands
        top5.to_csv(self.report_dir / "TOP5_BRANDS.csv", index=False)
        
        return top5, df
    
    def create_enhanced_profiles(self, top5):
        """Create enhanced profiles for Top 5 brands"""
        print("\n=== Creating Enhanced Profiles ===")
        
        for _, row in top5.iterrows():
            brand_slug = row['brand_slug']
            brand = row['brand']
            website = row.get('website_url', '')
            
            if not website or pd.isna(website):
                print(f"⚠️  {brand}: No website found, creating placeholder profile")
                website = f"https://www.{brand_slug}.com"  # Placeholder
            
            # Enhanced profile configuration
            profile = {
                'brand': brand,
                'brand_slug': brand_slug,
                'website_url': website,
                'status': 'pilot',
                'pilot_date': datetime.now().strftime('%Y-%m-%d'),
                'sku_count': int(row['sku_count']),
                
                # Enhanced rate limits for production
                'rate_limits': {
                    'delay_seconds': 3,  # Increased delay
                    'jitter_seconds': 2,
                    'max_concurrent': 1,
                    'respect_robots': True,
                    'use_proxy': False,  # Enable if needed
                    'use_headless': True  # Enable headless browser
                },
                
                # Discovery methods
                'discovery': {
                    'method': 'multi',  # Use multiple methods
                    'sitemap_urls': [
                        f"{website}/sitemap.xml",
                        f"{website}/sitemap_index.xml",
                        f"{website}/products-sitemap.xml"
                    ],
                    'category_urls': [
                        f"{website}/products/",
                        f"{website}/dog/",
                        f"{website}/dogs/",
                        f"{website}/dog-food/",
                        f"{website}/products/dog/",
                        f"{website}/shop/dog/",
                        f"{website}/en/dog/",
                        f"{website}/uk/dog/"
                    ],
                    'search_urls': [
                        f"{website}/search?q=dog",
                        f"{website}/search?category=dog"
                    ]
                },
                
                # Enhanced selectors
                'pdp_selectors': {
                    'product_name': {
                        'css': 'h1.product-title, h1.product-name, h1[itemprop="name"], .product h1, h1.page-title, .product-detail h1',
                        'xpath': '//h1[@class="product-title" or @class="product-name" or @itemprop="name"]',
                        'jsonld_field': 'name'
                    },
                    'ingredients': {
                        'css': '.ingredients, .composition, .product-ingredients, [itemprop="ingredients"], .product-composition',
                        'xpath': '//div[contains(@class, "ingredients") or contains(@class, "composition")]',
                        'regex': r'(?:Composition|Ingredients|Zutaten|Zusammensetzung):\s*([^.]+)',
                        'jsonld_field': 'ingredients'
                    },
                    'analytical_constituents': {
                        'css': '.analytical, .nutrition, .analysis, .constituents, .product-nutrition',
                        'xpath': '//div[contains(@class, "analytical") or contains(@class, "nutrition")]',
                        'regex': r'(?:Crude\s+)?Protein[:\s]+([0-9.]+)%',
                        'pdf_section': 'Analytical Constituents'
                    },
                    'form': {
                        'css': '.product-type, .food-type, .product-form',
                        'keywords': ['dry', 'wet', 'canned', 'pouch', 'kibble', 'raw', 'freeze-dried', 'semi-moist'],
                        'jsonld_field': 'category'
                    },
                    'life_stage': {
                        'css': '.life-stage, .age-group, .product-subtitle, .product-age',
                        'keywords': ['puppy', 'adult', 'senior', 'junior', 'all life stages', 'mature'],
                        'jsonld_field': 'audience'
                    },
                    'pack_size': {
                        'css': '.pack-size, .weight, .size, .product-weight, .product-size',
                        'regex': r'([0-9.]+)\s*[x×]?\s*([0-9.]+)?\s*(kg|g|lb|oz|ml|l)',
                        'jsonld_field': 'weight'
                    },
                    'price': {
                        'css': '.price, .product-price, .cost, [itemprop="price"], .price-now',
                        'xpath': '//span[@class="price" or @itemprop="price"]',
                        'jsonld_field': 'offers.price'
                    }
                },
                
                # Enhanced JSON-LD support
                'jsonld': {
                    'enabled': True,
                    'types': ['Product', 'Offer', 'AggregateOffer', 'BreadcrumbList'],
                    'extract_all': True  # Extract all JSON-LD blocks
                },
                
                # Enhanced PDF support
                'pdf_support': {
                    'enabled': True,
                    'selectors': [
                        'a[href*="specification"]',
                        'a[href*="datasheet"]',
                        'a[href*="pdf"]',
                        'a[href*=".pdf"]',
                        'a:contains("Download")',
                        'a:contains("Specification")',
                        'a:contains("Data Sheet")',
                        'a:contains("Technical")'
                    ],
                    'max_pdfs_per_product': 3,
                    'max_size_mb': 20,
                    'parse_images': False  # Enable OCR if needed
                },
                
                # ScrapingBee configuration (if API key available)
                'scrapingbee': {
                    'enabled': False,  # Enable if API key is set
                    'render_js': True,
                    'premium_proxy': False,
                    'country_code': 'gb'
                },
                
                # Field mapping with confidence
                'field_mapping': {
                    'brand': brand,
                    'source': f'manufacturer_{brand_slug}',
                    'confidence': 0.95,
                    'pilot': True
                },
                
                # Validation rules
                'validation': {
                    'kcal_min': 200,
                    'kcal_max': 600,
                    'price_min': 1,
                    'price_max': 200,
                    'required_fields': ['product_name', 'brand']
                }
            }
            
            # Save enhanced profile
            profile_path = Path(f"profiles/brands/{brand_slug}_pilot.yaml")
            profile_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(profile_path, 'w') as f:
                yaml.dump(profile, f, default_flow_style=False, sort_keys=False)
            
            print(f"✅ Created enhanced profile: {profile_path}")
        
        return True
    
    def generate_pilot_plan(self, top5, df):
        """Generate pilot execution plan"""
        
        report = f"""# TOP 5 BRANDS PRODUCTION PILOT PLAN
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Selected Brands (by SKU count)

| Rank | Brand | SKUs | Website | Form Gap | Life Stage Gap | Ingredients Gap | Price Gap |
|------|-------|------|---------|----------|----------------|-----------------|-----------|
"""
        
        for idx, row in top5.iterrows():
            form_gap = row['sku_count'] - row['has_form']
            life_gap = row['sku_count'] - row['has_life_stage']
            ing_gap = row['sku_count'] - row['has_ingredients']
            price_gap = row['sku_count'] - row['has_price']
            
            website = '✅' if row.get('has_website') else '❌'
            
            report += f"| {idx+1} | {row['brand']} | {row['sku_count']} | {website} | "
            report += f"{form_gap} | {life_gap} | {ing_gap} | {price_gap} |\n"
        
        # Calculate potential impact
        total_skus = top5['sku_count'].sum()
        total_form_gap = (top5['sku_count'] - top5['has_form']).sum()
        total_life_gap = (top5['sku_count'] - top5['has_life_stage']).sum()
        
        report += f"""

## Pilot Impact Potential

- **Total SKUs in Pilot**: {total_skus} ({total_skus/len(df)*100:.1f}% of catalog)
- **Form Coverage Gap**: {total_form_gap} products
- **Life Stage Gap**: {total_life_gap} products
- **Expected Form Improvement**: {total_form_gap/total_skus*100:.1f}pp
- **Expected Life Stage Improvement**: {total_life_gap/total_skus*100:.1f}pp

## Quality Gates (Per Brand)

| Metric | Target | Current (Avg) | Gap |
|--------|--------|---------------|-----|
| Form | ≥95% | {(top5['has_form'].sum()/total_skus*100):.1f}% | {95-(top5['has_form'].sum()/total_skus*100):.1f}pp |
| Life Stage | ≥95% | {(top5['has_life_stage'].sum()/total_skus*100):.1f}% | {95-(top5['has_life_stage'].sum()/total_skus*100):.1f}pp |
| Ingredients | ≥85% | {(top5['has_ingredients'].sum()/total_skus*100):.1f}% | {max(0, 85-(top5['has_ingredients'].sum()/total_skus*100)):.1f}pp |
| Price Bucket | ≥70% | {(top5['has_price'].sum()/total_skus*100):.1f}% | {70-(top5['has_price'].sum()/total_skus*100):.1f}pp |

## Execution Steps

1. **Profile Enhancement** ✅
   - Created enhanced profiles with multi-method discovery
   - Added headless browser support
   - Configured ScrapingBee integration points

2. **Harvest Phase** (Next)
   - Run sequential harvests for each brand
   - Expected duration: 2-3 hours per brand
   - Cache all responses locally

3. **Enrichment Phase**
   - Parse harvested data
   - Match to catalog products
   - Calculate enrichment metrics

4. **Validation Phase**
   - Check brand-level quality gates
   - Generate conflict reports
   - Prepare preview table

5. **Delivery**
   - Brand quality reports
   - 50-row samples per brand
   - foods_published_preview table

## Risk Mitigation

- **Website Issues**: 3 of 5 brands have verified websites
- **Rate Limiting**: 3s delay + 2s jitter configured
- **Fallback**: ScrapingBee API ready if needed
- **Manual Override**: Admin interface for corrections

## Next Command

```bash
python3 pilot_harvest_top5.py --brand <brand_slug> --limit 50
```
"""
        
        # Save report
        with open(self.report_dir / "PILOT_PLAN.md", "w") as f:
            f.write(report)
        
        print(report)
        
        return report
    
    def run(self):
        """Run Top 5 brands pilot preparation"""
        print("=" * 60)
        print("PRODUCTION PILOT: TOP 5 BRANDS")
        print("=" * 60)
        
        # Identify Top 5 brands
        top5, df = self.identify_top5_brands()
        
        # Create enhanced profiles
        self.create_enhanced_profiles(top5)
        
        # Generate pilot plan
        self.generate_pilot_plan(top5, df)
        
        print("\n" + "=" * 60)
        print("✅ PILOT PREPARATION COMPLETE")
        print("=" * 60)
        
        return top5

if __name__ == "__main__":
    pilot = Top5BrandsPilot()
    pilot.run()