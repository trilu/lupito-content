# Lupito • Context Transfer Pack (Paste into your other ChatGPT chat)

> **How to use this:** Paste this entire document into your *other* ChatGPT conversation (the one where you already discuss the AI service and Admin). Ask it to act as your AI + product architect and continue from here. This pack includes the architecture, data model, APIs, workflows, and checklists we aligned on in this thread.

---

## TL;DR
We’re building a pipeline that (1) ingests external **dog breed** pages (from Dogo) into our system, (2) lets us **edit / AI‑adapt / translate** them inside **Lupito Admin**, and (3) powers a **smart recommendation engine** that combines **breed facts + foods + activities** to produce personalized **food picks, portions, and weekly activity plans**.  
**Admin** is the source of truth for content and approvals. **AI service** is stateless compute (scraping, ETL, embeddings, LLM generation, and recommendations).

---

## Current State (from this conversation)
- Admin Dashboard is already configured to call the AI service via a proxy in STAGING.
  - Base URL: `https://ai.stg.lupito.pet`
  - Authentication works via the proxy. (**Do not paste secrets in chats**.)
- We have a scraper plan for `https://dogo.app/dog-breeds` and an **NDJSON** export structure.
- We decided to prioritize an **Admin-first** workflow: Editors can tweak structured facts, adapt tone with AI, translate, link breed → food rules & activity profiles, then **Publish** snapshots for the app.
- The recommendation engine will be **hybrid**: rules + vector retrieval + LLM for succinct explanation.

---

## Objectives
1) **Own the content**: copy external breed pages into our DB (raw), normalize to structured facts; keep editable narrative text with versions.
2) **Admin-first editing**: simple screens to tweak facts, AI‑adapt tone, translate, link to foods/activities, publish.
3) **Recommendations**: return foods, portion sizes, weekly activity plans, and a short rationale per dog.
4) **Localization**: EN canonical; RO/PL/CZ/HU as machine drafts with human approval.
5) **Separation of concerns**: Admin = content & approvals; AI service = stateless compute & recommendation logic.

---

## Architecture Overview (Two Repos, Clear Contract)

### Admin repo
- **Stores**: `breeds` (normalized facts), `breed_raw` (verbatim snapshots), `breed_text_version` (EN, versioned), `breed_text_locale` (locales), plus `foods`, `activities`, and link/rule tables.
- **UI**: “Breed Editor” with 5 tabs (see below).
- **Content API**: read-only, serves **published snapshots** per breed and locale.
- **Calls AI service** for: compose (tone/merge), translate, explain rationale, and recommendations (via proxy).

### AI repo
- **Endpoints**: `compose-breed`, `translate`, `explain-reco`, `recommendations`.
- **Jobs**: `scrape_dogo`, `etl_breeds_normalize`, `embed_content`.
- **Stateless** runtime; writes back to Admin DB. Pydantic schemas + validations + guardrails.

---

## End-to-End Data Flow
1) **Ingest**: scraper fetches each breed page → saves **raw JSON** (verbatim) with URL + timestamp in `breed_raw`.
2) **Normalize (ETL)**: parse to typed fields (size, energy, lifespan, coat length, shedding, trainability, sensitivities). Keep **both** raw and normalized. Build an **embedding** from traits + summary (`breed_trait_vector`).
3) **Seed narrative**: if missing, generate an initial EN draft from raw → clean outline.
4) **Admin editing**:
   - **Facts**: tweak dropdowns/numbers.
   - **Narrative**: click **Adapt with AI** (tone, length, merge sources) → side-by-side diff → accept changes.
   - **Translations**: machine draft for RO/PL/CZ/HU → human approve.
   - **Links**: connect to **Food rules** and **Activity profiles**.
5) **Publish**: approved version per locale → **snapshot** used by the app.
6) **Recommend**: app sends dog profile → engine picks foods + portions + weekly activities + returns a short rationale.

---

