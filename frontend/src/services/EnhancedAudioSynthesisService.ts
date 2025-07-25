// Enhanced Audio Synthesis Service - Advanced spatial audio with realistic physics
export interface AudioSource {
  id: string;
  name: string;
  type: 'oscillator' | 'audio';
  frequency?: number;
  file?: string;
  category?: string;
}

export interface DistanceEffects {
  enabled: boolean;
  pitchEffect: boolean;
  filterEffect: boolean;
  reverbEffect: boolean;
  pitchRange: number;
  filterRange: number;
  reverbRange: number;
}

export interface AudioTrack {
  deviceId: string;
  deviceName: string;
  audioSource: AudioSource;
  volume: number; // Distance-based volume
  nodeVolume: number; // User-set volume
  pitch: number; // User-set pitch
  reverb: number; // User-set reverb
  filter: number; // User-set filter
  // Distance-calculated effects
  distancePitch: number;
  distanceFilter: number;
  distanceReverb: number;
  playing: boolean;
  oscillator?: OscillatorNode;
  audioSourceNode?: AudioBufferSourceNode;
  gainNode?: GainNode;
  filterNode?: BiquadFilterNode;
  reverbNode?: DelayNode;
}

export type VolumeCurve = 'inverse_square' | 'exponential' | 'logarithmic' | 'linear';

export class EnhancedAudioSynthesisService {
  private audioContext: AudioContext | null = null;
  private audioTracks = new Map<string, AudioTrack>();
  private audioBuffers = new Map<string, AudioBuffer>();
  private globalVolume = 0.7;
  private maxVolumeLimit = 0.8;
  private maxDistance = 200;
  private minDistance = 5;
  private volumeCurve: VolumeCurve = 'inverse_square';
  
  private distanceEffects: DistanceEffects = {
    enabled: true,
    pitchEffect: true,
    filterEffect: true,
    reverbEffect: true,
    pitchRange: 0.3,
    filterRange: 0.7,
    reverbRange: 0.4
  };

  // Comprehensive audio sources
  private audioSources: AudioSource[] = [
    // Animal Sounds
    { id: 'cow_moo', name: '🐄 Cow Mooing', type: 'audio', file: 'cow_moo.wav', category: 'animals' },
    { id: 'dog_bark', name: '🐕 Dog Barking', type: 'audio', file: 'dog_bark.wav', category: 'animals' },
    { id: 'cat_meow', name: '🐱 Cat Meowing', type: 'audio', file: 'cat_meow.wav', category: 'animals' },
    { id: 'bird_chirp', name: '🐦 Bird Chirping', type: 'audio', file: 'bird_chirp.wav', category: 'animals' },
    
    // Vehicle Sounds
    { id: 'car_horn', name: '🚗 Car Horn', type: 'audio', file: 'car_horn.wav', category: 'vehicles' },
    { id: 'car_engine', name: '🚙 Car Engine', type: 'audio', file: 'car_engine.wav', category: 'vehicles' },
    { id: 'motorcycle', name: '🏍️ Motorcycle', type: 'audio', file: 'motorcycle.wav', category: 'vehicles' },
    { id: 'truck_horn', name: '🚛 Truck Horn', type: 'audio', file: 'truck_horn.wav', category: 'vehicles' },
    
    // Music & Musical Instruments
    { id: 'piano_melody', name: '🎹 Piano Melody', type: 'audio', file: 'piano_melody.wav', category: 'music' },
    { id: 'guitar_strum', name: '🎸 Guitar Strum', type: 'audio', file: 'guitar_strum.wav', category: 'music' },
    { id: 'drums_beat', name: '🥁 Drum Beat', type: 'audio', file: 'drums_beat.wav', category: 'music' },
    { id: 'violin_note', name: '🎻 Violin Note', type: 'audio', file: 'violin_note.wav', category: 'music' },
    
    // Environmental/Nature
    { id: 'rain_drops', name: '🌧️ Rain Drops', type: 'audio', file: 'rain_drops.wav', category: 'nature' },
    { id: 'ocean_waves', name: '🌊 Ocean Waves', type: 'audio', file: 'ocean_waves.wav', category: 'nature' },
    { id: 'wind_blow', name: '💨 Wind Blowing', type: 'audio', file: 'wind_blow.wav', category: 'nature' },
    { id: 'forest_ambient', name: '🌲 Forest Ambient', type: 'audio', file: 'forest_ambient.wav', category: 'nature' },
    
    // Urban/Industrial
    { id: 'construction', name: '🔨 Construction', type: 'audio', file: 'construction.wav', category: 'urban' },
    { id: 'subway_train', name: '🚇 Subway Train', type: 'audio', file: 'subway_train.wav', category: 'urban' },
    { id: 'police_siren', name: '🚨 Police Siren', type: 'audio', file: 'police_siren.wav', category: 'urban' },
    { id: 'crowd_chatter', name: '👥 Crowd Chatter', type: 'audio', file: 'crowd_chatter.wav', category: 'urban' },
    
    // Oscillators (for testing)
    { id: 'osc_bass', name: '🎵 Bass Tone', type: 'oscillator', frequency: 60, category: 'synth' },
    { id: 'osc_mid', name: '🎵 Mid Tone', type: 'oscillator', frequency: 440, category: 'synth' },
    { id: 'osc_high', name: '🎵 High Tone', type: 'oscillator', frequency: 1000, category: 'synth' }
  ];

