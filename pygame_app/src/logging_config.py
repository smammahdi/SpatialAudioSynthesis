"""
Centralized Logging Configuration for Spatial Audio System

This module provides global boolean flags to control different types of logging throughout the application.
Only simulation-related logs are enabled by default to reduce console spam.
"""

# =============================================================================
# GLOBAL LOGGING CONFIGURATION
# =============================================================================

# Audio System Logs
AUDIO_LOGS = False              # 🎵 🎬 ⏳ Audio playback, synthesis, and timing logs
AUDIO_ENGINE_LOGS = False       # Audio engine initialization, cleanup, and processing
AUDIO_FILE_LOGS = False         # Audio file loading, registration, and management

# Device & Bluetooth Logs  
DEVICE_LOGS = False             # 📱 📡 Device discovery, connection, and management
BLUETOOTH_LOGS = False          # Bluetooth scanning, RSSI, and HC-05 detection
DEVICE_SCANNER_LOGS = False     # Device scanner real-time updates and scanning

# Simulation & Trilateration Logs (ENABLED - Primary focus)
SIMULATION_LOGS = True          # 🔧 📍 Trilateration algorithm, position calculation
TRILATERATION_LOGS = True       # Triangle validation, constraint checking, algorithm details
POSITION_LOGS = True            # Car position updates, coordinate changes
GRID_LOGS = True                # Grid interactions, sensor positioning, coordinate editing

# UI & Interaction Logs
UI_LOGS = False                 # UI rendering, button clicks, interface updates  
INPUT_LOGS = False              # Mouse clicks, keyboard input, user interactions
DEMO_LOGS = False               # Demo mode controls, demo object movement

# System & Error Logs
SYSTEM_LOGS = False             # System initialization, cleanup, general status
ERROR_LOGS = True               # Error messages and exceptions (always useful)
DEBUG_LOGS = True               # Detailed debugging information

# File & Configuration Logs
FILE_LOGS = False               # File operations, loading, saving
CONFIG_LOGS = False             # Configuration changes, settings updates

# =============================================================================
# LOGGING HELPER FUNCTIONS
# =============================================================================

def log_audio(message: str):
    """Log audio-related messages if AUDIO_LOGS is enabled"""
    if AUDIO_LOGS:
        print(message)

def log_audio_engine(message: str):
    """Log audio engine messages if AUDIO_ENGINE_LOGS is enabled"""
    if AUDIO_ENGINE_LOGS:
        print(message)

def log_audio_file(message: str):
    """Log audio file messages if AUDIO_FILE_LOGS is enabled"""
    if AUDIO_FILE_LOGS:
        print(message)

def log_device(message: str):
    """Log device-related messages if DEVICE_LOGS is enabled"""
    if DEVICE_LOGS:
        print(message)

def log_bluetooth(message: str):
    """Log Bluetooth-related messages if BLUETOOTH_LOGS is enabled"""
    if BLUETOOTH_LOGS:
        print(message)

def log_device_scanner(message: str):
    """Log device scanner messages if DEVICE_SCANNER_LOGS is enabled"""
    if DEVICE_SCANNER_LOGS:
        print(message)

def log_simulation(message: str):
    """Log simulation-related messages if SIMULATION_LOGS is enabled"""
    if SIMULATION_LOGS:
        print(message)

def log_trilateration(message: str):
    """Log trilateration algorithm messages if TRILATERATION_LOGS is enabled"""
    if TRILATERATION_LOGS:
        print(message)

def log_position(message: str):
    """Log position-related messages if POSITION_LOGS is enabled"""
    if POSITION_LOGS:
        print(message)

def log_grid(message: str):
    """Log grid-related messages if GRID_LOGS is enabled"""
    if GRID_LOGS:
        print(message)

def log_ui(message: str):
    """Log UI-related messages if UI_LOGS is enabled"""
    if UI_LOGS:
        print(message)

def log_input(message: str):
    """Log input-related messages if INPUT_LOGS is enabled"""
    if INPUT_LOGS:
        print(message)

def log_demo(message: str):
    """Log demo-related messages if DEMO_LOGS is enabled"""
    if DEMO_LOGS:
        print(message)

def log_system(message: str):
    """Log system-related messages if SYSTEM_LOGS is enabled"""
    if SYSTEM_LOGS:
        print(message)

def log_error(message: str):
    """Log error messages if ERROR_LOGS is enabled"""
    if ERROR_LOGS:
        print(message)

def log_debug(message: str):
    """Log debug messages if DEBUG_LOGS is enabled"""
    if DEBUG_LOGS:
        print(message)

