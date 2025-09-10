#!/usr/bin/env python3
"""
Enrich breeds data to Grade A+ (98% coverage) using multi-source approach.
Primary: Wikipedia (existing scraper)
Backup: Manual data for common breeds
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from supabase import create_client
import json

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)

# Comprehensive weight data for missing breeds
BREED_DATA = {
    # Format: 'slug': (min_kg, max_kg, min_cm, max_cm, min_years, max_years)
    'affenpinscher': (3.0, 6.0, 25, 30, 12, 14),
    'afghan-hound': (23.0, 27.0, 64, 74, 12, 14),
    'airedale-terrier': (19.0, 25.0, 56, 61, 10, 13),
    'akita': (32.0, 59.0, 61, 71, 10, 13),
    'alaskan-malamute': (32.0, 43.0, 58, 64, 10, 14),
    'american-bulldog': (27.0, 58.0, 50, 70, 10, 15),
    'american-eskimo-dog': (2.7, 16.0, 23, 48, 13, 15),
    'american-staffordshire-terrier': (18.0, 32.0, 43, 48, 12, 16),
    'anatolian-shepherd': (40.0, 65.0, 71, 81, 11, 13),
    'australian-cattle-dog': (15.0, 22.0, 43, 51, 12, 16),
    'australian-shepherd': (16.0, 32.0, 46, 58, 12, 15),
    'basenji': (9.0, 11.0, 40, 43, 12, 14),
    'basset-hound': (20.0, 29.0, 28, 38, 10, 12),
    'beagle': (9.0, 11.0, 33, 40, 12, 15),
    'bearded-collie': (18.0, 27.0, 51, 56, 12, 14),
    'belgian-malinois': (18.0, 36.0, 56, 66, 12, 14),
    'bernese-mountain-dog': (32.0, 52.0, 58, 70, 6, 8),
    'bichon-frise': (5.0, 8.0, 23, 30, 14, 15),
    'black-and-tan-coonhound': (29.0, 50.0, 58, 69, 10, 12),
    'bloodhound': (36.0, 50.0, 58, 69, 10, 12),
    'border-collie': (12.0, 20.0, 46, 56, 12, 15),
    'border-terrier': (5.0, 7.0, 28, 40, 12, 15),
    'borzoi': (27.0, 48.0, 66, 81, 10, 12),
    'boston-terrier': (5.0, 11.0, 38, 43, 11, 13),
    'bouvier-des-flandres': (27.0, 40.0, 59, 68, 10, 12),
    'boxer': (25.0, 32.0, 53, 64, 10, 12),
    'briard': (25.0, 45.0, 56, 69, 10, 12),
    'brittany': (14.0, 18.0, 43, 52, 12, 15),
    'brussels-griffon': (3.0, 6.0, 18, 20, 12, 15),
    'bull-terrier': (20.0, 32.0, 53, 56, 10, 14),
    'bulldog': (18.0, 25.0, 31, 40, 8, 10),
    'bullmastiff': (45.0, 59.0, 61, 69, 7, 9),
    'cairn-terrier': (6.0, 8.0, 23, 33, 13, 15),
    'cane-corso': (40.0, 50.0, 60, 70, 9, 12),
    'cardigan-welsh-corgi': (11.0, 17.0, 27, 33, 12, 15),
    'cavalier-king-charles-spaniel': (5.0, 8.0, 30, 33, 9, 14),
    'chesapeake-bay-retriever': (25.0, 36.0, 53, 66, 10, 13),
    'chihuahua': (1.5, 3.0, 15, 23, 14, 18),
    'chinese-crested': (3.6, 5.4, 23, 33, 13, 15),
    'chinese-shar-pei': (18.0, 30.0, 46, 51, 8, 12),
    'chow-chow': (20.0, 32.0, 43, 56, 8, 12),
    'clumber-spaniel': (25.0, 39.0, 43, 51, 10, 12),
    'cocker-spaniel': (11.0, 14.0, 34, 39, 12, 15),
    'collie': (20.0, 29.0, 51, 61, 12, 14),
    'coton-de-tulear': (4.0, 6.0, 22, 28, 14, 16),
    'curly-coated-retriever': (27.0, 41.0, 58, 69, 10, 12),
    'dachshund': (7.0, 14.0, 13, 23, 12, 16),
    'dalmatian': (20.0, 32.0, 48, 61, 11, 13),
    'dandie-dinmont-terrier': (8.0, 11.0, 20, 28, 12, 15),
    'doberman-pinscher': (27.0, 45.0, 61, 71, 10, 13),
    'dogue-de-bordeaux': (45.0, 68.0, 58, 69, 5, 8),
    'english-cocker-spaniel': (12.0, 15.0, 38, 43, 12, 14),
    'english-foxhound': (27.0, 34.0, 53, 64, 10, 13),
    'english-setter': (20.0, 36.0, 58, 69, 10, 12),
    'english-springer-spaniel': (18.0, 25.0, 46, 56, 12, 14),
    'english-toy-spaniel': (4.0, 6.0, 25, 28, 10, 12),
    'field-spaniel': (16.0, 23.0, 43, 46, 12, 14),
    'finnish-spitz': (9.0, 14.0, 38, 51, 12, 15),
    'flat-coated-retriever': (25.0, 36.0, 56, 61, 8, 10),
    'fox-terrier': (7.0, 9.0, 38, 40, 12, 15),
    'french-bulldog': (8.0, 14.0, 28, 33, 10, 12),
    'german-pinscher': (11.0, 20.0, 43, 51, 12, 14),
    'german-shepherd': (22.0, 40.0, 55, 65, 9, 13),
    'german-shorthaired-pointer': (20.0, 32.0, 53, 64, 12, 14),
    'german-wirehaired-pointer': (23.0, 32.0, 56, 68, 12, 14),
    'giant-schnauzer': (25.0, 48.0, 60, 70, 10, 12),
    'glen-of-imaal-terrier': (14.0, 17.0, 30, 36, 10, 15),
    'golden-retriever': (25.0, 34.0, 51, 61, 10, 12),
    'gordon-setter': (20.0, 36.0, 58, 69, 10, 12),
    'great-dane': (54.0, 90.0, 71, 86, 7, 10),
    'great-pyrenees': (39.0, 73.0, 65, 82, 10, 12),
    'greater-swiss-mountain-dog': (38.0, 64.0, 60, 72, 8, 11),
    'greyhound': (27.0, 32.0, 68, 76, 10, 14),
    'harrier': (20.0, 27.0, 46, 56, 12, 15),
    'havanese': (3.0, 6.0, 22, 29, 14, 16),
    'ibizan-hound': (20.0, 30.0, 56, 74, 11, 14),
    'irish-red-and-white-setter': (25.0, 34.0, 57, 66, 11, 15),
    'irish-setter': (24.0, 32.0, 64, 69, 12, 15),
    'irish-terrier': (11.0, 12.0, 43, 46, 13, 15),
    'irish-water-spaniel': (20.0, 30.0, 51, 61, 10, 12),
    'irish-wolfhound': (48.0, 54.0, 71, 90, 6, 8),
    'italian-greyhound': (3.0, 7.0, 33, 38, 12, 15),
    'jack-russell-terrier': (6.0, 8.0, 25, 38, 13, 16),
    'japanese-chin': (2.0, 7.0, 20, 28, 10, 12),
    'keeshond': (16.0, 20.0, 43, 46, 12, 15),
    'kerry-blue-terrier': (13.0, 18.0, 44, 51, 12, 15),
    'komondor': (36.0, 61.0, 64, 76, 10, 12),
    'kuvasz': (32.0, 52.0, 66, 76, 10, 12),
    'labrador-retriever': (25.0, 36.0, 53, 62, 10, 14),
    'lakeland-terrier': (7.0, 8.0, 33, 38, 12, 16),
    'leonberger': (41.0, 77.0, 65, 80, 7, 9),
    'lhasa-apso': (5.0, 8.0, 25, 28, 12, 15),
    'lowchen': (4.0, 8.0, 25, 36, 13, 15),
    'maltese': (2.0, 4.0, 18, 25, 12, 15),
    'manchester-terrier': (5.0, 10.0, 38, 41, 14, 16),
    'mastiff': (54.0, 91.0, 70, 91, 6, 10),
    'miniature-bull-terrier': (8.0, 14.0, 25, 36, 11, 14),
    'miniature-pinscher': (3.0, 5.0, 25, 32, 12, 16),
    'miniature-schnauzer': (5.0, 9.0, 30, 36, 12, 15),
    'neapolitan-mastiff': (50.0, 70.0, 60, 75, 7, 9),
    'newfoundland': (45.0, 68.0, 63, 74, 8, 10),
    'norfolk-terrier': (5.0, 5.5, 23, 25, 12, 16),
    'norwegian-elkhound': (20.0, 25.0, 48, 52, 12, 15),
    'norwich-terrier': (5.0, 5.5, 23, 26, 12, 15),
    'nova-scotia-duck-tolling-retriever': (17.0, 23.0, 43, 53, 12, 14),
    'old-english-sheepdog': (27.0, 45.0, 53, 61, 10, 12),
    'otterhound': (29.0, 52.0, 61, 69, 10, 13),
    'papillon': (3.0, 5.0, 20, 28, 13, 15),
    'parson-russell-terrier': (6.0, 9.0, 31, 38, 13, 15),
    'pekingese': (3.0, 6.0, 15, 23, 12, 14),
    'pembroke-welsh-corgi': (10.0, 14.0, 25, 30, 12, 15),
    'petit-basset-griffon-vendeen': (14.0, 18.0, 32, 40, 12, 14),
    'pharaoh-hound': (20.0, 25.0, 53, 64, 11, 14),
    'plott': (20.0, 27.0, 51, 64, 12, 14),
    'pointer': (20.0, 34.0, 53, 71, 12, 17),
    'polish-lowland-sheepdog': (14.0, 23.0, 42, 50, 12, 14),
    'pomeranian': (1.8, 3.5, 18, 30, 12, 16),
    'poodle': (2.0, 32.0, 25, 60, 12, 15),
    'portuguese-water-dog': (16.0, 27.0, 43, 57, 10, 14),
    'pug': (6.0, 9.0, 25, 36, 12, 15),
    'puli': (10.0, 15.0, 38, 44, 10, 15),
    'pyrenean-shepherd': (7.0, 14.0, 38, 48, 12, 15),
    'rat-terrier': (4.0, 11.0, 25, 46, 12, 18),
    'redbone-coonhound': (20.0, 32.0, 53, 69, 12, 14),
    'rhodesian-ridgeback': (29.0, 41.0, 61, 69, 10, 12),
    'rottweiler': (35.0, 60.0, 56, 69, 8, 10),
    'saint-bernard': (54.0, 82.0, 65, 90, 8, 10),
    'saluki': (18.0, 27.0, 58, 71, 12, 14),
    'samoyed': (16.0, 30.0, 48, 60, 12, 14),
    'schipperke': (3.0, 9.0, 25, 33, 13, 15),
    'scottish-deerhound': (34.0, 50.0, 71, 81, 8, 11),
    'scottish-terrier': (8.0, 10.0, 25, 28, 12, 15),
    'sealyham-terrier': (10.0, 11.0, 27, 31, 12, 14),
    'shetland-sheepdog': (6.0, 12.0, 33, 41, 12, 14),
    'shiba-inu': (8.0, 11.0, 33, 43, 12, 15),
    'shih-tzu': (4.0, 7.0, 20, 28, 10, 18),
    'siberian-husky': (16.0, 27.0, 50, 60, 12, 14),
    'silky-terrier': (3.5, 5.5, 23, 25, 12, 15),
    'skye-terrier': (11.0, 14.0, 23, 25, 12, 14),
    'smooth-fox-terrier': (7.0, 9.0, 38, 40, 12, 15),
    'soft-coated-wheaten-terrier': (14.0, 20.0, 43, 48, 12, 14),
    'spinone-italiano': (28.0, 39.0, 56, 70, 10, 12),
    'staffordshire-bull-terrier': (11.0, 17.0, 36, 41, 12, 14),
    'standard-schnauzer': (14.0, 20.0, 43, 51, 13, 16),
    'sussex-spaniel': (16.0, 20.0, 33, 38, 11, 13),
    'swedish-vallhund': (9.0, 14.0, 30, 35, 12, 15),
    'tibetan-mastiff': (34.0, 68.0, 61, 76, 10, 12),
    'tibetan-spaniel': (4.0, 7.0, 25, 25, 12, 15),
    'tibetan-terrier': (8.0, 14.0, 35, 41, 12, 15),
    'toy-fox-terrier': (1.5, 3.0, 22, 29, 13, 14),
    'vizsla': (18.0, 29.0, 53, 64, 12, 14),
    'weimaraner': (25.0, 40.0, 56, 69, 10, 13),
    'welsh-springer-spaniel': (16.0, 25.0, 43, 48, 12, 15),
    'welsh-terrier': (9.0, 10.0, 38, 39, 12, 15),
    'west-highland-white-terrier': (7.0, 10.0, 25, 28, 13, 15),
    'whippet': (6.8, 14.0, 44, 57, 12, 15),
    'wire-fox-terrier': (7.0, 9.0, 38, 40, 12, 15),
    'wirehaired-pointing-griffon': (20.0, 32.0, 51, 61, 12, 14),
    'xoloitzcuintli': (4.0, 25.0, 25, 58, 13, 18),
    'yorkshire-terrier': (2.0, 3.2, 17, 20, 13, 16),
}

def calculate_size_category(avg_weight):
    """Calculate size category from average weight"""
    if avg_weight < 5:
        return 'xs'
    elif avg_weight < 10:
        return 's'
    elif avg_weight < 25:
        return 'm'
    elif avg_weight < 45:
        return 'l'
    else:
        return 'xl'

def get_age_bounds_defaults(size_category):
    """Get default age bounds based on size category"""
    defaults = {
        'xs': {'growth_end': 8, 'senior_start': 10},
        's': {'growth_end': 10, 'senior_start': 10},
        'm': {'growth_end': 12, 'senior_start': 8},
        'l': {'growth_end': 15, 'senior_start': 7},
        'xl': {'growth_end': 18, 'senior_start': 6}
    }
    return defaults.get(size_category, {'growth_end': 12, 'senior_start': 8})

def enrich_breeds():
    """Main enrichment function"""
    
    print("=" * 80)
    print("BREEDS GRADE A+ ENRICHMENT")
    print("=" * 80)
    
    # Get all breeds
    response = supabase.table('breeds_details').select('*').execute()
    breeds_df = pd.DataFrame(response.data)
    total_breeds = len(breeds_df)
    
    print(f"Total breeds to process: {total_breeds}")
    
    # Track results
    enriched_count = 0
    conflicts = []
    
    # Process each breed
    for _, breed in breeds_df.iterrows():
        slug = breed['breed_slug']
        updates = {}
        provenance = {}
        
        # Calculate average weight if we have min/max
        if pd.notna(breed.get('weight_kg_min')) and pd.notna(breed.get('weight_kg_max')):
            avg_weight = (breed['weight_kg_min'] + breed['weight_kg_max']) / 2
            updates['adult_weight_avg_kg'] = round(avg_weight, 1)
            provenance['weight_from'] = 'calculated'
        elif slug in BREED_DATA:
            # Use our enrichment data
            min_w, max_w, min_h, max_h, min_l, max_l = BREED_DATA[slug]
            updates['weight_kg_min'] = min_w
            updates['weight_kg_max'] = max_w
            updates['adult_weight_avg_kg'] = round((min_w + max_w) / 2, 1)
            updates['height_cm_min'] = min_h
            updates['height_cm_max'] = max_h
            updates['lifespan_years_min'] = min_l
            updates['lifespan_years_max'] = max_l
            updates['lifespan_avg_years'] = round((min_l + max_l) / 2, 1)
            provenance['weight_from'] = 'enrichment'
            provenance['height_from'] = 'enrichment'
            provenance['lifespan_from'] = 'enrichment'
            avg_weight = updates['adult_weight_avg_kg']
        else:
            avg_weight = None
        
        # Calculate size category
        if avg_weight:
            updates['size_category'] = calculate_size_category(avg_weight)
            provenance['size_from'] = 'calculated'
            
            # Get age bounds
            age_bounds = get_age_bounds_defaults(updates['size_category'])
            updates['growth_end_months'] = age_bounds['growth_end']
            updates['senior_start_months'] = age_bounds['senior_start'] * 12  # Convert years to months
            provenance['age_bounds_from'] = 'default'
        
        # Calculate lifespan average if we have min/max
        if pd.notna(breed.get('lifespan_years_min')) and pd.notna(breed.get('lifespan_years_max')):
            if 'lifespan_avg_years' not in updates:
                updates['lifespan_avg_years'] = round((breed['lifespan_years_min'] + breed['lifespan_years_max']) / 2, 1)
                provenance['lifespan_from'] = 'calculated'
        
        # Apply updates
        if updates:
            try:
                # Add provenance fields
                for field, source in provenance.items():
                    updates[field] = source
                
                # Update breed
                supabase.table('breeds_details').update(updates).eq('breed_slug', slug).execute()
                enriched_count += 1
                
                if enriched_count % 50 == 0:
                    print(f"  Processed {enriched_count}/{total_breeds} breeds...")
            except Exception as e:
                print(f"  Error updating {slug}: {e}")
    
    print(f"\nEnrichment complete!")
    print(f"  Breeds enriched: {enriched_count}/{total_breeds}")
    
    return enriched_count, total_breeds

def validate_quality():
    """Validate final quality metrics"""
    
    print("\n" + "=" * 80)
    print("QUALITY VALIDATION")
    print("=" * 80)
    
    response = supabase.table('breeds_details').select('*').execute()
    df = pd.DataFrame(response.data)
    total = len(df)
    
    # Calculate coverage
    metrics = {
        'size_category': (~df['size_category'].isna()).sum() / total * 100,
        'growth_end_months': (~df['growth_end_months'].isna()).sum() / total * 100,
        'senior_start_months': (~df['senior_start_months'].isna()).sum() / total * 100,
        'adult_weight_avg_kg': (~df['adult_weight_avg_kg'].isna()).sum() / total * 100,
        'weight_kg_min': (~df['weight_kg_min'].isna()).sum() / total * 100,
        'weight_kg_max': (~df['weight_kg_max'].isna()).sum() / total * 100,
        'height_cm_min': (~df['height_cm_min'].isna()).sum() / total * 100,
        'height_cm_max': (~df['height_cm_max'].isna()).sum() / total * 100,
        'lifespan_years_min': (~df['lifespan_years_min'].isna()).sum() / total * 100,
        'lifespan_years_max': (~df['lifespan_years_max'].isna()).sum() / total * 100,
        'lifespan_avg_years': (~df['lifespan_avg_years'].isna()).sum() / total * 100,
    }
    
    print("\nField Coverage:")
    for field, coverage in metrics.items():
        status = "✅" if coverage >= 95 else "⚠️" if coverage >= 90 else "❌"
        print(f"  {status} {field:25s}: {coverage:5.1f}%")
    
    # Check for Grade A+ (98% operational fields)
    operational_coverage = np.mean([
        metrics['size_category'],
        metrics['growth_end_months'],
        metrics['senior_start_months'],
        metrics['adult_weight_avg_kg']
    ])
    
    print(f"\nOperational Fields Average: {operational_coverage:.1f}%")
    
    if operational_coverage >= 98:
        print("✅ GRADE A+ ACHIEVED!")
    elif operational_coverage >= 95:
        print("✅ Grade A achieved")
    elif operational_coverage >= 90:
        print("⚠️ Grade B - need more enrichment")
    else:
        print("❌ Below Grade B - significant enrichment needed")
    
    return metrics, operational_coverage

def generate_reports():
    """Generate quality reports"""
    
    metrics, score = validate_quality()
    
    # Create enrichment report
    report = f"""# Breeds Enrichment Report - Grade A+ Campaign

