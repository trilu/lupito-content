#!/usr/bin/env python3
"""
Generate QA report for scraped food products
Exports sample data to CSV and displays inline
"""
import os
import sys
import csv
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import random

from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()


def get_supabase_client() -> Client:
    """Setup Supabase client"""
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_KEY')
    
    if not url or not key:
        raise ValueError("Supabase credentials not found in environment")
    
    return create_client(url, key)


def fetch_sample_data(client: Client, limit: int = 20) -> List[Dict]:
    """Fetch sample data from foods_published view"""
    try:
        # Try to fetch from foods_published view
        response = client.table('foods_published').select(
            'brand, product_name, form, life_stage, kcal_per_100g, '
            'protein_percent, fat_percent, contains_chicken, price_eur'
        ).limit(limit).execute()
        
        return response.data
    except:
        # If view doesn't exist, fetch from food_candidates
        print("Note: foods_published view not found, fetching from food_candidates")
        response = client.table('food_candidates').select(
            'brand, product_name, form, life_stage, kcal_per_100g, '
            'protein_percent, fat_percent, contains_chicken, price_eur'
        ).limit(limit).execute()
        
        return response.data


def generate_sample_data() -> List[Dict]:
    """Generate sample data for demonstration if database is empty"""
    brands = ['Royal Canin', 'Hill\'s', 'Purina', 'Eukanuba', 'Acana', 'Orijen', 'Blue Buffalo', 'Taste of the Wild']
    forms = ['dry', 'wet', 'raw', 'vet']
    life_stages = ['puppy', 'adult', 'senior', 'all']
    
    sample_data = []
    for i in range(20):
        brand = random.choice(brands)
        form = random.choice(forms)
        life_stage = random.choice(life_stages)
        
        sample_data.append({
            'brand': brand,
            'product_name': f"{brand} {life_stage.title()} {form.title()} Formula",
            'form': form,
            'life_stage': life_stage,
            'kcal_per_100g': round(random.uniform(300, 450), 1),
            'protein_percent': round(random.uniform(20, 38), 1),
            'fat_percent': round(random.uniform(10, 20), 1),
            'contains_chicken': random.choice([True, False]),
            'price_eur': round(random.uniform(25, 85), 2)
        })
    
    return sample_data


def mask_long_field(text: str, max_length: int = 30) -> str:
    """Mask long fields for display"""
    if not text:
        return ''
    text = str(text)
    if len(text) > max_length:
        return text[:max_length-3] + '...'
    return text


def export_to_csv(data: List[Dict], output_path: str):
    """Export data to CSV file"""
    if not data:
        print("No data to export")
        return
    
    # Create output directory if needed
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Write CSV
    fieldnames = ['brand', 'product_name', 'form', 'life_stage', 'kcal_per_100g', 
                  'protein_percent', 'fat_percent', 'contains_chicken', 'price_eur']
    
    with open(output_path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in data:
            # Ensure all fields are present
            cleaned_row = {field: row.get(field, '') for field in fieldnames}
            writer.writerow(cleaned_row)
    
    print(f"\n✅ CSV exported to: {output_path}")


def display_sample_rows(data: List[Dict], sample_size: int = 5):
    """Display sample rows inline"""
    if not data:
        print("No data to display")
        return
    
    sample = data[:sample_size]
    
    print("\n" + "="*80)
    print("SAMPLE DATA (5 rows)")
    print("="*80)
    
    # Header
    print(f"{'Brand':<15} {'Product':<25} {'Form':<6} {'Stage':<8} {'kcal':<6} {'Prot%':<6} {'Fat%':<6} {'Chkn':<5} {'EUR':<7}")
    print("-"*80)
    
    # Rows
    for row in sample:
        print(f"{mask_long_field(row.get('brand', ''), 15):<15} "
              f"{mask_long_field(row.get('product_name', ''), 25):<25} "
              f"{str(row.get('form', '')):<6} "
              f"{str(row.get('life_stage', '')):<8} "
              f"{str(row.get('kcal_per_100g', '')):<6} "
              f"{str(row.get('protein_percent', '')):<6} "
              f"{str(row.get('fat_percent', '')):<6} "
              f"{'Yes' if row.get('contains_chicken') else 'No':<5} "
              f"{str(row.get('price_eur', '')):<7}")
    
    print("="*80)


def print_sql_view():
    """Print the SQL for creating foods_published view"""
    sql = """
-- CREATE OR REPLACE VIEW for foods_published
-- Copy and paste this into Supabase SQL editor

CREATE OR REPLACE VIEW foods_published AS
SELECT 
  id,
  source_domain,
  source_url,
  brand,
  product_name,
  form,
  life_stage,
  kcal_per_100g,
  protein_percent,
  fat_percent,
  fiber_percent,
  ash_percent,
  moisture_percent,
  ingredients_raw,
  -- Ensure tokens are trimmed and lowercased
  ARRAY(
    SELECT DISTINCT LOWER(TRIM(token))
    FROM UNNEST(ingredients_tokens) AS token
    WHERE TRIM(token) != ''
  ) AS ingredients_tokens,
  -- Ensure contains_chicken is set based on tokens
  CASE 
    WHEN contains_chicken = TRUE THEN TRUE
    WHEN EXISTS (
      SELECT 1 
      FROM UNNEST(ingredients_tokens) AS token 
      WHERE LOWER(token) IN ('chicken', 'chicken fat', 'chicken meal', 'chicken liver')
    ) THEN TRUE
    ELSE FALSE
  END AS contains_chicken,
  pack_sizes,
  price_eur,
  -- Derive price bucket based on price_eur
  CASE
    WHEN price_eur IS NULL THEN 'mid'
    WHEN price_eur < 30 THEN 'low'
    WHEN price_eur < 60 THEN 'mid'
    ELSE 'high'
  END AS price_bucket,
  -- Ensure available_countries defaults to EU
  COALESCE(available_countries, '{EU}') AS available_countries,
  gtin,
  first_seen_at,
  last_seen_at
FROM food_candidates
WHERE brand IS NOT NULL 
  AND product_name IS NOT NULL;

-- Grant appropriate permissions
GRANT SELECT ON foods_published TO anon;
GRANT SELECT ON foods_published TO authenticated;
"""
    
    print("\n" + "="*80)
    print("SQL FOR FOODS_PUBLISHED VIEW")
    print("="*80)
    print(sql)
    print("="*80)


def main():
    print("🔍 PetFoodExpert QA Report Generator")
    print("-"*40)
    
    try:
        # Connect to Supabase
        client = get_supabase_client()
        print("✅ Connected to Supabase")
        
        # Fetch sample data
        data = fetch_sample_data(client)
        
        if not data:
            print("\n⚠️  No data found in database. Generating sample data for demonstration...")
            data = generate_sample_data()
        else:
            print(f"✅ Fetched {len(data)} rows from database")
        
        # Export to CSV
        output_path = "out/pfx_qa_sample.csv"
        export_to_csv(data, output_path)
        
        # Display sample rows
        display_sample_rows(data)
        
        # Print row count
        print(f"\nTotal rows in report: {len(data)}")
        
        # Print SQL for view
        print_sql_view()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nGenerating demonstration data instead...")
        
        # Generate and display sample data
        data = generate_sample_data()
        
        # Export to CSV
        output_path = "out/pfx_qa_sample.csv"
        export_to_csv(data, output_path)
        
        # Display sample rows
        display_sample_rows(data)
        
        # Print SQL anyway
        print_sql_view()


if __name__ == '__main__':
    main()