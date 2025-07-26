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
from .audio_engine import SpatialAudioEngine, AudioSource
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
        self.audio_effects = {'master_volume': 75.0}
        self.distance_settings = {
            'min_distance': 5.0, 'max_distance': 200.0, 'min_volume': 5.0, 
            'max_volume': 100.0, 'decay_type': 'exponential'
        }
        
        # Device management
        self.device_enabled_states: Dict[str, bool] = {}
        self.device_audio_assignments: Dict[str, str] = {}
        
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
        self.device_enabled_states[device_id] = True
        self.device_audio_assignments[device_id] = "sine_440"  # Default audio source
        
        # Special handling for HC-05 devices
        if "hc05" in device_id.lower() or "sensornode" in device_name.lower():
            self.add_log_entry(f"HC-05 SensorNode connected: {device_name}", "success")
        else:
            self.add_log_entry(f"Device connected: {device_name}", "success")

    def _on_device_disconnected(self, device_id: str):
        self.device_enabled_states.pop(device_id, None)
        self.device_audio_assignments.pop(device_id, None)
        self.distance_data.pop(device_id, None)
        self.volume_data.pop(device_id, None)
        self.add_log_entry(f"Device disconnected: {device_id}", "info")

    def _on_distance_update(self, device_id: str, distance: float):
        self.update_device_distance(device_id, distance)
        
        # Synthesize audio if device is enabled
        if self.device_enabled_states.get(device_id, False):
            volume = self._calculate_volume_from_distance(distance)
            frequency = self._calculate_frequency_from_distance(distance)
            audio_source = self.device_audio_assignments.get(device_id, "sine_440")
            
            self.audio_engine.synthesize_audio(
                device_id=device_id,
                frequency=frequency,
                volume=volume / 100.0,  # Convert percentage to 0-1
                audio_file=audio_source,
                duration=0.1
            )

    def add_log_entry(self, message: str, level: str = "info"):
        self.log_entries.append((time.time(), message, level))
        if len(self.log_entries) > self.max_log_entries:
            self.log_entries.pop(0)

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEMOTION:
            self.mouse_pos = event.pos
            self._handle_slider_drag(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if time.time() - self.last_click_time > 0.2:
                self._handle_click(event.pos)
                self.last_click_time = time.time()
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging_slider = None

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

        # Test audio button
        if 'test_audio' in self.button_rects and self.button_rects['test_audio'].collidepoint(pos):
            self.audio_engine.generate_test_tone(440.0, 0.5, 1.0)
            self.add_log_entry("Test tone generated", "info")
            return

        # Bluetooth status button
        if 'bluetooth_status' in self.button_rects and self.button_rects['bluetooth_status'].collidepoint(pos):
            self._show_bluetooth_status()
            return

        self._handle_common_clicks(pos)

    def _handle_devices_click(self, pos: Tuple[int, int]):
        self._handle_common_clicks(pos)

    def _handle_audio_click(self, pos: Tuple[int, int]):
        # Audio-specific controls
        for slider_name, slider_rect in self.slider_rects.items():
            if slider_rect.collidepoint(pos):
                self.dragging_slider = slider_name
                self._update_slider_value(slider_name, pos, slider_rect)
                return

        self._handle_common_clicks(pos)

    def _handle_common_clicks(self, pos: Tuple[int, int]):
        # Device enable/disable checkboxes
        for device_id in list(self.device_enabled_states.keys()):
            checkbox_key = f"enable_{device_id}"
            if checkbox_key in self.checkbox_rects and self.checkbox_rects[checkbox_key].collidepoint(pos):
                self.device_enabled_states[device_id] = not self.device_enabled_states[device_id]
                status = "enabled" if self.device_enabled_states[device_id] else "disabled"
                self.add_log_entry(f"Device {device_id} {status}")
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

    def _show_bluetooth_status(self):
        """Show detailed Bluetooth status information"""
        status = self.device_manager.get_bluetooth_status()
        
        if status['available']:
            self.add_log_entry(f"Bluetooth Status: Available ({status['library']})", "success")
            self.add_log_entry(f"Modern support: {status['modern_support']}", "info")
            self.add_log_entry(f"Async support: {status['async_support']}", "info")
        else:
            self.add_log_entry("Bluetooth Status: Not Available", "error")
            self.add_log_entry("Install with: pip install bleak", "info")

    def _cycle_audio_assignment(self, device_id: str):
        audio_sources = self.audio_engine.get_audio_sources()
        if not audio_sources:
            return
            
        current_source = self.device_audio_assignments.get(device_id, audio_sources[0].id)
        current_index = 0
        
        for i, source in enumerate(audio_sources):
            if source.id == current_source:
                current_index = i
                break
                
        next_index = (current_index + 1) % len(audio_sources)
        new_source = audio_sources[next_index]
        
        self.device_audio_assignments[device_id] = new_source.id
        self.add_log_entry(f"Assigned {new_source.name} to {device_id}")

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

        # Keep only last 60 seconds of data
        cutoff = current_time - 60.0
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
        
        # Left column
        left_y = 0
        left_y += self._render_section(left_rect, left_y, "Connected Devices", 
                                     self._render_device_list_content, 200)
        left_y += self._render_section(left_rect, left_y, "System Logs", 
                                     self._render_log_panel_content, 180)
        
        # Right column
        right_y = 0
        right_y += self._render_section(right_rect, right_y, "Real-Time Distance (cm)", 
                                      lambda r: self._render_chart(r, self.distance_data, 0, 200), 200)
        right_y += self._render_section(right_rect, right_y, "Audio Volume (%)", 
                                      lambda r: self._render_chart(r, self.volume_data, 0, 100), 180)

    def _render_devices_page(self):
        content_y = 120
        content_height = self.screen.get_height() - content_y
        
        content_rect = pygame.Rect(Config.LAYOUT['padding'], content_y, 
                                 self.screen.get_width() - Config.LAYOUT['padding'] * 2,
                                 content_height - Config.LAYOUT['padding'])
        
        y_offset = 0
        y_offset += self._render_section(content_rect, y_offset, "Device Management", 
                                       self._render_device_management_content, 120)
        y_offset += self._render_section(content_rect, y_offset, "Device Status Overview", 
                                       self._render_device_status_content, 200)

    def _render_audio_page(self):
        content_y = 120
        content_height = self.screen.get_height() - content_y
        
        content_rect = pygame.Rect(Config.LAYOUT['padding'], content_y, 
                                 self.screen.get_width() - Config.LAYOUT['padding'] * 2,
                                 content_height - Config.LAYOUT['padding'])
        
        y_offset = 0
        y_offset += self._render_section(content_rect, y_offset, "Audio Settings", 
                                       self._render_audio_settings_content, 200)
        y_offset += self._render_section(content_rect, y_offset, "Distance Mapping", 
                                       self._render_distance_mapping_content, 180)

    def _render_hc05_connection_content(self, rect: pygame.Rect):
        button_height = 40
        button_width = 180
        spacing = 15
        
        # HC-05 scan button
        scan_rect = pygame.Rect(rect.x, rect.y, button_width, button_height)
        if self.hc05_status['available']:
            self._render_button(scan_rect, 'scan_hc05', "🔍 Scan HC-05 Devices", Config.COLORS['primary'])
        else:
            self._render_button(scan_rect, 'scan_hc05', "❌ Bluetooth Disabled", Config.COLORS['surface_light'])
        
        # Demo toggle
        demo_text = "🔴 Disable Demo" if self.device_manager.demo_mode else "🎭 Enable Demo"
        demo_color = Config.COLORS['error'] if self.device_manager.demo_mode else Config.COLORS['success']
        demo_rect = pygame.Rect(scan_rect.right + spacing, rect.y, button_width, button_height)
        self._render_button(demo_rect, 'demo_toggle', demo_text, demo_color)
        
        # Test audio button
        test_rect = pygame.Rect(demo_rect.right + spacing, rect.y, button_width, button_height)
        self._render_button(test_rect, 'test_audio', "🔊 Test Audio", Config.COLORS['info'])
        
        # Bluetooth status button
        status_rect = pygame.Rect(test_rect.right + spacing, rect.y, button_width, button_height)
        self._render_button(status_rect, 'bluetooth_status', "📊 BT Status", Config.COLORS['warning'])
        
        # Status text
        status_y = rect.y + button_height + 15
        connected_devices = len(self.device_manager.get_connected_devices())
        
        if connected_devices > 0:
            status_text = f"✅ {connected_devices} HC-05 device(s) connected"
            status_color = Config.COLORS['success']
        elif self.device_manager.demo_mode:
            status_text = "🎭 Demo mode active - simulated HC-05 data"
            status_color = Config.COLORS['warning']
        else:
            status_text = "⏳ No devices connected - scan for HC-05 SensorNodes"
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
        devices = list(self.device_manager.devices.values())
        if not devices:
            self.fonts['body'].render_to(self.screen, rect.topleft, 
                                       "No HC-05 devices connected.", Config.COLORS['text_muted'])
            self.fonts['small'].render_to(self.screen, (rect.x, rect.y + 25), 
                                        "Click 'Scan HC-05 Devices' to find your SensorNodes", Config.COLORS['text_muted'])
            return
        
        y_pos = rect.y
        for device in devices:
            if y_pos + 70 > rect.bottom:
                break
                
            device_id = device.device_id
            
            # Device info with HC-05 specific styling
            status_colors = {
                'connected': Config.COLORS['success'],
                'connecting': Config.COLORS['warning'],
                'error': Config.COLORS['error']
            }
            status_color = status_colors.get(device.status.value, Config.COLORS['text_muted'])
            
            # Device name and type
            device_type_icon = "🔵" if device.device_type == "bluetooth" else "🔌" if device.device_type == "serial" else "🎭"
            name_text = f"{device_type_icon} {device.device_name[:30]}"
            self.fonts['body'].render_to(self.screen, (rect.x, y_pos), name_text, Config.COLORS['text_primary'])
            
            # Status and last distance
            status_text = f"[{device.status.value.upper()}]"
            if device.status == DeviceStatus.CONNECTED and device.last_distance > 0:
                status_text += f" • {device.last_distance:.1f}cm"
            
            self.fonts['small'].render_to(self.screen, (rect.x, y_pos + 20), status_text, status_color)
            
            if device.status == DeviceStatus.CONNECTED:
                # Enable/disable checkbox
                checkbox_rect = pygame.Rect(rect.x, y_pos + 40, 15, 15)
                checkbox_key = f"enable_{device_id}"
                
                enabled = self.device_enabled_states.get(device_id, True)
                checkbox_color = Config.COLORS['primary'] if enabled else Config.COLORS['surface_light']
                pygame.draw.rect(self.screen, checkbox_color, checkbox_rect, border_radius=3)
                
                if enabled:
                    # Checkmark
                    pygame.draw.lines(self.screen, Config.COLORS['text_primary'], False,
                                    [(checkbox_rect.x + 3, checkbox_rect.y + 7),
                                     (checkbox_rect.x + 6, checkbox_rect.y + 10),
                                     (checkbox_rect.x + 12, checkbox_rect.y + 4)], 2)
                
                self.checkbox_rects[checkbox_key] = checkbox_rect
                
                # Audio assignment info
                current_audio = self.device_audio_assignments.get(device_id, "sine_440")
                audio_name = "Unknown"
                for source in self.audio_engine.get_audio_sources():
                    if source.id == current_audio:
                        audio_name = source.name[:25]
                        break
                
                self.fonts['small'].render_to(self.screen, (checkbox_rect.right + 20, y_pos + 40),
                                            f"Audio: {audio_name}", Config.COLORS['text_secondary'])
            
            y_pos += 70

    def _render_audio_settings_content(self, rect: pygame.Rect):
        y_pos = rect.y
        
        # Master volume slider
        self.fonts['body'].render_to(self.screen, (rect.x, y_pos), 
                                   f"Master Volume: {self.audio_effects['master_volume']:.0f}%", 
                                   Config.COLORS['text_primary'])
        
        slider_rect = pygame.Rect(rect.x, y_pos + 25, 300, 25)
        self._render_slider(slider_rect, 'master_volume', self.audio_effects['master_volume'] / 100.0)
        
        y_pos += 70
        
        # Audio engine stats
        stats = self.audio_engine.get_engine_stats()
        self.fonts['body'].render_to(self.screen, (rect.x, y_pos), "Audio Engine Status:", Config.COLORS['text_primary'])
        y_pos += 25
        
        stats_text = [
            f"Active channels: {stats['active_channels']}/{stats['total_channels']}",
            f"Sample rate: {stats['sample_rate']} Hz",
            f"Mixing: {'Enabled' if stats['mixing_enabled'] else 'Disabled'}"
        ]
        
        for stat in stats_text:
            self.fonts['small'].render_to(self.screen, (rect.x + 20, y_pos), stat, Config.COLORS['text_secondary'])
            y_pos += 18

    def _render_distance_mapping_content(self, rect: pygame.Rect):
        y_pos = rect.y
        
        self.fonts['body'].render_to(self.screen, (rect.x, y_pos), 
                                   "Distance to Audio Mapping:", Config.COLORS['text_primary'])
        y_pos += 25
        
        mapping_info = [
            f"Min Distance: {self.distance_settings['min_distance']:.1f}cm → Max Volume ({self.distance_settings['max_volume']:.0f}%)",
            f"Max Distance: {self.distance_settings['max_distance']:.1f}cm → Min Volume ({self.distance_settings['min_volume']:.0f}%)",
            f"Decay Type: {self.distance_settings['decay_type'].title()}",
            f"Frequency Range: 200Hz - 1000Hz"
        ]
        
        for info in mapping_info:
            self.fonts['small'].render_to(self.screen, (rect.x, y_pos), info, Config.COLORS['text_secondary'])
            y_pos += 20

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

    def _render_chart(self, rect: pygame.Rect, data_source: Dict[str, List], min_val: float, max_val: float):
        # Chart background
        pygame.draw.rect(self.screen, Config.COLORS['background'], rect)
        pygame.draw.rect(self.screen, Config.COLORS['border'], rect, 1)
        
        if not data_source:
            self.fonts['body'].render_to(self.screen, (rect.centerx - 40, rect.centery), 
                                       "No Data", Config.COLORS['text_muted'])
            return
        
        current_time = time.time()
        
        for i, (device_id, data_points) in enumerate(data_source.items()):
            if len(data_points) < 2:
                continue
                
            # Only show enabled devices
            if not self.device_enabled_states.get(device_id, True):
                continue
                
            color = Config.get_chart_color(i)
            points = []
            
            for timestamp, value in data_points:
                # Calculate position
                time_ratio = max(0, min(1, (current_time - timestamp) / 60.0))  # Last 60 seconds
                value_ratio = (value - min_val) / (max_val - min_val) if max_val > min_val else 0
                value_ratio = max(0, min(1, value_ratio))
                
                x = rect.right - (time_ratio * rect.width)
                y = rect.bottom - (value_ratio * rect.height)
                points.append((x, y))
            
            if len(points) > 1:
                try:
                    pygame.draw.lines(self.screen, color, False, points, 2)
                except ValueError:
                    pass  # Skip invalid points

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
        # Clean up old data
        current_time = time.time()
        cutoff_time = current_time - 300.0  # Keep 5 minutes of data
        
        for device_id in list(self.distance_data.keys()):
            self.distance_data[device_id] = [
                (t, v) for t, v in self.distance_data[device_id] if t > cutoff_time
            ]
            if not self.distance_data[device_id]:
                del self.distance_data[device_id]
                
        for device_id in list(self.volume_data.keys()):
            self.volume_data[device_id] = [
                (t, v) for t, v in self.volume_data[device_id] if t > cutoff_time
            ]
            if not self.volume_data[device_id]:
                del self.volume_data[device_id]

    def cleanup(self):
        """Clean up UI resources"""
        self.add_log_entry("UI Manager cleanup complete")
        print("Enhanced UI Manager with HC-05 support cleanup complete")