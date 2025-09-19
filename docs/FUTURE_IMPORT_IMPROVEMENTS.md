# Future Import Improvements Plan

## Executive Summary

This document outlines improvements to the product import process to automatically detect and handle size/pack variants, preventing future duplication while preserving important product distinctions (life stage and breed size).

## Current Import Issues

### Problems Identified
1. **No variant detection** - Size/pack variants imported as separate products
2. **Duplicate product keys** - Same product with different sizes creates conflicts
3. **Inconsistent normalization** - Brand and product names not standardized
4. **No consolidation logic** - Missing ingredients/nutrition not pulled from variants
5. **URL variants** - `?activeVariant=` parameters treated as different products

### Impact
- Database contains ~20% duplicates (1,828 variants)
- Inaccurate coverage metrics
- Confusing search results
- Wasted storage and processing

## Proposed Import Pipeline Architecture

```
Raw Product Data
    ↓
[1. Pre-Processing]
    ├── URL Normalization
    ├── Brand Standardization
    └── Name Cleaning
    ↓
[2. Variant Detection]
    ├── Check Existing Products
    ├── Identify Variant Type
    └── Group Related Products
    ↓
[3. Decision Logic]
    ├── New Product → Import
    ├── Size/Pack Variant → Variants Table
    └── Life/Breed Variant → Import
    ↓
[4. Data Consolidation]
    ├── Merge Ingredients
    ├── Merge Nutrition
    └── Update Parent
    ↓
[5. Database Operations]
    ├── Insert/Update Main Table
    └── Insert Variants Table
```

## Implementation Components

### 1. Enhanced Import Class

```python
class SmartProductImporter:
    """
    Intelligent product importer with variant detection
    """
    
    def __init__(self):
        self.variant_detector = VariantDetector()
        self.data_consolidator = DataConsolidator()
        self.brand_normalizer = BrandNormalizer()
        
    def import_product(self, product_data):
        """
        Smart import with variant handling
        """
        # 1. Pre-process
        product = self.preprocess(product_data)
        
        # 2. Check for variants
        variant_info = self.variant_detector.check_variant(product)
        
        if variant_info['is_variant']:
            if variant_info['type'] in ['size', 'pack']:
                # Add to variants table
                self.add_to_variants(product, variant_info['parent'])
                # Consolidate data to parent
                self.consolidate_to_parent(product, variant_info['parent'])
            else:
                # Life stage/breed - import normally
                self.import_as_new(product)
        else:
            # Check if this could be parent of existing variants
            self.check_and_consolidate_existing(product)
            self.import_as_new(product)
```

### 2. Variant Detection Module

```python
class VariantDetector:
    """
    Detects if a product is a variant of existing product
    """
    
    def __init__(self):
        # Compile patterns once for performance
        self.size_pattern = re.compile(r'\b\d+(?:\.\d+)?\s*(?:kg|g|lb|oz|ml|l)\b', re.I)
        self.pack_pattern = re.compile(r'\b\d+\s*x\s*\d+', re.I)
        self.life_pattern = re.compile(r'\b(?:puppy|junior|adult|senior)\b', re.I)
        self.breed_pattern = re.compile(r'\b(?:small|medium|large|mini|maxi)\b', re.I)
        
    def check_variant(self, product):
        """
        Check if product is variant of existing product
        """
        # Normalize for comparison
        base_name = self.get_base_name(product['product_name'])
        
        # Look for existing products with same base
        existing = self.find_similar_products(product['brand'], base_name)
        
        if existing:
            variant_type = self.determine_variant_type(product, existing[0])
            return {
                'is_variant': True,
                'type': variant_type,
                'parent': existing[0],
                'confidence': self.calculate_confidence(product, existing[0])
            }
        
        return {'is_variant': False}
    
    def get_base_name(self, product_name):
        """
        Get base name without size/pack indicators
        """
        name = self.size_pattern.sub('', product_name)
        name = self.pack_pattern.sub('', name)
        name = re.sub(r'\s+', ' ', name).strip()
        return name
```