  constructor() {
    this.initializeAudioContext();
  }

  private async initializeAudioContext(): Promise<void> {
    try {
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      console.log('🎵 Enhanced Audio Context initialized');
    } catch (error) {
      console.error('❌ Failed to initialize audio context:', error);
      throw error;
    }
  }

  // Get available audio sources
  getAudioSources(): AudioSource[] {
    return this.audioSources;
  }

  getAudioSourcesByCategory(category: string): AudioSource[] {
    return this.audioSources.filter(source => source.category === category);
  }

  // Set distance curve
  setVolumeCurve(curve: VolumeCurve): void {
    this.volumeCurve = curve;
    console.log(`📊 Volume curve set to: ${curve}`);
  }

  // Set distance range
  setDistanceRange(minDistance: number, maxDistance: number): void {
    this.minDistance = Math.max(0, minDistance);
    this.maxDistance = Math.max(this.minDistance + 1, maxDistance);
    console.log(`📏 Distance range: ${this.minDistance}-${this.maxDistance}cm`);
  }

  // Set volume limits
  setVolumeLimit(limit: number): void {
    this.maxVolumeLimit = Math.max(0.1, Math.min(1.0, limit));
    console.log(`🔊 Max volume limit: ${(this.maxVolumeLimit * 100).toFixed(0)}%`);
  }

  // Calculate volume from distance using selected curve
  private calculateVolumeFromDistance(distance: number): number {
    const clampedDistance = Math.max(this.minDistance, Math.min(this.maxDistance, distance));
    const normalizedDistance = (clampedDistance - this.minDistance) / (this.maxDistance - this.minDistance);
    
    let volumeRatio: number;
    
    switch (this.volumeCurve) {
      case 'inverse_square':
        // Realistic physics: I ∝ 1/r²
        const effectiveDistance = normalizedDistance * 0.9 + 0.1; // Avoid division by zero
        volumeRatio = 1 / (effectiveDistance * effectiveDistance);
        volumeRatio = Math.min(1, volumeRatio / 100); // Normalize
        break;
        
      case 'exponential':
        // Exponential decay: V = e^(-k*d)
        const decayConstant = 4;
        volumeRatio = Math.exp(-decayConstant * normalizedDistance);
        break;
        
      case 'logarithmic':
        // Logarithmic: V = -log(d+1)
        volumeRatio = Math.max(0, 1 - Math.log10(normalizedDistance * 9 + 1));
        break;
        
      case 'linear':
      default:
        volumeRatio = 1 - normalizedDistance;
        break;
    }
    
    return Math.max(0, Math.min(1, volumeRatio)) * this.maxVolumeLimit;
  }

