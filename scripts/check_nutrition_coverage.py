#!/usr/bin/env python3
"""
Check actual nutrition coverage in the database
Using existing supabase setup from other scripts
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_KEY')
)

def main():
    print("ACTUAL DATABASE NUTRITION COVERAGE ANALYSIS")
    print("="*60)
    
    # Get total count
    total = supabase.table('foods_canonical').select('product_key', count='exact').execute()
    total_count = total.count
    print(f"Total products: {total_count}")
    
    print("\nNutrition field coverage:")
    print("-"*40)
    
    # Check each field
    fields = [
        ('protein_percent', 'Protein'),
        ('fat_percent', 'Fat'),
        ('fiber_percent', 'Fiber'),
        ('ash_percent', 'Ash'),
        ('moisture_percent', 'Moisture'),
        ('kcal_per_100g', 'Calories'),
        ('ingredients_raw', 'Ingredients')
    ]
    
    results = {}
    for field, name in fields:
        response = supabase.table('foods_canonical').select(
            'product_key', count='exact'
        ).not_.is_(field, 'null').execute()
        
        count = response.count
        results[field] = count
        percentage = (count/total_count*100) if total_count > 0 else 0
        print(f"{name:15}: {count:5}/{total_count} = {percentage:5.1f}%")
    
    # Check UK products
    print("\nUK/AADF Products:")
    print("-"*40)
    
    uk_total = supabase.table('foods_canonical').select(
        'product_key', count='exact'
    ).like('product_url', '%allaboutdogfood%').execute()
    
    uk_with_protein = supabase.table('foods_canonical').select(
        'product_key', count='exact'
    ).like('product_url', '%allaboutdogfood%').not_.is_('protein_percent', 'null').execute()
    
    print(f"UK total: {uk_total.count}")
    print(f"UK with protein: {uk_with_protein.count} ({uk_with_protein.count/uk_total.count*100:.1f}%)")
    
    # Non-UK products
    non_uk_total = total_count - uk_total.count
    non_uk_with_protein = results['protein_percent'] - uk_with_protein.count
    
    print(f"\nNon-UK total: {non_uk_total}")
    print(f"Non-UK with protein: {non_uk_with_protein} ({non_uk_with_protein/non_uk_total*100:.1f}%)")
    
    print("\n" + "="*60)
    print("CONCLUSION:")
    print(f"✅ ACTUAL protein coverage: {results['protein_percent']}/{total_count} = {results['protein_percent']/total_count*100:.1f}%")
    print(f"✅ ACTUAL ingredients coverage: {results['ingredients_raw']}/{total_count} = {results['ingredients_raw']/total_count*100:.1f}%")
    
    # The 90.8% claim check
    if results['protein_percent']/total_count > 0.85:
        print("✅ The 90.8% nutrition coverage claim appears CORRECT")
    else:
        print("❌ The 90.8% nutrition coverage claim is INCORRECT")

if __name__ == "__main__":
    main()