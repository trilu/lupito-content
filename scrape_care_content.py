#!/usr/bin/env python3
"""
Scrape comprehensive care content for breeds from authoritative sources
Targets grooming, exercise, training, health, and feeding information
"""

import os
import time
import json
import logging
import requests
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import re

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Supabase
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(supabase_url, supabase_key)

# Care content sources and URL patterns
CARE_SOURCES = {
    'akc': {
        'base_url': 'https://www.akc.org/dog-breeds/{breed_slug}/',
        'care_sections': [
            'grooming', 'exercise', 'training', 'nutrition', 'health'
        ]
    },
    'petmd': {
        'base_url': 'https://www.petmd.com/dog/breeds/{breed_slug}',
        'care_sections': [
            'care', 'feeding', 'grooming', 'exercise'
        ]
    },
    'dogtime': {
        'base_url': 'https://dogtime.com/dog-breeds/{breed_slug}',
        'care_sections': [
            'care', 'grooming', 'exercise-needs', 'training'
        ]
    }
}

def normalize_breed_name_for_url(breed_name):
    """Convert breed name to URL-friendly format"""
    # Remove special characters and convert to lowercase
    normalized = re.sub(r'[^\w\s-]', '', breed_name.lower())
    # Replace spaces and underscores with hyphens
    normalized = re.sub(r'[\s_]+', '-', normalized)
    # Remove multiple consecutive hyphens
    normalized = re.sub(r'-+', '-', normalized)
    # Remove leading/trailing hyphens
    normalized = normalized.strip('-')

    return normalized

def get_breeds_missing_care_content():
    """Get breeds that have minimal or no care content"""

    result = supabase.table('breeds_comprehensive_content').select(
        'breed_slug, general_care'
    ).execute()

    missing_care = []
    for breed in result.data:
        care_content = breed.get('general_care', '')
        # Consider care content missing if empty or very short
        if not care_content or len(care_content.strip()) < 100:
            missing_care.append(breed['breed_slug'])

    return missing_care

def scrape_akc_care_content(breed_slug, breed_name):
    """Scrape care content from AKC website"""

    normalized_name = normalize_breed_name_for_url(breed_name)
    url = f"https://www.akc.org/dog-breeds/{normalized_name}/"

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            logger.warning(f"AKC page not found for {breed_name}: {url}")
            return None

        soup = BeautifulSoup(response.content, 'html.parser')

        care_sections = {}

        # Look for grooming information
        grooming_section = soup.find('section', {'data-module': 'grooming'}) or \
                          soup.find('div', class_=re.compile('grooming', re.I))
        if grooming_section:
            care_sections['grooming'] = grooming_section.get_text(strip=True)

        # Look for exercise information
        exercise_section = soup.find('section', {'data-module': 'exercise'}) or \
                          soup.find('div', class_=re.compile('exercise', re.I))
        if exercise_section:
            care_sections['exercise'] = exercise_section.get_text(strip=True)

        # Look for training information
        training_section = soup.find('section', {'data-module': 'training'}) or \
                          soup.find('div', class_=re.compile('training', re.I))
        if training_section:
            care_sections['training'] = training_section.get_text(strip=True)

        # Look for health information
        health_section = soup.find('section', {'data-module': 'health'}) or \
                        soup.find('div', class_=re.compile('health', re.I))
        if health_section:
            care_sections['health'] = health_section.get_text(strip=True)

        # Look for nutrition/feeding information
        nutrition_section = soup.find('section', {'data-module': 'nutrition'}) or \
                           soup.find('div', class_=re.compile('nutrition|feeding', re.I))
        if nutrition_section:
            care_sections['nutrition'] = nutrition_section.get_text(strip=True)

        if care_sections:
            logger.info(f"✅ Found AKC care content for {breed_name}")
            return care_sections
        else:
            logger.warning(f"⚠️ No care sections found on AKC for {breed_name}")
            return None

    except Exception as e:
        logger.error(f"Error scraping AKC for {breed_name}: {e}")
        return None

def scrape_petmd_care_content(breed_slug, breed_name):
    """Scrape care content from PetMD website"""

    normalized_name = normalize_breed_name_for_url(breed_name)
    url = f"https://www.petmd.com/dog/breeds/{normalized_name}"

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.content, 'html.parser')

        care_sections = {}

        # Look for care and grooming information
        care_content = soup.find('div', class_=re.compile('care|grooming', re.I))
        if care_content:
            care_sections['care'] = care_content.get_text(strip=True)

        # Look for exercise information
        exercise_content = soup.find('div', class_=re.compile('exercise', re.I))
        if exercise_content:
            care_sections['exercise'] = exercise_content.get_text(strip=True)

        if care_sections:
            logger.info(f"✅ Found PetMD care content for {breed_name}")
            return care_sections
        else:
            return None

    except Exception as e:
        logger.error(f"Error scraping PetMD for {breed_name}: {e}")
        return None

def combine_care_content(akc_content, petmd_content):
    """Combine care content from multiple sources into comprehensive text"""

    combined_sections = []

    # Combine grooming information
    grooming_parts = []
    if akc_content and 'grooming' in akc_content:
        grooming_parts.append(akc_content['grooming'])
    if petmd_content and 'care' in petmd_content:
        grooming_parts.append(petmd_content['care'])

    if grooming_parts:
        combined_sections.append(f"**Grooming:** {' '.join(grooming_parts)}")

    # Combine exercise information
    exercise_parts = []
    if akc_content and 'exercise' in akc_content:
        exercise_parts.append(akc_content['exercise'])
    if petmd_content and 'exercise' in petmd_content:
        exercise_parts.append(petmd_content['exercise'])

    if exercise_parts:
        combined_sections.append(f"**Exercise:** {' '.join(exercise_parts)}")

    # Add training information
    if akc_content and 'training' in akc_content:
        combined_sections.append(f"**Training:** {akc_content['training']}")

    # Add health information
    if akc_content and 'health' in akc_content:
        combined_sections.append(f"**Health:** {akc_content['health']}")

    # Add nutrition information
    if akc_content and 'nutrition' in akc_content:
        combined_sections.append(f"**Nutrition:** {akc_content['nutrition']}")

    return '\n\n'.join(combined_sections)

