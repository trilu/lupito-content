#!/usr/bin/env python3
"""
Direct update of form and life_stage for Bozita and Belcando based on product names
"""

import os
import re
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(url, key)

# Form detection patterns
FORM_PATTERNS = {
    'dry': ['dry', 'kibble', 'croquette', 'biscuit', 'pellet', 'crispy', 'robur', 'original'],
    'wet': ['wet', 'can', 'canned', 'pouch', 'pate', 'paté', 'terrine', 'chunks', 'gravy', 'jelly', 'sauce', 'frischebeutel', 'menüdosen'],
    'raw': ['raw', 'fresh', 'frozen', 'freeze-dried', 'dehydrated'],
    'treat': ['treat', 'snack', 'chew', 'bone', 'stick', 'biscuit', 'meaty bites'],
}

# Life stage detection patterns
LIFE_STAGE_PATTERNS = {
    'puppy': ['puppy', 'junior', 'growth', 'young', 'welpe', 'valp', 'puppy & junior'],
    'adult': ['adult', 'mature', 'maintenance', 'vuxen', 'purely adult'],
    'senior': ['senior', 'mature', 'aging', 'older', 'aged', 'veteran'],
    'all': ['all life stages', 'all ages', 'family', 'complete'],
}

def detect_form(text):
    """Detect product form from text"""
    if not text:
        return None
    text_lower = text.lower()
    
    for form, patterns in FORM_PATTERNS.items():
        for pattern in patterns:
            if pattern in text_lower:
                return form
    return None

def detect_life_stage(text):
    """Detect life stage from text"""
    if not text:
        return None
    text_lower = text.lower()
    
    for stage, patterns in LIFE_STAGE_PATTERNS.items():
        for pattern in patterns:
            if pattern in text_lower:
                return stage
    return None

def update_brand(brand_slug):
    """Update form and life_stage for a brand's products"""
    print(f"\nProcessing {brand_slug.upper()}...")
    
    # Get all products for this brand
    products = supabase.table('foods_canonical').select('*').eq('brand_slug', brand_slug).execute()
    
    updates_made = 0
    form_updates = 0
    life_stage_updates = 0
    
    for product in products.data:
        update_data = {}
        
        # Check if form is missing
        if not product.get('form'):
            detected_form = detect_form(product.get('product_name'))
            if detected_form:
                update_data['form'] = detected_form
                form_updates += 1
        
        # Check if life_stage is missing
        if not product.get('life_stage'):
            detected_life_stage = detect_life_stage(product.get('product_name'))
            if detected_life_stage:
                update_data['life_stage'] = detected_life_stage
                life_stage_updates += 1
        
        # Update if we have data
        if update_data:
            try:
                supabase.table('foods_canonical').update(update_data).eq(
                    'product_key', product['product_key']
                ).execute()
                updates_made += 1
                print(f"  Updated: {product['product_name'][:50]}... [{', '.join(update_data.keys())}]")
            except Exception as e:
                print(f"  Error updating {product['product_name']}: {e}")
    
    print(f"  Summary: {updates_made} products updated ({form_updates} form, {life_stage_updates} life_stage)")
    return updates_made, form_updates, life_stage_updates

def main():
    print("="*80)
    print("DIRECT FORM & LIFE_STAGE UPDATE")
    print("="*80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    brands = ['bozita', 'belcando', 'briantos']
    
    total_updates = 0
    total_form = 0
    total_life_stage = 0
    
    for brand in brands:
        updates, form, life_stage = update_brand(brand)
        total_updates += updates
        total_form += form
        total_life_stage += life_stage
    
    print("\n" + "="*80)
    print("UPDATE COMPLETE")
    print(f"Total products updated: {total_updates}")
    print(f"Form fields added: {total_form}")
    print(f"Life stage fields added: {total_life_stage}")
    print("="*80)

if __name__ == "__main__":
    main()