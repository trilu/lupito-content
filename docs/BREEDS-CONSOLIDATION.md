# Breeds Consolidation — Runbook & Report Template

> **Goal:** unify multiple `breed*` tables into one canonical `breeds_canonical` view/table the AI and Admin can trust.  
> **Use:** Paste the prompts (no code) into the **Content repo** Claude session so it can analyze & build. Fill this report with the generated facts.

---

## 0) Executive Summary (to be filled by Claude)
- Sources inspected: `…`
- Total raw rows across sources: `…`
- Unique breeds after aliasing: `…`
- Coverage (canonical targets):
  - `size_category` filled: `…%` (target ≥ 95%)
  - `growth_end_months` filled: `…%` (target ≥ 90%)
  - `senior_start_months` filled: `…%` (target ≥ 90%)
  - `activity_baseline` filled: `…%` (target ≥ 90%)
- Dogs linkage: `…%` of dogs matched to a canonical breed via slug/alias
- Top blockers (1–2 lines each):
  1. …
  2. …
  3. …

---

## 1) Source Inventory
List all tables/views that may contain breed info.

| Source | Type | Rows | Last Updated | Key Columns Found | Notes |
|---|---|---:|---|---|---|
| `breed_catalog` | table | … | … | name, size, activity | legacy |
| `breeds_scraped` | table | … | … | name_raw, traits_json | scraper |
| `breed_raw` | table | … | … | html_path, parsed_json | raw |
| … | … | … | … | … | … |

**Discovery query used:** `…`

---

## 2) Field Coverage per Source
For each source, report % filled for core fields and any variants that need mapping.

**Fields we care about (canonical):**
- `breed_name`, `breed_slug`
- `size_category` ∈ {xs, s, m, l, xl}
- `growth_end_months` *(puppy→adult)*
- `senior_start_months`
- `activity_baseline` ∈ {low, moderate, high, very_high}
- `energy_factor_mod` (float, default 0.0; bounds −0.10..+0.10)
- *(optional)* `ideal_weight_min_kg`, `ideal_weight_max_kg`

### Example block (repeat per source)
**Source:** `breeds_scraped`
- Rows: `…`
- Coverage:
  - size: `…%`
  - growth_end_months: `…%` (min `…`, p50 `…`, max `…`)
  - senior_start_months: `…%`
  - activity_baseline: `…%` (low `…%`, moderate `…%`, high `…%`, very_high `…%`)
  - energy_factor_mod: `…%` (mean `…`, min `…`, max `…`)
- Notable variants to normalize: `height`, `weight_range`, `group`, `exercise_needs`, etc.

---

## 3) Alias & Duplicate Analysis
We need a **canonical name + slug** and a **breed_aliases** mapping.

- Canonicalization steps that will be applied:
  - strip punctuation & parentheses, collapse whitespace, lowercase
  - convert diacritics, standardize hyphens/spaces
  - remove suffixes like “dog”, “hound” only when safe
- **Clusters (examples):** show 5 clusters where aliases collapse into one canonical.
- **Conflicts:** cases where two distinct breeds share a near-identical name; propose disambiguators.

**Deliverables:**
- `breed_aliases` table (alias → canonical_slug)
- Final canonical list (slug, name, size, growth/senior cutoffs, activity, energy_factor_mod)

---

## 4) Dogs Table Linkage
How many existing dogs can be auto-matched to canonical breeds?

| Metric | Value |
|---|---:|
| Dog records total | … |
| With breed name present | … |
| With breed_id present | … |
| Mapped to canonical by slug | … (`…%`) |
| Unmapped (need manual or fuzzy) | … |

- If unmapped > 5–10%, propose a minimal manual alias list for the top unmapped names.

---

## 5) Canonical Schema (what we will publish)
**Table/View:** `breeds_canonical`

| Column | Type | Notes |
|---|---|---|
| `breed_id` | uuid/text | Stable id (can be slug if no UUIDs yet) |
| `breed_name` | text | Canonical display name |
| `breed_slug` | text unique | Lowercase, URL-safe |
| `size_category` | enum | xs/s/m/l/xl |
| `growth_end_months` | int | Puppy→adult boundary (guidance) |
| `senior_start_months` | int | Senior boundary (guidance) |
| `activity_baseline` | enum | low/moderate/high/very_high |
| `energy_factor_mod` | numeric | −0.10..+0.10 (soft kcal tweak) |
| `ideal_weight_min_kg` | numeric | optional |
| `ideal_weight_max_kg` | numeric | optional |
| `sources` | jsonb | provenance of fields |
| `updated_at` | timestamptz | — |

