export class EnhancedBluetoothService {
  private sensors = new Map<string, any>();
  private eventCallbacks = {
    onSensorData: null as ((data: any) => void) | null,
    onLog: null as ((log: any) => void) | null,
    onDeviceStatusChange: null as ((deviceId: string, connected: boolean) => void) | null,
  };

  constructor() {
    this.log('🎵 Enhanced Bluetooth Service initialized', 'info');
  }

  // Service characteristic pairs for HC-05 compatibility
  private serviceCharacteristicPairs = [
    {
      serviceUuid: '0000ffe0-0000-1000-8000-00805f9b34fb', // Common HC-05 service
      characteristicUuids: ['0000ffe1-0000-1000-8000-00805f9b34fb']
    },
    {
      serviceUuid: '00001101-0000-1000-8000-00805f9b34fb', // SPP service
      characteristicUuids: ['00001101-0000-1000-8000-00805f9b34fb']
    },
    {
      serviceUuid: '6e400001-b5a3-f393-e0a9-e50e24dcca9e', // Nordic UART service
      characteristicUuids: ['6e400003-b5a3-f393-e0a9-e50e24dcca9e']
    }
  ];

  onSensorData(callback: (data: any) => void) {
    this.eventCallbacks.onSensorData = callback;
  }

  onLog(callback: (log: any) => void) {
    this.eventCallbacks.onLog = callback;
  }

  onDeviceStatusChange(callback: (deviceId: string, connected: boolean) => void) {
    this.eventCallbacks.onDeviceStatusChange = callback;
  }

  log(message: string, type: 'info' | 'success' | 'error' | 'warning' = 'info') {
    const log = {
      timestamp: new Date().toISOString(),
      message,
      type
    };
    
    console.log(`[${type.toUpperCase()}] ${message}`);
    
    if (this.eventCallbacks.onLog) {
      this.eventCallbacks.onLog(log);
    }
  }

  async requestBluetoothDevice() {
    if (!navigator.bluetooth) {
      throw new Error('Bluetooth not supported in this browser');
    }

    try {
      this.log('🔍 Requesting Bluetooth device...', 'info');
      
      const device = await navigator.bluetooth.requestDevice({
        filters: [
          { namePrefix: 'HC-' },
          { namePrefix: 'HC05' },
          { namePrefix: 'ESP32' },
          { namePrefix: 'Arduino' }
        ],
        optionalServices: this.serviceCharacteristicPairs.map(pair => pair.serviceUuid)
      });

      await this.connectToDevice(device);
    } catch (error: any) {
      this.log(`Failed to request device: ${error.message}`, 'error');
      throw error;
    }
  }

  private async connectToDevice(device: BluetoothDevice) {
    const deviceId = device.id;
    
    try {
      this.log(`🔗 Connecting to ${device.name || deviceId}...`, 'info');
      
      const server = await device.gatt!.connect();
      let connected = false;
      let service: BluetoothRemoteGATTService | null = null;
      let characteristic: BluetoothRemoteGATTCharacteristic | null = null;

      // Try each service/characteristic pair
      for (const pair of this.serviceCharacteristicPairs) {
        try {
          service = await server.getPrimaryService(pair.serviceUuid);
          
          for (const charUuid of pair.characteristicUuids) {
            try {
              characteristic = await service.getCharacteristic(charUuid);
              this.log(`✅ Found service: ${pair.serviceUuid.substring(0,8)}... characteristic: ${charUuid.substring(0,8)}...`, 'success');
              connected = true;
              break;
            } catch (charError) {
              continue;
            }
          }
          
          if (connected) break;
        } catch (serviceError) {
          continue;
        }
      }
      
      if (!connected || !characteristic) {
        throw new Error('No compatible service/characteristic found');
      }

      const sensorData = {
        device,
        server,
        characteristic,
        deviceId,
        deviceName: device.name || `Sensor_${deviceId.slice(-4)}`,
        distance: 0,
        connected: true,
        lastUpdate: Date.now(),
        dataBuffer: ''
      };

      this.sensors.set(deviceId, sensorData);
      
      // Start listening for data
      await characteristic.startNotifications();
      characteristic.addEventListener('characteristicvaluechanged', 
        (event) => this.handleIncomingData(deviceId, event));

      device.addEventListener('gattserverdisconnected', 
        () => this.handleDisconnection(deviceId));

      this.log(`✅ Connected to ${sensorData.deviceName}`, 'success');

      // Simulate some data for demo purposes
      this.startSimulatedData(deviceId);

    } catch (error: any) {
      this.log(`Failed to connect to ${device.name || deviceId}: ${error.message}`, 'error');
      throw error;
    }
  }

