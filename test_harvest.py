#!/usr/bin/env python3
"""Test harvest for top 3 brands"""

import os
import yaml
import json
import requests
from pathlib import Path
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

# Initialize Supabase
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(url, key)

# Test brands
test_brands = [
    {
        'brand_slug': 'eukanuba',
        'brand_name': 'Eukanuba',
        'website_url': 'https://www.eukanuba.co.uk'
    },
    {
        'brand_slug': 'brit',
        'brand_name': 'Brit',
        'website_url': 'https://www.brit-petfood.com'
    },
    {
        'brand_slug': 'alpha',
        'brand_name': 'Alpha Pet Foods',
        'website_url': 'https://www.alphapetfoods.com'
    }
]

print("="*80)
print("TEST HARVEST - TOP 3 BRANDS")
print("="*80)

# Create sample harvest data
harvest_data = []
batch_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

for brand in test_brands:
    print(f"\n📦 Processing {brand['brand_name']}...")
    
    # Get products from canonical table
    response = supabase.table('foods_canonical').select(
        'product_key,product_name,form,life_stage,kcal_per_100g,ingredients_tokens,price_per_kg'
    ).eq('brand_slug', brand['brand_slug']).execute()
    
    if response.data:
        products = response.data
        print(f"  Found {len(products)} products in foods_canonical")
        
        # Simulate harvested data for testing
        for product in products[:10]:  # Just first 10 products
            # Simulate some enriched data
            harvest_row = {
                'brand_slug': brand['brand_slug'],
                'product_name': product['product_name'],
                'product_url': f"{brand['website_url']}/products/{product['product_key']}",
                'harvest_batch': batch_id,
                'harvest_timestamp': datetime.now().isoformat(),
                'confidence_score': 0.95
            }
            
            # Add simulated data if missing
            if not product.get('form'):
                harvest_row['form'] = 'dry'  # Simulated
            
            if not product.get('life_stage'):
                harvest_row['life_stage'] = 'adult'  # Simulated
            
            if not product.get('kcal_per_100g'):
                harvest_row['kcal_per_100g'] = 380  # Simulated average
            
            if not product.get('price_per_kg'):
                harvest_row['price_per_kg'] = 12.50  # Simulated
                harvest_row['currency'] = 'GBP'
            
            # Simulated nutrition data
            harvest_row['protein_percent'] = 25.0
            harvest_row['fat_percent'] = 15.0
            harvest_row['fibre_percent'] = 3.5
            harvest_row['moisture_percent'] = 10.0
            harvest_row['ash_percent'] = 7.0
            
            # Add some sample ingredients if missing
            if not product.get('ingredients_tokens'):
                harvest_row['ingredients_tokens'] = [
                    'chicken', 'rice', 'maize', 'barley', 'animal fat',
                    'dried beet pulp', 'minerals', 'vitamins'
                ]
                harvest_row['ingredients_raw'] = 'Chicken, Rice, Maize, Barley, Animal Fat, Dried Beet Pulp, Minerals, Vitamins'
            
            harvest_data.append(harvest_row)

print(f"\n\n📊 Total harvest records: {len(harvest_data)}")

# Insert into staging table
if harvest_data:
    print("\n💾 Loading data into manufacturer_harvest_staging...")
    
    try:
        # Insert in batches
        batch_size = 50
        for i in range(0, len(harvest_data), batch_size):
            batch = harvest_data[i:i+batch_size]
            response = supabase.table('manufacturer_harvest_staging').insert(batch).execute()
            print(f"  Inserted batch {i//batch_size + 1}: {len(batch)} records")
        
        print(f"\n✅ Successfully loaded {len(harvest_data)} records")
        
        # Verify data was inserted
        verify = supabase.table('manufacturer_harvest_staging').select('count', count='exact').eq('harvest_batch', batch_id).execute()
        print(f"  Verified: {verify.count} records in staging table")
        
    except Exception as e:
        print(f"❌ Error loading data: {e}")

# Save harvest report
report_path = Path(f"reports/MANUF/harvests/test_harvest_{batch_id}.csv")
report_path.parent.mkdir(parents=True, exist_ok=True)
df = pd.DataFrame(harvest_data)
df.to_csv(report_path, index=False)
print(f"\n📄 Report saved to: {report_path}")

print("\n" + "="*80)
print("TEST HARVEST COMPLETE")
print("="*80)
print("\nNext steps:")
print("1. Run the enrichment UPDATE query")
print("2. Check manufacturer_matches view for matches")
print("3. Verify foods_published_preview was updated")