**Notes:** These are **soft priors** for personalization, not medical rules.

---

## 6) Defaults & Fallbacks (when a field is missing)
- `activity_baseline`: default `moderate`
- `energy_factor_mod`: default `0.0` (bounded to ±0.10)
- `growth_end_months` / `senior_start_months`:
  - If missing, backfill from **size-based defaults** (list your chosen defaults here and tag them as `default_from_size=true` in provenance)
- `size_category`: map from weight/height groups if present; otherwise null

*(Fill this with the actual defaults you decide to use.)*

---

## 7) Build Plan (what Claude will execute)
**B1 — Audit & Report (no code output)**
- Enumerate breed sources, columns, counts, coverage, duplicates, alias clusters, and dogs linkage.
- Paste a summary to fill Sections 1–4 above.

**B2 — Alias Map & Compat Views**
- Create `breed_aliases` (alias → canonical_slug). Start with the obvious clusters found.
- Build `*_compat` views for each source that emit the canonical columns.

**B3 — Canonical Build & Publish**
- Merge compat views into `breeds_canonical` (table or materialized view).
- Dedupe by `breed_slug` with precedence: more complete row > newer `updated_at`.
- Publish read-only view for AI/Admin: `SELECT … FROM breeds_canonical`.

**B4 — QA & Linkage Re-check**
- Recompute coverage %.
- Re-run dogs linkage; list the top unmapped dog breed strings.
- Export `breeds_sample.csv` (50 rows).

**B5 — Acceptance Criteria**
- ≥ 95% of rows have `size_category`
- ≥ 90% have `growth_end_months` and `senior_start_months` (after defaults)
- ≥ 90% have `activity_baseline`
- Dogs linkage ≥ 90% auto-mapped (or provide top 50 unmapped for manual aliasing)

---

## 8) Prompts (copy-paste into the Content repo)

### Prompt C-B1 — Audit & Report
> **Task:** Audit all `breed*` sources and produce a consolidation report.  
> 1) List candidate tables/views; row counts; last updated.  
> 2) For each, compute coverage for: size_category (or equivalent), growth_end_months, senior_start_months, activity baseline, energy_factor_mod, any ideal weight fields.  
> 3) Generate alias clusters (name variants → canonical) and show 10 examples.  
> 4) Attempt to link the **dogs** table’s breed field(s) to canonical slugs; report match %, and list top 25 unmapped names.  
> 5) Paste back a filled version of Sections 1–4 of this report.

### Prompt C-B2 — Alias Map & Compat Views
> **Task:** Create `breed_aliases` and compat views.  
> 1) Create `breed_aliases` (alias → canonical_slug), seeded with the clusters from B1; ensure `canonical_slug` exists or define it now.  
> 2) For each source, build a `*_compat` view outputting: breed_name, breed_slug, size_category, growth_end_months, senior_start_months, activity_baseline, energy_factor_mod, ideal_weight_min_kg, ideal_weight_max_kg, sources, updated_at.  
> 3) Report row counts and 10-row samples per view.

### Prompt C-B3 — Canonical Build & Publish
> **Task:** Build and publish `breeds_canonical`.  
> 1) Merge the compat views, dedupe by `breed_slug` with precedence: more complete > newer updated_at.  
> 2) Write provenance into `sources` JSON.  
> 3) Publish final **read view** `breeds_canonical_view` (or just rely on `breeds_canonical` if it’s the table).  
> 4) Paste coverage metrics and 20-row sample.

### Prompt C-B4 — QA & Linkage Re-check
> **Task:** QA the canonical view and dog linkage.  
> 1) Recalculate coverage % for canonical fields.  
> 2) Re-run linkage to the `dogs` table and report % matched.  
> 3) Export `breeds_sample.csv` (50 rows).  
> 4) Paste back acceptance criteria status and any remaining gaps.

---

## 9) Integration Notes (for later)
- **AI service:** add a small lookup to `breeds_canonical` by `breed_slug` or `breed_id`; attach `used_breed` to responses and apply soft MER and size-line boosts.  
- **Admin:** on `/smart-care-qa`, when a dog is selected, show a compact Breed card from `breeds_canonical` (size, growth/senior cut-offs, activity).

---

## 10) Risks & Safeguards
- Don’t hard-filter foods by breed; use breed only for **soft scoring** and life-stage boundaries.  
- Keep **energy_factor_mod** capped in ±10%.  
- Mark all defaults and inferred values in `sources`/provenance so they’re auditable.

---

**Deliverable:** a filled report + a published `breeds_canonical` view with coverage ≥ targets and dogs linkage ≥ 90%.
