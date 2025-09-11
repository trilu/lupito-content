# ANOMALY SUMMARY

Generated: 2025-09-11 08:40:36

## Anomalies by Type

### Stringified Arrays

| Table | Column | Affected Rows |
|-------|--------|---------------|
| foods_published_v2.csv | ingredients_tokens | 1264 |
| foods_published_v2.csv | available_countries | 1264 |
| foods_published_v2.csv | sources | 1264 |
| 02_foods_published_sample.csv | ingredients_tokens | 1000 |

**Total rows with stringified arrays**: 4792

### Invalid Slugs

| Table | Column | Count | Samples |
|-------|--------|-------|---------|
| foods_published_v2.csv | name_slug | 234 | grain_free_haddock,_sweet_potato_with_parsley, grain_free_lamb,_sweet_potato__mint, grain_free_light_turkey,_sweet_potato__cranberry |