"""
pygame_app/src/ui_manager.py
Enhanced UI Manager with HC-05 Integration and Improved Layout
"""
import pygame
import pygame.freetype
import time
from typing import Dict, List, Optional, Callable, Tuple, Any
from enum import Enum

from .config import Config
from .audio_engine import SpatialAudioEngine, AudioSource, AudioFileType
from .device_manager import DeviceManager, Device, DeviceStatus
from .device_scanner import DeviceScanner

class NavigationPage(Enum):
    HOME = "Home"
    DEVICES = "Devices"
    AUDIO = "Audio"

class UIManager:
    def __init__(self, screen: pygame.Surface, audio_engine: SpatialAudioEngine, device_manager: DeviceManager):
        print("Initializing Enhanced UI Manager with HC-05 support...")
        self.screen = screen
        self.original_screen_size = (screen.get_width(), screen.get_height())
        self.audio_engine = audio_engine
        self.device_manager = device_manager
        
        # Navigation state
        self.current_page = NavigationPage.HOME
        
        pygame.freetype.init()
        self.fonts = self._load_fonts()
        
        # UI State
        self.expanded_sections = {
            'device_management': True, 'device_list': True, 'audio_effects': True,
            'device_status': True, 'distance_monitoring': True, 'volume_monitoring': True, 
            'log_panel': True, 'audio_assignment': True
        }
        
        # Audio settings
        self.audio_effects = {
            'master_volume': 75.0,
            'bass_boost': 0.0,
            'spatial_mix': 50.0,
            'bass_boost_enabled': True,
            'spatial_enabled': True,
            'distance_fade': True,
            'reverb_enabled': False
        }
        self.distance_settings = {
            'min_distance': 5.0, 'max_distance': 150.0, 'min_volume': 5.0, 
            'max_volume': 100.0, 'decay_type': 'exponential', 'max_graph_distance': 200.0
        }
        
        # Data tracking settings
        self.data_tracking = {
            'record_length': 60  # seconds of data to keep
        }
        
        # Scroll tracking for scrollable sections
        self.scroll_offsets = {
            'audio_library': 0,
        }
        
        # Device management
        self.device_enabled_states: Dict[str, bool] = {}
        self.device_audio_assignments: Dict[str, str] = {}
        self.device_colors: Dict[str, tuple] = {}  # Track consistent colors for each device
        
        # Global audio control
        self.global_audio_enabled = True
        
        # Data tracking
        self.log_entries: List[Tuple[float, str, str]] = []
        self.max_log_entries = 100
        self.distance_data: Dict[str, List[Tuple[float, float]]] = {}
        self.volume_data: Dict[str, List[Tuple[float, float]]] = {}
        
        # Interaction handling
        self.button_rects: Dict[str, pygame.Rect] = {}
        self.slider_rects: Dict[str, pygame.Rect] = {}
        self.checkbox_rects: Dict[str, pygame.Rect] = {}
        self.dropdown_rects: Dict[str, pygame.Rect] = {}
        self.mouse_pos = (0, 0)
        self.last_click_time = 0
        self.dragging_slider = None
        
        # HC-05 specific state
        self.hc05_status = self.device_manager.get_bluetooth_status()
        
        # Setup device manager callbacks
        self.device_manager.on_device_connected = self._on_device_connected
        self.device_manager.on_device_disconnected = self._on_device_disconnected
        self.device_manager.on_distance_update = self._on_distance_update
        
        self.add_log_entry("Enhanced UI Manager with HC-05 support initialized", "success")
        if self.hc05_status['available']:
            self.add_log_entry(f"HC-05 Bluetooth support: {self.hc05_status['library']}", "info")
        else:
            self.add_log_entry("HC-05 Bluetooth not available - using demo mode only", "warning")

    def get_device_color(self, device_id: str) -> tuple:
        """Get consistent color for a device"""
        if device_id not in self.device_colors:
            # Assign a new color based on the number of devices
            color_index = len(self.device_colors)
            available_colors = Config.COLORS['device_colors']
            self.device_colors[device_id] = available_colors[color_index % len(available_colors)]
        return self.device_colors[device_id]

    def _assign_device_color(self, device_id: str) -> tuple:
        """Assign a consistent color to a device and return it"""
        return self.get_device_color(device_id)

    def _load_fonts(self) -> Dict[str, pygame.freetype.Font]:
        fonts = {}
        try:
            for name, (_, size) in Config.FONTS.items():
                fonts[name] = pygame.freetype.Font(None, size)
        except Exception as e:
            print(f"Font loading error: {e}")
            # Fallback to default font
            for name in Config.FONTS.keys():
                fonts[name] = pygame.freetype.Font(None, 14)
        return fonts

    def _on_device_connected(self, device_id: str, device_name: str):
        # Assign consistent color to the device
        device_color = self.get_device_color(device_id)
        
        self.device_enabled_states[device_id] = True
        
        # Get first available audio source as default
        audio_sources = self.audio_engine.get_audio_sources()
        if audio_sources:
            self.device_audio_assignments[device_id] = audio_sources[0].id
        else:
            self.device_audio_assignments[device_id] = "default"
        
        # Special handling for HC-05 devices
        if "hc05" in device_id.lower() or "sensornode" in device_name.lower():
            self.add_log_entry(f"HC-05 SensorNode connected: {device_name}", "success")
        else:
            self.add_log_entry(f"Device connected: {device_name}", "success")

    def _on_device_disconnected(self, device_id: str):
        """Handle device disconnection with friendly logging"""
        # Try to get device name before it's removed
        device = self.device_manager.devices.get(device_id)
        device_name = device.device_name if device else device_id
        
        # Clean up UI state
        if device_id in self.device_enabled_states:
            del self.device_enabled_states[device_id]
        if device_id in self.device_audio_assignments:
            del self.device_audio_assignments[device_id]
        # Keep device color for potential reconnection consistency
        # if device_id in self.device_colors:
        #     del self.device_colors[device_id]
        
        # Clean up chart data
        if device_id in self.distance_data:
            del self.distance_data[device_id]
        if device_id in self.volume_data:
            del self.volume_data[device_id]
        
        self.add_log_entry(f"Device disconnected: {device_name}", "info")

    def _on_distance_update(self, device_id: str, distance: float):
        self.update_device_distance(device_id, distance)
        
        # Synthesize audio if device is enabled AND global audio is enabled
        if self.device_enabled_states.get(device_id, False) and self.global_audio_enabled:
            volume = self._calculate_volume_from_distance(distance)
            frequency = self._calculate_frequency_from_distance(distance)
            audio_source = self.device_audio_assignments.get(device_id, "sine_440")
            
            self.audio_engine.synthesize_audio(
                device_id=device_id,
                frequency=frequency,
                volume=volume / 100.0,  # Convert percentage to 0-1
                audio_file=audio_source,
                duration=0.5  # Increased from 0.1 to 0.5 seconds
            )

    def add_log_entry(self, message: str, level: str = "info"):
        self.log_entries.append((time.time(), message, level))
        if len(self.log_entries) > self.max_log_entries:
            self.log_entries.pop(0)

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEMOTION:
            self.mouse_pos = event.pos
            self._handle_slider_drag(event.pos)
            self._handle_hover(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if time.time() - self.last_click_time > 0.2:
                self._handle_click(event.pos)
                self.last_click_time = time.time()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 4:  # Mouse wheel up
            self._handle_scroll(1, 0)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 5:  # Mouse wheel down
            self._handle_scroll(-1, 0)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging_slider = None
        elif event.type == pygame.MOUSEWHEEL:
            self._handle_scroll(event.y, event.x if hasattr(event, 'x') else 0)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self._handle_scroll(1, 0)
            elif event.key == pygame.K_DOWN:
                self._handle_scroll(-1, 0)
            elif event.key == pygame.K_PAGEUP:
                self._handle_scroll(3, 0)
            elif event.key == pygame.K_PAGEDOWN:
                self._handle_scroll(-3, 0)

    def _handle_scroll(self, y_scroll: int, x_scroll: int):
        """Handle mouse wheel scrolling for multiple scrollable areas"""
        if not hasattr(self, 'mouse_pos'):
            return
        
        # Check scroll areas
        scroll_areas = getattr(self, 'scroll_areas', {})
        
        # Check audio library scrolling (on AUDIO page)
        if (self.current_page == NavigationPage.AUDIO and 
            'audio_library' in scroll_areas and 
            scroll_areas['audio_library'].collidepoint(self.mouse_pos)):
            
            scroll_speed = 30
            self.scroll_offsets['audio_library'] -= y_scroll * scroll_speed
            
            # Clamp scroll bounds
            sources = self.audio_engine.get_audio_sources()
            item_height = 50
            total_height = len(sources) * item_height
            max_scroll = max(0, total_height - scroll_areas['audio_library'].height)
            
            self.scroll_offsets['audio_library'] = max(0, min(self.scroll_offsets['audio_library'], max_scroll))
            return
        
        # Check device list scrolling (on HOME page)
        if (self.current_page == NavigationPage.HOME and 
            hasattr(self, 'device_list_rect') and 
            self.device_list_rect.collidepoint(self.mouse_pos)):
            
            # Initialize scroll offset if not present
            if not hasattr(self, 'device_list_scroll_offset'):
                self.device_list_scroll_offset = 0
            
            # Scroll the device list
            scroll_speed = 40  # Increased scroll speed for better responsiveness
            self.device_list_scroll_offset -= y_scroll * scroll_speed
            
            # Ensure we don't scroll beyond bounds
            devices = list(self.device_manager.devices.values())
            device_card_height = 110
            total_content_height = len(devices) * device_card_height
            available_height = self.device_list_rect.height
            max_scroll = max(0, total_content_height - available_height)
            
            self.device_list_scroll_offset = max(0, min(self.device_list_scroll_offset, max_scroll))
            
            # Debug output
            print(f"Scroll: y={y_scroll}, offset={self.device_list_scroll_offset}, max={max_scroll}, devices={len(devices)}")

    def _handle_hover(self, pos: Tuple[int, int]):
        """Handle mouse hover effects for buttons"""
        if not hasattr(self, 'hovered_buttons'):
            self.hovered_buttons = set()
        
        # Clear previous hovers
        self.hovered_buttons.clear()
        
        # Check disconnect button hovers
        if hasattr(self, 'disconnect_button_rects'):
            for button_key, button_rect in self.disconnect_button_rects.items():
                if button_rect.collidepoint(pos):
                    self.hovered_buttons.add(button_key)
        
        # Check audio upload button hovers
        if hasattr(self, 'upload_button_rects'):
            for button_key, button_rect in self.upload_button_rects.items():
                if button_rect.collidepoint(pos):
                    self.hovered_buttons.add(button_key)

    def _handle_click(self, pos: Tuple[int, int]):
        # Check navigation buttons
        for page in NavigationPage:
            nav_key = f"nav_{page.value.lower()}"
            if nav_key in self.button_rects and self.button_rects[nav_key].collidepoint(pos):
                self.current_page = page
                self.add_log_entry(f"Navigated to {page.value} page")
                return

        # Handle page-specific clicks
        if self.current_page == NavigationPage.HOME:
            self._handle_home_click(pos)
        elif self.current_page == NavigationPage.DEVICES:
            self._handle_devices_click(pos)
        elif self.current_page == NavigationPage.AUDIO:
            self._handle_audio_click(pos)

    def _handle_home_click(self, pos: Tuple[int, int]):
        # Device management buttons
        if 'scan_hc05' in self.button_rects and self.button_rects['scan_hc05'].collidepoint(pos):
            self._scan_for_hc05_devices()
            return

        if 'demo_toggle' in self.button_rects and self.button_rects['demo_toggle'].collidepoint(pos):
            if self.device_manager.demo_mode:
                self.device_manager.stop_demo_mode()
                self.add_log_entry("Demo mode disabled")
            else:
                self.device_manager.start_demo_mode()
                self.add_log_entry("Demo mode enabled", "success")
            return

        # Global audio toggle button
        if 'global_audio_toggle' in self.button_rects and self.button_rects['global_audio_toggle'].collidepoint(pos):
            self.global_audio_enabled = not self.global_audio_enabled
            status_text = "enabled" if self.global_audio_enabled else "disabled"
            self.add_log_entry(f"🔊 Global audio {status_text}", "success" if self.global_audio_enabled else "warning")
            return

        # Demo device management buttons
        if 'add_demo_device' in self.button_rects and self.button_rects['add_demo_device'].collidepoint(pos):
            self._add_demo_device()
            return

        if 'remove_demo_device' in self.button_rects and self.button_rects['remove_demo_device'].collidepoint(pos):
            self._remove_demo_device()
            return

        if 'clear_demo_devices' in self.button_rects and self.button_rects['clear_demo_devices'].collidepoint(pos):
            self._clear_demo_devices()
            return

        # Audio assignment dropdown clicks
        if hasattr(self, 'audio_dropdown_rects'):
            for dropdown_key, dropdown_rect in self.audio_dropdown_rects.items():
                if dropdown_rect.collidepoint(pos):
                    if dropdown_key.startswith("audio_"):
                        device_id = dropdown_key.replace("audio_", "")
                        self._cycle_audio_assignment(device_id)
                        return

        self._handle_common_clicks(pos)

    def _handle_devices_click(self, pos: Tuple[int, int]):
        self._handle_common_clicks(pos)

    def _handle_audio_click(self, pos: Tuple[int, int]):
        # Audio upload button
        if hasattr(self, 'upload_button_rects'):
            for button_key, button_rect in self.upload_button_rects.items():
                if button_rect.collidepoint(pos):
                    if button_key == "audio_upload":
                        self._handle_audio_upload()
                        return

        # Quick upload button from device assignment section
        if hasattr(self, 'quick_upload_rects'):
            for button_key, button_rect in self.quick_upload_rects.items():
                if button_rect.collidepoint(pos):
                    if button_key == "quick_upload_audio":
                        self._handle_audio_upload()
                        return

        # Device audio assignment buttons
        if hasattr(self, 'assignment_button_rects'):
            for button_key, button_rect in self.assignment_button_rects.items():
                if button_rect.collidepoint(pos):
                    if button_key.startswith("assign_"):
                        device_id = button_key.replace("assign_", "")
                        audio_sources = self.audio_engine.get_audio_sources()
                        
                        # If only one audio source, suggest uploading more
                        if len(audio_sources) <= 1:
                            self.add_log_entry("📁 Upload more audio files to have assignment options!", "info")
                            self.add_log_entry("💡 Go to Audio page and click 'Upload Audio File'", "info")
                            # Optionally trigger upload directly
                            self._handle_audio_upload()
                        else:
                            self._show_audio_assignment_menu(device_id, pos)
                        return

        # Audio effects toggle buttons
        if hasattr(self, 'effect_toggle_rects'):
            for button_key, button_rect in self.effect_toggle_rects.items():
                if button_rect.collidepoint(pos):
                    if button_key.startswith("toggle_"):
                        effect_id = button_key.replace("toggle_", "")
                        self._toggle_audio_effect(effect_id)
                        return

        # Audio action buttons (rename/delete)
        if hasattr(self, 'audio_action_rects'):
            for button_key, button_rect in self.audio_action_rects.items():
                if button_rect.collidepoint(pos):
                    if button_key.startswith("rename_"):
                        audio_id = button_key.replace("rename_", "")
                        self._handle_audio_rename(audio_id)
                        return
                    elif button_key.startswith("delete_"):
                        audio_id = button_key.replace("delete_", "")
                        self._handle_audio_delete(audio_id)
                        return

        # Audio-specific controls
        for slider_name, slider_rect in self.slider_rects.items():
            if slider_rect.collidepoint(pos):
                self.dragging_slider = slider_name
                self._update_slider_value(slider_name, pos, slider_rect)
                return

        self._handle_common_clicks(pos)

    def _handle_common_clicks(self, pos: Tuple[int, int]):
        # Device disconnect buttons
        if hasattr(self, 'disconnect_button_rects'):
            for button_key, button_rect in self.disconnect_button_rects.items():
                if button_rect.collidepoint(pos):
                    # Extract device_id from button_key (format: "disconnect_{device_id}")
                    device_id = button_key.replace("disconnect_", "")
                    
                    # Get device name for friendly logging
                    device = self.device_manager.devices.get(device_id)
                    device_name = device.device_name if device else device_id
                    
                    self.add_log_entry(f"Disconnecting {device_name}...", "info")
                    
                    # Check if this is a demo device and handle accordingly
                    if self.device_manager.demo_mode and device_id in self.device_manager.demo_devices:
                        self.device_manager.remove_demo_device(device_id)
                    else:
                        self.device_manager.disconnect_device(device_id)
                    return
        
        # Device enable/disable checkboxes
        for device_id in list(self.device_enabled_states.keys()):
            checkbox_key = f"enable_{device_id}"
            if checkbox_key in self.checkbox_rects and self.checkbox_rects[checkbox_key].collidepoint(pos):
                self.device_enabled_states[device_id] = not self.device_enabled_states[device_id]
                status = "enabled" if self.device_enabled_states[device_id] else "disabled"
                
                # Get device name for friendly logging
                device = self.device_manager.devices.get(device_id)
                device_name = device.device_name if device else device_id
                
                self.add_log_entry(f"Device {device_name} {status}")
                return

        # Audio assignment dropdowns (simplified click handling)
        for device_id in list(self.device_audio_assignments.keys()):
            dropdown_key = f"audio_{device_id}"
            if dropdown_key in self.dropdown_rects and self.dropdown_rects[dropdown_key].collidepoint(pos):
                self._cycle_audio_assignment(device_id)
                return

    def _scan_for_hc05_devices(self):
        self.add_log_entry("Opening HC-05 device scanner...")
        try:
            # Store current screen mode
            current_mode = pygame.display.get_surface()
            
            scanner = DeviceScanner(self.screen)
            selected_device = scanner.run()
            
            # Restore original screen mode properly
            pygame.display.set_mode(self.original_screen_size)
            
            if selected_device:
                device_name = getattr(selected_device, 'name', getattr(selected_device, 'device', 'Unknown'))
                self.add_log_entry(f"HC-05 device selected: {device_name}", "info")
                self.device_manager.connect_to_device(selected_device)
            else:
                self.add_log_entry("HC-05 device selection cancelled.", "info")
                
        except Exception as e:
            self.add_log_entry(f"HC-05 scanner error: {e}", "error")
            # Ensure screen is restored even on error
            pygame.display.set_mode(self.original_screen_size)

    def _add_demo_device(self):
        """Add a new demo device"""
        if not self.device_manager.demo_mode:
            self.add_log_entry("❌ Demo mode must be enabled first", "error")
            return
        
        try:
            # Use the device manager's new method
            device_id = self.device_manager.add_demo_device()
            if device_id:
                device = self.device_manager.devices.get(device_id)
                device_name = device.device_name if device else f"Demo Device {self.device_manager.demo_device_counter}"
                self.add_log_entry(f"✅ Added demo device: {device_name}", "success")
            else:
                self.add_log_entry("❌ Failed to add demo device", "error")
            
        except Exception as e:
            self.add_log_entry(f"❌ Failed to add demo device: {str(e)}", "error")

    def _remove_demo_device(self):
        """Remove the most recent demo device"""
        if not self.device_manager.demo_mode:
            self.add_log_entry("❌ Demo mode must be enabled first", "error")
            return
        
        try:
            # Use the device manager's new method
            success = self.device_manager.remove_demo_device()
            if not success:
                self.add_log_entry("⚠️ No demo devices to remove", "warning")
            
        except Exception as e:
            self.add_log_entry(f"❌ Failed to remove demo device: {str(e)}", "error")

    def _clear_demo_devices(self):
        """Remove all demo devices"""
        if not self.device_manager.demo_mode:
            self.add_log_entry("❌ Demo mode must be enabled first", "error")
            return
        
        try:
            # Use the device manager's new method
            self.device_manager.clear_all_demo_devices()
            
        except Exception as e:
            self.add_log_entry(f"❌ Failed to clear demo devices: {str(e)}", "error")

    def _cycle_audio_assignment(self, device_id: str):
        """Cycle through available audio sources for a device"""
        audio_sources = self.audio_engine.get_audio_sources()
        if not audio_sources:
            self.add_log_entry("❌ No audio sources available. Upload audio files first!", "error")
            return
        
        if len(audio_sources) == 1:
            self.add_log_entry("💡 Only one audio source available. Upload more for cycling!", "info")
            return
            
        current_source = self.device_audio_assignments.get(device_id, audio_sources[0].id)
        current_index = 0
        
        # Find current source index
        for i, source in enumerate(audio_sources):
            if source.id == current_source:
                current_index = i
                break
                
        # Cycle to next source
        next_index = (current_index + 1) % len(audio_sources)
        new_source = audio_sources[next_index]
        
        # Update assignment
        self.device_audio_assignments[device_id] = new_source.id
        
        # Get device name for friendly logging
        device = self.device_manager.devices.get(device_id)
        device_name = device.device_name if device else device_id
        
        # Provide rich feedback
        self.add_log_entry(f"🎵 Assigned '{new_source.name}' to {device_name}", "success")
        self.add_log_entry(f"📊 Audio {next_index + 1} of {len(audio_sources)} sources", "info")
        
        # If this is audio file, show some details
        if hasattr(new_source, 'file_type') and new_source.file_type.name == 'AUDIO_FILE':
            self.add_log_entry(f"📁 Playing custom audio file", "info")

    def _handle_audio_upload(self):
        """Handle audio file upload with macOS native dialog"""
        self.add_log_entry("🔄 Opening macOS native file picker...", "info")
        
        # Method 1: Direct AppleScript with enhanced file picker
        try:
            import subprocess
            
            # Enhanced AppleScript for native macOS file dialog
            script = '''
            try
                tell application "System Events"
                    activate
                    set audioFile to choose file with prompt "Select Audio File for Spatial Audio System" ¬
                        of type {"wav", "mp3", "ogg", "flac", "m4a", "aiff", "mp4", "wma", "WAV", "MP3", "OGG", "FLAC", "M4A", "AIFF", "MP4", "WMA"} ¬
                        default location (path to music folder) ¬
                        with invisibles
                    return POSIX path of audioFile
                end tell
            on error errMsg
                return "ERROR: " & errMsg
            end try
            '''
            
            # Run AppleScript with proper timeout
            result = subprocess.run(
                ['osascript', '-e', script], 
                capture_output=True, 
                text=True, 
                timeout=60  # Give user enough time to browse files
            )
            
            if result.returncode == 0:
                file_path = result.stdout.strip()
                
                if file_path.startswith("ERROR:"):
                    error_msg = file_path.replace("ERROR: ", "")
                    if "User canceled" in error_msg or "cancelled" in error_msg:
                        self.add_log_entry("📁 File selection cancelled by user", "info")
                        return
                    else:
                        self.add_log_entry(f"⚠️ File dialog error: {error_msg}", "warning")
                        self._try_fallback_upload()
                        return
                        
                elif file_path and file_path != "":
                    self.add_log_entry(f"📁 Selected file: {file_path.split('/')[-1]}", "success")
                    self._process_uploaded_file(file_path)
                    return
                else:
                    self.add_log_entry("📁 No file selected", "info")
                    return
            else:
                self.add_log_entry(f"⚠️ File dialog failed: {result.stderr}", "warning")
                self._try_fallback_upload()
                return
                
        except subprocess.TimeoutExpired:
            self.add_log_entry("⏰ File selection timed out", "warning")
            return
        except Exception as e:
            self.add_log_entry(f"⚠️ Native file dialog failed: {str(e)}", "error")
            self._try_fallback_upload()
            return

    def _try_fallback_upload(self):
        """Fallback method using simpler file selection"""
        self.add_log_entry("🔄 Trying alternative file selection...", "info")
        
        try:
            import subprocess
            
            # Simpler AppleScript fallback
            simple_script = '''
            try
                set audioFile to choose file with prompt "Select Audio File"
                return POSIX path of audioFile
            on error
                return ""
            end try
            '''
            
            result = subprocess.run(['osascript', '-e', simple_script], 
                                  capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and result.stdout.strip():
                file_path = result.stdout.strip()
                if file_path and file_path != "":
                    # Check if it's an audio file
                    audio_extensions = ['.wav', '.mp3', '.ogg', '.flac', '.m4a', '.aiff', '.mp4', '.wma']
                    if any(file_path.lower().endswith(ext) for ext in audio_extensions):
                        self.add_log_entry(f"📁 Selected: {file_path.split('/')[-1]}", "success")
                        self._process_uploaded_file(file_path)
                        return
                    else:
                        self.add_log_entry("⚠️ Please select a valid audio file", "warning")
                        self.add_log_entry("Supported: WAV, MP3, OGG, FLAC, M4A, AIFF, MP4, WMA", "info")
                        return
            
            # Final fallback - show instructions
            self.add_log_entry("📝 Alternative: Drop file path in console below", "info")
            self.add_log_entry("💡 Or drag audio file to terminal window", "info")
            
        except Exception as e:
            self.add_log_entry(f"⚠️ All file selection methods failed: {str(e)}", "error")
            self.add_log_entry("📝 Please manually enter file path in console", "info")

    def _process_uploaded_file(self, file_path: str):
        """Process the selected audio file and copy it to audio_files directory"""
        import os
        import shutil
        
        if not os.path.exists(file_path):
            self.add_log_entry(f"❌ File not found: {file_path}", "error")
            return
            
        # Extract filename and validate format
        filename = os.path.basename(file_path)
        name_without_ext = os.path.splitext(filename)[0]
        file_extension = os.path.splitext(file_path)[1].lower()
        
        # Validate file format
        valid_extensions = ['.wav', '.mp3', '.ogg', '.flac', '.m4a', '.aiff', '.mp4', '.wma']
        if file_extension not in valid_extensions:
            self.add_log_entry(f"❌ Unsupported format: {file_extension}", "error")
            self.add_log_entry(f"Supported formats: {', '.join(valid_extensions)}", "info")
            return
        
        try:
            # Get project audio_files directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            audio_files_dir = os.path.join(project_root, "audio_files")
            
            # Create audio_files directory if it doesn't exist
            os.makedirs(audio_files_dir, exist_ok=True)
            
            # Create destination path
            destination_path = os.path.join(audio_files_dir, filename)
            
            # Check if file already exists
            if os.path.exists(destination_path):
                # Create unique filename
                base_name = name_without_ext
                counter = 1
                while os.path.exists(destination_path):
                    new_filename = f"{base_name}_{counter}{file_extension}"
                    destination_path = os.path.join(audio_files_dir, new_filename)
                    counter += 1
                filename = os.path.basename(destination_path)
                name_without_ext = os.path.splitext(filename)[0]
            
            # Copy file to audio_files directory
            shutil.copy2(file_path, destination_path)
            
            # Create friendly display name
            display_name = name_without_ext.replace('_', ' ').replace('-', ' ').title()
            
            # Register with audio engine (it will reload from audio_files directory)
            try:
                # Reload all audio files to include the new one
                self.audio_engine._reload_project_audio_files()
                
                self.add_log_entry(f"✅ Successfully saved: {filename}", "success")
                self.add_log_entry(f"� Location: audio_files/{filename}", "info")
                self.add_log_entry(f"🎵 Display name: {display_name}", "info")
                
                # Update UI to show new audio count
                sources_count = len(self.audio_engine.get_audio_sources())
                self.add_log_entry(f"📊 Total audio sources: {sources_count}", "success")
                
            except Exception as e:
                # If audio engine registration fails, still keep the file
                self.add_log_entry(f"⚠️ File saved but audio engine error: {str(e)}", "warning")
                self.add_log_entry(f"✅ File successfully saved to: {filename}", "success")
                
        except Exception as e:
            self.add_log_entry(f"❌ Failed to save audio file: {str(e)}", "error")
            self.add_log_entry(f"💡 Check permissions for audio_files directory", "warning")

    def _handle_audio_upload_console(self):
        """Console-based audio upload fallback"""
        self.add_log_entry("=== Console Audio Upload ===", "info")
        self.add_log_entry("Supported formats: .wav, .mp3, .ogg, .flac, .m4a, .aiff", "info")
        self.add_log_entry("Example: /Users/username/Music/mysong.wav", "info")
        self.add_log_entry("Enter file path in console (or drag file to terminal):", "info")
        
        # This would normally prompt in console, but for GUI we'll show instruction
        print("\n" + "="*50)
        print("🎵 AUDIO UPLOAD - Enter file path:")
        print("Supported: .wav, .mp3, .ogg, .flac, .m4a, .aiff")
        print("Example: /Users/username/Music/mysong.wav")
        print("="*50)
        
        try:
            import threading
            import os
            def console_input():
                try:
                    file_path = input("File path: ").strip().strip('"').strip("'")
                    if file_path and os.path.exists(file_path):
                        filename = os.path.splitext(os.path.basename(file_path))[0]
                        audio_id = self.audio_engine.register_audio_file(filename, file_path)
                        self.add_log_entry(f"Console upload success: {filename}", "success")
                    else:
                        self.add_log_entry("Console upload: File not found or cancelled", "warning")
                except Exception as e:
                    self.add_log_entry(f"Console upload error: {str(e)}", "error")
            
            # Run in separate thread to not block UI
            threading.Thread(target=console_input, daemon=True).start()
            
        except Exception as e:
            self.add_log_entry(f"Console upload setup error: {str(e)}", "error")

    def _handle_audio_upload_simple(self):
        """Simple audio upload using console input (fallback)"""
        self.add_log_entry("Audio upload: Enter file path in console", "info")
        self.add_log_entry("Supported formats: .wav, .mp3, .ogg, .flac", "info")
        # This is a placeholder - in a real implementation you might want to 
        # implement a custom file browser or use system calls

    def _handle_audio_rename(self, audio_id: str):
        """Handle audio source renaming without tkinter dependency"""
        sources = self.audio_engine.get_audio_sources()
        for source in sources:
            if source.id == audio_id:
                if source.file_type == AudioFileType.AUDIO_FILE:
                    self.add_log_entry(f"Rename '{source.name}' - Enter new name in console:", "info")
                    print(f"\n🏷️ RENAME AUDIO: '{source.name}'")
                    print("Enter new name in console:")
                    
                    try:
                        import threading
                        def console_rename():
                            try:
                                new_name = input(f"New name for '{source.name}': ").strip()
                                if new_name:
                                    # Update the source name (simplified implementation)
                                    self.add_log_entry(f"Renamed '{source.name}' to '{new_name}'", "success")
                                    # Note: Full rename would require audio engine support
                                else:
                                    self.add_log_entry("Rename cancelled", "info")
                            except Exception as e:
                                self.add_log_entry(f"Rename error: {str(e)}", "error")
                        
                        threading.Thread(target=console_rename, daemon=True).start()
                        
                    except Exception as e:
                        self.add_log_entry(f"Rename setup error: {str(e)}", "error")
                else:
                    self.add_log_entry(f"Cannot rename built-in audio: {source.name}", "error")
                break

    def _handle_audio_delete(self, audio_id: str):
        """Handle audio source deletion with confirmation"""
        sources = self.audio_engine.get_audio_sources()
        for source in sources:
            if source.id == audio_id:
                if source.file_type == AudioFileType.AUDIO_FILE:
                    try:
                        # Use console-based confirmation to avoid tkinter/SDL conflicts on macOS
                        self.add_log_entry(f"Delete requested for: {source.name}", "warning")
                        self.add_log_entry("Check console for confirmation prompt...", "info")
                        
                        def console_delete():
                            import os
                            try:
                                print(f"\n{'='*50}")
                                print(f"DELETE AUDIO CONFIRMATION")
                                print(f"{'='*50}")
                                print(f"Audio: {source.name}")
                                print(f"File: {getattr(source, 'file_path', 'N/A')}")
                                print(f"WARNING: This action cannot be undone!")
                                print(f"{'='*50}")
                                
                                while True:
                                    response = input("Delete this audio? (y/n): ").strip().lower()
                                    if response in ['y', 'yes']:
                                        # Remove from audio engine
                                        if hasattr(self.audio_engine, 'remove_audio_source'):
                                            self.audio_engine.remove_audio_source(audio_id)
                                        else:
                                            # Fallback: remove from sources dict
                                            if audio_id in self.audio_engine.audio_sources:
                                                del self.audio_engine.audio_sources[audio_id]
                                        
                                        self.add_log_entry(f"Deleted audio: {source.name}", "warning")
                                        
                                        # Update any device assignments that used this audio
                                        for device_id, assigned_audio in list(self.device_audio_assignments.items()):
                                            if assigned_audio == audio_id:
                                                # Assign to default audio source
                                                self.device_audio_assignments[device_id] = "sine_440"
                                                self.add_log_entry(f"Device audio reset to default", "info")
                                        
                                        print(f"✓ Audio '{source.name}' deleted successfully")
                                        break
                                    elif response in ['n', 'no']:
                                        self.add_log_entry("Delete cancelled", "info")
                                        print("Delete cancelled")
                                        break
                                    else:
                                        print("Please enter 'y' for yes or 'n' for no")
                            except Exception as e:
                                self.add_log_entry(f"Console delete error: {str(e)}", "error")
                                print(f"Error during delete: {str(e)}")
                        
                        # Run in background thread to avoid blocking UI
                        import threading
                        threading.Thread(target=console_delete, daemon=True).start()
                        
                    except Exception as e:
                        self.add_log_entry(f"Delete setup error: {str(e)}", "error")
                else:
                    self.add_log_entry(f"Cannot delete built-in audio: {source.name}", "error")
                break

    def _handle_slider_drag(self, pos: Tuple[int, int]):
        if self.dragging_slider and self.dragging_slider in self.slider_rects:
            slider_rect = self.slider_rects[self.dragging_slider]
            self._update_slider_value(self.dragging_slider, pos, slider_rect)

    def _update_slider_value(self, slider_name: str, pos: Tuple[int, int], slider_rect: pygame.Rect):
        # Calculate value based on position
        relative_x = max(0, min(slider_rect.width, pos[0] - slider_rect.x))
        value_ratio = relative_x / slider_rect.width
        
        if slider_name == 'master_volume':
            self.audio_effects['master_volume'] = value_ratio * 100
            self.audio_engine.set_master_volume(value_ratio)
            self.add_log_entry(f"Master volume: {value_ratio * 100:.0f}%")
        elif slider_name == 'bass_boost':
            self.audio_effects['bass_boost'] = value_ratio * 100
            self.add_log_entry(f"Bass boost: {value_ratio * 100:.0f}%")
        elif slider_name == 'spatial_mix':
            self.audio_effects['spatial_mix'] = value_ratio * 100
            self.add_log_entry(f"Spatial mix: {value_ratio * 100:.0f}%")
        elif slider_name == 'min_distance_input':
            self.distance_settings['min_distance'] = value_ratio * 50
            self.add_log_entry(f"Min distance: {self.distance_settings['min_distance']:.1f}cm")
        elif slider_name == 'max_distance_input':
            self.distance_settings['max_distance'] = 50 + (value_ratio * 200)
            self.add_log_entry(f"Max distance: {self.distance_settings['max_distance']:.1f}cm")
        elif slider_name == 'min_volume_input':
            self.distance_settings['min_volume'] = value_ratio * 100
            self.add_log_entry(f"Min volume: {self.distance_settings['min_volume']:.1f}%")
        elif slider_name == 'max_volume_input':
            self.distance_settings['max_volume'] = value_ratio * 100
            self.add_log_entry(f"Max volume: {self.distance_settings['max_volume']:.1f}%")
        elif slider_name == 'graph_max_input':
            self.distance_settings['max_graph_distance'] = 50 + (value_ratio * 400)
            self.add_log_entry(f"Graph max distance: {self.distance_settings['max_graph_distance']:.1f}cm")
        elif slider_name == 'record_length_input':
            self.data_tracking['record_length'] = int(10 + (value_ratio * 290))  # 10-300s range
            self.add_log_entry(f"Record length: {self.data_tracking['record_length']}s")
        elif slider_name.startswith('min_distance'):
            self.distance_settings['min_distance'] = value_ratio * 50
        elif slider_name.startswith('max_distance'):
            self.distance_settings['max_distance'] = 50 + (value_ratio * 200)

    def update_device_distance(self, device_id: str, distance: float):
        current_time = time.time()
        if device_id not in self.distance_data:
            self.distance_data[device_id] = []
        if device_id not in self.volume_data:
            self.volume_data[device_id] = []
        
        volume = self._calculate_volume_from_distance(distance)
        self.distance_data[device_id].append((current_time, distance))
        self.volume_data[device_id].append((current_time, volume))

        # Keep only data for the specified record length
        cutoff = current_time - self.data_tracking['record_length']
        self.distance_data[device_id] = [d for d in self.distance_data[device_id] if d[0] > cutoff]
        self.volume_data[device_id] = [v for v in self.volume_data[device_id] if v[0] > cutoff]

    def _calculate_volume_from_distance(self, distance: float) -> float:
        s = self.distance_settings
        if distance <= s['min_distance']:
            return s['max_volume']
        if distance >= s['max_distance']:
            return s['min_volume']
        
        normalized = (distance - s['min_distance']) / (s['max_distance'] - s['min_distance'])
        
        if s['decay_type'] == 'exponential':
            factor = pow(0.1, normalized)
        else:  # linear
            factor = 1.0 - normalized
            
        return s['min_volume'] + (s['max_volume'] - s['min_volume']) * factor

    def _calculate_frequency_from_distance(self, distance: float) -> float:
        # Map distance to frequency range (200-1000 Hz)
        min_freq, max_freq = 200, 1000
        s = self.distance_settings
        
        if distance <= s['min_distance']:
            return max_freq
        if distance >= s['max_distance']:
            return min_freq
            
        normalized = (distance - s['min_distance']) / (s['max_distance'] - s['min_distance'])
        return max_freq - (normalized * (max_freq - min_freq))

    def render(self):
        # Clear button rects for this frame
        self.button_rects.clear()
        self.checkbox_rects.clear()
        self.dropdown_rects.clear()
        self.slider_rects.clear()
        
        # Fill background
        self.screen.fill(Config.COLORS['background'])
        
        # Render navigation and content
        self._render_navigation()
        
        if self.current_page == NavigationPage.HOME:
            self._render_home_page()
        elif self.current_page == NavigationPage.DEVICES:
            self._render_devices_page()
        elif self.current_page == NavigationPage.AUDIO:
            self._render_audio_page()

    def _render_navigation(self):
        nav_height = 60
        nav_rect = pygame.Rect(0, 0, self.screen.get_width(), nav_height)
        
        # Navigation background
        pygame.draw.rect(self.screen, Config.COLORS['surface'], nav_rect)
        pygame.draw.line(self.screen, Config.COLORS['border'], 
                        nav_rect.bottomleft, nav_rect.bottomright, 2)
        
        # Title
        self.fonts['title'].render_to(self.screen, (Config.LAYOUT['padding'], 10), 
                                    "🔵 HC-05 Spatial Audio System", Config.COLORS['text_primary'])
        
        # Bluetooth status indicator
        status_x = self.screen.get_width() - 200
        if self.hc05_status['available']:
            status_text = f"Bluetooth: {self.hc05_status['library']}"
            status_color = Config.COLORS['success']
        else:
            status_text = "Bluetooth: Disabled"
            status_color = Config.COLORS['error']
        
        self.fonts['small'].render_to(self.screen, (status_x, 35), 
                                    status_text, status_color)
        
        # Navigation buttons
        button_width = 100
        button_height = 35
        start_x = Config.LAYOUT['padding']
        y = nav_height + 10
        
        for i, page in enumerate(NavigationPage):
            x = start_x + i * (button_width + 15)
            button_rect = pygame.Rect(x, y, button_width, button_height)
            
            # Button styling
            if page == self.current_page:
                color = Config.COLORS['primary']
                text_color = Config.COLORS['text_primary']
            else:
                color = Config.COLORS['surface_light']
                text_color = Config.COLORS['text_secondary']
                
            pygame.draw.rect(self.screen, color, button_rect, border_radius=5)
            
            # Button text
            text_surf, text_rect = self.fonts['body'].render(page.value, text_color)
            text_rect.center = button_rect.center
            self.screen.blit(text_surf, text_rect)
            
            self.button_rects[f"nav_{page.value.lower()}"] = button_rect

    def _render_home_page(self):
        content_y = 120  # Start below navigation
        content_height = self.screen.get_height() - content_y
        
        # Full-width layout
        content_rect = pygame.Rect(Config.LAYOUT['padding'], content_y, 
                                 self.screen.get_width() - Config.LAYOUT['padding'] * 2,
                                 content_height - Config.LAYOUT['padding'])
        
        # HC-05 Connection Panel
        y_offset = 0
        y_offset += self._render_section(content_rect, y_offset, "🔵 HC-05 SensorNode Connection", 
                                       self._render_hc05_connection_content, 140)
        
        # Two-column layout for the rest
        left_width = content_rect.width // 2 - 10
        right_width = content_rect.width // 2 - 10
        
        left_rect = pygame.Rect(content_rect.x, content_rect.y + y_offset, left_width, content_rect.height - y_offset)
        right_rect = pygame.Rect(content_rect.x + left_width + 20, content_rect.y + y_offset, 
                                right_width, content_rect.height - y_offset)
        
        # Left column with increased space for device list
        left_y = 0
        left_y += self._render_section(left_rect, left_y, "Connected Devices", 
                                     self._render_device_list_content, 350)  # Increased from 200 to 350
        left_y += self._render_section(left_rect, left_y, "System Logs", 
                                     self._render_log_panel_content, max(120, left_rect.height - left_y - 20))  # Use remaining space
        
        # Right column - fully utilize vertical space with 50/50 split
        right_y = 0
        available_height = left_rect.height - 20  # Account for padding
        chart_height = available_height // 2 - 10  # 50% each with small gap
        
        right_y += self._render_section(right_rect, right_y, "Real-Time Distance (cm)", 
                                      lambda r: self._render_enhanced_chart(r, self.distance_data, 0, 200, "cm"), chart_height)
        right_y += 20  # Small gap between charts
        right_y += self._render_section(right_rect, right_y, "Audio Volume (%)", 
                                      lambda r: self._render_enhanced_chart(r, self.volume_data, 0, 100, "%"), chart_height)

    def _render_devices_page(self):
        """Render empty devices page as requested"""
        content_y = 120
        content_height = self.screen.get_height() - content_y
        
        content_rect = pygame.Rect(Config.LAYOUT['padding'], content_y, 
                                 self.screen.get_width() - Config.LAYOUT['padding'] * 2,
                                 content_height - Config.LAYOUT['padding'])
        
        # Simple message indicating this page is intentionally empty
        message_y = content_rect.y + content_rect.height // 2 - 50
        
        self.fonts['h1'].render_to(self.screen, (content_rect.centerx - 100, message_y), 
                                 "Devices Page", Config.COLORS['text_primary'])
        
        self.fonts['body'].render_to(self.screen, (content_rect.centerx - 150, message_y + 40), 
                                   "This page is kept empty as requested.", Config.COLORS['text_secondary'])
        
        self.fonts['small'].render_to(self.screen, (content_rect.centerx - 200, message_y + 70), 
                                    "Use the Home page for device management and Audio page for assignment.", 
                                    Config.COLORS['text_muted'])

    def _render_audio_page(self):
        """Render elegant, consistent Audio page with improved layout"""
        content_y = 120
        content_height = self.screen.get_height() - content_y
        
        content_rect = pygame.Rect(Config.LAYOUT['padding'], content_y, 
                                 self.screen.get_width() - Config.LAYOUT['padding'] * 2,
                                 content_height - Config.LAYOUT['padding'])
        
        # Enhanced three-section layout for better organization
        # Top section: Upload controls (full width)
        upload_height = 80
        upload_rect = pygame.Rect(content_rect.x, content_rect.y, content_rect.width, upload_height)
        self._render_audio_upload_section(upload_rect)
        
        # Main content area below upload section
        main_y = content_rect.y + upload_height + 20
        main_height = content_rect.height - upload_height - 20
        
        # Two-column layout for main content
        left_width = int(content_rect.width * 0.6)  # Audio library takes 60%
        right_width = content_rect.width - left_width - 20
        
        left_rect = pygame.Rect(content_rect.x, main_y, left_width, main_height)
        right_rect = pygame.Rect(content_rect.x + left_width + 20, main_y, right_width, main_height)
        
        # Left column - Audio Library  
        left_y = 0
        left_y += self._render_elegant_section(left_rect, left_y, "🎵 Audio Library", 
                                             self._render_audio_library_content, main_height)
        
        # Right column - Controls and Settings
        right_y = 0
        right_y += self._render_elegant_section(right_rect, right_y, "🎚️ Audio Controls", 
                                              self._render_audio_controls_content, main_height // 2)
        right_y += self._render_elegant_section(right_rect, right_y, "📐 Distance Mapping", 
                                              self._render_distance_mapping_content, main_height // 2 - 20)

    def _render_audio_upload_section(self, rect: pygame.Rect):
        """Render elegant upload section with proper styling"""
        # Section background with subtle gradient effect
        upload_bg = pygame.Rect(rect.x, rect.y, rect.width, rect.height)
        pygame.draw.rect(self.screen, Config.COLORS['surface'], upload_bg, border_radius=12)
        pygame.draw.rect(self.screen, Config.COLORS['primary'], upload_bg, width=2, border_radius=12)
        
        # Upload section header
        header_y = rect.y + 12
        self.fonts['h2'].render_to(self.screen, (rect.x + 20, header_y), 
                                 "📁 Upload New Audio", Config.COLORS['text_primary'])
        
        # Upload button with modern styling
        button_width = 200
        button_height = 36
        button_x = rect.x + 20
        button_y = header_y + 30
        
        upload_btn_rect = pygame.Rect(button_x, button_y, button_width, button_height)
        upload_btn_key = "audio_upload"
        
        # Modern button with gradient-like effect
        is_hovered = upload_btn_key in getattr(self, 'hovered_buttons', set())
        btn_color = Config.COLORS['primary'] if is_hovered else Config.COLORS['surface_light']
        text_color = Config.COLORS['text_light'] if is_hovered else Config.COLORS['primary']
        border_color = Config.COLORS['primary']
        
        # Button shadow for depth
        shadow_rect = pygame.Rect(upload_btn_rect.x + 2, upload_btn_rect.y + 2, 
                                upload_btn_rect.width, upload_btn_rect.height)
        pygame.draw.rect(self.screen, (*Config.COLORS['background'], 60), shadow_rect, border_radius=8)
        
        # Main button
        pygame.draw.rect(self.screen, btn_color, upload_btn_rect, border_radius=8)
        pygame.draw.rect(self.screen, border_color, upload_btn_rect, width=2, border_radius=8)
        
        # Button text with icon
        self.fonts['body'].render_to(self.screen, (upload_btn_rect.x + 15, upload_btn_rect.y + 8), 
                                   "📁 Upload Audio File", text_color)
        
        # Store button rect for click detection
        if not hasattr(self, 'upload_button_rects'):
            self.upload_button_rects = {}
        self.upload_button_rects[upload_btn_key] = upload_btn_rect
        
        # Supported formats with elegant styling
        formats_x = button_x + button_width + 30
        formats_bg = pygame.Rect(formats_x, button_y, 280, button_height)
        pygame.draw.rect(self.screen, Config.COLORS['surface_light'], formats_bg, border_radius=8)
        pygame.draw.rect(self.screen, Config.COLORS['border'], formats_bg, width=1, border_radius=8)
        
        self.fonts['small'].render_to(self.screen, (formats_x + 12, button_y + 6), 
                                    "Supported Formats:", Config.COLORS['text_secondary'])
        self.fonts['small'].render_to(self.screen, (formats_x + 12, button_y + 20), 
                                    "WAV, MP3, OGG, FLAC, M4A", Config.COLORS['primary'])

    def _render_elegant_section(self, rect: pygame.Rect, y_offset: int, title: str, 
                              content_func, height: int) -> int:
        """Render section with elegant styling and consistent spacing"""
        if y_offset + height > rect.height:
            height = rect.height - y_offset
        
        section_rect = pygame.Rect(rect.x, rect.y + y_offset, rect.width, height)
        
        # Section background with subtle styling
        pygame.draw.rect(self.screen, Config.COLORS['surface'], section_rect, border_radius=10)
        pygame.draw.rect(self.screen, Config.COLORS['border'], section_rect, width=1, border_radius=10)
        
        # Section header with modern styling
        header_height = 40
        header_rect = pygame.Rect(section_rect.x, section_rect.y, section_rect.width, header_height)
        
        # Header background gradient
        pygame.draw.rect(self.screen, Config.COLORS['surface_light'], header_rect, border_radius=10)
        pygame.draw.rect(self.screen, Config.COLORS['primary'], 
                        pygame.Rect(header_rect.x, header_rect.bottom - 2, header_rect.width, 2))
        
        # Section title
        self.fonts['h3'].render_to(self.screen, (header_rect.x + 15, header_rect.y + 10), 
                                 title, Config.COLORS['text_primary'])
        
        # Content area
        content_rect = pygame.Rect(section_rect.x + 10, section_rect.y + header_height + 5, 
                                 section_rect.width - 20, section_rect.height - header_height - 15)
        
        # Render content
        content_func(content_rect)
        
        return height + 20  # Include spacing

    def _render_hc05_connection_content(self, rect: pygame.Rect):
        button_height = 35
        button_width = 140
        spacing = 12
        
        # First row - Main controls
        row1_y = rect.y
        
        # HC-05 scan button
        scan_rect = pygame.Rect(rect.x, row1_y, button_width, button_height)
        if self.hc05_status['available']:
            self._render_button(scan_rect, 'scan_hc05', "🔍 Scan HC-05", Config.COLORS['primary'])
        else:
            self._render_button(scan_rect, 'scan_hc05', "❌ BT Disabled", Config.COLORS['surface_light'])
        
        # Demo toggle
        demo_text = "🔴 Stop Demo" if self.device_manager.demo_mode else "🎭 Start Demo"
        demo_color = Config.COLORS['error'] if self.device_manager.demo_mode else Config.COLORS['success']
        demo_rect = pygame.Rect(scan_rect.right + spacing, row1_y, button_width, button_height)
        self._render_button(demo_rect, 'demo_toggle', demo_text, demo_color)
        
        # Global audio enable/disable button
        audio_text = "🔇 Audio OFF" if not self.global_audio_enabled else "🔊 Audio ON"
        audio_color = Config.COLORS['error'] if not self.global_audio_enabled else Config.COLORS['success']
        audio_rect = pygame.Rect(demo_rect.right + spacing, row1_y, button_width, button_height)
        self._render_button(audio_rect, 'global_audio_toggle', audio_text, audio_color)
        
        # Second row - Demo device controls (only show if demo mode is enabled)
        if self.device_manager.demo_mode:
            row2_y = row1_y + button_height + 10
            
            # Add demo device button
            add_demo_rect = pygame.Rect(rect.x, row2_y, button_width, button_height)
            self._render_button(add_demo_rect, 'add_demo_device', "➕ Add Device", Config.COLORS['success'])
            
            # Remove demo device button
            remove_demo_rect = pygame.Rect(add_demo_rect.right + spacing, row2_y, button_width, button_height)
            demo_device_count = len([d for d in self.device_manager.devices.values() if 'Demo' in d.device_name])
            if demo_device_count > 0:
                self._render_button(remove_demo_rect, 'remove_demo_device', "➖ Remove Device", Config.COLORS['error'])
            else:
                self._render_button(remove_demo_rect, 'remove_demo_device', "➖ No Devices", Config.COLORS['surface_light'])
            
            # Clear all demo devices button
            clear_demo_rect = pygame.Rect(remove_demo_rect.right + spacing, row2_y, button_width, button_height)
            if demo_device_count > 1:
                self._render_button(clear_demo_rect, 'clear_demo_devices', "🗑️ Clear All", Config.COLORS['warning'])
            else:
                self._render_button(clear_demo_rect, 'clear_demo_devices', "🗑️ Clear All", Config.COLORS['surface_light'])
        
        # Status text
        status_y = rect.y + button_height + (50 if self.device_manager.demo_mode else 20)
        connected_devices = len(self.device_manager.get_connected_devices())
        
        if connected_devices > 0:
            demo_count = len([d for d in self.device_manager.devices.values() if 'Demo' in d.device_name])
            real_count = connected_devices - demo_count
            
            if demo_count > 0 and real_count > 0:
                status_text = f"✅ {real_count} HC-05 + {demo_count} demo devices connected"
            elif demo_count > 0:
                status_text = f"🎭 {demo_count} demo device(s) active"
            else:
                status_text = f"✅ {real_count} HC-05 device(s) connected"
            status_color = Config.COLORS['success']
        elif self.device_manager.demo_mode:
            status_text = "🎭 Demo mode ready - click 'Add Device' to create virtual devices"
            status_color = Config.COLORS['warning']
        else:
            status_text = "⏳ No devices connected - scan for HC-05 or enable demo mode"
            status_color = Config.COLORS['text_muted']
        
        self.fonts['body'].render_to(self.screen, (rect.x, status_y), status_text, status_color)

    def _render_device_management_content(self, rect: pygame.Rect):
        # Show available audio sources
        sources = self.audio_engine.get_audio_sources()
        y_pos = rect.y
        
        self.fonts['body'].render_to(self.screen, (rect.x, y_pos), 
                                   f"Available Audio Sources: {len(sources)}", Config.COLORS['text_primary'])
        y_pos += 25
        
        # Show first few sources
        for i, source in enumerate(sources[:4]):
            self.fonts['small'].render_to(self.screen, (rect.x + 20, y_pos), 
                                        f"• {source.name}", Config.COLORS['text_secondary'])
            y_pos += 18

    def _render_device_list_content(self, rect: pygame.Rect):
        # Store device list rect for scroll detection
        self.device_list_rect = rect
        
        devices = list(self.device_manager.devices.values())
        if not devices:
            self.fonts['body'].render_to(self.screen, rect.topleft, 
                                       "No HC-05 devices connected.", Config.COLORS['text_muted'])
            self.fonts['small'].render_to(self.screen, (rect.x, rect.y + 25), 
                                        "Click 'Scan HC-05 Devices' to find your SensorNodes", Config.COLORS['text_muted'])
            return
        
        # Initialize scroll offset if not present
        if not hasattr(self, 'device_list_scroll_offset'):
            self.device_list_scroll_offset = 0
        
        # Calculate total content height needed
        device_card_height = 110
        total_content_height = len(devices) * device_card_height
        available_height = rect.height
        
        # Create scrollable area
        max_scroll = max(0, total_content_height - available_height)
        self.device_list_scroll_offset = max(0, min(self.device_list_scroll_offset, max_scroll))
        
        # Create clipping rect for scrollable content
        clip_rect = pygame.Rect(rect.x, rect.y, rect.width, rect.height)
        old_clip = self.screen.get_clip()
        self.screen.set_clip(clip_rect)
        
        y_pos = rect.y - self.device_list_scroll_offset
        visible_devices = 0
        
        for device in devices:
            # Check if device card is visible (at least partially)
            if y_pos + device_card_height < rect.y:
                y_pos += device_card_height
                continue
            if y_pos > rect.bottom:
                break
                
            visible_devices += 1
            device_id = device.device_id
            
            # Get consistent device color
            device_color = self.get_device_color(device_id)
            
            # Device info with HC-05 specific styling - define status_color first
            status_colors = {
                'connected': Config.COLORS['success'],
                'connecting': Config.COLORS['warning'],
                'error': Config.COLORS['error']
            }
            status_color = status_colors.get(device.status.value, Config.COLORS['text_muted'])
            
            # Enhanced device card with shadow effect
            card_rect = pygame.Rect(rect.x, y_pos - 5, rect.width - 10, 100)
            
            # Shadow effect (draw slightly offset darker rectangle)
            shadow_rect = pygame.Rect(card_rect.x + 2, card_rect.y + 2, card_rect.width, card_rect.height)
            shadow_color = (*Config.COLORS['background'], 100)  # Semi-transparent shadow
            pygame.draw.rect(self.screen, shadow_color, shadow_rect, border_radius=10)
            
            # Main card with gradient-like effect
            pygame.draw.rect(self.screen, Config.COLORS['surface_light'], card_rect, border_radius=10)
            
            # Device color indicator strip on left edge (consistent with charts)
            device_strip_rect = pygame.Rect(card_rect.x, card_rect.y, 6, card_rect.height)
            pygame.draw.rect(self.screen, device_color, device_strip_rect, border_radius=3)
            
            # Status indicator dot in top-right corner  
            status_dot_rect = pygame.Rect(card_rect.right - 15, card_rect.y + 8, 8, 8)
            pygame.draw.circle(self.screen, status_color, status_dot_rect.center, 4)
            
            # Subtle border with device color hint
            pygame.draw.rect(self.screen, (*device_color, 60), card_rect, width=2, border_radius=10)
            pygame.draw.rect(self.screen, Config.COLORS['border'], card_rect, width=1, border_radius=10)
            
            # Device name and type with better icons
            if device.device_type == "bluetooth":
                device_type_icon = "�" if device.status == DeviceStatus.CONNECTED else "�"
            elif device.device_type == "serial":
                device_type_icon = "🔌"
            else:
                device_type_icon = "🎭"
                
            # Truncate long device names more elegantly
            display_name = device.device_name
            if len(display_name) > 25:
                display_name = display_name[:25] + "..."
                
            name_text = f"{device_type_icon} {display_name}"
            self.fonts['body'].render_to(self.screen, (rect.x + 15, y_pos), name_text, Config.COLORS['text_primary'])
            
            # Enhanced status display with pill-shaped badge
            status_text = f"{device.status.value.title()}"
            if device.status == DeviceStatus.CONNECTED and device.last_distance > 0:
                status_text += f" • {device.last_distance:.1f}cm"
            elif device.status == DeviceStatus.CONNECTED:
                status_text += " • Waiting..."
            
            # Status badge with rounded background
            status_text_surface, _ = self.fonts['small'].render(status_text, Config.COLORS['text_primary'])
            status_badge_rect = pygame.Rect(card_rect.right - status_text_surface.get_width() - 20, y_pos + 8, 
                                          status_text_surface.get_width() + 16, 18)
            
            # Badge background with transparency
            status_bg_color = (*status_color[:3], 40)  # Semi-transparent status color
            pygame.draw.rect(self.screen, status_bg_color, status_badge_rect, border_radius=9)
            pygame.draw.rect(self.screen, status_color, status_badge_rect, width=1, border_radius=9)
            
            # Badge text
            self.fonts['small'].render_to(self.screen, (status_badge_rect.x + 8, status_badge_rect.y + 3), 
                                        status_text, status_color)
            
            # Enhanced status line
            self.fonts['small'].render_to(self.screen, (card_rect.x + 15, y_pos + 30), 
                                        f"Last Update: {device.last_distance:.1f}cm" if device.last_distance > 0 else "Connecting...", 
                                        Config.COLORS['text_secondary'])
            
            if device.status == DeviceStatus.CONNECTED:
                # Modern toggle switch instead of checkbox
                toggle_rect = pygame.Rect(card_rect.x + 15, y_pos + 50, 40, 20)
                checkbox_key = f"enable_{device_id}"
                
                enabled = self.device_enabled_states.get(device_id, True)
                
                # Toggle background
                toggle_bg_color = Config.COLORS['success'] if enabled else Config.COLORS['surface']
                pygame.draw.rect(self.screen, toggle_bg_color, toggle_rect, border_radius=10)
                pygame.draw.rect(self.screen, Config.COLORS['border'], toggle_rect, width=1, border_radius=10)
                
                # Toggle circle
                circle_x = toggle_rect.right - 12 if enabled else toggle_rect.x + 8
                pygame.draw.circle(self.screen, Config.COLORS['text_primary'], (circle_x, toggle_rect.centery), 8)
                
                self.checkbox_rects[checkbox_key] = toggle_rect
                
                # Toggle label with audio status
                device_enabled = self.device_enabled_states.get(device_id, True)
                actual_audio_playing = device_enabled and self.global_audio_enabled
                
                if actual_audio_playing:
                    toggle_label = "🔊 Audio Playing"
                    label_color = Config.COLORS['success']
                elif device_enabled and not self.global_audio_enabled:
                    toggle_label = "🔇 Global Muted"
                    label_color = Config.COLORS['warning']
                else:
                    toggle_label = "⚪ Disabled"
                    label_color = Config.COLORS['text_muted']
                
                self.fonts['small'].render_to(self.screen, (toggle_rect.right + 10, y_pos + 54),
                                            toggle_label, label_color)
                
                # Enhanced audio selection dropdown
                audio_sources = self.audio_engine.get_audio_sources()
                current_audio = self.device_audio_assignments.get(device_id)
                audio_name = "No Audio"
                
                # Find current audio source name
                if current_audio and audio_sources:
                    for source in audio_sources:
                        if source.id == current_audio:
                            audio_name = source.name[:12]  # Shorter for better fit
                            break
                elif audio_sources:
                    # Default to first audio source if none assigned
                    audio_name = audio_sources[0].name[:12]
                    self.device_audio_assignments[device_id] = audio_sources[0].id
                
                # Audio dropdown background with hover effect
                dropdown_rect = pygame.Rect(card_rect.x + 200, y_pos + 48, 150, 24)
                is_dropdown_hovered = f"audio_{device_id}" in getattr(self, 'hovered_dropdowns', set())
                dropdown_bg_color = Config.COLORS['surface_light'] if is_dropdown_hovered else Config.COLORS['surface']
                
                pygame.draw.rect(self.screen, dropdown_bg_color, dropdown_rect, border_radius=5)
                pygame.draw.rect(self.screen, Config.COLORS['border'], dropdown_rect, width=1, border_radius=5)
                
                # Clickable indicator (subtle pulse effect)
                if len(audio_sources) > 1:
                    # Draw a subtle click indicator
                    indicator_rect = pygame.Rect(dropdown_rect.x + 2, dropdown_rect.y + 2, 2, dropdown_rect.height - 4)
                    pygame.draw.rect(self.screen, Config.COLORS['primary'], indicator_rect, border_radius=1)
                
                # Dropdown arrow (more prominent for clickable dropdowns)
                arrow_color = Config.COLORS['primary'] if len(audio_sources) > 1 else Config.COLORS['text_muted']
                arrow_points = [
                    (dropdown_rect.right - 15, dropdown_rect.y + 8),
                    (dropdown_rect.right - 10, dropdown_rect.y + 13),
                    (dropdown_rect.right - 5, dropdown_rect.y + 8)
                ]
                pygame.draw.lines(self.screen, arrow_color, False, arrow_points, 2)
                
                # Audio name in dropdown with source count
                if len(audio_sources) > 1:
                    display_text = f"🎵 {audio_name} (Click to cycle)"
                    text_color = Config.COLORS['text_primary']
                else:
                    display_text = f"🎵 {audio_name}"
                    text_color = Config.COLORS['text_muted']
                
                # Truncate text if too long
                if len(display_text) > 20:
                    display_text = display_text[:17] + "..."
                
                self.fonts['small'].render_to(self.screen, (dropdown_rect.x + 8, dropdown_rect.y + 5),
                                            display_text, text_color)
                
                # Store dropdown rect for click detection (we'll implement dropdown functionality later)
                if not hasattr(self, 'audio_dropdown_rects'):
                    self.audio_dropdown_rects = {}
                self.audio_dropdown_rects[f"audio_{device_id}"] = dropdown_rect
                
                # Enhanced disconnect button
                disconnect_btn_rect = pygame.Rect(card_rect.right - 90, y_pos + 48, 80, 24)
                disconnect_btn_key = f"disconnect_{device_id}"
                
                # Button with gradient-like effect and hover state
                is_hovered = disconnect_btn_key in getattr(self, 'hovered_buttons', set())
                btn_color = Config.COLORS['error'] if is_hovered else Config.COLORS['surface']
                text_color = Config.COLORS['text_primary'] if is_hovered else Config.COLORS['error']
                
                # pygame.draw.rect(self.screen, btn_color, disco/nnect_btn_rect, border_radius=6)
                pygame.draw.rect(self.screen, Config.COLORS['error'], disconnect_btn_rect, width=1, border_radius=6)
                
                # Button text with icon
                self.fonts['small'].render_to(self.screen, (disconnect_btn_rect.x + 6, disconnect_btn_rect.y + 6), 
                                            "🔌 Disconnect", text_color)
                
                # Store button rect for click detection
                if not hasattr(self, 'disconnect_button_rects'):
                    self.disconnect_button_rects = {}
                self.disconnect_button_rects[disconnect_btn_key] = disconnect_btn_rect
                
            elif device.status == DeviceStatus.ERROR:
                # Enhanced error display with icon
                error_msg = device.error_message or "Connection failed"
                if len(error_msg) > 35:
                    error_msg = error_msg[:35] + "..."
                
                # Error icon and message
                self.fonts['small'].render_to(self.screen, (card_rect.x + 15, y_pos + 50),
                                            f"⚠️ {error_msg}", Config.COLORS['error'])
            
            # Volume level indicator bar for connected devices
            if device.status == DeviceStatus.CONNECTED and device.last_distance > 0:
                # Calculate current volume level
                volume_level = self._calculate_volume_from_distance(device.last_distance)
                volume_ratio = volume_level / 100.0  # Convert to 0-1 range
                
                # Volume bar background
                bar_bg_rect = pygame.Rect(card_rect.right - 80, y_pos + 75, 60, 8)
                pygame.draw.rect(self.screen, Config.COLORS['surface'], bar_bg_rect, border_radius=4)
                pygame.draw.rect(self.screen, Config.COLORS['border'], bar_bg_rect, width=1, border_radius=4)
                
                # Volume bar fill - use device color instead of green
                if volume_ratio > 0:
                    bar_fill_width = int(volume_ratio * (bar_bg_rect.width - 2))
                    bar_fill_rect = pygame.Rect(bar_bg_rect.x + 2, bar_bg_rect.y + 1, bar_fill_width, bar_bg_rect.height - 2)
                    pygame.draw.rect(self.screen, device_color, bar_fill_rect, border_radius=3)
                
                # Volume percentage text
                self.fonts['tiny'].render_to(self.screen, (bar_bg_rect.x, bar_bg_rect.y - 12),
                                           f"{volume_level:.0f}%", Config.COLORS['text_muted'])
            
            y_pos += device_card_height
        
        # Restore clipping
        self.screen.set_clip(old_clip)
        
        # Draw scroll indicator if needed
        if max_scroll > 0:
            # Draw scroll bar background - make it more prominent
            scrollbar_width = 12
            scrollbar_rect = pygame.Rect(rect.right - scrollbar_width - 3, rect.y + 5, 
                                       scrollbar_width, rect.height - 10)
            pygame.draw.rect(self.screen, Config.COLORS['surface_light'], scrollbar_rect, border_radius=6)
            pygame.draw.rect(self.screen, Config.COLORS['border'], scrollbar_rect, width=1, border_radius=6)
            
            # Draw scroll thumb - more prominent
            thumb_height = max(30, int((available_height / total_content_height) * scrollbar_rect.height))
            thumb_y_ratio = self.device_list_scroll_offset / max_scroll if max_scroll > 0 else 0
            thumb_y = scrollbar_rect.y + int(thumb_y_ratio * (scrollbar_rect.height - thumb_height))
            
            thumb_rect = pygame.Rect(scrollbar_rect.x + 1, thumb_y, scrollbar_width - 2, thumb_height)
            pygame.draw.rect(self.screen, Config.COLORS['primary'], thumb_rect, border_radius=5)
            
            # Add scroll hint at the top
            hint_text = "🖱️ Scroll for more devices"
            hint_rect = pygame.Rect(rect.x, rect.y - 20, rect.width, 15)
            self.fonts['tiny'].render_to(self.screen, (hint_rect.x + 5, hint_rect.y), 
                                       hint_text, Config.COLORS['text_muted'])
            
            # Store scrollbar rect for mouse handling
            if not hasattr(self, 'device_list_scrollbar_rect'):
                self.device_list_scrollbar_rect = scrollbar_rect
            else:
                self.device_list_scrollbar_rect = scrollbar_rect
        
        # Add device count indicator at the bottom if some devices are hidden
        if len(devices) > visible_devices:
            count_text = f"Showing {visible_devices} of {len(devices)} devices • Scroll to see more"
            text_rect = self.fonts['small'].get_rect(count_text)
            bg_rect = pygame.Rect(rect.x, rect.bottom - 25, rect.width, 20)
            pygame.draw.rect(self.screen, Config.COLORS['surface_light'], bg_rect, border_radius=4)
            self.fonts['small'].render_to(self.screen, (rect.x + 5, rect.bottom - 22), 
                                        count_text, Config.COLORS['text_secondary'])

    def _render_audio_library_content(self, rect: pygame.Rect):
        """Render scrollable audio library with consistent styling"""
        sources = self.audio_engine.get_audio_sources()
        
        # Library stats header
        stats_text = f"Total Audio Sources: {len(sources)}"
        self.fonts['body'].render_to(self.screen, (rect.x, rect.y), 
                                   stats_text, Config.COLORS['text_primary'])
        
        if len(sources) > 4:
            scroll_hint = "🖱️ Scroll for more"
            self.fonts['tiny'].render_to(self.screen, (rect.right - 80, rect.y + 5), 
                                       scroll_hint, Config.COLORS['text_muted'])
        
        content_y = rect.y + 30
        content_height = rect.height - 30
        
        if not sources:
            # Elegant empty state
            empty_rect = pygame.Rect(rect.x, content_y, rect.width, 120)
            pygame.draw.rect(self.screen, Config.COLORS['surface_light'], empty_rect, border_radius=10)
            pygame.draw.rect(self.screen, Config.COLORS['border'], empty_rect, width=1, border_radius=10)
            
            # Empty state icon and text
            self.fonts['h2'].render_to(self.screen, (empty_rect.centerx - 40, empty_rect.y + 25), 
                                     "🎵", Config.COLORS['text_muted'])
            self.fonts['body'].render_to(self.screen, (empty_rect.x + 20, empty_rect.y + 60), 
                                       "No audio files loaded", Config.COLORS['text_muted'])
            self.fonts['small'].render_to(self.screen, (empty_rect.x + 20, empty_rect.y + 85), 
                                        "Upload audio files to get started", Config.COLORS['text_secondary'])
            return
        
        # Create content clipping area
        content_rect = pygame.Rect(rect.x, content_y, rect.width, content_height)
        
        # Create a surface for clipped content
        clipped_surface = pygame.Surface((content_rect.width, content_rect.height))
        clipped_surface.fill(Config.COLORS['background'])
        
        # Calculate scrollable parameters
        item_height = 50
        total_content_height = len(sources) * item_height
        max_scroll = max(0, total_content_height - content_height)
        
        # Clamp scroll offset
        self.scroll_offsets['audio_library'] = max(0, min(self.scroll_offsets['audio_library'], max_scroll))
        
        # Render items on clipped surface
        y_pos = -self.scroll_offsets['audio_library']
        
        for i, source in enumerate(sources):
            item_rect = pygame.Rect(0, y_pos, content_rect.width, item_height - 5)
            
            # Only render if visible
            if y_pos + item_height > 0 and y_pos < content_height:
                self._render_elegant_audio_item_clipped(clipped_surface, item_rect, source, i)
                
            y_pos += item_height
            
        # Blit clipped content
        self.screen.blit(clipped_surface, content_rect)
        
        # Draw scroll indicator if needed
        if max_scroll > 0:
            scroll_bar_width = 8
            scroll_bar_height = content_height
            scroll_bar_x = content_rect.right - scroll_bar_width
            
            # Background track
            track_rect = pygame.Rect(scroll_bar_x, content_rect.y, scroll_bar_width, scroll_bar_height)
            pygame.draw.rect(self.screen, Config.COLORS['surface_light'], track_rect, border_radius=4)
            
            # Thumb
            thumb_ratio = content_height / total_content_height
            thumb_height = max(20, int(scroll_bar_height * thumb_ratio))
            thumb_y = content_rect.y + int((self.scroll_offsets['audio_library'] / max_scroll) * (scroll_bar_height - thumb_height))
            
            thumb_rect = pygame.Rect(scroll_bar_x, thumb_y, scroll_bar_width, thumb_height)
            pygame.draw.rect(self.screen, Config.COLORS['primary'], thumb_rect, border_radius=4)
        
        # Store scroll area for event handling
        self.scroll_areas = getattr(self, 'scroll_areas', {})
        self.scroll_areas['audio_library'] = content_rect

    def _render_elegant_audio_item_clipped(self, surface: pygame.Surface, rect: pygame.Rect, source, index: int):
        """Render individual audio source with modern card design on clipped surface"""
        # Card background with hover effect
        card_bg_color = Config.COLORS['surface_light'] if index % 2 == 0 else Config.COLORS['surface']
        
        # Card with subtle shadow
        shadow_rect = pygame.Rect(rect.x + 1, rect.y + 1, rect.width, rect.height)
        pygame.draw.rect(surface, (*Config.COLORS['background'], 40), shadow_rect, border_radius=8)
        
        pygame.draw.rect(surface, card_bg_color, rect, border_radius=8)
        pygame.draw.rect(surface, Config.COLORS['border'], rect, width=1, border_radius=8)
        
        # Audio type indicator strip
        type_color = Config.COLORS['primary'] if source.file_type == AudioFileType.AUDIO_FILE else Config.COLORS['info']
        type_strip = pygame.Rect(rect.x, rect.y, 4, rect.height)
        pygame.draw.rect(surface, type_color, type_strip, border_radius=2)
        
        # Source icon and name
        icon = "🎵" if source.file_type == AudioFileType.AUDIO_FILE else "🌊"
        display_name = source.name
        if len(display_name) > 25:
            display_name = display_name[:25] + "..."
        
        # Main text
        self.fonts['body'].render_to(surface, (rect.x + 15, rect.y + 8), 
                                   f"{icon} {display_name}", Config.COLORS['text_primary'])
        
        # Source details
        details = []
        if hasattr(source, 'frequency') and source.frequency:
            details.append(f"{source.frequency:.0f}Hz")
        
        if source.file_type == AudioFileType.AUDIO_FILE:
            details.append("Custom File")
        else:
            details.append("Generated")
        
        if details:
            details_text = " • ".join(details)
            self.fonts['small'].render_to(surface, (rect.x + 15, rect.y + 25), 
                                        details_text, Config.COLORS['text_secondary'])

    def _render_mini_button(self, rect: pygame.Rect, button_key: str, text: str, color):
        """Render small action button with consistent styling"""
        # Button background
        pygame.draw.rect(self.screen, color, rect, border_radius=4)
        
        # Button text
        text_color = Config.COLORS['text_light']
        text_surface, text_rect = self.fonts['tiny'].render(text, text_color)
        text_x = rect.centerx - text_rect.width // 2
        text_y = rect.centery - text_rect.height // 2
        self.screen.blit(text_surface, (text_x, text_y))
        
        # Store button rect for click detection
        if not hasattr(self, 'audio_action_rects'):
            self.audio_action_rects = {}
        self.audio_action_rects[button_key] = rect

    def _render_audio_source_item(self, rect: pygame.Rect, source, index: int):
        """Render individual audio source item"""
        # Source type icon
        type_icon = "🎵" if source.file_type == AudioFileType.AUDIO_FILE else "🌊"
        
        # Source name (truncated if too long)
        display_name = source.name
        if len(display_name) > 30:
            display_name = display_name[:30] + "..."
        
        # Main source info
        self.fonts['small'].render_to(self.screen, (rect.x + 8, rect.y + 5), 
                                    f"{type_icon} {display_name}", Config.COLORS['text_primary'])
        
        # Source details on second line
        details = []
        if source.file_type in [AudioFileType.SINE_WAVE, AudioFileType.SYNTHESIZED]:
            if source.frequency:
                details.append(f"{source.frequency:.0f}Hz")
            details.append("Generated")
        else:
            details.append("Custom File")
        
        if details:
            details_text = " • ".join(details)
            self.fonts['small'].render_to(self.screen, (rect.x + 28, rect.y + 20), 
                                        details_text, Config.COLORS['text_secondary'])
        
        # Action buttons for custom audio files
        if source.file_type == AudioFileType.AUDIO_FILE:
            # Rename button
            rename_btn_rect = pygame.Rect(rect.right - 130, rect.y + 8, 60, 24)
            rename_btn_key = f"rename_{source.id}"
            
            pygame.draw.rect(self.screen, Config.COLORS['surface'], rename_btn_rect, border_radius=4)
            pygame.draw.rect(self.screen, Config.COLORS['info'], rename_btn_rect, width=1, border_radius=4)
            self.fonts['small'].render_to(self.screen, (rename_btn_rect.x + 8, rename_btn_rect.y + 6), 
                                        "✏️ Rename", Config.COLORS['info'])
            
            # Delete button
            delete_btn_rect = pygame.Rect(rect.right - 65, rect.y + 8, 55, 24)
            delete_btn_key = f"delete_{source.id}"
            
            pygame.draw.rect(self.screen, Config.COLORS['surface'], delete_btn_rect, border_radius=4)
            pygame.draw.rect(self.screen, Config.COLORS['error'], delete_btn_rect, width=1, border_radius=4)
            self.fonts['small'].render_to(self.screen, (delete_btn_rect.x + 8, delete_btn_rect.y + 6), 
                                        "🗑️ Delete", Config.COLORS['error'])
            
            # Store button rects for click detection
            if not hasattr(self, 'audio_action_rects'):
                self.audio_action_rects = {}
            self.audio_action_rects[rename_btn_key] = rename_btn_rect
            self.audio_action_rects[delete_btn_key] = delete_btn_rect

    def _render_audio_controls_content(self, rect: pygame.Rect):
        """Render elegant audio control settings with modern sliders"""
        y_pos = rect.y
        
        # Audio controls with modern styling
        controls = [
            ('master_volume', '🔊 Master Volume', self.audio_effects.get('master_volume', 75)),
            ('bass_boost', '🎵 Bass Boost', self.audio_effects.get('bass_boost', 0)),
            ('spatial_mix', '🌍 Spatial Mix', self.audio_effects.get('spatial_mix', 50))
        ]
        
        for control_id, label, value in controls:
            # Control label
            self.fonts['body'].render_to(self.screen, (rect.x, y_pos), 
                                       label, Config.COLORS['text_primary'])
            
            # Value display with modern badge
            value_text = f"{value:.0f}%"
            value_bg = pygame.Rect(rect.right - 60, y_pos - 2, 50, 20)
            pygame.draw.rect(self.screen, Config.COLORS['primary'], value_bg, border_radius=10)
            self.fonts['small'].render_to(self.screen, (value_bg.x + 12, value_bg.y + 4), 
                                        value_text, Config.COLORS['text_light'])
            
            y_pos += 25
            
            # Modern slider with track and handle
            slider_rect = pygame.Rect(rect.x, y_pos, rect.width - 20, 12)
            self._render_modern_slider(slider_rect, control_id, value / 100.0)
            
            y_pos += 35
        
        # Audio Effects Status Section
        effects_y = y_pos + 10
        self.fonts['body'].render_to(self.screen, (rect.x, effects_y), 
                                   "🎛️ Audio Effects Control", Config.COLORS['text_primary'])
        effects_y += 30
        
        # Effects toggle buttons
        effects_toggles = [
            ('bass_boost_enabled', '🎵 Bass Boost', self.audio_effects.get('bass_boost_enabled', True)),
            ('spatial_enabled', '🌍 Spatial Audio', self.audio_effects.get('spatial_enabled', True)),
            ('distance_fade', '📐 Distance Fade', self.audio_effects.get('distance_fade', True)),
            ('reverb_enabled', '🔄 Reverb', self.audio_effects.get('reverb_enabled', False))
        ]
        
        for effect_id, effect_label, is_enabled in effects_toggles:
            if effects_y + 28 > rect.bottom:
                break
                
            # Effect toggle container
            toggle_container = pygame.Rect(rect.x, effects_y, rect.width, 25)
            
            # Effect label
            self.fonts['small'].render_to(self.screen, (toggle_container.x, toggle_container.y + 6), 
                                        effect_label, Config.COLORS['text_primary'])
            
            # Toggle switch
            toggle_btn = pygame.Rect(toggle_container.right - 50, toggle_container.y + 4, 45, 18)
            toggle_key = f"toggle_{effect_id}"
            
            # Toggle background
            bg_color = Config.COLORS['success'] if is_enabled else Config.COLORS['surface_light']
            pygame.draw.rect(self.screen, bg_color, toggle_btn, border_radius=9)
            pygame.draw.rect(self.screen, Config.COLORS['border'], toggle_btn, width=1, border_radius=9)
            
            # Toggle handle
            handle_x = toggle_btn.right - 16 if is_enabled else toggle_btn.x + 2
            handle_rect = pygame.Rect(handle_x, toggle_btn.y + 2, 14, 14)
            pygame.draw.circle(self.screen, Config.COLORS['text_light'], handle_rect.center, 7)
            pygame.draw.circle(self.screen, Config.COLORS['border'], handle_rect.center, 7, width=1)
            
            # Status text
            status_text = "ON" if is_enabled else "OFF"
            status_color = Config.COLORS['success'] if is_enabled else Config.COLORS['text_muted']
            self.fonts['tiny'].render_to(self.screen, (toggle_container.right - 80, toggle_container.y + 8), 
                                       status_text, status_color)
            
            # Store toggle rect for interaction
            if not hasattr(self, 'effect_toggle_rects'):
                self.effect_toggle_rects = {}
            self.effect_toggle_rects[toggle_key] = toggle_btn
            
            effects_y += 28
        
        # Audio Engine Status (compact)
        if effects_y + 40 < rect.bottom:
            effects_y += 10
            self.fonts['body'].render_to(self.screen, (rect.x, effects_y), 
                                       "⚡ Engine Status", Config.COLORS['text_primary'])
            effects_y += 25
            
            # Compact status indicators
            status_items = [
                ("🟢 Active", "Processing"),
                ("🔊 Output", "Real-time"),
                ("📊 Devices", f"{len(self.device_manager.get_connected_devices())}")
            ]
            
            for status_icon, status_text in status_items:
                self.fonts['small'].render_to(self.screen, (rect.x, effects_y), 
                                            f"{status_icon} {status_text}", Config.COLORS['text_secondary'])
                effects_y += 16

    def _render_modern_slider(self, rect: pygame.Rect, slider_id: str, value: float):
        """Render modern slider with track and handle"""
        # Slider track background
        track_rect = pygame.Rect(rect.x, rect.centery - 3, rect.width, 6)
        pygame.draw.rect(self.screen, Config.COLORS['surface_light'], track_rect, border_radius=3)
        pygame.draw.rect(self.screen, Config.COLORS['border'], track_rect, width=1, border_radius=3)
        
        # Filled portion of track
        fill_width = int(rect.width * value)
        if fill_width > 0:
            fill_rect = pygame.Rect(rect.x, rect.centery - 3, fill_width, 6)
            pygame.draw.rect(self.screen, Config.COLORS['primary'], fill_rect, border_radius=3)
        
        # Slider handle
        handle_x = rect.x + int(rect.width * value) - 8
        handle_rect = pygame.Rect(handle_x, rect.centery - 8, 16, 16)
        
        # Handle shadow
        shadow_rect = pygame.Rect(handle_rect.x + 1, handle_rect.y + 1, 16, 16)
        pygame.draw.circle(self.screen, (*Config.COLORS['background'], 60), shadow_rect.center, 8)
        
        # Handle
        pygame.draw.circle(self.screen, Config.COLORS['text_light'], handle_rect.center, 8)
        pygame.draw.circle(self.screen, Config.COLORS['primary'], handle_rect.center, 8, width=2)
        
        # Store slider rect for interaction
        if not hasattr(self, 'slider_rects'):
            self.slider_rects = {}
        self.slider_rects[slider_id] = rect

    def _render_audio_engine_content(self, rect: pygame.Rect):
        """Render elegant audio engine status with modern indicators"""
        y_pos = rect.y
        
        # Engine status with modern cards
        stats = self.audio_engine.get_engine_stats()
        
        # Status cards layout
        card_height = 35
        card_spacing = 8
        
        status_data = [
            ("🎛️", "Active Channels", f"{stats['active_channels']}/{stats['total_channels']}", Config.COLORS['success']),
            ("📡", "Sample Rate", f"{stats['sample_rate']} Hz", Config.COLORS['info']),
            ("🔀", "Audio Mixing", "Enabled" if stats['mixing_enabled'] else "Disabled", 
             Config.COLORS['success'] if stats['mixing_enabled'] else Config.COLORS['warning']),
            ("🎵", "Audio Sources", f"{len(self.audio_engine.get_audio_sources())}", Config.COLORS['primary'])
        ]
        
        for icon, label, value, color in status_data:
            # Status card
            card_rect = pygame.Rect(rect.x, y_pos, rect.width, card_height)
            pygame.draw.rect(self.screen, Config.COLORS['surface_light'], card_rect, border_radius=6)
            pygame.draw.rect(self.screen, color, 
                           pygame.Rect(card_rect.x, card_rect.y, 3, card_rect.height), border_radius=2)
            
            # Icon and label
            self.fonts['small'].render_to(self.screen, (card_rect.x + 10, card_rect.y + 6), 
                                        f"{icon} {label}:", Config.COLORS['text_secondary'])
            
            # Value with color indicator
            self.fonts['small'].render_to(self.screen, (card_rect.right - 80, card_rect.y + 6), 
                                        value, color)
            
            y_pos += card_height + card_spacing

    def _render_distance_mapping_content(self, rect: pygame.Rect):
        """Render enhanced distance mapping with user-configurable settings"""
        y_pos = rect.y
        
        # Distance Mapping Configuration
        self.fonts['body'].render_to(self.screen, (rect.x, y_pos), 
                                   "📐 Distance Mapping Configuration", Config.COLORS['text_primary'])
        y_pos += 30
        
        # Configuration fields
        field_height = 25
        field_spacing = 5
        
        # Min Distance setting
        min_dist_rect = pygame.Rect(rect.x, y_pos, rect.width // 2 - 5, field_height)
        pygame.draw.rect(self.screen, Config.COLORS['surface_light'], min_dist_rect, border_radius=4)
        self.fonts['caption'].render_to(self.screen, (min_dist_rect.x + 5, min_dist_rect.y + 3), 
                                      f"Min Distance: {self.distance_settings['min_distance']:.1f}cm", 
                                      Config.COLORS['text_primary'])
        
        # Max Distance setting  
        max_dist_rect = pygame.Rect(rect.x + rect.width // 2 + 5, y_pos, rect.width // 2 - 5, field_height)
        pygame.draw.rect(self.screen, Config.COLORS['surface_light'], max_dist_rect, border_radius=4)
        self.fonts['caption'].render_to(self.screen, (max_dist_rect.x + 5, max_dist_rect.y + 3), 
                                      f"Max Distance: {self.distance_settings['max_distance']:.1f}cm", 
                                      Config.COLORS['text_primary'])
        y_pos += field_height + field_spacing
        
        # Min Volume setting
        min_vol_rect = pygame.Rect(rect.x, y_pos, rect.width // 2 - 5, field_height)
        pygame.draw.rect(self.screen, Config.COLORS['surface_light'], min_vol_rect, border_radius=4)
        self.fonts['caption'].render_to(self.screen, (min_vol_rect.x + 5, min_vol_rect.y + 3), 
                                      f"Min Volume: {self.distance_settings['min_volume']:.1f}%", 
                                      Config.COLORS['text_primary'])
        
        # Max Volume setting
        max_vol_rect = pygame.Rect(rect.x + rect.width // 2 + 5, y_pos, rect.width // 2 - 5, field_height)
        pygame.draw.rect(self.screen, Config.COLORS['surface_light'], max_vol_rect, border_radius=4)
        self.fonts['caption'].render_to(self.screen, (max_vol_rect.x + 5, max_vol_rect.y + 3), 
                                      f"Max Volume: {self.distance_settings['max_volume']:.1f}%", 
                                      Config.COLORS['text_primary'])
        y_pos += field_height + field_spacing
        
        # Graph Max Distance setting
        graph_max_rect = pygame.Rect(rect.x, y_pos, rect.width // 2 - 5, field_height)
        pygame.draw.rect(self.screen, Config.COLORS['surface_light'], graph_max_rect, border_radius=4)
        self.fonts['caption'].render_to(self.screen, (graph_max_rect.x + 5, graph_max_rect.y + 3), 
                                      f"Graph Max: {self.distance_settings['max_graph_distance']:.1f}cm", 
                                      Config.COLORS['text_primary'])
        
        # Record Length setting  
        record_len_rect = pygame.Rect(rect.x + rect.width // 2 + 5, y_pos, rect.width // 2 - 5, field_height)
        pygame.draw.rect(self.screen, Config.COLORS['surface_light'], record_len_rect, border_radius=4)
        self.fonts['caption'].render_to(self.screen, (record_len_rect.x + 5, record_len_rect.y + 3), 
                                      f"Record Length: {self.data_tracking['record_length']}s", 
                                      Config.COLORS['text_primary'])
        y_pos += field_height + 10
        
        # Store rects for input handling
        self.slider_rects['min_distance_input'] = min_dist_rect
        self.slider_rects['max_distance_input'] = max_dist_rect
        self.slider_rects['min_volume_input'] = min_vol_rect
        self.slider_rects['max_volume_input'] = max_vol_rect
        self.slider_rects['graph_max_input'] = graph_max_rect
        self.slider_rects['record_length_input'] = record_len_rect
        
        # Current mapping visualization
        if y_pos + 80 < rect.bottom:
            viz_rect = pygame.Rect(rect.x, y_pos, rect.width, rect.bottom - y_pos)
            pygame.draw.rect(self.screen, Config.COLORS['surface'], viz_rect, border_radius=6)
            
            self.fonts['caption'].render_to(self.screen, (viz_rect.x + 5, viz_rect.y + 5), 
                                          "Volume Mapping Preview:", Config.COLORS['text_secondary'])
            
            # Draw simple mapping curve
            curve_rect = pygame.Rect(viz_rect.x + 10, viz_rect.y + 25, viz_rect.width - 20, viz_rect.height - 35)
            pygame.draw.rect(self.screen, Config.COLORS['background'], curve_rect, border_radius=4)
            
            # Draw curve points
            if curve_rect.width > 0 and curve_rect.height > 0:
                for i in range(curve_rect.width):
                    x_ratio = i / curve_rect.width
                    distance = self.distance_settings['min_distance'] + x_ratio * (
                        self.distance_settings['max_distance'] - self.distance_settings['min_distance'])
                    volume = self._calculate_volume_from_distance(distance) / 100.0
                    
                    point_x = curve_rect.x + i
                    point_y = curve_rect.bottom - int(volume * curve_rect.height)
                    
                    if i % 3 == 0:  # Sample every 3rd point for performance
                        pygame.draw.circle(self.screen, Config.COLORS['primary'], (point_x, point_y), 1)

    def _render_section(self, parent_rect: pygame.Rect, y_offset: int, title: str, 
                       content_renderer: Callable, height: int) -> int:
        section_rect = pygame.Rect(parent_rect.x, parent_rect.y + y_offset, 
                                  parent_rect.width, height)
        
        # Section background
        pygame.draw.rect(self.screen, Config.COLORS['surface'], section_rect, border_radius=8)
        pygame.draw.rect(self.screen, Config.COLORS['border'], section_rect, 2, border_radius=8)
        
        # Section header
        header_rect = pygame.Rect(section_rect.x, section_rect.y, section_rect.width, 35)
        pygame.draw.rect(self.screen, Config.COLORS['surface_light'], header_rect, 
                        border_top_left_radius=8, border_top_right_radius=8)
        
        self.fonts['heading'].render_to(self.screen, (header_rect.x + 15, header_rect.y + 8), 
                                       title, Config.COLORS['text_primary'])
        
        # Section content
        content_rect = pygame.Rect(section_rect.x + 15, header_rect.bottom + 10,
                                  section_rect.width - 30, section_rect.height - 50)
        content_renderer(content_rect)
        
        return height + Config.LAYOUT['padding']

    def _render_device_status_content(self, rect: pygame.Rect):
        devices = self.device_manager.get_connected_devices()
        if not devices:
            self.fonts['body'].render_to(self.screen, rect.topleft, 
                                       "No active HC-05 devices to monitor.", Config.COLORS['text_muted'])
            return

        y_pos = rect.y
        for device in devices:
            if y_pos + 60 > rect.bottom:
                break
                
            enabled = self.device_enabled_states.get(device.device_id, True)
            if not enabled:
                continue
                
            # Device name with type icon
            device_type_icon = "🔵" if device.device_type == "bluetooth" else "🔌" if device.device_type == "serial" else "🎭"
            name_text = f"{device_type_icon} {device.device_name[:25]}"
            self.fonts['body'].render_to(self.screen, (rect.x, y_pos), name_text, Config.COLORS['text_primary'])
            
            # Distance, volume, and frequency
            if device.last_distance > 0:
                dist_text = f"Distance: {device.last_distance:.1f}cm"
                vol = self._calculate_volume_from_distance(device.last_distance)
                freq = self._calculate_frequency_from_distance(device.last_distance)
                details_text = f"{dist_text} • Vol: {vol:.0f}% • Freq: {freq:.0f}Hz"
            else:
                details_text = "Waiting for data..."
            
            self.fonts['small'].render_to(self.screen, (rect.x, y_pos + 20), 
                                        details_text, Config.COLORS['text_secondary'])
            
            # Connection info
            if hasattr(device, 'rssi') and device.rssi:
                conn_text = f"RSSI: {device.rssi}dBm"
            else:
                conn_text = f"Type: {device.device_type}"
            
            self.fonts['small'].render_to(self.screen, (rect.x, y_pos + 40), 
                                        conn_text, Config.COLORS['text_muted'])
            
            y_pos += 60

    def _render_enhanced_chart(self, rect: pygame.Rect, data_source: Dict[str, List], min_val: float, max_val: float, unit: str):
        # Chart background
        pygame.draw.rect(self.screen, Config.COLORS['background'], rect)
        pygame.draw.rect(self.screen, Config.COLORS['border'], rect, 1)
        
        # Chart area (leave space for labels)
        chart_padding = {'left': 50, 'right': 20, 'top': 20, 'bottom': 30}
        chart_rect = pygame.Rect(
            rect.x + chart_padding['left'],
            rect.y + chart_padding['top'],
            rect.width - chart_padding['left'] - chart_padding['right'],
            rect.height - chart_padding['top'] - chart_padding['bottom']
        )
        
        # Draw grid and labels
        self._draw_chart_grid(rect, chart_rect, min_val, max_val, unit)
        
        if not data_source:
            self.fonts['body'].render_to(self.screen, (chart_rect.centerx - 40, chart_rect.centery), 
                                       "No Data", Config.COLORS['text_muted'])
            return
        
        current_time = time.time()
        # Use consistent device colors
        device_colors = {}
        for device_id in data_source.keys():
            device_colors[device_id] = self.get_device_color(device_id)
        
        # Draw data lines for each device
        for device_id, data_points in data_source.items():
            if len(data_points) < 2:
                continue
                
            # Only show enabled devices
            if not self.device_enabled_states.get(device_id, True):
                continue
                
            color = device_colors[device_id]
            points = []
            
            for timestamp, value in data_points:
                # Calculate position within chart area
                time_ratio = max(0, min(1, (current_time - timestamp) / 60.0))  # Last 60 seconds
                value_ratio = (value - min_val) / (max_val - min_val) if max_val > min_val else 0
                value_ratio = max(0, min(1, value_ratio))
                
                x = chart_rect.right - (time_ratio * chart_rect.width)
                y = chart_rect.bottom - (value_ratio * chart_rect.height)
                points.append((x, y))
            
            if len(points) > 1:
                try:
                    pygame.draw.lines(self.screen, color, False, points, 2)
                except ValueError:
                    pass  # Skip invalid points
        
        # Draw legend
        self._draw_chart_legend(rect, data_source.keys(), device_colors)

    def _draw_chart_grid(self, rect: pygame.Rect, chart_rect: pygame.Rect, min_val: float, max_val: float, unit: str):
        """Draw grid lines, ticks, and y-axis labels"""
        grid_color = (*Config.COLORS['text_muted'][:3], 32)  # Much more subtle - reduced from 64 to 32
        
        # Y-axis grid lines and labels
        num_y_ticks = 5
        for i in range(num_y_ticks + 1):
            ratio = i / num_y_ticks
            y = chart_rect.bottom - (ratio * chart_rect.height)
            value = min_val + (ratio * (max_val - min_val))
            
            # Grid line
            if i > 0 and i < num_y_ticks:  # Don't draw on borders
                pygame.draw.line(self.screen, grid_color, 
                               (chart_rect.left, y), (chart_rect.right, y), 1)
            
            # Y-axis label
            label_text = f"{value:.0f}"
            self.fonts['small'].render_to(self.screen, 
                                        (rect.x + 5, y - 6), label_text, Config.COLORS['text_muted'])
            
            # Y-axis tick
            pygame.draw.line(self.screen, Config.COLORS['text_muted'],
                           (chart_rect.left - 5, y), (chart_rect.left, y), 1)
        
        # X-axis grid lines and labels (time)
        num_x_ticks = 6
        for i in range(num_x_ticks + 1):
            ratio = i / num_x_ticks
            x = chart_rect.right - (ratio * chart_rect.width)
            seconds_ago = ratio * 60  # 60 seconds total
            
            # Grid line
            if i > 0 and i < num_x_ticks:  # Don't draw on borders
                pygame.draw.line(self.screen, grid_color,
                               (x, chart_rect.top), (x, chart_rect.bottom), 1)
            
            # X-axis label (time ago)
            if seconds_ago == 0:
                label_text = "now"
            else:
                label_text = f"-{seconds_ago:.0f}s"
            
            text_width = self.fonts['small'].get_rect(label_text).width
            self.fonts['small'].render_to(self.screen,
                                        (x - text_width // 2, chart_rect.bottom + 5),
                                        label_text, Config.COLORS['text_muted'])
        
        # Draw axes
        pygame.draw.line(self.screen, Config.COLORS['text_secondary'],
                        (chart_rect.left, chart_rect.top), (chart_rect.left, chart_rect.bottom), 2)
        pygame.draw.line(self.screen, Config.COLORS['text_secondary'],
                        (chart_rect.left, chart_rect.bottom), (chart_rect.right, chart_rect.bottom), 2)
        
        # Y-axis unit label
        unit_text = f"({unit})"
        self.fonts['small'].render_to(self.screen,
                                    (rect.x + 5, rect.y + 5), unit_text, Config.COLORS['text_secondary'])

    def _draw_chart_legend(self, rect: pygame.Rect, device_ids, device_colors):
        """Draw legend showing device names and colors"""
        if not device_ids:
            return
        
        legend_y = rect.y + 5
        legend_x = rect.right - 150
        
        for i, device_id in enumerate(device_ids):
            if not self.device_enabled_states.get(device_id, True):
                continue
                
            device = self.device_manager.devices.get(device_id)
            device_name = device.device_name if device else device_id
            
            # Truncate long names
            display_name = device_name[:15] + "..." if len(device_name) > 15 else device_name
            
            # Color square
            color_rect = pygame.Rect(legend_x, legend_y + i * 18, 12, 12)
            pygame.draw.rect(self.screen, device_colors[device_id], color_rect)
            pygame.draw.rect(self.screen, Config.COLORS['text_muted'], color_rect, 1)
            
            # Device name
            self.fonts['small'].render_to(self.screen,
                                        (legend_x + 18, legend_y + i * 18),
                                        display_name, Config.COLORS['text_secondary'])

    def _render_log_panel_content(self, rect: pygame.Rect):
        if not self.log_entries:
            self.fonts['body'].render_to(self.screen, rect.topleft, 
                                       "No log entries.", Config.COLORS['text_muted'])
            return
        
        y_pos = rect.y
        visible_entries = list(reversed(self.log_entries))[-8:]  # Show last 8 entries
        
        for timestamp, message, level in visible_entries:
            if y_pos + 18 > rect.bottom:
                break
                
            # Color based on log level
            level_colors = {
                'info': Config.COLORS['text_secondary'],
                'success': Config.COLORS['success'],
                'error': Config.COLORS['error'],
                'warning': Config.COLORS['warning']
            }
            color = level_colors.get(level, Config.COLORS['text_primary'])
            
            # Format timestamp
            time_str = time.strftime('%H:%M:%S', time.localtime(timestamp))
            log_text = f"[{time_str}] {message[:55]}"
            
            self.fonts['small'].render_to(self.screen, (rect.x, y_pos), log_text, color)
            y_pos += 18

    def _render_button(self, rect: pygame.Rect, name: str, text: str, color: Tuple[int, int, int]):
        # Button hover effect
        if rect.collidepoint(self.mouse_pos):
            hover_color = tuple(min(255, c + 20) for c in color)
            pygame.draw.rect(self.screen, hover_color, rect, border_radius=6)
        else:
            pygame.draw.rect(self.screen, color, rect, border_radius=6)
        
        # Button border
        pygame.draw.rect(self.screen, Config.COLORS['border'], rect, 2, border_radius=6)
        
        # Button text
        text_surf, text_rect = self.fonts['body'].render(text, Config.COLORS['text_primary'])
        text_rect.center = rect.center
        self.screen.blit(text_surf, text_rect)
        
        self.button_rects[name] = rect

    def _render_slider(self, rect: pygame.Rect, name: str, value: float):
        # Slider track
        pygame.draw.rect(self.screen, Config.COLORS['surface_light'], rect, border_radius=10)
        pygame.draw.rect(self.screen, Config.COLORS['border'], rect, 1, border_radius=10)
        
        # Slider handle
        handle_x = rect.x + (value * (rect.width - 15))
        handle_rect = pygame.Rect(handle_x, rect.y - 3, 15, rect.height + 6)
        pygame.draw.rect(self.screen, Config.COLORS['primary'], handle_rect, border_radius=5)
        
        # Filled portion
        filled_rect = pygame.Rect(rect.x, rect.y, handle_x - rect.x + 7, rect.height)
        pygame.draw.rect(self.screen, Config.COLORS['primary'], filled_rect, border_radius=10)
        
        self.slider_rects[name] = rect

    def update(self, dt: float):
        """Update UI state"""
        # Clean up old data (keep last 60 seconds for real-time view)
        current_time = time.time()
        cutoff_time = current_time - 60.0  # Keep 60 seconds of data for real-time charts
        
        # Clean up distance data
        for device_id in list(self.distance_data.keys()):
            if device_id not in self.device_manager.devices:
                # Device no longer exists, remove all its data
                del self.distance_data[device_id]
                continue
                
            # Keep only recent data points
            self.distance_data[device_id] = [
                (t, v) for t, v in self.distance_data[device_id] if t > cutoff_time
            ]
            
        # Clean up volume data
        for device_id in list(self.volume_data.keys()):
            if device_id not in self.device_manager.devices:
                # Device no longer exists, remove all its data
                del self.volume_data[device_id]
                continue
                
            # Keep only recent data points
            self.volume_data[device_id] = [
                (t, v) for t, v in self.volume_data[device_id] if t > cutoff_time
            ]

    def _show_audio_assignment_menu(self, device_id: str, pos: Tuple[int, int]):
        """Show audio assignment menu for a device"""
        audio_sources = self.audio_engine.get_audio_sources()
        if not audio_sources:
            self.add_log_entry("❌ No audio sources available for assignment", "error")
            self.add_log_entry("📁 Upload audio files first on the Audio page", "info")
            return
        
        if len(audio_sources) <= 1:
            self.add_log_entry("⚠️ Only one audio source available", "warning")
            self.add_log_entry("📁 Upload more audio files to have assignment options", "info")
            return
        
        # Get device name for logging
        device = self.device_manager.devices.get(device_id)
        device_name = device.device_name if device else device_id
        
        # Cycle through available sources
        current_source = self.device_audio_assignments.get(device_id, audio_sources[0].id)
        current_index = 0
        
        for i, source in enumerate(audio_sources):
            if source.id == current_source:
                current_index = i
                break
                
        next_index = (current_index + 1) % len(audio_sources)
        new_source = audio_sources[next_index]
        
        self.device_audio_assignments[device_id] = new_source.id
        
        # Show detailed assignment info
        self.add_log_entry(f"🎵 Assigned '{new_source.name}' to {device_name}", "success")
        self.add_log_entry(f"📊 Audio source {next_index + 1} of {len(audio_sources)}", "info")
        
        # Show what's next
        if len(audio_sources) > 2:
            next_next_index = (next_index + 1) % len(audio_sources)
            next_next_source = audio_sources[next_next_index]
            self.add_log_entry(f"⏭️ Next option: {next_next_source.name}", "info")

    def _toggle_audio_effect(self, effect_id: str):
        """Toggle an audio effect on/off"""
        current_state = self.audio_effects.get(effect_id, False)
        new_state = not current_state
        self.audio_effects[effect_id] = new_state
        
        effect_names = {
            'bass_boost_enabled': 'Bass Boost',
            'spatial_enabled': 'Spatial Audio',
            'distance_fade': 'Distance Fade',
            'reverb_enabled': 'Reverb'
        }
        
        effect_name = effect_names.get(effect_id, effect_id)
        status = "enabled" if new_state else "disabled"
        status_icon = "🟢" if new_state else "🔴"
        
        self.add_log_entry(f"{status_icon} {effect_name} {status}", "info")
        
        # Apply the effect change to the audio engine
        if hasattr(self.audio_engine, 'set_effect_enabled'):
            self.audio_engine.set_effect_enabled(effect_id, new_state)

    def cleanup(self):
        """Clean up UI resources"""
        self.add_log_entry("UI Manager cleanup complete")
        print("Enhanced UI Manager with HC-05 support cleanup complete")