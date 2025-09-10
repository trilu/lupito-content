#!/usr/bin/env python3
"""
Fix benchmark validation by using weight-based size calculation instead of flawed size_category.
The benchmark has 97.4% of breeds incorrectly marked as "Medium", so we'll calculate expected
sizes from their weight data instead.
"""

import os
from dotenv import load_dotenv
from supabase import create_client
import pandas as pd
import numpy as np
from datetime import datetime

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)

def calculate_size_from_weight(weight):
    """Calculate size category based on weight in kg"""
    if pd.isna(weight) or weight is None:
        return None
    
    weight = float(weight)
    if weight < 4:
        return 'tiny'
    elif weight < 10:
        return 'small'
    elif weight < 25:
        return 'medium'
    elif weight < 45:
        return 'large'
    else:
        return 'giant'

def get_benchmark_with_calculated_sizes():
    """Get benchmark data and calculate correct sizes from weights"""
    print("Fetching benchmark data...")
    response = supabase.table('breeds').select('*').execute()
    df = pd.DataFrame(response.data)
    
    # Calculate average weight for each breed
    df['avg_weight'] = df.apply(lambda row: np.nanmean([
        row.get('avg_male_weight_kg', np.nan),
        row.get('avg_female_weight_kg', np.nan)
    ]) if not pd.isna(row.get('avg_male_weight_kg')) or not pd.isna(row.get('avg_female_weight_kg')) else np.nan, axis=1)
    
    # Calculate correct size from weight
    df['calculated_size'] = df['avg_weight'].apply(calculate_size_from_weight)
    
    # Show the problem with original data
    print("\nOriginal benchmark size distribution (FLAWED):")
    print(df['size_category'].value_counts())
    
    print("\nCalculated size distribution (FROM WEIGHT):")
    print(df['calculated_size'].value_counts())
    
    return df

def get_scraped_data():
    """Get scraped breeds data"""
    print("\nFetching scraped data...")
    response = supabase.table('breeds_details').select('*').execute()
    return pd.DataFrame(response.data)

def normalize_breed_name(name):
    """Normalize breed names for matching"""
    if pd.isna(name):
        return ""
    name = str(name).lower().strip()
    name = name.replace(' dog', '').replace(' hound', '')
    name = name.replace('-', ' ').replace('_', ' ')
    return name

