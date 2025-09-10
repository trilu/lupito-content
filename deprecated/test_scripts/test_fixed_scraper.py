#!/usr/bin/env python3
"""
Test fixed Wikipedia scraper with proper parsing
"""

import requests
from bs4 import BeautifulSoup
import re
from typing import Dict, Any
import json

def parse_wikipedia_breed(breed_name: str, url: str) -> Dict[str, Any]:
    """Parse breed information from Wikipedia with fixed logic"""
    
    print(f"\nProcessing {breed_name}...")
    
    # Fetch page
    response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 Educational Scraper'})
    soup = BeautifulSoup(response.text, 'html.parser')
    
    breed_data = {
        'breed_name': breed_name,
        'url': url
    }
    
    # Find the infobox - it's now class "infobox biota" for dog breeds
    infobox = soup.find('table', class_='infobox')
    if not infobox:
        infobox = soup.find('table', class_=lambda x: x and 'infobox' in str(x))
    
    if not infobox:
        print(f"  ⚠️ No infobox found for {breed_name}")
        return breed_data
    
    # Process all rows in the infobox
    for row in infobox.find_all('tr'):
        # Get header
        header = row.find('th')
        if not header:
            continue
        
        header_text = header.get_text(strip=True).lower()
        
        # Handle Weight rows
        if 'weight' in header_text:
            # Weight data is in the following td cells
            cells = row.find_all('td')
            if cells:
                weight_text = ' '.join([cell.get_text(strip=True) for cell in cells])
                print(f"  Found weight data: {weight_text}")
                
                # Extract weight values with improved regex
                # Look for patterns like "29–36 kg" or "65–80 lb"
                kg_pattern = r'(\d+)[–\-](\d+)\s*kg'
                lb_pattern = r'(\d+)[–\-](\d+)\s*lb'
                
                kg_matches = re.findall(kg_pattern, weight_text)
                lb_matches = re.findall(lb_pattern, weight_text)
                
                if kg_matches:
                    # Use kg values directly
                    weights = []
                    for match in kg_matches:
                        weights.extend([float(match[0]), float(match[1])])
                    breed_data['weight_kg_min'] = min(weights)
                    breed_data['weight_kg_max'] = max(weights)
                    print(f"    Extracted: {breed_data['weight_kg_min']}-{breed_data['weight_kg_max']} kg")
                    
                elif lb_matches:
                    # Convert lb to kg
                    weights = []
                    for match in lb_matches:
                        weights.extend([float(match[0]) * 0.453592, float(match[1]) * 0.453592])
                    breed_data['weight_kg_min'] = round(min(weights), 1)
                    breed_data['weight_kg_max'] = round(max(weights), 1)
                    print(f"    Extracted (from lb): {breed_data['weight_kg_min']}-{breed_data['weight_kg_max']} kg")
        
        # Handle Height rows
        elif 'height' in header_text:
            cells = row.find_all('td')
            if cells:
                height_text = ' '.join([cell.get_text(strip=True) for cell in cells])
                print(f"  Found height data: {height_text}")
                
                # Extract height values
                cm_pattern = r'(\d+)[–\-](\d+)\s*cm'
                inch_pattern = r'(\d+(?:\.\d+)?)[–\-](\d+(?:\.\d+)?)\s*in'
                
                cm_matches = re.findall(cm_pattern, height_text)
                inch_matches = re.findall(inch_pattern, height_text)
                
                if cm_matches:
                    heights = []
                    for match in cm_matches:
                        heights.extend([float(match[0]), float(match[1])])
                    breed_data['height_cm_min'] = int(min(heights))
                    breed_data['height_cm_max'] = int(max(heights))
                    print(f"    Extracted: {breed_data['height_cm_min']}-{breed_data['height_cm_max']} cm")
                    
                elif inch_matches:
                    heights = []
                    for match in inch_matches:
                        heights.extend([float(match[0]) * 2.54, float(match[1]) * 2.54])
                    breed_data['height_cm_min'] = int(round(min(heights)))
                    breed_data['height_cm_max'] = int(round(max(heights)))
                    print(f"    Extracted (from inches): {breed_data['height_cm_min']}-{breed_data['height_cm_max']} cm")
        
        # Handle Life span
        elif 'life' in header_text and 'span' in header_text:
            cells = row.find_all('td')
            if cells:
                lifespan_text = ' '.join([cell.get_text(strip=True) for cell in cells])
                year_pattern = r'(\d+)[–\-](\d+)\s*year'
                year_matches = re.findall(year_pattern, lifespan_text.lower())
                if year_matches:
                    breed_data['lifespan_years_min'] = int(year_matches[0][0])
                    breed_data['lifespan_years_max'] = int(year_matches[0][1])
                    print(f"  Found lifespan: {breed_data['lifespan_years_min']}-{breed_data['lifespan_years_max']} years")
    
    # Determine size category based on weight
    if 'weight_kg_max' in breed_data:
        weight = breed_data['weight_kg_max']
        if weight < 5:
            breed_data['size'] = 'tiny'
        elif weight < 10:
            breed_data['size'] = 'small'
        elif weight < 25:
            breed_data['size'] = 'medium'
        elif weight < 45:
            breed_data['size'] = 'large'
        else:
            breed_data['size'] = 'giant'
        print(f"  Determined size: {breed_data['size']}")
    
    return breed_data

