"""
pygame_app/src/device_manager.py
Enhanced Device Manager with HC-05 Bluetooth Support
Uses the same patterns as the working HTML implementation
"""

import threading
import time
import random
import math
import socket
import asyncio
import json
from typing import Dict, List, Optional, Callable, Tuple, Any
from dataclasses import dataclass

from .config import Config
from enum import Enum
import serial
import serial.tools.list_ports
from serial.tools.list_ports_common import ListPortInfo

# Modern Bluetooth support with bleak (recommended)
BLUETOOTH_AVAILABLE = False
BLUETOOTH_LIBRARY = None

try:
    import bleak
    from bleak import BleakScanner, BleakClient
    BLUETOOTH_AVAILABLE = True
    BLUETOOTH_LIBRARY = "bleak"
    print("✅ Using 'bleak' for modern Bluetooth support")
except ImportError:
    # Fallback to pybluez (legacy)
    try:
        import bluetooth
        BLUETOOTH_AVAILABLE = True
        BLUETOOTH_LIBRARY = "pybluez"
        print("⚠️  Using 'pybluez' for legacy Bluetooth support")
        print("   Consider upgrading to 'bleak' for better compatibility")
    except ImportError:
        print("❌ No Bluetooth library available")
        print("   Install with: pip install bleak")
        print("   Alternative: pip install pybluez")
        BLUETOOTH_AVAILABLE = False
        BLUETOOTH_LIBRARY = None
        
        # Define dummy classes for type checking when Bluetooth is not available
        class BleakClient:
            pass
        class BleakScanner:
            pass

class DeviceStatus(Enum):
    DISCONNECTED = "disconnected"
    SCANNING = "scanning"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"

@dataclass
class Device:
    """Represents a connected or discovered device"""
    device_id: str
    device_name: str
    status: DeviceStatus
    last_distance: float = 0.0
    last_update: float = 0.0
    audio_file: Optional[str] = None
    connection_time: float = 0.0
    error_message: Optional[str] = None
    connection_info: Optional[Any] = None
    device_type: str = "unknown"  # "bluetooth", "serial", "demo"
    rssi: Optional[int] = None  # Signal strength
    manufacturer_data: Optional[Dict] = None
    # Moving object specific fields
    last_orientation: Optional[float] = None  # Orientation in degrees
    orientation_updated: bool = False  # Flag to indicate new orientation data

class BluetoothDeviceInfo:
    """Container for Bluetooth device information with bleak compatibility"""
    def __init__(self, address: str, name: str, rssi: int = 0, manufacturer_data: Dict = None):
        self.address = address
        self.name = name if name else f"Device-{address[-5:].replace(':', '')}"
        self.device_name = self.name  # For UI manager compatibility
        self.rssi = rssi
        self.manufacturer_data = manufacturer_data or {}
        self.device = address  # For compatibility
        self.description = f"Bluetooth BLE Device - {self.name}"
        self.is_bluetooth = True

def safe_get_rssi(device) -> int:
    """Safely extract RSSI from BLE device across different bleak versions"""
    try:
        # Direct attribute access (most common)
        if hasattr(device, 'rssi') and device.rssi is not None:
            return device.rssi
        
        # Metadata access (some versions)
        if hasattr(device, 'metadata') and device.metadata:
            if isinstance(device.metadata, dict):
                return device.metadata.get('rssi', 0)
            elif hasattr(device.metadata, 'get'):
                return device.metadata.get('rssi', 0)
        
        # Details access (rare cases)
        if hasattr(device, 'details') and hasattr(device.details, 'rssi'):
            return device.details.rssi
        
        # Advertisement data access (alternative)
        if hasattr(device, 'advertisement_data') and hasattr(device.advertisement_data, 'rssi'):
            return device.advertisement_data.rssi
            
    except Exception as e:
        print(f"RSSI extraction error for device {getattr(device, 'address', 'unknown')}: {e}")
    
    return 0  # Default fallback

