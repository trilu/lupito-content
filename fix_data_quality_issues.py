#!/usr/bin/env python3
"""
Fix data quality issues in breeds_published table
Corrects mismatched size categories and weight values
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

# Define corrections needed
CORRECTIONS = [
    {
        'breed_slug': 'black-and-tan-coonhound',
        'fixes': {
            'size_category': 'l',  # was xs, should be large (18-34kg)
            'adult_weight_min_kg': 18.1,
            'adult_weight_max_kg': 34.0
        },
        'reason': 'Coonhounds are large dogs, not extra small'
    },
    {
        'breed_slug': 'boerboel',
        'fixes': {
            'size_category': 'xl',  # was m, should be extra large (68-91kg)
            'adult_weight_min_kg': 68.0,
            'adult_weight_max_kg': 91.0
        },
        'reason': 'Boerboels are extra large mastiff-type dogs'
    },
    {
        'breed_slug': 'doberman-pinscher',
        'fixes': {
            'adult_weight_min_kg': 32.0,  # was 4.54kg (wrong)
            'adult_weight_max_kg': 45.0   # was 5.44kg (wrong)
        },
        'reason': 'Weight was incorrectly set to ~5kg instead of 32-45kg'
    },
    {
        'breed_slug': 'english-toy-spaniel',
        'fixes': {
            'size_category': 'xs',  # was m, should be extra small (3.6-6.4kg)
            'adult_weight_min_kg': 3.6,
            'adult_weight_max_kg': 6.4
        },
        'reason': 'Toy breeds are extra small, not medium'
    },
    {
        'breed_slug': 'giant-schnauzer',
        'fixes': {
            'size_category': 'xl',  # was xs, should be extra large (35-47kg)
            'adult_weight_min_kg': 35.0,
            'adult_weight_max_kg': 47.0
        },
        'reason': 'Giant Schnauzers are extra large dogs, not extra small'
    },
    {
        'breed_slug': 'leonberger',
        'fixes': {
            'adult_weight_min_kg': 45.0,  # was 13.61kg (wrong)
            'adult_weight_max_kg': 77.0   # was 27.22kg (wrong)
        },
        'reason': 'Leonbergers are giant dogs weighing 45-77kg, not 13-27kg'
    },
    {
        'breed_slug': 'norwegian-lundehund',
        'fixes': {
            'size_category': 's',  # was m, should be small (5.9-6.8kg)
            'adult_weight_min_kg': 5.9,
            'adult_weight_max_kg': 6.8
        },
        'reason': 'Lundehunds are small dogs, not medium'
    },
    {
        'breed_slug': 'portuguese-podengo-pequeno',
        'fixes': {
            'size_category': 's',  # was xs with wrong weight
            'adult_weight_min_kg': 4.0,   # was 20kg (wrong for pequeno)
            'adult_weight_max_kg': 6.0    # was 30kg (wrong for pequeno)
        },
        'reason': 'Pequeno (small) variety weighs 4-6kg, not 20-30kg'
    },
    {
        'breed_slug': 'tibetan-mastiff',
        'fixes': {
            'adult_weight_min_kg': 45.0,  # was 4.54kg (wrong)
            'adult_weight_max_kg': 73.0   # was 5.44kg (wrong)
        },
        'reason': 'Tibetan Mastiffs are giant dogs weighing 45-73kg, not 5kg'
    }
]

def apply_corrections():
    """Apply all corrections to the database"""

    logger.info("Starting data quality fixes...")
    logger.info(f"Processing {len(CORRECTIONS)} breed corrections")

    successful = 0
    failed = 0

    for correction in CORRECTIONS:
        breed_slug = correction['breed_slug']
        fixes = correction['fixes']
        reason = correction['reason']

        try:
            # First get the current data
            current = supabase.table('breeds_published').select('*').eq('breed_slug', breed_slug).execute()

            if not current.data:
                logger.warning(f"Breed not found: {breed_slug}")
                failed += 1
                continue

            current_data = current.data[0]
            logger.info(f"\nFixing {breed_slug}:")
            logger.info(f"  Reason: {reason}")

            # Log changes
            for field, new_value in fixes.items():
                old_value = current_data.get(field)
                if old_value != new_value:
                    logger.info(f"  {field}: {old_value} → {new_value}")

            # Apply the fix - update breeds_details table (breeds_published is a view)
            # Map view columns to table columns
            table_fixes = {}
            for field, value in fixes.items():
                if field == 'size_category':
                    # Map size categories to database enum values
                    size_map = {
                        'xs': 'tiny',
                        's': 'small',
                        'm': 'medium',
                        'l': 'large',
                        'xl': 'giant'
                    }
                    table_fixes['size'] = size_map.get(value, value)
                elif field == 'adult_weight_min_kg':
                    table_fixes['weight_kg_min'] = value
                elif field == 'adult_weight_max_kg':
                    table_fixes['weight_kg_max'] = value
                else:
                    table_fixes[field] = value

            result = supabase.table('breeds_details').update(table_fixes).eq('breed_slug', breed_slug).execute()

            if result.data:
                logger.info(f"  ✅ Successfully fixed {breed_slug}")
                successful += 1
            else:
                logger.error(f"  ❌ Failed to update {breed_slug}")
                failed += 1

        except Exception as e:
            logger.error(f"Error fixing {breed_slug}: {e}")
            failed += 1

    # Summary
    logger.info("\n" + "="*60)
    logger.info("DATA QUALITY FIXES COMPLETE")
    logger.info("="*60)
    logger.info(f"Total corrections attempted: {len(CORRECTIONS)}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")

    if successful == len(CORRECTIONS):
        logger.info("✅ All data quality issues fixed!")
    else:
        logger.warning(f"⚠️ {failed} corrections failed - please review")

    return successful, failed

def verify_fixes():
    """Verify that all fixes were applied correctly"""

    logger.info("\nVerifying fixes...")
    all_good = True

    for correction in CORRECTIONS:
        breed_slug = correction['breed_slug']
        expected = correction['fixes']

        # Get current data
        result = supabase.table('breeds_published').select('*').eq('breed_slug', breed_slug).execute()

        if not result.data:
            logger.error(f"❌ {breed_slug} not found in database")
            all_good = False
            continue

        current = result.data[0]

        # Check each field
        issues = []
        for field, expected_value in expected.items():
            current_value = current.get(field)
            if current_value != expected_value:
                issues.append(f"{field} is {current_value}, expected {expected_value}")

        if issues:
            logger.error(f"❌ {breed_slug}: {', '.join(issues)}")
            all_good = False
        else:
            logger.info(f"✅ {breed_slug}: All fixes verified")

    return all_good

if __name__ == "__main__":
    # Apply corrections
    successful, failed = apply_corrections()

    # Verify fixes
    if successful > 0:
        logger.info("\n" + "="*60)
        logger.info("VERIFICATION")
        logger.info("="*60)

        if verify_fixes():
            logger.info("\n🎉 All data quality issues have been successfully resolved!")
        else:
            logger.warning("\n⚠️ Some issues remain - please check the logs")

    # Save summary
    with open('data_quality_fixes_log.txt', 'w') as f:
        f.write(f"Data Quality Fixes - {datetime.now().isoformat()}\n")
        f.write(f"{'='*60}\n")
        f.write(f"Successful: {successful}/{len(CORRECTIONS)}\n")
        f.write(f"Failed: {failed}/{len(CORRECTIONS)}\n")
        f.write("\nCorrections applied:\n")
        for correction in CORRECTIONS:
            f.write(f"- {correction['breed_slug']}: {correction['reason']}\n")