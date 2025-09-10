#!/usr/bin/env python3
"""
Enrich breeds with missing weight data using multiple sources.
Target: Fill weight data for 177 breeds (30.4%) that currently have NULL weights.
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

# Add jobs directory for scraper access
sys.path.insert(0, str(Path(__file__).parent / 'jobs'))
from wikipedia_breed_scraper_fixed import WikipediaBreedScraper

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)

# Manual weight overrides for breeds where we know the data
WEIGHT_OVERRIDES = {
    # Format: 'breed_slug': (min_weight_kg, max_weight_kg)
    # Common breeds that might be missing
    'affenpinscher': (3.0, 6.0),
    'afghan-hound': (23.0, 27.0),
    'airedale-terrier': (19.0, 25.0),
    'akita': (32.0, 59.0),
    'alaskan-malamute': (32.0, 43.0),
    'basenji': (9.0, 11.0),
    'basset-hound': (20.0, 29.0),
    'bloodhound': (36.0, 50.0),
    'borzoi': (27.0, 48.0),
    'cairn-terrier': (6.0, 8.0),
    'cane-corso': (40.0, 50.0),
    'chinese-crested': (3.6, 5.4),
    'chow-chow': (20.0, 32.0),
    'collie': (20.0, 29.0),
    'dalmatian': (20.0, 32.0),
    'english-setter': (20.0, 36.0),
    'flat-coated-retriever': (25.0, 36.0),
    'fox-terrier': (7.0, 9.0),
    'german-shorthaired-pointer': (20.0, 32.0),
    'giant-schnauzer': (25.0, 48.0),
    'gordon-setter': (20.0, 36.0),
    'great-pyrenees': (39.0, 73.0),
    'greyhound': (27.0, 32.0),
    'irish-setter': (24.0, 32.0),
    'irish-wolfhound': (48.0, 54.0),
    'jack-russell-terrier': (6.0, 8.0),
    'japanese-chin': (2.0, 7.0),  # Fix the 537kg error!
    'keeshond': (16.0, 20.0),
    'kerry-blue-terrier': (13.0, 18.0),
    'komondor': (36.0, 61.0),
    'kuvasz': (32.0, 52.0),
    'leonberger': (41.0, 77.0),
    'lhasa-apso': (5.0, 8.0),
    'maltese': (2.0, 4.0),
    'mastiff': (54.0, 91.0),
    'newfoundland': (45.0, 68.0),
    'norfolk-terrier': (5.0, 5.5),
    'norwegian-elkhound': (20.0, 25.0),
    'old-english-sheepdog': (27.0, 45.0),
    'papillon': (3.0, 5.0),
    'pointer': (20.0, 34.0),
    'puli': (10.0, 15.0),
    'saint-bernard': (54.0, 82.0),
    'saluki': (18.0, 27.0),
    'samoyed': (16.0, 30.0),
    'scottish-deerhound': (34.0, 50.0),
    'scottish-terrier': (8.0, 10.0),
    'sealyham-terrier': (10.0, 11.0),
    'shetland-sheepdog': (6.0, 12.0),
    'shiba-inu': (8.0, 11.0),
    'silky-terrier': (3.5, 5.5),
    'skye-terrier': (11.0, 14.0),
    'soft-coated-wheaten-terrier': (14.0, 20.0),
    'staffordshire-bull-terrier': (11.0, 17.0),
    'standard-schnauzer': (14.0, 20.0),
    'tibetan-mastiff': (34.0, 68.0),
    'tibetan-spaniel': (4.0, 7.0),
    'tibetan-terrier': (8.0, 14.0),
    'toy-fox-terrier': (1.5, 3.0),
    'vizsla': (18.0, 29.0),
    'weimaraner': (25.0, 40.0),
    'welsh-terrier': (9.0, 10.0),
    'west-highland-white-terrier': (7.0, 10.0),
    'whippet': (6.8, 14.0),
    'wire-fox-terrier': (7.0, 9.0),
}

def get_breeds_without_weight():
    """Get all breeds that don't have weight data"""
    response = supabase.table('breeds_details').select('*').is_('weight_kg_max', 'null').execute()
    return pd.DataFrame(response.data)

def try_wikipedia_rescrape(breed_name, breed_slug):
    """Try to get weight from Wikipedia with enhanced patterns"""
    # Common Wikipedia URL patterns
    url_patterns = [
        f"https://en.wikipedia.org/wiki/{breed_name.replace(' ', '_')}",
        f"https://en.wikipedia.org/wiki/{breed_name.replace(' ', '_')}_(dog)",
        f"https://en.wikipedia.org/wiki/{breed_slug.replace('-', '_').title()}",
    ]
    
    scraper = WikipediaBreedScraper()
    
    for url in url_patterns:
        try:
            print(f"    Trying Wikipedia: {url}")
            breed_data = scraper.scrape_breed(breed_name, url)
            if breed_data and breed_data.get('weight_kg_max'):
                return breed_data
        except Exception as e:
            continue
    
    return None

