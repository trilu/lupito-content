# Foods Enrichment Before/After P7 Report

**Generated:** 2025-09-11T20:56:54.622753
**Brands:** bozita, belcando, briantos
**Total Products Analyzed:** 114

## Executive Summary

### Overall Coverage ❌ TODO

- **Ingredients Tokens:** 14.0% (16/114)
- **Valid Kcal (200-600):** 90.4% (103/114)
- **Language Detection:** 100.0% (114/114)

### Macros Coverage Tiers

1. **Protein Only:** 96.5% (110/114) ✅ PASS
2. **Protein + Fat:** 96.5% (110/114) ✅ PASS
3. **All 5 Macros:** 0.0% (0/114) ❌ TODO

## Per-Brand Analysis

### BOZITA

**Products:** 34

| Metric | BEFORE P7 | AFTER P7 | Change | Status |
|--------|-----------|----------|--------|--------|
| Ingredients Tokens | 0% | 0.0% | +0.0% | ❌ TODO |
| Valid Kcal (200-600) | 79.4% | 79.4% | 0% | ⚠️ NEAR |
| Protein Present | 100.0% | 100.0% | 0% | ✅ PASS |
| Protein + Fat | 100.0% | 100.0% | 0% | ✅ PASS |
| All 5 Macros | 0.0% | 0.0% | 0% | ❌ TODO |
| Language Set | 0% | 100.0% | +100.0% | ✅ PASS |

### BELCANDO

**Products:** 34

| Metric | BEFORE P7 | AFTER P7 | Change | Status |
|--------|-----------|----------|--------|--------|
| Ingredients Tokens | 0% | 2.9% | +2.9% | ❌ TODO |
| Valid Kcal (200-600) | 97.1% | 97.1% | 0% | ✅ PASS |
| Protein Present | 97.1% | 97.1% | 0% | ✅ PASS |
| Protein + Fat | 97.1% | 97.1% | 0% | ✅ PASS |
| All 5 Macros | 0.0% | 0.0% | 0% | ❌ TODO |
| Language Set | 0% | 100.0% | +100.0% | ✅ PASS |

### BRIANTOS

**Products:** 46

| Metric | BEFORE P7 | AFTER P7 | Change | Status |
|--------|-----------|----------|--------|--------|
| Ingredients Tokens | 15% | 32.6% | +17.6% | ❌ TODO |
| Valid Kcal (200-600) | 93.5% | 93.5% | 0% | ✅ PASS |
| Protein Present | 93.5% | 93.5% | 0% | ✅ PASS |
| Protein + Fat | 93.5% | 93.5% | 0% | ✅ PASS |
| All 5 Macros | 0.0% | 0.0% | 0% | ❌ TODO |
| Language Set | 0% | 100.0% | +100.0% | ✅ PASS |

## Top Blockers Analysis

### Identified Issues

1. **Nutrition Pdf Only:** Affecting ~98 products
1. **Units Kj:** Affecting ~7 products

### Specific Blockers by Type

#### Nutrition Data Issues
- **Hidden behind tabs:** Product pages use JavaScript tabs for nutrition
- **PDF/Image only:** Nutrition data only available in downloadable PDFs
- **Units in kJ:** Energy values given in kilojoules, not kilocalories
- **Per kg not per 100g:** Values given per kilogram instead of per 100g

#### Technical Issues
- **JavaScript rendering:** Content loaded dynamically after page load
- **Incomplete HTML:** Snapshots captured before full page load

## Sample Rows with New Ingredients (10 Examples)

| Product | Tokens Count | Language | Source | Sample Ingredients |
|---------|--------------|----------|--------|--------------------|
| Adult Chicken  Rice | 7 | en | site | chicken, rice, barley... |
| Adult Grain-Free Lamb  Potato | 7 | en | site | chicken, rice, corn... |
| Adult Grain-Free Salmon  Potato | 7 | en | site | salmon, potato, peas... |

## Recommendations

### Immediate Actions
1. **Re-parse with enhanced extractors** for products missing ingredients
2. **Handle kJ to kcal conversion** in parser
3. **Implement JavaScript rendering** for dynamic content

### Future Improvements
1. **PDF extraction pipeline** for nutrition sheets
2. **Image OCR** for nutrition labels in images
3. **Multi-pass parsing** with different strategies

## Success Metrics

### ❌ P7 NEEDS IMPROVEMENT
- Only 14.0% ingredients coverage
- Major blockers preventing extraction
