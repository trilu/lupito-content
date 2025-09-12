# Product Name Cleanup Plan - Remove Brand Prefixes

**Date:** 2025-09-12  
**Scope:** Remove brand name prefixes from product names across entire database  
**Affected:** 2,090 products (40% of database) across 144 brands  

## Problem Statement

After fixing brand names (e.g., "BETTY" → "Betty & Butch"), product names still contain partial or full brand prefixes. For example:
- Brand: "Betty & Butch", Product: "BUTCH Duck, Rice and Veg" 
- Should be: "Duck, Rice and Veg"

## Analysis Summary

### Pattern Distribution

| Pattern Type | Count | % of DB | Example |
|--------------|-------|---------|---------|
| Full brand at start | 1,175 | 22.5% | "Royal Canin Cavalier..." (Royal Canin) |
| Last word of brand | 621 | 11.9% | "BUTCH Duck..." (Betty & Butch) |
| Middle part of brand | 235 | 4.5% | "Pet Foods Grain..." (Borders Pet Foods) |
| First word of brand | 59 | 1.1% | "Advance Maxi..." (Advance Veterinary Diets) |
| **Total Affected** | **2,090** | **40.0%** | |
| No issue | 3,000 | 57.4% | Clean product names |

### Critical Brands (100% Products Affected)

These recently fixed brands have ALL products with prefix issues:

| Brand | Products | Current Pattern | Required Fix |
|-------|----------|-----------------|--------------|
| Betty & Butch | 23 | "BUTCH ..." | Remove "BUTCH " |
| Sausage Dog Sanctuary Food | 25 | "Dog Sanctuary ..." | Remove "Dog Sanctuary " |
| Bright Eyes Bushy Tails | 25 | "Eyes Bushy Tails ..." | Remove "Eyes Bushy Tails " |
| Bounce and Bella | 20 | "Bella ..." | Remove "Bella " |
| Borders Pet Foods | 28 | "Pet Foods ..." | Remove "Pet Foods " |
| Harrier Pro Pet Foods | 28 | "Pro Pet Foods ..." | Remove "Pro Pet Foods " |
| Growling Tums | 27 | "Tums ..." | Remove "Tums " |
| Dragonfly Products | 20 | "Products ..." | Remove "Products " |
| Edgard & Cooper | 26 | "Cooper ..." | Remove "Cooper " |
| Natural Instinct | 18 | "Instinct ..." | Remove "Instinct " |
| Cotswold Raw | 19 | "Raw ..." | Remove "Raw " |

### Major Brands Affected

| Brand | Products | Pattern Types |
|-------|----------|---------------|
| Royal Canin | 250 | Full brand, last word |
| Wolf Of Wilderness | 69 | Full brand, middle part |
| Happy Dog | 64 | Last word, full brand |
| James Wellbeloved | 59 | Last word, full brand |
| Hill's Science Plan | 59 | Middle part, full brand |
| Pets at Home | 54 | Middle part "at Home" |
| Lily's Kitchen | 52 | Last word "Kitchen" |

## Implementation Strategy

### Phase 1: Simple Pattern Removal (High Confidence)

**Target:** 1,500+ products with clear patterns

#### 1.1 Exact Brand Name Removal
- Pattern: Product starts with exact brand name
- Example: "Royal Canin Yorkshire Terrier" → "Yorkshire Terrier"
- Confidence: 100%

#### 1.2 Last Word Removal (Multi-word Brands)
- Pattern: Product starts with last word of brand
- Example: "BUTCH Duck and Rice" → "Duck and Rice"
- Confidence: 95%

#### 1.3 Middle Part Removal
- Pattern: Product starts with middle portion of brand
- Example: "Pet Foods Grain Free Adult" → "Grain Free Adult"
- Confidence: 95%

### Phase 2: Context-Sensitive Removal

**Target:** 500+ products needing careful handling

#### 2.1 Conditional Removal Rules

```python
# Example rules structure
conditional_rules = {
    'Happy Dog': {
        'remove_if': 'Dog ',
        'only_when_followed_by': ['NaturCroq', 'Fit', 'Supreme', 'Sensible'],
        'preserve_when': ['Dog Chow', 'Dog Treats']  # Hypothetical product lines
    },
    'Natural Instinct': {
        'remove': 'Instinct ',
        'preserve_if_next_word': ['Natural']  # Don't remove from "Instinct Natural Chicken"
    }
}
```

#### 2.2 Special Cases
- Possessive forms: "Lily's Kitchen" → Remove "Kitchen" not "Lily's"
- Abbreviations: "N&D" from "Farmina N&D"
- Compound removals: "Hill's Prescription Diet" (multiple patterns)

### Phase 3: Edge Case Handling

**Target:** ~100 products with complex patterns

