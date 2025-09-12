#!/usr/bin/env python3
"""
Improved AADF matching with better brand normalization
"""

import os
import pandas as pd
from supabase import create_client
from dotenv import load_dotenv
from difflib import SequenceMatcher
from typing import Dict, Tuple

load_dotenv()
supabase = create_client(os.environ.get('SUPABASE_URL'), os.environ.get('SUPABASE_SERVICE_KEY'))

def normalize_brand_for_matching(brand: str) -> str:
    """Normalize brand name for matching"""
    if not brand:
        return ""
    brand_lower = str(brand).lower().strip()
    
    # Remove common suffixes that cause mismatches
    suffixes_to_remove = [' breed', ' plan', ' diet', ' prescription', ' science', ' veterinary']
    for suffix in suffixes_to_remove:
        if brand_lower.endswith(suffix):
            brand_lower = brand_lower[:-len(suffix)].strip()
    
    # Handle apostrophes
    brand_lower = brand_lower.replace("'s", "s").replace("'", "")
    
    return brand_lower

def get_brand_variants(brand: str) -> list:
    """Get possible brand variants for matching"""
    variants = [brand]
    brand_lower = brand.lower()
    
    # Specific mappings
    mappings = {
        'royal canin': ['Royal Canin', 'Royal Canin Breed', 'ROYAL CANIN'],
        'hills science': ["Hill's Science Plan", "Hill's", 'Hills', "Hill's Science", "Hill's Prescription Diet"],
        'hills': ["Hill's Science Plan", "Hill's", 'Hills', "Hill's Prescription Diet"],
        'james wellbeloved': ['James Wellbeloved', 'James Well Beloved', 'JamesWellbeloved'],
        'natures menu': ["Nature's Menu", 'Natures Menu'],
        'natures deli': ["Nature's Deli", 'Natures Deli'],
        'millies wolfheart': ['Millies Wolfheart', "Millie's Wolfheart"],
        'barking heads': ['Barking Heads', 'Barking'],
        'alpha spirit': ['Alpha Spirit', 'Alpha'],
        'pooch mutt': ['Pooch & Mutt', 'Pooch', 'Pooch and Mutt'],
        'wainwrights': ['Wainwrights', 'Wainwright'],
        'fish4dogs': ['Fish4Dogs', 'Fish 4 Dogs', 'Fish'],
        'lilys kitchen': ["Lily's Kitchen", 'Lilys Kitchen', 'Lily'],
        'burns': ['Burns', 'Burns Original'],
        'arden grange': ['Arden Grange', 'Arden'],
        'concept for': ['Concept for Life', 'Concept For', 'Concept'],
        'pro plan': ['Pro Plan', 'Purina Pro Plan', 'ProPlan']
    }
    
    if brand_lower in mappings:
        variants.extend(mappings[brand_lower])
    
    # Also try without 's at the end
    if brand.endswith('s') and len(brand) > 3:
        variants.append(brand[:-1])
    
    return list(set(variants))

def calculate_similarity(str1, str2) -> float:
    """Calculate string similarity"""
    if not str1 or not str2:
        return 0.0
    # Convert to strings and handle various types
    str1 = str(str1) if str1 is not None else ""
    str2 = str(str2) if str2 is not None else ""
    if not str1 or not str2:
        return 0.0
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

def find_best_match(staged_brand: str, staged_product: str, canonical_df: pd.DataFrame) -> Tuple[float, Dict]:
    """Find best match in canonical data with improved brand matching"""
    best_score = 0
    best_match = None
    
    # Get brand variants
    brand_variants = get_brand_variants(staged_brand)
    
    # Normalize for comparison
    staged_brand_norm = normalize_brand_for_matching(staged_brand)
    
    # Find products with matching or similar brands
    potential_matches = []
    for _, row in canonical_df.iterrows():
        canonical_brand_norm = normalize_brand_for_matching(row['brand'])
        
        # Check exact match after normalization
        if canonical_brand_norm == staged_brand_norm:
            potential_matches.append(row)
        # Check if any variant matches
        elif row['brand'] in brand_variants:
            potential_matches.append(row)
        # Check if brands are very similar
        elif calculate_similarity(staged_brand_norm, canonical_brand_norm) >= 0.85:
            potential_matches.append(row)
    
    # Calculate product similarity for potential matches
    for match in potential_matches:
        product_score = calculate_similarity(
            staged_product,
            match.get('name_slug', '') or match.get('product_name', '')
        )
        
        # Boost score slightly if brand matches exactly
        if normalize_brand_for_matching(match['brand']) == staged_brand_norm:
            product_score = min(1.0, product_score * 1.1)
        
        if product_score > best_score:
            best_score = product_score
            best_match = match.to_dict() if hasattr(match, 'to_dict') else match
    
    return best_score, best_match

