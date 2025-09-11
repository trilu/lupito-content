#!/usr/bin/env python3
"""
Parallel Multi-Brand Harvester
Harvest multiple brands simultaneously, each in their own thread
This respects per-site rate limits while maximizing overall throughput
"""

import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime
import yaml
import json
from scrapingbee_harvester import ScrapingBeeHarvester

class MultiBrandHarvester:
    def __init__(self, max_brands=3):
        """
        Initialize multi-brand harvester
        max_brands: Number of brands to harvest simultaneously
        """
        self.max_brands = max_brands
        self.stats = {}
        self.lock = threading.Lock()
        self.start_time = time.time()
        
    def harvest_brand(self, brand_config):
        """Harvest a single brand sequentially"""
        brand = brand_config['name']
        urls = brand_config.get('urls', [])
        
        print(f"\n{'='*60}")
        print(f"[{brand.upper()}] Starting harvest of {len(urls)} products")
        print(f"{'='*60}\n")
        
        # Initialize harvester for this brand
        profile_path = Path(f'profiles/manufacturers/{brand}.yaml')
        
        # Create profile if it doesn't exist
        if not profile_path.exists():
            profile_path.parent.mkdir(parents=True, exist_ok=True)
            profile_data = {
                'name': brand,
                'website_url': brand_config.get('base_url', f'https://{brand}.com')
            }
            with open(profile_path, 'w') as f:
                yaml.dump(profile_data, f)
        
        harvester = ScrapingBeeHarvester(brand, profile_path)
        
        # Track stats for this brand
        brand_stats = {
            'total': len(urls),
            'completed': 0,
            'failed': 0,
            'start_time': time.time()
        }
        
        # Harvest products sequentially for this brand
        for i, url in enumerate(urls, 1):
            try:
                print(f"[{brand}] {i}/{len(urls)}: {url.split('/')[-2][:30]}...")
                
                html_content = harvester.fetch_with_scrapingbee(url)
                
                if html_content:
                    # Upload to GCS
                    filename = url.replace('https://', '').replace('/', '_').rstrip('_') + '.html'
                    success = harvester._upload_to_gcs(html_content, filename)
                    
                    if success:
                        brand_stats['completed'] += 1
                        print(f"  ✓ [{brand}] {i}/{len(urls)} success")
                    else:
                        brand_stats['failed'] += 1
                        print(f"  ✗ [{brand}] {i}/{len(urls)} upload failed")
                else:
                    brand_stats['failed'] += 1
                    print(f"  ✗ [{brand}] {i}/{len(urls)} fetch failed")
                    
                # Small delay between requests for same site
                if i < len(urls):
                    time.sleep(2)
                    
            except Exception as e:
                brand_stats['failed'] += 1
                print(f"  ✗ [{brand}] Error: {str(e)[:50]}")
        
        # Calculate final stats
        brand_stats['end_time'] = time.time()
        brand_stats['duration'] = brand_stats['end_time'] - brand_stats['start_time']
        brand_stats['api_credits'] = harvester.stats.get('api_credits_used', 0)
        
        with self.lock:
            self.stats[brand] = brand_stats
        
        print(f"\n[{brand.upper()}] Complete: {brand_stats['completed']}/{brand_stats['total']} in {brand_stats['duration']:.1f}s")
        
        return brand_stats
    
    def harvest_parallel(self, brands_config):
        """Harvest multiple brands in parallel"""
        print(f"\n{'='*80}")
        print(f"PARALLEL MULTI-BRAND HARVEST")
        print(f"Brands: {', '.join([b['name'] for b in brands_config])}")
        print(f"Max parallel brands: {self.max_brands}")
        print(f"{'='*80}\n")
        
        results = {}
        
        with ThreadPoolExecutor(max_workers=self.max_brands) as executor:
            # Submit all brand harvests
            future_to_brand = {
                executor.submit(self.harvest_brand, config): config['name'] 
                for config in brands_config
            }
            
            # Process as they complete
            for future in as_completed(future_to_brand):
                brand = future_to_brand[future]
                try:
                    result = future.result()
                    results[brand] = result
                except Exception as e:
                    print(f"✗ Brand {brand} failed: {e}")
                    results[brand] = {'error': str(e)}
        
        return results
    
    def print_summary(self):
        """Print harvest summary"""
        elapsed = time.time() - self.start_time
        
        print(f"\n{'='*80}")
        print("MULTI-BRAND HARVEST SUMMARY")
        print(f"{'='*80}")
        
        total_products = 0
        total_success = 0
        total_failed = 0
        total_credits = 0
        
        for brand, stats in self.stats.items():
            if 'error' not in stats:
                total_products += stats['total']
                total_success += stats['completed']
                total_failed += stats['failed']
                total_credits += stats.get('api_credits', 0)
                
                print(f"\n{brand.upper()}:")
                print(f"  ✓ Success: {stats['completed']}/{stats['total']}")
                print(f"  ⏱ Time: {stats['duration']:.1f}s")
                print(f"  📊 Rate: {stats['completed']/stats['duration']:.2f} products/sec")
                print(f"  💳 Credits: {stats.get('api_credits', 0)}")
        
        print(f"\n{'='*40}")
        print(f"TOTALS:")
        print(f"  ✓ Products: {total_success}/{total_products}")
        print(f"  ✗ Failed: {total_failed}")
        print(f"  ⏱ Total time: {elapsed:.1f}s")
        print(f"  📊 Overall rate: {total_success/elapsed:.2f} products/sec")
        print(f"  💳 Total credits: {total_credits}")
        print(f"  🎯 Success rate: {total_success/total_products*100:.1f}%")

