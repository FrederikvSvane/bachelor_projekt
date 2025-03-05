#!/bin/bash

# Exit immediately if a command fails
set -e

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtual environment created."
else
    echo "Virtual environment already exists."
fi

# Activate the virtual environment
source venv/bin/activate
echo "Virtual environment activated."

# Upgrade pip to the latest version
pip install --upgrade pip

# Install dependencies
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "Dependencies installed."
else
    echo "No requirements.txt found. Skipping dependency installation."
fi

echo "Setup complete."
