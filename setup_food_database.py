#!/usr/bin/env python3
"""
Setup SQLite database with food catalog schema and sample data.
"""

import sqlite3
import random
import json
from datetime import datetime, timedelta

def create_schema(conn):
    """Create the food catalog schema."""
    cursor = conn.cursor()
    
    # Drop existing tables if they exist
    cursor.execute("DROP TABLE IF EXISTS foods_published")
    cursor.execute("DROP TABLE IF EXISTS food_candidates")
    cursor.execute("DROP TABLE IF EXISTS food_brands")
    cursor.execute("DROP TABLE IF EXISTS foods_enrichment")
    cursor.execute("DROP TABLE IF EXISTS foods_overrides")
    
    # Create foods_published table
    cursor.execute("""
    CREATE TABLE foods_published (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_key TEXT UNIQUE NOT NULL,
        source_domain TEXT,
        source_url TEXT,
        brand TEXT,
        brand_slug TEXT,
        product_name TEXT,
        form TEXT,
        life_stage TEXT,
        kcal_per_100g REAL,
        protein_percent REAL,
        fat_percent REAL,
        fiber_percent REAL,
        ash_percent REAL,
        moisture_percent REAL,
        ingredients_raw TEXT,
        ingredients_tokens TEXT,
        ingredients_unknown INTEGER DEFAULT 0,
        pack_size TEXT,
        price_eur REAL,
        price_per_kg_eur REAL,
        price_bucket TEXT,
        available_countries TEXT,
        gtin TEXT,
        fetched_at TIMESTAMP,
        updated_at TIMESTAMP,
        ingredients_tokens_from TEXT,
        kcal_per_100g_from TEXT,
        price_bucket_from TEXT,
        life_stage_from TEXT,
        form_from TEXT
    )
    """)
    
    # Create indexes
    cursor.execute("CREATE INDEX idx_product_key ON foods_published(product_key)")
    cursor.execute("CREATE INDEX idx_brand ON foods_published(brand)")
    cursor.execute("CREATE INDEX idx_brand_slug ON foods_published(brand_slug)")
    cursor.execute("CREATE INDEX idx_form ON foods_published(form)")
    cursor.execute("CREATE INDEX idx_life_stage ON foods_published(life_stage)")
    cursor.execute("CREATE INDEX idx_form_life ON foods_published(form, life_stage)")
    
    # Create other tables
    cursor.execute("""
    CREATE TABLE food_candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_key TEXT,
        brand TEXT,
        product_name TEXT,
        kcal_per_100g REAL,
        life_stage TEXT,
        form TEXT
    )
    """)
    
    cursor.execute("""
    CREATE TABLE food_brands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        brand TEXT,
        brand_slug TEXT,
        product_count INTEGER
    )
    """)
    
    cursor.execute("""
    CREATE TABLE foods_enrichment (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_key TEXT,
        field_name TEXT,
        field_value TEXT,
        source TEXT
    )
    """)
    
    cursor.execute("""
    CREATE TABLE foods_overrides (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_key TEXT,
        field_name TEXT,
        field_value TEXT,
        reason TEXT
    )
    """)
    
    conn.commit()

