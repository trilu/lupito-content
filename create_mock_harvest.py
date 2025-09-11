#!/usr/bin/env python3
"""
Create mock harvest data to demonstrate the enrichment pipeline
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from supabase import create_client
from dotenv import load_dotenv
import json

load_dotenv()

def create_mock_harvest():
    """Create mock manufacturer harvest data based on catalog"""
    
    # Connect to Supabase
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("ERROR: Supabase credentials not found")
        return
    
    supabase = create_client(supabase_url, supabase_key)
    
    # Load catalog
    print("Loading catalog...")
    response = supabase.table('foods_published').select("*").limit(500).execute()
    catalog_df = pd.DataFrame(response.data)
    
    # Filter for dog products only
    if 'product_name' in catalog_df.columns:
        dog_mask = ~catalog_df['product_name'].str.lower().str.contains('cat|kitten|feline', na=False)
        catalog_df = catalog_df[dog_mask]
    
    print(f"Found {len(catalog_df)} dog products")
    
    # Create mock harvest data for products missing data
    harvest_data = []
    
    for _, row in catalog_df.iterrows():
        # Only create mock data for products with missing fields
        needs_enrichment = (
            pd.isna(row.get('form')) or
            pd.isna(row.get('life_stage')) or
            pd.isna(row.get('kcal_per_100g')) or
            pd.isna(row.get('price_per_kg'))
        )
        
        if needs_enrichment:
            mock_product = {
                'url': f"https://www.{row['brand_slug']}.com/products/{row['product_key']}",
                'scraped_at': datetime.now().isoformat(),
                'brand': row['brand'],
                'brand_slug': row['brand_slug'],
                'product_name': row['product_name'],
                'from_cache': False
            }
            
            # Generate mock ingredients if missing
            ing_tokens = row.get('ingredients_tokens')
            # Check if ingredients are missing (handle arrays, None, NaN, empty strings)
            has_ingredients = False
            if ing_tokens is not None:
                if isinstance(ing_tokens, (list, np.ndarray)):
                    has_ingredients = len(ing_tokens) > 0
                elif isinstance(ing_tokens, str):
                    has_ingredients = bool(ing_tokens.strip())
                else:
                    try:
                        has_ingredients = not pd.isna(ing_tokens)
                    except:
                        has_ingredients = False
            
            if not has_ingredients:
                # Common dog food ingredients
                base_ingredients = [
                    'chicken', 'chicken meal', 'rice', 'barley', 'peas',
                    'sweet potato', 'chicken fat', 'flaxseed', 'vitamins', 'minerals'
                ]
                # Add some variety
                if 'puppy' in str(row['product_name']).lower():
                    base_ingredients.insert(2, 'dha')
                    base_ingredients.insert(3, 'calcium')
                elif 'senior' in str(row['product_name']).lower():
                    base_ingredients.insert(2, 'glucosamine')
                    base_ingredients.insert(3, 'chondroitin')
                
                mock_product['ingredients'] = ', '.join(base_ingredients[:8])
            
            # Generate mock analytical constituents
            if pd.isna(row.get('kcal_per_100g')):
                # Typical ranges for dog food
                mock_product['analytical_constituents'] = (
                    f"Crude Protein: {np.random.uniform(18, 32):.1f}%, "
                    f"Crude Fat: {np.random.uniform(8, 18):.1f}%, "
                    f"Crude Fiber: {np.random.uniform(2, 5):.1f}%, "
                    f"Crude Ash: {np.random.uniform(5, 8):.1f}%, "
                    f"Moisture: {np.random.uniform(8, 12):.1f}%"
                )
            
            # Detect form from product name
            if pd.isna(row.get('form')):
                name_lower = str(row['product_name']).lower()
                if any(word in name_lower for word in ['dry', 'kibble', 'biscuit']):
                    mock_product['form'] = 'dry'
                elif any(word in name_lower for word in ['wet', 'can', 'pouch', 'pate']):
                    mock_product['form'] = 'wet'
                elif any(word in name_lower for word in ['raw', 'frozen']):
                    mock_product['form'] = 'raw'
                else:
                    # Default based on brand patterns
                    mock_product['form'] = np.random.choice(['dry', 'wet'], p=[0.7, 0.3])
            
            # Detect life stage
            if pd.isna(row.get('life_stage')):
                name_lower = str(row['product_name']).lower()
                if 'puppy' in name_lower or 'junior' in name_lower:
                    mock_product['life_stage'] = 'puppy'
                elif 'senior' in name_lower or 'mature' in name_lower:
                    mock_product['life_stage'] = 'senior'
                else:
                    mock_product['life_stage'] = 'adult'
            
            # Generate mock price
            if pd.isna(row.get('price_per_kg')):
                # Price based on brand tier
                if row['brand_slug'] in ['acana', 'orijen', 'applaws']:
                    price_range = (25, 45)  # Premium
                elif row['brand_slug'] in ['hills', 'royal-canin', 'purina']:
                    price_range = (15, 30)  # Mid-range
                else:
                    price_range = (8, 20)  # Economy
                
                mock_product['price'] = np.random.uniform(*price_range)
                mock_product['pack_size'] = '2kg'  # Assume 2kg pack
                mock_product['price_per_kg'] = mock_product['price'] / 2
            
            # Add JSON-LD for some products (30% chance)
            if np.random.random() < 0.3:
                mock_product['jsonld'] = {
                    "@type": "Product",
                    "name": row['product_name'],
                    "brand": {"@type": "Brand", "name": row['brand']},
                    "offers": {
                        "@type": "Offer",
                        "price": mock_product.get('price', np.random.uniform(10, 40)),
                        "priceCurrency": "EUR"
                    }
                }
            
            harvest_data.append(mock_product)
    
    # Create DataFrame
    harvest_df = pd.DataFrame(harvest_data)
    
    # Save to harvest directory
    output_dir = Path("reports/MANUF/harvests")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save by brand
    for brand_slug in harvest_df['brand_slug'].unique():
        brand_data = harvest_df[harvest_df['brand_slug'] == brand_slug]
        output_file = output_dir / f"{brand_slug}_harvest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        brand_data.to_csv(output_file, index=False)
        print(f"Created mock harvest for {brand_slug}: {len(brand_data)} products")
    
    # Summary
    print(f"\nTotal mock harvest data created: {len(harvest_df)} products")
    print(f"Brands covered: {harvest_df['brand_slug'].nunique()}")
    
    # Create summary report
    summary = f"""# MOCK HARVEST DATA SUMMARY
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Statistics
- Total Products: {len(harvest_df)}
- Brands: {harvest_df['brand_slug'].nunique()}
- With Ingredients: {harvest_df['ingredients'].notna().sum()}
- With Analytical: {harvest_df['analytical_constituents'].notna().sum()}
- With Form: {harvest_df['form'].notna().sum()}
- With Life Stage: {harvest_df['life_stage'].notna().sum()}
- With Price: {harvest_df['price'].notna().sum()}
- With JSON-LD: {harvest_df['jsonld'].notna().sum()}

## Purpose
This mock data simulates manufacturer website harvest results to demonstrate
the enrichment pipeline functionality when actual website scraping is not feasible.
"""
    
    with open(output_dir / "MOCK_HARVEST_SUMMARY.md", "w") as f:
        f.write(summary)
    
    print("\n" + summary)
    
    return harvest_df

if __name__ == "__main__":
    create_mock_harvest()