-- Rollback brand normalization
-- Generated: 2025-09-12T12:44:38.348492

BEGIN;

UPDATE foods_canonical 
SET brand = 'ACANA',
    brand_slug = 'acana'
WHERE product_key = 'acana|acana_adult_dog_recipe_(grain-free)|dry';

UPDATE foods_canonical 
SET brand = 'Arden',
    brand_slug = 'arden'
WHERE product_key = 'arden|grange_adult_grain_free_duck|unknown';

UPDATE foods_canonical 
SET brand = 'Almo Nature',
    brand_slug = 'almo_nature'
WHERE product_key = 'almo_nature|almo_nature_bioorganic_maintenance|wet';

UPDATE foods_canonical 
SET brand = 'Almo Nature',
    brand_slug = 'almo_nature'
WHERE product_key = 'almo_nature|almo_nature_hfc_adult_dog_medium/large_chicken|dry';

UPDATE foods_canonical 
SET brand = 'Almo Nature',
    brand_slug = 'almo_nature'
WHERE product_key = 'almo_nature|almo_nature_hfc_adult_dog_medium/large_pork|dry';

UPDATE foods_canonical 
SET brand = 'Almo Nature',
    brand_slug = 'almo_nature'
WHERE product_key = 'almo_nature|almo_nature_hfc_adult_dog_medium/large_salmon|dry';

UPDATE foods_canonical 
SET brand = 'Almo Nature',
    brand_slug = 'almo_nature'
WHERE product_key = 'almo_nature|almo_nature_hfc|wet';

UPDATE foods_canonical 
SET brand = 'Almo Nature',
    brand_slug = 'almo_nature'
WHERE product_key = 'almo_nature|almo_nature_holistic_large_adult_dog_-_chicken_&_rice|dry';

UPDATE foods_canonical 
SET brand = 'Almo Nature',
    brand_slug = 'almo_nature'
WHERE product_key = 'almo_nature|almo_nature_holistic_large_adult_dog_-_lamb_&_rice|dry';

UPDATE foods_canonical 
SET brand = 'Almo Nature',
    brand_slug = 'almo_nature'
WHERE product_key = 'almo_nature|almo_nature_holistic_large_adult_salmon_&_rice_kibble_for_dogs|dry';

UPDATE foods_canonical 
SET brand = 'Almo Nature',
    brand_slug = 'almo_nature'
WHERE product_key = 'almo_nature|almo_nature_holistic_medium_adult_dog_-_lamb_&_rice|dry';

UPDATE foods_canonical 
SET brand = 'Almo Nature',
    brand_slug = 'almo_nature'
WHERE product_key = 'almo_nature|almo_nature_holistic_medium_adult_dog_-_salmon_&_rice|dry';

UPDATE foods_canonical 
SET brand = 'Almo Nature',
    brand_slug = 'almo_nature'
WHERE product_key = 'almo_nature|almo_nature_holistic_small_adult_dog_-_salmon_&_rice|dry';

UPDATE foods_canonical 
SET brand = 'Almo Nature',
    brand_slug = 'almo_nature'
WHERE product_key = 'almo_nature|almo_nature_saver_pack|wet';

UPDATE foods_canonical 
SET brand = 'Alpha Spirit',
    brand_slug = 'alpha_spirit'
WHERE product_key = 'alpha_spirit|alpha_spirit_7_days_formula_(semi-moist)|dry';

UPDATE foods_canonical 
SET brand = 'AniForte',
    brand_slug = 'aniforte'
WHERE product_key = 'aniforte|pure_nature_country_beef|unknown';

UPDATE foods_canonical 
SET brand = 'AniForte',
    brand_slug = 'aniforte'
WHERE product_key = 'aniforte|semi_moist_cold_pressed_salmon|unknown';

UPDATE foods_canonical 
SET brand = 'animonda',
    brand_slug = 'animonda'
WHERE product_key = 'animonda|animonda_grancarno_original_junior|wet';

UPDATE foods_canonical 
SET brand = 'AniForte',
    brand_slug = 'aniforte'
WHERE product_key = 'aniforte|pure_nature_farms_lamb|unknown';

UPDATE foods_canonical 
SET brand = 'AniForte',
    brand_slug = 'aniforte'
WHERE product_key = 'aniforte|pure_nature_greenfield_turkey|unknown';

UPDATE foods_canonical 
SET brand = 'AniForte',
    brand_slug = 'aniforte'
