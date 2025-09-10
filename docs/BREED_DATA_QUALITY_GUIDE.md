# Breed Data Quality Guide

## Overview

This guide documents the breed data quality management system for the Lupito Content database. It covers issue identification, resolution procedures, and ongoing maintenance strategies.

## Table of Contents

1. [Known Issues and Root Causes](#known-issues-and-root-causes)
2. [Data Quality Standards](#data-quality-standards)
3. [Scraper Usage Guidelines](#scraper-usage-guidelines)
4. [Issue Resolution Procedures](#issue-resolution-procedures)
5. [Validation and Monitoring](#validation-and-monitoring)
6. [Maintenance Schedule](#maintenance-schedule)

## Known Issues and Root Causes

### 1. Historical Data Corruption (Sep 6-9, 2025)

**Issue**: 198 breeds were incorrectly categorized, with 81% marked as "small" regardless of actual size.

**Root Cause**: Early version of the Wikipedia scraper had parsing issues with:
- Unicode dash characters in weight ranges
- Incorrect weight extraction logic
- Missing size recalculation on updates

**Resolution**: Fixed scraper logic and re-scraped affected breeds.

### 2. Size-Weight Mismatches

**Issue**: Breed size categories don't match their weight ranges.

**Root Cause**: 
- Scraper not recalculating size when updating existing records
- Partial updates preserving old incorrect values
- NULL weight handling keeping non-NULL size values

**Resolution**: Implemented validation logic and size recalculation for all updates.

### 3. NULL Weight Data

**Issue**: 177 breeds have NULL weights but assigned (incorrect) size values.

**Root Cause**: When Wikipedia lacks weight data, scraper doesn't set size to NULL, preserving old values.

**Resolution**: Updated scraper to explicitly set size=NULL when weight data is unavailable.

## Data Quality Standards

### Size Categories

Size categories are strictly determined by weight ranges:

| Size Category | Weight Range (kg) | Examples |
|--------------|------------------|-----------|
| Tiny | < 4 kg | Chihuahua, Yorkshire Terrier |
| Small | 4-10 kg | Pug, Boston Terrier |
| Medium | 10-25 kg | Beagle, Cocker Spaniel |
| Large | 25-45 kg | Labrador, German Shepherd |
| Giant | > 45 kg | Great Dane, Saint Bernard |

### Data Completeness Targets

| Field | Target Completeness | Current | Priority |
|-------|-------------------|---------|----------|
| Weight | 85% | 69.6% | HIGH |
| Height | 80% | 67.2% | MEDIUM |
| Size | 85% | 69.5% | HIGH |
| Lifespan | 60% | 38.8% | LOW |
| Energy | 75% | 66.6% | MEDIUM |
| Trainability | 75% | 70.2% | LOW |

### Quality Score Targets

- **Overall Quality Score**: ≥ 80% (Grade B or higher)
- **Size Accuracy**: ≥ 95%
- **Weight Accuracy**: ≥ 90%
- **Update Recency**: 100% within 30 days

## Scraper Usage Guidelines

### Primary Scraper

**Always use**: `jobs/wikipedia_breed_scraper_fixed.py`

This is the only approved scraper with:
- Proper Unicode handling
- Size validation logic
- NULL weight handling
- Comprehensive logging

### Deprecated Scrapers

The following scrapers are deprecated and moved to `deprecated/scrapers/`:
- `wikipedia_breed_scraper.py` (old version with bugs)
- Test scripts and experimental scrapers

### Running the Scraper

```bash
# Activate virtual environment
source venv/bin/activate

# Single breed scraping
python3 -c "
from jobs.wikipedia_breed_scraper_fixed import WikipediaBreedScraper
scraper = WikipediaBreedScraper()
scraper.scrape_breed('Labrador Retriever', 'https://en.wikipedia.org/wiki/Labrador_Retriever')
"

# Batch scraping from file
python3 rescrape_all_breeds.py --min-delay 3 --max-delay 7

# Fix size accuracy issues
python3 fix_size_accuracy.py
```

### Rate Limiting

- **Minimum delay**: 3 seconds between requests
- **Maximum delay**: 7 seconds between requests
- **Batch size**: Maximum 100 breeds per session

## Issue Resolution Procedures

### 1. Identifying Issues

Run the quality analysis script:

```bash
python3 analyze_full_quality.py
```

This will identify:
- Size-weight mismatches
- NULL weight issues
- Data completeness gaps
- Update recency problems

### 2. Fixing Size Accuracy

```bash
python3 fix_size_accuracy.py
```

This script:
1. Identifies all breeds with size issues
2. Recalculates correct sizes based on weight
3. Updates database with corrections
4. Validates the fixes

### 3. Re-scraping Specific Breeds

For targeted re-scraping:

```python
# Create a list of breeds to fix
BREEDS_TO_FIX = {
    'Breed Name': 'wikipedia_url',
    # ...
}

# Run targeted scraper
python3 scrape_critical_breeds.py
```

### 4. Handling NULL Weights

When a breed has no weight data available:
1. Size should be set to NULL (not guessed)
2. Document in notes field if size is known from other sources
3. Consider alternative data sources

## Validation and Monitoring

### Pre-Update Validation

Before updating any breed:
1. Check if weight data exists
2. Calculate expected size from weight
3. Log any discrepancies
4. Ensure full record update (not partial)

### Post-Update Validation

After updates:
1. Verify size matches weight calculation
2. Check update timestamp
3. Confirm no NULL weights have assigned sizes
4. Run quality analysis

### Monitoring Commands

```bash
# Check recent updates
python3 -c "
import pandas as pd
from supabase import create_client
# ... check breeds updated today
"

# Verify critical breeds
python3 -c "
# ... check top 20 popular breeds
"

# Size accuracy check
python3 -c "
# ... compare sizes with weight calculations
"
```

## Maintenance Schedule

### Daily Tasks
- Monitor scraping logs for errors
- Check critical breeds (top 20) for data integrity
- Review any manual data corrections

### Weekly Tasks
- Run full quality analysis
- Fix any size accuracy issues
- Update breeds with stale data (>30 days)

### Monthly Tasks
- Comprehensive data audit
- Re-scrape breeds with incomplete data
- Update this documentation with new findings
- Archive old scraper versions

### Quarterly Tasks
- Review and update size category thresholds
- Evaluate new data sources
- Performance optimization of scrapers
- Database cleanup and optimization

## Troubleshooting

### Common Issues and Solutions

1. **Scraper returns NULL weight but breed obviously has weight**
   - Check Wikipedia page structure changes
   - Update weight extraction patterns
   - Consider manual override

2. **Size doesn't match weight after update**
   - Verify scraper is using latest version
   - Check for partial update issues
   - Run fix_size_accuracy.py

3. **Breeds not found on Wikipedia**
   - Check alternative spellings
   - Try breed name with "(dog)" suffix
   - Consider alternative data sources

4. **Rate limiting or blocking**
   - Increase delay between requests
   - Rotate user agents
   - Consider using proxy service

## Quality Metrics

Track these metrics regularly:

```python
# Key metrics to monitor
metrics = {
    'coverage': 'Percentage of benchmark breeds in database',
    'completeness': 'Percentage of non-NULL fields',
    'size_accuracy': 'Percentage where size matches weight calculation',
    'weight_accuracy': 'Percentage within 20% of benchmark',
    'update_recency': 'Percentage updated within 30 days',
}
```

## Appendix: SQL Queries

### Find breeds with size issues
```sql
SELECT breed_slug, display_name, size, weight_kg_max
FROM breeds_details
WHERE (weight_kg_max < 4 AND size != 'tiny')
   OR (weight_kg_max >= 4 AND weight_kg_max < 10 AND size != 'small')
   OR (weight_kg_max >= 10 AND weight_kg_max < 25 AND size != 'medium')
   OR (weight_kg_max >= 25 AND weight_kg_max < 45 AND size != 'large')
   OR (weight_kg_max >= 45 AND size != 'giant');
```

### Find breeds with NULL weight but assigned size
```sql
SELECT breed_slug, display_name, size
FROM breeds_details
WHERE weight_kg_max IS NULL AND size IS NOT NULL;
```

### Check update recency
```sql
SELECT 
    DATE(updated_at) as update_date,
    COUNT(*) as breed_count
FROM breeds_details
GROUP BY DATE(updated_at)
ORDER BY update_date DESC
LIMIT 30;
```

---

**Last Updated**: September 10, 2025  
**Maintained By**: Lupito Content Team  
**Version**: 1.0