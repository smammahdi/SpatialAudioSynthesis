// Audio Synthesis Service - Real-time spatial audio generation
import * as Tone from 'tone';

export interface AudioTrack {
  sensorId: string;
  sensorName: string;
  audioType: 'bass' | 'mid' | 'treble' | 'ambient' | 'harmonic';
  synth: Tone.Synth | Tone.FMSynth | Tone.AMSynth;
  volume: Tone.Volume;
  currentDistance: number;
  currentVolume: number;
  isPlaying: boolean;
}

export interface SpatialAudioSettings {
  maxDistance: number; // 200cm default
  minDistance: number; // 0cm default
  globalVolume: number; // 0-1
  enabled: boolean;
}

export class AudioSynthesisService {
  private audioTracks: Map<string, AudioTrack> = new Map();
  private masterVolume: Tone.Volume;
  private isInitialized: boolean = false;
  private settings: SpatialAudioSettings = {
    maxDistance: 200,
    minDistance: 0,
    globalVolume: 0.7,
    enabled: false
  };

  constructor() {
    this.masterVolume = new Tone.Volume(-10).toDestination();
    this.setupAudioContext();
  }

  // Initialize audio context
  private async setupAudioContext(): Promise<void> {
    try {
      // Start Tone.js audio context
      if (Tone.context.state !== 'running') {
        await Tone.start();
      }
      this.isInitialized = true;
      console.log('✅ Audio synthesis engine initialized');
    } catch (error) {
      console.error('❌ Failed to initialize audio engine:', error);
      throw error;
    }
  }

  // Create audio track for a sensor
  createAudioTrack(sensorId: string, sensorName: string): AudioTrack {
    if (this.audioTracks.has(sensorId)) {
      return this.audioTracks.get(sensorId)!;
    }

    // Determine audio type based on sensor name/order
    const audioType = this.getAudioTypeForSensor(sensorId, sensorName);
    
    // Create appropriate synthesizer
    const synth = this.createSynthesizer(audioType);
    const volume = new Tone.Volume(-Infinity); // Start muted
    
    // Connect audio chain: synth -> volume -> master
    synth.connect(volume);
    volume.connect(this.masterVolume);

    const audioTrack: AudioTrack = {
      sensorId,
      sensorName,
      audioType,
      synth,
      volume,
      currentDistance: this.settings.maxDistance,
      currentVolume: 0,
      isPlaying: false
    };

    this.audioTracks.set(sensorId, audioTrack);
    console.log(`🎵 Created ${audioType} audio track for ${sensorName}`);

    return audioTrack;
  }

  // Determine audio type based on sensor
  private getAudioTypeForSensor(sensorId: string, sensorName: string): AudioTrack['audioType'] {
    // Map sensors to different audio types for spatial effect
    const sensorIndex = Array.from(this.audioTracks.keys()).length;
    const audioTypes: AudioTrack['audioType'][] = ['bass', 'mid', 'treble', 'ambient', 'harmonic'];
    
    // Assign based on sensor name if possible
    if (sensorName.includes('A') || sensorName.includes('Bass')) return 'bass';
    if (sensorName.includes('B') || sensorName.includes('Mid')) return 'mid';
    if (sensorName.includes('C') || sensorName.includes('Treble')) return 'treble';
    if (sensorName.includes('D') || sensorName.includes('Ambient')) return 'ambient';
    
    // Otherwise assign cyclically
    return audioTypes[sensorIndex % audioTypes.length];
  }

  // Create synthesizer based on audio type
  private createSynthesizer(audioType: AudioTrack['audioType']): Tone.Synth | Tone.FMSynth | Tone.AMSynth {
    switch (audioType) {
      case 'bass':
        return new Tone.FMSynth({
          harmonicity: 1,
          modulationIndex: 2,
          oscillator: { type: 'sine' },
          envelope: { attack: 0.1, decay: 0.2, sustain: 0.8, release: 1.0 }
        });
      
      case 'mid':
        return new Tone.Synth({
          oscillator: { type: 'square' },
          envelope: { attack: 0.05, decay: 0.1, sustain: 0.9, release: 0.5 }
        });
      
      case 'treble':
        return new Tone.AMSynth({
          harmonicity: 3,
          oscillator: { type: 'sine' },
          envelope: { attack: 0.01, decay: 0.05, sustain: 0.9, release: 0.3 }
        });
      
      case 'ambient':
        return new Tone.Synth({
          oscillator: { type: 'sawtooth' },
          envelope: { attack: 0.5, decay: 0.5, sustain: 0.7, release: 2.0 }
        });
      
      case 'harmonic':
        return new Tone.FMSynth({
          harmonicity: 0.5,
          modulationIndex: 1.5,
          oscillator: { type: 'triangle' },
          envelope: { attack: 0.2, decay: 0.3, sustain: 0.6, release: 1.5 }
        });
      
      default:
        return new Tone.Synth();
    }
  }

