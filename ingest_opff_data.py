#!/usr/bin/env python3
"""
Open Pet Food Facts (OPFF) data ingestion and enrichment pipeline.
Imports OPFF data dump to enrich food catalog with ingredients, nutrition, and classification.
"""

import os
import re
import json
import hashlib
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dotenv import load_dotenv
from supabase import create_client
import logging
import gzip
from urllib.parse import urlparse

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OPFFIngester:
    def __init__(self):
        load_dotenv()
        self.supabase = self._connect_supabase()
        self.reports_dir = Path("reports/OPFF")
        self.data_dir = Path("data/opff")
        self.reports_dir.mkdir(exist_ok=True, parents=True)
        self.data_dir.mkdir(exist_ok=True, parents=True)
        
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.import_stats = {}
        
        # OPFF data URLs
        self.opff_urls = {
            'csv': 'https://world.openpetfoodfacts.org/data/en.openpetfoodfacts.org.products.csv.gz',
            'jsonl': 'https://world.openpetfoodfacts.org/data/openpetfoodfacts-products.jsonl.gz',
            'mongodb': 'https://world.openpetfoodfacts.org/data/openpetfoodfacts-mongodbdump.tar.gz'
        }
        
    def _connect_supabase(self):
        """Connect to Supabase"""
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not url or not key:
            raise ValueError("Missing Supabase credentials")
        
        logger.info("Connected to Supabase")
        return create_client(url, key)
    
    # ========== 1. DOWNLOAD AND IMPORT OPFF DATA ==========
    def download_opff_dump(self, format='jsonl'):
        """Download the OPFF data dump."""
        logger.info(f"Downloading OPFF {format} dump...")
        
        url = self.opff_urls.get(format)
        if not url:
            raise ValueError(f"Unknown format: {format}")
        
        filename = os.path.basename(urlparse(url).path)
        filepath = self.data_dir / filename
        
        # Download if not exists or older than 7 days
        if filepath.exists():
            age_days = (datetime.now() - datetime.fromtimestamp(filepath.stat().st_mtime)).days
            if age_days < 7:
                logger.info(f"Using cached dump from {age_days} days ago")
                self.import_stats['dump_cached'] = True
                self.import_stats['dump_age_days'] = age_days
                return filepath
        
        # Download with progress
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        block_size = 8192
        downloaded = 0
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(block_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        progress = downloaded / total_size * 100
                        if downloaded % (block_size * 100) == 0:  # Log every 100 blocks
                            logger.info(f"Download progress: {progress:.1f}%")
        
        # Calculate SHA256
        sha256 = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        
        self.import_stats['dump_url'] = url
        self.import_stats['dump_file'] = str(filepath)
        self.import_stats['dump_size_mb'] = os.path.getsize(filepath) / (1024 * 1024)
        self.import_stats['dump_sha256'] = sha256.hexdigest()
        self.import_stats['dump_fetched_at'] = self.timestamp
        self.import_stats['dump_cached'] = False
        
        logger.info(f"✓ Downloaded {self.import_stats['dump_size_mb']:.1f} MB")
        logger.info(f"  SHA256: {self.import_stats['dump_sha256']}")
        
        return filepath
    
    # ========== 2. NORMALIZE OPFF DATA ==========
    def normalize_opff_data(self, filepath):
        """Parse and normalize OPFF data to our schema."""
        logger.info("Normalizing OPFF data...")
        
        normalized_products = []
        total_products = 0
        dog_products = 0
        cat_products = 0
        other_products = 0
        languages = {}
        
        # Read compressed JSONL file
        with gzip.open(filepath, 'rt', encoding='utf-8') as f:
            for line_num, line in enumerate(f):
                if line_num >= 10000:  # Limit for testing
                    break
                
                try:
                    product = json.loads(line)
                    total_products += 1
                    
                    # Skip if not pet food
                    categories = product.get('categories_tags', [])
                    if not any('pet' in cat or 'animal' in cat for cat in categories):
                        continue
                    
                    # Categorize by pet type
                    if any('dog' in cat for cat in categories):
                        dog_products += 1
                    elif any('cat' in cat for cat in categories):
                        cat_products += 1
                    else:
                        other_products += 1
                    
                    # Track languages
                    lang = product.get('lang', 'unknown')
                    languages[lang] = languages.get(lang, 0) + 1
                    
                    # Normalize to our schema
                    normalized = self._normalize_product(product)
                    if normalized:
                        normalized_products.append(normalized)
                    
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    if line_num < 10:  # Log first few errors
                        logger.warning(f"Error parsing line {line_num}: {e}")
        
        # Convert to DataFrame
        opff_df = pd.DataFrame(normalized_products)
        
        # Store statistics
        self.import_stats['total_products'] = total_products
        self.import_stats['dog_products'] = dog_products
        self.import_stats['cat_products'] = cat_products
        self.import_stats['other_products'] = other_products
        self.import_stats['normalized_count'] = len(opff_df)
        self.import_stats['languages'] = languages
        
        logger.info(f"✓ Normalized {len(opff_df):,} products from {total_products:,} total")
        logger.info(f"  Dog: {dog_products:,}, Cat: {cat_products:,}, Other: {other_products:,}")
        
        return opff_df
    
    def _normalize_product(self, product):
        """Normalize a single OPFF product to our schema."""
        try:
            # Extract basic fields
            normalized = {
                'barcode': product.get('code', ''),
                'brand': product.get('brands', ''),
                'product_name': product.get('product_name', ''),
                'quantity': product.get('quantity', ''),
                'categories_tags': product.get('categories_tags', []),
                'labels_tags': product.get('labels_tags', []),
                'ingredients_text': product.get('ingredients_text', ''),
                'ingredients_tags': product.get('ingredients_tags', []),
                'ingredients_analysis_tags': product.get('ingredients_analysis_tags', []),
                'lang': product.get('lang', 'en'),
                'images': []
            }
            
            # Extract nutrition
            nutriments = product.get('nutriments', {})
            normalized['kcal_per_100g'] = nutriments.get('energy-kcal_100g')
            normalized['protein_percent'] = nutriments.get('proteins_100g')
            normalized['fat_percent'] = nutriments.get('fat_100g')
            normalized['fiber_percent'] = nutriments.get('fiber_100g')
            normalized['ash_percent'] = nutriments.get('ash_100g')
            normalized['moisture_percent'] = nutriments.get('moisture_100g')
            
            # Extract images
            if product.get('image_url'):
                normalized['images'].append(product['image_url'])
            if product.get('image_front_url'):
                normalized['images'].append(product['image_front_url'])
            if product.get('image_ingredients_url'):
                normalized['images'].append(product['image_ingredients_url'])
            if product.get('image_nutrition_url'):
                normalized['images'].append(product['image_nutrition_url'])
            
            # Parse weight from quantity
            normalized['weight_kg'] = self._parse_weight(normalized['quantity'])
            
            # Derive form and life_stage
            normalized['form'] = self._derive_form(product)
            normalized['life_stage'] = self._derive_life_stage(product)
            
            # Tokenize ingredients
            normalized['ingredients_tokens'] = self._tokenize_ingredients(
                normalized['ingredients_text'],
                normalized['ingredients_tags']
            )
            
            # Generate allergen groups
            normalized['allergen_groups'] = self._detect_allergens(normalized['ingredients_tokens'])
            
            # Set provenance
            normalized['source'] = 'OPFF'
            normalized['fetched_at'] = self.timestamp
            normalized['confidence'] = 0.8  # Default confidence for OPFF data
            
            return normalized
            
        except Exception as e:
            return None
    
    def _parse_weight(self, quantity_str):
        """Extract weight in kg from quantity string."""
        if not quantity_str:
            return None
        
        quantity_str = str(quantity_str).lower()
        
        # Pattern: number + unit
        match = re.search(r'(\d+(?:[.,]\d+)?)\s*(kg|g|l|ml)', quantity_str)
        if match:
            value = float(match.group(1).replace(',', '.'))
            unit = match.group(2)
            
            if unit in ['g', 'ml']:
                return value / 1000
            elif unit in ['kg', 'l']:
                return value
        
        return None
    
    def _derive_form(self, product):
        """Derive form from OPFF product data."""
        # Check categories
        categories = ' '.join(product.get('categories_tags', [])).lower()
        name = product.get('product_name', '').lower()
        
        if any(term in categories + name for term in ['dry', 'kibble', 'croquettes', 'pellet']):
            return 'dry'
        elif any(term in categories + name for term in ['wet', 'can', 'pouch', 'pate', 'chunks', 'gravy']):
            return 'wet'
        elif any(term in categories + name for term in ['freeze-dried', 'freeze dried', 'lyophilized']):
            return 'freeze_dried'
        elif any(term in categories + name for term in ['raw', 'barf', 'frozen']):
            return 'raw'
        
        return None
    
    def _derive_life_stage(self, product):
        """Derive life stage from OPFF product data."""
        # Check categories and labels
        tags = ' '.join(product.get('categories_tags', []) + product.get('labels_tags', [])).lower()
        name = product.get('product_name', '').lower()
        
        if any(term in tags + name for term in ['puppy', 'junior', 'growth', 'kitten']):
            return 'puppy'
        elif any(term in tags + name for term in ['senior', 'mature', '7+', 'aged']):
            return 'senior'
        elif any(term in tags + name for term in ['adult', 'maintenance']):
            return 'adult'
        elif any(term in tags + name for term in ['all-life-stages', 'all ages', 'complete']):
            return 'all'
        
        return None
    
    def _tokenize_ingredients(self, ingredients_text, ingredients_tags):
        """Extract ingredient tokens from text and tags."""
        tokens = set()
        
        # From ingredients text
        if ingredients_text:
            # Split by common separators
            text_tokens = re.split(r'[,;()]', ingredients_text.lower())
            for token in text_tokens:
                token = token.strip()
                # Remove percentages and numbers
                token = re.sub(r'\d+(?:\.\d+)?%?', '', token).strip()
                if token and len(token) > 2:
                    tokens.add(token)
        
        # From ingredients tags (already parsed by OPFF)
        for tag in ingredients_tags:
            # Remove language prefix (e.g., "en:chicken" -> "chicken")
            if ':' in tag:
                tag = tag.split(':', 1)[1]
            tokens.add(tag.replace('-', ' '))
        
        return list(tokens)
    
    def _detect_allergens(self, ingredients_tokens):
        """Detect allergen groups from ingredients."""
        if not ingredients_tokens:
            return []
        
        allergen_map = {
            'chicken': ['chicken', 'poultry', 'hen', 'fowl'],
            'beef': ['beef', 'bovine', 'cow', 'veal'],
            'fish_salmon': ['fish', 'salmon', 'trout', 'tuna', 'herring', 'mackerel', 'sardine'],
            'lamb': ['lamb', 'mutton', 'sheep'],
            'turkey': ['turkey'],
            'duck': ['duck'],
            'pork': ['pork', 'ham', 'bacon', 'swine'],
            'egg': ['egg', 'eggs'],
            'dairy': ['milk', 'cheese', 'whey', 'casein', 'lactose', 'yogurt'],
            'grain_gluten': ['wheat', 'barley', 'rye', 'oats', 'gluten', 'cereal'],
            'corn_maize': ['corn', 'maize'],
            'soy': ['soy', 'soya', 'soybean'],
            'pea_legume': ['pea', 'lentil', 'chickpea', 'bean', 'legume'],
            'potato': ['potato', 'sweet potato'],
            'rice': ['rice'],
            'novel_protein': ['venison', 'rabbit', 'kangaroo', 'buffalo', 'bison', 'ostrich']
        }
        
        detected = set()
        tokens_lower = [str(t).lower() for t in ingredients_tokens]
        
        for allergen_group, keywords in allergen_map.items():
            for keyword in keywords:
                if any(keyword in token for token in tokens_lower):
                    detected.add(allergen_group)
                    break
        
        return list(detected)
    
    # ========== 3. CREATE ENRICHMENT TABLES ==========
    def create_enrichment_tables(self, opff_df):
        """Create enrichment tables from OPFF data."""
        logger.info("Creating OPFF enrichment tables...")
        
        # Match with existing products
        products = self.supabase.table('foods_published').select('*').execute()
        existing_df = pd.DataFrame(products.data)
        
        if existing_df.empty:
            logger.warning("No existing products to enrich")
            return pd.DataFrame()
        
        # Match by brand and product name (fuzzy matching would be better)
        enrichments = []
        matches = 0
        
        for _, opff_product in opff_df.iterrows():
            # Try to find matching product
            brand = opff_product.get('brand', '').lower()
            name = opff_product.get('product_name', '').lower()
            
            if not brand or not name:
                continue
            
            # Find matches
            brand_matches = existing_df[existing_df['brand'].str.lower() == brand]
            if len(brand_matches) > 0:
                # Try exact name match first
                name_matches = brand_matches[brand_matches['product_name'].str.lower().str.contains(name[:20], na=False)]
                
                if len(name_matches) > 0:
                    # Take first match
                    match = name_matches.iloc[0]
                    matches += 1
                    
                    # Create enrichment record
                    enrichment = {
                        'product_key': match['product_key'],
                        'opff_barcode': opff_product.get('barcode'),
                        'opff_confidence': opff_product.get('confidence', 0.8)
                    }
                    
                    # Add nutrition if available
                    if pd.notna(opff_product.get('kcal_per_100g')):
                        enrichment['kcal_per_100g'] = opff_product['kcal_per_100g']
                        enrichment['kcal_from'] = 'OPFF'
                    
                    if pd.notna(opff_product.get('protein_percent')):
                        enrichment['protein_percent'] = opff_product['protein_percent']
                        enrichment['fat_percent'] = opff_product.get('fat_percent')
                        enrichment['fiber_percent'] = opff_product.get('fiber_percent')
                        enrichment['macros_from'] = 'OPFF'
                    
                    # Add form/life_stage if available
                    if pd.notna(opff_product.get('form')):
                        enrichment['form'] = opff_product['form']
                        enrichment['form_from'] = 'OPFF'
                    
                    if pd.notna(opff_product.get('life_stage')):
                        enrichment['life_stage'] = opff_product['life_stage']
                        enrichment['life_stage_from'] = 'OPFF'
                    
                    # Add ingredients/allergens
                    if opff_product.get('ingredients_tokens'):
                        enrichment['ingredients_tokens'] = json.dumps(opff_product['ingredients_tokens'])
                        enrichment['ingredients_from'] = 'OPFF'
                        enrichment['ingredients_unknown'] = False
                    
                    if opff_product.get('allergen_groups'):
                        enrichment['allergen_groups'] = json.dumps(opff_product['allergen_groups'])
                        enrichment['allergen_groups_from'] = 'OPFF'
                    
                    # Add images
                    if opff_product.get('images'):
                        enrichment['images'] = json.dumps(opff_product['images'])
                        enrichment['images_from'] = 'OPFF'
                    
                    enrichment['fetched_at'] = self.timestamp
                    enrichment['source'] = 'OPFF'
                    
                    enrichments.append(enrichment)
        
        enrichment_df = pd.DataFrame(enrichments)
        
        self.import_stats['products_matched'] = matches
        self.import_stats['match_rate'] = (matches / len(opff_df) * 100) if len(opff_df) > 0 else 0
        
        logger.info(f"✓ Created enrichments for {matches:,} products ({self.import_stats['match_rate']:.1f}% match rate)")
        
        return enrichment_df
    
    # ========== 4. CALCULATE COVERAGE DELTA ==========
    def calculate_coverage_delta(self, enrichment_df):
        """Calculate coverage improvements from OPFF enrichment."""
        logger.info("Calculating coverage delta...")
        
        # Get current coverage
        products = self.supabase.table('foods_published').select('*').execute()
        current_df = pd.DataFrame(products.data)
        
        if current_df.empty or enrichment_df.empty:
            return {}
        
        total = len(current_df)
        
        # Current coverage
        coverage_before = {
            'kcal_per_100g': (current_df['kcal_per_100g'].notna() & (current_df['kcal_per_100g'] > 0)).sum() / total * 100,
            'protein_percent': (current_df['protein_percent'].notna() & (current_df['protein_percent'] > 0)).sum() / total * 100,
            'ingredients_tokens': (current_df['ingredients_tokens'].notna() & (current_df['ingredients_tokens'] != '')).sum() / total * 100,
            'form': (current_df['form'].notna() & (current_df['form'] != '')).sum() / total * 100,
            'life_stage': (current_df['life_stage'].notna() & (current_df['life_stage'] != '')).sum() / total * 100
        }
        
        # Simulate after enrichment
        enriched_products = set(enrichment_df['product_key'])
        
        coverage_after = {}
        for field in coverage_before.keys():
            # Count products that have the field after enrichment
            has_field_before = (current_df[field].notna() & (current_df[field] != '')).sum()
            
            # Add products that gain the field from OPFF
            if field in enrichment_df.columns:
                gains_field = enrichment_df[
                    enrichment_df[field].notna() & 
                    ~current_df.set_index('product_key')[field].reindex(enrichment_df['product_key']).notna()
                ]['product_key'].nunique()
            else:
                gains_field = 0
            
            has_field_after = has_field_before + gains_field
            coverage_after[field] = has_field_after / total * 100
        
        # Calculate deltas
        coverage_delta = {
            field: coverage_after[field] - coverage_before[field]
            for field in coverage_before.keys()
        }
        
        self.import_stats['coverage_before'] = coverage_before
        self.import_stats['coverage_after'] = coverage_after
        self.import_stats['coverage_delta'] = coverage_delta
        
        logger.info("Coverage improvements:")
        for field, delta in coverage_delta.items():
            logger.info(f"  {field}: {coverage_before[field]:.1f}% → {coverage_after[field]:.1f}% ({delta:+.1f}pp)")
        
        return coverage_delta
    
    # ========== 5. GENERATE REPORTS ==========
    def generate_reports(self, opff_df, enrichment_df, coverage_delta):
        """Generate comprehensive OPFF reports."""
        logger.info("Generating OPFF reports...")
        
        # Report 1: Import summary
        import_report = f"""# OPFF IMPORT REPORT
Generated: {self.timestamp}

## Data Source
- **URL:** {self.import_stats.get('dump_url', 'N/A')}
- **SHA256:** {self.import_stats.get('dump_sha256', 'N/A')}
- **File Size:** {self.import_stats.get('dump_size_mb', 0):.1f} MB
- **Fetched At:** {self.import_stats.get('dump_fetched_at', 'N/A')}

## Import Statistics
- **Total Products in Dump:** {self.import_stats.get('total_products', 0):,}
- **Dog Products:** {self.import_stats.get('dog_products', 0):,} ({self.import_stats.get('dog_products', 0) / max(self.import_stats.get('total_products', 1), 1) * 100:.1f}%)
- **Cat Products:** {self.import_stats.get('cat_products', 0):,} ({self.import_stats.get('cat_products', 0) / max(self.import_stats.get('total_products', 1), 1) * 100:.1f}%)
- **Other Products:** {self.import_stats.get('other_products', 0):,}
- **Normalized Products:** {self.import_stats.get('normalized_count', 0):,}
- **Products Matched:** {self.import_stats.get('products_matched', 0):,}
- **Match Rate:** {self.import_stats.get('match_rate', 0):.1f}%

## Language Distribution
"""
        languages = self.import_stats.get('languages', {})
        for lang, count in sorted(languages.items(), key=lambda x: x[1], reverse=True)[:10]:
            import_report += f"- {lang}: {count:,}\n"
        
        import_report += """
## Field Coverage (from OPFF data)
"""
        if not opff_df.empty:
            for field in ['kcal_per_100g', 'protein_percent', 'ingredients_tokens', 'form', 'life_stage']:
                if field in opff_df.columns:
                    coverage = opff_df[field].notna().sum() / len(opff_df) * 100
                    import_report += f"- {field}: {coverage:.1f}%\n"
        
        import_report += """
## Attribution
This data is sourced from Open Pet Food Facts (https://world.openpetfoodfacts.org)
Licensed under Open Database License (ODbL) v1.0
"""
        
        with open(self.reports_dir / "OPFF_IMPORT.md", 'w') as f:
            f.write(import_report)
        
        # Report 2: Coverage Delta
        delta_report = f"""# OPFF COVERAGE DELTA REPORT
Generated: {self.timestamp}

## Coverage Improvements

| Field | Before | After | Delta | Status |
|-------|--------|-------|-------|--------|
"""
        
        coverage_before = self.import_stats.get('coverage_before', {})
        coverage_after = self.import_stats.get('coverage_after', {})
        
        for field in ['kcal_per_100g', 'protein_percent', 'ingredients_tokens', 'form', 'life_stage']:
            before = coverage_before.get(field, 0)
            after = coverage_after.get(field, 0)
            delta = coverage_delta.get(field, 0)
            status = '✅' if delta > 0 else '➖'
            delta_report += f"| {field} | {before:.1f}% | {after:.1f}% | {delta:+.1f}pp | {status} |\n"
        
        delta_report += """
## Images Coverage
"""
        if 'images' in enrichment_df.columns:
            with_images = enrichment_df['images'].notna().sum()
            delta_report += f"- Products with images from OPFF: {with_images:,}\n"
        
        with open(self.reports_dir / "OPFF_COVERAGE_DELTA.md", 'w') as f:
            f.write(delta_report)
        
        # Report 3: Brand Impact
        if not enrichment_df.empty:
            brand_impact = []
            
            # Group enrichments by brand
            products = self.supabase.table('foods_published').select('product_key,brand').execute()
            products_df = pd.DataFrame(products.data)
            
            if not products_df.empty:
                enriched_with_brand = enrichment_df.merge(products_df, on='product_key')
                
                for brand in enriched_with_brand['brand'].unique():
                    brand_enrichments = enriched_with_brand[enriched_with_brand['brand'] == brand]
                    
                    brand_impact.append({
                        'brand': brand,
                        'products_enriched': len(brand_enrichments),
                        'new_kcal': brand_enrichments['kcal_per_100g'].notna().sum() if 'kcal_per_100g' in brand_enrichments.columns else 0,
                        'new_ingredients': brand_enrichments['ingredients_tokens'].notna().sum() if 'ingredients_tokens' in brand_enrichments.columns else 0,
                        'new_form': brand_enrichments['form'].notna().sum() if 'form' in brand_enrichments.columns else 0,
                        'new_life_stage': brand_enrichments['life_stage'].notna().sum() if 'life_stage' in brand_enrichments.columns else 0
                    })
                
                brand_impact_df = pd.DataFrame(brand_impact).sort_values('products_enriched', ascending=False).head(20)
                
                impact_report = f"""# OPFF BRAND IMPACT REPORT
Generated: {self.timestamp}

## Top 20 Brands Enriched by OPFF

| Brand | Products | New Kcal | New Ingredients | New Form | New Life Stage |
|-------|----------|----------|-----------------|----------|----------------|
"""
                for _, row in brand_impact_df.iterrows():
                    impact_report += f"| {row['brand']} | {row['products_enriched']} | {row['new_kcal']} | {row['new_ingredients']} | {row['new_form']} | {row['new_life_stage']} |\n"
                
                with open(self.reports_dir / "OPFF_BRAND_IMPACT.md", 'w') as f:
                    f.write(impact_report)
        
        logger.info("✓ Generated OPFF reports")
    
    # ========== 6. VALIDATE ACCEPTANCE GATES ==========
    def validate_acceptance_gates(self, coverage_delta):
        """Check if OPFF enrichment meets acceptance criteria."""
        logger.info("Validating acceptance gates...")
        
        gates = {
            'kcal_lift': {
                'target': 5,
                'actual': coverage_delta.get('kcal_per_100g', 0),
                'passed': coverage_delta.get('kcal_per_100g', 0) >= 5
            },
            'ingredients_lift': {
                'target': 15,
                'actual': coverage_delta.get('ingredients_tokens', 0),
                'passed': coverage_delta.get('ingredients_tokens', 0) >= 15
            },
            'form_lift': {
                'target': 15,
                'actual': coverage_delta.get('form', 0),
                'passed': coverage_delta.get('form', 0) >= 15
            },
            'life_stage_lift': {
                'target': 15,
                'actual': coverage_delta.get('life_stage', 0),
                'passed': coverage_delta.get('life_stage', 0) >= 15
            }
        }
        
        all_passed = all(gate['passed'] for gate in gates.values())
        
        # Generate acceptance report
        acceptance_report = f"""# OPFF ACCEPTANCE GATES
Generated: {self.timestamp}

## Gate Results

| Gate | Target | Actual | Status |
|------|--------|--------|--------|
"""
        
        for name, gate in gates.items():
            status = '✅ PASS' if gate['passed'] else '❌ FAIL'
            acceptance_report += f"| {name} | ≥{gate['target']}pp | {gate['actual']:.1f}pp | {status} |\n"
        
        acceptance_report += f"""
## Overall Status: {'✅ PASSED - Ready to include OPFF in production' if all_passed else '❌ FAILED - OPFF enrichment insufficient'}

## Attribution
Open Pet Food Facts data is licensed under ODbL v1.0
https://world.openpetfoodfacts.org
"""
        
        with open(self.reports_dir / "OPFF_ACCEPTANCE.md", 'w') as f:
            f.write(acceptance_report)
        
        logger.info(f"Acceptance gates: {'PASSED' if all_passed else 'FAILED'}")
        
        return all_passed
    
    # ========== MAIN PIPELINE ==========
    def run_opff_pipeline(self):
        """Execute the complete OPFF ingestion pipeline."""
        logger.info("=" * 60)
        logger.info("STARTING OPFF INGESTION PIPELINE")
        logger.info("=" * 60)
        
        try:
            # Step 1: Download OPFF dump
            dump_file = self.download_opff_dump('jsonl')
            
            # Step 2: Normalize OPFF data
            opff_df = self.normalize_opff_data(dump_file)
            
            # Step 3: Create enrichment tables
            enrichment_df = self.create_enrichment_tables(opff_df)
            
            # Step 4: Calculate coverage delta
            coverage_delta = self.calculate_coverage_delta(enrichment_df)
            
            # Step 5: Generate reports
            self.generate_reports(opff_df, enrichment_df, coverage_delta)
            
            # Step 6: Validate acceptance gates
            gates_passed = self.validate_acceptance_gates(coverage_delta)
            
            # Print summary
            logger.info("=" * 60)
            logger.info("OPFF PIPELINE COMPLETE")
            logger.info("=" * 60)
            
            print("\n📊 OPFF INGESTION SUMMARY")
            print("-" * 40)
            print(f"Products in dump: {self.import_stats.get('total_products', 0):,}")
            print(f"Products matched: {self.import_stats.get('products_matched', 0):,}")
            print(f"Match rate: {self.import_stats.get('match_rate', 0):.1f}%")
            
            print("\n📈 Coverage Improvements:")
            for field, delta in coverage_delta.items():
                print(f"  {field}: {delta:+.1f}pp")
            
            print(f"\n{'✅ ACCEPTANCE GATES PASSED' if gates_passed else '❌ ACCEPTANCE GATES FAILED'}")
            
            if gates_passed:
                print("\nOPFF enrichment ready for production integration")
                print("Execute reconciliation to include in foods_published_v2")
            else:
                print("\nOPFF enrichment insufficient for production")
                print("Consider alternative matching strategies or data sources")
            
            print("\n📄 Reports generated in /reports/OPFF/:")
            print("- OPFF_IMPORT.md")
            print("- OPFF_COVERAGE_DELTA.md")
            print("- OPFF_BRAND_IMPACT.md")
            print("- OPFF_ACCEPTANCE.md")
            
            return gates_passed
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    ingester = OPFFIngester()
    success = ingester.run_opff_pipeline()