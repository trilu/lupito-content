#!/usr/bin/env python3
"""
Analyze missing ingredients_tokens for Briantos and Bozita brands
- Query production database for SKUs with NULL/empty ingredients_tokens
- Check GCS snapshots availability for each SKU
- Sample failures and analyze reasons
- Generate comprehensive summary report
"""

import os
import re
import json
from datetime import datetime
from supabase import create_client, Client
from google.cloud import storage
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import logging
from typing import Dict, List, Optional
import langdetect

# Setup
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MissingIngredientsAnalyzer:
    def __init__(self):
        # Database connection
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase: Client = create_client(url, key)
        
        # GCS connection
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = './secrets/gcp-sa.json'
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket('lupito-content-raw-eu')
        
        self.timestamp = datetime.now()
        self.target_brands = ['briantos', 'bozita']
        
        print("="*80)
        print("MISSING INGREDIENTS ANALYSIS: BRIANTOS & BOZITA")
        print("="*80)
        print(f"Timestamp: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Target brands: {', '.join(self.target_brands)}")
        print("="*80)
    
    def get_missing_ingredients_skus(self, brand_slug: str) -> List[Dict]:
        """Get SKUs with NULL or empty ingredients_tokens from foods_published_prod"""
        try:
            # Query for products with missing ingredients_tokens
            response = self.supabase.table('foods_published_prod').select(
                'product_key, product_name, brand_slug, ingredients_tokens, product_url, sources'
            ).eq('brand_slug', brand_slug).execute()
            
            if not response.data:
                logger.warning(f"No data found for {brand_slug}")
                return []
            
            # Filter for missing ingredients
            missing_skus = []
            for item in response.data:
                ingredients_tokens = item.get('ingredients_tokens')
                # Check if ingredients_tokens is None, empty list, or contains only empty/null values
                if (not ingredients_tokens or 
                    (isinstance(ingredients_tokens, list) and len(ingredients_tokens) == 0) or
                    (isinstance(ingredients_tokens, list) and all(not token or token.strip() == '' for token in ingredients_tokens))):
                    missing_skus.append(item)
            
            logger.info(f"Found {len(missing_skus)} SKUs with missing ingredients_tokens for {brand_slug}")
            return missing_skus
            
        except Exception as e:
            logger.error(f"Error fetching missing ingredients SKUs for {brand_slug}: {e}")
            return []
    
    def check_gcs_snapshot_exists(self, brand_slug: str, product_key: str, product_url: str = None) -> Dict:
        """Check if GCS snapshot exists for a given SKU"""
        result = {
            'has_snapshot': False,
            'snapshot_path': None,
            'latest_date': None,
            'file_size': 0,
            'metadata': {}
        }
        
        try:
            # List all date folders for the brand
            prefix = f"manufacturers/{brand_slug}/"
            iterator = self.bucket.list_blobs(prefix=prefix, delimiter='/')
            blobs = list(iterator)
            prefixes = list(iterator.prefixes)
            
            # Find date folders
            dates = []
            for prefix_path in prefixes:
                parts = prefix_path.rstrip('/').split('/')
                if parts:
                    date_part = parts[-1]
                    if re.match(r'\d{4}-\d{2}-\d{2}', date_part):
                        dates.append(date_part)
            
            if not dates:
                return result
            
            # Check latest date folder for snapshots
            latest_date = sorted(dates)[-1]
            result['latest_date'] = latest_date
            
            # Search for HTML files that might match this product
            snapshot_prefix = f"manufacturers/{brand_slug}/{latest_date}/"
            
            # Try to find snapshot by different matching strategies
            potential_matches = []
            
            for blob in self.bucket.list_blobs(prefix=snapshot_prefix):
                if not blob.name.endswith('.html'):
                    continue
                
                filename = blob.name.split('/')[-1]
                
                # Strategy 1: Match by product_key
                if product_key and product_key.lower() in filename.lower():
                    potential_matches.append((blob, 'product_key_match'))
                
                # Strategy 2: Match by URL slug
                if product_url:
                    url_slug = self.extract_product_slug_from_url(product_url)
                    if url_slug and url_slug.lower() in filename.lower():
                        potential_matches.append((blob, 'url_slug_match'))
                
                # Strategy 3: Fuzzy matching based on product name
                # This would require additional logic to match product names
            
            if potential_matches:
                # Take the first match (could be improved with better scoring)
                best_match = potential_matches[0]
                blob = best_match[0]
                
                result['has_snapshot'] = True
                result['snapshot_path'] = blob.name
                result['file_size'] = blob.size
                result['metadata'] = blob.metadata or {}
                
        except Exception as e:
            logger.error(f"Error checking GCS snapshot for {brand_slug}/{product_key}: {e}")
        
        return result
    
    def extract_product_slug_from_url(self, url: str) -> Optional[str]:
        """Extract product slug from URL"""
        if not url:
            return None
        
        # Common patterns for product URLs
        patterns = [
            r'/products?/([^/]+?)(?:\.html)?$',
            r'/([^/]+?)(?:\.html)?$'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def analyze_snapshot_failure(self, brand_slug: str, snapshot_path: str) -> Dict:
        """Analyze why ingredients extraction failed for a snapshot"""
        result = {
            'failure_reason': 'unknown',
            'language_detected': None,
            'selectors_tried': [],
            'text_patterns_found': [],
            'html_structure_issues': []
        }
        
        try:
            # Download the HTML snapshot
            blob = self.bucket.blob(snapshot_path)
            html_content = blob.download_as_text()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 1. Language detection
            page_text = soup.get_text()[:1000]  # First 1000 chars for language detection
            try:
                detected_lang = langdetect.detect(page_text)
                result['language_detected'] = detected_lang
                if detected_lang not in ['en', 'de', 'fr', 'es', 'it']:
                    result['failure_reason'] = 'unsupported_language'
            except:
                result['language_detected'] = 'unknown'
                result['failure_reason'] = 'language_detection_failed'
            
            # 2. Check common selectors
            common_selectors = [
                'div.ingredients',
                'div.composition', 
                'div.product-ingredients',
                'div#ingredients',
                '[itemprop="ingredients"]',
                '.ingredients-list',
                '.product-details'
            ]
            
            selectors_found = []
            for selector in common_selectors:
                elements = soup.select(selector)
                if elements:
                    selectors_found.append(selector)
                    result['selectors_tried'].append({
                        'selector': selector,
                        'found': True,
                        'text_length': len(elements[0].get_text().strip())
                    })
                else:
                    result['selectors_tried'].append({
                        'selector': selector,
                        'found': False
                    })
            
            # 3. Check for text patterns
            text_patterns = [
                r'ingredients?:',
                r'composition:',
                r'contains:',
                r'zutaten:',  # German
                r'inhaltsstoffe:',  # German
                r'ingrédients:',  # French
                r'ingredientes:'  # Spanish
            ]
            
            full_text = soup.get_text().lower()
            patterns_found = []
            for pattern in text_patterns:
                if re.search(pattern, full_text, re.IGNORECASE):
                    patterns_found.append(pattern)
            
            result['text_patterns_found'] = patterns_found
            
            # 4. Determine likely failure reason
            if not patterns_found:
                if result['language_detected'] not in ['en', 'de', 'fr', 'es', 'it']:
                    result['failure_reason'] = 'unsupported_language'
                else:
                    result['failure_reason'] = 'no_ingredients_section_found'
            elif not selectors_found:
                result['failure_reason'] = 'selector_mismatch'
            else:
                result['failure_reason'] = 'extraction_logic_issue'
            
            # 5. Check HTML structure issues
            if len(soup.find_all('script')) > 20:
                result['html_structure_issues'].append('heavily_js_dependent')
            
            if 'javascript' in full_text and 'enable' in full_text:
                result['html_structure_issues'].append('requires_js_execution')
            
            if len(soup.get_text().strip()) < 500:
                result['html_structure_issues'].append('minimal_content')
                
        except Exception as e:
            logger.error(f"Error analyzing snapshot {snapshot_path}: {e}")
            result['failure_reason'] = f'analysis_error: {str(e)}'
        
        return result
    
    def generate_brand_analysis(self, brand_slug: str) -> Dict:
        """Generate complete analysis for a brand"""
        logger.info(f"Analyzing {brand_slug}...")
        
        # Get missing ingredients SKUs
        missing_skus = self.get_missing_ingredients_skus(brand_slug)
        
        analysis = {
            'brand_slug': brand_slug,
            'total_missing': len(missing_skus),
            'with_snapshots': 0,
            'needs_harvest': 0,
            'sample_failures': [],
            'failure_reasons_summary': {},
            'skus_with_snapshots': [],
            'skus_need_harvest': []
        }
        
        if not missing_skus:
            return analysis
        
        # Check GCS snapshots for each SKU
        for sku in missing_skus:
            product_key = sku.get('product_key')
            product_url = sku.get('product_url')
            
            snapshot_check = self.check_gcs_snapshot_exists(brand_slug, product_key, product_url)
            
            if snapshot_check['has_snapshot']:
                analysis['with_snapshots'] += 1
                analysis['skus_with_snapshots'].append({
                    'product_key': product_key,
                    'product_name': sku.get('product_name'),
                    'snapshot_path': snapshot_check['snapshot_path'],
                    'file_size': snapshot_check['file_size']
                })
            else:
                analysis['needs_harvest'] += 1
                analysis['skus_need_harvest'].append({
                    'product_key': product_key,
                    'product_name': sku.get('product_name'),
                    'product_url': product_url
                })
        
        # Sample 2-3 snapshots for failure analysis
        sample_size = min(3, analysis['with_snapshots'])
        sampled_skus = analysis['skus_with_snapshots'][:sample_size]
        
        for sku_info in sampled_skus:
            failure_analysis = self.analyze_snapshot_failure(brand_slug, sku_info['snapshot_path'])
            
            sample_failure = {
                'product_key': sku_info['product_key'],
                'product_name': sku_info['product_name'],
                'snapshot_path': sku_info['snapshot_path'],
                'analysis': failure_analysis
            }
            
            analysis['sample_failures'].append(sample_failure)
            
            # Update failure reasons summary
            reason = failure_analysis['failure_reason']
            analysis['failure_reasons_summary'][reason] = analysis['failure_reasons_summary'].get(reason, 0) + 1
        
        return analysis
    
    def generate_comprehensive_report(self, all_analyses: List[Dict]) -> str:
        """Generate comprehensive summary report"""
        
        report = []
        report.append("# Missing Ingredients Analysis Report")
        report.append(f"**Generated:** {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**Database:** foods_published_prod")
        report.append(f"**GCS Bucket:** lupito-content-raw-eu")
        report.append("")
        
        # Summary section
        report.append("## Summary")
        report.append("")
        
        for analysis in all_analyses:
            brand = analysis['brand_slug'].title()
            total = analysis['total_missing']
            with_snapshots = analysis['with_snapshots']
            needs_harvest = analysis['needs_harvest']
            
            report.append(f"- **{brand}:** {total} SKUs missing ingredients "
                         f"({with_snapshots} have snapshots, {needs_harvest} need harvest)")
        
        report.append("")
        
        # Detailed analysis for each brand
        for analysis in all_analyses:
            brand = analysis['brand_slug'].title()
            report.append(f"## {brand} Detailed Analysis")
            report.append("")
            
            report.append(f"**Total SKUs missing ingredients_tokens:** {analysis['total_missing']}")
            report.append(f"**SKUs with GCS snapshots:** {analysis['with_snapshots']}")
            report.append(f"**SKUs needing harvest:** {analysis['needs_harvest']}")
            report.append("")
            
            # Sample failures
            if analysis['sample_failures']:
                report.append("### Sample Failure Analysis")
                report.append("")
                
                for i, failure in enumerate(analysis['sample_failures'], 1):
                    report.append(f"**Sample {i}:** {failure['product_name']}")
                    report.append(f"- Product Key: `{failure['product_key']}`")
                    report.append(f"- Snapshot: `{failure['snapshot_path']}`")
                    
                    analysis_data = failure['analysis']
                    report.append(f"- **Failure Reason:** {analysis_data['failure_reason']}")
                    report.append(f"- **Language Detected:** {analysis_data['language_detected']}")
                    
                    if analysis_data['text_patterns_found']:
                        report.append(f"- **Text Patterns Found:** {', '.join(analysis_data['text_patterns_found'])}")
                    else:
                        report.append("- **Text Patterns Found:** None")
                    
                    working_selectors = [s['selector'] for s in analysis_data['selectors_tried'] if s['found']]
                    if working_selectors:
                        report.append(f"- **Working Selectors:** {', '.join(working_selectors)}")
                    else:
                        report.append("- **Working Selectors:** None")
                    
                    if analysis_data['html_structure_issues']:
                        report.append(f"- **HTML Issues:** {', '.join(analysis_data['html_structure_issues'])}")
                    
                    report.append("")
            
            # Failure reasons summary
            if analysis['failure_reasons_summary']:
                report.append("### Failure Reasons Summary")
                report.append("")
                for reason, count in sorted(analysis['failure_reasons_summary'].items(), 
                                          key=lambda x: x[1], reverse=True):
                    report.append(f"- {reason}: {count}")
                report.append("")
            
            # SKUs needing harvest (first 10)
            if analysis['skus_need_harvest']:
                report.append("### SKUs Needing Harvest (Sample)")
                report.append("")
                for sku in analysis['skus_need_harvest'][:10]:
                    report.append(f"- {sku['product_name']} (`{sku['product_key']}`)")
                    if sku.get('product_url'):
                        report.append(f"  - URL: {sku['product_url']}")
                
                if len(analysis['skus_need_harvest']) > 10:
                    remaining = len(analysis['skus_need_harvest']) - 10
                    report.append(f"  ... and {remaining} more")
                report.append("")
        
        # Recommendations
        report.append("## Recommendations")
        report.append("")
        
        # Analyze common failure patterns across brands
        all_failures = {}
        for analysis in all_analyses:
            for reason, count in analysis['failure_reasons_summary'].items():
                all_failures[reason] = all_failures.get(reason, 0) + count
        
        top_failure = max(all_failures.items(), key=lambda x: x[1]) if all_failures else None
        
        if top_failure:
            reason, count = top_failure
            if reason == 'selector_mismatch':
                report.append("- **Priority:** Update ingredient extraction selectors for brand-specific HTML structures")
            elif reason == 'unsupported_language':
                report.append("- **Priority:** Add language detection and multi-language ingredient extraction support")
            elif reason == 'no_ingredients_section_found':
                report.append("- **Priority:** Expand text pattern matching to catch edge cases")
            elif reason == 'extraction_logic_issue':
                report.append("- **Priority:** Debug and improve extraction logic for complex HTML structures")
            else:
                report.append(f"- **Priority:** Address {reason} which affects {count} products")
        
        report.append("- Prioritize harvesting missing snapshots for products with URLs")
        report.append("- Consider brand-specific extraction rules for better coverage")
        report.append("- Implement fallback extraction methods for JavaScript-heavy pages")
        report.append("")
        
        return "\n".join(report)

def main():
    analyzer = MissingIngredientsAnalyzer()
    
    all_analyses = []
    
    # Analyze each target brand
    for brand_slug in analyzer.target_brands:
        analysis = analyzer.generate_brand_analysis(brand_slug)
        all_analyses.append(analysis)
    
    # Generate comprehensive report
    report_content = analyzer.generate_comprehensive_report(all_analyses)
    
    # Save report to file
    report_filename = f"MISSING_INGREDIENTS_ANALYSIS_{analyzer.timestamp.strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    # Print summary to console
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    
    for analysis in all_analyses:
        brand = analysis['brand_slug'].title()
        total = analysis['total_missing']
        with_snapshots = analysis['with_snapshots']
        needs_harvest = analysis['needs_harvest']
        
        print(f"{brand}: {total} SKUs missing ingredients ({with_snapshots} have snapshots, {needs_harvest} need harvest)")
    
    print(f"\nDetailed report saved to: {report_filename}")
    
    # Also save as JSON for programmatic access
    json_filename = f"missing_ingredients_data_{analyzer.timestamp.strftime('%Y%m%d_%H%M%S')}.json"
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': analyzer.timestamp.isoformat(),
            'analyses': all_analyses
        }, f, indent=2, ensure_ascii=False)
    
    print(f"Raw data saved to: {json_filename}")

if __name__ == "__main__":
    main()