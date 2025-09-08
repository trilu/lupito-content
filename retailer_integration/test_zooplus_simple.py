#!/usr/bin/env python3
"""
Simple test script for Zooplus connector without database dependency
"""
import os
import sys
import json
import requests
from datetime import datetime
from bs4 import BeautifulSoup

def test_zooplus_search():
    """Test Zooplus search functionality"""
    print("🔍 Testing Zooplus Search")
    print("=" * 40)
    
    base_url = "https://www.zooplus.co.uk"
    test_brands = ['Royal Canin', 'Hills', 'Acana']
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    
    results = {}
    
    for brand in test_brands:
        print(f"\n🔎 Testing: {brand}")
        
        try:
            # Test search
            search_url = f"{base_url}/shop/search"
            response = session.get(search_url, params={'q': brand})
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for JSON-LD
                json_ld_scripts = soup.find_all('script', type='application/ld+json')
                json_ld_found = len(json_ld_scripts)
                
                # Look for product elements  
                product_elements = soup.find_all(['article', 'div'], class_=lambda x: x and 'product' in x.lower())
                product_count = len(product_elements)
                
                # Check if brand name appears in results
                page_text = soup.get_text().lower()
                brand_mentioned = brand.lower() in page_text
                
                results[brand] = {
                    'status': 'success',
                    'json_ld_scripts': json_ld_found,
                    'product_elements': product_count,
                    'brand_mentioned': brand_mentioned,
                    'page_size': len(response.text)
                }
                
                print(f"  ✅ Status: {response.status_code}")
                print(f"  📊 JSON-LD scripts: {json_ld_found}")
                print(f"  📦 Product elements: {product_count}")
                print(f"  🏷️  Brand mentioned: {'Yes' if brand_mentioned else 'No'}")
                
            else:
                results[brand] = {
                    'status': 'failed',
                    'error': f'HTTP {response.status_code}'
                }
                print(f"  ❌ HTTP Error: {response.status_code}")
                
        except Exception as e:
            results[brand] = {
                'status': 'error',
                'error': str(e)
            }
            print(f"  ❌ Exception: {e}")
    
    return results


def test_product_page():
    """Test product page parsing"""
    print(f"\n🎯 Testing Product Page")
    print("=" * 40)
    
    # Use a known product URL
    test_url = "https://www.zooplus.co.uk/shop/dogs/dry_dog_food"
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    
    try:
        response = session.get(test_url)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Analyze structured data
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            
            structured_data = []
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)
                    structured_data.append({
                        'type': data.get('@type', 'Unknown'),
                        'has_products': 'Product' in str(data) or 'ItemList' in str(data)
                    })
                except:
                    pass
            
            # Look for nutrition patterns
            page_text = soup.get_text().lower()
            nutrition_found = {
                'protein': 'protein' in page_text,
                'fat': 'fat' in page_text,
                'fiber': 'fiber' in page_text or 'fibre' in page_text,
                'ingredients': 'ingredients' in page_text or 'composition' in page_text
            }
            
            results = {
                'status': 'success',
                'json_ld_count': len(json_ld_scripts),
                'structured_data': structured_data,
                'nutrition_indicators': nutrition_found,
                'page_title': soup.title.string if soup.title else 'N/A'
            }
            
            print(f"  ✅ Status: 200")
            print(f"  📊 JSON-LD scripts: {len(json_ld_scripts)}")
            print(f"  📋 Page title: {results['page_title']}")
            print(f"  🥩 Nutrition indicators found:")
            for nutrient, found in nutrition_found.items():
                print(f"    {nutrient}: {'✅' if found else '❌'}")
            
            return results
            
        else:
            print(f"  ❌ HTTP Error: {response.status_code}")
            return {'status': 'failed', 'error': f'HTTP {response.status_code}'}
            
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        return {'status': 'error', 'error': str(e)}


def main():
    """Run all tests"""
    print("🚀 Zooplus Simple Test Suite")
    print("=" * 50)
    
    # Test search functionality
    search_results = test_zooplus_search()
    
    # Test product page
    product_results = test_product_page()
    
    # Generate summary
    print(f"\n📊 Test Summary")
    print("=" * 40)
    
    successful_searches = sum(1 for r in search_results.values() if r.get('status') == 'success')
    total_searches = len(search_results)
    
    print(f"Search tests: {successful_searches}/{total_searches} passed")
    print(f"Product page test: {'✅ PASS' if product_results.get('status') == 'success' else '❌ FAIL'}")
    
    # Save detailed results
    report = {
        'timestamp': datetime.utcnow().isoformat(),
        'search_results': search_results,
        'product_results': product_results
    }
    
    report_file = f"zooplus_simple_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📋 Detailed results saved to: {report_file}")
    
    # Overall assessment
    overall_success = (
        successful_searches >= 2 and 
        product_results.get('status') == 'success' and
        product_results.get('json_ld_count', 0) > 0
    )
    
    if overall_success:
        print(f"\n🎉 Tests passed! Zooplus appears to be scrapeable.")
        print(f"💡 Recommendations:")
        print(f"   - Use JSON-LD structured data for product extraction")
        print(f"   - Search functionality works well")
        print(f"   - Nutrition data appears to be available")
    else:
        print(f"\n⚠️  Some issues detected. Manual review may be needed.")
    
    return overall_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)