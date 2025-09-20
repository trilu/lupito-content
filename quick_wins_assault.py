#!/usr/bin/env python3
"""
QUICK WINS ASSAULT - Phase 1 of 95% Completeness Strategy

Target fields with 50-90% completion for maximum efficiency:
- coat (50.6% complete, 288 missing)
- grooming_needs (53.5% complete, 271 missing)
- colors (54.5% complete, 265 missing)
- lifespan_min/max/avg_years (59.2% complete, 238 missing each)
- training_tips (61.2% complete, 226 missing)
- temperament (67.8% complete, 188 missing)

Strategy: Use ScrapingBee to scrape breed-specific pages from multiple sources
Expected impact: +1,500 fields, ~5% completeness gain
"""

import os
import json
import re
import time
import random
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv
from scrapingbee import ScrapingBeeClient

load_dotenv()

class QuickWinsAssault:
    def __init__(self):
        """Initialize quick wins assault scraper"""
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

        # ScrapingBee setup
        self.scrapingbee_key = os.getenv('SCRAPINGBEE_API_KEY')
        self.client = ScrapingBeeClient(api_key=self.scrapingbee_key)

        # Target fields for quick wins
        self.quick_win_fields = [
            'coat', 'grooming_needs', 'colors', 'lifespan_min_years',
            'lifespan_max_years', 'lifespan_avg_years', 'training_tips', 'temperament'
        ]

        # High-value breed information sources
        self.breed_sources = [
            "https://www.akc.org/dog-breeds/{breed_name}/",
            "https://dogtime.com/dog-breeds/{breed_name}",
            "https://www.petfinder.com/dog-breeds/{breed_name}/",
            "https://www.hillspet.com/dog-care/dog-breeds/{breed_name}",
            "https://www.purina.com/dogs/dog-breeds/{breed_name}",
            "https://www.orvis.com/dog-encyclopedia/{breed_name}",
            "https://www.vetstreet.com/dogs/{breed_name}",
            "https://www.thesprucepets.com/{breed_name}-dog-breed-profile",
            "https://dogbreedslist.info/{breed_name}/",
            "https://www.rover.com/dog-breeds/{breed_name}/"
        ]

    def get_incomplete_breeds(self):
        """Get breeds missing quick win fields"""
        print("📋 Finding breeds with missing quick win fields...")

        # Build condition for breeds missing any quick win field
        conditions = []
        for field in self.quick_win_fields:
            conditions.append(f"({field} IS NULL OR {field} = '')")

        where_clause = " OR ".join(conditions)

        response = self.supabase.table('breeds_comprehensive_content').select('*').execute()
        all_breeds = response.data

        # Filter for breeds missing quick win fields
        incomplete_breeds = []
        for breed in all_breeds:
            missing_fields = []
            for field in self.quick_win_fields:
                if not breed.get(field) or breed.get(field).strip() == '':
                    missing_fields.append(field)

            if missing_fields:
                breed['missing_quick_win_fields'] = missing_fields
                incomplete_breeds.append(breed)

        print(f"✅ Found {len(incomplete_breeds)} breeds missing quick win fields")
        return incomplete_breeds

    def format_breed_name_for_url(self, breed_name):
        """Convert breed name to URL-friendly format"""
        # Handle common breed name variations
        name = breed_name.lower()
        name = re.sub(r'[^\w\s-]', '', name)
        name = re.sub(r'\s+', '-', name.strip())
        return name

    def extract_lifespan_data(self, content):
        """Extract lifespan information from scraped content"""
        lifespan_patterns = [
            r'(?:lifespan|life expectancy|lives?)[:\s]*(\d+)[-–—to\s]+(\d+)\s*years?',
            r'(\d+)[-–—to\s]+(\d+)\s*years?\s*(?:lifespan|life expectancy)',
            r'typically lives?\s*(\d+)[-–—to\s]+(\d+)\s*years?',
            r'expected lifespan[:\s]*(\d+)[-–—to\s]+(\d+)\s*years?'
        ]

        for pattern in lifespan_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                min_years = int(match.group(1))
                max_years = int(match.group(2))
                avg_years = round((min_years + max_years) / 2, 1)
                return {
                    'lifespan_min_years': min_years,
                    'lifespan_max_years': max_years,
                    'lifespan_avg_years': avg_years
                }
        return {}

    def extract_coat_data(self, content):
        """Extract coat information from scraped content"""
        coat_patterns = [
            r'coat[:\s]*((?:double|single|short|long|medium|thick|dense|curly|wavy|straight|smooth|rough|wiry|silky|harsh)[^.]*)',
            r'(?:hair|fur)[:\s]*((?:short|long|medium|thick|dense|curly|wavy|straight|smooth|rough|wiry|silky)[^.]*)',
            r'(?:grooming|coat type)[:\s]*([^.]{1,100})'
        ]

        for pattern in coat_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                coat_desc = match.group(1).strip()
                if len(coat_desc) > 10 and len(coat_desc) < 200:
                    return {'coat': coat_desc}
        return {}

    def extract_colors_data(self, content):
        """Extract color information from scraped content"""
        color_patterns = [
            r'colors?[:\s]*([^.]{10,150})',
            r'comes in[:\s]*([^.]{10,150})',
            r'coat colors?[:\s]*([^.]{10,150})',
            r'available in[:\s]*([^.]{10,150})'
        ]

        for pattern in color_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                colors_desc = match.group(1).strip()
                if len(colors_desc) > 10 and len(colors_desc) < 200:
                    return {'colors': colors_desc}
        return {}

    def extract_temperament_data(self, content):
        """Extract temperament information from scraped content"""
        temperament_patterns = [
            r'temperament[:\s]*([^.]{10,200})',
            r'personality[:\s]*([^.]{10,200})',
            r'character[:\s]*([^.]{10,200})',
            r'disposition[:\s]*([^.]{10,200})'
        ]

        for pattern in temperament_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                temp_desc = match.group(1).strip()
                if len(temp_desc) > 10 and len(temp_desc) < 250:
                    return {'temperament': temp_desc}
        return {}

    def extract_grooming_data(self, content):
        """Extract grooming information from scraped content"""
        grooming_patterns = [
            r'grooming[:\s]*([^.]{10,200})',
            r'grooming needs[:\s]*([^.]{10,200})',
            r'maintenance[:\s]*([^.]{10,200})',
            r'care requirements[:\s]*([^.]{10,200})'
        ]

        for pattern in grooming_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                grooming_desc = match.group(1).strip()
                if len(grooming_desc) > 10 and len(grooming_desc) < 200:
                    return {'grooming_needs': grooming_desc}
        return {}

    def extract_training_data(self, content):
        """Extract training information from scraped content"""
        training_patterns = [
            r'training[:\s]*([^.]{10,200})',
            r'training tips[:\s]*([^.]{10,200})',
            r'how to train[:\s]*([^.]{10,200})',
            r'trainability[:\s]*([^.]{10,200})'
        ]

        for pattern in training_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                training_desc = match.group(1).strip()
                if len(training_desc) > 10 and len(training_desc) < 200:
                    return {'training_tips': training_desc}
        return {}

    def scrape_breed_page(self, breed_name, url_template):
        """Scrape a specific breed page"""
        try:
            formatted_name = self.format_breed_name_for_url(breed_name)
            url = url_template.format(breed_name=formatted_name)

            response = self.client.get(
                url,
                params={
                    'render_js': 'false',
                    'premium_proxy': 'true',
                    'wait': 2000
                }
            )

            if response.status_code == 200:
                content = response.content.decode('utf-8')

                # Extract all relevant data
                extracted_data = {}
                extracted_data.update(self.extract_lifespan_data(content))
                extracted_data.update(self.extract_coat_data(content))
                extracted_data.update(self.extract_colors_data(content))
                extracted_data.update(self.extract_temperament_data(content))
                extracted_data.update(self.extract_grooming_data(content))
                extracted_data.update(self.extract_training_data(content))

                return extracted_data

        except Exception as e:
            print(f"   ⚠️ Error scraping {url}: {e}")
            return {}

        return {}

    def process_breed(self, breed):
        """Process a single breed through multiple sources"""
        breed_slug = breed['breed_slug']
        breed_name = breed.get('display_name', breed_slug)
        missing_fields = breed.get('missing_quick_win_fields', [])

        print(f"\n🐕 Processing {breed_name}")
        print(f"   Missing: {', '.join(missing_fields)}")

        # Try multiple sources until we fill enough fields
        all_extracted_data = {}
        sources_tried = 0
        max_sources = min(5, len(self.breed_sources))  # Limit sources to avoid excessive calls

        for source_template in random.sample(self.breed_sources, max_sources):
            sources_tried += 1
            extracted_data = self.scrape_breed_page(breed_name, source_template)

            if extracted_data:
                # Merge new data, prioritizing existing
                for field, value in extracted_data.items():
                    if field in missing_fields and field not in all_extracted_data:
                        all_extracted_data[field] = value

                print(f"   ✅ Source {sources_tried}: Found {len(extracted_data)} fields")

                # Stop if we've filled most missing fields
                filled_fields = len([f for f in missing_fields if f in all_extracted_data])
                if filled_fields >= len(missing_fields) * 0.7:  # 70% threshold
                    break
            else:
                print(f"   ❌ Source {sources_tried}: No data found")

            # Rate limiting
            time.sleep(random.uniform(1, 3))

        # Update database if we found any data
        if all_extracted_data:
            try:
                self.supabase.table('breeds_comprehensive_content').update(all_extracted_data).eq('breed_slug', breed_slug).execute()
                fields_updated = list(all_extracted_data.keys())
                print(f"   ✅ Updated: {', '.join(fields_updated)}")
                return len(fields_updated)
            except Exception as e:
                print(f"   ❌ Database error: {e}")
                return 0
        else:
            print(f"   ❌ No data found for {breed_name}")
            return 0

    def run_quick_wins_assault(self, max_breeds=50):
        """Run the quick wins assault on incomplete breeds"""
        print("\n" + "="*80)
        print("🚀 QUICK WINS ASSAULT - PHASE 1 STARTING")
        print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)

        incomplete_breeds = self.get_incomplete_breeds()

        # Sort by number of missing fields (prioritize breeds missing fewer fields)
        incomplete_breeds.sort(key=lambda x: len(x.get('missing_quick_win_fields', [])))

        # Limit to max_breeds
        target_breeds = incomplete_breeds[:max_breeds]

        print(f"\n🎯 Targeting {len(target_breeds)} breeds for quick wins...")
        print(f"🔍 Target fields: {', '.join(self.quick_win_fields)}")

        total_fields_updated = 0
        breeds_updated = 0

        for i, breed in enumerate(target_breeds, 1):
            print(f"\n[{i:3d}/{len(target_breeds)}]", end=" ")
            fields_updated = self.process_breed(breed)

            if fields_updated > 0:
                total_fields_updated += fields_updated
                breeds_updated += 1

            # Progress update every 10 breeds
            if i % 10 == 0:
                progress = (i / len(target_breeds)) * 100
                success_rate = (breeds_updated / i) * 100
                print(f"\n📊 Progress: {progress:.1f}% | Success rate: {success_rate:.1f}% | Fields updated: {total_fields_updated}")

        # Final summary
        success_rate = (breeds_updated / len(target_breeds)) * 100 if target_breeds else 0
        estimated_gain = (total_fields_updated / 29733) * 100

        print("\n" + "="*80)
        print("🎉 QUICK WINS ASSAULT COMPLETE")
        print("="*80)
        print(f"📊 FINAL STATISTICS:")
        print(f"   Breeds processed: {len(target_breeds)}")
        print(f"   Breeds updated: {breeds_updated}")
        print(f"   Success rate: {success_rate:.1f}%")
        print(f"   Fields updated: {total_fields_updated}")
        print(f"   Estimated completeness gain: +{estimated_gain:.1f}%")
        print(f"⏰ Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Save report
        report = {
            'timestamp': datetime.now().isoformat(),
            'operation': 'Quick Wins Assault',
            'target_fields': self.quick_win_fields,
            'breeds_processed': len(target_breeds),
            'breeds_updated': breeds_updated,
            'fields_updated': total_fields_updated,
            'success_rate_percent': success_rate,
            'estimated_gain_percent': estimated_gain
        }

        with open('quick_wins_assault_report.json', 'w') as f:
            json.dump(report, f, indent=2)

        print(f"📁 Detailed report saved to quick_wins_assault_report.json")
        return total_fields_updated

if __name__ == "__main__":
    assault = QuickWinsAssault()
    fields_updated = assault.run_quick_wins_assault(max_breeds=75)