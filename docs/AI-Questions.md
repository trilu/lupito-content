⏺ Questions for the Database/Content Team

  1. Table/View Verification

  - Do the views foods_published_prod and foods_published_preview exist in the Supabase instance at cibjeqgftuxuezarjsdl.supabase.co?
  - Can you confirm the exact schema/columns these views expose? (Please provide the output of \d foods_published_prod or equivalent)
  - Are these views or materialized views? If materialized, when were they last refreshed?

  2. Permissions & Access

  - What exact permissions does the service account (using the service key) have on these views?
  - Can you run this test query as the service account and share the result:
  SELECT COUNT(*) FROM foods_published_prod;
  SELECT * FROM foods_published_prod LIMIT 1;
  - Are there any Row Level Security (RLS) policies enabled on these views? If yes, what are the conditions?
  - Is there a difference in permissions between counting rows vs selecting data?

  3. Data Volume & Performance

  - How many rows are in foods_published_prod and foods_published_preview? (The service reports 9339 but let's confirm)
  - Is there a timeout or max rows limit configured in Supabase for SELECT queries?
  - Are there any indexes on these views? Particularly on commonly filtered columns like brand, life_stage, available_countries?

  4. Column Names & Data Types

  - Do these columns exist exactly as named (case-sensitive)?
    - brand, product_name, brand_slug
    - kcal_per_100g or kcal_per_kg
    - ingredients_tokens (array type?)
    - available_countries (array type?)
    - life_stage, form, price_bucket
  - Are any columns computed/virtual that might fail during selection?

  5. Service Key Configuration

  - Is the service key we're using (SUPABASE_SERVICE_KEY) valid and active?
  - Does it bypass RLS as expected for service keys?
  - Has it been rotated recently?

  6. Error Details

  - Can you check the Supabase logs for these specific request IDs and share the actual error:
    - 1757947360-d81025e2 (Food Recommendations)
    - 1757947375.473443-139671197682384 (Brand Recommendations)
    - 1757947429-88716cfc (Search Products)
  - Are there any rate limits or connection limits being hit?

  7. Testing Query

  Please run this exact query that our service is attempting and share both the result and any errors:
  # This is what our Python client is doing:
  client.table("foods_published_prod").select("*").execute()

  8. Network/API Gateway

  - Is there an API gateway or proxy between our Cloud Run service and Supabase that might be modifying requests?
  - Are there any IP whitelist requirements?
  - Is the response size limited (e.g., max 6MB response)?

  9. Alternative Access Methods

  - Should we be using the REST API directly instead of the Python client?
  - Is there a specific query pattern we should follow (e.g., always include .limit() or .range())?
  - Should we paginate large result sets? If so, what's the recommended page size?

  10. Quick Debug Test

  Can you create a minimal test view with just 10 rows called foods_test with the same permissions as foods_published_prod so we can verify if it's a data volume issue or a permission issue?

  Most Critical Questions (If Limited Time):

  1. Run this test as the service account: SELECT * FROM foods_published_prod LIMIT 1; - Does it work or error?
  2. Check Supabase logs for request ID 1757947360-d81025e2 - What's the actual error?
  3. Verify the service key is valid and has proper permissions
  4. Check if RLS is enabled on these views and if service key bypasses it

---

## ANSWERS FROM DATABASE TEAM (2024-09-15)

### 1. Table/View Verification

✅ **Both views exist and are accessible:**
- `foods_published_prod`: EXISTS - Contains 114 rows
- `foods_published_preview`: EXISTS - Contains 1,000 rows (NOT 9,339 as reported)

**Schema for foods_published_prod:**
```
brand: string
product_name: string
brand_slug: string
name_slug: string
product_key: string
form: string
life_stage: string
primary_protein: null (in test data)
kcal_per_100g: integer
kcal_per_100g_final: integer
kcal_is_estimated: boolean
protein_percent: integer
fat_percent: integer
price_per_kg: float
price_bucket: null (in test data)
has_chicken: boolean
has_poultry: boolean
quality_score: integer
product_url: string
image_url: string
source: string
ingredients_tokens: array
available_countries: array
sources: object/dict
allowlist_status: string
updated_at: string
```

### 2. Permissions & Access

✅ **Service account has full read access:**
- Can count rows: YES
- Can select data: YES
- Can select all rows: YES (tested with SELECT * - works fine)
- No apparent RLS restrictions for service account

### 3. Data Volume & Performance

⚠️ **CRITICAL FINDING:**
- `foods_published_prod`: 114 rows (small, no issues)
- `foods_published_preview`: 1,000 rows (NOT 9,339 as your service reports)
- Both queries complete successfully with `SELECT *`
- No timeout issues observed

### 4. Column Names & Data Types

❌ **COLUMN ISSUE FOUND:**
- `kcal_per_kg` does NOT exist - use `kcal_per_100g` instead
- All other requested columns exist:
  - ✅ brand (string)
  - ✅ product_name (string)
  - ✅ brand_slug (string)
  - ✅ kcal_per_100g (integer)
  - ❌ kcal_per_kg (DOES NOT EXIST)
  - ✅ ingredients_tokens (array)
  - ✅ available_countries (array)
  - ✅ life_stage (string)
  - ✅ form (string)
  - ✅ price_bucket (null in test data, but column exists)

### 5. Service Key Configuration

✅ **Service key is valid and working:**
- Successfully authenticated
- Can read both views
- Can perform SELECT * queries
- Appears to bypass any RLS policies

### 6. Error Details

⚠️ **Cannot access Supabase logs directly** - you'll need to check these in the Supabase dashboard

### 7. Testing Query Results

✅ **This exact query WORKS:**
```python
client.table("foods_published_prod").select("*").execute()
# Returns: 114 rows successfully

client.table("foods_published_preview").select("*").execute()  
# Returns: 1,000 rows successfully
```

### 8. Potential Issues to Investigate

1. **Row count mismatch**: Your service thinks there are 9,339 rows in preview but there are only 1,000
2. **Column name error**: Using `kcal_per_kg` instead of `kcal_per_100g`
3. **Possible caching issue**: The service might be using cached/stale metadata

### 9. Recommendations

1. **Fix column reference**: Change `kcal_per_kg` to `kcal_per_100g` in your queries
2. **Verify connection**: Your service might be connecting to a different database/project
3. **Check response size**: 1,000 rows shouldn't hit any limits, but 9,339 might
4. **Add error handling**: Catch and log the specific Supabase error responses

### 10. Next Steps

Since the queries work fine from our testing, the issue is likely:
1. Wrong column name (`kcal_per_kg` vs `kcal_per_100g`)
2. Different database connection (wrong project/URL)
3. Client library version mismatch
4. Response size handling in Cloud Run

**To debug further, we need:**
- The exact error message from your Cloud Run logs
- Confirmation of which Supabase project URL you're connecting to
- The version of the Supabase Python client you're using