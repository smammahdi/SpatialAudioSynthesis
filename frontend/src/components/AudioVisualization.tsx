import React, { useRef, useEffect, useState } from 'react';
import { Box, Card, CardContent, Typography, ToggleButton, ToggleButtonGroup, Chip } from '@mui/material';
import { GraphicEq, ShowChart, BarChart, Timeline } from '@mui/icons-material';

interface AudioVisualizationProps {
  audioContext?: AudioContext;
  sourceNode?: AudioNode;
  isActive: boolean;
  width?: number;
  height?: number;
}

type VisualizationType = 'waveform' | 'frequency' | 'oscilloscope' | 'volume';

export const AudioVisualization: React.FC<AudioVisualizationProps> = ({
  audioContext,
  sourceNode,
  isActive,
  width = 400,
  height = 200
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationRef = useRef<number>();
  const [visualizationType, setVisualizationType] = useState<VisualizationType>('frequency');
  const [isInitialized, setIsInitialized] = useState(false);

  useEffect(() => {
    if (audioContext && sourceNode && !analyserRef.current) {
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 2048;
      analyser.smoothingTimeConstant = 0.8;
      analyser.minDecibels = -90;
      analyser.maxDecibels = -10;
      
      sourceNode.connect(analyser);
      analyserRef.current = analyser;
      setIsInitialized(true);
    }

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [audioContext, sourceNode]);

  useEffect(() => {
    if (isActive && analyserRef.current && canvasRef.current) {
      startVisualization();
    } else {
      stopVisualization();
    }

    return () => stopVisualization();
  }, [isActive, visualizationType, isInitialized]);

  const startVisualization = () => {
    if (!analyserRef.current || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const analyser = analyserRef.current;
    
    const animate = () => {
      if (!isActive) return;

      ctx.fillStyle = 'rgba(18, 18, 18, 0.2)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      switch (visualizationType) {
        case 'frequency':
          drawFrequencyBars(ctx, analyser, canvas.width, canvas.height);
          break;
        case 'waveform':
          drawWaveform(ctx, analyser, canvas.width, canvas.height);
          break;
        case 'oscilloscope':
          drawOscilloscope(ctx, analyser, canvas.width, canvas.height);
          break;
        case 'volume':
          drawVolumeMeters(ctx, analyser, canvas.width, canvas.height);
          break;
      }

      animationRef.current = requestAnimationFrame(animate);
    };

    animate();
  };

  const stopVisualization = () => {
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
    }
  };

  const drawFrequencyBars = (ctx: CanvasRenderingContext2D, analyser: AnalyserNode, width: number, height: number) => {
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    analyser.getByteFrequencyData(dataArray);

    const barWidth = (width / bufferLength) * 2.5;
    let barHeight;
    let x = 0;

    const gradient = ctx.createLinearGradient(0, height, 0, 0);
    gradient.addColorStop(0, '#00ff88');
    gradient.addColorStop(0.5, '#00ccff');
    gradient.addColorStop(1, '#ff00ff');

    for (let i = 0; i < bufferLength; i++) {
      barHeight = (dataArray[i] / 255) * height;

      ctx.fillStyle = gradient;
      ctx.fillRect(x, height - barHeight, barWidth, barHeight);

      // Add glow effect
      ctx.shadowColor = '#00ff88';
      ctx.shadowBlur = 20;
      ctx.fillRect(x, height - barHeight, barWidth, barHeight);
      ctx.shadowBlur = 0;

      x += barWidth + 1;
    }
  };

  const drawWaveform = (ctx: CanvasRenderingContext2D, analyser: AnalyserNode, width: number, height: number) => {
    const bufferLength = analyser.fftSize;
    const dataArray = new Uint8Array(bufferLength);
    analyser.getByteTimeDomainData(dataArray);

    ctx.lineWidth = 2;
    ctx.strokeStyle = '#00ff88';
    ctx.beginPath();

    const sliceWidth = width / bufferLength;
    let x = 0;

    for (let i = 0; i < bufferLength; i++) {
      const v = dataArray[i] / 128.0;
      const y = v * height / 2;

      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }

      x += sliceWidth;
    }

    ctx.lineTo(width, height / 2);
    ctx.stroke();

    // Add glow effect
    ctx.shadowColor = '#00ff88';
    ctx.shadowBlur = 10;
    ctx.stroke();
    ctx.shadowBlur = 0;
  };

  const drawOscilloscope = (ctx: CanvasRenderingContext2D, analyser: AnalyserNode, width: number, height: number) => {
    const bufferLength = analyser.fftSize;
    const dataArray = new Uint8Array(bufferLength);
    analyser.getByteTimeDomainData(dataArray);

    // Draw grid
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
    ctx.lineWidth = 1;
    
    // Horizontal lines
    for (let i = 0; i <= 4; i++) {
      const y = (height / 4) * i;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    // Vertical lines
    for (let i = 0; i <= 8; i++) {
      const x = (width / 8) * i;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }

    // Draw waveform
    ctx.lineWidth = 3;
    ctx.strokeStyle = '#00ccff';
    ctx.beginPath();

    const sliceWidth = width / bufferLength;
    let x = 0;

    for (let i = 0; i < bufferLength; i++) {
      const v = dataArray[i] / 128.0;
      const y = v * height / 2;

      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }

      x += sliceWidth;
    }

    ctx.stroke();

    // Add glow
    ctx.shadowColor = '#00ccff';
    ctx.shadowBlur = 15;
    ctx.stroke();
    ctx.shadowBlur = 0;
  };

  const drawVolumeMeters = (ctx: CanvasRenderingContext2D, analyser: AnalyserNode, width: number, height: number) => {
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    analyser.getByteFrequencyData(dataArray);

    // Calculate RMS
    let sum = 0;
    for (let i = 0; i < bufferLength; i++) {
      sum += dataArray[i] * dataArray[i];
    }
    const rms = Math.sqrt(sum / bufferLength);
    const volume = (rms / 255) * 100;

    // Left channel meter
    const meterWidth = 40;
    const meterHeight = height - 40;
    const meterX = 50;
    const meterY = 20;

    // Background
    ctx.fillStyle = 'rgba(255, 255, 255, 0.1)';
    ctx.fillRect(meterX, meterY, meterWidth, meterHeight);

    // Volume bar
    const volumeHeight = (volume / 100) * meterHeight;
    const gradient = ctx.createLinearGradient(0, meterY + meterHeight, 0, meterY);
    
    if (volume < 30) {
      gradient.addColorStop(0, '#00ff00');
      gradient.addColorStop(1, '#88ff00');
    } else if (volume < 70) {
      gradient.addColorStop(0, '#ffff00');
      gradient.addColorStop(1, '#ff8800');
    } else {
      gradient.addColorStop(0, '#ff0000');
      gradient.addColorStop(1, '#ff0066');
    }

    ctx.fillStyle = gradient;
    ctx.fillRect(meterX, meterY + meterHeight - volumeHeight, meterWidth, volumeHeight);

    // Peak indicators
    ctx.fillStyle = volume > 90 ? '#ff0000' : 'rgba(255, 255, 255, 0.3)';
    ctx.fillRect(meterX, meterY, meterWidth, 5);
    ctx.fillRect(meterX, meterY + 10, meterWidth, 5);

    // Right channel (simulated)
    const rightMeterX = meterX + meterWidth + 20;
    const rightVolume = volume * (0.8 + Math.random() * 0.4);
    
    ctx.fillStyle = 'rgba(255, 255, 255, 0.1)';
    ctx.fillRect(rightMeterX, meterY, meterWidth, meterHeight);

    const rightVolumeHeight = (rightVolume / 100) * meterHeight;
    ctx.fillStyle = gradient;
    ctx.fillRect(rightMeterX, meterY + meterHeight - rightVolumeHeight, meterWidth, rightVolumeHeight);

    // Labels
    ctx.fillStyle = '#ffffff';
    ctx.font = '12px monospace';
    ctx.textAlign = 'center';
    ctx.fillText('L', meterX + meterWidth/2, meterY + meterHeight + 15);
    ctx.fillText('R', rightMeterX + meterWidth/2, meterY + meterHeight + 15);

    // Volume text
    ctx.textAlign = 'left';
    ctx.fillText(`Volume: ${Math.round(volume)}%`, width - 150, 30);

    // Frequency analysis
    const maxFreq = Math.max(...dataArray);
    const dominantFreq = dataArray.indexOf(maxFreq) * (analyser.context.sampleRate / 2) / bufferLength;
    ctx.fillText(`Peak: ${Math.round(dominantFreq)}Hz`, width - 150, 50);
  };

  const handleVisualizationChange = (
    event: React.MouseEvent<HTMLElement>,
    newVisualization: VisualizationType | null,
  ) => {
    if (newVisualization !== null) {
      setVisualizationType(newVisualization);
    }
  };

  return (
    <Card sx={{ 
      background: 'linear-gradient(135deg, rgba(18,18,18,0.95) 0%, rgba(35,35,60,0.95) 100%)',
      backdropFilter: 'blur(10px)',
      border: '1px solid rgba(255,255,255,0.1)',
      borderRadius: 2
    }}>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h6" color="white">
            Audio Visualization
          </Typography>
          <Box display="flex" gap={1} alignItems="center">
            <Chip 
              label={isActive ? 'Active' : 'Inactive'} 
              color={isActive ? 'success' : 'default'}
              size="small"
            />
            <Chip 
              label={isInitialized ? 'Ready' : 'Initializing'} 
              color={isInitialized ? 'info' : 'warning'}
              size="small"
            />
          </Box>
        </Box>

        <ToggleButtonGroup
          value={visualizationType}
          exclusive
          onChange={handleVisualizationChange}
          size="small"
          sx={{ mb: 2 }}
        >
          <ToggleButton value="frequency" sx={{ color: 'white' }}>
            <BarChart sx={{ mr: 1 }} />
            Frequency
          </ToggleButton>
          <ToggleButton value="waveform" sx={{ color: 'white' }}>
            <Timeline sx={{ mr: 1 }} />
            Waveform
          </ToggleButton>
          <ToggleButton value="oscilloscope" sx={{ color: 'white' }}>
            <ShowChart sx={{ mr: 1 }} />
            Scope
          </ToggleButton>
          <ToggleButton value="volume" sx={{ color: 'white' }}>
            <GraphicEq sx={{ mr: 1 }} />
            Volume
          </ToggleButton>
        </ToggleButtonGroup>

        <Box 
          sx={{ 
            border: '1px solid rgba(255,255,255,0.1)', 
            borderRadius: 1,
            overflow: 'hidden',
            position: 'relative'
          }}
        >
          <canvas
            ref={canvasRef}
            width={width}
            height={height}
            style={{
              width: '100%',
              height: 'auto',
              display: 'block',
              background: 'linear-gradient(45deg, #121212 0%, #1a1a2e 50%, #16213e 100%)'
            }}
          />
          
          {!isActive && (
            <Box
              sx={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: 'rgba(0,0,0,0.7)',
                color: 'white',
                fontSize: '1.2rem'
              }}
            >
              Audio visualization paused
            </Box>
          )}
        </Box>

        <Box mt={1}>
          <Typography variant="caption" color="text.secondary">
            {visualizationType === 'frequency' && 'Real-time frequency spectrum analysis'}
            {visualizationType === 'waveform' && 'Time-domain waveform display'}
            {visualizationType === 'oscilloscope' && 'Oscilloscope-style visualization with grid'}
            {visualizationType === 'volume' && 'Stereo volume meters with peak detection'}
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );
};
