"""
pygame_app/src/audio_engine.py
Enhanced Spatial Audio Engine
Advanced audio synthesis and real-time mixing for spatial audio applications
"""

import pygame
import numpy as np
import threading
import time
import os
import queue
from typing import Dict, List, Optional, Tuple, Callable, Any
from dataclasses import dataclass
from enum import Enum
import wave
import json

class AudioFileType(Enum):
    SINE_WAVE = "sine_wave"
    AUDIO_FILE = "audio_file"
    SYNTHESIZED = "synthesized"

@dataclass
class AudioSource:
    """Represents an audio source that can be assigned to devices"""
    id: str
    name: str
    file_type: AudioFileType
    file_path: Optional[str] = None
    frequency: Optional[float] = None
    waveform: Optional[np.ndarray] = None

@dataclass
class AudioChannel:
    """Represents an active audio channel for a device"""
    device_id: str
    audio_source: AudioSource
    current_volume: float
    current_frequency: float
    is_playing: bool
    last_update: float
    is_enabled: bool = True

class SpatialAudioEngine:
    """Enhanced spatial audio synthesis engine with real-time mixing"""
    
    def __init__(self):
        """Initialize the enhanced audio engine"""
        self.channels: Dict[str, AudioChannel] = {}
        self.audio_sources: Dict[str, AudioSource] = {}
        self.master_volume = 0.75
        self.enabled = True
        self.sample_rate = 44100
        self.buffer_size = 1024
        
        # Real-time audio mixing
        self.mixing_enabled = True
        self.mixed_audio_queue = queue.Queue(maxsize=10)
        self.audio_thread = None
        self.mixing_thread = None
        self.running = False
        
        # Audio processing parameters
        self.fade_duration = 0.01  # 10ms fade to prevent clicks
        self.max_concurrent_sounds = 8
        
        # Initialize pygame mixer with optimal settings
        try:
            pygame.mixer.quit()  # Ensure clean state
            pygame.mixer.init(
                frequency=self.sample_rate,
                size=-16,  # 16-bit signed
                channels=2,  # Stereo
                buffer=self.buffer_size
            )
            print(f"Audio engine initialized: {self.sample_rate}Hz, {self.buffer_size} buffer")
        except Exception as e:
            print(f"Audio initialization error: {e}")
            # Fallback initialization
            pygame.mixer.init()
            
        # Create default audio sources
        self._create_default_sources()
        
        # Start real-time audio processing
        self._start_audio_processing()
        
        print("Enhanced Spatial Audio Engine initialized")
        
    def _create_default_sources(self):
        """Create default sine wave audio sources with better variety"""
        # Musical frequencies
        musical_sources = [
            (220.0, "A3 - Low Tone"),
            (261.63, "C4 - Middle C"),
            (329.63, "E4 - Major Third"),
            (440.0, "A4 - Concert Pitch"),
            (523.25, "C5 - High C"),
            (659.25, "E5 - High E"),
            (880.0, "A5 - High A"),
            (1000.0, "B5 - Pure Tone")
        ]
        
        for freq, name in musical_sources:
            source_id = f"sine_{int(freq)}"
            self.audio_sources[source_id] = AudioSource(
                id=source_id,
                name=name,
                file_type=AudioFileType.SINE_WAVE,
                frequency=freq
            )
        
        # Add special waveforms
        self._create_special_waveforms()
            
    def _create_special_waveforms(self):
        """Create special synthesized waveforms"""
        special_sources = [
            ("square_440", "Square Wave (440Hz)", self._generate_square_wave, 440.0),
            ("sawtooth_440", "Sawtooth Wave (440Hz)", self._generate_sawtooth_wave, 440.0),
            ("triangle_440", "Triangle Wave (440Hz)", self._generate_triangle_wave, 440.0),
            ("pulse_440", "Pulse Wave (440Hz)", self._generate_pulse_wave, 440.0)
        ]
        
        for source_id, name, generator, freq in special_sources:
            waveform = generator(freq, 1.0)  # 1 second sample
            self.audio_sources[source_id] = AudioSource(
                id=source_id,
                name=name,
                file_type=AudioFileType.SYNTHESIZED,
                frequency=freq,
                waveform=waveform
            )
    
    def _generate_square_wave(self, frequency: float, duration: float) -> np.ndarray:
        """Generate a square wave"""
        samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, samples, False)
        return np.sign(np.sin(2 * np.pi * frequency * t))
    
    def _generate_sawtooth_wave(self, frequency: float, duration: float) -> np.ndarray:
        """Generate a sawtooth wave"""
        samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, samples, False)
        return 2 * (t * frequency - np.floor(t * frequency + 0.5))
    
    def _generate_triangle_wave(self, frequency: float, duration: float) -> np.ndarray:
        """Generate a triangle wave"""
        samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, samples, False)
        return 2 * np.abs(2 * (t * frequency - np.floor(t * frequency + 0.5))) - 1
    
    def _generate_pulse_wave(self, frequency: float, duration: float, duty_cycle: float = 0.3) -> np.ndarray:
        """Generate a pulse wave with adjustable duty cycle"""
        samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, samples, False)
        phase = (t * frequency) % 1
        return np.where(phase < duty_cycle, 1.0, -1.0)
        
    def _start_audio_processing(self):
        """Start the real-time audio processing threads"""
        if self.running:
            return
            
        self.running = True
        
        # Start mixing thread
        self.mixing_thread = threading.Thread(target=self._mixing_worker, daemon=True)
        self.mixing_thread.start()
        
        print("Real-time audio processing started")
        
    def _mixing_worker(self):
        """Real-time audio mixing worker thread"""
        while self.running:
            try:
                if self.mixing_enabled and self.channels:
                    self._process_active_channels()
                time.sleep(0.05)  # 20Hz update rate for smooth mixing
            except Exception as e:
                print(f"Mixing worker error: {e}")
                
    def _process_active_channels(self):
        """Process and mix active audio channels"""
        current_time = time.time()
        active_channels = []
        
        # Get currently active channels
        for channel in self.channels.values():
            if (channel.is_enabled and 
                current_time - channel.last_update < 0.5 and  # Active within 500ms
                channel.current_volume > 0.01):  # Audible volume
                active_channels.append(channel)
        
        if not active_channels:
            return
            
        # Limit concurrent sounds for performance
        if len(active_channels) > self.max_concurrent_sounds:
            # Sort by volume and take the loudest ones
            active_channels.sort(key=lambda c: c.current_volume, reverse=True)
            active_channels = active_channels[:self.max_concurrent_sounds]
        
        # Generate mixed audio for active channels
        self._generate_mixed_audio(active_channels)
    
    def _generate_mixed_audio(self, channels: List[AudioChannel]):
        """Generate and mix audio from multiple channels"""
        if not channels:
            return
            
        try:
            duration = 0.1  # 100ms chunks for smooth playback
            samples = int(self.sample_rate * duration)
            mixed_audio = np.zeros((samples, 2), dtype=np.float32)
            
            for channel in channels:
                if not channel.is_enabled:
                    continue
                    
                # Generate audio for this channel
                channel_audio = self._generate_channel_audio(channel, duration)
                if channel_audio is not None:
                    # Apply volume and add to mix
                    volume = channel.current_volume * self.master_volume
                    volume = max(0.0, min(1.0, volume))  # Clamp volume
                    
                    # Ensure stereo format
                    if len(channel_audio.shape) == 1:
                        stereo_audio = np.column_stack((channel_audio, channel_audio))
                    else:
                        stereo_audio = channel_audio
                    
                    # Add to mixed audio with volume control
                    if stereo_audio.shape[0] == samples:
                        mixed_audio += stereo_audio * volume
            
            # Normalize to prevent clipping
            max_amplitude = np.max(np.abs(mixed_audio))
            if max_amplitude > 0.95:
                mixed_audio *= 0.95 / max_amplitude
            
            # Convert to 16-bit and play
            mixed_audio_16bit = (mixed_audio * 32767).astype(np.int16)
            
            # Play the mixed audio
            if not pygame.mixer.get_busy() or pygame.mixer.get_num_channels() < 4:
                try:
                    sound = pygame.sndarray.make_sound(mixed_audio_16bit)
                    sound.play()
                except Exception as e:
                    print(f"Audio playback error: {e}")
                    
        except Exception as e:
            print(f"Mixed audio generation error: {e}")
    
    def _generate_channel_audio(self, channel: AudioChannel, duration: float) -> Optional[np.ndarray]:
        """Generate audio for a specific channel"""
        try:
            audio_source = channel.audio_source
            frequency = channel.current_frequency
            
            if audio_source.file_type == AudioFileType.SINE_WAVE:
                return self._generate_sine_wave_audio(frequency, duration)
            elif audio_source.file_type == AudioFileType.SYNTHESIZED:
                return self._generate_synthesized_audio(audio_source, frequency, duration)
            elif audio_source.file_type == AudioFileType.AUDIO_FILE:
                return self._generate_file_audio(audio_source, duration)
                
        except Exception as e:
            print(f"Channel audio generation error: {e}")
            return None
    
    def _generate_sine_wave_audio(self, frequency: float, duration: float) -> np.ndarray:
        """Generate sine wave audio"""
        samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, samples, False)
        wave_data = np.sin(2 * np.pi * frequency * t)
        
        # Apply fade envelope
        envelope_samples = int(self.fade_duration * self.sample_rate)
        if samples > 2 * envelope_samples:
            # Fade in
            wave_data[:envelope_samples] *= np.linspace(0, 1, envelope_samples)
            # Fade out
            wave_data[-envelope_samples:] *= np.linspace(1, 0, envelope_samples)
        
        return wave_data
    
    def _generate_synthesized_audio(self, audio_source: AudioSource, frequency: float, duration: float) -> np.ndarray:
        """Generate audio from synthesized waveforms"""
        if audio_source.waveform is None:
            return self._generate_sine_wave_audio(frequency, duration)
        
        # Use the pre-generated waveform, scaled to the requested frequency
        base_frequency = audio_source.frequency or 440.0
        frequency_ratio = frequency / base_frequency
        
        # Resample the waveform for the new frequency
        samples = int(self.sample_rate * duration)
        waveform_samples = len(audio_source.waveform)
        
        # Simple resampling by adjusting playback speed
        indices = np.arange(samples) * frequency_ratio * waveform_samples / samples
        indices = indices.astype(int) % waveform_samples
        
        wave_data = audio_source.waveform[indices]
        
        # Apply fade envelope
        envelope_samples = int(self.fade_duration * self.sample_rate)
        if samples > 2 * envelope_samples:
            wave_data[:envelope_samples] *= np.linspace(0, 1, envelope_samples)
            wave_data[-envelope_samples:] *= np.linspace(1, 0, envelope_samples)
        
        return wave_data
    
    def _generate_file_audio(self, audio_source: AudioSource, duration: float) -> Optional[np.ndarray]:
        """Generate audio from file source"""
        if not audio_source.file_path or not os.path.exists(audio_source.file_path):
            return None
        
        try:
            # Load audio file (simplified - in practice, you'd want more robust loading)
            sound = pygame.mixer.Sound(audio_source.file_path)
            # For now, fall back to sine wave
            return self._generate_sine_wave_audio(440.0, duration)
        except Exception as e:
            print(f"File audio generation error: {e}")
            return None
            
    def register_audio_file(self, file_name: str, file_path: str) -> str:
        """Register a new audio file"""
        source_id = f"file_{len(self.audio_sources)}"
        
        self.audio_sources[source_id] = AudioSource(
            id=source_id,
            name=file_name,
            file_type=AudioFileType.AUDIO_FILE,
            file_path=file_path
        )
        
        print(f"Registered audio file: {file_name}")
        return source_id
        
    def get_audio_sources(self) -> List[AudioSource]:
        """Get list of all available audio sources"""
        return list(self.audio_sources.values())
        
    def synthesize_audio(self, device_id: str, frequency: float, volume: float, 
                        audio_file: Optional[str] = None, duration: float = 0.5):
        """Synthesize audio for a specific device with enhanced real-time mixing"""
        if not self.enabled:
            return
            
        try:
            # Get or create audio channel
            if device_id not in self.channels:
                # Default to first sine wave if no audio file specified
                source_id = audio_file or "sine_440"
                audio_source = self.audio_sources.get(source_id)
                
                if not audio_source:
                    print(f"Audio source not found: {source_id}, using default")
                    audio_source = list(self.audio_sources.values())[0]
                    
                self.channels[device_id] = AudioChannel(
                    device_id=device_id,
                    audio_source=audio_source,
                    current_volume=volume,
                    current_frequency=frequency,
                    is_playing=False,
                    last_update=time.time(),
                    is_enabled=True
                )
                
            channel = self.channels[device_id]
            
            # Update channel parameters
            channel.current_volume = volume
            channel.current_frequency = frequency
            channel.last_update = time.time()
            channel.is_playing = True
            
            # If real-time mixing is disabled, play individual sounds
            if not self.mixing_enabled:
                self._play_individual_sound(channel, duration)
                
        except Exception as e:
            print(f"Audio synthesis error: {e}")
    
    def _play_individual_sound(self, channel: AudioChannel, duration: float):
        """Play individual sound for a channel (fallback mode)"""
        try:
            audio_data = self._generate_channel_audio(channel, duration)
            if audio_data is not None:
                # Apply volume
                volume = min(1.0, max(0.0, channel.current_volume * self.master_volume))
                audio_data = audio_data * volume
                
                # Convert to 16-bit integers
                audio_data = (audio_data * 32767).astype(np.int16)
                
                # Create stereo sound
                if len(audio_data.shape) == 1:
                    stereo_wave = np.column_stack((audio_data, audio_data))
                else:
                    stereo_wave = audio_data
                
                # Create pygame sound and play
                sound = pygame.sndarray.make_sound(stereo_wave)
                sound.play()
                
        except Exception as e:
            print(f"Individual sound playback error: {e}")
            
    def assign_audio_to_device(self, device_id: str, audio_source_id: str):
        """Assign an audio source to a device"""
        audio_source = self.audio_sources.get(audio_source_id)
        if not audio_source:
            print(f"Audio source not found: {audio_source_id}")
            return False
            
        if device_id in self.channels:
            self.channels[device_id].audio_source = audio_source
        else:
            self.channels[device_id] = AudioChannel(
                device_id=device_id,
                audio_source=audio_source,
                current_volume=0.5,
                current_frequency=audio_source.frequency or 440.0,
                is_playing=False,
                last_update=time.time(),
                is_enabled=True
            )
            
        print(f"Assigned {audio_source.name} to device {device_id}")
        return True
    
    def enable_device_audio(self, device_id: str, enabled: bool):
        """Enable or disable audio for a specific device"""
        if device_id in self.channels:
            self.channels[device_id].is_enabled = enabled
            status = "enabled" if enabled else "disabled"
            print(f"Device {device_id} audio {status}")
        
    def get_device_audio_source(self, device_id: str) -> Optional[AudioSource]:
        """Get the audio source assigned to a device"""
        channel = self.channels.get(device_id)
        return channel.audio_source if channel else None
        
    def set_master_volume(self, volume: float):
        """Set master volume (0.0 to 1.0)"""
        self.master_volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(self.master_volume)
        print(f"Master volume set to {self.master_volume:.1%}")
        
    def set_mixing_enabled(self, enabled: bool):
        """Enable or disable real-time audio mixing"""
        self.mixing_enabled = enabled
        status = "enabled" if enabled else "disabled"
        print(f"Real-time audio mixing {status}")
        
    def enable(self):
        """Enable audio synthesis"""
        self.enabled = True
        print("Audio synthesis enabled")
        
    def disable(self):
        """Disable audio synthesis"""
        self.enabled = False
        # Stop all currently playing sounds
        pygame.mixer.stop()
        print("Audio synthesis disabled")
        
    def get_active_channels(self) -> List[AudioChannel]:
        """Get list of active audio channels"""
        current_time = time.time()
        active_channels = []
        
        for channel in self.channels.values():
            if (channel.is_enabled and 
                current_time - channel.last_update < 5.0):  # Active within 5 seconds
                active_channels.append(channel)
                
        return active_channels
    
    def get_enabled_channels(self) -> List[AudioChannel]:
        """Get list of enabled audio channels"""
        return [channel for channel in self.channels.values() if channel.is_enabled]
        
    def generate_test_tone(self, frequency: float = 440.0, volume: float = 0.5, duration: float = 1.0) -> bool:
        """Generate a test tone for system verification"""
        try:
            print(f"Generating test tone: {frequency}Hz, volume: {volume:.1%}, duration: {duration}s")
            
            # Generate test tone
            samples = int(self.sample_rate * duration)
            t = np.linspace(0, duration, samples, False)
            wave_data = np.sin(2 * np.pi * frequency * t) * volume
            
            # Apply envelope
            envelope_samples = int(0.05 * self.sample_rate)  # 50ms envelope
            if samples > 2 * envelope_samples:
                wave_data[:envelope_samples] *= np.linspace(0, 1, envelope_samples)
                wave_data[-envelope_samples:] *= np.linspace(1, 0, envelope_samples)
            
            # Convert to 16-bit
            wave_data = (wave_data * 32767).astype(np.int16)
            stereo_wave = np.column_stack((wave_data, wave_data))
            
            # Play sound
            sound = pygame.sndarray.make_sound(stereo_wave)
            sound.play()
            
            print("Test tone playback initiated")
            return True
            
        except Exception as e:
            print(f"Test tone generation failed: {e}")
            return False
    
    def get_engine_stats(self) -> Dict[str, Any]:
        """Get engine statistics for monitoring"""
        current_time = time.time()
        
        stats = {
            'total_channels': len(self.channels),
            'active_channels': len(self.get_active_channels()),
            'enabled_channels': len(self.get_enabled_channels()),
            'master_volume': self.master_volume,
            'mixing_enabled': self.mixing_enabled,
            'audio_sources': len(self.audio_sources),
            'sample_rate': self.sample_rate,
            'buffer_size': self.buffer_size
        }
        
        return stats
            
    def update(self, dt: float):
        """Update audio engine state"""
        # Clean up inactive channels
        current_time = time.time()
        inactive_devices = []
        
        for device_id, channel in self.channels.items():
            if current_time - channel.last_update > 30.0:  # 30 seconds timeout
                inactive_devices.append(device_id)
                
        for device_id in inactive_devices:
            del self.channels[device_id]
            print(f"Cleaned up inactive channel: {device_id}")
            
    def cleanup(self):
        """Clean up audio engine resources"""
        print("Cleaning up audio engine...")
        self.running = False
        self.enabled = False
        
        # Wait for threads to finish
        if self.mixing_thread and self.mixing_thread.is_alive():
            self.mixing_thread.join(timeout=1.0)
        
        # Stop all audio
        pygame.mixer.stop()
        pygame.mixer.quit()
        
        print("Audio engine cleanup complete")