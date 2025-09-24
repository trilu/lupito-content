#!/usr/bin/env python3
"""
UPLOAD PIXABAY BREED IMAGES TO GOOGLE CLOUD STORAGE
Upload downloaded Pixabay breed images to public GCS bucket using gsutil commands
"""

import os
import json
import subprocess
import logging
from datetime import datetime
from typing import List, Optional, Dict
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PixabayGCSUploader:
    def __init__(self):
        self.upload_stats = {
            'images_uploaded': 0,
            'thumbnails_uploaded': 0,
            'errors_encountered': 0,
            'total_size_uploaded_mb': 0
        }

        # GCS configuration - using the public bucket
        self.bucket_name = 'lupito-breed-images-public'

        # Local image directory for Pixabay images
        self.image_dir = Path('pixabay_breed_images')

    def run_gsutil_command(self, command: List[str]) -> tuple:
        """Run a gsutil command and return success status and output"""
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            return False, e.stderr

    def upload_file_to_gcs(self, local_path: Path, gcs_path: str) -> bool:
        """Upload a single file to GCS using gsutil"""
        try:
            # Upload the file
            upload_command = [
                'gsutil', 'cp',
                str(local_path),
                f'gs://{self.bucket_name}/{gcs_path}'
            ]

            success, output = self.run_gsutil_command(upload_command)
            if not success:
                logger.error(f"   ❌ Failed to upload {local_path.name}: {output}")
                self.upload_stats['errors_encountered'] += 1
                return False

            # Make it publicly accessible
            acl_command = [
                'gsutil', 'acl', 'ch', '-u', 'AllUsers:R',
                f'gs://{self.bucket_name}/{gcs_path}'
            ]

            acl_success, acl_output = self.run_gsutil_command(acl_command)
            if not acl_success:
                logger.warning(f"   ⚠️ Failed to make {local_path.name} public: {acl_output}")

            # Get file size
            file_size_mb = local_path.stat().st_size / (1024 * 1024)
            self.upload_stats['total_size_uploaded_mb'] += file_size_mb

            # Generate public URL
            public_url = f"https://storage.googleapis.com/{self.bucket_name}/{gcs_path}"

            logger.info(f"   ✅ Uploaded {local_path.name}: {file_size_mb:.1f}MB")
            logger.info(f"   🔗 URL: {public_url}")

            return True

        except Exception as e:
            logger.error(f"   ❌ Error uploading {local_path.name}: {e}")
            self.upload_stats['errors_encountered'] += 1
            return False

    def upload_breed_images(self, breed_slug: str) -> dict:
        """Upload original and thumbnail images for a breed"""
        results = {
            'breed_slug': breed_slug,
            'original_uploaded': False,
            'thumbnail_uploaded': False,
            'original_url': None,
            'thumbnail_url': None
        }

        logger.info(f"📤 Uploading {breed_slug}")

        # Upload original image (store in breeds/pixabay/ subfolder to distinguish from Wikimedia)
        original_path = self.image_dir / 'originals' / f'{breed_slug}.jpg'
        if original_path.exists():
            gcs_original_path = f'breeds/pixabay/{breed_slug}.jpg'
            if self.upload_file_to_gcs(original_path, gcs_original_path):
                results['original_uploaded'] = True
                results['original_url'] = f"https://storage.googleapis.com/{self.bucket_name}/{gcs_original_path}"
                self.upload_stats['images_uploaded'] += 1

        # Upload thumbnail
        thumbnail_path = self.image_dir / 'thumbnails' / f'{breed_slug}_thumb.jpg'
        if thumbnail_path.exists():
            gcs_thumbnail_path = f'breeds/pixabay/{breed_slug}_thumb.jpg'
            if self.upload_file_to_gcs(thumbnail_path, gcs_thumbnail_path):
                results['thumbnail_uploaded'] = True
                results['thumbnail_url'] = f"https://storage.googleapis.com/{self.bucket_name}/{gcs_thumbnail_path}"
                self.upload_stats['thumbnails_uploaded'] += 1

        success = results['original_uploaded'] and results['thumbnail_uploaded']
        if success:
            logger.info(f"   🎉 {breed_slug} upload complete")
        else:
            logger.warning(f"   ⚠️ {breed_slug} upload had issues")

        return results

    def check_gsutil_available(self) -> bool:
        """Check if gsutil is available"""
        try:
            result = subprocess.run(['gsutil', 'version'], capture_output=True, text=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def upload_all_images(self) -> List[dict]:
        """Upload all Pixabay breed images to GCS using gsutil"""
        logger.info("☁️ STARTING PIXABAY GCS UPLOAD WITH GSUTIL")
        logger.info("=" * 50)

        # Check if gsutil is available
        if not self.check_gsutil_available():
            logger.error("❌ gsutil is not available. Please install Google Cloud SDK.")
            return []

        # Get list of breeds from originals directory
        originals_dir = self.image_dir / 'originals'
        if not originals_dir.exists():
            logger.error("❌ No Pixabay originals directory found")
            return []

        breed_files = list(originals_dir.glob('*.jpg'))
        breed_slugs = [f.stem for f in breed_files]

        logger.info(f"📊 UPLOAD PLAN:")
        logger.info(f"   - Pixabay breeds to upload: {len(breed_slugs)}")
        logger.info(f"   - Target bucket: gs://{self.bucket_name}")
        logger.info(f"   - Target folder: breeds/pixabay/")
        logger.info(f"   - Image directory: {self.image_dir}")

        upload_results = []

        # Process each breed
        for i, breed_slug in enumerate(breed_slugs, 1):
            logger.info(f"\n[{i}/{len(breed_slugs)}] {breed_slug}")

            result = self.upload_breed_images(breed_slug)
            upload_results.append(result)

            # Progress update
            if i % 3 == 0:
                self.print_progress_stats()

        # Generate final report
        self.generate_upload_report(upload_results)
        return upload_results

    def print_progress_stats(self):
        """Print current upload progress"""
        logger.info(f"   📊 Progress: {self.upload_stats['images_uploaded']} images uploaded, "
                   f"{self.upload_stats['thumbnails_uploaded']} thumbnails uploaded")

    def generate_upload_report(self, upload_results: List[dict]):
        """Generate upload completion report"""
        logger.info("\n" + "=" * 50)
        logger.info("🎉 PIXABAY GCS UPLOAD COMPLETE")
        logger.info("=" * 50)

        successful_uploads = [r for r in upload_results if r['original_uploaded'] and r['thumbnail_uploaded']]

        logger.info(f"📊 UPLOAD RESULTS:")
        logger.info(f"   - Breeds processed: {len(upload_results)}")
        logger.info(f"   - Successful uploads: {len(successful_uploads)}")
        logger.info(f"   - Images uploaded: {self.upload_stats['images_uploaded']}")
        logger.info(f"   - Thumbnails uploaded: {self.upload_stats['thumbnails_uploaded']}")
        logger.info(f"   - Total size uploaded: {self.upload_stats['total_size_uploaded_mb']:.1f}MB")
        logger.info(f"   - Errors encountered: {self.upload_stats['errors_encountered']}")

        success_rate = (len(successful_uploads) / len(upload_results) * 100) if upload_results else 0
        logger.info(f"   - Success rate: {success_rate:.1f}%")

        logger.info(f"\n✅ SUCCESSFULLY UPLOADED BREEDS:")
        for result in successful_uploads:
            logger.info(f"   • {result['breed_slug']}")
            logger.info(f"     - Original: {result['original_url']}")
            logger.info(f"     - Thumbnail: {result['thumbnail_url']}")

        # Save upload report
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'upload_type': 'pixabay_breed_images_to_gcs_gsutil',
            'bucket_name': self.bucket_name,
            'statistics': self.upload_stats,
            'upload_results': upload_results,
            'successful_uploads': len(successful_uploads),
            'success_rate': success_rate
        }

        report_filename = f'pixabay_gcs_upload_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_filename, 'w') as f:
            json.dump(report_data, f, indent=2)

        logger.info(f"\n📋 Upload report saved: {report_filename}")

        if success_rate >= 90:
            logger.info("\n🌟 UPLOAD SUCCESSFUL!")
            logger.info(f"☁️ Uploaded {len(successful_uploads)} Pixabay breed images to GCS!")
            logger.info(f"🔗 Public bucket: gs://{self.bucket_name}/breeds/pixabay/")
            logger.info(f"📜 All images under Pixabay License (commercial use allowed)")
        else:
            logger.warning(f"\n⚠️ Uploads completed with {success_rate:.1f}% success rate")

        return upload_results

if __name__ == '__main__':
    uploader = PixabayGCSUploader()

    try:
        results = uploader.upload_all_images()
        successful_count = len([r for r in results if r['original_uploaded'] and r['thumbnail_uploaded']])

        if successful_count == len(results) and len(results) > 0:
            logger.info("\n✅ ALL PIXABAY IMAGES UPLOADED TO GCS SUCCESSFULLY!")
        elif successful_count > 0:
            logger.warning(f"\n⚠️ UPLOADED {successful_count}/{len(results)} BREEDS SUCCESSFULLY")
        else:
            logger.error("\n❌ NO IMAGES WERE UPLOADED SUCCESSFULLY")

    except Exception as e:
        logger.error(f"❌ Upload process failed: {e}")
        exit(1)