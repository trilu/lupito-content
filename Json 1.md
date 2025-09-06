 **Prompt 1 — Discover & document the site’s JSON endpoints (no code yet)**

  

**Context:** We already have HTML scraping working. If PetFoodExpert exposes JSON/XHR endpoints, we want to use them first and only fall back to HTML. Be polite + ToS-compliant.

  

**Do this:**

1. Write a short **checklist for me** to follow in Chrome DevTools to find the endpoints:
    
    - Open a **product detail** page and a **category/search** page.
        
    - Network tab → filter **XHR/Fetch** → click JSON responses.
        
    - Record the **full request URL**, required **headers** (Origin/Referer/Accept/Auth), and notable **query params** (like page/size/cursor).
        
    
2. Ask me to paste **6 example URLs** back here:
    
    - 3× product **detail** JSON endpoints
        
    - 3× **listing/search** JSON endpoints (with pagination)
        
    
3. From those, create a concise doc **api/NOTES_pfx.md** that includes:
    
    - URL patterns / templates (e.g., /api/products/{slug})
        
    - Pagination mechanism (page/size or cursor)
        
    - Field mapping → brand, name, ingredients, energy (kcal/100g or kJ), protein%, fat%, life_stage, form, packs + price + currency, GTIN/EAN
        
    - Required headers
        
    - Any caveats (auth cookies? anti-bot headers? rate limits?)
        
    
4. Do **not** hit any endpoints yet. No code changes. Just produce the doc and a short list of open questions.
    

  

**Output:** api/NOTES_pfx.md with URL templates, headers, pagination, and JSON path mapping candidates.