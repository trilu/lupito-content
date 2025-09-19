#!/usr/bin/env python3
"""
Apply data quality fixes using breeds_overrides table
Uses the actual structure of breeds_overrides with specific columns
"""

import os
from supabase import create_client
from dotenv import load_dotenv
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Supabase
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(supabase_url, supabase_key)

# Define overrides needed
OVERRIDES = [
    {
        'breed_slug': 'black-and-tan-coonhound',
        'data': {
            'size_category': 'l',
            'adult_weight_min_kg': 18.1,
            'adult_weight_max_kg': 34.0
        },
        'reason': 'Coonhounds are large dogs (18-34kg), not extra small'
    },
    {
        'breed_slug': 'boerboel',
        'data': {
            'size_category': 'xl',
            'adult_weight_min_kg': 68.0,
            'adult_weight_max_kg': 91.0
        },
        'reason': 'Boerboels are extra large mastiff-type dogs (68-91kg)'
    },
    {
        'breed_slug': 'doberman-pinscher',
        'data': {
            'adult_weight_min_kg': 32.0,
            'adult_weight_max_kg': 45.0
        },
        'reason': 'Weight was incorrectly set to ~5kg instead of 32-45kg'
    },
    {
        'breed_slug': 'english-toy-spaniel',
        'data': {
            'size_category': 'xs',
            'adult_weight_min_kg': 3.6,
            'adult_weight_max_kg': 6.4
        },
        'reason': 'Toy breeds are extra small (3.6-6.4kg), not medium'
    },
    {
        'breed_slug': 'giant-schnauzer',
        'data': {
            'size_category': 'xl',
            'adult_weight_min_kg': 35.0,
            'adult_weight_max_kg': 47.0
        },
        'reason': 'Giant Schnauzers are extra large dogs (35-47kg), not extra small'
    },
    {
        'breed_slug': 'leonberger',
        'data': {
            'adult_weight_min_kg': 45.0,
            'adult_weight_max_kg': 77.0
        },
        'reason': 'Leonbergers are giant dogs weighing 45-77kg, not 13-27kg'
    },
    {
        'breed_slug': 'norwegian-lundehund',
        'data': {
            'size_category': 's',
            'adult_weight_min_kg': 5.9,
            'adult_weight_max_kg': 6.8
        },
        'reason': 'Lundehunds are small dogs (5.9-6.8kg), not medium'
    },
    {
        'breed_slug': 'portuguese-podengo-pequeno',
        'data': {
            'size_category': 's',
            'adult_weight_min_kg': 4.0,
            'adult_weight_max_kg': 6.0
        },
        'reason': 'Pequeno (small) variety weighs 4-6kg, not 20-30kg'
    },
    {
        'breed_slug': 'tibetan-mastiff',
        'data': {
            'adult_weight_min_kg': 45.0,
            'adult_weight_max_kg': 73.0
        },
        'reason': 'Tibetan Mastiffs are giant dogs weighing 45-73kg, not 5kg'
    }
]

def apply_overrides():
    """Apply all overrides to the breeds_overrides table"""

    logger.info("Starting data quality fixes via overrides...")
    logger.info(f"Processing {len(OVERRIDES)} breed overrides")

    successful = 0
    failed = 0

    for override in OVERRIDES:
        breed_slug = override['breed_slug']
        override_data = override['data'].copy()
        reason = override['reason']

        try:
            # Add metadata fields
            override_data['breed_slug'] = breed_slug
            override_data['override_reason'] = reason

            # Calculate average weight if both min and max are provided
            if 'adult_weight_min_kg' in override_data and 'adult_weight_max_kg' in override_data:
                override_data['adult_weight_avg_kg'] = (
                    override_data['adult_weight_min_kg'] + override_data['adult_weight_max_kg']
                ) / 2

            # Check if override already exists
            existing = supabase.table('breeds_overrides').select('*').eq('breed_slug', breed_slug).execute()

            if existing.data:
                # Update existing override
                logger.info(f"Updating override for {breed_slug}")
                result = supabase.table('breeds_overrides').update(override_data).eq('breed_slug', breed_slug).execute()
            else:
                # Insert new override
                logger.info(f"Creating override for {breed_slug}")
                result = supabase.table('breeds_overrides').insert(override_data).execute()

            if result.data:
                logger.info(f"  ✅ Successfully applied override for {breed_slug}")
                successful += 1
            else:
                logger.error(f"  ❌ Failed to apply override for {breed_slug}")
                failed += 1

        except Exception as e:
            logger.error(f"Error applying override for {breed_slug}: {e}")
            failed += 1

    # Summary
    logger.info("\n" + "="*60)
    logger.info("DATA QUALITY OVERRIDES COMPLETE")
    logger.info("="*60)
    logger.info(f"Total overrides attempted: {len(OVERRIDES)}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")

    if successful == len(OVERRIDES):
        logger.info("✅ All data quality overrides applied!")
    else:
        logger.warning(f"⚠️ {failed} overrides failed - please review")

    return successful, failed

def verify_overrides():
    """Verify that all overrides were applied correctly"""

    logger.info("\nVerifying overrides in breeds_published view...")
    all_good = True

    for override in OVERRIDES:
        breed_slug = override['breed_slug']
        expected_data = override['data']

        # Get current data from the view
        result = supabase.table('breeds_published').select('*').eq('breed_slug', breed_slug).execute()

        if not result.data:
            logger.error(f"❌ {breed_slug} not found in breeds_published view")
            all_good = False
            continue

        current = result.data[0]

        # Check each overridden field
        issues = []
        for field, expected_value in expected_data.items():
            # Map override field names to view field names if needed
            view_field = field
            current_value = current.get(view_field)

            # For numeric fields, compare with tolerance
            if isinstance(expected_value, (int, float)):
                if abs(current_value - expected_value) > 0.01:
                    issues.append(f"{view_field} is {current_value}, expected {expected_value}")
            else:
                if current_value != expected_value:
                    issues.append(f"{view_field} is {current_value}, expected {expected_value}")

        if issues:
            logger.error(f"❌ {breed_slug}: {', '.join(issues)}")
            all_good = False
        else:
            logger.info(f"✅ {breed_slug}: All overrides verified")

    return all_good

if __name__ == "__main__":
    # Apply overrides
    successful, failed = apply_overrides()

    # Verify fixes
    if successful > 0:
        logger.info("\n" + "="*60)
        logger.info("VERIFICATION")
        logger.info("="*60)

        if verify_overrides():
            logger.info("\n🎉 All data quality issues have been successfully resolved via overrides!")
        else:
            logger.warning("\n⚠️ Some issues may remain - check if view correctly uses overrides")