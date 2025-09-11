#!/usr/bin/env python3
"""
Quick website mapper using known brands and common patterns
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

# Load brand data
report_dir = Path("reports/MANUF")
brands_df = pd.read_csv(report_dir / "MANUF_BRAND_PRIORITY.csv")

# Manual mappings for known brands
manual_mappings = {
    'brit': 'https://www.brit-petfood.com',
    'alpha': 'https://www.alphapetfoods.com', 
    'bozita': 'https://www.bozita.com',
    'belcando': 'https://www.belcando.de',
    'arden': 'https://www.ardengrange.com',
    'barking': 'https://www.barkingheads.co.uk',
    'briantos': 'https://www.briantos.de',
    'bosch': 'https://www.bosch-tiernahrung.de',
    'acana': 'https://www.acana.com',
    'advance': 'https://www.advance-pet.com',
    'affinity': 'https://www.affinity-petcare.com',
    'bakers': 'https://www.bakerspetfood.co.uk',
    'burns': 'https://burnspet.co.uk',
    'eukanuba': 'https://www.eukanuba.com',
    'hills': 'https://www.hillspet.com',
    'iams': 'https://www.iams.com',
    'pedigree': 'https://www.pedigree.com',
    'purina': 'https://www.purina.co.uk',
    'royal-canin': 'https://www.royalcanin.com',
    'whiskas': 'https://www.whiskas.co.uk',
    'applaws': 'https://www.applaws.com',
    'lily-s-kitchen': 'https://www.lilyskitchen.co.uk',
    'harringtons': 'https://www.harringtonspetfood.com',
    'beco': 'https://www.becopets.com',
    'arion': 'https://www.arionpetfood.com',
    'aatu': 'https://www.aatu.co.uk',
    'akela': 'https://www.akelapetfood.co.uk',
    'arden-grange': 'https://www.ardengrange.com',
    'autarky': 'https://www.autarky.co.uk',
    'benyfit': 'https://www.benyfitnatural.co.uk',
    'beta': 'https://www.beta-petfood.co.uk',
    'billy-margot': 'https://www.billymargot.com',
    'bounce': 'https://www.bounceandbella.co.uk',
    'burgess': 'https://www.burgesspetcare.com',
    'butchers': 'https://www.butcherspetcare.com',
    'canagan': 'https://www.canagan.co.uk',
    'carnilove': 'https://www.carnilove.com',
    'cesar': 'https://www.cesar.com',
    'chappie': 'https://www.chappiepetfood.com',
    'country-value': 'https://www.countryvaluepetfoods.co.uk',
    'wainwrights': 'https://www.wainwrights.co.uk',
    'wagg': 'https://www.waggfoods.com',
    'wellness': 'https://www.wellnesspetfood.com',
    'wolfsblut': 'https://www.wolfsblut.com',
    'yora': 'https://www.yorapetfoods.com',
    'zooplus': 'https://www.zooplus.co.uk'
}

# Update brands with websites
results = []
for _, row in brands_df.head(50).iterrows():  # Top 50 brands
    brand = row['brand']
    brand_slug = row['brand_slug']
    
    # Check if we have existing website
    if pd.notna(row.get('website_url')) and row['website_url']:
        website = row['website_url']
        source = 'existing'
    # Check manual mappings
    elif brand_slug in manual_mappings:
        website = manual_mappings[brand_slug]
        source = 'manual'
    # Try simple patterns
    elif brand_slug in ['bright', 'borders', 'betty', 'biofood', 'browns']:
        website = f"https://www.{brand_slug}petfood.com"
        source = 'pattern'
    else:
        website = None
        source = None
    
    results.append({
        'brand': brand,
        'brand_slug': brand_slug,
        'product_count': row['product_count'],
        'website_url': website,
        'source': source,
        'has_website': website is not None
    })

# Create DataFrame
results_df = pd.DataFrame(results)

# Save results
output_file = report_dir / "MANUFACTURER_WEBSITES.csv"
results_df.to_csv(output_file, index=False)

# Generate report
report = f"""# MANUFACTURER WEBSITE MAPPING
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary
- Brands Mapped: {len(results_df)}
- With Websites: {results_df['has_website'].sum()}
- Success Rate: {results_df['has_website'].sum() / len(results_df) * 100:.1f}%

## Top Brands with Websites

| Brand | Products | Website | Source |
|-------|----------|---------|--------|
"""

for _, row in results_df[results_df['has_website']].head(20).iterrows():
    report += f"| {row['brand']} | {row['product_count']} | {row['website_url']} | {row['source']} |\n"

report += f"""

## Brands Without Websites
"""

no_website = results_df[~results_df['has_website']]
report += f"Missing websites for {len(no_website)} brands: {', '.join(no_website['brand_slug'].head(10).tolist())}"

print(report)

# Save report
with open(report_dir / "MANUFACTURER_WEBSITES.md", "w") as f:
    f.write(report)

print(f"\nSaved to {output_file}")