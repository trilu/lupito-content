#!/usr/bin/env python3
"""
Analyze failed breeds and create a plan to fix their URLs
"""

import json
import re

# Load the scraping progress
with open('scraping_progress.json', 'r') as f:
    data = json.load(f)

errors = data['stats']['errors']

print("FAILED BREEDS ANALYSIS")
print("=" * 60)
print(f"Total failed: {len(errors)}\n")

# Parse the errors
failed_breeds = []
for error in errors:
    # Extract breed name and URL from error message
    match = re.match(r"(.+?):\s+(.+)", error)
    if match:
        breed_name = match.group(1)
        error_msg = match.group(2)
        
        # Extract URL if it's a 404 error
        url_match = re.search(r'url: (.+)', error_msg)
        if url_match:
            url = url_match.group(1)
            failed_breeds.append({
                'name': breed_name,
                'failed_url': url,
                'error': error_msg
            })
        elif 'Connection' in error_msg:
            # Connection error - might need retry
            failed_breeds.append({
                'name': breed_name,
                'failed_url': 'Connection error',
                'error': error_msg
            })

print("CATEGORIZED FAILURES:")
print("-" * 60)

# Categorize the failures
with_dog_suffix = []
connection_errors = []
other_404s = []

for breed in failed_breeds:
    if breed['failed_url'] == 'Connection error':
        connection_errors.append(breed)
    elif '_(dog)' in breed['failed_url']:
        with_dog_suffix.append(breed)
    else:
        other_404s.append(breed)

print(f"\n1. URLs ending with _(dog) suffix: {len(with_dog_suffix)}")
for breed in with_dog_suffix:
    print(f"   - {breed['name']}: {breed['failed_url']}")

print(f"\n2. Connection errors (need retry): {len(connection_errors)}")
for breed in connection_errors:
    print(f"   - {breed['name']}")

print(f"\n3. Other 404 errors: {len(other_404s)}")
for breed in other_404s:
    print(f"   - {breed['name']}: {breed['failed_url']}")

print("\n" + "=" * 60)
print("PROPOSED URL CORRECTIONS:")
print("-" * 60)

# Create URL corrections mapping
url_corrections = {}

for breed in with_dog_suffix:
    # Remove the _(dog) suffix
    corrected_url = breed['failed_url'].replace('_(dog)', '')
    url_corrections[breed['name']] = {
        'original': breed['failed_url'],
        'corrected': corrected_url
    }
    print(f"{breed['name']}:")
    print(f"  FROM: {breed['failed_url']}")
    print(f"  TO:   {corrected_url}")
    print()

# Special cases that need manual checking
special_cases = {
    'Florida Brown Dog': 'https://en.wikipedia.org/wiki/Florida_Cracker_cur',
    'Là': None,  # This seems to be a misnamed breed
    'Pachón Navarro': 'https://en.wikipedia.org/wiki/Pachón_Navarro',
    'English Mastiff': 'https://en.wikipedia.org/wiki/English_Mastiff'  # Retry
}

print("\nSPECIAL CASES (need manual verification):")
print("-" * 60)
for breed_name, suggested_url in special_cases.items():
    if any(b['name'] == breed_name for b in failed_breeds):
        print(f"{breed_name}:")
        if suggested_url:
            print(f"  SUGGESTED: {suggested_url}")
        else:
            print(f"  NOTE: May be invalid breed name or needs research")
        print()

# Save the corrections to a file
corrections_data = {
    'url_corrections': url_corrections,
    'special_cases': special_cases,
    'connection_retries': [b['name'] for b in connection_errors]
}

with open('failed_breeds_corrections.json', 'w') as f:
    json.dump(corrections_data, f, indent=2)

print(f"\nCorrections saved to: failed_breeds_corrections.json")
print(f"Total breeds to fix: {len(failed_breeds)}")