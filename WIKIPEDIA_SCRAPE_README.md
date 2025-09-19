# Wikipedia Breed Scraping - Ready to Run

## What Will Happen

When you run `./run_wikipedia_scrape.sh` or `python3 wikipedia_breed_rescraper_gcs.py`:

### 1. Data Collection (583 breeds)
- Fetches all breeds from `breeds_published` view
- For each breed, tries multiple Wikipedia URLs (display name, aliases, with "Dog" suffix)
- Extracts structured data from infoboxes and content

### 2. Data Extraction
The scraper extracts:
- **Weight**: min/max/avg in kg (converts from lbs if needed)
- **Height**: min/max in cm (converts from inches if needed)
- **Lifespan**: min/max/avg in years
- **Energy level**: from exercise/activity sections
- **Temperament**: from temperament sections
- **Health issues**: from health sections (first 3 paragraphs)
- **Origin**: country of origin
- **Coat & Colors**: physical characteristics

### 3. Storage
- **Full HTML**: Saved to GCS at `gs://lupito-content-raw-eu/scraped/wikipedia_breeds/[timestamp]/[breed-slug].html`
- **Extracted JSON**: Saved to GCS at same location with `.json` extension
- **Database**: Updates `breeds_published` with extracted data (only in production mode, not test mode)

### 4. Database Updates
For each successfully scraped breed, updates:
- `adult_weight_min_kg`, `adult_weight_max_kg`, `adult_weight_avg_kg`
- `height_min_cm`, `height_max_cm`
- `lifespan_min_years`, `lifespan_max_years`, `lifespan_avg_years`
- `energy` (if found)
- Sets `*_from` fields to 'wikipedia'

### 5. Rate Limiting
- 2 second delay between requests to be respectful to Wikipedia
- Estimated total time: ~40-50 minutes for all 583 breeds

## Commands

### Test Run (5 breeds)
```bash
python3 wikipedia_breed_rescraper_gcs.py --test
```

### Full Production Run (583 breeds)
```bash
./run_wikipedia_scrape.sh
# or
python3 wikipedia_breed_rescraper_gcs.py
```

## Post-Scrape Verification

After completion, check:

1. **Report file**: `wikipedia_rescrape_report_[timestamp].json`
   - Lists all breeds processed
   - Shows which fields were extracted
   - Records any failures

2. **GCS Storage**:
```bash
gsutil ls gs://lupito-content-raw-eu/scraped/wikipedia_breeds/
gsutil du -sh gs://lupito-content-raw-eu/scraped/wikipedia_breeds/[timestamp]/
```

3. **Database Updates**:
```sql
-- Check how many breeds now have Wikipedia data
SELECT
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE weight_from = 'wikipedia') as weight_from_wiki,
    COUNT(*) FILTER (WHERE height_from = 'wikipedia') as height_from_wiki,
    COUNT(*) FILTER (WHERE lifespan_from = 'wikipedia') as lifespan_from_wiki
FROM breeds_published;
```

4. **Run Quality Audit**:
```bash
python3 breed_comprehensive_audit.py
```

## Expected Results

- **Success rate**: 85-95% (some breeds may not have Wikipedia pages)
- **Weight data improvement**: Should fill most of the 42 missing weights
- **Energy data**: May improve some of the 461 default "moderate" values
- **Quality score**: Should improve from 85/100 to ~95/100

## Troubleshooting

If the scraper fails:
- Check internet connection
- Verify GCS credentials: `echo $GOOGLE_APPLICATION_CREDENTIALS`
- Check Supabase connection in `.env`
- Review logs for specific error messages

## Important Notes

- The scraper is respectful to Wikipedia (2s delays, proper User-Agent)
- All HTML is backed up to GCS for future reference
- Database updates happen in real-time (can be disabled with test_mode)
- The scraper continues even if individual breeds fail