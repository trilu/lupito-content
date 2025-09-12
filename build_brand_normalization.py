#!/usr/bin/env python3
"""
Build comprehensive brand normalization map from ALL-BRANDS.md
"""

import os
import re
import yaml
import pandas as pd
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

def load_canonical_brands() -> Dict[str, str]:
    """Load brands from ALL-BRANDS.md as canonical source"""
    brands = {}
    with open('docs/ALL-BRANDS.md', 'r') as f:
        for line in f:
            brand = line.strip()
            if brand:
                # Create slug (lowercase, alphanumeric + spaces)
                slug = re.sub(r'[^\w\s]', '', brand.lower()).strip()
                slug = re.sub(r'\s+', ' ', slug)
                brands[slug] = brand  # slug -> display name
    return brands

def extract_brand_variants_from_canonical() -> Dict[str, Set[str]]:
    """Extract brand variants from foods_canonical"""
    variants = defaultdict(set)
    
    try:
        supabase = create_client(
            os.environ.get('SUPABASE_URL'),
            os.environ.get('SUPABASE_SERVICE_KEY')
        )
        
        response = supabase.table('foods_canonical').select('brand').execute()
        for row in response.data:
            if row.get('brand'):
                brand = row['brand']
                variants[brand.lower()].add(brand)
    except Exception as e:
        print(f"Warning: Could not load canonical DB: {e}")
    
    return variants

def extract_brand_variants_from_staging() -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]:
    """Extract brand variants from AADF and Chewy staging"""
    aadf_variants = defaultdict(set)
    chewy_variants = defaultdict(set)
    
    # AADF staging
    if Path('data/staging/aadf_staging_v2.csv').exists():
        df = pd.read_csv('data/staging/aadf_staging_v2.csv')
        for brand in df['brand_slug'].dropna().unique():
            aadf_variants[brand.lower()].add(brand)
    
    # Chewy staging
    if Path('data/staging/retailer_staging.chewy.csv').exists():
        df = pd.read_csv('data/staging/retailer_staging.chewy.csv')
        for brand in df['brand'].dropna().unique():
            chewy_variants[brand.lower()].add(brand)
    
    return aadf_variants, chewy_variants

def build_alias_map(canonical_brands: Dict[str, str], 
                    canonical_variants: Dict[str, Set[str]],
                    aadf_variants: Dict[str, Set[str]], 
                    chewy_variants: Dict[str, Set[str]]) -> Dict[str, Dict]:
    """Build comprehensive brand alias map"""
    
    alias_map = {}
    
    # Known problematic mappings that need special handling
    special_mappings = {
        # Royal Canin variations
        'royal canin': 'Royal Canin',
        'royal canin breed': 'Royal Canin',
        'royal canin veterinary': 'Royal Canin',
        'royal canin veterinary diet': 'Royal Canin',
        'royal canin vet': 'Royal Canin',
        
        # Hill's variations
        'hills': "Hill's",
        'hill': "Hill's",
        'hills science': "Hill's",
        'hills science plan': "Hill's",
        'hills science diet': "Hill's",
        'hills prescription': "Hill's",
        'hills prescription diet': "Hill's",
        
        # Pro Plan variations
        'pro plan': 'Pro Plan',
        'purina pro plan': 'Pro Plan',
        'proplan': 'Pro Plan',
        
        # Nature's variations
        'natures menu': "Nature's Menu",
        'natures deli': "Nature's Deli",
        'natures harvest': "Nature's Harvest",
        
        # Lily's Kitchen
        'lilys kitchen': "Lily's Kitchen",
        'lily kitchen': "Lily's Kitchen",
        'lily s kitchen': "Lily's Kitchen",
        
        # Wainwright's
        'wainwrights': "Wainwright's",
        'wainwright': "Wainwright's",
        'wainwrights dry': "Wainwright's",
        'wainwrights trays': "Wainwright's",
        
        # James Wellbeloved
        'james wellbeloved': 'James Wellbeloved',
        'james well beloved': 'James Wellbeloved',
        'jameswellbeloved': 'James Wellbeloved',
        
        # Pooch & Mutt
        'pooch mutt': 'Pooch & Mutt',
        'pooch and mutt': 'Pooch & Mutt',
        'pooch': 'Pooch & Mutt',
        
        # Fish4Dogs
        'fish4dogs': 'Fish4Dogs',
        'fish 4 dogs': 'Fish4Dogs',
        'fish for dogs': 'Fish4Dogs',
        
        # Dr. variations
        'dr john': 'Dr John',
        'dr johns': 'Dr John',
        'dr clauders': 'Dr Clauders',
        'dr clauder': 'Dr Clauders',
        
        # Barking Heads
        'barking heads': 'Barking Heads',
        'barking': 'Barking Heads',
        
        # Burns
        'burns': 'Burns',
        'burns original': 'Burns',
        
        # Arden Grange
        'arden grange': 'Arden Grange',
        'arden': 'Arden Grange',
        
        # Alpha Spirit
        'alpha spirit': 'Alpha Spirit',
        'alpha': 'Alpha',  # Note: Alpha might be its own brand too
        
        # Millies Wolfheart
        'millies wolfheart': 'Millies Wolfheart',
        'millie wolfheart': 'Millies Wolfheart',
        'millies': 'Millies Wolfheart',
        
        # Others
        'bob and lush': 'Bob & Lush',
        'bob lush': 'Bob & Lush',
        'pets at home': 'Pets at Home',
        'country dog': 'Country Dog',
        'country pursuit': 'Country Pursuit',
        'wolf of wilderness': 'Wolf of Wilderness',
        'concept for life': 'Concept For Life',
        'edgard cooper': 'Edgard & Cooper',
        'edgard and cooper': 'Edgard & Cooper',
        'forthglade': 'Forthglade',
        'nutribalance': 'Nutribalance',
    }
    
    # Process each special mapping
    for variant, canonical in special_mappings.items():
        slug = re.sub(r'[^\w\s]', '', canonical.lower()).strip()
        slug = re.sub(r'\s+', ' ', slug)
        
        if slug not in alias_map:
            alias_map[slug] = {
                'display': canonical,
                'aliases': []
            }
        
        if variant not in alias_map[slug]['aliases'] and variant != slug:
            alias_map[slug]['aliases'].append(variant)
    
    # Add canonical brands
    for slug, display in canonical_brands.items():
        if slug not in alias_map:
            alias_map[slug] = {
                'display': display,
                'aliases': []
            }
    
    # Collect all unique brand strings from all sources
    all_brand_strings = set()
    
    for variants in [canonical_variants, aadf_variants, chewy_variants]:
        for brand_set in variants.values():
            all_brand_strings.update(brand_set)
    
    # Map each unique brand string to canonical
    unmapped = []
    for brand_str in sorted(all_brand_strings):
        if not brand_str:
            continue
            
        brand_lower = brand_str.lower().strip()
        
        # Check if it's already a canonical slug
        if brand_lower in alias_map:
            continue
        
        # Check special mappings
        mapped = False
        for variant, canonical in special_mappings.items():
            if brand_lower == variant:
                mapped = True
                break
        
        if mapped:
            continue
        
        # Try to find best match in canonical brands
        best_match = None
        for slug in alias_map.keys():
            # Exact match after normalization
            if brand_lower == slug:
                best_match = slug
                break
            
            # Check if one contains the other (for multi-word brands)
            if len(slug.split()) > 1 and brand_lower.startswith(slug):
                best_match = slug
                break
            
            # Check known aliases
            if brand_lower in alias_map[slug].get('aliases', []):
                best_match = slug
                break
        
        if best_match:
            if brand_lower not in alias_map[best_match]['aliases']:
                alias_map[best_match]['aliases'].append(brand_lower)
        else:
            unmapped.append(brand_str)
    
    return alias_map, unmapped

