#!/bin/bash
# Setup script for Spatial Audio Synthesis System

echo "🎵 Setting up Spatial Audio Synthesis System"
echo "============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "README.md" ]; then
    print_error "Please run this script from the Spatial_Audio_Final directory"
    exit 1
fi

print_step "1. Setting up Frontend (React)"
echo "------------------------------"

cd frontend

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed. Please install Node.js 16+ from https://nodejs.org/"
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    print_error "npm is not installed. Please install npm"
    exit 1
fi

print_status "Node.js version: $(node --version)"
print_status "npm version: $(npm --version)"

# Install frontend dependencies
print_status "Installing frontend dependencies..."
npm install

if [ $? -eq 0 ]; then
    print_status "Frontend dependencies installed successfully"
else
    print_error "Failed to install frontend dependencies"
    exit 1
fi

cd ..

print_step "2. Setting up Backend (Python)"
echo "------------------------------"

cd backend

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.8+ from https://python.org/"
    exit 1
fi

print_status "Python version: $(python3 --version)"

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    print_error "pip3 is not installed. Please install pip3"
    exit 1
fi

# Create virtual environment
print_status "Creating Python virtual environment..."
python3 -m venv venv

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies
print_status "Installing Python dependencies..."
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    print_status "Python dependencies installed successfully"
else
    print_error "Failed to install Python dependencies"
    exit 1
fi

cd ..

print_step "3. Creating development scripts"
echo "------------------------------"

# Create start script for frontend
cat > start_frontend.sh << 'EOF'
#!/bin/bash
echo "🚀 Starting React Frontend..."
cd frontend
npm start
EOF
chmod +x start_frontend.sh

# Create start script for backend
cat > start_backend.sh << 'EOF'
#!/bin/bash
echo "🚀 Starting Python Backend..."
cd backend

# Activate virtual environment
source venv/bin/activate

# Create required directories
mkdir -p audio_files
mkdir -p custom_audio

# Start the server
python app.py
EOF
chmod +x start_backend.sh

# Create combined start script
cat > start_dev.sh << 'EOF'
#!/bin/bash
echo "🚀 Starting Spatial Audio Synthesis System in Development Mode"
echo "==============================================================="

# Function to handle cleanup
cleanup() {
    echo "Stopping all services..."
    kill $(jobs -p) 2>/dev/null
    exit 0
}

# Trap Ctrl+C
trap cleanup SIGINT

echo "Initializing backend..."
cd backend

# Activate virtual environment
source venv/bin/activate

# Create required directories
mkdir -p audio_files
mkdir -p custom_audio

# Check backend dependencies
echo "Checking backend dependencies..."
python -c "import fastapi, uvicorn; print('✅ Backend dependencies OK')" || {
    echo "❌ Backend dependencies missing. Installing..."
    pip install -r requirements.txt
}

# Start backend
echo "Starting backend server..."
python app.py &
BACKEND_PID=$!

# Wait for backend to start
echo "Waiting for backend to initialize..."
sleep 5

# Test backend connection
echo "Testing backend connection..."
if curl -s http://localhost:8000/ > /dev/null; then
    echo "✅ Backend is running and responding"
else
    echo "❌ Backend failed to start properly"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

# Start frontend
echo "Starting frontend development server..."
cd ../frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

npm start &
FRONTEND_PID=$!

# Wait for both processes
echo ""
echo "✅ Services started successfully!"
echo "================================================"
echo "🌐 Frontend:     http://localhost:3000"
echo "🔧 Backend API:  http://localhost:8000"
echo "📊 API Docs:     http://localhost:8000/docs"
echo "🧪 Test Page:    file://$(pwd)/test.html"
echo ""
echo "📝 Features Available:"
echo "   • Audio file upload with custom naming"
echo "   • Real-time WebSocket communication"  
echo "   • Python-powered audio synthesis"
echo "   • Distance-based audio effects"
echo "   • Only sine wave test tones included"
echo ""
echo "Press Ctrl+C to stop all services"

wait
EOF
chmod +x start_dev.sh

print_status "Development scripts created"

print_step "4. Verification"
echo "---------------"

# Check if all files exist
files_to_check=(
    "frontend/package.json"
    "frontend/src/ConnectedApp.tsx"
    "frontend/src/services/WebSocketService.ts"
    "frontend/src/services/AudioSourceManager.ts"
    "frontend/src/components/AudioUploadDialog.tsx"
    "backend/requirements.txt"
    "backend/app.py"
    "backend/audio_synthesis.py"
    "start_dev.sh"
)

all_good=true
for file in "${files_to_check[@]}"; do
    if [ -f "$file" ]; then
        print_status "✅ $file exists"
    else
        print_error "❌ $file missing"
        all_good=false
    fi
done

if [ "$all_good" = true ]; then
    print_step "🎉 Setup completed successfully!"
    echo ""
    echo "🚀 QUICK START:"
    echo "==============="
    echo "Run this command to start everything:"
    echo "   ./start_dev.sh"
    echo ""
    echo "📱 WEBAPP ACCESS:"
    echo "• Main App: http://localhost:3000"
    echo "• Test Page: file://$(pwd)/frontend/test.html"
    echo ""
    echo "✨ FEATURES IMPLEMENTED:"
    echo "• ✅ Frontend-Backend WebSocket communication"
    echo "• ✅ Audio file upload with custom naming"
    echo "• ✅ Python-powered audio synthesis"
    echo "• ✅ Only sine wave test tones (220Hz, 440Hz, 880Hz, 1kHz)"
    echo "• ✅ Distance-based audio effects (4 response curves)"
    echo "• ✅ Clean, emoji-free elegant UI"
    echo "• ✅ Real-time sensor data processing"
    echo ""
    echo "🔧 TROUBLESHOOTING:"
    echo "• If frontend fails: Check Node.js version (16+)"
    echo "• If backend fails: Check Python version (3.8+)"
    echo "• Backend API docs: http://localhost:8000/docs"
    echo ""
    echo "📖 See README.md for detailed usage instructions"
else
    print_error "Setup incomplete. Please check the missing files above."
    exit 1
fi
