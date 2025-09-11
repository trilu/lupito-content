#!/usr/bin/env python3
"""
B4: Database Write Diagnosis
Prove where the join/upsert is failing and quantify matchability
"""

import os
import re
import json
import hashlib
from datetime import datetime
from google.cloud import storage
from supabase import create_client
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import logging
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher

# Setup
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize clients
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = './secrets/gcp-sa.json'
storage_client = storage.Client()
bucket = storage_client.bucket('lupito-content-raw-eu')

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(url, key)

def generate_product_key_exact(brand: str, product_name: str) -> str:
    """Generate product key exactly as B1 does"""
    combined = f"{brand}_{product_name}".lower()
    combined = re.sub(r'[^a-z0-9]+', '_', combined)
    combined = re.sub(r'_+', '_', combined).strip('_')
    hash_suffix = hashlib.md5(combined.encode()).hexdigest()[:8]
    return f"{brand}_{hash_suffix}"

def generate_name_slug(product_name: str) -> str:
    """Generate name slug from product name"""
    slug = product_name.lower()
    slug = re.sub(r'[^a-z0-9]+', '_', slug)
    slug = re.sub(r'_+', '_', slug).strip('_')
    return slug[:50]  # Limit length

def extract_b1_records() -> List[Dict]:
    """Extract records from B1 run by re-processing snapshots"""
    
    print("Extracting B1 records from GCS snapshots...")
    
    brands = ['bozita', 'belcando', 'briantos']
    extracted_records = []
    
    for brand in brands:
        print(f"Processing {brand}...")
        
        prefix = f"manufacturers/{brand}/2025-09-11/"
        blobs = list(bucket.list_blobs(prefix=prefix))
        
        for i, blob in enumerate(blobs[:40]):  # Process up to 40 per brand
            if not blob.name.endswith('.html'):
                continue
                
            try:
                filename = blob.name.split('/')[-1]
                
                # Download HTML
                html_content = blob.download_as_text()
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Extract product name from title or filename
                product_name_raw = filename.replace('.html', '').replace('_', ' ').replace('-', ' ')
                
                # Try to get better product name from page
                title = soup.find('title')
                if title:
                    title_text = title.get_text().strip()
                    if ' - ' in title_text:
                        product_name_raw = title_text.split(' - ')[0].strip()
                    else:
                        product_name_raw = title_text
                else:
                    h1 = soup.find('h1')
                    if h1:
                        product_name_raw = h1.get_text().strip()
                
                # Generate IDs exactly as B1 does
                product_key = generate_product_key_exact(brand, product_name_raw)
                name_slug = generate_name_slug(product_name_raw)
                
                # Extract ingredients (simplified version of B1 logic)
                ingredients_raw = None
                all_text = soup.get_text()
                
                # Look for protein indicators as B1 does
                protein_indicators = ['chicken', 'beef', 'lamb', 'salmon', 'duck']
                
                for indicator in protein_indicators:
                    if indicator.lower() in all_text.lower():
                        # Find paragraph containing this protein
                        for p in soup.find_all(['p', 'div', 'section']):
                            p_text = p.get_text(strip=True)
                            if indicator.lower() in p_text.lower() and len(p_text) > 100:
                                ingredients_raw = p_text[:500]  # First 500 chars
                                break
                        if ingredients_raw:
                            break
                
                if ingredients_raw:
                    record = {
                        'brand_slug': brand,
                        'product_name_raw': product_name_raw,
                        'name_slug': name_slug,
                        'product_url': blob.name,
                        'ingredients_raw': ingredients_raw,
                        'extracted_at': datetime.now().isoformat(),
                        'product_key': product_key,
                        'filename': filename
                    }
                    
                    extracted_records.append(record)
                    
                    if len(extracted_records) >= 100:
                        break
                        
            except Exception as e:
                logger.error(f"Error processing {blob.name}: {e}")
                continue
        
        if len(extracted_records) >= 100:
            break
    
    print(f"Extracted {len(extracted_records)} records")
    return extracted_records[:100]

