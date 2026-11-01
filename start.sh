#!/bin/bash

# Mieux - Start backend server

echo "🚀 Starting Mieux Backend..."
echo "===================="

cd backend

# Kill any existing process on port 8010
if lsof -ti:8010 > /dev/null 2>&1; then
    echo "Stopping existing server on port 8010..."
    lsof -ti:8010 | xargs kill -9 2>/dev/null
    sleep 1
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env 2>/dev/null || true
    DATABASE_URL=sqlite:///./foodiq.db alembic upgrade head
else
    source .venv/bin/activate
fi

# Start the server
echo "Starting server on http://localhost:8010"
DATABASE_URL=sqlite:///./foodiq.db uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload &

echo ""
echo "✓ Backend started!"
echo ""
echo "API:        http://localhost:8010"
echo "API Docs:   http://localhost:8010/docs"
echo "Health:     http://localhost:8010/v1/health"
echo ""
echo "Press Ctrl+C to stop"
echo "===================="

wait
