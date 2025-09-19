#!/usr/bin/env python3
"""
Monitor AADF review page scraping progress
"""
import os
import time
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def check_progress():
    """Check current AADF image coverage"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Get total AADF products
    total_result = supabase.table('foods_canonical').select(
        'product_key', count='exact'
    ).ilike(
        'product_url', '%allaboutdogfood%'
    ).execute()

    total = total_result.count

    # Get AADF products with images
    with_images_result = supabase.table('foods_canonical').select(
        'product_key', count='exact'
    ).ilike(
        'product_url', '%allaboutdogfood%'
    ).not_.is_(
        'image_url', 'null'
    ).execute()

    with_images = with_images_result.count
    without_images = total - with_images
    coverage = (with_images / total * 100) if total > 0 else 0

    return {
        'total': total,
        'with_images': with_images,
        'without_images': without_images,
        'coverage': coverage
    }

def main():
    """Main monitoring loop"""
    print("="*60)
    print("AADF SCRAPING PROGRESS MONITOR")
    print("="*60)

    # Get initial state
    initial = check_progress()
    print(f"\nStarting state:")
    print(f"  Total AADF products: {initial['total']}")
    print(f"  With images: {initial['with_images']} ({initial['coverage']:.1f}%)")
    print(f"  Without images: {initial['without_images']}")

    print("\nMonitoring progress... (Ctrl+C to stop)\n")

    last_with_images = initial['with_images']

    try:
        while True:
            time.sleep(30)  # Check every 30 seconds

            current = check_progress()

            # Calculate progress
            new_images = current['with_images'] - last_with_images

            if new_images > 0:
                timestamp = datetime.now().strftime('%H:%M:%S')
                print(f"[{timestamp}] +{new_images} new images | "
                      f"Total: {current['with_images']}/{current['total']} "
                      f"({current['coverage']:.1f}%) | "
                      f"Remaining: {current['without_images']}")
                last_with_images = current['with_images']

            # Check if we're done (>95% coverage or no more without images)
            if current['coverage'] >= 95 or current['without_images'] <= 10:
                print("\n✅ Scraping appears to be complete!")
                print(f"Final coverage: {current['with_images']}/{current['total']} ({current['coverage']:.1f}%)")
                break

    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")
        final = check_progress()
        print(f"\nFinal state:")
        print(f"  Total AADF products: {final['total']}")
        print(f"  With images: {final['with_images']} ({final['coverage']:.1f}%)")
        print(f"  Without images: {final['without_images']}")
        print(f"\n  Images added this session: {final['with_images'] - initial['with_images']}")

if __name__ == "__main__":
    main()