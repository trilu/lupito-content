#!/bin/bash

# Wikipedia Breed Scraping Script
# Scrapes all 583 breeds and stores HTML in GCS

echo "=================================================="
echo "WIKIPEDIA BREED SCRAPING - PRODUCTION RUN"
echo "=================================================="
echo ""
echo "This will scrape all 583 breeds from Wikipedia"
echo "Estimated time: ~40-50 minutes (with rate limiting)"
echo "Storage: gs://lupito-content-raw-eu/scraped/wikipedia_breeds/"
echo ""
echo "Press Ctrl+C to cancel, or Enter to continue..."
read

# Run the scraper
echo "Starting scrape at $(date)"
/Library/Developer/CommandLineTools/usr/bin/python3 wikipedia_breed_rescraper_gcs.py

# Check if successful
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Scraping completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Check the report: wikipedia_rescrape_report_*.json"
    echo "2. Verify GCS storage: gsutil ls gs://lupito-content-raw-eu/scraped/wikipedia_breeds/"
    echo "3. Apply enrichments to database (if needed)"
else
    echo "❌ Scraping failed. Check the logs above."
fi