# Lupito Catalog Consolidation Report

> **Purpose:** Decide how to unify all `food_*` tables into one canonical catalog the AI can trust.  
> **Scope:** `food_candidates`, `food_candidates_sc`, `food_brands` (plus any other `food_*`) and current published views.

> **Instructions for Claude Code:**  
> - Run your analysis script over Supabase and **fill every placeholder** below with real numbers, tables, and short summaries.  
> - Do **not** include raw secrets.  
> - Keep this file human-friendly and decision-oriented.

---

## 1) Executive Summary

- **Estimated unique products (pre-dedupe):** `N`
- **Coverage snapshot (union of sources, before dedupe):**
  - Life stage known / `all` / `null`: `X% / Y% / Z%`  *(target ≥ 95% known or `all`)*  
  - kcal/100g known / **estimated** / missing: `X% / Y% / Z%`  *(target ≥ 90% known+estimated)*  
  - Ingredients tokens present: `X%`  *(target ≥ 95%)*  
  - Availability has `"EU"` or a country: `X%`  *(target ≥ 90%)*  
  - Price per kg or bucket present: `X%`  *(target ≥ 85%)*  
- **Top 5 blockers** *(1–2 lines each)*  
  1. …  
  2. …  
  3. …  
  4. …  
  5. …
- **Decisions we need today (checkboxes):**
  - [ ] Adopt `foods_canonical` → `foods_published` as AI source
  - [ ] Confirm price bucket thresholds
  - [ ] Treat `"EU"` as EU-wide availability
  - [ ] Life-stage relax rule (adult→`adult|all|null`, senior→`senior|all|null`)
  - [ ] Allergy synonyms map (treat “poultry” as chicken conflict)
  - [ ] Allow Atwater kcal estimates (flagged)

---

## 2) Inventory of Sources

| Source table/view | Type | Rows | Last updated | Notes |
|---|---|---:|---|---|
| food_candidates | table | … | … | PFX/API + HTML |
| food_candidates_sc | table | … | … | Scraper batch |
| food_brands | table | … | … | Legacy seed |
| foods_published (current) | view | … | – | Current AI view |
| other `food_*` | … | … | … | … |

---

## 3) Field-Level Data Quality (per primary source)

> **For each of:** `food_candidates`, `food_candidates_sc`, `food_brands`.

### 3.a `<source_name>`

| Field | Null/Unknown % | Distribution / Notes |
|---|---:|---|
| life_stage | …% | Puppy `…%`, Adult `…%`, Senior `…%`, All `…%`, Null `…%` |
| kcal_per_100g | …% | Of missing, have protein+fat: `…%` |
| protein_percent | …% | – |
| fat_percent | …% | – |
| ingredients_tokens | …% | Vocab size ≈ `…` |
| available_countries | …% | `"EU"` present in `…%` |
| price_per_kg / bucket | …% | Buckets: Low `…%`, Mid `…%`, High `…%` |
| form | …% | Dry `…%`, Wet `…%`, Other `…%` |

**Life-stage alias hit-rates:**  
- `senior|mature|7+` → `…` rows  
- `puppy|junior|growth` → `…`  
- `adult|maintenance` → `…`  
- `all life stages` → `…`

---

## 4) Ingredients Token Health

- **Top 30 tokens (with counts):**  
  `token (count)`, …
- **Allergy-critical synonyms (presence % across union):**
  - chicken `…%` · poultry `…%` · chicken meal `…%` · hydrolyzed chicken protein `…%` · egg `…%`
  - beef `…%` · lamb `…%` · fish `…%` · salmon `…%` · trout `…%` · turkey `…%` · duck `…%`
- **Ambiguity:** % rows with **only** “poultry” (no “chicken” token): `…%`
- **Primary protein detected:** `…%` of rows

---

## 5) Availability Coverage (union of sources)

- `%` with `"EU"` in `available_countries`: `…%`  
- `%` with any ISO country: `…%`  
- `%` null/empty: `…%`  
- **Top 5 retailers/sources** by count and their availability patterns:  
  1. …  
  2. …  

---

## 6) Price Coverage & Buckets

- `%` with `price_per_kg`: `…%`
- **Bucket thresholds used:** Low ≤ `…` €/kg, Mid `…–…` €/kg, High > `…` €/kg
- **Bucket distribution:** Low `…%`, Mid `…%`, High `…%`
- **Outliers:** Top/bottom 10 `price_per_kg` with brand + product

