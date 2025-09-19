# PetFoodExpert.com Scraping Plan

## Executive Summary

After achieving 95.4% coverage for Zooplus products, the next major opportunity for improving database completeness is scraping **petfoodexpert.com**, which accounts for **100% of non-Zooplus products missing ingredients** (3,292 products).

## Current Database State

### Overall Statistics
- **Total products:** 8,926
- **With ingredients:** 5,136 (57.5%)
- **With nutrition:** 7,860 (88.1%)
- **Missing ingredients:** 3,790
- **Missing nutrition:** 1,066

### Source Breakdown
| Source | Total Products | Missing Ingredients | Coverage |
|--------|---------------|-------------------|----------|
| Zooplus | 3,510 | 160 | 95.4% ✅ |
| PetFoodExpert | 3,767 | 3,292 | 12.6% ❌ |
| Amazon | 16 | 15 | 6.3% ❌ |
| Petco | 5 | 4 | 20.0% ❌ |
| No URL | 414 | 220 | 46.9% ⚠️ |
| Others | ~1,214 | ~99 | 91.8% ✅ |

## PetFoodExpert.com Analysis

### Key Findings
1. **3,292 products missing ingredients** (87.4% of their catalog)
2. **3,610 products have nutrition data** (95.7% - already good!)
3. **Ingredients ARE available** on the website (confirmed via testing)
4. **Some URLs may be broken** (404 errors encountered)

### Top Brands Missing Ingredients
| Brand | Products Missing | Percentage |
|-------|-----------------|------------|
| Natures Menu | 83 | 2.5% |
| Wainwright's | 73 | 2.2% |
| Brit | 71 | 2.2% |
| Royal Canin | 70 | 2.1% |
| Happy Dog | 63 | 1.9% |
| Pets at Home | 58 | 1.8% |
| James Wellbeloved | 50 | 1.5% |
| Lily's Kitchen | 44 | 1.3% |
| Yorkshire Valley Farms | 42 | 1.3% |
| Dr John | 39 | 1.2% |

### Website Structure Analysis

#### Successful Test Scrape
```
URL: https://petfoodexpert.com/food/4paws-supplies-premium-cold-pressed-omega-salmon
Result: ✅ Ingredients found

Extracted:
- Product: "4PAWS Supplies Premium Cold Pressed Omega Salmon"
- Ingredients: "Dried ground salmon, sweet potato, peas, dried ground white fish, tapioca, chicken oil, yeast extract, dried ground chicken liver, beet pulp, salmon oil, seaweed, carnitine (50 mg/kg), MOS (400 mg/kg), yucca schidigera, chicory, inuline, natural antioxidants (vit.E and rosemary)"
```

#### Pattern Observations
- Ingredients are in a **dedicated section** on the page
- Clear labeling as "Ingredients"
- No JavaScript rendering required (simple HTML)
- Consistent format across products

## Proposed Scraping Strategy

### Phase 1: PetFoodExpert Bulk Scraping (Week 1)

#### 1.1 Infrastructure Setup
- Create `scrape_petfoodexpert_orchestrated.py` based on proven Zooplus scraper
- Use existing GCS pipeline (scrape → GCS → database)
- Implement extraction patterns specific to PetFoodExpert HTML structure

#### 1.2 Extraction Patterns
```python
# Primary pattern for PetFoodExpert
patterns = [
    r'Ingredients[:\s]*([^<]+)',  # Simple ingredients section
    r'<h3>Ingredients</h3>\s*<p>([^<]+)</p>',  # With HTML tags
    r'Ingredients.*?<div[^>]*>([^<]+)</div>',  # In div container
]
```

#### 1.3 Execution Plan
- **Batch size:** 500-1000 products per session
- **Concurrent sessions:** 3-5 (different country codes)
- **Rate limiting:** 10-20 seconds between requests
- **Error handling:** Skip 404s, retry 500s
- **Total time estimate:** 24-48 hours for all 3,292 products

