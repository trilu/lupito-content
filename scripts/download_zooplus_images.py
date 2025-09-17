#!/usr/bin/env python3
"""
Zooplus Image Download Script
Downloads product images from Zooplus and stores them in Google Cloud Storage
Runs in parallel with AADF downloads since they use different servers
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
from supabase import create_client
import logging

# Load environment variables
load_dotenv()

# Configuration
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
LOG_FILE = f"logs/zooplus_image_download_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Set up GCS authentication
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/sergiubiris/Desktop/lupito-content/secrets/gcp-sa.json'

# Rate limiting configuration - More conservative for Zooplus
RATE_LIMITS = {
    'daytime': {
        'delay_min': 6,      # 6-8 seconds between requests
        'delay_max': 8,
        'batch_pause': 90    # 1.5 minutes between 50-image batches
    },
    'nighttime': {
        'delay_min': 3,      # 3-4 seconds between requests
        'delay_max': 4,
        'batch_pause': 45    # 45 seconds between batches
    }
}

# Batch configuration
BATCH_SIZE = 50
MAX_RETRIES = 3
RETRY_DELAYS = [10, 30, 60]  # Exponential backoff

# Headers for requests - Different user agent for Zooplus
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'image/jpeg, image/png, image/webp, image/*',
    'Accept-Language': 'en-US,en;q=0.9,de;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Referer': 'https://www.zooplus.com/'
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


class ZooplusImageDownloader:
    def __init__(self, checkpoint_file="data/zooplus_checkpoint.json"):
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(GCS_BUCKET)
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.checkpoint_file = checkpoint_file

        # Tracking
        self.total_downloaded = 0
        self.total_failed = 0
        self.failed_downloads = []
        self.start_time = datetime.now()
        self.last_product_key = None

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

    def load_checkpoint(self) -> Optional[str]:
        """Load checkpoint to resume from last position"""
        if Path(self.checkpoint_file).exists():
            try:
                with open(self.checkpoint_file, 'r') as f:
                    data = json.load(f)
                    logger.info(f"Resuming from checkpoint: {data.get('last_product_key')}")
                    self.total_downloaded = data.get('total_downloaded', 0)
                    return data.get('last_product_key')
            except Exception as e:
                logger.error(f"Error loading checkpoint: {e}")
        return None

    def save_checkpoint(self):
        """Save current progress for resuming"""
        checkpoint_data = {
            'last_product_key': self.last_product_key,
            'total_downloaded': self.total_downloaded,
            'timestamp': datetime.now().isoformat()
        }
        try:
            with open(self.checkpoint_file, 'w') as f:
                json.dump(checkpoint_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving checkpoint: {e}")

    def get_zooplus_urls_from_database(self, limit=None) -> List[Tuple[str, str]]:
        """Get Zooplus image URLs from database"""
        logger.info("Loading Zooplus URLs from database...")

        try:
            # Paginate through ALL results (Supabase has 1000 row limit per query)
            all_image_urls = []
            batch_size = 1000
            offset = 0

            while True:
                # Query for Zooplus products by product_url pattern
                query = self.supabase.table('foods_canonical').select(
                    'product_key, image_url'
                ).ilike(
                    'product_url', '%zooplus%'
                ).not_.is_(
                    'image_url', 'null'
                ).range(offset, offset + batch_size - 1)

                # Execute query
                result = query.execute()

                if not result.data:
                    break

                # Add to results
                batch_urls = [(item['product_key'], item['image_url'])
                             for item in result.data
                             if item['image_url']]
                all_image_urls.extend(batch_urls)

                logger.info(f"Loaded batch: {len(batch_urls)} URLs (total so far: {len(all_image_urls)})")

                # Check if we got less than batch_size (last batch)
                if len(result.data) < batch_size:
                    break

                offset += batch_size

            # Apply limit if testing
            if limit and all_image_urls:
                all_image_urls = all_image_urls[:limit]
                logger.info(f"TEST MODE: Limiting to {limit} products")

            if all_image_urls:
                logger.info(f"Found {len(all_image_urls)} Zooplus products with image URLs")
                return all_image_urls
            else:
                logger.warning("No Zooplus products found with image URLs")
                return []

        except Exception as e:
            logger.error(f"Error querying database: {e}")
            return []

    def check_existing_images(self) -> set:
        """Check which images already exist in GCS"""
        logger.info("Checking existing Zooplus images in GCS...")
        existing = set()

        prefix = "product-images/zooplus/"
        blobs = self.bucket.list_blobs(prefix=prefix)

        for blob in blobs:
            # Extract product key from path
            filename = Path(blob.name).stem
            existing.add(filename)

        logger.info(f"Found {len(existing)} existing Zooplus images")
        return existing

    def download_image(self, url: str, max_retries: int = MAX_RETRIES) -> Optional[bytes]:
        """Download an image with retry logic"""
        for attempt in range(max_retries):
            try:
                # Add timeout and stream for large images
                response = self.session.get(url, timeout=30, stream=True)

                if response.status_code == 200:
                    # Validate it's an image
                    content_type = response.headers.get('content-type', '')
                    if 'image' in content_type:
                        # Read content in chunks
                        content = b""
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                content += chunk
                        return content
                    else:
                        logger.warning(f"Non-image content type: {content_type}")
                        return None

                elif response.status_code == 404:
                    logger.warning(f"Image not found: {url}")
                    return None

                elif response.status_code == 429:
                    # Rate limited - wait longer
                    logger.warning(f"Rate limited, waiting {60 * (attempt + 1)} seconds...")
                    time.sleep(60 * (attempt + 1))

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
            blob_path = f"product-images/zooplus/{product_key}.jpg"
            blob = self.bucket.blob(blob_path)

            blob.upload_from_string(
                content,
                content_type='image/jpeg'
            )

            # Don't make public - bucket has public access prevention
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
            self.last_product_key = product_key

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
                self.save_checkpoint()

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
            failed_file = f"data/zooplus_failed_downloads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(failed_file, 'w') as f:
                json.dump(self.failed_downloads, f, indent=2)
            logger.info(f"Saved {len(self.failed_downloads)} failed downloads to {failed_file}")

    def run(self, test_mode=False):
        """Main download process"""
        logger.info("Starting Zooplus image download process...")
        logger.info(f"Mode: {'Daytime' if self.is_daytime() else 'Nighttime'}")
        logger.info("Running in parallel with AADF downloads...")

        # Load URLs from database (limit to 10 if testing)
        limit = 10 if test_mode else None
        image_urls = self.get_zooplus_urls_from_database(limit=limit)

        if not image_urls:
            logger.error("No Zooplus URLs found in database!")
            return

        # Check existing
        existing = self.check_existing_images()

        # Filter out existing
        to_download = [(k, v) for k, v in image_urls if k not in existing]

        # Resume from checkpoint if available
        checkpoint_key = self.load_checkpoint()
        if checkpoint_key:
            # Find position in list
            for idx, (key, _) in enumerate(to_download):
                if key == checkpoint_key:
                    to_download = to_download[idx+1:]
                    logger.info(f"Resuming from position after {checkpoint_key}")
                    break

        logger.info(f"Need to download: {len(to_download)} images")

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

            # Save checkpoint after each batch
            self.save_checkpoint()

            # Pause between batches
            if batch_num + BATCH_SIZE < len(to_download):
                pause = self.get_batch_pause()
                logger.info(f"Batch complete. Pausing {pause} seconds...")
                time.sleep(pause)

        # Final report
        self.print_final_report()

        # Save failed downloads
        self.save_failed_downloads()

        # Clear checkpoint on completion
        if Path(self.checkpoint_file).exists():
            os.remove(self.checkpoint_file)
            logger.info("Cleared checkpoint file")

    def print_final_report(self):
        """Print final download report"""
        total_time = (datetime.now() - self.start_time).total_seconds()

        logger.info(f"""
        ========== FINAL REPORT ==========
        Total downloaded: {self.total_downloaded}
        Total failed: {self.total_failed}
        Success rate: {(self.total_downloaded/(self.total_downloaded+self.total_failed)*100):.1f}% if self.total_failed > 0 else 100%
        Total time: {total_time/3600:.1f} hours
        Average rate: {self.total_downloaded/total_time:.2f} images/second
        ==================================
        """)


if __name__ == "__main__":
    import sys

    # Create directories if they don't exist
    Path("logs").mkdir(exist_ok=True)
    Path("data").mkdir(exist_ok=True)

    # Check for test mode
    test_mode = '--test' in sys.argv

    # Run downloader
    downloader = ZooplusImageDownloader()

    try:
        downloader.run(test_mode=test_mode)
    except KeyboardInterrupt:
        logger.info("\n\nDownload interrupted by user")
        downloader.print_final_report()
        downloader.save_failed_downloads()
        downloader.save_checkpoint()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        downloader.save_failed_downloads()
        downloader.save_checkpoint()
        raise