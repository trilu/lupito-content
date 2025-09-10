# BRAND ALLOWLIST CHANGELOG

This document tracks all changes to the production brand allowlist for transparency and auditability.

## Format
Each entry follows this format:
```
## YYYY-MM-DD HH:MM UTC
**Action**: ADD|REMOVE|PAUSE|REACTIVATE|UPDATE
**Brand**: brand_slug
**Status**: ACTIVE|PENDING|PAUSED|REMOVED
**Changed By**: Name/Team
**Reason**: Brief explanation
**Coverage**: Form X%, Life Stage Y%, Ingredients Z%
```

---

## 2025-09-10 22:30 UTC
**Action**: SYSTEM INITIALIZATION  
**Brands**: Multiple  
**Changed By**: Data Engineering  
**Reason**: Initial allowlist setup with pilot results

### ACTIVE Brands Added:
- **briantos**: Passed all quality gates (Form 100%, Life Stage 97.8%, Ingredients 100%)
- **bozita**: Passed all quality gates (Form 97.1%, Life Stage 97.1%, Ingredients 100%)

### PENDING Brands Added:
- **brit**: Near pass - fixing form detection (Form 91.8%, Life Stage 95.9%, Ingredients 100%)
- **alpha**: Near pass - fixing form detection (Form 94.3%, Life Stage 98.1%, Ingredients 100%)
- **belcando**: Near pass - fixing life stage (Form 97.1%, Life Stage 94.1%, Ingredients 100%)

---

## 2025-09-10 21:00 UTC
**Action**: ADD  
**Brand**: belcando  
**Status**: PENDING  
**Changed By**: Data Engineering  
**Reason**: Near pass in pilot, applying fix pack for life stage detection  
**Coverage**: Form 97.1%, Life Stage 94.1% (target 95%), Ingredients 100%  
**Notes**: Enhanced selectors added, re-harvest scheduled

---

## 2025-09-10 21:00 UTC
**Action**: ADD  
**Brand**: alpha  
**Status**: PENDING  
**Changed By**: Data Engineering  
**Reason**: Near pass in pilot, applying fix pack for form detection  
**Coverage**: Form 94.3% (target 95%), Life Stage 98.1%, Ingredients 100%  
**Notes**: Multi-language keywords added, inference rules implemented

---

## 2025-09-10 21:00 UTC
**Action**: ADD  
**Brand**: brit  
**Status**: PENDING  
**Changed By**: Data Engineering  
**Reason**: Near pass in pilot, applying fix pack for form detection  
**Coverage**: Form 91.8% (target 95%), Life Stage 95.9%, Ingredients 100%  
**Notes**: Product line mapping added, fallback rules implemented

---

## 2025-09-10 20:00 UTC
**Action**: ADD  
**Brand**: bozita  
**Status**: ACTIVE  
**Changed By**: Data Engineering  
**Reason**: Passed all quality gates in production pilot  
**Coverage**: Form 97.1%, Life Stage 97.1%, Ingredients 100%, Price 88.2%  
**Notes**: First cohort for production deployment

---

## 2025-09-10 20:00 UTC
**Action**: ADD  
**Brand**: briantos  
**Status**: ACTIVE  
**Changed By**: Data Engineering  
**Reason**: Passed all quality gates in production pilot  
**Coverage**: Form 100%, Life Stage 97.8%, Ingredients 100%, Price 82.6%  
**Notes**: First cohort for production deployment

---

## Upcoming Changes (Planned)

### 2025-09-11 (Expected)
- **PROMOTE**: brit from PENDING to ACTIVE (after re-harvest)
- **PROMOTE**: alpha from PENDING to ACTIVE (after re-harvest)
- **PROMOTE**: belcando from PENDING to ACTIVE (after re-harvest)

### 2025-09-12 (Wave 1)
- **ADD**: acana as PENDING (32 SKUs)
- **ADD**: advance as PENDING (28 SKUs)
- **ADD**: almo_nature as PENDING (26 SKUs)
- **ADD**: animonda as PENDING (25 SKUs)
- **ADD**: applaws as PENDING (24 SKUs)

---

## Allowlist Management Rules

1. **Adding Brands**
   - Must have completed harvest
   - Coverage metrics must be documented
   - Reason for addition must be provided
   - Changed by must be recorded

2. **Promoting to ACTIVE**
   - Form coverage ≥ 95%
   - Life stage coverage ≥ 95%
   - Ingredients coverage ≥ 85%
   - Price bucket coverage ≥ 70%
   - Zero kcal outliers

3. **Pausing Brands**
   - Temporary issues (site down, API issues)
   - Data quality concerns
   - Maximum pause: 2 weeks

4. **Removing Brands**
   - Brand discontinued
   - Persistent quality issues
   - Business decision

## SQL Commands for Changes

### Add new brand
```sql
INSERT INTO brand_allowlist_audit (
    brand_slug, action, new_status, changed_by, reason
) VALUES (
    'new_brand', 'ADD', 'PENDING', 'Your Name', 'Starting harvest'
);
```

### Promote to active
```sql
UPDATE brand_allowlist 
SET status = 'ACTIVE', 
    updated_at = CURRENT_TIMESTAMP,
    last_validated = CURRENT_TIMESTAMP
WHERE brand_slug = 'brand_name'
  AND form_coverage >= 95
  AND life_stage_coverage >= 95;
```

### View audit trail
```sql
SELECT * FROM brand_allowlist_audit 
WHERE brand_slug = 'brand_name'
ORDER BY changed_at DESC;
```

---

**Note**: This changelog is the source of truth for all allowlist changes. Any modification to the production allowlist must be documented here with appropriate justification.