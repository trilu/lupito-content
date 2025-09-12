#!/usr/bin/env python3
"""
Import previously harvested manufacturer data from CSV files
"""

import os
import csv
import json
import re
from pathlib import Path
from typing import Dict, List, Optional
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_KEY')
)

class HarvestedDataImporter:
    def __init__(self):
        self.supabase = supabase
        self.stats = {
            'files_processed': 0,
            'products_matched': 0,
            'products_updated': 0,
            'products_not_found': 0,
            'errors': []
        }
    
    def normalize_product_name(self, name: str) -> str:
        """Normalize product name for matching"""
        if not name:
            return ""
        
        # Convert to lowercase
        normalized = name.lower()
        
        # Remove special characters but keep spaces
        normalized = re.sub(r'[^\w\s]', '', normalized)
        
        # Remove extra spaces
        normalized = ' '.join(normalized.split())
        
        return normalized
    
    def find_matching_product(self, brand: str, product_name: str) -> Optional[Dict]:
        """Find matching product in database"""
        
        # Try exact match first
        response = supabase.table('foods_canonical').select('*').eq('brand', brand).eq('product_name', product_name).execute()
        
        if response.data:
            return response.data[0]
        
        # Try normalized match
        normalized_name = self.normalize_product_name(product_name)
        
        # Get all products for this brand
        response = supabase.table('foods_canonical').select('*').eq('brand', brand).execute()
        
        for product in response.data:
            db_normalized = self.normalize_product_name(product.get('product_name', ''))
            
            # Check for close match
            if db_normalized == normalized_name:
                return product
            
            # Check if one contains the other (partial match)
            if len(normalized_name) > 10 and len(db_normalized) > 10:
                if normalized_name in db_normalized or db_normalized in normalized_name:
                    # Calculate similarity
                    common = len(set(normalized_name.split()) & set(db_normalized.split()))
                    total = len(set(normalized_name.split()) | set(db_normalized.split()))
                    
                    if total > 0 and common / total > 0.7:  # 70% word overlap
                        return product
        
        return None
    
    def import_csv_file(self, csv_path: str):
        """Import data from a CSV file"""
        
        print(f"\n=== IMPORTING {csv_path} ===")
        
        updates = []
        not_found = []
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                brand = row.get('brand', '').strip()
                product_name = row.get('product_name', '').strip()
                
                if not brand or not product_name:
                    continue
                
                # Find matching product in database
                match = self.find_matching_product(brand, product_name)
                
                if not match:
                    not_found.append(f"{brand} - {product_name}")
                    self.stats['products_not_found'] += 1
                    continue
                
                # Prepare update data
                update_data = {}
                
                # Import ingredients
                if row.get('ingredients') and not match.get('ingredients_raw'):
                    update_data['ingredients_raw'] = row['ingredients']
                    update_data['ingredients_source'] = 'manufacturer'
                    
                    # Parse tokens if available
                    if row.get('ingredients_tokens'):
                        try:
                            tokens = json.loads(row['ingredients_tokens'])
                            update_data['ingredients_tokens'] = tokens
                        except:
                            pass
                
                # Import nutritional data
                nutrition_fields = [
                    ('protein_percent', 'protein_percent'),
                    ('fat_percent', 'fat_percent'),
                    ('fiber_percent', 'fiber_percent'),
                    ('ash_percent', 'ash_percent'),
                    ('moisture_percent', 'moisture_percent'),
                    ('kcal_per_100g', 'kcal_per_100g')
                ]
                
                for csv_field, db_field in nutrition_fields:
                    if row.get(csv_field) and not match.get(db_field):
                        try:
                            value = float(row[csv_field])
                            update_data[db_field] = value
                        except:
                            pass
                
                # Import URL if missing
                if row.get('url') and not match.get('product_url'):
                    update_data['product_url'] = row['url']
                
                # Import price if available
                if row.get('price_per_kg') and not match.get('price_per_kg'):
                    try:
                        price = float(row['price_per_kg'])
                        update_data['price_per_kg'] = price
                        update_data['price_bucket'] = row.get('price_bucket')
                    except:
                        pass
                
                # Import form and life_stage if missing
                if row.get('form') and not match.get('form'):
                    update_data['form'] = row['form']
                
                if row.get('life_stage') and not match.get('life_stage'):
                    update_data['life_stage'] = row['life_stage']
                
                if update_data:
                    updates.append({
                        'product_key': match['product_key'],
                        'updates': update_data,
                        'product_name': product_name
                    })
                    self.stats['products_matched'] += 1
        
        # Apply updates
        if updates:
            print(f"\nApplying {len(updates)} updates...")
            
            for update in updates:
                try:
                    response = supabase.table('foods_canonical').update(
                        update['updates']
                    ).eq('product_key', update['product_key']).execute()
                    
                    self.stats['products_updated'] += 1
                    print(f"  ✅ Updated: {update['product_name']}")
                    
                except Exception as e:
                    print(f"  ❌ Failed to update {update['product_name']}: {e}")
                    self.stats['errors'].append(str(e))
        
        if not_found:
            print(f"\n⚠️  {len(not_found)} products not found in database:")
            for product in not_found[:5]:
                print(f"  - {product}")
            if len(not_found) > 5:
                print(f"  ... and {len(not_found) - 5} more")
        
        self.stats['files_processed'] += 1
    
    def import_all_harvested_data(self):
        """Import all available harvested data"""
        
        # Look for CSV files in known locations
        csv_patterns = [
            'reports/MANUF/PRODUCTION/*_fixed_*.csv',
            'reports/MANUF/PILOT/harvests/*.csv',
            'data/manufacturers/*.csv'
        ]
        
        csv_files = []
        for pattern in csv_patterns:
            csv_files.extend(Path('.').glob(pattern))
        
        # Also check for specific brand files
        brands = ['bozita', 'belcando', 'briantos', 'burns', 'brit']
        for brand in brands:
            csv_files.extend(Path('.').glob(f'**/*{brand}*.csv'))
        
        # Remove duplicates and sort
        csv_files = sorted(set(csv_files))
        
        print("="*60)
        print("IMPORTING HARVESTED MANUFACTURER DATA")
        print("="*60)
        print(f"Found {len(csv_files)} CSV files to process")
        
        for csv_file in csv_files:
            # Skip if not a product data file
            if 'audit' in str(csv_file) or 'summary' in str(csv_file):
                continue
            
            self.import_csv_file(str(csv_file))
        
        # Print final summary
        print("\n" + "="*60)
        print("IMPORT SUMMARY")
        print("="*60)
        print(f"Files processed: {self.stats['files_processed']}")
        print(f"Products matched: {self.stats['products_matched']}")
        print(f"Products updated: {self.stats['products_updated']}")
        print(f"Products not found: {self.stats['products_not_found']}")
        print(f"Errors: {len(self.stats['errors'])}")

def main():
    import sys
    
    importer = HarvestedDataImporter()
    
    if len(sys.argv) > 1:
        # Import specific file
        csv_file = sys.argv[1]
        if os.path.exists(csv_file):
            importer.import_csv_file(csv_file)
        else:
            print(f"File not found: {csv_file}")
    else:
        # Import all available data
        importer.import_all_harvested_data()
    
    print("\n✅ Import completed!")

if __name__ == "__main__":
    main()