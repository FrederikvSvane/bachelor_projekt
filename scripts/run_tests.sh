# Exit on error
set -e

# Navigate to project root
cd "$(dirname "$0")/.."

# Ensure we're using the right Python
# If you have a virtual environment, uncomment the next line:
# source venv/bin/activate

# Run all tests
python -m unittest discover -s tests -p "test_*.py" -v

echo "All tests completed."