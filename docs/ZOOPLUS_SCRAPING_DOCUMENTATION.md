# Zooplus Product Scraping System Documentation

## Overview

This documentation covers the complete Zooplus product scraping system, which extracts ingredients and nutritional data from Zooplus product pages and stores them in our database via Google Cloud Storage.

## Table of Contents

1. [Architecture](#architecture)
2. [Prerequisites](#prerequisites)
3. [Components](#components)
4. [Setup Instructions](#setup-instructions)
5. [Usage Guide](#usage-guide)
6. [Data Flow](#data-flow)
7. [Extracted Data Fields](#extracted-data-fields)
8. [Performance Metrics](#performance-metrics)
9. [Troubleshooting](#troubleshooting)
10. [Best Practices](#best-practices)

## Architecture

The system uses a two-stage approach:

```
[Zooplus Website] 
    ↓ (ScrapingBee API)
[Scraper Script]
    ↓ (JSON files)
[Google Cloud Storage]
    ↓ (Batch processing)
[Database Processor]
    ↓ (Supabase API)
[PostgreSQL Database]
```

### Why Two-Stage?

1. **Decoupling**: Separates scraping from database operations
2. **Reliability**: Can retry failed DB updates without re-scraping
3. **Auditing**: Maintains raw scraped data for verification
4. **Scalability**: Can process GCS files in parallel
5. **Resume Capability**: Know exactly what's been scraped

## Prerequisites

### Required Services

1. **ScrapingBee Account**
   - API key with premium proxy access
   - Sufficient credits for JavaScript rendering

2. **Google Cloud Platform**
   - Storage bucket configured
   - Service account with write permissions

3. **Supabase Database**
   - PostgreSQL database with `foods_canonical` table
   - Service key for authentication

### Python Dependencies

```bash
pip install requests beautifulsoup4 google-cloud-storage supabase python-dotenv
```

### Environment Variables

Create a `.env` file with:

```bash
# ScrapingBee
SCRAPING_BEE=your_scrapingbee_api_key

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_key

# Google Cloud Storage
GCS_BUCKET=your-bucket-name
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
```

## Components

### 1. Scraper (`scrape_zooplus_to_gcs.py`)

**Purpose**: Scrapes Zooplus product pages and saves raw data to GCS

**Key Features**:
- JavaScript rendering for dynamic content
- Automatic tab/accordion clicking to reveal ingredients
- Rate limiting (15-20 seconds between requests)
- Premium proxy rotation
- Comprehensive error handling

**Output**: JSON files in GCS with structure:
```json
{
  "url": "https://www.zooplus.com/...",
  "product_key": "brand|product-name|form",
  "product_name": "Product Name",
  "brand": "Brand Name",
  "ingredients_raw": "Full ingredients text...",
  "nutrition": {
    "protein_percent": 25.0,
    "fat_percent": 14.0,
    "fiber_percent": 2.5,
    "ash_percent": 6.0,
    "moisture_percent": 10.0
  },
  "scraped_at": "2024-12-12T14:30:00Z",
  "html_sample": "First 50KB of HTML for debugging"
}
```

### 2. Database Processor (`process_gcs_scraped_data.py`)

**Purpose**: Processes GCS files and updates the database

**Key Features**:
- Batch processing of scraped files
- Ingredient tokenization for search
- Data validation and cleaning
- Comprehensive error logging
- Idempotent operations

**Database Updates**:
- `ingredients_raw`: Full ingredient text
- `ingredients_tokens`: Tokenized ingredients for search
- `protein_percent`, `fat_percent`, `fiber_percent`, `ash_percent`, `moisture_percent`
- `ingredients_source`, `macros_source`: Set to 'site'

## Setup Instructions

### 1. Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

### 2. Configure Google Cloud

```bash
# Install gcloud CLI
curl https://sdk.cloud.google.com | bash

# Authenticate
gcloud auth login
gcloud config set project your-project-id

# Create service account
gcloud iam service-accounts create zooplus-scraper
gcloud projects add-iam-policy-binding your-project-id \
  --member="serviceAccount:zooplus-scraper@your-project-id.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"

# Download key
gcloud iam service-accounts keys create credentials.json \
  --iam-account=zooplus-scraper@your-project-id.iam.gserviceaccount.com
```

### 3. Create GCS Bucket

```bash
gsutil mb -l eu gs://your-bucket-name
```

## Usage Guide

### Running the Scraper

#### Small Test Batch (10 products)
```bash
python scripts/scrape_zooplus_to_gcs.py
```

#### Custom Batch Size
```python
# Edit scrape_zooplus_to_gcs.py
scraper.run_batch(batch_size=50)  # Scrape 50 products
```

#### Monitor Progress
The scraper outputs real-time progress:
```
[1/10] Royal Canin Medium Adult...
  ✓ Ingredients: Dried poultry protein, wheat, maize meal...
  ✓ Nutrition: Protein=25.0%, Fat=14.0%
  ✓ Saved to GCS
```

### Processing Scraped Data

#### Process Latest Batch
```bash
# List recent scraping sessions
gsutil ls gs://your-bucket/scraped/zooplus/

# Process specific session
python scripts/process_gcs_scraped_data.py scraped/zooplus/20241212_143000
```

#### Process All Pending
```python
# Create a script to process all unprocessed batches
import subprocess
from google.cloud import storage

client = storage.Client()
bucket = client.bucket('your-bucket')

for blob in bucket.list_blobs(prefix='scraped/zooplus/'):
    folder = '/'.join(blob.name.split('/')[:-1])
    subprocess.run(['python', 'process_gcs_scraped_data.py', folder])
```

## Data Flow

### 1. Product Selection
```sql
-- Query products without ingredients
SELECT product_key, product_url 
FROM foods_canonical 
WHERE product_url LIKE '%zooplus%' 
  AND ingredients_raw IS NULL
LIMIT 50;
```

### 2. Scraping Process
```python
# For each product:
1. Clean URL (remove activeVariant parameter)
2. Configure ScrapingBee with JavaScript rendering
3. Execute JavaScript to click tabs/reveal content
4. Wait for content to load (3-7 seconds)
5. Extract ingredients and nutrition
6. Save to GCS as JSON
```

### 3. Data Extraction Patterns

#### Ingredients
```python
# Pattern 1: Standard format
r'Composition[:\s]*\n?([^\n]{20,}?)(?:\nAnalytical|$)'

# Pattern 2: With "Ingredients" label
r'Ingredients[:\s]*\n?([^\n]{20,}?)(?:\nAnalytical|$)'

# Validation: Must contain food words
['meat', 'chicken', 'beef', 'fish', 'rice', 'wheat', 'protein']
```

#### Nutrition
```python
# Protein
r'(?:Crude\s+)?Protein[:\s]+(\d+(?:\.\d+)?)\s*%'

# Fat
r'(?:Crude\s+)?(?:Fat|Oils)[:\s]+(\d+(?:\.\d+)?)\s*%'

# Fiber
r'(?:Crude\s+)?Fib(?:re|er)[:\s]+(\d+(?:\.\d+)?)\s*%'

# Ash
r'(?:Crude\s+)?Ash[:\s]+(\d+(?:\.\d+)?)\s*%'

# Moisture
r'Moisture[:\s]+(\d+(?:\.\d+)?)\s*%'
```

### 4. Tokenization Process
```python
def tokenize_ingredients(text):
    # Remove percentages: "chicken (20%)" → "chicken"
    # Remove parentheses: "meat (dried)" → "meat"
    # Split by comma/semicolon
    # Clean and lowercase
    # Filter: 2 < length < 50 characters
    # Skip common non-ingredients
```

## Extracted Data Fields

### Ingredients Data
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `ingredients_raw` | TEXT | Full ingredients text | "Chicken (20%), rice, wheat..." |
| `ingredients_tokens` | TEXT[] | Tokenized ingredients | ["chicken", "rice", "wheat"] |
| `ingredients_source` | VARCHAR | Data source | "site" |

### Nutritional Data
| Field | Type | Description | Range |
|-------|------|-------------|-------|
| `protein_percent` | DECIMAL | Crude protein content | 15-40% |
| `fat_percent` | DECIMAL | Crude fat content | 5-25% |
| `fiber_percent` | DECIMAL | Crude fiber content | 1-10% |
| `ash_percent` | DECIMAL | Crude ash content | 3-12% |
| `moisture_percent` | DECIMAL | Moisture content | 5-85% |
| `macros_source` | VARCHAR | Data source | "site" |

## Performance Metrics

### Success Rates (Based on Testing)

| Metric | Rate | Notes |
|--------|------|-------|
| **Scraping Success** | 95-100% | With premium proxies |
| **Ingredients Extraction** | 85-90% | Depends on page structure |
| **Nutrition Extraction** | 85-90% | Usually available |
| **Database Update** | 90-95% | Validation may reject some |

### Timing

| Operation | Duration | Notes |
|-----------|----------|-------|
| **Per Product Scrape** | 10-15 seconds | Including JS rendering |
| **Rate Limit Delay** | 15-20 seconds | To avoid bans |
| **Batch of 50** | ~20 minutes | With delays |
| **GCS Processing** | <1 second/file | Database updates |

### Resource Usage

- **ScrapingBee Credits**: ~1 credit per product (with JS rendering)
- **GCS Storage**: ~50KB per product (JSON + HTML sample)
- **Network Bandwidth**: ~1MB per product (full HTML download)

## Troubleshooting

### Common Issues

#### 1. No Ingredients Found
**Symptoms**: Products scraped but no ingredients extracted

**Causes**:
- Product is a variant listing page
- Ingredients in unexpected format
- JavaScript didn't fully load

**Solutions**:
```python
# Increase wait time
'wait': '10000'  # 10 seconds

# Add more selector patterns
patterns.append(r'Recipe[:\s]*([^\n]{20,})')

# Check HTML sample in GCS file
```

#### 2. Rate Limiting/Bans
**Symptoms**: 403/429 errors, empty responses

**Solutions**:
```python
# Increase delay between requests
delay = random.uniform(20, 30)  # 20-30 seconds

# Use different proxy location
'country_code': 'de'  # Try Germany for EU site

# Reduce batch size
batch_size = 10  # Smaller batches
```

#### 3. Database Update Failures
**Symptoms**: Scraped successfully but DB not updated

**Causes**:
- Invalid data format
- Database constraints
- Network issues

**Solutions**:
```python
# Check error logs
print(f"Database error: {e}")

# Validate data before update
if len(ingredients) > 2000:
    ingredients = ingredients[:2000]

# Retry with exponential backoff
```

### Debugging Tools

#### Check Scraped HTML
```python
# Load and inspect HTML sample from GCS
import json
from google.cloud import storage

client = storage.Client()
bucket = client.bucket('your-bucket')
blob = bucket.blob('scraped/zooplus/20241212/product.json')
data = json.loads(blob.download_as_text())

# Write HTML to file for browser inspection
with open('debug.html', 'w') as f:
    f.write(data['html_sample'])
```

#### Manual URL Testing
```python
# Test single URL with verbose output
scraper = ZooplusGCSScraper()
result = scraper.scrape_product('https://www.zooplus.com/...')
print(json.dumps(result, indent=2))
```

## Best Practices

### 1. Rate Limiting
- **Always use delays**: 15-20 seconds minimum
- **Randomize delays**: Avoid patterns
- **Monitor for blocks**: Stop if errors increase
- **Use premium proxies**: Better success rates

### 2. Data Quality
- **Validate extractions**: Check for food words
- **Preserve original data**: Store raw text
- **Handle variations**: Multiple pattern matching
- **Clean tokenization**: Remove noise, normalize

### 3. Error Handling
- **Graceful failures**: Continue batch on errors
- **Comprehensive logging**: Track all issues
- **Retry logic**: For transient failures
- **Save everything**: Even failed attempts

### 4. Scalability
- **Batch appropriately**: 20-50 products per run
- **Use GCS folders**: Organize by date/time
- **Process asynchronously**: Separate scraping from processing
- **Monitor costs**: Track API usage

### 5. Maintenance
- **Regular testing**: Verify extraction patterns
- **Update patterns**: As site changes
- **Clean old data**: Remove processed GCS files
- **Document changes**: Track pattern updates

## Cost Optimization

### ScrapingBee Credits
- **Use JS rendering only when needed**
- **Cache successful scrapes in GCS**
- **Batch similar products**
- **Monitor credit usage**

### GCS Storage
- **Compress old data**
- **Delete processed files after 30 days**
- **Use lifecycle policies**
```bash
gsutil lifecycle set lifecycle.json gs://your-bucket
```

### Database Operations
- **Batch updates when possible**
- **Use connection pooling**
- **Index frequently queried fields**

## Future Enhancements

### Planned Improvements

1. **Parallel Processing**
   - Use ThreadPoolExecutor for concurrent scraping
   - Process GCS files in parallel

2. **Advanced Extraction**
   - Machine learning for ingredient parsing
   - OCR for image-based ingredients

3. **Monitoring Dashboard**
   - Real-time scraping statistics
   - Success rate tracking
   - Error analysis

4. **Automatic Retries**
   - Failed product queue
   - Exponential backoff
   - Different proxy strategies

5. **Data Enrichment**
   - Cross-reference with other sources
   - Validate nutritional data
   - Detect anomalies

## Appendix

### Sample Commands

```bash
# Check scraping history
gsutil ls -l gs://your-bucket/scraped/zooplus/ | tail -10

# Count scraped products
gsutil ls gs://your-bucket/scraped/zooplus/20241212_*/*.json | wc -l

# Download all files from a session
gsutil -m cp -r gs://your-bucket/scraped/zooplus/20241212_143000 ./local_backup/

# Process multiple sessions
for dir in $(gsutil ls gs://your-bucket/scraped/zooplus/); do
  python process_gcs_scraped_data.py ${dir#gs://your-bucket/}
done

# Check database coverage
psql -c "SELECT 
  COUNT(*) as total,
  COUNT(ingredients_raw) as with_ingredients,
  COUNT(protein_percent) as with_protein
FROM foods_canonical 
WHERE product_url LIKE '%zooplus%'"
```

### Monitoring Queries

```sql
-- Products still needing ingredients
SELECT COUNT(*) 
FROM foods_canonical 
WHERE product_url LIKE '%zooplus%' 
  AND ingredients_raw IS NULL;

-- Recent updates
SELECT product_key, updated_at 
FROM foods_canonical 
WHERE ingredients_source = 'site' 
  AND updated_at > NOW() - INTERVAL '1 day'
ORDER BY updated_at DESC;

-- Nutrition coverage
SELECT 
  COUNT(*) as total,
  COUNT(protein_percent) as has_protein,
  COUNT(CASE WHEN protein_percent IS NOT NULL 
    AND fat_percent IS NOT NULL 
    AND fiber_percent IS NOT NULL THEN 1 END) as complete_nutrition
FROM foods_canonical 
WHERE product_url LIKE '%zooplus%';
```

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review GCS logs for scraping errors
3. Inspect database constraints
4. Contact the development team

---

*Last Updated: December 2024*
*Version: 1.0*