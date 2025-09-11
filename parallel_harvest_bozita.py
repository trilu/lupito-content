#!/usr/bin/env python3
"""
Parallel harvesting for Bozita products
Process multiple products concurrently to speed up harvesting
"""

import os
import asyncio
import aiohttp
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from datetime import datetime
from scrapingbee_harvester import ScrapingBeeHarvester
import threading

class ParallelHarvester:
    def __init__(self, brand, max_workers=3):
        """
        Initialize parallel harvester
        max_workers: Number of concurrent requests (be careful with API limits)
        """
        self.brand = brand
        self.max_workers = max_workers
        self.harvester = ScrapingBeeHarvester(brand, Path(f'profiles/manufacturers/{brand}.yaml'))
        self.lock = threading.Lock()
        self.stats = {
            'total': 0,
            'completed': 0,
            'failed': 0,
            'start_time': time.time()
        }
    
    def harvest_single_product(self, url, index, total):
        """Harvest a single product (thread-safe)"""
        try:
            print(f"[{index}/{total}] Starting: {url.split('/')[-2][:30]}...")
            
            # Fetch with ScrapingBee
            html_content = self.harvester.fetch_with_scrapingbee(url)
            
            if html_content:
                # Upload to GCS
                filename = url.replace('https://', '').replace('/', '_').rstrip('_') + '.html'
                filename = filename.replace(f'{self.brand}.com_', '')  # Shorten filename
                
                success = self.harvester._upload_to_gcs(html_content, filename)
                
                with self.lock:
                    if success:
                        self.stats['completed'] += 1
                        print(f"  ✓ [{index}/{total}] Success: {url.split('/')[-2][:30]}")
                    else:
                        self.stats['failed'] += 1
                        print(f"  ✗ [{index}/{total}] Upload failed: {url.split('/')[-2][:30]}")
                
                return success
            else:
                with self.lock:
                    self.stats['failed'] += 1
                print(f"  ✗ [{index}/{total}] Fetch failed: {url.split('/')[-2][:30]}")
                return False
                
        except Exception as e:
            with self.lock:
                self.stats['failed'] += 1
            print(f"  ✗ [{index}/{total}] Error: {str(e)[:50]}")
            return False
    
    def harvest_parallel(self, product_urls):
        """Harvest products in parallel"""
        self.stats['total'] = len(product_urls)
        print(f"\n{'='*80}")
        print(f"PARALLEL HARVEST: {len(product_urls)} products with {self.max_workers} workers")
        print(f"{'='*80}\n")
        
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_url = {
                executor.submit(self.harvest_single_product, url, i+1, len(product_urls)): (url, i+1) 
                for i, url in enumerate(product_urls)
            }
            
            # Process as they complete
            for future in as_completed(future_to_url):
                url, index = future_to_url[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    # Print progress
                    if self.stats['completed'] % 10 == 0:
                        elapsed = time.time() - self.stats['start_time']
                        rate = self.stats['completed'] / elapsed if elapsed > 0 else 0
                        remaining = (self.stats['total'] - self.stats['completed']) / rate if rate > 0 else 0
                        print(f"\n>>> Progress: {self.stats['completed']}/{self.stats['total']} "
                              f"({self.stats['completed']/self.stats['total']*100:.1f}%) "
                              f"Rate: {rate:.1f}/sec, ETA: {remaining:.0f}s\n")
                        
                except Exception as e:
                    print(f"  ✗ Exception for {url}: {e}")
                    results.append(False)
        
        return results
    
    def print_summary(self):
        """Print harvest summary"""
        elapsed = time.time() - self.stats['start_time']
        
        print(f"\n{'='*80}")
        print("PARALLEL HARVEST COMPLETE")
        print(f"{'='*80}")
        print(f"✓ Successful: {self.stats['completed']}/{self.stats['total']}")
        print(f"✗ Failed: {self.stats['failed']}")
        print(f"⏱ Time: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
        print(f"📊 Rate: {self.stats['total']/elapsed:.1f} products/second")
        print(f"🎯 Success rate: {self.stats['completed']/self.stats['total']*100:.1f}%")
        
        return self.stats

def main():
    """Main function to run parallel harvest"""
    
    # Check for remaining products
    remaining_file = 'bozita_remaining.txt'
    
    if os.path.exists(remaining_file):
        print(f"Loading remaining products from {remaining_file}")
        with open(remaining_file, 'r') as f:
            product_urls = [line.strip() for line in f if line.strip()]
    else:
        # Load all products
        with open('bozita_product_urls.txt', 'r') as f:
            all_urls = [line.strip() for line in f if line.strip()]
        
        # Skip first 20 that were already done
        product_urls = all_urls[20:]  # Remaining 38 products
        
        # Save remaining for tracking
        with open(remaining_file, 'w') as f:
            for url in product_urls:
                f.write(url + '\n')
    
    print(f"Found {len(product_urls)} products to harvest")
    
    # Initialize parallel harvester
    # Use 3-5 workers for good balance of speed vs API limits
    harvester = ParallelHarvester('bozita', max_workers=4)
    
    # Run parallel harvest
    results = harvester.harvest_parallel(product_urls)
    
    # Print summary
    stats = harvester.print_summary()
    
    # Clean up if all successful
    if stats['completed'] == stats['total']:
        if os.path.exists(remaining_file):
            os.remove(remaining_file)
            print(f"\n✓ Removed {remaining_file} - all products harvested!")
    else:
        # Update remaining file with failed URLs
        failed_urls = [url for i, url in enumerate(product_urls) if not results[i]]
        if failed_urls:
            with open(remaining_file, 'w') as f:
                for url in failed_urls:
                    f.write(url + '\n')
            print(f"\n⚠ {len(failed_urls)} failed URLs saved to {remaining_file}")

if __name__ == "__main__":
    main()