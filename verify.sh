#!/bin/bash

# Mieux Verification Script
# Quick check that backend is working

echo "✓ Mieux Backend Verification"
echo "================================"

cd backend

# Check virtual environment
if [ ! -d ".venv" ]; then
    echo "✗ Virtual environment not found"
    echo "Run ./start.sh first to set up the environment"
    exit 1
fi

# Check tests
echo ""
echo "Running tests..."
DATABASE_URL=sqlite:///./foodiq.db .venv/bin/python -m pytest -v

if [ $? -eq 0 ]; then
    echo ""
    echo "================================"
    echo "✓ All verification checks passed!"
    echo ""
    echo "To start the server:"
    echo "  ./start.sh"
else
    echo ""
    echo "✗ Tests failed"
    exit 1
fi
