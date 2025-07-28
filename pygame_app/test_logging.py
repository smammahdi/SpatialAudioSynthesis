#!/usr/bin/env python3
"""
Test script to demonstrate the logging configuration system
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.logging_config import *

def test_logging_system():
    """Test all logging categories"""
    print("=== TESTING LOGGING SYSTEM ===\n")
    
    # Show current configuration
    print_logging_status()
    
    print("Testing with current configuration (simulation-only):")
    log_audio("🎵 This audio log should NOT appear")
    log_device("📱 This device log should NOT appear")
    log_simulation("🔧 This simulation log SHOULD appear")
    log_trilateration("📍 This trilateration log SHOULD appear")
    log_error("❌ This error log SHOULD appear")
    
    print("\n" + "="*50)
    print("ENABLING ALL LOGS...")
    enable_all_logs()
    print_logging_status()
    
    print("Testing with all logs enabled:")
    log_audio("🎵 This audio log SHOULD appear")
    log_device("📱 This device log SHOULD appear")
    log_simulation("🔧 This simulation log SHOULD appear")
    log_trilateration("📍 This trilateration log SHOULD appear")
    log_error("❌ This error log SHOULD appear")
    
    print("\n" + "="*50)
    print("DISABLING ALL LOGS...")
    disable_all_logs()
    print_logging_status()
    
    print("Testing with all logs disabled:")
    log_audio("🎵 This audio log should NOT appear")
    log_device("📱 This device log should NOT appear")
    log_simulation("🔧 This simulation log should NOT appear")
    log_trilateration("📍 This trilateration log should NOT appear")
    log_error("❌ This error log should NOT appear")
    
    print("\n" + "="*50)
    print("RESTORING SIMULATION-ONLY CONFIGURATION...")
    enable_simulation_only()
    print_logging_status()
    
    print("Testing with simulation-only configuration:")
    log_audio("🎵 This audio log should NOT appear")
    log_device("📱 This device log should NOT appear")
    log_simulation("🔧 This simulation log SHOULD appear")
    log_trilateration("📍 This trilateration log SHOULD appear")
    log_error("❌ This error log SHOULD appear")
    
    print("\n=== LOGGING SYSTEM TEST COMPLETE ===")

if __name__ == "__main__":
    test_logging_system()
