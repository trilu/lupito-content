#!/usr/bin/env python3
"""
Analyze breeds in breeds_published vs breeds_details tables
"""

import os
from dotenv import load_dotenv
from supabase import create_client
import json

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(supabase_url, supabase_key)

print("Fetching data from Supabase...")

# Fetch all breeds from breeds_published
published_response = supabase.table('breeds_published').select('breed_slug, breed_name').execute()
published_breeds = {row['breed_slug']: row['breed_name'] for row in published_response.data}

# Fetch all breeds from breeds_details
details_response = supabase.table('breeds_details').select('breed_slug, display_name').execute()
details_breeds = {row['breed_slug']: row['display_name'] for row in details_response.data}

print(f"\nTotal breeds in breeds_published: {len(published_breeds)}")
print(f"Total breeds in breeds_details: {len(details_breeds)}")

# Find breeds in published but not in details
missing_in_details = {}
for slug, name in published_breeds.items():
    if slug not in details_breeds:
        missing_in_details[slug] = name

# Find breeds in details but not in published
missing_in_published = {}
for slug, name in details_breeds.items():
    if slug not in published_breeds:
        missing_in_published[slug] = name

# Find common breeds
common_breeds = set(published_breeds.keys()) & set(details_breeds.keys())

print(f"\nBreeds in both tables: {len(common_breeds)}")
print(f"Breeds in breeds_published but NOT in breeds_details: {len(missing_in_details)}")
print(f"Breeds in breeds_details but NOT in breeds_published: {len(missing_in_published)}")

# Display missing breeds
if missing_in_details:
    print("\n" + "="*60)
    print("BREEDS IN breeds_published BUT MISSING FROM breeds_details:")
    print("="*60)
    for i, (slug, name) in enumerate(sorted(missing_in_details.items()), 1):
        print(f"{i:3}. {name} ({slug})")

if missing_in_published:
    print("\n" + "="*60)
    print("BREEDS IN breeds_details BUT MISSING FROM breeds_published:")
    print("="*60)
    for i, (slug, name) in enumerate(sorted(missing_in_published.items()), 1):
        print(f"{i:3}. {name} ({slug})")

# Save analysis to file
analysis_data = {
    'summary': {
        'total_published': len(published_breeds),
        'total_details': len(details_breeds),
        'common_breeds': len(common_breeds),
        'missing_in_details': len(missing_in_details),
        'missing_in_published': len(missing_in_published)
    },
    'missing_in_details': missing_in_details,
    'missing_in_published': missing_in_published,
    'common_breeds': list(common_breeds)
}

with open('breeds_comparison_analysis.json', 'w') as f:
    json.dump(analysis_data, f, indent=2)

print(f"\nAnalysis saved to breeds_comparison_analysis.json")

# Generate Wikipedia URLs for missing breeds
if missing_in_details:
    print("\nGenerating Wikipedia URLs for missing breeds...")
    with open('missing_breeds_wikipedia_urls.txt', 'w') as f:
        for slug, name in sorted(missing_in_details.items()):
            # Convert slug back to Wikipedia URL format
            wiki_name = name.replace(' ', '_')
            url = f"https://en.wikipedia.org/wiki/{wiki_name}"
            f.write(f"{name}|{url}\n")
    print(f"Generated {len(missing_in_details)} Wikipedia URLs in missing_breeds_wikipedia_urls.txt")