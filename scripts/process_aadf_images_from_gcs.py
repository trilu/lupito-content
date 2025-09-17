#!/usr/bin/env python3
"""
Process AADF Images from GCS to Database
Following the proven Zooplus pattern: GCS → Database
"""

import os
import json
from datetime import datetime
from typing import Dict, List
from google.cloud import storage
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Environment setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")

# Set up GCS authentication
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/sergiubiris/Desktop/lupito-content/secrets/gcp-sa.json'

class AADFImageProcessor:
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(GCS_BUCKET)
        
        self.stats = {
            'files_processed': 0,
            'images_found': 0,
            'db_updated': 0,
            'errors': 0,
            'already_processed': 0
        }
    
    def get_gcs_files(self, prefix: str = "scraped/aadf_images/") -> List[str]:
        """Get list of AADF image files from GCS"""
        blobs = self.bucket.list_blobs(prefix=prefix)
        files = []
        for blob in blobs:
            if blob.name.endswith('.json'):
                files.append(blob.name)
        return files
    
    def process_file(self, file_path: str) -> bool:
        """Process single GCS file and update database"""
        try:
            # Download and parse JSON
            blob = self.bucket.blob(file_path)
            content = blob.download_as_text()
            data = json.loads(content)
            
            self.stats['files_processed'] += 1
            
            # Check if image was found
            if not data.get('image_url'):
                return False
            
            self.stats['images_found'] += 1
            
            # Update database
            try:
                response = self.supabase.table('foods_canonical')\
                    .update({'image_url': data['image_url']})\
                    .eq('product_key', data['product_key'])\
                    .execute()
                
                if response.data:
                    self.stats['db_updated'] += 1
                    return True
            except Exception as e:
                print(f"DB update failed for {data['product_key']}: {e}")
                self.stats['errors'] += 1
                
        except Exception as e:
            print(f"Failed to process {file_path}: {e}")
            self.stats['errors'] += 1
        
        return False
    
    def check_existing_images(self):
        """Check how many AADF products already have images"""
        try:
            response = self.supabase.table('foods_canonical')\
                .select('product_key', count='exact')\
                .ilike('product_url', '%allaboutdogfood%')\
                .not_.is_('image_url', 'null')\
                .execute()
            
            return response.count
        except:
            return 0
    
    def process_all(self, session_filter: str = None):
        """Process all AADF image files from GCS"""
        print("🔄 AADF IMAGE PROCESSOR")
        print("=" * 60)
        
        # Check existing images
        existing = self.check_existing_images()
        print(f"📊 Existing AADF products with images: {existing}")
        
        # Get files to process
        prefix = "scraped/aadf_images/"
        if session_filter:
            prefix += session_filter
        
        files = self.get_gcs_files(prefix)
        print(f"📁 Found {len(files)} files in GCS to process")
        
        if not files:
            print("No files to process")
            return
        
        # Process each file
        print("\nProcessing files...")
        for i, file_path in enumerate(files):
            if (i + 1) % 100 == 0:
                print(f"Progress: {i+1}/{len(files)} files processed")
            
            self.process_file(file_path)
        
        # Final stats
        print("\n" + "=" * 60)
        print("✅ PROCESSING COMPLETE")
        print(f"📄 Files processed: {self.stats['files_processed']}")
        print(f"🖼️ Images found: {self.stats['images_found']}")
        print(f"💾 Database updated: {self.stats['db_updated']}")
        print(f"❌ Errors: {self.stats['errors']}")
        
        # Check final coverage
        final = self.check_existing_images()
        print(f"\n📈 Coverage increased from {existing} to {final} (+{final - existing})")
        
        # Calculate success rate
        if self.stats['files_processed'] > 0:
            success_rate = (self.stats['db_updated'] / self.stats['files_processed']) * 100
            print(f"Success rate: {success_rate:.1f}%")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Process AADF images from GCS to database')
    parser.add_argument('--session', help='Filter by session ID (optional)')
    args = parser.parse_args()
    
    processor = AADFImageProcessor()
    processor.process_all(args.session)

if __name__ == "__main__":
    main()