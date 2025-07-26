#!/bin/bash

# pygame/setup.sh
# Simplified Setup Script for Spatial Audio System

echo "🚀 Setting up Spatial Audio System..."
echo "====================================="

# Check Python version
python_version=$(python3 --version 2>&1 | grep -o '[0-9]\+\.[0-9]\+' | head -1)
major_version=$(echo "$python_version" | cut -d. -f1)
minor_version=$(echo "$python_version" | cut -d. -f2)

echo "🐍 Python version: $(python3 --version)"

if [ "$major_version" -lt 3 ] || ([ "$major_version" -eq 3 ] && [ "$minor_version" -lt 8 ]); then
    echo "❌ Error: Python 3.8 or higher required. Found: $python_version"
    exit 1
fi

# Clean up existing environment (with better permission handling)
if [ -d "venv" ]; then
    echo "🧹 Removing existing virtual environment..."
    rm -rf venv 2>/dev/null || {
        echo "⚠️  Permission issue removing venv, trying with sudo..."
        sudo rm -rf venv 2>/dev/null || {
            echo "⚠️  Could not remove venv, renaming it..."
            mv venv venv_backup_$(date +%s) 2>/dev/null || true
        }
    }
fi

# Create fresh virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "⚡ Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip --quiet

echo ""
echo "📚 Installing Dependencies..."
echo "============================"

# Install core dependencies
echo "Installing pygame..."
pip install pygame

echo "Installing numpy..."
pip install numpy

echo "Installing audio support..."
pip install sounddevice

echo "Installing serial communication..."
pip install pyserial

# Modern Bluetooth support
echo "Installing Bluetooth support..."
if pip install bleak; then
    echo "✅ Bluetooth (bleak) installed successfully"
else
    echo "⚠️  Bluetooth support failed to install (app will still work)"
fi

# Test core installation
echo ""
echo "🧪 Testing installation..."
python3 -c "
import pygame
import numpy
import serial
print('✅ Core dependencies working')

try:
    import bleak
    print('✅ Bluetooth support available')
except ImportError:
    print('⚠️  Bluetooth support not available')
"

if [ $? -ne 0 ]; then
    echo "❌ Installation test failed"
    exit 1
fi

# Set proper permissions
chmod +x run.sh
chmod +x setup.sh


echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "To start the application:"
echo "  ./run.sh"
echo ""