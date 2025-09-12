#!/usr/bin/env python3
"""
Fix PetFoodExpert.com brand extraction issues.
Only applies high-confidence corrections (≥95% confidence).
Based on validated research documented in PETFOODEXPERT_BRAND_NORMALIZATION_PLAN.md
"""

import os
from supabase import create_client
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
import json
from typing import Dict, List, Tuple

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# High-confidence brand corrections with websites
VALIDATED_BRANDS = {
    'BETTY': {
        'correct': 'Betty & Butch',
        'website': 'https://www.bettyandbutch.co.uk/',
        'confidence': 1.0,
        'pattern': 'BUTCH'  # All products start with BUTCH
    },
    'Sausage': {
        'correct': 'Sausage Dog Sanctuary Food',
        'website': 'https://sausagedogsanctuaryfood.com/',
        'confidence': 1.0,
        'pattern': 'Dog'
    },
    'Bright': {
        'correct': 'Bright Eyes Bushy Tails',
        'website': 'https://brighteyes-bushytails.co.uk/',
        'confidence': 1.0,
        'pattern': 'Eyes'
    },
    'Bounce': {
        'correct': 'Bounce and Bella',
        'website': 'https://shop.bounceandbella.co.uk/',
        'confidence': 1.0,
        'pattern': 'Bella'
    },
    'Edgard': {
        'correct': 'Edgard & Cooper',
        'website': 'https://www.edgardcooper.com/',
        'confidence': 1.0,
        'pattern': 'Cooper'
    },
    'Growling': {
        'correct': 'Growling Tums',
        'website': 'https://growlingtums.co.uk/',
        'confidence': 1.0,
        'pattern': 'Tums'
    },
    'Dragonfly': {
        'correct': 'Dragonfly Products',
        'website': 'https://dragonflyproducts.co.uk/',
        'confidence': 1.0,
        'pattern': 'Products'
    },
    'Borders': {
        'correct': 'Borders Pet Foods',
        'website': None,  # Company House verified
        'confidence': 0.95,
        'pattern': 'Pet Foods'
    },
    'Harrier': {
        'correct': 'Harrier Pro Pet Foods',
        'website': 'https://www.harrierpropetfoods.co.uk/',
        'confidence': 1.0,
        'pattern': 'Pro'
    },
    'Wolf': {
        'correct': 'Wolf Of Wilderness',
        'website': None,  # Already in ALL-BRANDS.md
        'confidence': 1.0,
        'pattern': 'of Wilderness'
    }
}

# Context-dependent corrections
CONTEXT_DEPENDENT = {
    'Country': [
        {'pattern': 'Dog', 'correct': 'Country Dog', 'website': 'https://www.countrydogfood.co.uk/'},
        {'pattern': 'Pursuit', 'correct': 'Country Pursuit', 'website': 'https://countrypursuit.co.uk/'}
    ],
    'Natural': [
        {'pattern': 'Instinct', 'correct': 'Natural Instinct', 'confidence': 0.95}
    ],
    'Cotswold': [
        {'pattern': 'Raw', 'correct': 'Cotswold Raw', 'confidence': 0.95}
    ],
    'Jollyes': [
        {'pattern': 'K9 Optimum', 'correct': 'K9 Optimum', 'confidence': 0.95},
        {'pattern': 'Lifestage', 'correct': 'Jollyes Lifestage', 'confidence': 0.90}
    ]
}

def load_petfoodexpert_products():
    """Load all products from petfoodexpert.com"""
    print("Loading products from database...")
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
    
    df = pd.DataFrame(all_products)
    
    # Filter for petfoodexpert.com products
    petfood_products = df[df['product_url'].str.contains('petfoodexpert.com', na=False)]
    print(f"  Found {len(petfood_products)} products from petfoodexpert.com")
    
    return petfood_products

def validate_pattern(products_df: pd.DataFrame, brand: str, pattern: str) -> float:
    """Validate that products match expected pattern"""
    brand_products = products_df[products_df['brand'] == brand]
    if brand_products.empty:
        return 0.0
    
    matching = 0
    for _, product in brand_products.iterrows():
        if pattern.lower() in product['product_name'].lower():
            matching += 1
    
    return matching / len(brand_products)

