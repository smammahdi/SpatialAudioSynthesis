#!/usr/bin/env python3
"""
Spatial Audio Synthesis Backend Server
FastAPI server with WebSocket support for real-time audio synthesis
"""

import asyncio
import json
import logging
import numpy as np
import os
import uuid
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from audio_synthesis import AudioSynthesisEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Spatial Audio Synthesis API",
    description="Real-time audio synthesis from multiple HC-05 sensor nodes",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure audio directories exist
os.makedirs("audio_files", exist_ok=True)
os.makedirs("custom_audio", exist_ok=True)

# Serve static audio files
app.mount("/static-audio", StaticFiles(directory="audio_files"), name="audio")
app.mount("/custom-audio", StaticFiles(directory="custom_audio"), name="custom_audio")

# Data models
class SensorData(BaseModel):
    device_id: str
    device_name: str
    distance: float
    angle: Optional[float] = None
    timestamp: datetime
    connected: bool

class AudioSettings(BaseModel):
    enabled: bool
    global_volume: float = 0.7
    max_distance: float = 200.0
    min_distance: float = 0.0

class AudioTrackInfo(BaseModel):
    sensor_id: str
    sensor_name: str
    audio_type: str
    volume: float
    playing: bool
    distance: float

# Global state
class AppState:
    def __init__(self):
        self.connected_sensors: Dict[str, SensorData] = {}
        self.websocket_connections: List[WebSocket] = []
        self.audio_engine = AudioSynthesisEngine()
        self.audio_settings = AudioSettings(enabled=False)
        self.logs: List[dict] = []

app_state = AppState()

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove stale connections
                self.active_connections.remove(connection)

manager = ConnectionManager()

# Utility functions
def add_log(message: str, level: str = "info", device_id: str = None):
    """Add log entry"""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "message": message,
        "level": level,
        "device_id": device_id
    }
    app_state.logs.append(log_entry)
    
    # Keep only last 1000 logs
    if len(app_state.logs) > 1000:
        app_state.logs = app_state.logs[-1000:]
    
    logger.info(f"[{level.upper()}] {message}")

async def broadcast_sensor_update(sensor_data: SensorData):
    """Broadcast sensor data update to all connected clients"""
    message = {
        "type": "sensor_update",
        "data": {
            "device_id": sensor_data.device_id,
            "device_name": sensor_data.device_name,
            "distance": sensor_data.distance,
            "angle": sensor_data.angle,
            "timestamp": sensor_data.timestamp.isoformat(),
            "connected": sensor_data.connected
        }
    }
    await manager.broadcast(json.dumps(message))

async def broadcast_audio_status():
    """Broadcast audio synthesis status to all connected clients"""
    audio_status = app_state.audio_engine.get_status()
    message = {
        "type": "audio_status",
        "data": audio_status
    }
    await manager.broadcast(json.dumps(message))

async def broadcast_log(log_entry: dict):
    """Broadcast log entry to all connected clients"""
    message = {
        "type": "log",
        "data": log_entry
    }
    await manager.broadcast(json.dumps(message))

# API Routes
@app.get("/")
async def root():
    return {
        "message": "Spatial Audio Synthesis Backend",
        "version": "1.0.0",
        "connected_sensors": len(app_state.connected_sensors),
        "audio_enabled": app_state.audio_settings.enabled
    }

@app.get("/sensors", response_model=List[SensorData])
async def get_sensors():
    """Get all connected sensors"""
    return list(app_state.connected_sensors.values())

@app.get("/sensors/{sensor_id}", response_model=SensorData)
async def get_sensor(sensor_id: str):
    """Get specific sensor data"""
    if sensor_id not in app_state.connected_sensors:
        raise HTTPException(status_code=404, detail="Sensor not found")
    return app_state.connected_sensors[sensor_id]

