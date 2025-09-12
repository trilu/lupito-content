#!/usr/bin/env python3
"""
Improved brand mapping with better variant detection
"""

import os
import re
import yaml
import pandas as pd
from pathlib import Path
from typing import Dict, List, Set
from collections import defaultdict
from supabase import create_client
from dotenv import load_dotenv
from difflib import SequenceMatcher

load_dotenv()

def normalize_brand_name(brand: str) -> str:
    """Normalize brand name for comparison"""
    if not brand:
        return ""
    # Lower case, remove special chars except spaces
    normalized = re.sub(r'[^\w\s]', '', brand.lower()).strip()
    # Collapse multiple spaces
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized

def load_all_brands() -> Dict[str, str]:
    """Load ALL-BRANDS.md as canonical reference"""
    canonical = {}
    with open('docs/ALL-BRANDS.md', 'r') as f:
        for line in f:
            brand = line.strip()
            if brand:
                canonical[normalize_brand_name(brand)] = brand
    return canonical

def collect_all_brand_variants() -> Dict[str, Set[str]]:
    """Collect all brand strings from all sources"""
    variants = defaultdict(set)
    
    # From canonical DB
    try:
        supabase = create_client(
            os.environ.get('SUPABASE_URL'),
            os.environ.get('SUPABASE_SERVICE_KEY')
        )
        response = supabase.table('foods_canonical').select('brand').execute()
        for row in response.data:
            if row.get('brand'):
                brand = row['brand']
                normalized = normalize_brand_name(brand)
                variants[normalized].add(brand)
    except Exception as e:
        print(f"Warning: Could not load canonical DB: {e}")
    
    # From AADF staging
    if Path('data/staging/aadf_staging_v2.csv').exists():
        df = pd.read_csv('data/staging/aadf_staging_v2.csv')
        for brand in df['brand_slug'].dropna().unique():
            normalized = normalize_brand_name(brand)
            variants[normalized].add(brand)
    
    # From Chewy staging
    if Path('data/staging/retailer_staging.chewy.csv').exists():
        df = pd.read_csv('data/staging/retailer_staging.chewy.csv')
        for brand in df['brand'].dropna().unique():
            normalized = normalize_brand_name(brand)
            variants[normalized].add(brand)
    
    return variants

def find_best_canonical_match(brand_norm: str, canonical: Dict[str, str]) -> tuple[str, float]:
    """Find best matching canonical brand"""
    
    # Exact match
    if brand_norm in canonical:
        return canonical[brand_norm], 1.0
    
    # Known mappings
    mappings = {
        'royal canin breed': 'royal canin',
        'royal canin veterinary': 'royal canin',
        'royal canin veterinary diet': 'royal canin',
        'royal canin vet': 'royal canin',
        'hills science': 'hills',
        'hills science plan': 'hills',
        'hills science diet': 'hills',
        'hills prescription': 'hills',
        'hills prescription diet': 'hills',
        'purina pro plan': 'pro plan',
        'proplan': 'pro plan',
        'natures menu': 'natures menu',
        'natures deli': 'natures deli',
        'lilys kitchen': 'lilys kitchen',
        'lily s kitchen': 'lilys kitchen',
        'wainwrights dry': 'wainwrights',
        'wainwrights trays': 'wainwrights',
        'wainwright': 'wainwrights',
        'james well beloved': 'james wellbeloved',
        'pooch mutt': 'pooch mutt',
        'pooch and mutt': 'pooch mutt',
        'pooch': 'pooch mutt',
        'fish 4 dogs': 'fish4dogs',
        'fish for dogs': 'fish4dogs',
        'dr johns': 'dr john',
        'dr clauder': 'dr clauders',
        'barking': 'barking heads',
        'burns original': 'burns',
        'arden': 'arden grange',
        'millies': 'millies wolfheart',
        'millie wolfheart': 'millies wolfheart',
        'bob lush': 'bob lush',
        'bob and lush': 'bob lush',
        'pets at home': 'pets at home',
        'wolf of': 'wolf of wilderness',
        'concept for': 'concept for life',
        'edgard cooper': 'edgard cooper',
        'edgard and cooper': 'edgard cooper',
        'csj': 'csj',
        'lifestage': 'lifestage',
        'hills': 'hills',
        'hill': 'hills',
        'skinners': 'skinners',
        'feelwells': 'feelwells',
        'edmondson': 'edmondson',
        'edmondsons': 'edmondson',
        'honeys': 'honeys',
        'josidog': 'josidog',
        'josera': 'josera',
        'langhams': 'langhams',
        'michies': 'michies',
        'mypetsays': 'mypetsays',
        'poppys': 'poppys',
        'rosies': 'rosies',
        'sainsburys': 'sainsburys',
        'skippers': 'skippers',
        'bentleys': 'bentleys',
    }
    
    # Check mapping
    if brand_norm in mappings:
        mapped = mappings[brand_norm]
        if mapped in canonical:
            return canonical[mapped], 0.95
    
    # Try substring matching for multi-word brands
    best_score = 0
    best_match = None
    
    for canon_norm, canon_display in canonical.items():
        # Calculate similarity
        score = SequenceMatcher(None, brand_norm, canon_norm).ratio()
        
        # Boost score if one contains the other
        if brand_norm in canon_norm or canon_norm in brand_norm:
            score = max(score, 0.85)
        
        # Check word overlap for multi-word brands
        brand_words = set(brand_norm.split())
        canon_words = set(canon_norm.split())
        if len(brand_words) > 1 and len(canon_words) > 1:
            overlap = len(brand_words.intersection(canon_words))
            if overlap >= min(len(brand_words), len(canon_words)) - 1:
                score = max(score, 0.80)
        
        if score > best_score:
            best_score = score
            best_match = canon_display
    
    return best_match, best_score