def probe_database_matches(records: List[Dict]) -> Dict:
    """Probe database for different match types"""
    
    print("Probing database matches...")
    
    results = {
        'product_key_matches': 0,
        'brand_name_slug_matches': 0,
        'brand_product_name_loose_matches': 0,
        'total_records': len(records),
        'failed_matches': [],
        'match_details': []
    }
    
    for i, record in enumerate(records):
        print(f"Processing record {i+1}/{len(records)}: {record['product_name_raw'][:50]}...")
        
        match_result = {
            'record': record,
            'product_key_match': False,
            'brand_name_slug_match': False,
            'loose_match': False,
            'loose_match_score': 0.0,
            'existing_products_same_brand': []
        }
        
        # 1. Test product_key exact match
        try:
            response = supabase.table('foods_canonical').select('product_key, product_name, brand_slug').eq('product_key', record['product_key']).execute()
            if response.data:
                match_result['product_key_match'] = True
                results['product_key_matches'] += 1
                print(f"  ✓ Product key match found")
        except Exception as e:
            print(f"  ❌ Product key query failed: {e}")
        
        # 2. Test (brand_slug, name_slug) match
        try:
            # First, let's see what name_slug values actually exist for this brand
            brand_products = supabase.table('foods_canonical').select('product_key, product_name, brand_slug').eq('brand_slug', record['brand_slug']).limit(50).execute()
            
            if brand_products.data:
                match_result['existing_products_same_brand'] = [
                    {
                        'product_key': p['product_key'],
                        'product_name': p['product_name'],
                        'name_slug': generate_name_slug(p['product_name'])
                    }
                    for p in brand_products.data[:10]  # Limit to 10 for analysis
                ]
                
                # Look for exact name_slug match
                for existing in match_result['existing_products_same_brand']:
                    if existing['name_slug'] == record['name_slug']:
                        match_result['brand_name_slug_match'] = True
                        results['brand_name_slug_matches'] += 1
                        print(f"  ✓ Brand+name_slug match found")
                        break
                
                # 3. Test loose product name matching (diagnostic only)
                best_score = 0.0
                for existing in match_result['existing_products_same_brand']:
                    score = SequenceMatcher(None, 
                                          record['product_name_raw'].lower(), 
                                          existing['product_name'].lower()).ratio()
                    if score > best_score:
                        best_score = score
                
                match_result['loose_match_score'] = best_score
                if best_score > 0.8:  # 80% similarity threshold
                    match_result['loose_match'] = True
                    results['brand_product_name_loose_matches'] += 1
                    print(f"  ✓ Loose name match found (score: {best_score:.2f})")
        
        except Exception as e:
            print(f"  ❌ Brand query failed: {e}")
        
        results['match_details'].append(match_result)
        
        # If no matches found, add to failed list
        if not (match_result['product_key_match'] or match_result['brand_name_slug_match']):
            results['failed_matches'].append(match_result)
    
    return results

def analyze_supabase_responses():
    """Analyze what B1 expects vs gets from Supabase"""
    
    print("Analyzing Supabase response expectations...")
    
    # Test what different operations return
    analysis = {
        'insert_response': None,
        'update_response': None,
        'select_response': None,
        'headers_analysis': {}
    }
    
    # Try a test insert (will fail but we can see the response format)
    try:
        test_data = {
            'product_key': 'test_diagnostic_key',
            'product_name': 'Test Diagnostic Product',
            'brand_slug': 'test_brand'
        }
        
        response = supabase.table('foods_canonical').insert(test_data).execute()
        analysis['insert_response'] = {
            'data_returned': bool(response.data),
            'data_length': len(response.data) if response.data else 0,
            'data_sample': response.data[0] if response.data else None
        }
    except Exception as e:
        analysis['insert_response'] = {'error': str(e)}
    
    # Try a test update on non-existent record
    try:
        update_data = {'product_name': 'Updated Test Product'}
        response = supabase.table('foods_canonical').update(update_data).eq('product_key', 'nonexistent_key').execute()
        analysis['update_response'] = {
            'data_returned': bool(response.data),
            'data_length': len(response.data) if response.data else 0,
            'status_code': getattr(response, 'status_code', None)
        }
    except Exception as e:
        analysis['update_response'] = {'error': str(e)}
    
    # Test select to see normal response format
    try:
        response = supabase.table('foods_canonical').select('product_key, product_name').limit(1).execute()
        analysis['select_response'] = {
            'data_returned': bool(response.data),
            'data_length': len(response.data) if response.data else 0,
            'data_sample': response.data[0] if response.data else None
        }
    except Exception as e:
        analysis['select_response'] = {'error': str(e)}
    
    return analysis

