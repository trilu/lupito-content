#!/usr/bin/env python3
"""
Monitor Zooplus Image Scraping Progress
Real-time progress tracking for Zooplus image acquisition
"""

import os
import time
from datetime import datetime
from typing import Dict
from dotenv import load_dotenv
from supabase import create_client
from google.cloud import storage

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")

class ZooplusImageMonitor:
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(GCS_BUCKET)

        print("=" * 60)
        print("ZOOPLUS IMAGE SCRAPING PROGRESS MONITOR")
        print("=" * 60)

    def get_current_coverage(self) -> Dict:
        """Get current Zooplus coverage stats"""
        try:
            # Overall Zooplus stats
            response = self.supabase.table('foods_canonical')\
                .select('product_key, image_url, source')\
                .ilike('product_url', '%zooplus%')\
                .execute()

            all_zooplus = response.data
            total = len(all_zooplus)
            with_images = sum(1 for p in all_zooplus if p['image_url'])

            # CSV import specific stats
            csv_imports = [p for p in all_zooplus if p['source'] == 'zooplus_csv_import']
            csv_total = len(csv_imports)
            csv_with_images = sum(1 for p in csv_imports if p['image_url'])

            return {
                'total': total,
                'with_images': with_images,
                'coverage': (with_images / total * 100) if total > 0 else 0,
                'csv_total': csv_total,
                'csv_with_images': csv_with_images,
                'csv_coverage': (csv_with_images / csv_total * 100) if csv_total > 0 else 0,
                'remaining': total - with_images,
                'csv_remaining': csv_total - csv_with_images
            }

        except Exception as e:
            print(f"Error getting coverage: {e}")
            return {}

    def get_scraping_progress(self) -> Dict:
        """Get progress from GCS scraped files"""
        try:
            # Count files in latest zooplus_images sessions
            blobs = list(self.bucket.list_blobs(prefix="scraped/zooplus_images/"))

            if not blobs:
                return {'gcs_files': 0, 'latest_session': None}

            # Group by session
            sessions = {}
            for blob in blobs:
                if blob.name.endswith('.json'):
                    path_parts = blob.name.split('/')
                    if len(path_parts) >= 4:
                        session = path_parts[2]  # Extract session ID
                        if session not in sessions:
                            sessions[session] = []
                        sessions[session].append(blob.name)

            # Get latest session info
            if sessions:
                latest_session = max(sessions.keys())
                total_files = sum(len(files) for files in sessions.values())
                latest_files = len(sessions[latest_session])

                return {
                    'gcs_files': total_files,
                    'latest_session': latest_session,
                    'latest_files': latest_files,
                    'total_sessions': len(sessions)
                }

        except Exception as e:
            print(f"Error getting scraping progress: {e}")

        return {'gcs_files': 0, 'latest_session': None}

    def print_status(self, coverage: Dict, scraping: Dict):
        """Print current status"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        print(f"\n[{timestamp}] Current Status:")
        print(f"  📊 Overall Zooplus: {coverage.get('with_images', 0):,}/{coverage.get('total', 0):,} ({coverage.get('coverage', 0):.1f}%)")
        print(f"  📦 CSV Imports: {coverage.get('csv_with_images', 0)}/{coverage.get('csv_total', 0)} ({coverage.get('csv_coverage', 0):.1f}%)")
        print(f"  🎯 Remaining: {coverage.get('csv_remaining', 0)} products")

        if scraping.get('gcs_files', 0) > 0:
            print(f"  📁 GCS Files: {scraping['gcs_files']} across {scraping.get('total_sessions', 0)} sessions")
            if scraping.get('latest_session'):
                print(f"  🕐 Latest Session: {scraping['latest_session']} ({scraping.get('latest_files', 0)} files)")

    def monitor(self, interval: int = 30):
        """Monitor progress with specified interval"""

        # Get initial state
        initial_coverage = self.get_current_coverage()
        print("\nStarting state:")
        print(f"  Total Zooplus products: {initial_coverage.get('total', 0):,}")
        print(f"  With images: {initial_coverage.get('with_images', 0):,} ({initial_coverage.get('coverage', 0):.1f}%)")
        print(f"  CSV imports without images: {initial_coverage.get('csv_remaining', 0)}")

        print(f"\nMonitoring progress... (Ctrl+C to stop)")
        print(f"Update interval: {interval} seconds")

        previous_coverage = initial_coverage.copy()

        try:
            while True:
                time.sleep(interval)

                # Get current stats
                current_coverage = self.get_current_coverage()
                scraping_progress = self.get_scraping_progress()

                # Calculate changes
                if previous_coverage and current_coverage:
                    img_change = current_coverage.get('with_images', 0) - previous_coverage.get('with_images', 0)
                    csv_change = current_coverage.get('csv_with_images', 0) - previous_coverage.get('csv_with_images', 0)

                    if img_change > 0 or csv_change > 0:
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        if csv_change > 0:
                            print(f"[{timestamp}] +{csv_change} CSV images | CSV: {current_coverage.get('csv_with_images', 0)}/{current_coverage.get('csv_total', 0)} ({current_coverage.get('csv_coverage', 0):.1f}%) | Remaining: {current_coverage.get('csv_remaining', 0)}")
                        else:
                            print(f"[{timestamp}] +{img_change} total images | Overall: {current_coverage.get('with_images', 0)}/{current_coverage.get('total', 0)} ({current_coverage.get('coverage', 0):.1f}%)")

                # Check if scraping appears complete
                if (current_coverage.get('csv_remaining', 0) <= 10 and
                    scraping_progress.get('gcs_files', 0) >= 600):  # Most files processed
                    print(f"\n✅ Scraping appears to be nearly complete!")
                    print(f"CSV coverage: {current_coverage.get('csv_coverage', 0):.1f}%")
                    print(f"Remaining: {current_coverage.get('csv_remaining', 0)} products")
                    break

                previous_coverage = current_coverage

        except KeyboardInterrupt:
            print(f"\n\n🛑 Monitoring stopped by user")

        # Final status
        final_coverage = self.get_current_coverage()
        final_scraping = self.get_scraping_progress()

        print(f"\n" + "=" * 60)
        print("FINAL STATUS")
        print("=" * 60)
        self.print_status(final_coverage, final_scraping)

        # Progress summary
        if initial_coverage and final_coverage:
            total_gained = final_coverage.get('with_images', 0) - initial_coverage.get('with_images', 0)
            csv_gained = final_coverage.get('csv_with_images', 0) - initial_coverage.get('csv_with_images', 0)

            print(f"\n📈 Progress Summary:")
            print(f"  Total images gained: +{total_gained}")
            print(f"  CSV images gained: +{csv_gained}")
            if csv_gained > 0:
                coverage_improvement = final_coverage.get('csv_coverage', 0) - initial_coverage.get('csv_coverage', 0)
                print(f"  CSV coverage improvement: +{coverage_improvement:.1f}%")

def main():
    monitor = ZooplusImageMonitor()

    # Quick status check
    coverage = monitor.get_current_coverage()
    scraping = monitor.get_scraping_progress()
    monitor.print_status(coverage, scraping)

    # Ask if user wants to monitor
    choice = input("\nStart continuous monitoring? (y/n): ").lower().strip()

    if choice == 'y':
        interval = input("Update interval in seconds (default 30): ").strip()
        try:
            interval = int(interval) if interval else 30
        except:
            interval = 30

        monitor.monitor(interval)
    else:
        print("Monitoring cancelled")

if __name__ == "__main__":
    main()