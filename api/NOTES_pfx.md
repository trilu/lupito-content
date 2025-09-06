# PetFoodExpert API Documentation

## Overview
PetFoodExpert exposes **public JSON endpoints** that provide product data without authentication. These endpoints should be preferred over HTML scraping for better performance and reliability.

## Base URL
```
https://petfoodexpert.com/api
```

## Endpoints

### 1. Product Detail Endpoint
**Pattern:** `/products/{slug}`

Retrieves complete product information by slug.

**Example URLs:**
- `https://petfoodexpert.com/api/products/aardvark-complete-grain-free-insect-dry-food-dry-dog`
- `https://petfoodexpert.com/api/products/aatu-chicken-dry-dog`
- `https://petfoodexpert.com/api/products/canagan-insect-dry-dog`

**Note:** The slug is extracted from the product page URL: `/food/{slug}` → `/api/products/{slug}`

### 2. Product Listing Endpoint
**Pattern:** `/products`

Returns paginated list of products with filtering options.

**Query Parameters:**
- `species` - Filter by species (e.g., `dog`, `cat`)
- `page` - Page number (1-based)
- `search` - Search term (may not be fully supported)

**Example URLs:**
- `https://petfoodexpert.com/api/products?species=dog&page=1`
- `https://petfoodexpert.com/api/products?species=dog&page=2`
- `https://petfoodexpert.com/api/products?search=chicken&page=1`

## Pagination

Listing responses include pagination metadata:
```json
{
  "meta": {
    "pagination": {
      "total": 3793,
      "count": 20,
      "per_page": 20,
      "current_page": 1,
      "total_pages": 190,
      "links": {
        "next": "https://petfoodexpert.com/api/products?species=dog&page=2"
      }
    }
  }
}
```

- **Fixed page size:** 20 items per page
- **Total pages:** Available in `total_pages`
- **Next page URL:** Provided in `links.next`

## Field Mapping

### Our Schema → API Response

| Our Field | API Path | Notes |
|-----------|----------|-------|
| `brand` | `data.brand.name` | Brand object includes id and external_url |
| `product_name` | `data.name` | Full product name |
| `form` | `data.food.moisture_level` | "Dry", "Wet", etc. |
| `life_stage` | `data.animal.life_stage.string` | "All Life Stages", "Adult", etc. |
| `ingredients_raw` | `data.food.ingredients` | Complete ingredients string |
| `kcal_per_100g` | Not directly provided | Must calculate from recommendations/cost |
| `protein_percent` | Not in JSON | Would need HTML scraping or estimation |
| `fat_percent` | Not in JSON | Would need HTML scraping or estimation |
| `fiber_percent` | Not in JSON | Would need HTML scraping or estimation |
| `contains_chicken` | Parse from `data.food.ingredients` | Text analysis required |
| `pack_sizes` | `data.variations[].weight_label` | Array of size options |
| `price_eur` | `data.variations[].variation_price` | In GBP, needs conversion |
| `gtin` | Not provided | Not available in JSON |
| `source_url` | `data.url` | Canonical product page URL |

### Additional Useful Fields
- `data.checklist.grain_free` - "Y"/"N" for grain-free status
- `data.checklist.wheat_free` - "Y"/"N" for wheat-free status
- `data.checklist.hypoallergenic_principles` - "Y"/"N" 
- `data.checklist.cooking_process` - "Extruded", etc.
- `data.score.nutritional` - Numerical nutrition score (0-100)
- `data.packaging.original_url` - Product image URL
- `data.recommendations` - Feeding guide with weight ranges and cost/day

## Required Headers

**Minimal headers needed:**
```
Accept: application/json
User-Agent: Mozilla/5.0 (compatible; LupitoBot/1.0; +https://lupito.app)
```

**No authentication required** - These are public endpoints.

## Rate Limiting & Best Practices

1. **Concurrency:** Limit to ≤2 concurrent requests
2. **Delay:** 600-1000ms between requests to same host
3. **Retry:** Honor `Retry-After` header on 429/5xx responses
4. **User-Agent:** Always include realistic User-Agent
5. **Error handling:** Gracefully handle 403s (temporary blocks)

## Response Structure

### Listing Response
```json
{
  "data": [
    {
      "id": 2,
      "name": "Aatu Free Run Chicken",
      "slug": "aatu-chicken-dry-dog",
      "species": "dog",
      "url": "https://petfoodexpert.com/food/aatu-chicken-dry-dog",
      "brand": {...},
      "animal": {...},
      "food": {...},
      "score": {...},
      "checklist": {...},
      "packaging": {...}
    }
  ],
  "meta": {
    "pagination": {...}
  }
}
```

### Detail Response
```json
{
  "data": {
    "id": 1,
    "name": "Product Name",
    "slug": "product-slug",
    "brand": {...},
    "animal": {...},
    "food": {
      "ingredients": "...",
      "moisture_level": "Dry"
    },
    "variations": [
      {
        "weight_label": "1.5kg",
        "weight_value": 1.5,
        "variation_price": 12.99
      }
    ],
    "recommendations": [...],
    "cost": {
      "day": "£1.51",
      "year": "£551.15"
    }
  }
}
```

## Caveats & Limitations

1. **Nutrition data missing:** Protein%, fat%, fiber%, ash%, moisture% not in JSON - would need HTML scraping or estimation
2. **Energy (kcal) missing:** Not directly provided, could estimate from cost/feeding data
3. **Search unreliable:** The `search` parameter may not work as expected
4. **Filters limited:** Only `species` and `page` are confirmed to work
5. **Currency:** Prices in GBP (£), need conversion to EUR
6. **No GTIN/EAN:** Product codes not available in JSON

## Open Questions

1. **Nutrition data strategy:** Should we:
   - Fall back to HTML scraping for nutrition tables?
   - Estimate from feeding guidelines?
   - Mark as unavailable?

2. **Search implementation:** If `search` parameter unreliable:
   - Fetch all pages and filter client-side?
   - Use category listings only?

3. **Currency conversion:** 
   - Use static rates or dynamic API?
   - Store original GBP + converted EUR?

4. **Caching strategy:**
   - How often do products change?
   - Should we cache listing pages?

## Implementation Priority

1. **First:** Use JSON API for product discovery (listing endpoint)
2. **Second:** Use JSON API for product details (by slug)
3. **Fallback:** HTML scraping only for missing nutrition data
4. **Optional:** Implement search if parameter works reliably

## Testing Checklist

- [ ] Verify listing pagination works up to page 190+
- [ ] Confirm product detail slugs match URL patterns
- [ ] Test rate limiting behavior at different speeds
- [ ] Validate all variations prices are captured
- [ ] Check if undocumented filters work (moisture_level, etc.)