WHERE product_key = 'aniforte|pure_nature_senior_menu|unknown';

UPDATE foods_canonical 
SET brand = 'AniForte',
    brand_slug = 'aniforte'
WHERE product_key = 'aniforte|pure_nature_wild_buffalo|unknown';

UPDATE foods_canonical 
SET brand = 'animonda',
    brand_slug = 'animonda'
WHERE product_key = 'animonda|animonda_grancarno_original_adult|wet';

UPDATE foods_canonical 
SET brand = 'animonda',
    brand_slug = 'animonda'
WHERE product_key = 'animonda|animonda_grancarno_original_senior|wet';

UPDATE foods_canonical 
SET brand = 'animonda',
    brand_slug = 'animonda'
WHERE product_key = 'animonda|animonda_vom_feinsten_adult_grain-free|wet';

UPDATE foods_canonical 
SET brand = 'Arden Grange',
    brand_slug = 'arden_grange'
WHERE product_key = 'arden_grange|arden_grange_adult_chicken_&_rice|dry';

UPDATE foods_canonical 
SET brand = 'Arden Grange',
    brand_slug = 'arden_grange'
WHERE product_key = 'arden_grange|arden_grange_adult_lamb_&_rice|dry';

UPDATE foods_canonical 
SET brand = 'Arden Grange',
    brand_slug = 'arden_grange'
WHERE product_key = 'arden_grange|arden_grange_adult_light_chicken_&_rice|dry';

UPDATE foods_canonical 
SET brand = 'Arden Grange',
    brand_slug = 'arden_grange'
WHERE product_key = 'arden_grange|arden_grange_adult_mini_lamb_&_rice|dry';

UPDATE foods_canonical 
SET brand = 'Arden Grange',
    brand_slug = 'arden_grange'
WHERE product_key = 'arden_grange|arden_grange_adult_premium_chicken_&_rice|dry';

UPDATE foods_canonical 
SET brand = 'Arden Grange',
    brand_slug = 'arden_grange'
WHERE product_key = 'arden_grange|arden_grange_adult_prestige_chicken|dry';

UPDATE foods_canonical 
SET brand = 'Arden Grange',
    brand_slug = 'arden_grange'
WHERE product_key = 'arden_grange|arden_grange_adult_salmon_&_rice|dry';

UPDATE foods_canonical 
SET brand = 'Arden Grange',
    brand_slug = 'arden_grange'
WHERE product_key = 'arden_grange|arden_grange_large_breed|dry';

UPDATE foods_canonical 
SET brand = 'Arden Grange',
    brand_slug = 'arden_grange'
WHERE product_key = 'arden_grange|arden_grange_partners_chicken,_rice_&_veg|wet';

UPDATE foods_canonical 
SET brand = 'Arden Grange',
    brand_slug = 'arden_grange'
WHERE product_key = 'arden_grange|arden_grange_partners_lamb,_rice_&_veg|wet';

UPDATE foods_canonical 
SET brand = 'Arden Grange',
    brand_slug = 'arden_grange'
WHERE product_key = 'arden_grange|arden_grange_puppy_junior_chicken_&_rice|dry';

UPDATE foods_canonical 
SET brand = 'Arden Grange',
    brand_slug = 'arden_grange'
WHERE product_key = 'arden_grange|arden_grange_puppy_junior_large_breed_chicken_&_rice|dry';

UPDATE foods_canonical 
SET brand = 'Arden Grange',
    brand_slug = 'arden_grange'
WHERE product_key = 'arden_grange|arden_grange_senior_chicken_&_rice|dry';

UPDATE foods_canonical 
SET brand = 'Arden Grange',
    brand_slug = 'arden_grange'
WHERE product_key = 'arden_grange|arden_grange_sensitive_adult|dry';

UPDATE foods_canonical 
SET brand = 'Arden',
    brand_slug = 'arden'
WHERE product_key = 'arden|grange_adult_chicken__rice|dry';

UPDATE foods_canonical 
SET brand = 'Arden',
    brand_slug = 'arden'
WHERE product_key = 'arden|grange_adult_lamb__rice|dry';

UPDATE foods_canonical 
SET brand = 'Arden',
    brand_slug = 'arden'
WHERE product_key = 'arden|grange_adult_light_chicken__rice|dry';

UPDATE foods_canonical 
SET brand = 'Arden',
    brand_slug = 'arden'
