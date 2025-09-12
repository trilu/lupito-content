#!/usr/bin/env python3
"""
Clean product names by removing brand name prefixes.
Based on PRODUCT_NAME_CLEANUP_PLAN.md
"""

import os
from supabase import create_client
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
import json
import re
from typing import Dict, List, Tuple, Optional

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Define cleanup rules for each brand
CLEANUP_RULES = {
    # Recently fixed brands - 100% need cleanup
    'Betty & Butch': {
        'patterns': [{'match': '^BUTCH ', 'remove': 'BUTCH '}],
        'confidence': 1.0
    },
    'Sausage Dog Sanctuary Food': {
        'patterns': [{'match': '^Dog Sanctuary ', 'remove': 'Dog Sanctuary '}],
        'confidence': 1.0
    },
    'Bright Eyes Bushy Tails': {
        'patterns': [{'match': '^Eyes Bushy Tails ', 'remove': 'Eyes Bushy Tails '}],
        'confidence': 1.0
    },
    'Bounce and Bella': {
        'patterns': [{'match': '^Bella ', 'remove': 'Bella '}],
        'confidence': 1.0
    },
    'Borders Pet Foods': {
        'patterns': [{'match': '^Pet Foods ', 'remove': 'Pet Foods '}],
        'confidence': 1.0
    },
    'Harrier Pro Pet Foods': {
        'patterns': [{'match': '^Pro Pet Foods ', 'remove': 'Pro Pet Foods '}],
        'confidence': 1.0
    },
    'Growling Tums': {
        'patterns': [{'match': '^Tums ', 'remove': 'Tums '}],
        'confidence': 1.0
    },
    'Dragonfly Products': {
        'patterns': [{'match': '^Products ', 'remove': 'Products '}],
        'confidence': 1.0
    },
    'Edgard & Cooper': {
        'patterns': [
            {'match': '^Cooper ', 'remove': 'Cooper '},
            {'match': '^Edgard & Cooper ', 'remove': 'Edgard & Cooper '}
        ],
        'confidence': 1.0
    },
    'Natural Instinct': {
        'patterns': [{'match': '^Instinct ', 'remove': 'Instinct '}],
        'confidence': 1.0
    },
    'Cotswold Raw': {
        'patterns': [{'match': '^Raw ', 'remove': 'Raw '}],
        'confidence': 1.0
    },
    'Country Dog': {
        'patterns': [{'match': '^Dog ', 'remove': 'Dog '}],
        'confidence': 1.0
    },
    'Country Pursuit': {
        'patterns': [{'match': '^Pursuit ', 'remove': 'Pursuit '}],
        'confidence': 1.0
    },
    
    # Major brands with clear patterns
    'Royal Canin': {
        'patterns': [
            {'match': '^Royal Canin ', 'remove': 'Royal Canin '},
            {'match': '^Canin ', 'remove': 'Canin '}
        ],
        'confidence': 0.95
    },
    'Wolf Of Wilderness': {
        'patterns': [
            {'match': '^Wolf of Wilderness ', 'remove': 'Wolf of Wilderness ', 'case_insensitive': True},
            {'match': '^of Wilderness ', 'remove': 'of Wilderness '}
        ],
        'confidence': 0.95
    },
    'Happy Dog': {
        'patterns': [
            {'match': '^Dog ', 'remove': 'Dog ', 'conditional': ['NaturCroq', 'Fit', 'Supreme', 'Sensible']},
            {'match': '^Happy Dog ', 'remove': 'Happy Dog '}
        ],
        'confidence': 0.95
    },
    'James Wellbeloved': {
        'patterns': [
            {'match': '^Wellbeloved ', 'remove': 'Wellbeloved '},
            {'match': '^James Wellbeloved ', 'remove': 'James Wellbeloved '}
        ],
        'confidence': 0.95
    },
    "Lily's Kitchen": {
        'patterns': [
            {'match': '^Kitchen ', 'remove': 'Kitchen '},
            {'match': "^Lily's Kitchen ", 'remove': "Lily's Kitchen "}
        ],
        'confidence': 0.95
    },
    'Natures Menu': {
        'patterns': [{'match': '^Menu ', 'remove': 'Menu '}],
        'confidence': 0.95
    },
    'Arden Grange': {
        'patterns': [
            {'match': '^Arden Grange ', 'remove': 'Arden Grange '},
            {'match': '^Grange ', 'remove': 'Grange '}
        ],
        'confidence': 0.95
    },
    'Barking Heads': {
        'patterns': [{'match': '^Heads ', 'remove': 'Heads '}],
        'confidence': 0.95
    },
    'Millies Wolfheart': {
        'patterns': [{'match': '^Wolfheart ', 'remove': 'Wolfheart '}],
        'confidence': 0.95
    },
    'Pets at Home': {
        'patterns': [{'match': '^at Home ', 'remove': 'at Home '}],
        'confidence': 0.95
    },
    "Hill's Science Plan": {
        'patterns': [
            {'match': '^Science Plan ', 'remove': 'Science Plan '},
            {'match': "^Hill's Science Plan ", 'remove': "Hill's Science Plan "}
        ],
        'confidence': 0.95
    },
    "Hill's Prescription Diet": {
        'patterns': [
            {'match': "^Hill's Prescription Diet ", 'remove': "Hill's Prescription Diet "}
        ],
        'confidence': 0.95
    },
    'Eukanuba': {
        'patterns': [{'match': '^Eukanuba ', 'remove': 'Eukanuba '}],
        'confidence': 0.95
    },
    'Brit': {
        'patterns': [{'match': '^Brit ', 'remove': 'Brit '}],
        'confidence': 0.95
    },
    'Lukullus': {
        'patterns': [{'match': '^Lukullus ', 'remove': 'Lukullus '}],
        'confidence': 0.95
    },
    'Rocco': {
        'patterns': [{'match': '^Rocco ', 'remove': 'Rocco '}],
        'confidence': 0.95
    },
    'Purizon': {
        'patterns': [{'match': '^Purizon ', 'remove': 'Purizon '}],
        'confidence': 0.95
    },
    'Bosch': {
        'patterns': [{'match': '^bosch ', 'remove': 'bosch ', 'case_insensitive': True}],
        'confidence': 0.95
    },
    'Pro Plan': {
        'patterns': [{'match': '^Pro Plan ', 'remove': 'Pro Plan '}],
        'confidence': 0.95
    },
    'Bozita': {
        'patterns': [{'match': '^Bozita ', 'remove': 'Bozita '}],
        'confidence': 0.95
    },
    'Advance Veterinary Diets': {
        'patterns': [
            {'match': '^Advance ', 'remove': 'Advance '},
            {'match': '^Advance Veterinary Diets ', 'remove': 'Advance Veterinary Diets '}
        ],
        'confidence': 0.90
    },
    'Farmina N&D': {
        'patterns': [
            {'match': '^N&D ', 'remove': 'N&D '},
            {'match': '^Farmina ', 'remove': 'Farmina '},
            {'match': '^Farmina N&D ', 'remove': 'Farmina N&D '}
        ],
        'confidence': 0.90
    }
}

