#!/usr/bin/env python3
"""
Generate comprehensive care content from existing breed data
Uses grooming_needs, exercise_needs_detail, training_tips, and other fields
"""

import os
import time
import json
import logging
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Supabase
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(supabase_url, supabase_key)

def get_breed_care_data():
    """Get all breed data for care content generation"""

    result = supabase.table('breeds_comprehensive_content').select(
        'breed_slug, general_care, grooming_needs, grooming_frequency, '
        'exercise_needs_detail, exercise_level, training_tips, health_issues'
    ).execute()

    return result.data

def get_breed_basic_data():
    """Get basic breed characteristics for care recommendations"""

    result = supabase.table('breeds_published').select(
        'breed_slug, display_name, size_category, energy, coat_length, '
        'shedding, trainability, adult_weight_avg_kg'
    ).execute()

    # Convert to dict for easy lookup
    breed_dict = {}
    for breed in result.data:
        breed_dict[breed['breed_slug']] = breed

    return breed_dict

def generate_care_content_from_data(breed_data, basic_data):
    """Generate comprehensive care content from existing data"""

    breed_slug = breed_data['breed_slug']
    basic_info = basic_data.get(breed_slug, {})

    care_sections = []

    # Grooming section
    grooming_parts = []
    if breed_data.get('grooming_needs'):
        grooming_parts.append(breed_data['grooming_needs'])
    if breed_data.get('grooming_frequency'):
        grooming_parts.append(f"Grooming frequency: {breed_data['grooming_frequency']}")

    # Add basic grooming recommendations based on coat and shedding
    if basic_info.get('coat_length'):
        if basic_info['coat_length'] == 'long':
            grooming_parts.append("Daily brushing is recommended to prevent matting and tangles.")
        elif basic_info['coat_length'] == 'medium':
            grooming_parts.append("Regular brushing 2-3 times per week helps maintain coat health.")
        elif basic_info['coat_length'] == 'short':
            grooming_parts.append("Weekly brushing is usually sufficient for coat maintenance.")

    if basic_info.get('shedding'):
        if basic_info['shedding'] == 'high':
            grooming_parts.append("Expect heavy shedding; daily brushing during shedding seasons is beneficial.")
        elif basic_info['shedding'] == 'moderate':
            grooming_parts.append("Moderate shedding requires regular brushing to manage loose hair.")
        elif basic_info['shedding'] == 'low':
            grooming_parts.append("Minimal shedding makes grooming relatively easy.")

    if grooming_parts:
        care_sections.append(f"**Grooming:** {' '.join(grooming_parts)}")

    # Exercise section
    exercise_parts = []
    if breed_data.get('exercise_needs_detail'):
        exercise_parts.append(breed_data['exercise_needs_detail'])

    # Add exercise recommendations based on energy level and size
    if basic_info.get('energy'):
        if basic_info['energy'] == 'high':
            exercise_parts.append("Requires substantial daily exercise including vigorous activities, long walks, or active play sessions.")
        elif basic_info['energy'] == 'moderate':
            exercise_parts.append("Benefits from regular daily walks and moderate exercise activities.")
        elif basic_info['energy'] == 'low':
            exercise_parts.append("Moderate exercise needs; short walks and gentle play sessions are usually sufficient.")

    if basic_info.get('size_category'):
        if basic_info['size_category'] == 'tiny' or basic_info['size_category'] == 'small':
            exercise_parts.append("Indoor play can meet many exercise needs, though outdoor walks are still important.")
        elif basic_info['size_category'] == 'large' or basic_info['size_category'] == 'giant':
            exercise_parts.append("Needs adequate space for exercise; apartments may be challenging without sufficient outdoor access.")

    if exercise_parts:
        care_sections.append(f"**Exercise:** {' '.join(exercise_parts)}")

    # Training section
    training_parts = []
    if breed_data.get('training_tips'):
        training_parts.append(breed_data['training_tips'])

    # Add training recommendations based on trainability
    if basic_info.get('trainability'):
        if basic_info['trainability'] == 'high':
            training_parts.append("Highly trainable and responds well to positive reinforcement methods.")
        elif basic_info['trainability'] == 'moderate':
            training_parts.append("Generally trainable with consistent, patient training approaches.")
        elif basic_info['trainability'] == 'low':
            training_parts.append("May require more patience and persistence in training; professional training help can be beneficial.")

    if training_parts:
        care_sections.append(f"**Training:** {' '.join(training_parts)}")

    # Health section
    health_parts = []
    if breed_data.get('health_issues'):
        health_parts.append(f"Health considerations: {breed_data['health_issues']}")

    # Add general health recommendations based on size
    if basic_info.get('size_category'):
        if basic_info['size_category'] == 'giant':
            health_parts.append("Large breeds benefit from joint supplements and careful monitoring for hip/elbow dysplasia.")
        elif basic_info['size_category'] == 'tiny':
            health_parts.append("Small breeds may be prone to dental issues and benefit from regular dental care.")

    if health_parts:
        care_sections.append(f"**Health:** {' '.join(health_parts)}")

    # Feeding section (basic recommendations based on size and energy)
    feeding_parts = []
    if basic_info.get('adult_weight_avg_kg') and basic_info.get('energy'):
        weight = basic_info['adult_weight_avg_kg']
        energy = basic_info['energy']

        if weight < 10:
            feeding_parts.append("Small breed dogs typically need 1/4 to 1 cup of high-quality dry food daily, divided into two meals.")
        elif weight < 25:
            feeding_parts.append("Medium-sized dogs usually require 1 to 2 cups of high-quality dry food daily, divided into two meals.")
        elif weight < 45:
            feeding_parts.append("Large dogs typically need 2 to 3 cups of high-quality dry food daily, divided into two meals.")
        else:
            feeding_parts.append("Giant breeds often require 3 to 5 cups of high-quality dry food daily, divided into two or three meals.")

        if energy == 'high':
            feeding_parts.append("High-energy dogs may need additional calories to fuel their active lifestyle.")
        elif energy == 'low':
            feeding_parts.append("Monitor food intake carefully as lower energy dogs are prone to weight gain.")

    if feeding_parts:
        care_sections.append(f"**Feeding:** {' '.join(feeding_parts)}")

    return '\n\n'.join(care_sections)

