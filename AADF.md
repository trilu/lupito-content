# Harvesting “All About Dog Food” (AADF) Politely

This document outlines a polite, robots-aware plan for gathering dog-food nutrition data from **All About Dog Food** (AADF). It details how to check for permission, discover any JSON endpoints via DevTools, and, if no API is present, how to extract data from HTML listings and product pages.

## 1. Robots/Terms-of-Service Checklist

1.        **Check** **robots.txt**: Before making any requests, load https://www.allaboutdogfood.co.uk/robots.txt. If the file disallows the directory or review pages, or prohibits bots entirely, **do not proceed**. If the file is neutral or permits access, proceed, but still adhere to the rate limits below【0†L1-L4】.

2.        **Check the Terms of Use**: Read the terms at https://www.allaboutdogfood.co.uk/terms-of-use. If the terms forbid scraping or automated data collection, respect this and halt. If they permit casual browsing, proceed politely【0†L1-L4】.

3.        **Rate Limits & Politeness**: Even if permitted, throttle requests to **≤ 1 request every 2 seconds**, adding random jitter (±250–750 ms). Reuse a single HTTP client (to benefit from connection pooling) and honour cache headers. If you encounter 429 or other error codes, back off exponentially.

4.        **User-Agent & Session Hygiene**: Send an informative User-Agent identifying yourself and your purpose. Avoid concurrently crawling multiple pages; respect off‑peak hours and avoid heavy filtering or repeated calls.

## 2. DevTools Discovery Steps (To Find JSON Endpoints)

If AADF uses public JSON endpoints for its directory search or product detail views, using them will be more efficient than HTML scraping. Here’s how to find them:

1.        **Open a Product Page**: Navigate to a review page, e.g., https://www.allaboutdogfood.co.uk/dog-food-reviews/2087/pure-pet-food-adult【0†L1-L4】. Open **DevTools → Network**, filter by **XHR/Fetch**, and hard refresh the page (Ctrl + F5 or ⌘ + Shift + R). Interact with the page: expand sections like “Nutrition” or “Where to buy” to trigger network calls.

2.        **Look for JSON**: In the **Network** panel, record any requests returning application/json. Copy the full URL, note the HTTP method and query parameters (e.g., page, cursor, limit), and save response samples. Pay special attention to the presence of Origin, Referer, or Accept headers.

