#!/bin/bash
# Data refresh script for Swiss Bandmap
# Run this periodically (e.g., daily via cron) to update the data

echo "🔄 Refreshing Swiss Bandmap data..."
echo "Started at: $(date)"

# Run the preprocessing script
python preprocess_data.py

# Check if successful
if [ $? -eq 0 ]; then
    echo "✅ Data refresh completed successfully at $(date)"
    echo "📊 Updated files:"
    ls -la data/*.json
else
    echo "❌ Data refresh failed at $(date)"
    exit 1
fi