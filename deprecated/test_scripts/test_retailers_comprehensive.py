#!/usr/bin/env python3
"""
Comprehensive test of various European pet food retailers
"""
import requests
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urljoin

def test_retailer(name, base_url, category_path, product_selector=None):
    """Generic retailer test function"""
    print(f"\n{'='*60}")
    print(f"🔍 TESTING {name.upper()}")
    print(f"{'='*60}")
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-GB,en;q=0.5'
    })
    
    result = {
        'name': name,
        'accessible': False,
        'products_found': False,
        'nutrition_found': False,
        'json_ld': False,
        'sample_product': None
    }
    
    try:
        # Test main site
        response = session.get(base_url, timeout=10)
        print(f"Main site status: {response.status_code}")
        
        if response.status_code == 200:
            result['accessible'] = True
            print("✓ Site accessible")
            
            # Test category page
            category_url = urljoin(base_url, category_path)
            print(f"\nTesting category: {category_url}")
            
            cat_response = session.get(category_url, timeout=10)
            print(f"Category status: {cat_response.status_code}")
            
            if cat_response.status_code == 200:
                soup = BeautifulSoup(cat_response.content, 'html.parser')
                
                # Check for JSON-LD
                json_ld_scripts = soup.find_all('script', type='application/ld+json')
                if json_ld_scripts:
                    result['json_ld'] = True
                    print(f"✓ Found {len(json_ld_scripts)} JSON-LD scripts")
                    
                    # Try to extract product from JSON-LD
                    for script in json_ld_scripts:
                        try:
                            data = json.loads(script.string)
                            if 'Product' in str(data):
                                print("  ✓ Contains Product schema")
                                break
                        except:
                            pass
                
                # Look for product links
                product_urls = []
                
                # Try provided selector first
                if product_selector:
                    products = soup.select(product_selector)
                    if products:
                        print(f"✓ Found {len(products)} products with selector")
                        for prod in products[:3]:
                            link = prod.find('a', href=True)
                            if link:
                                product_urls.append(urljoin(base_url, link['href']))
                
                # Fallback: find product-like URLs
                if not product_urls:
                    for link in soup.find_all('a', href=True)[:200]:
                        href = link['href']
                        # Common product URL patterns
                        if any(pattern in href for pattern in ['/p/', '/product/', '/artikel/', '-p-', '/item/']):
                            full_url = urljoin(base_url, href)
                            if full_url not in product_urls:
                                product_urls.append(full_url)
                                if len(product_urls) >= 3:
                                    break
                
                if product_urls:
                    result['products_found'] = True
                    print(f"✓ Found {len(product_urls)} product URLs")
                    
                    # Test first product
                    print(f"\nTesting product page...")
                    prod_response = session.get(product_urls[0], timeout=10)
                    
                    if prod_response.status_code == 200:
                        prod_soup = BeautifulSoup(prod_response.content, 'html.parser')
                        page_text = prod_soup.get_text().lower()
                        
                        # Check for nutrition keywords
                        nutrition_keywords = ['protein', 'fat', 'fibre', 'fiber', 'ash', 'analytical', 'constituents']
                        found_keywords = [kw for kw in nutrition_keywords if kw in page_text]
                        
                        if found_keywords and '%' in page_text:
                            result['nutrition_found'] = True
                            print(f"✓ Nutrition keywords found: {', '.join(found_keywords)}")
                        
                        # Extract product name
                        h1 = prod_soup.find('h1')
                        if h1:
                            product_name = h1.get_text(strip=True)
                            result['sample_product'] = product_name[:50]
                            print(f"✓ Product: {product_name[:50]}...")
                
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return result


def main():
    """Test multiple European retailers"""
    
    retailers = [
        # UK Retailers
        {
            'name': 'Amazon UK',
            'base_url': 'https://www.amazon.co.uk',
            'category_path': '/s?k=dry+dog+food&rh=n%3A340840031',
            'selector': 'div[data-component-type="s-search-result"]'
        },
        {
            'name': 'Fetch (UK)',
            'base_url': 'https://www.fetch.co.uk',
            'category_path': '/dog/food/dry-food',
            'selector': 'div.product-item'
        },
        {
            'name': 'Monster Pet Supplies',
            'base_url': 'https://www.monsterpetsupplies.co.uk',
            'category_path': '/dog-supplies/dog-food/dry-dog-food',
            'selector': 'div.product-item'
        },
        {
            'name': 'VioVet',
            'base_url': 'https://www.viovet.co.uk',
            'category_path': '/Dogs-Dry_Dog_Food/c2264/',
            'selector': 'div.product'
        },
        {
            'name': 'Petplanet UK',
            'base_url': 'https://www.petplanet.co.uk',
            'category_path': '/dog/food/dry-dog-food',
            'selector': 'article.product-item'
        },
        
        # German Retailers
        {
            'name': 'Futterhaus',
            'base_url': 'https://www.futterhaus.de',
            'category_path': '/hunde/hundefutter/trockenfutter',
            'selector': 'article.product-item'
        },
        {
            'name': 'Kölle Zoo',
            'base_url': 'https://www.koelle-zoo.de',
            'category_path': '/hund/hundefutter/trockenfutter',
            'selector': 'div.product-item'
        },
        
        # Netherlands
        {
            'name': 'Zooplus NL',
            'base_url': 'https://www.zooplus.nl',
            'category_path': '/shop/honden/hondenvoer/droogvoer',
            'selector': 'article'
        },
        
        # Ireland
        {
            'name': 'Petworld',
            'base_url': 'https://www.petworld.ie',
            'category_path': '/dog/dog-food/dry-dog-food',
            'selector': 'div.product'
        }
    ]
    
    results = []
    
    for retailer in retailers:
        result = test_retailer(
            retailer['name'],
            retailer['base_url'],
            retailer['category_path'],
            retailer.get('selector')
        )
        results.append(result)
    
    # Summary
    print("\n" + "="*60)
    print("📊 SUMMARY OF ALL RETAILERS")
    print("="*60)
    
    accessible = [r for r in results if r['accessible']]
    with_products = [r for r in results if r['products_found']]
    with_nutrition = [r for r in results if r['nutrition_found']]
    with_json_ld = [r for r in results if r['json_ld']]
    
    print(f"\n✅ Accessible: {len(accessible)}/{len(results)}")
    for r in accessible:
        print(f"  - {r['name']}")
    
    print(f"\n📦 Products found: {len(with_products)}/{len(results)}")
    for r in with_products:
        print(f"  - {r['name']}")
        if r['sample_product']:
            print(f"    Sample: {r['sample_product']}")
    
    print(f"\n🥩 Nutrition data: {len(with_nutrition)}/{len(results)}")
    for r in with_nutrition:
        print(f"  - {r['name']}")
    
    print(f"\n📋 JSON-LD support: {len(with_json_ld)}/{len(results)}")
    for r in with_json_ld:
        print(f"  - {r['name']}")
    
    # Recommendations
    print("\n" + "="*60)
    print("🎯 RECOMMENDATIONS")
    print("="*60)
    
    best = [r for r in results if r['accessible'] and r['products_found']]
    if best:
        print("\nBest candidates for scraping:")
        for r in best:
            score = sum([
                r['accessible'],
                r['products_found'],
                r['nutrition_found'],
                r['json_ld']
            ])
            print(f"  {r['name']} (score: {score}/4)")
    else:
        print("\n⚠️  Most retailers have bot protection.")
        print("Consider using:")
        print("  1. ScrapingBee API (you already have this)")
        print("  2. Selenium/Playwright for JavaScript rendering")
        print("  3. Retailer APIs if available")


if __name__ == "__main__":
    main()