#### 3.1 Manual Review Required
- Products where brand word is also a common word
- Breed names matching brand parts
- Product lines with brand-like names

#### 3.2 Preservation Rules
- Keep: Breed names (Yorkshire, Beagle, etc.)
- Keep: Size indicators (Mini, Maxi, Large)
- Keep: Age indicators (Puppy, Adult, Senior)
- Keep: Medical/dietary terms

## Technical Implementation

### Script Structure

```
clean_product_names.py
├── Load all products
├── Apply cleanup rules by brand
├── Validate changes
├── Generate review report
├── Update database (with confirmation)
└── Create rollback file
```

### Cleanup Rules Format

```python
cleanup_rules = {
    'brand_name': {
        'type': 'simple|complex|conditional',
        'patterns': [
            {'match': 'BUTCH ', 'remove': 'BUTCH '},
            {'match': '^Dog Sanctuary ', 'remove': 'Dog Sanctuary '}
        ],
        'preserve': ['specific_terms'],
        'confidence': 0.95
    }
}
```

### Database Update Strategy

1. **Backup Original Data**
   - Save current product_name values
   - Create timestamped rollback file

2. **Batch Processing**
   - Process by brand for efficiency
   - Use transactions for consistency
   - Update in batches of 100

3. **Field Updates**
   - Update: product_name
   - Regenerate: product_key (if name is part of key)
   - Maintain: audit trail

## Quality Assurance

### Validation Rules

1. **No Over-Removal**
   - Product name must not be empty
   - Must retain at least 2 words (where applicable)
   - Must keep product descriptors

2. **Semantic Integrity**
   - Name must still describe the product
   - No loss of flavor/variety information
   - Maintain size/age/dietary indicators

3. **Consistency Checks**
   - Similar products should have similar patterns
   - No brand name at start of any product
   - Product keys remain unique

### Test Cases

| Brand | Original | Expected | Rule |
|-------|----------|----------|------|
| Betty & Butch | "BUTCH Duck, Rice and Veg" | "Duck, Rice and Veg" | Remove "BUTCH " |
| Royal Canin | "Royal Canin Yorkshire Terrier Adult" | "Yorkshire Terrier Adult" | Remove brand |
| Royal Canin | "Canin Beagle Adult" | "Beagle Adult" | Remove last word |
| Happy Dog | "Dog NaturCroq Balance" | "NaturCroq Balance" | Conditional removal |
| Lily's Kitchen | "Kitchen Chicken & Duck" | "Chicken & Duck" | Remove last word |
| Borders Pet Foods | "Pet Foods Grain Free Adult" | "Grain Free Adult" | Remove middle part |
| Pets at Home | "at Home Advanced Nutrition" | "Advanced Nutrition" | Remove middle part |

## Risk Assessment & Mitigation

### Risks

1. **Over-Removal Risk**
   - Mitigation: Conservative patterns, manual review
   - Fallback: Full rollback capability

2. **Information Loss**
   - Mitigation: Preserve all descriptive terms
   - Fallback: Original data saved

3. **Pattern Misidentification**
   - Mitigation: Confidence scoring, test cases
   - Fallback: Staged rollout

4. **Database Integrity**
   - Mitigation: Transactions, validation
   - Fallback: Backup before execution

## Execution Plan

### Day 1: High-Priority Fixes
1. Fix recently corrected brands (266 products)
2. Apply simple full-brand removals (1,000+ products)
3. Generate review report

### Day 2: Complex Patterns
1. Apply conditional rules (500+ products)
2. Handle special cases
3. Manual review of edge cases

### Day 3: Verification
1. Full database scan for remaining issues
2. Quality assurance checks
3. Final report generation

## Success Metrics

- ✅ **0 products** start with their brand name
- ✅ **100% of affected products** have clean names
- ✅ **No information loss** in product descriptions
- ✅ **All product keys** remain unique
- ✅ **Full rollback capability** maintained

## Expected Outcomes

### Before
- 2,090 products with redundant brand prefixes
- Inconsistent naming across brands
- Poor user experience with repetitive text

### After
- Clean, descriptive product names
- Consistent naming convention
- Improved readability and searchability
- Professional data presentation

## Rollback Plan

If issues arise:
1. Load rollback file with original values
2. Restore product_name fields
3. Regenerate product_keys if needed
4. Verify restoration complete

## Appendix: Affected Brands List

Full list of 144 brands needing cleanup (sorted by product count):
1. Royal Canin (250)
2. Wolf Of Wilderness (69)
3. Happy Dog (64)
4. James Wellbeloved (59)
5. Hill's Science Plan (59)
6. Pets at Home (54)
7. Lily's Kitchen (52)
8. Natures Menu (46)
9. Arden Grange (46)
10. Eukanuba (45)
... (134 more brands)

---

**Next Step:** Execute Phase 1 with high-confidence patterns on recently fixed brands.