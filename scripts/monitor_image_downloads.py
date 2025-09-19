#!/usr/bin/env python3
"""
Image Download Monitor
Real-time monitoring of AADF and Zooplus image downloads
"""

import os
import sys
import time
import json
from datetime import datetime
from pathlib import Path
from google.cloud import storage
from dotenv import load_dotenv
from typing import Dict, Tuple
import argparse

# Load environment variables
load_dotenv()

# Configuration
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/sergiubiris/Desktop/lupito-content/secrets/gcp-sa.json'

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


class ImageDownloadMonitor:
    def __init__(self):
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(GCS_BUCKET)

        # Expected totals
        self.expected_totals = {
            'aadf': 1398,
            'zooplus': 6400  # Approximate
        }

    def count_scraped_jsons(self) -> int:
        """Count total AADF JSONs in scraped folders"""
        session_folders = [
            "scraped/aadf_images/aadf_images_20250915_150547_gb1/",
            "scraped/aadf_images/aadf_images_20250915_150547_de1/",
            "scraped/aadf_images/aadf_images_20250915_150547_ca1/",
            "scraped/aadf_images/aadf_images_20250915_150436_us1/"
        ]

        total_jsons = 0
        for folder in session_folders:
            blobs = list(self.bucket.list_blobs(prefix=folder))
            json_count = sum(1 for blob in blobs if blob.name.endswith('.json'))
            total_jsons += json_count

        return total_jsons

    def count_downloaded_images(self, source: str) -> int:
        """Count downloaded images for a source (aadf or zooplus)"""
        prefix = f"product-images/{source}/"
        blobs = list(self.bucket.list_blobs(prefix=prefix))
        return sum(1 for blob in blobs if blob.name.endswith(('.jpg', '.jpeg', '.png')))

    def get_latest_log_stats(self) -> Dict:
        """Parse latest log file for current session stats"""
        log_dir = Path("logs")
        if not log_dir.exists():
            return {}

        # Find latest AADF log file
        log_files = sorted(log_dir.glob("aadf_image_download_*.log"))
        if not log_files:
            return {}

        latest_log = log_files[-1]

        stats = {
            'session_downloaded': 0,
            'session_failed': 0,
            'current_rate': 0,
            'session_start': None,
            'last_download': None,
            'mode': 'Unknown'
        }

        try:
            with open(latest_log, 'r') as f:
                lines = f.readlines()
                for line in reversed(lines):
                    if 'Downloaded:' in line:
                        # Parse progress update
                        for next_line in lines[lines.index(line):]:
                            if 'Downloaded:' in next_line:
                                stats['session_downloaded'] = int(next_line.split(':')[1].strip())
                            elif 'Failed:' in next_line:
                                stats['session_failed'] = int(next_line.split(':')[1].strip())
                            elif 'Rate:' in next_line:
                                stats['current_rate'] = float(next_line.split(':')[1].strip().split()[0])
                            elif 'Mode:' in next_line:
                                stats['mode'] = next_line.split(':')[1].strip()
                        break
                    elif 'Successfully downloaded and uploaded' in line:
                        # Get timestamp of last successful download
                        timestamp_str = line.split(' - ')[0]
                        stats['last_download'] = timestamp_str

        except Exception as e:
            pass

        return stats

    def format_time_diff(self, seconds: float) -> str:
        """Format time difference in human-readable format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"

    def calculate_eta(self, downloaded: int, total: int, rate: float) -> str:
        """Calculate estimated time of arrival"""
        if rate <= 0 or downloaded >= total:
            return "N/A"

        remaining = total - downloaded
        seconds_remaining = remaining / rate
        return self.format_time_diff(seconds_remaining)

    def print_progress_bar(self, current: int, total: int, width: int = 50) -> str:
        """Create a text progress bar"""
        if total == 0:
            return "[" + " " * width + "]"

        percent = current / total
        filled = int(width * percent)
        bar = "█" * filled + "░" * (width - filled)
        return f"[{bar}]"

    def display_stats(self, clear_screen: bool = True):
        """Display current download statistics"""
        if clear_screen:
            os.system('clear' if os.name == 'posix' else 'cls')

        # Get current counts
        aadf_scraped = self.count_scraped_jsons()
        aadf_downloaded = self.count_downloaded_images('aadf')
        zooplus_downloaded = self.count_downloaded_images('zooplus')

        # Get session stats from log
        session_stats = self.get_latest_log_stats()

        # Calculate percentages
        aadf_percent = (aadf_downloaded / self.expected_totals['aadf'] * 100) if self.expected_totals['aadf'] > 0 else 0
        zooplus_percent = (zooplus_downloaded / self.expected_totals['zooplus'] * 100) if self.expected_totals['zooplus'] > 0 else 0

        # Print header
        print(f"\n{Colors.BOLD}{Colors.HEADER}📊 IMAGE DOWNLOAD MONITOR{Colors.END}")
        print(f"{Colors.CYAN}{'='*70}{Colors.END}")
        print(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Mode: {session_stats.get('mode', 'Not Running')}")
        print()

        # AADF Section
        print(f"{Colors.BOLD}{Colors.BLUE}AADF Images{Colors.END}")
        print(f"Scraped JSONs:    {aadf_scraped:,}")
        print(f"Target Images:    {self.expected_totals['aadf']:,}")
        print(f"Downloaded:       {Colors.GREEN}{aadf_downloaded:,}{Colors.END} / {self.expected_totals['aadf']:,} ({aadf_percent:.1f}%)")
        print(f"Progress:         {self.print_progress_bar(aadf_downloaded, self.expected_totals['aadf'])}")

        if aadf_downloaded < self.expected_totals['aadf']:
            print(f"Remaining:        {Colors.YELLOW}{self.expected_totals['aadf'] - aadf_downloaded:,}{Colors.END}")
            if session_stats.get('current_rate', 0) > 0:
                eta = self.calculate_eta(aadf_downloaded, self.expected_totals['aadf'], session_stats['current_rate'])
                print(f"ETA:              {eta}")
        else:
            print(f"Status:           {Colors.GREEN}✅ COMPLETE{Colors.END}")

        print()

        # Zooplus Section
        print(f"{Colors.BOLD}{Colors.BLUE}Zooplus Images{Colors.END}")
        print(f"Target Images:    ~{self.expected_totals['zooplus']:,}")
        print(f"Downloaded:       {Colors.GREEN}{zooplus_downloaded:,}{Colors.END} / ~{self.expected_totals['zooplus']:,} ({zooplus_percent:.1f}%)")
        print(f"Progress:         {self.print_progress_bar(zooplus_downloaded, self.expected_totals['zooplus'])}")

        if zooplus_downloaded == 0:
            print(f"Status:           {Colors.YELLOW}⏳ Pending (waiting for AADF completion){Colors.END}")
        elif zooplus_downloaded < self.expected_totals['zooplus']:
            print(f"Remaining:        {Colors.YELLOW}{self.expected_totals['zooplus'] - zooplus_downloaded:,}{Colors.END}")
        else:
            print(f"Status:           {Colors.GREEN}✅ COMPLETE{Colors.END}")

        print()

        # Current Session Stats (if available)
        if session_stats and session_stats.get('session_downloaded', 0) > 0:
            print(f"{Colors.BOLD}{Colors.BLUE}Current Session{Colors.END}")
            print(f"Session Downloads: {session_stats['session_downloaded']:,}")
            print(f"Session Failed:    {Colors.RED}{session_stats['session_failed']:,}{Colors.END}")
            print(f"Download Rate:     {session_stats['current_rate']:.2f} images/second")
            if session_stats.get('last_download'):
                print(f"Last Download:     {session_stats['last_download']}")
            print()

        # Overall Summary
        print(f"{Colors.BOLD}{Colors.BLUE}Overall Summary{Colors.END}")
        total_target = self.expected_totals['aadf'] + self.expected_totals['zooplus']
        total_downloaded = aadf_downloaded + zooplus_downloaded
        overall_percent = (total_downloaded / total_target * 100) if total_target > 0 else 0

        print(f"Total Target:     {total_target:,} images")
        print(f"Total Downloaded: {Colors.GREEN}{total_downloaded:,}{Colors.END} ({overall_percent:.1f}%)")
        print(f"Total Progress:   {self.print_progress_bar(total_downloaded, total_target)}")

        # Storage estimate
        estimated_size_gb = (total_downloaded * 0.3) / 1024  # Assume 300KB per image
        print(f"Estimated Storage: {estimated_size_gb:.2f} GB")

        print(f"\n{Colors.CYAN}{'='*70}{Colors.END}")

        # Check for failed downloads file
        failed_files = list(Path("data").glob("aadf_failed_downloads_*.json"))
        if failed_files:
            latest_failed = sorted(failed_files)[-1]
            try:
                with open(latest_failed, 'r') as f:
                    failed_data = json.load(f)
                    if failed_data:
                        print(f"{Colors.RED}⚠️  {len(failed_data)} failed downloads found in {latest_failed.name}{Colors.END}")
            except:
                pass

    def continuous_monitor(self, refresh_interval: int = 30):
        """Continuously monitor download progress"""
        print(f"Starting continuous monitoring (refresh every {refresh_interval} seconds)")
        print("Press Ctrl+C to stop monitoring")

        try:
            while True:
                self.display_stats(clear_screen=True)
                time.sleep(refresh_interval)

        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Monitoring stopped by user{Colors.END}")
            sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description='Monitor image download progress')
    parser.add_argument('--refresh', type=int, default=30,
                      help='Refresh interval in seconds (default: 30)')
    parser.add_argument('--once', action='store_true',
                      help='Run once and exit (no continuous monitoring)')

    args = parser.parse_args()

    monitor = ImageDownloadMonitor()

    if args.once:
        monitor.display_stats(clear_screen=False)
    else:
        monitor.continuous_monitor(refresh_interval=args.refresh)


if __name__ == "__main__":
    main()