#!/usr/bin/env python3
"""
Comprehensive brand normalization analysis comparing foods_canonical against ALL-BRANDS.md benchmark.
This script performs deep analysis to find:
1. Brands that don't match the benchmark exactly
2. Product names that suggest different brands than assigned
3. Partial brand extractions
4. Case sensitivity issues
5. Special character handling issues
"""

import os
from supabase import create_client
from dotenv import load_dotenv
import pandas as pd
import re
from typing import Dict, List, Set, Tuple
from difflib import SequenceMatcher
import json

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def load_benchmark_brands():
    """Load canonical brands from ALL-BRANDS.md"""
    benchmark_brands = []
    
    with open('docs/ALL-BRANDS.md', 'r') as f:
        for line in f:
            brand = line.strip()
            if brand and not brand.startswith('#'):
                benchmark_brands.append(brand)
    
    return benchmark_brands

def load_database_data():
    """Load all products from foods_canonical with pagination"""
    print("Loading database products...")
    all_products = []
    limit = 1000
    offset = 0
    
    while True:
        response = supabase.table('foods_canonical').select('*').range(offset, offset + limit - 1).execute()
        batch = response.data
        if not batch:
            break
        all_products.extend(batch)
        offset += limit
        print(f"  Loaded {len(all_products)} products...", end='\r')
    
    print(f"  Loaded {len(all_products)} products total")
    return pd.DataFrame(all_products)

def find_similar_brand(brand: str, benchmark: List[str], threshold: float = 0.85) -> List[Tuple[str, float]]:
    """Find similar brands in benchmark using fuzzy matching"""
    matches = []
    brand_lower = brand.lower()
    
    for bench_brand in benchmark:
        # Exact match (case-insensitive)
        if brand_lower == bench_brand.lower():
            return [(bench_brand, 1.0)]
        
        # Calculate similarity
        ratio = SequenceMatcher(None, brand_lower, bench_brand.lower()).ratio()
        if ratio >= threshold:
            matches.append((bench_brand, ratio))
    
    return sorted(matches, key=lambda x: x[1], reverse=True)

def analyze_brand_in_product_name(product_name: str, benchmark: List[str]) -> List[str]:
    """Check if product name contains a different brand than assigned"""
    if not product_name:
        return []
    
    product_lower = product_name.lower()
    found_brands = []
    
    for bench_brand in benchmark:
        brand_lower = bench_brand.lower()
        # Check for brand at start of product name or with word boundaries
        if (product_lower.startswith(brand_lower + ' ') or 
            f' {brand_lower} ' in product_lower or
            product_lower.endswith(f' {brand_lower}')):
            found_brands.append(bench_brand)
    
    return found_brands

