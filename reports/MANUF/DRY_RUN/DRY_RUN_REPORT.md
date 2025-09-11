# BRAND NORMALIZATION DRY RUN REPORT

Generated: 2025-09-11 00:06:00
Mode: DRY RUN - No data modified

## 📊 SUMMARY

### Before
- Total products: 240
- Unique brands: 5
- Unique brand_slugs: 5

### After
- Total products: 240
- Unique brands: 5
- Unique brand_slugs: 5
- Products changed: 0
- Duplicate keys found: 9

## 🔧 CHANGES APPLIED

Total changes: 0

## 🔄 DUPLICATE KEYS DETECTED

Found 9 product keys with duplicates after normalization:

| Product Key | Count | Product IDs | Brands |
|-------------|-------|-------------|--------|
| briantos|briantos_sensitive_lamb_small_b... | 2 | briantos_030, briantos_031 | Briantos |
| belcando|belcando_active_beef_puppy|wet | 2 | belcando_003, belcando_020 | Belcando |
| briantos|briantos_light_lamb_adult|dry | 2 | briantos_037, briantos_040 | Briantos |
| alpha|alpha_grain_free_chicken_adult|dry | 2 | alpha_028, alpha_039 | Alpha |
| belcando|belcando_active_lamb_adult|dry | 2 | belcando_006, belcando_015 | Belcando |
## ✅ QUALITY CHECKS

### Guard Conditions
- No products starting with 'Canin ': ✅ PASS
- No products starting with 'Science Plan ': ✅ PASS
- No products starting with 'Pro Plan ': ✅ PASS
- No products starting with 'Prescription Diet ': ✅ PASS


## 📝 NEXT STEPS

1. Review changes above
2. Check for false positives
3. Run with dry_run=False to apply changes
4. Refresh materialized views
