-- Check data completeness
SELECT 
    COUNT(*) as total_breeds,
    COUNT(CASE WHEN ideal_weight_min_kg IS NOT NULL THEN 1 END) as has_weight,
    COUNT(CASE WHEN ideal_weight_min_kg IS NOT NULL THEN 1 END) * 100.0 / COUNT(*) as weight_pct,
    COUNT(CASE WHEN activity_baseline != 'moderate' THEN 1 END) as has_specific_energy,
    COUNT(CASE WHEN activity_baseline != 'moderate' THEN 1 END) * 100.0 / COUNT(*) as energy_pct
FROM breeds_published;

-- Check content table
SELECT 
    COUNT(*) as total_records,
    COUNT(CASE WHEN personality_description IS NOT NULL OR personality_traits IS NOT NULL THEN 1 END) as has_personality,
    COUNT(CASE WHEN history IS NOT NULL OR history_brief IS NOT NULL THEN 1 END) as has_history,
    COUNT(CASE WHEN fun_facts IS NOT NULL THEN 1 END) as has_fun_facts,
    COUNT(CASE WHEN working_roles IS NOT NULL THEN 1 END) as has_working_roles
FROM breeds_comprehensive_content;
