#!/usr/bin/env python3
"""
BREED STANDARDS IMPORT - Phase 3 of 95% Completeness Strategy

Import official breed standards and detailed breed information from authoritative sources:
- American Kennel Club (AKC)
- The Kennel Club (UK)
- Fédération Cynologique Internationale (FCI)
- United Kennel Club (UKC)

Strategy: Use the breed_standard URLs generated in Phase 1 (zero fields) to extract comprehensive data
Expected impact: +2,000 fields, ~7% completeness gain
"""

import os
import json
import re
import time
import random
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv
import requests
from urllib.parse import urljoin, urlparse

load_dotenv()

class BreedStandardsImporter:
    def __init__(self):
        """Initialize breed standards importer"""
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

        # Request headers to mimic browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

        # Fields we can extract from breed standards
        self.extractable_fields = [
            'height_min_cm', 'height_max_cm', 'weight_min_kg', 'weight_max_kg',
            'coat', 'colors', 'temperament', 'personality_traits', 'grooming_needs',
            'exercise_needs_detail', 'health_issues', 'lifespan_min_years',
            'lifespan_max_years', 'training_tips', 'fun_facts', 'origin'
        ]

    def get_breeds_with_standards(self):
        """Get breeds that have breed_standard URLs"""
        print("📋 Finding breeds with breed standard URLs...")

        response = self.supabase.table('breeds_comprehensive_content').select('*').neq('breed_standard', None).execute()
        breeds_with_standards = [breed for breed in response.data if breed.get('breed_standard') and breed.get('breed_standard').strip()]

        print(f"✅ Found {len(breeds_with_standards)} breeds with breed standard URLs")
        return breeds_with_standards

    def extract_measurements(self, content):
        """Extract height and weight measurements from content"""
        extracted = {}

        # Height patterns (looking for cm, inches)
        height_patterns = [
            r'height[:\s]*(\d+)[-–—to\s]+(\d+)\s*(?:cm|centimeters)',
            r'(\d+)[-–—to\s]+(\d+)\s*(?:cm|centimeters)[^.]*height',
            r'height[:\s]*(\d+)[-–—to\s]+(\d+)\s*(?:in|inches)',
            r'(\d+)[-–—to\s]+(\d+)\s*(?:in|inches)[^.]*height'
        ]

        for pattern in height_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                min_val = int(match.group(1))
                max_val = int(match.group(2))

                # Convert inches to cm if needed
                if 'in' in pattern:
                    min_val = round(min_val * 2.54)
                    max_val = round(max_val * 2.54)

                extracted['height_min_cm'] = min_val
                extracted['height_max_cm'] = max_val
                break

        # Weight patterns (looking for kg, pounds)
        weight_patterns = [
            r'weight[:\s]*(\d+)[-–—to\s]+(\d+)\s*(?:kg|kilograms)',
            r'(\d+)[-–—to\s]+(\d+)\s*(?:kg|kilograms)[^.]*weight',
            r'weight[:\s]*(\d+)[-–—to\s]+(\d+)\s*(?:lb|lbs|pounds)',
            r'(\d+)[-–—to\s]+(\d+)\s*(?:lb|lbs|pounds)[^.]*weight'
        ]

        for pattern in weight_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                min_val = int(match.group(1))
                max_val = int(match.group(2))

                # Convert pounds to kg if needed
                if 'lb' in pattern or 'pound' in pattern:
                    min_val = round(min_val * 0.453592, 1)
                    max_val = round(max_val * 0.453592, 1)

                extracted['weight_min_kg'] = min_val
                extracted['weight_max_kg'] = max_val
                break

        return extracted

    def extract_descriptive_fields(self, content):
        """Extract descriptive fields from breed standard content"""
        extracted = {}

        # Temperament patterns
        temperament_patterns = [
            r'temperament[:\s]*([^.]{20,300})',
            r'personality[:\s]*([^.]{20,300})',
            r'character[:\s]*([^.]{20,300})',
            r'disposition[:\s]*([^.]{20,300})'
        ]

        for pattern in temperament_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                desc = match.group(1).strip()
                if len(desc) > 20 and len(desc) < 350:
                    extracted['temperament'] = desc
                    break

        # Coat description patterns
        coat_patterns = [
            r'coat[:\s]*([^.]{10,200})',
            r'hair[:\s]*([^.]{10,200})',
            r'fur[:\s]*([^.]{10,200})'
        ]

        for pattern in coat_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                desc = match.group(1).strip()
                if len(desc) > 10 and len(desc) < 250:
                    extracted['coat'] = desc
                    break

        # Colors patterns
        color_patterns = [
            r'colors?[:\s]*([^.]{10,200})',
            r'colou?rs?[:\s]*([^.]{10,200})',
            r'coat colou?rs?[:\s]*([^.]{10,200})'
        ]

        for pattern in color_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                desc = match.group(1).strip()
                if len(desc) > 10 and len(desc) < 250:
                    extracted['colors'] = desc
                    break

        # Health issues patterns
        health_patterns = [
            r'health[:\s]*([^.]{20,300})',
            r'health issues?[:\s]*([^.]{20,300})',
            r'health concerns?[:\s]*([^.]{20,300})',
            r'common problems?[:\s]*([^.]{20,300})'
        ]

        for pattern in health_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                desc = match.group(1).strip()
                if len(desc) > 20 and len(desc) < 350:
                    extracted['health_issues'] = desc
                    break

        # Grooming patterns
        grooming_patterns = [
            r'grooming[:\s]*([^.]{10,200})',
            r'care[:\s]*([^.]{10,200})',
            r'maintenance[:\s]*([^.]{10,200})'
        ]

        for pattern in grooming_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                desc = match.group(1).strip()
                if len(desc) > 10 and len(desc) < 250:
                    extracted['grooming_needs'] = desc
                    break

        # Exercise patterns
        exercise_patterns = [
            r'exercise[:\s]*([^.]{10,200})',
            r'activity[:\s]*([^.]{10,200})',
            r'exercise needs?[:\s]*([^.]{10,200})'
        ]

        for pattern in exercise_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                desc = match.group(1).strip()
                if len(desc) > 10 and len(desc) < 250:
                    extracted['exercise_needs_detail'] = desc
                    break

        return extracted

    def extract_lifespan(self, content):
        """Extract lifespan information"""
        lifespan_patterns = [
            r'(?:lifespan|life expectancy|lives?)[:\s]*(\d+)[-–—to\s]+(\d+)\s*years?',
            r'(\d+)[-–—to\s]+(\d+)\s*years?\s*(?:lifespan|life expectancy)',
            r'typically lives?\s*(\d+)[-–—to\s]+(\d+)\s*years?'
        ]

        for pattern in lifespan_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                min_years = int(match.group(1))
                max_years = int(match.group(2))
                return {
                    'lifespan_min_years': min_years,
                    'lifespan_max_years': max_years,
                    'lifespan_avg_years': round((min_years + max_years) / 2, 1)
                }
        return {}

    def scrape_breed_standard(self, breed_standard_url):
        """Scrape breed standard page and extract data"""
        try:
            response = requests.get(breed_standard_url, headers=self.headers, timeout=10)
            response.raise_for_status()

            content = response.text.lower()

            # Extract all possible data
            extracted_data = {}
            extracted_data.update(self.extract_measurements(content))
            extracted_data.update(self.extract_descriptive_fields(content))
            extracted_data.update(self.extract_lifespan(content))

            return extracted_data

        except Exception as e:
            print(f"   ⚠️ Error scraping {breed_standard_url}: {e}")
            return {}

    def process_breed(self, breed):
        """Process a single breed's standard"""
        breed_slug = breed['breed_slug']
        breed_name = breed.get('display_name', breed_slug)
        breed_standard_url = breed.get('breed_standard')

        print(f"\n🐕 Processing {breed_name}")
        print(f"   Standard URL: {breed_standard_url}")

        # Find missing extractable fields
        missing_fields = []
        for field in self.extractable_fields:
            if not breed.get(field) or str(breed.get(field)).strip() == '':
                missing_fields.append(field)

        if not missing_fields:
            print(f"   ✅ All extractable fields already filled")
            return 0

        print(f"   Missing: {', '.join(missing_fields[:5])}{'...' if len(missing_fields) > 5 else ''}")

        # Scrape the breed standard
        extracted_data = self.scrape_breed_standard(breed_standard_url)

        if not extracted_data:
            print(f"   ❌ No data extracted from standard")
            return 0

        # Filter to only update missing fields
        updates = {}
        for field, value in extracted_data.items():
            if field in missing_fields and value:
                updates[field] = value

        if updates:
            try:
                self.supabase.table('breeds_comprehensive_content').update(updates).eq('breed_slug', breed_slug).execute()
                fields_updated = list(updates.keys())
                print(f"   ✅ Updated: {', '.join(fields_updated)}")
                return len(fields_updated)
            except Exception as e:
                print(f"   ❌ Database error: {e}")
                return 0
        else:
            print(f"   ❌ No useful data found in standard")
            return 0

    def run_standards_import(self, max_breeds=100):
        """Run the breed standards import process"""
        print("\n" + "="*80)
        print("📚 BREED STANDARDS IMPORT - PHASE 3 STARTING")
        print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)

        breeds_with_standards = self.get_breeds_with_standards()

        # Prioritize breeds with fewer missing fields (easier wins)
        target_breeds = breeds_with_standards[:max_breeds]

        print(f"\n🎯 Targeting {len(target_breeds)} breeds with official standards...")
        print(f"🔍 Extractable fields: {', '.join(self.extractable_fields[:8])}...")

        total_fields_updated = 0
        breeds_updated = 0

        for i, breed in enumerate(target_breeds, 1):
            print(f"\n[{i:3d}/{len(target_breeds)}]", end=" ")
            fields_updated = self.process_breed(breed)

            if fields_updated > 0:
                total_fields_updated += fields_updated
                breeds_updated += 1

            # Rate limiting and progress update
            time.sleep(random.uniform(2, 4))  # Be respectful to official sites

            if i % 10 == 0:
                progress = (i / len(target_breeds)) * 100
                success_rate = (breeds_updated / i) * 100
                print(f"\n📊 Progress: {progress:.1f}% | Success rate: {success_rate:.1f}% | Fields updated: {total_fields_updated}")

        # Final summary
        success_rate = (breeds_updated / len(target_breeds)) * 100 if target_breeds else 0
        estimated_gain = (total_fields_updated / 29733) * 100

        print("\n" + "="*80)
        print("🎉 BREED STANDARDS IMPORT COMPLETE")
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
            'operation': 'Breed Standards Import',
            'extractable_fields': self.extractable_fields,
            'breeds_processed': len(target_breeds),
            'breeds_updated': breeds_updated,
            'fields_updated': total_fields_updated,
            'success_rate_percent': success_rate,
            'estimated_gain_percent': estimated_gain
        }

        with open('breed_standards_import_report.json', 'w') as f:
            json.dump(report, f, indent=2)

        print(f"📁 Detailed report saved to breed_standards_import_report.json")
        return total_fields_updated

if __name__ == "__main__":
    importer = BreedStandardsImporter()
    fields_updated = importer.run_standards_import(max_breeds=100)