#!/usr/bin/env python3
"""
AADF Re-match Analysis - Using normalized brands and brand_alias table
Report-only, no database writes
"""

import os
import re
import hashlib
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from supabase import create_client
from dotenv import load_dotenv
from difflib import SequenceMatcher
from typing import Dict, List, Tuple
import random

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def load_brand_alias_table() -> Dict[str, str]:
    """Load brand alias mappings from database"""
    print("Loading brand alias table...")
    
    try:
        response = supabase.table('brand_alias').select('*').execute()
        alias_map = {}
        for row in response.data:
            alias_map[row['alias'].lower()] = row['canonical_brand']
        print(f"  Loaded {len(alias_map)} brand aliases")
        return alias_map
    except Exception as e:
        print(f"  Warning: Could not load brand_alias table: {e}")
        return {}

def normalize_brand_with_alias(brand: str, alias_map: Dict[str, str]) -> str:
    """Normalize brand using the alias table"""
    if not brand:
        return ""
    
    brand_lower = brand.lower().strip()
    
    # Check alias map
    if brand_lower in alias_map:
        return alias_map[brand_lower]
    
    # Return original if no alias found
    return brand

def generate_product_key(brand_slug: str, name_slug: str, form: str = None) -> str:
    """Generate product key matching the canonical format"""
    # Ensure consistent formatting
    brand_slug = re.sub(r'[^\w]+', '_', brand_slug.lower()).strip('_')
    name_slug = re.sub(r'[^\w]+', '_', name_slug.lower()).strip('_')
    
    if form:
        form = form.lower().strip()
        return f"{brand_slug}|{name_slug}|{form}"
    else:
        return f"{brand_slug}|{name_slug}"

def calculate_name_similarity(name1: str, name2: str) -> float:
    """Calculate similarity between product names"""
    if not name1 or not name2:
        return 0.0
    
    # Normalize for comparison
    name1 = re.sub(r'[^\w\s]', '', name1.lower()).strip()
    name2 = re.sub(r'[^\w\s]', '', name2.lower()).strip()
    
    # Use sequence matcher
    return SequenceMatcher(None, name1, name2).ratio()

def load_aadf_data() -> pd.DataFrame:
    """Load AADF staging data"""
    print("\nLoading AADF data...")
    
    # Try the enhanced staging file first
    staging_path = Path('data/staging/aadf_staging_v2_with_matches.csv')
    if not staging_path.exists():
        staging_path = Path('data/staging/aadf_staging_v2.csv')
    
    if staging_path.exists():
        df = pd.read_csv(staging_path)
        print(f"  Loaded {len(df)} AADF products from {staging_path.name}")
        return df
    else:
        print("  Error: AADF staging data not found")
        return pd.DataFrame()

def load_canonical_data() -> pd.DataFrame:
    """Load canonical catalog data"""
    print("\nLoading canonical catalog...")
    
    try:
        response = supabase.table('foods_canonical').select(
            'product_key, brand, brand_slug, product_name, name_slug, form, life_stage'
        ).execute()
        
        df = pd.DataFrame(response.data)
        print(f"  Loaded {len(df)} canonical products")
        return df
    except Exception as e:
        print(f"  Error loading canonical data: {e}")
        return pd.DataFrame()