def load_all_products() -> pd.DataFrame:
    """Load all products from database"""
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
    print(f"  Loaded {len(df)} products")
    return df

def clean_product_name(product_name: str, brand: str, rules: Dict) -> Tuple[str, bool, str]:
    """
    Clean a single product name based on brand rules.
    Returns: (cleaned_name, was_changed, pattern_used)
    """
    if brand not in rules:
        return product_name, False, ""
    
    brand_rules = rules[brand]
    original_name = product_name
    
    for pattern in brand_rules.get('patterns', []):
        match_pattern = pattern['match']
        remove_text = pattern['remove']
        
        # Handle conditional patterns
        if 'conditional' in pattern:
            # Check if any conditional term is in the product name
            found_condition = False
            for term in pattern['conditional']:
                if term in product_name:
                    found_condition = True
                    break
            if not found_condition:
                continue
        
        # Handle case-insensitive matching
        if pattern.get('case_insensitive', False):
            if product_name.lower().startswith(remove_text.lower()):
                product_name = product_name[len(remove_text):]
                return product_name.strip(), True, f"Removed '{remove_text}' (case-insensitive)"
        else:
            # Check if pattern matches
            if match_pattern.startswith('^'):
                # Regex pattern
                if re.match(match_pattern, product_name):
                    product_name = re.sub(match_pattern, '', product_name)
                    return product_name.strip(), True, f"Removed '{remove_text}'"
            elif product_name.startswith(remove_text):
                product_name = product_name[len(remove_text):]
                return product_name.strip(), True, f"Removed '{remove_text}'"
    
    return original_name, False, ""