WHERE product_key = 'arden|grange_adult_mini_lamb__rice|dry';

UPDATE foods_canonical 
SET brand = 'Arden',
    brand_slug = 'arden'
WHERE product_key = 'arden|grange_adult_premium_chicken__rice|dry';

UPDATE foods_canonical 
SET brand = 'Arden',
    brand_slug = 'arden'
WHERE product_key = 'arden|grange_adult_prestige_chicken|dry';

UPDATE foods_canonical 
SET brand = 'Arden',
    brand_slug = 'arden'
WHERE product_key = 'arden|grange_adult_salmon__rice|dry';

UPDATE foods_canonical 
SET brand = 'Arden',
    brand_slug = 'arden'
WHERE product_key = 'arden|grange_adult_grain_free_lamb|unknown';

UPDATE foods_canonical 
SET brand = 'Arden',
    brand_slug = 'arden'
WHERE product_key = 'arden|grange_adult_grain_free_salmon|unknown';

UPDATE foods_canonical 
SET brand = 'Arden',
    brand_slug = 'arden'
WHERE product_key = 'arden|grange_adult_grain_free_turkey|unknown';

UPDATE foods_canonical 
SET brand = 'Arden',
    brand_slug = 'arden'
WHERE product_key = 'arden|grange_adult_large_breed_sensitive|unknown';

UPDATE foods_canonical 
SET brand = 'Arden',
    brand_slug = 'arden'
WHERE product_key = 'arden|grange_adult_pork__rice|unknown';

UPDATE foods_canonical 
SET brand = 'Arden',
    brand_slug = 'arden'
WHERE product_key = 'arden|grange_grain_free_adult_duck__superfoods|unknown';

UPDATE foods_canonical 
SET brand = 'Arden',
    brand_slug = 'arden'
WHERE product_key = 'arden|grange_grain_free_adult_lamb__superfoods|unknown';

UPDATE foods_canonical 
SET brand = 'Arden',
    brand_slug = 'arden'
WHERE product_key = 'arden|grange_grain_free_adult_turkey__superfoods|unknown';

UPDATE foods_canonical 
SET brand = 'Arden',
    brand_slug = 'arden'
WHERE product_key = 'arden|grange_grain_free_light/senior|unknown';

UPDATE foods_canonical 
SET brand = 'Arden',
    brand_slug = 'arden'
WHERE product_key = 'arden|grange_grain_free_puppy|unknown';

UPDATE foods_canonical 
SET brand = 'Arden',
    brand_slug = 'arden'
WHERE product_key = 'arden|grange_puppy_junior_chicken__rice|dry';

UPDATE foods_canonical 
SET brand = 'Arden',
    brand_slug = 'arden'
WHERE product_key = 'arden|grange_puppy_junior_large_breed_chicken__rice|dry';

UPDATE foods_canonical 
SET brand = 'Arden',
    brand_slug = 'arden'
WHERE product_key = 'arden|grange_senior_chicken__rice|dry';

UPDATE foods_canonical 
SET brand = 'Arden',
    brand_slug = 'arden'
WHERE product_key = 'arden|grange_sensitive_adult|dry';

UPDATE foods_canonical 
SET brand = 'Arden',
    brand_slug = 'arden'
WHERE product_key = 'arden|grange_partners_chicken,_rice__veg|wet';

UPDATE foods_canonical 
SET brand = 'Arden',
    brand_slug = 'arden'
WHERE product_key = 'arden|grange_partners_lamb,_rice__veg|wet';

UPDATE foods_canonical 
SET brand = 'Arden',
    brand_slug = 'arden'
WHERE product_key = 'arden|grange_mini_adult_chicken__rice|unknown';

UPDATE foods_canonical 
SET brand = 'Arden',
    brand_slug = 'arden'
WHERE product_key = 'arden|grange_partners_sensitive_adult|unknown';

UPDATE foods_canonical 
SET brand = 'Arden',
    brand_slug = 'arden'
WHERE product_key = 'arden|grange_performance_adult|unknown';

UPDATE foods_canonical 
SET brand = 'Arden',
    brand_slug = 'arden'
WHERE product_key = 'arden|grange_sensitive_light/senior|unknown';

UPDATE foods_canonical 
SET brand = 'Arden',
    brand_slug = 'arden'
WHERE product_key = 'arden|grange_sensitive_mini_adult|unknown';