def update_breed_care_content(breed_slug, care_content):
    """Update breed care content in the database"""

    try:
        result = supabase.table('breeds_comprehensive_content').update({
            'general_care': care_content,
            'updated_at': datetime.now().isoformat()
        }).eq('breed_slug', breed_slug).execute()

        if result.data:
            return True
        else:
            return False

    except Exception as e:
        logger.error(f"Database update error for {breed_slug}: {e}")
        return False

def scrape_care_content_for_breeds():
    """Main function to scrape care content for breeds missing it"""

    logger.info("Starting care content scraping for breeds...")

    # Get breeds missing care content
    missing_care_breeds = get_breeds_missing_care_content()
    logger.info(f"Found {len(missing_care_breeds)} breeds missing care content")

    # Get breed names for the missing breeds
    result = supabase.table('breeds_published').select(
        'breed_slug, display_name'
    ).in_('breed_slug', missing_care_breeds).execute()

    breed_map = {b['breed_slug']: b['display_name'] for b in result.data}

    successful = 0
    failed = 0
    results = []

    for breed_slug in missing_care_breeds[:50]:  # Process first 50 breeds
        if breed_slug not in breed_map:
            continue

        breed_name = breed_map[breed_slug]
        logger.info(f"Processing {breed_name} ({breed_slug})...")

        try:
            # Scrape from multiple sources
            akc_content = scrape_akc_care_content(breed_slug, breed_name)
            time.sleep(2)  # Rate limiting

            petmd_content = scrape_petmd_care_content(breed_slug, breed_name)
            time.sleep(2)  # Rate limiting

            # Combine content
            if akc_content or petmd_content:
                combined_content = combine_care_content(akc_content, petmd_content)

                if len(combined_content.strip()) > 50:  # Minimum content threshold
                    # Update database
                    if update_breed_care_content(breed_slug, combined_content):
                        logger.info(f"✅ Updated care content for {breed_name}")
                        successful += 1
                        results.append({
                            'breed_slug': breed_slug,
                            'display_name': breed_name,
                            'content_length': len(combined_content),
                            'sources': ['akc' if akc_content else None, 'petmd' if petmd_content else None],
                            'status': 'success'
                        })
                    else:
                        logger.error(f"❌ Failed to update database for {breed_name}")
                        failed += 1
                        results.append({
                            'breed_slug': breed_slug,
                            'display_name': breed_name,
                            'status': 'database_error'
                        })
                else:
                    logger.warning(f"⚠️ Insufficient content found for {breed_name}")
                    failed += 1
                    results.append({
                        'breed_slug': breed_slug,
                        'display_name': breed_name,
                        'status': 'insufficient_content'
                    })
            else:
                logger.warning(f"⚠️ No care content found for {breed_name}")
                failed += 1
                results.append({
                    'breed_slug': breed_slug,
                    'display_name': breed_name,
                    'status': 'no_content_found'
                })

        except Exception as e:
            logger.error(f"Error processing {breed_name}: {e}")
            failed += 1
            results.append({
                'breed_slug': breed_slug,
                'display_name': breed_name,
                'status': 'error',
                'error': str(e)
            })

    # Summary
    logger.info("\n" + "="*60)
    logger.info("CARE CONTENT SCRAPING COMPLETE")
    logger.info("="*60)
    logger.info(f"Total breeds processed: {len(missing_care_breeds[:50])}")
    logger.info(f"Successful updates: {successful}")
    logger.info(f"Failed: {failed}")

    # Save results
    report_file = f'care_content_scraping_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(report_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_processed': len(missing_care_breeds[:50]),
            'successful': successful,
            'failed': failed,
            'results': results
        }, f, indent=2)

    logger.info(f"\nReport saved to: {report_file}")

    return successful, failed

def verify_care_content_improvement():
    """Verify care content coverage after scraping"""

    logger.info("\nVerifying care content coverage...")

    result = supabase.table('breeds_comprehensive_content').select(
        'breed_slug, general_care'
    ).execute()

    total_breeds = len(result.data)
    with_care = 0

    for breed in result.data:
        care_content = breed.get('general_care', '')
        if care_content and len(care_content.strip()) >= 100:
            with_care += 1

    care_coverage = (with_care / total_breeds) * 100

    logger.info(f"\nCare Content Coverage: {care_coverage:.1f}% ({with_care}/{total_breeds})")

    # Previous coverage was 4.8%
    improvement = care_coverage - 4.8
    logger.info(f"Coverage improvement: +{improvement:.1f}%")

    return care_coverage

if __name__ == "__main__":
    # Scrape care content
    successful, failed = scrape_care_content_for_breeds()

    if successful > 0:
        logger.info("\nWaiting for database to update...")
        time.sleep(3)

        # Verify improvement
        coverage = verify_care_content_improvement()

        if coverage >= 50:
            logger.info("\n✅ Stage 4 COMPLETE: Care content target achieved!")
        else:
            logger.info(f"\n⚠️ Care content at {coverage:.1f}% - may need additional sources")