3.        **Check Listing/Search Pages**: Go to the Dog Food Directory (https://www.allaboutdogfood.co.uk/the-dog-food-directory) and apply filters or click through pages【0†L1-L4】. Watch for any JSON responses on the initial load or during pagination. Capture up to three **detail endpoints** and three **listing endpoints** (if they exist). Use the placeholders below to record them.

Example placeholders (replace once discovered):

Detail endpoints (up to 3):  
1. https://www.allaboutdogfood.co.uk/…  
2. https://www.allaboutdogfood.co.uk/…  
3. https://www.allaboutdogfood.co.uk/…  
  
Listing/search endpoints (up to 3):  
4. https://www.allaboutdogfood.co.uk/…?page=2  
5. https://www.allaboutdogfood.co.uk/…?filters=…  
6. https://www.allaboutdogfood.co.uk/…?cursor=…  
  
Headers to record:  
- Origin: https://www.allaboutdogfood.co.uk  
- Referer: (the page from which you triggered the request)  
- Accept: application/json (if present)  
- Any authorization/cookie tokens (if present; if necessary, stop politely if the API requires auth)

## 3. If No Public JSON Exists → HTML‑Only Strategy

If your DevTools session reveals no JSON endpoints, use an HTML-first approach:

·      **Starting Points**: Begin at https://www.allaboutdogfood.co.uk/the-dog-food-directory【0†L1-L4】 (and the complementary food directory). These pages list products and provide navigation to the detail pages.

·      **Pagination**: Use the directory’s visible page numbers or “next” links to traverse. If there is infinite scroll, scroll until new items load and inspect the page source for parameters (e.g., ?page=2 or offset=). Respect the rate limit as you click pages.

·      **Extracting Data**: On each product page, parse the following fields:

·      **Brand**: Usually displayed with the product name【0†L1-L4】.

·      **Product Name**: The page’s main heading【0†L1-L4】.

·      **Composition/Ingredients**: Listed under “Composition” or “Ingredients” sections【0†L1-L4】.

·      **Analytical Constituents**: Capture these sub‑fields where available: protein_percent, fat_percent, fibre_percent, ash_percent, moisture_percent. Use synonyms like “Crude Protein”→Protein, “Fat/Oil”→Fat.

·      **Energy**: Kcal or kJ per kg (if listed).

·      **Life Stage**: Terms like “Adult,” “Puppy,” or “All life stages.”

·      **Form**: Dry, wet, raw, air‑dried, freeze‑dried, etc., based on the site’s taxonomy【0†L1-L4】.

·      **Rating Score**: If AADF shows a numeric or star rating, capture the value and scale (e.g., 4.6/5). Include the raw text.

·      **Notes**: Capture descriptors like “grain‑free,” “single protein,” or “hypoallergenic.”

·      **Source URL**: Keep the canonical URL for traceability.

Use a parser (e.g., BeautifulSoup) to locate the composition and analytical constituents tables. Maintain the order of ingredients. If the site distinguishes between “mixing bowl” and “as fed,” record which basis each set of percentages corresponds to.

## 4. Field Mapping Plan

When parsing HTML, map the data to the following schema:

|Field|Description|
|---|---|
|**brand**|Brand name (e.g., “Pure”)【0†L1-L4】|
|**product_name**|Product title on the review page【0†L1-L4】|
|**composition**|Raw ingredient list, including percentages and order【0†L1-L4】|
|**protein_percent**|Crude protein percentage from the analytical table|
|**fat_percent**|Crude fat (Fat/Oil) percentage|
|**fibre_percent**|Crude fibre percentage|
|**ash_percent**|Ash percentage|
|**moisture_percent**|Moisture percentage (if available)|
|**energy_kcal_per_kg**|Energy value, normalized to kcal/kg (or kJ/kg with field name adjusted)|
|**life_stage**|“Puppy,” “Adult,” “Senior,” etc.|
|**form**|“Dry,” “Wet,” “Raw,” “Air‑dried,” etc.|
|**rating_score**|Numeric/star rating, if present|
|**notes**|Flags like “grain‑free,” “hypoallergenic,” etc.|
|**source_url**|Link to the product’s page for auditing|

## 5. Open Questions

1.        **Pagination mechanics**: Does the directory use simple ?page=2 query parameters or dynamic offset/cursor? DevTools observation is needed.

2.        **JSON vs. HTML**: Does AADF call a hidden API for searching? If so, capture endpoints, parameters, and required headers. If not, stick to HTML.

3.        **Price availability**: Some pages may embed price information via third-party widgets; you should not collect these unless permitted, and pricing may be dynamic. Document whether the site provides price data or just links to retailers.

4.        **Rating scale consistency**: Confirm whether all products have a rating and whether the scale is always out of 5 (or 100). If absent for some items, set the rating field to null.

5.        **Life stage & form**: Are these fields always displayed or sometimes inferred? Plan fallback logic (e.g., categorize by “adult” if unspecified and ingredients imply adult formulation).

## 6. Go/No‑Go Decision

**Current recommendation:** Start with the **HTML-first** strategy. This plan is safe and respects AADF’s public pages. Only transition to an API-first approach if DevTools reveals clearly accessible JSON endpoints without login or secret tokens. In either case, abide by the robots and ToS guidelines【0†L1-L4】.

---

**Reference:** Many details in this plan—such as the existence of listings and composition sections—are based on publicly accessible pages of AADF, including its Dog Food Directory【0†L1-L4】.

---