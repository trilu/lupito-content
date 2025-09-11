# Wave-Next-3 Harvest Plan

**Generated:** 2025-09-11T22:07:00  
**Scope:** foods_published_preview (Preview environment)  
**Target:** 3 highest-impact brands excluding already-harvested brands  

## Executive Summary

After B1A success with Bozita (64.4% coverage), Belcando (35.3%), and Briantos (34.0%), Wave-Next-3 targets the next highest-impact accessible brands:

1. **Brit** - Czech premium pet food (65 SKUs, 84.6% ingredient gap)
2. **Alpha Spirit** - Spanish/European pet food (47 SKUs, 78.7% gap)  
3. **Bosch** - German pet food manufacturer (31 SKUs, 93.5% gap)

**Combined impact potential:** 12,096 points (143 total SKUs with significant ingredient gaps)

---

## Brand Selection Methodology

**Impact Formula:** `SKU count × (100 - ingredients_coverage)`

**Exclusion Criteria:**
- Already harvested: bozita, belcando, briantos ❌
- Domain inaccessible: arden, barking, borders, burns ❌
- Insufficient SKU count: <20 products ❌

**Final Selection:**
| Rank | Brand | SKUs | Gap% | Impact | Domain Status |
|------|-------|------|------|---------|---------------|
| 1 | Brit | 65 | 84.6% | 5,499 | ✅ Accessible |
| 2 | Alpha | 47 | 78.7% | 3,699 | ✅ Accessible |
| 3 | Bosch | 31 | 93.5% | 2,898 | ✅ Accessible |

---

## 1. BRIT (Czech Premium Pet Food)

### Brand Profile
- **Official Domain:** `brit-petfood.com` → redirects to `/en/`
- **Languages:** 25+ supported (English primary for harvest)
- **Product Range:** ~380 products across dogs, cats, rodents
- **Market Position:** Premium European brand with detailed nutritional data

### Technical Specifications
- **Product Listing URLs:**
  - Dogs: `/en/products/dogs` (19 pages × ~20 products)
  - Cats: `/en/products/cats`
  - All Products: `/en/products`
- **Individual Product Pattern:** `/en/products/dogs/[id]-[slug]`
- **Robots.txt Status:** Generally permissive (blocks admin, allows product crawling)
- **Content Format:** Structured HTML with detailed composition sections

### Data Locations & Parsing Focus
- **Ingredients:** "Composition" section with precise percentages
- **Nutrition:** "Analytical ingredients" + "Nutritional composition"
- **Form:** Clearly labeled (Adult, Puppy, Senior, etc.)
- **Life Stage:** Systematically categorized
- **Kcal:** Listed as kcal/100g in nutrition sections

### Harvest Strategy
- **Seed URLs:** Start with `/en/products` sitemap
- **Throttling:** 2-3 seconds between requests (respect Czech servers)
- **Headers:** Standard User-Agent, Accept-Language: en
- **Expected Volume:** ~380 product pages
- **Auth Requirements:** None

---

## 2. ALPHA SPIRIT (Spanish/European Pet Food)

### Brand Profile  
- **Official Domain:** `aspiritpetfood.store` (Alpha Spirit brand)
- **Languages:** Spanish primary, some English
- **Product Range:** ~47+ products across multiple sub-brands
- **Market Position:** European premium with natural/raw focus

### Technical Specifications
- **Product Listing URLs:**
  - Dogs: `/collections/perros`
  - Cats: `/collections/gatos`
  - All: `/collections/all`
- **Individual Product Pattern:** `/products/[slug]`
- **Robots.txt Status:** Standard e-commerce (accessible)
- **Content Format:** Modern Shopify-based structure

### Data Locations & Parsing Focus
- **Ingredients:** Product description sections
- **Nutrition:** "Analytical constituents" when available
- **Form:** Inferred from product names/descriptions
- **Life Stage:** Product categorization
- **Kcal:** Variable availability, extract where present
- **Language Challenge:** Spanish content may need translation

### Harvest Strategy
- **Seed URLs:** `/collections/all` or collection pages
- **Throttling:** 1-2 seconds (Shopify infrastructure)
- **Headers:** Accept-Language: es,en for broader content
- **Expected Volume:** ~47 product pages
- **Special Handling:** Spanish→English ingredient translation may be needed

---

## 3. BOSCH (German Pet Food Manufacturer)

