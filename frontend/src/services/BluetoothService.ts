// Bluetooth Service - Ported from working Multi_HC05_WebApp.html
// This service handles multiple HC-05 Bluetooth connections for spatial audio

export interface SensorData {
  deviceId: string;
  deviceName: string;
  distance: number;
  lastUpdate: number;
  connected: boolean;
  angle?: number;
}

export interface BluetoothDeviceData {
  device: BluetoothDevice;
  server: BluetoothRemoteGATTServer;
  characteristic: BluetoothRemoteGATTCharacteristic;
  lastDistance: number;
  connected: boolean;
  lastUpdate: number;
  dataBuffer: string;
}

export type LogLevel = 'info' | 'error' | 'success' | 'warning' | 'debug';

export interface LogEntry {
  timestamp: string;
  message: string;
  level: LogLevel;
  deviceId?: string;
}

export class BluetoothSensorService {
  private devices: Map<string, BluetoothDeviceData> = new Map();
  private isConnecting: boolean = false;
  private onSensorDataCallback?: (data: SensorData) => void;
  private onLogCallback?: (log: LogEntry) => void;
  private onDeviceStatusCallback?: (deviceId: string, connected: boolean) => void;

  constructor() {
    this.checkWebBluetoothSupport();
  }

  // Event handlers
  onSensorData(callback: (data: SensorData) => void) {
    this.onSensorDataCallback = callback;
  }

  onLog(callback: (log: LogEntry) => void) {
    this.onLogCallback = callback;
  }

  onDeviceStatusChange(callback: (deviceId: string, connected: boolean) => void) {
    this.onDeviceStatusCallback = callback;
  }

  // Main connection method - based on working implementation
  async requestBluetoothDevice(): Promise<void> {
    if (this.isConnecting) return;

    try {
      this.isConnecting = true;
      this.log('Scanning for Bluetooth sensor devices...', 'info');

      const device = await navigator.bluetooth.requestDevice({
        filters: [
          { namePrefix: 'SensorNode' },
          { name: 'SensorNode_A' },
          { name: 'SensorNode_B' },
          { name: 'SensorNode_C' },
          { name: 'SensorNodeB' },
          { namePrefix: 'HC-' },
          { namePrefix: 'linvor' }
        ],
        optionalServices: [
          '0000ffe0-0000-1000-8000-00805f9b34fb',  // HC-05 default service
          '00001101-0000-1000-8000-00805f9b34fb',  // Serial Port Profile
          '0000ffe1-0000-1000-8000-00805f9b34fb'   // HC-05 characteristic
        ]
      });

      await this.connectDevice(device);

    } catch (error: any) {
      this.log(`Connection failed: ${error.message}`, 'error');
      throw error;
    } finally {
      this.isConnecting = false;
    }
  }

  // Connect to individual device - ported from working code
  private async connectDevice(device: BluetoothDevice): Promise<void> {
    const deviceId = device.id;

    if (this.devices.has(deviceId)) {
      this.log(`Device ${device.name || deviceId} already connected`, 'info');
      return;
    }

    try {
      this.log(`Connecting to ${device.name || deviceId}...`, 'info');

      const server = await device.gatt?.connect();
      if (!server) throw new Error('Failed to connect to GATT server');

      // Try different service UUIDs that HC-05 might use (from working code)
      let service: BluetoothRemoteGATTService;
      let characteristic: BluetoothRemoteGATTCharacteristic;

      try {
        // Try HC-05 default service first
        service = await server.getPrimaryService('0000ffe0-0000-1000-8000-00805f9b34fb');
        
        // Check for the working characteristic (ffe2 for SensorNodeB, ffe1 for others)
        try {
          characteristic = await service.getCharacteristic('0000ffe2-0000-1000-8000-00805f9b34fb');
        } catch {
          characteristic = await service.getCharacteristic('0000ffe1-0000-1000-8000-00805f9b34fb');
        }
      } catch (e1) {
        try {
          // Try Serial Port Profile
          service = await server.getPrimaryService('00001101-0000-1000-8000-00805f9b34fb');
          characteristic = await service.getCharacteristic('00001101-0000-1000-8000-00805f9b34fb');
        } catch (e2) {
          // List all available services for debugging
          this.log('Available services:', 'info');
          const services = await server.getPrimaryServices();
          services.forEach(svc => {
            this.log(`Service UUID: ${svc.uuid}`, 'debug');
          });
          throw new Error('No compatible service found. Check console for available services.');
        }
      }

      const deviceData: BluetoothDeviceData = {
        device,
        server,
        characteristic,
        lastDistance: 0,
        connected: true,
        lastUpdate: Date.now(),
        dataBuffer: ''
      };

      this.devices.set(deviceId, deviceData);

      // Start listening for data - critical for sensor readings
      await characteristic.startNotifications();
      characteristic.addEventListener('characteristicvaluechanged', 
        (event) => this.handleIncomingData(deviceId, event));

      device.addEventListener('gattserverdisconnected', 
        () => this.handleDisconnection(deviceId));

      this.log(`✅ Connected to ${device.name || deviceId}`, 'success');
      this.onDeviceStatusCallback?.(deviceId, true);

    } catch (error: any) {
      this.log(`Failed to connect to ${device.name || deviceId}: ${error.message}`, 'error');
      throw error;
    }
  }

