Create a tiny “content-lite” structure for one-off scrapes:

GOALS
- No heavy framework. One CLI command per job.
- Store raw HTML in GCS, parsed rows in Supabase.
- Keep it safe (rate limits) and resumable.

STRUCTURE
- /jobs/pfx_scrape.py        # entrypoint: crawl urls -> raw snapshots -> parse -> upsert
- /profiles/pfx_profile.yaml # CSS/XPath/JSON-LD selectors for petfoodexpert
- /etl/normalize_foods.py    # helpers: unit parsing, kcal conversions, tokenization
- /db/schema.sql             # creates food_raw, food_candidates tables and foods_published view
- /config.example.yaml       # GCP bucket, Supabase URL, concurrency, delay, etc.
- /README.md                 # how to run, how to add new sources

DB (schema.sql)
- Table food_raw:
  id uuid pk default gen_random_uuid()
  source_domain text
  source_url text unique
  html_gcs_path text
  parsed_json jsonb
  first_seen_at timestamptz default now()
  last_seen_at timestamptz default now()
  fingerprint text  -- hash of (brand+name+ingredients) to detect updates

- Table food_candidates:
  id uuid pk default gen_random_uuid()
  source_domain text
  source_url text
  brand text
  product_name text
  form text
  life_stage text
  kcal_per_100g numeric null
  protein_percent numeric null
  fat_percent numeric null
  fiber_percent numeric null
  ash_percent numeric null
  moisture_percent numeric null
  ingredients_raw text
  ingredients_tokens text[] default '{}'
  contains_chicken boolean default false
  pack_sizes text[] default '{}'
  price_eur numeric null
  price_currency text
  available_countries text[] default '{EU}'
  gtin text null
  first_seen_at timestamptz default now()
  last_seen_at timestamptz default now()
  fingerprint text

- View foods_published (CREATE OR REPLACE):
  Select the above fields but:
    - coalesce available_countries to '{EU}'
    - derive price_bucket: low/mid/high from price_eur (simple thresholds for now)
    - trim/lower tokens; ensure contains_chicken set via tokens

ASK ME for:
- Supabase URL/service key
- GCS bucket name (e.g., lupito-content-raw)
- petfoodexpert base URL (confirm domain spelling)
- Desired crawl rate (default 0.5 req/sec)

Do NOT print secrets. Create .env.example and ask at runtime if missing.
Output:
- schema.sql ready to paste into Supabase SQL editor
- a minimal README with run commands:
  - “Run DB schema (paste into Supabase)”
  - “python jobs/pfx_scrape.py --seed-list <file_of_urls.txt>”
  - “python jobs/pfx_scrape.py --from-sitemap”