### Phase 2: Minor Sources Cleanup (Day 3)

#### 2.1 Amazon Products (15 items)
- May require special handling for Amazon's anti-bot measures
- Consider using product API if available
- Manual fallback if needed (only 15 products)

#### 2.2 Petco Products (4 items)
- Standard scraping should work
- Test with one product first

### Phase 3: No-URL Products (Week 2)

#### 3.1 URL Discovery
- 414 products without URLs
- Search for products by name on likely sources
- Prioritize high-value brands (Royal Canin, etc.)

#### 3.2 Database Update
- Add discovered URLs to database
- Queue for scraping in next batch

### Phase 4: Quality Assurance (Ongoing)

#### 4.1 Validation
- Verify scraped ingredients make sense
- Check for truncation or encoding issues
- Compare with existing products for consistency

#### 4.2 Nutrition Data Gap
- 1,066 products still missing nutrition
- Cross-reference with PetFoodExpert nutrition data
- Update where available

## Implementation Timeline

| Phase | Duration | Products | Expected Coverage Gain |
|-------|----------|----------|----------------------|
| Setup & Testing | 1 day | 50 test | - |
| Phase 1: PetFoodExpert | 2-3 days | 3,292 | +36.9% |
| Phase 2: Minor Sources | 1 day | 19 | +0.2% |
| Phase 3: No-URL Discovery | 3-5 days | 200-400 | +2-4% |
| Phase 4: QA & Cleanup | Ongoing | - | - |
| **Total** | **1-2 weeks** | **~3,500** | **~40%** |

## Expected Outcomes

### Coverage Improvements
- **Current:** 57.5% products with ingredients
- **After Phase 1:** ~94% products with ingredients
- **After all phases:** ~96-97% products with ingredients

### Database Quality
- Near-complete ingredients coverage
- Consistent data across all major sources
- Foundation for nutritional analysis features

## Technical Requirements

### Infrastructure
- Existing ScrapingBee API (proven with Zooplus)
- Google Cloud Storage bucket (`lupito-content-raw-eu`)
- Supabase database connection
- Python environment with required packages

### Monitoring
- Real-time progress dashboard
- GCS file tracking
- Error logging and retry mechanisms
- Coverage statistics updates

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|---------|------------|
| Website structure changes | Low | High | Monitor first 100 scrapes closely |
| Rate limiting | Medium | Medium | Use multiple sessions, add delays |
| 404 errors | High | Low | Skip and log, continue with others |
| Data quality issues | Low | Medium | Validation checks, sample reviews |

## Success Criteria

1. ✅ Successfully scrape 80%+ of PetFoodExpert products
2. ✅ Achieve 90%+ overall ingredients coverage
3. ✅ Maintain data quality standards
4. ✅ Complete within 2 weeks
5. ✅ No service disruptions

## Next Steps

1. **Review and approve** this plan
2. **Create test scraper** for 50 PetFoodExpert products
3. **Validate extraction patterns** work consistently
4. **Launch full scraping operation**
5. **Monitor and adjust** as needed

## Appendix: Sample Products for Testing

### Products WITH Ingredients (Pattern Reference)
1. https://petfoodexpert.com/food/royal-canin-dalmatian-adult-dry-dog
2. https://petfoodexpert.com/food/angell-petco-superior-puppy-grain-free
3. https://petfoodexpert.com/food/royal-canin-labrador-retriever-adult-dry-dog

### Products MISSING Ingredients (To Scrape)
1. https://petfoodexpert.com/food/4paws-supplies-premium-cold-pressed-omega-salmon
2. https://petfoodexpert.com/food/4paws-supplies-premium-cold-pressed-tasty-chicken
3. https://petfoodexpert.com/food/4paws-supplies-working-dog-cold-pressed-brilliant-beef

---
*Document created: September 14, 2025*
*Purpose: Strategic plan for scraping 3,292 products from petfoodexpert.com to improve database coverage from 57.5% to ~94%*