def analyze_normalization_gaps(df: pd.DataFrame, benchmark: List[str]):
    """Perform comprehensive analysis of brand normalization gaps"""
    
    print("\n" + "=" * 80)
    print("BRAND NORMALIZATION GAP ANALYSIS")
    print("=" * 80)
    
    # Create benchmark sets for faster lookup
    benchmark_set = set(benchmark)
    benchmark_lower = {b.lower(): b for b in benchmark}
    
    # Track issues
    issues = {
        'not_in_benchmark': [],
        'case_mismatch': [],
        'special_char_mismatch': [],
        'partial_extraction': [],
        'product_name_mismatch': [],
        'similar_to_benchmark': [],
        'suspicious_short': [],
        'null_brands': []
    }
    
    # Analyze each unique brand in database
    db_brands = df['brand'].dropna().unique()
    
    print(f"\n1. Analyzing {len(db_brands)} unique brands from database...")
    print("-" * 60)
    
    for db_brand in db_brands:
        product_count = len(df[df['brand'] == db_brand])
        
        # Check if brand is in benchmark
        if db_brand not in benchmark_set:
            # Check for case mismatch
            if db_brand.lower() in benchmark_lower:
                correct_brand = benchmark_lower[db_brand.lower()]
                issues['case_mismatch'].append({
                    'current': db_brand,
                    'correct': correct_brand,
                    'count': product_count
                })
            else:
                # Check for similar brands
                similar = find_similar_brand(db_brand, benchmark, threshold=0.8)
                if similar:
                    issues['similar_to_benchmark'].append({
                        'current': db_brand,
                        'similar': similar[0][0],
                        'similarity': similar[0][1],
                        'count': product_count
                    })
                else:
                    issues['not_in_benchmark'].append({
                        'brand': db_brand,
                        'count': product_count
                    })
        
        # Check for suspicious short brands (likely partial extractions)
        if len(db_brand) <= 4 and product_count > 5:
            issues['suspicious_short'].append({
                'brand': db_brand,
                'count': product_count
            })
        
        # Check for special character handling
        if any(char in db_brand for char in ["'", "&", "-", "."]):
            # Check if there's a version without special chars in benchmark
            normalized = db_brand.replace("'", "").replace("&", "and").replace("-", " ").replace(".", "")
            if normalized in benchmark_set and normalized != db_brand:
                issues['special_char_mismatch'].append({
                    'current': db_brand,
                    'suggested': normalized,
                    'count': product_count
                })
    
    # Analyze product names for brand mismatches
    print("\n2. Analyzing product names for brand consistency...")
    print("-" * 60)
    
    sample_size = min(len(df), 10000)  # Analyze sample for performance
    sample_df = df.sample(n=sample_size) if len(df) > sample_size else df
    
    for _, product in sample_df.iterrows():
        if pd.isna(product['brand']) or pd.isna(product['product_name']):
            if pd.isna(product['brand']):
                issues['null_brands'].append({
                    'product_key': product['product_key'],
                    'product_name': product.get('product_name', 'N/A')
                })
            continue
        
        # Check if product name contains a different benchmark brand
        brands_in_name = analyze_brand_in_product_name(product['product_name'], benchmark)
        
        # Remove the assigned brand from the list
        brands_in_name = [b for b in brands_in_name if b.lower() != product['brand'].lower()]
        
        if brands_in_name:
            # Check if it's a real mismatch
            if not any(product['brand'].lower() in b.lower() or b.lower() in product['brand'].lower() 
                      for b in brands_in_name):
                issues['product_name_mismatch'].append({
                    'product_key': product['product_key'],
                    'assigned_brand': product['brand'],
                    'brands_in_name': brands_in_name,
                    'product_name': product['product_name'][:60]
                })
    
    # Check for partial brand extractions
    print("\n3. Checking for partial brand extractions...")
    print("-" * 60)
    
    partial_patterns = [
        ('Hill\'s', ['Hill\'s Science Plan', 'Hill\'s Prescription Diet']),
        ('Nature\'s', ['Nature\'s Menu', 'Nature\'s Harvest', 'Nature\'s Variety', 'Nature\'s Way']),
        ('Natural', ['Natural Dog Food Company', 'Natural Greatness', 'Natural Instinct']),
        ('Wolf', ['Wolf Of Wilderness', 'Wolf Tucker']),
        ('Pet', ['Pets at Home', 'Pets Love Fresh']),
        ('Pro', ['Pro Plan', 'Prodog Raw']),
        ('Royal', ['Royal Canin']),
        ('The', ['The Pack', 'The Natural Pet Company'])
    ]
    
    for partial, full_brands in partial_patterns:
        if partial in db_brands:
            count = len(df[df['brand'] == partial])
            if count > 0:
                # Check product names to determine correct full brand
                partial_products = df[df['brand'] == partial]
                suggested_mapping = {}
                
                for _, prod in partial_products.iterrows():
                    prod_name = (prod.get('product_name') or '').lower()
                    for full_brand in full_brands:
                        if full_brand.lower() in prod_name:
                            suggested_mapping[full_brand] = suggested_mapping.get(full_brand, 0) + 1
                
                if suggested_mapping:
                    best_match = max(suggested_mapping.items(), key=lambda x: x[1])
                    issues['partial_extraction'].append({
                        'current': partial,
                        'suggested': best_match[0],
                        'confidence': best_match[1] / count,
                        'count': count
                    })
    
    return issues, db_brands

