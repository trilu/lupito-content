
-- Create brand_alias table for normalization
CREATE TABLE IF NOT EXISTS brand_alias (
    alias VARCHAR(255) PRIMARY KEY,
    canonical_brand VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_brand_alias_canonical ON brand_alias(canonical_brand);