def update_breed_care_content():
    """Generate and update care content for breeds missing it"""

    logger.info("Starting care content generation from existing data...")

    # Get all breed data
    breed_care_data = get_breed_care_data()
    basic_data = get_breed_basic_data()

    logger.info(f"Processing {len(breed_care_data)} breeds...")

    successful = 0
    failed = 0
    results = []

    for breed_data in breed_care_data:
        breed_slug = breed_data['breed_slug']

        try:
            # Check if already has substantial care content
            existing_care = breed_data.get('general_care', '')
            if existing_care and len(existing_care.strip()) >= 200:
                logger.info(f"⏭️ {breed_slug}: Already has care content, skipping")
                continue

            # Generate care content
            generated_care = generate_care_content_from_data(breed_data, basic_data)

            if len(generated_care.strip()) >= 100:  # Minimum content threshold
                # Update database
                result = supabase.table('breeds_comprehensive_content').update({
                    'general_care': generated_care,
                    'updated_at': datetime.now().isoformat()
                }).eq('breed_slug', breed_slug).execute()

                if result.data:
                    logger.info(f"✅ {breed_slug}: Generated {len(generated_care)} chars of care content")
                    successful += 1
                    results.append({
                        'breed_slug': breed_slug,
                        'content_length': len(generated_care),
                        'status': 'success'
                    })
                else:
                    logger.error(f"❌ {breed_slug}: Database update failed")
                    failed += 1
                    results.append({
                        'breed_slug': breed_slug,
                        'status': 'database_error'
                    })
            else:
                logger.warning(f"⚠️ {breed_slug}: Insufficient data to generate meaningful content")
                failed += 1
                results.append({
                    'breed_slug': breed_slug,
                    'status': 'insufficient_data'
                })

        except Exception as e:
            logger.error(f"Error processing {breed_slug}: {e}")
            failed += 1
            results.append({
                'breed_slug': breed_slug,
                'status': 'error',
                'error': str(e)
            })

        # Progress logging
        if (successful + failed) % 50 == 0:
            logger.info(f"Progress: {successful + failed}/{len(breed_care_data)} processed")

    # Summary
    logger.info("\n" + "="*60)
    logger.info("CARE CONTENT GENERATION COMPLETE")
    logger.info("="*60)
    logger.info(f"Total breeds processed: {len(breed_care_data)}")
    logger.info(f"Successful updates: {successful}")
    logger.info(f"Failed: {failed}")

    # Save results
    report_file = f'care_content_generation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(report_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_processed': len(breed_care_data),
            'successful': successful,
            'failed': failed,
            'results': results
        }, f, indent=2)

    logger.info(f"\nReport saved to: {report_file}")

    return successful, failed

def verify_care_content_improvement():
    """Verify care content coverage after generation"""

    logger.info("\nVerifying care content coverage...")

    result = supabase.table('breeds_comprehensive_content').select(
        'breed_slug, general_care'
    ).execute()

    total_breeds = len(result.data)
    with_care = 0
    care_lengths = []

    for breed in result.data:
        care_content = breed.get('general_care', '')
        if care_content and len(care_content.strip()) >= 100:
            with_care += 1
            care_lengths.append(len(care_content))

    care_coverage = (with_care / total_breeds) * 100

    logger.info(f"\nCare Content Coverage: {care_coverage:.1f}% ({with_care}/{total_breeds})")

    if care_lengths:
        avg_length = sum(care_lengths) / len(care_lengths)
        logger.info(f"Average care content length: {avg_length:.0f} characters")

    # Previous coverage was 2.6%
    improvement = care_coverage - 2.6
    logger.info(f"Coverage improvement: +{improvement:.1f}%")

    return care_coverage

if __name__ == "__main__":
    # Generate care content
    successful, failed = update_breed_care_content()

    if successful > 0:
        logger.info("\nWaiting for database to update...")
        time.sleep(3)

        # Verify improvement
        coverage = verify_care_content_improvement()

        if coverage >= 50:
            logger.info("\n✅ Stage 4 COMPLETE: Care content target achieved!")
        elif coverage >= 30:
            logger.info(f"\n🎯 Good progress: Care content at {coverage:.1f}% - significant improvement!")
        else:
            logger.info(f"\n⚠️ Care content at {coverage:.1f}% - additional work needed")

        # Calculate quality impact
        # Each 10% increase in care content adds ~0.5 points to overall quality
        quality_impact = (coverage - 2.6) * 0.05
        estimated_quality = 92 + quality_impact
        logger.info(f"Estimated quality score: 92% → {estimated_quality:.1f}%")