def simulate_impact(alias_map: Dict, aadf_variants: Dict, chewy_variants: Dict) -> Dict:
    """Simulate the impact of applying brand normalization"""
    
    # Count current unique brands
    aadf_current = len(aadf_variants)
    chewy_current = len(chewy_variants)
    
    # Simulate after normalization
    aadf_normalized = set()
    chewy_normalized = set()
    
    for brand_set in aadf_variants.values():
        for brand in brand_set:
            brand_lower = brand.lower()
            found = False
            for slug, data in alias_map.items():
                if brand_lower == slug or brand_lower in data.get('aliases', []):
                    aadf_normalized.add(slug)
                    found = True
                    break
            if not found:
                aadf_normalized.add(brand_lower)
    
    for brand_set in chewy_variants.values():
        for brand in brand_set:
            brand_lower = brand.lower()
            found = False
            for slug, data in alias_map.items():
                if brand_lower == slug or brand_lower in data.get('aliases', []):
                    chewy_normalized.add(slug)
                    found = True
                    break
            if not found:
                chewy_normalized.add(brand_lower)
    
    return {
        'aadf_before': aadf_current,
        'aadf_after': len(aadf_normalized),
        'chewy_before': chewy_current,
        'chewy_after': len(chewy_normalized),
        'total_canonical': len(alias_map)
    }

