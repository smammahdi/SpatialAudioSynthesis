// Simple Audio Control Panel for the React App
import React, { useState, useEffect } from 'react';
import { Box, Typography, Button, Slider, FormControlLabel, Switch, Select, MenuItem } from '@mui/material';

const SimpleEnhancedAudioControls = ({ audioService, connectedDevices }) => {
  const [globalVolume, setGlobalVolume] = useState(70);
  const [volumeCurve, setVolumeCurve] = useState('inverse_square');
  const [maxVolumeLimit, setMaxVolumeLimit] = useState(80);
  const [minDistance, setMinDistance] = useState(5);
  const [maxDistance, setMaxDistance] = useState(200);
  const [distanceEffects, setDistanceEffects] = useState({
    enabled: true,
    pitchEffect: true,
    filterEffect: true,
    reverbEffect: true
  });
  const [trackStatus, setTrackStatus] = useState({});

  useEffect(() => {
    const interval = setInterval(() => {
      setTrackStatus(audioService.getAllTracksStatus());
    }, 500);
    
    return () => clearInterval(interval);
  }, [audioService]);

  const handleGlobalVolumeChange = (value) => {
    setGlobalVolume(value);
    audioService.setGlobalVolume(value / 100);
  };

  const handleVolumeCurveChange = (curve) => {
    setVolumeCurve(curve);
    audioService.setVolumeCurve(curve);
  };

  const handleMaxVolumeLimitChange = (limit) => {
    setMaxVolumeLimit(limit);
    audioService.setVolumeLimit(limit / 100);
  };

  const handleDistanceRangeChange = () => {
    audioService.setDistanceRange(minDistance, maxDistance);
  };

  const handleDistanceEffectsChange = (effects) => {
    setDistanceEffects(effects);
    audioService.setDistanceEffects(effects);
  };

  const audioSources = audioService.getAudioSources();
  const categories = ['animals', 'vehicles', 'music', 'nature', 'urban', 'synth'];

  return (
    <Box sx={{ 
      p: 3, 
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      borderRadius: 3,
      color: 'white',
      my: 3
    }}>
      <Typography variant="h5" gutterBottom sx={{ textAlign: 'center', mb: 3 }}>
        🎵 Enhanced Spatial Audio Controls
      </Typography>
      
      {/* Global Controls */}
      <Box sx={{ mb: 3, p: 2, background: 'rgba(255,255,255,0.1)', borderRadius: 2 }}>
        <Typography variant="h6" gutterBottom>🌍 Global Settings</Typography>
        
        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" gutterBottom>Global Volume: {globalVolume}%</Typography>
          <Slider
            value={globalVolume}
            onChange={(_, value) => handleGlobalVolumeChange(value)}
            min={0}
            max={100}
            step={5}
            sx={{ color: 'white' }}
          />
        </Box>
        
        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" gutterBottom>Volume Curve:</Typography>
          <Select
            value={volumeCurve}
            onChange={(e) => handleVolumeCurveChange(e.target.value)}
            sx={{ color: 'white', minWidth: 200 }}
          >
            <MenuItem value="inverse_square">🔬 Inverse Square (Realistic)</MenuItem>
            <MenuItem value="exponential">📉 Exponential Decay</MenuItem>
            <MenuItem value="logarithmic">📊 Logarithmic</MenuItem>
            <MenuItem value="linear">📐 Linear</MenuItem>
          </Select>
        </Box>
        
        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" gutterBottom>Max Volume Limit: {maxVolumeLimit}%</Typography>
          <Slider
            value={maxVolumeLimit}
            onChange={(_, value) => handleMaxVolumeLimitChange(value)}
            min={10}
            max={100}
            step={5}
            sx={{ color: 'white' }}
          />
        </Box>

        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <Typography variant="body2">Distance Range:</Typography>
          <Slider
            value={[minDistance, maxDistance]}
            onChange={(_, value) => {
              setMinDistance(value[0]);
              setMaxDistance(value[1]);
              handleDistanceRangeChange();
            }}
            min={0}
            max={300}
            step={5}
            valueLabelDisplay="auto"
            sx={{ color: 'white', flex: 1 }}
          />
        </Box>
      </Box>

      {/* Distance Effects */}
      <Box sx={{ mb: 3, p: 2, background: 'rgba(255,255,255,0.1)', borderRadius: 2 }}>
        <Typography variant="h6" gutterBottom>🌊 Distance Effects</Typography>
        
        <FormControlLabel
          control={
            <Switch
              checked={distanceEffects.enabled}
              onChange={(e) => handleDistanceEffectsChange({...distanceEffects, enabled: e.target.checked})}
              sx={{ color: 'white' }}
            />
          }
          label="Enable Distance Effects"
        />
        
        {distanceEffects.enabled && (
          <Box sx={{ mt: 2 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={distanceEffects.pitchEffect}
                  onChange={(e) => handleDistanceEffectsChange({...distanceEffects, pitchEffect: e.target.checked})}
                  sx={{ color: 'white' }}
                />
              }
              label="Pitch Effect"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={distanceEffects.filterEffect}
                  onChange={(e) => handleDistanceEffectsChange({...distanceEffects, filterEffect: e.target.checked})}
                  sx={{ color: 'white' }}
                />
              }
              label="Filter Effect"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={distanceEffects.reverbEffect}
                  onChange={(e) => handleDistanceEffectsChange({...distanceEffects, reverbEffect: e.target.checked})}
                  sx={{ color: 'white' }}
                />
              }
              label="Reverb Effect"
            />
          </Box>
        )}
      </Box>

      {/* Device Audio Sources */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h6" gutterBottom>🎼 Audio Sources</Typography>
        
        {connectedDevices.map(device => (
          <Box key={device.id} sx={{ 
            mb: 2, 
            p: 2, 
            background: 'rgba(255,255,255,0.05)', 
            borderRadius: 2,
            borderLeft: '4px solid #00ff88'
          }}>
            <Typography variant="subtitle1" sx={{ color: '#00ff88', mb: 1 }}>
              {device.name} (Distance: {device.distance}cm)
            </Typography>
            
            {/* Audio Source Selection */}
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" gutterBottom>Select Audio:</Typography>
              <Select
                onChange={(e) => {
                  const source = audioSources.find(s => s.id === e.target.value);
                  if (source) {
                    audioService.setAudioTrack(device.id, device.name, source);
                  }
                }}
                sx={{ color: 'white', minWidth: 200 }}
                displayEmpty
              >
                <MenuItem value="">Choose Audio...</MenuItem>
                {categories.map(category => [
                  <MenuItem key={category} disabled sx={{ fontWeight: 'bold' }}>
                    {category.toUpperCase()}
                  </MenuItem>,
                  ...audioSources
                    .filter(source => source.category === category)
                    .map(source => (
                      <MenuItem key={source.id} value={source.id}>
                        {source.name}
                      </MenuItem>
                    ))
                ])}
              </Select>
            </Box>

            {/* Track Status */}
            {trackStatus[device.id] && (
              <Box sx={{ 
                p: 1, 
                background: 'rgba(0,0,0,0.3)', 
                borderRadius: 1,
                fontFamily: 'monospace',
                fontSize: '12px'
              }}>
                <Typography variant="body2" sx={{ color: '#00ff88' }}>
                  {trackStatus[device.id].playing ? '▶️' : '⏸️'} 
                  {trackStatus[device.id].audioSource} - 
                  Vol: {trackStatus[device.id].volume}%
                  {distanceEffects.enabled && (
                    <>
                      {distanceEffects.pitchEffect && ` P:${trackStatus[device.id].distanceEffects?.pitch}`}
                      {distanceEffects.filterEffect && ` F:${trackStatus[device.id].distanceEffects?.filter}%`}
                      {distanceEffects.reverbEffect && ` R:${trackStatus[device.id].distanceEffects?.reverb}%`}
                    </>
                  )}
                </Typography>
              </Box>
            )}

            {/* Quick Audio Assignment Buttons */}
            <Box sx={{ mt: 2, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              <Button 
                size="small" 
                variant="outlined"
                sx={{ color: 'white', borderColor: 'white' }}
                onClick={() => {
                  const cowSource = audioSources.find(s => s.id === 'cow_moo');
                  if (cowSource) audioService.setAudioTrack(device.id, device.name, cowSource);
                }}
              >
                🐄 Cow
              </Button>
              <Button 
                size="small" 
                variant="outlined"
                sx={{ color: 'white', borderColor: 'white' }}
                onClick={() => {
                  const hornSource = audioSources.find(s => s.id === 'car_horn');
                  if (hornSource) audioService.setAudioTrack(device.id, device.name, hornSource);
                }}
              >
                🚗 Car Horn
              </Button>
              <Button 
                size="small" 
                variant="outlined"
                sx={{ color: 'white', borderColor: 'white' }}
                onClick={() => {
                  const pianoSource = audioSources.find(s => s.id === 'piano_melody');
                  if (pianoSource) audioService.setAudioTrack(device.id, device.name, pianoSource);
                }}
              >
                🎹 Piano
              </Button>
            </Box>
          </Box>
        ))}
      </Box>
    </Box>
  );
};

export default SimpleEnhancedAudioControls;
