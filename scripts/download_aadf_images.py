#!/usr/bin/env python3
"""
AADF Image Download Script
Downloads product images from AADF and stores them in Google Cloud Storage
"""

import os
import sys
import json
import time
import random
import requests
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from google.cloud import storage
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configuration
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")
LOG_FILE = f"logs/aadf_image_download_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Set up GCS authentication
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/sergiubiris/Desktop/lupito-content/secrets/gcp-sa.json'

# Rate limiting configuration
RATE_LIMITS = {
    'daytime': {
        'delay_min': 4,      # 4-6 seconds between requests
        'delay_max': 6,
        'batch_pause': 60    # 1 minute between 50-image batches
    },
    'nighttime': {
        'delay_min': 2,      # 2-3 seconds between requests
        'delay_max': 3,
        'batch_pause': 30    # 30 seconds between batches
    }
}

# Batch configuration
BATCH_SIZE = 50
MAX_RETRIES = 3
RETRY_DELAYS = [10, 30, 60]  # Exponential backoff

# Headers for requests
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Accept': 'image/jpeg, image/png, image/webp, image/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AADFImageDownloader:
    def __init__(self):
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(GCS_BUCKET)
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

        # Tracking
        self.total_downloaded = 0
        self.total_failed = 0
        self.failed_downloads = []
        self.start_time = datetime.now()

    def is_daytime(self) -> bool:
        """Check if current time is daytime (9 AM - 10 PM)"""
        hour = datetime.now().hour
        return 9 <= hour < 22

    def get_delay(self) -> float:
        """Get appropriate delay based on time of day"""
        limits = RATE_LIMITS['daytime'] if self.is_daytime() else RATE_LIMITS['nighttime']
        return random.uniform(limits['delay_min'], limits['delay_max'])

    def get_batch_pause(self) -> int:
        """Get batch pause duration based on time of day"""
        limits = RATE_LIMITS['daytime'] if self.is_daytime() else RATE_LIMITS['nighttime']
        return limits['batch_pause']

    def load_aadf_urls_from_gcs(self) -> List[Tuple[str, str]]:
        """Load image URLs from scraped JSON files in GCS"""
        logger.info("Loading AADF URLs from GCS scraped data...")

        # Session folders to check
        session_folders = [
            "scraped/aadf_images/aadf_images_20250915_150547_gb1/",
            "scraped/aadf_images/aadf_images_20250915_150547_de1/",
            "scraped/aadf_images/aadf_images_20250915_150547_ca1/",
            "scraped/aadf_images/aadf_images_20250915_150436_us1/"
        ]

        image_urls = []

        for folder in session_folders:
            logger.info(f"Processing folder: {folder}")
            blobs = self.bucket.list_blobs(prefix=folder)

            for blob in blobs:
                if blob.name.endswith('.json'):
                    try:
                        # Download and parse JSON
                        content = blob.download_as_text()
                        data = json.loads(content)

                        # Extract product key from filename
                        product_key = Path(blob.name).stem

                        # Extract image URL
                        if 'image_url' in data and data['image_url']:
                            image_urls.append((product_key, data['image_url']))

                    except Exception as e:
                        logger.error(f"Error processing {blob.name}: {e}")

        # Remove duplicates
        image_urls = list(set(image_urls))
        logger.info(f"Found {len(image_urls)} unique image URLs to download")
        return image_urls

    def check_existing_images(self) -> set:
        """Check which images already exist in GCS"""
        logger.info("Checking existing images in GCS...")
        existing = set()

        prefix = "product-images/aadf/"
        blobs = self.bucket.list_blobs(prefix=prefix)

        for blob in blobs:
            # Extract product key from path
            filename = Path(blob.name).stem
            existing.add(filename)

        logger.info(f"Found {len(existing)} existing images")
        return existing

    def download_image(self, url: str, max_retries: int = MAX_RETRIES) -> Optional[bytes]:
        """Download an image with retry logic"""
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=30)

                if response.status_code == 200:
                    # Validate it's an image
                    content_type = response.headers.get('content-type', '')
                    if 'image' in content_type:
                        return response.content
                    else:
                        logger.warning(f"Non-image content type: {content_type}")
                        return None

                elif response.status_code == 404:
                    logger.warning(f"Image not found: {url}")
                    return None

                else:
                    logger.warning(f"HTTP {response.status_code} for {url}")
                    if attempt < max_retries - 1:
                        time.sleep(RETRY_DELAYS[attempt])

            except Exception as e:
                logger.error(f"Error downloading {url}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(RETRY_DELAYS[attempt])

        return None

    def upload_to_gcs(self, content: bytes, product_key: str) -> bool:
        """Upload image to GCS"""
        try:
            blob_path = f"product-images/aadf/{product_key}.jpg"
            blob = self.bucket.blob(blob_path)

            blob.upload_from_string(
                content,
                content_type='image/jpeg'
            )

            # Don't make public - bucket has public access prevention
            # blob.make_public()

            return True

        except Exception as e:
            logger.error(f"Failed to upload {product_key} to GCS: {e}")
            return False

    def download_batch(self, batch: List[Tuple[str, str]]):
        """Download a batch of images"""
        for i, (product_key, image_url) in enumerate(batch, 1):
            # Respectful delay
            delay = self.get_delay()
            time.sleep(delay)

            logger.info(f"[{i}/{len(batch)}] Downloading {product_key}...")

            # Download image
            image_content = self.download_image(image_url)

            if image_content:
                # Upload to GCS
                if self.upload_to_gcs(image_content, product_key):
                    self.total_downloaded += 1
                    logger.info(f"✅ Successfully downloaded and uploaded {product_key}")
                else:
                    self.total_failed += 1
                    self.failed_downloads.append((product_key, image_url, "Upload failed"))
            else:
                self.total_failed += 1
                self.failed_downloads.append((product_key, image_url, "Download failed"))
                logger.warning(f"❌ Failed to download {product_key}")

            # Progress update every 10 images
            if self.total_downloaded % 10 == 0:
                self.print_progress()

    def print_progress(self):
        """Print download progress"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        rate = self.total_downloaded / elapsed if elapsed > 0 else 0

        logger.info(f"""
        ========== Progress Update ==========
        Downloaded: {self.total_downloaded}
        Failed: {self.total_failed}
        Rate: {rate:.2f} images/second
        Time elapsed: {elapsed/3600:.1f} hours
        Mode: {'Daytime' if self.is_daytime() else 'Nighttime'}
        =====================================
        """)

    def save_failed_downloads(self):
        """Save failed downloads for retry"""
        if self.failed_downloads:
            failed_file = f"data/aadf_failed_downloads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(failed_file, 'w') as f:
                json.dump(self.failed_downloads, f, indent=2)
            logger.info(f"Saved {len(self.failed_downloads)} failed downloads to {failed_file}")

    def run(self):
        """Main download process"""
        logger.info("Starting AADF image download process...")
        logger.info(f"Mode: {'Daytime' if self.is_daytime() else 'Nighttime'}")

        # Load URLs
        image_urls = self.load_aadf_urls_from_gcs()

        # Check existing
        existing = self.check_existing_images()

        # Filter out existing
        to_download = [(k, v) for k, v in image_urls if k not in existing]
        logger.info(f"Need to download: {len(to_download)} new images")

        if not to_download:
            logger.info("No new images to download!")
            return

        # Process in batches
        total_batches = (len(to_download) + BATCH_SIZE - 1) // BATCH_SIZE

        for batch_num in range(0, len(to_download), BATCH_SIZE):
            batch = to_download[batch_num:batch_num + BATCH_SIZE]
            current_batch = (batch_num // BATCH_SIZE) + 1

            logger.info(f"\n=== Processing batch {current_batch}/{total_batches} ===")

            # Download batch
            self.download_batch(batch)

            # Pause between batches
            if batch_num + BATCH_SIZE < len(to_download):
                pause = self.get_batch_pause()
                logger.info(f"Batch complete. Pausing {pause} seconds...")
                time.sleep(pause)

        # Final report
        self.print_final_report()

        # Save failed downloads
        self.save_failed_downloads()

    def print_final_report(self):
        """Print final download report"""
        total_time = (datetime.now() - self.start_time).total_seconds()

        logger.info(f"""
        ========== FINAL REPORT ==========
        Total downloaded: {self.total_downloaded}
        Total failed: {self.total_failed}
        Success rate: {(self.total_downloaded/(self.total_downloaded+self.total_failed)*100):.1f}%
        Total time: {total_time/3600:.1f} hours
        Average rate: {self.total_downloaded/total_time:.2f} images/second
        ==================================
        """)


if __name__ == "__main__":
    # Create logs directory if it doesn't exist
    Path("logs").mkdir(exist_ok=True)
    Path("data").mkdir(exist_ok=True)

    # Run downloader
    downloader = AADFImageDownloader()

    try:
        downloader.run()
    except KeyboardInterrupt:
        logger.info("\n\nDownload interrupted by user")
        downloader.print_final_report()
        downloader.save_failed_downloads()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        downloader.save_failed_downloads()
        raise