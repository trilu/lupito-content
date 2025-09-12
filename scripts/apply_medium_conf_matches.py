#!/usr/bin/env python3
"""
Apply medium-confidence AADF matches (≥0.5)
"""

import os
import re
import json
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_KEY')
)

def parse_ingredients(ingredients_text: str):
    """Parse ingredients into tokens"""
    if not ingredients_text:
        return []
    
    # Remove percentages
    text = re.sub(r'\([^)]*\)', '', ingredients_text)
    
    # Split and clean
    parts = []
    for part in re.split(r'[,;]', text):
        part = re.sub(r'[^\w\s-]', ' ', part).strip()
        if part and len(part) > 1:
            parts.append(part.lower())
    
    return parts[:50]  # Limit to 50 ingredients

def main():
    print("="*60)
    print("APPLYING MEDIUM-CONFIDENCE AADF MATCHES")
    print("="*60)
    
    # Load matches
    with open('data/aadf_new_matches_20250912_180309.json', 'r') as f:
        data = json.load(f)
    
    all_matches = data['new_matches']
    medium_conf = [m for m in all_matches if m['score'] >= 0.5]
    
    print(f"\nFound {len(medium_conf)} medium-confidence matches (≥0.5)")
    
    # Apply updates
    success = 0
    failed = 0
    
    for i, match in enumerate(medium_conf, 1):
        try:
            # Update product
            response = supabase.table('foods_canonical').update({
                'ingredients_raw': match['ingredients'],
                'ingredients_source': 'site',
                'ingredients_tokens': parse_ingredients(match['ingredients'])
            }).eq('product_key', match['product_key']).execute()
            
            print(f"  [{i}/{len(medium_conf)}] ✅ [{match['score']:.2f}] {match['brand']}: {match['name']}")
            success += 1
            
        except Exception as e:
            print(f"  [{i}/{len(medium_conf)}] ❌ Failed: {match['name']}")
            print(f"      Error: {e}")
            failed += 1
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total matches processed: {len(medium_conf)}")
    print(f"Successfully updated: {success}")
    print(f"Failed: {failed}")
    
    # Check new coverage
    total = supabase.table('foods_canonical').select('*', count='exact').execute()
    with_ingredients = supabase.table('foods_canonical').select('*', count='exact').not_.is_('ingredients_raw', 'null').execute()
    
    print(f"\nDatabase coverage:")
    print(f"  Total products: {total.count}")
    print(f"  Products with ingredients: {with_ingredients.count} ({with_ingredients.count/total.count*100:.1f}%)")
    
    print("\n✅ Medium-confidence matches applied!")

if __name__ == "__main__":
    main()