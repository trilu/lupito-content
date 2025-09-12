#!/usr/bin/env python3
"""
Process scraped Zooplus data from GCS and update database
Separate script to process saved scraping results
"""

import os
import json
import re
from typing import Dict, List
from dotenv import load_dotenv
from google.cloud import storage
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content")

class GCSDataProcessor:
    def __init__(self, gcs_folder: str):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(GCS_BUCKET)
        self.gcs_folder = gcs_folder
        
        self.stats = {
            'files_processed': 0,
            'products_updated': 0,
            'ingredients_added': 0,
            'nutrition_added': 0,
            'errors': 0
        }
    
    def list_scraped_files(self) -> List[str]:
        """List all JSON files in the GCS folder"""
        
        print(f"Listing files in gs://{GCS_BUCKET}/{self.gcs_folder}/")
        
        blobs = self.bucket.list_blobs(prefix=self.gcs_folder)
        files = [blob.name for blob in blobs if blob.name.endswith('.json')]
        
        print(f"Found {len(files)} files to process")
        return files
    
    def download_and_process(self, file_path: str) -> bool:
        """Download and process a single file"""
        
        try:
            # Download file
            blob = self.bucket.blob(file_path)
            content = blob.download_as_text()
            data = json.loads(content)
            
            self.stats['files_processed'] += 1
            
            # Skip if error in scraping
            if 'error' in data:
                print(f"  Skipping - had error: {data['error']}")
                return False
            
            # Process the data
            return self.update_database(data)
            
        except Exception as e:
            print(f"  Error processing file: {str(e)[:100]}")
            self.stats['errors'] += 1
            return False
    
    def tokenize_ingredients(self, text: str) -> List[str]:
        """Tokenize ingredients text"""
        
        # Remove percentages and parentheses
        text = re.sub(r'\([^)]*\)', '', text)
        text = re.sub(r'\d+\.?\d*\s*%', '', text)
        
        # Split and clean
        tokens = []
        for part in re.split(r'[,;]', text)[:50]:
            part = re.sub(r'[^\w\s-]', ' ', part)
            part = ' '.join(part.split()).strip().lower()
            if part and 2 < len(part) < 50:
                if part not in ['ingredients', 'composition', 'analytical constituents']:
                    tokens.append(part)
        
        return tokens
    
    def update_database(self, data: Dict) -> bool:
        """Update database with processed data"""
        
        product_key = data.get('product_key')
        if not product_key:
            print(f"  No product_key in data")
            return False
        
        update_data = {}
        
        # Process ingredients
        if 'ingredients_raw' in data:
            update_data['ingredients_raw'] = data['ingredients_raw'][:2000]
            update_data['ingredients_source'] = 'site'
            
            # Tokenize
            tokens = self.tokenize_ingredients(data['ingredients_raw'])
            if tokens:
                update_data['ingredients_tokens'] = tokens
            
            self.stats['ingredients_added'] += 1
        
        # Process nutrition
        if 'nutrition' in data:
            nutrition = data['nutrition']
            
            if 'protein_percent' in nutrition:
                update_data['protein_percent'] = nutrition['protein_percent']
                update_data['macros_source'] = 'site'
            
            if 'fat_percent' in nutrition:
                update_data['fat_percent'] = nutrition['fat_percent']
                update_data['macros_source'] = 'site'
            
            if 'fiber_percent' in nutrition:
                update_data['fiber_percent'] = nutrition['fiber_percent']
            
            if 'ash_percent' in nutrition:
                update_data['ash_percent'] = nutrition['ash_percent']
            
            if 'moisture_percent' in nutrition:
                update_data['moisture_percent'] = nutrition['moisture_percent']
            
            self.stats['nutrition_added'] += 1
        
        # Update database
        if update_data:
            try:
                self.supabase.table('foods_canonical').update(
                    update_data
                ).eq('product_key', product_key).execute()
                
                self.stats['products_updated'] += 1
                return True
                
            except Exception as e:
                print(f"  Database error: {str(e)[:100]}")
                self.stats['errors'] += 1
                return False
        
        return False
    
    def process_all(self):
        """Process all files in the folder"""
        
        print("\nPROCESSING GCS SCRAPED DATA")
        print("="*60)
        
        files = self.list_scraped_files()
        
        if not files:
            print("No files to process")
            return
        
        print(f"\nProcessing {len(files)} files...")
        print("-"*60)
        
        for i, file_path in enumerate(files, 1):
            # Extract product key from filename
            filename = file_path.split('/')[-1].replace('.json', '')
            print(f"\n[{i}/{len(files)}] {filename}")
            
            # Process file
            if self.download_and_process(file_path):
                print(f"  ✓ Updated database")
            else:
                print(f"  ✗ Not updated")
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Print processing summary"""
        
        print("\n" + "="*60)
        print("PROCESSING SUMMARY")
        print("="*60)
        print(f"Files processed: {self.stats['files_processed']}")
        print(f"Products updated: {self.stats['products_updated']}")
        print(f"Ingredients added: {self.stats['ingredients_added']}")
        print(f"Nutrition added: {self.stats['nutrition_added']}")
        print(f"Errors: {self.stats['errors']}")
        
        if self.stats['files_processed'] > 0:
            success_rate = self.stats['products_updated'] / self.stats['files_processed'] * 100
            print(f"\nSuccess rate: {success_rate:.1f}%")

def main():
    """Process scraped data from GCS"""
    
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python process_gcs_scraped_data.py <gcs_folder>")
        print("Example: python process_gcs_scraped_data.py scraped/zooplus/20241212_143000")
        
        # List recent folders
        print("\nRecent scraping folders:")
        storage_client = storage.Client()
        bucket = storage_client.bucket(GCS_BUCKET)
        
        prefixes = set()
        for blob in bucket.list_blobs(prefix="scraped/zooplus/", delimiter="/"):
            if blob.name.endswith('.json'):
                folder = '/'.join(blob.name.split('/')[:-1])
                prefixes.add(folder)
        
        for folder in sorted(prefixes)[-5:]:
            print(f"  {folder}")
        
        return
    
    gcs_folder = sys.argv[1]
    processor = GCSDataProcessor(gcs_folder)
    processor.process_all()

if __name__ == "__main__":
    main()