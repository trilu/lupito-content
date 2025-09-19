SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'breeds_details' 
ORDER BY ordinal_position;
