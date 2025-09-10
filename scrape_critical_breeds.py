#!/usr/bin/env python3
"""
Scrape critical breeds that were missed in the main campaign
"""

import sys
import time
import random
from pathlib import Path

# Add the jobs directory to the path
sys.path.insert(0, str(Path(__file__).parent / 'jobs'))

from wikipedia_breed_scraper_fixed import WikipediaBreedScraper

# Critical breeds with correct Wikipedia URLs
CRITICAL_BREEDS = {
    'Labrador Retriever': 'https://en.wikipedia.org/wiki/Labrador_Retriever',
    'German Shepherd': 'https://en.wikipedia.org/wiki/German_Shepherd',
    'Golden Retriever': 'https://en.wikipedia.org/wiki/Golden_Retriever',
    'French Bulldog': 'https://en.wikipedia.org/wiki/French_Bulldog',
    'Bulldog': 'https://en.wikipedia.org/wiki/Bulldog',
    'Poodle': 'https://en.wikipedia.org/wiki/Poodle',
    'Beagle': 'https://en.wikipedia.org/wiki/Beagle',
    'Rottweiler': 'https://en.wikipedia.org/wiki/Rottweiler',
    'Yorkshire Terrier': 'https://en.wikipedia.org/wiki/Yorkshire_Terrier',
    'Dachshund': 'https://en.wikipedia.org/wiki/Dachshund',
    'Siberian Husky': 'https://en.wikipedia.org/wiki/Siberian_Husky',
    'Great Dane': 'https://en.wikipedia.org/wiki/Great_Dane',
    'Pomeranian': 'https://en.wikipedia.org/wiki/Pomeranian_dog',
    'Shih Tzu': 'https://en.wikipedia.org/wiki/Shih_Tzu',
    'Boston Terrier': 'https://en.wikipedia.org/wiki/Boston_Terrier',
    'Bernese Mountain Dog': 'https://en.wikipedia.org/wiki/Bernese_Mountain_Dog',
    'Cocker Spaniel': 'https://en.wikipedia.org/wiki/Cocker_Spaniel',
    'Cavalier King Charles Spaniel': 'https://en.wikipedia.org/wiki/Cavalier_King_Charles_Spaniel',
    'Boxer': 'https://en.wikipedia.org/wiki/Boxer_(dog)',
    'Pembroke Welsh Corgi': 'https://en.wikipedia.org/wiki/Pembroke_Welsh_Corgi',
}

def main():
    print("=" * 80)
    print("CRITICAL BREEDS WIKIPEDIA SCRAPING")
    print("=" * 80)
    print(f"Breeds to scrape: {len(CRITICAL_BREEDS)}")
    print()
    
    # Initialize scraper
    scraper = WikipediaBreedScraper()
    
    # Track results
    success = []
    failed = []
    
    for i, (breed_name, url) in enumerate(CRITICAL_BREEDS.items(), 1):
        print(f"[{i}/{len(CRITICAL_BREEDS)}] Scraping: {breed_name}")
        print(f"  URL: {url}")
        
        try:
            scraper.scrape_breed(breed_name, url)
            print(f"  ✅ SUCCESS: {breed_name} scraped and saved")
            success.append(breed_name)
        except Exception as e:
            print(f"  ❌ FAILED: {e}")
            failed.append((breed_name, str(e)))
        
        # Rate limiting (3-7 seconds between requests)
        if i < len(CRITICAL_BREEDS):
            delay = random.uniform(3, 7)
            print(f"  Waiting {delay:.1f}s...")
            time.sleep(delay)
        
        print()
    
    # Summary
    print("=" * 80)
    print("SCRAPING SUMMARY")
    print("=" * 80)
    print(f"✅ Successfully scraped: {len(success)}/{len(CRITICAL_BREEDS)}")
    for breed in success:
        print(f"   - {breed}")
    
    if failed:
        print(f"\n❌ Failed to scrape: {len(failed)}/{len(CRITICAL_BREEDS)}")
        for breed, error in failed:
            print(f"   - {breed}: {error}")
    
    print(f"\nSuccess rate: {len(success)/len(CRITICAL_BREEDS)*100:.1f}%")
    
    # Verify Labrador was fixed
    import os
    from dotenv import load_dotenv
    from supabase import create_client
    
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    supabase = create_client(url, key)
    
    print("\n" + "=" * 80)
    print("VERIFICATION: Checking Labrador Retriever")
    print("=" * 80)
    
    response = supabase.table('breeds_details').select('*').eq('breed_slug', 'labrador-retriever').execute()
    if response.data:
        breed = response.data[0]
        print(f"Labrador Retriever in breeds_details:")
        print(f"  Size: {breed.get('size')}")
        print(f"  Weight: {breed.get('weight_kg_min')}-{breed.get('weight_kg_max')} kg")
        print(f"  Updated: {breed.get('updated_at')}")
        
        if breed.get('size') == 'large' and breed.get('weight_kg_min', 0) > 20:
            print("  ✅ SUCCESS: Labrador size and weight CORRECTED!")
        else:
            print("  ❌ WARNING: Labrador still has incorrect data!")

if __name__ == "__main__":
    main()