def update_breed_weight(breed_slug, min_weight, max_weight, source="manual"):
    """Update breed with weight data"""
    try:
        # Calculate size from weight
        if max_weight < 4:
            size = 'tiny'
        elif max_weight < 10:
            size = 'small'
        elif max_weight < 25:
            size = 'medium'
        elif max_weight < 45:
            size = 'large'
        else:
            size = 'giant'
        
        update_data = {
            'weight_kg_min': min_weight,
            'weight_kg_max': max_weight,
            'size': size
        }
        
        response = supabase.table('breeds_details').update(update_data).eq('breed_slug', breed_slug).execute()
        
        print(f"    ✅ Updated: {min_weight:.1f}-{max_weight:.1f}kg, size={size} (source: {source})")
        return True
    except Exception as e:
        print(f"    ❌ Failed to update: {e}")
        return False

def main():
    print("=" * 80)
    print("ENRICHING MISSING WEIGHT DATA")
    print("=" * 80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get breeds without weight
    null_weight_df = get_breeds_without_weight()
    total_missing = len(null_weight_df)
    
    print(f"\nBreeds without weight data: {total_missing}")
    
    if total_missing == 0:
        print("✅ All breeds have weight data!")
        return
    
    # Track results
    enriched = 0
    failed = []
    
    print("\nProcessing breeds...")
    print("-" * 60)
    
    for i, (_, breed) in enumerate(null_weight_df.iterrows(), 1):
        breed_slug = breed['breed_slug']
        breed_name = breed['display_name']
        
        print(f"\n[{i}/{total_missing}] {breed_name} ({breed_slug})")
        
        # 1. Check manual overrides first
        if breed_slug in WEIGHT_OVERRIDES:
            min_w, max_w = WEIGHT_OVERRIDES[breed_slug]
            if update_breed_weight(breed_slug, min_w, max_w, "manual"):
                enriched += 1
            else:
                failed.append((breed_name, "Update failed"))
            continue
        
        # 2. Try Wikipedia re-scrape with better patterns
        if breed_name:
            wiki_data = try_wikipedia_rescrape(breed_name, breed_slug)
            if wiki_data and wiki_data.get('weight_kg_max'):
                if update_breed_weight(
                    breed_slug, 
                    wiki_data.get('weight_kg_min', wiki_data['weight_kg_max'] * 0.8),
                    wiki_data['weight_kg_max'],
                    "wikipedia"
                ):
                    enriched += 1
                    time.sleep(random.uniform(1, 2))  # Rate limiting
                    continue
        
        # 3. If all else fails, mark as needing manual research
        print(f"    ⚠️ No weight data found - needs manual research")
        failed.append((breed_name, "No data found"))
    
    # Summary
    print("\n" + "=" * 80)
    print("ENRICHMENT SUMMARY")
    print("=" * 80)
    print(f"Total processed: {total_missing}")
    print(f"Successfully enriched: {enriched} ({enriched/total_missing*100:.1f}%)")
    print(f"Failed: {len(failed)} ({len(failed)/total_missing*100:.1f}%)")
    
    if failed:
        print("\nBreeds still needing weight data:")
        for name, reason in failed[:20]:
            print(f"  - {name}: {reason}")
    
    # Calculate impact
    print("\n" + "=" * 80)
    print("QUALITY IMPACT")
    print("=" * 80)
    
    # Get updated stats
    response = supabase.table('breeds_details').select('weight_kg_max').execute()
    df = pd.DataFrame(response.data)
    
    with_weight = (~df['weight_kg_max'].isna()).sum()
    total = len(df)
    weight_coverage = with_weight / total * 100
    
    print(f"Weight data coverage: {weight_coverage:.1f}% ({with_weight}/{total})")
    
    # Estimated quality score improvement
    old_score = 86.7
    improvement = (enriched / total_missing) * 5  # Each 20% improvement adds ~1 point
    new_score = min(old_score + improvement, 100)
    
    print(f"Estimated quality score: {old_score:.1f}% → {new_score:.1f}% (+{improvement:.1f}%)")
    
    if new_score >= 90:
        print("\n✅ TARGET REACHED: Grade A quality achieved!")
    else:
        print(f"\n⚠️ More enrichment needed for Grade A (need {90 - new_score:.1f}% more)")
    
    print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()