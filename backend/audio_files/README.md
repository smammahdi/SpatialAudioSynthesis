# Audio Files Directory

This directory contains audio files that can be used as sources for spatial audio synthesis.

## Supported Formats
- WAV (recommended for low latency)
- MP3 (compressed, smaller file size)
- OGG (open source alternative)

## Sample Audio Files

### Default Tracks
- `ambient_rain.wav` - Gentle rain sounds for ambient atmosphere
- `bass_drop.wav` - Deep bass tones for low-frequency synthesis
- `bell_chimes.wav` - Metallic bell sounds for high-frequency synthesis
- `nature_birds.wav` - Bird chirping for natural ambience
- `synth_pad.wav` - Synthesizer pad for harmonic layers
- `water_flow.wav` - Flowing water sounds for relaxation

### Usage
Each connected sensor can be assigned one of these audio files. The volume and playback of the audio will be controlled by the distance readings from the sensor.

### Adding Custom Audio Files
1. Place your audio files in this directory
2. Supported formats: .wav, .mp3, .ogg
3. Recommended: 44.1kHz sample rate, 16-bit depth
4. Keep file sizes reasonable for web playback (< 5MB per file)

### Audio File Naming Convention
- Use descriptive names: `ambient_forest.wav`
- Avoid spaces: use underscores or hyphens
- Include the type: `bass_`, `ambient_`, `percussion_`, etc.
