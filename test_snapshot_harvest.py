#!/usr/bin/env python3
"""
Test snapshot harvest with just 1 brand and 5 products
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set credentials from .env
if 'GOOGLE_APPLICATION_CREDENTIALS' not in os.environ:
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = './secrets/gcp-sa.json'

from wave1_snapshot_harvester import Wave1SnapshotHarvester
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test with just alpha brand, limited to 5 products
brand_slug = 'alpha'
profile_path = Path(f'profiles/manufacturers/{brand_slug}.yaml')

if not profile_path.exists():
    logger.error(f"Profile not found: {profile_path}")
    exit(1)

logger.info(f"Testing snapshot harvest for {brand_slug}")
logger.info("Limiting to 5 products for test")

# Monkey patch to limit products
original_discover = Wave1SnapshotHarvester.discover_product_urls

def limited_discover(self):
    urls = original_discover(self)
    return urls[:5]  # Limit to 5 products

Wave1SnapshotHarvester.discover_product_urls = limited_discover

try:
    harvester = Wave1SnapshotHarvester(brand_slug, profile_path)
    stats = harvester.harvest_snapshot()
    
    print("\n" + "="*60)
    print("TEST RESULTS")
    print("="*60)
    print(f"Brand: {brand_slug}")
    print(f"Pages uploaded: {stats['pages_uploaded']}")
    print(f"PDFs uploaded: {stats['pdfs_uploaded']}")
    print(f"Total size: {stats['total_size_mb']:.2f} MB")
    print(f"Failures: {stats['failures']}")
    print(f"GCS path: gs://lupito-content-raw-eu/manufacturers/{brand_slug}/")
    
except Exception as e:
    logger.error(f"Test failed: {e}")
    import traceback
    traceback.print_exc()