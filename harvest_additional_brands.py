#!/usr/bin/env python3
"""
Try harvesting additional brands that might be more accessible
Focus on brands that typically have less protection
"""

import os
import requests
from pathlib import Path
from scrapingbee_harvester import ScrapingBeeHarvester
from bs4 import BeautifulSoup
import time

def test_brand_accessibility(brand_name, test_url):
    """Quick test if a brand is accessible"""
    try:
        # Try regular request first
        response = requests.get(test_url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        if response.status_code == 200:
            return 'direct', response.text
        elif response.status_code in [403, 503]:
            # Try with ScrapingBee
            api_key = os.getenv('SCRAPING_BEE')
            params = {
                'api_key': api_key,
                'url': test_url,
                'render_js': 'true',
                'premium_proxy': 'true',
                'stealth_proxy': 'true',
                'wait': '5000',
                'block_ads': 'true',
            }
            
            response = requests.get(
                'https://app.scrapingbee.com/api/v1/',
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                return 'scrapingbee', response.text
        
    except Exception as e:
        pass
    
    return None, None

def discover_and_harvest_brand(brand_info):
    """Discover and harvest a single brand"""
    brand_name = brand_info['name']
    base_url = brand_info['url']
    test_url = brand_info.get('test_url', base_url)
    
    print(f"\n{'='*60}")
    print(f"Testing: {brand_name}")
    print(f"URL: {base_url}")
    print(f"{'='*60}")
    
    # Test accessibility
    access_method, html = test_brand_accessibility(brand_name, test_url)
    
    if not access_method:
        print(f"✗ {brand_name} is not accessible")
        return False
    
    print(f"✓ {brand_name} is accessible via {access_method}")
    
    # Try to discover products
    products = []
    soup = BeautifulSoup(html, 'html.parser')
    
    # Look for product links
    for link in soup.find_all('a', href=True):
        href = link.get('href', '')
        if any(keyword in href.lower() for keyword in ['product', 'artikel', 'item', '/p/', 'detail']):
            if href.startswith('/'):
                full_url = base_url.rstrip('/') + href
            elif not href.startswith('http'):
                full_url = base_url.rstrip('/') + '/' + href
            else:
                full_url = href
            
            if base_url.replace('www.', '') in full_url:
                products.append(full_url.split('?')[0])
    
    products = list(set(products))[:20]  # Limit to 20 for testing
    
    if products:
        print(f"✓ Found {len(products)} products")
        
        # Save URLs
        with open(f'{brand_name}_discovered_urls.txt', 'w') as f:
            for url in products:
                f.write(url + '\n')
        
        # Try to harvest a few
        if access_method == 'scrapingbee':
            print(f"\nHarvesting {brand_name} with ScrapingBee...")
            profile_path = Path(f'profiles/manufacturers/{brand_name}.yaml')
            if not profile_path.exists():
                profile_path.parent.mkdir(parents=True, exist_ok=True)
                import yaml
                with open(profile_path, 'w') as f:
                    yaml.dump({'name': brand_name, 'website_url': base_url}, f)
            
            harvester = ScrapingBeeHarvester(brand_name, profile_path)
            harvest_stats = harvester.harvest_products(products[:5])  # Test with 5
            
            if harvest_stats.get('snapshots_created', 0) > 0:
                print(f"✅ Successfully harvested {harvest_stats['snapshots_created']} {brand_name} products")
                return True
        else:
            print(f"✅ {brand_name} accessible directly (no ScrapingBee needed)")
            return True
    else:
        print(f"⚠ No products found for {brand_name}")
    
    return False

def main():
    """Test multiple brands"""
    
    print("="*80)
    print("TESTING ADDITIONAL BRANDS FOR HARVESTING")
    print("="*80)
    
    # Brands to test
    brands_to_test = [
        {
            'name': 'hills',
            'url': 'https://www.hillspet.com',
            'test_url': 'https://www.hillspet.com/dog-food'
        },
        {
            'name': 'purina',
            'url': 'https://www.purina.com',
            'test_url': 'https://www.purina.com/dogs/dog-food'
        },
        {
            'name': 'iams',
            'url': 'https://www.iams.com',
            'test_url': 'https://www.iams.com/dog'
        },
        {
            'name': 'eukanuba',
            'url': 'https://www.eukanuba.com',
            'test_url': 'https://www.eukanuba.com/us/products/dogs'
        },
        {
            'name': 'acana',
            'url': 'https://www.acana.com',
            'test_url': 'https://www.acana.com/en-US/dogs/dog-food'
        },
        {
            'name': 'orijen',
            'url': 'https://www.orijen.com',
            'test_url': 'https://www.orijen.com/en-US/dogs/dog-food'
        },
        {
            'name': 'taste-of-the-wild',
            'url': 'https://www.tasteofthewildpetfood.com',
            'test_url': 'https://www.tasteofthewildpetfood.com/dog-formulas/'
        },
        {
            'name': 'wellness',
            'url': 'https://www.wellnesspetfood.com',
            'test_url': 'https://www.wellnesspetfood.com/dog-food'
        }
    ]
    
    successful_brands = []
    failed_brands = []
    
    for brand_info in brands_to_test:
        success = discover_and_harvest_brand(brand_info)
        
        if success:
            successful_brands.append(brand_info['name'])
        else:
            failed_brands.append(brand_info['name'])
        
        # Small delay between brands
        time.sleep(2)
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    if successful_brands:
        print(f"\n✅ Successful brands ({len(successful_brands)}):")
        for brand in successful_brands:
            print(f"  - {brand}")
    
    if failed_brands:
        print(f"\n❌ Failed brands ({len(failed_brands)}):")
        for brand in failed_brands:
            print(f"  - {brand}")
    
    print(f"\nSuccess rate: {len(successful_brands)}/{len(brands_to_test)} brands")
    
    if successful_brands:
        print("\n" + "="*80)
        print("NEXT STEPS")
        print("="*80)
        print("For successful brands, you can now:")
        print("1. Review the discovered URLs in [brand]_discovered_urls.txt")
        print("2. Run full harvest with ScrapingBeeHarvester")
        print("3. Parse the harvested snapshots from GCS")

if __name__ == "__main__":
    main()