#!/usr/bin/env python3
"""
Weekly maintenance job for breeds database.
Spot-checks 5 random breeds and re-scrapes if needed.
"""

import os
import sys
import random
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client
import pandas as pd

# Add jobs directory for scraper access
sys.path.insert(0, str(Path(__file__).parent / 'jobs'))

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)

def get_random_breeds(count=5):
    """Get random breeds for spot-checking"""
    response = supabase.table('breeds_details').select('*').execute()
    all_breeds = response.data
    return random.sample(all_breeds, min(count, len(all_breeds)))

def needs_rescrape(breed):
    """Check if breed needs re-scraping"""
    reasons = []
    
    # Check if data is stale (>180 days)
    if breed.get('updated_at'):
        updated = datetime.fromisoformat(breed['updated_at'].replace('Z', '+00:00'))
        age_days = (datetime.now(updated.tzinfo) - updated).days
        if age_days > 180:
            reasons.append(f"Stale data ({age_days} days old)")
    
    # Check for conflict flags
    if breed.get('conflict_flags'):
        reasons.append(f"Has conflicts: {breed['conflict_flags']}")
    
    # Check for missing critical data
    if not breed.get('adult_weight_avg_kg'):
        reasons.append("Missing weight data")
    
    if not breed.get('size_category'):
        reasons.append("Missing size category")
    
    # Check for default data that could be improved
    if breed.get('weight_from') == 'default':
        reasons.append("Using default weight data")
    
    return reasons

def rescrape_breed(breed_slug, breed_name):
    """Attempt to re-scrape breed from Wikipedia"""
    try:
        from wikipedia_breed_scraper_fixed import WikipediaBreedScraper
        
        scraper = WikipediaBreedScraper()
        
        # Try different URL patterns
        urls = [
            f"https://en.wikipedia.org/wiki/{breed_name.replace(' ', '_')}",
            f"https://en.wikipedia.org/wiki/{breed_name.replace(' ', '_')}_(dog)",
            f"https://en.wikipedia.org/wiki/{breed_slug.replace('-', '_').title()}"
        ]
        
        for url in urls:
            try:
                data = scraper.scrape_breed(breed_name, url)
                if data and data.get('weight_kg_max'):
                    # Update breed with new data
                    updates = {
                        'weight_kg_min': data.get('weight_kg_min'),
                        'weight_kg_max': data.get('weight_kg_max'),
                        'adult_weight_avg_kg': round((data.get('weight_kg_min', 0) + data.get('weight_kg_max', 0)) / 2, 1),
                        'weight_from': 'enrichment',
                        'updated_at': datetime.now().isoformat()
                    }
                    
                    if data.get('height_cm_max'):
                        updates['height_cm_min'] = data.get('height_cm_min')
                        updates['height_cm_max'] = data.get('height_cm_max')
                        updates['height_from'] = 'enrichment'
                    
                    supabase.table('breeds_details').update(updates).eq('breed_slug', breed_slug).execute()
                    return True, "Successfully re-scraped from Wikipedia"
            except:
                continue
        
        return False, "Could not scrape from Wikipedia"
    except Exception as e:
        return False, f"Scraping error: {str(e)}"

def generate_spotcheck_report(results):
    """Generate spot-check report"""
    report = f"""
## Weekly Spot-Check Report
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Breeds Checked:** {len(results)}

### Summary
- Needed rescraping: {sum(1 for r in results if r['needed_rescrape'])}
- Successfully updated: {sum(1 for r in results if r.get('rescrape_success'))}
- Failed updates: {sum(1 for r in results if r.get('rescrape_attempted') and not r.get('rescrape_success'))}

### Details

"""
    
    for result in results:
        report += f"#### {result['display_name']} ({result['breed_slug']})\n"
        report += f"- Current quality: {result.get('data_quality', 'Unknown')}\n"
        report += f"- Weight coverage: {result.get('has_weight', False)}\n"
        report += f"- Last updated: {result.get('age_days', 'Unknown')} days ago\n"
        
        if result['needed_rescrape']:
            report += f"- **Needs rescrape:** {', '.join(result['reasons'])}\n"
            
            if result.get('rescrape_attempted'):
                if result.get('rescrape_success'):
                    report += f"- ✅ **Rescrape successful:** {result.get('rescrape_message')}\n"
                else:
                    report += f"- ❌ **Rescrape failed:** {result.get('rescrape_message')}\n"
        else:
            report += "- ✅ Data is current\n"
        
        report += "\n"
    
    report += "---\n\n"
    return report

def main():
    """Run weekly maintenance"""
    print("=" * 80)
    print("BREEDS WEEKLY MAINTENANCE")
    print("=" * 80)
    print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # Get random breeds
    breeds = get_random_breeds(5)
    print(f"\nSelected {len(breeds)} breeds for spot-checking")
    
    results = []
    
    for breed in breeds:
        print(f"\nChecking: {breed['display_name']} ({breed['breed_slug']})")
        
        result = {
            'breed_slug': breed['breed_slug'],
            'display_name': breed['display_name'],
            'has_weight': bool(breed.get('adult_weight_avg_kg')),
            'data_quality': 'A+' if breed.get('size_category') and breed.get('adult_weight_avg_kg') else 'B',
            'needed_rescrape': False,
            'rescrape_attempted': False,
            'rescrape_success': False
        }
        
        # Calculate age
        if breed.get('updated_at'):
            updated = datetime.fromisoformat(breed['updated_at'].replace('Z', '+00:00'))
            result['age_days'] = (datetime.now(updated.tzinfo) - updated).days
        
        # Check if needs rescraping
        reasons = needs_rescrape(breed)
        if reasons:
            result['needed_rescrape'] = True
            result['reasons'] = reasons
            print(f"  ⚠️ Needs rescraping: {', '.join(reasons)}")
            
            # Attempt rescrape
            if breed.get('weight_from') == 'default' or not breed.get('adult_weight_avg_kg'):
                print(f"  🔄 Attempting to rescrape...")
                result['rescrape_attempted'] = True
                success, message = rescrape_breed(breed['breed_slug'], breed['display_name'])
                result['rescrape_success'] = success
                result['rescrape_message'] = message
                
                if success:
                    print(f"  ✅ {message}")
                else:
                    print(f"  ❌ {message}")
        else:
            print(f"  ✅ Data is current")
        
        results.append(result)
    
    # Generate report
    report = generate_spotcheck_report(results)
    
    # Append to spotcheck file
    spotcheck_file = Path('reports/BREEDS_SPOTCHECK.md')
    
    # Create file with header if doesn't exist
    if not spotcheck_file.exists():
        spotcheck_file.parent.mkdir(parents=True, exist_ok=True)
        with open(spotcheck_file, 'w') as f:
            f.write("# Breeds Weekly Spot-Check Log\n\n")
            f.write("This file contains the history of weekly spot-checks performed on the breeds database.\n\n")
            f.write("---\n\n")
    
    # Append new report
    with open(spotcheck_file, 'a') as f:
        f.write(report)
    
    print(f"\nReport appended to: {spotcheck_file}")
    
    # Print summary
    print("\n" + "=" * 80)
    print("MAINTENANCE SUMMARY")
    print("=" * 80)
    print(f"Breeds checked: {len(results)}")
    print(f"Needed rescraping: {sum(1 for r in results if r['needed_rescrape'])}")
    print(f"Successfully updated: {sum(1 for r in results if r.get('rescrape_success'))}")
    print(f"Failed updates: {sum(1 for r in results if r.get('rescrape_attempted') and not r.get('rescrape_success'))}")
    
    return results

if __name__ == "__main__":
    main()