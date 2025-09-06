# **Pet Food Expert – Public JSON endpoints (observed)**

  

## **Product Detail Endpoints (3 examples)**

  

These return a **single product’s full JSON** by slug (no auth required):

1. Full JSON URL for product 1:
    
    https://petfoodexpert.com/api/products/aardvark-complete-grain-free-insect-dry-food-dry-dog
    
2. Full JSON URL for product 2:
    
    https://petfoodexpert.com/api/products/aatu-chicken-dry-dog
    
3. Full JSON URL for product 3:
    
    https://petfoodexpert.com/api/products/canagan-insect-dry-dog
    

  

> Notes

- > The **slug** is the last segment of the public product page URL:
    
    > e.g., page https://petfoodexpert.com/food/aatu-chicken-dry-dog ⇒ detail JSON at /api/products/aatu-chicken-dry-dog.
    
- > The detail payload includes: name, slug, url (canonical product page), brand, animal (life stage / breed size), food.ingredients, food.moisture_level, score blocks, checklist flags (grain_free, wheat_free, etc.), company_info, recommendations (feeding guide), packaging URLs, variations (weights/prices), and sometimes cost.
    

---

## **Listing/Search Endpoints (3 examples)**

  

All observed listing data comes from **one paginated endpoint**. It returns an array of products plus pagination metadata.

4. Category listing JSON URL (dogs, page 1):
    
    https://petfoodexpert.com/api/products?species=dog&page=1
    
5. Search results JSON URL:
    
    - **Likely** the same endpoint supports a query term via q, e.g.:
        
        https://petfoodexpert.com/api/products?species=dog&q=chicken&page=1
        
    - I did not see a separate /search path. If q is not accepted, fall back to listing+client-side filter.
        
    
6. Paginated listing JSON URL (page 2):
    
    https://petfoodexpert.com/api/products?species=dog&page=2
    

  

> Notes

- > Pagination info is included in meta.pagination (e.g., total_pages, links.next, etc.).
    
- > I didn’t observe a dedicated “category” path—category views appear to be filters on the same products endpoint (e.g., by species). Other filters used in the UI (moisture level, allergen flags, cooking process) may or may not be exposed as query params; if needed, you can add them experimentally (e.g., &moisture_level=Dry) and fall back to client-side filtering if the API ignores them.
    

---

## **Required headers**

- **No Authorization / API key required** in my tests.
    
