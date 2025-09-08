#!/usr/bin/env python3
"""
Analyze the full JSON data from AKC page to understand all available fields
"""

import json
import re
from bs4 import BeautifulSoup
from pprint import pprint

# Read the HTML file
with open('akc_10sec_wait.html', 'r') as f:
    html = f.read()

# Parse HTML
soup = BeautifulSoup(html, 'html.parser')

# Find the breed data div
breed_div = soup.find('div', {'data-js-component': 'breedPage'})

if breed_div and breed_div.get('data-js-props'):
    # Parse the JSON
    data = json.loads(breed_div['data-js-props'])
    
    # Save full JSON for analysis
    with open('akc_full_json.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    print("=" * 80)
    print("FULL JSON STRUCTURE ANALYSIS")
    print("=" * 80)
    
    # Analyze the structure
    def analyze_dict(d, prefix=""):
        """Recursively analyze dictionary structure"""
        for key, value in d.items():
            if isinstance(value, dict):
                print(f"{prefix}{key}: dict with {len(value)} keys")
                if len(value) <= 10:  # Show keys for small dicts
                    analyze_dict(value, prefix + "  ")
            elif isinstance(value, list):
                print(f"{prefix}{key}: list with {len(value)} items")
                if len(value) > 0 and isinstance(value[0], dict):
                    print(f"{prefix}  First item keys: {list(value[0].keys())}")
            elif isinstance(value, str):
                if len(value) > 100:
                    print(f"{prefix}{key}: string ({len(value)} chars)")
                else:
                    print(f"{prefix}{key}: '{value[:50]}{'...' if len(value) > 50 else ''}'")
            else:
                print(f"{prefix}{key}: {value}")
    
    print("\n1. TOP LEVEL KEYS:")
    print("-" * 40)
    print(list(data.keys()))
    
    print("\n2. BREED DATA STRUCTURE:")
    print("-" * 40)
    if 'breed' in data:
        breed = data['breed']
        analyze_dict(breed)
    
    print("\n3. TRAIT SCORES:")
    print("-" * 40)
    # Look for trait-related data
    if 'breed' in data:
        breed = data['breed']
        for key in breed:
            if 'trait' in key.lower() or 'score' in key.lower() or 'characteristic' in key.lower():
                print(f"{key}: {breed[key]}")
    
    print("\n4. CONTENT SECTIONS:")
    print("-" * 40)
    # Check what content sections exist
    content_keys = ['about', 'care', 'health', 'grooming', 'training', 'exercise', 'nutrition', 'personality']
    for key in content_keys:
        if key in breed:
            content = breed[key]
            if isinstance(content, dict):
                print(f"{key}: {list(content.keys())}")
            elif isinstance(content, str):
                print(f"{key}: string ({len(content)} chars)")
            else:
                print(f"{key}: {type(content)}")
    
    print("\n5. PHYSICAL CHARACTERISTICS:")
    print("-" * 40)
    physical_keys = ['height', 'weight', 'size', 'lifespan', 'life_expectancy']
    for key in breed:
        for phys_key in physical_keys:
            if phys_key in key.lower():
                print(f"{key}: {breed[key]}")
    
    print("\n6. MISSING DATA WE NEED:")
    print("-" * 40)
    # Check what we're looking for but not finding
    needed_keys = [
        'temperament_scores', 'traits', 'characteristics',
        'female_height', 'female_weight', 
        'grooming_frequency', 'exercise_needs',
        'about_text', 'personality_text'
    ]
    for key in needed_keys:
        found = False
        for breed_key in breed:
            if key in breed_key.lower():
                found = True
                break
        if not found:
            print(f"❌ {key}: NOT FOUND")
        else:
            print(f"✅ {key}: Found as {breed_key}")

else:
    print("Could not find breed data JSON in HTML")