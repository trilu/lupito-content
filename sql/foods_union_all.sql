
        CREATE OR REPLACE VIEW foods_union_all AS
        SELECT * FROM food_candidates_compat
        UNION ALL
        SELECT * FROM food_candidates_sc_compat
        UNION ALL
        SELECT * FROM food_brands_compat;
        