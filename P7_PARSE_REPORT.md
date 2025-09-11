# P7: Manufacturer Snapshot Parse Report

**Generated:** 2025-09-11T20:47:34.184667
**Source:** gs://lupito-content-raw-eu/manufacturers/
**Brands Processed:** bozita, belcando, briantos

## Summary

- **Total Products Processed:** 80
- **Total Ingredients Extracted:** 68
- **Total Macros Extracted:** 0
- **Total Kcal Extracted:** 0

## BOZITA

**Total products parsed:** 59

### Extraction Results
- Ingredients extracted: 50
- Macros extracted: 0
- Kcal extracted: 0

### Coverage (Before → After)
- **Ingredients (non-empty tokens):** 0.0% → 0.0% (+0 products)
- **Macros (protein + fat present):** 100.0% → 100.0% (+0 products)
- **Kcal (200-600 range):** 79.4% → 79.4% (+0 products)

### Example Rows (5 samples)

**1. Dog food - Bozita International**
   - Fields updated: ingredients_raw, ingredients_tokens, ingredients_language, ingredients_parsed_at, ingredients_source
   - Ingredients tokens: 67

**2. Purely Adult Large Salmon & Beef - Bozita Internat**
   - Fields updated: ingredients_raw, ingredients_tokens, ingredients_language, ingredients_parsed_at, ingredients_source
   - Ingredients tokens: 58

**3. ORIGINAL ADULT CLASSIC - Bozita International**
   - Fields updated: ingredients_raw, ingredients_tokens, ingredients_language, ingredients_parsed_at, ingredients_source
   - Ingredients tokens: 51

**4. ORIGINAL ADULT FLAVOUR PLUS - Bozita International**
   - Fields updated: ingredients_raw, ingredients_tokens, ingredients_language, ingredients_parsed_at, ingredients_source
   - Ingredients tokens: 54

**5. ORIGINAL ADULT LIGHT - Bozita International**
   - Fields updated: ingredients_raw, ingredients_tokens, ingredients_language, ingredients_parsed_at, ingredients_source
   - Ingredients tokens: 54


## BELCANDO

**Total products parsed:** 19

### Extraction Results
- Ingredients extracted: 18
- Macros extracted: 0
- Kcal extracted: 0

### Coverage (Before → After)
- **Ingredients (non-empty tokens):** 2.9% → 2.9% (+0 products)
- **Macros (protein + fat present):** 97.1% → 97.1% (+0 products)
- **Kcal (200-600 range):** 97.1% → 97.1% (+0 products)

### Example Rows (5 samples)

**1. Baseline**
   - Fields updated: ingredients_raw, ingredients_tokens, ingredients_language, ingredients_parsed_at, ingredients_source
   - Ingredients tokens: 11

**2. Nassfutter im Frischebeutel**
   - Fields updated: ingredients_raw, ingredients_tokens, ingredients_language, ingredients_parsed_at, ingredients_source
   - Ingredients tokens: 11

**3. Holistic**
   - Fields updated: ingredients_raw, ingredients_tokens, ingredients_language, ingredients_parsed_at, ingredients_source
   - Ingredients tokens: 6

**4. Dosenfutter für Hunde**
   - Fields updated: ingredients_raw, ingredients_tokens, ingredients_language, ingredients_parsed_at, ingredients_source
   - Ingredients tokens: 11

**5. Single Protein**
   - Fields updated: ingredients_raw, ingredients_tokens, ingredients_language, ingredients_parsed_at, ingredients_source
   - Ingredients tokens: 11


## BRIANTOS

**Total products parsed:** 2

### Extraction Results
- Ingredients extracted: 0
- Macros extracted: 0
- Kcal extracted: 0

### Coverage (Before → After)
- **Ingredients (non-empty tokens):** 32.6% → 32.6% (+0 products)
- **Macros (protein + fat present):** 93.5% → 93.5% (+0 products)
- **Kcal (200-600 range):** 93.5% → 93.5% (+0 products)


## P7 Rules Compliance

✓ **Upsert by product_key:** Products updated/created using unique keys
✓ **Non-null preservation:** Only updating fields with actual values
✓ **JSONB arrays:** ingredients_tokens stored as proper arrays
✓ **Language detection:** Detecting language (sv, de, en) for all content
✓ **Canonical mapping:** Applied ingredient canonicalization
✓ **Unit normalization:** Converting kJ to kcal where found
✓ **Change logging:** Tracking all field updates
✓ **Source tracking:** Setting ingredients_source, macros_source, kcal_source
