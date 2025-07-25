import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Container,
  Typography,
  Box,
  Button,
  Card,
  CardContent,
  Grid,
  Chip,
  Alert,
  Switch,
  FormControlLabel,
  Slider,
  Select,
  MenuItem,
  FormControl,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Collapse,
  IconButton,
  Divider,
  InputLabel,
  CardHeader,
  List,
  ListItem,
  ListItemText
} from '@mui/material';
import {
  Bluetooth,
  CloudUpload,
  Settings,
  ShowChart,
  ExpandMore,
  ExpandLess,
  Add,
  DeviceHub,
  GraphicEq,
  Visibility,
  Timeline,
  PlayArrow,
  Stop
} from '@mui/icons-material';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';

// Configuration from environment variables
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';
const WS_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws';

interface AudioFile {
  id: string;
  name: string;
  type: string;
  frequency?: number;
}

interface ConnectedDevice {
  deviceId: string;
  deviceName: string;
  connected: boolean;
  distance: number;
  volume: number;
  audioFile?: AudioFile;
}

export default function ProfessionalSpatialAudioApp() {
  // State management
  const [backendConnected, setBackendConnected] = useState(false);
  const [connectedDevices, setConnectedDevices] = useState<ConnectedDevice[]>([]);
  const [hiddenDevices, setHiddenDevices] = useState<Set<string>>(new Set()); // Track hidden devices
  const [audioFiles, setAudioFiles] = useState<AudioFile[]>([]);
  const [audioEnabled, setAudioEnabled] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  
  // Collapsible sections state
  const [expandedSections, setExpandedSections] = useState({
    deviceManagement: true,
    deviceList: true,
    audioEffects: true,
    deviceStatus: true,
    distanceMonitoring: true,
    volumeMonitoring: true
  });

  // Demo mode
  const [demoMode, setDemoMode] = useState(false);
  const [demoDevice, setDemoDevice] = useState<ConnectedDevice | null>(null);
  const [demoInterval, setDemoInterval] = useState<NodeJS.Timeout | null>(null);
  
  // Audio effects settings
  const [masterVolume, setMasterVolume] = useState(70);
  
  // Distance-volume mapping settings
  const [volumeDecayType, setVolumeDecayType] = useState('linear');
  const [minDistance, setMinDistance] = useState(5);
  const [maxDistance, setMaxDistance] = useState(200);
  const [minVolume, setMinVolume] = useState(5);
  const [maxVolume, setMaxVolume] = useState(100);
  
  // Upload dialog
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [uploadName, setUploadName] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  // Real-time data for graphs
  const [distanceHistory, setDistanceHistory] = useState<{[deviceId: string]: number[]}>({});
  const [volumeHistory, setVolumeHistory] = useState<{[deviceId: string]: number[]}>({});
  const [deviceColors] = useState<{[deviceId: string]: string}>({});

  // WebSocket connection
  const ws = useRef<WebSocket | null>(null);

  // Generate unique colors for devices
  const generateDeviceColor = (deviceId: string): string => {
    const colors = [
      '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
      '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9'
    ];
    if (!deviceColors[deviceId]) {
      const colorIndex = Object.keys(deviceColors).length % colors.length;
      deviceColors[deviceId] = colors[colorIndex];
    }
    return deviceColors[deviceId];
  };

  // Transform data for Recharts - Distance
  const transformDistanceData = () => {
    const visibleDevices = getVisibleDevices();
    const relevantHistory = Object.fromEntries(
      Object.entries(distanceHistory).filter(([deviceId]) => 
        visibleDevices.some(device => device.deviceId === deviceId)
      )
    );
    
    const maxLength = Math.max(...Object.values(relevantHistory).map(arr => arr.length));
    if (maxLength === 0) return [];
    
    const data: Array<{timestamp: number, [key: string]: number | null}> = [];
    for (let i = 0; i < maxLength; i++) {
      const timestamp = Date.now() - (maxLength - i - 1) * 500; // 500ms intervals
      const dataPoint: {timestamp: number, [key: string]: number | null} = { timestamp };
      
      visibleDevices.forEach(device => {
        const history = distanceHistory[device.deviceId] || [];
        dataPoint[device.deviceId] = history[i] || null;
      });
      
      data.push(dataPoint);
    }
    return data;
  };

  // Transform data for Recharts - Volume  
  const transformVolumeData = () => {
    const visibleDevices = getVisibleDevices();
    const relevantHistory = Object.fromEntries(
      Object.entries(volumeHistory).filter(([deviceId]) => 
        visibleDevices.some(device => device.deviceId === deviceId)
      )
    );
    
    const maxLength = Math.max(...Object.values(relevantHistory).map(arr => arr.length));
    if (maxLength === 0) return [];
    
    const data: Array<{timestamp: number, [key: string]: number | null}> = [];
    for (let i = 0; i < maxLength; i++) {
      const timestamp = Date.now() - (maxLength - i - 1) * 500; // 500ms intervals
      const dataPoint: {timestamp: number, [key: string]: number | null} = { timestamp };
      
      visibleDevices.forEach(device => {
        const history = volumeHistory[device.deviceId] || [];
        dataPoint[device.deviceId] = history[i] || null;
      });
      
      data.push(dataPoint);
    }
    return data;
  };

  // Calculate volume based on distance and settings
  const calculateVolumeFromDistance = useCallback((distance: number): number => {
    if (distance <= minDistance) return maxVolume;
    if (distance >= maxDistance) return minVolume;
    
    const normalizedDistance = (distance - minDistance) / (maxDistance - minDistance);
    let volumeRatio;
    
    switch (volumeDecayType) {
      case 'exponential':
        volumeRatio = Math.exp(-3 * normalizedDistance);
        break;
      case 'logarithmic':
        volumeRatio = 1 - Math.log(1 + normalizedDistance * 9) / Math.log(10);
        break;
      case 'linear':
      default:
        volumeRatio = 1 - normalizedDistance;
        break;
    }
    
    return Math.round(minVolume + (maxVolume - minVolume) * volumeRatio);
  }, [minDistance, maxDistance, minVolume, maxVolume, volumeDecayType]);

  // Toggle collapsible sections
  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  // Demo device simulation
  const startDemoDevice = async () => {
    if (demoDevice || demoInterval) return;
    
    try {
      // Start demo on backend
      const response = await fetch(`${API_BASE_URL}/demo/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (response.ok) {
        const result = await response.json();
        console.log('Demo started on backend:', result);
        
        // Ensure audio files are loaded first
        if (audioFiles.length === 0) {
          loadAudioFiles();
        }
        
        // Get a default audio file (prefer 440Hz sine wave)
        const defaultAudio = audioFiles.find(f => f.id === 'sine-440') || audioFiles[0];
        
        const demo: ConnectedDevice = {
          deviceId: 'demo-triangle-wave', // Match backend device ID
          deviceName: 'Demo Triangle Wave Device',
          connected: true,
          distance: 100,
          volume: calculateVolumeFromDistance(100),
          audioFile: defaultAudio // Assign default audio file
        };
        
        setDemoDevice(demo);
        setConnectedDevices(prev => [...prev, demo]);
        generateDeviceColor('demo-triangle-wave');
        
        // Simulate changing distance from 0 to 175 and back
        let demoStartTime = Date.now();
        const interval = setInterval(async () => {
          // Create a smooth triangle wave from 0 to 175 and back over 30 seconds
          const elapsed = (Date.now() - demoStartTime) / 1000; // seconds
          const cycleDuration = 30; // 30 seconds for full cycle (0->175->0)
          const cyclePosition = (elapsed % cycleDuration) / cycleDuration; // 0 to 1
          
          let newDistance;
          if (cyclePosition <= 0.5) {
            // First half: 0 to 175
            newDistance = Math.round(cyclePosition * 2 * 175);
          } else {
            // Second half: 175 to 0
            newDistance = Math.round(175 - (cyclePosition - 0.5) * 2 * 175);
          }
          
          const newVolume = calculateVolumeFromDistance(newDistance);
          
          // Update backend with new distance
          try {
            await fetch(`${API_BASE_URL}/demo/update-distance`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({ distance: newDistance })
            });
          } catch (error) {
            console.error('Error updating demo distance:', error);
          }
          
          setConnectedDevices(prev => 
            prev.map(device => 
              device.deviceId === 'demo-triangle-wave' 
                ? { ...device, distance: newDistance, volume: newVolume }
                : device
            )
          );
          
          // Update histories
          setDistanceHistory(prev => ({
            ...prev,
            'demo-triangle-wave': [...(prev['demo-triangle-wave'] || []).slice(-19), newDistance]
          }));
          setVolumeHistory(prev => ({
            ...prev,
            'demo-triangle-wave': [...(prev['demo-triangle-wave'] || []).slice(-19), newVolume]
          }));
          
        }, 1000); // Update every second
        
        setDemoInterval(interval);
      } else {
        console.error('Failed to start demo:', await response.text());
      }
    } catch (error) {
      console.error('Error starting demo:', error);
    }
  };

  const stopDemoDevice = async () => {
    if (demoInterval) {
      clearInterval(demoInterval);
      setDemoInterval(null);
    }
    
    try {
      // Stop demo on backend
      await fetch(`${API_BASE_URL}/demo/stop`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });
    } catch (error) {
      console.error('Error stopping demo:', error);
    }
    
    setConnectedDevices(prev => prev.filter(d => d.deviceId !== 'demo-triangle-wave'));
    setDemoDevice(null);
    delete deviceColors['demo-triangle-wave'];
    
    // Properly update state for history
    setDistanceHistory(prev => {
      const newHistory = { ...prev };
      delete newHistory['demo-triangle-wave'];
      return newHistory;
    });
    
    setVolumeHistory(prev => {
      const newHistory = { ...prev };
      delete newHistory['demo-triangle-wave'];
      return newHistory;
    });
  };

  // Handle demo mode toggle
  const handleDemoToggle = () => {
    const newDemoMode = !demoMode;
    setDemoMode(newDemoMode);
    
    if (newDemoMode) {
      startDemoDevice();
    } else {
      stopDemoDevice();
    }
  };

  // Connect to backend
  const connectToBackend = useCallback(() => {
    // Close existing connection if any
    if (ws.current) {
      ws.current.close();
    }

    try {
      ws.current = new WebSocket(WS_URL);
      
      ws.current.onopen = () => {
        setBackendConnected(true);
        console.log('✅ Connected to backend');
      };
      
      ws.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'device_data') {
          const calculatedVolume = calculateVolumeFromDistance(data.distance);
          
          setConnectedDevices(prev => 
            prev.map(device => 
              device.deviceId === data.device_id 
                ? { ...device, distance: data.distance, volume: calculatedVolume }
                : device
            )
          );
          
          // Update histories for graphs
          setDistanceHistory(prev => ({
            ...prev,
            [data.device_id]: [...(prev[data.device_id] || []).slice(-19), data.distance]
          }));
          setVolumeHistory(prev => ({
            ...prev,
            [data.device_id]: [...(prev[data.device_id] || []).slice(-19), calculatedVolume]
          }));
        }
      };
      
      ws.current.onclose = () => {
        setBackendConnected(false);
        console.log('❌ Disconnected from backend');
      };

      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setBackendConnected(false);
      };
    } catch (error) {
      console.error('Failed to connect to backend:', error);
    }
  }, [calculateVolumeFromDistance]);

  // Cleanup WebSocket on unmount
  useEffect(() => {
    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, []);

  // Load audio files
  const loadAudioFiles = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/audio-list`);
      if (response.ok) {
        const files = await response.json();
        setAudioFiles(files);
      }
    } catch (error) {
      console.error('Failed to load audio files:', error);
    }
  }, []);

  // Handle device scan
  const handleScanDevices = () => {
    setIsScanning(true);
    // Simulate device discovery
    setTimeout(() => {
      const newDevice: ConnectedDevice = {
        deviceId: `device_${Date.now()}`,
        deviceName: `HC-05 Sensor ${connectedDevices.filter(d => d.deviceId !== 'demo-device').length + 1}`,
        connected: true,
        distance: 100,
        volume: calculateVolumeFromDistance(100)
      };
      setConnectedDevices(prev => [...prev, newDevice]);
      generateDeviceColor(newDevice.deviceId);
      setIsScanning(false);
    }, 2000);
  };

  // Handle audio toggle
  const handleAudioToggle = async () => {
    const newState = !audioEnabled;
    
    try {
      // Update backend audio settings
      const response = await fetch(`${API_BASE_URL}/audio/settings`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          enabled: newState,
          global_volume: 0.7,
          max_distance: maxDistance,
          min_distance: minDistance
        })
      });

      if (response.ok) {
        setAudioEnabled(newState);
        console.log(`🎵 Audio synthesis ${newState ? 'enabled' : 'disabled'}`);
      } else {
        console.error('Failed to update audio settings:', await response.text());
        alert('Failed to update audio settings. Please check the backend connection.');
      }
    } catch (error) {
      console.error('Error updating audio settings:', error);
      alert('Error connecting to backend. Please ensure the server is running.');
    }
  };



  // Handle device audio assignment
  const handleDeviceAudioChange = (deviceId: string, audioFileId: string) => {
    const audioFile = audioFiles.find(f => f.id === audioFileId);
    setConnectedDevices(prev =>
      prev.map(device =>
        device.deviceId === deviceId
          ? { ...device, audioFile }
          : device
      )
    );
  };

  // Disconnect device
  const disconnectDevice = (deviceId: string) => {
    setConnectedDevices(prev => prev.filter(d => d.deviceId !== deviceId));
  };

  // Hide/Show device functions
  const hideDevice = (deviceId: string) => {
    setHiddenDevices(prev => new Set(prev).add(deviceId));
  };

  const showDevice = (deviceId: string) => {
    setHiddenDevices(prev => {
      const newSet = new Set(prev);
      newSet.delete(deviceId);
      return newSet;
    });
  };

  // Get visible devices (not hidden)
  const getVisibleDevices = () => {
    return connectedDevices.filter(device => !hiddenDevices.has(device.deviceId));
  };

  // Handle file upload
  const handleFileUpload = async () => {
    if (!selectedFile || !uploadName.trim()) return;

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('name', uploadName);

    try {
      const response = await fetch(`${API_BASE_URL}/upload-audio`, {
        method: 'POST',
        body: formData
      });

      if (response.ok) {
        const newFile = await response.json();
        setAudioFiles(prev => [...prev, newFile]);
        setUploadDialogOpen(false);
        setSelectedFile(null);
        setUploadName('');
      }
    } catch (error) {
      console.error('Upload failed:', error);
    }
  };

  // Initialize
  useEffect(() => {
    connectToBackend();
    loadAudioFiles();
  }, [connectToBackend, loadAudioFiles]);

  return (
    <Box sx={{ 
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      py: 4
    }}>
      <Container maxWidth="xl">
        {/* Header */}
        <Box sx={{ mb: 4, textAlign: 'center' }}>
          <Typography 
            variant="h2" 
            component="h1" 
            gutterBottom 
            sx={{ 
              color: 'white',
              fontWeight: 700,
              fontSize: { xs: '2.5rem', md: '3.5rem' },
              fontFamily: "'Inter', 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif",
              textShadow: '0 4px 20px rgba(0,0,0,0.3)',
              mb: 2
            }}
          >
            Enhanced Spatial Audio System
          </Typography>
          <Typography 
            variant="h6" 
            sx={{ 
              color: 'rgba(255,255,255,0.9)',
              fontWeight: 400,
              fontSize: '1.1rem',
              fontFamily: "'Inter', sans-serif",
              mb: 3,
              maxWidth: '600px',
              mx: 'auto',
              lineHeight: 1.6
            }}
          >
            Real-time distance-responsive audio synthesis with HC-05 Bluetooth sensors
          </Typography>
        </Box>

        {/* Connection Status Alert */}
        {!backendConnected && (
          <Alert 
            severity="warning" 
            sx={{ 
              mb: 3, 
              borderRadius: 3,
              background: 'rgba(255,255,255,0.95)',
              backdropFilter: 'blur(10px)',
              border: '1px solid rgba(255,193,7,0.3)',
              fontFamily: "'Inter', sans-serif",
              fontWeight: 500,
              boxShadow: '0 8px 32px rgba(0,0,0,0.1)'
            }}
          >
            Backend connection lost. Please ensure the backend server is running on port 8001.
          </Alert>
        )}

        {/* Main Content - Split Layout */}
        <Grid container spacing={4}>
          {/* Left Panel - Controls & Settings */}
          <Grid item xs={12} md={6}>
            <Typography 
              variant="h4" 
              gutterBottom 
              sx={{ 
                mb: 3, 
                display: 'flex', 
                alignItems: 'center',
                color: 'white',
                fontWeight: 600,
                fontSize: '1.5rem',
                fontFamily: "'Inter', sans-serif",
                textShadow: '0 2px 10px rgba(0,0,0,0.3)'
              }}
            >
              <Settings sx={{ mr: 1.5, fontSize: '1.8rem' }} />
              Control Panel
            </Typography>

            {/* Segment 1: Device Management */}
            <Card sx={{ 
              mb: 3,
              background: 'rgba(255,255,255,0.95)',
              backdropFilter: 'blur(20px)',
              borderRadius: 4,
              border: '1px solid rgba(255,255,255,0.2)',
              boxShadow: '0 20px 40px rgba(0,0,0,0.1)',
              overflow: 'hidden',
              transition: 'all 0.3s ease',
              '&:hover': {
                transform: 'translateY(-2px)',
                boxShadow: '0 25px 50px rgba(0,0,0,0.15)'
              }
            }}>
              <CardHeader
                title={
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <DeviceHub sx={{ mr: 1.5, color: '#667eea', fontSize: '1.5rem' }} />
                    <Typography sx={{ 
                      fontFamily: "'Inter', sans-serif",
                      fontWeight: 600,
                      fontSize: '1.1rem',
                      color: '#2c3e50'
                    }}>
                      Device Management
                    </Typography>
                  </Box>
                }
                action={
                  <IconButton 
                    onClick={() => toggleSection('deviceManagement')}
                    sx={{ 
                      color: '#667eea',
                      '&:hover': { 
                        background: 'rgba(102, 126, 234, 0.1)',
                        transform: 'scale(1.1)' 
                      },
                      transition: 'all 0.2s ease'
                    }}
                  >
                    {expandedSections.deviceManagement ? <ExpandLess /> : <ExpandMore />}
                  </IconButton>
                }
                sx={{ pb: 1 }}
              />
              <Collapse in={expandedSections.deviceManagement}>
                <CardContent sx={{ pt: 0 }}>
                  {/* Demo Mode Toggle */}
                  <FormControlLabel
                    control={
                      <Switch
                        checked={demoMode}
                        onChange={handleDemoToggle}
                        sx={{
                          '& .MuiSwitch-switchBase.Mui-checked': {
                            color: '#667eea',
                          },
                          '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': {
                            backgroundColor: '#667eea',
                          },
                        }}
                      />
                    }
                    label={
                      <Typography sx={{ 
                        fontFamily: "'Inter', sans-serif",
                        fontWeight: 500,
                        color: '#2c3e50',
                        fontSize: '0.95rem'
                      }}>
                        Enable Demo Mode
                      </Typography>
                    }
                    sx={{ mb: 3, display: 'flex' }}
                  />
                  
                  {/* Add New Device Button */}
                  <Button 
                    variant="contained" 
                    onClick={handleScanDevices}
                    disabled={isScanning || !backendConnected}
                    startIcon={isScanning ? <Timeline sx={{ animation: 'spin 1s linear infinite' }} /> : <Add />}
                    fullWidth
                    sx={{ 
                      mb: 2,
                      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                      borderRadius: 3,
                      py: 1.5,
                      fontFamily: "'Inter', sans-serif",
                      fontWeight: 600,
                      fontSize: '0.95rem',
                      textTransform: 'none',
                      boxShadow: '0 8px 25px rgba(102, 126, 234, 0.3)',
                      '&:hover': {
                        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                        transform: 'translateY(-1px)',
                        boxShadow: '0 12px 30px rgba(102, 126, 234, 0.4)'
                      },
                      '&:disabled': {
                        background: 'rgba(102, 126, 234, 0.3)',
                        color: 'rgba(255,255,255,0.7)'
                      },
                      transition: 'all 0.3s ease'
                    }}
                  >
                    {isScanning ? 'Scanning for Devices...' : '📡 Add New HC-05 Device'}
                  </Button>
                  
                  {connectedDevices.length > 0 && (
                    <Alert 
                      severity="success" 
                      sx={{ 
                        borderRadius: 3,
                        background: 'rgba(76, 175, 80, 0.1)',
                        border: '1px solid rgba(76, 175, 80, 0.3)',
                        fontFamily: "'Inter', sans-serif",
                        fontWeight: 500,
                        '& .MuiAlert-icon': {
                          color: '#4caf50'
                        }
                      }}
                    >
                      Active devices: {connectedDevices.length}
                      {demoMode && ' (including demo)'}
                    </Alert>
                  )}
                </CardContent>
              </Collapse>
            </Card>

            {/* Segment 2: Connected Devices List */}
            <Card sx={{ 
              mb: 3,
              background: 'rgba(255,255,255,0.95)',
              backdropFilter: 'blur(20px)',
              borderRadius: 4,
              border: '1px solid rgba(255,255,255,0.2)',
              boxShadow: '0 20px 40px rgba(0,0,0,0.1)',
              overflow: 'hidden',
              transition: 'all 0.3s ease',
              '&:hover': {
                transform: 'translateY(-2px)',
                boxShadow: '0 25px 50px rgba(0,0,0,0.15)'
              }
            }}>
              <CardHeader
                title={
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Bluetooth sx={{ mr: 1.5, color: '#667eea', fontSize: '1.5rem' }} />
                    <Typography sx={{ 
                      fontFamily: "'Inter', sans-serif",
                      fontWeight: 600,
                      fontSize: '1.1rem',
                      color: '#2c3e50'
                    }}>
                      Connected Devices ({connectedDevices.length})
                    </Typography>
                  </Box>
                }
                action={
                  <IconButton 
                    onClick={() => toggleSection('deviceList')}
                    sx={{ 
                      color: '#667eea',
                      '&:hover': { 
                        background: 'rgba(102, 126, 234, 0.1)',
                        transform: 'scale(1.1)' 
                      },
                      transition: 'all 0.2s ease'
                    }}
                  >
                    {expandedSections.deviceList ? <ExpandLess /> : <ExpandMore />}
                  </IconButton>
                }
                sx={{ pb: 1 }}
              />
              <Collapse in={expandedSections.deviceList}>
                <CardContent sx={{ pt: 0 }}>
                  {connectedDevices.length === 0 ? (
                    <Alert 
                      severity="info" 
                      sx={{ 
                        borderRadius: 2,
                        fontFamily: "'Inter', sans-serif"
                      }}
                    >
                      No devices connected. Add a device or enable demo mode to get started.
                    </Alert>
                  ) : (
                    <List sx={{ p: 0 }}>
                      {connectedDevices.map((device, index) => (
                        <Box key={device.deviceId}>
                          <ListItem sx={{ px: 0 }}>
                            <Box sx={{ width: '100%' }}>
                              {/* Device Info */}
                              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                                <Typography 
                                  variant="body1" 
                                  sx={{ 
                                    fontWeight: 600, 
                                    display: 'flex', 
                                    alignItems: 'center',
                                    fontFamily: "'Inter', sans-serif",
                                    color: '#2c3e50'
                                  }}
                                >
                                  <Box 
                                    sx={{ 
                                      width: 12, 
                                      height: 12, 
                                      borderRadius: '50%', 
                                      bgcolor: generateDeviceColor(device.deviceId),
                                      mr: 1 
                                    }} 
                                  />
                                  {device.deviceName}
                                </Typography>
                                <Chip 
                                  label="Connected" 
                                  color="success" 
                                  size="small"
                                  variant="outlined"
                                  sx={{ fontFamily: "'Inter', sans-serif" }}
                                />
                              </Box>
                              
                              {/* Audio Assignment */}
                              <FormControl fullWidth size="small" sx={{ mb: 1 }}>
                                <InputLabel sx={{ fontFamily: "'Inter', sans-serif" }}>Assign Audio</InputLabel>
                                <Select
                                  value={device.audioFile?.id || ''}
                                  onChange={(e) => handleDeviceAudioChange(device.deviceId, e.target.value)}
                                  label="Assign Audio"
                                  sx={{ fontFamily: "'Inter', sans-serif" }}
                                >
                                  <MenuItem value="" sx={{ fontFamily: "'Inter', sans-serif" }}>
                                    <em>No Audio</em>
                                  </MenuItem>
                                  {audioFiles.map((file) => (
                                    <MenuItem 
                                      key={file.id} 
                                      value={file.id}
                                      sx={{ fontFamily: "'Inter', sans-serif" }}
                                    >
                                      {file.name}
                                    </MenuItem>
                                  ))}
                                </Select>
                              </FormControl>
                              
                              {/* Quick Stats */}
                              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <Typography 
                                  variant="caption" 
                                  color="text.secondary"
                                  sx={{ fontFamily: "'Inter', sans-serif" }}
                                >
                                  Distance: {device.distance}cm | Volume: {device.volume}%
                                </Typography>
                                <Box sx={{ display: 'flex', gap: 1 }}>
                                  <Button
                                    variant="outlined"
                                    size="small"
                                    onClick={() => hiddenDevices.has(device.deviceId) ? showDevice(device.deviceId) : hideDevice(device.deviceId)}
                                    color={hiddenDevices.has(device.deviceId) ? "warning" : "secondary"}
                                    sx={{ 
                                      minWidth: 'auto', 
                                      px: 1,
                                      fontFamily: "'Inter', sans-serif"
                                    }}
                                    title={hiddenDevices.has(device.deviceId) ? "Show in simulation" : "Hide from simulation"}
                                  >
                                    {hiddenDevices.has(device.deviceId) ? '👁️‍🗨️' : '👁️'}
                                  </Button>
                                  <Button
                                    variant="outlined"
                                    size="small"
                                    onClick={() => disconnectDevice(device.deviceId)}
                                    color="error"
                                    sx={{ 
                                      minWidth: 'auto', 
                                      px: 1,
                                      fontFamily: "'Inter', sans-serif"
                                    }}
                                  >
                                    🗑️
                                  </Button>
                                </Box>
                              </Box>
                            </Box>
                          </ListItem>
                          {index < connectedDevices.length - 1 && <Divider />}
                        </Box>
                      ))}
                    </List>
                  )}
                </CardContent>
              </Collapse>
            </Card>

            {/* Segment 3: Audio Effects */}
            <Card sx={{ 
              mb: 3,
              background: 'rgba(255,255,255,0.95)',
              backdropFilter: 'blur(20px)',
              borderRadius: 4,
              border: '1px solid rgba(255,255,255,0.2)',
              boxShadow: '0 20px 40px rgba(0,0,0,0.1)',
              overflow: 'hidden',
              transition: 'all 0.3s ease',
              '&:hover': {
                transform: 'translateY(-2px)',
                boxShadow: '0 25px 50px rgba(0,0,0,0.15)'
              }
            }}>
              <CardHeader
                title={
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <GraphicEq sx={{ mr: 1.5, color: '#667eea', fontSize: '1.5rem' }} />
                    <Typography sx={{ 
                      fontFamily: "'Inter', sans-serif",
                      fontWeight: 600,
                      fontSize: '1.1rem',
                      color: '#2c3e50'
                    }}>
                      Audio Effects & Distance Mapping
                    </Typography>
                  </Box>
                }
                action={
                  <IconButton 
                    onClick={() => toggleSection('audioEffects')}
                    sx={{ 
                      color: '#667eea',
                      '&:hover': { 
                        background: 'rgba(102, 126, 234, 0.1)',
                        transform: 'scale(1.1)' 
                      },
                      transition: 'all 0.2s ease'
                    }}
                  >
                    {expandedSections.audioEffects ? <ExpandLess /> : <ExpandMore />}
                  </IconButton>
                }
                sx={{ pb: 1 }}
              />
              <Collapse in={expandedSections.audioEffects}>
                <CardContent sx={{ pt: 0 }}>
                  {/* Audio Enable Toggle */}
                  <FormControlLabel
                    control={
                      <Switch
                        checked={audioEnabled}
                        onChange={handleAudioToggle}
                        color="primary"
                      />
                    }
                    label={
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        {audioEnabled ? <PlayArrow sx={{ mr: 0.5 }} /> : <Stop sx={{ mr: 0.5 }} />}
                        <Typography sx={{ fontFamily: "'Inter', sans-serif", color: '#2c3e50' }}>
                          Enable Audio Synthesis
                        </Typography>
                      </Box>
                    }
                    sx={{ mb: 3, display: 'flex' }}
                  />

                  {/* Master Volume */}
                  <Box sx={{ mb: 3 }}>
                    <Typography 
                      gutterBottom 
                      sx={{ fontFamily: "'Inter', sans-serif", color: '#2c3e50' }}
                    >
                      Master Volume: {masterVolume}%
                    </Typography>
                    <Slider
                      value={masterVolume}
                      onChange={(e, val) => setMasterVolume(val as number)}
                      min={0}
                      max={100}
                      step={1}
                      valueLabelDisplay="auto"
                      sx={{ '& .MuiSlider-thumb': { color: '#667eea' }, '& .MuiSlider-track': { color: '#667eea' } }}
                    />
                  </Box>

                  <Divider sx={{ my: 3 }} />

                  {/* Distance-Volume Mapping */}
                  <Typography 
                    variant="h6" 
                    gutterBottom 
                    sx={{ 
                      color: '#667eea', 
                      fontWeight: 600,
                      fontFamily: "'Inter', sans-serif"
                    }}
                  >
                    Distance-Volume Mapping
                  </Typography>

                  {/* Volume Decay Type */}
                  <FormControl fullWidth sx={{ mb: 3 }}>
                    <InputLabel sx={{ fontFamily: "'Inter', sans-serif" }}>Volume Decay Type</InputLabel>
                    <Select
                      value={volumeDecayType}
                      onChange={(e) => setVolumeDecayType(e.target.value)}
                      label="Volume Decay Type"
                      sx={{ fontFamily: "'Inter', sans-serif" }}
                    >
                      <MenuItem value="linear" sx={{ fontFamily: "'Inter', sans-serif" }}>Linear Decay</MenuItem>
                      <MenuItem value="exponential" sx={{ fontFamily: "'Inter', sans-serif" }}>Exponential Decay</MenuItem>
                      <MenuItem value="logarithmic" sx={{ fontFamily: "'Inter', sans-serif" }}>Logarithmic Decay</MenuItem>
                    </Select>
                  </FormControl>

                  {/* Distance Range */}
                  <Grid container spacing={2} sx={{ mb: 3 }}>
                    <Grid item xs={6}>
                      <TextField
                        fullWidth
                        label="Min Distance (cm)"
                        type="number"
                        value={minDistance}
                        onChange={(e) => setMinDistance(Number(e.target.value))}
                        inputProps={{ min: 1, max: 500 }}
                        sx={{ 
                          '& .MuiInputLabel-root': { fontFamily: "'Inter', sans-serif" },
                          '& .MuiInputBase-input': { fontFamily: "'Inter', sans-serif" }
                        }}
                      />
                    </Grid>
                    <Grid item xs={6}>
                      <TextField
                        fullWidth
                        label="Max Distance (cm)"
                        type="number"
                        value={maxDistance}
                        onChange={(e) => setMaxDistance(Number(e.target.value))}
                        inputProps={{ min: 10, max: 1000 }}
                        sx={{ 
                          '& .MuiInputLabel-root': { fontFamily: "'Inter', sans-serif" },
                          '& .MuiInputBase-input': { fontFamily: "'Inter', sans-serif" }
                        }}
                      />
                    </Grid>
                  </Grid>

                  {/* Volume Range */}
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <TextField
                        fullWidth
                        label="Min Volume (%)"
                        type="number"
                        value={minVolume}
                        onChange={(e) => setMinVolume(Number(e.target.value))}
                        inputProps={{ min: 0, max: 100 }}
                        sx={{ 
                          '& .MuiInputLabel-root': { fontFamily: "'Inter', sans-serif" },
                          '& .MuiInputBase-input': { fontFamily: "'Inter', sans-serif" }
                        }}
                      />
                    </Grid>
                    <Grid item xs={6}>
                      <TextField
                        fullWidth
                        label="Max Volume (%)"
                        type="number"
                        value={maxVolume}
                        onChange={(e) => setMaxVolume(Number(e.target.value))}
                        inputProps={{ min: 0, max: 100 }}
                        sx={{ 
                          '& .MuiInputLabel-root': { fontFamily: "'Inter', sans-serif" },
                          '& .MuiInputBase-input': { fontFamily: "'Inter', sans-serif" }
                        }}
                      />
                    </Grid>
                  </Grid>
                </CardContent>
              </Collapse>
            </Card>
          </Grid>

          {/* Right Panel - Monitoring & Live Data */}
          <Grid item xs={12} md={6}>
            <Typography 
              variant="h4" 
              gutterBottom 
              sx={{ 
                mb: 3, 
                display: 'flex', 
                alignItems: 'center',
                color: 'white',
                fontWeight: 600,
                fontSize: '1.5rem',
                fontFamily: "'Inter', sans-serif",
                textShadow: '0 2px 10px rgba(0,0,0,0.3)'
              }}
            >
              <ShowChart sx={{ mr: 1.5, fontSize: '1.8rem' }} />
              Live Monitoring
            </Typography>

            {/* Segment 1: Device Status List */}
            <Card sx={{ 
              mb: 3,
              background: 'rgba(255,255,255,0.95)',
              backdropFilter: 'blur(20px)',
              borderRadius: 4,
              border: '1px solid rgba(255,255,255,0.2)',
              boxShadow: '0 20px 40px rgba(0,0,0,0.1)',
              overflow: 'hidden',
              transition: 'all 0.3s ease',
              '&:hover': {
                transform: 'translateY(-2px)',
                boxShadow: '0 25px 50px rgba(0,0,0,0.15)'
              }
            }}>
              <CardHeader
                title={
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Visibility sx={{ mr: 1.5, color: '#667eea', fontSize: '1.5rem' }} />
                    <Typography sx={{ 
                      fontFamily: "'Inter', sans-serif",
                      fontWeight: 600,
                      fontSize: '1.1rem',
                      color: '#2c3e50'
                    }}>
                      Device Status
                    </Typography>
                  </Box>
                }
                action={
                  <IconButton 
                    onClick={() => toggleSection('deviceStatus')}
                    sx={{ 
                      color: '#667eea',
                      '&:hover': { 
                        background: 'rgba(102, 126, 234, 0.1)',
                        transform: 'scale(1.1)' 
                      },
                      transition: 'all 0.2s ease'
                    }}
                  >
                    {expandedSections.deviceStatus ? <ExpandLess /> : <ExpandMore />}
                  </IconButton>
                }
                sx={{ pb: 1 }}
              />
              <Collapse in={expandedSections.deviceStatus}>
                <CardContent sx={{ pt: 0 }}>
                  {getVisibleDevices().length === 0 ? (
                    <Alert 
                      severity="info" 
                      sx={{ 
                        borderRadius: 2,
                        fontFamily: "'Inter', sans-serif"
                      }}
                    >
                      No visible devices to monitor. Connect devices or show hidden devices to see live data.
                    </Alert>
                  ) : (
                    <List sx={{ p: 0 }}>
                      {getVisibleDevices().map((device, index) => (
                        <Box key={device.deviceId}>
                          <ListItem sx={{ px: 0, py: 1 }}>
                            <ListItemText
                              primary={
                                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                                  <Box 
                                    sx={{ 
                                      width: 8, 
                                      height: 8, 
                                      borderRadius: '50%', 
                                      bgcolor: generateDeviceColor(device.deviceId),
                                      mr: 1 
                                    }} 
                                  />
                                  <Typography 
                                    variant="body2" 
                                    sx={{ 
                                      fontWeight: 600,
                                      fontFamily: "'Inter', sans-serif",
                                      color: '#2c3e50'
                                    }}
                                  >
                                    {device.deviceName}
                                  </Typography>
                                </Box>
                              }
                              secondary={
                                <Grid container spacing={2}>
                                  <Grid item xs={6}>
                                    <Typography 
                                      variant="h5" 
                                      color="primary" 
                                      sx={{ 
                                        fontFamily: "'Inter', 'monospace'",
                                        fontWeight: 600
                                      }}
                                    >
                                      {device.distance}cm
                                    </Typography>
                                    <Typography 
                                      variant="caption" 
                                      color="text.secondary"
                                      sx={{ fontFamily: "'Inter', sans-serif" }}
                                    >
                                      Distance
                                    </Typography>
                                  </Grid>
                                  <Grid item xs={6}>
                                    <Typography 
                                      variant="h5" 
                                      color="secondary" 
                                      sx={{ 
                                        fontFamily: "'Inter', 'monospace'",
                                        fontWeight: 600
                                      }}
                                    >
                                      {device.volume}%
                                    </Typography>
                                    <Typography 
                                      variant="caption" 
                                      color="text.secondary"
                                      sx={{ fontFamily: "'Inter', sans-serif" }}
                                    >
                                      Volume
                                    </Typography>
                                  </Grid>
                                </Grid>
                              }
                            />
                          </ListItem>
                          {index < getVisibleDevices().length - 1 && <Divider />}
                        </Box>
                      ))}
                    </List>
                  )}
                </CardContent>
              </Collapse>
            </Card>

            {/* Segment 2: Distance Monitoring Graph */}
            <Card sx={{ 
              mb: 3,
              background: 'rgba(255,255,255,0.95)',
              backdropFilter: 'blur(20px)',
              borderRadius: 4,
              border: '1px solid rgba(255,255,255,0.2)',
              boxShadow: '0 20px 40px rgba(0,0,0,0.1)',
              overflow: 'hidden',
              transition: 'all 0.3s ease',
              '&:hover': {
                transform: 'translateY(-2px)',
                boxShadow: '0 25px 50px rgba(0,0,0,0.15)'
              }
            }}>
              <CardHeader
                title={
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Timeline sx={{ mr: 1.5, color: '#667eea', fontSize: '1.5rem' }} />
                    <Typography sx={{ 
                      fontFamily: "'Inter', sans-serif",
                      fontWeight: 600,
                      fontSize: '1.1rem',
                      color: '#2c3e50'
                    }}>
                      Distance Monitoring
                    </Typography>
                  </Box>
                }
                action={
                  <IconButton 
                    onClick={() => toggleSection('distanceMonitoring')}
                    sx={{ 
                      color: '#667eea',
                      '&:hover': { 
                        background: 'rgba(102, 126, 234, 0.1)',
                        transform: 'scale(1.1)' 
                      },
                      transition: 'all 0.2s ease'
                    }}
                  >
                    {expandedSections.distanceMonitoring ? <ExpandLess /> : <ExpandMore />}
                  </IconButton>
                }
                sx={{ pb: 1 }}
              />
              <Collapse in={expandedSections.distanceMonitoring}>
                <CardContent sx={{ pt: 0 }}>
                  {getVisibleDevices().length === 0 ? (
                    <Alert 
                      severity="info" 
                      sx={{ 
                        borderRadius: 2,
                        fontFamily: "'Inter', sans-serif"
                      }}
                    >
                      No visible devices. Distance data will appear here once visible devices are connected.
                    </Alert>
                  ) : (
                    <Box sx={{ position: 'relative', border: '2px solid #e2e8f0', borderRadius: 2, p: 2 }}>
                      {/* Device legends */}
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                        {getVisibleDevices().map((device) => (
                          <Chip
                            key={device.deviceId}
                            label={device.deviceName}
                            size="small"
                            sx={{ 
                              bgcolor: generateDeviceColor(device.deviceId),
                              color: 'white',
                              fontSize: '10px',
                              fontFamily: "'Inter', sans-serif"
                            }}
                          />
                        ))}
                      </Box>
                      
                      {/* Real-time Distance Chart */}
                      <Box sx={{ height: 300, mt: 2 }}>
                        {getVisibleDevices().length === 0 ? (
                          <Alert 
                            severity="info" 
                            sx={{ 
                              borderRadius: 2,
                              fontFamily: "'Inter', sans-serif"
                            }}
                          >
                            No devices connected. Distance data will appear here once devices are connected.
                          </Alert>
                        ) : Object.keys(distanceHistory).length === 0 ? (
                          <Box sx={{ 
                            height: '100%',
                            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                            borderRadius: 2, 
                            display: 'flex', 
                            alignItems: 'center', 
                            justifyContent: 'center',
                            color: 'white'
                          }}>
                            <Typography 
                              variant="body1" 
                              sx={{ 
                                fontFamily: "'Inter', sans-serif",
                                textShadow: '0 0 10px rgba(0,0,0,0.5)'
                              }}
                            >
                              Waiting for distance data...
                            </Typography>
                          </Box>
                        ) : (
                          <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={transformDistanceData()}>
                              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.2)" />
                              <XAxis 
                                dataKey="timestamp" 
                                type="number"
                                scale="time"
                                domain={['dataMin', 'dataMax']}
                                tickFormatter={(value) => new Date(value).toLocaleTimeString()}
                                stroke="#666"
                                fontSize={12}
                              />
                              <YAxis 
                                domain={[0, 300]}
                                label={{ value: 'Distance (cm)', angle: -90, position: 'insideLeft' }}
                                stroke="#666"
                                fontSize={12}
                              />
                              <Tooltip 
                                labelFormatter={(value) => `Time: ${new Date(value).toLocaleTimeString()}`}
                                contentStyle={{
                                  backgroundColor: 'rgba(255,255,255,0.95)',
                                  border: '1px solid #ddd',
                                  borderRadius: '8px',
                                  boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
                                }}
                              />
                              {getVisibleDevices().map((device) => (
                                <Line 
                                  key={device.deviceId}
                                  type="monotone" 
                                  dataKey={device.deviceId} 
                                  stroke={generateDeviceColor(device.deviceId)}
                                  strokeWidth={2}
                                  dot={false}
                                  connectNulls={false}
                                  name={device.deviceName}
                                />
                              ))}
                            </LineChart>
                          </ResponsiveContainer>
                        )}
                      </Box>
                    </Box>
                  )}
                </CardContent>
              </Collapse>
            </Card>

            {/* Segment 3: Volume Monitoring Graph */}
            <Card sx={{ 
              mb: 3,
              background: 'rgba(255,255,255,0.95)',
              backdropFilter: 'blur(20px)',
              borderRadius: 4,
              border: '1px solid rgba(255,255,255,0.2)',
              boxShadow: '0 20px 40px rgba(0,0,0,0.1)',
              overflow: 'hidden',
              transition: 'all 0.3s ease',
              '&:hover': {
                transform: 'translateY(-2px)',
                boxShadow: '0 25px 50px rgba(0,0,0,0.15)'
              }
            }}>
              <CardHeader
                title={
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <GraphicEq sx={{ mr: 1.5, color: '#667eea', fontSize: '1.5rem' }} />
                    <Typography sx={{ 
                      fontFamily: "'Inter', sans-serif",
                      fontWeight: 600,
                      fontSize: '1.1rem',
                      color: '#2c3e50'
                    }}>
                      Volume Monitoring
                    </Typography>
                  </Box>
                }
                action={
                  <IconButton 
                    onClick={() => toggleSection('volumeMonitoring')}
                    sx={{ 
                      color: '#667eea',
                      '&:hover': { 
                        background: 'rgba(102, 126, 234, 0.1)',
                        transform: 'scale(1.1)' 
                      },
                      transition: 'all 0.2s ease'
                    }}
                  >
                    {expandedSections.volumeMonitoring ? <ExpandLess /> : <ExpandMore />}
                  </IconButton>
                }
                sx={{ pb: 1 }}
              />
              <Collapse in={expandedSections.volumeMonitoring}>
                <CardContent sx={{ pt: 0 }}>
                  {getVisibleDevices().length === 0 ? (
                    <Alert 
                      severity="info" 
                      sx={{ 
                        borderRadius: 2,
                        fontFamily: "'Inter', sans-serif"
                      }}
                    >
                      No visible devices. Volume data will appear here once visible devices are connected.
                    </Alert>
                  ) : (
                    <Box sx={{ position: 'relative', border: '2px solid #e2e8f0', borderRadius: 2, p: 2 }}>
                      {/* Device status indicators */}
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                        {getVisibleDevices().map((device) => (
                          <Chip
                            key={device.deviceId}
                            label={`${device.deviceName}: ${device.volume}%`}
                            size="small"
                            sx={{ 
                              bgcolor: generateDeviceColor(device.deviceId),
                              color: 'white',
                              fontSize: '10px',
                              fontFamily: "'Inter', sans-serif"
                            }}
                          />
                        ))}
                      </Box>
                      
                      {/* Real-time Volume Chart */}
                      <Box sx={{ height: 280, mt: 2 }}>
                        {Object.keys(volumeHistory).length === 0 ? (
                          <Box sx={{ 
                            height: '100%',
                            background: 'linear-gradient(135deg, #ff9a9e 0%, #fecfef 50%, #fecfef 100%)',
                            borderRadius: 2, 
                            display: 'flex', 
                            alignItems: 'center', 
                            justifyContent: 'center'
                          }}>
                            <Typography 
                              variant="body2" 
                              color="rgba(0,0,0,0.7)"
                              sx={{ 
                                fontFamily: "'Inter', sans-serif",
                                textShadow: '0 0 5px rgba(255,255,255,0.8)'
                              }}
                            >
                              Waiting for volume data...
                            </Typography>
                          </Box>
                        ) : (
                          <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={transformVolumeData()}>
                              <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.1)" />
                              <XAxis 
                                dataKey="timestamp" 
                                type="number"
                                scale="time"
                                domain={['dataMin', 'dataMax']}
                                tickFormatter={(value) => new Date(value).toLocaleTimeString()}
                                stroke="#666"
                                fontSize={12}
                              />
                              <YAxis 
                                domain={[0, 100]}
                                label={{ value: 'Volume (%)', angle: -90, position: 'insideLeft' }}
                                stroke="#666"
                                fontSize={12}
                              />
                              <Tooltip 
                                labelFormatter={(value) => `Time: ${new Date(value).toLocaleTimeString()}`}
                                contentStyle={{
                                  backgroundColor: 'rgba(255,255,255,0.95)',
                                  border: '1px solid #ddd',
                                  borderRadius: '8px',
                                  boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
                                }}
                              />
                              {getVisibleDevices().map((device, index) => (
                                <Area 
                                  key={device.deviceId}
                                  type="monotone" 
                                  dataKey={device.deviceId} 
                                  stackId={index}
                                  stroke={generateDeviceColor(device.deviceId)}
                                  fill={generateDeviceColor(device.deviceId)}
                                  fillOpacity={0.6}
                                  strokeWidth={2}
                                  connectNulls={false}
                                  name={device.deviceName}
                                />
                              ))}
                            </AreaChart>
                          </ResponsiveContainer>
                        )}
                      </Box>
                    </Box>
                  )}
                </CardContent>
              </Collapse>
            </Card>

            {/* System Status */}
            <Card sx={{ 
              mb: 3,
              background: 'rgba(255,255,255,0.95)',
              backdropFilter: 'blur(20px)',
              borderRadius: 4,
              border: '1px solid rgba(255,255,255,0.2)',
              boxShadow: '0 20px 40px rgba(0,0,0,0.1)',
              overflow: 'hidden',
              transition: 'all 0.3s ease',
              '&:hover': {
                transform: 'translateY(-2px)',
                boxShadow: '0 25px 50px rgba(0,0,0,0.15)'
              }
            }}>
              <CardContent>
                <Typography 
                  variant="h6" 
                  gutterBottom
                  sx={{ 
                    fontFamily: "'Inter', sans-serif",
                    fontWeight: 600,
                    color: '#2c3e50'
                  }}
                >
                  System Status
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <Box display="flex" alignItems="center" justifyContent="space-between">
                      <Typography 
                        variant="body2"
                        sx={{ fontFamily: "'Inter', sans-serif", color: '#2c3e50' }}
                      >
                        Backend:
                      </Typography>
                      <Chip 
                        label={backendConnected ? 'Connected' : 'Disconnected'}
                        color={backendConnected ? 'success' : 'error'}
                        size="small"
                        sx={{ fontFamily: "'Inter', sans-serif" }}
                      />
                    </Box>
                  </Grid>
                  <Grid item xs={6}>
                    <Box display="flex" alignItems="center" justifyContent="space-between">
                      <Typography 
                        variant="body2"
                        sx={{ fontFamily: "'Inter', sans-serif", color: '#2c3e50' }}
                      >
                        Audio:
                      </Typography>
                      <Chip 
                        label={audioEnabled ? 'Playing' : 'Stopped'}
                        color={audioEnabled ? 'success' : 'default'}
                        size="small"
                        sx={{ fontFamily: "'Inter', sans-serif" }}
                      />
                    </Box>
                  </Grid>
                  <Grid item xs={6}>
                    <Box display="flex" alignItems="center" justifyContent="space-between">
                      <Typography 
                        variant="body2"
                        sx={{ fontFamily: "'Inter', sans-serif", color: '#2c3e50' }}
                      >
                        Demo Mode:
                      </Typography>
                      <Chip 
                        label={demoMode ? 'Active' : 'Inactive'}
                        color={demoMode ? 'secondary' : 'default'}
                        size="small"
                        sx={{ fontFamily: "'Inter', sans-serif" }}
                      />
                    </Box>
                  </Grid>
                  <Grid item xs={6}>
                    <Box display="flex" alignItems="center" justifyContent="space-between">
                      <Typography 
                        variant="body2"
                        sx={{ fontFamily: "'Inter', sans-serif", color: '#2c3e50' }}
                      >
                        Devices:
                      </Typography>
                      <Chip 
                        label={connectedDevices.length.toString()}
                        color={connectedDevices.length > 0 ? 'success' : 'default'}
                        size="small"
                        sx={{ fontFamily: "'Inter', sans-serif" }}
                      />
                    </Box>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Audio Upload Section */}
        <Box sx={{ 
          mt: 4, 
          p: 4, 
          background: 'rgba(255,255,255,0.95)', 
          borderRadius: 4,
          border: '1px solid rgba(255,255,255,0.2)',
          backdropFilter: 'blur(20px)',
          boxShadow: '0 20px 40px rgba(0,0,0,0.1)',
          textAlign: 'center' 
        }}>
          <Typography 
            variant="h5" 
            gutterBottom
            sx={{ 
              fontFamily: "'Inter', sans-serif",
              fontWeight: 600,
              color: '#2c3e50',
              mb: 2
            }}
          >
            Audio Management
          </Typography>
          <Typography 
            variant="body1" 
            sx={{ 
              fontFamily: "'Inter', sans-serif",
              color: '#666',
              mb: 3,
              maxWidth: '500px',
              mx: 'auto'
            }}
          >
            Audio upload and editing features will be available on a separate dedicated page. 
            For now, use the quick upload below for testing.
          </Typography>
          <Button
            variant="contained"
            startIcon={<CloudUpload />}
            onClick={() => setUploadDialogOpen(true)}
            sx={{ 
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              borderRadius: 3,
              px: 4,
              py: 1.5,
              fontFamily: "'Inter', sans-serif",
              fontWeight: 600,
              textTransform: 'none',
              boxShadow: '0 8px 25px rgba(102, 126, 234, 0.3)',
              '&:hover': {
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                transform: 'translateY(-1px)',
                boxShadow: '0 12px 30px rgba(102, 126, 234, 0.4)'
              },
              transition: 'all 0.3s ease'
            }}
          >
            Quick Upload Audio
          </Button>
        </Box>

        {/* Upload Dialog */}
        <Dialog 
          open={uploadDialogOpen} 
          onClose={() => setUploadDialogOpen(false)}
          maxWidth="sm" 
          fullWidth
          PaperProps={{ 
            sx: { 
              borderRadius: 4,
              background: 'rgba(255,255,255,0.98)',
              backdropFilter: 'blur(20px)',
              boxShadow: '0 25px 50px rgba(0,0,0,0.2)'
            } 
          }}
        >
          <DialogTitle sx={{ pb: 1 }}>
            <Typography 
              variant="h5" 
              sx={{ 
                fontWeight: 600, 
                color: '#2c3e50',
                fontFamily: "'Inter', sans-serif"
              }}
            >
              📤 Quick Audio Upload
            </Typography>
          </DialogTitle>
          <DialogContent sx={{ pt: 2 }}>
            <Alert 
              severity="info" 
              sx={{ 
                mb: 3, 
                borderRadius: 2,
                fontFamily: "'Inter', sans-serif"
              }}
            >
              This feature will be moved to a dedicated Audio Management page.
            </Alert>
            
            <TextField
              autoFocus
              margin="dense"
              label="Audio File Name"
              fullWidth
              variant="outlined"
              value={uploadName}
              onChange={(e) => setUploadName(e.target.value)}
              sx={{ 
                mb: 3,
                '& .MuiOutlinedInput-root': {
                  borderRadius: 2,
                  fontFamily: "'Inter', sans-serif"
                },
                '& .MuiInputLabel-root': { fontFamily: "'Inter', sans-serif" }
              }}
              placeholder="Enter a descriptive name for your audio"
            />
            
            <Box
              sx={{
                border: '2px dashed #bdc3c7',
                borderRadius: 3,
                p: 4,
                textAlign: 'center',
                cursor: 'pointer',
                transition: 'all 0.3s ease',
                background: '#fafafa',
                '&:hover': {
                  borderColor: '#667eea',
                  bgcolor: 'rgba(102, 126, 234, 0.02)',
                  transform: 'translateY(-2px)'
                }
              }}
              component="label"
            >
              <input
                type="file"
                hidden
                accept="audio/*"
                onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
              />
              <CloudUpload sx={{ fontSize: 56, color: '#bdc3c7', mb: 2 }} />
              <Typography 
                variant="h6" 
                sx={{ 
                  mb: 1, 
                  color: '#7f8c8d',
                  fontFamily: "'Inter', sans-serif",
                  fontWeight: 500
                }}
              >
                {selectedFile ? selectedFile.name : 'Click to select audio file'}
              </Typography>
              <Typography 
                variant="body2" 
                sx={{ 
                  color: '#95a5a6',
                  fontFamily: "'Inter', sans-serif"
                }}
              >
                Supports MP3, WAV, OGG, MP4, M4A files
              </Typography>
            </Box>
            
            {selectedFile && (
              <Alert 
                severity="success" 
                sx={{ 
                  mt: 3, 
                  borderRadius: 2,
                  fontFamily: "'Inter', sans-serif"
                }}
              >
                File selected: {selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
              </Alert>
            )}
          </DialogContent>
          <DialogActions sx={{ p: 3, pt: 1 }}>
            <Button 
              onClick={() => {
                setUploadDialogOpen(false);
                setSelectedFile(null);
                setUploadName('');
              }}
              sx={{ 
                textTransform: 'none',
                fontFamily: "'Inter', sans-serif",
                borderRadius: 2,
                px: 3
              }}
            >
              Cancel
            </Button>
            <Button 
              onClick={handleFileUpload} 
              variant="contained"
              disabled={!selectedFile || !uploadName.trim()}
              sx={{ 
                textTransform: 'none',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                borderRadius: 2,
                px: 3,
                fontFamily: "'Inter', sans-serif",
                fontWeight: 600,
                '&:hover': { 
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  opacity: 0.9
                }
              }}
            >
              Upload Audio
            </Button>
          </DialogActions>
        </Dialog>
      </Container>
    </Box>
  );
}