# Test with 5 known breeds
test_breeds = [
    ('Labrador Retriever', 'https://en.wikipedia.org/wiki/Labrador_Retriever'),
    ('German Shepherd', 'https://en.wikipedia.org/wiki/German_Shepherd'),
    ('Golden Retriever', 'https://en.wikipedia.org/wiki/Golden_Retriever'),
    ('French Bulldog', 'https://en.wikipedia.org/wiki/French_Bulldog'),
    ('Chihuahua', 'https://en.wikipedia.org/wiki/Chihuahua_(dog)'),
]

print("="*80)
print("TESTING FIXED WIKIPEDIA SCRAPER")
print("="*80)

results = []
for breed_name, url in test_breeds:
    breed_data = parse_wikipedia_breed(breed_name, url)
    results.append(breed_data)

# Compare with benchmark
print("\n" + "="*80)
print("COMPARISON WITH BENCHMARK DATA")
print("="*80)

benchmark = {
    'Labrador Retriever': {'weight': '24.1-37.8', 'size': 'Large', 'height': 60},
    'German Shepherd': {'weight': '23.1-40.4', 'size': 'Large', 'height': 60.5},
    'Golden Retriever': {'weight': '23.1-37.8', 'size': 'Large', 'height': 57},
    'French Bulldog': {'weight': '7.7-12.5', 'size': 'Small', 'height': 30.5},
    'Chihuahua': {'weight': '2.4-3.7', 'size': 'Toy/Tiny', 'height': 16.5},
}

for result in results:
    breed = result['breed_name']
    if breed in benchmark:
        bench = benchmark[breed]
        print(f"\n{breed}:")
        print(f"  Scraped weight: {result.get('weight_kg_min', 'N/A')}-{result.get('weight_kg_max', 'N/A')} kg")
        print(f"  Benchmark: {bench['weight']} kg")
        print(f"  Scraped size: {result.get('size', 'N/A')}")
        print(f"  Benchmark size: {bench['size']}")
        
        # Check if within reasonable range
        if 'weight_kg_max' in result:
            bench_max = float(bench['weight'].split('-')[1])
            diff_pct = abs(result['weight_kg_max'] - bench_max) / bench_max * 100
            if diff_pct < 20:
                print(f"  ✅ Weight match (within {diff_pct:.1f}%)")
            else:
                print(f"  ❌ Weight mismatch ({diff_pct:.1f}% difference)")

# Save results
with open('test_scraper_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print("\nResults saved to test_scraper_results.json")