  // Calculate distance-based effects (pitch, filter, reverb)
  private calculateDistanceEffects(distance: number): { pitch: number; filter: number; reverb: number } {
    if (!this.distanceEffects.enabled) {
      return { pitch: 1, filter: 1, reverb: 0 };
    }

    const clampedDistance = Math.max(this.minDistance, Math.min(this.maxDistance, distance));
    const normalizedDistance = (clampedDistance - this.minDistance) / (this.maxDistance - this.minDistance);
    
    // Pitch effect: closer = slightly higher pitch (0.85 to 1.15)
    let pitch = 1;
    if (this.distanceEffects.pitchEffect) {
      pitch = 1 + (1 - normalizedDistance) * this.distanceEffects.pitchRange * 0.5 - this.distanceEffects.pitchRange * 0.25;
      pitch = Math.max(0.5, Math.min(2, pitch));
    }
    
    // Filter effect: closer = brighter (30% to 100%)
    let filter = 1;
    if (this.distanceEffects.filterEffect) {
      filter = 0.3 + (1 - normalizedDistance) * this.distanceEffects.filterRange;
      filter = Math.max(0.1, Math.min(1, filter));
    }
    
    // Reverb effect: farther = more reverb (0% to 40%)
    let reverb = 0;
    if (this.distanceEffects.reverbEffect) {
      reverb = normalizedDistance * this.distanceEffects.reverbRange;
      reverb = Math.max(0, Math.min(0.8, reverb));
    }
    
    return { pitch, filter, reverb };
  }

  // Load audio file
  private async loadAudioFile(filename: string): Promise<AudioBuffer> {
    if (this.audioBuffers.has(filename)) {
      return this.audioBuffers.get(filename)!;
    }

    try {
      const response = await fetch(`/audio/${filename}`);
      if (!response.ok) {
        throw new Error(`Failed to load audio file: ${filename}`);
      }
      
      const arrayBuffer = await response.arrayBuffer();
      const audioBuffer = await this.audioContext!.decodeAudioData(arrayBuffer);
      
      this.audioBuffers.set(filename, audioBuffer);
      console.log(`🎵 Loaded audio file: ${filename}`);
      return audioBuffer;
    } catch (error) {
      console.error(`❌ Failed to load ${filename}:`, error);
      throw error;
    }
  }

  // Create or update audio track
  async setAudioTrack(deviceId: string, deviceName: string, audioSource: AudioSource): Promise<void> {
    // Stop existing track if any
    if (this.audioTracks.has(deviceId)) {
      this.stopAudioTrack(deviceId);
    }

    const track: AudioTrack = {
      deviceId,
      deviceName,
      audioSource,
      volume: 0,
      nodeVolume: 0.7, // Default user volume
      pitch: 1.0, // Default user pitch
      reverb: 0.2, // Default user reverb
      filter: 1.0, // Default user filter
      distancePitch: 1.0,
      distanceFilter: 1.0,
      distanceReverb: 0.0,
      playing: false
    };

    this.audioTracks.set(deviceId, track);
    console.log(`🎵 Set ${audioSource.name} for ${deviceName}`);
  }

  // Update sensor distance and recalculate audio
  updateSensorDistance(deviceId: string, distance: number): void {
    const track = this.audioTracks.get(deviceId);
    if (!track) return;

    // Calculate new volume and effects
    const newVolume = this.calculateVolumeFromDistance(distance);
    const effects = this.calculateDistanceEffects(distance);

    track.volume = newVolume;
    track.distancePitch = effects.pitch;
    track.distanceFilter = effects.filter;
    track.distanceReverb = effects.reverb;

    // Update audio if playing
    if (track.playing) {
      this.updateAudioTrack(track);
    }

    // Auto start/stop based on volume
    if (newVolume > 0 && !track.playing) {
      this.startAudioTrack(deviceId);
    } else if (newVolume === 0 && track.playing) {
      this.stopAudioTrack(deviceId);
    }
  }

