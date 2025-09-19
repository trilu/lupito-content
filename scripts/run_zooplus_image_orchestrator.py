#!/usr/bin/env python3
"""
Zooplus Image Scraping Orchestrator
Manages multiple sessions for scraping Zooplus CSV import products
Based on the proven scraper_orchestrator.py pattern
"""

import subprocess
import time
import threading
import os
from datetime import datetime

def run_scraper_session(name, country, min_delay, max_delay, batch_size, offset):
    """Run a single scraper session"""
    cmd = [
        'python', 'scripts/scrape_zooplus_images_orchestrated.py',
        name, country, str(min_delay), str(max_delay), str(batch_size), str(offset)
    ]

    print(f"🚀 Starting {name} session...")
    print(f"   Command: {' '.join(cmd)}")

    try:
        # Run in the virtual environment
        env = os.environ.copy()
        result = subprocess.run(cmd, cwd=os.getcwd(), env=env, capture_output=False)

        if result.returncode == 0:
            print(f"✅ {name} session completed successfully")
        else:
            print(f"❌ {name} session failed with exit code {result.returncode}")

    except Exception as e:
        print(f"❌ {name} session error: {e}")

def main():
    """Main orchestrator"""

    print("=" * 60)
    print("ZOOPLUS IMAGE SCRAPING ORCHESTRATOR")
    print("=" * 60)
    print(f"Started: {datetime.now().isoformat()}")
    print()

    # Session configurations (proven from ingredients scraper)
    session_configs = [
        {"name": "zooplus_img_us", "country_code": "us", "min_delay": 15, "max_delay": 25, "batch_size": 12},
        {"name": "zooplus_img_gb", "country_code": "gb", "min_delay": 20, "max_delay": 30, "batch_size": 12},
        {"name": "zooplus_img_de", "country_code": "de", "min_delay": 25, "max_delay": 35, "batch_size": 12}
    ]

    # Calculate offsets for 730 total products
    total_products = 730
    products_per_session = total_products // len(session_configs)
    remainder = total_products % len(session_configs)

    threads = []

    for i, config in enumerate(session_configs):
        # Calculate offset and batch size for this session
        offset = i * products_per_session

        # Add remainder products to the last session
        batch_size = products_per_session
        if i == len(session_configs) - 1:
            batch_size += remainder

        print(f"Session {i+1}: {config['name']}")
        print(f"  Country: {config['country_code']}")
        print(f"  Delays: {config['min_delay']}-{config['max_delay']}s")
        print(f"  Products: {batch_size} (offset: {offset})")
        print()

        # Create and start thread
        thread = threading.Thread(
            target=run_scraper_session,
            args=(
                config['name'],
                config['country_code'],
                config['min_delay'],
                config['max_delay'],
                batch_size,
                offset
            )
        )

        threads.append(thread)
        thread.start()

        # Small delay between session starts
        time.sleep(2)

    print("🎯 All sessions started, waiting for completion...")
    print()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    print()
    print("=" * 60)
    print("ZOOPLUS IMAGE SCRAPING ORCHESTRATOR COMPLETE")
    print("=" * 60)
    print(f"Finished: {datetime.now().isoformat()}")
    print()
    print("Next steps:")
    print("1. Check GCS bucket: gs://lupito-content-raw-eu/scraped/zooplus_images/")
    print("2. Run processor: python scripts/process_zooplus_image_urls.py")
    print("3. Monitor progress: python scripts/monitor_zooplus_images.py")

if __name__ == "__main__":
    main()