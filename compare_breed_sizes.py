#!/usr/bin/env python3
"""
Compare size and weight data between breeds_published and breeds_details
"""

import os
import json
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(supabase_url, supabase_key)

print("="*80)
print("BREEDS SIZE & WEIGHT COMPARISON AUDIT")
print("="*80)
print(f"Timestamp: {datetime.now().isoformat()}\n")

# Fetch all data from both tables
print("Fetching data from Supabase...")
published_response = supabase.table('breeds_published').select('*').execute()
details_response = supabase.table('breeds_details').select('*').execute()

# Create dictionaries keyed by breed_slug
published_breeds = {row['breed_slug']: row for row in published_response.data}
details_breeds = {row['breed_slug']: row for row in details_response.data}

print(f"Total breeds in breeds_published: {len(published_breeds)}")
print(f"Total breeds in breeds_details: {len(details_breeds)}")

# Size mapping between tables
SIZE_MAPPING = {
    # breeds_published -> breeds_details
    'xs': 'tiny',
    's': 'small',
    'm': 'medium',
    'l': 'large',
    'xl': 'giant',
    'tiny': 'tiny',
    'small': 'small',
    'medium': 'medium',
    'large': 'large',
    'giant': 'giant'
}

# Track mismatches
mismatches = {
    'size': [],
    'weight': [],
    'missing_in_details': [],
    'suspicious_data': []
}

print("\n" + "="*80)
print("ANALYZING DATA QUALITY ISSUES")
print("="*80)

# Compare breeds that exist in both tables
for slug, pub_breed in published_breeds.items():
    if slug not in details_breeds:
        mismatches['missing_in_details'].append({
            'breed_slug': slug,
            'breed_name': pub_breed.get('breed_name', 'Unknown')
        })
        continue
    
    detail_breed = details_breeds[slug]
    
    # 1. Check size mismatch
    pub_size = (pub_breed.get('size_category') or '').lower()
    detail_size = (detail_breed.get('size') or '').lower()
    
    # Map published size to details format
    mapped_pub_size = SIZE_MAPPING.get(pub_size, pub_size)
    
    if mapped_pub_size and detail_size and mapped_pub_size != detail_size:
        mismatches['size'].append({
            'breed': pub_breed.get('breed_name', slug),
            'breed_slug': slug,
            'published_size': pub_size,
            'wikipedia_size': detail_size,
            'published_weight': f"{pub_breed.get('ideal_weight_min_kg', 'N/A')}-{pub_breed.get('ideal_weight_max_kg', 'N/A')} kg",
            'wikipedia_weight': f"{detail_breed.get('weight_kg_min', 'N/A')}-{detail_breed.get('weight_kg_max', 'N/A')} kg"
        })
    
    # 2. Check weight discrepancies (significant differences)
    pub_weight_min = pub_breed.get('ideal_weight_min_kg')
    pub_weight_max = pub_breed.get('ideal_weight_max_kg')
    detail_weight_min = detail_breed.get('weight_kg_min')
    detail_weight_max = detail_breed.get('weight_kg_max')
    
    if all([pub_weight_min, pub_weight_max, detail_weight_min, detail_weight_max]):
        # Check if weights differ by more than 30%
        min_diff_pct = abs(pub_weight_min - detail_weight_min) / detail_weight_min * 100 if detail_weight_min else 0
        max_diff_pct = abs(pub_weight_max - detail_weight_max) / detail_weight_max * 100 if detail_weight_max else 0
        
        if min_diff_pct > 30 or max_diff_pct > 30:
            mismatches['weight'].append({
                'breed': pub_breed.get('breed_name', slug),
                'breed_slug': slug,
                'published_weight': f"{pub_weight_min}-{pub_weight_max} kg",
                'wikipedia_weight': f"{detail_weight_min}-{detail_weight_max} kg",
                'min_diff_pct': round(min_diff_pct, 1),
                'max_diff_pct': round(max_diff_pct, 1)
            })
    
    # 3. Check for suspicious data patterns
    # Example: Large/Giant breeds marked as small
    if detail_weight_max and detail_weight_max > 30 and pub_size in ['xs', 's']:
        mismatches['suspicious_data'].append({
            'breed': pub_breed.get('breed_name', slug),
            'breed_slug': slug,
            'issue': f"Large breed ({detail_weight_max}kg) marked as {pub_size}",
            'published_size': pub_size,
            'wikipedia_weight': f"{detail_weight_min}-{detail_weight_max} kg"
        })

