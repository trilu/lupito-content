# Updated Dogo Breed Scraper - Compatible with Existing Schema

## ✅ **Adapted for Existing Breeds Table**

### **Key Changes Made**
- **Preserves** your existing `breeds` table structure
- **Adds** new Dogo-specific columns with `dogo_` prefix
- **No data loss** - all your existing breed data remains intact
- **Clean separation** between existing data and new Dogo content

## 📋 **Updated Schema** (`breed_schema_updated.sql`)

### **Existing breeds table preserved + enhanced:**
- ✅ Keeps all your current fields: `name_en`, `size_category`, `avg_male_weight_kg`, etc.
- ➕ Adds Dogo fields: `dogo_size`, `dogo_energy`, `dogo_trainability`, etc.
- ➕ Adds `breed_slug` for canonical identification
- ➕ Adds `aliases` array for name variations

### **New tables created:**
- **`breed_raw`**: Raw HTML from Dogo.app (linked via `breed_slug`)
- **`breed_text_versions`**: 5-section narrative content (draft/published)
- **`breed_images`**: Hero images with attribution
- **Updated `breeds_published` view**: Combines existing + Dogo data

## 🔄 **Data Flow**

1. **Scraper extracts** Dogo breed data + narrative content
2. **Updates existing breeds** with new `dogo_*` columns (or creates new record)
3. **Stores raw HTML** in `breed_raw` table
4. **Saves narrative** in `breed_text_versions` (status='draft')
5. **Downloads images** to `dog-food/breeds/` bucket
6. **breeds_published view** provides clean API access

## 🚀 **Ready to Use**

### **Step 1: Execute Schema**
```sql
-- Run breed_schema_updated.sql in Supabase dashboard
-- Safely adds new columns to existing breeds table
```

### **Step 2: Test Scraper**
```bash
python3 jobs/dogo_breed_scraper.py --urls dogo_seed_breeds.txt
```

## 📊 **What You'll Get**

- **Existing data intact**: All current breed records preserved
- **Enhanced breed records**: New Dogo characteristics alongside existing data
- **Narrative content**: 5-section structured text (overview, temperament, training, grooming, health)
- **Hero images**: High-quality breed photos with attribution
- **Publishing workflow**: Draft → Published content versioning
- **Clean API**: `breeds_published` view combines everything

## 🎯 **Benefits of This Approach**

✅ **Zero data loss** - your existing breeds table stays intact  
✅ **Gradual enhancement** - breeds get Dogo data as they're processed  
✅ **Clear separation** - existing data vs Dogo data clearly distinguished  
✅ **Flexible** - can run scraper multiple times, only processes changed content  
✅ **API ready** - `breeds_published` view ready for consumption  

The scraper now works as an enhancement to your existing breed system rather than a replacement!