UPDATE foods_canonical 
SET brand = 'Arden',
    brand_slug = 'arden'
WHERE product_key = 'arden|grange_sensitive_puppy/junior|unknown';

UPDATE foods_canonical 
SET brand = 'Arden',
    brand_slug = 'arden'
WHERE product_key = 'arden|grange_weaning/puppy|unknown';

UPDATE foods_canonical 
SET brand = 'ASDA',
    brand_slug = 'asda'
WHERE product_key = 'asda|asda_hero_beef_&_vegetables|dry';

UPDATE foods_canonical 
SET brand = 'ASDA',
    brand_slug = 'asda'
WHERE product_key = 'asda|asda_hero_chicken_rice_&_vegetables|dry';

UPDATE foods_canonical 
SET brand = 'ASDA',
    brand_slug = 'asda'
WHERE product_key = 'asda|asda_hero_meaty_&_poultry_chunks_in_jelly|wet';

UPDATE foods_canonical 
SET brand = 'ASDA',
    brand_slug = 'asda'
WHERE product_key = 'asda|asda_hero_puppy_with_chicken|dry';

UPDATE foods_canonical 
SET brand = 'ASDA',
    brand_slug = 'asda'
WHERE product_key = 'asda|asda_hero_senior_chicken_rice_&_veg|dry';

UPDATE foods_canonical 
SET brand = 'ASDA',
    brand_slug = 'asda'
WHERE product_key = 'asda|hero_chicken__veg_working|unknown';

UPDATE foods_canonical 
SET brand = 'ASDA',
    brand_slug = 'asda'
WHERE product_key = 'asda|hero_light_with_chicken_rice__veg|unknown';

UPDATE foods_canonical 
SET brand = 'ASDA',
    brand_slug = 'asda'
WHERE product_key = 'asda|hero_puppy_with_chicken|dry';

UPDATE foods_canonical 
SET brand = 'ASDA',
    brand_slug = 'asda'
WHERE product_key = 'asda|hero_senior_chicken_rice__veg|dry';

UPDATE foods_canonical 
SET brand = 'ASDA',
    brand_slug = 'asda'
WHERE product_key = 'asda|hero_chicken_rice__vegetables|dry';

UPDATE foods_canonical 
SET brand = 'ASDA',
    brand_slug = 'asda'
WHERE product_key = 'asda|hero_meaty__poultry_chunks_in_jelly|wet';

UPDATE foods_canonical 
SET brand = 'Barking',
    brand_slug = 'barking'
WHERE product_key = 'barking|heads_all_hounder_bowl_lickin_goodness_lamb|unknown';

UPDATE foods_canonical 
SET brand = 'Barking',
    brand_slug = 'barking'
WHERE product_key = 'barking|heads_all_hounder_fat_dog_slim|unknown';

UPDATE foods_canonical 
SET brand = 'Barking',
    brand_slug = 'barking'
WHERE product_key = 'barking|heads_all_hounder_puppy_days_turkey|unknown';

UPDATE foods_canonical 
SET brand = 'Barking',
    brand_slug = 'barking'
WHERE product_key = 'barking|heads_all_hounder_golden_years|unknown';

UPDATE foods_canonical 
SET brand = 'Barking',
    brand_slug = 'barking'
WHERE product_key = 'barking|heads_all_hounder_hair_necessities|unknown';

UPDATE foods_canonical 
SET brand = 'Barking',
    brand_slug = 'barking'
WHERE product_key = 'barking|heads_all_hounder_tummy_lovin_care_fish|unknown';

UPDATE foods_canonical 
SET brand = 'Barking',
    brand_slug = 'barking'
WHERE product_key = 'barking|heads_big_foot_golden_years|unknown';

UPDATE foods_canonical 
SET brand = 'Barking',
    brand_slug = 'barking'
WHERE product_key = 'barking|heads_big_foot_puppy_days|dry';

UPDATE foods_canonical 
SET brand = 'Barking',
    brand_slug = 'barking'
WHERE product_key = 'barking|heads_beef_waggington_wet|wet';

UPDATE foods_canonical 
SET brand = 'Barking',
    brand_slug = 'barking'
WHERE product_key = 'barking|heads_big_foot_bowl_lickin_chicken|dry';

UPDATE foods_canonical 
SET brand = 'Barking',
    brand_slug = 'barking'
WHERE product_key = 'barking|heads_big_foot_chop_lickin_lamb|dry';

