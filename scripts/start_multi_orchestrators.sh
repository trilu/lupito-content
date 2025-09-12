#!/bin/bash
# Start Multiple Orchestrator Instances
# Launches 4 orchestrator instances with non-overlapping offsets

echo "🚀 STARTING MULTI-ORCHESTRATOR SCALING SYSTEM"
echo "=============================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please create it first:"
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Kill any existing orchestrator processes
echo "🧹 Cleaning up existing orchestrator processes..."
pkill -f scraper_orchestrator.py 2>/dev/null
pkill -f orchestrated_scraper.py 2>/dev/null
sleep 3

# Create logs directory
mkdir -p logs/orchestrators

echo "🎛️  Starting 4 orchestrator instances..."
echo "   Instance 1: Offset 0-299   (Countries: US, GB, DE, CA, FR)"
echo "   Instance 2: Offset 300-599 (Countries: IT, ES, NL, AU, NO)" 
echo "   Instance 3: Offset 600-899 (Countries: US, GB, DE, CA, FR)"
echo "   Instance 4: Offset 900-1199 (Countries: IT, ES, NL, AU, NO)"
echo ""

# Start orchestrator instances in background
source venv/bin/activate

# Instance 1 - Primary
echo "Starting Instance 1..."
nohup python scripts/scraper_orchestrator.py --instance 1 --offset-start 0 > logs/orchestrators/instance_1.log 2>&1 &
INSTANCE_1_PID=$!
sleep 5

# Instance 2  
echo "Starting Instance 2..."
nohup python scripts/scraper_orchestrator.py --instance 2 --offset-start 300 > logs/orchestrators/instance_2.log 2>&1 &
INSTANCE_2_PID=$!
sleep 5

# Instance 3
echo "Starting Instance 3..." 
nohup python scripts/scraper_orchestrator.py --instance 3 --offset-start 600 > logs/orchestrators/instance_3.log 2>&1 &
INSTANCE_3_PID=$!
sleep 5

# Instance 4
echo "Starting Instance 4..."
nohup python scripts/scraper_orchestrator.py --instance 4 --offset-start 900 > logs/orchestrators/instance_4.log 2>&1 &
INSTANCE_4_PID=$!
sleep 5

echo "✅ All orchestrator instances started!"
echo ""
echo "📊 PROCESS STATUS:"
echo "   Instance 1: PID $INSTANCE_1_PID (logs/orchestrators/instance_1.log)"
echo "   Instance 2: PID $INSTANCE_2_PID (logs/orchestrators/instance_2.log)"
echo "   Instance 3: PID $INSTANCE_3_PID (logs/orchestrators/instance_3.log)"
echo "   Instance 4: PID $INSTANCE_4_PID (logs/orchestrators/instance_4.log)"
echo ""
echo "🎯 EXPECTED PERFORMANCE:"
echo "   Total scrapers: 20 (4 instances × 5 scrapers each)"
echo "   Estimated rate: 300-500 files/hour"
echo "   Time to 6,000: 12-20 hours"
echo ""
echo "🖥️  MONITORING COMMANDS:"
echo "   Multi-dashboard: python scripts/multi_orchestrator_dashboard.py"
echo "   Continuous monitoring: python scripts/multi_orchestrator_dashboard.py --continuous"
echo "   Process status: ps aux | grep orchestrator"
echo "   Quick status: ./scripts/quick_status.sh"
echo ""
echo "🛑 TO STOP ALL:"
echo "   ./scripts/stop_all_orchestrators.sh"
echo ""
echo "🔄 Orchestrators are now running in the background..."
echo "   Use the monitoring commands above to track progress"