### 3. Data Consolidation Module

```python
class DataConsolidator:
    """
    Consolidates data from variants to parent products
    """
    
    def consolidate(self, parent, variant):
        """
        Merge variant data into parent
        """
        updates = {}
        
        # Take ingredients if parent lacks them
        if not parent.get('ingredients_raw') and variant.get('ingredients_raw'):
            updates['ingredients_raw'] = variant['ingredients_raw']
            updates['ingredients_source'] = 'consolidated'
            
        # Take nutrition if parent lacks it
        if not parent.get('protein_percent') and variant.get('protein_percent'):
            for field in ['protein_percent', 'fat_percent', 'fiber_percent', 
                         'ash_percent', 'moisture_percent']:
                if variant.get(field):
                    updates[field] = variant[field]
            updates['macros_source'] = 'consolidated'
        
        # Keep best product URL (shortest, no variants)
        if '?activeVariant=' not in parent.get('product_url', ''):
            updates['product_url'] = parent['product_url']
        elif variant.get('product_url') and '?activeVariant=' not in variant['product_url']:
            updates['product_url'] = variant['product_url']
        
        return updates
```

### 4. Brand Normalization Module

```python
class BrandNormalizer:
    """
    Standardizes brand names across imports
    """
    
    # Master brand mapping
    BRAND_MAPPINGS = {
        'royal canin': ['royalcanin', 'royal-canin', 'royal_canin'],
        'hills': ['hills', "hill's", 'hills science plan', 'hills-science-plan'],
        'purina': ['purina', 'purina-pro-plan', 'purina pro plan'],
        'advance': ['advance', 'advance-veterinary-diets', 'advance veterinary'],
        # ... more mappings
    }
    
    def normalize(self, brand_name):
        """
        Normalize brand name to standard form
        """
        if not brand_name:
            return None
            
        clean = brand_name.lower().strip()
        clean = re.sub(r'[^\w\s-]', '', clean)
        clean = re.sub(r'\s+', ' ', clean)
        
        # Check mappings
        for standard, variants in self.BRAND_MAPPINGS.items():
            if clean in variants or clean == standard:
                return standard.title()
        
        # If no mapping, return cleaned version
        return clean.title()
```

### 5. Import Configuration

```python
# config/import_config.py

IMPORT_CONFIG = {
    'variant_detection': {
        'enabled': True,
        'types_to_consolidate': ['size', 'pack'],
        'types_to_keep': ['life_stage', 'breed_size'],
        'confidence_threshold': 0.8
    },
    
    'normalization': {
        'normalize_brands': True,
        'normalize_urls': True,
        'remove_variant_params': True
    },
    
    'consolidation': {
        'prefer_complete_data': True,
        'merge_ingredients': True,
        'merge_nutrition': True,
        'keep_all_urls': True
    },
    
    'validation': {
        'require_product_name': True,
        'require_brand': True,
        'max_name_length': 200,
        'check_duplicates': True
    }
}
```

## Import Process Improvements

### 1. Pre-Import Validation

```python
def validate_import_batch(products):
    """
    Validate batch before import
    """
    validation_report = {
        'total': len(products),
        'valid': 0,
        'variants_detected': 0,
        'duplicates_found': 0,
        'errors': []
    }
    
    for product in products:
        # Check required fields
        if not product.get('product_name'):
            validation_report['errors'].append(f"Missing name: {product}")
            continue
            
        # Check for variants
        if is_size_pack_variant(product):
            validation_report['variants_detected'] += 1
            
        # Check for duplicates
        if product_exists(product):
            validation_report['duplicates_found'] += 1
        
        validation_report['valid'] += 1
    
    return validation_report
```

### 2. Batch Import with Variant Handling

