# Breed Data Comprehensive Audit Report
Generated: 2025-09-17 17:39:25

============================================================
BREEDS_PUBLISHED ANALYSIS
============================================================

Total Breeds: 583

Field Coverage:
  id: 100.0% (583/583)
  breed_slug: 100.0% (583/583)
  display_name: 100.0% (583/583)
  aliases: 100.0% (583/583)
  size_category: 100.0% (583/583)
  growth_end_months: 100.0% (583/583)
  senior_start_months: 100.0% (583/583)
  energy: 100.0% (583/583)
  trainability: 100.0% (583/583)
  size_from: 100.0% (583/583)

Size Distribution:
  XS: 64 breeds
  S:  40 breeds
  M:  323 breeds
  L:  106 breeds
  XL: 50 breeds

Energy Distribution:
  Low:       42 breeds
  Moderate:  461 breeds
  High:      80 breeds
  Very High: 0 breeds

Weight Coverage: 92.8%
Missing Weight: 42 breeds


============================================================
BREEDS_DETAILS ANALYSIS (Wikipedia)
============================================================

Total Breeds: 583
Has Raw HTML: 0 (0.0%)
Avg HTML Length: 0 chars
Max HTML Length: 0 chars

Field Coverage:


============================================================
MISSING DATA ANALYSIS
============================================================

Critical Missing Data:
  Breeds without weight: 42 (7.2%)
  Breeds with default energy (moderate): 461 (79.1%)
  Breeds with no energy data: 0 (0.0%)
  Breeds without Wikipedia data: 0

Top 10 Breeds Missing Weight:
  - Africanis (africanis)
  - Anglo-Français de Petite Vénerie (anglo-fran-ais-de-petite-v-nerie)
  - Argentine Pila (argentine-pila)
  - Ariège Pointer (ari-ge-pointer)
  - Australian Silky Terrier (australian-silky-terrier)
  - Australian Stumpy Tail Cattle Dog (australian-stumpy-tail-cattle-dog)
  - Austrian Pinscher (austrian-pinscher)
  - Basset Bleu de Gascogne (basset-bleu-de-gascogne)
  - Basset Fauve de Bretagne (basset-fauve-de-bretagne)
  - Bavarian Mountain Hound (bavarian-mountain-hound)


============================================================
DATA QUALITY CHECKS
============================================================

Quality Issues Found:
  Size/Weight Inconsistencies: 9
  Growth End Outliers (<6 or >24 months): 0
  Senior Start Outliers (<60 or >144 months): 0

Size/Weight Inconsistencies (first 5):
  - Black And Tan Coonhound: Size=xs, Weight=18.1-34.0kg, Expected=0-7kg
  - Boerboel: Size=m, Weight=68.0-91.0kg, Expected=10-30kg
  - Doberman Pinscher: Size=l, Weight=4.54-5.44kg, Expected=25-50kg
  - English Toy Spaniel: Size=m, Weight=3.6-6.4kg, Expected=10-30kg
  - Giant Schnauzer: Size=xs, Weight=35.0-47.0kg, Expected=0-7kg


============================================================
DOGS TABLE LINKAGE
============================================================

Total Dogs: 38
Dogs with Breed: 35 (92.1%)

Top 10 Breeds in Dogs Table:
  - Beagle: 4 dogs
  - Mongrel: 4 dogs
  - German Shepherd: 3 dogs
  - Golden Retriever: 2 dogs
  - Siberian Husky: 2 dogs
  - Labrador Retriever: 2 dogs
  - Entlebucher Mountain Dog: 2 dogs
  - Dachshund: 1 dogs
  - German Hound: 1 dogs
  - Yorkshire Terrier: 1 dogs


============================================================
RECOMMENDATIONS
============================================================

Priority 1 - Critical Data Fixes:
  1. Add weight data for 42 breeds missing weights
  2. Review and update energy levels for 461 breeds with defaults
  3. Add energy data for 0 breeds without any energy info

Priority 2 - Wikipedia Enhancement:
  1. Re-scrape all 583 breeds from Wikipedia
  2. Store complete HTML in GCS (current limit: 50k chars)
  3. Extract missing fields: health issues, exercise needs, dietary requirements
  4. Add 0 breeds without Wikipedia data

Priority 3 - Quality Improvements:
  1. Fix 9 size/weight inconsistencies
  2. Review 0 growth boundary outliers
  3. Review 0 senior age outliers
  4. Implement breeds_overrides table for manual corrections

Priority 4 - Enrichment:
  1. Add breed-specific health conditions
  2. Add nutrition requirements
  3. Add exercise requirements
  4. Add temperament scores

Estimated Data Quality Score: 85/100