def process_products(df: pd.DataFrame, rules: Dict, confidence_threshold: float = 0.95) -> List[Dict]:
    """Process all products and return list of changes"""
    changes = []
    
    print("\n" + "=" * 70)
    print("PROCESSING PRODUCTS")
    print("=" * 70)
    
    # Group by brand for efficiency
    for brand in df['brand'].dropna().unique():
        if brand not in rules:
            continue
        
        # Check confidence threshold
        if rules[brand].get('confidence', 0) < confidence_threshold:
            continue
        
        brand_products = df[df['brand'] == brand]
        brand_changes = []
        
        for _, product in brand_products.iterrows():
            original_name = product['product_name']
            if pd.isna(original_name):
                continue
            
            cleaned_name, was_changed, pattern_used = clean_product_name(original_name, brand, rules)
            
            if was_changed:
                brand_changes.append({
                    'product_key': product['product_key'],
                    'brand': brand,
                    'original_name': original_name,
                    'cleaned_name': cleaned_name,
                    'pattern': pattern_used
                })
        
        if brand_changes:
            print(f"\n{brand}: {len(brand_changes)} products to clean")
            # Show samples
            for change in brand_changes[:3]:
                print(f"  '{change['original_name'][:40]}' → '{change['cleaned_name'][:40]}'")
            changes.extend(brand_changes)
    
    return changes