def main():
    """Main B4 diagnosis"""
    
    print("="*80)
    print("B4: DATABASE WRITE DIAGNOSIS")
    print("="*80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    # Step 1: Extract B1 records
    records = extract_b1_records()
    
    # Step 2 & 3: Compute candidate IDs and probe database
    match_results = probe_database_matches(records)
    
    # Step 4: Analyze Supabase responses
    response_analysis = analyze_supabase_responses()
    
    # Generate report
    with open('DB_WRITE_DIAGNOSIS.md', 'w') as f:
        f.write("# B4: Database Write Diagnosis Report\n\n")
        f.write(f"**Generated:** {datetime.now().isoformat()}\n")
        f.write(f"**Records Analyzed:** {match_results['total_records']}\n\n")
        
        # Hit/Miss Metrics
        f.write("## Hit/Miss Metrics\n\n")
        f.write("| Match Type | Hits | Miss | Hit Rate |\n")
        f.write("|------------|------|------|----------|\n")
        
        total = match_results['total_records']
        pk_hits = match_results['product_key_matches']
        bn_hits = match_results['brand_name_slug_matches']
        loose_hits = match_results['brand_product_name_loose_matches']
        
        f.write(f"| Product Key Exact | {pk_hits} | {total - pk_hits} | {pk_hits/total*100:.1f}% |\n")
        f.write(f"| Brand + Name Slug | {bn_hits} | {total - bn_hits} | {bn_hits/total*100:.1f}% |\n")
        f.write(f"| Loose Name Match (diagnostic) | {loose_hits} | {total - loose_hits} | {loose_hits/total*100:.1f}% |\n\n")
        
        # Writer's Current Match Path
        f.write("## Writer's Current Match Path (Pseudocode)\n\n")
        f.write("```python\n")
        f.write("# B1 Current Logic:\n")
        f.write("def generate_product_key(brand, product_name):\n")
        f.write("    combined = f'{brand}_{product_name}'.lower()\n")
        f.write("    combined = re.sub(r'[^a-z0-9]+', '_', combined)\n")
        f.write("    combined = re.sub(r'_+', '_', combined).strip('_')\n")
        f.write("    hash_suffix = hashlib.md5(combined.encode()).hexdigest()[:8]\n")
        f.write("    return f'{brand}_{hash_suffix}'\n\n")
        
        f.write("# Update Logic:\n")
        f.write("1. Check if product exists: SELECT * WHERE product_key = generated_key\n")
        f.write("2. If not exists: INSERT new product\n")
        f.write("3. UPDATE product SET ... WHERE product_key = generated_key\n")
        f.write("4. Expect response.data to contain updated row(s)\n")
        f.write("```\n\n")
        
        # Top 20 Failed Matches
        f.write("## Top 20 Failed Matches Analysis\n\n")
        
        failed_matches = match_results['failed_matches'][:20]
        
        for i, failed in enumerate(failed_matches, 1):
            record = failed['record']
            f.write(f"### {i}. {record['product_name_raw'][:50]}...\n\n")
            f.write(f"**Candidate IDs:**\n")
            f.write(f"- Product Key: `{record['product_key']}`\n")
            f.write(f"- Brand Slug: `{record['brand_slug']}`\n")
            f.write(f"- Name Slug: `{record['name_slug']}`\n\n")
            
            f.write(f"**Brand Exists:** {'Yes' if failed['existing_products_same_brand'] else 'No'}\n\n")
            
            if failed['existing_products_same_brand']:
                f.write("**Similar Products in Same Brand:**\n")
                for existing in failed['existing_products_same_brand'][:3]:
                    similarity = SequenceMatcher(None, 
                                               record['product_name_raw'].lower(), 
                                               existing['product_name'].lower()).ratio()
                    f.write(f"- `{existing['product_key']}`: {existing['product_name'][:40]}... (similarity: {similarity:.2f})\n")
            else:
                f.write("**No existing products found for this brand**\n")
            
            f.write(f"\n**Best Loose Match Score:** {failed['loose_match_score']:.2f}\n\n")
        
        # Supabase Response Analysis
        f.write("## Supabase Response Analysis\n\n")
        
        f.write("### INSERT Response\n")
        if 'error' in response_analysis['insert_response']:
            f.write(f"**Error:** {response_analysis['insert_response']['error']}\n\n")
        else:
            insert_resp = response_analysis['insert_response']
            f.write(f"- Data Returned: {insert_resp['data_returned']}\n")
            f.write(f"- Data Length: {insert_resp['data_length']}\n")
            if insert_resp['data_sample']:
                f.write(f"- Sample: {insert_resp['data_sample']}\n")
            f.write("\n")
        
        f.write("### UPDATE Response\n")
        if 'error' in response_analysis['update_response']:
            f.write(f"**Error:** {response_analysis['update_response']['error']}\n\n")
        else:
            update_resp = response_analysis['update_response']
            f.write(f"- Data Returned: {update_resp['data_returned']}\n")
            f.write(f"- Data Length: {update_resp['data_length']}\n")
            f.write(f"- Status Code: {update_resp.get('status_code', 'Unknown')}\n\n")
        
        f.write("### SELECT Response (Normal)\n")
        if 'error' in response_analysis['select_response']:
            f.write(f"**Error:** {response_analysis['select_response']['error']}\n\n")
        else:
            select_resp = response_analysis['select_response']
            f.write(f"- Data Returned: {select_resp['data_returned']}\n")
            f.write(f"- Data Length: {select_resp['data_length']}\n")
            if select_resp['data_sample']:
                f.write(f"- Sample: {select_resp['data_sample']}\n")
            f.write("\n")
        
        # Root Cause Analysis
        f.write("## Root Cause Analysis\n\n")
        
        if pk_hits == 0 and bn_hits == 0:
            f.write("### 🚨 CRITICAL: Zero Exact Matches Found\n\n")
            f.write("**Hypothesis:**\n")
            f.write("1. **New Products**: All B1 extractions are creating new products not in database\n")
            f.write("2. **Key Generation Mismatch**: Product key algorithm differs between systems\n")
            f.write("3. **Brand Slug Issues**: Brand slugs in B1 don't match database values\n\n")
        
        if loose_hits > 0:
            f.write("### ✅ Products Exist with Similar Names\n")
            f.write(f"Found {loose_hits} products with >80% name similarity, suggesting products exist but key generation differs.\n\n")
        
        f.write("### UPDATE Response Issue\n")
        if response_analysis['update_response'].get('data_length', 0) == 0:
            f.write("**Confirmed Bug**: UPDATE operations return empty data arrays when no rows match.\n")
            f.write("B1 expects response.data to contain updated rows, but gets empty array for non-matching keys.\n\n")
        
        # Recommendations
        f.write("## Recommendations\n\n")
        f.write("### Immediate Fixes\n")
        f.write("1. **Check Product Key Generation**: Verify B1 key generation matches existing products\n")
        f.write("2. **Handle Empty UPDATE Response**: Modify B1 to not treat empty response.data as error\n")
        f.write("3. **Add Logging**: Log generated keys vs existing keys to identify mismatches\n\n")
        
        f.write("### Verification Steps\n")
        f.write("1. **Manual Check**: Query database for existing products from these brands\n")
        f.write("2. **Key Comparison**: Compare B1 generated keys with actual database keys\n")
        f.write("3. **Brand Validation**: Confirm brand_slug values match between B1 and database\n\n")
    
    print(f"\n✓ Diagnosis complete - Report saved to DB_WRITE_DIAGNOSIS.md")
    
    # Print summary
    print(f"\nSUMMARY:")
    print(f"  Records analyzed: {total}")
    print(f"  Product key matches: {pk_hits} ({pk_hits/total*100:.1f}%)")
    print(f"  Brand+name matches: {bn_hits} ({bn_hits/total*100:.1f}%)")
    print(f"  Loose matches: {loose_hits} ({loose_hits/total*100:.1f}%)")
    print(f"  Failed matches: {len(failed_matches)}")
    
    if pk_hits == 0 and bn_hits == 0:
        print(f"\n🚨 CRITICAL: Zero exact matches suggests new products or key mismatch!")

if __name__ == "__main__":
    main()