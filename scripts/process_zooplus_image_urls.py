#!/usr/bin/env python3
"""
Process Zooplus Image URLs
Reads extracted image URLs from GCS and updates database
"""

import os
import json
import time
from datetime import datetime
from typing import List, Dict
from dotenv import load_dotenv
from google.cloud import storage
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")

class ZooplusImageProcessor:
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(GCS_BUCKET)

        self.stats = {
            'files_processed': 0,
            'urls_extracted': 0,
            'database_updates': 0,
            'errors': 0,
            'skipped': 0
        }

        print("🔄 ZOOPLUS IMAGE URL PROCESSOR STARTED")
        print(f"Processing GCS bucket: gs://{GCS_BUCKET}/")

    def get_latest_session_folders(self) -> List[str]:
        """Get latest zooplus_images session folders from GCS"""
        try:
            blobs = self.bucket.list_blobs(prefix="scraped/zooplus_images/")

            # Extract unique session folders
            folders = set()
            for blob in blobs:
                path_parts = blob.name.split('/')
                if len(path_parts) >= 4:  # scraped/zooplus_images/20250916_123456_session/file.json
                    folder = '/'.join(path_parts[:3])  # scraped/zooplus_images/20250916_123456_session
                    folders.add(folder)

            # Sort by timestamp (newest first)
            sorted_folders = sorted(list(folders), reverse=True)

            print(f"Found {len(sorted_folders)} session folders:")
            for folder in sorted_folders[:3]:  # Show latest 3
                print(f"  {folder}")

            return sorted_folders

        except Exception as e:
            print(f"Error listing GCS folders: {e}")
            return []

    def process_session_folder(self, folder_path: str) -> Dict:
        """Process all JSON files in a session folder"""
        session_stats = {'processed': 0, 'updated': 0, 'errors': 0, 'skipped': 0}

        print(f"\n📁 Processing folder: {folder_path}")

        try:
            blobs = self.bucket.list_blobs(prefix=f"{folder_path}/")
            json_files = [blob for blob in blobs if blob.name.endswith('.json')]

            print(f"Found {len(json_files)} JSON files to process")

            for i, blob in enumerate(json_files, 1):
                if i % 50 == 0:
                    print(f"  Progress: {i}/{len(json_files)} files processed")

                try:
                    # Download and parse JSON
                    content = blob.download_as_text()
                    data = json.loads(content)

                    session_stats['processed'] += 1
                    self.stats['files_processed'] += 1

                    # Skip if error or no image URL
                    if 'error' in data or 'image_url' not in data:
                        session_stats['skipped'] += 1
                        self.stats['skipped'] += 1
                        continue

                    # Update database
                    success = self.update_database(data)
                    if success:
                        session_stats['updated'] += 1
                        self.stats['database_updates'] += 1
                        self.stats['urls_extracted'] += 1
                    else:
                        session_stats['errors'] += 1
                        self.stats['errors'] += 1

                except Exception as e:
                    session_stats['errors'] += 1
                    self.stats['errors'] += 1
                    print(f"  Error processing {blob.name}: {str(e)[:100]}")

            print(f"✅ Session complete: {session_stats['updated']} URLs processed")

        except Exception as e:
            print(f"Error processing session folder {folder_path}: {e}")

        return session_stats

    def update_database(self, data: Dict) -> bool:
        """Update foods_canonical with image URL"""
        try:
            product_key = data['product_key']
            image_url = data['image_url']

            # Update the database record
            result = self.supabase.table('foods_canonical')\
                .update({'image_url': image_url})\
                .eq('product_key', product_key)\
                .execute()

            return len(result.data) > 0

        except Exception as e:
            print(f"Database update error for {data.get('product_key', 'unknown')}: {e}")
            return False

    def check_coverage_improvement(self):
        """Check current Zooplus coverage after processing"""
        try:
            # Get Zooplus coverage stats
            response = self.supabase.table('foods_canonical')\
                .select('product_key, image_url')\
                .ilike('product_url', '%zooplus%')\
                .execute()

            total = len(response.data)
            with_images = sum(1 for p in response.data if p['image_url'])
            coverage = (with_images / total * 100) if total > 0 else 0

            print(f"\n📊 CURRENT ZOOPLUS COVERAGE")
            print(f"Total products: {total}")
            print(f"With images: {with_images}")
            print(f"Coverage: {coverage:.1f}%")

            return {'total': total, 'with_images': with_images, 'coverage': coverage}

        except Exception as e:
            print(f"Error checking coverage: {e}")
            return None

    def run(self, session_limit: int = 3):
        """Process latest session folders"""
        start_time = datetime.now()

        # Get latest session folders
        folders = self.get_latest_session_folders()
        if not folders:
            print("❌ No session folders found")
            return

        # Process latest sessions (limit for safety)
        folders_to_process = folders[:session_limit]
        print(f"\n🎯 Processing {len(folders_to_process)} most recent sessions")

        for folder in folders_to_process:
            session_stats = self.process_session_folder(folder)
            time.sleep(1)  # Brief pause between sessions

        # Final summary
        elapsed = datetime.now() - start_time
        print(f"\n" + "=" * 60)
        print("ZOOPLUS IMAGE URL PROCESSING COMPLETE")
        print("=" * 60)
        print(f"Duration: {elapsed}")
        print(f"Files processed: {self.stats['files_processed']}")
        print(f"URLs extracted: {self.stats['urls_extracted']}")
        print(f"Database updates: {self.stats['database_updates']}")
        print(f"Errors: {self.stats['errors']}")
        print(f"Skipped: {self.stats['skipped']}")

        if self.stats['files_processed'] > 0:
            success_rate = self.stats['database_updates'] / self.stats['files_processed'] * 100
            print(f"Success rate: {success_rate:.1f}%")

        # Check final coverage
        self.check_coverage_improvement()

        print(f"\n✨ Next step: Run image downloader if coverage improved significantly")

def main():
    processor = ZooplusImageProcessor()

    # Ask user confirmation
    print("This will process extracted image URLs from GCS and update the database.")
    choice = input("Continue? (y/n): ").lower().strip()

    if choice != 'y':
        print("Operation cancelled")
        return

    processor.run()

if __name__ == "__main__":
    main()