  // Start audio track
  async startAudioTrack(deviceId: string): Promise<void> {
    const track = this.audioTracks.get(deviceId);
    if (!track || track.playing || !this.audioContext) return;

    try {
      if (track.audioSource.type === 'oscillator') {
        // Create oscillator
        track.oscillator = this.audioContext.createOscillator();
        track.oscillator.frequency.setValueAtTime(
          track.audioSource.frequency! * track.pitch * track.distancePitch,
          this.audioContext.currentTime
        );
        track.oscillator.type = 'sine';
      } else if (track.audioSource.type === 'audio' && track.audioSource.file) {
        // Load and create audio source
        const buffer = await this.loadAudioFile(track.audioSource.file);
        track.audioSourceNode = this.audioContext.createBufferSource();
        track.audioSourceNode.buffer = buffer;
        track.audioSourceNode.loop = true;
        track.audioSourceNode.playbackRate.setValueAtTime(
          track.pitch * track.distancePitch,
          this.audioContext.currentTime
        );
      }

      // Create audio processing chain
      track.gainNode = this.audioContext.createGain();
      track.filterNode = this.audioContext.createBiquadFilter();
      track.reverbNode = this.audioContext.createDelay();

      // Configure filter
      track.filterNode.type = 'lowpass';
      track.filterNode.frequency.setValueAtTime(
        22050 * track.filter * track.distanceFilter,
        this.audioContext.currentTime
      );

      // Configure reverb (simple delay-based)
      track.reverbNode.delayTime.setValueAtTime(
        0.03 + (track.reverb + track.distanceReverb) * 0.1,
        this.audioContext.currentTime
      );

      // Connect audio chain
      const source = track.oscillator || track.audioSourceNode;
      if (source) {
        source.connect(track.filterNode);
        track.filterNode.connect(track.gainNode);
        track.gainNode.connect(this.audioContext.destination);
        
        // Add reverb (mix with dry signal)
        const reverbGain = this.audioContext.createGain();
        reverbGain.gain.setValueAtTime(track.reverb + track.distanceReverb, this.audioContext.currentTime);
        track.filterNode.connect(track.reverbNode);
        track.reverbNode.connect(reverbGain);
        reverbGain.connect(this.audioContext.destination);

        // Start playback
        source.start();
        track.playing = true;
        
        // Update track with current settings
        this.updateAudioTrack(track);
        
        console.log(`▶️ Started ${track.audioSource.name} for ${track.deviceName}`);
      }
    } catch (error) {
      console.error(`❌ Failed to start audio for ${deviceName}:`, error);
    }
  }

  // Stop audio track
  stopAudioTrack(deviceId: string): void {
    const track = this.audioTracks.get(deviceId);
    if (!track || !track.playing) return;

    try {
      if (track.oscillator) {
        track.oscillator.stop();
        track.oscillator.disconnect();
        track.oscillator = undefined;
      }
      
      if (track.audioSourceNode) {
        track.audioSourceNode.stop();
        track.audioSourceNode.disconnect();
        track.audioSourceNode = undefined;
      }
      
      if (track.gainNode) {
        track.gainNode.disconnect();
        track.gainNode = undefined;
      }
      
      if (track.filterNode) {
        track.filterNode.disconnect();
        track.filterNode = undefined;
      }
      
      if (track.reverbNode) {
        track.reverbNode.disconnect();
        track.reverbNode = undefined;
      }

      track.playing = false;
      console.log(`⏹️ Stopped ${track.audioSource.name} for ${track.deviceName}`);
    } catch (error) {
      console.error(`❌ Failed to stop audio for ${track.deviceName}:`, error);
    }
  }

