# Brand Normalization Plan
Generated: 2025-09-12T12:38:23.244153

## Executive Summary

Comprehensive brand normalization strategy based on authoritative ALL-BRANDS.md list.

## Statistics

### Canonical Brands
- **Total canonical brands**: 279
- **Brands with aliases**: 16
- **Total aliases defined**: 33

### Impact Simulation

| Dataset | Before Normalization | After Normalization | Reduction |
|---------|---------------------|---------------------|-----------|
| AADF | 241 brands | 240 brands | -1 (0.4%) |
| Chewy | 160 brands | 158 brands | -2 (1.2%) |

## Key Normalizations

### Royal Canin Family
- **Canonical**: Royal Canin
- **Variants normalized**:
  - royal canin breed
  - royal canin veterinary
  - royal canin veterinary diet
  - royal canin vet

### Hill's Family
- **Canonical**: Hill's
- **Variants normalized**:
  - hills
  - hill
  - hills science
  - hills science plan
  - hills science diet
  - hills prescription
  - hills prescription diet

### Pro Plan Family
- **Canonical**: Pro Plan
- **Variants normalized**:
  - purina pro plan
  - proplan

### Nature's Brands
- **Nature's Menu**: natures menu
- **Nature's Deli**: natures deli
- **Nature's Harvest**: natures harvest

## Edge Cases Handled

1. **Apostrophes**: Hill's, Lily's Kitchen, Wainwright's
2. **Multi-word brands**: James Wellbeloved, Pooch & Mutt, Wolf of Wilderness
3. **Abbreviations**: Dr John, CSJ, Fish4Dogs
4. **Brand families**: Royal Canin (Breed, Veterinary), Hill's (Science, Prescription)

## Unmapped Brands

Total unmapped: 254

### Sample Unmapped Brands (may need manual review):
- 360 Pet Nutrition
- 4PAWS
- 4PAWSRAW
- Aardvark
- Addiction
- Advance
- Advance Veterinary Diets
- Affinity
- Aflora
- Albion
- Aldi
- Algoods
- Almo
- Ambrosia
- American Journey
- American Journey Dry
- American Journey Wet
- American Natural Premium
- Ami
- Angell

... and 234 more

## Conflicting Patterns

### Brands with Multiple Interpretations
- **Alpha**: Could be "Alpha" or "Alpha Spirit" 
- **Arden**: Could be "Arden" or "Arden Grange"
- **Burns**: Standalone brand vs "Burns Original"
- **Barking**: Could be "Barking" or "Barking Heads"

### Resolution Strategy
These conflicts are resolved by preferring the full brand name when context is unclear.

## Implementation Notes

1. **Case Insensitive**: All matching is case-insensitive
2. **Special Characters**: Removed for slug creation, preserved in display names
3. **Whitespace**: Normalized to single spaces
4. **Priority**: Exact matches > Known aliases > Partial matches

## Recommendations

1. **Review unmapped brands** - Many may be retailer-specific or discontinued
2. **Validate edge cases** - Especially brands with multiple possible interpretations
3. **Consider brand families** - Some brands may benefit from hierarchical organization
4. **Regular updates** - ALL-BRANDS.md should be the single source of truth

## Files Generated

- `data/brand_alias_map.yaml` - Authoritative mapping file
- `reports/BRANDS-NORMALIZATION-PLAN.md` - This report
