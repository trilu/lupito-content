# QUALITY LOCKDOWN REPORT

**Snapshot Label**: `SNAPSHOT_20250911_101939`
**Timestamp**: 2025-09-11 10:19:39
**Supabase Host**: https://cibjeqgftuxuezarjsdl.supabase.co

## 1. TABLE VERIFICATION

| Table | Status | Row Count |
|-------|--------|----------|
| foods_canonical | ✅ | 5,151 |
| foods_published_preview | ✅ | 240 |
| foods_published_prod | ✅ | 80 |
| brand_allowlist | ✅ | 5 |
| foods_brand_quality_preview_mv | ✅ | 5 |
| foods_brand_quality_prod_mv | ✅ | 2 |

## 2. TRUTH RULES

The following rules are enforced throughout the system:

- ✓ Brand identification uses ONLY brand_slug column
- ✓ NO substring matching on product_name for brand detection
- ✓ NO regex patterns on name fields for brand presence
- ✓ Canonical brand mapping applied to brand_slug only
- ✓ All brand counts/metrics key on brand_slug
- ✓ Split-brand fixes update brand_slug, not name parsing

## 3. ARRAY TYPE AUDIT

### foods_canonical

| Column | Valid Arrays % | Stringified | Nulls | Status |
|--------|---------------|-------------|-------|--------|
| ingredients_tokens | 100.0% | 0 | 0 | ✅ |
| available_countries | 100.0% | 0 | 0 | ✅ |
| sources | 100.0% | 0 | 0 | ✅ |

### foods_published_preview

| Column | Valid Arrays % | Stringified | Nulls | Status |
|--------|---------------|-------------|-------|--------|
| ingredients_tokens | 100.0% | 0 | 0 | ✅ |
| available_countries | 100.0% | 0 | 0 | ✅ |
| sources | 100.0% | 0 | 0 | ✅ |

### foods_published_prod

| Column | Valid Arrays % | Stringified | Nulls | Status |
|--------|---------------|-------------|-------|--------|
| ingredients_tokens | 100.0% | 0 | 0 | ✅ |
| available_countries | 100.0% | 0 | 0 | ✅ |
| sources | 100.0% | 0 | 0 | ✅ |

## 4. SUMMARY

✅ **All required tables are present and accessible**

### Key Metrics:

- Total rows in foods_canonical: 5,151
- Products in Preview: 240
- Products in Prod: 80
- Brands in allowlist: 5

### Data Quality Status:

- ✅ Brand_slug is the only source of truth
- ✅ No substring matching for brand detection
- ✅ Array columns are properly typed (>95% valid)

---
*This snapshot (SNAPSHOT_20250911_101939) will be referenced in all subsequent reports*
