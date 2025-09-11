# B1: Brand-Specific HTML Extraction Report

**Generated:** 2025-09-11T21:15:34.095558
**Brands:** bozita, belcando, briantos
**Method:** Enhanced selector-based extraction

## BOZITA

### Coverage Results
- **Products:** 34
- **Ingredients:** 0.0% → 0.0% (+0.0%)
- **Macros:** 100.0% → 100.0%
- **Kcal:** 79.4% → 79.4%

### Successful Extractions (10 examples)
1. **dog-food.html** - Extracted 67 ingredients (selector: text_protein_chicken)
2. **dog-food_adult-large-salmon-beef.html** - Extracted 58 ingredients (selector: text_protein_beef)
3. **dog-food_bozita-meaty-bites-duck.html** - Extracted 32 ingredients (selector: text_protein_lamb)
4. **dog-food_bozita-meaty-bites-elk-duck.html** - Extracted 34 ingredients (selector: text_protein_lamb)
5. **dog-food_bozita-meaty-bites-lamb.html** - Extracted 34 ingredients (selector: text_protein_lamb)
6. **dog-food_bozita-meaty-bites-reindeer-duck.html** - Extracted 33 ingredients (selector: text_protein_lamb)
7. **dog-food_bozita-meaty-bites-venison-duck.html** - Extracted 33 ingredients (selector: text_protein_lamb)
8. **dog-food_bozita-original-adult-classic.html** - Extracted 51 ingredients (selector: text_protein_lamb)
9. **dog-food_bozita-original-adult-flavour-plus.html** - Extracted 54 ingredients (selector: text_protein_lamb)
10. **dog-food_bozita-original-adult-light.html** - Extracted 54 ingredients (selector: text_protein_lamb)

### Failed Extractions (5 examples)
1. **dog-food_nutrition-and-diet.html** - No ingredients found in HTML
2. **sitemap.html** - No ingredients found in HTML

### Selectors Used
- `text_protein_chicken`
- `text_protein_beef`
- `text_protein_lamb`

## BELCANDO

### Coverage Results
- **Products:** 34
- **Ingredients:** 2.9% → 2.9% (+0.0%)
- **Macros:** 97.1% → 97.1%
- **Kcal:** 97.1% → 97.1%

### Successful Extractions (10 examples)
1. **nassfutter_baseline.html** - Extracted 11 ingredients (selector: text_protein_beef)
2. **nassfutter_frischebeutel.html** - Extracted 11 ingredients (selector: text_protein_beef)
3. **nassfutter_holistic.html** - Extracted 6 ingredients (selector: text_protein_beef)
4. **nassfutter_menuedosen.html** - Extracted 11 ingredients (selector: text_protein_beef)
5. **nassfutter_single-protein-dosen.html** - Extracted 2 ingredients (selector: div.product-info)
6. **nassfutter_toppings.html** - Extracted 6 ingredients (selector: div.product-info)
7. **probierboxen_nassfutter.html** - Extracted 3 ingredients (selector: div.product-info)
8. **probierboxen_welpen-junghunde.html** - Extracted 11 ingredients (selector: div.product-info)
9. **produkte.html** - Extracted 11 ingredients (selector: div.product-info)
10. **produkte_nassfutter.html** - Extracted 2 ingredients (selector: div.product-info)

### Failed Extractions (5 examples)
1. **sitemap.html** - No ingredients found in HTML

### Selectors Used
- `text_protein_beef`
- `div.product-info`

## BRIANTOS

### Coverage Results
- **Products:** 46
- **Ingredients:** 32.6% → 32.6% (+0.0%)
- **Macros:** 93.5% → 93.5%
- **Kcal:** 93.5% → 93.5%

### Successful Extractions (10 examples)
1. **produkte.html** - Extracted 29 ingredients (selector: text_search_composition)

### Failed Extractions (5 examples)
1. **sitemap.html** - No ingredients found in HTML

### Selectors Used
- `text_search_composition`

## Acceptance Gate Results

❌ **BOZITA**: 0.0% < 60% - NEEDS B2/B3
❌ **BELCANDO**: 2.9% < 60% - NEEDS B2/B3
❌ **BRIANTOS**: 32.6% < 60% - NEEDS B2/B3

## Next Steps
- For brands passing 60%: Continue to next phase
- For brands <60%: Implement B2 (JavaScript rendering) and B3 (PDF extraction)