@app.post("/sensors/{sensor_id}/data")
async def update_sensor_data(sensor_id: str, data: dict):
    """Update sensor data (for testing purposes)"""
    try:
        distance = float(data.get("distance", 0))
        angle = data.get("angle")
        
        sensor_data = SensorData(
            device_id=sensor_id,
            device_name=data.get("device_name", f"Sensor_{sensor_id[-4:]}"),
            distance=distance,
            angle=angle,
            timestamp=datetime.now(),
            connected=True
        )
        
        app_state.connected_sensors[sensor_id] = sensor_data
        
        # Update audio synthesis
        if app_state.audio_settings.enabled:
            app_state.audio_engine.update_sensor_distance(sensor_id, distance)
        
        await broadcast_sensor_update(sensor_data)
        add_log(f"Updated sensor {sensor_id}: {distance}cm", "info", sensor_id)
        
        return {"status": "success", "data": sensor_data.dict()}
        
    except Exception as e:
        add_log(f"Error updating sensor {sensor_id}: {str(e)}", "error", sensor_id)
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/audio/settings", response_model=AudioSettings)
async def get_audio_settings():
    """Get current audio settings"""
    return app_state.audio_settings

@app.post("/audio/settings")
async def update_audio_settings(settings: AudioSettings):
    """Update audio settings"""
    try:
        app_state.audio_settings = settings
        
        # Update audio engine
        app_state.audio_engine.set_enabled(settings.enabled)
        app_state.audio_engine.set_global_volume(settings.global_volume)
        app_state.audio_engine.set_distance_range(settings.min_distance, settings.max_distance)
        
        await broadcast_audio_status()
        add_log(f"Audio settings updated: enabled={settings.enabled}, volume={settings.global_volume}", "info")
        
        return {"status": "success", "settings": settings.dict()}
        
    except Exception as e:
        add_log(f"Error updating audio settings: {str(e)}", "error")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/audio/status")
async def get_audio_status():
    """Get current audio synthesis status"""
    return app_state.audio_engine.get_status()

