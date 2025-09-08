#!/bin/bash

# AKC Scraper Job Monitor
# Usage: ./monitor_job.sh [job_id]

SERVICE_URL="https://akc-breed-scraper-izqu6hdfrq-uc.a.run.app"
JOB_ID="${1:-c78b9dcb}"  # Use provided job ID or default to latest

echo "🔍 Monitoring Job: $JOB_ID"
echo "Service: $SERVICE_URL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Monitor loop
COUNTER=0
while true; do
    COUNTER=$((COUNTER + 1))
    
    # Get status
    RESPONSE=$(curl -s "$SERVICE_URL/status/$JOB_ID")
    
    # Parse status (handle potential JSON errors)
    STATUS=$(echo "$RESPONSE" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    
    # Display status
    echo "[$(date '+%H:%M:%S')] Check #$COUNTER - Status: ${STATUS:-checking...}"
    
    # Check if completed
    if [ "$STATUS" = "completed" ]; then
        echo ""
        echo "✅ Job Completed!"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        # Show results count if available
        RESULTS_COUNT=$(echo "$RESPONSE" | grep -o '"results_count":[0-9]*' | cut -d':' -f2)
        SUCCESSFUL=$(echo "$RESPONSE" | grep -o '"successful_extractions":[0-9]*' | cut -d':' -f2)
        
        if [ -n "$RESULTS_COUNT" ]; then
            echo "📊 Results: $RESULTS_COUNT breeds processed"
            echo "✅ Successful: ${SUCCESSFUL:-0} extractions"
        fi
        
        # Check if download available
        HAS_FILE=$(echo "$RESPONSE" | grep -o '"output_file":"[^"]*"')
        if [ -n "$HAS_FILE" ]; then
            echo ""
            echo "📥 Download available!"
            echo "Run: curl -O $SERVICE_URL/download/$JOB_ID"
        fi
        
        break
    elif [ "$STATUS" = "failed" ]; then
        echo ""
        echo "❌ Job Failed!"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "Error details:"
        echo "$RESPONSE" | grep -o '"error":"[^"]*"' | cut -d'"' -f4
        break
    fi
    
    # Wait before next check
    sleep 15
done

echo ""
echo "Full response:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"