def main():
    print("=== Improved AADF Matching ===\n")
    
    # Load AADF staging data
    aadf_df = pd.read_csv('data/staging/aadf_staging_v2.csv')
    print(f"Loaded {len(aadf_df)} AADF products")
    
    # Load canonical data
    response = supabase.table('foods_canonical').select('brand, product_name, name_slug').execute()
    canonical_df = pd.DataFrame(response.data)
    print(f"Loaded {len(canonical_df)} canonical products\n")
    
    # Perform improved matching
    matches = []
    high_count = 0
    review_count = 0
    no_match_count = 0
    
    print("Processing matches...")
    for idx, staged in aadf_df.iterrows():
        if not staged['brand_slug'] or not staged['product_name_norm']:
            matches.append({'score': 0, 'category': 'no-match', 'canonical_match': None})
            no_match_count += 1
            continue
        
        score, match = find_best_match(
            staged['brand_slug'],
            staged['product_name_norm'],
            canonical_df
        )
        
        # Categorize
        if score >= 0.80:
            category = 'high'
            high_count += 1
        elif score >= 0.65:
            category = 'review'
            review_count += 1
        else:
            category = 'no-match'
            no_match_count += 1
        
        matches.append({
            'score': score,
            'category': category,
            'canonical_match': match
        })
        
        # Show progress
        if (idx + 1) % 100 == 0:
            print(f"  Processed {idx + 1}/{len(aadf_df)} products...")
    
    # Add match data to dataframe
    aadf_df['match_score_improved'] = [m['score'] for m in matches]
    aadf_df['match_category_improved'] = [m['category'] for m in matches]
    
    # Save results
    aadf_df.to_csv('data/staging/aadf_staging_v2_improved_matches.csv', index=False)
    
    print(f"\n=== Matching Results ===")
    print(f"High confidence (≥0.80): {high_count} ({high_count/len(aadf_df)*100:.1f}%)")
    print(f"Review needed (0.65-0.79): {review_count} ({review_count/len(aadf_df)*100:.1f}%)")
    print(f"No match (<0.65): {no_match_count} ({no_match_count/len(aadf_df)*100:.1f}%)")
    
    # Compare with original matching
    original_high = (aadf_df['match_category'] == 'high').sum() if 'match_category' in aadf_df else 0
    print(f"\nImprovement: {high_count - original_high} more high-confidence matches")
    
    # Show sample improvements
    print("\n=== Sample Improved Matches ===")
    improved = aadf_df[
        (aadf_df['match_category_improved'] == 'high') & 
        (aadf_df['match_category'] != 'high')
    ][['brand_slug', 'product_name_norm', 'match_score', 'match_score_improved']].head(10)
    
    if not improved.empty:
        print(improved.to_string(index=False))
    
    # Check specific brands
    print("\n=== Brand-Specific Improvements ===")
    for brand in ['Royal Canin', 'Hills Science', 'Wainwrights']:
        brand_data = aadf_df[aadf_df['brand_slug'] == brand]
        if not brand_data.empty:
            orig_matches = (brand_data['match_category'].isin(['high', 'review'])).sum() if 'match_category' in brand_data else 0
            new_matches = (brand_data['match_category_improved'].isin(['high', 'review'])).sum()
            print(f"{brand}: {orig_matches} → {new_matches} matches")

if __name__ == "__main__":
    main()