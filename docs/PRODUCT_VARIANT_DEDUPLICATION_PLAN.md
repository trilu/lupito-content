# Product Variant Deduplication Plan

## Executive Summary

This document outlines the strategy for cleaning up product variants in the foods_canonical database by moving size and pack variants to a separate table while preserving life stage and breed size distinctions in the main table.

## Current State Analysis

### Database Statistics
- **Total products**: 9,092
- **Estimated duplication rate**: 20.1% (1,828 duplicates/variants)
- **True unique products**: ~7,264

### Duplication Sources Identified

1. **URL Variants**: 548 base URLs with multiple variants
   - Example: Advance Vet Diets has 92 variants
   - Royal Canin Vet Diet has 65 variants

2. **Similar Names**: 1,092 groups of products with similar names
   - Size variations: 5.6% have size indicators
   - Pack variations: 5.3% have pack indicators
   - Life stage variants: 49.1% mention puppy/adult/senior
   - Breed size variants: 23.1% mention small/medium/large

3. **Identical Ingredients**: 683 groups sharing same ingredients
   - Same products in different pack sizes
   - Regional variations with same formula

## Deduplication Strategy

### Variant Classification Rules

#### KEEP in Main Table
✅ **Life stage variants** (puppy, junior, adult, senior, mature)
- These represent different nutritional formulations
- Important for pet health and customer selection

✅ **Breed size variants** (small, medium, large, mini, maxi, giant)
- Different formulations for different dog sizes
- Critical for proper nutrition

✅ **Products with no variants**
- Unique products stay as-is

✅ **Base product from each variant group**
- One representative from size/pack variants

#### MOVE to Variants Table
❌ **Package size variants** (3kg, 12kg, 400g, 800g)
- Same product in different quantities

❌ **Multi-pack variants** (6x400g, 12x800g, 24x300g)
- Same product in different pack configurations

### Impact Analysis

With the revised requirements:
- **Products to remain**: 8,978 (from 9,092)
- **Products to move**: 114 (size/pack variants only)
- **Reduction**: 1.3% (conservative approach)
- **Variant groups affected**: 97

## Implementation Plan

### Phase 1: Database Structure

#### New Tables

```sql
-- Table for storing size/pack variants
CREATE TABLE product_variants (
  variant_id SERIAL PRIMARY KEY,
  parent_product_key TEXT REFERENCES foods_canonical(product_key),
  variant_product_key TEXT UNIQUE,
  variant_type VARCHAR(20) CHECK (variant_type IN ('size', 'pack')),
  size_value TEXT, -- e.g., "3kg", "6x400g"
  product_name TEXT,
  product_url TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  migrated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_parent_key ON product_variants(parent_product_key);
CREATE INDEX idx_variant_key ON product_variants(variant_product_key);

-- Tracking table for migration
CREATE TABLE variant_migration_log (
  id SERIAL PRIMARY KEY,
  original_product_key TEXT,
  parent_product_key TEXT,
  action VARCHAR(50),
  data_migrated JSONB,
  migrated_at TIMESTAMP DEFAULT NOW()
);
```

### Phase 2: Variant Detection

#### Detection Patterns

```python
# Size variants pattern
size_pattern = r'\b\d+(?:\.\d+)?\s*(kg|g|lb|oz|ml|l)\b'

# Pack variants pattern  
pack_pattern = r'\b\d+\s*x\s*\d+(?:\.\d+)?(?:\s*(?:kg|g|lb|oz|ml|l|cans?|pouches?))?'

# Patterns to KEEP (not remove)
life_stage_pattern = r'\b(puppy|junior|adult|senior|mature)\b'
breed_size_pattern = r'\b(small|medium|large|mini|maxi|giant)\s*(?:breed|dog)?\b'
```

#### Normalization Function

```python
def normalize_for_variants(product_name):
    """
    Normalize product name by removing ONLY size and pack indicators
    Keep life stage and breed size information
    """
    # Remove size indicators
    name = re.sub(size_pattern, '', name, flags=re.IGNORECASE)
    
    # Remove pack indicators
    name = re.sub(pack_pattern, '', name, flags=re.IGNORECASE)
    
    # Clean up extra spaces
    name = re.sub(r'\s+', ' ', name).strip()
    
    return name
```

### Phase 3: Data Consolidation Strategy

#### Parent Selection Algorithm

For each variant group, select the parent product based on:
1. **Data completeness** (has ingredients AND nutrition)
2. **Most common size** (if identifiable)
3. **Alphabetically first** (as tiebreaker)

#### Data Merging Rules

```python
def consolidate_variant_data(parent, variants):
    """
    Merge data from variants into parent product
    """
    # Take ingredients from ANY variant that has them
    if not parent.ingredients_raw:
        for variant in variants:
            if variant.ingredients_raw:
                parent.ingredients_raw = variant.ingredients_raw
                parent.ingredients_source = variant.ingredients_source
                break
    
    # Take nutrition from ANY variant (should be identical)
    if not parent.protein_percent:
        for variant in variants:
            if variant.protein_percent:
                parent.protein_percent = variant.protein_percent
                parent.fat_percent = variant.fat_percent
                parent.fiber_percent = variant.fiber_percent
                parent.ash_percent = variant.ash_percent
                parent.moisture_percent = variant.moisture_percent
                parent.macros_source = variant.macros_source
                break
    
    # Normalize product name (remove size/pack)
    parent.product_name = normalize_for_variants(parent.product_name)
    
    return parent
```