  // Data handling - ported from working implementation
  private handleIncomingData(deviceId: string, event: Event): void {
    const deviceData = this.devices.get(deviceId);
    if (!deviceData) return;

    const target = event.target as BluetoothRemoteGATTCharacteristic;
    const value = new TextDecoder().decode(target.value);

    // Debug logging
    this.log(`Raw data from ${deviceData.device.name || deviceId}: "${value}"`, 'debug');

    deviceData.dataBuffer += value;

    // Process complete lines
    const lines = deviceData.dataBuffer.split('\n');
    deviceData.dataBuffer = lines.pop() || ''; // Keep incomplete line

    lines.forEach(line => {
      line = line.trim();
      if (line) {
        this.log(`Processing line: "${line}"`, 'debug');
        this.processDistanceData(deviceId, line);
      }
    });
  }

  // Distance data processing - enhanced from working code
  private processDistanceData(deviceId: string, data: string): void {
    const deviceData = this.devices.get(deviceId);
    if (!deviceData) return;

    let distance: number | null = null;
    let angle: number | undefined = undefined;

    try {
      // Try to parse JSON format first: {"angle": 60, "distance": 15.3}
      if (data.startsWith('{') && data.endsWith('}')) {
        const jsonData = JSON.parse(data);
        if (jsonData.distance !== undefined) {
          distance = parseFloat(jsonData.distance);
          angle = jsonData.angle ? parseFloat(jsonData.angle) : undefined;
        }
      }
      // Primary format: Simple distance value like "15.3"
      else {
        distance = parseFloat(data.trim());
      }
    } catch (e) {
      // Fallback parsing for legacy formats
      if (data.includes(':')) {
        const parts = data.split(':');
        distance = parseFloat(parts[1]);
      } else if (data.includes('cm')) {
        distance = parseFloat(data.replace('cm', '').trim());
      } else {
        distance = parseFloat(data.trim());
      }
    }

    if (distance !== null && !isNaN(distance) && distance >= 0) {
      deviceData.lastDistance = distance;
      deviceData.lastUpdate = Date.now();

      // Create sensor data object
      const sensorData: SensorData = {
        deviceId,
        deviceName: deviceData.device.name || `Device ${deviceId.slice(-4)}`,
        distance,
        lastUpdate: deviceData.lastUpdate,
        connected: true,
        angle
      };

      this.log(`📏 ${sensorData.deviceName}: ${distance}cm${angle ? ` @ ${angle}°` : ''}`, 'info');
      
      // Notify callback with sensor data
      this.onSensorDataCallback?.(sensorData);

    } else {
      this.log(`⚠️ Invalid data from ${deviceData.device.name || deviceId}: ${data}`, 'warning');
    }
  }

  // Disconnect individual device
  async disconnectDevice(deviceId: string): Promise<void> {
    const deviceData = this.devices.get(deviceId);
    if (!deviceData) return;

    try {
      if (deviceData.server && deviceData.server.connected) {
        deviceData.server.disconnect();
      }

      this.handleDisconnection(deviceId);
      this.log(`🔌 Disconnected from ${deviceData.device.name || deviceId}`, 'info');

    } catch (error: any) {
      this.log(`Error disconnecting from ${deviceData.device.name || deviceId}: ${error.message}`, 'error');
    }
  }

