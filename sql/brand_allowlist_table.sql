-- ============================================================================
-- BRAND ALLOWLIST TABLE
-- Purpose: Transparent and auditable control of production brand enrichment
-- Generated: 2025-09-10
-- ============================================================================

-- Drop existing table if exists
DROP TABLE IF EXISTS brand_allowlist CASCADE;

-- Create allowlist table
CREATE TABLE brand_allowlist (
    brand_slug VARCHAR(100) PRIMARY KEY,
    status VARCHAR(20) NOT NULL CHECK (status IN ('ACTIVE', 'PENDING', 'PAUSED', 'REMOVED')),
    added_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    added_by VARCHAR(100) NOT NULL,
    reason TEXT NOT NULL,
    quality_gate_passed BOOLEAN NOT NULL DEFAULT false,
    form_coverage DECIMAL(5,2),
    life_stage_coverage DECIMAL(5,2),
    ingredients_coverage DECIMAL(5,2),
    price_bucket_coverage DECIMAL(5,2),
    kcal_outliers INTEGER DEFAULT 0,
    last_validated TIMESTAMP,
    notes TEXT,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create index for fast lookups
CREATE INDEX idx_allowlist_status ON brand_allowlist(status);
CREATE INDEX idx_allowlist_added_date ON brand_allowlist(added_date DESC);

-- Create audit log table for changes
CREATE TABLE brand_allowlist_audit (
    audit_id SERIAL PRIMARY KEY,
    brand_slug VARCHAR(100) NOT NULL,
    action VARCHAR(20) NOT NULL CHECK (action IN ('ADD', 'UPDATE', 'REMOVE', 'PAUSE', 'REACTIVATE')),
    old_status VARCHAR(20),
    new_status VARCHAR(20),
    changed_by VARCHAR(100) NOT NULL,
    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reason TEXT,
    details JSONB
);

-- Create trigger for audit logging
CREATE OR REPLACE FUNCTION audit_allowlist_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO brand_allowlist_audit (
            brand_slug, action, new_status, changed_by, reason, details
        ) VALUES (
            NEW.brand_slug, 'ADD', NEW.status, NEW.added_by, NEW.reason,
            jsonb_build_object(
                'form_coverage', NEW.form_coverage,
                'life_stage_coverage', NEW.life_stage_coverage,
                'quality_gate_passed', NEW.quality_gate_passed
            )
        );
    ELSIF TG_OP = 'UPDATE' THEN
        IF OLD.status != NEW.status THEN
            INSERT INTO brand_allowlist_audit (
                brand_slug, action, old_status, new_status, changed_by, reason, details
            ) VALUES (
                NEW.brand_slug, 
                CASE 
                    WHEN NEW.status = 'REMOVED' THEN 'REMOVE'
                    WHEN NEW.status = 'PAUSED' THEN 'PAUSE'
                    WHEN NEW.status = 'ACTIVE' AND OLD.status = 'PAUSED' THEN 'REACTIVATE'
                    ELSE 'UPDATE'
                END,
                OLD.status, NEW.status, NEW.added_by, NEW.reason,
                jsonb_build_object(
                    'form_coverage', NEW.form_coverage,
                    'life_stage_coverage', NEW.life_stage_coverage,
                    'quality_gate_passed', NEW.quality_gate_passed
                )
            );
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_allowlist_audit
AFTER INSERT OR UPDATE ON brand_allowlist
FOR EACH ROW
EXECUTE FUNCTION audit_allowlist_changes();

-- ============================================================================
-- INITIAL DATA POPULATION
-- Current production-ready brands based on pilot results
-- ============================================================================

INSERT INTO brand_allowlist (
    brand_slug, status, added_by, reason, quality_gate_passed,
    form_coverage, life_stage_coverage, ingredients_coverage, 
    price_bucket_coverage, kcal_outliers, last_validated
) VALUES
-- Brands that PASSED quality gates
('briantos', 'ACTIVE', 'Data Engineering', 'Passed all quality gates in pilot', true,
 100.0, 97.8, 100.0, 82.6, 0, '2025-09-10 20:00:00'),
 
('bozita', 'ACTIVE', 'Data Engineering', 'Passed all quality gates in pilot', true,
 97.1, 97.1, 100.0, 88.2, 0, '2025-09-10 20:00:00'),

-- Brands that are NEAR passing (pending fixes)
('brit', 'PENDING', 'Data Engineering', 'Near pass - fixing form detection (91.8% -> 95%)', false,
 91.8, 95.9, 100.0, 82.2, 0, '2025-09-10 21:00:00'),
 
('alpha', 'PENDING', 'Data Engineering', 'Near pass - fixing form detection (94.3% -> 95%)', false,
 94.3, 98.1, 100.0, 83.0, 0, '2025-09-10 21:00:00'),
 
('belcando', 'PENDING', 'Data Engineering', 'Near pass - fixing life stage (94.1% -> 95%)', false,
 97.1, 94.1, 100.0, 88.2, 0, '2025-09-10 21:00:00');

-- ============================================================================
-- VIEWS FOR EASY QUERYING
-- ============================================================================

-- View for active brands only
CREATE OR REPLACE VIEW active_brand_allowlist AS
SELECT 
    brand_slug,
    added_date,
    form_coverage,
    life_stage_coverage,
    ingredients_coverage,
    price_bucket_coverage,
    last_validated,
    DATE_PART('day', CURRENT_TIMESTAMP - last_validated) AS days_since_validation
FROM brand_allowlist
WHERE status = 'ACTIVE'
ORDER BY added_date;

-- View for pending brands with gap analysis
CREATE OR REPLACE VIEW pending_brand_allowlist AS
SELECT 
    brand_slug,
    GREATEST(0, 95 - form_coverage) AS form_gap,
    GREATEST(0, 95 - life_stage_coverage) AS life_stage_gap,
    GREATEST(0, 85 - ingredients_coverage) AS ingredients_gap,
    GREATEST(0, 70 - price_bucket_coverage) AS price_bucket_gap,
    kcal_outliers,
    reason,
    last_validated
FROM brand_allowlist
WHERE status = 'PENDING'
ORDER BY 
    LEAST(form_gap, life_stage_gap, ingredients_gap, price_bucket_gap),
    brand_slug;

-- View for audit trail
CREATE OR REPLACE VIEW recent_allowlist_changes AS
SELECT 
    brand_slug,
    action,
    old_status,
    new_status,
    changed_by,
    changed_at,
    reason
FROM brand_allowlist_audit
ORDER BY changed_at DESC
LIMIT 20;

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to add a brand to allowlist
CREATE OR REPLACE FUNCTION add_brand_to_allowlist(
    p_brand_slug VARCHAR,
    p_added_by VARCHAR,
    p_reason TEXT,
    p_form_cov DECIMAL,
    p_life_cov DECIMAL,
    p_ingr_cov DECIMAL,
    p_price_cov DECIMAL,
    p_kcal_outliers INTEGER DEFAULT 0
)
RETURNS BOOLEAN AS $$
DECLARE
    v_quality_gate_passed BOOLEAN;
BEGIN
    -- Check quality gates
    v_quality_gate_passed := (
        p_form_cov >= 95 AND
        p_life_cov >= 95 AND
        p_ingr_cov >= 85 AND
        p_price_cov >= 70 AND
        p_kcal_outliers = 0
    );
    
    INSERT INTO brand_allowlist (
        brand_slug, status, added_by, reason, quality_gate_passed,
        form_coverage, life_stage_coverage, ingredients_coverage,
        price_bucket_coverage, kcal_outliers, last_validated
    ) VALUES (
        p_brand_slug,
        CASE WHEN v_quality_gate_passed THEN 'ACTIVE' ELSE 'PENDING' END,
        p_added_by,
        p_reason,
        v_quality_gate_passed,
        p_form_cov,
        p_life_cov,
        p_ingr_cov,
        p_price_cov,
        p_kcal_outliers,
        CURRENT_TIMESTAMP
    );
    
    RETURN v_quality_gate_passed;
END;
$$ LANGUAGE plpgsql;

-- Function to promote pending brand to active
CREATE OR REPLACE FUNCTION promote_brand_to_active(
    p_brand_slug VARCHAR,
    p_promoted_by VARCHAR,
    p_reason TEXT
)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE brand_allowlist
    SET 
        status = 'ACTIVE',
        added_by = p_promoted_by,
        reason = p_reason,
        quality_gate_passed = true,
        updated_at = CURRENT_TIMESTAMP,
        last_validated = CURRENT_TIMESTAMP
    WHERE brand_slug = p_brand_slug
        AND status = 'PENDING'
        AND form_coverage >= 95
        AND life_stage_coverage >= 95
        AND ingredients_coverage >= 85
        AND price_bucket_coverage >= 70
        AND kcal_outliers = 0;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- UPDATED PRODUCTION VIEW (uses allowlist table)
-- ============================================================================

CREATE OR REPLACE VIEW foods_published_prod_with_allowlist AS
SELECT 
    f.*,
    CASE 
        WHEN a.status = 'ACTIVE' THEN 'production'
        WHEN a.status = 'PENDING' THEN 'pending'
        ELSE 'catalog_only'
    END AS enrichment_status,
    a.status AS allowlist_status,
    a.last_validated AS allowlist_validated_at
FROM foods_published_prod f
LEFT JOIN brand_allowlist a ON f.brand_slug = a.brand_slug;

-- ============================================================================
-- SUMMARY QUERIES
-- ============================================================================

-- Get current allowlist summary
/*
SELECT 
    status,
    COUNT(*) AS brand_count,
    STRING_AGG(brand_slug, ', ' ORDER BY brand_slug) AS brands
FROM brand_allowlist
GROUP BY status
ORDER BY 
    CASE status 
        WHEN 'ACTIVE' THEN 1
        WHEN 'PENDING' THEN 2
        WHEN 'PAUSED' THEN 3
        WHEN 'REMOVED' THEN 4
    END;
*/

-- Get production statistics
/*
SELECT 
    a.brand_slug,
    COUNT(DISTINCT f.product_id) AS sku_count,
    a.form_coverage,
    a.life_stage_coverage,
    a.last_validated,
    DATE_PART('day', CURRENT_TIMESTAMP - a.last_validated) AS days_old
FROM brand_allowlist a
LEFT JOIN foods_published_prod f ON a.brand_slug = f.brand_slug
WHERE a.status = 'ACTIVE'
GROUP BY a.brand_slug, a.form_coverage, a.life_stage_coverage, a.last_validated
ORDER BY sku_count DESC;
*/