### Phase 4: Migration Process

#### Step-by-Step Migration

1. **Backup Current State**
   ```sql
   CREATE TABLE foods_canonical_backup_YYYYMMDD AS 
   SELECT * FROM foods_canonical;
   ```

2. **Identify Variant Groups**
   - Run detection script to find all size/pack variant groups
   - Generate CSV report for manual review
   - Validate detection accuracy

3. **Manual Review** (97 groups only)
   - Check each variant group
   - Confirm parent selection
   - Approve for migration

4. **Execute Migration**
   ```python
   for variant_group in approved_groups:
       # Select parent
       parent = select_parent_product(variant_group)
       
       # Consolidate data
       parent = consolidate_variant_data(parent, variant_group)
       
       # Create variant records
       for variant in variant_group:
           if variant.product_key != parent.product_key:
               create_variant_record(variant, parent)
               log_migration(variant, parent)
       
       # Update parent in database
       update_product(parent)
   ```

5. **Validation**
   - Verify ingredient coverage maintained
   - Check nutrition data preserved
   - Ensure no products lost
   - Test search functionality

6. **Cleanup**
   - Remove migrated variants from main table
   - Update statistics
   - Clear caches

### Phase 5: Future Import Process Updates

#### Variant Detection During Import

```python
def check_for_variants(new_product):
    """
    Check if new product is a variant of existing product
    """
    # Normalize name
    base_name = normalize_for_variants(new_product.product_name)
    
    # Look for existing product with same base name and brand
    existing = find_product(brand=new_product.brand, 
                           normalized_name=base_name)
    
    if existing:
        # Check if only differs by size/pack
        if is_size_pack_variant(new_product, existing):
            # Add to variants table instead
            add_to_variants(new_product, existing)
            return True
    
    return False
```

## Examples

### Products to be Consolidated

| Current Products | After Migration |
|-----------------|-----------------|
| Terra Canis Essential 8+ **6 x 780g** | Terra Canis Essential 8+ |
| Terra Canis Essential 8+ **6 x 385g** | → moved to variants |
| Wolf of Wilderness Adult **6 x 800g** | Wolf of Wilderness Adult |
| Wolf of Wilderness Adult **12 x 400g** | → moved to variants |

### Products to Remain Separate

| Product | Why Keep Separate |
|---------|-------------------|
| Royal Canin **Mini** Adult | Breed size variant |
| Royal Canin **Medium** Adult | Breed size variant |
| Royal Canin **Maxi** Adult | Breed size variant |
| Eukanuba **Puppy** | Life stage variant |
| Eukanuba **Adult** | Life stage variant |
| Eukanuba **Senior** | Life stage variant |

## Risk Management

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Data loss | Low | High | Full backup before migration |
| Wrong consolidation | Low | Medium | Manual review of 97 groups |
| Breaking references | Low | Low | Update all foreign keys |
| Search issues | Low | Low | Test search after migration |

### Rollback Plan

1. Keep backup table for 30 days
2. Migration log tracks all changes
3. Variant table preserves all original data
4. Can restore from backup if needed

## Success Metrics

### Expected Outcomes

- ✅ Database reduced from 9,092 to 8,978 products (1.3% reduction)
- ✅ All ingredient and nutrition data preserved
- ✅ Life stage and breed variants maintained
- ✅ Cleaner search results without size/pack duplicates
- ✅ More accurate coverage metrics

### Validation Criteria

1. **Data Integrity**
   - No ingredients lost
   - No nutrition data lost
   - All URLs preserved

2. **Functionality**
   - Search returns expected results
   - No broken product pages
   - Variants accessible if needed

3. **Performance**
   - No degradation in query speed
   - Reduced database size

## Timeline

| Phase | Duration | Tasks |
|-------|----------|-------|
| Preparation | 1 day | Create scripts, backup database |
| Detection | 2 hours | Identify variant groups |
| Review | 2 hours | Manual review of 97 groups |
| Migration | 1 hour | Execute migration |
| Validation | 2 hours | Test and verify |
| **Total** | **~2 days** | Complete migration |

## Appendix

### SQL Queries for Analysis

```sql
-- Find products with size indicators
SELECT COUNT(*) 
FROM foods_canonical 
WHERE product_name ~ '\d+(\.\d+)?\s*(kg|g|lb|oz|ml|l)';

-- Find products with pack indicators
SELECT COUNT(*) 
FROM foods_canonical 
WHERE product_name ~ '\d+\s*x\s*\d+';

-- Find variant groups
SELECT brand, 
       regexp_replace(product_name, '\d+(\.\d+)?\s*(kg|g|lb|oz|ml|l)', '', 'gi') as base_name,
       COUNT(*) as variant_count
FROM foods_canonical
GROUP BY brand, base_name
HAVING COUNT(*) > 1
ORDER BY variant_count DESC;
```

### Python Scripts Required

1. `detect_variants.py` - Identify size/pack variant groups
2. `consolidate_variants.py` - Merge data and create parent products
3. `migrate_variants.py` - Execute the migration
4. `validate_migration.py` - Check data integrity
5. `update_import_process.py` - Modify import to detect variants

## Approval and Sign-off

**Status**: Ready for implementation
**Estimated Impact**: Minimal (1.3% of products)
**Risk Level**: Low
**Reversibility**: Full

---

*Document Version: 1.0*
*Created: December 2024*
*Last Updated: December 2024*