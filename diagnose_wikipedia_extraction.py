#!/usr/bin/env python3
"""
Diagnostic script to understand why Wikipedia extraction isn't finding data
Tests extraction on a few specific breeds
"""

import os
import re
from google.cloud import storage
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

# Initialize GCS
storage_client = storage.Client(project='careful-drummer-468512-p0')
bucket = storage_client.bucket('lupito-content-raw-eu')

def analyze_breed_html(breed_slug: str, limit_text: int = 500):
    """Analyze a specific breed's HTML to see what sections exist"""

    # Download HTML from GCS
    blob_path = f'scraped/wikipedia_breeds/20250917_162810/{breed_slug}.html'
    blob = bucket.blob(blob_path)

    if not blob.exists():
        print(f"❌ No HTML file found for {breed_slug}")
        return

    html_content = blob.download_as_text()
    soup = BeautifulSoup(html_content, 'html.parser')

    print(f"\n{'='*60}")
    print(f"ANALYZING: {breed_slug}")
    print('='*60)

    # Find all headings
    print("\n📑 SECTION HEADINGS FOUND:")
    print("-"*40)
    headings = soup.find_all(['h2', 'h3', 'h4'])
    for h in headings[:20]:  # Show first 20 headings
        level = h.name
        text = h.get_text(strip=True)
        print(f"  {level}: {text}")

    # Look for exercise-related content
    print("\n🏃 EXERCISE-RELATED CONTENT:")
    print("-"*40)
    exercise_keywords = ['exercise', 'activity', 'walk', 'run', 'energy']
    found_exercise = False

    for p in soup.find_all('p'):
        text = p.get_text(strip=True)
        for keyword in exercise_keywords:
            if keyword in text.lower():
                print(f"  Found '{keyword}' in: {text[:limit_text]}...")
                found_exercise = True
                break
        if found_exercise:
            break

    if not found_exercise:
        print("  No exercise-related content found in paragraphs")

    # Look for training-related content
    print("\n🎯 TRAINING-RELATED CONTENT:")
    print("-"*40)
    training_keywords = ['train', 'obedience', 'command', 'teach', 'intelligent']
    found_training = False

    for p in soup.find_all('p'):
        text = p.get_text(strip=True)
        for keyword in training_keywords:
            if keyword in text.lower():
                print(f"  Found '{keyword}' in: {text[:limit_text]}...")
                found_training = True
                break
        if found_training:
            break

    if not found_training:
        print("  No training-related content found in paragraphs")

    # Look for grooming-related content
    print("\n✂️ GROOMING-RELATED CONTENT:")
    print("-"*40)
    grooming_keywords = ['groom', 'brush', 'coat', 'fur', 'shed', 'bath']
    found_grooming = False

    for p in soup.find_all('p'):
        text = p.get_text(strip=True)
        for keyword in grooming_keywords:
            if keyword in text.lower():
                print(f"  Found '{keyword}' in: {text[:limit_text]}...")
                found_grooming = True
                break
        if found_grooming:
            break

    if not found_grooming:
        print("  No grooming-related content found in paragraphs")

    # Look for child/pet compatibility
    print("\n👶 CHILD/PET COMPATIBILITY:")
    print("-"*40)
    compat_keywords = ['children', 'kids', 'family', 'other dogs', 'pets', 'cats']
    found_compat = False

    for p in soup.find_all('p'):
        text = p.get_text(strip=True)
        for keyword in compat_keywords:
            if keyword in text.lower():
                print(f"  Found '{keyword}' in: {text[:limit_text]}...")
                found_compat = True
                break
        if found_compat:
            break

    if not found_compat:
        print("  No compatibility-related content found")

    # Check what's in the first few paragraphs
    print("\n📄 FIRST 3 PARAGRAPHS:")
    print("-"*40)
    paragraphs = soup.find_all('p')
    for i, p in enumerate(paragraphs[:3]):
        text = p.get_text(strip=True)
        if text:
            print(f"\nParagraph {i+1}: {text[:300]}...")

# Test on a few popular breeds
test_breeds = [
    'golden-retriever',
    'german-shepherd',
    'labrador-retriever',
    'beagle',
    'bulldog'
]

print("DIAGNOSTIC: Wikipedia Content Analysis")
print("="*60)

for breed in test_breeds:
    try:
        analyze_breed_html(breed)
    except Exception as e:
        print(f"Error analyzing {breed}: {e}")

print("\n" + "="*60)
print("DIAGNOSTIC COMPLETE")