#!/usr/bin/env python3
"""
Dog Breed API Integration Script
Integrates with multiple free dog breed APIs to gather structured data
for missing fields in our breeds database.
"""

import os
import json
import time
import logging
import requests
from typing import Dict, Any, List, Optional
from supabase import create_client, Client
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class DogBreedAPIIntegrator:
    def __init__(self):
        """Initialize the API integrator"""
        # Supabase setup
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

        # Stats tracking
        self.stats = {
            'total_breeds': 0,
            'api_calls': 0,
            'breeds_updated': 0,
            'fields_populated': 0,
            'dog_api_success': 0,
            'dog_api_failed': 0,
            'ninja_api_success': 0,
            'ninja_api_failed': 0
        }

    def get_breeds_with_missing_fields(self) -> List[Dict[str, Any]]:
        """Get breeds that are missing key fields"""
        try:
            # Get breeds with missing temperament, compatibility, or other structured data
            response = self.supabase.table('breeds_comprehensive_content').select(
                'breed_slug, temperament, good_with_children, good_with_pets, '
                'exercise_level, grooming_frequency, personality_traits'
            ).execute()

            breeds_needing_api_data = []
            for breed in response.data:
                missing_fields = []

                # Check which fields are missing or could be enhanced
                temperament = breed.get('temperament')
                if not temperament or (isinstance(temperament, str) and temperament.strip() == ''):
                    missing_fields.append('temperament')

                if breed.get('good_with_children') is None:
                    missing_fields.append('good_with_children')
                if breed.get('good_with_pets') is None:
                    missing_fields.append('good_with_pets')
                if not breed.get('exercise_level'):
                    missing_fields.append('exercise_level')
                if not breed.get('grooming_frequency'):
                    missing_fields.append('grooming_frequency')

                personality_traits = breed.get('personality_traits')
                if not personality_traits or (isinstance(personality_traits, str) and personality_traits.strip() == ''):
                    missing_fields.append('personality_traits')

                if missing_fields:
                    breed['missing_fields'] = missing_fields
                    breeds_needing_api_data.append(breed)

            logger.info(f"Found {len(breeds_needing_api_data)} breeds needing API data")
            return breeds_needing_api_data

        except Exception as e:
            logger.error(f"Error getting breeds with missing fields: {e}")
            return []

    def normalize_breed_name(self, breed_slug: str) -> str:
        """Convert breed slug to standard format for API calls"""
        # Convert slug to proper breed name
        name = breed_slug.replace('-', ' ').title()

        # Handle common variations
        name_mappings = {
            'German Shepherd Dog': 'German Shepherd',
            'Labrador Retriever': 'Labrador',
            'Golden Retriever': 'Golden Retriever',
            'French Bulldog': 'French Bulldog',
            'Yorkshire Terrier': 'Yorkshire Terrier',
            'American Pit Bull Terrier': 'Pit Bull',
            'American Staffordshire Terrier': 'American Staffordshire Terrier',
            'Cavalier King Charles Spaniel': 'Cavalier King Charles Spaniel'
        }

        return name_mappings.get(name, name)

    def fetch_from_dog_api(self, breed_name: str) -> Optional[Dict[str, Any]]:
        """Fetch breed data from The Dog API (free tier)"""
        try:
            # The Dog API endpoint
            url = "https://api.thedogapi.com/v1/breeds/search"
            params = {'q': breed_name}

            response = requests.get(url, params=params, timeout=10)
            self.stats['api_calls'] += 1

            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    breed_data = data[0]  # Take first match
                    self.stats['dog_api_success'] += 1

                    # Extract useful fields
                    extracted_data = {}

                    # Temperament (convert to array format for PostgreSQL)
                    if 'temperament' in breed_data and breed_data['temperament']:
                        temperament_array = f"{{{breed_data['temperament']}}}"
                        extracted_data['temperament'] = temperament_array
                        # Also use temperament to enhance personality_traits
                        extracted_data['personality_traits'] = temperament_array

                    # Exercise level
                    if 'energy_level' in breed_data:
                        extracted_data['exercise_level'] = self.normalize_energy_level(
                            breed_data['energy_level']
                        )

                    # Child and pet compatibility
                    if 'child_friendly' in breed_data:
                        extracted_data['good_with_children'] = self.normalize_rating(
                            breed_data['child_friendly']
                        )

                    # Other traits mapping to available fields
                    traits_mapping = {
                        'grooming': 'grooming_frequency',
                        'social_needs': 'good_with_pets'
                    }

                    for api_field, our_field in traits_mapping.items():
                        if api_field in breed_data:
                            if our_field == 'grooming_frequency':
                                extracted_data[our_field] = self.normalize_grooming_level(
                                    breed_data[api_field]
                                )
                            else:
                                extracted_data[our_field] = self.normalize_rating(
                                    breed_data[api_field]
                                )

                    logger.info(f"✓ Dog API data for {breed_name}: {list(extracted_data.keys())}")
                    return extracted_data

            self.stats['dog_api_failed'] += 1
            logger.info(f"- No Dog API data for {breed_name}")
            return None

        except Exception as e:
            self.stats['dog_api_failed'] += 1
            logger.error(f"Error fetching from Dog API for {breed_name}: {e}")
            return None

    def fetch_from_api_ninjas(self, breed_name: str) -> Optional[Dict[str, Any]]:
        """Fetch breed data from API Ninjas (requires API key)"""
        api_key = os.getenv('API_NINJAS_KEY')
        if not api_key:
            logger.warning("API_NINJAS_KEY not found, skipping API Ninjas")
            return None

        try:
            url = "https://api.api-ninjas.com/v1/dogs"
            headers = {'X-Api-Key': api_key}
            params = {'name': breed_name}

            response = requests.get(url, headers=headers, params=params, timeout=10)
            self.stats['api_calls'] += 1

            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    breed_data = data[0]
                    self.stats['ninja_api_success'] += 1

                    # Extract structured ratings (1-5 scale)
                    extracted_data = {}

                    # Map API fields to our fields (only available fields)
                    field_mappings = {
                        'energy': 'exercise_level',
                        'grooming': 'grooming_frequency',
                        'good_with_children': 'good_with_children',
                        'good_with_other_dogs': 'good_with_pets'
                    }

                    for api_field, our_field in field_mappings.items():
                        if api_field in breed_data and breed_data[api_field]:
                            # Convert 1-5 rating to our text scale
                            rating = breed_data[api_field]
                            if our_field in ['good_with_children', 'good_with_pets']:
                                # Boolean conversion
                                extracted_data[our_field] = rating >= 4
                            else:
                                # Text level conversion
                                extracted_data[our_field] = self.convert_rating_to_text(rating)

                    logger.info(f"✓ API Ninjas data for {breed_name}: {list(extracted_data.keys())}")
                    return extracted_data

            self.stats['ninja_api_failed'] += 1
            logger.info(f"- No API Ninjas data for {breed_name}")
            return None

        except Exception as e:
            self.stats['ninja_api_failed'] += 1
            logger.error(f"Error fetching from API Ninjas for {breed_name}: {e}")
            return None

    def normalize_energy_level(self, value: Any) -> Optional[str]:
        """Normalize energy level to our scale (low/moderate/high)"""
        if isinstance(value, (int, float)):
            if value <= 2:
                return 'low'
            elif value <= 3:
                return 'moderate'
            else:
                return 'high'
        elif isinstance(value, str):
            value_lower = value.lower()
            if 'low' in value_lower or 'calm' in value_lower:
                return 'low'
            elif 'moderate' in value_lower or 'medium' in value_lower:
                return 'moderate'
            elif 'high' in value_lower or 'active' in value_lower or 'energetic' in value_lower:
                return 'high'
        return None

    def normalize_grooming_level(self, value: Any) -> Optional[str]:
        """Normalize grooming level to our scale (minimal/weekly/daily)"""
        if isinstance(value, (int, float)):
            if value <= 2:
                return 'minimal'
            elif value <= 3:
                return 'weekly'
            else:
                return 'daily'
        elif isinstance(value, str):
            value_lower = value.lower()
            if 'minimal' in value_lower or 'low' in value_lower:
                return 'minimal'
            elif 'weekly' in value_lower or 'moderate' in value_lower:
                return 'weekly'
            elif 'daily' in value_lower or 'high' in value_lower:
                return 'daily'
        return None

    def normalize_rating(self, value: Any) -> Optional[bool]:
        """Convert numeric rating to boolean (4+ = True)"""
        try:
            if isinstance(value, (int, float)):
                return value >= 4
            elif isinstance(value, str) and value.isdigit():
                return int(value) >= 4
        except:
            pass
        return None

    def convert_rating_to_text(self, rating: int) -> str:
        """Convert 1-5 rating to text level"""
        if rating <= 2:
            return 'low'
        elif rating <= 3:
            return 'moderate'
        else:
            return 'high'

    def update_breed_with_api_data(self, breed_slug: str, api_data: Dict[str, Any],
                                  missing_fields: List[str]) -> bool:
        """Update breed with API data - only missing fields"""
        try:
            # Only update fields that were missing and we have data for
            update_data = {}
            for field in missing_fields:
                if field in api_data:
                    update_data[field] = api_data[field]

            if not update_data:
                return False

            # Update the database
            result = self.supabase.table('breeds_comprehensive_content').update(
                update_data
            ).eq('breed_slug', breed_slug).execute()

            if result.data:
                self.stats['breeds_updated'] += 1
                self.stats['fields_populated'] += len(update_data)
                logger.info(f"✓ Updated {breed_slug} with API data: {', '.join(update_data.keys())}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error updating {breed_slug} with API data: {e}")
            return False

    def integrate_breed_apis(self, limit: Optional[int] = None):
        """Main method to integrate API data for all breeds"""
        logger.info("Starting dog breed API integration...")

        # Get breeds needing API data
        breeds = self.get_breeds_with_missing_fields()

        if limit:
            breeds = breeds[:limit]

        self.stats['total_breeds'] = len(breeds)
        logger.info(f"Will attempt API integration for {self.stats['total_breeds']} breeds")

        for i, breed in enumerate(breeds, 1):
            breed_slug = breed['breed_slug']
            missing_fields = breed['missing_fields']
            breed_name = self.normalize_breed_name(breed_slug)

            logger.info(f"\n[{i}/{self.stats['total_breeds']}] Processing {breed_name}...")
            logger.info(f"  Missing fields: {', '.join(missing_fields)}")

            # Try Dog API first (free)
            api_data = self.fetch_from_dog_api(breed_name)

            # Try API Ninjas if Dog API didn't provide enough data
            if not api_data or len(set(api_data.keys()) & set(missing_fields)) < len(missing_fields):
                ninja_data = self.fetch_from_api_ninjas(breed_name)
                if ninja_data:
                    if api_data:
                        # Merge data, preferring API Ninjas for conflicts
                        api_data.update(ninja_data)
                    else:
                        api_data = ninja_data

            # Update database with API data
            if api_data:
                self.update_breed_with_api_data(breed_slug, api_data, missing_fields)
            else:
                logger.info(f"  No API data found for {breed_name}")

            # Rate limiting
            time.sleep(1)

            # Progress update every 25 breeds
            if i % 25 == 0:
                self.log_progress()

        self.log_final_stats()

    def log_progress(self):
        """Log current progress"""
        logger.info(f"""
        Progress: {self.stats['breeds_updated']}/{self.stats['total_breeds']} breeds updated
        API calls made: {self.stats['api_calls']}
        Fields populated: {self.stats['fields_populated']}
        Dog API: {self.stats['dog_api_success']} success, {self.stats['dog_api_failed']} failed
        API Ninjas: {self.stats['ninja_api_success']} success, {self.stats['ninja_api_failed']} failed
        """)

    def log_final_stats(self):
        """Log final statistics"""
        logger.info(f"""
        ========================================
        DOG BREED API INTEGRATION COMPLETE
        ========================================
        Total breeds processed: {self.stats['total_breeds']}
        Breeds updated: {self.stats['breeds_updated']}
        Fields populated: {self.stats['fields_populated']}
        Total API calls: {self.stats['api_calls']}

        API Success Rates:
        - Dog API: {self.stats['dog_api_success']} success, {self.stats['dog_api_failed']} failed
        - API Ninjas: {self.stats['ninja_api_success']} success, {self.stats['ninja_api_failed']} failed
        ========================================
        """)

if __name__ == "__main__":
    import sys

    # Allow limiting for testing
    limit = None
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])
        logger.info(f"Limiting to {limit} breeds for testing")

    integrator = DogBreedAPIIntegrator()
    integrator.integrate_breed_apis(limit=limit)