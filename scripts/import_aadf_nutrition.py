#!/usr/bin/env python3
"""
Import nutritional data from AADF dataset
Updates UK products with macros (protein, fat, fiber, ash, moisture) and calories
"""

import os
import re
import csv
import json
from datetime import datetime
from typing import Dict, Optional
from urllib.parse import urlparse
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_KEY')
)

class AADFNutritionImporter:
    def __init__(self):
        self.supabase = supabase
        self.stats = {
            'total_processed': 0,
            'products_updated': 0,
            'products_skipped': 0,
            'errors': [],
            'nutrients_extracted': {
                'protein': 0,
                'fat': 0,
                'fiber': 0,
                'ash': 0,
                'moisture': 0,
                'calories': 0
            }
        }
        self.product_url_map = {}
        
    def load_uk_products(self):
        """Load all UK products from database"""
        print("Loading UK products from database...")
        
        uk_products = []
        offset = 0
        limit = 1000
        
        while True:
            response = supabase.table('foods_canonical').select(
                'product_key,product_url,protein_percent,fat_percent,fiber_percent'
            ).like('product_url', '%allaboutdogfood%').range(offset, offset + limit - 1).execute()
            
            batch = response.data
            if not batch:
                break
            uk_products.extend(batch)
            offset += limit
        
        # Create lookup by URL
        for product in uk_products:
            if product.get('product_url'):
                self.product_url_map[product['product_url']] = product
        
        print(f"Loaded {len(uk_products)} UK products")
        
        # Check how many already have macros
        with_macros = sum(1 for p in uk_products if p.get('protein_percent') is not None)
        print(f"Products already with macros: {with_macros}")
        print(f"Products needing macros: {len(uk_products) - with_macros}")
    
    def extract_nutrients(self, text: str) -> Dict[str, float]:
        """Extract nutritional values from text"""
        if not text:
            return {}
        
        text = str(text)
        nutrients = {}
        
        # Patterns for extracting percentages
        patterns = {
            'protein': r'[Pp]rotein[:\s]+([0-9.]+)%',
            'fat': r'(?:[Cc]rude\s+)?[Ff]at[:\s]+([0-9.]+)%',
            'fiber': r'(?:[Cc]rude\s+)?[Ff]ib(?:re|er)[:\s]+([0-9.]+)%',
            'ash': r'(?:[Cc]rude\s+)?[Aa]sh[:\s]+([0-9.]+)%',
            'moisture': r'[Mm]oisture[:\s]+([0-9.]+)%',
            'omega_3': r'[Oo]mega[\s-]?3[:\s]+([0-9.]+)%',
            'omega_6': r'[Oo]mega[\s-]?6[:\s]+([0-9.]+)%',
            'calcium': r'[Cc]alcium[:\s]+([0-9.]+)%',
            'phosphorus': r'[Pp]hosphorus[:\s]+([0-9.]+)%',
        }
        
        for nutrient, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                try:
                    value = float(match.group(1))
                    nutrients[nutrient] = value
                except:
                    pass
        
        # Extract calories (kcal/100g)
        kcal_patterns = [
            r'([0-9.]+)\s*kcal/100g',
            r'([0-9.]+)\s*kcal\s*/\s*100g',
            r'Energy[:\s]+([0-9.]+)\s*kcal',
            r'([0-9.]+)\s*kcal\s*per\s*100g'
        ]
        
        for pattern in kcal_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    nutrients['kcal_per_100g'] = float(match.group(1))
                    break
                except:
                    pass
        
        return nutrients
    
    def import_nutrition_data(self, csv_path: str = 'data/aadf/aadf-dataset.csv'):
        """Import nutritional data from AADF CSV"""
        
        print("\n" + "="*60)
        print("IMPORTING NUTRITIONAL DATA FROM AADF")
        print("="*60)
        
        self.load_uk_products()
        
        print(f"\nProcessing AADF data from: {csv_path}")
        
        updates = []
        
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            for row_num, row in enumerate(reader, 1):
                if row_num % 100 == 0:
                    print(f"  Processing row {row_num}...", end='\r')
                
                self.stats['total_processed'] += 1
                
                # Get URL and nutritional data
                url = row.get('data-page-selector-href', '').strip()
                nutritional_text = row.get('text-8', '').strip()
                additives_text = row.get('text-7', '').strip()
                
                if not url or url not in self.product_url_map:
                    continue
                
                product = self.product_url_map[url]
                
                # Skip if already has macros
                if product.get('protein_percent') is not None:
                    self.stats['products_skipped'] += 1
                    continue
                
                # Extract nutrients
                nutrients = self.extract_nutrients(nutritional_text)
                
                if not nutrients:
                    continue
                
                # Prepare update data
                update_data = {
                    'product_key': product['product_key'],
                    'url': url,
                    'updates': {}
                }
                
                # Map extracted nutrients to database columns
                if 'protein' in nutrients:
                    update_data['updates']['protein_percent'] = nutrients['protein']
                    self.stats['nutrients_extracted']['protein'] += 1
                
                if 'fat' in nutrients:
                    update_data['updates']['fat_percent'] = nutrients['fat']
                    self.stats['nutrients_extracted']['fat'] += 1
                
                if 'fiber' in nutrients:
                    update_data['updates']['fiber_percent'] = nutrients['fiber']
                    self.stats['nutrients_extracted']['fiber'] += 1
                
                if 'ash' in nutrients:
                    update_data['updates']['ash_percent'] = nutrients['ash']
                    self.stats['nutrients_extracted']['ash'] += 1
                
                if 'moisture' in nutrients:
                    update_data['updates']['moisture_percent'] = nutrients['moisture']
                    self.stats['nutrients_extracted']['moisture'] += 1
                
                if 'kcal_per_100g' in nutrients:
                    update_data['updates']['kcal_per_100g'] = nutrients['kcal_per_100g']
                    update_data['updates']['kcal_source'] = 'site'  # Use 'site' instead of 'aadf'
                    update_data['updates']['kcal_is_estimated'] = False
                    self.stats['nutrients_extracted']['calories'] += 1
                
                # Mark source
                if update_data['updates']:
                    update_data['updates']['macros_source'] = 'site'  # Use 'site' instead of 'aadf'
                    updates.append(update_data)
        
        print(f"\n\nReady to update {len(updates)} products with nutritional data")
        
        # Apply updates
        if updates:
            print("\nUpdating products...")
            
            batch_size = 100
            for i in range(0, len(updates), batch_size):
                batch = updates[i:i+batch_size]
                
                for update in batch:
                    try:
                        response = supabase.table('foods_canonical').update(
                            update['updates']
                        ).eq('product_key', update['product_key']).execute()
                        
                        self.stats['products_updated'] += 1
                        
                        if self.stats['products_updated'] % 50 == 0:
                            print(f"  Updated {self.stats['products_updated']} products...")
                        
                    except Exception as e:
                        self.stats['errors'].append(str(e))
                        print(f"  ❌ Error updating {update['product_key']}: {e}")
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print import summary"""
        print("\n" + "="*60)
        print("NUTRITIONAL DATA IMPORT SUMMARY")
        print("="*60)
        print(f"Total AADF rows processed: {self.stats['total_processed']}")
        print(f"Products updated: {self.stats['products_updated']}")
        print(f"Products skipped (already had data): {self.stats['products_skipped']}")
        
        print("\nNutrients extracted:")
        for nutrient, count in self.stats['nutrients_extracted'].items():
            print(f"  {nutrient}: {count} products")
        
        if self.stats['errors']:
            print(f"\nErrors encountered: {len(self.stats['errors'])}")
        
        # Verify results
        print("\nVerifying results...")
        
        # Check UK products with macros now
        uk_with_protein = supabase.table('foods_canonical').select(
            '*', count='exact'
        ).like('product_url', '%allaboutdogfood%').not_.is_('protein_percent', 'null').execute()
        
        uk_with_calories = supabase.table('foods_canonical').select(
            '*', count='exact'
        ).like('product_url', '%allaboutdogfood%').not_.is_('kcal_per_100g', 'null').execute()
        
        uk_total = supabase.table('foods_canonical').select(
            '*', count='exact'
        ).like('product_url', '%allaboutdogfood%').execute()
        
        print(f"\nUK Products nutritional coverage:")
        print(f"  Total UK products: {uk_total.count}")
        print(f"  With macros (protein): {uk_with_protein.count} ({uk_with_protein.count/uk_total.count*100:.1f}%)")
        print(f"  With calories: {uk_with_calories.count} ({uk_with_calories.count/uk_total.count*100:.1f}%)")
        
        # Check overall database
        total_with_protein = supabase.table('foods_canonical').select(
            '*', count='exact'
        ).not_.is_('protein_percent', 'null').execute()
        
        total_all = supabase.table('foods_canonical').select('*', count='exact').execute()
        
        print(f"\nOverall database nutritional coverage:")
        print(f"  Total products: {total_all.count}")
        print(f"  With macros: {total_with_protein.count} ({total_with_protein.count/total_all.count*100:.1f}%)")

def main():
    importer = AADFNutritionImporter()
    importer.import_nutrition_data()
    print("\n✅ AADF nutritional data import completed!")

if __name__ == "__main__":
    main()