def generate_report(issues: Dict, db_brands, benchmark: List[str]):
    """Generate comprehensive report of findings"""
    
    print("\n" + "=" * 80)
    print("NORMALIZATION GAP REPORT")
    print("=" * 80)
    
    # Summary statistics
    benchmark_set = set(benchmark)
    db_brands_set = set(db_brands)
    
    print("\n📊 SUMMARY STATISTICS:")
    print("-" * 60)
    print(f"Benchmark brands (ALL-BRANDS.md): {len(benchmark)}")
    print(f"Database unique brands: {len(db_brands)}")
    print(f"Brands in DB matching benchmark: {len(db_brands_set & benchmark_set)}")
    print(f"Brands in DB not in benchmark: {len(db_brands_set - benchmark_set)}")
    print(f"Benchmark brands missing from DB: {len(benchmark_set - db_brands_set)}")
    
    # Critical issues
    total_issues = sum(len(v) for v in issues.values())
    
    if total_issues == 0:
        print("\n✅ NO NORMALIZATION ISSUES FOUND!")
        return
    
    print(f"\n⚠️ TOTAL ISSUES FOUND: {total_issues}")
    
    # Report each issue type
    if issues['not_in_benchmark']:
        print("\n🔴 BRANDS NOT IN BENCHMARK ({} found):".format(len(issues['not_in_benchmark'])))
        print("-" * 60)
        sorted_issues = sorted(issues['not_in_benchmark'], key=lambda x: x['count'], reverse=True)
        for issue in sorted_issues[:15]:
            print(f"  '{issue['brand']}': {issue['count']} products")
        if len(sorted_issues) > 15:
            print(f"  ... and {len(sorted_issues) - 15} more")
    
    if issues['case_mismatch']:
        print("\n🟡 CASE MISMATCHES ({} found):".format(len(issues['case_mismatch'])))
        print("-" * 60)
        for issue in sorted(issues['case_mismatch'], key=lambda x: x['count'], reverse=True)[:10]:
            print(f"  '{issue['current']}' → '{issue['correct']}' ({issue['count']} products)")
    
    if issues['partial_extraction']:
        print("\n🟠 PARTIAL BRAND EXTRACTIONS ({} found):".format(len(issues['partial_extraction'])))
        print("-" * 60)
        for issue in issues['partial_extraction']:
            confidence_pct = issue['confidence'] * 100
            print(f"  '{issue['current']}' → '{issue['suggested']}' ({issue['count']} products, {confidence_pct:.0f}% confidence)")
    
    if issues['similar_to_benchmark']:
        print("\n🟡 SIMILAR TO BENCHMARK ({} found):".format(len(issues['similar_to_benchmark'])))
        print("-" * 60)
        for issue in sorted(issues['similar_to_benchmark'], key=lambda x: x['similarity'], reverse=True)[:10]:
            similarity_pct = issue['similarity'] * 100
            print(f"  '{issue['current']}' ≈ '{issue['similar']}' ({similarity_pct:.0f}% similar, {issue['count']} products)")
    
    if issues['product_name_mismatch']:
        print("\n🔴 PRODUCT NAME/BRAND MISMATCHES ({} found):".format(len(issues['product_name_mismatch'])))
        print("-" * 60)
        for issue in issues['product_name_mismatch'][:10]:
            print(f"  Product: {issue['product_name']}")
            print(f"    Assigned: '{issue['assigned_brand']}' | In name: {issue['brands_in_name']}")
        if len(issues['product_name_mismatch']) > 10:
            print(f"  ... and {len(issues['product_name_mismatch']) - 10} more")
    
    if issues['suspicious_short']:
        print("\n⚠️ SUSPICIOUS SHORT BRANDS ({} found):".format(len(issues['suspicious_short'])))
        print("-" * 60)
        for issue in sorted(issues['suspicious_short'], key=lambda x: x['count'], reverse=True):
            print(f"  '{issue['brand']}': {issue['count']} products")
    
    # Generate action plan
    print("\n" + "=" * 80)
    print("RECOMMENDED ACTION PLAN")
    print("=" * 80)
    
    actions = []
    
    if issues['case_mismatch']:
        total_products = sum(i['count'] for i in issues['case_mismatch'])
        actions.append(f"1. Fix case mismatches: {len(issues['case_mismatch'])} brands, {total_products} products")
    
    if issues['partial_extraction']:
        total_products = sum(i['count'] for i in issues['partial_extraction'])
        actions.append(f"2. Fix partial extractions: {len(issues['partial_extraction'])} brands, {total_products} products")
    
    if issues['similar_to_benchmark']:
        high_confidence = [i for i in issues['similar_to_benchmark'] if i['similarity'] >= 0.9]
        if high_confidence:
            total_products = sum(i['count'] for i in high_confidence)
            actions.append(f"3. Fix high-confidence similar brands: {len(high_confidence)} brands, {total_products} products")
    
    if issues['product_name_mismatch']:
        actions.append(f"4. Review product/brand mismatches: {len(issues['product_name_mismatch'])} products")
    
    if issues['not_in_benchmark']:
        high_volume = [i for i in issues['not_in_benchmark'] if i['count'] >= 10]
        if high_volume:
            actions.append(f"5. Review high-volume non-benchmark brands: {len(high_volume)} brands")
    
    if actions:
        print("\nRecommended actions in priority order:")
        for action in actions:
            print(f"  {action}")
    else:
        print("\n✅ No critical actions required!")
    
    # Save detailed report
    report_data = {
        'summary': {
            'benchmark_brands': len(benchmark),
            'database_brands': len(db_brands),
            'matching_brands': len(db_brands_set & benchmark_set),
            'total_issues': total_issues
        },
        'issues': {k: v for k, v in issues.items() if v}
    }
    
    with open('reports/brand_normalization_gaps.json', 'w') as f:
        json.dump(report_data, f, indent=2)
    
    print(f"\n💾 Detailed report saved to: reports/brand_normalization_gaps.json")
    
    return issues

def main():
    # Load benchmark
    print("Loading benchmark brands from ALL-BRANDS.md...")
    benchmark = load_benchmark_brands()
    print(f"Loaded {len(benchmark)} benchmark brands")
    
    # Load database
    df = load_database_data()
    
    # Analyze gaps
    issues, db_brands = analyze_normalization_gaps(df, benchmark)
    
    # Generate report
    generate_report(issues, db_brands, benchmark)
    
    # Check if we should generate fix script
    total_fixable = (len(issues.get('case_mismatch', [])) + 
                    len(issues.get('partial_extraction', [])) +
                    len([i for i in issues.get('similar_to_benchmark', []) if i['similarity'] >= 0.95]))
    
    if total_fixable > 0:
        print(f"\n🔧 Found {total_fixable} automatically fixable issues")
        print("Run 'python fix_remaining_brand_issues.py' to apply fixes")

if __name__ == "__main__":
    main()