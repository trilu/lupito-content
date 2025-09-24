#!/usr/bin/env python3
"""
UPDATE DATABASE WITH PIXABAY IMAGE URLS
Update the breed database with the newly uploaded Pixabay image URLs
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PixabayDatabaseUpdater:
    def __init__(self):
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase: Client = create_client(supabase_url, supabase_key)

        self.update_stats = {
            'breeds_updated': 0,
            'breeds_failed': 0,
            'total_processed': 0
        }

        # GCS public bucket base URL
        self.bucket_base_url = 'https://storage.googleapis.com/lupito-breed-images-public/breeds/pixabay'

    def load_upload_report(self, report_file: str) -> Optional[Dict]:
        """Load upload report from JSON file"""
        try:
            with open(report_file, 'r') as f:
                data = json.load(f)
                return data
        except Exception as e:
            logger.error(f"❌ Failed to load upload report: {e}")
            return None

    def update_breed_image(self, breed_slug: str, image_url: str, thumbnail_url: str) -> bool:
        """Update a single breed's image URLs in the database"""
        try:
            # Update the breeds_comprehensive_content table
            result = self.supabase.table('breeds_comprehensive_content')\
                .update({
                    'image_url': image_url,
                    'image_thumbnail_url': thumbnail_url,
                    'image_source': 'pixabay',
                    'image_license': 'Pixabay License',
                    'updated_at': datetime.now().isoformat()
                })\
                .eq('breed_slug', breed_slug)\
                .execute()

            if result.data and len(result.data) > 0:
                logger.info(f"   ✅ Updated {breed_slug}")
                logger.info(f"      Image: {image_url}")
                logger.info(f"      Thumbnail: {thumbnail_url}")
                self.update_stats['breeds_updated'] += 1
                return True
            else:
                logger.warning(f"   ⚠️ No record found for {breed_slug}")
                self.update_stats['breeds_failed'] += 1
                return False

        except Exception as e:
            logger.error(f"   ❌ Error updating {breed_slug}: {e}")
            self.update_stats['breeds_failed'] += 1
            return False

    def process_upload_report(self, report_file: str) -> List[str]:
        """Process upload report and update database"""
        logger.info("📝 UPDATING DATABASE WITH PIXABAY IMAGE URLS")
        logger.info("=" * 60)

        # Load upload report
        report_data = self.load_upload_report(report_file)
        if not report_data:
            return []

        upload_results = report_data.get('upload_results', [])
        successful_breeds = []

        logger.info(f"📊 UPDATE PLAN:")
        logger.info(f"   - Total breeds in report: {len(upload_results)}")

        # Filter successful uploads
        successful_uploads = [r for r in upload_results if r['original_uploaded'] and r['thumbnail_uploaded']]
        logger.info(f"   - Successful uploads to process: {len(successful_uploads)}")

        # Process each successful upload
        for i, result in enumerate(successful_uploads, 1):
            breed_slug = result['breed_slug']
            original_url = result['original_url']
            thumbnail_url = result['thumbnail_url']

            logger.info(f"\n[{i}/{len(successful_uploads)}] {breed_slug}")

            if self.update_breed_image(breed_slug, original_url, thumbnail_url):
                successful_breeds.append(breed_slug)

            self.update_stats['total_processed'] += 1

            # Progress update
            if i % 5 == 0:
                self.print_progress_stats()

        # Generate final report
        self.generate_update_report(successful_breeds, report_file)
        return successful_breeds

    def print_progress_stats(self):
        """Print current update progress"""
        logger.info(f"   📊 Progress: {self.update_stats['breeds_updated']} updated, "
                   f"{self.update_stats['breeds_failed']} failed, "
                   f"{self.update_stats['total_processed']} processed")

    def generate_update_report(self, successful_breeds: List[str], source_file: str):
        """Generate database update completion report"""
        logger.info("\n" + "=" * 60)
        logger.info("🎉 DATABASE UPDATE COMPLETE")
        logger.info("=" * 60)

        logger.info(f"📊 UPDATE RESULTS:")
        logger.info(f"   - Breeds processed: {self.update_stats['total_processed']}")
        logger.info(f"   - Successfully updated: {self.update_stats['breeds_updated']}")
        logger.info(f"   - Failed updates: {self.update_stats['breeds_failed']}")

        success_rate = (self.update_stats['breeds_updated'] / self.update_stats['total_processed'] * 100) if self.update_stats['total_processed'] > 0 else 0
        logger.info(f"   - Success rate: {success_rate:.1f}%")

        logger.info(f"\n✅ SUCCESSFULLY UPDATED BREEDS:")
        for breed_slug in successful_breeds:
            logger.info(f"   • {breed_slug}")

        # Save update report
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'source_file': source_file,
            'update_type': 'pixabay_image_urls_database',
            'statistics': self.update_stats,
            'successful_breeds': successful_breeds,
            'success_rate': success_rate
        }

        report_filename = f'pixabay_db_update_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_filename, 'w') as f:
            json.dump(report_data, f, indent=2)

        logger.info(f"\n📋 Update report saved: {report_filename}")

        if success_rate >= 90:
            logger.info("\n🌟 DATABASE UPDATE SUCCESSFUL!")
            logger.info(f"🚀 Updated {len(successful_breeds)} breed records with Pixabay images!")
            logger.info(f"📜 All images are under Pixabay License (commercial use allowed)")
        else:
            logger.warning(f"\n⚠️ Database update completed with {success_rate:.1f}% success rate")

        return successful_breeds

    def verify_database_updates(self, breed_slugs: List[str]):
        """Verify that database updates were applied correctly"""
        logger.info(f"\n🔍 VERIFYING DATABASE UPDATES FOR {len(breed_slugs)} BREEDS")
        logger.info("=" * 50)

        verified_count = 0
        failed_verifications = []

        for breed_slug in breed_slugs:
            try:
                result = self.supabase.table('breeds_comprehensive_content')\
                    .select('breed_slug, image_url, image_thumbnail_url, image_source')\
                    .eq('breed_slug', breed_slug)\
                    .execute()

                if result.data and len(result.data) > 0:
                    breed_data = result.data[0]
                    image_url = breed_data.get('image_url')
                    thumbnail_url = breed_data.get('image_thumbnail_url')
                    image_source = breed_data.get('image_source')

                    if image_url and thumbnail_url and image_source == 'pixabay':
                        if self.bucket_base_url in image_url and self.bucket_base_url in thumbnail_url:
                            logger.info(f"   ✅ {breed_slug} - URLs verified")
                            verified_count += 1
                        else:
                            logger.error(f"   ❌ {breed_slug} - URLs don't match expected format")
                            failed_verifications.append(breed_slug)
                    else:
                        logger.error(f"   ❌ {breed_slug} - Missing or invalid data")
                        failed_verifications.append(breed_slug)
                else:
                    logger.error(f"   ❌ {breed_slug} - No record found")
                    failed_verifications.append(breed_slug)

            except Exception as e:
                logger.error(f"   ❌ {breed_slug} - Verification error: {e}")
                failed_verifications.append(breed_slug)

        verification_rate = (verified_count / len(breed_slugs) * 100) if breed_slugs else 0
        logger.info(f"\n📊 VERIFICATION RESULTS:")
        logger.info(f"   - Breeds verified: {verified_count}/{len(breed_slugs)}")
        logger.info(f"   - Verification rate: {verification_rate:.1f}%")

        if failed_verifications:
            logger.warning(f"   - Failed verifications: {len(failed_verifications)}")
            for failed in failed_verifications:
                logger.warning(f"     • {failed}")

        return verified_count, failed_verifications

if __name__ == '__main__':
    updater = PixabayDatabaseUpdater()

    # Find the most recent upload report
    import glob
    upload_reports = glob.glob('pixabay_gcs_upload_report_*.json')

    if upload_reports:
        # Use the most recent upload report
        latest_report = max(upload_reports, key=lambda f: os.path.getctime(f))
        logger.info(f"🔍 Using upload report: {latest_report}")

        successful_breeds = updater.process_upload_report(latest_report)

        if successful_breeds:
            logger.info(f"\n✅ DATABASE UPDATE COMPLETED!")
            logger.info(f"📊 Updated {len(successful_breeds)} breed records")

            # Verify the updates
            verified_count, failed_verifications = updater.verify_database_updates(successful_breeds)

            if verified_count == len(successful_breeds):
                logger.info(f"\n🌟 ALL DATABASE UPDATES VERIFIED SUCCESSFULLY!")
            else:
                logger.warning(f"\n⚠️ {len(failed_verifications)} BREEDS FAILED VERIFICATION")
        else:
            logger.error(f"\n❌ NO BREEDS WERE UPDATED")
    else:
        logger.error("❌ No Pixabay upload report found. Run upload_pixabay_to_gcs.py first.")