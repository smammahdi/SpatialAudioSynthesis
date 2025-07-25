// Simplified Audio Sources - Only Sine Waves + Custom Uploads
export interface AudioSource {
  id: string;
  name: string;
  type: 'sine' | 'custom';
  frequency?: number; // For sine waves
  filename?: string; // For custom uploads
  category: string;
}

export const defaultAudioSources: AudioSource[] = [
  // Pure Sine Waves for Testing
  { 
    id: 'sine-220', 
    name: 'Low Sine (220Hz)', 
    type: 'sine', 
    frequency: 220, 
    category: 'Test Tones' 
  },
  { 
    id: 'sine-440', 
    name: 'A4 Sine (440Hz)', 
    type: 'sine', 
    frequency: 440, 
    category: 'Test Tones' 
  },
  { 
    id: 'sine-880', 
    name: 'High Sine (880Hz)', 
    type: 'sine', 
    frequency: 880, 
    category: 'Test Tones' 
  },
  { 
    id: 'sine-1000', 
    name: 'Reference Tone (1kHz)', 
    type: 'sine', 
    frequency: 1000, 
    category: 'Test Tones' 
  }
];

export class AudioSourceManager {
  private customSources: AudioSource[] = [];
  
  getAllSources(): AudioSource[] {
    return [...defaultAudioSources, ...this.customSources];
  }
  
  addCustomSource(source: AudioSource): void {
    this.customSources.push(source);
  }
  
  removeCustomSource(id: string): void {
    this.customSources = this.customSources.filter(s => s.id !== id);
  }
  
  getSourceById(id: string): AudioSource | undefined {
    return this.getAllSources().find(s => s.id === id);
  }
  
  getCustomSources(): AudioSource[] {
    return [...this.customSources];
  }
}