@app.post("/synthesize-audio")
async def synthesize_audio(request: dict):
    """Test audio synthesis with given parameters"""
    try:
        frequency = request.get("frequency", 440)
        volume = request.get("volume", 50)
        duration = request.get("duration", 1.0)
        
        logger.info(f"Audio synthesis request - freq: {frequency}Hz, vol: {volume}%, dur: {duration}s")
        
        # Generate test tone
        result = app_state.audio_engine.generate_test_tone(
            frequency=frequency,
            volume=volume / 100.0,  # Convert percentage to 0-1
            duration=duration
        )
        
        add_log(f"Audio synthesis test: {frequency}Hz at {volume}% volume", "info")
        
        return {
            "success": True,
            "message": "Audio synthesis test completed",
            "parameters": {
                "frequency": frequency,
                "volume": volume,
                "duration": duration
            },
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Audio synthesis error: {str(e)}")
        add_log(f"Audio synthesis failed: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {str(e)}")

@app.post("/demo/start")
async def start_demo():
    """Start demo mode with simulated device"""
    try:
        demo_device_id = "demo-triangle-wave"
        demo_device = SensorData(
            device_id=demo_device_id,
            device_name="Demo Triangle Wave Device",
            distance=100.0,
            angle=None,
            timestamp=datetime.now(),
            connected=True
        )
        
        app_state.connected_sensors[demo_device_id] = demo_device
        
        # Broadcast demo device connection
        await broadcast_sensor_update(demo_device)
        
        add_log("Demo mode started with triangle wave device", "info")
        
        return {
            "success": True,
            "message": "Demo mode started",
            "device": {
                "device_id": demo_device.device_id,
                "device_name": demo_device.device_name,
                "distance": demo_device.distance,
                "connected": demo_device.connected
            }
        }
        
    except Exception as e:
        logger.error(f"Demo start error: {str(e)}")
        add_log(f"Failed to start demo: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=f"Demo start failed: {str(e)}")

@app.post("/demo/stop")
async def stop_demo():
    """Stop demo mode"""
    try:
        demo_device_id = "demo-triangle-wave"
        
        if demo_device_id in app_state.connected_sensors:
            del app_state.connected_sensors[demo_device_id]
            app_state.audio_engine.remove_track(demo_device_id)
            
            disconnect_message = {
                "type": "sensor_disconnected",
                "data": {"sensor_id": demo_device_id}
            }
            await manager.broadcast(json.dumps(disconnect_message))
            
            add_log("Demo mode stopped", "info")
            
            return {"success": True, "message": "Demo mode stopped"}
        else:
            return {"success": False, "message": "Demo mode was not active"}
            
    except Exception as e:
        logger.error(f"Demo stop error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Demo stop failed: {str(e)}")

@app.post("/demo/update-distance")
async def update_demo_distance(request: dict):
    """Update demo device distance and trigger audio"""
    try:
        distance = float(request.get("distance", 100))
        demo_device_id = "demo-triangle-wave"
        
        if demo_device_id in app_state.connected_sensors:
            # Update device distance
            app_state.connected_sensors[demo_device_id].distance = distance
            app_state.connected_sensors[demo_device_id].timestamp = datetime.now()
            
            # Broadcast update
            await broadcast_sensor_update(app_state.connected_sensors[demo_device_id])
            
            # Trigger audio synthesis if enabled
            if app_state.audio_settings.enabled:
                # Calculate frequency based on distance (200-1000Hz range)
                frequency = 200 + (800 * (200 - min(distance, 200)) / 200)
                volume = max(10, min(100, 100 - (distance / 2)))  # Volume decreases with distance
                
                # Generate audio
                result = app_state.audio_engine.generate_test_tone(
                    frequency=frequency,
                    volume=volume / 100.0,
                    duration=0.3  # Short tone for demo
                )
                
                logger.info(f"Demo audio played: {frequency:.0f}Hz at {volume:.0f}% for distance {distance}cm")
            
            return {
                "success": True,
                "message": f"Demo distance updated to {distance}cm",
                "distance": distance,
                "audio_played": app_state.audio_settings.enabled
            }
        else:
            return {"success": False, "message": "Demo device not found"}
            
    except Exception as e:
        logger.error(f"Demo distance update error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Demo distance update failed: {str(e)}")

@app.get("/audio/tracks", response_model=List[AudioTrackInfo])
async def get_audio_tracks():
    """Get all audio tracks"""
    tracks = []
    for sensor_id, sensor_data in app_state.connected_sensors.items():
        track_info = app_state.audio_engine.get_track_info(sensor_id)
        if track_info:
            tracks.append(AudioTrackInfo(
                sensor_id=sensor_id,
                sensor_name=sensor_data.device_name,
                audio_type=track_info["type"],
                volume=track_info["volume"],
                playing=track_info["playing"],
                distance=sensor_data.distance
            ))
    return tracks

@app.get("/logs")
async def get_logs(limit: int = 100):
    """Get recent logs"""
    return app_state.logs[-limit:]

@app.delete("/logs")
async def clear_logs():
    """Clear all logs"""
    app_state.logs.clear()
    add_log("Logs cleared", "info")
    return {"status": "success", "message": "Logs cleared"}

# Audio upload endpoints
@app.post("/upload-audio")
async def upload_audio(audio_file: UploadFile = File(...), name: str = Form(None)):
    """Upload custom audio file"""
    try:
        logger.info(f"Upload attempt - filename: {audio_file.filename}, content_type: {audio_file.content_type}, name: {name}")
        
        # Use filename if name not provided
        if not name:
            name = os.path.splitext(audio_file.filename or "uploaded_audio")[0]
        
        # Validate file extension
        allowed_extensions = {'.mp3', '.wav', '.ogg', '.mp4', '.m4a', '.aac', '.flac'}
        file_extension = os.path.splitext(audio_file.filename or "")[1].lower()
        
        logger.info(f"File extension detected: {file_extension}")
        
        if not file_extension or file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Generate unique ID and filename
        audio_id = str(uuid.uuid4())
        filename = f"{name.replace(' ', '_')}_{audio_id[:8]}{file_extension}"
        filepath = os.path.join("custom_audio", filename)
        
        logger.info(f"Saving to: {filepath}")
        
        # Save file
        content = await audio_file.read()
        with open(filepath, "wb") as f:
            f.write(content)
        
        add_log(f"Audio uploaded: {name} ({filename})", "info")
        
        return {
            "success": True,
            "id": audio_id,
            "name": name,
            "filename": filename,
            "filepath": filepath
        }
        
    except Exception as e:
        logger.error(f"Audio upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/audio-list")
async def get_audio_list():
    """Get list of available audio files"""
    try:
        audio_files = []
        
        # Default sine waves
        sine_waves = [
            {"id": "sine-220", "name": "Low Sine (220Hz)", "type": "sine", "frequency": 220, "category": "Test Tones"},
            {"id": "sine-440", "name": "A4 Sine (440Hz)", "type": "sine", "frequency": 440, "category": "Test Tones"},
            {"id": "sine-880", "name": "High Sine (880Hz)", "type": "sine", "frequency": 880, "category": "Test Tones"},
            {"id": "sine-1000", "name": "Reference Tone (1kHz)", "type": "sine", "frequency": 1000, "category": "Test Tones"}
        ]
        audio_files.extend(sine_waves)
        
        # Custom uploaded files
        if os.path.exists("custom_audio"):
            for filename in os.listdir("custom_audio"):
                if filename.endswith(('.mp3', '.wav', '.ogg', '.mp4', '.m4a')):
                    file_id = os.path.splitext(filename)[0]
                    audio_files.append({
                        "id": file_id,
                        "name": f"Custom: {filename}",
                        "type": "custom",
                        "filename": filename,
                        "category": "Custom Audio"
                    })
        
        return audio_files
        
    except Exception as e:
        logger.error(f"Error getting audio list: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get audio list")

@app.delete("/audio/{audio_id}")
async def delete_audio(audio_id: str):
    """Delete custom audio file"""
    try:
        # Find and delete custom audio file
        if os.path.exists("custom_audio"):
            for filename in os.listdir("custom_audio"):
                if filename.startswith(audio_id):
                    filepath = os.path.join("custom_audio", filename)
                    os.remove(filepath)
                    add_log(f"Audio deleted: {filename}", "info")
                    return {"success": True, "message": "Audio file deleted"}
        
        raise HTTPException(status_code=404, detail="Audio file not found")
        
    except Exception as e:
        logger.error(f"Error deleting audio: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete audio file")

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    try:
        # Send initial state
        initial_data = {
            "type": "initial_state",
            "data": {
                "sensors": [sensor.dict() for sensor in app_state.connected_sensors.values()],
                "audio_settings": app_state.audio_settings.dict(),
                "audio_status": app_state.audio_engine.get_status(),
                "logs": app_state.logs[-50:]  # Send last 50 logs
            }
        }
        await websocket.send_text(json.dumps(initial_data))
        
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            
            elif message.get("type") == "sensor_data":
                # Handle sensor data from frontend (from Bluetooth)
                sensor_data = message.get("data")
                sensor_id = sensor_data.get("deviceId")
                distance = sensor_data.get("distance")
                
                if sensor_id and distance is not None:
                    # Create or update sensor
                    sensor = SensorData(
                        device_id=sensor_id,
                        device_name=sensor_data.get("deviceName", f"Sensor_{sensor_id[-4:]}"),
                        distance=distance,
                        angle=sensor_data.get("angle"),
                        timestamp=datetime.now(),
                        connected=True
                    )
                    
                    app_state.connected_sensors[sensor_id] = sensor
                    
                    # Update audio synthesis
                    if app_state.audio_settings.enabled:
                        app_state.audio_engine.update_sensor_distance(sensor_id, distance)
                    
                    # Broadcast to other clients
                    await broadcast_sensor_update(sensor)
                    
            elif message.get("type") == "disconnect_sensor":
                sensor_id = message.get("sensor_id")
                if sensor_id in app_state.connected_sensors:
                    del app_state.connected_sensors[sensor_id]
                    app_state.audio_engine.remove_track(sensor_id)
                    
                    disconnect_message = {
                        "type": "sensor_disconnected",
                        "data": {"sensor_id": sensor_id}
                    }
                    await manager.broadcast(json.dumps(disconnect_message))
                    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        manager.disconnect(websocket)

# Background tasks
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    add_log("Spatial Audio Synthesis Backend starting up", "info")
    
    # Initialize audio engine
    try:
        app_state.audio_engine.initialize()
        add_log("Audio synthesis engine initialized", "success")
    except Exception as e:
        add_log(f"Failed to initialize audio engine: {str(e)}", "error")
    
    # Start background tasks
    asyncio.create_task(audio_status_updater())

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    add_log("Spatial Audio Synthesis Backend shutting down", "info")
    app_state.audio_engine.cleanup()

async def audio_status_updater():
    """Background task to periodically broadcast audio status"""
    while True:
        try:
            if app_state.audio_settings.enabled and app_state.connected_sensors:
                await broadcast_audio_status()
            await asyncio.sleep(1)  # Update every second
        except Exception as e:
            logger.error(f"Audio status updater error: {str(e)}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment variable, default to 8000
    backend_port = int(os.getenv("BACKEND_PORT", "8000"))
    
    uvicorn.run(
        "app:app",
        host="127.0.0.1",  # Use localhost instead of 0.0.0.0
        port=backend_port,
        reload=True,
        log_level="info"
    )
