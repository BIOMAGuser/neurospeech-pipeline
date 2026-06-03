#!/bin/bash

# Activate the backend virtual environment
if [ -d "venv" ]; then
    source .venv/bin/activate
    echo "Virtual environment activated."
else
    echo "venv directory not found. Please run setup_backend_venv.sh first."
fi 