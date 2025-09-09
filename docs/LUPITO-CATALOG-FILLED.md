# Lupito Catalog Consolidation Report

> **Generated:** 2025-09-09 19:36
> **Purpose:** Unify all `food_*` tables into one canonical catalog the AI can trust.

---

## 1) Executive Summary

- **Estimated unique products (pre-dedupe):** 5,191
- **Coverage snapshot (union of sources, before dedupe):**
  - Life stage known / `all` / `null`: 6.6% / 0% / 93.4%
  - kcal/100g known / **estimated** / missing: 44.7% / 0% / 55.3%
  - Ingredients tokens present: 47.5%
  - Availability has `"EU"` or a country: 95.0%
  - Price per kg or bucket present: 1.5%
  
- **Top 5 blockers:**
  1. Life stage data missing for 96.7% of food_candidates
  2. Ash and moisture percentages completely missing (100%)
  3. GTIN codes not populated in any table
  4. Ingredients raw text missing for 96.7% of products
  5. Price data sparse (only 3.2% have pricing)

- **Decisions we need today (checkboxes):**
  - [ ] Adopt `foods_canonical` → `foods_published` as AI source
  - [ ] Confirm price bucket thresholds (€3.5 / €7.0)
  - [ ] Treat `"EU"` as EU-wide availability
  - [ ] Life-stage relax rule (adult→`adult|all|null`, senior→`senior|all|null`)
  - [ ] Allergy synonyms map (treat "poultry" as chicken conflict)
  - [ ] Allow Atwater kcal estimates (flagged)

---

## 2) Inventory of Sources

| Source table/view | Type | Rows | Last updated | Notes |
|---|---|---:|---|---|
| food_candidates | table | 3,851 | 2025-09-09 | PFX/API + HTML |
| food_candidates_sc | table | 1,234 | 2025-09-09 | Scraper batch |
| food_brands | table | 106 | 2025-09-09 | Legacy seed |
| foods_published | view | 3,917 | - | Current AI view |

---

## 3.1 `food_candidates`

| Field | Null/Unknown % | Distribution / Notes |
|---|---:|---|
| life_stage | 96.7% | None `96.7%`, adult `2.9%`, puppy `0.2%`, all `0.1%`, senior `0.1%` |
| kcal_per_100g | 5.9% |  |
| ingredients_tokens | 0.0% | Vocab size ≈ 242 |
| available_countries | 0.0% |  |
| price_eur | 96.8% | Low `21.9%`, Mid `15.6%`, High `62.5%` |
| form | 43.2% | None `43.2%`, dry `41.4%`, wet `15.1%`, raw `0.3%` |

---

## 3.2 `food_candidates_sc`

| Field | Null/Unknown % | Distribution / Notes |
|---|---:|---|
| life_stage | 100.0% | None `100.0%` |
| kcal_per_100g | 100.0% |  |
| ingredients_tokens | 100.0% | Vocab size ≈ 0 |
| available_countries | 0.0% |  |
| form | 0.0% | dry `82.0%`, wet `18.0%` |

---

## 3.3 `food_brands`

| Field | Null/Unknown % | Distribution / Notes |
|---|---:|---|
| life_stage | 0.0% | adult `90.6%`, senior `3.8%`, puppy `3.8%`, puppy and adult `1.9%` |

---

## 4) Ingredients Token Health

- **Total tokens analyzed:** 597
- **Unique tokens:** 242
- **Top 30 tokens (with counts):**
  - `minerals` (18)
  - `glucosamine` (11)
  - `peas` (10)
  - `rice` (10)
  - `beet pulp` (9)
  - `yucca extract` (9)
  - `chondroitin` (9)
  - `cereals` (9)
  - `yeast` (8)
  - `meat and animal derivatives` (8)
  - `oils and fats` (8)
  - `turmeric` (7)
  - `milk thistle` (7)
  - `maize` (7)
  - `carrot` (6)
  - `oregano` (6)
  - `cranberries` (6)
  - `tomato` (5)
  - `seaweed` (5)
  - `refined chicken oil` (5)
  - `krill` (5)
  - `prebiotic fos` (5)
  - `prebiotic mos` (5)
  - `msm` (5)
  - `ginger` (5)
  - `cranberry` (4)
  - `thyme` (4)
  - `rosehip` (4)
  - `marigold` (4)
  - `aniseed` (4)

- **Allergy-critical presence (% of all tokens):**
  - chicken: `6.4%`
  - poultry: `1.5%`
  - chicken meal: `0.3%`
  - hydrolyzed chicken: `0.0%`
  - egg: `1.3%`
  - beef: `0.5%`
  - lamb: `0.7%`
  - fish: `1.2%`
  - salmon: `1.3%`
  - trout: `0.0%`
  - turkey: `0.2%`
  - duck: `0.3%`

---

## 5) Overlap & Duplicates (before dedupe)

- **Proposed `product_key`:** `slug(brand) | slug(product_name) | form`
- **Overlap counts between tables:**
  - food_candidates_vs_food_candidates_sc: 0 products
  - food_candidates_vs_food_brands: 0 products
  - food_candidates_sc_vs_food_brands: 0 products

---

## 6) Canonicalization Rules (to be implemented)

- **Precedence per `product_key`:**
  1) `kcal_per_100g`: known > estimated > null
  2) `life_stage`: specific (`puppy|adult|senior`) > `all` > `null`
  3) **Ingredients richness** (more tokens)
  4) `price_per_kg` present > missing
  5) `updated_at` newest

- **Availability merge:** if any source has `"EU"` → include `"EU"`; union all country codes
- **Quality score formula:** completeness * 0.4 + accuracy * 0.3 + freshness * 0.3

---

## 7) Decisions Needed (tick to approve)

- [ ] Flip AI to `foods_published` (now backed by `foods_canonical`)
- [ ] Approve **bucket thresholds** (Low ≤ €3.5/kg, Mid €3.5–7.0/kg, High > €7.0/kg)
- [ ] Approve **EU wildcard** rule
- [ ] Approve **life-stage relax** rule
- [ ] Approve **allergy synonyms** list (poultry=chicken conflict)
- [ ] Approve **Atwater estimation** policy (`kcal_is_estimated=true` flag)

---

## 8) Next Actions

- [ ] Create unified `foods_canonical` table with deduplication
- [ ] Implement canonicalization rules in ETL pipeline
- [ ] Add/confirm DB indexes:
  - `UNIQUE(product_key)`
  - btree: `brand_slug`, `life_stage`
  - GIN: `available_countries`, `ingredients_tokens`
- [ ] Admin QA presets (adult, senior, puppy, chicken-allergy, budget-low)
- [ ] Point AI env `CATALOG_VIEW_NAME=foods_published` and verify row count

---

**End of report.**
