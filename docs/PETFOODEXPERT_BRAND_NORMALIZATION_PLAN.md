# PetFoodExpert.com Brand Normalization Plan

**Date:** 2025-09-12  
**Total Products Affected:** 3,849  
**Unique Brands to Review:** 282  

## Problem Summary

The petfoodexpert.com data import has significant brand extraction issues where partial brand names were extracted. For example:
- "BETTY" instead of "Betty & Butch" (all 23 products start with "BUTCH")
- "Borders" instead of "Borders Pet Foods" (all products start with "Pet Foods")
- "Sausage" instead of "Sausage Dog Sanctuary Food"
- "Bright" instead of "Bright Eyes Bushy Tails"

## Phase 1: High-Confidence Brand Corrections (95%+ Certainty)

### 1.1 Validated Brand Corrections with Official Websites

| Current Brand | Correct Brand | Products | Website | Confidence |
|--------------|--------------|----------|---------|------------|
| BETTY | Betty & Butch | 23 | https://www.bettyandbutch.co.uk/ | 100% |
| Sausage | Sausage Dog Sanctuary Food | 25 | https://sausagedogsanctuaryfood.com/ | 100% |
| Bright | Bright Eyes Bushy Tails | 25 | https://brighteyes-bushytails.co.uk/ | 100% |
| Bounce | Bounce and Bella | 20 | https://shop.bounceandbella.co.uk/ | 100% |
| Edgard | Edgard & Cooper | 26 | https://www.edgardcooper.com/ | 100% |
| Growling | Growling Tums | 27 | https://growlingtums.co.uk/ | 100% |
| Dragonfly | Dragonfly Products | 20 | https://dragonflyproducts.co.uk/ | 100% |
| Borders | Borders Pet Foods | 28 | Company House verified | 95% |
| Harrier | Harrier Pro Pet Foods | 28 | https://www.harrierpropetfoods.co.uk/ | 100% |
| Wolf | Wolf Of Wilderness | 14 | Already in ALL-BRANDS.md | 100% |

**Total Products for Immediate Fix:** 266

### 1.2 Context-Dependent Corrections (Need Product Name Analysis)

#### "The" brand (76 products)
- Products starting with "Natural" (38) → Need individual research
- Products starting with "Barkside" (10) → Likely "The Barkside"
- Products starting with "Innocent" (3) → Likely "The Innocent Hound"
- Remaining need investigation

#### "Natural" brand (44 products)
- Products with "Choice" (19) → Likely "Natural Choice Pet Foods"
- Products with "Instinct" (18) → "Natural Instinct" (confirmed in ALL-BRANDS.md)
- Remaining need verification

