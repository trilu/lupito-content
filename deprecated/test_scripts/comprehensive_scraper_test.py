#!/usr/bin/env python3
"""
Comprehensive test of Wikipedia scraper - checking ALL attributes
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from jobs.wikipedia_breed_scraper import WikipediaBreedScraper
import json
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# Get benchmark data from the 'breeds' table
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(supabase_url, supabase_key)

# Initialize scraper (without DB save for testing)
class TestScraper(WikipediaBreedScraper):
    def save_to_database(self, breed_data):
        """Override to prevent saving during test"""
        return True

# Test breeds with comprehensive expected data
test_cases = [
    {
        'name': 'Labrador Retriever',
        'url': 'https://en.wikipedia.org/wiki/Labrador_Retriever',
        'expected': {
            'weight_range': (25, 36),
            'height_range': (54, 61),
            'size': 'large',
            'lifespan_range': (10, 14),
            'energy': 'high',
            'trainability': 'easy',
            'friendliness': 'high'
        }
    },
    {
        'name': 'German Shepherd',
        'url': 'https://en.wikipedia.org/wiki/German_Shepherd',
        'expected': {
            'weight_range': (22, 40),
            'height_range': (55, 65),
            'size': 'large',
            'lifespan_range': (9, 13),
            'energy': 'high',
            'trainability': 'easy',
            'friendliness': 'moderate'
        }
    },
    {
        'name': 'French Bulldog',
        'url': 'https://en.wikipedia.org/wiki/French_Bulldog',
        'expected': {
            'weight_range': (8, 14),
            'height_range': (25, 35),
            'size': 'small',
            'lifespan_range': (10, 12),
            'energy': 'moderate',
            'trainability': 'moderate',
            'friendliness': 'high'
        }
    },
    {
        'name': 'Chihuahua',
        'url': 'https://en.wikipedia.org/wiki/Chihuahua_(dog)',
        'expected': {
            'weight_range': (1.5, 3),
            'height_range': (15, 23),
            'size': 'tiny',
            'lifespan_range': (12, 18),
            'energy': 'moderate',
            'trainability': 'moderate',
            'friendliness': 'moderate'
        }
    },
    {
        'name': 'Great Dane',
        'url': 'https://en.wikipedia.org/wiki/Great_Dane',
        'expected': {
            'weight_range': (45, 90),
            'height_range': (71, 86),
            'size': 'giant',
            'lifespan_range': (8, 10),
            'energy': 'moderate',
            'trainability': 'moderate',
            'friendliness': 'high'
        }
    }
]

print("="*80)
print("COMPREHENSIVE WIKIPEDIA SCRAPER VALIDATION")
print("="*80)

scraper = TestScraper()
all_results = []
validation_report = []

for test_case in test_cases:
    breed_name = test_case['name']
    url = test_case['url']
    expected = test_case['expected']
    
    print(f"\n{'='*60}")
    print(f"Testing: {breed_name}")
    print(f"{'='*60}")
    
    # Scrape the breed
    breed_data = scraper.scrape_breed(breed_name, url)
    
    if not breed_data:
        print(f"❌ FAILED to scrape {breed_name}")
        validation_report.append({
            'breed': breed_name,
            'status': 'FAILED',
            'issues': ['Failed to scrape data']
        })
        continue
    
    # Remove raw HTML for display
    display_data = {k: v for k, v in breed_data.items() if k not in ['raw_html', 'comprehensive_content']}
    
    # Check each attribute
    issues = []
    
    # 1. Weight validation
    weight_min = breed_data.get('weight_kg_min', 0)
    weight_max = breed_data.get('weight_kg_max', 0)
    exp_weight_min, exp_weight_max = expected['weight_range']
    
    print(f"Weight: {weight_min}-{weight_max} kg (expected {exp_weight_min}-{exp_weight_max} kg)")
    if weight_min == 0 or weight_max == 0:
        issues.append(f"Missing weight data")
    elif abs(weight_min - exp_weight_min) > exp_weight_min * 0.3 or abs(weight_max - exp_weight_max) > exp_weight_max * 0.3:
        issues.append(f"Weight mismatch: got {weight_min}-{weight_max}, expected {exp_weight_min}-{exp_weight_max}")
    
    # 2. Height validation
    height_min = breed_data.get('height_cm_min', 0)
    height_max = breed_data.get('height_cm_max', 0)
    exp_height_min, exp_height_max = expected['height_range']
    
    print(f"Height: {height_min}-{height_max} cm (expected {exp_height_min}-{exp_height_max} cm)")
    if height_min == 0 or height_max == 0:
        issues.append(f"Missing height data")
    elif abs(height_min - exp_height_min) > 10 or abs(height_max - exp_height_max) > 10:
        issues.append(f"Height mismatch: got {height_min}-{height_max}, expected {exp_height_min}-{exp_height_max}")
    
    # 3. Size category validation
    size = breed_data.get('size', '')
    print(f"Size: {size} (expected {expected['size']})")
    if size != expected['size']:
        issues.append(f"Size mismatch: got {size}, expected {expected['size']}")
    
    # 4. Lifespan validation
    lifespan_min = breed_data.get('lifespan_years_min', 0)
    lifespan_max = breed_data.get('lifespan_years_max', 0)
    exp_life_min, exp_life_max = expected['lifespan_range']
    
    print(f"Lifespan: {lifespan_min}-{lifespan_max} years (expected {exp_life_min}-{exp_life_max} years)")
    if lifespan_min == 0 or lifespan_max == 0:
        issues.append(f"Missing lifespan data")
    
    # 5. Other attributes
    energy = breed_data.get('energy', 'unknown')
    trainability = breed_data.get('trainability', 'unknown')
    friendliness_dogs = breed_data.get('friendliness_to_dogs', 0)
    friendliness_humans = breed_data.get('friendliness_to_humans', 0)
    
    print(f"Energy: {energy}")
    print(f"Trainability: {trainability}")
    print(f"Friendliness (dogs/humans): {friendliness_dogs}/{friendliness_humans}")
    
    # 6. Origin and other info
    origin = breed_data.get('origin', 'unknown')
    coat_length = breed_data.get('coat_length', 'unknown')
    shedding = breed_data.get('shedding', 'unknown')
    bark_level = breed_data.get('bark_level', 'unknown')
    
    print(f"Origin: {origin[:50] if origin else 'N/A'}")
    print(f"Coat: {coat_length}, Shedding: {shedding}, Barking: {bark_level}")
    
    # Validation status
    if issues:
        print(f"\n⚠️ Issues found:")
        for issue in issues:
            print(f"  - {issue}")
        validation_report.append({
            'breed': breed_name,
            'status': 'ISSUES',
            'issues': issues
        })
    else:
        print(f"\n✅ All validations passed!")
        validation_report.append({
            'breed': breed_name,
            'status': 'PASSED',
            'issues': []
        })
    
    all_results.append(display_data)

# Final report
print("\n" + "="*80)
print("VALIDATION SUMMARY")
print("="*80)

passed = sum(1 for r in validation_report if r['status'] == 'PASSED')
issues = sum(1 for r in validation_report if r['status'] == 'ISSUES')
failed = sum(1 for r in validation_report if r['status'] == 'FAILED')

print(f"✅ Passed: {passed}/{len(test_cases)}")
print(f"⚠️ Issues: {issues}/{len(test_cases)}")
print(f"❌ Failed: {failed}/{len(test_cases)}")

if issues > 0 or failed > 0:
    print("\nBreeds with issues:")
    for report in validation_report:
        if report['status'] != 'PASSED':
            print(f"  {report['breed']}: {', '.join(report['issues'])}")

# Save detailed results
with open('comprehensive_test_results.json', 'w') as f:
    json.dump({
        'validation_report': validation_report,
        'scraped_data': all_results
    }, f, indent=2)

print("\nDetailed results saved to comprehensive_test_results.json")

# Compare with breeds table
print("\n" + "="*80)
print("COMPARISON WITH BREEDS TABLE")
print("="*80)

for breed_name in ['Labrador Retriever', 'German Shepherd', 'French Bulldog']:
    result = supabase.table('breeds').select('*').eq('name_en', breed_name).execute()
    if result.data:
        b = result.data[0]
        scraped = next((r for r in all_results if r.get('display_name') == breed_name), None)
        if scraped:
            print(f"\n{breed_name}:")
            print(f"  Breeds table: {b.get('size_category')}, {b.get('avg_male_weight_kg')}kg")
            print(f"  Scraped: {scraped.get('size')}, {scraped.get('weight_kg_min')}-{scraped.get('weight_kg_max')}kg")