- Recommended request headers:
    
    - Accept: application/json
        
    - A realistic **User-Agent**, e.g.
        
        Mozilla/5.0 (compatible; xPortal-dog-food-extractor/1.0; +https://yourdomain.example)
        
    
- Be polite:
    
    - Limit concurrency to **≤ 2**
        
    - Add **600–1000 ms** delay between requests to the same host
        
    - Honor Retry-After on 429/5xx

## **Response format samples**

  

### **Listing (page) — shape (abridged)**

{
  "data": [
    {
      "id": 2,
      "name": "Aatu Free Run Chicken",
      "slug": "aatu-chicken-dry-dog",
      "species": "dog",
      "url": "https://petfoodexpert.com/food/aatu-chicken-dry-dog",
      "brand": { "id": 2, "name": "Aatu", "external_url": "https://aatu.co.uk/" },
      "animal": {
        "life_breed_title": "Life Stage / Breed Size",
        "life_stage": { "array": ["Adult","Senior"], "string": "Adult" },
        "breed_size": { "array": ["Small","Medium","Large"], "string": "All Breed Sizes" },
        "species": "Dog"
      },
      "food": { "ingredients": "…", "moisture_level": "Dry" },
      "score": { "nutritional": 96, "ethical": 0 },
      "checklist": { "wheat_free": "Y", "grain_free": "Y", "cooking_process": "Extruded" },
      "packaging": { "original_url": "https://…/packshots/…/aatu-free-run-chicken.jpg" }
    }
    // …more products
  ],
  "meta": {
    "pagination": {
      "total": 3793,
      "count": 20,
      "per_page": 20,
      "current_page": 1,
      "total_pages": 190,
      "links": { "next": "https://petfoodexpert.com/api/products?species=dog&page=2" }
    }
  }
}

### **Product detail — shape (abridged)**

{
  "data": {
    "id": 1,
    "name": "Aardvark Complete Grain Free Insect Dry Food",
    "slug": "aardvark-complete-grain-free-insect-dry-food-dry-dog",
    "species": "dog",
    "url": "https://petfoodexpert.com/food/aardvark-complete-grain-free-insect-dry-food-dry-dog",
    "brand": { "id": 1, "name": "Aardvark", "external_url": "https://aardvark.store/" },
    "animal": {
      "life_stage": { "array": ["Puppy","Adult","Senior"], "string": "All Life Stages" },
      "breed_size": { "array": ["Small","Medium","Large"], "string": "All Breed Sizes" },
      "species": "Dog"
    },
    "food": {
      "ingredients": "35% Insect (Insect Meal 30%, Insect Oil 5%), Sweet Potato …",
      "moisture_level": "Dry"
    },
    "score": { "nutritional": 64, "hypoallergenic": 2, "moisture_score": 0 },
    "checklist": {
      "wheat_free": "Y",
      "grain_free": "Y",
      "hypoallergenic_principles": "Y",
      "only_natural_preservatives": "Y",
      "cooking_process": "Extruded"
    },
    "company_info": { "renewable_production_ci": 1, "packaging_recyclable_ci": 1, "…" : 0 },
    "recommendations": [
      { "activity_level": "low", "weight_range_low": 0, "grams_per_day": 30, "cost_per_day": "£0.26" }
      // …weight/level rows
    ],
    "packaging": {
      "original_url": "https://petfoodexpert.com/packshots/1/aardvark-…-dry-dog.jpg",
      "thumbnail__md_url": "https://petfoodexpert.com/packshots/1/conversions/…-thumb--md.jpg"
    },
    "variations": [
      { "weight_label": "1.5kg", "weight_value": 1.5, "variation_price": 12.99 }
    ],
    "cost": { "day": "£1.51", "year": "£551.15" }
  }
}

## **CORS / authentication**

- **No authentication** needed for reads in my testing.
    
- **CORS**: The API is fetched by their web frontend; browser access works. For your server-side scripts, just send a normal Accept: application/json and a realistic User-Agent. If you hammer or omit UA, you might see temporary 403s—use throttling and retries.
    

---

## **Caveats / limitations**

- I did not see a **documented** parameter list; beyond species=dog and page=n, other filters may not be officially supported even if the UI suggests them. If you need moisture level or allergen filters, try adding them (e.g., &moisture_level=Dry) and **gracefully fall back** to client-side filtering if the API ignores unknown params.
    
- Product **detail by slug** is reliable and contains nearly everything visible on the page; prefer it over HTML scraping.
    
- Be polite: ≤2 concurrent requests and at least 600–1000 ms delay between calls to avoid rate limiting.

### **Product Detail Endpoints (examples)**

  

These endpoints return a single product’s complete JSON record. The slug is the last segment of the public product URL.

1. https://petfoodexpert.com/api/products/aardvark-complete-grain-free-insect-dry-food-dry-dog – sample detail for “Aardvark Complete Grain Free Insect Dry Food” .
    
2. https://petfoodexpert.com/api/products/aatu-chicken-dry-dog – sample detail for “Aatu Free Run Chicken” (dry dog).
    
3. https://petfoodexpert.com/api/products/canagan-insect-dry-dog – sample detail for “Canagan Insect” .
    

  

These endpoints return a JSON object under data containing fields like id, name, slug, species, url, brand, animal (life stage and breed size), food.ingredients, moisture_level, score and score_breakdown, checklist flags, company_info, recommendations, packaging image URLs and variations (weights and prices) .

  

### **Listing/Search Endpoints (examples)**

  

The API uses a single products endpoint with query parameters for filtering and pagination:

4. **Category listing JSON** – for all dog products, page 1:
    
    https://petfoodexpert.com/api/products?species=dog&page=1
    
5. **Search results JSON** – the UI search appears to call the same endpoint with a search parameter. For example, searching for “chicken” (across cats and dogs):
    
    https://petfoodexpert.com/api/products?search=chicken&page=1 .
    
    _Note_: the search parameter isn’t documented; it may be ignored or return mixed species. Client-side filtering is safer.
    
6. **Paginated listing JSON** – to page through results:
    
    https://petfoodexpert.com/api/products?species=dog&page=2 (page 2 of the dog listing). The response’s meta.pagination block shows total, count, per_page, current_page and total_pages, along with a links.next URL for the next page .
    

  

### **Additional Information**

- **Headers & authentication**: No authentication is required. You can request JSON anonymously. It’s polite to send Accept: application/json and a realistic User-Agent string.
    
- **Response format**: Both listing and detail endpoints return JSON. Listings wrap an array of product summaries in a data field and a meta.pagination field; details wrap a single product in data  .
    
- **CORS / access**: Requests from the browser succeed without CORS restrictions. Server-side scripts work as long as they set a proper User-Agent and avoid hitting the server too quickly.
    
- **Limitations**: Filtering beyond species and page isn’t documented. Search via search or q may not behave reliably. Pagination returns 20 items per page; meta.pagination indicates there are ~190 pages of dog products as of the latest check .
    

  

These URLs and observations should allow you to document the API patterns, pagination mechanism, and field mappings in api/NOTES_pfx.md.