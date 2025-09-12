#!/bin/bash
# Quick status check

source venv/bin/activate

echo "🔍 QUICK STATUS CHECK - $(date)"
echo "================================="

python3 -c "
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY'))

# Get stats
total = supabase.table('foods_canonical').select('*', count='exact').execute().count
ingredients = supabase.table('foods_canonical').select('*', count='exact').not_.is_('ingredients_raw', 'null').execute().count
complete_nutrition = supabase.table('foods_canonical').select('*', count='exact').not_.is_('protein_percent', 'null').not_.is_('fat_percent', 'null').not_.is_('fiber_percent', 'null').not_.is_('ash_percent', 'null').not_.is_('moisture_percent', 'null').execute().count

ing_pct = ingredients/total*100
nutr_pct = complete_nutrition/total*100
ing_goal = int(total * 0.95)
nutr_goal = int(total * 0.95)
ing_gap = max(0, ing_goal - ingredients)
nutr_gap = max(0, nutr_goal - complete_nutrition)

print(f'📊 DATABASE STATUS')
print(f'Total products: {total:,}')
print(f'')
print(f'🥘 INGREDIENTS')
print(f'   Current: {ingredients:,} ({ing_pct:.1f}%)')
print(f'   Goal (95%): {ing_goal:,}')
print(f'   Gap: {ing_gap:,} products')
print(f'')
print(f'🍖 COMPLETE NUTRITION (all 5 nutrients)')
print(f'   Current: {complete_nutrition:,} ({nutr_pct:.1f}%)')
print(f'   Goal (95%): {nutr_goal:,}')
print(f'   Gap: {nutr_gap:,} products')
print(f'')
print(f'🎯 PRIORITY: Need to scrape ~{max(ing_gap, nutr_gap):,} products')
"

echo ""
echo "🤖 ACTIVE SCRAPERS"
orchestrator_count=$(ps aux | grep -c "scraper_orchestrator.py")
scraper_count=$(ps aux | grep -c "orchestrated_scraper.py")
echo "   Orchestrators: $((orchestrator_count - 1))"
echo "   Scrapers: $((scraper_count - 1))"

echo ""
echo "☁️ SCRAPING PROGRESS"

# Count total scraped files today
today=$(date +%Y%m%d)
total_files=$(gsutil ls "gs://lupito-content-raw-eu/scraped/zooplus/${today}_*/*.json" 2>/dev/null | wc -l | tr -d ' ')
echo "   📄 Total files scraped today: $total_files"

# Count total scraped files all time
total_all_files=$(gsutil ls "gs://lupito-content-raw-eu/scraped/zooplus/*/*.json" 2>/dev/null | wc -l | tr -d ' ')
echo "   📄 Total files scraped all time: $total_all_files"

# Show recent session activity
echo "   📂 Recent sessions:"
gsutil ls gs://lupito-content-raw-eu/scraped/zooplus/ 2>/dev/null | grep "$(date +%Y%m%d)" | tail -5 | while read line; do
    folder=$(basename "$line")
    if [[ $folder =~ ^[0-9]{8}_[0-9]{6}_[a-z0-9]+$ ]]; then
        count=$(gsutil ls "gs://lupito-content-raw-eu/scraped/zooplus/$folder/*.json" 2>/dev/null | wc -l | tr -d ' ')
        session=$(echo $folder | cut -d'_' -f3)
        timestamp=$(echo $folder | cut -d'_' -f2)
        time_formatted="${timestamp:0:2}:${timestamp:2:2}:${timestamp:4:2}"
        echo "      $time_formatted $session: $count files"
    fi
done

# Calculate completion percentage
if [ "$total_all_files" -gt 0 ]; then
    completion_pct=$(echo "scale=1; $total_all_files / 6000 * 100" | bc 2>/dev/null || echo "0")
    if [ $(echo "$completion_pct > 100" | bc 2>/dev/null || echo "0") -eq 1 ]; then
        completion_pct="100.0"
    fi
    echo ""
    echo "🎯 SCRAPING COMPLETION"
    echo "   Progress: $completion_pct% (est. 6,000 products target)"
    
    # Progress bar
    filled=$(echo "scale=0; $completion_pct / 2.5" | bc 2>/dev/null || echo "0")
    empty=$((40 - filled))
    printf "   ["
    for i in $(seq 1 $filled); do printf "█"; done
    for i in $(seq 1 $empty); do printf "░"; done
    printf "] $completion_pct%%\n"
fi