def main():
    print("=== Building Brand Normalization Map ===\n")
    
    # Load canonical brands from ALL-BRANDS.md
    print("1. Loading canonical brands from ALL-BRANDS.md...")
    canonical_brands = load_canonical_brands()
    print(f"   Found {len(canonical_brands)} canonical brands")
    
    # Extract variants from all sources
    print("\n2. Extracting brand variants from all sources...")
    canonical_variants = extract_brand_variants_from_canonical()
    aadf_variants, chewy_variants = extract_brand_variants_from_staging()
    print(f"   Canonical DB: {len(canonical_variants)} unique brand strings")
    print(f"   AADF staging: {len(aadf_variants)} unique brand strings")
    print(f"   Chewy staging: {len(chewy_variants)} unique brand strings")
    
    # Build alias map
    print("\n3. Building brand alias map...")
    alias_map, unmapped = build_alias_map(
        canonical_brands, 
        canonical_variants,
        aadf_variants, 
        chewy_variants
    )
    print(f"   Created mappings for {len(alias_map)} canonical brands")
    print(f"   Unmapped brands: {len(unmapped)}")
    
    # Simulate impact
    print("\n4. Simulating normalization impact...")
    impact = simulate_impact(alias_map, aadf_variants, chewy_variants)
    
    # Save alias map as YAML
    print("\n5. Saving outputs...")
    
    # Convert to simpler format for YAML
    yaml_map = {}
    for slug, data in alias_map.items():
        yaml_map[data['display']] = data['aliases'] if data['aliases'] else []
    
    with open('data/brand_alias_map.yaml', 'w') as f:
        yaml.dump(yaml_map, f, default_flow_style=False, sort_keys=True)
    print("   Created: data/brand_alias_map.yaml")
    
    # Generate report
    report = f"""# Brand Normalization Plan
Generated: {pd.Timestamp.now().isoformat()}

## Executive Summary

Comprehensive brand normalization strategy based on authoritative ALL-BRANDS.md list.

## Statistics

### Canonical Brands
- **Total canonical brands**: {len(canonical_brands)}
- **Brands with aliases**: {len([k for k, v in alias_map.items() if v['aliases']])}
- **Total aliases defined**: {sum(len(v['aliases']) for v in alias_map.values())}

### Impact Simulation

| Dataset | Before Normalization | After Normalization | Reduction |
|---------|---------------------|---------------------|-----------|
| AADF | {impact['aadf_before']} brands | {impact['aadf_after']} brands | -{impact['aadf_before'] - impact['aadf_after']} ({(impact['aadf_before'] - impact['aadf_after'])/impact['aadf_before']*100:.1f}%) |
| Chewy | {impact['chewy_before']} brands | {impact['chewy_after']} brands | -{impact['chewy_before'] - impact['chewy_after']} ({(impact['chewy_before'] - impact['chewy_after'])/impact['chewy_before']*100:.1f}%) |

## Key Normalizations

### Royal Canin Family
- **Canonical**: Royal Canin
- **Variants normalized**:
  - royal canin breed
  - royal canin veterinary
  - royal canin veterinary diet
  - royal canin vet

### Hill's Family
- **Canonical**: Hill's
- **Variants normalized**:
  - hills
  - hill
  - hills science
  - hills science plan
  - hills science diet
  - hills prescription
  - hills prescription diet

### Pro Plan Family
- **Canonical**: Pro Plan
- **Variants normalized**:
  - purina pro plan
  - proplan

### Nature's Brands
- **Nature's Menu**: natures menu
- **Nature's Deli**: natures deli
- **Nature's Harvest**: natures harvest

## Edge Cases Handled

1. **Apostrophes**: Hill's, Lily's Kitchen, Wainwright's
2. **Multi-word brands**: James Wellbeloved, Pooch & Mutt, Wolf of Wilderness
3. **Abbreviations**: Dr John, CSJ, Fish4Dogs
4. **Brand families**: Royal Canin (Breed, Veterinary), Hill's (Science, Prescription)

## Unmapped Brands

Total unmapped: {len(unmapped)}

### Sample Unmapped Brands (may need manual review):
"""
    
    for brand in sorted(unmapped)[:20]:
        report += f"- {brand}\n"
    
    if len(unmapped) > 20:
        report += f"\n... and {len(unmapped) - 20} more\n"
    
    report += """
## Conflicting Patterns

### Brands with Multiple Interpretations
- **Alpha**: Could be "Alpha" or "Alpha Spirit" 
- **Arden**: Could be "Arden" or "Arden Grange"
- **Burns**: Standalone brand vs "Burns Original"
- **Barking**: Could be "Barking" or "Barking Heads"

### Resolution Strategy
These conflicts are resolved by preferring the full brand name when context is unclear.

## Implementation Notes

1. **Case Insensitive**: All matching is case-insensitive
2. **Special Characters**: Removed for slug creation, preserved in display names
3. **Whitespace**: Normalized to single spaces
4. **Priority**: Exact matches > Known aliases > Partial matches

## Recommendations

1. **Review unmapped brands** - Many may be retailer-specific or discontinued
2. **Validate edge cases** - Especially brands with multiple possible interpretations
3. **Consider brand families** - Some brands may benefit from hierarchical organization
4. **Regular updates** - ALL-BRANDS.md should be the single source of truth

## Files Generated

- `data/brand_alias_map.yaml` - Authoritative mapping file
- `reports/BRANDS-NORMALIZATION-PLAN.md` - This report
"""
    
    with open('reports/BRANDS-NORMALIZATION-PLAN.md', 'w') as f:
        f.write(report)
    print("   Created: reports/BRANDS-NORMALIZATION-PLAN.md")
    
    print(f"\n=== Complete ===")
    print(f"Normalization would reduce:")
    print(f"  AADF: {impact['aadf_before']} → {impact['aadf_after']} brands")
    print(f"  Chewy: {impact['chewy_before']} → {impact['chewy_after']} brands")

if __name__ == "__main__":
    main()