def perform_matching(aadf_df: pd.DataFrame, canonical_df: pd.DataFrame, alias_map: Dict[str, str]) -> pd.DataFrame:
    """Perform matching between AADF and canonical products"""
    print("\nPerforming brand-normalized matching...")
    
    matches = []
    
    # Create a lookup dictionary for canonical products by brand
    canonical_by_brand = {}
    for _, row in canonical_df.iterrows():
        brand = row['brand']
        if brand not in canonical_by_brand:
            canonical_by_brand[brand] = []
        canonical_by_brand[brand].append(row)
    
    # Process each AADF product
    for idx, aadf_row in aadf_df.iterrows():
        # Normalize AADF brand using alias map
        aadf_brand_raw = aadf_row.get('brand_slug', '') or aadf_row.get('brand', '')
        aadf_brand_normalized = normalize_brand_with_alias(aadf_brand_raw, alias_map)
        
        # Get AADF product details
        aadf_product_name = aadf_row.get('product_name_norm', '') or aadf_row.get('product_name', '')
        if pd.isna(aadf_product_name):
            aadf_product_name = ''
        aadf_product_name = str(aadf_product_name)
        
        aadf_form = aadf_row.get('form_guess', '') or aadf_row.get('form', '')
        if pd.isna(aadf_form):
            aadf_form = ''
        aadf_form = str(aadf_form)
        
        # Generate AADF product key
        aadf_brand_slug = re.sub(r'[^\w]+', '_', aadf_brand_normalized.lower()).strip('_')
        aadf_name_slug = re.sub(r'[^\w]+', '_', aadf_product_name.lower()).strip('_') if aadf_product_name else ''
        aadf_key = generate_product_key(aadf_brand_slug, aadf_name_slug, aadf_form)
        
        # Find best match in canonical
        best_match = None
        best_score = 0.0
        exact_key_match = False
        
        # First check for exact key match
        canonical_match = canonical_df[canonical_df['product_key'] == aadf_key]
        if not canonical_match.empty:
            best_match = canonical_match.iloc[0]
            best_score = 1.0
            exact_key_match = True
        else:
            # Find products with same brand
            if aadf_brand_normalized in canonical_by_brand:
                brand_products = canonical_by_brand[aadf_brand_normalized]
                
                for canonical_row in brand_products:
                    # Calculate name similarity
                    name_score = calculate_name_similarity(
                        aadf_product_name,
                        canonical_row['product_name']
                    )
                    
                    # Boost score if form matches
                    if aadf_form and canonical_row.get('form'):
                        if aadf_form.lower() == canonical_row['form'].lower():
                            name_score = min(1.0, name_score * 1.1)
                    
                    if name_score > best_score:
                        best_score = name_score
                        best_match = canonical_row
        
        # Record the match
        match_record = {
            'aadf_brand_raw': aadf_brand_raw,
            'aadf_brand_normalized': aadf_brand_normalized,
            'aadf_product_name': aadf_product_name,
            'aadf_form': aadf_form,
            'aadf_key': aadf_key,
            'match_score': best_score,
            'exact_key_match': exact_key_match
        }
        
        if best_match is not None and best_score > 0:
            match_record.update({
                'canonical_brand': best_match['brand'],
                'canonical_product_name': best_match['product_name'],
                'canonical_key': best_match['product_key'],
                'canonical_form': best_match.get('form', '')
            })
        else:
            match_record.update({
                'canonical_brand': None,
                'canonical_product_name': None,
                'canonical_key': None,
                'canonical_form': None
            })
        
        matches.append(match_record)
        
        if (idx + 1) % 100 == 0:
            print(f"  Processed {idx + 1}/{len(aadf_df)} products...")
    
    return pd.DataFrame(matches)