def validate_changes(changes: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """Validate proposed changes and separate into safe and review needed"""
    safe_changes = []
    review_needed = []
    
    for change in changes:
        cleaned = change['cleaned_name']
        
        # Validation rules
        if len(cleaned) < 3:
            review_needed.append({**change, 'issue': 'Name too short'})
        elif cleaned.count(' ') < 1 and len(cleaned) < 10:
            review_needed.append({**change, 'issue': 'Single word name'})
        elif cleaned.startswith(' ') or cleaned.endswith(' '):
            review_needed.append({**change, 'issue': 'Leading/trailing space'})
        else:
            safe_changes.append(change)
    
    return safe_changes, review_needed

def update_database(changes: List[Dict]) -> int:
    """Apply changes to database"""
    
    if not changes:
        print("\n✅ No changes to apply!")
        return 0
    
    print("\n" + "=" * 70)
    print("UPDATING DATABASE")
    print("=" * 70)
    
    print(f"\nApplying {len(changes)} product name cleanups...")
    
    rollback_data = []
    success_count = 0
    error_count = 0
    
    # Process in batches
    batch_size = 50
    for i in range(0, len(changes), batch_size):
        batch = changes[i:i+batch_size]
        
        for change in batch:
            old_key = change['product_key']
            new_name = change['cleaned_name']
            
            # Store rollback info
            rollback_data.append({
                'product_key': old_key,
                'original_name': change['original_name'],
                'cleaned_name': new_name,
                'brand': change['brand'],
                'pattern': change['pattern']
            })
            
            # Update product
            update_data = {'product_name': new_name}
            
            try:
                result = supabase.table('foods_canonical').update(update_data).eq('product_key', old_key).execute()
                success_count += 1
            except Exception as e:
                print(f"  ⚠️ Error updating {old_key}: {e}")
                error_count += 1
        
        print(f"  Progress: {min(i+batch_size, len(changes))}/{len(changes)} processed...")
    
    print(f"\n✅ Successfully cleaned {success_count} product names")
    if error_count > 0:
        print(f"⚠️ Failed to update {error_count} products")
    
    # Save rollback data
    if rollback_data:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rollback_file = f'data/rollback/product_name_cleanup_{timestamp}.json'
        os.makedirs('data/rollback', exist_ok=True)
        
        with open(rollback_file, 'w') as f:
            json.dump(rollback_data, f, indent=2)
        
        print(f"\n💾 Rollback data saved to: {rollback_file}")
    
    return success_count

def generate_report(changes: List[Dict], review_needed: List[Dict]):
    """Generate detailed report of changes"""
    
    print("\n" + "=" * 70)
    print("CLEANUP SUMMARY REPORT")
    print("=" * 70)
    
    # Group by brand
    brand_summary = {}
    for change in changes:
        brand = change['brand']
        if brand not in brand_summary:
            brand_summary[brand] = []
        brand_summary[brand].append(change)
    
    print(f"\nTotal products cleaned: {len(changes)}")
    print(f"Products needing review: {len(review_needed)}")
    print(f"Brands affected: {len(brand_summary)}")
    
    print("\nTop brands by cleanup count:")
    print("-" * 60)
    
    sorted_brands = sorted(brand_summary.items(), key=lambda x: len(x[1]), reverse=True)
    for brand, brand_changes in sorted_brands[:15]:
        print(f"{brand}: {len(brand_changes)} products")
    
    # Save detailed report
    report_file = f'reports/product_name_cleanup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    os.makedirs('reports', exist_ok=True)
    
    report_data = {
        'summary': {
            'total_cleaned': len(changes),
            'needs_review': len(review_needed),
            'brands_affected': len(brand_summary)
        },
        'by_brand': {brand: len(items) for brand, items in brand_summary.items()},
        'sample_changes': changes[:50],
        'review_needed': review_needed,
        'timestamp': datetime.now().isoformat()
    }
    
    with open(report_file, 'w') as f:
        json.dump(report_data, f, indent=2)
    
    print(f"\n📊 Detailed report saved to: {report_file}")

def main():
    # Load products
    df = load_all_products()
    
    # Process products with high confidence rules
    print("\nPhase 1: Processing high-confidence patterns (≥95% confidence)...")
    all_changes = process_products(df, CLEANUP_RULES, confidence_threshold=0.95)
    
    # Validate changes
    safe_changes, review_needed = validate_changes(all_changes)
    
    print(f"\n📋 Validation results:")
    print(f"  Safe to apply: {len(safe_changes)}")
    print(f"  Need review: {len(review_needed)}")
    
    if review_needed:
        print("\nProducts needing review:")
        for item in review_needed[:5]:
            print(f"  {item['brand']}: '{item['original_name'][:30]}' - {item['issue']}")
    
    if safe_changes:
        print("\n" + "=" * 70)
        print(f"Ready to clean {len(safe_changes)} product names")
        print("=" * 70)
        
        # Apply changes
        updated = update_database(safe_changes)
        
        # Generate report
        generate_report(safe_changes, review_needed)
        
        print("\n" + "=" * 70)
        print("COMPLETION")
        print("=" * 70)
        print(f"\n✅ Successfully cleaned {updated} product names")
        
        # Next steps
        if review_needed:
            print(f"\n⚠️ {len(review_needed)} products need manual review")
        
        print("\nNext steps:")
        print("1. Review the cleanup report")
        print("2. Process medium-confidence patterns if needed")
        print("3. Handle edge cases manually")
    else:
        print("\n✅ No product names need cleaning!")

if __name__ == "__main__":
    main()