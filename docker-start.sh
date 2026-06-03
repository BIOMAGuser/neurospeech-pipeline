#!/bin/bash

# SpeechScribe Docker Startup Script
# Both dev and prod run on port 8088 — only one mode at a time.

set -e

MODE="prod"
BUILD_FLAG=""

# Parse arguments
for arg in "$@"; do
  case $arg in
    --dev)       MODE="dev" ;;
    --prod)      MODE="prod" ;;
    --build)     BUILD_FLAG="--build" ;;
    --stop)
      echo "Stopping all SpeechScribe services..."
      docker compose --profile dev down
      echo "All services stopped."
      exit 0
      ;;
    --help|-h)
      echo "SpeechScribe Docker Startup"
      echo ""
      echo "Usage: ./docker-start.sh [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --dev        Start dev environment (HMR, live-reload)"
      echo "  --prod       Start production build (default)"
      echo "  --build      Force rebuild (frontend + Docker images)"
      echo "  --stop       Stop all running services"
      echo "  --help       Show this help message"
      echo ""
      echo "Both modes run on http://localhost:8088"
      echo "Only one mode can run at a time."
      echo ""
      echo "Prod serves static files from ./www (no frontend container)."
      echo "Dev uses Next.js dev server with HMR."
      exit 0
      ;;
    *)
      echo "Unknown option: $arg (use --help for usage)"
      exit 1
      ;;
  esac
done

echo "Starting SpeechScribe ($MODE) on port 8088..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "ERROR: .env not found!"
    echo "  1. cp .env.example .env"
    echo "  2. Add your OPENAI_API_KEY"
    echo "  3. Update JWT_SECRET_KEY for production"
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | grep -v '^\s*$' | xargs)

# Ensure appdata directory exists
mkdir -p ./appdata

if [ "$MODE" = "dev" ]; then
  # Stop prod nginx (same port) — must rm to free port
  docker compose rm -sf nginx-prod 2>/dev/null || true
  docker compose --profile dev up -d $BUILD_FLAG backend frontend nginx

elif [ "$MODE" = "prod" ]; then
  # Stop dev services (same port)
  docker compose --profile dev rm -sf nginx frontend 2>/dev/null || true

  # Build frontend to ./www if needed
  if [ -n "$BUILD_FLAG" ] || [ ! -d "./www" ] || [ ! -f "./www/index.html" ]; then
    echo "Building frontend to ./www ..."
    docker compose --profile dev run --rm \
      -e NEXT_PUBLIC_API_URL=http://localhost:8088/api \
      -e NEXT_PUBLIC_APP_NAME="${APP_NAME:-PARK_SPEECH}" \
      -e NEXT_PUBLIC_APP_VERSION="${APP_VERSION:-3.0.0}" \
      frontend sh -c "cd /app && rm -rf .next out && npx next build"
    rm -rf ./www
    cp -r ./frontend/out ./www
    echo "Frontend built: $(find ./www -name '*.html' | wc -l) pages in ./www/"
  fi

  # Start backend + nginx (nginx serves ./www directly)
  docker compose up -d $BUILD_FLAG backend nginx-prod
fi

echo ""
docker compose ps
echo ""
echo "========================================="
echo " SpeechScribe is running! ($MODE)"
echo " http://localhost:8088"
echo "========================================="
echo ""
echo " Logs:    docker compose logs -f"
echo " Stop:    ./docker-start.sh --stop"
echo " Rebuild: ./docker-start.sh --$MODE --build"
