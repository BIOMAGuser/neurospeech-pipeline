#!/bin/bash

# Exit on error
set -e

# Remove old venv if it exists
if [ -d ".venv" ]; then
    echo "Removing existing venv..."
    rm -rf .venv
fi

# Create new venv with Python 3.11
python3.11 -m venv .venv

echo "Activating venv..."
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

echo "Virtual environment setup complete!" 
echo "Run 'source .venv/bin/activate' to activate the virtual environment"