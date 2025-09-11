# Storage Migration: Local to GCS

## Overview

As of 2025-09-11, we've migrated snapshot storage from local filesystem to Google Cloud Storage (GCS). This document explains the migration and how to work with both storage types.

## Migration Timeline

- **Before 2025-09-11**: Snapshots stored locally in `./snapshots/` or `./cache/`
- **After 2025-09-11**: Snapshots stored in GCS at `gs://lupito-content-raw-eu/`

## Mixed History

The system now handles both storage types:

1. **Legacy Local Paths**: Files stored as `/path/to/local/file.html`
2. **New GCS URIs**: Files stored as `gs://lupito-content-raw-eu/manufacturers/brand/date/file.html`

## Storage Structure

### GCS Structure
```
gs://lupito-content-raw-eu/
└── manufacturers/
    └── <brand_slug>/
        └── <YYYY-MM-DD>/
            ├── *.html  (product pages)
            ├── *.pdf   (datasheets, specs)
            └── *.json  (metadata)
```

### Local Structure (Legacy)
```
./snapshots/
└── brands/
    └── <brand_slug>/
        └── cache/
            ├── *.html
            └── *.meta.json
```

## Reading from GCS

### Using gsutil (Command Line)
```bash
# List files
gsutil ls gs://lupito-content-raw-eu/manufacturers/brit/2025-09-11/

# Download a file
gsutil cp gs://lupito-content-raw-eu/manufacturers/brit/2025-09-11/product.html ./local.html

# Cat a file directly
gsutil cat gs://lupito-content-raw-eu/manufacturers/brit/2025-09-11/product.html
```

### Using Python
```python
from google.cloud import storage
import os

# Set credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = './secrets/gcp-sa.json'

# Initialize client
client = storage.Client()
bucket = client.bucket('lupito-content-raw-eu')

# Download a blob
blob = bucket.blob('manufacturers/brit/2025-09-11/product.html')
content = blob.download_as_text()

# List blobs
for blob in bucket.list_blobs(prefix='manufacturers/brit/'):
    print(f"gs://{bucket.name}/{blob.name}")
```

## Configuration

### Environment Variables
```bash
# Required for GCS
GCS_BUCKET=lupito-content-raw-eu
GCS_PREFIX=manufacturers
GOOGLE_APPLICATION_CREDENTIALS=./secrets/gcp-sa.json

# Optional: Force local storage
USE_LOCAL_SNAPSHOTS=true  # Set to use local storage instead of GCS
```

### Service Account
- **Account**: `content-snapshots@careful-drummer-468512-p0.iam.gserviceaccount.com`
- **Permissions**: `roles/storage.objectAdmin` on bucket
- **Key Location**: `./secrets/gcp-sa.json` (git-ignored)

## Database Storage

### Storage Path Field
The `storage_path` field in database tables now contains:
- **Legacy**: Local filesystem paths (e.g., `/snapshots/brands/brit/cache/file.html`)
- **Current**: GCS URIs (e.g., `gs://lupito-content-raw-eu/manufacturers/brit/2025-09-11/file.html`)

### Handling Mixed Storage
```python
def read_snapshot(storage_path):
    """Read snapshot from either local or GCS storage"""
    if storage_path.startswith('gs://'):
        # Read from GCS
        from google.cloud import storage
        client = storage.Client()
        
        # Parse GCS URI
        parts = storage_path.replace('gs://', '').split('/', 1)
        bucket_name = parts[0]
        blob_path = parts[1]
        
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        return blob.download_as_text()
    else:
        # Read from local filesystem
        with open(storage_path, 'r') as f:
            return f.read()
```

## Verification

### Check GCS Setup
```bash
# Run the doctor script
./scripts/gcs_doctor.sh

# Should output:
# RESULT: PASS
# Service Account: content-snapshots@...
# Bucket: gs://lupito-content-raw-eu
```

### Test Upload
```bash
# Test with a single brand
python3 test_snapshot_harvest.py

# Check results
gsutil ls gs://lupito-content-raw-eu/manufacturers/
```

## Troubleshooting

### Authentication Issues
```bash
# Ensure credentials file exists
ls -la ./secrets/gcp-sa.json

# Test authentication
gcloud auth application-default print-access-token

# Re-download from Secret Manager if needed
gcloud secrets versions access latest \
  --secret=GCS_SA_KEY_CONTENT \
  --project=careful-drummer-468512-p0 > secrets/gcp-sa.json
```

### Permission Denied
```bash
# Check service account permissions
gsutil iam get gs://lupito-content-raw-eu | grep content-snapshots

# Should show:
# serviceAccount:content-snapshots@...:objectAdmin
# serviceAccount:content-snapshots@...:legacyBucketReader
```

### Fallback to Local
Set `USE_LOCAL_SNAPSHOTS=true` in `.env` to force local storage if GCS is unavailable.

## Migration Status

- ✅ Service account created
- ✅ Bucket permissions configured
- ✅ Credentials stored in Secret Manager
- ✅ Local credentials materialized
- ✅ Harvester updated for GCS
- ✅ Doctor script created
- ✅ Test uploads successful

## Next Steps

1. Complete Wave 1 snapshot harvest to GCS
2. Update parsing pipeline to read from GCS URIs
3. Migrate historical snapshots to GCS (optional)
4. Remove local snapshot storage code (after full migration)