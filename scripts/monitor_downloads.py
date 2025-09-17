#!/usr/bin/env python3
"""
Monitor both AADF and Zooplus image downloads
"""
import os
import time
from datetime import datetime
from pathlib import Path

def get_latest_log_stats(log_pattern):
    """Get stats from the latest log file matching pattern"""
    logs_dir = Path("logs")
    matching_logs = list(logs_dir.glob(log_pattern))

    if not matching_logs:
        return None

    # Get the most recent log
    latest_log = max(matching_logs, key=lambda p: p.stat().st_mtime)

    stats = {
        'downloaded': 0,
        'failed': 0,
        'last_product': None,
        'log_file': latest_log.name
    }

    try:
        with open(latest_log, 'r') as f:
            lines = f.readlines()
            for line in reversed(lines):
                if 'Downloaded:' in line and 'Failed:' in line:
                    # Parse progress update
                    for part in line.split():
                        if part.isdigit():
                            if 'Downloaded:' in prev_word:
                                stats['downloaded'] = int(part)
                            elif 'Failed:' in prev_word:
                                stats['failed'] = int(part)
                        prev_word = part
                    break
                elif '✅ Successfully downloaded' in line:
                    if not stats['last_product']:
                        # Extract product name
                        parts = line.split('uploaded ')
                        if len(parts) > 1:
                            stats['last_product'] = parts[1].strip()
                            if not stats['downloaded']:
                                # Count successful downloads if no progress update found
                                stats['downloaded'] = sum(1 for l in lines if '✅ Successfully downloaded' in l)
                prev_word = ""
    except Exception as e:
        print(f"Error reading log: {e}")

    return stats

def count_gcs_files(prefix):
    """Count files in GCS bucket"""
    try:
        result = os.popen(f"gsutil ls gs://lupito-content-raw-eu/product-images/{prefix}/ 2>/dev/null | wc -l").read()
        return int(result.strip())
    except:
        return 0

def main():
    print("\n" + "="*60)
    print("IMAGE DOWNLOAD MONITOR")
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*60)

    # AADF Status
    print("\n📦 AADF DOWNLOADS")
    print("-" * 40)

    aadf_stats = get_latest_log_stats("aadf_image_download_*.log")
    if aadf_stats:
        print(f"Log: {aadf_stats['log_file']}")
        print(f"Downloaded: {aadf_stats['downloaded']}/1,183")
        print(f"Failed: {aadf_stats['failed']}")
        print(f"Progress: {aadf_stats['downloaded']/1183*100:.1f}%")
        if aadf_stats['last_product']:
            print(f"Last: {aadf_stats['last_product'][:50]}")
    else:
        print("No AADF download logs found")

    aadf_gcs = count_gcs_files("aadf")
    print(f"GCS files: {aadf_gcs}")

    # Zooplus Status
    print("\n🛍️ ZOOPLUS DOWNLOADS")
    print("-" * 40)

    zooplus_stats = get_latest_log_stats("zooplus_full_download*.log")
    if not zooplus_stats:
        zooplus_stats = get_latest_log_stats("zooplus_image_download_*.log")

    if zooplus_stats:
        print(f"Log: {zooplus_stats['log_file']}")
        print(f"Downloaded: {zooplus_stats['downloaded']}/2,670")
        print(f"Failed: {zooplus_stats['failed']}")
        print(f"Progress: {zooplus_stats['downloaded']/2670*100:.1f}%")
        if zooplus_stats['last_product']:
            print(f"Last: {zooplus_stats['last_product'][:50]}")
    else:
        print("No Zooplus download logs found")

    zooplus_gcs = count_gcs_files("zooplus")
    print(f"GCS files: {zooplus_gcs}")

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("-" * 40)

    total_target = 1183 + 2670
    total_downloaded = (aadf_stats['downloaded'] if aadf_stats else 0) + (zooplus_stats['downloaded'] if zooplus_stats else 0)
    total_gcs = aadf_gcs + zooplus_gcs

    print(f"Total target: {total_target:,} images")
    print(f"Total downloaded: {total_downloaded:,} ({total_downloaded/total_target*100:.1f}%)")
    print(f"Total in GCS: {total_gcs:,} files")

    # ETA calculation (rough)
    if total_downloaded > 0:
        # Assume average of 3.5 seconds per image
        remaining = total_target - total_downloaded
        eta_seconds = remaining * 3.5
        eta_hours = eta_seconds / 3600
        print(f"Estimated time remaining: {eta_hours:.1f} hours")

    print("="*60)

if __name__ == "__main__":
    main()