class DeviceManager:
    """Enhanced Device Manager with HC-05 Bluetooth Support using proven patterns"""
    
    def __init__(self):
        self.devices: Dict[str, Device] = {}
        self.demo_devices: Dict[str, Device] = {}  # Track multiple demo devices
        self.demo_mode = False
        self.scanning = False
        self.demo_device_counter = 0  # For generating unique demo device IDs
        
        # Demo pattern settings
        self.demo_pattern = 'linear'  # 'linear', 'sinusoidal', 'random'
        self.demo_speed = 1.0         # Pattern speed multiplier
        self.demo_amplitude = 170.0   # Distance range amplitude
        
        # Callbacks
        self.on_device_connected: Optional[Callable[[str, str], None]] = None
        self.on_device_disconnected: Optional[Callable[[str], None]] = None
        self.on_distance_update: Optional[Callable[[str, float], None]] = None
        
        # Threading
        self.running = True
        self.bluetooth_clients: Dict[str, Any] = {}  # Store active BLE clients
        
        # Bluetooth status
        self.bluetooth_available = BLUETOOTH_AVAILABLE
        self.bluetooth_library = BLUETOOTH_LIBRARY
        
        # HC-05 specific configuration (from working HTML)
        self.hc05_device_filters = [
            'SensorNode', 'SENSORNODEB', 'SensorNodeB', 'BluetoothCarIn',
            'BT_ANURON', 'HC-', 'linvor', 'HC05', 'HC-05', 'HC-06', 'HC06'
        ]
        
        # Common HC-05 service UUIDs - these might need to be updated based on your device
        self.hc05_service_uuids = [
            "0000ffe0-0000-1000-8000-00805f9b34fb",  # HC-05 default service
            "00001101-0000-1000-8000-00805f9b34fb",  # Serial Port Profile (SPP)
            "0000ffe1-0000-1000-8000-00805f9b34fb",  # HC-05 characteristic
            "6e400001-b5a3-f393-e0a9-e50e24dcca9e",  # Nordic UART Service
            "49535343-fe7d-4ae5-8fa9-9fafd205e455"   # Alternative UART service
        ]
        
        self.hc05_characteristic_uuids = [
            "0000ffe1-0000-1000-8000-00805f9b34fb",  # HC-05 main characteristic
            "00001101-0000-1000-8000-00805f9b34fb",  # Serial Port Profile characteristic
            "6e400002-b5a3-f393-e0a9-e50e24dcca9e",  # Nordic UART RX
            "6e400003-b5a3-f393-e0a9-e50e24dcca9e",  # Nordic UART TX
            "49535343-1e4d-4bd9-ba61-23c647249616",  # Alternative TX
            "49535343-8841-43f4-a8d4-ecbe34729bb3"   # Alternative RX
        ]
        
        # Event loop for async operations
        self._setup_async_loop()
        
        print(f"✅ Device Manager initialized with HC-05 support")
        print(f"📶 Bluetooth support: {'Available' if BLUETOOTH_AVAILABLE else 'Not available'}")
        if BLUETOOTH_AVAILABLE:
            print(f"📚 Using library: {BLUETOOTH_LIBRARY}")

    def _setup_async_loop(self):
        """Setup asyncio event loop for Bluetooth operations"""
        try:
            # Create a new event loop for this thread
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            # Start the event loop in a separate thread
            self.async_thread = threading.Thread(target=self._run_async_loop, daemon=True)
            self.async_thread.start()
            
            print("✅ Async event loop initialized for Bluetooth operations")
        except Exception as e:
            print(f"⚠️  Async loop setup failed: {e}")
            self.loop = None

    def _run_async_loop(self):
        """Run the asyncio event loop"""
        if self.loop:
            self.loop.run_forever()

    def get_bluetooth_status(self) -> Dict[str, Any]:
        """Get detailed Bluetooth status information"""
        return {
            'available': self.bluetooth_available,
            'library': self.bluetooth_library,
            'can_scan': self.bluetooth_available,
            'modern_support': self.bluetooth_library == "bleak",
            'async_support': self.loop is not None,
            'hc05_filters': self.hc05_device_filters,
            'hc05_services': self.hc05_service_uuids
        }

    async def _scan_bluetooth_devices_async(self) -> List[BluetoothDeviceInfo]:
        """Async Bluetooth device scanning using bleak with HC-05 focus"""
        if not BLUETOOTH_AVAILABLE or BLUETOOTH_LIBRARY != "bleak":
            return []
        
        try:
            print("🔍 Scanning for HC-05 and compatible Bluetooth devices...")
            
            # Scan for devices (15 second timeout for better HC-05 discovery)
            devices = await BleakScanner.discover(timeout=15.0)
            
            bluetooth_devices = []
            
            print(f"📡 Found {len(devices)} total BLE devices")
            
            for device in devices:
                device_name = device.name or f"Unknown-{device.address[-5:].replace(':', '')}"
                
                # Check if device matches HC-05 patterns (from working HTML)
                is_hc05_device = any(
                    filter_name.lower() in device_name.lower() 
                    for filter_name in self.hc05_device_filters
                )
                
                # Also include devices with strong signal (likely nearby sensors)
                device_rssi = safe_get_rssi(device)
                is_nearby = device_rssi and device_rssi > -75
                
                # More permissive filtering for HC-05 devices
                is_potential_sensor = any(keyword in device_name.lower() for keyword in [
                    'sensor', 'node', 'arduino', 'esp', 'bluetooth', 'car', 'audio', 'distance'
                ])
                
                if is_hc05_device or (is_nearby and is_potential_sensor):
                    bt_device = BluetoothDeviceInfo(
                        address=device.address,
                        name=device_name,
                        rssi=device_rssi,
                        manufacturer_data=device.metadata.get('manufacturer_data', {})
                    )
                    bluetooth_devices.append(bt_device)
                    
                    print(f"📱 Found HC-05 compatible device: {device_name} ({device.address}) RSSI: {device_rssi}dBm")
                elif device_rssi and device_rssi > -60:  # Very strong signal
                    # Include very nearby devices regardless of name
                    bt_device = BluetoothDeviceInfo(
                        address=device.address,
                        name=device_name,
                        rssi=device_rssi,
                        manufacturer_data=device.metadata.get('manufacturer_data', {})
                    )
                    bluetooth_devices.append(bt_device)
                    print(f"📱 Found nearby device: {device_name} ({device.address}) RSSI: {device_rssi}dBm")
            
            print(f"✅ HC-05 scan complete. Found {len(bluetooth_devices)} compatible devices")
            return bluetooth_devices
            
        except Exception as e:
            print(f"❌ Bluetooth scan error: {e}")
            return []

    def scan_bluetooth_devices(self) -> List[BluetoothDeviceInfo]:
        """Scan for Bluetooth devices (blocking call that uses async internally)"""
        if not self.bluetooth_available:
            print("❌ Bluetooth not available")
            return []
        
        if self.scanning:
            print("⚠️  Already scanning...")
            return []
        
        self.scanning = True
        
        try:
            if BLUETOOTH_LIBRARY == "bleak" and self.loop:
                # Use modern bleak scanning
                future = asyncio.run_coroutine_threadsafe(
                    self._scan_bluetooth_devices_async(), self.loop
                )
                devices = future.result(timeout=20.0)  # 20 second timeout for HC-05
                return devices
            
            elif BLUETOOTH_LIBRARY == "pybluez":
                # Fallback to pybluez
                return self._scan_pybluez_devices()
            
            else:
                print("❌ No compatible Bluetooth library available")
                return []
                
        except Exception as e:
            print(f"❌ Bluetooth scanning failed: {e}")
            return []
        finally:
            self.scanning = False

    def _scan_pybluez_devices(self) -> List[BluetoothDeviceInfo]:
        """Fallback scanning using pybluez with HC-05 focus"""
        try:
            import bluetooth
            print("🔍 Scanning using PyBluez (legacy mode) for HC-05 devices...")
            
            nearby_devices = bluetooth.discover_devices(
                duration=10, lookup_names=True, flush_cache=True
            )
            
            devices = []
            for addr, name in nearby_devices:
                device_name = name if name else f"Device-{addr[-5:].replace(':', '')}"
                
                # Apply HC-05 filtering for pybluez too
                is_hc05_device = any(
                    filter_name.lower() in device_name.lower() 
                    for filter_name in self.hc05_device_filters
                )
                
                if is_hc05_device or not name:  # Include unnamed devices (might be HC-05)
                    devices.append(BluetoothDeviceInfo(addr, device_name))
                    print(f"📱 Found: {device_name} ({addr})")
            
            return devices
            
        except Exception as e:
            print(f"❌ PyBluez scan error: {e}")
            return []

    async def _connect_ble_device_async(self, device_info: BluetoothDeviceInfo, device: Device):
        """Async BLE connection using bleak with HC-05 service discovery"""
        try:
            print(f"🔗 Connecting to HC-05 device {device_info.name} ({device_info.address})...")
            print(f"🎯 Expected data format from ATmega32A: Simple float like '15.3' or startup 'SensorNode Online'")
            
            client = BleakClient(device_info.address)
            await client.connect(timeout=30.0)  # Longer timeout for HC-05
            
            if client.is_connected:
                print(f"✅ Successfully connected to {device_info.name}")
                print(f"📋 Connection details:")
                print(f"   - Device: {device_info.name}")
                print(f"   - Address: {device_info.address}")
                print(f"   - RSSI: {device_info.rssi}dBm")
                
                device.status = DeviceStatus.CONNECTED
                print(f"✅ Device {device.device_name} status set to CONNECTED (type: {device.device_type})")
                self.bluetooth_clients[device.device_id] = client
                
                if self.on_device_connected:
                    self.on_device_connected(device.device_id, device.device_name)
                
                # Start HC-05 specific data monitoring
                await self._monitor_hc05_device(client, device)
            else:
                raise Exception("Failed to establish BLE connection")
                
        except Exception as e:
            print(f"❌ HC-05 connection failed to {device_info.name}: {e}")
            print(f"🔍 Connection error details:")
            print(f"   - Device: {device_info.name}")
            print(f"   - Address: {device_info.address}")
            print(f"   - Error: {type(e).__name__}: {str(e)}")
            device.status = DeviceStatus.ERROR
            device.error_message = str(e)

    async def _monitor_hc05_device(self, client: BleakClient, device: Device):
        """Monitor HC-05 device for data using proven service UUIDs"""
        try:
            # Discover all services first - FIXED API CALL
            print(f"🔍 Discovering services for {device.device_name}...")
            services = client.services  # Use .services property instead of get_services()
            
            # Convert to list to get count and iterate properly
            service_list = list(services)
            print(f"📋 Found {len(service_list)} services:")
            
            for service in service_list:
                print(f"  🔧 Service: {service.uuid}")
                # Also show characteristics for each service
                for char in service.characteristics:
                    properties = []
                    if "read" in char.properties:
                        properties.append("read")
                    if "write" in char.properties:
                        properties.append("write")
                    if "notify" in char.properties:
                        properties.append("notify")
                    if "indicate" in char.properties:
                        properties.append("indicate")
                    print(f"    📱 Characteristic: {char.uuid} [{', '.join(properties)}]")
            
            # Try to find HC-05 compatible characteristics using proven UUIDs
            rx_char = None
            service_found = None
            
            # Try each known HC-05 service UUID
            for service_uuid in self.hc05_service_uuids:
                try:
                    # Use the services property to find the service
                    for service in service_list:
                        if str(service.uuid).lower() == service_uuid.lower():
                            service_found = service
                            print(f"✅ Found HC-05 service: {service_uuid}")
                            break
                    if service_found:
                        break
                except Exception as e:
                    print(f"  ❌ Service {service_uuid} not found: {e}")
                    continue
            
            if not service_found:
                # Fallback: try to find any service with notify characteristics
                print("⚠️  No standard HC-05 service found, trying alternative discovery...")
                for service in service_list:
                    try:
                        for char in service.characteristics:
                            if "notify" in char.properties or "read" in char.properties:
                                rx_char = char
                                service_found = service
                                print(f"✅ Found alternative characteristic: {char.uuid}")
                                break
                        if rx_char:
                            break
                    except Exception as e:
                        print(f"  ❌ Error checking service {service.uuid}: {e}")
                        continue
            else:
                # Try to get the characteristic from the found service
                try:
                    print(f"📡 Found {len(service_found.characteristics)} characteristics in service:")
                    
                    for char in service_found.characteristics:
                        properties = []
                        if "read" in char.properties:
                            properties.append("read")
                        if "write" in char.properties:
                            properties.append("write")
                        if "notify" in char.properties:
                            properties.append("notify")
                        if "indicate" in char.properties:
                            properties.append("indicate")
                        
                        print(f"  📱 Characteristic: {char.uuid} [{', '.join(properties)}]")
                        
                        # Prefer notify characteristics for HC-05 data
                        if "notify" in char.properties:
                            rx_char = char
                            break
                        elif not rx_char and "read" in char.properties:
                            rx_char = char
                            
                except Exception as e:
                    print(f"❌ Error getting characteristics: {e}")
            
            if rx_char:
                print(f"📡 Using characteristic: {rx_char.uuid}")
                
                def notification_handler(sender: int, data: bytearray):
                    try:
                        # Log raw data first
                        raw_data = data.decode('utf-8', errors='ignore').strip()
                        print(f"📦 RAW DATA from {device.device_name}: '{raw_data}' (bytes: {len(data)})")
                        
                        if raw_data:  # Only process non-empty messages
                            # Route to appropriate data processor based on device type
                            if device.device_type == "moving_object":
                                self._process_moving_object_data(device.device_id, raw_data)
                            else:
                                self._process_hc05_data(device.device_id, raw_data)
                    except Exception as e:
                        # Log error but continue running - don't crash the app
                        print(f"⚠️  Data processing error from {device.device_name}: {e}")
                        print(f"📝 Raw data causing error: {data}")
                        # App continues running
                
                # Start notifications if supported
                if "notify" in rx_char.properties:
                    await client.start_notify(rx_char, notification_handler)
                    print(f"✅ Started notifications on {rx_char.uuid}")
                    print(f"🎯 Waiting for distance data from ATmega32A...")
                else:
                    print("⚠️  Characteristic doesn't support notify, will poll instead")
                    # Start polling for devices that don't support notifications
                    asyncio.create_task(self._poll_hc05_data(client, rx_char, device))
                
                # Keep connection alive and log status
                connection_start = time.time()
                while client.is_connected and device.device_id in self.devices:
                    await asyncio.sleep(1.0)
                    
                    # Log connection status every 10 seconds
                    if int(time.time() - connection_start) % 10 == 0:
                        print(f"🔗 HC-05 connection alive for {int(time.time() - connection_start)}s - waiting for data...")
                    
            else:
                print("❌ No suitable data characteristic found for HC-05")
                print("🔍 Available characteristics:")
                for service in service_list:
                    for char in service.characteristics:
                        print(f"  📱 {char.uuid} - Properties: {char.properties}")
                
                # Don't fall back to simulation - keep trying
                print("⚠️  Will keep connection open but no data will be received")
                while client.is_connected and device.device_id in self.devices:
                    await asyncio.sleep(5.0)
                    print(f"⏳ Still connected to {device.device_name}, but no data characteristic found")
                
        except Exception as e:
            print(f"❌ HC-05 monitoring error: {e}")
            print(f"🔍 Error details: {type(e).__name__}: {str(e)}")
            # Don't simulate data - let the user know there's a real issue
            print("❌ Real connection failed - check HC-05 device and pairing")

    async def _poll_hc05_data(self, client: BleakClient, characteristic, device: Device):
        """Poll HC-05 device for data when notifications aren't supported"""
        print(f"🔄 Starting data polling for {device.device_name}")
        
        while client.is_connected and device.device_id in self.devices:
            try:
                if "read" in characteristic.properties:
                    data = await client.read_gatt_char(characteristic)
                    if data:
                        raw_data = data.decode('utf-8', errors='ignore').strip()
                        if raw_data:
                            print(f"📦 RAW POLLED DATA from {device.device_name}: '{raw_data}' (bytes: {len(data)})")
                            self._process_hc05_data(device.device_id, raw_data)
                
                await asyncio.sleep(0.5)  # Poll every 500ms
                
            except Exception as e:
                print(f"⚠️  Polling error: {e}")
                await asyncio.sleep(2.0)  # Longer delay on error

    def _process_hc05_data(self, device_id: str, data: str):
        """Process HC-05 data using the same logic as the working HTML"""
        try:
            # Get friendly device name for logging
            device = self.devices.get(device_id)
            device_name = device.device_name if device else device_id
            
            print(f"🧠 Processing data from {device_name}: '{data}'")
            distance = None
            
            # Based on ATmega32A code, it sends: sprintf(buffer, "%s\n", dist_str);
            # where dist_str is formatted as dtostrf(distance, 5, 1, dist_str) - so "  15.3" format
            
            # Handle startup message
            if "SensorNode Online" in data:
                print(f"✅ {device_name} startup message received")
                return
            
            # Try to parse JSON format first: {"angle": 60, "distance": 15.3}
            if data.startswith('{') and data.endswith('}'):
                try:
                    json_data = json.loads(data)
                    if 'distance' in json_data:
                        distance = float(json_data['distance'])
                except Exception as e:
                    print(f"⚠️  JSON parsing failed for {device_name}: {e}")
            
            # Primary format: Simple distance value like "15.3" or "  15.3"
            if distance is None:
                try:
                    # Clean up the string - remove whitespace and try to parse
                    clean_data = data.strip()
                    distance = float(clean_data)
                except ValueError as e:
                    print(f"⚠️  Simple parsing failed for {device_name} '{clean_data}': {e}")
                    
                    # Fallback parsing for legacy formats
                    if ':' in data:
                        try:
                            parts = data.split(':')
                            if len(parts) > 1:
                                distance = float(parts[1].strip())
                        except ValueError as e:
                            print(f"⚠️  Colon parsing failed for {device_name}: {e}")
                    elif 'cm' in data.lower():
                        try:
                            distance = float(data.lower().replace('cm', '').strip())
                        except ValueError as e:
                            print(f"⚠️  CM parsing failed for {device_name}: {e}")
            
            # Validate distance range (ATmega32A sends 1-200cm based on code)
            if distance is not None:
                if 1.0 <= distance <= 400.0:  # Valid range
                    # Check if distance actually changed before logging
                    device = self.devices.get(device_id)
                    previous_distance = device.last_distance if device else None
                    
                    self._update_device_distance(device_id, distance)
                    
                    # Only log if distance changed significantly (more than 0.5cm)
                    if previous_distance is None or abs(distance - previous_distance) > 0.5:
                        print(f"✅ Distance change for {device_name}: {distance}cm (prev: {previous_distance}cm)")
                else:
                    print(f"⚠️  Distance out of range from {device_name}: {distance}cm (expected 1-400cm)")
                    # Log error but continue - don't crash the app
            else:
                print(f"❌ Could not parse distance from {device_name}: '{data}' - continuing...")
                # App continues running despite parse failure
            
        except Exception as e:
            device = self.devices.get(device_id)
            device_name = device.device_name if device else device_id
            print(f"⚠️  HC-05 data processing error for {device_name} '{data}': {e}")
            print(f"📝 Error details: {type(e).__name__}")
            # Don't print traceback - just log and continue
            # App continues running

    def _process_moving_object_data(self, device_id: str, data: str):
        """Process moving object data (angle/orientation only)"""
        try:
            # Get friendly device name for logging
            device = self.devices.get(device_id)
            device_name = device.device_name if device else device_id
            
            print(f"🚗 Processing moving object data from {device_name}: '{data}'")
            
            # Handle startup message
            if "MovingObject Online" in data or "BluetoothCar Online" in data:
                print(f"✅ {device_name} moving object startup message received")
                return
            
            orientation = None
            
            # Try to parse JSON format with angle: {"angle": 45.0}
            if data.startswith('{') and data.endswith('}'):
                try:
                    json_data = json.loads(data)
                    if 'angle' in json_data:
                        orientation = float(json_data['angle'])
                        print(f"📊 Parsed JSON angle from {device_name}: {orientation}°")
                    elif 'orientation' in json_data:
                        orientation = float(json_data['orientation'])
                        print(f"📊 Parsed JSON orientation from {device_name}: {orientation}°")
                except Exception as e:
                    print(f"⚠️  Moving object JSON parsing failed for {device_name}: {e}")
            
            # Try simple angle value like "45.0" or "  45.0"
            if orientation is None:
                try:
                    # Clean up the string - remove whitespace and try to parse
                    clean_data = data.strip()
                    orientation = float(clean_data)
                    print(f"📊 Parsed simple angle from {device_name}: {orientation}°")
                except ValueError as e:
                    print(f"⚠️  Simple angle parsing failed for {device_name} '{clean_data}': {e}")
            
            # Validate orientation range and update
            if orientation is not None:
                # Normalize angle to 0-360 range
                orientation = orientation % 360
                self._update_moving_object_orientation(device_id, orientation)
                print(f"✅ Valid orientation from {device_name}: {orientation}°")
            else:
                print(f"❌ Could not parse orientation from {device_name}: '{data}' - expected angle value or JSON")
            
        except Exception as e:
            device = self.devices.get(device_id)
            device_name = device.device_name if device else device_id
            print(f"⚠️  Moving object data processing error for {device_name} '{data}': {e}")
            print(f"📝 Error details: {type(e).__name__}")

    def _update_moving_object_orientation(self, device_id: str, orientation: float):
        """Update moving object orientation only"""
        try:
            device = self.devices.get(device_id)
            if not device:
                print(f"❌ Moving object device {device_id} not found")
                return
            
            # Update device orientation data
            device.last_orientation = orientation
            device.orientation_updated = True  # Flag that new orientation data is available
            device.connection_time = time.time()
            
            print(f"✅ Updated moving object {device.device_name}: orientation={orientation:.1f}°")
            
        except Exception as e:
            print(f"⚠️  Failed to update moving object orientation: {e}")

    def get_moving_object_updates(self) -> List[Tuple[str, float]]:
        """Get all pending moving object orientation updates and clear the flags"""
        updates = []
        for device_id, device in self.devices.items():
            if (device.device_type == "moving_object" and 
                device.orientation_updated and 
                device.last_orientation is not None):
                
                updates.append((device_id, device.last_orientation))
                device.orientation_updated = False  # Clear the flag
        
        return updates

    async def _simulate_hc05_data(self, device: Device):
        """Simulate HC-05 data for testing when real connection fails"""
        print(f"🎭 Simulating HC-05 data for {device.device_name}")
        
        distance = 50.0
        while device.device_id in self.devices and device.status == DeviceStatus.CONNECTED:
            # Simulate realistic distance changes like an HC-05 sensor
            distance += random.uniform(-8, 8)
            distance = max(5, min(200, distance))
            
            self._process_hc05_data(device.device_id, f"{distance:.1f}")
            await asyncio.sleep(0.5)

    def connect_to_device(self, device_info):
        """Connect to a device (Bluetooth or Serial)"""
        if not device_info:
            print("❌ No device info provided")
            return

        try:
            if hasattr(device_info, 'is_bluetooth') and device_info.is_bluetooth:
                self._connect_bluetooth_device(device_info)
            elif isinstance(device_info, ListPortInfo):
                self._connect_serial_device(device_info)
            else:
                print(f"❌ Unknown device type: {type(device_info)}")
        except Exception as e:
            print(f"❌ Connection error: {e}")

    def _connect_bluetooth_device(self, device_info: BluetoothDeviceInfo):
        """Connect to a Bluetooth device with HC-05 support"""
        if not BLUETOOTH_AVAILABLE:
            print("❌ Bluetooth not available")
            return

        device_id = f"bt_{device_info.address.replace(':', '_')}"
        
        if device_id in self.devices:
            print(f"⚠️  Device {device_info.name} already connected")
            return

        print(f"🔗 Initiating HC-05 connection to {device_info.name}...")
        
        # Check if this is a moving object device
        is_moving_object = getattr(device_info, 'is_moving_object', False)
        device_type = "moving_object" if is_moving_object else "bluetooth"
        
        device = Device(
            device_id=device_id,
            device_name=device_info.name,
            status=DeviceStatus.CONNECTING,
            connection_time=time.time(),
            connection_info=device_info.address,
            device_type=device_type,
            rssi=device_info.rssi
        )
        
        self.devices[device_id] = device
        
        if BLUETOOTH_LIBRARY == "bleak" and self.loop:
            # Use modern bleak connection
            asyncio.run_coroutine_threadsafe(
                self._connect_ble_device_async(device_info, device), self.loop
            )
        else:
            # Fallback to pybluez or simulation
            self._connect_bluetooth_fallback(device_info, device)

    def _connect_bluetooth_fallback(self, device_info: BluetoothDeviceInfo, device: Device):
        """Fallback Bluetooth connection method"""
        def connection_worker():
            try:
                if BLUETOOTH_LIBRARY == "pybluez":
                    self._connect_pybluez_device(device_info, device)
                else:
                    # Simulate connection for demo purposes
                    print(f"🎭 Simulating HC-05 connection to {device_info.name}")
                    time.sleep(2)
                    device.status = DeviceStatus.CONNECTED
                    
                    if self.on_device_connected:
                        self.on_device_connected(device.device_id, device.device_name)
                    
                    self._simulate_device_data(device)
                    
            except Exception as e:
                print(f"❌ Fallback connection failed: {e}")
                device.status = DeviceStatus.ERROR
                device.error_message = str(e)

        thread = threading.Thread(target=connection_worker, daemon=True)
        thread.start()

    def _connect_pybluez_device(self, device_info: BluetoothDeviceInfo, device: Device):
        """Connect using pybluez (legacy) with HC-05 support"""
        try:
            import bluetooth
            
            sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
            sock.settimeout(15)
            
            # Try multiple channels for HC-05
            connected = False
            for channel in [1, 2, 3, 4]:
                try:
                    print(f"🔗 Trying HC-05 channel {channel}...")
                    sock.connect((device_info.address, channel))
                    connected = True
                    print(f"✅ Connected on channel {channel}")
                    break
                except bluetooth.BluetoothError:
                    continue
            
            if not connected:
                raise bluetooth.BluetoothError("No available channels")
            
            device.status = DeviceStatus.CONNECTED
            if self.on_device_connected:
                self.on_device_connected(device.device_id, device.device_name)
            
            # Start data monitoring
            self._monitor_pybluez_device(sock, device)
            
        except Exception as e:
            print(f"❌ PyBluez connection failed: {e}")
            device.status = DeviceStatus.ERROR
            device.error_message = str(e)

    def _monitor_pybluez_device(self, sock, device: Device):
        """Monitor pybluez device for incoming data"""
        try:
            sock.settimeout(1.0)
            buffer = ""
            
            while self.running and device.device_id in self.devices:
                try:
                    data = sock.recv(1024).decode('utf-8', errors='ignore')
                    if data:
                        buffer += data
                        while '\n' in buffer:
                            line, buffer = buffer.split('\n', 1)
                            line = line.strip()
                            if line:
                                self._process_hc05_data(device.device_id, line)
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"❌ Data read error: {e}")
                    break
                    
        finally:
            try:
                sock.close()
            except:
                pass
            self.disconnect_device(device.device_id)

    def _simulate_device_data(self, device: Device):
        """Simulate device data for testing"""
        distance = 50.0
        while (self.running and 
               device.device_id in self.devices and 
               device.status == DeviceStatus.CONNECTED):
            
            distance += random.uniform(-5, 5)
            distance = max(5, min(200, distance))
            
            self._process_hc05_data(device.device_id, f"{distance:.1f}")
            time.sleep(0.5)

    def _connect_serial_device(self, port_info: ListPortInfo):
        """Connect to a Serial device"""
        device_id = f"serial_{port_info.device.replace('/', '_').replace('\\', '_')}"
        
        if device_id in self.devices:
            print(f"⚠️  Serial device already connected: {port_info.device}")
            return

        print(f"🔗 Connecting to serial device: {port_info.device}")
        
        device = Device(
            device_id=device_id,
            device_name=port_info.description or f"Serial-{port_info.device}",
            status=DeviceStatus.CONNECTING,
            connection_time=time.time(),
            connection_info=port_info.device,
            device_type="serial"
        )
        
        self.devices[device_id] = device
        self._start_serial_listener(device)

    def _start_serial_listener(self, device: Device):
        """Start serial listener thread"""
        def serial_worker():
            ser = None
            try:
                ser = serial.Serial(device.connection_info, 9600, timeout=1)
                device.status = DeviceStatus.CONNECTED
                
                if self.on_device_connected:
                    self.on_device_connected(device.device_id, device.device_name)
                
                print(f"✅ Serial device connected: {device.device_name}")
                
                while self.running and device.device_id in self.devices:
                    try:
                        line = ser.readline().decode('utf-8', errors='ignore').strip()
                        if line:
                            self._process_hc05_data(device.device_id, line)
                    except Exception:
                        continue
                        
            except Exception as e:
                print(f"❌ Serial connection failed: {e}")
                device.status = DeviceStatus.ERROR
                device.error_message = str(e)
            finally:
                if ser and ser.is_open:
                    ser.close()
                self.disconnect_device(device.device_id)

        thread = threading.Thread(target=serial_worker, daemon=True)
        thread.start()

    def _update_device_distance(self, device_id: str, distance: float):
        """Update device distance and notify listeners"""
        device = self.devices.get(device_id)
        if device:
            device.last_distance = distance
            device.last_update = time.time()
            
            if self.on_distance_update:
                self.on_distance_update(device_id, distance)

    def disconnect_device(self, device_id: str):
        """Disconnect a device with enhanced error handling"""
        if device_id not in self.devices:
            print(f"⚠️  Device {device_id} not found in connected devices")
            return False
            
        try:
            device = self.devices.pop(device_id)
            device.status = DeviceStatus.DISCONNECTED
            
            # Clean up BLE client if exists
            if device_id in self.bluetooth_clients:
                client = self.bluetooth_clients.pop(device_id)
                if self.loop and BLUETOOTH_LIBRARY == "bleak":
                    try:
                        asyncio.run_coroutine_threadsafe(
                            self._disconnect_ble_client(client), self.loop
                        )
                    except Exception as ble_error:
                        print(f"⚠️  BLE cleanup error for {device.device_name}: {ble_error}")
            
            # Trigger disconnection callback
            if self.on_device_disconnected:
                try:
                    self.on_device_disconnected(device_id)
                except Exception as callback_error:
                    print(f"⚠️  Disconnect callback error: {callback_error}")
            
            print(f"🔌 Disconnected: {device.device_name}")
            return True
            
        except Exception as e:
            print(f"🚨 Error disconnecting device {device_id}: {e}")
            return False

    async def _disconnect_ble_client(self, client):
        """Safely disconnect BLE client"""
        try:
            if client.is_connected:
                await client.disconnect()
        except Exception as e:
            print(f"⚠️  BLE disconnect error: {e}")

    def get_connected_devices(self) -> List[Device]:
        """Get list of connected devices"""
        return [dev for dev in self.devices.values() 
                if dev.status == DeviceStatus.CONNECTED]

    def start_demo_mode(self):
        """Start demo mode without any initial devices"""
        if self.demo_mode:
            return
            
        self.demo_mode = True
        self.demo_devices.clear()  # Clear any existing demo devices
        self.demo_device_counter = 0
        
        print("✅ HC-05 demo mode activated")

    def add_demo_device(self, custom_name: str = None) -> str:
        """Add a new demo device and return its ID"""
        if not self.demo_mode:
            print("❌ Demo mode must be enabled first")
            return None
        
        self.demo_device_counter += 1
        device_id = f"demo_hc05_{self.demo_device_counter:03d}"
        
        if custom_name:
            device_name = custom_name
        else:
            device_name = f"Demo HC-05 SensorNode {self.demo_device_counter}"
        
        # Generate a random starting distance for variety
        starting_distance = random.uniform(20.0, 150.0)
        
        demo_device = Device(
            device_id=device_id,
            device_name=device_name,
            status=DeviceStatus.CONNECTED,
            audio_file="sine_440",
            device_type="demo",
            last_distance=starting_distance
        )
        
        # Add to both demo devices and main devices collections
        self.demo_devices[device_id] = demo_device
        self.devices[device_id] = demo_device
        
        if self.on_device_connected:
            self.on_device_connected(device_id, device_name)
        
        # Start individual demo data generation for this device
        self._start_demo_worker_for_device(device_id)
        
        print(f"✅ Added demo device: {device_name} (starting at {starting_distance:.1f}cm)")
        return device_id

    def remove_demo_device(self, device_id: str = None) -> bool:
        """Remove a specific demo device, or the most recent one if no ID provided"""
        if not self.demo_mode:
            print("❌ Demo mode must be enabled first")
            return False
        
        if not self.demo_devices:
            print("❌ No demo devices to remove")
            return False
        
        # If no device_id specified, remove the most recent one
        if device_id is None:
            device_id = max(self.demo_devices.keys())  # Get the highest numbered device
        
        if device_id not in self.demo_devices:
            print(f"⚠️  Demo device {device_id} not found")
            return False
        
        try:
            demo_device = self.demo_devices[device_id]
            device_name = demo_device.device_name
            
            # Remove from collections with proper cleanup
            self.demo_devices.pop(device_id, None)
            
            # Also remove from main devices collection if it exists there
            disconnect_success = True
            if device_id in self.devices:
                disconnect_success = self.disconnect_device(device_id)
            
            if disconnect_success:
                print(f"✅ Removed demo device: {device_name}")
                return True
            else:
                print(f"⚠️  Demo device {device_name} removed from demo collection but disconnect failed")
                return False
                
        except Exception as e:
            print(f"🚨 Error removing demo device {device_id}: {e}")
            return False

    def clear_all_demo_devices(self):
        """Remove all demo devices"""
        if not self.demo_mode:
            print("❌ Demo mode must be enabled first")
            return
        
        device_count = len(self.demo_devices)
        if device_count == 0:
            print("❌ No demo devices to clear")
            return
        
        # Remove all demo devices
        for device_id in list(self.demo_devices.keys()):
            self.disconnect_device(device_id)
        
        self.demo_devices.clear()
        print(f"✅ Cleared {device_count} demo devices")

    def _start_demo_worker_for_device(self, device_id: str):
        """Start a demo data worker thread for a specific device"""
        def demo_worker():
            device = self.demo_devices.get(device_id)
            if not device:
                return
            
            # Each device has its own unique pattern
            device_seed = hash(device_id) % 1000
            base_frequency = (0.1 + (device_seed % 5) * 0.05) * self.demo_speed  # Different cycle speeds with speed control
            base_offset = (device_seed % 10) * 3.0  # Different starting phases
            start_time = time.time()  # For linear pattern
            
            while (self.demo_mode and self.running and 
                   device_id in self.demo_devices and 
                   device_id in self.devices):
                
                # Generate distance based on selected pattern
                if self.demo_pattern == 'linear':
                    # Linear back-and-forth pattern
                    elapsed = (time.time() - start_time) * base_frequency
                    # Create triangle wave (0 to 1 to 0 to 1...)
                    cycle_pos = (elapsed % 2.0)  # 0 to 2
                    if cycle_pos <= 1.0:
                        base_distance = cycle_pos  # 0 to 1
                    else:
                        base_distance = 2.0 - cycle_pos  # 1 to 0
                elif self.demo_pattern == 'sinusoidal':
                    # Original sinusoidal pattern
                    cycle_progress = (time.time() * base_frequency) % (2 * math.pi)
                    base_distance = 0.5 * (1 - math.cos(cycle_progress + base_offset))
                else:  # random
                    # Random walk pattern
                    current_distance = device.last_distance if device.last_distance else 50.0
                    change = random.uniform(-10.0, 10.0) * self.demo_speed
                    base_distance = max(0.0, min(1.0, (current_distance + change) / self.demo_amplitude))
                
                # Apply amplitude and add noise
                distance = max(5.0, min(175.0, base_distance * self.demo_amplitude + random.uniform(-3.0, 3.0)))
                
                self._update_device_distance(device_id, distance)
                time.sleep(0.2)  # 5Hz update rate
        
        # Start the worker thread
        demo_thread = threading.Thread(target=demo_worker, daemon=True)
        demo_thread.start()

    def _demo_worker(self):
        """Legacy demo worker - now handles multiple devices"""
        # This method is kept for backwards compatibility but doesn't do much
        # Individual device workers are started by _start_demo_worker_for_device
        while self.demo_mode and self.running:
            # Just sleep, individual device workers handle the data generation
            time.sleep(1.0)

    def stop_demo_mode(self):
        """Stop demo mode and remove all demo devices"""
        if not self.demo_mode:
            return
            
        self.demo_mode = False
        
        # Remove all demo devices
        device_count = len(self.demo_devices)
        for device_id in list(self.demo_devices.keys()):
            self.disconnect_device(device_id)
        
        self.demo_devices.clear()
        self.demo_device_counter = 0
        
        print(f"✅ HC-05 demo mode deactivated - removed {device_count} demo devices")

    def get_device_statistics(self) -> Dict[str, Any]:
        """Get device manager statistics"""
        connected_count = len(self.get_connected_devices())
        bluetooth_count = len([d for d in self.devices.values() if d.device_type == "bluetooth"])
        serial_count = len([d for d in self.devices.values() if d.device_type == "serial"])
        demo_count = len(self.demo_devices)
        
        return {
            'total_devices': len(self.devices),
            'connected_devices': connected_count,
            'bluetooth_devices': bluetooth_count,
            'serial_devices': serial_count,
            'demo_devices': demo_count,
            'demo_mode_active': self.demo_mode,
            'bluetooth_available': BLUETOOTH_AVAILABLE,
            'bluetooth_library': BLUETOOTH_LIBRARY,
            'scanning': self.scanning,
            'hc05_support': True
        }

    def cleanup(self):
        """Clean up device manager resources"""
        print("🧹 Cleaning up device manager...")
        self.running = False
        
        # Disconnect all devices
        for device_id in list(self.devices.keys()):
            self.disconnect_device(device_id)
        
        # Stop demo mode
        if self.demo_mode:
            self.stop_demo_mode()
        
        # Close async loop
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
        
        print("✅ Device manager cleanup complete")
    
    def update_demo_settings(self, pattern: str = None, speed: float = None, amplitude: float = None):
        """Update demo pattern settings"""
        if pattern and pattern in ['linear', 'sinusoidal', 'random']:
            self.demo_pattern = pattern
            if Config.DEBUG.get('PRINT_UI_INTERACTIONS', True):
                print(f"Demo Settings: Pattern changed to {pattern}")
        
        if speed is not None and 0.1 <= speed <= 5.0:
            self.demo_speed = speed
            if Config.DEBUG.get('PRINT_UI_INTERACTIONS', True):
                print(f"Demo Settings: Speed changed to {speed:.1f}x")
        
        if amplitude is not None and 50.0 <= amplitude <= 300.0:
            self.demo_amplitude = amplitude
            if Config.DEBUG.get('PRINT_UI_INTERACTIONS', True):
                print(f"Demo Settings: Amplitude changed to {amplitude:.0f}cm")
    
    def get_demo_settings(self) -> dict:
        """Get current demo settings"""
        return {
            'pattern': self.demo_pattern,
            'speed': self.demo_speed,
            'amplitude': self.demo_amplitude
        }