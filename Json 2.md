 **Prompt 2 — Extend the profile to support API mode (config only)**

**Goal:** Add an **api:** section to profiles/pfx_profile.yaml while keeping the existing HTML selectors. Default behavior: **auto** (try API first, then HTML fallback).


**Do this:**

1. Edit/create profiles/pfx_profile.yaml to include:


- api.mode: api | html | auto (default **auto**)
    
- api.endpoints:
    
    - detail: <EDIT ME> e.g. https://www.example.com/api/products/{slug}
        
    - list: <EDIT ME> e.g. https://www.example.com/api/search?q={q}&page={page}&size={size}
        
    
- api.headers: (only public headers; no cookies)
    
    - referer: https://www.example.com/
        
    - origin: https://www.example.com
        
    - accept: application/json
        
    - authorization: <optional — leave empty unless strictly required>
        
    
- api.pagination: with either type: page (page_param, size_param) **or** type: cursor (cursor_param, next_cursor_path)
    
- api.mapping: dot-paths for JSON fields:
    
    - brand_path: data.brand.name
        
    - name_path: data.title
        
    - ingredients_path: data.ingredients
        
    - energy_kcal_path: data.nutrition.energyKcalPer100g
        
    - protein_pct_path: data.nutrition.proteinPct
        
    - fat_pct_path: data.nutrition.fatPct
        
    - life_stage_path: data.lifeStage
        
    - form_path: data.form
        
    - packs_path: data.packs (e.g., list with size & price)
        
    - gtin_path: data.gtin
        
    
- api.constraints: rate_limit_ms: 1500, max_per_run: 100
    

  

2. Add # EDIT ME comments where I must fill correct paths based on api/NOTES_pfx.md.
    

  

**Output:** Updated pfx_profile.yaml with an api: block (keeps HTML selectors intact).

---

# **Prompt 3 — Implement API-first fetch with HTML fallback**

  

**Goal:** Teach the scraper to try the configured API first; if API isn’t available/allowed/fails, fall back to HTML. Save raw **JSON** to GCS when API is used.

  

**Do this:**

1. Add etl/json_path.py — a small helper to safely read nested JSON by **dot-path** (e.g., data.nutrition.proteinPct), returning None if missing.
    
2. Update jobs/pfx_scrape.py:
    
    - New CLI flag --mode api|html|auto (default pulls from profile; fallback to **auto**).
        
    - For each product to ingest:
        
        a) If mode allows **API**:
        
        - Derive a **slug** or params from the product URL (add derive_slug(url)).
            
        - Call api.endpoints.detail with headers from the profile.
            
        - If **200 JSON**:
            
            - Save raw JSON to **GCS**: gs://lupito-content-raw-eu/petfoodexpert/YYYY-MM-DD/<hash>.json
                
            - Map fields using api.mapping.* + etl/json_path.py
                
            - Normalize using existing helpers (parse_percent, parse_energy incl. kJ→kcal, tokenize_ingredients, derive_form, derive_life_stage)
                
            - Upsert **food_raw** (raw_type='api', parsed_json) and **food_candidates** (same fingerprint logic)
                
            
        - Else: log reason and continue to **HTML fallback**.
            
            b) If mode allows **HTML** (or API failed), keep current snapshot+parse flow (raw HTML → GCS .html, etc.)
            
        
    - Respect api.constraints.rate_limit_ms between API calls. Keep polite delays for HTML too.
        
    
3. If needed, migrate **food_raw** to add raw_type text default 'html'.
    
4. Logging:
    
    - For each product, log source=api or source=html, and new/updated/skipped.
        
    - Harvest report: totals for **API hits** vs **HTML fallbacks**.
        
    
5. Add --dry-run mode that prints intended actions without writing.
    

  

**Smoke run:**

Use **≤30 URLs** (--seed-list or --from-sitemap), mode auto. Print a small table of 5 rows: brand, name, kcal/100g, protein%, fat%, contains_chicken, source.

---

# **Prompt 4 — QA & Compliance checklist (create file)**

  

**Goal:** Add a simple checklist to ensure we’re polite and safe.

  

**Do this:** Create QA_COMPLIANCE.md with these boxes:

- Confirm robots.txt/ToS allow API requests; if unclear, stick to HTML or get permission.
    
- No private tokens/cookies are committed; secrets only via .env.
    
- Rate limiting respected (≥ profile.api.rate_limit_ms), plus random jitter.
    
- 20 random rows pass sanity checks (brand/name non-empty; 0–100% ranges; kcal reasonable).
    
- foods_published shows API-sourced rows.
    
- Admin **Brand Alternatives** tab returns items for a typical **RO** profile (EU fallback ON).
    
- Any estimated fields (e.g., kcal from Atwater) are marked as **estimated** in notes/metadata.
    

  

**Output:** QA_COMPLIANCE.md committed with the checklist and a short paragraph on how to re-run a small harvest.

---

## **Notes & reminders for Claude**

- **Project:** careful-drummer-468512-p0
    
- **GCS bucket:** gs://lupito-content-raw-eu
    
- Do **not** print secrets. If you need SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY, **ask me** and save to .env locally.
    
- If endpoints require auth or violate ToS, **fall back to HTML** and note it in api/NOTES_pfx.md.
    

  

When you’ve run these, paste your short harvest report here and we’ll wire the Admin “Brand Alternatives” tab to verify items show up for RO profiles.