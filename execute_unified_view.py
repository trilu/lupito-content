#!/usr/bin/env python3
"""
Execute the unified breed view SQL in Supabase
"""

import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

def execute_unified_view():
    # Initialize Supabase
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    supabase = create_client(url, key)

    print("="*80)
    print("CREATING UNIFIED BREED VIEW IN SUPABASE")
    print("="*80)

    # Read the SQL file
    with open('create_unified_breed_view.sql', 'r') as f:
        sql_content = f.read()

    try:
        # Execute the SQL
        print("\n📝 Executing SQL to create breeds_unified_api view...")

        # Use RPC to execute raw SQL
        result = supabase.rpc('exec_sql', {'query': sql_content}).execute()

        print("✅ View creation SQL executed successfully!")

    except Exception as e:
        error_msg = str(e)

        # If exec_sql doesn't exist, provide instructions
        if 'exec_sql' in error_msg and 'does not exist' in error_msg:
            print("\n⚠️  The exec_sql function doesn't exist in your Supabase.")
            print("\n📋 MANUAL EXECUTION REQUIRED:")
            print("-" * 60)
            print("Please run the following SQL in your Supabase SQL editor:")
            print()
            print("1. Go to your Supabase Dashboard")
            print("2. Navigate to SQL Editor")
            print("3. Copy and paste the contents of 'create_unified_breed_view.sql'")
            print("4. Click 'Run' to execute")
            print()
            print("The SQL file is ready at: create_unified_breed_view.sql")

        else:
            print(f"❌ Error executing SQL: {error_msg}")

    # Test the view if it was created
    print("\n" + "="*80)
    print("TESTING THE NEW VIEW")
    print("-" * 60)

    try:
        # Try to query the new view
        response = supabase.table('breeds_unified_api').select('breed_slug, display_name, content_completeness_score').limit(5).execute()

        if response.data:
            print(f"✅ View is working! Found {len(response.data)} test records:")
            for breed in response.data:
                print(f"  - {breed['display_name']} (slug: {breed['breed_slug']}, score: {breed.get('content_completeness_score', 'N/A')})")
        else:
            print("⚠️ View exists but returned no data")

    except Exception as e:
        error_msg = str(e)
        if 'relation' in error_msg and 'does not exist' in error_msg:
            print("⚠️ View doesn't exist yet. Please execute the SQL manually in Supabase.")
        else:
            print(f"❌ Error testing view: {error_msg}")

    # Test the helper functions
    print("\n" + "="*80)
    print("TESTING HELPER FUNCTIONS")
    print("-" * 60)

    try:
        # Test get_breed_complete function
        print("\n📝 Testing get_breed_complete('golden-retriever')...")
        result = supabase.rpc('get_breed_complete', {'p_breed_slug': 'golden-retriever'}).execute()

        if result.data:
            print(f"✅ Function works! Retrieved data for: {result.data[0].get('display_name', 'Unknown')}")
        else:
            print("⚠️ Function exists but returned no data for golden-retriever")

    except Exception as e:
        print(f"⚠️ Function not yet created or error: {str(e)[:100]}")

    print("\n" + "="*80)
    print("SUMMARY")
    print("-" * 60)
    print("\n✅ SQL file is ready at: create_unified_breed_view.sql")
    print("\nTo complete the setup:")
    print("1. Go to Supabase SQL Editor")
    print("2. Paste and run the SQL from create_unified_breed_view.sql")
    print("3. The view will consolidate all breed data for the API team")
    print("\nThe view includes:")
    print("  - All columns from breeds_published")
    print("  - All content from breeds_comprehensive_content")
    print("  - Computed fields (completeness score, rich content flag, etc.)")
    print("  - Helper functions for search and recommendations")

if __name__ == "__main__":
    execute_unified_view()