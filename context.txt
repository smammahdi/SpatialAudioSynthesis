# Spatial Audio System (Pygame Application)

A sophisticated, Elegant-grade spatial audio synthesis application built with pygame, featuring elegant UI design and advanced audio processing capabilities.

## Overview

This pygame-based application replaces the previous web-based system with a unified Python solution that provides:

- **Elegant Interface**: Clean, elegant UI without emojis or informal elements
- **Real-time Audio Synthesis**: Advanced spatial audio processing based on distance sensors
- **Multi-device Management**: Support for multiple HC-05 Bluetooth sensor devices
- **Live Monitoring**: Real-time distance and volume visualization
- **Advanced Audio Effects**: Spatial Audio System-grade audio processing and effects

## Features

### Core Functionality
- **Device Management**: Connect and manage multiple HC-05 Bluetooth sensors
- **Spatial Audio Synthesis**: Real-time audio generation based on distance data
- **Audio File Support**: Upload and assign custom audio files to devices
- **Distance-Volume Mapping**: Configurable distance-to-volume relationships
- **Demo Mode**: Built-in simulation for testing without hardware

### Elegant Interface
- **Elegant Design**: Modern, Elegant UI with sophisticated color scheme
- **Collapsible Sections**: Organized interface with expandable content areas
- **Real-time Charts**: Live monitoring of distance and volume data
- **Status Indicators**: System health and connection monitoring
- **Responsive Layout**: Optimized for different screen sizes

### Audio Processing
- **High-Quality Synthesis**: 44.1kHz audio with Elegant DSP
- **Multiple Decay Types**: Linear, exponential, and logarithmic volume curves
- **Audio Effects**: Master volume, pitch shifting, reverb, EQ controls
- **Multi-channel Support**: Independent audio streams per device

## Quick Start

### 1. Setup
```bash
cd pygame_app
chmod +x setup.sh run.sh
./setup.sh
```

### 2. Run Application
```bash
./run.sh
```

### 3. Test with Demo Mode
1. Click "Enable Demo Mode" in Device Management
2. Observe simulated device with realistic distance changes
3. Listen to spatial audio synthesis based on distance

## System Requirements

- **Python**: 3.8 or higher
- **Operating System**: macOS, Linux, Windows
- **Audio**: Sound card with speakers or headphones
- **Memory**: 512MB RAM minimum
- **Storage**: 100MB free space

## Installation

### Automatic Setup
```bash
./setup.sh
```

### Manual Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Generate audio files
python3 -c "exec(open('setup.sh').read().split('python3 -c \"')[1].split('\"')[0])"
```

## Usage

### Interface Layout

**Left Panel (Controls):**
- **Device Management**: Demo mode toggle, device scanning
- **Connected Devices**: Device list with audio assignments
- **Audio Effects**: Volume controls, distance mapping settings

**Right Panel (Monitoring):**
- **Device Status**: Real-time device information
- **Distance Monitoring**: Live distance charts
- **Volume Monitoring**: Real-time volume visualization

### Distance-Volume Mapping

Configure how audio volume changes with distance:

1. **Min Distance**: Closest distance (100% volume)
2. **Max Distance**: Farthest distance (minimum volume)
3. **Decay Type**: 
   - **Linear**: Uniform volume decrease
   - **Exponential**: Rapid initial decrease, gradual at distance
   - **Logarithmic**: Gradual initial decrease, rapid at distance

### Hardware Integration

**HC-05 Bluetooth Setup:**
1. Connect HC-05 module to microcontroller
2. Configure baud rate to 9600
3. Send distance data format: `DISTANCE:123.45`
4. Use device scanning to detect and connect

**Demo Mode:**
- Simulates realistic HC-05 device behavior
- 30-second distance cycles (0-175cm)
- Realistic movement patterns with variations

## Technical Architecture

### Core Components

```
main.py                 # Application entry point
├── src/
│   ├── config.py      # Configuration and styling
│   ├── audio_engine.py # Audio synthesis engine  
│   ├── device_manager.py # Bluetooth device management
│   └── ui_manager.py   # Elegant UI system
├── audio_files/        # Generated sine wave files
├── assets/            # UI assets and resources
└── logs/              # Application logs
```

### Audio Engine
- **Synthesis**: Real-time sine wave and file-based audio
- **Processing**: Volume control, frequency modulation
- **Output**: Elegant-quality 44.1kHz stereo audio
- **Latency**: Sub-100ms response times

### Device Management
- **Scanning**: Automatic HC-05 device discovery
- **Connection**: Reliable Bluetooth communication
- **Monitoring**: Real-time distance data processing
- **Error Handling**: Robust connection management

### UI System
- **Rendering**: Hardware-accelerated pygame graphics
- **Layout**: Elegant responsive design
- **Interaction**: Mouse and keyboard input handling
- **Animation**: Smooth transitions and effects

## Configuration

### Color Scheme (Elegant)
- **Background**: Dark blue-gray (#0F0F14)
- **Surface**: Dark surface (#191E28)
- **Primary**: Elegant blue (#4682C8)
- **Text**: Light gray (#F0F5FA)

### Audio Settings
- **Sample Rate**: 44.1kHz
- **Bit Depth**: 16-bit
- **Channels**: Stereo (2)
- **Buffer Size**: 1024 samples

### Performance
- **Target FPS**: 60
- **Update Rate**: 2Hz for distance data
- **Chart History**: 60 seconds

## Development

### Code Structure
- **Object-Oriented**: Clean class hierarchy
- **Type Hints**: Full Python type annotations
- **Documentation**: Comprehensive docstrings
- **Error Handling**: Robust exception management

### Extending the System
1. **Audio Effects**: Add new effects in `audio_engine.py`
2. **UI Components**: Extend `ui_manager.py` rendering
3. **Device Types**: Support new sensors in `device_manager.py`
4. **Configuration**: Modify settings in `config.py`

## Troubleshooting

### Common Issues

**Audio Not Playing:**
```bash
# Check audio system
python3 -c "import pygame; pygame.mixer.init(); print('Audio system OK')"

# Test system audio
osascript -e "beep"  # macOS
```

**Device Connection Failed:**
- Verify HC-05 is powered and paired
- Check serial port permissions
- Enable demo mode for testing

**Performance Issues:**
- Reduce chart update frequency
- Lower audio buffer size
- Close other audio applications

### Logs and Debugging
- Application logs: `logs/app_YYYYMMDD_HHMMSS.log`
- Enable verbose logging: Set `DEBUG=1` environment variable
- Console output: Real-time status and error messages

## Elegant Features

### Enterprise-Grade Design
- No emojis or informal text elements
- Consistent Elegant typography
- Sophisticated color palette
- Clean, minimal interface design

### Advanced Audio Processing
- Elegant DSP algorithms
- Multiple synthesis methods
- Real-time effects processing
- High-quality audio output

### System Reliability
- Robust error handling
- Automatic recovery mechanisms
- Comprehensive logging
- Performance monitoring

## License

This Elegant spatial audio system is developed for educational and research purposes. All components use open-source libraries and follow industry best practices.

## Support

For technical support or feature requests, refer to the application logs and system documentation. The application includes comprehensive error reporting and diagnostic capabilities.
