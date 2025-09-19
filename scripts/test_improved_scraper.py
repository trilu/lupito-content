#!/usr/bin/env python3
"""
Test improved scraper on 20 Zooplus products missing ingredients
"""

import os
import sys
import json
import time
import random
from datetime import datetime
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

class ImprovedScraperTest:
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(GCS_BUCKET)
        
        # Test session folder
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.session_id = f"test_improved_{timestamp}"
        self.gcs_folder = f"scraped/zooplus/{self.session_id}"
        
        self.results = []
        
    def get_test_products(self, limit=20):
        """Get products missing ingredients from Zooplus"""
        print("🔍 Getting test products...")
        
        response = self.supabase.table('foods_canonical').select(
            'product_key, product_name, brand, product_url'
        ).ilike('product_url', '%zooplus%')\
        .is_('ingredients_raw', 'null')\
        .limit(limit).execute()
        
        return response.data if response.data else []
    
    def run_test(self):
        """Run test with improved scraper"""
        products = self.get_test_products(20)
        
        if not products:
            print("❌ No products found to test")
            return
        
        print(f"\n🧪 TESTING IMPROVED SCRAPER")
        print("="*60)
        print(f"Testing {len(products)} products missing ingredients")
        print(f"Session: {self.session_id}")
        print(f"GCS: gs://{GCS_BUCKET}/{self.gcs_folder}/")
        print()
        
        # Create scraper instance
        scraper = OrchestratedScraper('test_improved', 'gb', 10, 20, 20, 0)
        
        for i, product in enumerate(products, 1):
            print(f"[{i}/{len(products)}] {product['brand']}: {product['product_name'][:40]}...")
            
            # Scrape product
            result = scraper.scrape_product(product['product_url'])
            
            # Add metadata
            result['product_key'] = product['product_key']
            result['original_brand'] = product['brand']
            result['original_name'] = product['product_name']
            
            # Track results
            test_result = {
                'product_key': product['product_key'],
                'product_name': product['product_name'][:50],
                'brand': product['brand'],
                'url': product['product_url'],
                'scraped': 'error' not in result,
                'has_ingredients': 'ingredients_raw' in result,
                'has_nutrition': 'nutrition' in result,
                'ingredients_preview': result.get('ingredients_raw', '')[:100] if 'ingredients_raw' in result else None,
                'nutrition_count': len(result.get('nutrition', {}))
            }
            
            self.results.append(test_result)
            
            # Save to GCS
            if 'error' not in result:
                self.save_to_gcs(product['product_key'], result)
                
                if test_result['has_ingredients']:
                    print(f"  ✅ Ingredients found: {test_result['ingredients_preview']}...")
                else:
                    print(f"  ⚠️ No ingredients found")
                    
                if test_result['has_nutrition']:
                    print(f"  ✅ Nutrition found: {test_result['nutrition_count']} values")
            else:
                print(f"  ❌ Error: {result['error']}")
            
            # Delay between requests
            if i < len(products):
                delay = random.uniform(10, 20)
                print(f"  Waiting {delay:.1f}s...")
                time.sleep(delay)
        
        self.analyze_results()
        self.save_results()
    
    def save_to_gcs(self, product_key: str, data: dict):
        """Save to GCS"""
        try:
            safe_key = product_key.replace('|', '_').replace('/', '_')
            filename = f"{self.gcs_folder}/{safe_key}.json"
            
            blob = self.bucket.blob(filename)
            blob.upload_from_string(
                json.dumps(data, indent=2, ensure_ascii=False),
                content_type='application/json'
            )
            return True
        except Exception as e:
            print(f"    GCS error: {str(e)[:100]}")
            return False
    
    def analyze_results(self):
        """Analyze test results"""
        print("\n" + "="*60)
        print("📊 TEST RESULTS ANALYSIS")
        print("="*60)
        
        total = len(self.results)
        successful = sum(1 for r in self.results if r['scraped'])
        with_ingredients = sum(1 for r in self.results if r['has_ingredients'])
        with_nutrition = sum(1 for r in self.results if r['has_nutrition'])
        
        print(f"\nScraping Success:")
        print(f"  Total attempted: {total}")
        print(f"  Successful scrapes: {successful}/{total} ({successful/total*100:.1f}%)")
        
        print(f"\nData Extraction:")
        print(f"  With ingredients: {with_ingredients}/{successful} ({with_ingredients/successful*100:.1f}% of successful)")
        print(f"  With nutrition: {with_nutrition}/{successful} ({with_nutrition/successful*100:.1f}% of successful)")
        
        print(f"\nOverall Extraction Rate:")
        print(f"  Ingredients: {with_ingredients}/{total} ({with_ingredients/total*100:.1f}% of all attempts)")
        print(f"  Nutrition: {with_nutrition}/{total} ({with_nutrition/total*100:.1f}% of all attempts)")
        
        # List products that still don't have ingredients
        no_ingredients = [r for r in self.results if r['scraped'] and not r['has_ingredients']]
        if no_ingredients:
            print(f"\n⚠️ {len(no_ingredients)} products still missing ingredients after scraping:")
            for r in no_ingredients[:5]:
                print(f"  - {r['brand']}: {r['product_name']}")
        
        # Decision point
        print("\n" + "-"*60)
        print("💡 RECOMMENDATION:")
        
        if successful > 0:
            extraction_rate = with_ingredients / successful * 100
            if extraction_rate >= 95:
                print(f"  ✅ EXCELLENT! {extraction_rate:.1f}% extraction rate")
                print("  → Ready to automate rescraping for all missing products")
            elif extraction_rate >= 70:
                print(f"  ✅ GOOD! {extraction_rate:.1f}% extraction rate")
                print("  → Consider automating with monitoring")
            else:
                print(f"  ⚠️ MODERATE: {extraction_rate:.1f}% extraction rate")
                print("  → May need further pattern improvements")
        
        self.stats = {
            'total': total,
            'successful': successful,
            'with_ingredients': with_ingredients,
            'with_nutrition': with_nutrition,
            'extraction_rate': with_ingredients / successful * 100 if successful > 0 else 0
        }
    
    def save_results(self):
        """Save detailed results"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save detailed results
        with open(f'data/improved_scraper_test_{timestamp}.json', 'w') as f:
            json.dump({
                'session_id': self.session_id,
                'timestamp': timestamp,
                'stats': self.stats,
                'results': self.results
            }, f, indent=2)
        
        print(f"\n💾 Results saved to data/improved_scraper_test_{timestamp}.json")
        print(f"📁 Scraped files in: gs://{GCS_BUCKET}/{self.gcs_folder}/")

def main():
    tester = ImprovedScraperTest()
    tester.run_test()

if __name__ == "__main__":
    main()