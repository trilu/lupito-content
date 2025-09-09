
# Instructions to Create Compatibility Views in Supabase

1. Go to Supabase SQL Editor: https://supabase.com/dashboard/project/cibjeqgftuxuezarjsdl/sql

2. Execute each SQL file in order:
   - sql/food_candidates_compat.sql
   - sql/food_candidates_sc_compat.sql  
   - sql/food_brands_compat.sql

3. After creating views, run this verification query:

```sql
SELECT 
    'food_candidates_compat' as view_name, 
    COUNT(*) as row_count 
FROM food_candidates_compat
UNION ALL
SELECT 
    'food_candidates_sc_compat', 
    COUNT(*) 
FROM food_candidates_sc_compat
UNION ALL
SELECT 
    'food_brands_compat', 
    COUNT(*) 
FROM food_brands_compat;
```

4. Sample data query:

```sql
SELECT 
    brand, 
    product_name, 
    form, 
    life_stage, 
    kcal_per_100g_final,
    primary_protein,
    has_chicken,
    price_bucket
FROM food_candidates_compat
LIMIT 5;
```
