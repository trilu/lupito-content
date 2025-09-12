#!/usr/bin/env python3
"""
Continuous Processor - Automatically processes all new scraped files
Runs continuously, checking for new files every few minutes
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import Set
from process_gcs_scraped_data import GCSDataProcessor
from dotenv import load_dotenv
from supabase import create_client
from google.cloud import storage

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")

class ContinuousProcessor:
    def __init__(self):
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(GCS_BUCKET)
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Track processed folders
        self.processed_folders_file = 'scripts/processed_folders.txt'
        self.processed_folders = self.load_processed_folders()
        
        # Queue for failures
        self.queue_file = 'scripts/rescrape_queue.txt'
        
        # Stats
        self.session_stats = {
            'total_processed': 0,
            'total_updated': 0,
            'total_ingredients': 0,
            'total_nutrition': 0,
            'total_failures': 0
        }
        
        print("🤖 CONTINUOUS PROCESSOR STARTED")
        print("=" * 60)
        print(f"   Check interval: Every 2 minutes")
        print(f"   Processing all new scraped files automatically")
        print(f"   Failures will be queued for rescraping")
        print("=" * 60)
    
    def load_processed_folders(self) -> Set[str]:
        """Load list of already processed folders"""
        if os.path.exists(self.processed_folders_file):
            with open(self.processed_folders_file, 'r') as f:
                return set(line.strip() for line in f if line.strip())
        return set()
    
    def save_processed_folder(self, folder: str):
        """Mark folder as processed"""
        self.processed_folders.add(folder)
        with open(self.processed_folders_file, 'a') as f:
            f.write(f"{folder}\n")
    
    def get_unprocessed_folders(self):
        """Get list of folders that haven't been processed yet"""
        # Get all folders from scraped/zooplus/
        prefix = "scraped/zooplus/"
        blobs = self.bucket.list_blobs(prefix=prefix)
        
        folders = set()
        for blob in blobs:
            if '/' in blob.name and blob.name.endswith('.json'):
                folder = '/'.join(blob.name.split('/')[:3])
                folders.add(folder)
        
        # Filter out already processed
        unprocessed = folders - self.processed_folders
        
        # Sort by timestamp (oldest first)
        return sorted(list(unprocessed))
    
    def process_folder(self, folder: str) -> dict:
        """Process all files in a folder"""
        print(f"\n📁 Processing: {folder.split('/')[-1]}")
        
        processor = GCSDataProcessor(folder)
        files = processor.list_scraped_files()
        
        if not files:
            print(f"   Empty folder")
            return {'processed': 0, 'updated': 0, 'failures': 0}
        
        folder_stats = {
            'processed': 0,
            'updated': 0,
            'ingredients': 0,
            'nutrition': 0,
            'failures': 0
        }
        
        failed_products = []
        
        for file_path in files:
            product_name = os.path.basename(file_path).replace('.json', '')
            
            # Check for errors in file
            try:
                blob = self.bucket.blob(file_path)
                content = blob.download_as_text()
                data = json.loads(content)
                
                if 'error' in data:
                    folder_stats['failures'] += 1
                    
                    # Add to rescrape queue
                    if data.get('url'):
                        failed_products.append({
                            'url': data['url'],
                            'product_key': data.get('product_key', product_name.replace('_', '|'))
                        })
                    continue
                
                # Track what data we have
                if 'ingredients_raw' in data and data['ingredients_raw']:
                    folder_stats['ingredients'] += 1
                if 'nutrition' in data and data['nutrition']:
                    folder_stats['nutrition'] += 1
                    
            except Exception as e:
                continue
            
            # Process the file
            success = processor.download_and_process(file_path)
            folder_stats['processed'] += 1
            
            if success:
                folder_stats['updated'] += 1
        
        print(f"   ✅ {folder_stats['updated']}/{len(files)} updated (🥘 {folder_stats['ingredients']} 🍖 {folder_stats['nutrition']})")
        
        # Queue failures
        if failed_products:
            self.queue_failures(failed_products)
            print(f"   ⚠️  {len(failed_products)} failures queued for rescraping")
        
        # Update session stats
        self.session_stats['total_processed'] += folder_stats['processed']
        self.session_stats['total_updated'] += folder_stats['updated']
        self.session_stats['total_ingredients'] += processor.stats['ingredients_added']
        self.session_stats['total_nutrition'] += processor.stats['nutrition_added']
        self.session_stats['total_failures'] += folder_stats['failures']
        
        return folder_stats
    
    def queue_failures(self, failed_products):
        """Add failures to rescrape queue"""
        # Read existing queue
        existing_urls = set()
        if os.path.exists(self.queue_file):
            with open(self.queue_file, 'r') as f:
                for line in f:
                    if '|' in line:
                        url = line.split('|')[0].strip()
                        existing_urls.add(url)
        
        # Append new failures
        added = 0
        with open(self.queue_file, 'a') as f:
            for product in failed_products:
                url = product['url']
                if url not in existing_urls:
                    f.write(f"{url}|{product['product_key']}\n")
                    existing_urls.add(url)
                    added += 1
        
        return added
    
    def show_status(self):
        """Show current database coverage"""
        try:
            total = self.supabase.table('foods_canonical').select('*', count='exact').execute().count
            ingredients = self.supabase.table('foods_canonical').select('*', count='exact')\
                .not_.is_('ingredients_raw', 'null').execute().count
            
            print(f"\n📊 DATABASE STATUS:")
            print(f"   Ingredients coverage: {ingredients:,}/{total:,} ({ingredients/total*100:.1f}%)")
            print(f"   Gap to 95%: {int(total * 0.95) - ingredients:,} products")
            
        except Exception as e:
            print(f"   Error checking status: {e}")
    
    def run_continuous(self):
        """Main continuous processing loop"""
        check_interval = 120  # 2 minutes
        last_status_time = datetime.now()
        
        while True:
            # Get unprocessed folders
            unprocessed = self.get_unprocessed_folders()
            
            if unprocessed:
                print(f"\n🔍 Found {len(unprocessed)} unprocessed folders")
                
                # Process each folder
                for folder in unprocessed[:10]:  # Process up to 10 at a time
                    self.process_folder(folder)
                    self.save_processed_folder(folder)
                
                # Show session stats
                print(f"\n📈 SESSION STATS:")
                print(f"   Files processed: {self.session_stats['total_processed']}")
                print(f"   Products updated: {self.session_stats['total_updated']}")
                print(f"   Ingredients added: {self.session_stats['total_ingredients']}")
                print(f"   Nutrition added: {self.session_stats['total_nutrition']}")
                print(f"   Failures queued: {self.session_stats['total_failures']}")
            else:
                print(f"\n⏳ No new folders to process")
            
            # Show database status every 10 minutes
            if datetime.now() - last_status_time > timedelta(minutes=10):
                self.show_status()
                last_status_time = datetime.now()
            
            # Check for 95% completion
            try:
                total = self.supabase.table('foods_canonical').select('*', count='exact').execute().count
                ingredients = self.supabase.table('foods_canonical').select('*', count='exact')\
                    .not_.is_('ingredients_raw', 'null').execute().count
                
                if ingredients / total >= 0.95:
                    print("\n🎉 95% COVERAGE ACHIEVED!")
                    print(f"   Final coverage: {ingredients:,}/{total:,} ({ingredients/total*100:.1f}%)")
                    break
            except:
                pass
            
            # Wait before next check
            print(f"\n💤 Waiting {check_interval} seconds before next check...")
            time.sleep(check_interval)

def main():
    processor = ContinuousProcessor()
    
    try:
        processor.run_continuous()
    except KeyboardInterrupt:
        print("\n\n🛑 Continuous processor stopped by user")
        print(f"   Total processed: {processor.session_stats['total_processed']} files")
        print(f"   Total updated: {processor.session_stats['total_updated']} products")

if __name__ == "__main__":
    main()