# Print results
print(f"\n{'='*40}")
print("SIZE MISMATCHES")
print(f"{'='*40}")
print(f"Found {len(mismatches['size'])} size mismatches:\n")

for i, mismatch in enumerate(mismatches['size'][:20], 1):  # Show first 20
    print(f"{i:3}. {mismatch['breed']}")
    print(f"     Published: {mismatch['published_size']} ({mismatch['published_weight']})")
    print(f"     Wikipedia: {mismatch['wikipedia_size']} ({mismatch['wikipedia_weight']})")
    print()

if len(mismatches['size']) > 20:
    print(f"... and {len(mismatches['size']) - 20} more\n")

print(f"\n{'='*40}")
print("WEIGHT DISCREPANCIES (>30% difference)")
print(f"{'='*40}")
print(f"Found {len(mismatches['weight'])} significant weight discrepancies:\n")

for i, mismatch in enumerate(mismatches['weight'][:10], 1):  # Show first 10
    print(f"{i:3}. {mismatch['breed']}")
    print(f"     Published: {mismatch['published_weight']}")
    print(f"     Wikipedia: {mismatch['wikipedia_weight']}")
    print(f"     Difference: {mismatch['min_diff_pct']}% (min), {mismatch['max_diff_pct']}% (max)")
    print()

if len(mismatches['weight']) > 10:
    print(f"... and {len(mismatches['weight']) - 10} more\n")

print(f"\n{'='*40}")
print("SUSPICIOUS DATA PATTERNS")
print(f"{'='*40}")
print(f"Found {len(mismatches['suspicious_data'])} suspicious patterns:\n")

for i, issue in enumerate(mismatches['suspicious_data'][:10], 1):
    print(f"{i:3}. {issue['breed']}: {issue['issue']}")

print(f"\n{'='*40}")
print("MISSING FROM BREEDS_DETAILS")
print(f"{'='*40}")
print(f"Found {len(mismatches['missing_in_details'])} breeds not in breeds_details")
print("These need to be scraped from Wikipedia for comparison\n")

# Save detailed audit report
audit_data = {
    'timestamp': datetime.now().isoformat(),
    'summary': {
        'total_published': len(published_breeds),
        'total_details': len(details_breeds),
        'size_mismatches': len(mismatches['size']),
        'weight_discrepancies': len(mismatches['weight']),
        'suspicious_patterns': len(mismatches['suspicious_data']),
        'missing_from_details': len(mismatches['missing_in_details'])
    },
    'mismatches': mismatches
}

with open('breed_size_audit.json', 'w') as f:
    json.dump(audit_data, f, indent=2)

print(f"\n{'='*80}")
print("SUMMARY")
print(f"{'='*80}")
print(f"✓ Size mismatches: {len(mismatches['size'])} breeds")
print(f"✓ Weight discrepancies (>30%): {len(mismatches['weight'])} breeds")  
print(f"✓ Suspicious data patterns: {len(mismatches['suspicious_data'])} breeds")
print(f"✓ Missing from breeds_details: {len(mismatches['missing_in_details'])} breeds")
print(f"\nDetailed audit saved to: breed_size_audit.json")

# Check specific case mentioned by user
print(f"\n{'='*80}")
print("SPECIFIC CASE: Labrador Retriever")
print(f"{'='*80}")
if 'labrador-retriever' in published_breeds and 'labrador-retriever' in details_breeds:
    lab_pub = published_breeds['labrador-retriever']
    lab_det = details_breeds['labrador-retriever']
    print(f"Published data:")
    print(f"  - Size: {lab_pub.get('size_category')}")
    print(f"  - Weight: {lab_pub.get('ideal_weight_min_kg')}-{lab_pub.get('ideal_weight_max_kg')} kg")
    print(f"Wikipedia data:")
    print(f"  - Size: {lab_det.get('size')}")
    print(f"  - Weight: {lab_det.get('weight_kg_min')}-{lab_det.get('weight_kg_max')} kg")
else:
    print("Labrador Retriever data not found in one or both tables")

# Generate recommendation
print(f"\n{'='*80}")
print("RECOMMENDATIONS")
print(f"{'='*80}")
print("1. Update breeds_published with Wikipedia data for size mismatches")
print("2. Scrape missing 53 breeds from Wikipedia to complete comparison")
print("3. Review weight discrepancies and update where Wikipedia is more accurate")
print("4. Focus on suspicious patterns (large breeds marked as small)")
print("\nNext step: Run Wikipedia scraper for missing breeds using 'missing_breeds_wikipedia_urls.txt'")