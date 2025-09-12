#!/bin/bash

# Live Scraping Progress Monitor
# Run this in terminal to see real-time progress

# Activate virtual environment
source venv/bin/activate

echo "🔍 LIVE SCRAPING MONITOR"
echo "========================"
echo "Press Ctrl+C to stop monitoring"
echo ""

# Function to get database stats
get_stats() {
    python3 -c "
import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime

load_dotenv()
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY'))

# Get current stats
total = supabase.table('foods_canonical').select('*', count='exact').execute().count
ingredients = supabase.table('foods_canonical').select('*', count='exact').not_.is_('ingredients_raw', 'null').execute().count
complete_nutrition = supabase.table('foods_canonical').select('*', count='exact').not_.is_('protein_percent', 'null').not_.is_('fat_percent', 'null').not_.is_('fiber_percent', 'null').not_.is_('ash_percent', 'null').not_.is_('moisture_percent', 'null').execute().count

ing_pct = ingredients/total*100
nutr_pct = complete_nutrition/total*100
ing_goal = int(total * 0.95)
nutr_goal = int(total * 0.95)
ing_gap = max(0, ing_goal - ingredients)
nutr_gap = max(0, nutr_goal - complete_nutrition)

print(f'{datetime.now().strftime(\"%H:%M:%S\")} | Products: {total:,} | Ingredients: {ingredients:,} ({ing_pct:.1f}%) | Complete Nutrition: {complete_nutrition:,} ({nutr_pct:.1f}%)')
print(f'         | Gap to 95%: Ingredients {ing_gap:,} | Nutrition {nutr_gap:,}')
"
}

# Function to check GCS activity
check_gcs() {
    echo "☁️  Recent GCS Activity:"
    gsutil ls -l gs://lupito-content-raw-eu/scraped/zooplus/ | tail -5 | while read line; do
        if [[ $line == *"scraped/zooplus/"* ]]; then
            folder=$(echo $line | awk '{print $3}' | cut -d'/' -f4)
            count=$(gsutil ls gs://lupito-content-raw-eu/scraped/zooplus/$folder/*.json 2>/dev/null | wc -l)
            echo "   $folder: $count files"
        fi
    done 2>/dev/null || echo "   No recent activity or GCS access issue"
}

# Store initial stats for comparison
echo "Getting baseline stats..."
initial_stats=$(get_stats)
echo "$initial_stats"
echo ""

# Monitor loop
while true; do
    clear
    echo "🔍 LIVE SCRAPING MONITOR - $(date '+%Y-%m-%d %H:%M:%S')"
    echo "========================================================"
    
    # Current stats
    echo "📊 Current Database Status:"
    get_stats
    echo ""
    
    # GCS activity
    check_gcs
    echo ""
    
    # Progress bars
    echo "📈 Progress Visualization:"
    python3 -c "
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY'))

total = supabase.table('foods_canonical').select('*', count='exact').execute().count
ingredients = supabase.table('foods_canonical').select('*', count='exact').not_.is_('ingredients_raw', 'null').execute().count
complete_nutrition = supabase.table('foods_canonical').select('*', count='exact').not_.is_('protein_percent', 'null').not_.is_('fat_percent', 'null').not_.is_('fiber_percent', 'null').not_.is_('ash_percent', 'null').not_.is_('moisture_percent', 'null').execute().count

ing_pct = ingredients/total*100
nutr_pct = complete_nutrition/total*100

# Progress bars (out of 100)
ing_bar = '█' * int(ing_pct/2) + '░' * (50-int(ing_pct/2))
nutr_bar = '█' * int(nutr_pct/2) + '░' * (50-int(nutr_pct/2))

print(f'   Ingredients:     [{ing_bar}] {ing_pct:5.1f}% (Goal: 95%)')
print(f'   Complete Nutr:   [{nutr_bar}] {nutr_pct:5.1f}% (Goal: 95%)')
"
    
    echo ""
    echo "🕐 Refreshing in 30 seconds... (Ctrl+C to stop)"
    
    # Wait 30 seconds or until interrupted
    sleep 30
done