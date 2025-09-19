#!/usr/bin/env python3
"""
Monitor progress of final 227 Zooplus products scraping
Shows real-time statistics from GCS folders
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List
from dotenv import load_dotenv
from google.cloud import storage
import time

load_dotenv()

GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")
TARGET_PRODUCTS = 227

class Final227Monitor:
    def __init__(self):
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(GCS_BUCKET)
        self.start_time = datetime.now()
    
    def find_active_sessions(self) -> List[str]:
        """Find all final_227_* folders in GCS"""
        prefix = "scraped/zooplus/final_227_"
        
        # List all blobs with the prefix
        blobs = self.bucket.list_blobs(prefix=prefix)
        
        # Extract unique folder names
        folders = set()
        for blob in blobs:
            # Get folder name from blob path
            parts = blob.name.split('/')
            if len(parts) >= 3:
                folder_name = parts[2]  # e.g., "final_227_20250914_123456_us1"
                if folder_name.startswith("final_227_"):
                    folders.add(folder_name)
        
        return sorted(list(folders))
    
    def count_files_in_folder(self, folder_name: str) -> Dict:
        """Count files and analyze content in a specific folder"""
        prefix = f"scraped/zooplus/{folder_name}/"
        
        stats = {
            'total_files': 0,
            'with_ingredients': 0,
            'with_nutrition': 0,
            'with_errors': 0,
            'patterns_used': {}
        }
        
        blobs = self.bucket.list_blobs(prefix=prefix)
        
        for blob in blobs:
            if blob.name.endswith('.json'):
                stats['total_files'] += 1
                
                # Download and analyze file content (sample first 10)
                if stats['total_files'] <= 10:
                    try:
                        content = blob.download_as_text()
                        data = json.loads(content)
                        
                        if 'ingredients_raw' in data:
                            stats['with_ingredients'] += 1
                            pattern = data.get('pattern_used', 'Unknown')
                            stats['patterns_used'][pattern] = stats['patterns_used'].get(pattern, 0) + 1
                        
                        if 'nutrition' in data:
                            stats['with_nutrition'] += 1
                        
                        if 'error' in data:
                            stats['with_errors'] += 1
                    except:
                        pass
        
        # Extrapolate from sample if more than 10 files
        if stats['total_files'] > 10:
            sample_size = min(10, stats['total_files'])
            multiplier = stats['total_files'] / sample_size
            stats['with_ingredients'] = int(stats['with_ingredients'] * multiplier)
            stats['with_nutrition'] = int(stats['with_nutrition'] * multiplier)
            stats['with_errors'] = int(stats['with_errors'] * multiplier)
        
        return stats
    
    def extract_session_info(self, folder_name: str) -> Dict:
        """Extract session information from folder name"""
        # Format: final_227_20250914_123456_us1
        parts = folder_name.split('_')
        
        info = {
            'session_name': parts[-1] if len(parts) >= 5 else 'unknown',
            'timestamp': '_'.join(parts[2:4]) if len(parts) >= 5 else 'unknown'
        }
        
        # Map session to country flag
        country_flags = {
            'us1': '🇺🇸 US',
            'gb1': '🇬🇧 GB',
            'de1': '🇩🇪 DE',
            'ca1': '🇨🇦 CA',
            'fr1': '🇫🇷 FR',
            'default': '🌍 Default'
        }
        
        info['display_name'] = country_flags.get(info['session_name'], '🌍 ' + info['session_name'].upper())
        
        return info
    
    def display_progress(self):
        """Display current progress"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("=" * 60)
        print("📊 FINAL 227 ZOOPLUS SCRAPING PROGRESS")
        print("=" * 60)
        print(f"Target: {TARGET_PRODUCTS} products")
        print(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Running: {datetime.now() - self.start_time}")
        print()
        
        # Find active sessions
        sessions = self.find_active_sessions()
        
        if not sessions:
            print("⚠️ No active scraping sessions found")
            print("\nLooking for folders matching: scraped/zooplus/final_227_*")
            return
        
        # Aggregate statistics
        total_scraped = 0
        total_with_ingredients = 0
        total_with_nutrition = 0
        total_errors = 0
        all_patterns = {}
        
        print("🚀 ACTIVE SESSIONS")
        print("-" * 60)
        
        for folder in sessions:
            session_info = self.extract_session_info(folder)
            stats = self.count_files_in_folder(folder)
            
            total_scraped += stats['total_files']
            total_with_ingredients += stats['with_ingredients']
            total_with_nutrition += stats['with_nutrition']
            total_errors += stats['with_errors']
            
            # Merge pattern usage
            for pattern, count in stats['patterns_used'].items():
                all_patterns[pattern] = all_patterns.get(pattern, 0) + count
            
            # Display session info
            print(f"\n{session_info['display_name']} Session:")
            print(f"  📁 Folder: {folder}")
            print(f"  📊 Progress: {stats['total_files']}/{TARGET_PRODUCTS} files")
            
            if stats['total_files'] > 0:
                success_rate = (stats['with_ingredients'] / stats['total_files']) * 100
                print(f"  ✅ Success rate: {success_rate:.1f}%")
                print(f"  🥘 With ingredients: {stats['with_ingredients']}")
                print(f"  📈 With nutrition: {stats['with_nutrition']}")
                if stats['with_errors'] > 0:
                    print(f"  ❌ Errors: {stats['with_errors']}")
        
        # Overall progress
        print("\n" + "=" * 60)
        print("📈 OVERALL PROGRESS")
        print("-" * 60)
        
        progress_pct = (total_scraped / TARGET_PRODUCTS) * 100
        print(f"Completed: {total_scraped}/{TARGET_PRODUCTS} ({progress_pct:.1f}%)")
        
        # Progress bar
        bar_length = 40
        filled = int(bar_length * total_scraped / TARGET_PRODUCTS)
        bar = '█' * filled + '░' * (bar_length - filled)
        print(f"Progress: [{bar}] {progress_pct:.1f}%")
        
        if total_scraped > 0:
            overall_success = (total_with_ingredients / total_scraped) * 100
            print(f"\nExtraction rate: {overall_success:.1f}%")
            print(f"With ingredients: {total_with_ingredients}")
            print(f"With nutrition: {total_with_nutrition}")
            
            if total_errors > 0:
                error_rate = (total_errors / total_scraped) * 100
                print(f"Error rate: {error_rate:.1f}% ({total_errors} errors)")
        
        # Pattern usage
        if all_patterns:
            print("\n📋 EXTRACTION PATTERNS USED")
            print("-" * 60)
            for pattern, count in sorted(all_patterns.items(), key=lambda x: x[1], reverse=True):
                print(f"  {pattern}: {count} products")
        
        # Time estimates
        if total_scraped > 0:
            elapsed = datetime.now() - self.start_time
            rate = total_scraped / elapsed.total_seconds()  # products per second
            
            if rate > 0:
                remaining = TARGET_PRODUCTS - total_scraped
                eta_seconds = remaining / rate
                eta = datetime.now() + timedelta(seconds=eta_seconds)
                
                print("\n⏱️ TIME ESTIMATES")
                print("-" * 60)
                print(f"Rate: {rate * 3600:.1f} products/hour")
                print(f"ETA: {eta.strftime('%H:%M:%S')} ({timedelta(seconds=int(eta_seconds))})")
        
        print("\n" + "=" * 60)
        print(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("Press Ctrl+C to exit")
    
    def run_continuous(self, refresh_seconds: int = 30):
        """Run continuous monitoring"""
        try:
            while True:
                self.display_progress()
                time.sleep(refresh_seconds)
        except KeyboardInterrupt:
            print("\n\n👋 Monitoring stopped")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Monitor final 227 scraping progress')
    parser.add_argument('--once', action='store_true',
                       help='Run once instead of continuous monitoring')
    parser.add_argument('--refresh', type=int, default=30,
                       help='Refresh interval in seconds (default: 30)')
    
    args = parser.parse_args()
    
    monitor = Final227Monitor()
    
    if args.once:
        monitor.display_progress()
    else:
        print("Starting continuous monitoring...")
        print(f"Refresh interval: {args.refresh} seconds")
        print("Press Ctrl+C to stop\n")
        time.sleep(2)
        monitor.run_continuous(args.refresh)

if __name__ == "__main__":
    main()