#!/usr/bin/env python3
"""
Audio Synthesis Engine for Spatial Audio
Handles real-time audio generation based on sensor distance data
"""

import numpy as np
import threading
import time
import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Audio playback imports
try:
    import pygame
    pygame_available = True
except ImportError:
    pygame_available = False

try:
    import sounddevice as sd
    sounddevice_available = True
except ImportError:
    sounddevice_available = False

logger = logging.getLogger(__name__)

class AudioType(Enum):
    BASS = "bass"
    MID = "mid" 
    TREBLE = "treble"
    AMBIENT = "ambient"
    HARMONIC = "harmonic"

@dataclass
class AudioTrack:
    sensor_id: str
    sensor_name: str
    audio_type: AudioType
    frequency: float
    current_distance: float
    current_volume: float
    is_playing: bool
    
class AudioSynthesisEngine:
    """Real-time audio synthesis engine"""
    
    def __init__(self, sample_rate: int = 44100, buffer_size: int = 1024):
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        self.tracks: Dict[str, AudioTrack] = {}
        self.global_volume = 0.7
        self.max_distance = 200.0
        self.min_distance = 0.0
        self.enabled = False
        self.running = False
        
        # Audio generation parameters
        self.phase_accumulators: Dict[str, float] = {}
        self.audio_thread: Optional[threading.Thread] = None
        self.audio_lock = threading.Lock()
        
        # Frequency mapping for different audio types
        self.frequency_map = {
            AudioType.BASS: 60.0,      # C2
            AudioType.MID: 261.63,     # C4
            AudioType.TREBLE: 1046.50, # C6
            AudioType.AMBIENT: 196.00, # G3
            AudioType.HARMONIC: 329.63 # E4
        }
        
    def initialize(self):
        """Initialize the audio synthesis engine"""
        try:
            logger.info("Initializing audio synthesis engine")
            self.running = False  # Will be set to True when enabled
            logger.info("Audio synthesis engine initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize audio engine: {str(e)}")
            raise
    
    def create_audio_track(self, sensor_id: str, sensor_name: str) -> AudioTrack:
        """Create a new audio track for a sensor"""
        with self.audio_lock:
            if sensor_id in self.tracks:
                return self.tracks[sensor_id]
            
            # Determine audio type based on sensor order
            audio_type = self._get_audio_type_for_sensor(sensor_id, sensor_name)
            frequency = self.frequency_map[audio_type]
            
            track = AudioTrack(
                sensor_id=sensor_id,
                sensor_name=sensor_name,
                audio_type=audio_type,
                frequency=frequency,
                current_distance=self.max_distance,
                current_volume=0.0,
                is_playing=False
            )
            
            self.tracks[sensor_id] = track
            self.phase_accumulators[sensor_id] = 0.0
            
            logger.info(f"Created {audio_type.value} audio track for {sensor_name}")
            return track
    
    def _get_audio_type_for_sensor(self, sensor_id: str, sensor_name: str) -> AudioType:
        """Determine audio type based on sensor characteristics"""
        # Map sensors to different audio types for spatial effect
        sensor_count = len(self.tracks)
        audio_types = list(AudioType)
        
        # Assign based on sensor name if possible
        name_lower = sensor_name.lower()
        if 'a' in name_lower or 'bass' in name_lower:
            return AudioType.BASS
        elif 'b' in name_lower or 'mid' in name_lower:
            return AudioType.MID
        elif 'c' in name_lower or 'treble' in name_lower:
            return AudioType.TREBLE
        elif 'd' in name_lower or 'ambient' in name_lower:
            return AudioType.AMBIENT
        
        # Otherwise assign cyclically
        return audio_types[sensor_count % len(audio_types)]
    
    def update_sensor_distance(self, sensor_id: str, distance: float):
        """Update sensor distance and recalculate audio parameters"""
        with self.audio_lock:
            if sensor_id not in self.tracks:
                # Auto-create track if it doesn't exist
                self.create_audio_track(sensor_id, f"Sensor_{sensor_id[-4:]}")
            
            track = self.tracks[sensor_id]
            track.current_distance = distance
            
            # Calculate volume based on distance
            new_volume = self._calculate_volume_from_distance(distance)
            track.current_volume = new_volume
            
            # Update playing status
            should_play = self.enabled and new_volume > 0
            if should_play and not track.is_playing:
                track.is_playing = True
                logger.debug(f"Started audio for {track.sensor_name}")
            elif not should_play and track.is_playing:
                track.is_playing = False
                logger.debug(f"Stopped audio for {track.sensor_name}")
    
    def _calculate_volume_from_distance(self, distance: float) -> float:
        """Calculate volume from distance (0-200cm -> 100%-0%)"""
        # Clamp distance to valid range
        clamped_distance = max(self.min_distance, min(self.max_distance, distance))
        
        # Calculate volume: closer = louder
        if self.max_distance == self.min_distance:
            return 1.0  # Avoid division by zero
        
        volume_percent = max(0, 100 - (clamped_distance / self.max_distance) * 100)
        return volume_percent / 100.0
    
    def generate_audio_buffer(self) -> np.ndarray:
        """Generate audio buffer for current state"""
        with self.audio_lock:
            if not self.enabled or not self.tracks:
                return np.zeros(self.buffer_size, dtype=np.float32)
            
            # Initialize output buffer
            output = np.zeros(self.buffer_size, dtype=np.float32)
            
            # Generate audio for each active track
            for sensor_id, track in self.tracks.items():
                if track.is_playing and track.current_volume > 0:
                    # Generate sine wave for this track
                    samples = self._generate_sine_wave(
                        track.frequency,
                        track.current_volume * self.global_volume,
                        sensor_id
                    )
                    output += samples
            
            # Normalize to prevent clipping
            if np.max(np.abs(output)) > 1.0:
                output = output / np.max(np.abs(output))
            
            return output
    
    def _generate_sine_wave(self, frequency: float, volume: float, sensor_id: str) -> np.ndarray:
        """Generate sine wave samples for a specific frequency and volume"""
        # Get current phase accumulator
        phase = self.phase_accumulators.get(sensor_id, 0.0)
        
        # Generate samples
        samples = np.zeros(self.buffer_size, dtype=np.float32)
        phase_increment = 2.0 * np.pi * frequency / self.sample_rate
        
        for i in range(self.buffer_size):
            samples[i] = volume * np.sin(phase)
            phase += phase_increment
            
            # Keep phase in bounds
            if phase >= 2.0 * np.pi:
                phase -= 2.0 * np.pi
        
        # Update phase accumulator
        self.phase_accumulators[sensor_id] = phase
        
        return samples
    
    def set_enabled(self, enabled: bool):
        """Enable or disable audio synthesis"""
        with self.audio_lock:
            self.enabled = enabled
            
            if not enabled:
                # Stop all tracks
                for track in self.tracks.values():
                    track.is_playing = False
            else:
                # Start tracks that should be playing
                for track in self.tracks.values():
                    if track.current_volume > 0:
                        track.is_playing = True
        
        logger.info(f"Audio synthesis {'enabled' if enabled else 'disabled'}")
    
    def set_global_volume(self, volume: float):
        """Set global volume (0.0 to 1.0)"""
        self.global_volume = max(0.0, min(1.0, volume))
        logger.info(f"Global volume set to {self.global_volume:.2f}")
    
    def set_distance_range(self, min_distance: float, max_distance: float):
        """Set distance range for volume calculation"""
        self.min_distance = min_distance
        self.max_distance = max_distance
        
        # Recalculate volumes for all tracks
        with self.audio_lock:
            for track in self.tracks.values():
                self.update_sensor_distance(track.sensor_id, track.current_distance)
        
        logger.info(f"Distance range set to {min_distance}-{max_distance}cm")
    
    def remove_track(self, sensor_id: str):
        """Remove audio track for a sensor"""
        with self.audio_lock:
            if sensor_id in self.tracks:
                track = self.tracks[sensor_id]
                del self.tracks[sensor_id]
                if sensor_id in self.phase_accumulators:
                    del self.phase_accumulators[sensor_id]
                logger.info(f"Removed audio track for {track.sensor_name}")
    
    def get_status(self) -> Dict:
        """Get current audio synthesis status"""
        with self.audio_lock:
            tracks_status = {}
            for sensor_id, track in self.tracks.items():
                tracks_status[sensor_id] = {
                    "sensor_name": track.sensor_name,
                    "audio_type": track.audio_type.value,
                    "frequency": track.frequency,
                    "distance": track.current_distance,
                    "volume": round(track.current_volume * 100, 1),
                    "playing": track.is_playing
                }
            
            return {
                "enabled": self.enabled,
                "global_volume": round(self.global_volume * 100, 1),
                "track_count": len(self.tracks),
                "playing_tracks": sum(1 for track in self.tracks.values() if track.is_playing),
                "tracks": tracks_status,
                "settings": {
                    "min_distance": self.min_distance,
                    "max_distance": self.max_distance,
                    "sample_rate": self.sample_rate
                }
            }
    
    def get_track_info(self, sensor_id: str) -> Optional[Dict]:
        """Get information about a specific track"""
        with self.audio_lock:
            if sensor_id not in self.tracks:
                return None
            
            track = self.tracks[sensor_id]
            return {
                "type": track.audio_type.value,
                "volume": track.current_volume,
                "playing": track.is_playing,
                "frequency": track.frequency,
                "distance": track.current_distance
            }
    
    def generate_test_tone(self, frequency: float = 440, volume: float = 0.5, duration: float = 1.0) -> Dict:
        """Generate and play a test tone for audio synthesis testing"""
        try:
            # Calculate number of samples
            num_samples = int(self.sample_rate * duration)
            
            # Generate time array
            t = np.linspace(0, duration, num_samples, False)
            
            # Generate sine wave
            test_tone = volume * np.sin(2 * np.pi * frequency * t)
            
            # Try to play the audio using available libraries
            audio_played = self._play_audio(test_tone, frequency, duration)
            
            # Calculate audio properties
            max_amplitude = np.max(np.abs(test_tone))
            rms_amplitude = np.sqrt(np.mean(test_tone**2))
            
            logger.info(f"Generated test tone: {frequency}Hz, {duration}s, volume={volume*100:.1f}%, played={audio_played}")
            
            return {
                "success": True,
                "frequency": frequency,
                "duration": duration,
                "volume_percent": volume * 100,
                "samples_generated": num_samples,
                "max_amplitude": float(max_amplitude),
                "rms_amplitude": float(rms_amplitude),
                "audio_played": audio_played,
                "message": f"Test tone {'played' if audio_played else 'generated'} successfully: {frequency}Hz for {duration}s"
            }
            
        except Exception as e:
            logger.error(f"Test tone generation failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Test tone generation failed"
            }

    def _play_audio(self, audio_data: np.ndarray, frequency: float, duration: float) -> bool:
        """Attempt to play audio using available audio libraries"""
        
        # Method 1: Try sounddevice (best for real-time audio)
        if sounddevice_available:
            try:
                sd.play(audio_data, self.sample_rate)
                sd.wait()  # Wait until the sound has finished playing
                logger.info(f"Audio played via sounddevice: {frequency}Hz")
                return True
            except Exception as e:
                logger.warning(f"Sounddevice playback failed: {e}")
        
        # Method 2: Try pygame (more compatible)
        if pygame_available:
            try:
                # Initialize pygame mixer if not already done
                if not pygame.mixer.get_init():
                    pygame.mixer.init(frequency=self.sample_rate, size=-16, channels=1, buffer=512)
                
                # Convert to 16-bit integers and ensure correct format
                audio_16bit = (audio_data * 32767).astype(np.int16)
                
                # Create sound object and play
                sound = pygame.sndarray.make_sound(audio_16bit)
                sound.play()
                
                # Wait for playback to complete
                pygame.time.wait(int(duration * 1000))
                
                logger.info(f"Audio played via pygame: {frequency}Hz")
                return True
            except Exception as e:
                logger.warning(f"Pygame playback failed: {e}")
        
        # Method 3: System beep as fallback
        try:
            import os
            import sys
            
            if sys.platform == "darwin":  # macOS
                os.system(f"osascript -e 'beep {int(frequency/220)}'")
                logger.info(f"System beep played on macOS")
                return True
            elif sys.platform == "linux":  # Linux
                os.system(f"paplay <(speaker-test -t sine -f {frequency} -l 1 -s 1) 2>/dev/null &")
                logger.info(f"System beep attempted on Linux")
                return True
            else:  # Windows
                import winsound
                winsound.Beep(int(frequency), int(duration * 1000))
                logger.info(f"System beep played on Windows")
                return True
        except Exception as e:
            logger.warning(f"System beep failed: {e}")
        
        logger.warning("No audio playback method available - audio simulation only")
        return False
    
    def cleanup(self):
        """Cleanup audio resources"""
        self.running = False
        self.enabled = False
        
        with self.audio_lock:
            self.tracks.clear()
            self.phase_accumulators.clear()
        
        logger.info("Audio synthesis engine cleaned up")

# Example usage and testing
if __name__ == "__main__":
    # Simple test
    engine = AudioSynthesisEngine()
    engine.initialize()
    
    # Create test tracks
    engine.create_audio_track("sensor_a", "SensorNode_A")
    engine.create_audio_track("sensor_b", "SensorNode_B")
    
    # Enable and test
    engine.set_enabled(True)
    engine.update_sensor_distance("sensor_a", 50)  # Close = loud
    engine.update_sensor_distance("sensor_b", 150) # Far = quiet
    
    print("Audio engine status:")
    print(engine.get_status())
    
    # Generate some audio (in real app, this would be continuous)
    for i in range(10):
        buffer = engine.generate_audio_buffer()
        print(f"Generated buffer {i+1}: max amplitude = {np.max(np.abs(buffer)):.3f}")
        time.sleep(0.1)
    
    engine.cleanup()
