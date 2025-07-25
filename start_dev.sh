#!/bin/bash
echo "🚀 Starting Spatial Audio Synthesis System in Development Mode"
echo "==============================================================="

# Load configuration
if [ -f "config.env" ]; then
    export $(grep -v '^#' config.env | xargs)
    echo "✅ Configuration loaded from config.env"
else
    echo "⚠️  config.env not found, using defaults"
    export BACKEND_PORT=8000
    export FRONTEND_PORT=3000
    export BACKEND_HOST=localhost
    export REACT_APP_API_BASE_URL=http://localhost:8000
    export REACT_APP_WS_URL=ws://localhost:8000
fi

echo "📋 Configuration:"
echo "   Backend:  http://${BACKEND_HOST}:${BACKEND_PORT}"
echo "   Frontend: http://localhost:${FRONTEND_PORT}"
echo ""

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
echo "Starting backend server on port ${BACKEND_PORT}..."
python app.py &
BACKEND_PID=$!

# Wait for backend to start
echo "Waiting for backend to initialize..."
sleep 5

# Test backend connection
echo "Testing backend connection..."
if curl -s "http://${BACKEND_HOST}:${BACKEND_PORT}/" > /dev/null; then
    echo "✅ Backend is running and responding on port ${BACKEND_PORT}"
else
    echo "❌ Backend failed to start properly on port ${BACKEND_PORT}"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

# Start frontend development server
echo "Starting frontend development server..."
cd ../frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install --prefer-offline --no-audit --progress=false
fi

# Start frontend development server with environment variables
echo "Starting frontend development server on port ${FRONTEND_PORT}..."
BROWSER=none PORT=${FRONTEND_PORT} npm start &
FRONTEND_PID=$!

# Wait for both processes
echo ""
echo "✅ Services started successfully!"
echo "================================================"
echo "🌐 Frontend:     http://localhost:${FRONTEND_PORT}"
echo "🔧 Backend API:  http://${BACKEND_HOST}:${BACKEND_PORT}"
echo "📊 API Docs:     http://${BACKEND_HOST}:${BACKEND_PORT}/docs"
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
