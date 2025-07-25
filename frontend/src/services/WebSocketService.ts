// WebSocket Service for Backend Connection

// Configuration from environment variables
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';
const WS_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws';

export interface ServerMessage {
  type: 'sensor_data' | 'audio_ready' | 'error' | 'status';
  data: any;
  timestamp: string;
}

export interface AudioUploadResponse {
  success: boolean;
  filename: string;
  id: string;
  name: string;
}

export class WebSocketService {
  private ws: WebSocket | null = null;
  private readonly url: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectInterval = 3000;
  private onMessageCallback?: (message: ServerMessage) => void;
  private onStatusCallback?: (connected: boolean) => void;

  constructor(url: string = WS_URL) {
    this.url = url;
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
          console.log('🔗 Connected to backend server');
          this.reconnectAttempts = 0;
          this.onStatusCallback?.(true);
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const message: ServerMessage = JSON.parse(event.data);
            this.onMessageCallback?.(message);
          } catch (error) {
            console.error('Failed to parse message:', error);
          }
        };

        this.ws.onclose = () => {
          console.log('🔌 Disconnected from backend server');
          this.onStatusCallback?.(false);
          this.attemptReconnect();
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          reject(new Error('Failed to connect to backend server'));
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  private attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`🔄 Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
      
      setTimeout(() => {
        this.connect().catch(console.error);
      }, this.reconnectInterval);
    } else {
      console.error('❌ Max reconnection attempts reached');
    }
  }

  sendSensorData(deviceId: string, distance: number): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      const message = {
        type: 'sensor_data',
        device_id: deviceId,
        distance: distance,
        timestamp: new Date().toISOString()
      };
      this.ws.send(JSON.stringify(message));
    }
  }

  sendAudioConfig(deviceId: string, audioId: string, volume: number): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      const message = {
        type: 'audio_config',
        device_id: deviceId,
        audio_id: audioId,
        volume: volume,
        timestamp: new Date().toISOString()
      };
      this.ws.send(JSON.stringify(message));
    }
  }

  async uploadAudio(file: File, name: string): Promise<AudioUploadResponse> {
    const formData = new FormData();
    formData.append('audio_file', file);
    formData.append('name', name);

    const response = await fetch(`${API_BASE_URL}/upload-audio`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error('Failed to upload audio file');
    }

    return await response.json();
  }

  async getAvailableAudio(): Promise<any[]> {
    const response = await fetch(`${API_BASE_URL}/audio-list`);
    if (!response.ok) {
      throw new Error('Failed to get audio list');
    }
    return await response.json();
  }

  onMessage(callback: (message: ServerMessage) => void): void {
    this.onMessageCallback = callback;
  }

  onStatusChange(callback: (connected: boolean) => void): void {
    this.onStatusCallback = callback;
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
