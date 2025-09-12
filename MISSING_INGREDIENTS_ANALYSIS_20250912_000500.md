# Missing Ingredients Analysis Report
**Generated:** 2025-09-12 00:05:00
**Database:** foods_published_prod
**GCS Bucket:** lupito-content-raw-eu

## Summary

- **Briantos:** 31 SKUs missing ingredients (0 have snapshots, 31 need harvest)
- **Bozita:** 31 SKUs missing ingredients (2 have snapshots, 29 need harvest)

## Briantos Detailed Analysis

**Total SKUs missing ingredients_tokens:** 31
**SKUs with GCS snapshots:** 0
**SKUs needing harvest:** 31

### SKUs Needing Harvest (Sample)

- Adult Mobility Grain-Free Chicken  Potato (`briantos|adult_mobility_grain-free_chicken__potato|unknown`)
  - URL: https://petfoodexpert.com/food/briantos-adult-mobility-grain-free-chicken-potato
- Adult Salmon  Rice (`briantos|adult_salmon__rice|unknown`)
  - URL: https://petfoodexpert.com/food/briantos-adult-salmon-rice
- Adult Sensitive Lamb  Rice (`briantos|adult_sensitive_lamb__rice|unknown`)
  - URL: https://petfoodexpert.com/food/briantos-adult-sensitive-lamb-rice
- Briantos Adult Light (`briantos|briantos_adult_light|dry`)
  - URL: https://www.zooplus.com/shop/dogs/dry_dog_food/briantos/briantos_specialised/527598?activeVariant=527598.2
- Briantos Adult Mini Lamb & Rice (`briantos|briantos_adult_mini_lamb_&_rice|dry`)
  - URL: https://www.zooplus.com/shop/dogs/dry_dog_food/briantos/briantos_adult/527599?activeVariant=527599.6
- Briantos Adult Mobility Grain-Free Chicken & Potato (`briantos|briantos_adult_mobility_grain-free_chicken_&_potato|dry`)
  - URL: https://www.zooplus.com/shop/dogs/dry_dog_food/briantos/grain_free/1910367?activeVariant=1910367.3
- Briantos Adult Salmon & Rice (`briantos|briantos_adult_salmon_&_rice|dry`)
  - URL: https://www.zooplus.com/shop/dogs/dry_dog_food/briantos/briantos_adult/527603?activeVariant=527603.1
- Briantos Adult Sensitive Lamb & Rice (`briantos|briantos_adult_sensitive_lamb_&_rice|dry`)
  - URL: https://www.zooplus.com/shop/dogs/dry_dog_food/briantos/briantos_specialised/527600?activeVariant=527600.3
- Briantos Junior (`briantos|briantos_junior|dry`)
  - URL: https://www.zooplus.com/shop/dogs/dry_dog_food/briantos/briantos_junior/527602?activeVariant=527602.1
- Briantos Maxi Adult (`briantos|briantos_maxi_adult|dry`)
  - URL: https://www.zooplus.com/shop/dogs/dry_dog_food/briantos/briantos_adult/527596?activeVariant=527596.1
  ... and 21 more

## Bozita Detailed Analysis

**Total SKUs missing ingredients_tokens:** 31
**SKUs with GCS snapshots:** 2
**SKUs needing harvest:** 29

### Sample Failure Analysis

**Sample 1:** Robur Sensitive Single Protein Lamb  Rice
- Product Key: `bozita|robur_sensitive_single_protein_lamb__rice|unknown`
- Snapshot: `manufacturers/bozita/2025-09-11/dog-food_bozita-robur-sensitive-single-protein-lamb-rice.html`
- **Failure Reason:** no_ingredients_section_found
- **Language Detected:** en
- **Text Patterns Found:** None
- **Working Selectors:** None

**Sample 2:** Robur Sensitive Grain Free Reindeer
- Product Key: `bozita|robur_sensitive_grain_free_reindeer|unknown`
- Snapshot: `manufacturers/bozita/2025-09-11/dog-food_bozita-robur-sensitive-grain-free-reindeer.html`
- **Failure Reason:** no_ingredients_section_found
- **Language Detected:** en
- **Text Patterns Found:** None
- **Working Selectors:** None

### Failure Reasons Summary

- no_ingredients_section_found: 2

### SKUs Needing Harvest (Sample)

- Bozita Grain Free Mother & Puppy Elk (`bozita|bozita_grain_free_mother_&_puppy_elk|dry`)
  - URL: https://www.zooplus.com/shop/dogs/dry_dog_food/bozita/bozita_dog_food/1487109?activeVariant=1487109.6
- Bozita Grain Free Mother & Puppy XL Elk (`bozita|bozita_grain_free_mother_&_puppy_xl_elk|dry`)
  - URL: https://www.zooplus.com/shop/dogs/dry_dog_food/bozita/bozita_dog_food/1488409?activeVariant=1488409.7
- Bozita Original Adult Flavour Plus with Reindeer - Wheat-Free (`bozita|bozita_original_adult_flavour_plus_with_reindeer_-_wheat-free|dry`)
  - URL: https://www.zooplus.com/shop/dogs/dry_dog_food/bozita/bozita_dog_food/128406?activeVariant=128406.11
- Bozita Original Adult Light (`bozita|bozita_original_adult_light|dry`)
  - URL: https://www.zooplus.com/shop/dogs/dry_dog_food/bozita/bozita_dog_food/128405?activeVariant=128405.9
- Bozita Original Adult XL with Lamb - Wheat-Free (`bozita|bozita_original_adult_xl_with_lamb_-_wheat-free|dry`)
  - URL: https://www.zooplus.com/shop/dogs/dry_dog_food/bozita/bozita_dog_food/128404?activeVariant=128404.8
- Bozita Original Puppy & Junior with Chicken - Wheat-Free (`bozita|bozita_original_puppy_&_junior_with_chicken_-_wheat-free|dry`)
  - URL: https://www.zooplus.com/shop/dogs/dry_dog_food/bozita/bozita_dog_food/128402?activeVariant=128402.12
- Bozita Grain Free Elk (`bozita|bozita_grain_free_elk|dry`)
  - URL: https://www.zooplus.com/shop/dogs/dry_dog_food/bozita/bozita_dog_food/1488412?activeVariant=1488412.5
- Bozita Grain Free Reindeer (`bozita|bozita_grain_free_reindeer|dry`)
  - URL: https://www.zooplus.com/shop/dogs/dry_dog_food/bozita/bozita_dog_food/1486333?activeVariant=1486333.4
- Bozita Grain Free Salmon & Beef for Large Dogs (`bozita|bozita_grain_free_salmon_&_beef_for_large_dogs|dry`)
  - URL: https://www.zooplus.com/shop/dogs/dry_dog_food/bozita/bozita_dog_food/1488617?activeVariant=1488617.4
- Bozita Grain Free Salmon & Beef for Small Dogs (`bozita|bozita_grain_free_salmon_&_beef_for_small_dogs|dry`)
  - URL: https://www.zooplus.com/shop/dogs/dry_dog_food/bozita/bozita_dog_food/1488611?activeVariant=1488611.3
  ... and 19 more

## Recommendations

- **Priority:** Expand text pattern matching to catch edge cases
- Prioritize harvesting missing snapshots for products with URLs
- Consider brand-specific extraction rules for better coverage
- Implement fallback extraction methods for JavaScript-heavy pages
