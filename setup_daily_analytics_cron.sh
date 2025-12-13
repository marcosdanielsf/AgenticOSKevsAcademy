#!/bin/bash
# Setup daily analytics cron job for 8pm CST

echo "🕐 Setting up daily analytics cron job..."

# Get the current directory for absolute paths
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
ANALYTICS_SCRIPT="$SCRIPT_DIR/implementation/instantly_analytics.py"
LOG_FILE="$SCRIPT_DIR/logs/daily_analytics.log"

# Create logs directory if it doesn't exist
mkdir -p "$SCRIPT_DIR/logs"

# Create the cron job entry
# 8 PM CST = 8 PM Central Standard Time
# During CST (Winter): 8 PM CST = 2 AM UTC next day
# During CDT (Summer): 8 PM CDT = 1 AM UTC next day
# Using 02:00 UTC to cover CST (will be 8 PM CST in winter, 9 PM CDT in summer)
CRON_ENTRY="0 2 * * * cd $SCRIPT_DIR && /usr/bin/python3 $ANALYTICS_SCRIPT >> $LOG_FILE 2>&1"

# Add to crontab
echo "Adding cron job for daily analytics at 8 PM CST..."
(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

echo "✅ Cron job added successfully!"
echo "📋 Job details:"
echo "   Time: Daily at 8 PM CST (2 AM UTC)"
echo "   Script: $ANALYTICS_SCRIPT"
echo "   Logs: $LOG_FILE"
echo ""
echo "📝 To view current cron jobs: crontab -l"
echo "🗑️  To remove this job: crontab -e (then delete the line)"
echo ""
echo "⚠️  Note: Your computer must be running at 8 PM for the job to execute!"