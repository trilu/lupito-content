#!/usr/bin/env python3
"""
Check extraction results for test breeds
"""

import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Initialize Supabase
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(supabase_url, supabase_key)

# Check test breeds
test_breeds = ['affenpinscher', 'afghan-hound', 'airedale-terrier']

for breed in test_breeds:
    data = supabase.table('breeds_comprehensive_content').select('*').eq('breed_slug', breed).execute().data
    if data:
        record = data[0]
        print(f"\n{'='*60}")
        print(f"Breed: {breed}")
        print(f"{'='*60}")

        # Check each field
        fields = {
            'personality_description': 'Personality',
            'history': 'History',
            'general_care': 'Care',
            'health_issues': 'Health',
            'fun_facts': 'Fun Facts',
            'introduction': 'Introduction'
        }

        for field, label in fields.items():
            value = record.get(field)
            if value:
                print(f"\n{label}: {value[:200]}..." if len(str(value)) > 200 else f"\n{label}: {value}")
            else:
                print(f"\n{label}: None")
    else:
        print(f"No data found for {breed}")