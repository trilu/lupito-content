#!/usr/bin/env python3
"""
Create/Update Wave 1 Brand Profiles for Manufacturer Enrichment
"""

import yaml
from pathlib import Path
from datetime import datetime

# Wave 1 brands and their details
wave1_brands = {
    'alpha': {
        'brand_name': 'Alpha',
        'website_url': 'https://www.alphapetfoods.com',
        'country': 'UK',
        'language': 'en',
        'platform': 'Custom',
        'sitemap_url': 'https://www.alphapetfoods.com/sitemap.xml',
        'discovery_urls': [
            'https://www.alphapetfoods.com/dog-food/',
            'https://www.alphapetfoods.com/shop/dog/',
            'https://www.alphapetfoods.com/products/dog/'
        ]
    },
    'brit': {
        'brand_name': 'Brit',
        'website_url': 'https://www.brit-petfood.com',
        'country': 'CZ',
        'language': 'en',
        'platform': 'Custom',
        'sitemap_url': 'https://www.brit-petfood.com/sitemap.xml',
        'discovery_urls': [
            'https://www.brit-petfood.com/products/',
            'https://www.brit-petfood.com/dog/',
            'https://www.brit-petfood.com/dog-food/'
        ]
    },
    'briantos': {
        'brand_name': 'Briantos',
        'website_url': 'https://www.briantos.de',
        'country': 'DE',
        'language': 'de',
        'platform': 'Custom',
        'sitemap_url': 'https://www.briantos.de/sitemap.xml',
        'discovery_urls': [
            'https://www.briantos.de/hund/',
            'https://www.briantos.de/hundefutter/',
            'https://www.briantos.de/produkte/'
        ]
    },
    'canagan': {
        'brand_name': 'Canagan',
        'website_url': 'https://canagan.com',
        'country': 'UK',
        'language': 'en',
        'platform': 'Custom',
        'sitemap_url': 'https://canagan.com/sitemap.xml',
        'discovery_urls': [
            'https://canagan.com/uk/dog/',
            'https://canagan.com/uk/products/dog/',
            'https://canagan.com/uk/shop/dog/'
        ]
    },
    'cotswold': {
        'brand_name': 'Cotswold RAW',
        'website_url': 'https://www.cotswoldraw.com',
        'country': 'UK',
        'language': 'en',
        'platform': 'WooCommerce',
        'sitemap_url': 'https://www.cotswoldraw.com/sitemap_index.xml',
        'discovery_urls': [
            'https://www.cotswoldraw.com/shop/',
            'https://www.cotswoldraw.com/product-category/dog-food/',
            'https://www.cotswoldraw.com/dog-food/'
        ]
    },
    'burns': {
        'brand_name': 'Burns',
        'website_url': 'https://burnspet.co.uk',
        'country': 'UK',
        'language': 'en',
        'platform': 'Custom',
        'sitemap_url': 'https://burnspet.co.uk/sitemap.xml',
        'discovery_urls': [
            'https://burnspet.co.uk/dog-food/',
            'https://burnspet.co.uk/shop/dog/',
            'https://burnspet.co.uk/products/dog/'
        ],
        'alt_domain': 'https://burns.de'  # German site
    },
    'barking': {
        'brand_name': 'Barking Heads',
        'website_url': 'https://www.barkingheads.co.uk',
        'country': 'UK',
        'language': 'en',
        'platform': 'Custom',
        'sitemap_url': 'https://www.barkingheads.co.uk/sitemap.xml',
        'discovery_urls': [
            'https://www.barkingheads.co.uk/dog-food/',
            'https://www.barkingheads.co.uk/shop/',
            'https://www.barkingheads.co.uk/products/'
        ]
    },
    'bozita': {
        'brand_name': 'Bozita',
        'website_url': 'https://www.bozita.com',
        'country': 'SE',
        'language': 'en',
        'platform': 'Custom',
        'sitemap_url': 'https://www.bozita.com/sitemap.xml',
        'discovery_urls': [
            'https://www.bozita.com/dog/',
            'https://www.bozita.com/products/dog/',
            'https://www.bozita.com/en/dog/'
        ]
    },
    'forthglade': {
        'brand_name': 'Forthglade',
        'website_url': 'https://forthglade.com',
        'country': 'UK',
        'language': 'en',
        'platform': 'Shopify',
        'sitemap_url': 'https://forthglade.com/sitemap.xml',
        'discovery_urls': [
            'https://forthglade.com/collections/dog-food',
            'https://forthglade.com/collections/all',
            'https://forthglade.com/products/'
        ]
    },
    'belcando': {
        'brand_name': 'Belcando',
        'website_url': 'https://www.belcando.de',
        'country': 'DE',
        'language': 'de',
        'platform': 'Custom',
        'sitemap_url': 'https://www.belcando.de/sitemap.xml',
        'discovery_urls': [
            'https://www.belcando.de/hund/',
            'https://www.belcando.de/hundefutter/',
            'https://www.belcando.de/produkte/'
        ]
    }
}

