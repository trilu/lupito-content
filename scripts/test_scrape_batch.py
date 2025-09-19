#!/usr/bin/env python3
"""
Test scraping a batch of 50 Zooplus products to validate assumptions
"""

import os
import json
import time
import random
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
import subprocess

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

class BatchTestScraper:
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.test_products = []
        self.results = {
            'total': 0,
            'attempted': 0,
            'successful': 0,
            'failed': 0,
            'with_ingredients': 0,
            'with_nutrition': 0,
            'errors': []
        }
        
    def get_test_batch(self, limit=50):
        """Get a batch of Zooplus products without ingredients"""
        print("\n🔍 Getting test batch of products...")
        
        # Get products with Zooplus URLs but no ingredients
        # Prioritize those from zooplus_csv_import
        batch = self.supabase.table('foods_canonical').select(
            'product_key, product_name, brand, product_url, source'
        ).ilike('product_url', '%zooplus%').is_('ingredients_raw', 'null').limit(limit).execute()
        
        self.test_products = batch.data
        
        # Analyze the batch
        sources = {}
        for product in self.test_products:
            source = product.get('source', 'Unknown')
            sources[source] = sources.get(source, 0) + 1
        
        print(f"\n📦 Found {len(self.test_products)} products to test")
        print("\nProducts by source:")
        for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
            print(f"  {source}: {count}")
        
        # Show sample products
        print("\nSample products:")
        for i, product in enumerate(self.test_products[:5], 1):
            print(f"  {i}. {product['brand']}: {product['product_name'][:50]}...")
            print(f"     URL: {product['product_url'][:70]}...")
        
        return self.test_products
    
    def test_single_scrape(self, product):
        """Test scraping a single product using orchestrated_scraper"""
        try:
            # Prepare command with minimal batch
            cmd = [
                'python', 'scripts/orchestrated_scraper.py',
                '--name', 'test',
                '--country', 'gb',
                '--min-delay', '5',
                '--max-delay', '10',
                '--batch-size', '1',
                '--product-url', product['product_url']
            ]
            
            # Create a temporary script to scrape just this product
            test_script = f'''
import os
import time
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

SCRAPING_BEE = os.getenv('SCRAPING_BEE')
url = "{product['product_url']}"

if SCRAPING_BEE:
    params = {{
        'api_key': SCRAPING_BEE,
        'url': url,
        'render_js': 'true',
        'premium_proxy': 'true',
        'stealth_proxy': 'true',
        'country_code': 'gb',
        'wait': '3000',
        'return_page_source': 'true'
    }}
    
    response = requests.get('https://app.scrapingbee.com/api/v1/', params=params)
    
    result = {{
        'status_code': response.status_code,
        'has_content': len(response.text) > 1000,
        'has_ingredients': 'ingredients' in response.text.lower() or 'composition' in response.text.lower(),
        'has_nutrition': 'protein' in response.text.lower() and 'fat' in response.text.lower(),
        'content_length': len(response.text)
    }}
    
    print(json.dumps(result))
else:
    print(json.dumps({{'error': 'No API key'}}))
'''
            
            # Write and execute test script
            with open('/tmp/test_scrape.py', 'w') as f:
                f.write(test_script)
            
            result = subprocess.run(
                ['python', '/tmp/test_scrape.py'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout:
                try:
                    data = json.loads(result.stdout)
                    return data
                except json.JSONDecodeError:
                    return {'error': 'Invalid JSON response'}
            else:
                return {'error': result.stderr or 'Unknown error'}
                
        except subprocess.TimeoutExpired:
            return {'error': 'Timeout'}
        except Exception as e:
            return {'error': str(e)}
    
    def run_test(self, sample_size=10):
        """Run test on a sample of products"""
        print(f"\n🧪 Testing scraping on {sample_size} products...")
        print("=" * 60)
        
        # Test a sample
        test_sample = random.sample(self.test_products, min(sample_size, len(self.test_products)))
        
        for i, product in enumerate(test_sample, 1):
            print(f"\n[{i}/{sample_size}] Testing: {product['product_name'][:50]}...")
            print(f"  URL: {product['product_url'][:70]}...")
            
            result = self.test_single_scrape(product)
            
            self.results['attempted'] += 1
            
            if 'error' in result:
                print(f"  ❌ Error: {result['error']}")
                self.results['failed'] += 1
                self.results['errors'].append({
                    'product': product['product_key'],
                    'error': result['error']
                })
            elif result.get('status_code') == 200:
                print(f"  ✅ Success! Status: {result['status_code']}")
                print(f"     Content length: {result.get('content_length', 0):,} bytes")
                print(f"     Has ingredients: {result.get('has_ingredients', False)}")
                print(f"     Has nutrition: {result.get('has_nutrition', False)}")
                
                self.results['successful'] += 1
                if result.get('has_ingredients'):
                    self.results['with_ingredients'] += 1
                if result.get('has_nutrition'):
                    self.results['with_nutrition'] += 1
            else:
                print(f"  ⚠️ HTTP {result.get('status_code', 'Unknown')}")
                self.results['failed'] += 1
            
            # Delay between tests
            if i < sample_size:
                delay = random.uniform(10, 20)
                print(f"  Waiting {delay:.1f} seconds...")
                time.sleep(delay)
        
        self.print_summary()
    
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        print(f"\nProducts tested: {self.results['attempted']}")
        print(f"Successful requests: {self.results['successful']}")
        print(f"Failed requests: {self.results['failed']}")
        
        if self.results['successful'] > 0:
            print(f"\nOf successful requests:")
            print(f"  With ingredients: {self.results['with_ingredients']} ({self.results['with_ingredients']/self.results['successful']*100:.1f}%)")
            print(f"  With nutrition: {self.results['with_nutrition']} ({self.results['with_nutrition']/self.results['successful']*100:.1f}%)")
        
        if self.results['errors']:
            print(f"\nErrors encountered:")
            error_types = {}
            for err in self.results['errors']:
                error_type = err['error'].split(':')[0]
                error_types[error_type] = error_types.get(error_type, 0) + 1
            
            for error_type, count in error_types.items():
                print(f"  {error_type}: {count}")
        
        print("\n💡 Conclusions:")
        if self.results['successful'] > 0:
            success_rate = self.results['successful'] / self.results['attempted'] * 100
            ingredients_rate = self.results['with_ingredients'] / self.results['successful'] * 100 if self.results['successful'] > 0 else 0
            
            if success_rate > 80:
                print(f"  ✅ Scraping is working well ({success_rate:.1f}% success rate)")
            elif success_rate > 50:
                print(f"  ⚠️ Scraping partially working ({success_rate:.1f}% success rate)")
            else:
                print(f"  ❌ Scraping has issues ({success_rate:.1f}% success rate)")
            
            if ingredients_rate > 70:
                print(f"  ✅ Good ingredients extraction ({ingredients_rate:.1f}%)")
            elif ingredients_rate > 30:
                print(f"  ⚠️ Some products lack ingredients ({ingredients_rate:.1f}%)")
            else:
                print(f"  ❌ Most products lack ingredients ({ingredients_rate:.1f}%)")
        else:
            print("  ❌ Scraping is not working")

def main():
    tester = BatchTestScraper()
    
    # Get test batch
    products = tester.get_test_batch(50)
    
    if products:
        # Run test on sample
        tester.run_test(sample_size=10)
        
        print("\n" + "=" * 60)
        print("\n🎯 RECOMMENDATIONS:")
        
        if tester.results['successful'] > 5:
            print("  1. Scraping infrastructure is working")
            print("  2. Consider restarting orchestrators with fresh offsets")
            print("  3. Some products may genuinely lack ingredients on Zooplus")
        else:
            print("  1. Check ScrapingBee API credits")
            print("  2. Verify network connectivity")
            print("  3. Check if Zooplus has changed their anti-scraping measures")
    else:
        print("❌ No products found to test")

if __name__ == "__main__":
    main()