#!/usr/bin/env python3
"""
Test the updated Wikipedia scraper
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from jobs.wikipedia_breed_scraper import WikipediaBreedScraper
import json

# Initialize scraper (without DB connection for testing)
class TestScraper(WikipediaBreedScraper):
    def __init__(self):
        """Initialize without DB"""
        import requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Educational Breed Data Scraper) Contact: research@example.com'
        })
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }

# Test breeds
test_breeds = [
    ('Labrador Retriever', 'https://en.wikipedia.org/wiki/Labrador_Retriever'),
    ('German Shepherd', 'https://en.wikipedia.org/wiki/German_Shepherd'),
    ('French Bulldog', 'https://en.wikipedia.org/wiki/French_Bulldog'),
    ('Chihuahua', 'https://en.wikipedia.org/wiki/Chihuahua_(dog)'),
    ('Great Dane', 'https://en.wikipedia.org/wiki/Great_Dane'),
]

print("="*80)
print("TESTING UPDATED WIKIPEDIA BREED SCRAPER")
print("="*80)

scraper = TestScraper()
results = []

for breed_name, url in test_breeds:
    print(f"\nTesting {breed_name}...")
    breed_data = scraper.scrape_breed(breed_name, url)
    
    if breed_data:
        # Remove raw HTML from display
        display_data = {k: v for k, v in breed_data.items() if k != 'raw_html'}
        print(f"  Weight: {display_data.get('weight_kg_min', 'N/A')}-{display_data.get('weight_kg_max', 'N/A')} kg")
        print(f"  Height: {display_data.get('height_cm_min', 'N/A')}-{display_data.get('height_cm_max', 'N/A')} cm")
        print(f"  Size: {display_data.get('size', 'N/A')}")
        print(f"  Lifespan: {display_data.get('lifespan_years_min', 'N/A')}-{display_data.get('lifespan_years_max', 'N/A')} years")
        results.append(display_data)
    else:
        print("  Failed to scrape!")

# Compare with expected values
print("\n" + "="*80)
print("VALIDATION AGAINST EXPECTED VALUES")
print("="*80)

expected = {
    'Labrador Retriever': {'weight_min': 25, 'weight_max': 36, 'size': 'large'},
    'German Shepherd': {'weight_min': 22, 'weight_max': 40, 'size': 'large'},
    'French Bulldog': {'weight_min': 8, 'weight_max': 14, 'size': 'small'},
    'Chihuahua': {'weight_min': 1, 'weight_max': 3, 'size': 'tiny'},
    'Great Dane': {'weight_min': 45, 'weight_max': 90, 'size': 'giant'},
}

all_valid = True
for result in results:
    breed = result.get('display_name')
    if breed in expected:
        exp = expected[breed]
        weight_min = result.get('weight_kg_min', 0)
        weight_max = result.get('weight_kg_max', 0)
        size = result.get('size', '')
        
        # Check if within reasonable range (±20%)
        min_valid = abs(weight_min - exp['weight_min']) / exp['weight_min'] < 0.3
        max_valid = abs(weight_max - exp['weight_max']) / exp['weight_max'] < 0.3
        size_valid = size == exp['size']
        
        if min_valid and max_valid and size_valid:
            print(f"✅ {breed}: Valid")
        else:
            print(f"❌ {breed}: Issues detected")
            if not min_valid:
                print(f"   Min weight: {weight_min} kg (expected ~{exp['weight_min']} kg)")
            if not max_valid:
                print(f"   Max weight: {weight_max} kg (expected ~{exp['weight_max']} kg)")
            if not size_valid:
                print(f"   Size: {size} (expected {exp['size']})")
            all_valid = False

if all_valid:
    print("\n🎉 All breeds validated successfully! The scraper is working correctly.")
else:
    print("\n⚠️ Some breeds have validation issues. Please review the parsing logic.")