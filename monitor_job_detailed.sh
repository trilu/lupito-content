#!/bin/bash

# Enhanced monitoring script with detailed progress tracking
# Usage: ./monitor_job_detailed.sh <job_id>

if [ -z "$1" ]; then
    echo "Usage: $0 <job_id>"
    exit 1
fi

JOB_ID=$1
SERVICE_URL="https://akc-breed-scraper-izqu6hdfrq-uc.a.run.app"
CHECK_INTERVAL=10  # Check every 10 seconds for more granular updates

echo "🔍 Enhanced Monitoring for Job: $JOB_ID"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Function to check Cloud Run logs
check_logs() {
    echo "📋 Recent activity from Cloud Run logs:"
    gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=akc-breed-scraper AND textPayload:\"$JOB_ID\"" \
        --limit=10 \
        --format="value(textPayload)" \
        --freshness=5m 2>/dev/null | grep -E "(Processing|Scraping|Error|SUCCESS|FAILED|breed)" | tail -5
    echo ""
}

# Function to check for errors
check_errors() {
    local errors=$(gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=akc-breed-scraper AND textPayload:\"$JOB_ID\" AND (textPayload:\"ERROR\" OR textPayload:\"error\" OR textPayload:\"failed\")" \
        --limit=5 \
        --format="value(textPayload)" \
        --freshness=5m 2>/dev/null)
    
    if [ ! -z "$errors" ]; then
        echo "⚠️  ERRORS DETECTED:"
        echo "$errors" | head -3
        echo ""
    fi
}

CHECK_COUNT=0
LAST_STATUS=""
START_TIME=$(date +%s)

while true; do
    CHECK_COUNT=$((CHECK_COUNT + 1))
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))
    ELAPSED_MIN=$((ELAPSED / 60))
    ELAPSED_SEC=$((ELAPSED % 60))
    
    # Get job status
    RESPONSE=$(curl -s "$SERVICE_URL/status/$JOB_ID")
    STATUS=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('status', 'unknown'))" 2>/dev/null || echo "checking")
    
    # Clear screen for clean output
    clear
    echo "🔍 Enhanced Monitoring for Job: $JOB_ID"
    echo "⏱️  Elapsed: ${ELAPSED_MIN}m ${ELAPSED_SEC}s | Check #$CHECK_COUNT"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    # Status indicator with emoji
    case "$STATUS" in
        "running")
            echo "🏃 Status: RUNNING"
            ;;
        "completed")
            echo "✅ Status: COMPLETED"
            ;;
        "failed")
            echo "❌ Status: FAILED"
            ;;
        *)
            echo "❓ Status: $STATUS"
            ;;
    esac
    echo ""
    
    # Check for recent logs if running
    if [[ "$STATUS" == "running" ]]; then
        check_logs
        check_errors
        
        # Progress estimation (based on 30-60 sec per breed)
        if [[ "$ELAPSED" -gt 0 ]]; then
            echo "📊 Progress Estimation:"
            echo "   - If processing 5 breeds: ~$(($ELAPSED * 100 / 300))% complete"
            echo "   - Expected time: 2.5-5 minutes total"
            echo ""
        fi
    fi
    
    # If completed or failed, show final details
    if [[ "$STATUS" == "completed" ]] || [[ "$STATUS" == "failed" ]]; then
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "📊 Final Status Report:"
        echo ""
        
        # Parse response for details
        RESULTS_COUNT=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('results_count', 0))" 2>/dev/null || echo "0")
        SUCCESSFUL=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('successful_extractions', 0))" 2>/dev/null || echo "0")
        HAS_FILE=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print('Yes' if data.get('output_file') else 'No')" 2>/dev/null || echo "No")
        ERROR=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('error', '')[:200] if data.get('error') else '')" 2>/dev/null || echo "")
        
        echo "   Results: $RESULTS_COUNT breeds processed"
        echo "   Successful: $SUCCESSFUL extractions"
        echo "   Output file: $HAS_FILE"
        
        if [ ! -z "$ERROR" ]; then
            echo ""
            echo "❌ Error Details:"
            echo "$ERROR"
        fi
        
        if [[ "$STATUS" == "completed" ]] && [[ "$HAS_FILE" == "Yes" ]]; then
            echo ""
            echo "📥 Download results:"
            echo "   curl -O $SERVICE_URL/download/$JOB_ID"
        fi
        
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "Total time: ${ELAPSED_MIN}m ${ELAPSED_SEC}s"
        break
    fi
    
    # Check for timeout (15 minutes)
    if [[ "$ELAPSED" -gt 900 ]]; then
        echo ""
        echo "⏰ TIMEOUT: Job has been running for over 15 minutes"
        echo "This is unusual for a 5-breed test. Check Cloud Run logs:"
        echo "gcloud logging read \"resource.labels.service_name=akc-breed-scraper\" --limit=50"
        break
    fi
    
    sleep $CHECK_INTERVAL
done