## Admin UX (Breed Editor – 5 Tabs)
1) **Facts (Structured)** – view normalized fields; allow overrides; show change history.
2) **Narrative (AI‑assisted)** – sections: Overview, Temperament, Training, Grooming, Health, Exercise, Family Fit, Trivia. Button: **Adapt with AI** (tone/length/merge) with diff + accept.
3) **Translations** – EN canonical; machine-draft RO/PL/CZ/HU; approve per section. Translation Memory (TM) suggests prior phrases.
4) **Links** – connect this breed to **Food rules** and an **Activity profile**; allow contraindications (e.g., allergens to avoid).
5) **Review & Publish** – status (draft → in_review → approved → published). Publishing creates the read‑optimized snapshot.

---

## Data Model (Supabase Sketch)
**Content & taxonomy**
- `breeds(id, slug, name, origin, size_enum, energy_enum, lifespan_min, lifespan_max, coat_length_enum, shedding_enum, trainability_enum, heat_sensitivity_enum, cold_sensitivity_enum, created_at, updated_at)`
- `breed_raw(id, source, url, raw_json, last_crawled_at)`
- `breed_text_version(id, breed_id, version, status, tone, json_content, created_by, created_at)`
  - `json_content` schema: `{ sections:[{ title, paragraphs:[...] }, ...] }`
- `breed_text_locale(id, version_id, locale, status, json_content, tm_hits, updated_by)`

**Foods & activities**
- `foods(id, brand, product, flavor, life_stage_enum, size_range_enum, kcal_per_kg, protein_pct, fat_pct, fiber_pct, allergens[], country_availability[], price_per_kg, image_url, ... )`
- `activities(id, code, name, intensity_enum, indoor_ok, duration_min, skills[], notes)`
- `breed_food_rules(breed_id, rule_json)`          // macro windows, excludes, texture prefs
- `breed_activity_profiles(breed_id, profile_json)` // weekly template per class (mins/day, intensity mix)

**Vectors & recommendations**
- `vectors_breeds(breed_id, embedding)`
- `vectors_foods(food_id, embedding)`
- `rec_runs(id, dog_id, inputs_json, engine_version, created_at)`
- `rec_results(id, run_id, foods_json, activities_json, rationale_json, kcal_target, portion_plan_json)`

---

## API Contracts

### Content API (Admin → App)
`GET /v1/content/breeds/:slug?locale=ro` → returns published snapshot
```json
{ "facts": { /* enums/numbers */ },
  "text": { "sections": [ { "title": "...", "paragraphs": ["..."] }, ... ] },
  "images": [ { "src": "...", "alt": null } ] }
```

### AI Service (Admin → AI)
**Compose (tone/merge)**
- `POST /ai/compose-breed`
```json
{ "tone":"playful|friendly|expert", "length":"short|medium|long",
  "sources": { "raw": { ... }, "normalized": { ... }, "existing": { ... } } }
→ { "sections":[{ "title":"Overview", "paragraphs":[ "...", "..." ] }, ...] }
```

**Translate**
- `POST /ai/translate`
```json
{ "locale":"ro", "segments":[ { "id":"p1", "text":"..." }, ... ] }
→ { "segments":[ { "id":"p1", "text":"...", "tm": true }, ... ] }
```

**Explain Recommendation**
- `POST /ai/explain-reco`
```json
{ "facts": { "breed": { ... }, "dog": { ... } },
  "picks": { "foods":[ ... ], "activities":[ ... ] } }
→ { "rationale":"Because ..." }
```

**Recommendations**
- `POST /recommendations`
```json
{ "dog": { "breed_id":"...", "age_mo":24, "weight_kg":18, "sex":"M",
           "neutered":true, "allergies":["chicken"], "goals":["weight_loss"] },
  "country":"RO" }
→ { "kcal_target": 980,
    "foods":[{ "food_id":"...", "score":0.84, "portion_g_per_day": 260, "why":[ "...", "..." ] }],
    "activities":[{ "day":"Mon","plan":[{ "type":"run","mins":30,"intensity":"moderate"}]}],
    "rationale":"Because Border Collies are high‑energy..." }
```

---

## Scrape & ETL Guidelines
- Respect `robots.txt`, **1 req/sec**, exponential backoff on 429/5xx; custom UA: `LupitoResearchBot/1.0 (contact: email)`.
- Store **raw_json** per breed with `last_crawled_at`.
- ETL parses **Quick facts** → enums/numbers (size, energy, lifespan, coat length, shedding, trainability). Keep raw copy too.
- Build `breed_trait_vector` from normalized traits + short summary.

