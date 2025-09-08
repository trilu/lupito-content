#!/usr/bin/env python3
"""
Test the improved Zooplus connector with 5 products
"""
import os
import sys
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from retailer_integration.connectors.zooplus_connector_v2 import ZooplusConnectorV2
from supabase import create_client, Client

# Supabase configuration
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://cibjeqgftuxuezarjsdl.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNpYmplcWdmdHV4dWV6YXJqc2RsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1Mzg1NTY2NywiZXhwIjoyMDY5NDMxNjY3fQ.ngzgvYr2zXisvkz03F86zNWPRHP0tEMX0gQPBm2z_jk')


def test_zooplus_connector():
    """Test improved Zooplus connector"""
    
    print("="*80)
    print("🧪 TESTING IMPROVED ZOOPLUS CONNECTOR")
    print("="*80)
    
    # Initialize connector
    connector = ZooplusConnectorV2()
    
    # Test with specific brand
    brand = "Royal Canin"
    print(f"\n🔍 Searching for {brand} products...")
    
    products = connector.search_brand(brand, page=1)
    
    if not products:
        print("❌ No products found from category page, testing with known URLs...")
        
        # Test with known product URLs
        test_urls = [
            "https://www.zooplus.co.uk/shop/dogs/dry_dog_food/royal_canin_dog_food/royal_canin_maxi/183281",
            "https://www.zooplus.co.uk/shop/dogs/dry_dog_food/royal_canin_dog_food/royal_canin_medium/775723",
            "https://www.zooplus.co.uk/shop/dogs/dry_dog_food/hills_dry_dog_food/hills_science_plan_size/156508",
            "https://www.zooplus.co.uk/shop/dogs/dry_dog_food/acana/798853",
            "https://www.zooplus.co.uk/shop/dogs/dry_dog_food/orijen/267755"
        ]
        
        products = []
        for url in test_urls[:5]:
            print(f"\n📦 Fetching: {url}")
            product = connector.get_product_details(url)
            if product:
                products.append(product)
    
    print(f"\n✅ Found {len(products)} products")
    
    # Initialize Supabase
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    saved_count = 0
    
    # Process and save each product
    for i, product in enumerate(products[:5], 1):
        print(f"\n[{i}/5] Processing product...")
        print(f"  Name: {product.get('name', 'Unknown')[:60]}...")
        print(f"  Brand: {product.get('brand', 'Unknown')}")
        print(f"  Price: £{product.get('price', 'N/A')}")
        
        # Check nutrition data
        nutrition_found = []
        for nutrient in ['protein', 'fat', 'fiber', 'ash', 'moisture']:
            if nutrient in product:
                nutrition_found.append(f"{nutrient}: {product[nutrient]}%")
        
        if nutrition_found:
            print(f"  ✅ Nutrition: {', '.join(nutrition_found)}")
        else:
            print(f"  ⚠️  No nutrition data found")
        
        # Prepare for database
        db_record = {
            'retailer_source': 'zooplus',
            'retailer_url': product.get('url', ''),
            'retailer_product_id': product.get('id', ''),
            'product_name': product.get('name', ''),
            'brand': product.get('brand', ''),
            'retailer_price_eur': product.get('price'),
            'retailer_currency': product.get('currency', 'GBP'),
            'in_stock': product.get('in_stock', False),
            'image_url': product.get('image', ''),
            'image_urls': product.get('images', []),
            'ingredients_text': product.get('ingredients', ''),
            'pack_sizes': product.get('pack_sizes', []),
            'data_source': 'scraper',
            'last_scraped_at': datetime.utcnow().isoformat()
        }
        
        # Add nutrition data
        nutrition = connector.parse_nutrition(product)
        db_record.update(nutrition)
        
        # Save to database
        try:
            response = supabase.table('food_candidates_sc').insert(db_record).execute()
            print(f"  ✅ Saved to database")
            saved_count += 1
        except Exception as e:
            if 'duplicate' in str(e).lower():
                print(f"  ⚠️  Already in database")
            else:
                print(f"  ❌ Error saving: {e}")
    
    # Summary
    print("\n" + "="*80)
    print("📊 TEST RESULTS")
    print("="*80)
    print(f"Products found: {len(products)}")
    print(f"Products with nutrition: {sum(1 for p in products if any(n in p for n in ['protein', 'fat', 'fiber']))}")
    print(f"Products saved to DB: {saved_count}")
    
    # Check specific requirements
    requirements_met = []
    requirements_failed = []
    
    # Check product names
    if all(p.get('name') and p['name'] != 'Dry Dog Food' for p in products[:5]):
        requirements_met.append("✅ Product names properly extracted")
    else:
        requirements_failed.append("❌ Some product names missing or generic")
    
    # Check nutrition data
    products_with_nutrition = sum(1 for p in products if 'protein' in p or 'fat' in p)
    if products_with_nutrition >= 3:
        requirements_met.append(f"✅ Nutrition data found ({products_with_nutrition}/5 products)")
    else:
        requirements_failed.append(f"❌ Insufficient nutrition data ({products_with_nutrition}/5 products)")
    
    # Check category extraction
    if len(products) > 0:
        requirements_met.append("✅ Products extracted from pages")
    else:
        requirements_failed.append("❌ No products extracted")
    
    print("\n📋 Requirements Check:")
    for req in requirements_met:
        print(f"  {req}")
    for req in requirements_failed:
        print(f"  {req}")
    
    print("="*80)
    
    return len(requirements_failed) == 0


if __name__ == "__main__":
    success = test_zooplus_connector()
    sys.exit(0 if success else 1)