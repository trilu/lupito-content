# FOODS LINEAGE

Generated: 2025-09-11 09:08:20

## Table Inventory

| Path | Category | Rows | Last Modified |
|------|----------|------|---------------|
| reports/MANUF/PRODUCTION/foods_published_prod.csv | published | 340 | 2025-09-11 09:02 |
| reports/MANUF/PRODUCTION/foods_published_prod.csv | published | 340 | 2025-09-11 09:02 |
| reports/MANUF/foods_published_v2.csv | published | 994 | 2025-09-11 09:02 |
| reports/MANUF/foods_published_v2.csv | published | 994 | 2025-09-11 09:02 |
| reports/MANUF/foods_enrichment_manuf.csv | scratch | 121 | 2025-09-11 09:02 |
| reports/MANUF/foods_enrichment_manuf.csv | scratch | 121 | 2025-09-11 09:02 |

## Data Flow Diagram

```
Source/Raw Tables
    ↓
Compat/Normalization
    ↓
foods_union_all (union of all sources)
    ↓
foods_canonical (deduped, scored)
    ↓
foods_published_preview / foods_published_prod
```
