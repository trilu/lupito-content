#!/usr/bin/env python3
"""
Quick rescrape for 3 failed URLs (HTTP 503 errors)
"""

import os
import json
import time
import random
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google.cloud import storage

load_dotenv()

SCRAPINGBEE_API_KEY = os.getenv('SCRAPING_BEE')
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")

# URLs that failed with HTTP 503
urls_to_rescrape = [
    ("https://www.zooplus.com/shop/dogs/dry_dog_food/bosch/bosch_senior/317406", "bosch|bosch_adult_mini_senior_dry_dog_food|dry"),
    ("https://www.zooplus.com/shop/dogs/dry_dog_food/hills_science_plan/puppy_junior/2382911", "hillsscienceplan|hillsscienceplanpuppysmallminilam|dry"),
    ("https://www.zooplus.com/shop/dogs/dry_dog_food/lukullus/veggie/2129499", "lukullus|lukullus_veggie_adult_grain-free|dry")
]

def scrape_and_save(url, product_key):
    """Scrape a single URL and save to GCS"""
    
    print(f"🔄 Scraping: {product_key[:50]}...")
    
    try:
        # Use proven working parameters
        params = {
            'api_key': SCRAPINGBEE_API_KEY,
            'url': url,
            'render_js': 'true',
            'premium_proxy': 'true',
            'stealth_proxy': 'true',
            'country_code': 'us',
            'wait': '3000',
            'return_page_source': 'true'
        }
        
        response = requests.get('https://app.scrapingbee.com/api/v1/', params=params)
        
        if response.status_code != 200:
            print(f"   ❌ Failed: HTTP {response.status_code}")
            return False
        
        # Parse and extract data
        soup = BeautifulSoup(response.text, 'html.parser')
        
        product_data = {
            'url': url,
            'product_key': product_key,
            'scraped_at': datetime.now().isoformat()
        }
        
        # Extract ingredients
        for tag in ['dt', 'h3', 'strong']:
            elem = soup.find(tag, string=lambda s: s and 'composition' in s.lower())
            if elem:
                next_elem = elem.find_next_sibling()
                if next_elem:
                    ingredients = next_elem.get_text(strip=True)
                    if len(ingredients) > 20:
                        product_data['ingredients_raw'] = ingredients[:2000]
                        break
        
        # Extract nutrition
        import re
        text = soup.get_text()
        nutrition = {}
        
        patterns = [
            (r'(?:Crude\s+)?Protein[:\s]+(\d+(?:\.\d+)?)\s*%', 'protein_percent'),
            (r'(?:Crude\s+)?(?:Fat|Oils)[:\s]+(\d+(?:\.\d+)?)\s*%', 'fat_percent'),
            (r'(?:Crude\s+)?Fib(?:re|er)[:\s]+(\d+(?:\.\d+)?)\s*%', 'fiber_percent'),
            (r'(?:Crude\s+)?Ash[:\s]+(\d+(?:\.\d+)?)\s*%', 'ash_percent'),
            (r'Moisture[:\s]+(\d+(?:\.\d+)?)\s*%', 'moisture_percent'),
        ]
        
        for pattern, field in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                nutrition[field] = float(match.group(1))
        
        if nutrition:
            product_data['nutrition'] = nutrition
        
        # Save to GCS
        storage_client = storage.Client()
        bucket = storage_client.bucket(GCS_BUCKET)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        folder = f"scraped/zooplus/{timestamp}_quick_rescrape"
        filename = product_key.replace('|', '_').replace('/', '_')[:100] + '.json'
        blob_path = f"{folder}/{filename}"
        
        blob = bucket.blob(blob_path)
        blob.upload_from_string(
            json.dumps(product_data, indent=2),
            content_type='application/json'
        )
        
        print(f"   ✅ Success! Ingredients: {'Yes' if 'ingredients_raw' in product_data else 'No'}, Nutrition: {len(nutrition)} values")
        print(f"   Saved to: gs://{GCS_BUCKET}/{blob_path}")
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)[:100]}")
        return False

def main():
    print("🔄 QUICK RESCRAPE OF 3 FAILED URLS")
    print("=" * 60)
    
    successful = 0
    
    for url, product_key in urls_to_rescrape:
        if scrape_and_save(url, product_key):
            successful += 1
        
        # Delay between requests
        delay = random.uniform(12, 18)
        print(f"   Waiting {delay:.1f} seconds...\n")
        time.sleep(delay)
    
    print("=" * 60)
    print(f"✅ RESCRAPING COMPLETE")
    print(f"   Success: {successful}/3")
    
    if successful > 0:
        print(f"\n💡 Process the rescraped files to update database")

if __name__ == "__main__":
    main()