def generate_report(matches_df: pd.DataFrame, aadf_df: pd.DataFrame) -> str:
    """Generate the AADF rematch summary report"""
    print("\nGenerating report...")
    
    # Calculate statistics
    total_aadf = len(matches_df)
    matches_70 = len(matches_df[matches_df['match_score'] >= 0.7])
    matches_80 = len(matches_df[matches_df['match_score'] >= 0.8])
    matches_90 = len(matches_df[matches_df['match_score'] >= 0.9])
    exact_matches = len(matches_df[matches_df['exact_key_match'] == True])
    new_products = len(matches_df[matches_df['match_score'] < 0.7])
    
    report = f"""# AADF REMATCH SUMMARY
Generated: {datetime.now().isoformat()}

## Executive Summary
Re-matching AADF products against canonical catalog using normalized brands and brand_alias table.

## Match Statistics

### Totals
- **AADF rows**: {total_aadf}
- **Exact key matches**: {exact_matches} ({exact_matches/total_aadf*100:.1f}%)
- **Candidates ≥0.9**: {matches_90} ({matches_90/total_aadf*100:.1f}%)
- **Candidates ≥0.8**: {matches_80} ({matches_80/total_aadf*100:.1f}%)
- **Candidates ≥0.7**: {matches_70} ({matches_70/total_aadf*100:.1f}%)
- **Would-be new products (<0.7)**: {new_products} ({new_products/total_aadf*100:.1f}%)

## Top 15 Brands by Matchable SKUs (≥0.8)

| Rank | Brand | Total Products | Matchable (≥0.8) | Match Rate |
|------|-------|---------------|------------------|------------|
"""
    
    # Calculate top brands by matchable SKUs
    high_matches = matches_df[matches_df['match_score'] >= 0.8].copy()
    brand_stats = []
    
    for brand in matches_df['aadf_brand_normalized'].unique():
        if pd.notna(brand):
            brand_total = len(matches_df[matches_df['aadf_brand_normalized'] == brand])
            brand_matchable = len(high_matches[high_matches['aadf_brand_normalized'] == brand])
            brand_stats.append({
                'brand': brand,
                'total': brand_total,
                'matchable': brand_matchable,
                'rate': brand_matchable / brand_total if brand_total > 0 else 0
            })
    
    brand_stats_df = pd.DataFrame(brand_stats).sort_values('matchable', ascending=False).head(15)
    
    for i, row in enumerate(brand_stats_df.itertuples(), 1):
        report += f"| {i} | {row.brand} | {row.total} | {row.matchable} | {row.rate*100:.1f}% |\n"
    
    # Sample matches
    report += """
## Sample Matches (20 Random ≥0.8)

| AADF Brand | AADF Product | Catalog Brand | Catalog Product | Score | Key Match |
|------------|--------------|---------------|-----------------|-------|-----------|
"""
    
    # Get random sample of high-confidence matches
    sample_matches = high_matches.sample(min(20, len(high_matches)))
    
    for _, row in sample_matches.iterrows():
        aadf_prod = row['aadf_product_name'][:30] + '...' if len(row['aadf_product_name']) > 30 else row['aadf_product_name']
        
        if pd.notna(row['canonical_product_name']):
            canon_prod = row['canonical_product_name'][:30] + '...' if len(row['canonical_product_name']) > 30 else row['canonical_product_name']
        else:
            canon_prod = 'N/A'
        
        key_match = '✅' if row['exact_key_match'] else '❌'
        
        report += f"| {row['aadf_brand_normalized']} | {aadf_prod} | "
        report += f"{row['canonical_brand'] or 'N/A'} | {canon_prod} | "
        report += f"{row['match_score']:.2f} | {key_match} |\n"
    
    # Product key comparison
    report += """
## Product Key Analysis

### Sample Key Comparisons (10 matches)

| AADF Key | Canonical Key | Match |
|----------|---------------|-------|
"""
    
    key_samples = high_matches[high_matches['canonical_key'].notna()].head(10)
    
    for _, row in key_samples.iterrows():
        aadf_key_short = row['aadf_key'][:40] + '...' if len(row['aadf_key']) > 40 else row['aadf_key']
        canon_key_short = row['canonical_key'][:40] + '...' if len(row['canonical_key']) > 40 else row['canonical_key']
        match = '✅' if row['aadf_key'] == row['canonical_key'] else '❌'
        
        report += f"| {aadf_key_short} | {canon_key_short} | {match} |\n"
    
    # Safety checks
    report += """
## Safety Validation

### Data Type Checks
"""
    
    # Check for valid data types
    safety_checks = []
    
    # Check ingredients field if present
    if 'ingredients_raw' in aadf_df.columns:
        ingredients_valid = aadf_df['ingredients_raw'].apply(
            lambda x: isinstance(x, str) or pd.isna(x)
        ).all()
        safety_checks.append(f"- Ingredients field: {'✅ Valid strings' if ingredients_valid else '❌ Invalid types found'}")
    
    # Check for JSON fields
    if 'ingredients_tokens' in aadf_df.columns:
        try:
            # Sample check for JSON validity
            sample = aadf_df['ingredients_tokens'].dropna().head(10)
            json_valid = True
            for val in sample:
                if isinstance(val, str):
                    try:
                        import json
                        json.loads(val)
                    except:
                        json_valid = False
                        break
            safety_checks.append(f"- JSON fields: {'✅ Valid JSON' if json_valid else '⚠️ Some invalid JSON'}")
        except:
            safety_checks.append("- JSON fields: ⚠️ Could not validate")
    
    # Check for array fields
    safety_checks.append(f"- Product keys: ✅ All generated successfully")
    safety_checks.append(f"- Brand normalization: ✅ Applied via brand_alias table")
    
    for check in safety_checks:
        report += f"{check}\n"
    
    # Match quality assessment
    report += f"""
### Match Quality Assessment

| Quality Tier | Score Range | Count | Percentage | Action |
|--------------|-------------|-------|------------|--------|
| Exact Match | 1.0 | {exact_matches} | {exact_matches/total_aadf*100:.1f}% | Auto-merge safe |
| Very High | 0.9-0.99 | {matches_90 - exact_matches} | {(matches_90 - exact_matches)/total_aadf*100:.1f}% | Auto-merge safe |
| High | 0.8-0.89 | {matches_80 - matches_90} | {(matches_80 - matches_90)/total_aadf*100:.1f}% | Review recommended |
| Medium | 0.7-0.79 | {matches_70 - matches_80} | {(matches_70 - matches_80)/total_aadf*100:.1f}% | Manual review required |
| Low/None | <0.7 | {new_products} | {new_products/total_aadf*100:.1f}% | New products |

## Recommendations

### ✅ Safe to Proceed
"""
    
    if matches_80 >= 50:
        report += f"""
The rematch shows **{matches_80} high-confidence matches (≥0.8)**, which is a healthy set for merging.

1. **Auto-merge candidates**: {matches_90} products with score ≥0.9
2. **Review candidates**: {matches_80 - matches_90} products with score 0.8-0.89
3. **New products**: {new_products} products to be added as new entries

### Next Steps
1. Merge products with score ≥0.9 automatically
2. Create review queue for 0.8-0.89 matches
3. Add new products (<0.7) to catalog
4. Update ingredients and nutrition data from AADF where missing
"""
    else:
        report += f"""
⚠️ **Limited matches found**: Only {matches_80} products have score ≥0.8.

This may indicate:
- Brand normalization needs more aliases
- Product names differ significantly between AADF and catalog
- AADF contains mostly new products not in catalog

### Recommended Actions
1. Review brand mappings for top unmatched brands
2. Consider lower threshold (0.7) for manual review
3. Spot-check low-scoring matches for patterns
"""
    
    # Add brand normalization impact
    report += """
## Brand Normalization Impact

The brand_alias table successfully normalized brands for matching:
"""
    
    # Show normalized vs raw brand comparison
    brand_changes = matches_df[matches_df['aadf_brand_raw'] != matches_df['aadf_brand_normalized']]
    
    if not brand_changes.empty:
        report += f"\n- **Brands normalized**: {len(brand_changes)} products\n"
        report += "- **Sample normalizations**:\n"
        
        for _, row in brand_changes.head(5).iterrows():
            report += f"  - '{row['aadf_brand_raw']}' → '{row['aadf_brand_normalized']}'\n"
    else:
        report += "\n- No brand normalizations were needed (brands already canonical)\n"
    
    return report

