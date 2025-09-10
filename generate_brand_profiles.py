#!/usr/bin/env python3
"""
Generate brand profiles for top manufacturers with websites
"""

import pandas as pd
import yaml
from pathlib import Path
from datetime import datetime

# Load manufacturer websites
websites_df = pd.read_csv("reports/MANUF/MANUFACTURER_WEBSITES.csv")

# Filter brands with websites
with_websites = websites_df[websites_df['has_website']]

# Top 5 priority brands
top_brands = with_websites.head(5)

print(f"Generating profiles for {len(top_brands)} brands...")

for _, row in top_brands.iterrows():
    brand_slug = row['brand_slug']
    brand = row['brand']
    website = row['website_url']
    
    # Profile configuration
    profile = {
        'brand': brand,
        'brand_slug': brand_slug,
        'website_url': website,
        'status': 'active',
        'last_updated': datetime.now().strftime('%Y-%m-%d'),
        
        'rate_limits': {
            'delay_seconds': 2,
            'jitter_seconds': 1,
            'max_concurrent': 1,
            'respect_robots': True
        },
        
        'discovery': {
            'method': 'category_pages',
            'category_urls': [
                f"{website}/products/",
                f"{website}/dog/",
                f"{website}/dogs/",
                f"{website}/dog-food/",
                f"{website}/products/dog/",
                f"{website}/shop/dog/"
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
                'regex': r'(?:Crude\s+)?Protein[:\s]+([0-9.]+)%'
            },
            'form': {
                'css': '.product-type, .food-type',
                'keywords': ['dry', 'wet', 'canned', 'pouch', 'kibble', 'raw', 'freeze-dried']
            },
            'life_stage': {
                'css': '.life-stage, .age-group, .product-subtitle',
                'keywords': ['puppy', 'adult', 'senior', 'junior', 'all life stages']
            },
            'pack_size': {
                'css': '.pack-size, .weight, .size, .product-weight',
                'regex': r'([0-9.]+)\s*(kg|g|lb|oz)'
            },
            'price': {
                'css': '.price, .product-price, .cost, [itemprop="price"]',
                'xpath': '//span[@class="price" or @itemprop="price"]'
            }
        },
        
        'jsonld': {
            'enabled': True,
            'types': ['Product', 'Offer', 'AggregateOffer']
        },
        
        'pdf_support': {
            'enabled': True,
            'selectors': [
                'a[href*="specification"]',
                'a[href*="datasheet"]',
                'a[href*="pdf"]',
                'a:contains("Download")',
                'a:contains("Specification")'
            ],
            'max_pdfs_per_product': 2,
            'max_size_mb': 10
        },
        
        'field_mapping': {
            'brand': brand,
            'source': f'manufacturer_{brand_slug}',
            'confidence': 0.95
        }
    }
    
    # Save profile
    profile_path = Path(f"profiles/brands/{brand_slug}.yaml")
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(profile_path, 'w') as f:
        yaml.dump(profile, f, default_flow_style=False, sort_keys=False)
    
    print(f"✅ Created profile: {profile_path}")

print(f"\nProfile generation complete!")
print("\nNext steps:")
print("1. Run harvest for each brand: python3 jobs/brand_harvest.py <brand_slug> --limit 10")
print("2. Process harvested data: python3 manuf_enrichment_pipeline.py")
print("3. Check quality gates in reports/MANUF/")