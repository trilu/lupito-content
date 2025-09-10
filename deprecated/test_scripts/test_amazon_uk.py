#!/usr/bin/env python3
"""
Test Amazon UK for dog food product scraping
"""
import requests
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urljoin, quote
from datetime import datetime
from supabase import create_client
import time

# Supabase configuration
SUPABASE_URL = 'https://cibjeqgftuxuezarjsdl.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNpYmplcWdmdHV4dWV6YXJqc2RsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1Mzg1NTY2NywiZXhwIjoyMDY5NDMxNjY3fQ.ngzgvYr2zXisvkz03F86zNWPRHP0tEMX0gQPBm2z_jk'


def extract_nutrition_from_amazon(text):
    """Extract nutrition data from Amazon product page"""
    nutrition = {}
    
    # Amazon often has nutrition in a more structured format
    # Look for analytical constituents or guaranteed analysis
    patterns = {
        'protein_percent': [
            r'protein[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*%',
            r'crude protein[:\s]*\(min\)[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*%'
        ],
        'fat_percent': [
            r'fat[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*%',
            r'crude fat[:\s]*\(min\)[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*%',
            r'oils and fats[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*%'
        ],
        'fiber_percent': [
            r'fibre[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*%',
            r'crude fibre[:\s]*\(max\)[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*%',
            r'fiber[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*%'
        ],
        'ash_percent': [
            r'ash[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*%',
            r'crude ash[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*%'
        ],
        'moisture_percent': [
            r'moisture[:\s]*\(max\)[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*%',
            r'moisture[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*%'
        ]
    }
    
    text_lower = text.lower()
    
    for nutrient, pattern_list in patterns.items():
        for pattern in pattern_list:
            match = re.search(pattern, text_lower)
            if match:
                value = match.group(1).replace(',', '.')
                try:
                    nutrition[nutrient] = float(value)
                    break
                except:
                    pass
    
    return nutrition


def search_brand_on_amazon(brand_name):
    """Search for a brand on Amazon UK"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-GB,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    })
    
    # Search URL - search in pet supplies category for dry dog food
    search_query = f"{brand_name} dry dog food"
    search_url = f"https://www.amazon.co.uk/s?k={quote(search_query)}&rh=n%3A340840031&ref=nb_sb_noss"
    
    print(f"\n🔍 Searching Amazon UK for: {brand_name}")
    print(f"URL: {search_url}")
    
    try:
        response = session.get(search_url, timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find product cards
            products = soup.select('div[data-component-type="s-search-result"]')
            print(f"Found {len(products)} products")
            
            product_data = []
            
            for product in products[:5]:  # Get first 5
                try:
                    data = {}
                    
                    # Get ASIN (Amazon product ID)
                    asin = product.get('data-asin', '')
                    if asin:
                        data['asin'] = asin
                        data['url'] = f"https://www.amazon.co.uk/dp/{asin}"
                    
                    # Get title
                    title_elem = product.find('h2', class_='s-size-mini s-spacing-none s-color-base')
                    if not title_elem:
                        title_elem = product.find('h2')
                    if title_elem:
                        data['title'] = title_elem.get_text(strip=True)
                    
                    # Get price
                    price_elem = product.find('span', class_='a-price-whole')
                    if price_elem:
                        price_text = price_elem.get_text(strip=True).replace(',', '')
                        try:
                            data['price'] = float(price_text.replace('£', ''))
                        except:
                            pass
                    
                    # Get rating
                    rating_elem = product.find('span', class_='a-icon-alt')
                    if rating_elem:
                        rating_text = rating_elem.get_text()
                        rating_match = re.search(r'([0-9.]+) out of', rating_text)
                        if rating_match:
                            data['rating'] = float(rating_match.group(1))
                    
                    # Get image
                    img_elem = product.find('img', class_='s-image')
                    if img_elem:
                        data['image'] = img_elem.get('src', '')
                    
                    if data.get('asin'):
                        product_data.append(data)
                        
                except Exception as e:
                    print(f"Error parsing product: {e}")
            
            return product_data
            
    except Exception as e:
        print(f"Error searching Amazon: {e}")
    
    return []


def get_amazon_product_details(asin):
    """Get detailed product information from Amazon product page"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    })
    
    product_url = f"https://www.amazon.co.uk/dp/{asin}"
    
    try:
        response = session.get(product_url, timeout=30)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            details = {
                'asin': asin,
                'url': product_url
            }
            
            # Get full title
            title_elem = soup.find('span', id='productTitle')
            if title_elem:
                details['title'] = title_elem.get_text(strip=True)
            
            # Get brand
            brand_elem = soup.find('a', id='bylineInfo')
            if brand_elem:
                brand_text = brand_elem.get_text(strip=True)
                brand = brand_text.replace('Visit the', '').replace('Store', '').strip()
                details['brand'] = brand
            
            # Get price
            price_elem = soup.find('span', class_='a-price-whole')
            if price_elem:
                price_text = price_elem.get_text(strip=True).replace(',', '').replace('£', '')
                try:
                    details['price'] = float(price_text)
                except:
                    pass
            
            # Get product description and nutrition
            page_text = soup.get_text()
            
            # Extract nutrition
            nutrition = extract_nutrition_from_amazon(page_text)
            if nutrition:
                details.update(nutrition)
            
            # Look for ingredients
            ingredients_match = re.search(
                r'ingredients[:\s]*([^.]{50,500})',
                page_text,
                re.IGNORECASE
            )
            if ingredients_match:
                details['ingredients'] = ingredients_match.group(1).strip()
            
            # Get main image
            img_elem = soup.find('img', {'data-old-hires': True})
            if not img_elem:
                img_elem = soup.find('img', id='landingImage')
            if img_elem:
                details['image'] = img_elem.get('data-old-hires') or img_elem.get('src')
            
            return details
            
    except Exception as e:
        print(f"Error getting product details: {e}")
    
    return None


