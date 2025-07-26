# HC-05 SensorNode Integration Guide

## 🔵 Overview

This pygame application now supports direct connection to HC-05 Bluetooth modules, specifically your SensorNode devices that send distance data. The implementation uses the same proven patterns from your working HTML application.

## 🚀 Quick Start

1. **Setup the application:**
   ```bash
   ./setup.sh
   ```

2. **Test HC-05 connectivity:**
   ```bash
   python3 test_hc05.py
   ```

3. **Run the main application:**
   ```bash
   ./run.sh
   ```

## 📱 Supported HC-05 Devices

The application automatically detects devices with these names:
- `SensorNode*` (your main devices)
- `SENSORNODEB`
- `SensorNodeB` 
- `BluetoothCarIn`
- `BT_ANURON`
- `HC-*` (HC-05, HC-06, etc.)
- `linvor`

## 🔗 How to Connect

### Method 1: Using the Device Scanner (Recommended)
1. Launch the application with `./run.sh`
2. Click **"Scan for Devices"** in the Device Management panel
3. Click **"Scan HC-05"** to find your SensorNode devices
4. Select your device from the list
5. Click **"Connect"**

### Method 2: Demo Mode for Testing
1. Click **"Enable Demo"** to test with simulated data
2. This creates a virtual HC-05 device for testing audio functionality

## 📊 Data Format Support

Your HC-05 devices can send data in these formats:

### JSON Format (Recommended)
```json
{"distance": 15.3}
{"angle": 60, "distance": 15.3}
```

### Simple Format
```
15.3
23.7
```

### Legacy Formats
```
DISTANCE:15.3
15.3cm
```

## 🛠️ Troubleshooting

### If HC-05 devices don't appear in scan:

1. **Check device status:**
   ```bash
   python3 test_hc05.py
   ```

2. **Verify device is discoverable:**
   - Power cycle your SensorNode
   - Make sure it's in pairing mode
   - Check distance (keep within 10 meters)

3. **System Bluetooth issues:**
   ```bash
   # Linux: Check Bluetooth service
   sudo systemctl status bluetooth
   
   # macOS: Check Bluetooth is enabled in System Preferences
   # Windows: Check Bluetooth settings
   ```

### If connection fails:

1. **Try different scanning methods:**
   - Use "Scan All BT" to see all devices
   - Check if your device appears with a different name

2. **Library issues:**
   ```bash
   # Install alternative Bluetooth library
   pip install pybluez
   
   # Or update to latest bleak
   pip install --upgrade bleak
   ```

### If no data is received:

1. **Check your SensorNode code:**
   - Make sure it's sending data via Serial/UART
   - Verify baud rate is correct (usually 9600)
   - Check data format matches supported formats

2. **Test with serial connection:**
   - Try "Scan Serial" if device is connected via USB
   - Verify data appears in serial monitor

## 🔧 Technical Details

### Bluetooth Libraries Used:
- **bleak** (preferred): Modern BLE support, cross-platform
- **pybluez** (fallback): Legacy Bluetooth support

### Service UUIDs:
- `0000ffe0-0000-1000-8000-00805f9b34fb` (HC-05 default)
- `00001101-0000-1000-8000-00805f9b34fb` (Serial Port Profile)
- `0000ffe1-0000-1000-8000-00805f9b34fb` (HC-05 characteristic)

### Connection Process:
1. BLE device discovery (15 second scan)
2. Service and characteristic discovery
3. Enable notifications for data reception
4. Real-time distance data processing
5. Audio synthesis based on distance

## 📈 Audio Mapping

Distance values are automatically mapped to:
- **Volume**: Closer objects = louder audio
- **Frequency**: Closer objects = higher frequency
- **Audio Source**: Configurable per device

### Default Mapping:
- **5cm**: Maximum volume (100%), High frequency (1000Hz)
- **200cm**: Minimum volume (5%), Low frequency (200Hz)
- **Decay**: Exponential (configurable to linear)

## 🎵 Audio Sources Available:

- **Sine Waves**: A3 (220Hz), C4 (261Hz), A4 (440Hz), C5 (523Hz), A5 (880Hz)
- **Waveforms**: Square, Sawtooth, Triangle, Pulse waves
- **Test Tones**: 1kHz test tone, 200Hz bass

## 💡 Tips for Best Results

1. **Device Placement:**
   - Keep HC-05 devices within 10 meters
   - Avoid interference from WiFi routers
   - Ensure clear line of sight

2. **Data Quality:**
   - Send data at consistent intervals (recommended: 2Hz)
   - Use simple numeric format for best compatibility
   - Include error checking in your SensorNode code

3. **Performance:**
   - Connect maximum 4-6 devices simultaneously
   - Use demo mode for testing without hardware
   - Monitor system resources with many devices

## 🔄 Updating Your SensorNode Code

For best compatibility, send distance data in this format:

```c
// Arduino/ATmega32A example
void sendDistanceData(float distance) {
    // Simple format (recommended)
    Serial.println(distance);
    
    // Or JSON format for additional data
    // Serial.print("{\"distance\":");
    // Serial.print(distance);
    // Serial.println("}");
}
```

## 📞 Support

If you're still having issues:

1. Run the test script: `python3 test_hc05.py`
2. Check the application logs in `logs/` directory
3. Try demo mode to verify audio functionality
4. Ensure your SensorNode firmware is sending data correctly

The implementation mirrors your working HTML application, so if devices work there, they should work here too!