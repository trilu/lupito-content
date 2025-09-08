#!/usr/bin/env python3
"""
Test with known Zooplus product URLs to verify the scraping works
"""
import os
import sys
import json
import logging
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from supabase import create_client, Client
import re
from urllib.parse import urljoin

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supabase configuration
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://cibjeqgftuxuezarjsdl.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNpYmplcWdmdHV4dWV6YXJqc2RsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1Mzg1NTY2NywiZXhwIjoyMDY5NDMxNjY3fQ.ngzgvYr2zXisvkz03F86zNWPRHP0tEMX0gQPBm2z_jk')


def test_known_products():
    """Test with actual Zooplus product URLs"""
    
    # Known product URLs from Zooplus
    test_products = [
        {
            'brand': 'Royal Canin',
            'url': 'https://www.zooplus.co.uk/shop/dogs/dry_dog_food/royal_canin_dog_food/royal_canin_maxi/183281'
        },
        {
            'brand': 'Royal Canin',
            'url': 'https://www.zooplus.co.uk/shop/dogs/dry_dog_food/royal_canin_dog_food/royal_canin_medium/775723'
        },
        {
            'brand': "Hill's",
            'url': 'https://www.zooplus.co.uk/shop/dogs/dry_dog_food/hills_dry_dog_food/hills_science_plan_size/156508'
        },
        {
            'brand': 'Acana',
            'url': 'https://www.zooplus.co.uk/shop/dogs/dry_dog_food/acana/798853'
        },
        {
            'brand': 'Orijen',
            'url': 'https://www.zooplus.co.uk/shop/dogs/dry_dog_food/orijen/267755'
        }
    ]
    
    print("\n" + "="*60)
    print("🧪 TESTING WITH KNOWN ZOOPLUS PRODUCT URLs")
    print("="*60)
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    saved_count = 0
    
    for i, product_info in enumerate(test_products, 1):
        print(f"\n[{i}/{len(test_products)}] Testing: {product_info['brand']}")
        print(f"URL: {product_info['url']}")
        print("-"*40)
        
        try:
            response = session.get(product_info['url'], timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract basic info
            product = {
                'retailer_source': 'zooplus',
                'retailer_url': product_info['url'],
                'brand': product_info['brand'],
                'data_source': 'scraper',
                'last_scraped_at': datetime.utcnow().isoformat()
            }
            
            # Extract product ID
            id_match = re.search(r'/(\d+)$', product_info['url'])
            if id_match:
                product['retailer_product_id'] = id_match.group(1)
                print(f"✓ Product ID: {product['retailer_product_id']}")
            
            # Extract title/name
            title = soup.find('title')
            if title:
                product['product_name'] = title.text.split('|')[0].strip()
                print(f"✓ Name: {product['product_name'][:50]}...")
            
            # Look for price
            price_found = False
            for text in soup.stripped_strings:
                if '£' in text:
                    price_match = re.search(r'£([\d.,]+)', text)
                    if price_match:
                        product['retailer_price_eur'] = float(price_match.group(1).replace(',', ''))
                        product['retailer_currency'] = 'GBP'
                        print(f"✓ Price: £{product['retailer_price_eur']}")
                        price_found = True
                        break
            
            # Look for nutrition in page text
            page_text = soup.get_text().lower()
            
            # Protein
            protein_match = re.search(r'protein[:\s]*([0-9.,]+)\s*%', page_text)
            if protein_match:
                product['protein_percent'] = float(protein_match.group(1).replace(',', '.'))
                print(f"✓ Protein: {product['protein_percent']}%")
            
            # Fat
            fat_match = re.search(r'fat[:\s]*([0-9.,]+)\s*%', page_text)
            if fat_match:
                product['fat_percent'] = float(fat_match.group(1).replace(',', '.'))
                print(f"✓ Fat: {product['fat_percent']}%")
            
            # Images
            images = []
            for img in soup.find_all('img')[:10]:
                src = img.get('src', '')
                if 'bilder' in src or 'product' in src:
                    if not src.startswith('http'):
                        src = urljoin('https://www.zooplus.co.uk', src)
                    images.append(src)
            
            if images:
                product['image_url'] = images[0]
                product['image_urls'] = images[:5]
                print(f"✓ Images: {len(images)} found")
            
            # Save to database
            if product.get('product_name'):
                try:
                    response = supabase.table('food_candidates_sc').insert(product).execute()
                    print("✅ SAVED TO DATABASE")
                    saved_count += 1
                except Exception as e:
                    if 'duplicate' in str(e).lower():
                        print("⚠️  Already exists in database")
                    else:
                        print(f"❌ Save error: {e}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "="*60)
    print(f"📊 RESULTS: {saved_count}/{len(test_products)} products saved")
    print("="*60)
    
    return saved_count > 0


if __name__ == "__main__":
    success = test_known_products()
    sys.exit(0 if success else 1)