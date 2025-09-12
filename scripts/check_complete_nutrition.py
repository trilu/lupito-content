#!/usr/bin/env python3
"""
Check what products have COMPLETE nutrition vs partial
"""

import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_KEY')
)

def main():
    print("COMPLETE VS PARTIAL NUTRITION ANALYSIS")
    print("="*60)
    
    # Get all products with their nutrition fields
    all_products = []
    offset = 0
    limit = 1000
    
    while True:
        response = supabase.table('foods_canonical').select(
            'product_key,protein_percent,fat_percent,fiber_percent,ash_percent,moisture_percent,kcal_per_100g'
        ).range(offset, offset + limit - 1).execute()
        
        if not response.data:
            break
        
        all_products.extend(response.data)
        offset += limit
        
        if len(response.data) < limit:
            break
    
    total = len(all_products)
    print(f"Total products analyzed: {total}")
    
    # Categorize products
    complete_basic = 0  # Has protein + fat
    complete_standard = 0  # Has protein + fat + fiber
    complete_full = 0  # Has all 5 macros
    has_calories = 0
    has_any_nutrition = 0
    no_nutrition = 0
    
    for product in all_products:
        has_protein = product.get('protein_percent') is not None
        has_fat = product.get('fat_percent') is not None
        has_fiber = product.get('fiber_percent') is not None
        has_ash = product.get('ash_percent') is not None
        has_moisture = product.get('moisture_percent') is not None
        has_kcal = product.get('kcal_per_100g') is not None
        
        if has_kcal:
            has_calories += 1
        
        if has_protein and has_fat:
            complete_basic += 1
            
            if has_fiber:
                complete_standard += 1
                
                if has_ash and has_moisture:
                    complete_full += 1
        
        if has_protein or has_fat or has_fiber or has_ash or has_moisture:
            has_any_nutrition += 1
        else:
            no_nutrition += 1
    
    print("\nNutrition Completeness Levels:")
    print("-"*40)
    print(f"Complete BASIC (P+F):       {complete_basic:5}/{total} = {complete_basic/total*100:5.1f}%")
    print(f"Complete STANDARD (P+F+Fi): {complete_standard:5}/{total} = {complete_standard/total*100:5.1f}%")
    print(f"Complete FULL (all 5):      {complete_full:5}/{total} = {complete_full/total*100:5.1f}%")
    print(f"Has calories:               {has_calories:5}/{total} = {has_calories/total*100:5.1f}%")
    print(f"Has ANY nutrition:          {has_any_nutrition:5}/{total} = {has_any_nutrition/total*100:5.1f}%")
    print(f"NO nutrition at all:        {no_nutrition:5}/{total} = {no_nutrition/total*100:5.1f}%")
    
    print("\n" + "="*60)
    print("KEY INSIGHTS:")
    print("-"*40)
    print(f"✅ {complete_basic/total*100:.1f}% have basic nutrition (protein + fat)")
    print(f"⚠️  Only {complete_standard/total*100:.1f}% have standard nutrition (P+F+Fiber)")
    print(f"❌ Only {complete_full/total*100:.1f}% have complete nutrition (all 5 macros)")
    print(f"📊 {has_calories/total*100:.1f}% have caloric data")
    
    # Check what's missing
    print("\nWhat's missing for products with partial nutrition:")
    partial_products = [p for p in all_products if p.get('protein_percent') is not None]
    
    missing_fiber = sum(1 for p in partial_products if p.get('fiber_percent') is None)
    missing_ash = sum(1 for p in partial_products if p.get('ash_percent') is None)
    missing_moisture = sum(1 for p in partial_products if p.get('moisture_percent') is None)
    
    print(f"Products with protein but missing fiber: {missing_fiber}/{len(partial_products)} ({missing_fiber/len(partial_products)*100:.1f}%)")
    print(f"Products with protein but missing ash: {missing_ash}/{len(partial_products)} ({missing_ash/len(partial_products)*100:.1f}%)")
    print(f"Products with protein but missing moisture: {missing_moisture}/{len(partial_products)} ({missing_moisture/len(partial_products)*100:.1f}%)")

if __name__ == "__main__":
    main()