**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Target:** 98% coverage for operational fields

## Results Summary

**Overall Operational Coverage:** {score:.1f}%

## Field Coverage Details

| Field | Coverage | Status |
|-------|----------|--------|
"""
    
    for field, coverage in metrics.items():
        status = "✅ Passed" if coverage >= 95 else "⚠️ Warning" if coverage >= 90 else "❌ Failed"
        report += f"| {field} | {coverage:.1f}% | {status} |\n"
    
    report += f"""
## Grade Assessment

"""
    
    if score >= 98:
        report += "### ✅ GRADE A+ ACHIEVED!\n\nAll operational fields have 98%+ coverage."
    elif score >= 95:
        report += "### ✅ Grade A Achieved\n\nMost fields meet requirements, minor gaps remain."
    else:
        report += f"### ⚠️ Grade B\n\nNeed {98-score:.1f}% more coverage for Grade A+."
    
    # Save report
    with open('reports/BREEDS_ENRICHMENT_RUN.md', 'w') as f:
        f.write(report)
    
    print(f"\nReport saved to: reports/BREEDS_ENRICHMENT_RUN.md")
    
    return score

def main():
    # Run enrichment
    enriched, total = enrich_breeds()
    
    # Validate and report
    score = generate_reports()
    
    print("\n" + "=" * 80)
    print("ENRICHMENT COMPLETE")
    print("=" * 80)
    print(f"Final Score: {score:.1f}%")
    
    if score >= 98:
        print("🎉 Grade A+ Achieved!")
    else:
        print(f"Need {98-score:.1f}% more for Grade A+")

if __name__ == "__main__":
    main()