# Spatial Audio System - Centralized Configuration

## Overview
The application now uses centralized configuration management through environment variables instead of hardcoded ports and URLs throughout the codebase.

## Configuration File
All configuration is managed through `config.env`:

```bash
# Backend Configuration
BACKEND_PORT=8000
BACKEND_HOST=localhost

# Frontend Configuration  
FRONTEND_PORT=3000

# API Endpoints (used by React frontend)
REACT_APP_API_BASE_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000
```

## Changes Made

### Backend (`backend/app.py`)
- Updated to use `BACKEND_PORT` environment variable
- Falls back to port 8000 if not specified
- Now supports dynamic port configuration

### Frontend (`frontend/src/`)
- Added environment variable configuration to:
  - `ProfessionalApp.tsx`
  - `ProfessionalApp_Clean.tsx` 
  - `services/WebSocketService.ts`
- Uses `REACT_APP_API_BASE_URL` and `REACT_APP_WS_URL`
- Falls back to localhost:8000 if not specified

### Development Script (`start_dev.sh`)
- Loads configuration from `config.env`
- Displays configuration on startup
- Passes environment variables to both backend and frontend
- Uses dynamic ports for all services

## Benefits

1. **Maintainability**: No more hardcoded URLs scattered throughout the code
2. **Flexibility**: Easy to change ports without editing multiple files
3. **Deployment Ready**: Environment-based configuration supports different environments
4. **Development Friendly**: Clear configuration display on startup
5. **Fallback Support**: Graceful fallbacks if configuration is missing

## Usage

### Development Mode
```bash
./start_dev.sh
```
The script will:
1. Load configuration from `config.env`
2. Display current configuration
3. Start backend on configured port
4. Start frontend on configured port
5. Show all available URLs

### Custom Configuration
Edit `config.env` to change ports:
```bash
BACKEND_PORT=8080
FRONTEND_PORT=3001
REACT_APP_API_BASE_URL=http://localhost:8080
REACT_APP_WS_URL=ws://localhost:8080
```

### Production Deployment
Set environment variables directly:
```bash
export BACKEND_PORT=80
export REACT_APP_API_BASE_URL=https://your-domain.com
export REACT_APP_WS_URL=wss://your-domain.com
```

## Configuration Display
When starting the development environment, you'll see:
```
📋 Configuration:
   Backend:  http://localhost:8000
   Frontend: http://localhost:3000
```

## Technical Notes

- React environment variables must be prefixed with `REACT_APP_`
- Environment variables are loaded at build time for React
- Backend variables are loaded at runtime
- All URLs are now constructed dynamically from configuration
- TypeScript warnings about `process` are expected and harmless in React

## Future Enhancements

1. Add SSL/TLS configuration options
2. Add database connection configuration
3. Add authentication service configuration
4. Add external service API keys configuration
