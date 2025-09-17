#!/usr/bin/env python3
"""
Quick status check for rich content extraction
"""

import re
import os
from datetime import datetime

log_file = "rich_content_extraction.log"

if not os.path.exists(log_file):
    print("Extraction log not found!")
    exit(1)

# Read the log file
with open(log_file, 'r') as f:
    content = f.read()

# Find the latest progress
progress_matches = re.findall(r'\[(\d+)/571\] Processing', content)
if progress_matches:
    latest = int(progress_matches[-1])
    percent = (latest * 100) / 571

    print(f"Rich Content Extraction Progress")
    print("=" * 40)
    print(f"Processed: {latest}/571 breeds ({percent:.1f}%)")
    print(f"Remaining: {571 - latest} breeds")

    # Estimate time remaining (assuming ~0.5 sec per breed)
    estimated_minutes = (571 - latest) * 0.5 / 60
    print(f"Estimated time remaining: {estimated_minutes:.1f} minutes")

    # Check for completion
    if "EXTRACTION COMPLETE" in content:
        print("\n✅ EXTRACTION COMPLETE!")
        # Extract final stats
        stats_section = content.split("EXTRACTION COMPLETE")[-1]
        print(stats_section[:500])
else:
    print("No progress found in log file")