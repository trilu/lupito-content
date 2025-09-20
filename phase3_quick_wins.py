#!/usr/bin/env python3

"""
PHASE 3: QUICK WINS COMPLETION
Target: 87% → 92% completeness
Focus: Complete partially-filled fields by mining existing data
"""

import os
import json
import re
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from supabase import create_client, Client
from google.cloud import storage
from google.cloud import secretmanager
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_secret(secret_id: str) -> str:
    """Get a secret from Google Cloud Secret Manager"""
    client = secretmanager.SecretManagerServiceClient()
    project_id = os.getenv('GCP_PROJECT', 'lupito-436004')
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    try:
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logging.error(f"Failed to get secret {secret_id}: {e}")
        # Fallback to environment variable
        return os.getenv(secret_id, '')

# Get Supabase configuration from secrets
SUPABASE_URL = get_secret('SUPABASE_URL') or os.getenv('SUPABASE_URL')
SUPABASE_KEY = get_secret('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_SERVICE_KEY')

# Initialize clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
gcs_client = storage.Client()

class Phase3QuickWins:
    def __init__(self, test_mode: bool = False, test_limit: int = 5):
        self.test_mode = test_mode
        self.test_limit = test_limit
        self.breeds_processed = 0
        self.breeds_updated = 0
        self.fields_filled = {}
        self.errors = {}

        # Target fields for Phase 3 (excluding bark_level)
        self.target_fields = [
            'lifespan',
            'colors',
            'personality_traits',
            'grooming_needs'
        ]

    def get_breeds_needing_fields(self) -> List[Dict]:
        """Get breeds missing target Phase 3 fields"""
        # Get all breeds with basic info
        query = supabase.table('breeds_unified_api').select(
            'breed_slug, display_name, temperament, coat, energy'
        ).execute()

        all_breeds = query.data

        # Get existing data from other tables to check what's missing
        breeds_needing_update = []

        for breed in all_breeds:
            breed_slug = breed['breed_slug']

            # Check breeds_published for lifespan, colors, personality_traits
            published = supabase.table('breeds_published').select(
                'lifespan, colors, personality_traits'
            ).eq('breed_slug', breed_slug).execute()

            # Check breeds_comprehensive_content for grooming_needs, color_varieties
            comprehensive = supabase.table('breeds_comprehensive_content').select(
                'grooming_needs, color_varieties, coat_length, coat_texture, grooming_frequency'
            ).eq('breed_slug', breed_slug).execute()

            # Merge the data
            breed_data = breed.copy()
            if published.data:
                breed_data.update(published.data[0])
            if comprehensive.data:
                breed_data.update(comprehensive.data[0])

            # Check if breed needs any target fields
            needs_update = False
            if not breed_data.get('lifespan'):
                needs_update = True
            if not breed_data.get('colors'):
                needs_update = True
            if not breed_data.get('personality_traits'):
                needs_update = True
            if not breed_data.get('grooming_needs'):
                needs_update = True

            if needs_update:
                breeds_needing_update.append(breed_data)

        return breeds_needing_update

    def extract_lifespan_from_wikipedia(self, breed_slug: str) -> Optional[str]:
        """Extract lifespan from Wikipedia content in GCS"""
        try:
            bucket = gcs_client.bucket('breed-wikipedia-raw')
            blob = bucket.blob(f'wikipedia/{breed_slug}.html')

            if not blob.exists():
                return None

            content = blob.download_as_text()
            soup = BeautifulSoup(content, 'html.parser')

            # Look for lifespan in infobox
            infobox = soup.find('table', class_='infobox')
            if infobox:
                for row in infobox.find_all('tr'):
                    th = row.find('th')
                    if th and 'life' in th.text.lower():
                        td = row.find('td')
                        if td:
                            lifespan_text = td.get_text(strip=True)
                            # Clean up the text
                            lifespan_text = re.sub(r'\[\d+\]', '', lifespan_text)
                            lifespan_text = lifespan_text.replace('years', '').strip()
                            if lifespan_text:
                                return lifespan_text

            # Search in text for patterns like "10-12 years"
            text = soup.get_text()
            patterns = [
                r'(?:live|lifespan|life expectancy).*?(\d+[-–]\d+)\s*years',
                r'(\d+[-–]\d+)\s*years?\s*(?:life|lifespan)',
                r'average.*?(\d+[-–]\d+)\s*years'
            ]

            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return match.group(1).replace('–', '-')

        except Exception as e:
            logging.debug(f"Error extracting lifespan for {breed_slug}: {e}")

        return None

    def derive_colors_from_varieties(self, breed_info: Dict) -> Optional[List[str]]:
        """Derive colors list from color_varieties field"""
        if breed_info.get('color_varieties'):
            # Parse the color_varieties text
            varieties = breed_info['color_varieties']
            colors = []

            # Common color patterns
            color_words = [
                'black', 'white', 'brown', 'red', 'blue', 'gray', 'grey',
                'cream', 'fawn', 'brindle', 'tan', 'sable', 'gold', 'golden',
                'liver', 'chocolate', 'yellow', 'orange', 'silver', 'merle',
                'tri-color', 'tricolor', 'bicolor', 'bi-color', 'spotted',
                'patched', 'ticked', 'roan', 'wheaten', 'buff', 'mahogany'
            ]

            varieties_lower = varieties.lower()
            for color in color_words:
                if color in varieties_lower:
                    # Capitalize properly
                    if '-' in color:
                        colors.append(color.title())
                    else:
                        colors.append(color.capitalize())

            # Remove duplicates while preserving order
            seen = set()
            unique_colors = []
            for color in colors:
                if color.lower() not in seen:
                    seen.add(color.lower())
                    unique_colors.append(color)

            return unique_colors if unique_colors else None

        return None

    def extract_personality_from_temperament(self, breed_info: Dict) -> Optional[List[str]]:
        """Extract personality traits from temperament field"""
        temperament = breed_info.get('temperament')
        if not temperament:
            return None

        # Common personality trait mappings
        trait_patterns = {
            'friendly': ['friendly', 'sociable', 'social', 'outgoing'],
            'loyal': ['loyal', 'devoted', 'faithful'],
            'intelligent': ['intelligent', 'smart', 'clever', 'bright'],
            'playful': ['playful', 'fun-loving', 'spirited', 'lively'],
            'gentle': ['gentle', 'calm', 'docile', 'mild'],
            'protective': ['protective', 'guardian', 'watchful', 'alert'],
            'independent': ['independent', 'aloof', 'self-reliant'],
            'affectionate': ['affectionate', 'loving', 'cuddly', 'sweet'],
            'energetic': ['energetic', 'active', 'athletic', 'dynamic'],
            'confident': ['confident', 'bold', 'fearless', 'courageous'],
            'trainable': ['trainable', 'obedient', 'responsive', 'eager to please'],
            'patient': ['patient', 'tolerant', 'good-natured']
        }

        traits = []
        temp_lower = temperament.lower()

        for trait, patterns in trait_patterns.items():
            for pattern in patterns:
                if pattern in temp_lower:
                    traits.append(trait.capitalize())
                    break

        # Remove duplicates while preserving order
        seen = set()
        unique_traits = []
        for trait in traits:
            if trait.lower() not in seen:
                seen.add(trait.lower())
                unique_traits.append(trait)

        return unique_traits[:5] if unique_traits else None  # Limit to 5 traits

    def derive_grooming_needs(self, breed_info: Dict) -> Optional[str]:
        """Derive grooming needs from coat characteristics"""
        coat = breed_info.get('coat', '')
        coat_length = breed_info.get('coat_length', '')
        coat_texture = breed_info.get('coat_texture', '')
        grooming_freq = breed_info.get('grooming_frequency', '')

        # Build grooming needs description
        needs = []

        # Based on coat length
        if 'long' in str(coat_length).lower() or 'long' in coat.lower():
            needs.append("Regular brushing required to prevent matting")
        elif 'short' in str(coat_length).lower() or 'short' in coat.lower():
            needs.append("Minimal grooming with weekly brushing")
        elif 'medium' in str(coat_length).lower():
            needs.append("Moderate grooming with regular brushing")

        # Based on coat texture
        if 'curly' in str(coat_texture).lower() or 'curly' in coat.lower():
            needs.append("Professional grooming recommended every 6-8 weeks")
        elif 'wire' in str(coat_texture).lower() or 'wiry' in coat.lower():
            needs.append("Hand-stripping or professional trimming needed")
        elif 'double' in coat.lower():
            needs.append("Extra brushing during shedding seasons")

        # Based on grooming frequency
        if grooming_freq:
            if 'daily' in grooming_freq.lower():
                needs.append("Daily brushing essential")
            elif 'weekly' in grooming_freq.lower():
                needs.append("Weekly grooming sessions recommended")

        if needs:
            return '. '.join(needs[:2])  # Limit to 2 statements

        # Default based on general coat info
        if coat:
            if 'hairless' in coat.lower():
                return "Minimal grooming but requires skin care"
            elif 'smooth' in coat.lower():
                return "Low maintenance with occasional brushing"

        return None

    def process_breed(self, breed: Dict) -> Dict:
        """Process a single breed for Phase 3 fields"""
        updates = {}
        breed_slug = breed['breed_slug']

        # 1. Lifespan
        if not breed.get('lifespan'):
            lifespan = self.extract_lifespan_from_wikipedia(breed_slug)
            if lifespan:
                updates['lifespan'] = lifespan

        # 2. Colors
        if not breed.get('colors') and breed.get('color_varieties'):
            colors = self.derive_colors_from_varieties(breed)
            if colors:
                updates['colors'] = colors

        # 3. Personality traits
        if not breed.get('personality_traits') and breed.get('temperament'):
            traits = self.extract_personality_from_temperament(breed)
            if traits:
                updates['personality_traits'] = traits

        # 4. Grooming needs
        if not breed.get('grooming_needs'):
            grooming = self.derive_grooming_needs(breed)
            if grooming:
                updates['grooming_needs'] = grooming

        return updates

    def update_breed(self, breed_slug: str, updates: Dict) -> bool:
        """Update breed in database"""
        if not updates:
            return False

        try:
            # Update in appropriate table based on fields
            if any(field in updates for field in ['lifespan', 'colors', 'personality_traits']):
                # These go to breeds_published
                published_updates = {k: v for k, v in updates.items()
                                   if k in ['lifespan', 'colors', 'personality_traits']}
                if published_updates:
                    supabase.table('breeds_published').upsert({
                        'breed_slug': breed_slug,
                        **published_updates
                    }, on_conflict='breed_slug').execute()

            if 'grooming_needs' in updates:
                # This goes to breeds_comprehensive_content
                supabase.table('breeds_comprehensive_content').upsert({
                    'breed_slug': breed_slug,
                    'grooming_needs': updates['grooming_needs']
                }, on_conflict='breed_slug').execute()

            # Track fields filled
            for field in updates:
                self.fields_filled[field] = self.fields_filled.get(field, 0) + 1

            return True

        except Exception as e:
            logging.error(f"Failed to update {breed_slug}: {e}")
            self.errors[breed_slug] = str(e)
            return False

    def run(self):
        """Run Phase 3 quick wins processing"""
        logging.info("=" * 80)
        logging.info("PHASE 3: QUICK WINS COMPLETION")
        logging.info("=" * 80)

        if self.test_mode:
            logging.info(f"Running in TEST MODE ({self.test_limit} breeds)...")

        # Get breeds needing fields
        logging.info("Fetching breeds needing Phase 3 fields...")
        breeds = self.get_breeds_needing_fields()
        logging.info(f"Found {len(breeds)} breeds needing Phase 3 fields")

        # Apply test limit if in test mode
        if self.test_mode:
            breeds = breeds[:self.test_limit]

        logging.info(f"Processing {len(breeds)} breeds for Phase 3 fields")
        logging.info(f"Target fields: {', '.join(self.target_fields)}")

        # Process each breed
        for i, breed in enumerate(breeds, 1):
            breed_slug = breed['breed_slug']
            display_name = breed['display_name']

            logging.info(f"[{i}/{len(breeds)}] Processing {display_name}...")

            updates = self.process_breed(breed)

            if updates:
                if self.update_breed(breed_slug, updates):
                    self.breeds_updated += 1
                    field_list = ', '.join(updates.keys())
                    logging.info(f"  ✓ Updated {display_name}: {field_list}")
                else:
                    logging.error(f"  ✗ Failed to update {display_name}")
            else:
                logging.info(f"  No new fields generated for {display_name}")

            self.breeds_processed += 1

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print processing summary"""
        logging.info("\n" + "=" * 80)
        logging.info("PHASE 3 COMPLETE")
        logging.info("=" * 80)
        logging.info(f"Total breeds processed: {self.breeds_processed}")
        logging.info(f"Breeds updated: {self.breeds_updated}")

        total_fields = sum(self.fields_filled.values())
        logging.info(f"Total fields filled: {total_fields}")

        if self.fields_filled:
            logging.info("\nFields filled:")
            for field, count in sorted(self.fields_filled.items(),
                                      key=lambda x: x[1], reverse=True):
                logging.info(f"  {field}: {count}")

        if self.errors:
            logging.info(f"\nErrors encountered: {len(self.errors)}")
            for breed, error in list(self.errors.items())[:5]:
                logging.info(f"  {breed}: {error}")

        # Calculate success metrics
        success_rate = (self.breeds_updated / self.breeds_processed * 100) if self.breeds_processed > 0 else 0
        logging.info(f"\nSuccess rate: {success_rate:.1f}%")

        # Estimate completeness gain
        estimated_gain = total_fields * 0.003  # Rough estimate
        logging.info(f"Estimated completeness gain: +{estimated_gain:.2f}%")
        logging.info("\n" + "=" * 80)

def main():
    # Check for test mode
    import sys
    test_mode = '--test' in sys.argv or len(sys.argv) > 1 and sys.argv[1] == 'test'

    if not test_mode:
        print("\n" + "=" * 80)
        print("PHASE 3: QUICK WINS - FULL RUN")
        print("=" * 80)
        print("\nThis will process ALL breeds needing Phase 3 fields.")
        print("Expected outcome: +5% completeness gain")
        print("\nProceed with full run? (yes/no): ", end='')

        response = input().strip().lower()
        if response != 'yes':
            print("Aborted.")
            return

    processor = Phase3QuickWins(test_mode=test_mode)
    processor.run()

if __name__ == "__main__":
    main()