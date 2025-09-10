# BREEDS DATA QUALITY AUDIT REPORT

**Date:** 2025-09-10  
**Purpose:** Identify and document data quality issues in breed tables

## CRITICAL FINDINGS

### 🚨 Major Data Corruption in breeds_details Table

The `breeds_details` table contains severely corrupted data from Wikipedia scraping, which has propagated to `breeds_published`. This affects fundamental breed characteristics including size and weight.

## EXAMPLES OF CORRUPTED DATA

| Breed | Actual Weight | breeds_details (Wrong) | breeds_published (Wrong) |
|-------|--------------|------------------------|---------------------------|
| **Labrador Retriever** | 25-36 kg | 0.82-1.0 kg ❌ | 0.82-1.0 kg ❌ |
| **German Shepherd** | 22-40 kg | 4.54-5.44 kg ❌ | 4.54-5.44 kg ❌ |
| **Golden Retriever** | 25-34 kg | 4.54-5.44 kg ❌ | 4.54-5.44 kg ❌ |
| **French Bulldog** | 8-14 kg | 4.54-5.44 kg ❌ | 4.54-5.44 kg ❌ |

### Size Categories Also Affected

- **Labrador Retriever:** Marked as "small" (should be "large")
- **German Shepherd:** Marked as "small" (should be "large")
- **Golden Retriever:** Marked as "small" (should be "large")

## ROOT CAUSE ANALYSIS

1. **Wikipedia Scraper Issues:**
   - Likely parsing error in weight extraction
   - Possible unit conversion error (lbs to kg)
   - May have scraped wrong sections of Wikipedia pages

2. **Data Propagation:**
   - `breeds_published` is using `breeds_details` as source
   - Corrupted data has propagated throughout the system

3. **Missing Validation:**
   - No sanity checks on scraped data
   - No validation against known breed characteristics

## STATISTICS

- **Total breeds in breeds_published:** 636
- **Total breeds in breeds_details:** 583
- **Missing from breeds_details:** 53 breeds
- **Suspicious data patterns identified:** Multiple large breeds marked as small

## AFFECTED BREEDS REQUIRING IMMEDIATE ATTENTION

Based on the analysis, ALL breeds in `breeds_details` need to be reviewed, but priority should be given to popular breeds that are clearly miscategorized.

## RECOMMENDATIONS

### Immediate Actions

1. **Re-scrape ALL Wikipedia data** with fixed parser:
   - Fix weight parsing logic
   - Add unit conversion validation
   - Implement sanity checks (e.g., no dog over 100kg, no adult dog under 1kg)

2. **Add data validation layer:**
   - Weight ranges must be reasonable for size category
   - Size categories must align with weight ranges
   - Cross-reference with multiple sources

3. **Scrape missing 53 breeds** to complete dataset

### Data Quality Rules to Implement

| Size Category | Expected Weight Range |
|--------------|----------------------|
| Tiny | 1-5 kg |
| Small | 5-10 kg |
| Medium | 10-25 kg |
| Large | 25-45 kg |
| Giant | 45+ kg |

### Next Steps

1. **Fix Wikipedia scraper** (jobs/wikipedia_breed_scraper.py)
2. **Re-scrape all 583 existing breeds** with corrected parser
3. **Scrape 53 missing breeds** from missing_breeds_wikipedia_urls.txt
4. **Update breeds_published** with corrected data
5. **Implement validation checks** to prevent future corruption

## FILES GENERATED

- `breeds_audit_data.json` - Detailed audit data
- `breed_size_audit.json` - Size comparison analysis
- `missing_breeds_wikipedia_urls.txt` - URLs for 53 missing breeds
- `breeds_comparison_analysis.json` - Table comparison data

## CONCLUSION

The breed data requires immediate remediation. The Wikipedia scraper has fundamental parsing issues that have corrupted weight and size data for most breeds. This affects the entire Lupito system's ability to provide accurate feeding recommendations.