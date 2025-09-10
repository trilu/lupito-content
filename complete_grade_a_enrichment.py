#!/usr/bin/env python3
"""
Complete Grade A+ enrichment using existing weight data in database.
Fills in all calculated fields and defaults to achieve 98% coverage.
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

def calculate_size_category(avg_weight):
    """Calculate size category from average weight"""
    if pd.isna(avg_weight):
        return None
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

def size_from_height(height_cm):
    """Derive size from height as fallback"""
    if pd.isna(height_cm):
        return None
    if height_cm < 28:
        return 'xs'
    elif height_cm < 38:
        return 's'
    elif height_cm < 53:
        return 'm'
    elif height_cm < 63:
        return 'l'
    else:
        return 'xl'

def main():
    print("=" * 80)
    print("COMPLETE GRADE A+ ENRICHMENT")
    print("=" * 80)
    
    # Get all breeds
    response = supabase.table('breeds_details').select('*').execute()
    breeds_df = pd.DataFrame(response.data)
    total_breeds = len(breeds_df)
    
    print(f"Total breeds: {total_breeds}")
    
    # Track updates
    updated = 0
    missing_all = []
    
    for _, breed in breeds_df.iterrows():
        slug = breed['breed_slug']
        updates = {}
        provenance = {}
        
        # 1. Calculate weight average if we have min/max
        if pd.notna(breed.get('weight_kg_min')) and pd.notna(breed.get('weight_kg_max')):
            if pd.isna(breed.get('adult_weight_avg_kg')):
                avg_weight = (breed['weight_kg_min'] + breed['weight_kg_max']) / 2
                updates['adult_weight_avg_kg'] = round(avg_weight, 1)
                provenance['weight_from'] = 'calculated'
        else:
            avg_weight = None
        
        # Get existing average if calculated
        if 'adult_weight_avg_kg' in updates:
            avg_weight = updates['adult_weight_avg_kg']
        elif pd.notna(breed.get('adult_weight_avg_kg')):
            avg_weight = breed['adult_weight_avg_kg']
        
        # 2. Calculate size_category from weight
        if avg_weight and pd.isna(breed.get('size_category')):
            updates['size_category'] = calculate_size_category(avg_weight)
            provenance['size_from'] = 'weight'
        
        # 3. If no weight but have height, derive size from height
        if not avg_weight and pd.notna(breed.get('height_cm_max')):
            if pd.isna(breed.get('size_category')):
                size_cat = size_from_height(breed['height_cm_max'])
                if size_cat:
                    updates['size_category'] = size_cat
                    provenance['size_from'] = 'height'
        
        # 4. Get size (either from updates or existing)
        if 'size_category' in updates:
            size_cat = updates['size_category']
        else:
            size_cat = breed.get('size_category')
        
        # 5. Fallback: use old 'size' field mapping
        if not size_cat and pd.notna(breed.get('size')):
            size_mapping = {
                'tiny': 'xs',
                'small': 's', 
                'medium': 'm',
                'large': 'l',
                'giant': 'xl'
            }
            size_cat = size_mapping.get(breed['size'])
            if size_cat:
                updates['size_category'] = size_cat
                provenance['size_from'] = 'legacy'
        
        # 6. Add age bounds based on size category
        if size_cat:
            if pd.isna(breed.get('growth_end_months')):
                age_bounds = get_age_bounds_defaults(size_cat)
                updates['growth_end_months'] = age_bounds['growth_end']
                updates['senior_start_months'] = age_bounds['senior_start'] * 12
                provenance['age_bounds_from'] = 'default'
        
        # 7. Calculate lifespan average if we have min/max
        if pd.notna(breed.get('lifespan_years_min')) and pd.notna(breed.get('lifespan_years_max')):
            if pd.isna(breed.get('lifespan_avg_years')):
                avg_lifespan = (breed['lifespan_years_min'] + breed['lifespan_years_max']) / 2
                updates['lifespan_avg_years'] = round(avg_lifespan, 1)
                provenance['lifespan_from'] = 'calculated'
        
        # Apply updates if any
        if updates:
            try:
                # Add provenance fields
                for field, source in provenance.items():
                    updates[field] = source
                
                # Update breed
                supabase.table('breeds_details').update(updates).eq('breed_slug', slug).execute()
                updated += 1
                
                if updated % 50 == 0:
                    print(f"  Processed {updated} breeds...")
                    
            except Exception as e:
                print(f"  Error updating {slug}: {e}")
        
        # Track breeds with no data at all
        if not size_cat and pd.isna(breed.get('weight_kg_max')) and pd.isna(breed.get('height_cm_max')):
            missing_all.append(slug)
    
    print(f"\nEnrichment complete!")
    print(f"  Breeds updated: {updated}/{total_breeds}")
    print(f"  Breeds with no data: {len(missing_all)}")
    
    # Validate final quality
    print("\n" + "=" * 80)
    print("FINAL QUALITY ASSESSMENT")
    print("=" * 80)
    
    # Re-fetch to get updated data
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
        'lifespan_avg_years': (~df['lifespan_avg_years'].isna()).sum() / total * 100,
    }
    
    print("\nField Coverage:")
    for field, coverage in metrics.items():
        target = 100 if field in ['size_category', 'growth_end_months', 'senior_start_months'] else 95
        status = "✅" if coverage >= target else "⚠️" if coverage >= 90 else "❌"
        print(f"  {status} {field:25s}: {coverage:5.1f}%")
    
    # Check operational fields average
    operational_coverage = np.mean([
        metrics['size_category'],
        metrics['growth_end_months'],
        metrics['senior_start_months'],
        metrics['adult_weight_avg_kg']
    ])
    
    print(f"\n{'='*60}")
    print(f"Operational Fields Average: {operational_coverage:.1f}%")
    print(f"{'='*60}")
    
    if operational_coverage >= 98:
        print("🎉 GRADE A+ ACHIEVED!")
    elif operational_coverage >= 95:
        print("✅ Grade A achieved") 
    elif operational_coverage >= 90:
        print("✅ Grade A- achieved")
    else:
        print(f"⚠️ Need {98-operational_coverage:.1f}% more for Grade A+")
    
    # Save final report
    report = f"""# Grade A+ Enrichment Final Report

**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Total Breeds:** {total}
**Operational Coverage:** {operational_coverage:.1f}%

## Coverage by Field

| Field | Coverage | Target | Status |
|-------|----------|--------|--------|
"""
    
    for field, coverage in metrics.items():
        target = 100 if field in ['size_category', 'growth_end_months', 'senior_start_months'] else 95
        status = "✅" if coverage >= target else "⚠️" if coverage >= 90 else "❌"
        report += f"| {field} | {coverage:.1f}% | {target}% | {status} |\n"
    
    grade = "A+" if operational_coverage >= 98 else "A" if operational_coverage >= 95 else "B"
    report += f"\n## Final Grade: {grade}\n"
    
    with open('reports/BREEDS_QUALITY_AFTER.md', 'w') as f:
        f.write(report)
    
    print(f"\nFinal report saved to: reports/BREEDS_QUALITY_AFTER.md")
    
    return operational_coverage

if __name__ == "__main__":
    score = main()
    print(f"\nFinal Score: {score:.1f}%")