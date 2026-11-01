#!/bin/bash

# Mieux Web App Startup Script

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Start the dev server
echo "Starting web app on http://localhost:5173"
npm run dev
