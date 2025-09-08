#!/usr/bin/env python3
"""
Simple test to verify Zooplus scraping works
"""
import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
from supabase import create_client
import os

# Supabase configuration
SUPABASE_URL = 'https://cibjeqgftuxuezarjsdl.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNpYmplcWdmdHV4dWV6YXJqc2RsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1Mzg1NTY2NywiZXhwIjoyMDY5NDMxNjY3fQ.ngzgvYr2zXisvkz03F86zNWPRHP0tEMX0gQPBm2z_jk'


def extract_nutrition(text):
    """Extract nutrition data from text"""
    nutrition = {}
    
    # Patterns for different nutrients
    patterns = {
        'protein_percent': [
            r'[Cc]rude [Pp]rotein[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*%',
            r'[Pp]rotein[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*%'
        ],
        'fat_percent': [
            r'[Cc]rude [Ff]at[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*%',
            r'[Ff]at[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*%'
        ],
        'fiber_percent': [
            r'[Cc]rude [Ff]ibre[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*%',
            r'[Ff]iber[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*%'
        ]
    }
    
    for nutrient, pattern_list in patterns.items():
        for pattern in pattern_list:
            match = re.search(pattern, text)
            if match:
                value = match.group(1).replace(',', '.')
                nutrition[nutrient] = float(value)
                break
    
    return nutrition


def test_products():
    """Test with known product URLs"""
    
    print("="*60)
    print("🧪 TESTING ZOOPLUS PRODUCT SCRAPING")
    print("="*60)
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    # Test products - mix of brands
    test_products = [
        {
            'url': 'https://www.zooplus.co.uk/shop/dogs/dry_dog_food/royal_canin_dog_food/royal_canin_maxi/183281',
            'brand': 'Royal Canin'
        },
        {
            'url': 'https://www.zooplus.co.uk/shop/dogs/dry_dog_food/hills_dry_dog_food/hills_science_plan_size/156508',
            'brand': "Hill's"
        },
        {
            'url': 'https://www.zooplus.co.uk/shop/dogs/dry_dog_food/acana/798853',
            'brand': 'Acana'
        },
        {
            'url': 'https://www.zooplus.co.uk/shop/dogs/dry_dog_food/orijen/267755',
            'brand': 'Orijen'
        },
        {
            'url': 'https://www.zooplus.co.uk/shop/dogs/dry_dog_food/wolf_of_wilderness/wolf_of_wilderness_classic/462834',
            'brand': 'Wolf of Wilderness'
        }
    ]
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    products_saved = 0
    products_with_nutrition = 0
    
    for i, product_info in enumerate(test_products, 1):
        print(f"\n[{i}/{len(test_products)}] Testing: {product_info['brand']}")
        print(f"URL: {product_info['url']}")
        
        try:
            response = session.get(product_info['url'], timeout=30)
            if response.status_code != 200:
                print(f"❌ HTTP {response.status_code}")
                continue
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract product data
            product = {
                'retailer_source': 'zooplus',
                'retailer_url': product_info['url'],
                'brand': product_info['brand'],
                'data_source': 'scraper',
                'last_scraped_at': datetime.utcnow().isoformat()
            }
            
            # Extract product ID from URL
            id_match = re.search(r'/(\d+)/?$', product_info['url'])
            if id_match:
                product['retailer_product_id'] = id_match.group(1)
            
            # Extract product name
            h1 = soup.find('h1')
            if h1:
                product['product_name'] = h1.get_text(strip=True)
            else:
                title = soup.find('title')
                if title:
                    product['product_name'] = title.get_text(strip=True).split('|')[0].strip()
            
            print(f"Name: {product.get('product_name', 'Unknown')[:50]}...")
            
            # Try to get data from JSON-LD
            json_ld_found = False
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    if data.get('@type') == 'Product':
                        json_ld_found = True
                        
                        # Get price
                        offers = data.get('offers', {})
                        if isinstance(offers, dict):
                            product['retailer_price_eur'] = offers.get('price')
                            product['retailer_currency'] = offers.get('priceCurrency', 'GBP')
                        
                        # Get image
                        product['image_url'] = data.get('image', '')
                        
                        # Better product name from JSON-LD
                        if data.get('name'):
                            product['product_name'] = data['name']
                        
                        break
                except:
                    pass
            
            if json_ld_found:
                print("✓ Found JSON-LD data")
            
            # Extract nutrition from page text
            page_text = soup.get_text()
            nutrition = extract_nutrition(page_text)
            
            if nutrition:
                product.update(nutrition)
                products_with_nutrition += 1
                nutrition_str = ', '.join(f"{k.replace('_percent', '')}: {v}%" for k, v in nutrition.items())
                print(f"✓ Nutrition: {nutrition_str}")
            else:
                print("⚠️  No nutrition data found")
            
            # Extract price if not found
            if 'retailer_price_eur' not in product:
                price_match = re.search(r'£([0-9]+(?:\.[0-9]{2})?)', page_text)
                if price_match:
                    product['retailer_price_eur'] = float(price_match.group(1))
                    product['retailer_currency'] = 'GBP'
            
            if 'retailer_price_eur' in product:
                print(f"✓ Price: £{product['retailer_price_eur']}")
            
            # Save to database
            if product.get('product_name') and product['product_name'] != 'Dry Dog Food':
                try:
                    # Remove in_stock field if it exists
                    product.pop('in_stock', None)
                    
                    response = supabase.table('food_candidates_sc').insert(product).execute()
                    print("✅ Saved to database")
                    products_saved += 1
                except Exception as e:
                    if 'duplicate' in str(e).lower():
                        print("⚠️  Already in database")
                    else:
                        print(f"❌ Error: {str(e)[:100]}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("📊 RESULTS SUMMARY")
    print("="*60)
    print(f"Products tested: {len(test_products)}")
    print(f"Products with nutrition: {products_with_nutrition}")
    print(f"Products saved to DB: {products_saved}")
    
    if products_with_nutrition == 0:
        print("\n⚠️  NUTRITION EXTRACTION NEEDS IMPROVEMENT")
        print("Consider checking if Zooplus provides nutrition via:")
        print("  - AJAX/API calls")
        print("  - JavaScript-rendered content")
        print("  - Different URL patterns")
    
    print("="*60)


if __name__ == "__main__":
    test_products()