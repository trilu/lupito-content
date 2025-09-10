#!/usr/bin/env python3
"""
Compare scraped Wikipedia data with benchmark breeds table to analyze quality
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client
import pandas as pd
import numpy as np
from datetime import datetime

# Load environment variables
load_dotenv()

# Initialize Supabase client
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(url, key)

def fetch_benchmark_breeds():
    """Fetch benchmark data from breeds table"""
    response = supabase.table('breeds').select('*').execute()
    return pd.DataFrame(response.data)

def fetch_scraped_breeds():
    """Fetch scraped data from breeds_details table"""
    response = supabase.table('breeds_details').select('*').execute()
    return pd.DataFrame(response.data)

def normalize_breed_name(name):
    """Normalize breed name for comparison"""
    if pd.isna(name):
        return ''
    return str(name).lower().strip().replace(' ', '-')

def compare_weight_ranges(male_weight, female_weight, scraped_weight):
    """Compare weight ranges between benchmark and scraped data"""
    if pd.isna(scraped_weight):
        return None, None, None
    
    # Use average of male and female weights as benchmark
    bench_weights = []
    if not pd.isna(male_weight):
        bench_weights.append(float(male_weight))
    if not pd.isna(female_weight):
        bench_weights.append(float(female_weight))
    
    if not bench_weights:
        return None, None, None
    
    bench_avg = sum(bench_weights) / len(bench_weights)
    
    # Parse scraped weight (format: {"min": 25, "max": 32, "unit": "kg"})
    if isinstance(scraped_weight, dict):
        scrap_min = scraped_weight.get('min')
        scrap_max = scraped_weight.get('max')
        
        if scrap_min and scrap_max:
            # Calculate average of scraped weight
            scrap_avg = (scrap_min + scrap_max) / 2
            
            # Calculate difference
            diff = abs(bench_avg - scrap_avg)
            
            # Check if within reasonable range (20% tolerance)
            tolerance = 0.2
            matches = diff <= (bench_avg * tolerance)
            return bench_avg, scrap_avg, matches
    
    return None, None, False

def analyze_size_categories(benchmark_df, scraped_df):
    """Analyze size category accuracy"""
    # Merge dataframes
    benchmark_df['breed_slug'] = benchmark_df['name_en'].apply(normalize_breed_name)
    scraped_df['breed_slug'] = scraped_df['breed_slug'].apply(normalize_breed_name)
    
    # Prepare benchmark columns
    benchmark_cols = ['breed_slug', 'name_en', 'size_category', 'avg_male_weight_kg', 'avg_female_weight_kg']
    benchmark_subset = benchmark_df[benchmark_cols].copy()
    benchmark_subset.columns = ['breed_slug', 'name', 'size_benchmark', 'male_weight', 'female_weight']
    
    # Prepare scraped columns - using actual column names from breeds_details
    # Create weight dict from min/max values
    scraped_df['weight_dict'] = scraped_df.apply(
        lambda x: {'min': x['weight_kg_min'], 'max': x['weight_kg_max'], 'unit': 'kg'} 
        if pd.notna(x['weight_kg_min']) and pd.notna(x['weight_kg_max']) else None, 
        axis=1
    )
    scraped_df['life_expectancy'] = scraped_df.apply(
        lambda x: f"{x['lifespan_years_min']}-{x['lifespan_years_max']} years"
        if pd.notna(x['lifespan_years_min']) and pd.notna(x['lifespan_years_max']) else None,
        axis=1
    )
    
    scraped_cols = ['breed_slug', 'size', 'weight_dict', 'height_cm_min', 'height_cm_max', 'life_expectancy']
    scraped_subset = scraped_df[scraped_cols].copy()
    scraped_subset.columns = ['breed_slug', 'size_scraped', 'weight_scraped', 'height_min', 'height_max', 'life_expectancy']
    
    merged = pd.merge(
        benchmark_subset,
        scraped_subset,
        on='breed_slug',
        how='inner'
    )
    
    return merged

def main():
    print("=" * 80)
    print("WIKIPEDIA SCRAPING QUALITY ANALYSIS")
    print("=" * 80)
    print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Fetch data
    print("Fetching data...")
    benchmark_df = fetch_benchmark_breeds()
    scraped_df = fetch_scraped_breeds()
    
    print(f"Benchmark breeds (breeds table): {len(benchmark_df)}")
    print(f"Scraped breeds (breeds_details table): {len(scraped_df)}\n")
    
    # Analyze coverage
    print("COVERAGE ANALYSIS")
    print("-" * 60)
    
    # Find matching breeds
    merged_df = analyze_size_categories(benchmark_df, scraped_df)
    print(f"Breeds in both tables: {len(merged_df)}")
    print(f"Coverage rate: {len(merged_df)/len(benchmark_df)*100:.1f}%\n")
    
    # Analyze size categories
    print("SIZE CATEGORY COMPARISON")
    print("-" * 60)
    
    # Compare sizes (both already in same format: tiny, small, medium, large, giant)
    size_matches = merged_df[merged_df['size_benchmark'] == merged_df['size_scraped']]
    size_mismatches = merged_df[merged_df['size_benchmark'] != merged_df['size_scraped']]
    
    print(f"Size matches: {len(size_matches)} ({len(size_matches)/len(merged_df)*100:.1f}%)")
    print(f"Size mismatches: {len(size_mismatches)} ({len(size_mismatches)/len(merged_df)*100:.1f}%)")
    
    if len(size_mismatches) > 0:
        print("\nSIZE MISMATCHES (Top 20):")
        print("-" * 60)
        for idx, row in size_mismatches.head(20).iterrows():
            print(f"{row['name']}: Benchmark={row['size_benchmark']}, Scraped={row['size_scraped']}")
    
    # Analyze weight data quality
    print("\nWEIGHT DATA QUALITY")
    print("-" * 60)
    
    weight_comparison = []
    for idx, row in merged_df.iterrows():
        bench_avg, scrap_avg, matches = compare_weight_ranges(row['male_weight'], row['female_weight'], row['weight_scraped'])
        if bench_avg is not None:
            weight_comparison.append({
                'breed': row['name'],
                'benchmark_avg': bench_avg,
                'scraped_avg': scrap_avg,
                'scraped_weight': row['weight_scraped'],
                'diff': abs(bench_avg - scrap_avg),
                'matches': matches
            })
    
    weight_df = pd.DataFrame(weight_comparison)
    if len(weight_df) > 0:
        matching_weights = weight_df[weight_df['matches'] == True]
        print(f"Weights within 20% tolerance: {len(matching_weights)}/{len(weight_df)} ({len(matching_weights)/len(weight_df)*100:.1f}%)")
        
        # Show large discrepancies
        large_discrepancies = weight_df[weight_df['matches'] == False].head(10)
        if len(large_discrepancies) > 0:
            print("\nLARGE WEIGHT DISCREPANCIES (Top 10):")
            print("-" * 60)
            for idx, row in large_discrepancies.iterrows():
                print(f"{row['breed']}:")
                print(f"  Benchmark avg: {row['benchmark_avg']:.1f}kg")
                print(f"  Scraped: {row['scraped_weight']}")
                print(f"  Difference: {row['diff']:.1f}kg")
    
    # Check for critical breeds
    print("\nCRITICAL BREEDS CHECK")
    print("-" * 60)
    
    critical_breeds = ['Labrador Retriever', 'German Shepherd', 'Golden Retriever', 
                       'French Bulldog', 'Bulldog', 'Poodle', 'Beagle', 'Rottweiler']
    
    for breed in critical_breeds:
        breed_data = merged_df[merged_df['name'] == breed]
        if len(breed_data) > 0:
            row = breed_data.iloc[0]
            print(f"\n{breed}:")
            print(f"  Size: Benchmark={row['size_benchmark']}, Scraped={row['size_scraped']}")
            print(f"  Weight: Scraped={row['weight_scraped']}")
            
            # Special check for Labrador (the original issue)
            if breed == 'Labrador Retriever':
                if row['size_scraped'] == 'small':
                    print("  ⚠️ WARNING: Labrador still marked as SMALL!")
                else:
                    print("  ✅ SUCCESS: Labrador size corrected!")
        else:
            print(f"\n{breed}: NOT FOUND in scraped data")
    
    # Data completeness
    print("\nDATA COMPLETENESS")
    print("-" * 60)
    
    has_weight = scraped_df['weight_kg_min'].notna().sum()
    has_height = scraped_df['height_cm_min'].notna().sum()
    has_life = scraped_df['lifespan_years_min'].notna().sum()
    has_size = scraped_df['size'].notna().sum()
    
    print(f"Has weight data: {has_weight}/{len(scraped_df)} ({has_weight/len(scraped_df)*100:.1f}%)")
    print(f"Has height data: {has_height}/{len(scraped_df)} ({has_height/len(scraped_df)*100:.1f}%)")
    print(f"Has life expectancy: {has_life}/{len(scraped_df)} ({has_life/len(scraped_df)*100:.1f}%)")
    print(f"Has size category: {has_size}/{len(scraped_df)} ({has_size/len(scraped_df)*100:.1f}%)")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    quality_score = 0
    max_score = 5
    
    # Coverage score
    coverage_rate = len(merged_df)/len(benchmark_df)
    if coverage_rate > 0.8:
        quality_score += 1
        print("✅ Good coverage (>80%)")
    else:
        print("❌ Poor coverage (<80%)")
    
    # Size accuracy score
    if len(merged_df) > 0:
        size_accuracy = len(size_matches)/len(merged_df)
        if size_accuracy > 0.7:
            quality_score += 1
            print(f"✅ Good size accuracy ({size_accuracy*100:.1f}%)")
        else:
            print(f"❌ Poor size accuracy ({size_accuracy*100:.1f}%)")
    
    # Weight accuracy score
    if len(weight_df) > 0:
        weight_accuracy = len(matching_weights)/len(weight_df)
        if weight_accuracy > 0.7:
            quality_score += 1
            print(f"✅ Good weight accuracy ({weight_accuracy*100:.1f}%)")
        else:
            print(f"❌ Poor weight accuracy ({weight_accuracy*100:.1f}%)")
    
    # Data completeness score
    completeness = (has_weight + has_height + has_life + has_size) / (len(scraped_df) * 4)
    if completeness > 0.7:
        quality_score += 1
        print(f"✅ Good data completeness ({completeness*100:.1f}%)")
    else:
        print(f"❌ Poor data completeness ({completeness*100:.1f}%)")
    
    # Labrador fix score (critical issue)
    labrador_check = merged_df[merged_df['name'] == 'Labrador Retriever']
    if len(labrador_check) > 0 and labrador_check.iloc[0]['size_scraped'] != 'small':
        quality_score += 1
        print("✅ Critical issue fixed (Labrador size)")
    else:
        print("❌ Critical issue NOT fixed (Labrador size)")
    
    print(f"\nOVERALL QUALITY SCORE: {quality_score}/{max_score} ({quality_score/max_score*100:.0f}%)")
    
    # Save detailed report
    report_data = {
        'analysis_date': datetime.now().isoformat(),
        'coverage_rate': coverage_rate,
        'size_accuracy': size_accuracy if len(merged_df) > 0 else 0,
        'weight_accuracy': weight_accuracy if len(weight_df) > 0 else 0,
        'data_completeness': completeness,
        'quality_score': quality_score,
        'max_score': max_score,
        'total_benchmark_breeds': len(benchmark_df),
        'total_scraped_breeds': len(scraped_df),
        'matched_breeds': len(merged_df)
    }
    
    import json
    with open('scraping_quality_report.json', 'w') as f:
        json.dump(report_data, f, indent=2)
    
    print("\nDetailed report saved to: scraping_quality_report.json")

if __name__ == "__main__":
    main()