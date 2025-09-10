#!/usr/bin/env python3
"""
Fix size accuracy issues in breeds_details table.
This script identifies and corrects breeds with incorrect size categorization.
"""

import os
import sys
import time
import random
from pathlib import Path
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

# Add jobs directory to path for scraper import
sys.path.insert(0, str(Path(__file__).parent / 'jobs'))
from wikipedia_breed_scraper_fixed import WikipediaBreedScraper

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)

def get_expected_size(weight_max):
    """Calculate expected size based on weight"""
    if pd.isna(weight_max):
        return None
    
    weight = float(weight_max)
    if weight < 4:
        return 'tiny'
    elif weight < 10:
        return 'small'
    elif weight < 25:
        return 'medium'
    elif weight < 45:
        return 'large'
    else:
        return 'giant'

def identify_problematic_breeds():
    """Identify breeds that need fixing"""
    print("=" * 80)
    print("IDENTIFYING PROBLEMATIC BREEDS")
    print("=" * 80)
    
    # Fetch all breeds from breeds_details
    response = supabase.table('breeds_details').select('*').execute()
    df = pd.DataFrame(response.data)
    
    problematic_breeds = []
    
    # 1. Breeds with size/weight mismatch
    df_with_weights = df[df['weight_kg_max'].notna()].copy()
    df_with_weights['expected_size'] = df_with_weights['weight_kg_max'].apply(get_expected_size)
    df_with_weights['size_mismatch'] = df_with_weights['size'] != df_with_weights['expected_size']
    
    mismatched = df_with_weights[df_with_weights['size_mismatch']]
    for _, breed in mismatched.iterrows():
        problematic_breeds.append({
            'breed_slug': breed['breed_slug'],
            'display_name': breed['display_name'],
            'issue': 'size_mismatch',
            'current_size': breed['size'],
            'expected_size': breed['expected_size'],
            'weight': f"{breed['weight_kg_min']}-{breed['weight_kg_max']}kg"
        })
    
    # 2. Breeds with NULL weight but assigned size (should be NULL)
    null_weight_with_size = df[(df['weight_kg_max'].isna()) & (df['size'].notna())]
    for _, breed in null_weight_with_size.iterrows():
        problematic_breeds.append({
            'breed_slug': breed['breed_slug'],
            'display_name': breed['display_name'],
            'issue': 'null_weight_with_size',
            'current_size': breed['size'],
            'expected_size': None,
            'weight': 'NULL'
        })
    
    print(f"\nFound {len(problematic_breeds)} problematic breeds:")
    print(f"  - Size/weight mismatch: {len(mismatched)}")
    print(f"  - NULL weight with size: {len(null_weight_with_size)}")
    
    return problematic_breeds

def fix_breed_directly(breed_info):
    """Fix a breed's size directly in the database"""
    try:
        update_data = {}
        
        if breed_info['issue'] == 'size_mismatch':
            # Update size to match weight
            update_data['size'] = breed_info['expected_size']
        elif breed_info['issue'] == 'null_weight_with_size':
            # Set size to NULL when weight is NULL
            update_data['size'] = None
        
        # Update the database
        response = supabase.table('breeds_details').update(update_data).eq('breed_slug', breed_info['breed_slug']).execute()
        
        return True
    except Exception as e:
        print(f"    Error updating {breed_info['display_name']}: {e}")
        return False

def get_wikipedia_url(breed_slug):
    """Try to find Wikipedia URL for a breed"""
    # Common patterns for Wikipedia URLs
    breed_name = breed_slug.replace('-', '_').title()
    possible_urls = [
        f"https://en.wikipedia.org/wiki/{breed_name}",
        f"https://en.wikipedia.org/wiki/{breed_name}_(dog)",
        f"https://en.wikipedia.org/wiki/{breed_slug.replace('-', '_')}",
    ]
    
    # Check if we have a URL in wikipedia_urls.txt
    urls_file = Path('wikipedia_urls.txt')
    if urls_file.exists():
        with open(urls_file, 'r') as f:
            for line in f:
                if '|' in line:
                    name, url = line.strip().split('|', 1)
                    if name.lower().replace(' ', '-') == breed_slug:
                        return url
    
    return possible_urls[0]  # Default to first pattern