### Brand Profile
- **Official Domain:** `bosch-tiernahrung.de` (German pet nutrition division)
- **Languages:** German primary, English available
- **Product Range:** ~31 products, premium dry/wet food
- **Market Position:** Established German manufacturer with technical focus

### Technical Specifications
- **Product Listing URLs:**
  - `/en/products` (English version)
  - `/produkte` (German version)
- **Individual Product Pattern:** `/en/products/[category]/[slug]`
- **Robots.txt Status:** Accessible for product pages
- **Content Format:** Technical German-style structured data

### Data Locations & Parsing Focus
- **Ingredients:** "Zusammensetzung" or "Ingredients" sections
- **Nutrition:** "Analytische Bestandteile" (analytical constituents)
- **Form:** Clearly specified (Trockenfutter/dry, Nassfutter/wet)
- **Life Stage:** Age/size category specifications
- **Kcal:** Technical nutritional data sections

### Harvest Strategy
- **Seed URLs:** `/en/products` (English preferred)
- **Throttling:** 2-3 seconds (German server consideration)
- **Headers:** Accept-Language: en,de
- **Expected Volume:** ~31 product pages
- **Fallback:** German version if English incomplete

---

## Acceptance Gates (Preview Environment)

Each brand must achieve before promotion to Production:

### Primary Gates
- **Ingredients Coverage:** ≥85% of SKUs have non-empty `ingredients_tokens`
- **Kcal Accuracy:** ≥90% of products have `kcal_per_100g` in 200-600 range
- **Form Classification:** ≥90% have valid `form` (dry/wet/treat/raw)
- **Life Stage Classification:** ≥90% have valid `life_stage` (puppy/adult/senior)

### Quality Gates  
- **Zero Outliers:** 0 kcal values outside 200-600 range in target products
- **Ingredient Parsing:** >50% of extracted ingredients successfully canonicalized
- **No Duplicates:** All `product_key` values unique within brand

### Technical Gates
- **Harvest Success:** >90% of identified product URLs successfully scraped
- **Parse Success:** >80% of scraped pages yield extractable ingredient data  
- **Error Rate:** <10% HTTP/parsing failures during harvest

---

## Implementation Timeline

### Phase 1: Brit (Priority 1)
- **Week 1:** Domain research, selector development, small-scale test (10 products)
- **Week 2:** Full harvest execution, data validation, acceptance gate review
- **Expected Outcome:** 65 SKUs → 85%+ ingredients coverage

### Phase 2: Alpha Spirit (Priority 2)  
- **Week 3:** Spanish content analysis, translation pipeline setup
- **Week 4:** Harvest execution with language handling
- **Expected Outcome:** 47 SKUs → 85%+ ingredients coverage

### Phase 3: Bosch (Priority 3)
- **Week 5:** German technical documentation parsing
- **Week 6:** Final harvest and validation
- **Expected Outcome:** 31 SKUs → 85%+ ingredients coverage

### Consolidation
- **Week 7:** Cross-brand validation, Preview environment testing
- **Week 8:** Production promotion readiness assessment

---

## Risk Mitigation

### Technical Risks
- **Rate Limiting:** All brands use conservative throttling (2-3 sec intervals)
- **Language Barriers:** Spanish/German content handling with fallback strategies
- **Parsing Complexity:** Brand-specific selector development based on B1A learnings

### Business Risks  
- **Domain Changes:** Monitor for site restructuring during harvest period
- **Legal Compliance:** All harvesting respects robots.txt and terms of service
- **Data Quality:** Staging→merge workflow prevents production contamination

### Operational Risks
- **Harvest Failures:** Retry mechanisms and manual fallback procedures
- **Coverage Shortfalls:** B2/B3 strategies ready for brands not meeting 85% gate
- **Timeline Delays:** Staggered execution allows reallocation of resources

---

## Success Metrics

**Target Outcomes (Preview Environment):**
- **Brit:** 15.4% → 85%+ ingredients coverage (+69.6% lift)
- **Alpha:** 21.3% → 85%+ ingredients coverage (+63.7% lift) 
- **Bosch:** 6.5% → 85%+ ingredients coverage (+78.5% lift)

**Combined Impact:** ~211.8% total coverage increase across 143 high-value SKUs

**Quality Assurance:** All products meet kcal, form, and life_stage classification standards for Preview→Production promotion readiness.