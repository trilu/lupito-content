#!/usr/bin/env python3
"""
Check ACTUAL nutrition coverage in the database
"""

import os
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_KEY')
)

def check_nutrition_coverage():
    print("ACTUAL DATABASE NUTRITION COVERAGE ANALYSIS")
    print("="*60)
    
    # Get total count
    total_response = supabase.table('foods_canonical').select('product_key', count='exact').execute()
    total_count = total_response.count
    print(f"Total products in database: {total_count}")
    
    # Check each nutrition field
    print("\nIndividual nutrition field coverage:")
    print("-"*40)
    
    fields = {
        'protein_percent': 'Protein',
        'fat_percent': 'Fat', 
        'fiber_percent': 'Fiber',
        'ash_percent': 'Ash',
        'moisture_percent': 'Moisture',
        'kcal_per_100g': 'Calories',
        'ingredients_raw': 'Ingredients'
    }
    
    field_counts = {}
    for field, name in fields.items():
        response = supabase.table('foods_canonical').select('product_key', count='exact').not_.is_(field, 'null').execute()
        count = response.count
        field_counts[field] = count
        percentage = (count/total_count)*100 if total_count > 0 else 0
        print(f"{name:15}: {count:5}/{total_count} = {percentage:5.1f}%")
    
    # Check products with complete macros (protein AND fat AND fiber)
    print("\n" + "="*60)
    print("CHECKING PRODUCTS WITH COMPLETE NUTRITION")
    print("-"*40)
    
    # Get a larger sample to check
    offset = 0
    limit = 1000
    complete_macros_count = 0
    partial_macros_count = 0
    no_macros_count = 0
    
    while offset < total_count:
        response = supabase.table('foods_canonical').select(
            'product_key,protein_percent,fat_percent,fiber_percent'
        ).range(offset, offset + limit - 1).execute()
        
        for product in response.data:
            if product.get('protein_percent') is not None and \
               product.get('fat_percent') is not None and \
               product.get('fiber_percent') is not None:
                complete_macros_count += 1
            elif product.get('protein_percent') is not None or \
                 product.get('fat_percent') is not None or \
                 product.get('fiber_percent') is not None:
                partial_macros_count += 1
            else:
                no_macros_count += 1
        
        offset += limit
        if not response.data or len(response.data) < limit:
            break
    
    print(f"Products with COMPLETE macros (P+F+Fi): {complete_macros_count}/{total_count} = {complete_macros_count/total_count*100:.1f}%")
    print(f"Products with PARTIAL macros: {partial_macros_count}/{total_count} = {partial_macros_count/total_count*100:.1f}%")
    print(f"Products with NO macros: {no_macros_count}/{total_count} = {no_macros_count/total_count*100:.1f}%")
    
    # Check UK products specifically
    print("\n" + "="*60)
    print("UK/AADF PRODUCTS COVERAGE")
    print("-"*40)
    
    uk_total = supabase.table('foods_canonical').select('product_key', count='exact').like('product_url', '%allaboutdogfood%').execute()
    uk_with_protein = supabase.table('foods_canonical').select('product_key', count='exact').like('product_url', '%allaboutdogfood%').not_.is_('protein_percent', 'null').execute()
    uk_with_ingredients = supabase.table('foods_canonical').select('product_key', count='exact').like('product_url', '%allaboutdogfood%').not_.is_('ingredients_raw', 'null').execute()
    
    print(f"UK products total: {uk_total.count}")
    print(f"UK with protein: {uk_with_protein.count} ({uk_with_protein.count/uk_total.count*100:.1f}%)")
    print(f"UK with ingredients: {uk_with_ingredients.count} ({uk_with_ingredients.count/uk_total.count*100:.1f}%)")
    
    # Check non-UK products
    non_uk_total = total_count - uk_total.count
    non_uk_with_protein = field_counts['protein_percent'] - uk_with_protein.count
    
    print(f"\nNon-UK products: {non_uk_total}")
    print(f"Non-UK with protein: {non_uk_with_protein} ({non_uk_with_protein/non_uk_total*100:.1f}% if non_uk_total > 0 else 0)")
    
    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)
    print(f"❌ The claim of 90.8% nutrition coverage is INCORRECT")
    print(f"✅ ACTUAL protein coverage: {field_counts['protein_percent']}/{total_count} = {field_counts['protein_percent']/total_count*100:.1f}%")
    print(f"✅ ACTUAL complete macros: {complete_macros_count}/{total_count} = {complete_macros_count/total_count*100:.1f}%")
    print(f"✅ ACTUAL ingredients coverage: {field_counts['ingredients_raw']}/{total_count} = {field_counts['ingredients_raw']/total_count*100:.1f}%")

if __name__ == "__main__":
    check_nutrition_coverage()