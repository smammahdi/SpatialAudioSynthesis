#!/bin/bash
# Standalone HC-05 test script that handles virtual environment activation
echo "🧪 HC-05 Bluetooth Connectivity Test"
echo "====================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Running setup first..."
    ./setup.sh
    if [ $? -ne 0 ]; then
        echo "❌ Setup failed"
        exit 1
    fi
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Check if bleak is installed
echo "🔍 Checking Bluetooth libraries..."
python3 -c "
try:
    import bleak
    print('✅ bleak library available')
except ImportError:
    try:
        import bluetooth
        print('✅ pybluez library available') 
    except ImportError:
        print('❌ No Bluetooth libraries found')
        print('Installing bleak...')
        import subprocess
        subprocess.run(['pip', 'install', 'bleak'])
"

# Run the HC-05 test
echo ""
echo "🚀 Running HC-05 connectivity test..."
echo ""
python3 test_hc05.py

echo ""
echo "📋 Test completed!"
echo ""
echo "If the test passed:"
echo "  ./run.sh    # Start the main application"
echo ""
echo "If the test failed:"
echo "  • Make sure your HC-05 device is powered and discoverable"
echo "  • Check Bluetooth is enabled on your system"
echo "  • Try: ./run.sh  # The app works with demo mode too"