  // Update distance data and recalculate audio
  updateSensorDistance(sensorId: string, distance: number): void {
    const track = this.audioTracks.get(sensorId);
    if (!track) return;

    track.currentDistance = distance;
    const newVolume = this.calculateVolumeFromDistance(distance);
    
    if (newVolume !== track.currentVolume) {
      track.currentVolume = newVolume;
      this.updateTrackVolume(track);
    }

    // Start/stop audio based on volume
    if (this.settings.enabled) {
      if (newVolume > 0 && !track.isPlaying) {
        this.startTrackAudio(track);
      } else if (newVolume === 0 && track.isPlaying) {
        this.stopTrackAudio(track);
      }
    }
  }

  // Calculate volume from distance (0-200cm -> 100%-0%)
  private calculateVolumeFromDistance(distance: number): number {
    const { minDistance, maxDistance } = this.settings;
    
    // Clamp distance to valid range
    const clampedDistance = Math.max(minDistance, Math.min(maxDistance, distance));
    
    // Calculate volume: closer = louder
    const volumePercent = Math.max(0, 100 - (clampedDistance / maxDistance) * 100);
    
    return volumePercent / 100; // Convert to 0-1 range
  }

  // Update track volume
  private updateTrackVolume(track: AudioTrack): void {
    if (track.currentVolume <= 0) {
      track.volume.volume.value = -Infinity; // Mute
    } else {
      // Convert 0-1 to decibels (-60dB to 0dB)
      const dbValue = -60 + (track.currentVolume * 60);
      track.volume.volume.rampTo(dbValue, 0.1); // Smooth transition
    }
  }

  // Start audio for track
  private startTrackAudio(track: AudioTrack): void {
    if (!this.isInitialized || track.isPlaying) return;

    try {
      const note = this.getNoteForAudioType(track.audioType);
      track.synth.triggerAttack(note);
      track.isPlaying = true;
      console.log(`🎵 Started ${track.audioType} audio for ${track.sensorName}`);
    } catch (error) {
      console.error(`❌ Failed to start audio for ${track.sensorName}:`, error);
    }
  }

  // Stop audio for track
  private stopTrackAudio(track: AudioTrack): void {
    if (!track.isPlaying) return;

    try {
      track.synth.triggerRelease();
      track.isPlaying = false;
      console.log(`🔇 Stopped ${track.audioType} audio for ${track.sensorName}`);
    } catch (error) {
      console.error(`❌ Failed to stop audio for ${track.sensorName}:`, error);
    }
  }

  // Get musical note for audio type
  private getNoteForAudioType(audioType: AudioTrack['audioType']): string {
    const noteMap = {
      bass: 'C2',
      mid: 'C4',
      treble: 'C6',
      ambient: 'G3',
      harmonic: 'E4'
    };
    return noteMap[audioType] || 'C4';
  }

  // Enable/disable audio synthesis
  setEnabled(enabled: boolean): void {
    this.settings.enabled = enabled;
    
    if (!enabled) {
      // Stop all playing tracks
      this.audioTracks.forEach(track => {
        if (track.isPlaying) {
          this.stopTrackAudio(track);
        }
      });
    } else {
      // Start tracks that should be playing
      this.audioTracks.forEach(track => {
        if (track.currentVolume > 0) {
          this.startTrackAudio(track);
        }
      });
    }
  }

  // Set global volume
  setGlobalVolume(volume: number): void {
    this.settings.globalVolume = Math.max(0, Math.min(1, volume));
    const dbValue = -30 + (this.settings.globalVolume * 30); // -30dB to 0dB
    this.masterVolume.volume.rampTo(dbValue, 0.2);
  }

  // Set distance range
  setDistanceRange(minDistance: number, maxDistance: number): void {
    this.settings.minDistance = minDistance;
    this.settings.maxDistance = maxDistance;
    
    // Recalculate all volumes
    this.audioTracks.forEach(track => {
      this.updateSensorDistance(track.sensorId, track.currentDistance);
    });
  }

  // Remove audio track
  removeAudioTrack(sensorId: string): void {
    const track = this.audioTracks.get(sensorId);
    if (!track) return;

    // Stop and dispose
    if (track.isPlaying) {
      this.stopTrackAudio(track);
    }
    
    track.synth.dispose();
    track.volume.dispose();
    this.audioTracks.delete(sensorId);
    
    console.log(`🗑️ Removed audio track for ${track.sensorName}`);
  }

  // Get current status
  getAudioStatus(): { [sensorId: string]: { distance: number; volume: number; playing: boolean; type: string } } {
    const status: any = {};
    
    this.audioTracks.forEach(track => {
      status[track.sensorId] = {
        distance: track.currentDistance,
        volume: Math.round(track.currentVolume * 100),
        playing: track.isPlaying,
        type: track.audioType
      };
    });
    
    return status;
  }

  // Get settings
  getSettings(): SpatialAudioSettings {
    return { ...this.settings };
  }

  // Cleanup
  dispose(): void {
    this.audioTracks.forEach(track => {
      this.removeAudioTrack(track.sensorId);
    });
    this.masterVolume.dispose();
    console.log('🔇 Audio synthesis service disposed');
  }

  // Check if audio is supported
  get isSupported(): boolean {
    return typeof window !== 'undefined' && 'AudioContext' in window;
  }

  // Get initialization status
  get initialized(): boolean {
    return this.isInitialized;
  }
}
