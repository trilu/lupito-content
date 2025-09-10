#!/usr/bin/env python3
"""
End-to-End Test: AKC Breed Scraping to Supabase (akc_breeds table)
===================================================================
Test the complete pipeline from scraping to database storage using the existing akc_breeds table
"""

import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
import logging

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our extractors
from jobs.akc_comprehensive_extractor import AKCComprehensiveExtractor

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_test_data():
    """Load the already scraped Golden Retriever data"""
    logger.info("Loading pre-scraped Golden Retriever data...")
    
    # We already have the HTML from ScrapingBee
    with open('akc_10sec_wait.html', 'r') as f:
        html = f.read()
    
    return html, 'https://www.akc.org/dog-breeds/golden-retriever/'

def extract_breed_data(html, url):
    """Extract comprehensive breed data"""
    logger.info("Extracting breed data...")
    
    extractor = AKCComprehensiveExtractor()
    data = extractor.extract_all_data(html, url)
    
    # Log extraction results
    filled_fields = len([k for k, v in data.items() if v is not None])
    total_fields = len(data)
    logger.info(f"Extracted {filled_fields}/{total_fields} fields ({filled_fields/total_fields*100:.1f}%)")
    
    return data

def convert_inches_to_cm(inches):
    """Convert inches to centimeters"""
    if inches is None:
        return None
    return round(inches * 2.54, 1)

def convert_lbs_to_kg(lbs):
    """Convert pounds to kilograms"""
    if lbs is None:
        return None
    return round(lbs * 0.453592, 1)

