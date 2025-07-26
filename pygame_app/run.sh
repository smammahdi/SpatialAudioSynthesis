#!/bin/bash

# pygame/run.sh
# Simplified Run Script for Spatial Audio System

echo "🚀 Starting Spatial Audio System..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Running setup..."
    ./setup.sh
    if [ $? -ne 0 ]; then
        echo "❌ Setup failed"
        exit 1
    fi
fi

# Activate virtual environment
source venv/bin/activate

# Quick dependency check
python3 -c "
import pygame, numpy, serial
print('✅ Dependencies verified')
" 2>/dev/null

if [ $? -ne 0 ]; then
    echo "❌ Dependencies missing. Running setup..."
    ./setup.sh
    if [ $? -ne 0 ]; then
        exit 1
    fi
fi

# Set environment variables
export PYGAME_HIDE_SUPPORT_PROMPT=1

echo ""
echo "🎵 Spatial Audio System"
echo "==================================="


echo "Press Ctrl+C to stop"
echo ""
echo "💡 Tip: Run './run.sh test' to test HC-05 connectivity first"
echo ""

# Run the application
python3 main.py

echo ""
echo "✅ Application stopped"