def main():
    print("=" * 80)
    print("BREED SIZE ACCURACY FIX")
    print("=" * 80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Identify problematic breeds
    problematic_breeds = identify_problematic_breeds()
    
    if not problematic_breeds:
        print("\nNo problematic breeds found!")
        return
    
    # Show sample of issues
    print("\nSample of issues to fix:")
    for breed in problematic_breeds[:10]:
        arrow = "→" if breed['expected_size'] else "→ NULL"
        print(f"  {breed['display_name']:30s}: {breed['current_size']:10s} {arrow:5s} {breed['expected_size'] or 'NULL':10s} ({breed['weight']})")
    
    # Ask for confirmation
    print(f"\nThis will fix {len(problematic_breeds)} breeds.")
    response = input("Proceed with fixes? (yes/no): ")
    
    if response.lower() != 'yes':
        print("Aborted.")
        return
    
    # Fix breeds
    print("\n" + "=" * 80)
    print("APPLYING FIXES")
    print("=" * 80)
    
    fixed_count = 0
    failed_count = 0
    scraper = None
    
    for i, breed in enumerate(problematic_breeds, 1):
        print(f"\n[{i}/{len(problematic_breeds)}] Fixing: {breed['display_name']}")
        
        # For breeds with NULL weight, we can directly fix
        if breed['issue'] == 'null_weight_with_size':
            print(f"  Setting size to NULL (weight is NULL)")
            if fix_breed_directly(breed):
                fixed_count += 1
                print(f"  ✅ Fixed")
            else:
                failed_count += 1
                print(f"  ❌ Failed")
        
        # For size mismatches, we have two options:
        # Option 1: Direct database update (faster)
        # Option 2: Re-scrape from Wikipedia (more thorough but slower)
        else:
            # Option 1: Direct fix (recommended for speed)
            print(f"  Updating size: {breed['current_size']} → {breed['expected_size']}")
            if fix_breed_directly(breed):
                fixed_count += 1
                print(f"  ✅ Fixed")
            else:
                failed_count += 1
                print(f"  ❌ Failed")
            
            # Option 2: Re-scrape (uncomment if you want thorough re-scraping)
            # if not scraper:
            #     scraper = WikipediaBreedScraper()
            # 
            # url = get_wikipedia_url(breed['breed_slug'])
            # print(f"  Re-scraping from: {url}")
            # 
            # try:
            #     breed_data = scraper.scrape_breed(breed['display_name'], url)
            #     if breed_data and scraper.save_to_database(breed_data):
            #         fixed_count += 1
            #         print(f"  ✅ Re-scraped and saved")
            #     else:
            #         failed_count += 1
            #         print(f"  ❌ Failed to scrape/save")
            # except Exception as e:
            #     failed_count += 1
            #     print(f"  ❌ Error: {e}")
            # 
            # # Rate limiting for scraping
            # if i < len(problematic_breeds):
            #     delay = random.uniform(1, 2)
            #     time.sleep(delay)
    
    # Summary
    print("\n" + "=" * 80)
    print("FIX SUMMARY")
    print("=" * 80)
    print(f"Total breeds processed: {len(problematic_breeds)}")
    print(f"Successfully fixed: {fixed_count}")
    print(f"Failed: {failed_count}")
    print(f"Success rate: {fixed_count/len(problematic_breeds)*100:.1f}%")
    
    # Verification
    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80)
    
    # Re-check for issues
    remaining_issues = identify_problematic_breeds()
    if len(remaining_issues) == 0:
        print("✅ All size accuracy issues have been resolved!")
    else:
        print(f"⚠️  {len(remaining_issues)} issues remain")
        print("\nRemaining issues (first 5):")
        for breed in remaining_issues[:5]:
            print(f"  - {breed['display_name']}: {breed['issue']}")
    
    print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()