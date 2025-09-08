#!/usr/bin/env python3
"""Test the enhanced universal breed scraper with Golden Retriever"""

import sys
import os
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from jobs.universal_breed_scraper_enhanced import EnhancedUniversalBreedScraper

def test_golden_retriever():
    """Test scraping Golden Retriever from AKC"""
    
    print("=" * 80)
    print("Testing Enhanced Universal Breed Scraper with Golden Retriever")
    print("=" * 80)
    
    # Initialize scraper
    scraper = EnhancedUniversalBreedScraper()
    
    # Test URL
    url = "https://www.akc.org/dog-breeds/golden-retriever/"
    
    print(f"\n📍 Testing URL: {url}")
    print("-" * 40)
    
    # Scrape the breed
    result = scraper.scrape_breed(url)
    
    if result:
        print("\n✅ Scraping successful!")
        print("\n📊 Extracted Data:")
        print("-" * 40)
        
        # Display key information
        print(f"\n🐕 Breed: {result.get('display_name', 'Unknown')}")
        print(f"🔗 URL: {result.get('akc_url', 'N/A')}")
        print(f"⚙️ Scraping Method: {result.get('scraping_method', 'N/A')}")
        print(f"💰 ScrapingBee Cost: {result.get('scrapingbee_cost', 0)} credits")
        print(f"📈 Extraction Status: {result.get('extraction_status', 'N/A')}")
        
        # Display physical traits
        if result.get('has_physical_data'):
            print("\n📏 Physical Traits:")
            if result.get('height_cm_min'):
                print(f"  • Height: {result.get('height_cm_min')}-{result.get('height_cm_max')} cm")
            if result.get('weight_kg_min'):
                print(f"  • Weight: {result.get('weight_kg_min')}-{result.get('weight_kg_max')} kg")
            if result.get('lifespan_years_min'):
                print(f"  • Lifespan: {result.get('lifespan_years_min')}-{result.get('lifespan_years_max')} years")
            if result.get('size'):
                print(f"  • Size Category: {result.get('size')}")
        
        # Display temperament traits
        print("\n🧠 Temperament Traits:")
        for trait in ['energy', 'shedding', 'trainability', 'barking', 'friendliness_family', 
                      'friendliness_strangers', 'friendliness_dogs', 'grooming']:
            if result.get(trait):
                print(f"  • {trait.replace('_', ' ').title()}: {result.get(trait)}")
        
        # Display content sections
        if result.get('has_profile_data'):
            print("\n📖 Content Sections Found:")
            for section in ['about', 'personality', 'health', 'care', 'feeding', 
                           'grooming', 'exercise', 'training', 'history']:
                if result.get(section):
                    content = result.get(section, '')
                    if content:
                        preview = content[:100] + "..." if len(content) > 100 else content
                        print(f"  • {section.title()}: {preview}")
        
        # Save full result to file
        output_file = "golden_retriever_test_result.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\n💾 Full result saved to: {output_file}")
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 EXTRACTION SUMMARY:")
        print(f"  • Physical Data: {'✓' if result.get('has_physical_data') else '✗'}")
        print(f"  • Profile Content: {'✓' if result.get('has_profile_data') else '✗'}")
        print(f"  • Raw Traits Extracted: {len(result.get('traits', {}))}")
        print(f"  • Total Content Length: {sum(len(str(v)) for v in result.values() if v)} characters")
        print("=" * 80)
        
    else:
        print("\n❌ Scraping failed - no result returned")
        return False
    
    return True

if __name__ == "__main__":
    success = test_golden_retriever()
    sys.exit(0 if success else 1)