```python
def import_batch_with_variants(products):
    """
    Import batch with automatic variant detection
    """
    # Group products by potential base product
    product_groups = group_by_base_product(products)
    
    for base_key, group in product_groups.items():
        if len(group) == 1:
            # Single product - import normally
            import_single_product(group[0])
        else:
            # Multiple products - check for variants
            parent, variants = identify_parent_and_variants(group)
            
            # Import parent with consolidated data
            consolidated = consolidate_group_data(parent, variants)
            import_single_product(consolidated)
            
            # Add variants to variant table
            for variant in variants:
                add_to_variants_table(variant, parent['product_key'])
```

### 3. URL Normalization

```python
def normalize_product_url(url):
    """
    Normalize URL for consistent storage
    """
    if not url:
        return None
    
    # Remove variant parameters
    if '?activeVariant=' in url:
        url = url.split('?activeVariant=')[0]
    
    # Remove trailing slashes
    url = url.rstrip('/')
    
    # Remove duplicate slashes
    url = re.sub(r'/+', '/', url)
    
    # Ensure https
    if url.startswith('http://'):
        url = url.replace('http://', 'https://')
    
    return url
```

## Integration with Existing Systems

### 1. Zooplus Import Enhancement

```python
# scripts/import_zooplus_enhanced.py

class EnhancedZooplusImporter:
    """
    Zooplus importer with variant detection
    """
    
    def import_from_csv(self, csv_file):
        df = pd.read_csv(csv_file)
        
        # Pre-process all products
        products = []
        for _, row in df.iterrows():
            product = self.prepare_product(row)
            products.append(product)
        
        # Group by potential variants
        groups = self.group_variants(products)
        
        # Import each group
        for group in groups:
            self.import_group(group)
    
    def import_group(self, products):
        if len(products) == 1:
            self.import_single(products[0])
        else:
            # Handle as variant group
            parent = self.select_parent(products)
            self.import_with_variants(parent, products)
```

### 2. Scraping Integration

```python
# scripts/scrape_with_variant_check.py

def process_scraped_product(scraped_data):
    """
    Process scraped data with variant checking
    """
    # Check if this is a variant
    variant_check = check_if_variant(scraped_data)
    
    if variant_check['is_variant']:
        # Update parent instead of creating new
        update_parent_with_data(
            variant_check['parent_key'],
            scraped_data
        )
        
        # Log as variant
        log_variant_scrape(scraped_data, variant_check['parent_key'])
    else:
        # Import as new product
        import_new_product(scraped_data)
```

## Monitoring and Reporting

### 1. Import Statistics

```python
class ImportMonitor:
    """
    Monitor import process and variant detection
    """
    
    def __init__(self):
        self.stats = {
            'products_imported': 0,
            'variants_detected': 0,
            'variants_consolidated': 0,
            'data_enrichments': 0,
            'errors': 0
        }
    
    def report(self):
        """
        Generate import report
        """
        return {
            'summary': self.stats,
            'variant_rate': self.stats['variants_detected'] / self.stats['products_imported'],
            'consolidation_rate': self.stats['variants_consolidated'] / self.stats['variants_detected'],
            'enrichment_rate': self.stats['data_enrichments'] / self.stats['products_imported']
        }
```

### 2. Quality Metrics

```sql
-- Query to monitor variant detection effectiveness
SELECT 
    DATE(created_at) as import_date,
    COUNT(*) as total_imported,
    COUNT(CASE WHEN source = 'variant_consolidated' THEN 1 END) as variants_handled,
    COUNT(CASE WHEN ingredients_source = 'consolidated' THEN 1 END) as data_consolidated,
    ROUND(100.0 * COUNT(CASE WHEN source = 'variant_consolidated' THEN 1 END) / COUNT(*), 2) as variant_rate
FROM foods_canonical
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY import_date DESC;
```

## Implementation Roadmap

### Phase 1: Core Infrastructure (Week 1)
- [ ] Implement VariantDetector class
- [ ] Implement DataConsolidator class
- [ ] Implement BrandNormalizer class
- [ ] Create configuration system