def map_to_akc_breeds_schema(breed_data):
    """Map extracted data to akc_breeds table schema"""
    logger.info("Mapping data to akc_breeds table schema...")
    
    # Map temperament scores to text values
    def map_energy(score):
        if score is None: return None
        if score <= 2: return 'low'
        elif score == 3: return 'moderate'
        elif score == 4: return 'high'
        else: return 'very high'
    
    def map_shedding(score):
        if score is None: return None
        if score <= 2: return 'low'
        elif score == 3: return 'moderate'
        else: return 'high'
    
    def map_trainability(score):
        if score is None: return None
        if score >= 4: return 'easy'
        elif score == 3: return 'moderate'
        else: return 'challenging'
    
    def map_bark_level(score):
        if score is None: return None
        if score <= 2: return 'low'
        elif score == 3: return 'moderate'
        else: return 'high'
    
    # Determine size category based on weight
    def determine_size(weight_min, weight_max):
        if weight_max is None:
            return None
        avg_weight = (weight_min + weight_max) / 2 if weight_min else weight_max
        if avg_weight < 10:
            return 'small'
        elif avg_weight < 25:
            return 'medium'
        elif avg_weight < 40:
            return 'large'
        else:
            return 'giant'
    
    # Create comprehensive content JSON
    comprehensive_content = {
        'about': breed_data.get('about'),
        'history': breed_data.get('history'),
        'personality': breed_data.get('personality'),
        'health': breed_data.get('health'),
        'care': breed_data.get('care'),
        'feeding': breed_data.get('feeding'),
        'grooming': breed_data.get('grooming'),
        'training': breed_data.get('training'),
        'exercise': breed_data.get('exercise'),
        'breed_standard': breed_data.get('breed_standard'),
        'national_club': breed_data.get('national_club'),
        'rescue_groups': breed_data.get('rescue_groups'),
        'puppies_info': breed_data.get('puppies_info')
    }
    # Remove None values from content
    comprehensive_content = {k: v for k, v in comprehensive_content.items() if v is not None}
    
    # Create raw traits JSON
    raw_traits = {
        'affection_family': breed_data.get('affection_family'),
        'good_with_children': breed_data.get('good_with_children'),
        'good_with_dogs': breed_data.get('good_with_dogs'),
        'shedding': breed_data.get('shedding'),
        'grooming_needs': breed_data.get('grooming_needs'),
        'drooling': breed_data.get('drooling'),
        'coat_type': breed_data.get('coat_type'),
        'coat_length': breed_data.get('coat_length'),
        'good_with_strangers': breed_data.get('good_with_strangers'),
        'playfulness': breed_data.get('playfulness'),
        'protectiveness': breed_data.get('protectiveness'),
        'adaptability': breed_data.get('adaptability'),
        'trainability': breed_data.get('trainability'),
        'energy': breed_data.get('energy'),
        'barking': breed_data.get('barking'),
        'mental_stimulation': breed_data.get('mental_stimulation')
    }
    # Remove None values from traits
    raw_traits = {k: v for k, v in raw_traits.items() if v is not None}
    
    # Calculate data completeness score
    total_possible_fields = 30  # Approximate number of key fields
    filled_fields = sum([
        1 for v in [
            breed_data.get('height_male_min'),
            breed_data.get('weight_male_min'),
            breed_data.get('lifespan_min'),
            breed_data.get('energy'),
            breed_data.get('trainability'),
            breed_data.get('shedding'),
            breed_data.get('about'),
            breed_data.get('history'),
            breed_data.get('health'),
            breed_data.get('breed_group')
        ] if v is not None
    ])
    completeness_score = int((filled_fields / 10) * 100)
    
    # Determine what data categories we have
    has_physical = any([
        breed_data.get('height_male_min'),
        breed_data.get('height_female_min'),
        breed_data.get('weight_male_min'),
        breed_data.get('weight_female_min')
    ])
    
    has_temperament = len(raw_traits) > 0
    has_content = len(comprehensive_content) > 0
    
    # Map to akc_breeds table structure
    akc_record = {
        # Basic identification
        'breed_slug': breed_data.get('breed_slug', ''),
        'display_name': breed_data.get('display_name', ''),
        'akc_url': breed_data.get('url', ''),
        
        # Physical characteristics (convert to metric)
        'height_cm_min': convert_inches_to_cm(
            min(filter(None, [breed_data.get('height_male_min'), breed_data.get('height_female_min')]), default=None)
        ),
        'height_cm_max': convert_inches_to_cm(
            max(filter(None, [breed_data.get('height_male_max'), breed_data.get('height_female_max')]), default=None)
        ),
        'weight_kg_min': convert_lbs_to_kg(
            min(filter(None, [breed_data.get('weight_male_min'), breed_data.get('weight_female_min')]), default=None)
        ),
        'weight_kg_max': convert_lbs_to_kg(
            max(filter(None, [breed_data.get('weight_male_max'), breed_data.get('weight_female_max')]), default=None)
        ),
        
        # Size category
        'size': determine_size(
            convert_lbs_to_kg(breed_data.get('weight_male_min')),
            convert_lbs_to_kg(breed_data.get('weight_male_max'))
        ),
        
        # Lifespan
        'lifespan_years_min': breed_data.get('lifespan_min'),
        'lifespan_years_max': breed_data.get('lifespan_max'),
        
        # Breed characteristics (normalized)
        'energy': map_energy(breed_data.get('energy')),
        'coat_length': 'medium',  # Default, would need to parse from coat_type
        'shedding': map_shedding(breed_data.get('shedding')),
        'trainability': map_trainability(breed_data.get('trainability')),
        'bark_level': map_bark_level(breed_data.get('barking')),
        
        # Temperament scores
        'friendliness_to_dogs': breed_data.get('good_with_dogs'),
        'friendliness_to_humans': breed_data.get('good_with_strangers'),
        'good_with_children': breed_data.get('good_with_children') is not None and breed_data.get('good_with_children') >= 3,
        'good_with_other_pets': breed_data.get('good_with_dogs') is not None and breed_data.get('good_with_dogs') >= 3,
        
        # Origin and history
        'origin': None,  # Would need to parse from history text
        'breed_group': breed_data.get('breed_group'),
        
        # Comprehensive content (JSON)
        'comprehensive_content': json.dumps(comprehensive_content) if comprehensive_content else None,
        'raw_traits': json.dumps(raw_traits) if raw_traits else None,
        
        # Metadata
        'scraped_at': datetime.utcnow().isoformat(),
        'extraction_status': 'success' if completeness_score > 70 else 'partial',
        'extraction_notes': f"Extracted {filled_fields}/{total_possible_fields} key fields",
        
        # Quality tracking
        'data_completeness_score': completeness_score,
        'has_physical_data': has_physical,
        'has_temperament_data': has_temperament,
        'has_content': has_content
    }
    
    # Remove None values for cleaner insert
    akc_record = {k: v for k, v in akc_record.items() if v is not None}
    
    logger.info(f"Mapped {len(akc_record)} fields for akc_breeds table")
    return akc_record