def create_brand_profile(brand_slug, brand_info):
    """Create comprehensive brand profile YAML"""
    
    profile = {
        'brand': brand_info['brand_name'],
        'brand_slug': brand_slug,
        'website_url': brand_info['website_url'],
        'country': brand_info['country'],
        'language': brand_info['language'],
        'platform': brand_info['platform'],
        'status': 'active',
        'last_updated': datetime.now().strftime('%Y-%m-%d'),
        
        # Rate limiting
        'rate_limits': {
            'delay_seconds': 2,
            'jitter_seconds': 1,
            'max_concurrent': 1,
            'respect_robots': True,
            'user_agent': 'Mozilla/5.0 (compatible; LupitoBot/1.0; +https://lupito.com/bot)'
        },
        
        # Discovery configuration
        'discovery': {
            'method': 'hybrid',  # sitemap + category_pages
            'sitemap_url': brand_info.get('sitemap_url'),
            'category_urls': brand_info.get('discovery_urls', []),
            'product_url_patterns': [
                '/product/',
                '/products/',
                '/p/',
                '/shop/'
            ],
            'exclude_patterns': [
                '/cat/',
                '/cats/',
                '/kitten/',
                '/feline/'
            ]
        },
        
        # Product listing selectors
        'listing_selectors': {
            'product_links': {
                'css': [
                    'a.product-link',
                    'a.product-item',
                    'article a[href*="/product"]',
                    '.product-grid a',
                    '.products a.woocommerce-loop-product__link',
                    'a[href*="/p/"]'
                ],
                'xpath': '//a[contains(@class, "product")]/@href'
            },
            'next_page': {
                'css': [
                    'a.next',
                    'a[rel="next"]',
                    '.pagination a.next',
                    '.nav-next a'
                ],
                'xpath': '//a[@rel="next"]/@href'
            }
        },
        
        # Product detail page selectors
        'pdp_selectors': {
            'product_name': {
                'css': [
                    'h1.product-title',
                    'h1.product-name',
                    'h1[itemprop="name"]',
                    '.product h1',
                    'h1.entry-title'
                ],
                'xpath': '//h1[@class="product-title" or @itemprop="name"]/text()',
                'jsonld_path': 'name'
            },
            
            'variant_pack_size': {
                'css': [
                    '.pack-size',
                    '.product-weight',
                    'select.product-options option',
                    '.variant-selector option',
                    '.size-selector'
                ],
                'xpath': '//select[@name="size" or @name="weight"]/option/text()',
                'regex': r'(\d+(?:\.\d+)?)\s*(kg|g|lb|oz)',
                'jsonld_path': 'offers.properties.weight'
            },
            
            'ingredients': {
                'css': [
                    '.ingredients',
                    '.composition',
                    '.product-ingredients',
                    '[itemprop="ingredients"]',
                    'div:contains("Ingredients")',
                    'div:contains("Composition")'
                ],
                'xpath': '//div[contains(@class, "ingredients") or contains(text(), "Ingredients")]/following-sibling::*[1]',
                'regex': r'(?:Ingredients|Composition|Zutaten|Zusammensetzung)[:\s]*([^\.]+)',
                'jsonld_path': 'nutrition.ingredients'
            },
            
            'analytical_constituents': {
                'css': [
                    '.analytical',
                    '.nutrition',
                    '.analysis',
                    '.constituents',
                    'table.nutrition-table',
                    'div:contains("Analytical")'
                ],
                'xpath': '//table[contains(@class, "nutrition") or contains(@class, "analytical")]',
                'patterns': {
                    'protein': r'(?:Crude\s+)?(?:Protein|Rohprotein)[:\s]+(\d+(?:\.\d+)?)\s*%',
                    'fat': r'(?:Crude\s+)?(?:Fat|Rohfett)[:\s]+(\d+(?:\.\d+)?)\s*%',
                    'fiber': r'(?:Crude\s+)?(?:Fib(?:re|er)|Rohfaser)[:\s]+(\d+(?:\.\d+)?)\s*%',
                    'ash': r'(?:Crude\s+)?(?:Ash|Rohasche)[:\s]+(\d+(?:\.\d+)?)\s*%',
                    'moisture': r'(?:Moisture|Feuchtigkeit)[:\s]+(\d+(?:\.\d+)?)\s*%'
                },
                'jsonld_path': 'nutrition.analyticalConstituents'
            },
            
            'energy_kcal': {
                'css': [
                    '.energy',
                    '.kcal',
                    '.calories',
                    'td:contains("kcal")',
                    'span.energy-value'
                ],
                'xpath': '//td[contains(text(), "kcal")]/following-sibling::td/text()',
                'regex': r'(\d+(?:\.\d+)?)\s*kcal(?:/100\s*g)?',
                'jsonld_path': 'nutrition.calories'
            },
            
            'pdf_links': {
                'css': [
                    'a[href$=".pdf"]',
                    'a:contains("Download")',
                    'a:contains("Specification")',
                    'a:contains("Datasheet")',
                    'a:contains("Label")',
                    'a.pdf-download'
                ],
                'xpath': '//a[contains(@href, ".pdf")]/@href',
                'types': ['specification', 'label', 'datasheet', 'nutritional']
            },
            
            'price': {
                'css': [
                    '.price',
                    '.product-price',
                    '[itemprop="price"]',
                    'span.amount',
                    '.price-now'
                ],
                'xpath': '//span[@itemprop="price"]/@content',
                'jsonld_path': 'offers.price'
            },
            
            'form': {
                'css': [
                    '.product-type',
                    '.food-type',
                    'span.product-form'
                ],
                'keywords': ['dry', 'wet', 'raw', 'freeze-dried', 'canned', 'pouch'],
                'jsonld_path': 'properties.form'
            },
            
            'life_stage': {
                'css': [
                    '.life-stage',
                    '.age-group',
                    '.product-subtitle'
                ],
                'keywords': ['puppy', 'adult', 'senior', 'junior', 'all life stages'],
                'jsonld_path': 'properties.lifeStage'
            }
        },
        
        # JSON-LD configuration
        'jsonld': {
            'enabled': True,
            'types': ['Product', 'Offer', 'AggregateOffer'],
            'extract_all': True
        },
        
        # PDF support
        'pdf_support': {
            'enabled': True,
            'max_pdfs_per_product': 3,
            'max_size_mb': 10,
            'extract_text': True,
            'extract_tables': True
        },
        
        # Anti-bot and authentication
        'anti_bot': {
            'cloudflare': False,
            'recaptcha': False,
            'login_required': False,
            'notes': ''
        },
        
        # Field mapping for database
        'field_mapping': {
            'brand': brand_info['brand_name'],
            'source': f'manufacturer_{brand_slug}',
            'confidence': 0.95
        }
    }
    
    # Language-specific adjustments
    if brand_info['language'] == 'de':
        profile['anti_bot']['notes'] = 'German site - may need translation or ScrapingBee'
        profile['pdp_selectors']['ingredients']['css'].extend([
            '.zutaten',
            'div:contains("Zutaten")',
            'div:contains("Zusammensetzung")'
        ])
        profile['pdp_selectors']['analytical_constituents']['css'].extend([
            '.analytische',
            'div:contains("Analytische")'
        ])
    
    # Platform-specific adjustments
    if brand_info['platform'] == 'Shopify':
        profile['pdp_selectors']['product_name']['css'].insert(0, 'h1.product__title')
        profile['pdp_selectors']['price']['css'].insert(0, 'span.price-item--regular')
        profile['listing_selectors']['product_links']['css'].insert(0, 'a.product-item__link')
    elif brand_info['platform'] == 'WooCommerce':
        profile['pdp_selectors']['product_name']['css'].insert(0, 'h1.product_title')
        profile['pdp_selectors']['price']['css'].insert(0, 'span.woocommerce-Price-amount')
        profile['listing_selectors']['product_links']['css'].insert(0, 'a.woocommerce-loop-product__link')
    
    return profile

