#!/bin/bash

# Exit immediately if a command fails
set -e

# Remove existing virtual environment if it exists
if [ -d "venv" ]; then
    echo "Removing existing virtual environment..."
    rm -rf venv
fi

# Create a fresh virtual environment
echo "Creating new virtual environment..."
python3 -m venv venv

# Verify the virtual environment was created
if [ ! -f "venv/bin/python" ] && [ ! -f "venv/bin/python3" ]; then
    echo "ERROR: Virtual environment creation failed!"
    exit 1
fi

# Activate the virtual environment
source venv/bin/activate

# Verify we're using the correct Python
VENV_PYTHON=$(which python3)
if [[ "$VENV_PYTHON" != *"venv"* ]]; then
    echo "ERROR: Virtual environment not properly activated!"
    exit 1
fi

# Upgrade pip using the virtual environment's pip directly
venv/bin/python -m pip install --upgrade pip > /dev/null

# Install dependencies
if [ -f "requirements.txt" ]; then
    echo "Installing dependencies from requirements.txt..."
    venv/bin/python -m pip install -r requirements.txt
else
    echo "No requirements.txt found."
fi

echo "Setup complete."