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

# Import centralized logging configuration
from .logging_config import (
    log_audio, log_audio_engine, log_audio_file, log_system, log_error
)

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
    # New fields for play-to-completion logic
    audio_start_time: float = 0.0
    # Spatial audio fields
    left_volume: float = 1.0
    right_volume: float = 1.0
    audio_duration: float = 0.0
    pending_volume: Optional[float] = None
    pending_frequency: Optional[float] = None

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
        self.mixing_enabled = False  # Temporarily disable mixing for better audio file support
        self.mixed_audio_queue = queue.Queue(maxsize=10)
        self.audio_thread = None
        self.mixing_thread = None
        self.running = False
        
        # Audio processing parameters
        self.fade_duration = 0.01  # 10ms fade to prevent clicks
        self.max_concurrent_sounds = 8
        
        # Initialize pygame mixer with optimal settings
        try:
            pygame.mixer.init(frequency=self.sample_rate, buffer=self.buffer_size)
            log_audio_engine(f"Audio engine initialized: {self.sample_rate}Hz, {self.buffer_size} buffer")
        except Exception as e:
            log_error(f"Audio initialization error: {e}")
            # Fallback initialization
            pygame.mixer.init()
            
        # Load audio files from the audio_files directory only
        self._load_project_audio_files()
        
        # Start real-time audio processing
        self._start_audio_processing()
        
        log_system("Enhanced Spatial Audio Engine initialized")
        
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
    
    def _load_project_audio_files(self):
        """Load only audio files from the project's audio_files directory"""
        try:
            # Clear existing audio sources to start fresh
            self.audio_sources.clear()
            
            # Get project root directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            audio_files_dir = os.path.join(project_root, "audio_files")
            
            if not os.path.exists(audio_files_dir):
                print(f"Creating audio_files directory: {audio_files_dir}")
                os.makedirs(audio_files_dir, exist_ok=True)
                print("Audio files directory created. Add audio files to get started.")
                return
            
            # Supported audio formats
            supported_formats = ['.wav', '.mp3', '.ogg', '.flac', '.m4a', '.aiff', '.mp4', '.wma']
            
            # Load each audio file
            loaded_count = 0
            for filename in sorted(os.listdir(audio_files_dir)):
                if any(filename.lower().endswith(fmt) for fmt in supported_formats):
                    file_path = os.path.join(audio_files_dir, filename)
                    
                    try:
                        # Create friendly name from filename
                        name = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ').title()
                        # Clean up common frequency patterns
                        name = name.replace('Hz', 'Hz').replace('hz', 'Hz')
                        
                        # Register the audio file
                        source_id = self.register_audio_file(name, file_path)
                        print(f"Loaded: {name}")
                        loaded_count += 1
                        
                    except Exception as e:
                        print(f"Failed to load audio file {filename}: {e}")
                        
            # Show final count
            if loaded_count > 0:
                print(f"Successfully loaded {loaded_count} audio files from audio_files directory")
            else:
                print("No audio files found in audio_files directory. Upload some audio files to get started.")
                
        except Exception as e:
            print(f"Error loading project audio files: {e}")
    
    def _reload_project_audio_files(self):
        """Reload all audio files from the project directory"""
        print("Reloading audio files from audio_files directory...")
        self._load_project_audio_files()
    
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
                # Always check for finished audio, regardless of mixing mode
                self._check_finished_audio()
                
                if self.mixing_enabled and self.channels:
                    self._process_active_channels()
                time.sleep(0.1)  # 10Hz update rate for checking finished audio
            except Exception as e:
                print(f"Mixing worker error: {e}")
    
    def _check_finished_audio(self):
        """Check for finished audio and start pending audio if available"""
        current_time = time.time()
        
        for channel in self.channels.values():
            if not channel.is_enabled:
                continue
                
            # Check if current audio has finished
            if channel.audio_start_time > 0:
                time_since_start = current_time - channel.audio_start_time
                
                if time_since_start >= channel.audio_duration:
                    # Audio finished!
                    log_audio(f"✅ Audio finished for device {channel.device_id}: {channel.audio_source.name}")
                    
                    # Check if we have pending parameters (new distance-based audio)
                    if (channel.pending_volume is not None or 
                        channel.pending_frequency is not None or
                        current_time - channel.last_update < 2.0):  # Recent distance update
                        
                        # Apply pending parameters
                        if channel.pending_volume is not None:
                            channel.current_volume = channel.pending_volume
                            channel.pending_volume = None
                        
                        if channel.pending_frequency is not None:
                            channel.current_frequency = channel.pending_frequency
                            channel.pending_frequency = None
                        
                        # Start new audio cycle with current parameters
                        log_audio(f"🔄 Starting next audio cycle for device {channel.device_id}")
                        self._start_audio_playback(channel, 0.5)  # Default duration for distance-based audio
                    else:
                        # No pending updates, mark as not playing
                        channel.is_playing = False
                        channel.audio_start_time = 0.0
                        channel.audio_duration = 0.0
                
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
            print(f"File not found: {audio_source.file_path}")
            return None
        
        try:
            # CRITICAL FIX: Actually play the loaded audio file!
            sound = pygame.mixer.Sound(audio_source.file_path)
            
            # Get the raw audio array from the pygame sound
            array = pygame.sndarray.array(sound)
            
            # Convert to float32 for processing
            if array.dtype == np.int16:
                audio_data = array.astype(np.float32) / 32767.0
            elif array.dtype == np.int32:
                audio_data = array.astype(np.float32) / 2147483647.0
            else:
                audio_data = array.astype(np.float32)
            
            # Handle stereo to mono conversion if needed
            if len(audio_data.shape) > 1 and audio_data.shape[1] > 1:
                audio_data = np.mean(audio_data, axis=1)
            
            # Trim or repeat audio to match requested duration
            samples_needed = int(self.sample_rate * duration)
            current_samples = len(audio_data)
            
            if current_samples >= samples_needed:
                # Trim to requested duration
                audio_data = audio_data[:samples_needed]
            else:
                # Repeat the audio to fill the duration
                repeats = (samples_needed // current_samples) + 1
                audio_data = np.tile(audio_data, repeats)[:samples_needed]
            
            log_audio(f"🎵 Playing file audio: {audio_source.name} ({duration:.1f}s, {len(audio_data)} samples)")
            return audio_data
            
        except Exception as e:
            print(f"File audio generation error: {e}")
            # Fallback to direct pygame playback
            try:
                sound = pygame.mixer.Sound(audio_source.file_path)
                sound.play()
                print(f"🔊 Fallback: Playing {audio_source.name} directly via pygame")
            except Exception as e2:
                print(f"Fallback playback failed: {e2}")
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
        """Synthesize audio for a specific device with play-to-completion logic"""
        if not self.enabled:
            return
            
        try:
            # Get the requested audio source
            source_id = audio_file or "sine_440"
            audio_source = self.audio_sources.get(source_id)
            
            if not audio_source:
                print(f"Audio source not found: {source_id}, using default")
                if self.audio_sources:
                    audio_source = list(self.audio_sources.values())[0]
                else:
                    print("No audio sources available!")
                    return
            
            current_time = time.time()
            
            # Get or create audio channel
            if device_id not in self.channels:
                # Create new channel
                self.channels[device_id] = AudioChannel(
                    device_id=device_id,
                    audio_source=audio_source,
                    current_volume=volume,
                    current_frequency=frequency,
                    is_playing=False,
                    last_update=current_time,
                    is_enabled=True,
                    audio_start_time=0.0,
                    audio_duration=0.0,
                    pending_volume=None,
                    pending_frequency=None
                )
                # Start playing immediately for new channels
                self._start_audio_playback(self.channels[device_id], duration)
            else:
                channel = self.channels[device_id]
                
                # Check if current audio is still playing
                time_since_start = current_time - channel.audio_start_time
                is_audio_finished = (channel.audio_start_time == 0.0 or 
                                   time_since_start >= channel.audio_duration)
                
                if is_audio_finished:
                    # Audio finished or not playing - start new audio immediately
                    channel.audio_source = audio_source
                    channel.current_volume = volume
                    channel.current_frequency = frequency
                    channel.last_update = current_time
                    
                    log_audio(f"🎵 Device {device_id}: Starting '{audio_source.name}' (ID: {audio_source.id}) at volume {volume:.2f}")
                    self._start_audio_playback(channel, duration)
                else:
                    # Audio still playing - store pending parameters
                    channel.pending_volume = volume
                    channel.pending_frequency = frequency
                    channel.last_update = current_time
                    
                    # Update audio source if it changed
                    if channel.audio_source.id != audio_source.id:
                        channel.audio_source = audio_source
                        print(f"🔄 Device {device_id}: Audio source changed to '{audio_source.name}' (will apply after current audio finishes)")
                    
                    # Debug: Show remaining time
                    remaining_time = channel.audio_duration - time_since_start
                    log_audio(f"⏳ Device {device_id}: Audio playing, {remaining_time:.1f}s remaining")
                
        except Exception as e:
            print(f"Audio synthesis error: {e}")
    
    def _start_audio_playback(self, channel: AudioChannel, duration: float):
        """Start audio playback for a channel and set timing information"""
        try:
            # Determine actual audio duration
            if channel.audio_source.file_type == AudioFileType.AUDIO_FILE:
                actual_duration = self._get_audio_file_duration(channel.audio_source)
                if actual_duration is None:
                    actual_duration = duration  # Fallback to requested duration
            else:
                actual_duration = duration  # For synthesized audio, use requested duration
            
            # Update channel timing
            channel.audio_start_time = time.time()
            channel.audio_duration = actual_duration
            channel.is_playing = True
            
            log_audio(f"🎬 Starting audio: {channel.audio_source.name} ({actual_duration:.1f}s duration)")
            
            # Play the audio
            if not self.mixing_enabled:
                self._play_individual_sound(channel, actual_duration)
                
        except Exception as e:
            print(f"Audio playback start error: {e}")
    
    def _get_audio_file_duration(self, audio_source: AudioSource) -> Optional[float]:
        """Get the duration of an audio file in seconds"""
        if not audio_source.file_path or not os.path.exists(audio_source.file_path):
            return None
        
        try:
            # Load the sound to get its length
            sound = pygame.mixer.Sound(audio_source.file_path)
            # Get duration in seconds (pygame returns samples, need to convert)
            return sound.get_length()
        except Exception as e:
            print(f"Failed to get audio duration for {audio_source.name}: {e}")
            return None
    
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
                is_enabled=True,
                audio_start_time=0.0,
                audio_duration=0.0,
                pending_volume=None,
                pending_frequency=None
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
    
    def synthesize_spatial_audio(self, device_id: str, car_position: Tuple[float, float], 
                                car_orientation: float, sensor_positions: List[Tuple[float, float]], 
                                distances: List[float], volume: float = 0.5) -> bool:
        """
        Generate spatial audio for left and right ears based on car position and orientation.
        
        Args:
            device_id: ID of the device playing audio
            car_position: (x, y) position of car center
            car_orientation: Car orientation in radians (0 = facing right)
            sensor_positions: List of (x, y) positions of sensors
            distances: List of distances from sensors
            volume: Base volume level
        """
        try:
            if device_id not in self.channels:
                return False
                
            channel = self.channels[device_id]
            if not channel.is_enabled or not channel.is_playing:
                return False
            
            # Calculate left and right ear positions
            car_x, car_y = car_position
            
            # Ear positions are at the front half of the car (upper half based on orientation)
            # Distance from center to ear position (half car width)
            ear_offset = 8.0  # cm (half of 16cm car width)
            
            # Calculate perpendicular direction to car orientation for left/right ears
            left_ear_angle = car_orientation + np.pi/2  # 90 degrees left of car direction
            right_ear_angle = car_orientation - np.pi/2  # 90 degrees right of car direction
            
            left_ear_x = car_x + ear_offset * np.cos(left_ear_angle)
            left_ear_y = car_y + ear_offset * np.sin(left_ear_angle)
            
            right_ear_x = car_x + ear_offset * np.cos(right_ear_angle)
            right_ear_y = car_y + ear_offset * np.sin(right_ear_angle)
            
            # For each sensor, determine if sound is clear or muffled for each ear
            left_volumes = []
            right_volumes = []
            
            for i, (sensor_x, sensor_y) in enumerate(sensor_positions):
                sensor_distance = distances[i]
                
                # Check line-of-sight from each ear to sensor
                left_clear = self._is_line_of_sight_clear(
                    (left_ear_x, left_ear_y), (sensor_x, sensor_y), car_position, car_orientation
                )
                right_clear = self._is_line_of_sight_clear(
                    (right_ear_x, right_ear_y), (sensor_x, sensor_y), car_position, car_orientation
                )
                
                # Calculate distance-based volume
                base_volume = volume / (1 + sensor_distance / 100.0)  # Fade with distance
                
                # Apply muffling if blocked by car body
                left_vol = base_volume if left_clear else base_volume * 0.3  # Muffled
                right_vol = base_volume if right_clear else base_volume * 0.3  # Muffled
                
                left_volumes.append(left_vol)
                right_volumes.append(right_vol)
            
            # Combine volumes from all sensors
            total_left_volume = min(1.0, sum(left_volumes))
            total_right_volume = min(1.0, sum(right_volumes))
            
            # Update channel with spatial audio parameters
            channel.left_volume = total_left_volume
            channel.right_volume = total_right_volume
            channel.current_volume = max(total_left_volume, total_right_volume)
            
            log_audio(f"🎵 Spatial audio for {device_id}: L={total_left_volume:.2f}, R={total_right_volume:.2f}")
            return True
            
        except Exception as e:
            log_error(f"Spatial audio synthesis error for {device_id}: {e}")
            return False
    
    def _is_line_of_sight_clear(self, ear_pos: Tuple[float, float], sensor_pos: Tuple[float, float], 
                               car_center: Tuple[float, float], car_orientation: float) -> bool:
        """
        Check if there's a clear line of sight from ear to sensor (not blocked by car body).
        
        Args:
            ear_pos: (x, y) position of ear
            sensor_pos: (x, y) position of sensor
            car_center: (x, y) position of car center
            car_orientation: Car orientation in radians
        """
        try:
            import math
            
            ear_x, ear_y = ear_pos
            sensor_x, sensor_y = sensor_pos
            car_x, car_y = car_center
            
            # Define car body as rectangle
            car_length = 30.0  # cm
            car_width = 16.0   # cm
            
            # Calculate car corner positions based on orientation
            half_length = car_length / 2
            half_width = car_width / 2
            
            # Car corners in local coordinates (relative to center)
            corners_local = [
                (-half_length, -half_width),  # Back left
                (-half_length, half_width),   # Back right
                (half_length, half_width),    # Front right
                (half_length, -half_width)    # Front left
            ]
            
            # Rotate corners based on car orientation
            cos_angle = math.cos(car_orientation)
            sin_angle = math.sin(car_orientation)
            
            car_corners = []
            for local_x, local_y in corners_local:
                # Rotate and translate to world coordinates
                world_x = car_x + local_x * cos_angle - local_y * sin_angle
                world_y = car_y + local_x * sin_angle + local_y * cos_angle
                car_corners.append((world_x, world_y))
            
            # Check if line from ear to sensor intersects car body rectangle
            return not self._line_intersects_rectangle(ear_pos, sensor_pos, car_corners)
            
        except Exception as e:
            log_error(f"Line of sight calculation error: {e}")
            return True  # Default to clear if calculation fails
    
    def _line_intersects_rectangle(self, line_start: Tuple[float, float], 
                                  line_end: Tuple[float, float], 
                                  rect_corners: List[Tuple[float, float]]) -> bool:
        """Check if a line segment intersects with a rectangle defined by corners."""
        try:
            # Check intersection with each edge of the rectangle
            for i in range(4):
                edge_start = rect_corners[i]
                edge_end = rect_corners[(i + 1) % 4]
                
                if self._line_segments_intersect(line_start, line_end, edge_start, edge_end):
                    return True
            
            return False
            
        except Exception as e:
            log_error(f"Line-rectangle intersection error: {e}")
            return False
    
    def _line_segments_intersect(self, p1: Tuple[float, float], p2: Tuple[float, float],
                                p3: Tuple[float, float], p4: Tuple[float, float]) -> bool:
        """Check if two line segments intersect."""
        try:
            x1, y1 = p1
            x2, y2 = p2
            x3, y3 = p3
            x4, y4 = p4
            
            # Calculate the direction vectors
            d1 = ((x2 - x1), (y2 - y1))
            d2 = ((x4 - x3), (y4 - y3))
            d3 = ((x1 - x3), (y1 - y3))
            
            # Calculate cross products
            cross_d1_d2 = d1[0] * d2[1] - d1[1] * d2[0]
            
            if abs(cross_d1_d2) < 1e-10:
                return False  # Lines are parallel
            
            # Calculate intersection parameters
            t1 = (d3[0] * d2[1] - d3[1] * d2[0]) / cross_d1_d2
            t2 = (d3[0] * d1[1] - d3[1] * d1[0]) / cross_d1_d2
            
            # Check if intersection point is within both line segments
            return 0 <= t1 <= 1 and 0 <= t2 <= 1
            
        except Exception as e:
            log_error(f"Line segment intersection error: {e}")
            return False
        
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