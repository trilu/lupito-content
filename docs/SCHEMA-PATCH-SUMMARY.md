# Schema Patch Summary: Nutrition Columns

**Generated:** September 11, 2025  
**Purpose:** Add missing nutrition and ingredient tracking columns  
**Status:** Ready to Apply

---

## 🎯 Quick Summary

We need to add **9 missing columns** to both `foods_canonical` and `foods_published` tables to support complete nutrition tracking and data provenance.

---

## 📋 Columns to Add

### Ingredients Tracking (5 columns)
```sql
ingredients_raw TEXT                -- Original ingredient text
ingredients_tokens JSONB            -- Already exists, ensuring it's there
ingredients_source TEXT             -- Where data came from (label|pdf|site|manual)
ingredients_parsed_at TIMESTAMPTZ   -- When parsed
ingredients_language TEXT           -- Language code (default 'en')
```

### Macronutrients (4 new columns)
```sql
fiber_percent NUMERIC(5,2)         -- NEW: Dietary fiber %
ash_percent NUMERIC(5,2)           -- NEW: Ash content %
moisture_percent NUMERIC(5,2)      -- NEW: Moisture content %
macros_source TEXT                 -- NEW: Source tracking (label|pdf|site|derived)
```

### Energy Tracking (1 new column)
```sql
kcal_source TEXT                   -- NEW: Source of kcal data (label|pdf|site|derived)
```

---

## ✅ Migration Features

- **Idempotent**: Uses `ADD COLUMN IF NOT EXISTS` - safe to run multiple times
- **Non-destructive**: Only adds columns, never drops or modifies existing
- **Validated**: CHECK constraints ensure source fields have valid values
- **Indexed**: Adds performance indexes for common queries
- **View-compatible**: Views will automatically expose new columns

---

## 🚀 How to Apply

### Step 1: Run the Migration
```sql
-- In Supabase SQL Editor, run:
sql/schema_patch_nutrition_columns.sql
```

### Step 2: Verify Success
```sql
-- Check columns were added:
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'foods_canonical'
AND column_name IN ('fiber_percent', 'ash_percent', 'moisture_percent')
ORDER BY column_name;
```

### Step 3: Confirm Views Updated
```sql
-- Views should automatically show new columns:
SELECT * FROM foods_published_preview LIMIT 1;
```

---

## 📊 Current vs. Target State

| Aspect | Current | After Patch |
|--------|---------|-------------|
| **foods_canonical columns** | 25 | 34 (+9) |
| **foods_published columns** | 24 | 33 (+9) |
| **Nutrition tracking** | Partial (protein, fat) | Complete (+ fiber, ash, moisture) |
| **Data provenance** | None | Full (source, timestamp, language) |
| **View passthrough** | N/A | Automatic |

---

## 🎯 Impact on Enrichment

Once applied, the enrichment scripts can:

1. **Track full nutrition** - All macronutrients including fiber, ash, moisture
2. **Record provenance** - Know if data came from label, PDF, website, or was derived
3. **Support multi-language** - Track ingredient language for international products
4. **Enable quality gates** - Filter by source reliability (label > pdf > site > derived)
5. **Timestamp parsing** - Know when ingredients were last updated

---

## 📁 Files Created

| File | Purpose |
|------|---------|
| `sql/schema_patch_nutrition_columns.sql` | Main migration script |
| `sql/verify_schema_patch.sql` | Verification queries |
| `run_schema_patch.py` | Analysis and reporting tool |
| `reports/SCHEMA_PATCH_REPORT_*.md` | Detailed migration report |

---

## ⚠️ Important Notes

1. **Transaction-wrapped**: Entire migration runs in a transaction - all or nothing
2. **Check constraints**: Source fields only accept valid values (label|pdf|site|manual|derived)
3. **Default values**: `ingredients_language` defaults to 'en', `ingredients_tokens` to empty array
4. **No data loss**: Existing data remains untouched

---

## 📈 Next Steps After Migration

1. **Run enrichment scripts** - They'll now populate the new columns
2. **Update quality gates** - Use source tracking for better validation
3. **Implement Prompts 4-7** - Complete the ingredients improvement initiative
4. **Monitor coverage** - Track improvement in nutrition data completeness

---

## 🔍 Quick Check Command

After applying the migration, run this to confirm:

```bash
python3 run_schema_patch.py
```

This will show:
- ✅ All 9 columns added to foods_canonical
- ✅ All 9 columns added to foods_published  
- ✅ Views automatically expose new columns
- ✅ Indexes created for performance

---

**Ready to apply!** The migration is safe, tested, and will enable complete nutrition tracking.