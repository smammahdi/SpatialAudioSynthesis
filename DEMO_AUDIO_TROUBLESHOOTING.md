# 🔊 Demo Device Audio Troubleshooting Guide

## ✅ **Fixes Applied**

### **1. Demo Device Audio Assignment**
- ❌ **Before**: Demo device had no audio file assigned
- ✅ **Now**: Demo device automatically gets assigned a 440Hz sine wave

### **2. Automatic Audio Synthesis**  
- ❌ **Before**: Audio only played when manually clicking test button
- ✅ **Now**: Demo device automatically triggers audio as distance changes

### **3. Audio Test Button**
- ✅ **Added**: New "🔊 Test Audio (440Hz tone)" button in Audio Effects section
- ✅ **Purpose**: Quick test to verify audio system is working

## 🔍 **How to Test Audio**

### **Step 1: Start the System**
```bash
./start_multi_terminal.sh
```

### **Step 2: Check Audio Setup**
1. **Open Frontend**: http://localhost:3000
2. **Enable Audio Synthesis**: Toggle the switch in Audio Effects section
3. **Click Test Audio Button**: Should hear a 440Hz tone immediately

### **Step 3: Test Demo Device**
1. **Enable Demo Mode**: Toggle "Enable Demo Mode" 
2. **Wait for Audio Assignment**: Demo device gets 440Hz sine wave automatically
3. **Listen**: Audio should change pitch/volume as distance cycles (0-175cm)

## 🔧 **Audio System Flow**

```
Demo Device Distance Change → Audio Frequency Calculation → Backend Synthesis → Your Speakers
       ↓                              ↓                           ↓                 ↓
   0-175cm cycle              200-1000Hz range           pygame/sounddevice      Actual Sound
```

## 📊 **Expected Behavior**

### **Distance-Based Audio Changes**
- **Close (0-50cm)**: High frequency (800-1000Hz), High volume (80-100%)
- **Medium (50-100cm)**: Medium frequency (500-700Hz), Medium volume (40-80%)  
- **Far (100-175cm)**: Low frequency (200-400Hz), Low volume (10-40%)

### **Demo Cycle (30 seconds)**
- **0-15 seconds**: Distance increases 0→175cm (frequency decreases, volume decreases)
- **15-30 seconds**: Distance decreases 175→0cm (frequency increases, volume increases)

## 🚨 **Troubleshooting Steps**

### **If You Still Don't Hear Sound**

#### **1. Check System Audio**
```bash
# Test system audio (macOS)
osascript -e "beep"

# Check volume
osascript -e "get volume settings"
```

#### **2. Test Backend Audio Directly**
```bash
cd backend && source venv/bin/activate
python -c "
from audio_synthesis import AudioSynthesisEngine
engine = AudioSynthesisEngine()
result = engine.generate_test_tone(440, 0.5, 2.0)
print('Audio result:', result)
"
```

#### **3. Check Audio Libraries**
```bash
cd backend && source venv/bin/activate
python -c "
try:
    import pygame
    print('✅ pygame available')
except ImportError:
    print('❌ pygame not available')

try:
    import sounddevice
    print('✅ sounddevice available') 
except ImportError:
    print('❌ sounddevice not available')
"
```

#### **4. Browser Audio Permissions**
- **Chrome**: Check if site has audio permission
- **Safari**: Check autoplay settings
- **Firefox**: Check media autoplay settings

#### **5. Check Backend Logs**
Look for these messages in backend terminal:
```
✅ "Audio played via pygame: XXXHz"
✅ "Audio played via sounddevice: XXXHz"  
⚠️  "No audio playback method available"
```

## 🔧 **Manual Testing Commands**

### **Test Backend Audio Synthesis**
```bash
curl -X POST http://localhost:8000/synthesize-audio \
  -H "Content-Type: application/json" \
  -d '{"frequency": 440, "volume": 50, "duration": 1.0}'
```

### **Test Frontend API Connection**
```javascript
// In browser console
fetch('http://localhost:8000/audio-list')
  .then(r => r.json())
  .then(console.log)
```

## 📝 **Quick Fixes**

### **If Demo Audio Is Too Quiet**
1. Increase **Master Volume** slider
2. Increase **Max Volume (%)** in distance mapping
3. Check system volume level

### **If Demo Audio Is Too Fast/Slow**
- Demo cycles every 30 seconds (hardcoded)
- Audio plays every 2 seconds (throttled)
- Distance updates every 500ms

### **If Audio Stutters**
- Increase throttle time in `triggerDemoAudio`
- Check system CPU usage
- Try reducing update frequency

## ✅ **Success Indicators**

You should see/hear:
1. **Test Audio Button**: Immediate 440Hz tone when clicked
2. **Demo Device**: Auto-assigned "A4 Sine (440Hz)" in device list  
3. **Distance Changes**: Real-time updates in monitoring section
4. **Audio Variation**: Pitch and volume changing with distance
5. **Console Logs**: "🎵 Demo audio: XXXHz at XXcm" messages

If all steps above work, your spatial audio system is fully operational! 🎉
