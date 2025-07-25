import React from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Button,
  FormControlLabel,
  Switch,
  Slider,
  Grid
} from '@mui/material';

interface AudioControlsProps {
  enabled: boolean;
  volume: number;
  onToggle: (enabled: boolean) => void;
  onVolumeChange: (volume: number) => void;
  minDistance: number;
  maxDistance: number;
  onDistanceChange: (min: number, max: number) => void;
}

const AudioControls: React.FC<AudioControlsProps> = ({
  enabled,
  volume,
  onToggle,
  onVolumeChange,
  minDistance,
  maxDistance,
  onDistanceChange
}) => {
  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          🎵 Audio Controls
        </Typography>
        
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <FormControlLabel
              control={
                <Switch
                  checked={enabled}
                  onChange={(e) => onToggle(e.target.checked)}
                />
              }
              label="Enable Audio Synthesis"
            />
            
            {enabled && (
              <Box mt={2}>
                <Typography variant="body2" gutterBottom>
                  Master Volume: {volume}%
                </Typography>
                <Slider
                  value={volume}
                  onChange={(_, value) => onVolumeChange(value as number)}
                  min={0}
                  max={100}
                  step={5}
                />
              </Box>
            )}
          </Grid>
          
          <Grid item xs={12} md={6}>
            <Typography variant="body2" gutterBottom>
              Distance Range Configuration
            </Typography>
            <Box mb={2}>
              <Typography variant="caption" gutterBottom>
                Min Distance: {minDistance}cm
              </Typography>
              <Slider
                value={minDistance}
                onChange={(_, value) => onDistanceChange(value as number, maxDistance)}
                min={0}
                max={100}
                step={5}
                size="small"
              />
            </Box>
            <Box>
              <Typography variant="caption" gutterBottom>
                Max Distance: {maxDistance}cm
              </Typography>
              <Slider
                value={maxDistance}
                onChange={(_, value) => onDistanceChange(minDistance, value as number)}
                min={100}
                max={500}
                step={10}
                size="small"
              />
            </Box>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
};

export default AudioControls;