def build_comprehensive_mapping():
    """Build comprehensive brand mapping"""
    
    print("Loading canonical brands...")
    canonical = load_all_brands()
    print(f"  {len(canonical)} canonical brands loaded")
    
    print("\nCollecting brand variants...")
    all_variants = collect_all_brand_variants()
    print(f"  {len(all_variants)} unique normalized brand strings found")
    
    print("\nBuilding mappings...")
    
    # Build the mapping
    brand_map = {}
    unmapped = []
    stats = {
        'exact': 0,
        'high_confidence': 0,
        'medium_confidence': 0,
        'low_confidence': 0,
        'unmapped': 0
    }
    
    for brand_norm, variant_set in all_variants.items():
        if not brand_norm:
            continue
        
        # Find best canonical match
        best_match, score = find_best_canonical_match(brand_norm, canonical)
        
        if score >= 0.95:
            stats['exact'] += 1
            category = 'exact'
        elif score >= 0.85:
            stats['high_confidence'] += 1
            category = 'high'
        elif score >= 0.70:
            stats['medium_confidence'] += 1
            category = 'medium'
        elif best_match:
            stats['low_confidence'] += 1
            category = 'low'
        else:
            stats['unmapped'] += 1
            unmapped.append((brand_norm, variant_set))
            continue
        
        # Add to map
        canon_norm = normalize_brand_name(best_match)
        if best_match not in brand_map:
            brand_map[best_match] = {
                'canonical': best_match,
                'aliases': [],
                'confidence_levels': {}
            }
        
        # Add all variants as aliases
        for variant in variant_set:
            variant_norm = normalize_brand_name(variant)
            if variant_norm != canon_norm and variant not in brand_map[best_match]['aliases']:
                brand_map[best_match]['aliases'].append(variant)
                brand_map[best_match]['confidence_levels'][variant] = category
    
    return brand_map, unmapped, stats

def simulate_impact(brand_map: Dict) -> Dict:
    """Simulate impact of normalization"""
    
    results = {}
    
    # Check AADF impact
    if Path('data/staging/aadf_staging_v2.csv').exists():
        df = pd.read_csv('data/staging/aadf_staging_v2.csv')
        original_brands = df['brand_slug'].dropna().unique()
        
        normalized_brands = set()
        for brand in original_brands:
            found = False
            for canonical, data in brand_map.items():
                if brand == canonical or brand in data['aliases']:
                    normalized_brands.add(canonical)
                    found = True
                    break
            if not found:
                normalized_brands.add(brand)
        
        results['aadf'] = {
            'before': len(original_brands),
            'after': len(normalized_brands),
            'reduction': len(original_brands) - len(normalized_brands)
        }
    
    # Check Chewy impact
    if Path('data/staging/retailer_staging.chewy.csv').exists():
        df = pd.read_csv('data/staging/retailer_staging.chewy.csv')
        original_brands = df['brand'].dropna().unique()
        
        normalized_brands = set()
        for brand in original_brands:
            found = False
            for canonical, data in brand_map.items():
                if brand == canonical or brand in data['aliases']:
                    normalized_brands.add(canonical)
                    found = True
                    break
            if not found:
                normalized_brands.add(brand)
        
        results['chewy'] = {
            'before': len(original_brands),
            'after': len(normalized_brands),
            'reduction': len(original_brands) - len(normalized_brands)
        }
    
    return results

def main():
    print("=== Building Comprehensive Brand Mapping ===\n")
    
    brand_map, unmapped, stats = build_comprehensive_mapping()
    
    print(f"\nMapping Statistics:")
    print(f"  Exact matches: {stats['exact']}")
    print(f"  High confidence: {stats['high_confidence']}")
    print(f"  Medium confidence: {stats['medium_confidence']}")
    print(f"  Low confidence: {stats['low_confidence']}")
    print(f"  Unmapped: {stats['unmapped']}")
    
    # Simulate impact
    impact = simulate_impact(brand_map)
    
    # Save simplified YAML
    yaml_map = {}
    for canonical, data in brand_map.items():
        yaml_map[canonical] = data['aliases']
    
    with open('data/brand_alias_map_v2.yaml', 'w') as f:
        yaml.dump(yaml_map, f, default_flow_style=False, sort_keys=True, allow_unicode=True)
    
    print(f"\nFiles created:")
    print(f"  data/brand_alias_map_v2.yaml")
    
    # Show impact
    print(f"\nNormalization Impact:")
    if 'aadf' in impact:
        print(f"  AADF: {impact['aadf']['before']} → {impact['aadf']['after']} brands (-{impact['aadf']['reduction']})")
    if 'chewy' in impact:
        print(f"  Chewy: {impact['chewy']['before']} → {impact['chewy']['after']} brands (-{impact['chewy']['reduction']})")
    
    # Show some interesting mappings
    print(f"\nSample High-Impact Mappings:")
    for canonical, data in sorted(brand_map.items(), key=lambda x: len(x[1]['aliases']), reverse=True)[:10]:
        if data['aliases']:
            print(f"  {canonical}: {len(data['aliases'])} aliases")
            for alias in data['aliases'][:3]:
                print(f"    - {alias}")
            if len(data['aliases']) > 3:
                print(f"    ... and {len(data['aliases']) - 3} more")

if __name__ == "__main__":
    main()