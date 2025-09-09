#!/usr/bin/env python3
"""
Analyze the food_candidates table in Supabase
"""

import os
from dotenv import load_dotenv
from supabase import create_client
import pandas as pd
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def connect_to_supabase():
    """Connect to Supabase database"""
    load_dotenv()
    
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_KEY')
    
    if not url or not key:
        logger.error("Missing Supabase credentials in .env file")
        return None
    
    try:
        logger.info("Connecting to Supabase...")
        supabase = create_client(url, key)
        return supabase
    except Exception as e:
        logger.error(f"Error connecting to Supabase: {e}")
        return None

def analyze_food_candidates(supabase):
    """Analyze the food_candidates table"""
    
    try:
        # Get table schema info
        logger.info("Fetching food_candidates table structure...")
        
        # Get a sample to understand the structure
        sample = supabase.table('food_candidates').select('*').limit(1).execute()
        
        if sample.data:
            columns = list(sample.data[0].keys())
            logger.info(f"Table columns: {columns}")
            print("\n📊 TABLE STRUCTURE:")
            print("-" * 50)
            for col in columns:
                print(f"  • {col}")
        
        # Get total count
        count_response = supabase.table('food_candidates').select('*', count='exact').execute()
        total_count = count_response.count
        logger.info(f"Total records: {total_count}")
        
        print("\n📈 TABLE STATISTICS:")
        print("-" * 50)
        print(f"Total records: {total_count:,}")
        
        # Get data for analysis (limiting to manage memory)
        limit = min(10000, total_count) if total_count else 10000
        logger.info(f"Fetching up to {limit} records for detailed analysis...")
        
        data_response = supabase.table('food_candidates').select('*').limit(limit).execute()
        
        if data_response.data:
            df = pd.DataFrame(data_response.data)
            
            print("\n🔍 DETAILED ANALYSIS:")
            print("-" * 50)
            
            # Basic info
            print(f"\nDataframe shape: {df.shape}")
            print(f"Memory usage: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
            
            # Data types
            print("\n📝 Column Data Types:")
            for col, dtype in df.dtypes.items():
                print(f"  • {col}: {dtype}")
            
            # Missing values
            print("\n❓ Missing Values:")
            missing = df.isnull().sum()
            missing_pct = (missing / len(df)) * 100
            for col in missing[missing > 0].index:
                print(f"  • {col}: {missing[col]:,} ({missing_pct[col]:.1f}%)")
            
            # Unique values for categorical columns
            print("\n🏷️ Unique Values (for text/categorical columns):")
            for col in df.columns:
                if df[col].dtype == 'object':
                    try:
                        # Check if column contains lists/arrays
                        first_non_null = df[col].dropna().iloc[0] if not df[col].dropna().empty else None
                        if first_non_null and isinstance(first_non_null, (list, dict)):
                            print(f"  • {col}: Contains complex data (list/dict)")
                            continue
                        
                        unique_count = df[col].nunique()
                        if unique_count < 100:  # Only show if reasonable number
                            print(f"  • {col}: {unique_count} unique values")
                            if unique_count <= 10:
                                top_values = df[col].value_counts().head(5)
                                for val, count in top_values.items():
                                    print(f"      - {val}: {count} ({count/len(df)*100:.1f}%)")
                    except Exception as e:
                        print(f"  • {col}: Could not analyze (contains complex data)")
            
            # Numeric column statistics
            numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
            if len(numeric_cols) > 0:
                print("\n📊 Numeric Column Statistics:")
                for col in numeric_cols:
                    stats = df[col].describe()
                    print(f"\n  {col}:")
                    print(f"    • Min: {stats['min']:.2f}")
                    print(f"    • Max: {stats['max']:.2f}")
                    print(f"    • Mean: {stats['mean']:.2f}")
                    print(f"    • Median: {stats['50%']:.2f}")
                    print(f"    • Std Dev: {stats['std']:.2f}")
            
            # Date columns
            date_cols = []
            for col in df.columns:
                if 'date' in col.lower() or 'created' in col.lower() or 'updated' in col.lower():
                    try:
                        df[col] = pd.to_datetime(df[col])
                        date_cols.append(col)
                    except:
                        pass
            
            if date_cols:
                print("\n📅 Date Range Analysis:")
                for col in date_cols:
                    if df[col].notna().any():
                        print(f"  • {col}:")
                        print(f"      - Earliest: {df[col].min()}")
                        print(f"      - Latest: {df[col].max()}")
                        print(f"      - Range: {(df[col].max() - df[col].min()).days} days")
            
            # Brand analysis
            if 'brand' in df.columns:
                print("\n🏢 Top Brands:")
                top_brands = df['brand'].value_counts().head(15)
                for brand, count in top_brands.items():
                    print(f"  • {brand}: {count} products ({count/len(df)*100:.1f}%)")
            
            # Source domain analysis
            if 'source_domain' in df.columns:
                print("\n🌐 Data Sources:")
                sources = df['source_domain'].value_counts()
                for source, count in sources.items():
                    print(f"  • {source}: {count} products ({count/len(df)*100:.1f}%)")
            
            # Completeness analysis
            print("\n✅ Data Completeness by Field:")
            completeness = ((len(df) - df.isnull().sum()) / len(df) * 100).sort_values(ascending=False)
            for col, pct in completeness.items():
                status = "🟢" if pct >= 90 else "🟡" if pct >= 50 else "🔴"
                print(f"  {status} {col}: {pct:.1f}%")
            
            # Sample data
            print("\n📋 Sample Records (first 3):")
            print("-" * 50)
            sample_df = df.head(3)
            for idx, row in sample_df.iterrows():
                print(f"\nRecord {idx + 1}:")
                for col, val in row.items():
                    if pd.notna(val) and str(val).strip():
                        # Truncate long values
                        val_str = str(val)
                        if len(val_str) > 100:
                            val_str = val_str[:100] + "..."
                        print(f"  • {col}: {val_str}")
            
            return df
        else:
            logger.warning("No data found in food_candidates table")
            return None
            
    except Exception as e:
        logger.error(f"Error analyzing food_candidates table: {e}")
        return None

def main():
    """Main function"""
    print("=" * 80)
    print("🔍 ANALYZING FOOD_CANDIDATES TABLE IN SUPABASE")
    print("=" * 80)
    print()
    
    # Connect to Supabase
    supabase = connect_to_supabase()
    if not supabase:
        print("Failed to connect to Supabase")
        return
    
    # Analyze the table
    df = analyze_food_candidates(supabase)
    
    if df is not None:
        print("\n" + "=" * 80)
        print("✅ Analysis complete!")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("❌ Analysis failed or no data found")
        print("=" * 80)

if __name__ == "__main__":
    main()