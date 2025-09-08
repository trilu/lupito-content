# AKC Breed Scraper Documentation

## Overview
This document provides complete documentation for the AKC breed scraper implementation to improve breed coverage in the lupito-content database.

**Created**: 2025-01-07  
**Purpose**: Scrape breed data from akc.org to fill gaps in breeds_details table

## Current Status

### Database Coverage Analysis
- **Total breeds in `breeds` table**: 546
- **Total breeds in `breeds_details` table**: 196  
- **Current coverage**: 28% (153 matching breeds)
- **Missing breeds**: 393 breeds need details

### AKC Resource
- **Total AKC breeds available**: 187
- **URL pattern**: `https://www.akc.org/dog-breeds/{breed-slug}/`
- **Potential coverage improvement**: From 28% to ~50-60%

## Implementation Components

### 1. AKC Breed Scraper (`jobs/akc_breed_scraper.py`)
**Status**: ✅ Created

**Features**:
- Extracts breed characteristics from AKC pages
- Maps AKC data to our database schema
- Handles unit conversions (inches→cm, lbs→kg)
- Normalizes characteristics to controlled vocabulary
- Saves to `breeds_details` table

**Key Methods**:
- `extract_akc_breed_data()` - Main extraction logic
- `_extract_breed_traits()` - Gets structured breed data
- `_extract_content_sections()` - Gets comprehensive text content
- `_map_traits_to_schema()` - Maps to our database fields
- `save_breed()` - Saves to Supabase

### 2. URL List (`akc_breed_urls.txt`)
**Status**: 🔄 In Progress

Contains all 187 AKC breed URLs for scraping.

### 3. Database Schema

#### `breeds_details` Table Fields
```sql
- id (auto)
- breed_slug (unique identifier)
- display_name
- comprehensive_content (JSONB)
- origin
- size (small|medium|large|giant)
- energy (low|moderate|high|very high)
- coat_length (short|medium|long)
- shedding (low|moderate|high)
- trainability (easy|moderate|challenging)
- bark_level (low|moderate|high)
- height_cm_min, height_cm_max
- weight_kg_min, weight_kg_max
- lifespan_years_min, lifespan_years_max
- friendliness_to_dogs (1-5)
- friendliness_to_humans (1-5)
- created_at, updated_at
```

## Usage Instructions

### 1. Test Run (5 breeds)
```bash
cd /Users/sergiubiris/Desktop/lupito-content
python3 jobs/akc_breed_scraper.py --test
```

### 2. Limited Run (specific number)
```bash
python3 jobs/akc_breed_scraper.py --limit 20
```

### 3. Full Run (all breeds)
```bash
python3 jobs/akc_breed_scraper.py --urls-file akc_breed_urls.txt
```

### 4. Check Progress
```bash
# Check database coverage
python3 -c "
from supabase import create_client
import os
from dotenv import load_dotenv
load_dotenv()
client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY'))
result = client.table('breeds_details').select('breed_slug').execute()
print(f'Total breeds with details: {len(result.data)}')
"
```

## Sample AKC Breeds to Scrape

### High Priority (Missing Popular Breeds)
1. American Bulldog - `american-bulldog`
2. Australian Kelpie - `australian-kelpie`
3. Cairn Terrier - `cairn-terrier`
4. German Shorthaired Pointer - `german-shorthaired-pointer`
5. German Wirehaired Pointer - `german-wirehaired-pointer`
6. Jack Russell Terrier - `russell-terrier` (AKC name)
7. Chinese Shar-Pei - `chinese-shar-pei`
8. Saint Bernard - `st-bernard`
9. Doberman Pinscher - `doberman-pinscher`
10. Staffordshire Bull Terrier - `staffordshire-bull-terrier`

### Additional Available Breeds (Sample)
- Affenpinscher
- Afghan Hound
- Airedale Terrier
- Akita
- Alaskan Klee Kai
- Alaskan Malamute
- Anatolian Shepherd Dog
- Australian Cattle Dog
- Australian Shepherd
- Basenji
- Beagle
- Belgian Malinois
- Bernese Mountain Dog
- Border Collie
- Boston Terrier
- Boxer
- Brittany
- Bulldog
- Cavalier King Charles Spaniel
- Chihuahua
- Cocker Spaniel
- Dachshund
- Dalmatian
- English Setter
- French Bulldog
- German Shepherd Dog
- Golden Retriever
- Great Dane
- Greyhound
- Irish Setter
- Labrador Retriever
- Maltese
- Mastiff
- Newfoundland
- Pomeranian
- Poodle
- Pug
- Rottweiler
- Siberian Husky
- Yorkshire Terrier

## Troubleshooting

### Common Issues

1. **Rate Limiting**
   - Current: 2 seconds between requests
   - Adjust in `config['rate_limit_seconds']` if needed

2. **Extraction Failures**
   - Check AKC page structure changes
   - Review extraction patterns in `_extract_breed_traits()`

3. **Database Errors**
   - Verify Supabase credentials in `.env`
   - Check `breeds_details` table exists

### Monitoring Progress

Check scraper statistics:
```python
# In scraper output
URLs processed: X
New breeds added: X
Breeds updated: X
Extraction success: X
Success rate: X%
```

Check QA report:
```bash
ls akc_breed_qa_report_*.csv
```

## Expected Outcomes

### Coverage Improvement
- **Before**: 196 breeds with details (28% coverage)
- **After**: ~350 breeds with details (~60% coverage)
- **New breeds added**: ~150-180

### Data Quality
- Standardized size categories
- Normalized energy levels
- Consistent weight/height in metric units
- Comprehensive content for AI training

## Next Steps

1. ✅ Create scraper script
2. 🔄 Generate URL list (in progress)
3. ⏳ Run test batch
4. ⏳ Execute full scrape
5. ⏳ Generate coverage report

## Session Recovery

If session interrupts, resume with:

1. Check what's been scraped:
```bash
# Count breeds in database
python3 -c "
from supabase import create_client
import os
from dotenv import load_dotenv
load_dotenv()
client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY'))
akc = client.table('breeds_details').select('breed_slug').execute()
print(f'Total breeds: {len(akc.data)}')
"
```

2. Resume scraping:
```bash
# Continue from where left off
python3 jobs/akc_breed_scraper.py --urls-file akc_breed_urls.txt
```

## Files Created

1. `/jobs/akc_breed_scraper.py` - Main scraper script
2. `/akc_breed_urls.txt` - List of all AKC URLs (pending)
3. `/AKC_BREED_SCRAPER_DOCS.md` - This documentation
4. `/akc_breed_qa_report_*.csv` - QA reports (after runs)

## Contact

For issues or questions about the lupito-content breed scraping:
- Check this documentation first
- Review the scraper code in `jobs/akc_breed_scraper.py`
- Examine QA reports for specific breed issues