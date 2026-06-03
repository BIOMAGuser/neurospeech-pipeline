#!/bin/bash
# Integration test runner — runs from the host against the running containers.
# Usage: cd backend && bash tests/run_tests.sh
# Requires: pip install pytest requests gtts (or run inside venv)

set -e
cd "$(dirname "$0")/.."

echo "=== Generating audio fixtures ==="
python3 tests/generate_audio_fixtures.py

echo ""
echo "=== Running integration tests ==="
python3 -m pytest tests/ -v -s --tb=short 2>&1

echo ""
echo "=== Done ==="
