#!/usr/bin/env python3
"""
Scrape the failed breeds with corrected URLs
"""

import json
import time
import random
import sys
from pathlib import Path

# Add the jobs directory to the path
sys.path.insert(0, str(Path(__file__).parent / 'jobs'))

from wikipedia_breed_scraper_fixed import WikipediaBreedScraper

def load_failed_breeds_corrections():
    """Load the corrections file"""
    with open('failed_breeds_corrections.json', 'r') as f:
        return json.load(f)

def test_url(url):
    """Test if a URL is valid by making a quick request"""
    import requests
    try:
        response = requests.head(url, timeout=5, allow_redirects=True)
        return response.status_code == 200
    except:
        return False

def main():
    # Load corrections
    corrections = load_failed_breeds_corrections()
    
    # Initialize scraper
    scraper = WikipediaBreedScraper()
    
    print("=" * 80)
    print("FAILED BREEDS RE-SCRAPING WITH URL CORRECTIONS")
    print("=" * 80)
    
    # Track results
    results = {
        'success': [],
        'failed': [],
        'skipped': []
    }
    
    # 1. First, handle breeds with _(dog) suffix correction
    print("\n1. PROCESSING BREEDS WITH _(dog) SUFFIX CORRECTIONS")
    print("-" * 60)
    
    for breed_name, urls in corrections['url_corrections'].items():
        print(f"\n[{breed_name}]")
        print(f"  Testing corrected URL: {urls['corrected']}")
        
        # Test if the corrected URL exists
        if test_url(urls['corrected']):
            print(f"  ✓ URL is valid, scraping...")
            
            # Scrape with corrected URL
            try:
                scraper.scrape_breed(breed_name, urls['corrected'])
                print(f"  ✅ SUCCESS: Scraped {breed_name}")
                results['success'].append(breed_name)
            except Exception as e:
                print(f"  ❌ FAILED: {e}")
                results['failed'].append({
                    'breed': breed_name,
                    'url': urls['corrected'],
                    'error': str(e)
                })
        else:
            print(f"  ✗ URL still not valid, skipping")
            results['skipped'].append({
                'breed': breed_name,
                'url': urls['corrected'],
                'reason': 'URL not valid after correction'
            })
        
        # Rate limiting
        delay = random.uniform(3, 7)
        print(f"  Waiting {delay:.1f}s...")
        time.sleep(delay)
    
    # 2. Handle special cases
    print("\n2. PROCESSING SPECIAL CASES")
    print("-" * 60)
    
    special_cases_to_try = [
        ('English Mastiff', 'https://en.wikipedia.org/wiki/English_Mastiff'),
        ('Florida Brown Dog', 'https://en.wikipedia.org/wiki/Florida_Cracker_cur'),
        ('Pachón Navarro', 'https://en.wikipedia.org/wiki/Pachón_Navarro')
    ]
    
    for breed_name, url in special_cases_to_try:
        if url:
            print(f"\n[{breed_name}]")
            print(f"  Testing URL: {url}")
            
            if test_url(url):
                print(f"  ✓ URL is valid, scraping...")
                
                try:
                    scraper.scrape_breed(breed_name, url)
                    print(f"  ✅ SUCCESS: Scraped {breed_name}")
                    results['success'].append(breed_name)
                except Exception as e:
                    print(f"  ❌ FAILED: {e}")
                    results['failed'].append({
                        'breed': breed_name,
                        'url': url,
                        'error': str(e)
                    })
            else:
                print(f"  ✗ URL not valid, skipping")
                results['skipped'].append({
                    'breed': breed_name,
                    'url': url,
                    'reason': 'URL not valid'
                })
            
            # Rate limiting
            delay = random.uniform(3, 7)
            print(f"  Waiting {delay:.1f}s...")
            time.sleep(delay)
    
    # 3. Summary
    print("\n" + "=" * 80)
    print("SCRAPING SUMMARY")
    print("=" * 80)
    print(f"✅ Successfully scraped: {len(results['success'])} breeds")
    for breed in results['success']:
        print(f"   - {breed}")
    
    print(f"\n❌ Failed to scrape: {len(results['failed'])} breeds")
    for item in results['failed']:
        print(f"   - {item['breed']}: {item['error']}")
    
    print(f"\n⏭️ Skipped (invalid URLs): {len(results['skipped'])} breeds")
    for item in results['skipped']:
        print(f"   - {item['breed']}: {item['reason']}")
    
    # Save results
    with open('failed_breeds_scraping_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: failed_breeds_scraping_results.json")
    
    # Calculate final success rate
    total_attempted = len(results['success']) + len(results['failed'])
    if total_attempted > 0:
        success_rate = (len(results['success']) / total_attempted) * 100
        print(f"\nFinal success rate: {success_rate:.1f}% ({len(results['success'])}/{total_attempted})")

if __name__ == "__main__":
    main()