### Phase 2: Integration (Week 2)
- [ ] Update Zooplus import scripts
- [ ] Update scraping processors
- [ ] Add variant checking to all imports
- [ ] Create monitoring dashboard

### Phase 3: Testing (Week 3)
- [ ] Test with sample imports
- [ ] Validate variant detection accuracy
- [ ] Performance testing
- [ ] Edge case handling

### Phase 4: Deployment (Week 4)
- [ ] Deploy to production
- [ ] Monitor initial imports
- [ ] Tune detection parameters
- [ ] Document processes

## Expected Benefits

### Immediate Benefits
1. **Reduced duplication** - Prevent ~20% duplicate products
2. **Better data quality** - Consolidated ingredients/nutrition
3. **Cleaner database** - Proper variant relationships
4. **Accurate metrics** - True coverage statistics

### Long-term Benefits
1. **Scalability** - Handle larger product catalogs
2. **Consistency** - Standardized import process
3. **Maintainability** - Clear variant relationships
4. **User Experience** - Better search results

## Success Metrics

### KPIs to Track
1. **Variant Detection Rate** - % of variants correctly identified
2. **False Positive Rate** - % incorrectly marked as variants
3. **Data Consolidation Rate** - % of variants enriching parents
4. **Import Speed** - Products/minute with variant checking
5. **Database Growth Rate** - Reduction in duplicate growth

### Target Metrics
- Variant detection accuracy: >95%
- False positive rate: <2%
- Data consolidation success: >90%
- Import speed impact: <10% slower
- Database size reduction: 15-20%

## Risk Mitigation

### Potential Risks
1. **Over-aggressive detection** - Real products marked as variants
2. **Data loss** - Important distinctions lost
3. **Performance impact** - Slower imports
4. **Complex edge cases** - Unusual product naming

### Mitigation Strategies
1. **Conservative thresholds** - High confidence required
2. **Manual review queue** - Flag uncertain cases
3. **Caching and optimization** - Minimize lookups
4. **Continuous monitoring** - Track metrics closely
5. **Rollback capability** - Ability to revert changes

## Appendix

### A. Sample Code for Testing

```python
# Test variant detection
def test_variant_detection():
    test_cases = [
        ("Royal Canin Adult 3kg", "Royal Canin Adult 12kg", True, "size"),
        ("Purina One Adult", "Purina One Senior", False, None),
        ("Wolf 6x400g", "Wolf 12x400g", True, "pack"),
        ("Small Breed Adult", "Large Breed Adult", False, None),
    ]
    
    detector = VariantDetector()
    for name1, name2, expected_variant, expected_type in test_cases:
        result = detector.compare_products(name1, name2)
        assert result['is_variant'] == expected_variant
        assert result['type'] == expected_type
```

### B. Migration Script Template

```python
# Migrate existing duplicates using new system
def migrate_existing_variants():
    """
    Apply variant detection to existing database
    """
    importer = SmartProductImporter()
    
    # Get all products
    products = get_all_products()
    
    # Group by brand
    for brand, brand_products in group_by_brand(products):
        # Detect variant groups
        groups = importer.variant_detector.find_variant_groups(brand_products)
        
        for group in groups:
            # Consolidate each group
            importer.consolidate_variant_group(group)
```

### C. Configuration Examples

```yaml
# config/import_rules.yaml
variant_detection:
  rules:
    - pattern: '\d+\s*kg'
      type: size
      action: consolidate
    
    - pattern: '\d+\s*x\s*\d+'
      type: pack
      action: consolidate
    
    - pattern: 'puppy|adult|senior'
      type: life_stage
      action: keep_separate
    
    - pattern: 'small|medium|large'
      type: breed_size
      action: keep_separate
```

---

*Document Version: 1.0*
*Created: December 2024*
*Status: Planning Phase*