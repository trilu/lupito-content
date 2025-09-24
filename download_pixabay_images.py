#!/usr/bin/env python3
"""
DOWNLOAD PIXABAY BREED IMAGES
Download and process images found in Pixabay search
"""

import os
import json
import requests
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
from PIL import Image, ImageOps
import io

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PixabayImageDownloader:
    def __init__(self):
        self.download_stats = {
            'breeds_processed': 0,
            'images_downloaded': 0,
            'thumbnails_created': 0,
            'errors_encountered': 0,
            'total_size_mb': 0
        }

        # Create directories for storing images
        self.image_dir = Path('pixabay_breed_images')
        self.image_dir.mkdir(exist_ok=True)

        # Subdirectories for originals and thumbnails
        (self.image_dir / 'originals').mkdir(exist_ok=True)
        (self.image_dir / 'thumbnails').mkdir(exist_ok=True)

        # Headers for downloading from Pixabay
        self.headers = {
            'User-Agent': 'BreedImageBot/1.0 (breed-image-download; contact@example.com) python-requests/2.31.0'
        }

    def load_search_results(self, results_file: str) -> Optional[Dict]:
        """Load search results from JSON file"""
        try:
            with open(results_file, 'r') as f:
                data = json.load(f)
                return data
        except Exception as e:
            logger.error(f"❌ Failed to load search results: {e}")
            return None

    def download_image(self, image_url: str, breed_slug: str, is_thumbnail: bool = False) -> Optional[bytes]:
        """Download image from URL"""
        try:
            response = requests.get(image_url, headers=self.headers, timeout=30)

            if response.status_code == 200:
                image_data = response.content
                size_mb = len(image_data) / (1024 * 1024)

                if not is_thumbnail:
                    self.download_stats['total_size_mb'] += size_mb

                logger.info(f"   ✅ Downloaded {breed_slug} {'thumbnail' if is_thumbnail else 'image'}: {size_mb:.1f}MB")
                return image_data
            else:
                logger.error(f"   ❌ Failed to download {breed_slug}: HTTP {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"   ❌ Error downloading {breed_slug}: {e}")
            return None

    def create_thumbnail(self, image_data: bytes, max_size: tuple = (400, 400)) -> Optional[bytes]:
        """Create thumbnail from image data"""
        try:
            # Open image from bytes
            image = Image.open(io.BytesIO(image_data))

            # Convert to RGB if necessary (handles PNG with transparency)
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')

            # Create thumbnail maintaining aspect ratio
            image.thumbnail(max_size, Image.Resampling.LANCZOS)

            # Save to bytes
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=85, optimize=True)
            return output.getvalue()

        except Exception as e:
            logger.error(f"   ⚠️ Failed to create thumbnail: {e}")
            return None

    def get_best_image_url(self, image_data: Dict) -> str:
        """Get the best quality image URL from Pixabay data"""
        # Prefer full HD, then large, then web format
        if image_data.get('full_hd_url'):
            return image_data['full_hd_url']
        elif image_data.get('large_url'):
            return image_data['large_url']
        else:
            return image_data.get('web_url', '')

    def process_breed_images(self, breed_slug: str, breed_data: Dict) -> bool:
        """Process and download images for a single breed"""
        try:
            breed_name = breed_data.get('breed_name', breed_slug)
            best_image = breed_data.get('best_image')

            if not best_image:
                logger.warning(f"   ⚠️ No best image found for {breed_slug}")
                return False

            logger.info(f"📷 Processing {breed_slug} ({breed_name})")

            # Get best image URL
            image_url = self.get_best_image_url(best_image)

            if not image_url:
                logger.error(f"   ❌ No image URL for {breed_slug}")
                return False

            # Log Pixabay image details
            width = best_image.get('width', 0)
            height = best_image.get('height', 0)
            views = best_image.get('views', 0)
            downloads = best_image.get('downloads', 0)
            image_id = best_image.get('id', '')

            logger.info(f"   📏 Pixabay ID: {image_id}")
            logger.info(f"   📊 Stats: {views} views, {downloads} downloads")
            logger.info(f"   🔗 URL: {image_url}")

            # Download original image
            image_data = self.download_image(image_url, breed_slug)
            if not image_data:
                return False

            # Save original image
            original_path = self.image_dir / 'originals' / f'{breed_slug}.jpg'
            with open(original_path, 'wb') as f:
                f.write(image_data)

            self.download_stats['images_downloaded'] += 1

            # Create and save thumbnail
            thumbnail_data = self.create_thumbnail(image_data)
            if thumbnail_data:
                thumbnail_path = self.image_dir / 'thumbnails' / f'{breed_slug}_thumb.jpg'
                with open(thumbnail_path, 'wb') as f:
                    f.write(thumbnail_data)

                self.download_stats['thumbnails_created'] += 1

                # Log final info
                logger.info(f"   📏 Size: {width}x{height}")
                logger.info(f"   📜 License: Pixabay License (commercial use allowed)")
                logger.info(f"   💾 Saved: {original_path.name} + {thumbnail_path.name}")

                return True
            else:
                logger.warning(f"   ⚠️ Failed to create thumbnail for {breed_slug}")
                return True  # Still successful for original image

        except Exception as e:
            logger.error(f"   ❌ Error processing {breed_slug}: {e}")
            self.download_stats['errors_encountered'] += 1
            return False

    def download_all_images(self, results_file: str):
        """Download all images from search results"""
        logger.info("📥 STARTING PIXABAY IMAGE DOWNLOADS")
        logger.info("=" * 50)

        # Load search results
        search_data = self.load_search_results(results_file)
        if not search_data:
            return False

        results = search_data.get('results', {})
        successful_breeds = []

        logger.info(f"📊 DOWNLOAD PLAN:")
        logger.info(f"   - Total breeds found: {len(results)}")

        # Filter breeds that have images
        breeds_with_images = {slug: data for slug, data in results.items()
                             if data.get('best_image') is not None}

        logger.info(f"   - Breeds with images: {len(breeds_with_images)}")
        logger.info(f"   - Download directory: {self.image_dir}")

        # Process each breed
        for i, (breed_slug, breed_data) in enumerate(breeds_with_images.items(), 1):
            logger.info(f"\n[{i}/{len(breeds_with_images)}] {breed_slug}")

            if self.process_breed_images(breed_slug, breed_data):
                successful_breeds.append(breed_slug)

            self.download_stats['breeds_processed'] += 1

            # Progress update
            if i % 3 == 0:
                self.print_progress_stats()

        # Generate final report
        self.generate_download_report(successful_breeds, results_file)
        return len(successful_breeds) == len(breeds_with_images)

    def print_progress_stats(self):
        """Print current download progress"""
        logger.info(f"   📊 Progress: {self.download_stats['breeds_processed']} breeds processed, "
                   f"{self.download_stats['images_downloaded']} images downloaded, "
                   f"{self.download_stats['thumbnails_created']} thumbnails created")

    def generate_download_report(self, successful_breeds: List[str], source_file: str):
        """Generate download completion report"""
        logger.info("\n" + "=" * 50)
        logger.info("🎉 PIXABAY IMAGE DOWNLOADS COMPLETE")
        logger.info("=" * 50)

        logger.info(f"📊 DOWNLOAD RESULTS:")
        logger.info(f"   - Breeds processed: {self.download_stats['breeds_processed']}")
        logger.info(f"   - Images downloaded: {self.download_stats['images_downloaded']}")
        logger.info(f"   - Thumbnails created: {self.download_stats['thumbnails_created']}")
        logger.info(f"   - Total size downloaded: {self.download_stats['total_size_mb']:.1f}MB")
        logger.info(f"   - Errors encountered: {self.download_stats['errors_encountered']}")

        success_rate = (len(successful_breeds) / self.download_stats['breeds_processed'] * 100) if self.download_stats['breeds_processed'] > 0 else 0
        logger.info(f"   - Success rate: {success_rate:.1f}%")

        logger.info(f"\n✅ SUCCESSFULLY DOWNLOADED:")
        for breed_slug in successful_breeds:
            logger.info(f"   • {breed_slug}")

        # Save download report
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'source_file': source_file,
            'download_type': 'pixabay_breed_images',
            'statistics': self.download_stats,
            'successful_breeds': successful_breeds,
            'success_rate': success_rate,
            'image_directory': str(self.image_dir)
        }

        report_filename = f'pixabay_image_downloads_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_filename, 'w') as f:
            json.dump(report_data, f, indent=2)

        logger.info(f"\n📋 Download report saved: {report_filename}")

        if success_rate >= 90:
            logger.info("\n🌟 DOWNLOAD SUCCESSFUL!")
            logger.info(f"🚀 Downloaded {len(successful_breeds)} breed images from Pixabay!")
            logger.info(f"📁 Images saved in: {self.image_dir}")
            logger.info(f"📜 All images are under Pixabay License (commercial use allowed)")
        else:
            logger.warning(f"\n⚠️ Downloads completed with {success_rate:.1f}% success rate")

if __name__ == '__main__':
    downloader = PixabayImageDownloader()

    # Find the most recent Pixabay search results file
    search_files = [f for f in os.listdir('.') if f.startswith('pixabay_search_results_') and f.endswith('.json')]

    if search_files:
        # Use the most recent search results
        latest_file = max(search_files, key=lambda f: os.path.getctime(f))
        logger.info(f"🔍 Using search results: {latest_file}")

        success = downloader.download_all_images(latest_file)
        if success:
            logger.info("\n✅ ALL PIXABAY IMAGES DOWNLOADED SUCCESSFULLY!")
        else:
            logger.warning("\n⚠️ SOME DOWNLOADS ENCOUNTERED ISSUES")
    else:
        logger.error("❌ No Pixabay search results file found. Run pixabay_breed_image_search.py first.")