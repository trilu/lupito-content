# Brand Normalization Audit Report
Generated: 2025-09-12T12:44:38.348016

## Summary
- **Products Updated**: 137
- **Brands Before**: 88
- **Brands After**: 86
- **Brand Reduction**: 2

## Top Brand Changes

| Brand | Products Before | Products After | Change |
|-------|----------------|----------------|--------|
| Arden | 31 | 0 | -31 |
| Arden Grange | 0 | 40 | +40 |
| Barking | 29 | 0 | -29 |
| Barking Heads | 0 | 25 | +25 |
| Bosch | 0 | 28 | +28 |
| bosch | 22 | 0 | -22 |

## Updated Products Sample

| Product Key | Old Brand | New Brand |
|-------------|-----------|-----------|
| acana|acana_adult_dog_recipe_(... | ACANA | Acana |
| arden|grange_adult_grain_free_... | Arden | Arden Grange |
| almo_nature|almo_nature_bioorg... | Almo Nature | Almo Nature |
| almo_nature|almo_nature_hfc_ad... | Almo Nature | Almo Nature |
| almo_nature|almo_nature_hfc_ad... | Almo Nature | Almo Nature |
| almo_nature|almo_nature_hfc_ad... | Almo Nature | Almo Nature |
| almo_nature|almo_nature_hfc|we... | Almo Nature | Almo Nature |
| almo_nature|almo_nature_holist... | Almo Nature | Almo Nature |
| almo_nature|almo_nature_holist... | Almo Nature | Almo Nature |
| almo_nature|almo_nature_holist... | Almo Nature | Almo Nature |
| almo_nature|almo_nature_holist... | Almo Nature | Almo Nature |
| almo_nature|almo_nature_holist... | Almo Nature | Almo Nature |
| almo_nature|almo_nature_holist... | Almo Nature | Almo Nature |
| almo_nature|almo_nature_saver_... | Almo Nature | Almo Nature |
| alpha_spirit|alpha_spirit_7_da... | Alpha Spirit | Alpha Spirit |
| aniforte|pure_nature_country_b... | AniForte | Aniforte |
| aniforte|semi_moist_cold_press... | AniForte | Aniforte |
| animonda|animonda_grancarno_or... | animonda | Animonda |
| aniforte|pure_nature_farms_lam... | AniForte | Aniforte |
| aniforte|pure_nature_greenfiel... | AniForte | Aniforte |

... and 117 more

## Rollback Information
- Rollback SQL saved to: sql/rollback_brand_normalization.sql
- Rollback data saved to: data/audit/rollback_data.csv
- Before snapshot saved to: data/audit/before_normalization.csv

## Next Steps
1. Execute: sql/refresh_views_after_normalization.sql
2. Verify changes in foods_published_prod
3. Test admin interface for brand display
