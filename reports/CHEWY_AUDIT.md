# CHEWY DATASET AUDIT
Generated: 2025-09-12T08:28:16.911610

## Dataset Structure

**Source**: data/chewy/chewy-dataset.json
**Format**: JSON array of product objects
**Total Records**: 1282

## Field Mapping

| Chewy Field | Canonical Field | Coverage | Notes |
|-------------|-----------------|----------|-------|
| name | product_name | 100% | Full product name with size |
| brand.slogan | brand | 99.7% | Brand in slogan field, not brand.name |
| offers.price | price_per_kg_eur | 98.2% | Converted from USD with weight extraction |
| description | form, life_stage | 96.9% | Parsed from Specifications block |
| url | product_url | 100% | Full Chewy product URL |

## Parsing Rules Applied

### Brand Extraction
- Primary: `item['brand']['slogan']` field
- Fallback: First word(s) of product name before keywords
- Example: "ZIWI Peak Lamb..." → Brand: "ZIWI"

### Weight Extraction
- Pattern: `(\d+(?:\.\d+)?)\s*[-]?(lb|oz|kg)`
- Conversions: lb→kg (×0.453592), oz→kg (×0.0283495)
- Example: "3.5-oz pouch" → 0.099 kg

### Form Detection
- Specifications block: "Food Form: Dry" → form: "dry"
- Name patterns: "Air-Dried", "Freeze-Dried" → form: "raw"
- Keywords: "wet food", "canned", "pate" → form: "wet"

### Life Stage Detection  
- Specifications block: "Lifestage: Adult" → life_stage: "adult"
- Name patterns: "Puppy", "Junior" → life_stage: "puppy"
- "All Life Stages" → life_stage: "all"

## Sample Products


**Purina ONE Chicken & Rice Formula Dry Dog Food, 4-lb bag...**
- Brand: Purina ONE
- Form: dry
- Life Stage: all
- Price/kg: €3.16
- Confidence: 0.8

**Purina Pro Plan Veterinary Diets EN Gastroenteric Low Fat Dry Dog Food, 25-lb ba...**
- Brand: Purina Pro Plan Veterinary Diets
- Form: dry
- Life Stage: nan
- Price/kg: €7.38
- Confidence: 0.4

**Purina ONE SmartBlend True Instinct Tender Cuts in Gravy Variety Pack Canned Dog...**
- Brand: Purina ONE
- Form: wet
- Life Stage: all
- Price/kg: €45.41
- Confidence: 0.8

**Health Extension Gently Cooked Lamb & Carrot Recipe Wet Dog Food, 9-oz pouch, 1 ...**
- Brand: Health Extension
- Form: wet
- Life Stage: adult
- Price/kg: €16.37
- Confidence: 0.8

**Nutro Natural Choice Adult Lamb & Brown Rice Recipe Dry Dog Food, 20-lb bag...**
- Brand: Nutro
- Form: dry
- Life Stage: adult
- Price/kg: €3.62
- Confidence: 0.8

## Brand Distribution

| Brand | Product Count | Percentage |
|-------|---------------|------------|
| Stella & Chewy's | 71 | 5.5% |
| Blue Buffalo | 59 | 4.6% |
| Purina Pro Plan | 56 | 4.4% |
| Purina ONE | 44 | 3.4% |
| Pedigree | 41 | 3.2% |
| JustFoodForDogs | 40 | 3.1% |
| Hill's Science Diet | 37 | 2.9% |
| Instinct | 35 | 2.7% |
| Hill's Prescription Diet | 33 | 2.6% |
| Merrick | 31 | 2.4% |
| Wellness | 27 | 2.1% |
| Royal Canin Veterinary Diet | 26 | 2.0% |
| Vital Essentials | 25 | 2.0% |
| Royal Canin | 21 | 1.6% |
| Purina Pro Plan Veterinary Diets | 21 | 1.6% |

## Quality Metrics

- Products with valid form: 1267 (98.8%)
- Products with valid life_stage: 1243 (97.0%)
- Products with price data: 1228 (95.8%)
- Average confidence score: 0.79
- High confidence (≥0.7): 1242 products

## Known Issues

1. **No Ingredients Data**: Chewy dataset doesn't include ingredient lists
2. **Weight Parsing**: Some products have multiple size options, only first extracted
3. **Brand Normalization**: Some brands may need manual mapping
4. **Price Accuracy**: Depends on correct weight extraction