def load_brand_configs():
    """Load or create brand configurations"""
    
    # Example configurations - can be loaded from file
    configs = []
    
    # Check for Cotswold URLs (if we can find any that work)
    cotswold_urls = []
    if os.path.exists('cotswold_product_urls.txt'):
        with open('cotswold_product_urls.txt', 'r') as f:
            cotswold_urls = [line.strip() for line in f if line.strip()][:20]
    
    if cotswold_urls:
        configs.append({
            'name': 'cotswold',
            'base_url': 'https://www.cotswoldraw.com',
            'urls': cotswold_urls
        })
    
    # Check for other blocked brands we might retry
    blocked_brands = ['briantos', 'belcando', 'bozita']
    
    for brand in blocked_brands:
        url_file = f'{brand}_product_urls.txt'
        if os.path.exists(url_file):
            with open(url_file, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
                
            if urls and brand not in ['belcando', 'bozita']:  # Skip already harvested
                configs.append({
                    'name': brand,
                    'base_url': f'https://www.{brand}.{"de" if brand in ["briantos", "belcando"] else "com"}',
                    'urls': urls[:20]  # Limit for testing
                })
    
    # If no configs, try to discover and harvest new brands
    if not configs:
        print("No pending brands found. Looking for new brands to harvest...")
        
        # Check for brands with discovered URLs but no snapshots
        potential_brands = ['acana', 'orijen', 'hills', 'purina', 'iams']
        
        for brand in potential_brands:
            # Try to discover URLs using existing discovery methods
            profile_path = Path(f'profiles/manufacturers/{brand}.yaml')
            if profile_path.exists():
                # Check if we have URLs discovered
                from deep_product_discovery import DeepProductDiscovery
                try:
                    discoverer = DeepProductDiscovery(brand, profile_path)
                    urls = discoverer.discover_all_products()
                    
                    if urls:
                        configs.append({
                            'name': brand,
                            'base_url': discoverer.base_url,
                            'urls': list(urls)[:30]  # Limit to 30 products per brand
                        })
                        
                        if len(configs) >= 3:  # Max 3 brands for parallel
                            break
                except:
                    continue
    
    return configs

def main():
    """Main function to run multi-brand parallel harvest"""
    
    # Load brand configurations
    brands_config = load_brand_configs()
    
    if not brands_config:
        print("No brands available for harvesting")
        
        # Try to create configs for some easy brands
        easy_brands = [
            {
                'name': 'zooplus',
                'base_url': 'https://www.zooplus.com',
                'urls': [
                    'https://www.zooplus.com/shop/dogs/dry_dog_food/royal_canin',
                    'https://www.zooplus.com/shop/dogs/dry_dog_food/hills_science_plan',
                    'https://www.zooplus.com/shop/dogs/dry_dog_food/purina_pro_plan'
                ]
            },
            {
                'name': 'petco',
                'base_url': 'https://www.petco.com',
                'urls': [
                    'https://www.petco.com/shop/en/petcostore/category/dog/dog-food',
                    'https://www.petco.com/shop/en/petcostore/category/dog/dog-treats'
                ]
            }
        ]
        
        brands_config = easy_brands[:2]
    
    print(f"Found {len(brands_config)} brands to harvest")
    for config in brands_config:
        print(f"  - {config['name']}: {len(config.get('urls', []))} products")
    
    # Initialize multi-brand harvester
    # Use 3-4 parallel brands for optimal throughput
    harvester = MultiBrandHarvester(max_brands=min(3, len(brands_config)))
    
    # Run parallel harvest
    results = harvester.harvest_parallel(brands_config)
    
    # Print summary
    harvester.print_summary()
    
    # Save results
    with open('multi_brand_harvest_results.json', 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'brands': len(brands_config),
            'results': harvester.stats
        }, f, indent=2)
    
    print(f"\n✓ Results saved to multi_brand_harvest_results.json")

if __name__ == "__main__":
    main()