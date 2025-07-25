import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  CardActions,
  Typography,
  Box,
  Chip,
  Button,
  LinearProgress,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Switch,
  FormControlLabel,
  Divider,
  Alert
} from '@mui/material';
import {
  Bluetooth,
  BluetoothConnected,
  BluetoothDisabled,
  Settings,
  SignalCellular4Bar,
  SignalCellular2Bar,
  SignalCellular1Bar,
  SignalCellularOff,
  Close,
  Refresh,
  Info,
  LocationOn
} from '@mui/icons-material';

interface SensorData {
  deviceId: string;
  deviceName: string;
  distance: number;
  connected: boolean;
  lastUpdate: number;
}

interface SensorCardProps {
  sensor?: SensorData;
  isDemo?: boolean;
  onDisconnect?: (deviceId: string) => void;
  onConfigChange?: (deviceId: string, config: any) => void;
}

export const SensorCard: React.FC<SensorCardProps> = ({
  sensor,
  isDemo = false,
  onDisconnect,
  onConfigChange
}) => {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [simulatedDistance, setSimulatedDistance] = useState(50);
  const [autoUpdate, setAutoUpdate] = useState(true);
  const [minDistance, setMinDistance] = useState(5);
  const [maxDistance, setMaxDistance] = useState(200);
  const [smoothing, setSmoothing] = useState(0.8);
  const [calibrationOffset, setCalibrationOffset] = useState(0);

  // Demo sensor data
  const demoSensor: SensorData = {
    deviceId: 'demo-sensor-001',
    deviceName: 'Demo HC-05',
    distance: simulatedDistance,
    connected: true,
    lastUpdate: Date.now()
  };

  const currentSensor = sensor || (isDemo ? demoSensor : null);

  useEffect(() => {
    if (isDemo && autoUpdate) {
      const interval = setInterval(() => {
        // Simulate realistic distance changes
        const variation = (Math.random() - 0.5) * 20;
        const newDistance = Math.max(5, Math.min(200, simulatedDistance + variation));
        setSimulatedDistance(newDistance);
      }, 500);

      return () => clearInterval(interval);
    }
  }, [isDemo, autoUpdate, simulatedDistance]);

  if (!currentSensor) {
    return (
      <Card sx={{ 
        background: 'linear-gradient(135deg, rgba(18,18,18,0.95) 0%, rgba(35,35,60,0.95) 100%)',
        backdropFilter: 'blur(10px)',
        border: '1px solid rgba(255,255,255,0.1)',
        borderRadius: 2,
        minHeight: 200
      }}>
        <CardContent>
          <Box display="flex" flexDirection="column" alignItems="center" justifyContent="center" minHeight={150}>
            <BluetoothDisabled sx={{ fontSize: 48, color: 'rgba(255,255,255,0.3)', mb: 2 }} />
            <Typography variant="h6" color="text.secondary" textAlign="center">
              No Sensor Connected
            </Typography>
            <Typography variant="body2" color="text.secondary" textAlign="center" mt={1}>
              Connect a Bluetooth HC-05 sensor to get started
            </Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  const getSignalStrength = (distance: number) => {
    if (distance < 30) return 4;
    if (distance < 60) return 3;
    if (distance < 100) return 2;
    if (distance < 150) return 1;
    return 0;
  };

  const getSignalIcon = (strength: number) => {
    switch (strength) {
      case 4: return <SignalCellular4Bar color="success" />;
      case 3: return <SignalCellular4Bar color="info" />;
      case 2: return <SignalCellular2Bar color="warning" />;
      case 1: return <SignalCellular1Bar color="error" />;
      default: return <SignalCellularOff color="disabled" />;
    }
  };

  const getDistanceColor = (distance: number) => {
    if (distance < 30) return '#4caf50';
    if (distance < 60) return '#ff9800';
    if (distance < 100) return '#f44336';
    return '#9c27b0';
  };

  const signalStrength = getSignalStrength(currentSensor.distance);
  const timeSinceUpdate = Date.now() - currentSensor.lastUpdate;
  const isStale = timeSinceUpdate > 5000;

  const handleSaveSettings = () => {
    if (onConfigChange) {
      onConfigChange(currentSensor.deviceId, {
        minDistance,
        maxDistance,
        smoothing,
        calibrationOffset
      });
    }
    setSettingsOpen(false);
  };

  return (
    <>
      <Card sx={{ 
        background: 'linear-gradient(135deg, rgba(18,18,18,0.95) 0%, rgba(35,35,60,0.95) 100%)',
        backdropFilter: 'blur(10px)',
        border: `1px solid ${currentSensor.connected ? 'rgba(76,175,80,0.3)' : 'rgba(244,67,54,0.3)'}`,
        borderRadius: 2,
        position: 'relative',
        overflow: 'visible'
      }}>
        {/* Connection Status Indicator */}
        <Box
          sx={{
            position: 'absolute',
            top: -8,
            right: -8,
            width: 16,
            height: 16,
            borderRadius: '50%',
            backgroundColor: currentSensor.connected ? '#4caf50' : '#f44336',
            border: '2px solid white',
            boxShadow: '0 0 10px rgba(0,0,0,0.3)'
          }}
        />

        <CardContent>
          {/* Header */}
          <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={2}>
            <Box>
              <Box display="flex" alignItems="center" gap={1} mb={1}>
                {currentSensor.connected ? (
                  <BluetoothConnected color="primary" />
                ) : (
                  <BluetoothDisabled color="disabled" />
                )}
                <Typography variant="h6" color="white">
                  {currentSensor.deviceName}
                </Typography>
                {isDemo && (
                  <Chip label="DEMO" size="small" color="info" />
                )}
              </Box>
              <Typography variant="caption" color="text.secondary">
                ID: {currentSensor.deviceId.slice(-8)}
              </Typography>
            </Box>
            
            <Box display="flex" gap={1}>
              {getSignalIcon(signalStrength)}
              <IconButton
                size="small"
                onClick={() => setSettingsOpen(true)}
                sx={{ color: 'rgba(255,255,255,0.7)' }}
              >
                <Settings />
              </IconButton>
            </Box>
          </Box>

          {/* Distance Display */}
          <Box textAlign="center" mb={3}>
            <Typography 
              variant="h3" 
              sx={{ 
                color: getDistanceColor(currentSensor.distance),
                fontWeight: 'bold',
                textShadow: '0 0 20px currentColor'
              }}
            >
              {currentSensor.distance.toFixed(1)}
            </Typography>
            <Typography variant="h6" color="text.secondary">
              centimeters
            </Typography>
            
            {/* Distance Bar */}
            <Box mt={2}>
              <LinearProgress 
                variant="determinate" 
                value={Math.min((currentSensor.distance / 200) * 100, 100)}
                sx={{
                  height: 8,
                  borderRadius: 4,
                  backgroundColor: 'rgba(255,255,255,0.1)',
                  '& .MuiLinearProgress-bar': {
                    backgroundColor: getDistanceColor(currentSensor.distance),
                    borderRadius: 4,
                  }
                }}
              />
              <Box display="flex" justifyContent="space-between" mt={1}>
                <Typography variant="caption" color="text.secondary">0cm</Typography>
                <Typography variant="caption" color="text.secondary">200cm</Typography>
              </Box>
            </Box>
          </Box>

          {/* Status Information */}
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Box>
              <Chip 
                label={currentSensor.connected ? 'Connected' : 'Disconnected'}
                color={currentSensor.connected ? 'success' : 'error'}
                size="small"
                sx={{ mr: 1 }}
              />
              {isStale && (
                <Chip 
                  label="Stale Data"
                  color="warning"
                  size="small"
                  icon={<Refresh />}
                />
              )}
            </Box>
            
            <Typography variant="caption" color="text.secondary">
              Updated: {new Date(currentSensor.lastUpdate).toLocaleTimeString()}
            </Typography>
          </Box>

          {/* Additional Metrics */}
          <Box mt={2} pt={2} borderTop="1px solid rgba(255,255,255,0.1)">
            <Box display="flex" justifyContent="space-between" alignItems="center">
              <Box display="flex" alignItems="center" gap={1}>
                <LocationOn sx={{ fontSize: 16, color: 'text.secondary' }} />
                <Typography variant="caption" color="text.secondary">
                  Signal: {signalStrength}/4 bars
                </Typography>
              </Box>
              
              <Typography variant="caption" color="text.secondary">
                Range: {minDistance}-{maxDistance}cm
              </Typography>
            </Box>
          </Box>
        </CardContent>

        <CardActions>
          <Button
            size="small"
            color="error"
            onClick={() => onDisconnect?.(currentSensor.deviceId)}
            disabled={!currentSensor.connected}
            startIcon={<Close />}
          >
            Disconnect
          </Button>
          
          <Button
            size="small"
            onClick={() => setSettingsOpen(true)}
            startIcon={<Settings />}
          >
            Settings
          </Button>
        </CardActions>
      </Card>

      {/* Settings Dialog */}
      <Dialog 
        open={settingsOpen} 
        onClose={() => setSettingsOpen(false)}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            background: 'linear-gradient(135deg, rgba(18,18,18,0.95) 0%, rgba(35,35,60,0.95) 100%)',
            backdropFilter: 'blur(10px)',
            border: '1px solid rgba(255,255,255,0.1)',
          }
        }}
      >
        <DialogTitle>
          <Box display="flex" alignItems="center" gap={1}>
            <Settings />
            Sensor Settings - {currentSensor.deviceName}
          </Box>
        </DialogTitle>
        
        <DialogContent>
          {isDemo && (
            <Alert severity="info" sx={{ mb: 3 }}>
              <Typography variant="body2">
                Demo mode active. These settings simulate real sensor behavior.
              </Typography>
            </Alert>
          )}

          <Box display="flex" flexDirection="column" gap={3}>
            {/* Distance Range */}
            <Box>
              <Typography variant="subtitle2" gutterBottom>
                Distance Range
              </Typography>
              <Box display="flex" gap={2}>
                <TextField
                  label="Min Distance (cm)"
                  type="number"
                  value={minDistance}
                  onChange={(e) => setMinDistance(Number(e.target.value))}
                  size="small"
                  fullWidth
                />
                <TextField
                  label="Max Distance (cm)"
                  type="number"
                  value={maxDistance}
                  onChange={(e) => setMaxDistance(Number(e.target.value))}
                  size="small"
                  fullWidth
                />
              </Box>
            </Box>

            <Divider />

            {/* Calibration */}
            <Box>
              <Typography variant="subtitle2" gutterBottom>
                Calibration
              </Typography>
              <TextField
                label="Offset (cm)"
                type="number"
                value={calibrationOffset}
                onChange={(e) => setCalibrationOffset(Number(e.target.value))}
                size="small"
                fullWidth
                helperText="Adjust to calibrate sensor readings"
              />
            </Box>

            <Divider />

            {/* Data Processing */}
            <Box>
              <Typography variant="subtitle2" gutterBottom>
                Data Processing
              </Typography>
              <TextField
                label="Smoothing Factor"
                type="number"
                inputProps={{ min: 0, max: 1, step: 0.1 }}
                value={smoothing}
                onChange={(e) => setSmoothing(Number(e.target.value))}
                size="small"
                fullWidth
                helperText="0 = no smoothing, 1 = maximum smoothing"
              />
            </Box>

            {isDemo && (
              <>
                <Divider />
                
                {/* Demo Controls */}
                <Box>
                  <Typography variant="subtitle2" gutterBottom>
                    Demo Controls
                  </Typography>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={autoUpdate}
                        onChange={(e) => setAutoUpdate(e.target.checked)}
                      />
                    }
                    label="Auto-update distance"
                  />
                  <TextField
                    label="Simulated Distance (cm)"
                    type="number"
                    value={simulatedDistance}
                    onChange={(e) => setSimulatedDistance(Number(e.target.value))}
                    size="small"
                    fullWidth
                    sx={{ mt: 2 }}
                    disabled={autoUpdate}
                  />
                </Box>
              </>
            )}
          </Box>
        </DialogContent>

        <DialogActions>
          <Button onClick={() => setSettingsOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleSaveSettings} variant="contained">
            Save Settings
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};