UPDATE foods_canonical 
SET brand = 'Barking',
    brand_slug = 'barking'
WHERE product_key = 'barking|heads_bowl_lickin_chicken_wet|wet';

UPDATE foods_canonical 
SET brand = 'Barking',
    brand_slug = 'barking'
WHERE product_key = 'barking|heads_bowl_lickin_chicken|dry';

UPDATE foods_canonical 
SET brand = 'Barking',
    brand_slug = 'barking'
WHERE product_key = 'barking|heads_chop_lickin_lamb_wet|wet';

UPDATE foods_canonical 
SET brand = 'Barking',
    brand_slug = 'barking'
WHERE product_key = 'barking|heads_chop_lickin_lamb|dry';

UPDATE foods_canonical 
SET brand = 'Barking',
    brand_slug = 'barking'
WHERE product_key = 'barking|heads_doggylicious_duck|dry';

UPDATE foods_canonical 
SET brand = 'Barking',
    brand_slug = 'barking'
WHERE product_key = 'barking|heads_little_paws_golden_years|unknown';

UPDATE foods_canonical 
SET brand = 'Barking',
    brand_slug = 'barking'
WHERE product_key = 'barking|heads_puppy_days_wet|wet';

UPDATE foods_canonical 
SET brand = 'Barking',
    brand_slug = 'barking'
WHERE product_key = 'barking|heads_puppy_days|dry';

UPDATE foods_canonical 
SET brand = 'Barking',
    brand_slug = 'barking'
WHERE product_key = 'barking|heads_fat_dog_slim|dry';

UPDATE foods_canonical 
SET brand = 'Barking',
    brand_slug = 'barking'
WHERE product_key = 'barking|heads_fish_n_delish|dry';

UPDATE foods_canonical 
SET brand = 'Barking',
    brand_slug = 'barking'
WHERE product_key = 'barking|heads_golden_years_wet|wet';

UPDATE foods_canonical 
SET brand = 'Barking',
    brand_slug = 'barking'
WHERE product_key = 'barking|heads_little_paws_bowl_lickin_chicken|dry';

UPDATE foods_canonical 
SET brand = 'Barking',
    brand_slug = 'barking'
WHERE product_key = 'barking|heads_little_paws_chop_lickin_lamb|dry';

UPDATE foods_canonical 
SET brand = 'Barking',
    brand_slug = 'barking'
WHERE product_key = 'barking|heads_little_paws_fuss_pot_duck|dry';

UPDATE foods_canonical 
SET brand = 'Barking',
    brand_slug = 'barking'
WHERE product_key = 'barking|heads_plant_powered_pooches|dry';

UPDATE foods_canonical 
SET brand = 'Barking',
    brand_slug = 'barking'
WHERE product_key = 'barking|heads_pooched_salmon|dry';

UPDATE foods_canonical 
SET brand = 'Barking',
    brand_slug = 'barking'
WHERE product_key = 'barking|heads_top_dog_turkey_wet|wet';

UPDATE foods_canonical 
SET brand = 'Barking',
    brand_slug = 'barking'
WHERE product_key = 'barking|heads_top_dog_turkey|dry';

UPDATE foods_canonical 
SET brand = 'bosch',
    brand_slug = 'bosch'
WHERE product_key = 'bosch|bosch_adult_dry_dog_food_mixed_trial_pack|dry';

UPDATE foods_canonical 
SET brand = 'bosch',
    brand_slug = 'bosch'
WHERE product_key = 'bosch|bosch_adult_fish_&_potato_dry_dog_food|dry';

UPDATE foods_canonical 
SET brand = 'bosch',
    brand_slug = 'bosch'
WHERE product_key = 'bosch|bosch_adult_lamb_&_rice|dry';

UPDATE foods_canonical 
SET brand = 'bosch',
    brand_slug = 'bosch'
WHERE product_key = 'bosch|bosch_adult_life_&_care_dry_dog_food|dry';

UPDATE foods_canonical 
SET brand = 'bosch',
    brand_slug = 'bosch'
WHERE product_key = 'bosch|bosch_junior_medium_dry_dog_food|dry';

UPDATE foods_canonical 
SET brand = 'bosch',
    brand_slug = 'bosch'
WHERE product_key = 'bosch|bosch_adult_menu_dry_dog_food|dry';

UPDATE foods_canonical 
SET brand = 'bosch',
    brand_slug = 'bosch'
