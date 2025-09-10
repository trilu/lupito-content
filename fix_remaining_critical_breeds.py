#!/usr/bin/env python3
"""
Fix remaining critical breeds that were not updated
"""

import sys
import time
import random
from pathlib import Path

# Add the jobs directory to the path
sys.path.insert(0, str(Path(__file__).parent / 'jobs'))

from wikipedia_breed_scraper_fixed import WikipediaBreedScraper

# Critical breeds that need fixing (excluding Labrador which is already fixed)
CRITICAL_BREEDS = {
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
    print("FIXING REMAINING CRITICAL BREEDS")
    print("=" * 80)
    print(f"Breeds to fix: {len(CRITICAL_BREEDS)}")
    print()
    
    # Initialize scraper
    scraper = WikipediaBreedScraper()
    
    # Track results
    success = []
    failed = []
    
    for i, (breed_name, url) in enumerate(CRITICAL_BREEDS.items(), 1):
        print(f"[{i}/{len(CRITICAL_BREEDS)}] Processing: {breed_name}")
        print(f"  URL: {url}")
        
        try:
            # Scrape the breed
            breed_data = scraper.scrape_breed(breed_name, url)
            
            if breed_data:
                # Show what we scraped
                print(f"  Scraped data:")
                print(f"    Size: {breed_data.get('size')}")
                print(f"    Weight: {breed_data.get('weight_kg_min')}-{breed_data.get('weight_kg_max')} kg")
                
                # Save to database
                if scraper.save_to_database(breed_data):
                    print(f"  ✅ SUCCESS: {breed_name} updated in database")
                    success.append(breed_name)
                else:
                    print(f"  ❌ FAILED: Could not save to database")
                    failed.append((breed_name, "Database save failed"))
            else:
                print(f"  ❌ FAILED: No data extracted")
                failed.append((breed_name, "No data extracted"))
                
        except Exception as e:
            print(f"  ❌ FAILED: {e}")
            failed.append((breed_name, str(e)))
        
        # Rate limiting (2-4 seconds between requests)
        if i < len(CRITICAL_BREEDS):
            delay = random.uniform(2, 4)
            print(f"  Waiting {delay:.1f}s...")
            time.sleep(delay)
        
        print()
    
    # Summary
    print("=" * 80)
    print("FIXING SUMMARY")
    print("=" * 80)
    print(f"✅ Successfully fixed: {len(success)}/{len(CRITICAL_BREEDS)}")
    for breed in success:
        print(f"   - {breed}")
    
    if failed:
        print(f"\n❌ Failed to fix: {len(failed)}/{len(CRITICAL_BREEDS)}")
        for breed, error in failed:
            print(f"   - {breed}: {error}")
    
    print(f"\nSuccess rate: {len(success)/len(CRITICAL_BREEDS)*100:.1f}%")
    
    # Final verification
    import os
    from dotenv import load_dotenv
    from supabase import create_client
    
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    supabase = create_client(url, key)
    
    print("\n" + "=" * 80)
    print("FINAL VERIFICATION")
    print("=" * 80)
    
    critical_slugs = {
        'German Shepherd': 'german-shepherd',
        'Golden Retriever': 'golden-retriever',
        'French Bulldog': 'french-bulldog',
        'Great Dane': 'great-dane',
        'Rottweiler': 'rottweiler'
    }
    
    for name, slug in critical_slugs.items():
        response = supabase.table('breeds_details').select('size, weight_kg_min, weight_kg_max, updated_at').eq('breed_slug', slug).execute()
        if response.data:
            breed = response.data[0]
            updated_today = '2025-09-10' in breed['updated_at']
            status = '✅' if updated_today else '❌'
            print(f"{status} {name:20s} Size: {breed['size']:10s} Weight: {breed['weight_kg_min']:.1f}-{breed['weight_kg_max']:.1f} kg")

if __name__ == "__main__":
    main()