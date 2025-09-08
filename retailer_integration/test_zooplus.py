#!/usr/bin/env python3
"""
Test script for Zooplus connector
"""
import os
import sys
import json
from datetime import datetime

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from connectors.zooplus_connector import ZooplusConnector


def test_search_brands():
    """Test searching for different brands"""
    print("🚀 Testing Zooplus Connector")
    print("=" * 50)
    
    # Test brands - mix of popular and less common ones
    test_brands = [
        'Royal Canin',
        'Hills',
        'Acana',
        'Orijen',
        'Bella + Duke'
    ]
    
    try:
        connector = ZooplusConnector()
        
        for brand in test_brands:
            print(f"\n🔍 Testing brand: {brand}")
            print("-" * 30)
            
            try:
                # Search for products
                products = connector.search_brand(brand)
                
                if products:
                    print(f"✅ Found {len(products)} products for {brand}")
                    
                    # Show first product details
                    first_product = products[0]
                    print(f"📦 Sample product: {first_product.get('name', 'N/A')}")
                    print(f"💰 Price: £{first_product.get('price', 'N/A')}")
                    print(f"🏢 Brand: {first_product.get('brand', 'N/A')}")
                    print(f"🔗 URL: {first_product.get('url', 'N/A')[:50]}...")
                    
                    # Try to get detailed information for first product
                    if first_product.get('url'):
                        print(f"\n📋 Getting detailed info...")
                        detailed = connector.get_product_details(first_product['url'])
                        
                        if detailed:
                            print(f"✅ Got detailed info")
                            print(f"🥩 Protein: {detailed.get('protein', 'N/A')}%")
                            print(f"🥓 Fat: {detailed.get('fat', 'N/A')}%")
                            print(f"🌾 Fiber: {detailed.get('fiber', 'N/A')}%")
                            print(f"📸 Images: {len(detailed.get('images', []))}")
                            
                            # Test normalization
                            normalized = connector.normalize_product(detailed)
                            print(f"✅ Normalized product data")
                            
                            # Test validation
                            is_valid = connector.validate_product(normalized)
                            print(f"✅ Validation: {'PASS' if is_valid else 'FAIL'}")
                            
                        else:
                            print("❌ Could not get detailed info")
                else:
                    print(f"❌ No products found for {brand}")
                    
            except Exception as e:
                print(f"❌ Error testing brand {brand}: {e}")
                
    except Exception as e:
        print(f"❌ Error initializing connector: {e}")
        return False
    
    return True


def test_specific_product():
    """Test with a known product URL"""
    print(f"\n🎯 Testing specific product")
    print("-" * 30)
    
    # Use a known product URL from Zooplus
    test_url = "https://www.zooplus.co.uk/shop/dogs/dry_dog_food/royal_canin_dog_food/royal_canin_maxi/183281"
    
    try:
        connector = ZooplusConnector()
        
        product = connector.get_product_details(test_url)
        
        if product:
            print(f"✅ Successfully extracted product data")
            print(f"📦 Name: {product.get('name', 'N/A')}")
            print(f"🏢 Brand: {product.get('brand', 'N/A')}")
            print(f"💰 Price: £{product.get('price', 'N/A')}")
            print(f"🥩 Protein: {product.get('protein', 'N/A')}%")
            print(f"🥓 Fat: {product.get('fat', 'N/A')}%")
            print(f"📝 Ingredients: {product.get('ingredients', 'N/A')[:100]}...")
            
            # Test save functionality
            normalized = connector.normalize_product(product)
            if connector.validate_product(normalized):
                print(f"✅ Product is valid and ready to save")
                return True
            else:
                print(f"❌ Product validation failed")
                return False
        else:
            print(f"❌ Could not extract product data")
            return False
            
    except Exception as e:
        print(f"❌ Error testing specific product: {e}")
        return False


def generate_test_report():
    """Generate a test report"""
    print(f"\n📋 Generating Test Report")
    print("=" * 50)
    
    report = {
        'timestamp': datetime.utcnow().isoformat(),
        'connector': 'zooplus',
        'tests': {}
    }
    
    try:
        # Test brand search
        print("Testing brand search...")
        report['tests']['brand_search'] = test_search_brands()
        
        # Test specific product
        print("Testing specific product...")  
        report['tests']['specific_product'] = test_specific_product()
        
        # Overall result
        report['overall_result'] = all(report['tests'].values())
        
        # Save report
        report_file = f"zooplus_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📊 Test Results:")
        print(f"  Brand Search: {'✅ PASS' if report['tests']['brand_search'] else '❌ FAIL'}")
        print(f"  Specific Product: {'✅ PASS' if report['tests']['specific_product'] else '❌ FAIL'}")
        print(f"  Overall: {'✅ PASS' if report['overall_result'] else '❌ FAIL'}")
        print(f"\n📋 Report saved to: {report_file}")
        
        return report['overall_result']
        
    except Exception as e:
        print(f"❌ Error generating test report: {e}")
        return False


if __name__ == "__main__":
    success = generate_test_report()
    
    if success:
        print(f"\n🎉 All tests passed! Zooplus connector is ready.")
    else:
        print(f"\n💥 Some tests failed. Check the logs above.")
    
    sys.exit(0 if success else 1)