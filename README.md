# Lupito Content Ingestion

One-off content ingestion for Lupito (petfoodexpert, CSV imports). Stores raw snapshots + parsed rows for recommendations.

## Quick Start

### 1. Setup Environment

```bash
# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
# Edit .env with your Supabase credentials

# Authenticate with Google Cloud
gcloud auth application-default login
```

### 2. Setup Database

Paste the contents of `db/schema.sql` into the Supabase SQL editor and run to create tables and views.

### 3. Run Scraper

```bash
# Scrape a single URL
python jobs/pfx_scrape.py --url https://petfoodexpert.com/product/example

# Scrape from a list of URLs (one per line)
python jobs/pfx_scrape.py --seed-list urls.txt

# Scrape from sitemap
python jobs/pfx_scrape.py --from-sitemap

# Use custom config file
python jobs/pfx_scrape.py --config config.yaml --from-sitemap
```

## Project Structure

```
lupito-content/
├── jobs/
│   └── pfx_scrape.py        # Main scraper entrypoint
├── profiles/
│   └── pfx_profile.yaml     # PetFoodExpert scraping profile
├── etl/
│   └── normalize_foods.py   # Data normalization helpers
├── db/
│   └── schema.sql           # Database schema
├── .env.example             # Environment variables template
├── config.example.yaml      # Configuration template
└── requirements.txt         # Python dependencies
```

## Configuration

### Required Environment Variables

- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_SERVICE_KEY`: Service role key for Supabase
- `GCS_BUCKET`: Google Cloud Storage bucket name (default: lupito-content-raw-eu)

### Scraping Settings

Default settings in `config.example.yaml`:
- Rate limit: 0.5 requests/second
- Random jitter: 0.5-2.0 seconds
- Timeout: 30 seconds
- Max retries: 3

## Database Schema

### Tables

- **food_raw**: Stores raw HTML snapshots and parsed JSON
- **food_candidates**: Normalized product data
- **foods_published**: Clean view for AI service consumption

### Key Fields

- Product identity: brand, name, form, life_stage
- Nutrition: kcal_per_100g, protein%, fat%, fiber%, ash%, moisture%
- Ingredients: raw text, tokens array, contains_chicken flag
- Pricing: price_eur, price_bucket (low/mid/high)
- Metadata: GTIN, pack sizes, availability

## Adding New Sources

1. Create a new profile in `profiles/` directory
2. Define CSS/XPath selectors for the target site
3. Create a new job in `jobs/` directory
4. Follow the same pattern as `pfx_scrape.py`

## Safety & Compliance

- Respects rate limits (0.5 req/sec default)
- Random jitter between requests
- Standard User-Agent identification
- Stores raw HTML for audit trail
- Deduplicates using content fingerprints

## Monitoring

The scraper logs:
- Progress updates (X/Y URLs processed)
- Success/failure for each URL
- Parsing errors and warnings
- Final summary report

## QA Checklist

After scraping:
1. Check `food_candidates` table for new rows
2. Verify `foods_published` view shows products
3. Sample check parsed data accuracy
4. Confirm GCS has raw HTML backups