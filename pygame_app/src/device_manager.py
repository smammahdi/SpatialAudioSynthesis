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

class BluetoothDeviceInfo:
    """Container for Bluetooth device information with bleak compatibility"""
    def __init__(self, address: str, name: str, rssi: int = 0, manufacturer_data: Dict = None):
        self.address = address
        self.name = name if name else f"Device-{address[-5:].replace(':', '')}"
        self.rssi = rssi
        self.manufacturer_data = manufacturer_data or {}
        self.device = address  # For compatibility
        self.description = f"Bluetooth BLE Device - {self.name}"
        self.is_bluetooth = True

class DeviceManager:
    """Enhanced Device Manager with HC-05 Bluetooth Support using proven patterns"""
    
    def __init__(self):
        self.devices: Dict[str, Device] = {}
        self.demo_device: Optional[Device] = None
        self.demo_mode = False
        self.scanning = False
        
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
        
        self.hc05_service_uuids = [
            "0000ffe0-0000-1000-8000-00805f9b34fb",  # HC-05 default service
            "00001101-0000-1000-8000-00805f9b34fb",  # Serial Port Profile
            "0000ffe1-0000-1000-8000-00805f9b34fb"   # HC-05 characteristic
        ]
        
        self.hc05_characteristic_uuids = [
            "0000ffe1-0000-1000-8000-00805f9b34fb",  # HC-05 main characteristic
            "00001101-0000-1000-8000-00805f9b34fb"   # Serial Port Profile characteristic
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
                is_nearby = device.rssi and device.rssi > -75
                
                # More permissive filtering for HC-05 devices
                is_potential_sensor = any(keyword in device_name.lower() for keyword in [
                    'sensor', 'node', 'arduino', 'esp', 'bluetooth', 'car', 'audio', 'distance'
                ])
                
                if is_hc05_device or (is_nearby and is_potential_sensor):
                    bt_device = BluetoothDeviceInfo(
                        address=device.address,
                        name=device_name,
                        rssi=device.rssi or 0,
                        manufacturer_data=device.metadata.get('manufacturer_data', {})
                    )
                    bluetooth_devices.append(bt_device)
                    
                    print(f"📱 Found HC-05 compatible device: {device_name} ({device.address}) RSSI: {device.rssi}dBm")
                elif device.rssi and device.rssi > -60:  # Very strong signal
                    # Include very nearby devices regardless of name
                    bt_device = BluetoothDeviceInfo(
                        address=device.address,
                        name=device_name,
                        rssi=device.rssi or 0,
                        manufacturer_data=device.metadata.get('manufacturer_data', {})
                    )
                    bluetooth_devices.append(bt_device)
                    print(f"📱 Found nearby device: {device_name} ({device.address}) RSSI: {device.rssi}dBm")
            
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
            print(f"🔗 Connecting to HC-05 device {device_info.name}...")
            
            client = BleakClient(device_info.address)
            await client.connect(timeout=20.0)
            
            if client.is_connected:
                print(f"✅ Connected to {device_info.name}")
                
                device.status = DeviceStatus.CONNECTED
                self.bluetooth_clients[device.device_id] = client
                
                if self.on_device_connected:
                    self.on_device_connected(device.device_id, device.device_name)
                
                # Start HC-05 specific data monitoring
                await self._monitor_hc05_device(client, device)
            else:
                raise Exception("Failed to establish connection")
                
        except Exception as e:
            print(f"❌ HC-05 connection failed: {e}")
            device.status = DeviceStatus.ERROR
            device.error_message = str(e)

    async def _monitor_hc05_device(self, client: BleakClient, device: Device):
        """Monitor HC-05 device for data using proven service UUIDs"""
        try:
            # Discover all services first
            print(f"🔍 Discovering services for {device.device_name}...")
            services = await client.get_services()
            
            print(f"📋 Found {len(services)} services:")
            for service in services:
                print(f"  🔧 Service: {service.uuid}")
            
            # Try to find HC-05 compatible characteristics using proven UUIDs
            rx_char = None
            service_found = None
            
            # Try each known HC-05 service UUID
            for service_uuid in self.hc05_service_uuids:
                try:
                    service_found = await client.get_service(service_uuid)
                    print(f"✅ Found HC-05 service: {service_uuid}")
                    break
                except Exception as e:
                    print(f"  ❌ Service {service_uuid} not found: {e}")
                    continue
            
            if not service_found:
                # Fallback: try to find any service with notify characteristics
                print("⚠️  No standard HC-05 service found, trying alternative discovery...")
                for service in services:
                    try:
                        characteristics = await service.get_characteristics()
                        for char in characteristics:
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
                    characteristics = await service_found.get_characteristics()
                    print(f"📡 Found {len(characteristics)} characteristics in service:")
                    
                    for char in characteristics:
                        props = []
                        if hasattr(char.properties, 'notify') and char.properties.notify:
                            props.append('notify')
                        if hasattr(char.properties, 'read') and char.properties.read:
                            props.append('read')
                        if hasattr(char.properties, 'write') and char.properties.write:
                            props.append('write')
                        
                        print(f"  📱 Characteristic: {char.uuid} [{', '.join(props)}]")
                        
                        # Prefer notify characteristics for HC-05 data
                        if hasattr(char.properties, 'notify') and char.properties.notify:
                            rx_char = char
                            break
                        elif not rx_char and (hasattr(char.properties, 'read') and char.properties.read):
                            rx_char = char
                            
                except Exception as e:
                    print(f"❌ Error getting characteristics: {e}")
            
            if rx_char:
                print(f"📡 Using characteristic: {rx_char.uuid}")
                
                def notification_handler(sender: int, data: bytearray):
                    try:
                        message = data.decode('utf-8', errors='ignore').strip()
                        if message:  # Only process non-empty messages
                            print(f"📦 Raw data from {device.device_name}: '{message}'")
                            self._process_hc05_data(device.device_id, message)
                    except Exception as e:
                        print(f"⚠️  Data processing error: {e}")
                
                # Start notifications if supported
                if hasattr(rx_char.properties, 'notify') and rx_char.properties.notify:
                    await client.start_notify(rx_char, notification_handler)
                    print(f"✅ Started notifications on {rx_char.uuid}")
                else:
                    print("⚠️  Characteristic doesn't support notify, will poll instead")
                    # Start polling for devices that don't support notifications
                    asyncio.create_task(self._poll_hc05_data(client, rx_char, device))
                
                # Keep connection alive
                while client.is_connected and device.device_id in self.devices:
                    await asyncio.sleep(1.0)
                    
            else:
                print("⚠️  No suitable data characteristic found, using simulated data")
                await self._simulate_hc05_data(device)
                
        except Exception as e:
            print(f"❌ HC-05 monitoring error: {e}")
            await self._simulate_hc05_data(device)

    async def _poll_hc05_data(self, client: BleakClient, characteristic, device: Device):
        """Poll HC-05 device for data when notifications aren't supported"""
        print(f"🔄 Starting data polling for {device.device_name}")
        
        while client.is_connected and device.device_id in self.devices:
            try:
                if hasattr(characteristic.properties, 'read') and characteristic.properties.read:
                    data = await client.read_gatt_char(characteristic)
                    if data:
                        message = data.decode('utf-8', errors='ignore').strip()
                        if message:
                            print(f"📦 Polled data from {device.device_name}: '{message}'")
                            self._process_hc05_data(device.device_id, message)
                
                await asyncio.sleep(0.5)  # Poll every 500ms
                
            except Exception as e:
                print(f"⚠️  Polling error: {e}")
                await asyncio.sleep(2.0)  # Longer delay on error

    def _process_hc05_data(self, device_id: str, data: str):
        """Process HC-05 data using the same logic as the working HTML"""
        try:
            distance = None
            
            # Try to parse JSON format first: {"angle": 60, "distance": 15.3}
            if data.startswith('{') and data.endswith('}'):
                try:
                    json_data = json.loads(data)
                    if 'distance' in json_data:
                        distance = float(json_data['distance'])
                except:
                    pass
            
            # Primary format: Simple distance value like "15.3"
            if distance is None:
                try:
                    distance = float(data.strip())
                except ValueError:
                    # Fallback parsing for legacy formats
                    if ':' in data:
                        parts = data.split(':')
                        if len(parts) > 1:
                            distance = float(parts[1].strip())
                    elif 'cm' in data.lower():
                        distance = float(data.lower().replace('cm', '').strip())
            
            if distance is not None and distance >= 0 and distance <= 400:  # Valid range
                self._update_device_distance(device_id, distance)
                print(f"📏 {device_id}: {distance}cm")
            else:
                print(f"⚠️  Invalid distance from {device_id}: {data}")
            
        except (ValueError, IndexError, TypeError) as e:
            print(f"⚠️  HC-05 data parsing error for '{data}': {e}")

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
        
        device = Device(
            device_id=device_id,
            device_name=device_info.name,
            status=DeviceStatus.CONNECTING,
            connection_time=time.time(),
            connection_info=device_info.address,
            device_type="bluetooth",
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
        """Disconnect a device"""
        if device_id in self.devices:
            device = self.devices.pop(device_id)
            device.status = DeviceStatus.DISCONNECTED
            
            # Clean up BLE client if exists
            if device_id in self.bluetooth_clients:
                client = self.bluetooth_clients.pop(device_id)
                if self.loop and BLUETOOTH_LIBRARY == "bleak":
                    asyncio.run_coroutine_threadsafe(
                        self._disconnect_ble_client(client), self.loop
                    )
            
            if self.on_device_disconnected:
                self.on_device_disconnected(device_id)
            
            print(f"🔌 Disconnected: {device.device_name}")

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
        """Start demo mode with simulated HC-05 device"""
        if self.demo_mode:
            return
            
        self.demo_mode = True
        self.demo_device = Device(
            device_id="demo_hc05_001",
            device_name="Demo HC-05 SensorNode",
            status=DeviceStatus.CONNECTED,
            audio_file="sine_440",
            device_type="demo"
        )
        
        self.devices[self.demo_device.device_id] = self.demo_device
        
        if self.on_device_connected:
            self.on_device_connected(self.demo_device.device_id, self.demo_device.device_name)
        
        # Start demo data generation
        demo_thread = threading.Thread(target=self._demo_worker, daemon=True)
        demo_thread.start()
        
        print("✅ HC-05 demo mode activated")

    def _demo_worker(self):
        """Generate demo data that mimics HC-05 distance sensor"""
        while self.demo_mode and self.running:
            if self.demo_device:
                # Generate realistic distance pattern
                cycle_progress = (time.time() % 30.0) / 30.0
                base_distance = 0.5 * (1 - math.cos(cycle_progress * math.pi * 2))
                distance = max(5.0, min(175.0, base_distance * 170.0 + random.uniform(-3.0, 3.0)))
                
                self._update_device_distance(self.demo_device.device_id, distance)
            
            time.sleep(0.2)  # 5Hz update rate

    def stop_demo_mode(self):
        """Stop demo mode"""
        if not self.demo_mode:
            return
            
        self.demo_mode = False
        if self.demo_device:
            self.disconnect_device(self.demo_device.device_id)
        self.demo_device = None
        
        print("✅ HC-05 demo mode deactivated")

    def get_device_statistics(self) -> Dict[str, Any]:
        """Get device manager statistics"""
        connected_count = len(self.get_connected_devices())
        bluetooth_count = len([d for d in self.devices.values() if d.device_type == "bluetooth"])
        serial_count = len([d for d in self.devices.values() if d.device_type == "serial"])
        
        return {
            'total_devices': len(self.devices),
            'connected_devices': connected_count,
            'bluetooth_devices': bluetooth_count,
            'serial_devices': serial_count,
            'demo_devices': 1 if self.demo_mode else 0,
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