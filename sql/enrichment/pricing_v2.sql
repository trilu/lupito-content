-- Generated: 2025-09-10 15:32:53
-- Purpose: Pricing V2

-- Pricing Enrichment V2 with Pack Size Parser
-- Generated: 2025-09-10 15:32:53

-- Pack Size Patterns:
-- Multipack: (\d+)\s*[x×]\s*(\d+(?:\.\d+)?)\s*(kg|g|ml|l)
-- Single: (\d+(?:\.\d+)?)\s*(kg|g|ml|l)

-- Price Bucket Thresholds:
-- Low: < €15/kg
-- Mid: €15-30/kg
-- High: > €30/kg

-- Price Source Priority:
-- 1. Original price_per_kg_eur (source)
-- 2. Calculated from price_eur / weight_kg (calculated)
-- 3. Brand RRP median by form (rrp_estimate)