WHERE product_key = 'bosch|bosch_adult_mini_poultry_&_millet_dry_dog_food|dry';

UPDATE foods_canonical 
SET brand = 'bosch',
    brand_slug = 'bosch'
WHERE product_key = 'bosch|bosch_adult_mini_senior_dry_dog_food|dry';

UPDATE foods_canonical 
SET brand = 'bosch',
    brand_slug = 'bosch'
WHERE product_key = 'bosch|bosch_adult_salmon_&_potato|dry';

UPDATE foods_canonical 
SET brand = 'bosch',
    brand_slug = 'bosch'
WHERE product_key = 'bosch|bosch_hpc_adult_vegan_potato_&_pea|dry';

UPDATE foods_canonical 
SET brand = 'bosch',
    brand_slug = 'bosch'
WHERE product_key = 'bosch|bosch_hpc_oven_baked_beef|dry';

UPDATE foods_canonical 
SET brand = 'bosch',
    brand_slug = 'bosch'
WHERE product_key = 'bosch|bosch_hpc_soft_maxi_water_buffalo_&_sweet_potato|dry';

UPDATE foods_canonical 
SET brand = 'bosch',
    brand_slug = 'bosch'
WHERE product_key = 'bosch|bosch_junior_lamb_&_rice_dry_dog_food|dry';

UPDATE foods_canonical 
SET brand = 'bosch',
    brand_slug = 'bosch'
WHERE product_key = 'bosch|bosch_light_dry_dog_food|dry';

UPDATE foods_canonical 
SET brand = 'bosch',
    brand_slug = 'bosch'
WHERE product_key = 'bosch|bosch_organic_adult_dry_dog_food|dry';

UPDATE foods_canonical 
SET brand = 'bosch',
    brand_slug = 'bosch'
WHERE product_key = 'bosch|bosch_puppy_dry_dog_food|dry';

UPDATE foods_canonical 
SET brand = 'bosch',
    brand_slug = 'bosch'
WHERE product_key = 'bosch|bosch_senior_age_&_weight_dry_dog_food|dry';

UPDATE foods_canonical 
SET brand = 'bosch',
    brand_slug = 'bosch'
WHERE product_key = 'bosch|bosch_sensible_renal_&_reduction_dry_dog_food|dry';

UPDATE foods_canonical 
SET brand = 'bosch',
    brand_slug = 'bosch'
WHERE product_key = 'bosch|bosch_soft_chicken_&_banana_hpc_dry_dog_food|dry';

UPDATE foods_canonical 
SET brand = 'bosch',
    brand_slug = 'bosch'
WHERE product_key = 'bosch|bosch_soft_duck_&_potato_hpc_dry_dog_food|dry';

UPDATE foods_canonical 
SET brand = 'bosch',
    brand_slug = 'bosch'
WHERE product_key = 'bosch|bosch_soft_senior_goat_&_potato_hpc_dog_food|dry';

UPDATE foods_canonical 
SET brand = 'bosch',
    brand_slug = 'bosch'
WHERE product_key = 'bosch|bosch_special_light_dry_dog_food|dry';

UPDATE foods_canonical 
SET brand = 'BULLYBILLOWS',
    brand_slug = 'bullybillows'
WHERE product_key = 'bullybillows|angus_beef_super_food_adult|unknown';

UPDATE foods_canonical 
SET brand = 'BULLYBILLOWS',
    brand_slug = 'bullybillows'
WHERE product_key = 'bullybillows|angus_beef_super_food_puppy|unknown';

UPDATE foods_canonical 
SET brand = 'BULLYBILLOWS',
    brand_slug = 'bullybillows'
WHERE product_key = 'bullybillows|free_range_chicken_super_food_adult|unknown';

UPDATE foods_canonical 
SET brand = 'BULLYBILLOWS',
    brand_slug = 'bullybillows'
WHERE product_key = 'bullybillows|scottish_salmon_super_food_adult|unknown';

UPDATE foods_canonical 
SET brand = 'BULLYBILLOWS',
    brand_slug = 'bullybillows'
WHERE product_key = 'bullybillows|scottish_salmon_super_food_puppy|unknown';

UPDATE foods_canonical 
SET brand = 'BULLYBILLOWS',
    brand_slug = 'bullybillows'
WHERE product_key = 'bullybillows|scottish_salmon_super_food_senior|unknown';

COMMIT;