---

## Recommendation Engine (Hybrid)
**A. Compute dog needs**
- RER = `70 * (kg^0.75)`; add MER multiplier by life stage, activity, and size.
- Constraints: allergies, country availability, budget (price/kcal), texture preferences.

**B. Candidate selection (rules + SQL)**
- Filter foods by life_stage, size_range, allergens, availability.
- Score by distance to target macros (protein/fat) per breed/activity profile.
- Apply boosts/penalties (inventory, price/kcal).
- Portion = `kcal_target / (kcal_per_kg / 10)` → grams/day.

**C. Retrieval + rerank (vectors)**
- Use embeddings to retrieve semantically similar foods to `breed_trait_vector`; merge with rule scores.

**D. Activities plan**
- Start from `breed_activity_profiles` template; personalize minutes by age, weight, heat/cold sensitivity, owner goals.

**E. Explanation (LLM)**
- Generate concise rationale; **no medical treatment claims**.

---

## Localization Pipeline
- EN is canonical; others are **machine-draft → human approve**.
- TM pre-fills known phrases; changed segments trigger re-review.
- Optional pseudo-locale for QA.

---

## Versioning & Publishing
- Every edit creates a new `breed_text_version` (immutable).
- Locales reference a base version.
- **Publish** creates a frozen snapshot used by Content API.
- Rollback = switch the published pointer.

---

## Governance, Safety, QA
- Medical disclaimer template; block list for treatment/cure claims.
- Pre-publish checks: required sections present, images valid, locales approved.
- Telemetry: track CTR on foods, plan adherence, weight trends; use signals to tune rule weights.

---

## Execution Plan (What to ask your other chat to build next)
1) **DB migrations** (tables above).
2) **Admin UI**: Breed Editor (5 tabs) incl. diff viewer + approval flow.
3) **Content API**: read-only published snapshot for the app.
4) **AI endpoints**: compose-breed, translate, explain-reco, recommendations.
5) **Jobs**: scrape_dogo, etl_breeds_normalize, embed_content.
6) **Unit tests**: kcal math, portioning, rule filters, JSON schema validation, locale fallbacks.

---

## Acceptance Criteria
- Every breed visible in Admin with structured facts + narrative + translations + links.
- “Adapt with AI” and “Translate” flows work with human approval and versioning.
- Content API serves localized, approved snapshots.
- Recommendations API returns foods, portions, weekly activity plan, and a one-paragraph rationale.
- All Admin → AI calls go through the STAGING proxy.

---

## Prompt Templates (ready-to-paste)

**Compose-breed (tone/merge)**
- *System*: “You are a careful content editor. Return **only** valid JSON `{sections:[{title, paragraphs:[...]},...]}`. Avoid medical treatment claims. Keep facts aligned with the provided normalized fields.”
- *User*: “Tone: {{tone}}. Length: {{length}}. Merge these: raw={{raw excerpt}}, normalized={{facts}}, existing={{current text}}. Improve clarity and friendliness. **Return JSON only**.”

**Translate**
- *System*: “You are a translator. Preserve meaning, tone, and product names; no added claims. Output JSON segments only.”
- *User*: `{ "locale":"{{locale}}", "segments":[{"id":"p1","text":"..."}, ...] }`

**Explain-reco**
- *System*: “You write concise, friendly explanations for dog owners. No medical claims.”
- *User*: `{ "facts":{ "breed":{...}, "dog":{...} }, "picks":{ "foods":[...], "activities":[...] } } → One paragraph (≤ 80 words).”

---

## Open Questions (for the other chat to help decide)
- Price/kcal vs. brand/contract weighting in ranking (how to tune).
- Allergen taxonomy: do we standardize on a fixed list now?
- Portion rounding rules (to nearest 5 g? meal splits 2×/3× by default?).
- Locale rollout order and TM storage format.

---

**That’s the full context from this thread.** Continue the work in your other chat by generating:
- SQL migrations, Admin React screen blueprint, ETL parser from Dogo, embeddings job, FastAPI stubs, and unit tests.