def log_file(message: str):
    """Log file-related messages if FILE_LOGS is enabled"""
    if FILE_LOGS:
        print(message)

def log_config(message: str):
    """Log configuration messages if CONFIG_LOGS is enabled"""
    if CONFIG_LOGS:
        print(message)

# =============================================================================
# LOGGING CONTROL FUNCTIONS
# =============================================================================

def enable_all_logs():
    """Enable all logging categories"""
    global AUDIO_LOGS, AUDIO_ENGINE_LOGS, AUDIO_FILE_LOGS
    global DEVICE_LOGS, BLUETOOTH_LOGS, DEVICE_SCANNER_LOGS
    global SIMULATION_LOGS, TRILATERATION_LOGS, POSITION_LOGS, GRID_LOGS
    global UI_LOGS, INPUT_LOGS, DEMO_LOGS
    global SYSTEM_LOGS, ERROR_LOGS, DEBUG_LOGS
    global FILE_LOGS, CONFIG_LOGS
    
    AUDIO_LOGS = AUDIO_ENGINE_LOGS = AUDIO_FILE_LOGS = True
    DEVICE_LOGS = BLUETOOTH_LOGS = DEVICE_SCANNER_LOGS = True
    SIMULATION_LOGS = TRILATERATION_LOGS = POSITION_LOGS = GRID_LOGS = True
    UI_LOGS = INPUT_LOGS = DEMO_LOGS = True
    SYSTEM_LOGS = ERROR_LOGS = DEBUG_LOGS = True
    FILE_LOGS = CONFIG_LOGS = True

def disable_all_logs():
    """Disable all logging categories"""
    global AUDIO_LOGS, AUDIO_ENGINE_LOGS, AUDIO_FILE_LOGS
    global DEVICE_LOGS, BLUETOOTH_LOGS, DEVICE_SCANNER_LOGS
    global SIMULATION_LOGS, TRILATERATION_LOGS, POSITION_LOGS, GRID_LOGS
    global UI_LOGS, INPUT_LOGS, DEMO_LOGS
    global SYSTEM_LOGS, ERROR_LOGS, DEBUG_LOGS
    global FILE_LOGS, CONFIG_LOGS
    
    AUDIO_LOGS = AUDIO_ENGINE_LOGS = AUDIO_FILE_LOGS = False
    DEVICE_LOGS = BLUETOOTH_LOGS = DEVICE_SCANNER_LOGS = False
    SIMULATION_LOGS = TRILATERATION_LOGS = POSITION_LOGS = GRID_LOGS = False
    UI_LOGS = INPUT_LOGS = DEMO_LOGS = False
    SYSTEM_LOGS = ERROR_LOGS = DEBUG_LOGS = False
    FILE_LOGS = CONFIG_LOGS = False

def enable_simulation_only():
    """Enable only simulation-related logs (default configuration)"""
    disable_all_logs()
    global SIMULATION_LOGS, TRILATERATION_LOGS, POSITION_LOGS, GRID_LOGS, ERROR_LOGS
    SIMULATION_LOGS = TRILATERATION_LOGS = POSITION_LOGS = GRID_LOGS = True
    ERROR_LOGS = True  # Always keep error logs enabled

def print_logging_status():
    """Print the current status of all logging categories"""
    print("\n=== LOGGING CONFIGURATION STATUS ===")
    print(f"Audio Logs:         {AUDIO_LOGS}")
    print(f"Audio Engine Logs:  {AUDIO_ENGINE_LOGS}")
    print(f"Audio File Logs:    {AUDIO_FILE_LOGS}")
    print(f"Device Logs:        {DEVICE_LOGS}")
    print(f"Bluetooth Logs:     {BLUETOOTH_LOGS}")
    print(f"Device Scanner Logs:{DEVICE_SCANNER_LOGS}")
    print(f"Simulation Logs:    {SIMULATION_LOGS}")
    print(f"Trilateration Logs: {TRILATERATION_LOGS}")
    print(f"Position Logs:      {POSITION_LOGS}")
    print(f"Grid Logs:          {GRID_LOGS}")
    print(f"UI Logs:            {UI_LOGS}")
    print(f"Input Logs:         {INPUT_LOGS}")
    print(f"Demo Logs:          {DEMO_LOGS}")
    print(f"System Logs:        {SYSTEM_LOGS}")
    print(f"Error Logs:         {ERROR_LOGS}")
    print(f"Debug Logs:         {DEBUG_LOGS}")
    print(f"File Logs:          {FILE_LOGS}")
    print(f"Config Logs:        {CONFIG_LOGS}")
    print("=====================================\n")

# Initialize with simulation-only logging by default
enable_simulation_only()
