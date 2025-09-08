#!/usr/bin/env python3
"""
Script to add missing brands to food_brands_sc table
"""
import os
import uuid
from datetime import datetime
from supabase import create_client, Client

# Initialize Supabase client
supabase_url = os.environ.get('SUPABASE_URL', 'https://cibjeqgftuxuezarjsdl.supabase.co')
supabase_key = os.environ.get('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNpYmplcWdmdHV4dWV6YXJqc2RsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1Mzg1NTY2NywiZXhwIjoyMDY5NDMxNjY3fQ.ngzgvYr2zXisvkz03F86zNWPRHP0tEMX0gQPBm2z_jk')

supabase: Client = create_client(supabase_url, supabase_key)

def normalize_brand_name(brand: str) -> str:
    """Normalize brand name for matching"""
    return brand.lower().replace(' ', '').replace('-', '').replace('&', 'and').replace('.', '').replace("'", '')

def load_all_brands():
    """Load complete brand list"""
    brands = []
    with open('aadf_all_brands_complete.txt', 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                brands.append(line)
    return brands

def get_existing_brands():
    """Get brands already in database"""
    try:
        response = supabase.table('food_brands_sc').select('brand_name').execute()
        return [brand['brand_name'] for brand in response.data]
    except Exception as e:
        print(f"Error fetching existing brands: {e}")
        return []

def add_missing_brands():
    """Add missing brands to database"""
    # Get all brands from file
    all_brands = load_all_brands()
    print(f"Total brands from screenshots: {len(all_brands)}")
    
    # Get existing brands
    existing_brands = get_existing_brands()
    existing_brands_normalized = {normalize_brand_name(b) for b in existing_brands}
    print(f"Brands already in database: {len(existing_brands)}")
    
    # Find missing brands
    missing_brands = []
    for brand in all_brands:
        if normalize_brand_name(brand) not in existing_brands_normalized:
            missing_brands.append(brand)
    
    print(f"Missing brands to add: {len(missing_brands)}")
    
    if not missing_brands:
        print("No missing brands to add!")
        return
    
    # Prepare records for missing brands
    records = []
    timestamp = datetime.utcnow().isoformat()
    
    for brand in missing_brands:
        record = {
            'id': str(uuid.uuid4()),
            'brand_name': brand,
            'brand_normalized': normalize_brand_name(brand),
            'aadf_reference': True,
            'available_countries': ['UK'],
            'scraping_status': 'pending',
            'created_at': timestamp,
            'updated_at': timestamp,
            'scraping_priority': 0,
            'products_scraped_count': 0,
            'official_website_verified': False,
            'other_sources': []
        }
        records.append(record)
    
    # Insert in batches
    batch_size = 50
    total_inserted = 0
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i+batch_size]
        try:
            response = supabase.table('food_brands_sc').insert(batch).execute()
            total_inserted += len(batch)
            print(f"Inserted batch {i//batch_size + 1}: {len(batch)} records (Total: {total_inserted}/{len(records)})")
        except Exception as e:
            print(f"Error inserting batch {i//batch_size + 1}: {e}")
            # Try individual inserts for failed batch
            for record in batch:
                try:
                    supabase.table('food_brands_sc').insert(record).execute()
                    total_inserted += 1
                    print(f"  ✓ Added {record['brand_name']}")
                except Exception as individual_error:
                    if 'duplicate' not in str(individual_error).lower():
                        print(f"  ✗ Failed to add {record['brand_name']}: {individual_error}")
    
    print(f"\n{'='*80}")
    print(f"SUMMARY: Added {total_inserted} new brands to food_brands_sc")
    print(f"{'='*80}")
    
    # Final count
    try:
        count_response = supabase.table('food_brands_sc').select('id', count='exact').execute()
        print(f"\nTotal brands in database now: {count_response.count}")
    except Exception as e:
        print(f"Could not verify final count: {e}")

if __name__ == "__main__":
    print("="*80)
    print("ADDING MISSING BRANDS TO DATABASE")
    print("="*80)
    add_missing_brands()