def generate_sample_data(conn):
    """Generate realistic sample food data."""
    cursor = conn.cursor()
    
    # Define realistic data
    brands = [
        'Royal Canin', 'Hills Science Diet', 'Purina Pro Plan', 'Blue Buffalo', 
        'Orijen', 'Acana', 'Wellness', 'Taste of the Wild', 'Merrick', 'Nutro',
        'Iams', 'Eukanuba', 'Pedigree', 'Cesar', 'Sheba', 'Fancy Feast',
        'Friskies', 'Whiskas', 'Farmina', 'Canidae', 'Zignature', 'Fromm',
        'Victor', 'Diamond Naturals', 'Rachael Ray Nutrish', 'Natural Balance',
        'Solid Gold', 'Earthborn Holistic', 'Nulo', 'Go! Solutions',
        'Now Fresh', 'Open Farm', 'Jinx', 'Ollie', 'The Farmers Dog',
        'Nom Nom', 'JustFoodForDogs', 'Stella & Chewys', 'Primal Pet Foods',
        'Instinct', 'Ziwi Peak', 'Weruva', 'Tiki Cat', 'Applaws', 'Almo Nature',
        'Lily\'s Kitchen', 'Burns', 'James Wellbeloved', 'Arden Grange', 'Barking Heads'
    ]
    
    forms = ['dry', 'wet', 'freeze_dried', 'raw', 'fresh']
    life_stages = ['puppy', 'adult', 'senior', 'all']
    price_buckets = ['low', 'mid', 'high']
    
    common_ingredients = [
        'chicken', 'beef', 'lamb', 'fish', 'salmon', 'turkey', 'duck', 'venison',
        'rice', 'corn', 'wheat', 'barley', 'oats', 'potato', 'sweet potato',
        'peas', 'lentils', 'carrots', 'spinach', 'broccoli', 'blueberries',
        'chicken meal', 'fish meal', 'lamb meal', 'chicken fat', 'fish oil',
        'vitamins', 'minerals', 'probiotics', 'glucosamine', 'chondroitin'
    ]
    
    # Generate products
    products = []
    for i in range(2500):  # Generate 2500 products
        brand = random.choice(brands)
        form = random.choice(forms)
        life_stage = random.choice(life_stages)
        
        # Generate product name
        protein = random.choice(['Chicken', 'Beef', 'Lamb', 'Salmon', 'Turkey', 'Duck'])
        descriptor = random.choice(['Recipe', 'Formula', 'Dinner', 'Feast', 'Delight', 'Supreme'])
        life_stage_name = {
            'puppy': 'Puppy',
            'adult': 'Adult',
            'senior': 'Senior',
            'all': 'All Life Stages'
        }[life_stage]
        
        product_name = f"{brand} {protein} {descriptor} {life_stage_name}"
        product_key = f"{brand.lower().replace(' ', '_')}_{protein.lower()}_{life_stage}_{i}"
        
        # Generate nutrition data (with some missing)
        has_nutrition = random.random() < 0.7  # 70% have nutrition data
        if has_nutrition:
            if form == 'dry':
                kcal = random.uniform(300, 450)
                protein = random.uniform(20, 38)
                fat = random.uniform(10, 20)
                moisture = random.uniform(8, 12)
            elif form == 'wet':
                kcal = random.uniform(70, 120)
                protein = random.uniform(7, 12)
                fat = random.uniform(3, 8)
                moisture = random.uniform(75, 82)
            else:
                kcal = random.uniform(150, 400)
                protein = random.uniform(15, 35)
                fat = random.uniform(8, 18)
                moisture = random.uniform(10, 70)
            
            fiber = random.uniform(1, 5)
            ash = random.uniform(5, 9)
        else:
            kcal = protein = fat = fiber = ash = moisture = None
        
        # Generate ingredients (with some missing)
        has_ingredients = random.random() < 0.6  # 60% have ingredients
        if has_ingredients:
            num_ingredients = random.randint(5, 15)
            ingredients = random.sample(common_ingredients, min(num_ingredients, len(common_ingredients)))
            ingredients_tokens = json.dumps(ingredients)
            ingredients_raw = ', '.join(ingredients)
            ingredients_unknown = 1 if random.random() < 0.2 else 0
        else:
            ingredients_tokens = None
            ingredients_raw = None
            ingredients_unknown = None
        
        # Generate pricing (with some missing)
        has_price = random.random() < 0.8  # 80% have price
        if has_price:
            if form == 'dry':
                price_per_kg = random.uniform(5, 50)
            elif form == 'wet':
                price_per_kg = random.uniform(10, 80)
            else:
                price_per_kg = random.uniform(15, 100)
            
            pack_size = random.choice(['1kg', '2kg', '5kg', '10kg', '15kg', '400g', '200g'])
            if 'kg' in pack_size:
                weight = float(pack_size.replace('kg', ''))
            else:
                weight = float(pack_size.replace('g', '')) / 1000
            price_eur = price_per_kg * weight
            
            # Assign price bucket
            if price_per_kg < 15:
                price_bucket = 'low'
            elif price_per_kg < 30:
                price_bucket = 'mid'
            else:
                price_bucket = 'high'
        else:
            price_eur = price_per_kg = price_bucket = pack_size = None
        
        # Generate timestamps
        days_ago = random.randint(1, 365)
        fetched_at = datetime.now() - timedelta(days=days_ago)
        updated_at = fetched_at + timedelta(days=random.randint(0, 30))
        
        # Generate provenance
        provenance_options = ['source', 'enrichment', 'override', 'default']
        ingredients_from = random.choice(provenance_options) if ingredients_tokens else None
        kcal_from = random.choice(provenance_options) if kcal else None
        price_from = random.choice(provenance_options) if price_bucket else None
        
        products.append((
            product_key, 'petfood.com', f'https://petfood.com/{product_key}',
            brand, brand.lower().replace(' ', '-'), product_name,
            form, life_stage, kcal, protein, fat, fiber, ash, moisture,
            ingredients_raw, ingredients_tokens, ingredients_unknown,
            pack_size, price_eur, price_per_kg, price_bucket,
            'EU,US,UK', f'123456789{i:04d}',
            fetched_at, updated_at,
            ingredients_from, kcal_from, price_from, 'source', 'source'
        ))
    
    # Insert data
    cursor.executemany("""
        INSERT INTO foods_published (
            product_key, source_domain, source_url, brand, brand_slug, product_name,
            form, life_stage, kcal_per_100g, protein_percent, fat_percent,
            fiber_percent, ash_percent, moisture_percent, ingredients_raw,
            ingredients_tokens, ingredients_unknown, pack_size, price_eur,
            price_per_kg_eur, price_bucket, available_countries, gtin,
            fetched_at, updated_at, ingredients_tokens_from, kcal_per_100g_from,
            price_bucket_from, life_stage_from, form_from
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, products)
    
    # Add some duplicate products to food_candidates
    for product in random.sample(products, 500):
        cursor.execute("""
            INSERT INTO food_candidates (product_key, brand, product_name, kcal_per_100g, life_stage, form)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (product[0], product[3], product[5], product[8], product[7], product[6]))
    
    # Add brand summary
    brand_counts = {}
    for product in products:
        brand = product[3]
        brand_counts[brand] = brand_counts.get(brand, 0) + 1
    
    for brand, count in brand_counts.items():
        cursor.execute("""
            INSERT INTO food_brands (brand, brand_slug, product_count)
            VALUES (?, ?, ?)
        """, (brand, brand.lower().replace(' ', '-'), count))
    
    conn.commit()
    print(f"✓ Generated {len(products)} sample food products")

def main():
    # Create and populate database
    conn = sqlite3.connect('lupito.db')
    
    print("Creating schema...")
    create_schema(conn)
    
    print("Generating sample data...")
    generate_sample_data(conn)
    
    # Verify data
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM foods_published")
    count = cursor.fetchone()[0]
    print(f"✓ Database created with {count} products in foods_published")
    
    conn.close()

if __name__ == "__main__":
    main()