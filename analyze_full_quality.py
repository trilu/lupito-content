#!/usr/bin/env python3
"""
Comprehensive quality analysis of breeds_details table vs benchmark breeds table
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

def fetch_benchmark_data():
    """Fetch the benchmark breeds data"""
    response = supabase.table('breeds').select('*').execute()
    return pd.DataFrame(response.data)

def fetch_scraped_data():
    """Fetch the scraped breeds_details data"""
    response = supabase.table('breeds_details').select('*').execute()
    return pd.DataFrame(response.data)

def normalize_breed_name(name):
    """Normalize breed names for matching"""
    if pd.isna(name):
        return ""
    # Remove common suffixes and normalize
    name = str(name).lower().strip()
    name = name.replace(' dog', '').replace(' hound', '')
    name = name.replace('-', ' ').replace('_', ' ')
    return name

def compare_sizes(bench_size, scraped_size):
    """Compare size categories between benchmark and scraped"""
    size_map = {
        'toy': ['toy', 'tiny'],
        'small': ['small'],
        'medium': ['medium'],
        'large': ['large'],
        'giant': ['giant', 'extra large', 'xl']
    }
    
    if pd.isna(bench_size) or pd.isna(scraped_size):
        return False
    
    bench_size = str(bench_size).lower().strip()
    scraped_size = str(scraped_size).lower().strip()
    
    # Direct match
    if bench_size == scraped_size:
        return True
    
    # Check if both map to same category
    for category, variants in size_map.items():
        if bench_size in variants and scraped_size in variants:
            return True
    
    return False

def analyze_weight_accuracy(bench_weight, scraped_min, scraped_max):
    """Analyze weight accuracy"""
    if pd.isna(bench_weight) or pd.isna(scraped_min):
        return None
    
    try:
        bench_weight = float(bench_weight)
        scraped_min = float(scraped_min)
        scraped_max = float(scraped_max) if not pd.isna(scraped_max) else scraped_min
        
        # Check if benchmark falls within scraped range
        if scraped_min <= bench_weight <= scraped_max:
            return 1.0  # Perfect match
        
        # Calculate how far off we are
        if bench_weight < scraped_min:
            diff = scraped_min - bench_weight
        else:
            diff = bench_weight - scraped_max
            
        # Return accuracy as percentage (0-1)
        accuracy = max(0, 1 - (diff / bench_weight))
        return accuracy
    except:
        return None

def main():
    print("=" * 80)
    print("COMPREHENSIVE BREEDS QUALITY ANALYSIS")
    print("=" * 80)
    print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Fetch data
    print("Fetching data...")
    benchmark_df = fetch_benchmark_data()
    scraped_df = fetch_scraped_data()
    
    print(f"✓ Benchmark breeds: {len(benchmark_df)}")
    print(f"✓ Scraped breeds: {len(scraped_df)}")
    print()
    
    # Normalize names for matching
    benchmark_df['norm_name'] = benchmark_df['name_en'].apply(normalize_breed_name)
    scraped_df['norm_name'] = scraped_df['display_name'].apply(normalize_breed_name)
    
    # Create slug mapping for better matching
    scraped_df['slug_norm'] = scraped_df['breed_slug'].str.replace('-', ' ')
    
    # Match breeds
    matched_breeds = []
    unmatched_benchmark = []
    
    for _, bench_breed in benchmark_df.iterrows():
        # Try to match by normalized name or slug
        match = scraped_df[
            (scraped_df['norm_name'] == bench_breed['norm_name']) |
            (scraped_df['slug_norm'] == bench_breed['norm_name'])
        ]
        
        if not match.empty:
            matched_breeds.append({
                'benchmark': bench_breed,
                'scraped': match.iloc[0]
            })
        else:
            unmatched_benchmark.append(bench_breed['name_en'])
    
    print("=" * 80)
    print("1. COVERAGE ANALYSIS")
    print("=" * 80)
    
    coverage_rate = len(matched_breeds) / len(benchmark_df) * 100
    print(f"Matched breeds: {len(matched_breeds)}/{len(benchmark_df)} ({coverage_rate:.1f}%)")
    print(f"Unmatched benchmark breeds: {len(unmatched_benchmark)}")
    
    if unmatched_benchmark[:10]:
        print("\nSample of unmatched breeds:")
        for breed in unmatched_benchmark[:10]:
            print(f"  - {breed}")
    
    print()
    print("=" * 80)
    print("2. DATA COMPLETENESS")
    print("=" * 80)
    
    # Check completeness of scraped data
    completeness = {
        'weight_kg_min': (~scraped_df['weight_kg_min'].isna()).mean() * 100,
        'weight_kg_max': (~scraped_df['weight_kg_max'].isna()).mean() * 100,
        'height_cm_min': (~scraped_df['height_cm_min'].isna()).mean() * 100,
        'height_cm_max': (~scraped_df['height_cm_max'].isna()).mean() * 100,
        'size': (~scraped_df['size'].isna()).mean() * 100,
        'lifespan_years_min': (~scraped_df['lifespan_years_min'].isna()).mean() * 100,
        'energy': (~scraped_df['energy'].isna()).mean() * 100,
        'trainability': (~scraped_df['trainability'].isna()).mean() * 100,
    }
    
    for field, pct in completeness.items():
        status = "✅" if pct > 70 else "⚠️" if pct > 40 else "❌"
        print(f"{status} {field:30s}: {pct:5.1f}%")
    
    avg_completeness = np.mean(list(completeness.values()))
    print(f"\nAverage completeness: {avg_completeness:.1f}%")
    
    print()
    print("=" * 80)
    print("3. SIZE ACCURACY")
    print("=" * 80)
    
    size_matches = 0
    size_total = 0
    size_mismatches = []
    
    for match in matched_breeds:
        bench = match['benchmark']
        scraped = match['scraped']
        
        # Try different size field names in benchmark
        bench_size = bench.get('size_category') or bench.get('size_name') or bench.get('size')
        
        if not pd.isna(bench_size) and not pd.isna(scraped.get('size')):
            size_total += 1
            if compare_sizes(bench_size, scraped['size']):
                size_matches += 1
            else:
                size_mismatches.append({
                    'breed': bench['name_en'],
                    'benchmark': bench_size,
                    'scraped': scraped['size']
                })
    
    if size_total > 0:
        size_accuracy = size_matches / size_total * 100
        print(f"Size matches: {size_matches}/{size_total} ({size_accuracy:.1f}%)")
        
        if size_mismatches[:5]:
            print("\nSample size mismatches:")
            for mismatch in size_mismatches[:5]:
                print(f"  {mismatch['breed']:30s}: {mismatch['benchmark']:10s} → {mismatch['scraped']:10s}")
    else:
        size_accuracy = 0
        print("No size data to compare in benchmark")
    
    print()
    print("=" * 80)
    print("4. WEIGHT ACCURACY")
    print("=" * 80)
    
    weight_accuracies = []
    weight_issues = []
    
    for match in matched_breeds:
        bench = match['benchmark']
        scraped = match['scraped']
        
        # Get benchmark weights - try different field names
        bench_weights = []
        if not pd.isna(bench.get('avg_male_weight_kg')):
            bench_weights.append(float(bench['avg_male_weight_kg']))
        elif not pd.isna(bench.get('average_weight_male_kg')):
            bench_weights.append(float(bench['average_weight_male_kg']))
            
        if not pd.isna(bench.get('avg_female_weight_kg')):
            bench_weights.append(float(bench['avg_female_weight_kg']))
        elif not pd.isna(bench.get('average_weight_female_kg')):
            bench_weights.append(float(bench['average_weight_female_kg']))
        
        if bench_weights and not pd.isna(scraped.get('weight_kg_min')):
            bench_avg = np.mean(bench_weights)
            accuracy = analyze_weight_accuracy(
                bench_avg, 
                scraped['weight_kg_min'], 
                scraped['weight_kg_max']
            )
            
            if accuracy is not None:
                weight_accuracies.append(accuracy)
                
                if accuracy < 0.8:  # Less than 80% accurate
                    weight_issues.append({
                        'breed': bench['name_en'],
                        'benchmark': f"{bench_avg:.1f}",
                        'scraped': f"{scraped['weight_kg_min']:.1f}-{scraped['weight_kg_max']:.1f}",
                        'accuracy': accuracy
                    })
    
    if weight_accuracies:
        avg_weight_accuracy = np.mean(weight_accuracies) * 100
        high_accuracy = sum(1 for a in weight_accuracies if a >= 0.8) / len(weight_accuracies) * 100
        
        print(f"Average weight accuracy: {avg_weight_accuracy:.1f}%")
        print(f"Breeds with ≥80% accuracy: {high_accuracy:.1f}%")
        print(f"Total breeds with weight data: {len(weight_accuracies)}")
        
        if weight_issues[:5]:
            print("\nBreeds with weight discrepancies:")
            for issue in sorted(weight_issues, key=lambda x: x['accuracy'])[:5]:
                print(f"  {issue['breed']:30s}: {issue['benchmark']:8s}kg → {issue['scraped']:15s}kg (accuracy: {issue['accuracy']*100:.0f}%)")
    else:
        avg_weight_accuracy = 0
        print("No weight data to compare in benchmark")
    
    print()
    print("=" * 80)
    print("5. UPDATE RECENCY")
    print("=" * 80)
    
    # Check when breeds were last updated
    scraped_df['updated_at'] = pd.to_datetime(scraped_df['updated_at'])
    today = pd.Timestamp.now(tz='UTC')
    
    scraped_df['days_since_update'] = (today - scraped_df['updated_at']).dt.days
    
    updated_today = (scraped_df['days_since_update'] == 0).sum()
    updated_week = (scraped_df['days_since_update'] <= 7).sum()
    updated_month = (scraped_df['days_since_update'] <= 30).sum()
    
    print(f"Updated today: {updated_today} breeds")
    print(f"Updated this week: {updated_week} breeds")
    print(f"Updated this month: {updated_month} breeds")
    print(f"Never updated (>30 days): {len(scraped_df) - updated_month} breeds")
    
    print()
    print("=" * 80)
    print("6. CRITICAL BREEDS CHECK")
    print("=" * 80)
    
    critical_breeds = [
        'labrador-retriever', 'german-shepherd', 'golden-retriever',
        'french-bulldog', 'bulldog', 'poodle', 'beagle', 'rottweiler',
        'yorkshire-terrier', 'dachshund'
    ]
    
    print("Status of most popular breeds:")
    for breed_slug in critical_breeds:
        breed = scraped_df[scraped_df['breed_slug'] == breed_slug]
        if not breed.empty:
            breed = breed.iloc[0]
            status = "✅" if breed['days_since_update'] == 0 else "⚠️" if breed['days_since_update'] <= 7 else "❌"
            weight_str = f"{breed['weight_kg_min']:.1f}-{breed['weight_kg_max']:.1f}" if not pd.isna(breed['weight_kg_min']) else "N/A"
            print(f"{status} {breed['display_name']:30s}: Size={breed['size']:10s} Weight={weight_str:15s}kg")
        else:
            print(f"❌ {breed_slug:30s}: NOT FOUND")
    
    print()
    print("=" * 80)
    print("OVERALL QUALITY SCORE")
    print("=" * 80)
    
    # Calculate overall score
    scores = {
        'Coverage': min(100, coverage_rate),
        'Completeness': avg_completeness,
        'Size Accuracy': size_accuracy if size_total > 0 else 0,
        'Weight Accuracy': avg_weight_accuracy if weight_accuracies else 0,
        'Update Recency': (updated_week / len(scraped_df)) * 100
    }
    
    for metric, score in scores.items():
        bar = "█" * int(score / 5) + "░" * (20 - int(score / 5))
        print(f"{metric:20s}: {bar} {score:5.1f}%")
    
    overall_score = np.mean(list(scores.values()))
    print()
    print(f"{'='*60}")
    grade = "A" if overall_score >= 90 else "B" if overall_score >= 80 else "C" if overall_score >= 70 else "D" if overall_score >= 60 else "F"
    print(f"FINAL QUALITY SCORE: {overall_score:.1f}% (Grade: {grade})")
    print(f"{'='*60}")
    
    # Summary recommendations
    print()
    print("RECOMMENDATIONS:")
    print("-" * 40)
    
    if coverage_rate < 90:
        print(f"• Add {len(unmatched_benchmark)} missing breeds from benchmark")
    
    if avg_completeness < 70:
        print(f"• Improve data completeness (currently {avg_completeness:.1f}%)")
    
    if size_total > 0 and size_accuracy < 80:
        print(f"• Fix size categories for {size_total - size_matches} breeds")
    
    if weight_accuracies and avg_weight_accuracy < 80:
        print(f"• Correct weight data for {len(weight_issues)} breeds with discrepancies")
    
    if updated_month < len(scraped_df) * 0.8:
        print(f"• Update {len(scraped_df) - updated_month} breeds that haven't been scraped recently")

if __name__ == "__main__":
    main()