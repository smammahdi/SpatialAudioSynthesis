import React, { useState, useEffect } from 'react';
import { EnhancedAudioSynthesisService, AudioSource, VolumeCurve } from '../services/EnhancedAudioSynthesisService';

interface Props {
  audioService: EnhancedAudioSynthesisService;
  connectedDevices: Array<{ id: string; name: string; distance: number }>;
}

export const EnhancedAudioControls: React.FC<Props> = ({ audioService, connectedDevices }) => {
  const [audioSources, setAudioSources] = useState<AudioSource[]>([]);
  const [selectedSources, setSelectedSources] = useState<{ [deviceId: string]: string }>({});
  const [globalVolume, setGlobalVolume] = useState(70);
  const [volumeCurve, setVolumeCurve] = useState<VolumeCurve>('inverse_square');
  const [maxVolumeLimit, setMaxVolumeLimit] = useState(80);
  const [minDistance, setMinDistance] = useState(5);
  const [maxDistance, setMaxDistance] = useState(200);
  const [distanceEffects, setDistanceEffects] = useState({
    enabled: true,
    pitchEffect: true,
    filterEffect: true,
    reverbEffect: true,
    pitchRange: 30,
    filterRange: 70,
    reverbRange: 40
  });
  const [trackControls, setTrackControls] = useState<{ [deviceId: string]: {
    volume: number;
    pitch: number;
    reverb: number;
    filter: number;
  } }>({});
  const [trackStatus, setTrackStatus] = useState<{ [deviceId: string]: any }>({});
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  useEffect(() => {
    setAudioSources(audioService.getAudioSources());
    
    // Initialize track controls for connected devices
    const newTrackControls: any = {};
    connectedDevices.forEach(device => {
      if (!trackControls[device.id]) {
        newTrackControls[device.id] = {
          volume: 70,
          pitch: 100,
          reverb: 20,
          filter: 100
        };
      }
    });
    setTrackControls(prev => ({ ...prev, ...newTrackControls }));
    
    // Set up status update interval
    const interval = setInterval(() => {
      setTrackStatus(audioService.getAllTracksStatus());
    }, 500);
    
    return () => clearInterval(interval);
  }, [connectedDevices]);

  const categories = ['all', 'animals', 'vehicles', 'music', 'nature', 'urban', 'synth'];
  
  const getFilteredSources = () => {
    if (selectedCategory === 'all') return audioSources;
    return audioSources.filter(source => source.category === selectedCategory);
  };

  const handleSourceChange = async (deviceId: string, sourceId: string) => {
    const source = audioSources.find(s => s.id === sourceId);
    if (source) {
      await audioService.setAudioTrack(deviceId, getDeviceName(deviceId), source);
      setSelectedSources(prev => ({ ...prev, [deviceId]: sourceId }));
    }
  };

  const getDeviceName = (deviceId: string) => {
    return connectedDevices.find(d => d.id === deviceId)?.name || deviceId;
  };

  const handleGlobalVolumeChange = (volume: number) => {
    setGlobalVolume(volume);
    audioService.setGlobalVolume(volume / 100);
  };

  const handleVolumeCurveChange = (curve: VolumeCurve) => {
    setVolumeCurve(curve);
    audioService.setVolumeCurve(curve);
  };

  const handleMaxVolumeLimitChange = (limit: number) => {
    setMaxVolumeLimit(limit);
    audioService.setVolumeLimit(limit / 100);
  };

  const handleDistanceRangeChange = (min: number, max: number) => {
    setMinDistance(min);
    setMaxDistance(max);
    audioService.setDistanceRange(min, max);
  };

  const handleDistanceEffectsChange = (effects: any) => {
    setDistanceEffects(effects);
    audioService.setDistanceEffects({
      ...effects,
      pitchRange: effects.pitchRange / 100,
      filterRange: effects.filterRange / 100,
      reverbRange: effects.reverbRange / 100
    });
  };

  const handleTrackControlChange = (deviceId: string, control: string, value: number) => {
    setTrackControls(prev => ({
      ...prev,
      [deviceId]: { ...prev[deviceId], [control]: value }
    }));

    switch (control) {
      case 'volume':
        audioService.setTrackVolume(deviceId, value / 100);
        break;
      case 'pitch':
        audioService.setTrackPitch(deviceId, value / 100);
        break;
      case 'reverb':
        audioService.setTrackReverb(deviceId, value / 100);
        break;
      case 'filter':
        audioService.setTrackFilter(deviceId, value / 100);
        break;
    }
  };

  return (
    <div className="enhanced-audio-controls">
      <h3>🎵 Enhanced Spatial Audio Controls</h3>
      
      {/* Global Controls */}
      <div className="control-section">
        <h4>🌍 Global Settings</h4>
        
        <div className="control-row">
          <label>Global Volume: {globalVolume}%</label>
          <input
            type="range"
            min="0"
            max="100"
            value={globalVolume}
            onChange={(e) => handleGlobalVolumeChange(Number(e.target.value))}
          />
        </div>
        
        <div className="control-row">
          <label>Volume Curve:</label>
          <select value={volumeCurve} onChange={(e) => handleVolumeCurveChange(e.target.value as VolumeCurve)}>
            <option value="inverse_square">🔬 Inverse Square (Realistic)</option>
            <option value="exponential">📉 Exponential Decay</option>
            <option value="logarithmic">📊 Logarithmic</option>
            <option value="linear">📐 Linear</option>
          </select>
        </div>
        
        <div className="control-row">
          <label>Max Volume Limit: {maxVolumeLimit}%</label>
          <input
            type="range"
            min="10"
            max="100"
            value={maxVolumeLimit}
            onChange={(e) => handleMaxVolumeLimitChange(Number(e.target.value))}
          />
        </div>
        
        <div className="control-row">
          <label>Distance Range:</label>
          <input
            type="number"
            value={minDistance}
            onChange={(e) => handleDistanceRangeChange(Number(e.target.value), maxDistance)}
            style={{ width: '80px', marginRight: '10px' }}
          />
          cm to
          <input
            type="number"
            value={maxDistance}
            onChange={(e) => handleDistanceRangeChange(minDistance, Number(e.target.value))}
            style={{ width: '80px', marginLeft: '10px' }}
          />
          cm
        </div>
      </div>

      {/* Distance Effects */}
      <div className="control-section">
        <h4>🌊 Distance Effects</h4>
        
        <div className="control-row">
          <label>
            <input
              type="checkbox"
              checked={distanceEffects.enabled}
              onChange={(e) => handleDistanceEffectsChange({...distanceEffects, enabled: e.target.checked})}
            />
            Enable Distance Effects
          </label>
        </div>
        
        {distanceEffects.enabled && (
          <>
            <div className="control-row">
              <label>
                <input
                  type="checkbox"
                  checked={distanceEffects.pitchEffect}
                  onChange={(e) => handleDistanceEffectsChange({...distanceEffects, pitchEffect: e.target.checked})}
                />
                Pitch Effect ({distanceEffects.pitchRange}%)
              </label>
              <input
                type="range"
                min="0"
                max="50"
                value={distanceEffects.pitchRange}
                onChange={(e) => handleDistanceEffectsChange({...distanceEffects, pitchRange: Number(e.target.value)})}
                disabled={!distanceEffects.pitchEffect}
              />
            </div>
            
            <div className="control-row">
              <label>
                <input
                  type="checkbox"
                  checked={distanceEffects.filterEffect}
                  onChange={(e) => handleDistanceEffectsChange({...distanceEffects, filterEffect: e.target.checked})}
                />
                Filter Effect ({distanceEffects.filterRange}%)
              </label>
              <input
                type="range"
                min="0"
                max="100"
                value={distanceEffects.filterRange}
                onChange={(e) => handleDistanceEffectsChange({...distanceEffects, filterRange: Number(e.target.value)})}
                disabled={!distanceEffects.filterEffect}
              />
            </div>
            
            <div className="control-row">
              <label>
                <input
                  type="checkbox"
                  checked={distanceEffects.reverbEffect}
                  onChange={(e) => handleDistanceEffectsChange({...distanceEffects, reverbEffect: e.target.checked})}
                />
                Reverb Effect ({distanceEffects.reverbRange}%)
              </label>
              <input
                type="range"
                min="0"
                max="80"
                value={distanceEffects.reverbRange}
                onChange={(e) => handleDistanceEffectsChange({...distanceEffects, reverbRange: Number(e.target.value)})}
                disabled={!distanceEffects.reverbEffect}
              />
            </div>
          </>
        )}
      </div>

      {/* Audio Source Selection */}
      <div className="control-section">
        <h4>🎼 Audio Sources</h4>
        
        <div className="control-row">
          <label>Category:</label>
          <select value={selectedCategory} onChange={(e) => setSelectedCategory(e.target.value)}>
            {categories.map(cat => (
              <option key={cat} value={cat}>
                {cat.charAt(0).toUpperCase() + cat.slice(1)}
              </option>
            ))}
          </select>
        </div>

        {connectedDevices.map(device => (
          <div key={device.id} className="device-controls">
            <h5>{device.name} (Distance: {device.distance}cm)</h5>
            
            <div className="control-row">
              <label>Audio Source:</label>
              <select
                value={selectedSources[device.id] || ''}
                onChange={(e) => handleSourceChange(device.id, e.target.value)}
              >
                <option value="">Select Audio...</option>
                {getFilteredSources().map(source => (
                  <option key={source.id} value={source.id}>
                    {source.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Track Status */}
            {trackStatus[device.id] && (
              <div className="track-status">
                <div className="status-indicator">
                  {trackStatus[device.id].playing ? '▶️' : '⏸️'} 
                  Vol: {trackStatus[device.id].volume}%
                  {distanceEffects.enabled && (
                    <>
                      {distanceEffects.pitchEffect && ` P:${trackStatus[device.id].distanceEffects.pitch}`}
                      {distanceEffects.filterEffect && ` F:${trackStatus[device.id].distanceEffects.filter}%`}
                      {distanceEffects.reverbEffect && ` R:${trackStatus[device.id].distanceEffects.reverb}%`}
                    </>
                  )}
                </div>
              </div>
            )}

            {/* Individual Track Controls */}
            {trackControls[device.id] && (
              <div className="track-controls">
                <div className="control-row">
                  <label>Volume: {trackControls[device.id].volume}%</label>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={trackControls[device.id].volume}
                    onChange={(e) => handleTrackControlChange(device.id, 'volume', Number(e.target.value))}
                  />
                </div>
                
                <div className="control-row">
                  <label>Pitch: {trackControls[device.id].pitch}%</label>
                  <input
                    type="range"
                    min="50"
                    max="200"
                    value={trackControls[device.id].pitch}
                    onChange={(e) => handleTrackControlChange(device.id, 'pitch', Number(e.target.value))}
                  />
                </div>
                
                <div className="control-row">
                  <label>Reverb: {trackControls[device.id].reverb}%</label>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={trackControls[device.id].reverb}
                    onChange={(e) => handleTrackControlChange(device.id, 'reverb', Number(e.target.value))}
                  />
                </div>
                
                <div className="control-row">
                  <label>Filter: {trackControls[device.id].filter}%</label>
                  <input
                    type="range"
                    min="10"
                    max="100"
                    value={trackControls[device.id].filter}
                    onChange={(e) => handleTrackControlChange(device.id, 'filter', Number(e.target.value))}
                  />
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      <style jsx>{`
        .enhanced-audio-controls {
          padding: 20px;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          border-radius: 15px;
          color: white;
          margin: 20px 0;
        }
        
        .control-section {
          margin-bottom: 25px;
          padding: 15px;
          background: rgba(255, 255, 255, 0.1);
          border-radius: 10px;
          backdrop-filter: blur(10px);
        }
        
        .control-row {
          display: flex;
          align-items: center;
          margin: 10px 0;
          gap: 15px;
        }
        
        .control-row label {
          min-width: 150px;
          font-weight: 500;
        }
        
        .control-row input[type="range"] {
          flex: 1;
          height: 6px;
          background: rgba(255, 255, 255, 0.3);
          border-radius: 3px;
          outline: none;
        }
        
        .control-row select {
          padding: 8px 12px;
          border-radius: 6px;
          border: none;
          background: rgba(255, 255, 255, 0.2);
          color: white;
        }
        
        .control-row input[type="number"] {
          padding: 6px 10px;
          border-radius: 4px;
          border: none;
          background: rgba(255, 255, 255, 0.2);
          color: white;
          text-align: center;
        }
        
        .device-controls {
          margin: 15px 0;
          padding: 15px;
          background: rgba(255, 255, 255, 0.05);
          border-radius: 8px;
          border-left: 4px solid #00ff88;
        }
        
        .device-controls h5 {
          margin: 0 0 10px 0;
          color: #00ff88;
          font-weight: 600;
        }
        
        .track-status {
          margin: 10px 0;
          padding: 8px 12px;
          background: rgba(0, 0, 0, 0.3);
          border-radius: 6px;
          font-family: 'Courier New', monospace;
          font-size: 12px;
        }
        
        .status-indicator {
          color: #00ff88;
        }
        
        .track-controls {
          margin-top: 10px;
          padding: 10px;
          background: rgba(255, 255, 255, 0.05);
          border-radius: 6px;
        }
        
        h3 {
          text-align: center;
          margin-bottom: 20px;
          font-size: 24px;
          text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
        }
        
        h4 {
          margin: 0 0 15px 0;
          color: #fff;
          font-size: 16px;
          border-bottom: 2px solid rgba(255, 255, 255, 0.2);
          padding-bottom: 5px;
        }
      `}</style>
    </div>
  );
};
