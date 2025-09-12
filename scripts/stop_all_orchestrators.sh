#!/bin/bash
# Stop All Orchestrator Instances
# Safely terminates all running orchestrators and scrapers

echo "🛑 STOPPING ALL ORCHESTRATOR INSTANCES"
echo "======================================="

# Get list of running processes
echo "📋 Finding active processes..."
ORCHESTRATOR_PIDS=$(ps aux | grep scraper_orchestrator.py | grep -v grep | awk '{print $2}')
SCRAPER_PIDS=$(ps aux | grep orchestrated_scraper.py | grep -v grep | awk '{print $2}')

echo "🎛️  Orchestrator processes found: $(echo $ORCHESTRATOR_PIDS | wc -w | tr -d ' ')"
echo "🌍 Scraper processes found: $(echo $SCRAPER_PIDS | wc -w | tr -d ' ')"

if [ -z "$ORCHESTRATOR_PIDS" ] && [ -z "$SCRAPER_PIDS" ]; then
    echo "✅ No orchestrator or scraper processes running"
    exit 0
fi

# Graceful shutdown - SIGTERM first
echo ""
echo "🔄 Sending SIGTERM for graceful shutdown..."

if [ ! -z "$ORCHESTRATOR_PIDS" ]; then
    for pid in $ORCHESTRATOR_PIDS; do
        echo "   Terminating orchestrator PID $pid"
        kill -TERM $pid 2>/dev/null
    done
fi

if [ ! -z "$SCRAPER_PIDS" ]; then
    for pid in $SCRAPER_PIDS; do
        echo "   Terminating scraper PID $pid"  
        kill -TERM $pid 2>/dev/null
    done
fi

# Wait for graceful shutdown
echo "⏳ Waiting 10 seconds for graceful shutdown..."
sleep 10

# Check what's still running
REMAINING_ORCH=$(ps aux | grep scraper_orchestrator.py | grep -v grep | awk '{print $2}')
REMAINING_SCRAPE=$(ps aux | grep orchestrated_scraper.py | grep -v grep | awk '{print $2}')

# Force kill remaining processes
if [ ! -z "$REMAINING_ORCH" ] || [ ! -z "$REMAINING_SCRAPE" ]; then
    echo "💀 Force killing remaining processes..."
    
    if [ ! -z "$REMAINING_ORCH" ]; then
        for pid in $REMAINING_ORCH; do
            echo "   Force killing orchestrator PID $pid"
            kill -KILL $pid 2>/dev/null
        done
    fi
    
    if [ ! -z "$REMAINING_SCRAPE" ]; then
        for pid in $REMAINING_SCRAPE; do
            echo "   Force killing scraper PID $pid"
            kill -KILL $pid 2>/dev/null
        done
    fi
    
    sleep 3
fi

# Final check
FINAL_CHECK=$(ps aux | grep -E "(scraper_orchestrator|orchestrated_scraper)" | grep -v grep)

if [ -z "$FINAL_CHECK" ]; then
    echo "✅ All orchestrator and scraper processes stopped successfully"
    echo ""
    echo "📊 FINAL STATUS:"
    echo "   Active orchestrators: 0"  
    echo "   Active scrapers: 0"
    echo ""
    echo "💡 To restart scaling system:"
    echo "   ./scripts/start_multi_orchestrators.sh"
else
    echo "⚠️  Some processes may still be running:"
    echo "$FINAL_CHECK"
    echo ""
    echo "🔧 Manual cleanup may be required:"
    echo "   ps aux | grep -E '(orchestrator|scraper)'"
    echo "   kill -9 <PID>"
fi