def insert_to_akc_breeds(record):
    """Insert breed record into akc_breeds table"""
    logger.info("Connecting to Supabase...")
    
    # Load environment variables
    load_dotenv()
    
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_KEY')
    
    if not url or not key:
        logger.error("Missing Supabase credentials in .env file")
        return False
    
    try:
        # Create Supabase client
        supabase = create_client(url, key)
        
        # Check if breed already exists
        logger.info(f"Checking if breed '{record['breed_slug']}' exists in akc_breeds...")
        existing = supabase.table('akc_breeds').select('id').eq('breed_slug', record['breed_slug']).execute()
        
        if existing.data:
            # Update existing record
            logger.info(f"Updating existing breed record...")
            response = supabase.table('akc_breeds').update(record).eq('breed_slug', record['breed_slug']).execute()
            logger.info(f"✅ Updated breed in akc_breeds: {record['display_name']}")
        else:
            # Insert new record
            logger.info(f"Inserting new breed record...")
            response = supabase.table('akc_breeds').insert(record).execute()
            logger.info(f"✅ Inserted breed into akc_breeds: {record['display_name']}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        return False

def verify_in_akc_breeds(slug):
    """Verify the breed was inserted correctly"""
    logger.info("Verifying breed in akc_breeds table...")
    
    load_dotenv()
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_KEY')
    
    try:
        supabase = create_client(url, key)
        
        # Query the breed
        response = supabase.table('akc_breeds').select('*').eq('breed_slug', slug).execute()
        
        if response.data:
            breed = response.data[0]
            logger.info(f"✅ Breed found in akc_breeds table: {breed['display_name']}")
            
            # Count populated fields
            populated = len([k for k, v in breed.items() if v])
            logger.info(f"📊 Populated fields: {populated}/{len(breed)}")
            
            # Show some key fields
            logger.info(f"  - Breed Group: {breed.get('breed_group')}")
            logger.info(f"  - Size: {breed.get('size')}")
            logger.info(f"  - Lifespan: {breed.get('lifespan_years_min')}-{breed.get('lifespan_years_max')} years")
            logger.info(f"  - Height: {breed.get('height_cm_min')}-{breed.get('height_cm_max')} cm")
            logger.info(f"  - Weight: {breed.get('weight_kg_min')}-{breed.get('weight_kg_max')} kg")
            logger.info(f"  - Completeness Score: {breed.get('data_completeness_score')}%")
            logger.info(f"  - Has Content: {breed.get('has_content')}")
            
            return breed
        else:
            logger.error("❌ Breed not found in akc_breeds table")
            return None
            
    except Exception as e:
        logger.error(f"❌ Verification error: {e}")
        return None

def main():
    """Run the complete end-to-end test"""
    print("=" * 80)
    print("🧪 END-TO-END TEST: AKC → SUPABASE (akc_breeds table)")
    print("=" * 80)
    print()
    
    # Step 1: Load test data
    html, url = load_test_data()
    logger.info(f"Loaded {len(html)} bytes of HTML")
    
    # Step 2: Extract breed data
    breed_data = extract_breed_data(html, url)
    
    # Save extracted data for review
    with open('test_akc_extracted_data.json', 'w') as f:
        json.dump(breed_data, f, indent=2)
    logger.info("Saved extracted data to test_akc_extracted_data.json")
    
    # Step 3: Map to akc_breeds schema
    akc_record = map_to_akc_breeds_schema(breed_data)
    
    # Save mapped data for review
    with open('test_akc_breeds_record.json', 'w') as f:
        json.dump(akc_record, f, indent=2)
    logger.info("Saved akc_breeds record to test_akc_breeds_record.json")
    
    # Step 4: Insert to akc_breeds table
    success = insert_to_akc_breeds(akc_record)
    
    if success:
        # Step 5: Verify insertion
        verified = verify_in_akc_breeds(akc_record['breed_slug'])
        
        if verified:
            print()
            print("=" * 80)
            print("✅ TEST SUCCESSFUL!")
            print(f"Breed '{verified['display_name']}' is now in akc_breeds table")
            print(f"Completeness: {verified.get('data_completeness_score')}%")
            print(f"View at: https://supabase.com/dashboard/project/cibjeqgftuxuezarjsdl/editor/akc_breeds")
            print("=" * 80)
        else:
            print("⚠️ Test completed but verification failed")
    else:
        print("❌ Test failed - could not insert to akc_breeds table")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)