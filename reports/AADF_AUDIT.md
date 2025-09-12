# AADF DATASET AUDIT
Generated: 2025-09-12T08:28:16.913824

## Dataset Structure

**Source**: data/aadf/aadf-dataset.csv
**Format**: CSV with web scraping metadata
**Total Records**: 1101

## Field Mapping

| AADF Field | Canonical Field | Coverage | Notes |
|------------|-----------------|----------|-------|
| data-page-selector | product_name | 100% | Contains view count + name |
| type_of_food-0 | form | 97.7% | "Complete Wet paté" → "wet" |
| dog_ages-0 | life_stage | 92.3% | "From 12 months" → "adult" |
| ingredients-0 | ingredients_raw | 100% | Full ingredient list |
| price_per_day-0 | price_per_kg_eur | 93.5% | Converted from daily cost |

## Parsing Rules Applied

### Product Name Extraction
- Pattern: Remove view count prefix from data-page-selector
- Example: "1k 1,018 people have viewed... Forthglade Complete" → "Forthglade Complete"

### Brand Extraction
- Primary: First 1-2 words of cleaned product name
- Possessive handling: "Nature's Menu" recognized as brand
- Example: "Fish4Dogs Finest..." → Brand: "Fish4Dogs"

### Form Detection
- type_of_food-0: "Complete Wet" → form: "wet"
- type_of_food-0: "Complete Dry" → form: "dry"
- Fallback to name analysis for ambiguous types

### Life Stage Detection
- dog_ages-0: "From 12 months to old age" → life_stage: "adult"
- dog_ages-0: "Puppies" → life_stage: "puppy"
- dog_ages-0: "Senior dogs" → life_stage: "senior"

### Price Conversion
- Input: Price per day in GBP
- Assumption: Average dog eats 300g/day
- Formula: price_per_kg = price_per_day × (1000/300) × 0.92 (EUR conversion)

## Sample Products


**289 289 people have viewed this product in the last 30 days Pooch & Mutt Senior ...**
- Brand: 289 289
- Form: dry
- Life Stage: senior
- Has Ingredients: Yes
- Confidence: 0.7

**480 480 people have viewed this product in the last 30 days Bella + Duke Puppy C...**
- Brand: 480 480
- Form: raw
- Life Stage: adult
- Has Ingredients: Yes
- Confidence: 0.7

**69 69 people have viewed this product in the last 30 days Natural Instinct Senio...**
- Brand: 69 69
- Form: raw
- Life Stage: senior
- Has Ingredients: Yes
- Confidence: 0.7

**0 0 people have viewed this product in the last 30 days Growling Tums Gourmet Ad...**
- Brand: 0 0
- Form: dry
- Life Stage: senior
- Has Ingredients: Yes
- Confidence: 0.7

**21 21 people have viewed this product in the last 30 days Josera YoungStar Type:...**
- Brand: 21 21
- Form: dry
- Life Stage: nan
- Has Ingredients: Yes
- Confidence: 0.5

## Brand Distribution

| Brand | Product Count | Percentage |
|-------|---------------|------------|
| 0 0 | 44 | 4.0% |
| 22 22 | 18 | 1.6% |
| 23 23 | 13 | 1.2% |
| 31 31 | 13 | 1.2% |
| 15 15 | 13 | 1.2% |
| 21 21 | 12 | 1.1% |
| 25 25 | 12 | 1.1% |
| 20 20 | 12 | 1.1% |
| 34 34 | 11 | 1.0% |
| 26 26 | 11 | 1.0% |
| 14 14 | 11 | 1.0% |
| 18 18 | 11 | 1.0% |
| 13 13 | 11 | 1.0% |
| 36 36 | 11 | 1.0% |
| 32 32 | 10 | 0.9% |

## Quality Metrics

- Products with valid form: 1076 (97.7%)
- Products with valid life_stage: 1016 (92.3%)
- Products with ingredients: 1101 (100.0%)
- Products with price data: 1095 (99.5%)
- Average confidence score: 0.68

## Known Issues

1. **Product Name Quality**: Names include view count prefixes that were cleaned
2. **Brand Extraction**: Relies on name parsing, may be inaccurate for complex names
3. **Price Assumptions**: Daily feeding amount assumption may vary by dog size
4. **URL Generation**: URLs are synthetic when not provided in source
