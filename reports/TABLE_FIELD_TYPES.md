# TABLE FIELD TYPES

Generated: 2025-09-11 08:40:36

## foods_published_v2.csv

| Column | Data Type | % Null | Sample Value |
|--------|-----------|--------|---------------|
| product_key | object | 0.0% | 4paws|supplies_premium_cold_pressed_lovely_lamb|dr... |
| brand | object | 0.0% | 4PAWS |
| brand_slug | object | 0.0% | 4paws |
| product_name | object | 0.0% | Supplies Premium Cold Pressed Lovely Lamb |
| name_slug | object | 0.0% | supplies_premium_cold_pressed_lovely_lamb |
| form | object | 39.5% | dry |
| life_stage | object | 32.4% | adult |
| kcal_per_100g | float64 | 3.6% | 366.0 |
| kcal_is_estimated | bool | 0.0% | False |
| protein_percent | float64 | 3.5% | 2.0 |
| fat_percent | float64 | 0.6% | 6.0 |
| ingredients_tokens | object | 0.0% | [] |
| primary_protein | object | 93.8% | chicken |
| has_chicken | bool | 0.0% | False |
| has_poultry | bool | 0.0% | False |
| available_countries | object | 0.0% | ['UK', 'EU'] |
| price_per_kg | float64 | 75.3% | 15.2 |
| price_bucket | object | 78.5% | mid |
| image_url | object | 1.3% | https://cibjeqgftuxuezarjsdl.supabase.co/storage/v... |
| product_url | object | 1.3% | https://petfoodexpert.com/food/4paws-supplies-prem... |
| source | object | 0.0% | food_candidates |
| updated_at | object | 0.0% | 2025-09-07T02:11:05.236725+00:00 |
| quality_score | int64 | 0.0% | 2 |
| sources | object | 0.0% | [{'source': 'food_candidates', 'updated_at': '2025... |
| source_manuf | object | 69.3% | manufacturer |
| fetched_at | object | 69.3% | 2025-09-10T19:05:36.170162 |
| confidence | float64 | 69.3% | 0.8 |
| form_manuf | object | 81.2% | dry |
| form_from | object | 81.2% | enrichment_manuf |
| form_confidence | float64 | 81.2% | 0.7200000000000001 |
| life_stage_manuf | object | 80.7% | adult |
| life_stage_from | object | 80.7% | enrichment_manuf |
| life_stage_confidence | float64 | 80.7% | 0.7200000000000001 |
| price_eur | float64 | 72.2% | 11.069080341901277 |
| price_eur_from | object | 72.2% | enrichment_manuf |
| price_eur_confidence | float64 | 72.2% | 0.7200000000000001 |
| price_per_kg_eur | float64 | 72.2% | 5.534540170950638 |
| price_per_kg_eur_from | object | 72.2% | enrichment_manuf |
| price_per_kg_eur_confidence | float64 | 72.2% | 0.7200000000000001 |

## 02_foods_published_sample.csv

| Column | Data Type | % Null | Sample Value |
|--------|-----------|--------|---------------|
| product_key | object | 0.0% | 4paws|supplies_premium_cold_pressed_lovely_lamb|dr... |
| brand | object | 0.0% | 4PAWS |
| brand_slug | object | 0.0% | 4paws |
| product_name | object | 0.0% | Supplies Premium Cold Pressed Lovely Lamb |
| ingredients_tokens | object | 0.0% | [] |
| form | object | 54.4% | raw |
| life_stage | object | 45.6% | puppy |
| kcal_per_100g | float64 | 4.1% | 366.0 |

## brand_quality_metrics.csv

| Column | Data Type | % Null | Sample Value |
|--------|-----------|--------|---------------|
| brand_slug | object | 0.0% | brit |
| sku_count | int64 | 0.0% | 73 |
| form_cov | float64 | 0.0% | 91.8 |
| life_stage_cov | float64 | 0.0% | 95.9 |
| ingredients_cov | float64 | 0.0% | 100.0 |
| kcal_cov | float64 | 0.0% | 84.59 |
| price_cov | float64 | 0.0% | 80.25 |
| price_bucket_cov | float64 | 0.0% | 80.25 |
| completion_pct | float64 | 0.0% | 90.51 |
| kcal_outliers | int64 | 0.0% | 1 |
| status | object | 0.0% | NEAR |
| last_refreshed_at | object | 0.0% | 2025-09-10T22:23:36.928152 |
