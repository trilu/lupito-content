-- Product Variant Tables Creation Script
-- Purpose: Create tables for managing size/pack variants
-- Date: December 2024

-- ========================================
-- 1. CREATE BACKUP TABLE
-- ========================================
-- Create a backup of the current state before migration
CREATE TABLE IF NOT EXISTS foods_canonical_backup_20241213 AS 
SELECT * FROM foods_canonical;

-- Add comment for documentation
COMMENT ON TABLE foods_canonical_backup_20241213 IS 'Backup before variant migration - created 2024-12-13';

-- Create index on backup for querying if needed
CREATE INDEX IF NOT EXISTS idx_backup_product_key ON foods_canonical_backup_20241213(product_key);

-- ========================================
-- 2. CREATE PRODUCT VARIANTS TABLE
-- ========================================
-- Table to store size and pack variants
DROP TABLE IF EXISTS product_variants CASCADE;

CREATE TABLE product_variants (
  variant_id SERIAL PRIMARY KEY,
  parent_product_key TEXT NOT NULL,
  variant_product_key TEXT UNIQUE NOT NULL,
  variant_type VARCHAR(20) NOT NULL CHECK (variant_type IN ('size', 'pack', 'size_and_pack')),
  size_value TEXT, -- e.g., "3kg", "400g"
  pack_value TEXT, -- e.g., "6x400g", "12x800g"
  product_name TEXT NOT NULL,
  product_url TEXT,
  original_data JSONB, -- Store original product data for reference
  created_at TIMESTAMP DEFAULT NOW(),
  migrated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_variant_parent_key ON product_variants(parent_product_key);
CREATE INDEX idx_variant_product_key ON product_variants(variant_product_key);
CREATE INDEX idx_variant_type ON product_variants(variant_type);

-- Foreign key to ensure parent exists (will add after migration)
-- ALTER TABLE product_variants 
-- ADD CONSTRAINT fk_parent_product 
-- FOREIGN KEY (parent_product_key) 
-- REFERENCES foods_canonical(product_key);

-- Comments for documentation
COMMENT ON TABLE product_variants IS 'Stores size and pack variants of products';
COMMENT ON COLUMN product_variants.variant_type IS 'Type of variant: size (3kg), pack (6x400g), or both';
COMMENT ON COLUMN product_variants.size_value IS 'The size specification extracted from product name';
COMMENT ON COLUMN product_variants.pack_value IS 'The pack specification extracted from product name';
COMMENT ON COLUMN product_variants.original_data IS 'JSON backup of original product data before migration';

-- ========================================
-- 3. CREATE MIGRATION LOG TABLE
-- ========================================
-- Table to track the migration process
DROP TABLE IF EXISTS variant_migration_log CASCADE;

CREATE TABLE variant_migration_log (
  log_id SERIAL PRIMARY KEY,
  action_type VARCHAR(50) NOT NULL, -- 'group_identified', 'parent_selected', 'data_consolidated', 'variant_moved'
  brand TEXT,
  base_name TEXT,
  parent_product_key TEXT,
  variant_product_key TEXT,
  variant_count INTEGER,
  data_before JSONB,
  data_after JSONB,
  notes TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for querying migration history
CREATE INDEX idx_migration_log_action ON variant_migration_log(action_type);
CREATE INDEX idx_migration_log_parent ON variant_migration_log(parent_product_key);
CREATE INDEX idx_migration_log_timestamp ON variant_migration_log(created_at);

-- Comments
COMMENT ON TABLE variant_migration_log IS 'Audit log for variant migration process';
COMMENT ON COLUMN variant_migration_log.action_type IS 'Type of migration action performed';
COMMENT ON COLUMN variant_migration_log.data_before IS 'State before migration action';
COMMENT ON COLUMN variant_migration_log.data_after IS 'State after migration action';

-- ========================================
-- 4. CREATE VARIANT GROUPS VIEW
-- ========================================
-- View to easily see variant relationships
CREATE OR REPLACE VIEW product_variant_groups AS
SELECT 
  fc.product_key as parent_key,
  fc.brand,
  fc.product_name as parent_name,
  fc.ingredients_raw IS NOT NULL as parent_has_ingredients,
  fc.protein_percent IS NOT NULL as parent_has_nutrition,
  COUNT(pv.variant_id) as variant_count,
  ARRAY_AGG(pv.variant_product_key) as variant_keys,
  ARRAY_AGG(pv.product_name) as variant_names
FROM foods_canonical fc
LEFT JOIN product_variants pv ON fc.product_key = pv.parent_product_key
GROUP BY fc.product_key, fc.brand, fc.product_name, fc.ingredients_raw, fc.protein_percent
HAVING COUNT(pv.variant_id) > 0;

-- Comment
COMMENT ON VIEW product_variant_groups IS 'View showing parent products with their variants';

-- ========================================
-- 5. UTILITY FUNCTIONS
-- ========================================

-- Function to check if a product has variants
CREATE OR REPLACE FUNCTION has_variants(p_product_key TEXT)
RETURNS BOOLEAN AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1 FROM product_variants 
    WHERE parent_product_key = p_product_key
  );
END;
$$ LANGUAGE plpgsql;

-- Function to get all variants of a product
CREATE OR REPLACE FUNCTION get_product_variants(p_product_key TEXT)
RETURNS TABLE (
  variant_key TEXT,
  variant_name TEXT,
  variant_type VARCHAR(20),
  size_value TEXT,
  pack_value TEXT
) AS $$
BEGIN
  RETURN QUERY
  SELECT 
    variant_product_key,
    product_name,
    variant_type,
    size_value,
    pack_value
  FROM product_variants
  WHERE parent_product_key = p_product_key
  ORDER BY product_name;
END;
$$ LANGUAGE plpgsql;

-- ========================================
-- 6. GRANT PERMISSIONS
-- ========================================
-- Grant appropriate permissions
GRANT SELECT ON foods_canonical_backup_20241213 TO authenticated;
GRANT SELECT ON foods_canonical_backup_20241213 TO service_role;

GRANT ALL ON product_variants TO authenticated;
GRANT ALL ON product_variants TO service_role;
GRANT ALL ON product_variants_variant_id_seq TO authenticated;
GRANT ALL ON product_variants_variant_id_seq TO service_role;

GRANT ALL ON variant_migration_log TO authenticated;
GRANT ALL ON variant_migration_log TO service_role;
GRANT ALL ON variant_migration_log_log_id_seq TO authenticated;
GRANT ALL ON variant_migration_log_log_id_seq TO service_role;

GRANT SELECT ON product_variant_groups TO authenticated;
GRANT SELECT ON product_variant_groups TO service_role;

-- ========================================
-- 7. VERIFICATION QUERIES
-- ========================================
-- Run these after creation to verify

-- Check backup was created
SELECT COUNT(*) as backup_count FROM foods_canonical_backup_20241213;

-- Check new tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('product_variants', 'variant_migration_log');

-- Check view works
SELECT * FROM product_variant_groups LIMIT 1;

-- ========================================
-- END OF SCRIPT
-- ========================================