---

## 7) Overlap & Duplicates (before dedupe)

- **Proposed `product_key`:** `slug(brand) | slug(product_name) | form` *(note if size is included)*  
- Keys seen in **≥2 sources:** `N`  
- **Conflict types (counts):**
  - Same product_name, **different kcal**: `N`
  - **Different life_stage** across sources: `N`
  - Token conflicts (e.g., one has chicken, other doesn’t): `N`
- **Example conflict cluster (1–3 examples):** side-by-side rows (brand, name, form, kcal, life_stage, tokens highlights)

---

## 8) Canonicalization Rules (used by the script)

- **Precedence per `product_key`:**
  1) `kcal_per_100g`: known > estimated > null  
  2) `life_stage`: specific (`puppy|adult|senior`) > `all` > `null`  
  3) **Ingredients richness** (more tokens)  
  4) `price_per_kg` present > missing  
  5) `quality_score` higher  
  6) `updated_at` newest
- **Availability merge:** if any source has `"EU"` → include `"EU"`; union all country codes
- **Provenance:** `sources` JSON list of contributing rows
- **Quality score formula:** *(list the weights you used)*

---

## 9) Post-Unify Coverage (foods_canonical / foods_published)

| Metric | Before (best of sources) | After (canonical) | Target |
|---|---:|---:|---:|
| Unique products | … | … | – |
| Life stage known or `all` | …% | …% | ≥ 95% |
| kcal known + estimated | …% | …% | ≥ 90% |
| Ingredients tokens present | …% | …% | ≥ 95% |
| Availability has `"EU"` or country | …% | …% | ≥ 90% |
| Price present | …% | …% | ≥ 85% |

- **Duplicates merged:** `N`  
- **Top brands by count (post-unify):** list top 10  
- **Dry vs Wet split (post-unify):** Dry `…%` · Wet `…%` · Other `…%`

---

## 10) Risks & Anomalies

- Brands with **no kcal** and **no protein/fat** (5–10 examples)
- Rows with only “poultry” (no “chicken”) — potential allergy ambiguity
- Suspicious life_stage strings not matched by aliases
- Extreme `price_per_kg` outliers (with names)

---

## 11) Decisions Needed (tick to approve)

- [ ] Flip AI to `foods_published` (now backed by `foods_canonical`)  
- [ ] Approve **bucket thresholds** listed above  
- [ ] Approve **EU wildcard** rule  
- [ ] Approve **life-stage relax** rule  
- [ ] Approve **allergy synonyms** list (poultry=chicken conflict)  
- [ ] Approve **Atwater estimation** policy (`kcal_is_estimated=true` flag)

---

## 12) Next Actions

- [ ] Refresh pipeline: sources → compat views → union → canonical (idempotent)  
- [ ] Add/confirm DB indexes:  
  - `UNIQUE(product_key)`  
  - btree: `brand_slug`, `life_stage`  
  - GIN: `available_countries`, `ingredients_tokens`  
- [ ] Admin QA presets (adult, senior, puppy, chicken-allergy, budget-low)  
- [ ] Point AI env `CATALOG_VIEW_NAME=foods_published` and verify row count via debug

---

## Appendix A — Aliases & Mappings

**Form aliases:** kibble/dry → `dry`; canned/tin → `wet`; freeze-dried; raw; etc.  
**Life-stage aliases:**  
- `senior|mature|7+|8+|aging` → `senior`  
- `puppy|junior|growth` → `puppy`  
- `adult|maintenance` → `adult`  
- `all life stages|complete for all ages` → `all`

**Protein synonyms:** chicken ↔ poultry ↔ chicken meal ↔ hydrolyzed chicken protein ↔ egg;  
fish ↔ salmon/trout/whitefish; beef; lamb; turkey; duck.

**Atwater factors:** 3.5 (protein), 8.5 (fat), 3.5 (carbs) kcal/g (note if carbs assumed).  
**Budget buckets (proposed):** Low ≤ **€3.5/kg** · Mid **€3.5–7.0/kg** · High > **€7.0/kg**.

---

## Appendix B — Samples

- Path to `catalog_sample.csv` (50 rows; brand, product_name, form, life_stage, kcal_known/estimated, primary_protein, has_chicken, available_countries, price_bucket).  
- Links/paths to anomaly CSVs (if any).

---

**End of report.**