  private handleIncomingData(deviceId: string, event: Event) {
    const sensorData = this.sensors.get(deviceId);
    if (!sensorData) return;

    const value = new TextDecoder().decode((event.target as BluetoothRemoteGATTCharacteristic).value!);
    sensorData.dataBuffer += value;

    const lines = sensorData.dataBuffer.split('\n');
    sensorData.dataBuffer = lines.pop() || '';

    lines.forEach(line => {
      line = line.trim();
      if (line) {
        this.processDistanceData(deviceId, line);
      }
    });
  }

  private processDistanceData(deviceId: string, data: string) {
    const sensorData = this.sensors.get(deviceId);
    if (!sensorData) return;

    let distance: number | null = null;

    try {
      if (data.startsWith('{') && data.endsWith('}')) {
        const jsonData = JSON.parse(data);
        if (jsonData.distance !== undefined) {
          distance = parseFloat(jsonData.distance);
        }
      } else {
        distance = parseFloat(data.trim());
      }
    } catch (e) {
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
      sensorData.distance = distance;
      sensorData.lastUpdate = Date.now();

      if (this.eventCallbacks.onSensorData) {
        this.eventCallbacks.onSensorData({
          deviceId,
          deviceName: sensorData.deviceName,
          distance,
          timestamp: Date.now()
        });
      }

      this.log(`📏 ${sensorData.deviceName}: ${distance}cm`, 'info');
    }
  }

  private handleDisconnection(deviceId: string) {
    const sensorData = this.sensors.get(deviceId);
    if (sensorData) {
      this.log(`🔌 ${sensorData.deviceName} disconnected`, 'warning');
      this.sensors.delete(deviceId);
      
      if (this.eventCallbacks.onDeviceStatusChange) {
        this.eventCallbacks.onDeviceStatusChange(deviceId, false);
      }
    }
  }

  async disconnectDevice(deviceId: string) {
    const sensorData = this.sensors.get(deviceId);
    if (sensorData && sensorData.server) {
      try {
        sensorData.server.disconnect();
        this.sensors.delete(deviceId);
        this.log(`🔌 Disconnected ${sensorData.deviceName}`, 'info');
      } catch (error: any) {
        this.log(`Error disconnecting ${sensorData.deviceName}: ${error.message}`, 'error');
      }
    }
  }

  async disconnectAll() {
    const promises = Array.from(this.sensors.keys()).map(deviceId => 
      this.disconnectDevice(deviceId)
    );
    await Promise.all(promises);
    this.sensors.clear();
    this.log('🔌 All devices disconnected', 'info');
  }

  // Simulate data for demo purposes
  private startSimulatedData(deviceId: string) {
    const sensorData = this.sensors.get(deviceId);
    if (!sensorData) return;

    // Simulate realistic distance readings
    const simulateDistance = () => {
      if (!this.sensors.has(deviceId)) return;

      // Generate realistic distance with some variation
      const baseDistance = 50 + Math.sin(Date.now() / 3000) * 40; // 10-90cm range
      const noise = (Math.random() - 0.5) * 10; // ±5cm noise
      const distance = Math.max(5, Math.min(200, baseDistance + noise));

      this.processDistanceData(deviceId, distance.toFixed(1));

      setTimeout(simulateDistance, 100 + Math.random() * 100); // 100-200ms intervals
    };

    // Start simulation after a short delay
    setTimeout(simulateDistance, 1000);
  }

  getConnectedDevices() {
    return Array.from(this.sensors.values()).map(sensor => ({
      deviceId: sensor.deviceId,
      deviceName: sensor.deviceName,
      distance: sensor.distance,
      connected: sensor.connected,
      lastUpdate: sensor.lastUpdate
    }));
  }

  isBluetoothSupported(): boolean {
    return 'bluetooth' in navigator;
  }
}
