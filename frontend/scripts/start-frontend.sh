#!/bin/bash

# Frontend Development Server starten
# Usage: ./scripts/start-frontend.sh

set -e

echo "🚀 Starting SpeechScribe Frontend..."
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
FRONTEND_DIR="$(dirname "$SCRIPT_DIR")"

# Change to frontend directory
cd "$FRONTEND_DIR"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Start development server
echo "🌐 Frontend running on http://localhost:3000"
echo "📡 Backend: http://localhost:8001"
echo ""
npm run dev
