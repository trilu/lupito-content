#!/bin/bash

# GCS Doctor - Health check for Google Cloud Storage setup
# Exit codes: 0 = PASS, 1 = FAIL

set -e

echo "========================================="
echo "GCS Doctor - Health Check"
echo "========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track failures
FAILURES=0

# Function to check and report status
check_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
        FAILURES=$((FAILURES + 1))
    fi
}

# 1. Check environment variables
echo "1. Checking environment variables..."
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

if [ -z "$GCS_BUCKET" ]; then
    check_status 1 "GCS_BUCKET not set"
else
    check_status 0 "GCS_BUCKET: $GCS_BUCKET"
fi

if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    check_status 1 "GOOGLE_APPLICATION_CREDENTIALS not set"
else
    if [ -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
        check_status 0 "Credentials file exists: $GOOGLE_APPLICATION_CREDENTIALS"
    else
        check_status 1 "Credentials file not found: $GOOGLE_APPLICATION_CREDENTIALS"
    fi
fi

echo ""

# 2. Check GCloud configuration
echo "2. Checking GCloud configuration..."
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    check_status 1 "No GCloud project configured"
else
    check_status 0 "Project: $PROJECT_ID"
fi

echo ""

# 3. Check bucket access
echo "3. Checking bucket access..."
if gsutil ls -b gs://$GCS_BUCKET >/dev/null 2>&1; then
    check_status 0 "Bucket exists and is accessible"
else
    check_status 1 "Cannot access bucket gs://$GCS_BUCKET"
fi

echo ""

# 4. Test upload/download/delete operations
echo "4. Testing GCS operations..."
TEST_FILE="/tmp/gcs_doctor_test_$(date +%s).txt"
TEST_CONTENT="GCS Doctor test file - $(date)"
GCS_TEST_PATH="manufacturers/_healthcheck/test_$(date +%s).txt"

# Create test file
echo "$TEST_CONTENT" > $TEST_FILE

# Upload test
echo "   Uploading test file..."
if gsutil cp $TEST_FILE gs://$GCS_BUCKET/$GCS_TEST_PATH >/dev/null 2>&1; then
    check_status 0 "Upload successful"
else
    check_status 1 "Upload failed"
fi

# Stat test
echo "   Checking file metadata..."
if gsutil stat gs://$GCS_BUCKET/$GCS_TEST_PATH >/dev/null 2>&1; then
    check_status 0 "Stat successful"
else
    check_status 1 "Stat failed"
fi

# Download test
echo "   Downloading test file..."
DOWNLOAD_FILE="/tmp/gcs_doctor_download_$(date +%s).txt"
if gsutil cp gs://$GCS_BUCKET/$GCS_TEST_PATH $DOWNLOAD_FILE >/dev/null 2>&1; then
    # Verify content
    if [ "$(cat $DOWNLOAD_FILE)" = "$TEST_CONTENT" ]; then
        check_status 0 "Download successful and content matches"
    else
        check_status 1 "Download successful but content mismatch"
    fi
    rm -f $DOWNLOAD_FILE
else
    check_status 1 "Download failed"
fi

# Delete test
echo "   Deleting test file..."
if gsutil rm gs://$GCS_BUCKET/$GCS_TEST_PATH >/dev/null 2>&1; then
    check_status 0 "Delete successful"
else
    check_status 1 "Delete failed"
fi

# Cleanup
rm -f $TEST_FILE

echo ""

# 5. Check Python GCS client
echo "5. Testing Python GCS client..."
python3 -c "
import os
import sys
from google.cloud import storage

try:
    # Set credentials
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '$GOOGLE_APPLICATION_CREDENTIALS'
    
    # Initialize client
    client = storage.Client()
    bucket = client.bucket('$GCS_BUCKET')
    
    # List some blobs
    blobs = list(bucket.list_blobs(prefix='manufacturers/', max_results=1))
    print('Python client: OK')
    sys.exit(0)
except Exception as e:
    print(f'Python client: FAILED - {e}')
    sys.exit(1)
" 2>/dev/null

PYTHON_STATUS=$?
if [ $PYTHON_STATUS -eq 0 ]; then
    check_status 0 "Python GCS client working"
else
    check_status 1 "Python GCS client failed"
fi

echo ""
echo "========================================="

# Final summary
if [ $FAILURES -eq 0 ]; then
    echo -e "${GREEN}RESULT: PASS${NC}"
    echo "All checks passed successfully!"
    echo ""
    echo "Service Account: content-snapshots@careful-drummer-468512-p0.iam.gserviceaccount.com"
    echo "Bucket: gs://$GCS_BUCKET"
    echo "Ready for snapshot operations!"
    exit 0
else
    echo -e "${RED}RESULT: FAIL${NC}"
    echo "$FAILURES check(s) failed"
    echo "Please fix the issues above before proceeding"
    exit 1
fi