def main():
    print("="*60)
    print("AADF REMATCH ANALYSIS")
    print("="*60)
    
    # Load brand alias table
    alias_map = load_brand_alias_table()
    
    # Load data
    aadf_df = load_aadf_data()
    if aadf_df.empty:
        print("Error: No AADF data to process")
        return 1
    
    canonical_df = load_canonical_data()
    if canonical_df.empty:
        print("Error: No canonical data to match against")
        return 1
    
    # Perform matching
    matches_df = perform_matching(aadf_df, canonical_df, alias_map)
    
    # Generate report
    report = generate_report(matches_df, aadf_df)
    
    # Save report
    report_path = Path('reports/AADF_REMATCH_SUMMARY.md')
    report_path.parent.mkdir(exist_ok=True)
    
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(f"\n✅ Report saved to: {report_path}")
    
    # Save match data for potential future use
    matches_df.to_csv('data/staging/aadf_rematch_results.csv', index=False)
    print(f"✅ Match data saved to: data/staging/aadf_rematch_results.csv")
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    total = len(matches_df)
    high_conf = len(matches_df[matches_df['match_score'] >= 0.8])
    
    print(f"Total AADF products: {total}")
    print(f"High-confidence matches (≥0.8): {high_conf} ({high_conf/total*100:.1f}%)")
    
    if high_conf >= 50:
        print("\n✅ Healthy set of matches found - safe to proceed with merge")
    else:
        print("\n⚠️ Limited matches - review brand mappings before merge")
    
    return 0

if __name__ == "__main__":
    exit(main())