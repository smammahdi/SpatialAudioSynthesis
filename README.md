# Spatial Audio Synthesis System

A professional spatial audio system with React TypeScript frontend and Python FastAPI backend.

## Quick Start

1. **Setup Everything** (one command):
   ```bash
   ./setup.sh
   ```

2. **Start the App**:
   ```bash
   ./start_dev.sh
   ```

3. **Access**:
   - **App**: http://localhost:3000
   - **API**: http://localhost:8000/docs

## What's Inside

```
webapp/
├── frontend/               # React TypeScript app
│   └── src/ProfessionalApp.tsx   # Main application
├── backend/               # Python FastAPI server
│   ├── app.py                # API server
│   ├── audio_synthesis.py    # Audio processing engine
│   ├── audio_files/          # Built-in audio files (220Hz, 440Hz, 880Hz, 1kHz)
│   └── custom_audio/         # Uploaded audio files
├── setup.sh              # Setup script
└── start_dev.sh          # Start script
```

## Features

- **Multi-Device Support**: Connect multiple HC-05 Bluetooth sensor nodes
- **Audio Upload**: Upload custom audio files (MP3, WAV, OGG, MP4, M4A)
- **Audio Assignment**: Assign specific audio files to individual sensors
- **Distance Monitoring**: Real-time distance tracking with visual feedback
- **Spatial Audio**: Distance-based audio processing and volume control
- **Real-time Communication**: WebSocket-based live updates
- **Professional Interface**: Clean, elegant Material-UI design

## Manual Setup (if needed)

**Frontend**:
```bash
cd frontend && npm install && npm start
```

**Backend**:
```bash
cd backend && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt && python app.py
```

## Troubleshooting

- **Frontend won't start**: Check Node.js version (need 16+)
- **Backend won't start**: Check Python version (need 3.8+)
- **No connection**: Make sure both services are running
- **Upload fails**: Check file format (MP3, WAV, OGG, MP4, M4A supported)

## System Status

✅ Backend API: Fully functional  
✅ Frontend Interface: Professional, clean design  
✅ Audio Upload: Working properly  
✅ WebSocket Connection: Real-time updates  
✅ Device Management: HC-05 Bluetooth support  
✅ Audio Assignment: Per-device audio selection  

That's it! Clean and professional.