#!/usr/bin/env python3
"""
Database Migration: Add image_url column to food_candidates table
"""
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

def main():
    print("🔧 Adding image_url column to food_candidates table...")
    
    try:
        # Initialize Supabase client
        supabase = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_KEY')
        )
        
        # Execute SQL to add column (idempotent - safe to run multiple times)
        sql_query = """
        ALTER TABLE food_candidates 
        ADD COLUMN IF NOT EXISTS image_url text;
        """
        
        # Execute the SQL using Supabase client
        result = supabase.rpc('exec_sql', {'sql': sql_query}).execute()
        
        print("✅ Successfully added image_url column!")
        
        # Verify the column was added by querying the table structure
        print("🔍 Verifying column exists...")
        
        # Try a simple query to confirm column exists
        test_result = supabase.table('food_candidates')\
            .select('id, image_url')\
            .limit(1)\
            .execute()
        
        print("✅ Column verification successful!")
        print("🖼️  Ready to store product images in database!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n🔧 Alternative approach - try running this SQL manually in Supabase SQL editor:")
        print("ALTER TABLE food_candidates ADD COLUMN IF NOT EXISTS image_url text;")
        return False
    
    return True

if __name__ == '__main__':
    success = main()
    if success:
        print("\n🚀 Database migration completed successfully!")
    else:
        print("\n⚠️  Please run the SQL manually in Supabase dashboard")