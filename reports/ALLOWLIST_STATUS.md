# ALLOWLIST STATUS REPORT

Generated: 2025-09-10 23:30:00  
Last MV Refresh: 2025-09-10 23:30:00 UTC
Source: `brand_allowlist` table

## 📋 CURRENT ALLOWLIST

### ✅ ACTIVE BRANDS (In Production)

| Brand | Total SKUs | Food-Ready | Form | Life Stage | Ingredients | Kcal | Last Validated |
|-------|------------|------------|------|------------|-------------|------|----------------|
| **briantos** | 46 | **42** (91.3%) ✅ | 100.0% | 100.0% | 100.0% | 91.3% | 2025-09-10 23:16 |
| **bozita** | 34 | **31** (91.2%) ✅ | 97.1% | 100.0% | 100.0% | 91.2% | 2025-09-10 23:16 |

**Total Active**: 2 brands, 80 SKUs (**73 Food-Ready** ✅)

### 🔶 PENDING BRANDS (Awaiting Fixes)

| Brand | Issue | Form Gap | Life Gap | Target Date | Notes |
|-------|-------|----------|----------|-------------|-------|
| **brit** | Form detection | -3.2pp | ✅ Pass | 2025-09-11 | Fix pack applied, re-harvest needed |
| **alpha** | Form detection | -0.7pp | ✅ Pass | 2025-09-11 | Fix pack applied, re-harvest needed |
| **belcando** | Life stage detection | ✅ Pass | -0.9pp | 2025-09-11 | Fix pack applied, re-harvest needed |

| **brit** | 73 | **58** (79.5%) | Needs kcal fixes |
| **alpha** | 53 | **45** (84.9%) | Needs kcal fixes |
| **belcando** | 34 | **31** (91.2%) | Ready when promoted |

**Total Pending**: 3 brands, 160 SKUs (134 Food-Ready when fixed)

### ⏸️ PAUSED BRANDS

*No brands currently paused*

### ❌ REMOVED BRANDS

*No brands have been removed*

## 📊 ALLOWLIST STATISTICS

```
Status Distribution:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ACTIVE   ████████████████ 40% (2 brands)
PENDING  ████████████████████████ 60% (3 brands)
PAUSED   ░░░░░░░░░░░░░░░░ 0% (0 brands)
REMOVED  ░░░░░░░░░░░░░░░░ 0% (0 brands)
```

## 🍖 FOOD-READY STATUS

### What Makes a SKU Food-Ready?
- ✅ `life_stage` not null (for profile matching)
- ✅ `kcal_per_100g` between 40-600 (valid range)
- ✅ `ingredients_tokens` present (for allergen detection)

### Production Readiness
| Brand | Products in Catalog | Food-Ready | Can Serve Adult Dogs? |
| briantos | 46 | 42 | ✅ Yes (30+ adult SKUs) |
| bozita | 34 | 31 | ✅ Yes (20+ adult SKUs) |
| **Total** | **80** | **73** | ✅ Yes (50+ adult SKUs) |

### By Field (Active Brands Only)
| Field | Coverage | Products with Data |
|-------|----------|-------------------|
| Form | 98.8% | 79/80 |
| Life Stage | 97.5% | 78/80 |
| Ingredients | 100.0% | 80/80 |
| Price | 85.0% | 68/80 |
| Kcal | 91.3% | 73/80 |

## 🔄 RECENT CHANGES

| Date | Brand | Action | Changed By | Reason |
|------|-------|--------|------------|--------|
| 2025-09-10 21:00 | belcando | ADD (PENDING) | Data Engineering | Near pass - fixing life stage |
| 2025-09-10 21:00 | alpha | ADD (PENDING) | Data Engineering | Near pass - fixing form detection |
| 2025-09-10 21:00 | brit | ADD (PENDING) | Data Engineering | Near pass - fixing form detection |
| 2025-09-10 20:00 | bozita | ADD (ACTIVE) | Data Engineering | Passed all quality gates |
| 2025-09-10 20:00 | briantos | ADD (ACTIVE) | Data Engineering | Passed all quality gates |

## 🎯 QUALITY GATE STATUS

### Requirements for ACTIVE Status
- ✅ Form Coverage ≥ 95%
- ✅ Life Stage Coverage ≥ 95%
- ✅ Ingredients Coverage ≥ 85%
- ✅ Price Bucket Coverage ≥ 70%
- ✅ Kcal Outliers = 0

### Pending Brands Progress
| Brand | Form | Life | Ingr | Price | Kcal | Ready? |
|-------|------|------|------|-------|------|--------|
| brit | 91.8% ❌ | 95.9% ✅ | 100% ✅ | 82.2% ✅ | 0 ✅ | 4/5 |
| alpha | 94.3% ❌ | 98.1% ✅ | 100% ✅ | 83.0% ✅ | 0 ✅ | 4/5 |
| belcando | 97.1% ✅ | 94.1% ❌ | 100% ✅ | 88.2% ✅ | 0 ✅ | 4/5 |

## 🔧 SQL QUERIES

### View Current Allowlist
```sql
SELECT * FROM brand_allowlist 
ORDER BY status, brand_slug;
```

### Check Active Brands
```sql
SELECT * FROM active_brand_allowlist;
```

### Monitor Pending Brands
```sql
SELECT * FROM pending_brand_allowlist;
```

### Add New Brand (Example)
```sql
SELECT add_brand_to_allowlist(
    'new_brand', 
    'Your Name', 
    'Reason for adding',
    95.5,  -- form_coverage
    96.0,  -- life_stage_coverage
    90.0,  -- ingredients_coverage
    75.0,  -- price_bucket_coverage
    0      -- kcal_outliers
);
```

### Promote Pending to Active
```sql
SELECT promote_brand_to_active(
    'brit',
    'Your Name',
    'Fixed form detection, now meets all gates'
);
```

## 📝 NOTES

### Why These Brands?
1. **Briantos & Bozita**: First brands to pass all quality gates in pilot
2. **Brit, Alpha, Belcando**: High SKU count + near passing (minor fixes needed)

### Next Actions
1. Re-harvest Brit, Alpha, Belcando with enhanced selectors
2. Validate quality gates after re-harvest
3. Promote to ACTIVE status if gates pass
4. Begin Wave 1 brands (Acana, Advance, Almo Nature, etc.)

### Allowlist Management Policy
- Brands must pass ALL quality gates for ACTIVE status
- PENDING brands get 1 week to fix issues
- PAUSED status for temporary issues (site down, etc.)
- REMOVED only for discontinued brands

## 🔐 ACCESS CONTROL

```sql
-- Current permissions
GRANT SELECT ON brand_allowlist TO readonly_role;
GRANT SELECT, INSERT, UPDATE ON brand_allowlist TO admin_role;
GRANT SELECT ON brand_allowlist_audit TO audit_role;
```

---

**Report Generated By**: Automated System  
**Next Refresh**: 2025-09-11 02:00:00 UTC  
**Manual Refresh**: `SELECT refresh_allowlist_status();`