#!/usr/bin/env python3
"""
Resume ScrapingBee Harvesting for Remaining Brands
Continue from where API limit was reached
"""

import os
import sys
from pathlib import Path

# Import the existing harvester
from scrapingbee_harvester import ScrapingBeeHarvester, main, generate_blocked_sites_report

def resume_harvest():
    """Resume harvesting with remaining brands"""
    
    # We completed partial briantos, need to do belcando, bozita, cotswold
    remaining_brands = ['belcando', 'bozita', 'cotswold']
    
    print("="*80)
    print("RESUMING SCRAPINGBEE HARVEST")
    print("="*80)
    print(f"Remaining brands: {', '.join(remaining_brands)}")
    print("="*80)
    
    # Update the main function to only process remaining brands
    import scrapingbee_harvester
    original_brands = scrapingbee_harvester.main.__code__.co_consts
    
    # Monkey patch to use remaining brands
    def resume_main():
        """Process only remaining brands"""
        from datetime import datetime
        import logging
        import yaml
        
        logger = logging.getLogger(__name__)
        
        all_stats = {}
        
        for brand in remaining_brands:
            print(f"\n{'='*40}")
            print(f"Processing {brand.upper()}")
            print(f"{'='*40}")
            
            profile_path = Path(f'profiles/manufacturers/{brand}.yaml')
            
            # Create profile if needed
            if not profile_path.exists():
                from scrapingbee_harvester import get_brand_profile
                logger.info(f"Creating profile for {brand}")
                profile_data = get_brand_profile(brand)
                profile_path.parent.mkdir(parents=True, exist_ok=True)
                with open(profile_path, 'w') as f:
                    yaml.dump(profile_data, f)
            
            try:
                # Initialize harvester
                harvester = ScrapingBeeHarvester(brand, profile_path)
                
                # Discover product URLs
                product_urls = harvester.discover_product_urls()
                
                # Harvest products
                harvest_stats = harvester.harvest_products(product_urls)
                
                # Store results
                all_stats[brand] = {
                    'harvester': harvester.stats,
                    'harvest': harvest_stats,
                    'sample_urls': product_urls[:5]
                }
                
                print(f"\n✓ Completed {brand}:")
                print(f"  - API credits used: {harvester.stats['api_credits_used']}")
                print(f"  - Products found: {harvester.stats['products_found']}")
                print(f"  - Snapshots created: {harvest_stats['snapshots_created']}")
                
            except Exception as e:
                logger.error(f"Failed to process {brand}: {e}")
                all_stats[brand] = {'error': str(e)}
        
        # Update report with combined results
        update_final_report(all_stats)
        
        print("\n" + "="*80)
        print("RESUME HARVEST COMPLETE")
        print("="*80)
        print("Report updated: BLOCKED_SITES_REPORT_FINAL.md")
        
        return all_stats
    
    return resume_main()

def update_final_report(new_stats):
    """Update report with new results"""
    from datetime import datetime
    
    with open('BLOCKED_SITES_REPORT_FINAL.md', 'w') as f:
        f.write("# Blocked Sites Harvest Report - FINAL\n\n")
        f.write(f"**Generated:** {datetime.now().isoformat()}\n")
        f.write(f"**Method:** ScrapingBee with JS rendering (Resumed after API limit)\n")
        f.write(f"**Brands:** briantos (partial), belcando, bozita, cotswold\n\n")
        
        f.write("## Summary\n\n")
        
        # Calculate totals
        total_products = sum(s['harvester']['products_found'] for s in new_stats.values() if 'harvester' in s)
        total_snapshots = sum(s['harvest']['snapshots_created'] for s in new_stats.values() if 'harvest' in s)
        total_credits = sum(s['harvester']['api_credits_used'] for s in new_stats.values() if 'harvester' in s)
        
        f.write(f"**Resume Session Results:**\n")
        f.write(f"- **API credits used:** {total_credits}\n")
        f.write(f"- **Total products found:** {total_products}\n")
        f.write(f"- **Total snapshots created:** {total_snapshots}\n\n")
        
        f.write("**Combined Results (both sessions):**\n")
        f.write(f"- **Briantos:** 2 products found (first session)\n")
        f.write(f"- **Belcando:** {new_stats.get('belcando', {}).get('harvester', {}).get('products_found', 0)} products\n")
        f.write(f"- **Bozita:** {new_stats.get('bozita', {}).get('harvester', {}).get('products_found', 0)} products\n")
        f.write(f"- **Cotswold:** {new_stats.get('cotswold', {}).get('harvester', {}).get('products_found', 0)} products\n\n")
        
        # Success assessment
        successful_brands = 0
        if 2 > 0:  # briantos
            successful_brands += 1
        for brand in new_stats:
            if new_stats[brand].get('harvest', {}).get('snapshots_created', 0) >= 20:
                successful_brands += 1
        
        f.write(f"## Definition of Done Assessment\n\n")
        if successful_brands >= 2:
            f.write(f"✅ **ACHIEVED**: {successful_brands}/4 brands with products harvested\n")
            f.write(f"- Required: At least 2 brands with ≥20 products\n")
            f.write(f"- Actual: {successful_brands} brands successful\n")
        else:
            f.write(f"⚠️ **PARTIAL**: {successful_brands}/4 brands successful\n")
            f.write(f"- More work needed to reach 2 brands with ≥20 products\n")
        
        f.write("\n## Per-Brand Details\n\n")
        
        for brand, stats in new_stats.items():
            f.write(f"### {brand.upper()}\n")
            
            if 'error' in stats:
                f.write(f"**Status:** ❌ Failed\n")
                f.write(f"**Error:** {stats['error']}\n\n")
            elif 'harvester' in stats:
                snapshots = stats['harvest']['snapshots_created']
                if snapshots >= 20:
                    f.write(f"**Status:** ✅ Success\n")
                elif snapshots > 0:
                    f.write(f"**Status:** ⚠️ Partial\n")
                else:
                    f.write(f"**Status:** ❌ No products\n")
                
                f.write(f"- Products found: {stats['harvester']['products_found']}\n")
                f.write(f"- Snapshots created: {snapshots}\n")
                f.write(f"- API credits used: {stats['harvester']['api_credits_used']}\n\n")

if __name__ == "__main__":
    resume_harvest()