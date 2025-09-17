#!/usr/bin/env python3
"""
Process Wikipedia breed data from GCS and update database
Reads JSON files from GCS and updates breeds_details and breeds_comprehensive_content tables
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List
from google.cloud import storage
from supabase import create_client, Client
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class GCSBreedProcessor:
    def __init__(self, gcs_folder: str = None):
        """Initialize the processor

        Args:
            gcs_folder: GCS folder path (e.g., 'scraped/wikipedia_breeds/20250917_162810')
        """
        # Initialize Supabase
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

        # Initialize GCS
        self.storage_client = storage.Client(project='careful-drummer-468512-p0')
        self.bucket = self.storage_client.bucket('lupito-content-raw-eu')

        # Set folder
        self.gcs_folder = gcs_folder or 'scraped/wikipedia_breeds/20250917_162810'

        # Stats
        self.stats = {
            'total': 0,
            'processed': 0,
            'updated_details': 0,
            'updated_content': 0,
            'failed': 0,
            'errors': []
        }

    def list_json_files(self) -> List[str]:
        """List all JSON files in the GCS folder"""
        prefix = self.gcs_folder + '/'
        blobs = self.bucket.list_blobs(prefix=prefix)
        json_files = []
        for blob in blobs:
            if blob.name.endswith('.json'):
                json_files.append(blob.name)
        return sorted(json_files)

    def download_json(self, blob_path: str) -> Dict:
        """Download and parse a JSON file from GCS"""
        blob = self.bucket.blob(blob_path)
        content = blob.download_as_text()
        return json.loads(content)

    def process_breed_data(self, breed_data: Dict) -> bool:
        """Process a single breed's data and update database"""
        breed_slug = breed_data.get('breed_slug')
        if not breed_slug:
            logger.error("No breed_slug in data")
            return False

        extracted = breed_data.get('extracted_data', {})

        try:
            # Update breeds_details table
            details_updated = self.update_breeds_details(breed_slug, extracted)

            # Update breeds_comprehensive_content table
            content_updated = self.update_comprehensive_content(breed_slug, breed_data, extracted)

            if details_updated:
                self.stats['updated_details'] += 1
            if content_updated:
                self.stats['updated_content'] += 1

            return details_updated or content_updated

        except Exception as e:
            logger.error(f"Error processing {breed_slug}: {e}")
            self.stats['errors'].append({
                'breed_slug': breed_slug,
                'error': str(e)
            })
            return False

    def update_breeds_details(self, breed_slug: str, extracted: Dict) -> bool:
        """Update the breeds_details table with extracted data"""
        update_data = {}

        # Weight data (with proper column names and type conversion)
        if 'weight_min_kg' in extracted and extracted['weight_min_kg'] is not None:
            update_data['weight_kg_min'] = float(extracted['weight_min_kg'])
        if 'weight_max_kg' in extracted and extracted['weight_max_kg'] is not None:
            update_data['weight_kg_max'] = float(extracted['weight_max_kg'])
        if 'weight_avg_kg' in extracted and extracted['weight_avg_kg'] is not None:
            update_data['adult_weight_avg_kg'] = float(extracted['weight_avg_kg'])

        # Height data (convert to integers)
        if 'height_min_cm' in extracted and extracted['height_min_cm'] is not None:
            update_data['height_cm_min'] = int(float(extracted['height_min_cm']))
        if 'height_max_cm' in extracted and extracted['height_max_cm'] is not None:
            update_data['height_cm_max'] = int(float(extracted['height_max_cm']))

        # Lifespan data (convert to integers)
        if 'lifespan_min_years' in extracted and extracted['lifespan_min_years'] is not None:
            update_data['lifespan_years_min'] = int(float(extracted['lifespan_min_years']))
        if 'lifespan_max_years' in extracted and extracted['lifespan_max_years'] is not None:
            update_data['lifespan_years_max'] = int(float(extracted['lifespan_max_years']))
        if 'lifespan_avg_years' in extracted and extracted['lifespan_avg_years'] is not None:
            update_data['lifespan_avg_years'] = float(extracted['lifespan_avg_years'])

        # Energy level
        if 'energy_level' in extracted:
            energy_mapping = {
                'low': 'low',
                'moderate': 'moderate',
                'high': 'high',
                'very high': 'very_high'
            }
            energy_value = extracted['energy_level'].lower()
            if energy_value in energy_mapping:
                update_data['energy'] = energy_mapping[energy_value]

        # Origin
        if extracted.get('origin'):
            update_data['origin'] = extracted['origin']

        # Mark data sources
        if any(k.startswith('weight') for k in update_data.keys()):
            update_data['weight_from'] = 'wikipedia'
        if any(k.startswith('height') for k in update_data.keys()):
            update_data['height_from'] = 'wikipedia'
        if any(k.startswith('lifespan') for k in update_data.keys()):
            update_data['lifespan_from'] = 'wikipedia'

        update_data['updated_at'] = datetime.now().isoformat()

        if update_data:
            try:
                response = self.supabase.table('breeds_details').update(
                    update_data
                ).eq('breed_slug', breed_slug).execute()
                logger.info(f"Updated breeds_details for {breed_slug}")
                return True
            except Exception as e:
                logger.error(f"Failed to update breeds_details for {breed_slug}: {e}")
                return False
        return False

    def update_comprehensive_content(self, breed_slug: str, breed_data: Dict, extracted: Dict) -> bool:
        """Update the breeds_comprehensive_content table with rich content"""
        content_data = {
            'breed_slug': breed_slug,
            'wikipedia_url': breed_data.get('wikipedia_url'),
            'gcs_html_path': breed_data.get('gcs_html_path'),
            'gcs_json_path': breed_data.get('gcs_json_path'),
            'scraped_at': breed_data.get('scraped_at'),

            # Rich content fields
            'introduction': extracted.get('introduction'),
            'history': extracted.get('history'),
            'history_brief': extracted.get('history_brief'),
            'personality_description': extracted.get('personality_description'),
            'personality_traits': extracted.get('personality_traits'),
            'temperament': extracted.get('temperament'),
            'good_with_children': extracted.get('good_with_children'),
            'good_with_pets': extracted.get('good_with_pets'),
            'intelligence_noted': extracted.get('intelligence_noted'),
            'grooming_needs': extracted.get('grooming_needs'),
            'grooming_frequency': extracted.get('grooming_frequency'),
            'exercise_needs_detail': extracted.get('exercise_needs_detail'),
            'exercise_level': extracted.get('exercise_level'),
            'training_tips': extracted.get('training_tips'),
            'general_care': extracted.get('general_care'),
            'fun_facts': extracted.get('fun_facts'),
            'has_world_records': extracted.get('has_world_records'),
            'working_roles': extracted.get('working_roles'),
            'breed_standard': extracted.get('breed_standard'),
            'recognized_by': extracted.get('recognized_by'),
            'color_varieties': extracted.get('color_varieties'),
            'health_issues': extracted.get('health_issues'),
            'coat': extracted.get('coat'),
            'colors': extracted.get('colors'),
            'updated_at': datetime.now().isoformat()
        }

        # Remove None values
        content_data = {k: v for k, v in content_data.items() if v is not None}

        if content_data:
            try:
                # Upsert (insert or update)
                response = self.supabase.table('breeds_comprehensive_content').upsert(
                    content_data
                ).execute()
                logger.info(f"Updated breeds_comprehensive_content for {breed_slug}")
                return True
            except Exception as e:
                logger.error(f"Failed to update breeds_comprehensive_content for {breed_slug}: {e}")
                return False
        return False

    def process_all(self):
        """Process all JSON files in the GCS folder"""
        logger.info(f"Starting processing of GCS folder: {self.gcs_folder}")

        # List all JSON files
        json_files = self.list_json_files()
        self.stats['total'] = len(json_files)
        logger.info(f"Found {self.stats['total']} JSON files to process")

        # Process each file
        for i, json_path in enumerate(json_files, 1):
            breed_name = json_path.split('/')[-1].replace('.json', '')
            logger.info(f"[{i}/{self.stats['total']}] Processing {breed_name}")

            try:
                # Download and parse JSON
                breed_data = self.download_json(json_path)

                # Process the data
                if self.process_breed_data(breed_data):
                    self.stats['processed'] += 1
                else:
                    self.stats['failed'] += 1

            except Exception as e:
                logger.error(f"Failed to process {json_path}: {e}")
                self.stats['failed'] += 1
                self.stats['errors'].append({
                    'file': json_path,
                    'error': str(e)
                })

        # Print summary
        logger.info("=" * 50)
        logger.info("Processing Complete!")
        logger.info(f"Total files: {self.stats['total']}")
        logger.info(f"Successfully processed: {self.stats['processed']}")
        logger.info(f"Updated breeds_details: {self.stats['updated_details']}")
        logger.info(f"Updated comprehensive_content: {self.stats['updated_content']}")
        logger.info(f"Failed: {self.stats['failed']}")

        if self.stats['errors']:
            logger.warning(f"\nErrors encountered ({len(self.stats['errors'])}):")
            for error in self.stats['errors'][:5]:  # Show first 5 errors
                logger.warning(f"  - {error}")

        return self.stats


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description='Process Wikipedia breed data from GCS')
    parser.add_argument('--folder', type=str,
                       default='scraped/wikipedia_breeds/20250917_162810',
                       help='GCS folder path')
    parser.add_argument('--test', action='store_true',
                       help='Test mode - process only first 5 breeds')

    args = parser.parse_args()

    processor = GCSBreedProcessor(gcs_folder=args.folder)

    if args.test:
        # Test mode - process only first 5
        logger.info("TEST MODE - Processing only first 5 breeds")
        json_files = processor.list_json_files()[:5]
        processor.stats['total'] = len(json_files)

        for i, json_path in enumerate(json_files, 1):
            breed_name = json_path.split('/')[-1].replace('.json', '')
            logger.info(f"[{i}/{processor.stats['total']}] Processing {breed_name}")

            try:
                breed_data = processor.download_json(json_path)
                if processor.process_breed_data(breed_data):
                    processor.stats['processed'] += 1
                else:
                    processor.stats['failed'] += 1
            except Exception as e:
                logger.error(f"Failed: {e}")
                processor.stats['failed'] += 1

        logger.info(f"\nTest complete: {processor.stats}")
    else:
        processor.process_all()


if __name__ == "__main__":
    main()