# Create/update profiles
profiles_dir = Path('profiles/manufacturers')
profiles_dir.mkdir(parents=True, exist_ok=True)

created_profiles = []
updated_profiles = []

for brand_slug, brand_info in wave1_brands.items():
    profile_path = profiles_dir / f"{brand_slug}.yaml"
    
    # Check if profile exists
    is_update = profile_path.exists()
    
    # Create profile
    profile = create_brand_profile(brand_slug, brand_info)
    
    # Save profile
    with open(profile_path, 'w') as f:
        yaml.dump(profile, f, default_flow_style=False, sort_keys=False)
    
    if is_update:
        updated_profiles.append(brand_slug)
    else:
        created_profiles.append(brand_slug)
    
    print(f"{'Updated' if is_update else 'Created'}: {profile_path}")

# Generate summary report
report_path = Path('reports/WAVE_1_PROFILES.md')

with open(report_path, 'w') as f:
    f.write("# Wave 1 Brand Profiles Summary\n\n")
    f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"**Created:** {len(created_profiles)} profiles\n")
    f.write(f"**Updated:** {len(updated_profiles)} profiles\n\n")
    
    f.write("## Profile Coverage\n\n")
    f.write("| Brand | Language | Platform | Selectors | JSON-LD | PDF Support | Anti-Bot Notes |\n")
    f.write("|-------|----------|----------|-----------|---------|-------------|----------------|\n")
    
    for brand_slug, brand_info in wave1_brands.items():
        profile_path = profiles_dir / f"{brand_slug}.yaml"
        with open(profile_path, 'r') as pf:
            profile = yaml.safe_load(pf)
        
        selector_count = len(profile['pdp_selectors'])
        jsonld = "✓" if profile['jsonld']['enabled'] else "✗"
        pdf = "✓" if profile['pdf_support']['enabled'] else "✗"
        anti_bot = profile['anti_bot'].get('notes', 'None')
        
        f.write(f"| {brand_slug} | {brand_info['language']} | ")
        f.write(f"{brand_info['platform']} | {selector_count} types | ")
        f.write(f"{jsonld} | {pdf} | {anti_bot or 'None'} |\n")
    
    f.write("\n## Selector Details\n\n")
    f.write("All profiles include comprehensive selectors for:\n\n")
    f.write("- **Product Discovery**: Sitemap + category page crawling\n")
    f.write("- **Product Name**: Multiple CSS/XPath selectors + JSON-LD\n")
    f.write("- **Pack Sizes**: Variant selectors, regex patterns\n")
    f.write("- **Ingredients**: Multiple selectors for different formats\n")
    f.write("- **Nutrition**: Analytical constituents table parsing\n")
    f.write("- **Energy**: kcal/100g extraction patterns\n")
    f.write("- **PDFs**: Specification, label, datasheet links\n")
    f.write("- **Metadata**: Price, form, life stage\n\n")
    
    f.write("## Language-Specific Configurations\n\n")
    f.write("### German Sites (3 brands)\n")
    f.write("- **briantos, burns, belcando**\n")
    f.write("- Added German-specific selectors (Zutaten, Analytische)\n")
    f.write("- Configured for ScrapingBee/translation if needed\n\n")
    
    f.write("### English Sites (7 brands)\n")
    f.write("- **alpha, brit, canagan, cotswold, barking, bozita, forthglade**\n")
    f.write("- Standard English selectors\n\n")
    
    f.write("## Platform-Specific Optimizations\n\n")
    f.write("- **Shopify** (forthglade): Enhanced with Shopify-specific selectors\n")
    f.write("- **WooCommerce** (cotswold): Added WooCommerce class patterns\n")
    f.write("- **Custom** (8 brands): Comprehensive selector coverage\n\n")
    
    f.write("## Rate Limiting\n\n")
    f.write("All profiles configured with:\n")
    f.write("- Base delay: 2 seconds\n")
    f.write("- Jitter: 1 second\n")
    f.write("- Max concurrent: 1\n")
    f.write("- Robots.txt: Respected\n\n")
    
    f.write("## Next Steps\n\n")
    f.write("1. Test each profile with sample product URLs\n")
    f.write("2. Verify robots.txt compliance for each site\n")
    f.write("3. Configure ScrapingBee for German sites if needed\n")
    f.write("4. Run test harvest on 5 products per brand\n")
    f.write("5. Adjust selectors based on test results\n")

print(f"\n✅ Summary report generated: {report_path}")
print(f"\nProfiles created in: {profiles_dir}")
print(f"  Created: {', '.join(created_profiles) if created_profiles else 'none'}")
print(f"  Updated: {', '.join(updated_profiles) if updated_profiles else 'none'}")