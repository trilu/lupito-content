#!/usr/bin/env python3
"""
Run Wave 1 Snapshot Harvest for all brands
Captures HTML and PDFs to GCS - no parsing
"""

import os
import sys
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
import logging
import time

# Load environment
load_dotenv()
if 'GOOGLE_APPLICATION_CREDENTIALS' not in os.environ:
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = './secrets/gcp-sa.json'

from wave1_snapshot_harvester import Wave1SnapshotHarvester

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Wave 1 brands
WAVE1_BRANDS = [
    'alpha', 'brit', 'briantos', 'canagan', 'cotswold',
    'burns', 'barking', 'bozita', 'forthglade', 'belcando'
]

# Limit products per brand for initial snapshot
MAX_PRODUCTS_PER_BRAND = 20  # Reasonable limit for snapshot

def run_snapshot_harvest():
    """Run snapshot harvest for all Wave 1 brands"""
    
    print("\n" + "="*80)
    print("WAVE 1 SNAPSHOT HARVEST")
    print("="*80)
    print(f"Brands: {', '.join(WAVE1_BRANDS)}")
    print(f"Max products per brand: {MAX_PRODUCTS_PER_BRAND}")
    print(f"Storage: gs://lupito-content-raw-eu/manufacturers/")
    print("="*80)
    
    # Results storage
    harvest_results = []
    start_time = time.time()
    
    # Monkey patch to limit products
    original_discover = Wave1SnapshotHarvester.discover_product_urls
    def limited_discover(self):
        urls = original_discover(self)
        return urls[:MAX_PRODUCTS_PER_BRAND]
    Wave1SnapshotHarvester.discover_product_urls = limited_discover
    
    # Process each brand
    for i, brand_slug in enumerate(WAVE1_BRANDS, 1):
        print(f"\n[{i}/{len(WAVE1_BRANDS)}] Processing {brand_slug}...")
        print("-" * 60)
        
        profile_path = Path(f'profiles/manufacturers/{brand_slug}.yaml')
        
        if not profile_path.exists():
            logger.warning(f"Profile not found for {brand_slug}")
            harvest_results.append({
                'brand': brand_slug,
                'status': 'skipped',
                'reason': 'Profile not found'
            })
            continue
        
        try:
            # Run harvest
            harvester = Wave1SnapshotHarvester(brand_slug, profile_path)
            stats = harvester.harvest_snapshot()
            
            # Store results
            harvest_results.append({
                'brand': brand_slug,
                'status': 'success',
                'stats': stats,
                'gcs_path': f"gs://lupito-content-raw-eu/manufacturers/{brand_slug}/{harvester.date_str}/"
            })
            
            print(f"✅ {brand_slug}: {stats['pages_uploaded']} pages, {stats['pdfs_uploaded']} PDFs")
            
        except KeyboardInterrupt:
            print("\n\n⚠️ Harvest interrupted by user")
            break
            
        except Exception as e:
            logger.error(f"Failed {brand_slug}: {e}")
            harvest_results.append({
                'brand': brand_slug,
                'status': 'failed',
                'error': str(e)
            })
            print(f"❌ {brand_slug}: {e}")
    
    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    
    # Generate summary report
    print("\n" + "="*80)
    print("GENERATING SUMMARY REPORT")
    print("="*80)
    
    report_path = Path('reports/WAVE_1_SNAPSHOT_SUMMARY.md')
    
    with open(report_path, 'w') as f:
        f.write("# Wave 1 Snapshot Harvest Summary\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Duration:** {elapsed_time/60:.1f} minutes\n")
        f.write(f"**Bucket:** gs://lupito-content-raw-eu/\n")
        f.write(f"**Brands Processed:** {len([r for r in harvest_results if r['status'] != 'skipped'])}/{len(WAVE1_BRANDS)}\n\n")
        
        # Overall statistics
        total_pages = sum(r['stats']['pages_uploaded'] for r in harvest_results if r['status'] == 'success')
        total_pdfs = sum(r['stats']['pdfs_uploaded'] for r in harvest_results if r['status'] == 'success')
        total_fetched = sum(r['stats']['pages_fetched'] for r in harvest_results if r['status'] == 'success')
        total_size = sum(r['stats']['total_size_mb'] for r in harvest_results if r['status'] == 'success')
        
        f.write("## Overall Statistics\n\n")
        f.write(f"- **Total Pages Fetched:** {total_fetched}\n")
        f.write(f"- **Total Pages Uploaded:** {total_pages}\n")
        f.write(f"- **Total PDFs Found:** {total_pdfs}\n")
        f.write(f"- **Total Size:** {total_size:.1f} MB\n")
        f.write(f"- **Success Rate:** {len([r for r in harvest_results if r['status'] == 'success'])}/{len(harvest_results)}\n\n")
        
        f.write("## Per-Brand Results\n\n")
        f.write("| Brand | Status | Pages | PDFs | Size (MB) | Failures | GCS Path |\n")
        f.write("|-------|--------|-------|------|-----------|----------|----------|\n")
        
        for result in harvest_results:
            if result['status'] == 'success':
                stats = result['stats']
                failures = ', '.join([f"{k}:{v}" for k,v in stats['failures'].items()]) if stats['failures'] else 'None'
                gcs_link = f"[View]({result['gcs_path']})"
                f.write(f"| {result['brand']} | ✅ | {stats['pages_uploaded']} | ")
                f.write(f"{stats['pdfs_uploaded']} | {stats['total_size_mb']:.1f} | {failures} | {gcs_link} |\n")
            elif result['status'] == 'failed':
                f.write(f"| {result['brand']} | ❌ | - | - | - | {result.get('error', 'Unknown')[:30]} | - |\n")
            else:
                f.write(f"| {result['brand']} | ⏭️ | - | - | - | {result.get('reason', 'Skipped')} | - |\n")
        
        # Failure breakdown
        f.write("\n## HTTP Failure Breakdown\n\n")
        
        all_failures = {}
        for result in harvest_results:
            if result['status'] == 'success' and result['stats'].get('failures'):
                for failure_type, count in result['stats']['failures'].items():
                    all_failures[failure_type] = all_failures.get(failure_type, 0) + count
        
        if all_failures:
            f.write("| Failure Type | Count |\n")
            f.write("|--------------|-------|\n")
            for failure_type, count in sorted(all_failures.items()):
                f.write(f"| {failure_type} | {count} |\n")
        else:
            f.write("No HTTP failures recorded.\n")
        
        # GCS structure
        f.write("\n## GCS Storage Structure\n\n")
        f.write("```\n")
        f.write("gs://lupito-content-raw-eu/\n")
        f.write("└── manufacturers/\n")
        
        date_str = datetime.now().strftime('%Y-%m-%d')
        for result in harvest_results:
            if result['status'] == 'success':
                stats = result['stats']
                f.write(f"    ├── {result['brand']}/\n")
                f.write(f"    │   └── {date_str}/\n")
                f.write(f"    │       ├── *.html ({stats['pages_uploaded']} files)\n")
                if stats['pdfs_uploaded'] > 0:
                    f.write(f"    │       └── *.pdf ({stats['pdfs_uploaded']} files)\n")
        f.write("```\n")
        
        # Sample URLs captured
        f.write("\n## Sample URLs Captured\n\n")
        for result in harvest_results[:3]:  # Show first 3 brands
            if result['status'] == 'success' and result['stats'].get('urls_visited'):
                f.write(f"### {result['brand']}\n")
                sample_urls = list(result['stats']['urls_visited'])[:5]
                for url in sample_urls:
                    f.write(f"- {url}\n")
                f.write("\n")
        
        f.write("## Notes\n\n")
        f.write(f"- Rate limiting: 2-3 seconds between requests\n")
        f.write(f"- robots.txt: Respected for all brands\n")
        f.write(f"- Product limit: {MAX_PRODUCTS_PER_BRAND} products per brand\n")
        f.write(f"- Storage: All content stored in GCS, no local files\n")
        f.write(f"- Parsing: Not performed (snapshot only)\n\n")
        
        f.write("## Next Steps\n\n")
        f.write("1. Verify GCS uploads via Console or gsutil\n")
        f.write("2. Review captured content quality\n")
        f.write("3. Run parsing pipeline to extract structured data\n")
        f.write("4. Update foods_canonical with parsed data\n")
        f.write("5. Run quality gates validation\n")
    
    # Print summary
    print(f"\n✅ Snapshot harvest complete!")
    print(f"📄 Report saved to: {report_path}")
    print(f"\nSummary:")
    print(f"  - Brands processed: {len([r for r in harvest_results if r['status'] != 'skipped'])}")
    print(f"  - Total pages: {total_pages}")
    print(f"  - Total PDFs: {total_pdfs}")
    print(f"  - Total size: {total_size:.1f} MB")
    print(f"  - Duration: {elapsed_time/60:.1f} minutes")
    
    return harvest_results

if __name__ == "__main__":
    results = run_snapshot_harvest()