def test_amazon_uk():
    """Main test function for Amazon UK"""
    print("="*60)
    print("🛒 TESTING AMAZON UK DOG FOOD SCRAPING")
    print("="*60)
    
    # Test brands
    brands_to_test = [
        "Royal Canin",
        "Hill's Science",
        "Purina",
        "Pedigree",
        "James Wellbeloved"
    ]
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    all_products = []
    products_with_nutrition = 0
    products_saved = 0
    
    for brand in brands_to_test:
        # Search for brand
        products = search_brand_on_amazon(brand)
        
        if products:
            print(f"✓ Found {len(products)} products for {brand}")
            
            # Get details for first product
            if products[0].get('asin'):
                print(f"\n📦 Getting details for: {products[0].get('title', 'Unknown')[:50]}...")
                time.sleep(1)  # Rate limiting
                
                details = get_amazon_product_details(products[0]['asin'])
                
                if details:
                    # Check if has nutrition
                    has_nutrition = any(k.endswith('_percent') for k in details.keys())
                    if has_nutrition:
                        products_with_nutrition += 1
                        nutrition_str = ', '.join(
                            f"{k.replace('_percent', '')}: {v}%" 
                            for k, v in details.items() 
                            if k.endswith('_percent')
                        )
                        print(f"✓ Nutrition: {nutrition_str}")
                    
                    # Prepare for database
                    db_record = {
                        'retailer_source': 'amazon_uk',
                        'retailer_url': details['url'],
                        'retailer_product_id': details['asin'],
                        'product_name': details.get('title', ''),
                        'brand': details.get('brand', brand),
                        'retailer_price_eur': details.get('price'),
                        'retailer_currency': 'GBP',
                        'image_url': details.get('image', ''),
                        'ingredients_text': details.get('ingredients', ''),
                        'data_source': 'scraper',
                        'last_scraped_at': datetime.utcnow().isoformat()
                    }
                    
                    # Add nutrition fields
                    for field in ['protein_percent', 'fat_percent', 'fiber_percent', 'ash_percent', 'moisture_percent']:
                        if field in details:
                            db_record[field] = details[field]
                    
                    # Save to database
                    if db_record['product_name']:
                        try:
                            response = supabase.table('food_candidates_sc').insert(db_record).execute()
                            print("✅ Saved to database")
                            products_saved += 1
                        except Exception as e:
                            if 'duplicate' in str(e).lower():
                                print("⚠️  Already in database")
                            else:
                                print(f"❌ Error saving: {str(e)[:100]}")
                    
                    all_products.append(details)
        
        time.sleep(2)  # Rate limiting between brands
    
    # Summary
    print("\n" + "="*60)
    print("📊 AMAZON UK TEST RESULTS")
    print("="*60)
    print(f"Brands tested: {len(brands_to_test)}")
    print(f"Products found: {len(all_products)}")
    print(f"Products with nutrition: {products_with_nutrition}")
    print(f"Products saved to DB: {products_saved}")
    
    if products_with_nutrition > 0:
        print("\n✅ AMAZON UK IS VIABLE FOR SCRAPING")
        print("Nutrition data is available for many products")
    else:
        print("\n⚠️  Limited nutrition data found")
        print("May need to refine extraction patterns")
    
    return products_saved > 0


if __name__ == "__main__":
    success = test_amazon_uk()