  // Update audio track parameters
  private updateAudioTrack(track: AudioTrack): void {
    if (!track.playing || !this.audioContext) return;

    const currentTime = this.audioContext.currentTime;
    const combinedVolume = track.volume * track.nodeVolume * this.globalVolume;

    // Update volume
    if (track.gainNode) {
      track.gainNode.gain.setValueAtTime(combinedVolume, currentTime);
    }

    // Update pitch/playback rate
    const combinedPitch = track.pitch * track.distancePitch;
    if (track.oscillator) {
      track.oscillator.frequency.setValueAtTime(
        track.audioSource.frequency! * combinedPitch,
        currentTime
      );
    }
    if (track.audioSourceNode) {
      track.audioSourceNode.playbackRate.setValueAtTime(combinedPitch, currentTime);
    }

    // Update filter
    if (track.filterNode) {
      const combinedFilter = track.filter * track.distanceFilter;
      track.filterNode.frequency.setValueAtTime(22050 * combinedFilter, currentTime);
    }

    // Update reverb
    if (track.reverbNode) {
      const combinedReverb = Math.min(0.5, track.reverb + track.distanceReverb);
      track.reverbNode.delayTime.setValueAtTime(0.03 + combinedReverb * 0.1, currentTime);
    }
  }

  // Set user controls for a track
  setTrackVolume(deviceId: string, volume: number): void {
    const track = this.audioTracks.get(deviceId);
    if (track) {
      track.nodeVolume = Math.max(0, Math.min(1, volume));
      if (track.playing) this.updateAudioTrack(track);
    }
  }

  setTrackPitch(deviceId: string, pitch: number): void {
    const track = this.audioTracks.get(deviceId);
    if (track) {
      track.pitch = Math.max(0.5, Math.min(2, pitch));
      if (track.playing) this.updateAudioTrack(track);
    }
  }

  setTrackReverb(deviceId: string, reverb: number): void {
    const track = this.audioTracks.get(deviceId);
    if (track) {
      track.reverb = Math.max(0, Math.min(1, reverb));
      if (track.playing) this.updateAudioTrack(track);
    }
  }

  setTrackFilter(deviceId: string, filter: number): void {
    const track = this.audioTracks.get(deviceId);
    if (track) {
      track.filter = Math.max(0.1, Math.min(1, filter));
      if (track.playing) this.updateAudioTrack(track);
    }
  }

  // Set global volume
  setGlobalVolume(volume: number): void {
    this.globalVolume = Math.max(0, Math.min(1, volume));
    
    // Update all playing tracks
    this.audioTracks.forEach(track => {
      if (track.playing) this.updateAudioTrack(track);
    });
  }

  // Distance effects controls
  setDistanceEffects(effects: Partial<DistanceEffects>): void {
    this.distanceEffects = { ...this.distanceEffects, ...effects };
    console.log('🎛️ Distance effects updated:', this.distanceEffects);
  }

  // Get track status
  getTrackStatus(deviceId: string): any {
    const track = this.audioTracks.get(deviceId);
    if (!track) return null;

    return {
      deviceName: track.deviceName,
      audioSource: track.audioSource.name,
      volume: Math.round(track.volume * 100),
      nodeVolume: Math.round(track.nodeVolume * 100),
      pitch: track.pitch.toFixed(2),
      reverb: Math.round(track.reverb * 100),
      filter: Math.round(track.filter * 100),
      distanceEffects: {
        pitch: track.distancePitch.toFixed(2),
        filter: Math.round(track.distanceFilter * 100),
        reverb: Math.round(track.distanceReverb * 100)
      },
      playing: track.playing
    };
  }

  // Get all tracks status
  getAllTracksStatus(): { [deviceId: string]: any } {
    const status: { [deviceId: string]: any } = {};
    this.audioTracks.forEach((track, deviceId) => {
      status[deviceId] = this.getTrackStatus(deviceId);
    });
    return status;
  }

  // Remove audio track
  removeAudioTrack(deviceId: string): void {
    this.stopAudioTrack(deviceId);
    this.audioTracks.delete(deviceId);
  }

  // Cleanup
  dispose(): void {
    this.audioTracks.forEach((_, deviceId) => {
      this.removeAudioTrack(deviceId);
    });
    
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
    
    console.log('🔇 Enhanced Audio Service disposed');
  }
}
