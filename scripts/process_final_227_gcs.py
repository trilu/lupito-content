#!/usr/bin/env python3
"""
Process final 227 scraped data from GCS and update database
Reads from final_227_* folders and updates Supabase
"""

import os
import json
import re
from typing import Dict, List
from datetime import datetime
from dotenv import load_dotenv
from google.cloud import storage
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")

class Final227Processor:
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(GCS_BUCKET)
        
        self.stats = {
            'folders_processed': 0,
            'files_processed': 0,
            'products_updated': 0,
            'ingredients_added': 0,
            'nutrition_added': 0,
            'errors': 0,
            'patterns_found': {}
        }
        
        # Load processed folders
        self.processed_folders = self.load_processed_folders()
    
    def load_processed_folders(self) -> set:
        """Load list of already processed folders"""
        processed_file = "scripts/processed_folders.txt"
        
        if os.path.exists(processed_file):
            with open(processed_file, 'r') as f:
                return set(line.strip() for line in f if line.strip())
        return set()
    
    def save_processed_folder(self, folder: str):
        """Mark a folder as processed"""
        processed_file = "scripts/processed_folders.txt"
        
        with open(processed_file, 'a') as f:
            f.write(f"{folder}\n")
        
        self.processed_folders.add(folder)
    
    def find_final_227_folders(self) -> List[str]:
        """Find all final_227_* folders in GCS"""
        prefix = "scraped/zooplus/final_227_"
        
        blobs = self.bucket.list_blobs(prefix=prefix)
        
        folders = set()
        for blob in blobs:
            # Extract folder path
            if '/' in blob.name:
                folder = '/'.join(blob.name.split('/')[:3])
                folders.add(folder)
        
        # Filter out already processed folders
        new_folders = [f for f in folders if f not in self.processed_folders]
        
        return sorted(new_folders)
    
    def list_files_in_folder(self, folder: str) -> List[str]:
        """List all JSON files in a folder"""
        prefix = f"{folder}/"
        
        blobs = self.bucket.list_blobs(prefix=prefix)
        files = [blob.name for blob in blobs if blob.name.endswith('.json')]
        
        return files
    
    def download_and_process(self, file_path: str) -> bool:
        """Download and process a single file"""
        try:
            # Download file
            blob = self.bucket.blob(file_path)
            content = blob.download_as_text()
            data = json.loads(content)
            
            self.stats['files_processed'] += 1
            
            # Track pattern usage
            if 'pattern_used' in data:
                pattern = data['pattern_used']
                self.stats['patterns_found'][pattern] = self.stats['patterns_found'].get(pattern, 0) + 1
            
            # Skip if error in scraping
            if 'error' in data:
                print(f"  ⚠️ Skipping {data.get('product_key', 'unknown')} - had error: {data['error'][:50]}")
                return False
            
            # Process the data
            return self.update_database(data)
            
        except Exception as e:
            print(f"  ❌ Error processing {file_path}: {str(e)[:100]}")
            self.stats['errors'] += 1
            return False
    
    def tokenize_ingredients(self, text: str) -> List[str]:
        """Tokenize ingredients text for database storage"""
        
        # Remove percentages and parentheses
        text = re.sub(r'\([^)]*\)', '', text)
        text = re.sub(r'\d+\.?\d*\s*%', '', text)
        
        # Split and clean
        tokens = []
        for part in re.split(r'[,;]', text)[:50]:  # Limit to 50 tokens
            part = re.sub(r'[^\w\s-]', ' ', part)
            part = ' '.join(part.split()).strip().lower()
            
            # Filter out common non-ingredient words
            skip_words = ['ingredients', 'composition', 'analytical', 'constituents', 
                         'additives', 'nutritional', 'go to', 'per kg']
            
            if part and 2 < len(part) < 50:
                if not any(skip in part for skip in skip_words):
                    tokens.append(part)
        
        return tokens
    
    def update_database(self, data: Dict) -> bool:
        """Update database with processed data"""
        
        product_key = data.get('product_key')
        if not product_key:
            print(f"  ⚠️ No product_key in data")
            return False
        
        update_data = {}
        
        # Process ingredients
        if 'ingredients_raw' in data:
            ingredients = data['ingredients_raw'][:2000]  # Limit to 2000 chars
            update_data['ingredients_raw'] = ingredients
            update_data['ingredients_source'] = 'site'
            
            # Tokenize ingredients
            tokens = self.tokenize_ingredients(ingredients)
            if tokens:
                update_data['ingredients_tokens'] = tokens
            
            self.stats['ingredients_added'] += 1
            
            print(f"  ✅ {product_key}: Found ingredients ({data.get('pattern_used', 'unknown')})")
        
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
            
            print(f"     📊 Also found nutrition data ({len(nutrition)} values)")
        
        # Update database
        if update_data:
            try:
                response = self.supabase.table('foods_canonical').update(
                    update_data
                ).eq('product_key', product_key).execute()
                
                self.stats['products_updated'] += 1
                return True
                
            except Exception as e:
                print(f"  ❌ Database error for {product_key}: {str(e)[:100]}")
                self.stats['errors'] += 1
                return False
        
        return False
    
    def process_folder(self, folder: str):
        """Process all files in a folder"""
        print(f"\n📁 Processing folder: {folder}")
        
        files = self.list_files_in_folder(folder)
        print(f"   Found {len(files)} files to process")
        
        if not files:
            print("   ⚠️ No files found in folder")
            return
        
        for file_path in files:
            self.download_and_process(file_path)
        
        # Mark folder as processed
        self.save_processed_folder(folder)
        self.stats['folders_processed'] += 1
        
        print(f"   ✅ Folder processing complete")
    
    def run(self):
        """Main processing loop"""
        print("=" * 60)
        print("🔄 FINAL 227 GCS DATA PROCESSOR")
        print("=" * 60)
        print(f"GCS Bucket: {GCS_BUCKET}")
        print(f"Database: {SUPABASE_URL}")
        print()
        
        # Find folders to process
        folders = self.find_final_227_folders()
        
        if not folders:
            print("ℹ️ No new final_227_* folders to process")
            print(f"   Already processed: {len(self.processed_folders)} folders")
            return
        
        print(f"📂 Found {len(folders)} new folders to process")
        
        # Process each folder
        for folder in folders:
            self.process_folder(folder)
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print processing summary"""
        print("\n" + "=" * 60)
        print("📊 PROCESSING SUMMARY")
        print("=" * 60)
        
        print(f"Folders processed: {self.stats['folders_processed']}")
        print(f"Files processed: {self.stats['files_processed']}")
        print(f"Products updated: {self.stats['products_updated']}")
        print(f"Ingredients added: {self.stats['ingredients_added']}")
        print(f"Nutrition added: {self.stats['nutrition_added']}")
        print(f"Errors: {self.stats['errors']}")
        
        if self.stats['files_processed'] > 0:
            success_rate = (self.stats['products_updated'] / self.stats['files_processed']) * 100
            print(f"\nSuccess rate: {success_rate:.1f}%")
        
        if self.stats['patterns_found']:
            print("\n📋 PATTERNS USED:")
            for pattern, count in sorted(self.stats['patterns_found'].items(), 
                                        key=lambda x: x[1], reverse=True):
                print(f"  {pattern}: {count} products")
        
        print("\n✅ Processing complete!")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

def main():
    """Main entry point"""
    processor = Final227Processor()
    processor.run()

if __name__ == "__main__":
    main()