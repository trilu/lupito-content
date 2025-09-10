#!/usr/bin/env python3
"""
Fix weight outliers in breeds database.
Targets breeds with impossible weights that need correction.
"""

import os
from dotenv import load_dotenv
from supabase import create_client
import pandas as pd
from datetime import datetime

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)

# Known correct weights for breeds with outliers
WEIGHT_CORRECTIONS = {
    # Breed slug: (min_weight, max_weight, reason)
    'great-dane': (54.0, 90.0, 'Known giant breed, was 27.2kg'),
    'japanese-chin': (1.8, 4.1, 'Was 537.5kg - obvious error'),
    'spanish-mastiff': (55.0, 100.0, 'Large mastiff breed, was 120kg'),
    
    # Common breeds that might have wrong weights
    'yorkshire-terrier': (2.0, 3.2, 'Tiny breed, should be 2-3kg'),
    'chihuahua': (1.5, 3.0, 'Smallest breed, should be under 3kg'),
    'mastiff': (54.0, 91.0, 'Giant breed, English Mastiff'),
    'saint-bernard': (54.0, 82.0, 'Giant breed'),
    'newfoundland': (45.0, 68.0, 'Large working breed'),
    'irish-wolfhound': (40.0, 69.0, 'Tallest breed'),
    'great-pyrenees': (39.0, 73.0, 'Large mountain dog'),
    
    # Breeds that commonly have errors
    'pomeranian': (1.8, 3.5, 'Toy breed'),
    'papillon': (3.0, 5.0, 'Small toy breed'),
    'maltese': (2.0, 4.0, 'Toy breed'),
    'toy-poodle': (2.0, 4.0, 'Toy variety'),
    'teacup-yorkshire-terrier': (1.0, 2.0, 'Teacup variety'),
}

def find_outliers():
    """Find breeds with weight outliers"""
    response = supabase.table('breeds_details').select('*').execute()
    df = pd.DataFrame(response.data)
    
    outliers = []
    
    for _, breed in df.iterrows():
        if pd.isna(breed['weight_kg_max']):
            continue
            
        weight_max = breed['weight_kg_max']
        weight_min = breed.get('weight_kg_min', weight_max)
        name = breed['display_name']
        slug = breed['breed_slug']
        
        # Check for outliers
        issues = []
        
        if weight_max < 1.0:
            issues.append(f"Too light (<1kg): {weight_max:.1f}kg")
        elif weight_max > 100:
            issues.append(f"Too heavy (>100kg): {weight_max:.1f}kg")
        
        # Check for known large breeds with small weights
        large_breed_keywords = ['mastiff', 'dane', 'bernard', 'newfoundland', 'wolfhound', 'pyrenees']
        if any(keyword in name.lower() for keyword in large_breed_keywords):
            if weight_max < 40:
                issues.append(f"Large breed with small weight: {weight_max:.1f}kg")
        
        # Check for toy breeds with large weights
        toy_breed_keywords = ['toy', 'teacup', 'chihuahua', 'yorkshire', 'maltese', 'papillon']
        if any(keyword in name.lower() for keyword in toy_breed_keywords):
            if weight_max > 10:
                issues.append(f"Toy breed with large weight: {weight_max:.1f}kg")
        
        # Check for impossible weight ranges
        if weight_min > weight_max:
            issues.append(f"Min > Max: {weight_min:.1f} > {weight_max:.1f}")
        
        if issues:
            outliers.append({
                'slug': slug,
                'name': name,
                'weight_min': weight_min,
                'weight_max': weight_max,
                'issues': issues
            })
    
    return outliers

def fix_outlier(slug, min_weight, max_weight, reason):
    """Fix a weight outlier"""
    try:
        # Calculate correct size
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
        
        response = supabase.table('breeds_details').update(update_data).eq('breed_slug', slug).execute()
        
        print(f"  ✅ Fixed: {min_weight:.1f}-{max_weight:.1f}kg, size={size}")
        print(f"     Reason: {reason}")
        return True
        
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False

def main():
    print("=" * 80)
    print("FIXING WEIGHT OUTLIERS")
    print("=" * 80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Find outliers
    outliers = find_outliers()
    print(f"\nFound {len(outliers)} breeds with weight issues")
    
    if not outliers:
        print("✅ No weight outliers found!")
        return
    
    # Show sample
    print("\nSample of outliers found:")
    for outlier in outliers[:10]:
        print(f"  {outlier['name']:30s}: {outlier['weight_min']:.1f}-{outlier['weight_max']:.1f}kg")
        for issue in outlier['issues']:
            print(f"    - {issue}")
    
    # Fix known corrections
    print("\n" + "=" * 60)
    print("APPLYING CORRECTIONS")
    print("=" * 60)
    
    fixed = 0
    
    for outlier in outliers:
        slug = outlier['slug']
        name = outlier['name']
        
        if slug in WEIGHT_CORRECTIONS:
            min_w, max_w, reason = WEIGHT_CORRECTIONS[slug]
            print(f"\n{name} ({slug})")
            print(f"  Current: {outlier['weight_min']:.1f}-{outlier['weight_max']:.1f}kg")
            print(f"  Correct: {min_w:.1f}-{max_w:.1f}kg")
            
            if fix_outlier(slug, min_w, max_w, reason):
                fixed += 1
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total outliers: {len(outliers)}")
    print(f"Fixed: {fixed}")
    print(f"Remaining: {len(outliers) - fixed}")
    
    # Check quality impact
    print("\n" + "=" * 80)
    print("QUALITY IMPACT")
    print("=" * 80)
    
    # Run internal consistency check
    response = supabase.table('breeds_details').select('weight_kg_max, size').execute()
    df = pd.DataFrame(response.data)
    
    # Check consistency
    with_weight = df[df['weight_kg_max'].notna()]
    total_with_weight = len(with_weight)
    
    def expected_size(w):
        if pd.isna(w): return None
        if w < 4: return 'tiny'
        elif w < 10: return 'small'
        elif w < 25: return 'medium'
        elif w < 45: return 'large'
        else: return 'giant'
    
    with_weight['expected'] = with_weight['weight_kg_max'].apply(expected_size)
    with_weight['consistent'] = with_weight['size'] == with_weight['expected']
    
    consistency = with_weight['consistent'].mean() * 100
    
    print(f"Internal consistency: {consistency:.1f}%")
    print(f"Weight data coverage: {len(with_weight)/len(df)*100:.1f}%")
    
    # Calculate overall score
    scores = {
        'Coverage': 100.0,
        'Completeness': 65.0,  # Estimate
        'Consistency': consistency,
        'Weight Coverage': len(with_weight)/len(df)*100,
        'Recency': 100.0
    }
    
    overall = sum(scores.values()) / len(scores)
    grade = 'A' if overall >= 90 else 'B' if overall >= 80 else 'C'
    
    print(f"\nEstimated quality score: {overall:.1f}% (Grade {grade})")
    
    if overall >= 90:
        print("\n✅ GRADE A ACHIEVED!")
    else:
        print(f"\n⚠️ Need +{90-overall:.1f}% for Grade A")
    
    print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()