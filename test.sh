#!/bin/bash
# Test runner script for Swiss Bandmap

echo "🧪 Running unit tests..."
python -m pytest --tb=short -v

# Check exit code
if [ $? -eq 0 ]; then
    echo "✅ All tests passed!"
else
    echo "❌ Some tests failed"
    exit 1
fi