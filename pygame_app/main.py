#!/usr/bin/env python3
"""
pygame_app/main.py
Professional Spatial Audio System - Main Application Entry Point
"""

import os
import sys
import pygame
import time
import signal
import traceback

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def check_dependencies():
    """Check if all required modules can be imported"""
    try:
        import pygame
        import numpy
        import sounddevice
        import serial
        print("✅ Core dependencies verified")
        
        # Check Bluetooth support
        try:
            import bleak
            print("✅ Bluetooth support (bleak) available")
        except ImportError:
            try:
                import bluetooth
                print("⚠️  Bluetooth support (pybluez) available")
            except ImportError:
                print("⚠️  No Bluetooth support - HC-05 devices won't work")
                print("   Install with: pip install bleak")
        
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please run ./setup.sh to install dependencies")
        return False

def main():
    """Main application entry point"""
    print("🎵 Professional Spatial Audio System")
    print("====================================")
    
    # Check dependencies first
    if not check_dependencies():
        sys.exit(1)
    
    try:
        # Import application modules
        from src.config import Config
        from src.audio_engine import SpatialAudioEngine
        from src.device_manager import DeviceManager
        from src.ui_manager import UIManager
        
        print("✅ Application modules imported successfully")
        
        # Initialize pygame
        print("🎮 Initializing pygame...")
        pygame.init()
        
        # Create display
        screen = pygame.display.set_mode((Config.WINDOW_WIDTH, Config.WINDOW_HEIGHT))
        pygame.display.set_caption("Professional Spatial Audio System")
        
        # Initialize core components
        print("🔊 Initializing audio engine...")
        audio_engine = SpatialAudioEngine()
        
        print("📶 Initializing device manager...")
        device_manager = DeviceManager()
        
        print("🖥️  Initializing UI manager...")
        ui_manager = UIManager(screen, audio_engine, device_manager)
        
        # Application state
        clock = pygame.time.Clock()
        running = True
        last_update = time.time()
        
        print("✅ Application initialized successfully")
        print("🚀 Starting main loop...")
        
        # Main application loop
        while running:
            current_time = time.time()
            dt = current_time - last_update
            last_update = current_time
            
            # Handle pygame events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                else:
                    # Pass other events to UI manager
                    ui_manager.handle_event(event)
            
            # Update components
            audio_engine.update(dt)
            ui_manager.update(dt)
            
            # Render UI
            ui_manager.render()
            
            # Update display
            pygame.display.flip()
            clock.tick(Config.TARGET_FPS)
        
        print("🔄 Shutting down...")
        
        # Cleanup
        ui_manager.cleanup()
        device_manager.cleanup()
        audio_engine.cleanup()
        
        pygame.quit()
        print("✅ Shutdown complete")
        
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"❌ Application error: {e}")
        print("📝 Full traceback:")
        traceback.print_exc()
    finally:
        # Ensure pygame is properly closed
        try:
            pygame.quit()
        except:
            pass

def signal_handler(sig, frame):
    """Handle interrupt signals gracefully"""
    print("\n⚠️  Received interrupt signal, shutting down...")
    sys.exit(0)

if __name__ == "__main__":
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Check if we're in the right directory
    if not os.path.exists("src"):
        print("❌ src/ directory not found")
        print("Make sure to run this script from the pygame_app directory")
        sys.exit(1)
    
    main()