  // Handle disconnection
  private handleDisconnection(deviceId: string): void {
    const deviceData = this.devices.get(deviceId);
    if (!deviceData) return;

    deviceData.connected = false;
    this.devices.delete(deviceId);

    this.log(`❌ Device ${deviceData.device.name || deviceId} disconnected`, 'warning');
    this.onDeviceStatusCallback?.(deviceId, false);
  }

  // Disconnect all devices
  async disconnectAll(): Promise<void> {
    const deviceIds = Array.from(this.devices.keys());

    for (const deviceId of deviceIds) {
      await this.disconnectDevice(deviceId);
    }

    this.log('🔌 All devices disconnected', 'info');
  }

  // Get connected devices
  getConnectedDevices(): SensorData[] {
    return Array.from(this.devices.values())
      .filter(device => device.connected)
      .map(device => ({
        deviceId: device.device.id,
        deviceName: device.device.name || `Device ${device.device.id.slice(-4)}`,
        distance: device.lastDistance,
        lastUpdate: device.lastUpdate,
        connected: device.connected
      }));
  }

  // Check if device is connected
  isDeviceConnected(deviceId: string): boolean {
    const device = this.devices.get(deviceId);
    return device ? device.connected : false;
  }

  // Get device count
  getConnectedDeviceCount(): number {
    return Array.from(this.devices.values()).filter(device => device.connected).length;
  }

  // Service discovery - for debugging
  async discoverServices(): Promise<void> {
    try {
      this.log('🔍 Starting service discovery...', 'info');

      const device = await navigator.bluetooth.requestDevice({
        acceptAllDevices: true,
        optionalServices: [
          '0000ffe0-0000-1000-8000-00805f9b34fb',
          '00001101-0000-1000-8000-00805f9b34fb',
          '0000ffe1-0000-1000-8000-00805f9b34fb'
        ]
      });

      this.log(`🔗 Connecting to ${device.name || 'Unknown Device'} for discovery...`, 'info');

      const server = await device.gatt?.connect();
      if (!server) throw new Error('Failed to connect for discovery');

      this.log('✅ Connected! Discovering services...', 'success');

      const services = await server.getPrimaryServices();
      this.log(`📋 Found ${services.length} services:`, 'info');

      for (const service of services) {
        this.log(`🔧 Service: ${service.uuid}`, 'info');

        try {
          const characteristics = await service.getCharacteristics();
          this.log(`  └─ ${characteristics.length} characteristics:`, 'info');

          for (const char of characteristics) {
            const props = [];
            if (char.properties.read) props.push('read');
            if (char.properties.write) props.push('write');
            if (char.properties.notify) props.push('notify');
            if (char.properties.indicate) props.push('indicate');

            this.log(`     └─ ${char.uuid} [${props.join(', ')}]`, 'info');
          }
        } catch (charError: any) {
          this.log(`     └─ Error getting characteristics: ${charError.message}`, 'warning');
        }
      }

      server.disconnect();
      this.log('🔌 Discovery complete, disconnected', 'info');

    } catch (error: any) {
      this.log(`❌ Service discovery failed: ${error.message}`, 'error');
      throw error;
    }
  }

  // Logging
  private log(message: string, level: LogLevel): void {
    const logEntry: LogEntry = {
      timestamp: new Date().toLocaleTimeString(),
      message,
      level
    };

    console.log(`[${logEntry.timestamp}] ${message}`);
    this.onLogCallback?.(logEntry);
  }

  // Check Web Bluetooth support
  private checkWebBluetoothSupport(): void {
    if (!navigator.bluetooth) {
      this.log('❌ Web Bluetooth not supported in this browser', 'error');
      throw new Error('Web Bluetooth not supported. Use Chrome/Edge with HTTPS.');
    } else {
      this.log('✅ Web Bluetooth supported', 'success');
    }
  }

  // Get connection status
  get isConnecting(): boolean {
    return this.isConnecting;
  }
}