#### "Country" brand (21 products)
- Products with "Dog" pattern (13) → "Country Dog" (https://www.countrydogfood.co.uk/)
- Products with "Pursuit" pattern (8) → "Country Pursuit" (https://countrypursuit.co.uk/)

#### "Pet" brand (14 products)
- All start with "Shop" → Likely "Pet Shop Online" (needs verification)

#### "Cotswold" brand (28 products)
- Products with "Raw" (19) → "Cotswold Raw" (already in ALL-BRANDS.md)
- Products with "Pet Supplies" (9) → Needs investigation

#### "Jollyes" brand (33 products)
- Products with "K9 Optimum" (8) → "K9 Optimum" (separate brand)
- Products with "Lifestage" (21) → "Jollyes Lifestage"
- Remaining (4) → Keep as "Jollyes"

## Phase 2: Brands Requiring Additional Research

These brands need thorough validation before correction:

1. **Yorkshire Valley Farms** (42 products) - Currently as "Yorkshire"
2. **Lakes Heritage/Collection** (38 products) - Currently as "Lakes"
3. **Luvdogz** (34 products) - Unknown brand, needs research
4. **Websters** (20 products) - Unknown brand, needs research
5. **Tails** (23 products) - Could be "Tails.com"
6. **The Natural Pet Company** - For "The" brand products with "Natural"
7. **The Barkside** - For "The" brand products with "Barkside"

## Phase 3: Implementation Strategy

### 3.1 Validation Process

For each uncertain brand:
1. Extract first 2-3 words from all product names
2. Identify consistent patterns
3. Search web for "{pattern} dog food UK"
4. Check Companies House UK database
5. Verify against other UK retailer sites
6. Generate confidence score (must be ≥95% for automatic fix)

### 3.2 Database Updates

#### Create brand_metadata table
```sql
CREATE TABLE brand_metadata (
    brand_name TEXT PRIMARY KEY,
    official_website TEXT,
    company_registration TEXT,
    country TEXT DEFAULT 'UK',
    validation_date DATE,
    confidence_score DECIMAL(3,2),
    source TEXT
);
```

#### Update brand_alias table
Add all validated mappings:
```sql
INSERT INTO brand_alias (alias, canonical_brand, created_at) VALUES
('betty', 'Betty & Butch', NOW()),
('sausage', 'Sausage Dog Sanctuary Food', NOW()),
('bright', 'Bright Eyes Bushy Tails', NOW()),
-- etc for all validated brands
```

### 3.3 Scripts to Create

1. **validate_petfoodexpert_brands.py**
   - Analyze all petfoodexpert.com products
   - Generate validation report with confidence scores
   - Output brands needing manual review

2. **fix_petfoodexpert_brands.py**
   - Apply only high-confidence corrections (≥95%)
   - Update brand, brand_slug, and product_key fields
   - Generate rollback file
   - Create audit log

3. **update_brand_metadata.py**
   - Store validated brand information
   - Track websites and confidence scores
   - Enable future validation

## Phase 4: Quality Assurance

### Validation Rules
- ✅ Brand must have official website OR Companies House registration
- ✅ Product names should logically contain brand elements
- ✅ Cross-reference with at least 2 UK pet retailers
- ✅ Minimum 95% confidence for automatic correction
- ✅ Save website URL for each brand

### Manual Review Required
- Brands with <95% confidence
- Single-product brands (18 found)
- Brands where product names don't match patterns

## Phase 5: Update ALL-BRANDS.md

### Brands to Add
- Betty & Butch
- Sausage Dog Sanctuary Food
- Bright Eyes Bushy Tails
- Bounce and Bella
- Edgard & Cooper
- Growling Tums
- Dragonfly Products
- Borders Pet Foods
- Harrier Pro Pet Foods
- Country Dog
- Country Pursuit
- (Plus any additional validated brands)

## Success Metrics

- [ ] Zero brands with partial extractions (e.g., "The", "Natural", "Pet")
- [ ] All brands have verified websites or company registrations
- [ ] 95%+ products have brands appearing in product names
- [ ] Complete audit trail for all changes
- [ ] Full rollback capability maintained
- [ ] brand_metadata table populated with all brands

## Execution Timeline

### Day 1 (Immediate)
- Apply Phase 1.1 corrections (266 products)
- Create validation script
- Begin research on uncertain brands

### Day 2
- Complete brand research and validation
- Apply context-dependent corrections
- Update brand_alias table

### Day 3
- Manual review of remaining issues
- Update ALL-BRANDS.md
- Generate final report

## Expected Impact

- **Immediate fixes:** 266 products (100% confidence)
- **Context-dependent fixes:** ~200 products (after validation)
- **Total expected corrections:** 500+ products
- **Brands to normalize:** ~50 unique brands
- **Database consistency:** Major improvement

## Risk Mitigation

1. All changes have rollback capability
2. Only apply fixes with ≥95% confidence
3. Manual review for edge cases
4. Preserve original data in rollback files
5. Test on sample before full application

## Notes

- Many brands from petfoodexpert.com are UK-specific and not in ALL-BRANDS.md
- Pattern of taking first word as brand name caused most issues
- Web validation essential for confidence
- Company House UK is authoritative source for business names
- Some brands may be private label/white label products