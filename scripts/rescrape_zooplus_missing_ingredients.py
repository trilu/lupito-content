#!/usr/bin/env python3
"""
Full-scale rescraping of Zooplus products missing ingredients
Uses improved patterns that achieved 80% extraction rate in testing
Prioritizes products with nutrition but no ingredients
"""

import os
import sys
import json
import time
import random
import argparse
from datetime import datetime
from typing import List, Dict
from dotenv import load_dotenv
from supabase import create_client
from google.cloud import storage

# Add scripts to path
sys.path.insert(0, 'scripts')
from orchestrated_scraper import OrchestratedScraper

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")

class ZooplusRescraper:
    def __init__(self, scraper_name: str, country_code: str, batch_size: int, offset: int, prioritize: bool = True):
        self.scraper_name = scraper_name
        self.country_code = country_code
        self.batch_size = batch_size
        self.offset = offset
        self.prioritize = prioritize
        
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(GCS_BUCKET)
        
        # Session tracking
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.session_id = f"rescrape_zooplus_{timestamp}_{scraper_name}"
        self.gcs_folder = f"scraped/zooplus/{self.session_id}"
        
        # Create scraper with improved patterns
        self.scraper = OrchestratedScraper(
            scraper_name, 
            country_code, 
            15, 25,  # 15-25 second delays
            batch_size, 
            offset
        )
        
        self.stats = {
            'total': 0,
            'scraped': 0,
            'with_ingredients': 0,
            'with_nutrition': 0,
            'already_in_gcs': 0,
            'errors': 0
        }
        
    def get_products_to_rescrape(self) -> List[Dict]:
        """Get products missing ingredients, prioritizing those with nutrition"""
        try:
            query = self.supabase.table('foods_canonical').select(
                'product_key, product_name, brand, product_url, protein_percent'
            ).ilike('product_url', '%zooplus.com%')\
            .is_('ingredients_raw', 'null')\
            .not_.ilike('product_name', '%trial%pack%')\
            .not_.ilike('product_name', '%sample%')\
            .range(self.offset, self.offset + self.batch_size - 1)
            
            # Add ordering if prioritizing
            if self.prioritize:
                # Order by: has nutrition first, then by brand reliability
                query = query.order('protein_percent', desc=False, nullsfirst=False)
            
            response = query.execute()
            products = response.data if response.data else []
            
            print(f"[{self.scraper_name}] Found {len(products)} products to rescrape")
            
            # Log product types
            with_nutrition = sum(1 for p in products if p.get('protein_percent'))
            print(f"[{self.scraper_name}] Products with nutrition: {with_nutrition}/{len(products)}")
            
            return products
        except Exception as e:
            print(f"[{self.scraper_name}] Error fetching products: {e}")
            return []
    
    def check_gcs_exists(self, product_key: str) -> bool:
        """Check if product already scraped in GCS"""
        safe_key = product_key.replace('|', '_').replace('/', '_')
        
        # Check recent folders (last 24 hours)
        prefixes = [
            f"scraped/zooplus/rescrape_zooplus_",
            f"scraped/zooplus/test_"
        ]
        
        for prefix in prefixes:
            blob_name = f"{prefix}*/{safe_key}.json"
            # Simple check - would need more sophisticated logic for production
            # For now, we'll just rescrape everything
            
        return False
    
    def run(self):
        """Run the rescraping batch"""
        print(f"\n[{self.scraper_name}] =" * 40)
        print(f"[{self.scraper_name}] STARTING ZOOPLUS RESCRAPER")
        print(f"[{self.scraper_name}] Session: {self.session_id}")
        print(f"[{self.scraper_name}] =" * 40)
        
        products = self.get_products_to_rescrape()
        if not products:
            print(f"[{self.scraper_name}] No products to rescrape")
            return
        
        self.stats['total'] = len(products)
        
        for i, product in enumerate(products, 1):
            print(f"\n[{self.scraper_name}] [{i}/{len(products)}] {product['brand']}: {product['product_name'][:40]}...")
            
            # Check if already scraped
            if self.check_gcs_exists(product['product_key']):
                print(f"[{self.scraper_name}]   ⏭️  Already in GCS, skipping")
                self.stats['already_in_gcs'] += 1
                continue
            
            # Delay between requests (except first)
            if i > 1:
                delay = random.uniform(15, 25)
                print(f"[{self.scraper_name}]   Waiting {delay:.1f}s...")
                time.sleep(delay)
            
            # Scrape product
            result = self.scraper.scrape_product(product['product_url'])
            
            # Add metadata
            result['product_key'] = product['product_key']
            result['brand'] = product.get('brand')
            result['session_id'] = self.session_id
            
            # Check results
            if 'error' in result:
                print(f"[{self.scraper_name}]   ❌ Error: {result['error']}")
                self.stats['errors'] += 1
            else:
                self.stats['scraped'] += 1
                
                if 'ingredients_raw' in result:
                    print(f"[{self.scraper_name}]   ✅ Ingredients: {result['ingredients_raw'][:80]}...")
                    self.stats['with_ingredients'] += 1
                else:
                    print(f"[{self.scraper_name}]   ⚠️  No ingredients found")
                
                if 'nutrition' in result:
                    print(f"[{self.scraper_name}]   ✅ Nutrition: {len(result['nutrition'])} values")
                    self.stats['with_nutrition'] += 1
                
                # Save to GCS
                try:
                    safe_key = product['product_key'].replace('|', '_').replace('/', '_')
                    filename = f"{self.gcs_folder}/{safe_key}.json"
                    blob = self.bucket.blob(filename)
                    blob.upload_from_string(
                        json.dumps(result, indent=2, ensure_ascii=False),
                        content_type='application/json'
                    )
                except Exception as e:
                    print(f"[{self.scraper_name}]   GCS error: {str(e)[:100]}")
            
            # Stop if too many errors
            if self.stats['errors'] >= 5:
                print(f"[{self.scraper_name}] ⚠️  Too many errors, stopping")
                break
        
        self.print_summary()
    
    def print_summary(self):
        """Print scraping summary"""
        print(f"\n[{self.scraper_name}] " + "=" * 40)
        print(f"[{self.scraper_name}] RESCRAPING COMPLETE")
        print(f"[{self.scraper_name}] " + "=" * 40)
        
        print(f"[{self.scraper_name}] Total products: {self.stats['total']}")
        print(f"[{self.scraper_name}] Scraped: {self.stats['scraped']}")
        print(f"[{self.scraper_name}] With ingredients: {self.stats['with_ingredients']}")
        print(f"[{self.scraper_name}] With nutrition: {self.stats['with_nutrition']}")
        print(f"[{self.scraper_name}] Skipped (in GCS): {self.stats['already_in_gcs']}")
        print(f"[{self.scraper_name}] Errors: {self.stats['errors']}")
        
        if self.stats['scraped'] > 0:
            extraction_rate = self.stats['with_ingredients'] / self.stats['scraped'] * 100
            print(f"[{self.scraper_name}] Extraction rate: {extraction_rate:.1f}%")
        
        print(f"[{self.scraper_name}] GCS folder: gs://{GCS_BUCKET}/{self.gcs_folder}/")

def main():
    parser = argparse.ArgumentParser(description='Rescrape Zooplus products missing ingredients')
    parser.add_argument('--name', type=str, required=True, help='Scraper name')
    parser.add_argument('--country', type=str, default='gb', help='Country code')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size')
    parser.add_argument('--offset', type=int, default=0, help='Starting offset')
    parser.add_argument('--no-prioritize', action='store_true', help='Disable prioritization')
    
    args = parser.parse_args()
    
    rescraper = ZooplusRescraper(
        args.name,
        args.country,
        args.batch_size,
        args.offset,
        not args.no_prioritize
    )
    
    rescraper.run()

if __name__ == "__main__":
    main()