def apply_simple_corrections(products_df: pd.DataFrame) -> List[Dict]:
    """Apply simple brand corrections with high confidence"""
    corrections = []
    
    print("\n" + "=" * 70)
    print("APPLYING HIGH-CONFIDENCE CORRECTIONS")
    print("=" * 70)
    
    for old_brand, correction_info in VALIDATED_BRANDS.items():
        if correction_info['confidence'] < 0.95:
            continue
        
        brand_products = products_df[products_df['brand'] == old_brand]
        
        if brand_products.empty:
            continue
        
        # Validate pattern if specified
        if 'pattern' in correction_info:
            pattern_match = validate_pattern(products_df, old_brand, correction_info['pattern'])
            if pattern_match < 0.8:
                print(f"⚠️  Skipping {old_brand}: Pattern match only {pattern_match:.1%}")
                continue
        
        new_brand = correction_info['correct']
        website = correction_info.get('website', '')
        
        print(f"\n{old_brand} → {new_brand}")
        print(f"  Products: {len(brand_products)}")
        print(f"  Website: {website or 'N/A'}")
        print(f"  Confidence: {correction_info['confidence']:.0%}")
        
        for _, product in brand_products.iterrows():
            corrections.append({
                'product_key': product['product_key'],
                'old_brand': old_brand,
                'new_brand': new_brand,
                'website': website,
                'confidence': correction_info['confidence'],
                'product_name': product['product_name']
            })
    
    return corrections

def apply_context_corrections(products_df: pd.DataFrame) -> List[Dict]:
    """Apply context-dependent corrections"""
    corrections = []
    
    print("\n" + "=" * 70)
    print("APPLYING CONTEXT-DEPENDENT CORRECTIONS")
    print("=" * 70)
    
    for brand, patterns in CONTEXT_DEPENDENT.items():
        brand_products = products_df[products_df['brand'] == brand]
        
        if brand_products.empty:
            continue
        
        print(f"\nAnalyzing {brand} brand ({len(brand_products)} products)...")
        
        for pattern_info in patterns:
            pattern = pattern_info['pattern']
            confidence = pattern_info.get('confidence', 0.95)
            
            if confidence < 0.95:
                continue
            
            # Find products matching this pattern
            matching_products = []
            for _, product in brand_products.iterrows():
                if pattern in product['product_name']:
                    matching_products.append(product)
            
            if matching_products:
                new_brand = pattern_info['correct']
                website = pattern_info.get('website', '')
                
                print(f"  {brand} + '{pattern}' → {new_brand} ({len(matching_products)} products)")
                
                for product in matching_products:
                    corrections.append({
                        'product_key': product['product_key'],
                        'old_brand': brand,
                        'new_brand': new_brand,
                        'website': website,
                        'confidence': confidence,
                        'product_name': product['product_name']
                    })
    
    return corrections

def update_database(corrections: List[Dict]):
    """Apply corrections to database"""
    
    if not corrections:
        print("\n✅ No corrections to apply!")
        return 0
    
    print("\n" + "=" * 70)
    print("UPDATING DATABASE")
    print("=" * 70)
    
    rollback_data = []
    success_count = 0
    error_count = 0
    
    # Group by brand change for efficiency
    brand_groups = {}
    for correction in corrections:
        key = f"{correction['old_brand']}|{correction['new_brand']}"
        if key not in brand_groups:
            brand_groups[key] = []
        brand_groups[key].append(correction)
    
    print(f"\nApplying {len(corrections)} corrections across {len(brand_groups)} brand changes...")
    
    for brand_change, items in brand_groups.items():
        old_brand, new_brand = brand_change.split('|')
        print(f"\n  {old_brand} → {new_brand} ({len(items)} products)")
        
        for item in items:
            old_key = item['product_key']
            new_slug = new_brand.lower().replace(' ', '-').replace("'", '').replace('&', 'and')
            
            # Reconstruct product key
            key_parts = old_key.split('|')
            if len(key_parts) >= 2:
                key_parts[0] = new_slug
                new_key = '|'.join(key_parts)
            else:
                new_key = old_key
            
            # Store rollback info
            rollback_data.append({
                'product_key': old_key,
                'old_brand': old_brand,
                'new_brand': new_brand,
                'old_product_key': old_key,
                'new_product_key': new_key,
                'website': item.get('website', ''),
                'confidence': item['confidence']
            })
            
            # Update product
            update_data = {
                'brand': new_brand,
                'brand_slug': new_slug,
                'product_key': new_key
            }
            
            try:
                result = supabase.table('foods_canonical').update(update_data).eq('product_key', old_key).execute()
                success_count += 1
            except Exception as e:
                print(f"    ⚠️ Error updating {old_key}: {e}")
                error_count += 1
    
    print(f"\n✅ Successfully updated {success_count} products")
    if error_count > 0:
        print(f"⚠️ Failed to update {error_count} products")
    
    # Save rollback data
    if rollback_data:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rollback_file = f'data/rollback/petfoodexpert_fixes_{timestamp}.json'
        os.makedirs('data/rollback', exist_ok=True)
        
        with open(rollback_file, 'w') as f:
            json.dump(rollback_data, f, indent=2)
        
        print(f"\n💾 Rollback data saved to: {rollback_file}")
    
    return success_count