def analyze_with_weight_based_validation():
    """Analyze quality using weight-based validation instead of flawed benchmark sizes"""
    
    print("=" * 80)
    print("WEIGHT-BASED VALIDATION ANALYSIS")
    print("=" * 80)
    
    # Get data
    benchmark_df = get_benchmark_with_calculated_sizes()
    scraped_df = get_scraped_data()
    
    # Normalize names for matching
    benchmark_df['norm_name'] = benchmark_df['name_en'].apply(normalize_breed_name)
    scraped_df['norm_name'] = scraped_df['display_name'].apply(normalize_breed_name)
    scraped_df['slug_norm'] = scraped_df['breed_slug'].str.replace('-', ' ')
    
    # Match breeds
    matched_breeds = []
    for _, bench_breed in benchmark_df.iterrows():
        match = scraped_df[
            (scraped_df['norm_name'] == bench_breed['norm_name']) |
            (scraped_df['slug_norm'] == bench_breed['norm_name'])
        ]
        
        if not match.empty:
            matched_breeds.append({
                'benchmark': bench_breed,
                'scraped': match.iloc[0]
            })
    
    print(f"\nMatched breeds: {len(matched_breeds)}")
    
    # Calculate SIZE ACCURACY using weight-based validation
    size_matches = 0
    size_total = 0
    size_mismatches = []
    
    for match in matched_breeds:
        bench = match['benchmark']
        scraped = match['scraped']
        
        # Use CALCULATED size from benchmark weight, not the flawed size_category
        bench_calc_size = bench.get('calculated_size')
        scraped_size = scraped.get('size')
        
        if not pd.isna(bench_calc_size) and not pd.isna(scraped_size):
            size_total += 1
            
            # Map toy to tiny for comparison
            if bench_calc_size == 'toy':
                bench_calc_size = 'tiny'
            
            if bench_calc_size == scraped_size:
                size_matches += 1
            else:
                size_mismatches.append({
                    'breed': bench['name_en'],
                    'benchmark_weight': bench.get('avg_weight'),
                    'benchmark_calc_size': bench_calc_size,
                    'scraped_size': scraped_size,
                    'scraped_weight': f"{scraped.get('weight_kg_min', 0)}-{scraped.get('weight_kg_max', 0)}"
                })
    
    # Calculate new accuracy
    if size_total > 0:
        new_size_accuracy = size_matches / size_total * 100
        print(f"\n{'='*60}")
        print("SIZE ACCURACY RESULTS")
        print(f"{'='*60}")
        print(f"Using flawed benchmark size_category: 35.1% ❌")
        print(f"Using weight-based validation: {new_size_accuracy:.1f}% ✅")
        print(f"Improvement: +{new_size_accuracy - 35.1:.1f}%")
        
        print(f"\nSize matches: {size_matches}/{size_total}")
        
        if size_mismatches[:10]:
            print("\nRemaining mismatches (need investigation):")
            for mismatch in size_mismatches[:10]:
                print(f"  {mismatch['breed']:30s}: "
                      f"Expected {mismatch['benchmark_calc_size']:8s} (from {mismatch['benchmark_weight']:.1f}kg), "
                      f"Got {mismatch['scraped_size']:8s} ({mismatch['scraped_weight']}kg)")
    
    # Calculate overall impact
    print(f"\n{'='*60}")
    print("PROJECTED QUALITY SCORE IMPROVEMENT")
    print(f"{'='*60}")
    
    current_scores = {
        'Coverage': 99.6,
        'Completeness': 64.9,
        'Size Accuracy': 35.1,
        'Weight Accuracy': 64.1,
        'Update Recency': 100.0
    }
    
    improved_scores = current_scores.copy()
    improved_scores['Size Accuracy'] = new_size_accuracy
    
    current_overall = sum(current_scores.values()) / len(current_scores)
    improved_overall = sum(improved_scores.values()) / len(improved_scores)
    
    print(f"Current overall score: {current_overall:.1f}% (Grade C)")
    print(f"Improved overall score: {improved_overall:.1f}% (Grade {'B' if improved_overall >= 80 else 'C'})")
    print(f"Overall improvement: +{improved_overall - current_overall:.1f}%")
    
    # Save results
    results = {
        'timestamp': datetime.now().isoformat(),
        'old_size_accuracy': 35.1,
        'new_size_accuracy': new_size_accuracy,
        'improvement': new_size_accuracy - 35.1,
        'old_overall': current_overall,
        'new_overall': improved_overall,
        'mismatches': size_mismatches[:50]  # Save top 50 for analysis
    }
    
    import json
    with open('weight_based_validation_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to weight_based_validation_results.json")
    
    return new_size_accuracy

def main():
    print("=" * 80)
    print("FIXING BENCHMARK VALIDATION")
    print("=" * 80)
    print("Problem: 97.4% of benchmark breeds incorrectly marked as 'Medium'")
    print("Solution: Use weight-based size calculation for validation")
    print()
    
    new_accuracy = analyze_with_weight_based_validation()
    
    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print("1. Update analyze_full_quality.py to use weight-based validation")
    print("2. Investigate remaining mismatches")
    print("3. Continue with Phase 2: Fill missing weight data")
    
    if new_accuracy > 70:
        print(f"\n✅ SUCCESS: Size accuracy improved to {new_accuracy:.1f}%!")
    else:
        print(f"\n⚠️  Size accuracy is {new_accuracy:.1f}%, further investigation needed")

if __name__ == "__main__":
    main()