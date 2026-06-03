#!/bin/bash

# Frontend Production Build
# Usage: ./scripts/build-frontend.sh

set -e

echo "🏗️  Building SpeechScribe Frontend..."

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
FRONTEND_DIR="$(dirname "$SCRIPT_DIR")"

# Change to frontend directory
cd "$FRONTEND_DIR"

# Build
npm run build

echo ""
echo "✅ Build complete!"
echo "📦 Production files ready in: .next/"
echo ""
echo "To start production server:"
echo "  npm start"
