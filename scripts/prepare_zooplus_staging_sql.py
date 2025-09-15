#!/usr/bin/env python3
"""
Generate SQL for Zooplus staging table with proper normalization
"""

import pandas as pd
import re

def clean_product_name(name):
    """Clean and normalize product name"""
    if pd.isna(name):
        return ''
    name = str(name).strip()
    # Remove special characters but keep essential ones
    name = re.sub(r'["\']', '', name)
    # Normalize spaces
    name = re.sub(r'\s+', ' ', name)
    return name

def extract_brand_from_url(url):
    """Extract and normalize brand from URL"""
    if pd.isna(url):
        return 'Unknown'
    match = re.search(r'/shop/dogs/[^/]+/([^/]+)/', url)
    if match:
        brand = match.group(1).replace('_', ' ')
        # Apply brand normalization mappings
        brand_map = {
            'wolf of wilderness': 'Wolf of Wilderness',
            'hills science plan': "Hill's Science Plan", 
            'hills prescription diet': "Hill's Prescription Diet",
            'hills prescription': "Hill's Prescription Diet",
            'royal canin vet diet': 'Royal Canin Veterinary Diet',
            'royal canin veterinary diet': 'Royal Canin Veterinary Diet',
            'royal canin care nutrition': 'Royal Canin Care Nutrition',
            'royal canin breed': 'Royal Canin Breed',
            'purina pro plan': 'Pro Plan',
            'concept for life': 'Concept for Life',
            'advance vet diets': 'Advance Veterinary Diets',
            'macs': "MAC's",
            'dogsn tiger': "Dogs'n Tiger"
        }
        brand_lower = brand.lower()
        return brand_map.get(brand_lower, brand.title())
    return 'Unknown'

def generate_product_key(brand, name, food_type):
    """Generate consistent product key"""
    brand_clean = re.sub(r'[^a-z0-9]+', '', brand.lower())
    name_clean = re.sub(r'[^a-z0-9]+', '_', name.lower())
    return f"{brand_clean}|{name_clean}|{food_type}"

# Read both CSV files
df1 = pd.read_csv('data/zooplus/zooplus-com-2025-09-12.csv')
df2 = pd.read_csv('data/zooplus/zooplus-com-2025-09-12-2.csv')

# Process file 1 (wet food)
products1 = []
for _, row in df1.iterrows():
    url = row.get('data-page-selector-href', '')
    if pd.isna(url) or not url:
        continue
    
    brand = extract_brand_from_url(url)
    name = clean_product_name(row.get('product_name-0', ''))
    desc = str(row.get('product_description-0', ''))
    
    food_type = 'wet' if 'canned' in url or 'wet' in url else 'dry'
    
    # Check for ingredients
    has_ingredients = False
    ingredients_text = ''
    if not pd.isna(desc) and desc:
        if any(word in desc.lower() for word in ['ingredient', 'composition', 'meat', 'chicken', 'beef', 'lamb']):
            has_ingredients = True
            ingredients_text = desc[:500]  # First 500 chars
    
    product_key = generate_product_key(brand, name, food_type)
    
    products1.append({
        'product_key': product_key,
        'brand': brand,
        'product_name': name,
        'product_url': url,
        'food_type': food_type,
        'has_ingredients': has_ingredients,
        'ingredients_preview': ingredients_text,
        'source_file': 'file1'
    })

# Process file 2 (dry food)  
products2 = []
for _, row in df2.iterrows():
    url = row.get('data-page-selector-href', '')
    if pd.isna(url) or not url:
        continue
    
    brand = extract_brand_from_url(url)
    name = clean_product_name(row.get('text-1', ''))
    
    food_type = 'dry' if 'dry' in url else 'wet' if 'canned' in url or 'wet' in url else 'unknown'
    
    product_key = generate_product_key(brand, name, food_type)
    
    products2.append({
        'product_key': product_key,
        'brand': brand,
        'product_name': name,
        'product_url': url,
        'food_type': food_type,
        'has_ingredients': False,
        'ingredients_preview': '',
        'source_file': 'file2'
    })

# Combine and dedupe
all_products = products1 + products2
df_combined = pd.DataFrame(all_products)

# Remove duplicates by URL
df_combined = df_combined.drop_duplicates(subset=['product_url'])

print(f"Total unique products: {len(df_combined)}")
print(f"Products with ingredients preview: {df_combined['has_ingredients'].sum()}")
print(f"\nTop brands:")
print(df_combined['brand'].value_counts().head(10))

# Save to CSV for inspection
df_combined.to_csv('data/zooplus_staging_prepared.csv', index=False)

# Generate SQL
print("\n" + "="*60)
print("SQL TO CREATE STAGING TABLE:")
print("="*60)
print("""
CREATE TABLE IF NOT EXISTS zooplus_staging (
    id SERIAL PRIMARY KEY,
    product_key TEXT NOT NULL,
    brand TEXT,
    product_name TEXT,
    product_url TEXT UNIQUE,
    food_type TEXT,
    has_ingredients BOOLEAN DEFAULT FALSE,
    ingredients_preview TEXT,
    source_file TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    processed BOOLEAN DEFAULT FALSE,
    matched_product_key TEXT,
    match_type TEXT,
    match_confidence DECIMAL(3,2)
);

CREATE INDEX idx_zooplus_staging_url ON zooplus_staging(product_url);
CREATE INDEX idx_zooplus_staging_brand ON zooplus_staging(brand);
CREATE INDEX idx_zooplus_staging_product_key ON zooplus_staging(product_key);
CREATE INDEX idx_zooplus_staging_processed ON zooplus_staging(processed);
""")

print("\nSample insert statement (first 5 rows):")
for i, row in df_combined.head(5).iterrows():
    ingredients_preview = row['ingredients_preview'].replace("'", "''") if row['ingredients_preview'] else ''
    print(f"""
INSERT INTO zooplus_staging (product_key, brand, product_name, product_url, food_type, has_ingredients, ingredients_preview, source_file)
VALUES (
    '{row['product_key']}',
    '{row['brand']}',
    '{row['product_name'].replace("'", "''")}',
    '{row['product_url']}',
    '{row['food_type']}',
    {str(row['has_ingredients']).upper()},
    '{ingredients_preview}',
    '{row['source_file']}'
);""")

print(f"\nTotal rows to insert: {len(df_combined)}")
