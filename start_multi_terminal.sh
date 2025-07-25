#!/bin/bash
echo "🚀 Starting Spatial Audio Synthesis System with Separate Terminals"
echo "=================================================================="

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
    export REACT_APP_WS_URL=ws://localhost:8000/ws
fi

echo "📋 Configuration:"
echo "   Backend:  http://${BACKEND_HOST}:${BACKEND_PORT}"
echo "   Frontend: http://localhost:${FRONTEND_PORT}"
echo ""

# Function to get the current working directory
WEBAPP_DIR="$(pwd)"

echo "🔧 Preparing backend..."
cd backend

# Activate virtual environment
source venv/bin/activate

# Create required directories
mkdir -p audio_files
mkdir -p custom_audio

# Check and install audio dependencies
echo "Installing audio dependencies..."
pip install pygame sounddevice 2>/dev/null || echo "⚠️  Some audio libraries may not install - fallback methods available"

# Check backend dependencies
echo "Checking backend dependencies..."
python -c "import fastapi, uvicorn; print('✅ Backend dependencies OK')" || {
    echo "❌ Backend dependencies missing. Installing..."
    pip install -r requirements.txt
}

cd "$WEBAPP_DIR"

# Start backend in new terminal
echo "🖥️  Opening backend terminal..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS - use Terminal.app
    osascript <<EOF
tell application "Terminal"
    activate
    do script "cd '$WEBAPP_DIR/backend' && source venv/bin/activate && echo '🔧 Backend Server Starting...' && echo 'Port: $BACKEND_PORT' && echo 'API Docs: http://$BACKEND_HOST:$BACKEND_PORT/docs' && echo '' && python app.py"
end tell
EOF
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux - try different terminal emulators
    if command -v gnome-terminal &> /dev/null; then
        gnome-terminal -- bash -c "cd '$WEBAPP_DIR/backend' && source venv/bin/activate && echo '🔧 Backend Server Starting...' && echo 'Port: $BACKEND_PORT' && echo 'API Docs: http://$BACKEND_HOST:$BACKEND_PORT/docs' && echo '' && python app.py; exec bash"
    elif command -v xterm &> /dev/null; then
        xterm -e "cd '$WEBAPP_DIR/backend' && source venv/bin/activate && echo '🔧 Backend Server Starting...' && echo 'Port: $BACKEND_PORT' && echo 'API Docs: http://$BACKEND_HOST:$BACKEND_PORT/docs' && echo '' && python app.py; exec bash" &
    else
        echo "❌ No suitable terminal emulator found on Linux"
        exit 1
    fi
else
    # Windows (Git Bash/WSL)
    if command -v cmd.exe &> /dev/null; then
        cmd.exe /c "start cmd /k \"cd /d '$WEBAPP_DIR/backend' && venv\\Scripts\\activate && echo Backend Server Starting... && python app.py\""
    else
        echo "❌ Unsupported operating system"
        exit 1
    fi
fi

# Wait a moment for backend terminal to open
sleep 2

# Start frontend in another new terminal  
echo "🌐 Opening frontend terminal..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS - use Terminal.app
    osascript <<EOF
tell application "Terminal"
    activate
    do script "cd '$WEBAPP_DIR/frontend' && echo '🌐 Frontend Development Server Starting...' && echo 'Port: $FRONTEND_PORT' && echo 'URL: http://localhost:$FRONTEND_PORT' && echo '' && if [ ! -d node_modules ]; then echo 'Installing dependencies...' && npm install --prefer-offline --no-audit --progress=false; fi && BROWSER=none PORT=$FRONTEND_PORT npm start"
end tell
EOF
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    if command -v gnome-terminal &> /dev/null; then
        gnome-terminal -- bash -c "cd '$WEBAPP_DIR/frontend' && echo '🌐 Frontend Development Server Starting...' && echo 'Port: $FRONTEND_PORT' && echo 'URL: http://localhost:$FRONTEND_PORT' && echo '' && if [ ! -d node_modules ]; then echo 'Installing dependencies...' && npm install --prefer-offline --no-audit --progress=false; fi && BROWSER=none PORT=$FRONTEND_PORT npm start; exec bash"
    elif command -v xterm &> /dev/null; then
        xterm -e "cd '$WEBAPP_DIR/frontend' && echo '🌐 Frontend Development Server Starting...' && echo 'Port: $FRONTEND_PORT' && echo 'URL: http://localhost:$FRONTEND_PORT' && echo '' && if [ ! -d node_modules ]; then echo 'Installing dependencies...' && npm install --prefer-offline --no-audit --progress=false; fi && BROWSER=none PORT=$FRONTEND_PORT npm start; exec bash" &
    fi
else
    # Windows
    if command -v cmd.exe &> /dev/null; then
        cmd.exe /c "start cmd /k \"cd /d '$WEBAPP_DIR/frontend' && echo Frontend Development Server Starting... && if not exist node_modules npm install && set PORT=$FRONTEND_PORT && npm start\""
    fi
fi

echo ""
echo "✅ Terminals opened successfully!"
echo "================================================"
echo "🌐 Frontend:     http://localhost:${FRONTEND_PORT}"
echo "🔧 Backend API:  http://${BACKEND_HOST}:${BACKEND_PORT}"
echo "📊 API Docs:     http://${BACKEND_HOST}:${BACKEND_PORT}/docs"
echo ""
echo "📝 Audio Features:"
echo "   • Real audio playback (pygame/sounddevice)"
echo "   • Test tone generation and playback"  
echo "   • Distance-based audio synthesis"
echo "   • Real-time WebSocket communication"
echo ""
echo "📱 Monitor both terminals for:"
echo "   • Backend: API requests, WebSocket connections, audio synthesis"
echo "   • Frontend: React compilation, hot reloading, browser connections"
echo ""
echo "🔊 Audio troubleshooting:"
echo "   • Use 'Test Audio' button in the frontend"
echo "   • Check system volume and audio output device"
echo "   • Backend will try multiple audio libraries (pygame, sounddevice, system beep)"
echo ""
echo "Press any key to exit this launcher..."
read -n 1
