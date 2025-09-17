#!/usr/bin/env python3
"""
Validate Scraper Columns Against Database Schema
================================================

This script checks what columns scrapers are trying to use vs. what's available
in the breeds_details table to identify any mismatches causing failures.
"""

import os
import sys
import json
from typing import Dict, Any, Set
from supabase import create_client
from dotenv import load_dotenv

# Add the wikipedia scraper to test
sys.path.append('/Users/sergiubiris/Desktop/lupito-content/jobs')

load_dotenv()

def get_actual_table_columns() -> Set[str]:
    """Get the actual columns from breeds_details table"""

    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')

    if not supabase_url or not supabase_key:
        raise ValueError("Missing Supabase credentials")

    supabase = create_client(supabase_url, supabase_key)

    # Get a sample record to see the structure
    result = supabase.table('breeds_details').select('*').limit(1).execute()

    if result.data and len(result.data) > 0:
        return set(result.data[0].keys())
    else:
        return set()

def test_scraper_output() -> Dict[str, Any]:
    """Test what columns the scraper produces"""

    try:
        from wikipedia_breed_scraper_fixed import WikipediaBreedScraper

        scraper = WikipediaBreedScraper()

        # Test with a simple breed
        test_breed_data = scraper.scrape_breed(
            "Golden Retriever",
            "https://en.wikipedia.org/wiki/Golden_Retriever"
        )

        if test_breed_data:
            # Remove raw_html if present (as the scraper does)
            test_breed_data.pop('raw_html', None)
            return test_breed_data
        else:
            return {}

    except Exception as e:
        print(f"Error testing scraper: {e}")
        return {}

def main():
    """Main validation function"""

    print("Validating scraper columns against database schema...")
    print("=" * 60)

    # Get actual database columns
    try:
        db_columns = get_actual_table_columns()
        print(f"✅ Database has {len(db_columns)} columns in breeds_details:")
        for col in sorted(db_columns):
            print(f"   • {col}")
        print()
    except Exception as e:
        print(f"❌ Error getting database columns: {e}")
        return

    # Test scraper output
    print("Testing scraper output...")
    scraper_data = test_scraper_output()

    if scraper_data:
        scraper_columns = set(scraper_data.keys())
        print(f"✅ Scraper produces {len(scraper_columns)} columns:")
        for col in sorted(scraper_columns):
            print(f"   • {col}")
        print()

        # Find mismatches
        missing_in_db = scraper_columns - db_columns
        extra_in_db = db_columns - scraper_columns

        if missing_in_db:
            print("❌ COLUMNS MISSING IN DATABASE (will cause insert/update failures):")
            for col in sorted(missing_in_db):
                print(f"   • {col}")
            print()

        if extra_in_db:
            print("ℹ️  COLUMNS IN DATABASE NOT SET BY SCRAPER:")
            for col in sorted(extra_in_db):
                print(f"   • {col}")
            print()

        if not missing_in_db:
            print("✅ All scraper columns exist in database - no column mismatch issues!")

        # Show sample data
        print("\nSample scraper output:")
        print("-" * 40)
        for key, value in scraper_data.items():
            if isinstance(value, str) and len(str(value)) > 100:
                value = str(value)[:100] + "..."
            print(f"{key}: {value}")

    else:
        print("❌ Could not get scraper output for testing")

if __name__ == "__main__":
    main()