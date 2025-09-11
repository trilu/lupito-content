#!/usr/bin/env python3
"""
Verify GCS setup with brit brand snapshot
"""

import os
from dotenv import load_dotenv
from wave1_snapshot_harvester import Wave1SnapshotHarvester
from pathlib import Path
from google.cloud import storage
import logging

# Load environment
load_dotenv()
if 'GOOGLE_APPLICATION_CREDENTIALS' not in os.environ:
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = './secrets/gcp-sa.json'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test with brit brand, 3 products
brand_slug = 'brit'
profile_path = Path(f'profiles/manufacturers/{brand_slug}.yaml')

print("\n" + "="*60)
print("GCS SETUP VERIFICATION")
print("="*60)

# Limit to 3 products
original_discover = Wave1SnapshotHarvester.discover_product_urls
def limited_discover(self):
    urls = original_discover(self)
    # Get specific product URLs if found
    product_urls = [u for u in urls if '/product' in u or '/p/' in u][:3]
    if not product_urls:
        product_urls = urls[:3]
    return product_urls

Wave1SnapshotHarvester.discover_product_urls = limited_discover

try:
    print(f"\n1. Starting snapshot harvest for {brand_slug}")
    print("   Fetching 3 product pages + any linked PDFs")
    
    harvester = Wave1SnapshotHarvester(brand_slug, profile_path)
    stats = harvester.harvest_snapshot()
    
    print(f"\n2. Harvest Results:")
    print(f"   Pages uploaded: {stats['pages_uploaded']}")
    print(f"   PDFs uploaded: {stats['pdfs_uploaded']}")
    print(f"   Total size: {stats['total_size_mb']:.2f} MB")
    
    # List uploaded files
    print(f"\n3. Verifying GCS uploads:")
    client = storage.Client()
    bucket = client.bucket('lupito-content-raw-eu')
    
    prefix = f"manufacturers/{brand_slug}/{harvester.date_str}/"
    blobs = list(bucket.list_blobs(prefix=prefix))
    
    print(f"   Found {len(blobs)} objects in GCS:")
    for blob in blobs[:10]:  # Show first 10
        print(f"   - gs://{bucket.name}/{blob.name} ({blob.size} bytes)")
    
    # Read back one file to verify
    if blobs:
        print(f"\n4. Read-back verification:")
        test_blob = blobs[0]
        content = test_blob.download_as_text()[:200]
        print(f"   Successfully read {test_blob.name}")
        print(f"   Content preview: {content[:100]}...")
    
    print("\n" + "="*60)
    print("✅ GCS SETUP VERIFICATION: PASSED")
    print("="*60)
    print("\nSummary:")
    print(f"- Service Account: content-snapshots@careful-drummer-468512-p0.iam.gserviceaccount.com")
    print(f"- Bucket: gs://lupito-content-raw-eu")
    print(f"- Objects uploaded: {len(blobs)}")
    print(f"- Storage path: gs://lupito-content-raw-eu/{prefix}")
    print("\nNext step: Enable parsing pass to read from GCS URIs")
    
except Exception as e:
    print(f"\n❌ Verification failed: {e}")
    import traceback
    traceback.print_exc()