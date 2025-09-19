#!/usr/bin/env python3
"""
Fix data quality issues using breeds_overrides table
This allows us to override the view values correctly
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
        'field_name': 'size_category',
        'override_value': 'l',
        'reason': 'Coonhounds are large dogs (18-34kg), not extra small'
    },
    {
        'breed_slug': 'boerboel',
        'field_name': 'size_category',
        'override_value': 'xl',
        'reason': 'Boerboels are extra large mastiff-type dogs (68-91kg)'
    },
    {
        'breed_slug': 'english-toy-spaniel',
        'field_name': 'size_category',
        'override_value': 'xs',
        'reason': 'Toy breeds are extra small (3.6-6.4kg), not medium'
    },
    {
        'breed_slug': 'giant-schnauzer',
        'field_name': 'size_category',
        'override_value': 'xl',
        'reason': 'Giant Schnauzers are extra large dogs (35-47kg), not extra small'
    },
    {
        'breed_slug': 'norwegian-lundehund',
        'field_name': 'size_category',
        'override_value': 's',
        'reason': 'Lundehunds are small dogs (5.9-6.8kg), not medium'
    },
    {
        'breed_slug': 'portuguese-podengo-pequeno',
        'field_name': 'size_category',
        'override_value': 's',
        'reason': 'Pequeno (small) variety weighs 4-6kg, not 20-30kg'
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
        field_name = override['field_name']
        override_value = override['override_value']
        reason = override['reason']

        try:
            # Check if override already exists
            existing = supabase.table('breeds_overrides').select('*').eq('breed_slug', breed_slug).eq('field_name', field_name).execute()

            override_data = {
                'breed_slug': breed_slug,
                'field_name': field_name,
                'override_value': override_value,
                'reason': reason,
                'is_active': True
            }

            if existing.data:
                # Update existing override
                logger.info(f"Updating override for {breed_slug}.{field_name}")
                result = supabase.table('breeds_overrides').update(override_data).eq('breed_slug', breed_slug).eq('field_name', field_name).execute()
            else:
                # Insert new override
                logger.info(f"Creating override for {breed_slug}.{field_name}")
                result = supabase.table('breeds_overrides').insert(override_data).execute()

            if result.data:
                logger.info(f"  ✅ Successfully applied override: {breed_slug}.{field_name} = {override_value}")
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

    logger.info("\nVerifying overrides...")
    all_good = True

    for override in OVERRIDES:
        breed_slug = override['breed_slug']
        field_name = override['field_name']
        expected_value = override['override_value']

        # Get current data from the view
        result = supabase.table('breeds_published').select('*').eq('breed_slug', breed_slug).execute()

        if not result.data:
            logger.error(f"❌ {breed_slug} not found in breeds_published view")
            all_good = False
            continue

        current = result.data[0]
        current_value = current.get(field_name)

        if current_value != expected_value:
            logger.error(f"❌ {breed_slug}.{field_name}: is {current_value}, expected {expected_value}")
            all_good = False
        else:
            logger.info(f"✅ {breed_slug}.{field_name}: Override verified ({expected_value})")

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
            logger.warning("\n⚠️ Some issues remain - the view may not be using overrides correctly")