def update_brand_aliases(corrections: List[Dict]):
    """Update brand_alias table with new mappings"""
    
    print("\n" + "=" * 70)
    print("UPDATING BRAND ALIASES")
    print("=" * 70)
    
    # Get unique brand mappings
    unique_mappings = {}
    for correction in corrections:
        old_brand = correction['old_brand'].lower().strip()
        new_brand = correction['new_brand']
        unique_mappings[old_brand] = new_brand
    
    added = 0
    for alias, canonical in unique_mappings.items():
        # Check if alias already exists
        check = supabase.table('brand_alias').select('*').eq('alias', alias).execute()
        
        if not check.data:
            result = supabase.table('brand_alias').insert({
                'alias': alias,
                'canonical_brand': canonical,
                'created_at': datetime.now().isoformat()
            }).execute()
            print(f"  Added: '{alias}' → '{canonical}'")
            added += 1
    
    print(f"\n✅ Added {added} new brand aliases")

def generate_report(corrections: List[Dict]):
    """Generate detailed report of corrections"""
    
    print("\n" + "=" * 70)
    print("CORRECTION SUMMARY REPORT")
    print("=" * 70)
    
    if not corrections:
        print("\nNo corrections applied.")
        return
    
    # Summary by brand
    brand_summary = {}
    for correction in corrections:
        key = f"{correction['old_brand']} → {correction['new_brand']}"
        if key not in brand_summary:
            brand_summary[key] = {
                'count': 0,
                'website': correction.get('website', ''),
                'confidence': correction['confidence']
            }
        brand_summary[key]['count'] += 1
    
    print("\nBrand Corrections Applied:")
    print("-" * 60)
    
    for brand_change, info in sorted(brand_summary.items(), key=lambda x: x[1]['count'], reverse=True):
        print(f"{brand_change}: {info['count']} products")
        if info['website']:
            print(f"  Website: {info['website']}")
        print(f"  Confidence: {info['confidence']:.0%}")
    
    print(f"\nTotal products corrected: {len(corrections)}")
    
    # Save detailed report
    report_file = f'reports/petfoodexpert_corrections_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    os.makedirs('reports', exist_ok=True)
    
    with open(report_file, 'w') as f:
        json.dump({
            'summary': brand_summary,
            'total_corrections': len(corrections),
            'timestamp': datetime.now().isoformat(),
            'corrections': corrections[:100]  # Sample of corrections
        }, f, indent=2)
    
    print(f"\n📊 Detailed report saved to: {report_file}")

def main():
    # Load products
    products_df = load_petfoodexpert_products()
    
    # Apply corrections
    all_corrections = []
    
    # Simple corrections
    simple_corrections = apply_simple_corrections(products_df)
    all_corrections.extend(simple_corrections)
    
    # Context-dependent corrections
    context_corrections = apply_context_corrections(products_df)
    all_corrections.extend(context_corrections)
    
    # Remove duplicates
    seen = set()
    unique_corrections = []
    for correction in all_corrections:
        key = correction['product_key']
        if key not in seen:
            seen.add(key)
            unique_corrections.append(correction)
    
    print(f"\n📋 Total unique corrections to apply: {len(unique_corrections)}")
    
    if unique_corrections:
        # Update brand aliases first
        update_brand_aliases(unique_corrections)
        
        # Apply database updates
        updated = update_database(unique_corrections)
        
        # Generate report
        generate_report(unique_corrections)
        
        print("\n" + "=" * 70)
        print("COMPLETION")
        print("=" * 70)
        print(f"\n✅ Successfully corrected {updated} products from petfoodexpert.com")
        print("\nNext steps:")
        print("1. Review remaining 'The' and 'Natural' brand products manually")
        print("2. Research and validate uncertain brands (Luvdogz, Websters, etc.)")
        print("3. Update ALL-BRANDS.md with validated new brands")
    else:
        print("\n✅ No corrections needed!")

if __name__ == "__main__":
    main()