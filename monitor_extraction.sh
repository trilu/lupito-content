#!/bin/bash
# Monitor rich content extraction progress

while true; do
    clear
    echo "===== RICH CONTENT EXTRACTION MONITOR ====="
    echo "Time: $(date '+%H:%M:%S')"
    echo ""

    # Get progress from log
    CURRENT=$(grep -o "\[[0-9]*/571\]" rich_content_extraction.log | tail -1 | cut -d'/' -f1 | tr -d '[')
    if [ ! -z "$CURRENT" ]; then
        PERCENT=$((CURRENT * 100 / 571))
        echo "Progress: $CURRENT/571 breeds ($PERCENT%)"

        # Estimate time remaining
        if [ "$CURRENT" -gt 10 ]; then
            ELAPSED=$(ps -o etime= -p $(pgrep -f "extract_rich_content_from_gcs.py") 2>/dev/null | xargs)
            if [ ! -z "$ELAPSED" ]; then
                echo "Running for: $ELAPSED"
            fi
        fi
    fi

    echo ""
    echo "Last 5 breeds processed:"
    grep "Processing " rich_content_extraction.log | tail -5

    echo ""
    echo "Errors (if any):"
    grep ERROR rich_content_extraction.log | tail -3

    # Check if complete
    if grep -q "RICH CONTENT EXTRACTION COMPLETE" rich_content_extraction.log; then
        echo ""
        echo "===== EXTRACTION COMPLETE ====="
        tail -15 rich_content_extraction.log
        break
    fi

    sleep 10
done