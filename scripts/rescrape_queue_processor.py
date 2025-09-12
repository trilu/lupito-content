#!/usr/bin/env python3
"""
Continuous rescraper that processes URLs from the queue
Run this in the background to continuously rescrape failed products
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

class QueueRescraper:
    def __init__(self):
        self.api_key = SCRAPINGBEE_API_KEY
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(GCS_BUCKET)
        self.queue_file = 'scripts/rescrape_queue.txt'
        self.processed_file = 'scripts/rescrape_processed.txt'
        
        # Session tracking
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.session_id = f"{timestamp}_queue_rescrape"
        self.gcs_folder = f"scraped/zooplus/{self.session_id}"
        
        print(f"🔄 QUEUE RESCRAPER STARTED")
        print(f"   Session: {self.session_id}")
        print(f"   Queue file: {self.queue_file}")
        print("=" * 60)
    
    def get_next_from_queue(self):
        """Get next URL from queue"""
        
        if not os.path.exists(self.queue_file):
            return None, None
        
        # Read all lines
        with open(self.queue_file, 'r') as f:
            lines = f.readlines()
        
        if not lines:
            return None, None
        
        # Get first line
        first_line = lines[0].strip()
        if not first_line or '|' not in first_line:
            # Remove invalid line and try again
            with open(self.queue_file, 'w') as f:
                f.writelines(lines[1:])
            return self.get_next_from_queue()
        
        # Parse URL and product key
        parts = first_line.split('|')
        url = parts[0]
        product_key = '|'.join(parts[1:]) if len(parts) > 1 else ''
        
        # Remove from queue
        with open(self.queue_file, 'w') as f:
            f.writelines(lines[1:])
        
        # Add to processed file
        with open(self.processed_file, 'a') as f:
            f.write(f"{datetime.now().isoformat()}|{first_line}\n")
        
        return url, product_key
    
    def scrape_product(self, url: str, product_key: str) -> Dict:
        """Scrape a single product"""
        
        try:
            params = {
                'api_key': self.api_key,
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
                return {
                    'error': f'HTTP {response.status_code}',
                    'url': url,
                    'product_key': product_key,
                    'scraped_at': datetime.now().isoformat()
                }
            
            # Parse HTML
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
            
            return product_data
            
        except Exception as e:
            return {
                'error': str(e)[:200],
                'url': url,
                'product_key': product_key,
                'scraped_at': datetime.now().isoformat()
            }
    
    def save_to_gcs(self, product_data: Dict, product_key: str) -> bool:
        """Save to GCS"""
        
        try:
            filename = product_key.replace('|', '_').replace('/', '_')[:100] + '.json'
            blob_path = f"{self.gcs_folder}/{filename}"
            
            blob = self.bucket.blob(blob_path)
            blob.upload_from_string(
                json.dumps(product_data, indent=2),
                content_type='application/json'
            )
            
            return True
        except Exception as e:
            print(f"   GCS Error: {e}")
            return False
    
    def run_continuous(self, max_items=None):
        """Process queue continuously"""
        
        processed = 0
        successful = 0
        failed = 0
        
        while True:
            # Get next from queue
            url, product_key = self.get_next_from_queue()
            
            if not url:
                print(f"\n📭 Queue empty - waiting 60 seconds...")
                time.sleep(60)
                
                # Check if we should stop
                if max_items and processed >= max_items:
                    break
                continue
            
            processed += 1
            print(f"\n[{processed}] Rescraping: {product_key[:50]}...")
            print(f"   URL: {url[:80]}...")
            
            # Scrape the product
            result = self.scrape_product(url, product_key)
            
            # Save to GCS
            saved = self.save_to_gcs(result, product_key)
            
            if 'error' not in result and saved:
                successful += 1
                has_ingredients = 'ingredients_raw' in result
                has_nutrition = 'nutrition' in result
                print(f"   ✅ Success! Ingredients: {'Yes' if has_ingredients else 'No'}, Nutrition: {'Yes' if has_nutrition else 'No'}")
            else:
                failed += 1
                error = result.get('error', 'Unknown error')
                print(f"   ❌ Failed: {error[:100]}")
                
                # Re-add to queue if temporary error
                if 'HTTP 503' in error or 'HTTP 429' in error:
                    with open(self.queue_file, 'a') as f:
                        f.write(f"{url}|{product_key}\n")
                    print(f"   🔄 Re-added to queue for retry")
            
            # Show stats
            if processed % 10 == 0:
                print(f"\n📊 Stats: {successful} successful, {failed} failed, {successful+failed} total")
            
            # Delay between requests
            delay = random.uniform(12, 18)
            print(f"   Waiting {delay:.1f} seconds...")
            time.sleep(delay)
            
            # Check if we should stop
            if max_items and processed >= max_items:
                break
        
        # Final summary
        print("\n" + "=" * 60)
        print(f"✅ QUEUE PROCESSING COMPLETE")
        print(f"   Processed: {processed}")
        print(f"   Successful: {successful}")
        print(f"   Failed: {failed}")
        if processed > 0:
            print(f"   Success rate: {successful/processed*100:.1f}%")
        print(f"   GCS folder: gs://{GCS_BUCKET}/{self.gcs_folder}/")

if __name__ == "__main__":
    import sys
    
    # Check for max items argument
    max_items = None
    if len(sys.argv) > 1:
        try:
            max_items = int(sys.argv[1])
            print(f"Processing up to {max_items} items from queue")
        except:
            pass
    
    rescraper = QueueRescraper()
    rescraper.run_continuous(max_items)