#!/usr/bin/env python3
"""Analyze the brand discovery results"""

import yaml

# Load the results
with open('data/brand_sites_final.yaml', 'r') as f:
    data = yaml.unsafe_load(f)

total = len(data['brands'])
with_sites = data['metadata'].get('brands_with_websites', 0)
can_crawl = data['metadata'].get('brands_crawlable', 0)
need_sb = data['metadata'].get('brands_need_scrapingbee', 0)

print('='*60)
print('🎉 BRAND WEBSITE DISCOVERY COMPLETE!')
print('='*60)
print()
print('📊 FINAL RESULTS:')
print(f'  Total brands processed: {total}/279')
print(f'  Websites found: {with_sites} ({with_sites/279*100:.1f}% of all brands)')
print(f'  Can crawl directly: {can_crawl}')
print(f'  Need ScrapingBee (robots blocked): {need_sb}')
print(f'  No website found: {total - with_sites}')
print()

# Count by discovery method
methods = {}
for brand_data in data['brands'].values():
    if brand_data.get('has_website'):
        method = brand_data.get('discovery_method', 'unknown')
        methods[method] = methods.get(method, 0) + 1

print('🔍 Discovery methods:')
for method, count in sorted(methods.items(), key=lambda x: x[1], reverse=True):
    print(f'  {method}: {count} brands')

print()
print('💰 ScrapingBee usage:')
credits = data['metadata'].get('scrapingbee_credits_used', 0)
print(f'  Credits used for discovery: {credits}')
print(f'  Brands needing ScrapingBee for content: {need_sb}')
print(f'  Estimated cost for blocked sites: ${need_sb * 5 * 0.001:.2f} (5 credits per page)')

# List some brands that need ScrapingBee
print()
print('⚠️ Sample brands needing ScrapingBee for content (robots.txt blocked):')
count = 0
for slug, brand_data in data['brands'].items():
    if brand_data.get('scrapingbee_fallback'):
        print(f'  - {brand_data["brand_name"]}: {brand_data.get("website_url")}')
        count += 1
        if count >= 5:
            if need_sb > 5:
                print(f'  ... and {need_sb - 5} more')
            break

# Coverage breakdown
print()
print('📈 COVERAGE ANALYSIS:')
print(f'  Brands with websites: {with_sites}/{total} ({with_sites/total*100:.1f}%)')
print(f'  Expected to find more: ~{int(total * 0.85 - with_sites)} brands (targeting 85%)')
print(f'  Success rate so far: {with_sites/total*100:.1f}%')

# Top missing brands (no website found)
print()
print('❌ Sample brands without websites found:')
count = 0
for slug, brand_data in data['brands'].items():
    if not brand_data.get('has_website'):
        print(f'  - {brand_data["brand_name"]}')
        count += 1
        if count >= 10:
            no_site_count = total - with_sites
            if no_site_count > 10:
                print(f'  ... and {no_site_count - 10} more')
            break

print()
print('✅ NEXT STEPS:')
print('1. Use ScrapingBee to scrape content from blocked sites')
print('2. Manually research brands without websites')
print('3. Begin manufacturer data harvesting for brands with websites')
print('4. Update foods_published_preview with enriched data')