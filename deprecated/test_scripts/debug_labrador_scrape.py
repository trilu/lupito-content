#!/usr/bin/env python3
"""
Debug why Labrador Retriever is not being updated correctly
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'jobs'))

from wikipedia_breed_scraper_fixed import WikipediaBreedScraper
import json

def main():
    print("=" * 80)
    print("DEBUGGING LABRADOR RETRIEVER SCRAPING")
    print("=" * 80)
    
    # Initialize scraper
    scraper = WikipediaBreedScraper()
    
    # Test scraping Labrador
    breed_name = 'Labrador Retriever'
    url = 'https://en.wikipedia.org/wiki/Labrador_Retriever'
    
    print(f"\nScraping: {breed_name}")
    print(f"URL: {url}")
    print()
    
    # Call the scrape method
    breed_data = scraper.scrape_breed(breed_name, url)
    
    if breed_data:
        # Remove raw HTML for display
        breed_data.pop('raw_html', None)
        
        print("EXTRACTED DATA:")
        print("-" * 40)
        for key, value in sorted(breed_data.items()):
            print(f"  {key}: {value}")
        print()
        
        # Check what would be saved
        print("DATA TO BE SAVED TO DATABASE:")
        print("-" * 40)
        print(f"  breed_slug: {breed_data.get('breed_slug')}")
        print(f"  display_name: {breed_data.get('display_name')}")
        print(f"  size: {breed_data.get('size')}")
        print(f"  weight_kg_min: {breed_data.get('weight_kg_min')}")
        print(f"  weight_kg_max: {breed_data.get('weight_kg_max')}")
        print(f"  height_cm_min: {breed_data.get('height_cm_min')}")
        print(f"  height_cm_max: {breed_data.get('height_cm_max')}")
        print(f"  life_expectancy_years_min: {breed_data.get('life_expectancy_years_min')}")
        print(f"  life_expectancy_years_max: {breed_data.get('life_expectancy_years_max')}")
        print()
        
        # Test the save
        print("ATTEMPTING TO SAVE TO DATABASE...")
        print("-" * 40)
        success = scraper.save_to_database(breed_data)
        
        if success:
            print("✅ Save operation returned success")
            
            # Verify in database
            import os
            from dotenv import load_dotenv
            from supabase import create_client
            
            load_dotenv()
            url = os.environ.get("SUPABASE_URL")
            key = os.environ.get("SUPABASE_SERVICE_KEY")
            supabase = create_client(url, key)
            
            # Check the database
            response = supabase.table('breeds_details').select('*').eq('breed_slug', 'labrador-retriever').execute()
            
            if response.data:
                db_breed = response.data[0]
                print("\nVERIFICATION - Current database values:")
                print(f"  Size: {db_breed.get('size')}")
                print(f"  Weight: {db_breed.get('weight_kg_min')}-{db_breed.get('weight_kg_max')} kg")
                print(f"  Height: {db_breed.get('height_cm_min')}-{db_breed.get('height_cm_max')} cm")
                print(f"  Updated at: {db_breed.get('updated_at')}")
                
                # Check if values match
                if (db_breed.get('size') == breed_data.get('size') and
                    db_breed.get('weight_kg_min') == breed_data.get('weight_kg_min') and
                    db_breed.get('weight_kg_max') == breed_data.get('weight_kg_max')):
                    print("\n✅ DATABASE UPDATE SUCCESSFUL!")
                else:
                    print("\n❌ DATABASE VALUES DON'T MATCH SCRAPED DATA!")
                    print("\nExpected:")
                    print(f"  Size: {breed_data.get('size')}")
                    print(f"  Weight: {breed_data.get('weight_kg_min')}-{breed_data.get('weight_kg_max')} kg")
                    print("\nActual in DB:")
                    print(f"  Size: {db_breed.get('size')}")
                    print(f"  Weight: {db_breed.get('weight_kg_min')}-{db_breed.get('weight_kg_max')} kg")
        else:
            print("❌ Save operation failed")
    else:
        print("❌ Failed to scrape breed data")

if __name__ == "__main__":
    main()