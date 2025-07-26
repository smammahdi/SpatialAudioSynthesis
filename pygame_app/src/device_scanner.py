"""
pygame_app/src/device_scanner.py
Enhanced Device Scanner Modal Window with Scrolling and Better HC-05 Filtering
"""
import pygame
import pygame.freetype
import serial.tools.list_ports
import threading
import time
from typing import List, Optional, Tuple, Dict, Any
from serial.tools.list_ports_common import ListPortInfo

# Try to import bluetooth functionality
try:
    import bleak
    from bleak import BleakScanner
    BLUETOOTH_AVAILABLE = True
    BLUETOOTH_LIBRARY = "bleak"
except ImportError:
    try:
        import bluetooth
        BLUETOOTH_AVAILABLE = True
        BLUETOOTH_LIBRARY = "pybluez"
    except ImportError:
        BLUETOOTH_AVAILABLE = False
        BLUETOOTH_LIBRARY = None
        print("❌ No Bluetooth library available. Install with: pip install bleak")

# Configuration for the popup window
POPUP_WIDTH = 900
POPUP_HEIGHT = 750
COLORS = {
    'background': (25, 30, 40),
    'surface': (35, 42, 55),
    'surface_hover': (45, 52, 65),
    'surface_light': (50, 58, 70),
    'primary': (70, 130, 200),
    'primary_hover': (90, 150, 220),
    'text_primary': (240, 245, 250),
    'text_secondary': (180, 190, 200),
    'text_muted': (140, 150, 160),
    'border': (60, 70, 85),
    'success': (80, 180, 120),
    'warning': (220, 180, 80),
    'error': (220, 80, 80),
    'hc05_highlight': (120, 200, 120),
}
PADDING = 20

class BluetoothDeviceInfo:
    """Container for Bluetooth device information with enhanced HC-05 detection"""
    def __init__(self, address: str, name: str, device_class: int = 0, rssi: int = 0):
        self.address = address
        self.name = name if name else f"Unknown-{address[-5:].replace(':', '')}"
        self.device_class = device_class
        self.rssi = rssi
        self.device = address  # For compatibility with ListPortInfo interface
        self.description = f"Bluetooth Device - {self.name}"
        self.is_bluetooth = True
        
        # Enhanced HC-05 compatibility checking
        self.is_hc05_compatible = self._check_hc05_compatibility()
        self.hc05_confidence = self._calculate_hc05_confidence()
    
    def _check_hc05_compatibility(self) -> bool:
        """Enhanced HC-05 compatibility check with stricter filtering"""
        # Primary HC-05 patterns (high confidence)
        primary_patterns = [
            'sensornode', 'hc-05', 'hc-06', 'hc05', 'hc06', 
            'bt_anuron', 'linvor'
        ]
        
        name_lower = self.name.lower()
        
        # Check primary patterns first
        for pattern in primary_patterns:
            if pattern in name_lower:
                return True
        
        # Secondary patterns (medium confidence) - but only with additional checks
        secondary_patterns = ['bluetooth', 'sensor', 'node', 'car', 'audio']
        
        # Only consider secondary patterns if the name is reasonably specific
        if any(pattern in name_lower for pattern in secondary_patterns):
            # Additional checks for secondary patterns
            if (len(self.name) > 3 and 
                not self.name.startswith('Unknown-') and
                not any(exclude in name_lower for exclude in ['laptop', 'phone', 'airpods', 'headset', 'speaker'])):
                return True
        
        return False
    
    def _calculate_hc05_confidence(self) -> int:
        """Calculate confidence level (0-100) that this is an HC-05 device"""
        name_lower = self.name.lower()
        confidence = 0
        
        # High confidence indicators
        high_confidence_patterns = ['hc-05', 'hc05', 'sensornode', 'bt_anuron']
        for pattern in high_confidence_patterns:
            if pattern in name_lower:
                confidence += 80
                break
        
        # Medium confidence indicators  
        medium_confidence_patterns = ['hc-06', 'hc06', 'linvor', 'bluetooth']
        for pattern in medium_confidence_patterns:
            if pattern in name_lower and confidence < 50:
                confidence += 50
                break
        
        # Low confidence indicators
        low_confidence_patterns = ['sensor', 'node', 'car', 'audio']
        for pattern in low_confidence_patterns:
            if pattern in name_lower and confidence < 30:
                confidence += 30
                break
        
        # Penalty for generic names
        if self.name.startswith('Unknown-'):
            confidence = max(0, confidence - 70)
        
        # Bonus for specific device names
        if (not self.name.startswith('Unknown-') and 
            len(self.name) > 3 and 
            any(char.isalpha() for char in self.name)):
            confidence += 20
        
        return min(100, confidence)

class DeviceScanner:
    """Enhanced modal window for scanning HC-05 Bluetooth and serial devices with scrolling."""
    
    def __init__(self, parent_screen: pygame.Surface):
        self.parent_screen = parent_screen
        self.parent_size = parent_screen.get_size()
        
        # Create modal surface
        self.screen = parent_screen
        self.modal_surface = pygame.Surface((POPUP_WIDTH, POPUP_HEIGHT))
        self.modal_rect = pygame.Rect(
            (self.parent_size[0] - POPUP_WIDTH) // 2,
            (self.parent_size[1] - POPUP_HEIGHT) // 2,
            POPUP_WIDTH,
            POPUP_HEIGHT
        )
        
        # Initialize fonts
        pygame.freetype.init()
        try:
            self.font_body = pygame.freetype.Font(None, 16)
            self.font_title = pygame.freetype.Font(None, 24)
            self.font_small = pygame.freetype.Font(None, 14)
            self.font_heading = pygame.freetype.Font(None, 18)
        except Exception as e:
            print(f"Font initialization error: {e}")
            # Fallback fonts
            self.font_body = pygame.freetype.Font(None, 16)
            self.font_title = pygame.freetype.Font(None, 24)
            self.font_small = pygame.freetype.Font(None, 14)
            self.font_heading = pygame.freetype.Font(None, 18)
        
        # Scanner state
        self.available_devices: List[Any] = []
        self.selected_device_index: Optional[int] = None
        self.status_message = "Click 'Scan HC-05' to find your SensorNode devices."
        self.scanning = False
        self.running = True
        self.scan_type = "bluetooth"
        self.hc05_only_mode = True  # New flag for strict HC-05 filtering
        
        # Scrolling state
        self.scroll_offset = 0
        self.max_scroll = 0
        self.item_height = 75
        self.visible_items = 6
        
        # UI elements
        self.button_rects = {}
        self.mouse_pos = (0, 0)
        
        # Background overlay
        self.overlay = pygame.Surface(self.parent_size)
        self.overlay.set_alpha(128)
        self.overlay.fill((0, 0, 0))

    def _scan_for_hc05_devices(self):
        """Scans specifically for HC-05 devices with strict filtering."""
        if self.scanning or not BLUETOOTH_AVAILABLE:
            if not BLUETOOTH_AVAILABLE:
                self.status_message = f"Bluetooth not available. Library: {BLUETOOTH_LIBRARY}"
            return
            
        self.scanning = True
        self.scan_type = "bluetooth"
        self.hc05_only_mode = True
        self.status_message = "Scanning for HC-05 SensorNodes (strict filtering)..."
        self.available_devices = []
        self.selected_device_index = None
        self.scroll_offset = 0
        
        def hc05_strict_scan_worker():
            try:
                if BLUETOOTH_LIBRARY == "bleak":
                    self._scan_hc05_strict_with_bleak()
                else:
                    self._scan_hc05_strict_with_pybluez()
                    
            except Exception as e:
                self.status_message = f"HC-05 scan error: {str(e)}"
                print(f"HC-05 scanning error: {e}")
            
            self.scanning = False
        
        scan_thread = threading.Thread(target=hc05_strict_scan_worker, daemon=True)
        scan_thread.start()

    def _scan_hc05_strict_with_bleak(self):
        """Strict HC-05 scanning with bleak - only true HC-05 devices"""
        import asyncio
        
        async def bleak_hc05_strict_scan():
            self.status_message = "Scanning for HC-05 devices (strict mode)..."
            
            try:
                devices = await BleakScanner.discover(timeout=15.0)
                
                hc05_devices = []
                
                print(f"📡 Found {len(devices)} total BLE devices")
                
                for device in devices:
                    device_name = device.name or f"Unknown-{device.address[-5:].replace(':', '')}"
                    rssi = getattr(device, 'rssi', 0)
                    
                    bt_device = BluetoothDeviceInfo(
                        address=device.address,
                        name=device_name,
                        rssi=rssi
                    )
                    
                    # Strict filtering: only devices with high HC-05 confidence
                    if bt_device.is_hc05_compatible and bt_device.hc05_confidence >= 30:
                        hc05_devices.append(bt_device)
                        confidence_str = f"({bt_device.hc05_confidence}% confidence)"
                        print(f"📱 HC-05 device: {device_name} {confidence_str} RSSI: {rssi}dBm")
                
                # Sort by HC-05 confidence (highest first)
                hc05_devices.sort(key=lambda d: d.hc05_confidence, reverse=True)
                
                self.available_devices = hc05_devices
                self._update_scroll_limits()
                
                if not self.available_devices:
                    self.status_message = "No HC-05 SensorNodes found. Make sure your device is powered and discoverable."
                else:
                    self.status_message = f"Found {len(self.available_devices)} HC-05 SensorNode(s). Select one to connect."
                    
            except Exception as e:
                self.status_message = f"HC-05 scan error: {str(e)}"
                print(f"HC-05 scanning error: {e}")
        
        try:
            asyncio.run(bleak_hc05_strict_scan())
        except Exception as e:
            self.status_message = f"Scan error: {str(e)}"

    def _scan_hc05_strict_with_pybluez(self):
        """Strict HC-05 scanning using pybluez"""
        try:
            import bluetooth
            self.status_message = "Scanning for HC-05 devices (PyBluez strict mode)..."
            
            nearby_devices = bluetooth.discover_devices(
                duration=10, lookup_names=True, flush_cache=True, lookup_class=True
            )
            
            hc05_devices = []
            
            for addr, name, device_class in nearby_devices:
                device_name = name if name else f"Unknown-{addr[-5:].replace(':', '')}"
                
                bt_device = BluetoothDeviceInfo(addr, device_name, device_class)
                
                # Strict filtering for PyBluez too
                if bt_device.is_hc05_compatible and bt_device.hc05_confidence >= 30:
                    hc05_devices.append(bt_device)
                    print(f"📱 HC-05 device: {device_name} ({bt_device.hc05_confidence}% confidence)")
            
            # Sort by confidence
            hc05_devices.sort(key=lambda d: d.hc05_confidence, reverse=True)
            
            self.available_devices = hc05_devices
            self._update_scroll_limits()
            
            if not self.available_devices:
                self.status_message = "No HC-05 SensorNodes found with PyBluez."
            else:
                self.status_message = f"Found {len(self.available_devices)} HC-05 SensorNode(s). Select one to connect."
                
        except Exception as e:
            self.status_message = f"PyBluez HC-05 scan error: {str(e)}"

    def _scan_all_bluetooth_devices(self):
        """Scans for ALL Bluetooth devices (not filtered)."""
        if self.scanning or not BLUETOOTH_AVAILABLE:
            return
            
        self.scanning = True
        self.scan_type = "bluetooth"
        self.hc05_only_mode = False
        self.status_message = "Scanning for ALL Bluetooth devices..."
        self.available_devices = []
        self.selected_device_index = None
        self.scroll_offset = 0
        
        def bluetooth_scan_all_worker():
            try:
                if BLUETOOTH_LIBRARY == "bleak":
                    self._scan_all_with_bleak()
                else:
                    self._scan_all_with_pybluez()
                    
            except Exception as e:
                self.status_message = f"All devices scan error: {str(e)}"
                print(f"All devices scanning error: {e}")
            
            self.scanning = False
        
        scan_thread = threading.Thread(target=bluetooth_scan_all_worker, daemon=True)
        scan_thread.start()

    def _scan_all_with_bleak(self):
        """Scan for all devices using bleak"""
        import asyncio
        
        async def bleak_scan_all():
            self.status_message = "Discovering ALL Bluetooth devices..."
            
            try:
                devices = await BleakScanner.discover(timeout=15.0)
                
                bluetooth_devices = []
                
                for device in devices:
                    device_name = device.name or f"Unknown-{device.address[-5:].replace(':', '')}"
                    rssi = getattr(device, 'rssi', 0)
                    
                    bt_device = BluetoothDeviceInfo(
                        address=device.address,
                        name=device_name,
                        rssi=rssi
                    )
                    bluetooth_devices.append(bt_device)
                
                # Sort: HC-05 devices first, then by name
                bluetooth_devices.sort(key=lambda d: (-d.hc05_confidence, d.name))
                
                self.available_devices = bluetooth_devices
                self._update_scroll_limits()
                
                if not self.available_devices:
                    self.status_message = "No Bluetooth devices found."
                else:
                    hc05_count = len([d for d in bluetooth_devices if d.is_hc05_compatible])
                    self.status_message = f"Found {len(self.available_devices)} devices ({hc05_count} HC-05 compatible)."
                    
            except Exception as e:
                self.status_message = f"All devices scan error: {str(e)}"
        
        try:
            asyncio.run(bleak_scan_all())
        except Exception as e:
            self.status_message = f"Scan error: {str(e)}"

    def _scan_all_with_pybluez(self):
        """Scan for all devices using pybluez"""
        try:
            import bluetooth
            
            nearby_devices = bluetooth.discover_devices(
                duration=10, lookup_names=True, flush_cache=True, lookup_class=True
            )
            
            bluetooth_devices = []
            
            for addr, name, device_class in nearby_devices:
                device_name = name if name else f"Unknown Device ({addr})"
                bluetooth_devices.append(BluetoothDeviceInfo(addr, device_name, device_class))
            
            # Sort: HC-05 devices first
            bluetooth_devices.sort(key=lambda d: (-d.hc05_confidence, d.name))
            
            self.available_devices = bluetooth_devices
            self._update_scroll_limits()
            
            if not self.available_devices:
                self.status_message = "No Bluetooth devices found."
            else:
                hc05_count = len([d for d in bluetooth_devices if d.is_hc05_compatible])
                self.status_message = f"Found {len(self.available_devices)} devices ({hc05_count} HC-05 compatible)."
                
        except Exception as e:
            self.status_message = f"All devices scan error: {str(e)}"

    def _scan_for_serial_ports(self):
        """Scans for available serial ports."""
        if self.scanning:
            return
            
        self.scanning = True
        self.scan_type = "serial"
        self.hc05_only_mode = False
        self.status_message = "Scanning for serial devices..."
        self.available_devices = []
        self.selected_device_index = None
        self.scroll_offset = 0
        
        try:
            ports = serial.tools.list_ports.comports()
            self.available_devices = list(ports)
            self._update_scroll_limits()
            
            if not self.available_devices:
                self.status_message = "No serial ports found."
            else:
                self.status_message = f"Found {len(self.available_devices)} serial port(s)."
                
        except Exception as e:
            self.status_message = f"Serial scan error: {str(e)}"
        
        self.scanning = False

    def _update_scroll_limits(self):
        """Update scrolling limits based on device count"""
        total_items = len(self.available_devices)
        if total_items <= self.visible_items:
            self.max_scroll = 0
        else:
            self.max_scroll = (total_items - self.visible_items) * self.item_height
        
        # Ensure scroll offset is within bounds
        self.scroll_offset = max(0, min(self.scroll_offset, self.max_scroll))

    def _handle_scroll(self, scroll_direction: int):
        """Handle scrolling the device list"""
        scroll_amount = self.item_height * 2  # Scroll 2 items at a time
        
        if scroll_direction > 0:  # Scroll down
            self.scroll_offset = min(self.max_scroll, self.scroll_offset + scroll_amount)
        else:  # Scroll up
            self.scroll_offset = max(0, self.scroll_offset - scroll_amount)

    def run(self) -> Optional[Any]:
        """Runs the modal window loop and returns the selected device or None."""
        try:
            clock = pygame.time.Clock()
            selected_device = None
            
            while self.running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                        return None
                    elif event.type == pygame.MOUSEMOTION:
                        # Adjust mouse position to modal coordinates
                        self.mouse_pos = (
                            event.pos[0] - self.modal_rect.x,
                            event.pos[1] - self.modal_rect.y
                        )
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        if event.button == 1:  # Left click
                            # Check if click is within modal
                            if self.modal_rect.collidepoint(event.pos):
                                modal_pos = (
                                    event.pos[0] - self.modal_rect.x,
                                    event.pos[1] - self.modal_rect.y
                                )
                                self._handle_click(modal_pos)
                            else:
                                # Click outside modal - close it
                                self.running = False
                                return None
                        elif event.button == 4:  # Mouse wheel up
                            self._handle_scroll(-1)
                        elif event.button == 5:  # Mouse wheel down
                            self._handle_scroll(1)
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            self.running = False
                            return None
                        elif event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                            if self.selected_device_index is not None:
                                selected_device = self.available_devices[self.selected_device_index]
                                self.running = False
                                break
                        elif event.key == pygame.K_UP:
                            self._handle_scroll(-1)
                        elif event.key == pygame.K_DOWN:
                            self._handle_scroll(1)

                # Render
                self.modal_surface.fill(COLORS['background'])
                self.render()
                
                # Draw overlay and modal
                self.screen.blit(self.overlay, (0, 0))
                self.screen.blit(self.modal_surface, self.modal_rect)
                
                # Draw modal border
                pygame.draw.rect(self.screen, COLORS['border'], self.modal_rect, 3, border_radius=10)
                
                pygame.display.flip()
                clock.tick(60)

            # Return selected device
            if self.selected_device_index is not None and self.selected_device_index < len(self.available_devices):
                selected_device = self.available_devices[self.selected_device_index]
                
        except Exception as e:
            print(f"Scanner run error: {e}")
            selected_device = None
        
        return selected_device

    def _handle_click(self, pos: Tuple[int, int]):
        """Handles mouse clicks on buttons and list items."""
        # Button clicks
        if 'scan_hc05' in self.button_rects and self.button_rects['scan_hc05'].collidepoint(pos):
            if not self.scanning:
                self._scan_for_hc05_devices()
            return

        if 'scan_all_bluetooth' in self.button_rects and self.button_rects['scan_all_bluetooth'].collidepoint(pos):
            if not self.scanning:
                self._scan_all_bluetooth_devices()
            return

        if 'scan_serial' in self.button_rects and self.button_rects['scan_serial'].collidepoint(pos):
            if not self.scanning:
                self._scan_for_serial_ports()
            return

        if 'connect' in self.button_rects and self.button_rects['connect'].collidepoint(pos):
            if self.selected_device_index is not None:
                self.running = False
            return

        if 'cancel' in self.button_rects and self.button_rects['cancel'].collidepoint(pos):
            self.selected_device_index = None
            self.running = False
            return

        # Device list clicks
        self._handle_device_list_click(pos)

    def _handle_device_list_click(self, pos: Tuple[int, int]):
        """Handle clicks on the device list with scrolling support"""
        list_start_y = 180
        list_height = POPUP_HEIGHT - list_start_y - 140
        
        # Check if click is within list area
        list_rect = pygame.Rect(PADDING, list_start_y, POPUP_WIDTH - PADDING * 2, list_height)
        if not list_rect.collidepoint(pos):
            return
        
        # Calculate which item was clicked considering scroll
        relative_y = pos[1] - list_start_y + self.scroll_offset
        item_index = int(relative_y // self.item_height)
        
        if 0 <= item_index < len(self.available_devices):
            self.selected_device_index = item_index

    def render(self):
        """Renders the entire scanner window."""
        self.button_rects.clear()
        
        self._render_header()
        self._render_status()
        self._render_device_list()
        self._render_buttons()
        self._render_instructions()

    def _render_header(self):
        """Render the header section."""
        header_rect = pygame.Rect(0, 0, POPUP_WIDTH, 70)
        pygame.draw.rect(self.modal_surface, COLORS['surface'], header_rect)
        pygame.draw.line(self.modal_surface, COLORS['border'], 
                        header_rect.bottomleft, header_rect.bottomright, 2)
        
        # Title
        self.font_title.render_to(self.modal_surface, (PADDING, 15), 
                                "🔵 HC-05 Device Scanner", COLORS['text_primary'])
        
        # Subtitle
        subtitle = "SensorNode & HC-05 Bluetooth Discovery"
        if not BLUETOOTH_AVAILABLE:
            subtitle += f" (Bluetooth disabled - {BLUETOOTH_LIBRARY or 'no library'})"
        self.font_small.render_to(self.modal_surface, (PADDING, 40), subtitle, COLORS['text_secondary'])

    def _render_status(self):
        """Render the status message."""
        status_y = 80
        
        status_rect = pygame.Rect(PADDING, status_y, POPUP_WIDTH - PADDING * 2, 45)
        pygame.draw.rect(self.modal_surface, COLORS['surface_light'], status_rect, border_radius=5)
        
        # Status color
        if "error" in self.status_message.lower():
            status_color = COLORS['error']
        elif "scanning" in self.status_message.lower():
            status_color = COLORS['warning']
        elif "found" in self.status_message.lower():
            status_color = COLORS['success']
        else:
            status_color = COLORS['text_secondary']
        
        # Wrap message if too long
        message = self.status_message
        if len(message) > 85:
            message = message[:82] + "..."
        
        self.font_body.render_to(self.modal_surface, (status_rect.x + 15, status_rect.y + 15), 
                               message, status_color)

    def _render_device_list(self):
        """Render the scrollable device list."""
        list_start_y = 180
        list_height = POPUP_HEIGHT - list_start_y - 140
        
        # List background
        list_rect = pygame.Rect(PADDING, list_start_y, POPUP_WIDTH - PADDING * 2, list_height)
        pygame.draw.rect(self.modal_surface, COLORS['surface'], list_rect, border_radius=8)
        pygame.draw.rect(self.modal_surface, COLORS['border'], list_rect, 2, border_radius=8)
        
        if not self.available_devices:
            # No devices message
            if self.scanning:
                msg = "🔍 Scanning for devices..."
            else:
                msg = "No devices found. Use scan buttons above."
            
            text_rect = self.font_body.get_rect(msg)
            text_x = list_rect.centerx - text_rect.width // 2
            text_y = list_rect.centery - text_rect.height // 2
            
            self.font_body.render_to(self.modal_surface, (text_x, text_y), msg, COLORS['text_muted'])
            return

        # Calculate visible items
        first_visible = max(0, self.scroll_offset // self.item_height)
        last_visible = min(len(self.available_devices), first_visible + self.visible_items + 1)
        
        # Render visible device items
        for i in range(first_visible, last_visible):
            device = self.available_devices[i]
            
            # Calculate item position
            item_y = list_start_y + 10 + (i * self.item_height) - self.scroll_offset
            
            # Skip items that are completely outside the visible area
            if item_y + self.item_height < list_start_y or item_y > list_start_y + list_height:
                continue
            
            item_rect = pygame.Rect(PADDING + 10, item_y, POPUP_WIDTH - PADDING * 2 - 20, self.item_height - 5)
            
            # Item background
            if i == self.selected_device_index:
                item_color = COLORS['primary']
                text_color = COLORS['text_primary']
                desc_color = COLORS['text_primary']
            elif item_rect.collidepoint(self.mouse_pos):
                item_color = COLORS['surface_hover']
                text_color = COLORS['text_primary']
                desc_color = COLORS['text_secondary']
            else:
                item_color = COLORS['surface_light']
                text_color = COLORS['text_secondary']
                desc_color = COLORS['text_muted']
            
            # Highlight HC-05 compatible devices
            if hasattr(device, 'is_bluetooth') and hasattr(device, 'is_hc05_compatible') and device.is_hc05_compatible:
                if i != self.selected_device_index:
                    # Add subtle green tint for HC-05 devices
                    item_color = tuple(min(255, c + 15) if j == 1 else c for j, c in enumerate(item_color))
            
            pygame.draw.rect(self.modal_surface, item_color, item_rect, border_radius=5)
            
            # Device information
            if hasattr(device, 'is_bluetooth'):
                # Bluetooth device
                device_name = device.name
                device_info = f"Bluetooth: {device.address}"
                if hasattr(device, 'rssi') and device.rssi:
                    device_info += f" (RSSI: {device.rssi}dBm)"
                
                # Type indicator with HC-05 confidence
                if hasattr(device, 'is_hc05_compatible') and device.is_hc05_compatible:
                    confidence = getattr(device, 'hc05_confidence', 0)
                    type_indicator = f"🔵 HC-05 ({confidence}%)"
                    type_color = COLORS['hc05_highlight'] if confidence >= 50 else COLORS['warning']
                else:
                    type_indicator = "🔵 BT"
                    type_color = text_color
            else:
                # Serial device
                device_name = getattr(device, 'device', 'Unknown Port')
                device_info = getattr(device, 'description', 'No description')
                type_indicator = "🔌 USB"
                type_color = text_color
            
            # Truncate long names
            if len(device_name) > 45:
                device_name = device_name[:42] + "..."
            if len(device_info) > 55:
                device_info = device_info[:52] + "..."
            
            # Render device info
            self.font_body.render_to(self.modal_surface, (item_rect.x + 15, item_rect.y + 8), 
                                   device_name, text_color)
            self.font_small.render_to(self.modal_surface, (item_rect.x + 15, item_rect.y + 28), 
                                    device_info, desc_color)
            
            # Type indicator
            self.font_small.render_to(self.modal_surface, (item_rect.right - 120, item_rect.y + 8), 
                                    type_indicator, type_color)
            
            # Additional HC-05 info
            if (hasattr(device, 'is_bluetooth') and hasattr(device, 'is_hc05_compatible') and 
                device.is_hc05_compatible and hasattr(device, 'hc05_confidence')):
                confidence = device.hc05_confidence
                if confidence >= 70:
                    conf_text = "✅ High Confidence"
                    conf_color = COLORS['success']
                elif confidence >= 40:
                    conf_text = "⚠️ Medium Confidence"
                    conf_color = COLORS['warning']
                else:
                    conf_text = "❓ Low Confidence"
                    conf_color = COLORS['error']
                
                self.font_small.render_to(self.modal_surface, (item_rect.x + 15, item_rect.y + 48), 
                                        conf_text, conf_color)

        # Render scrollbar if needed
        if self.max_scroll > 0:
            self._render_scrollbar(list_rect)

    def _render_scrollbar(self, list_rect: pygame.Rect):
        """Render scrollbar for the device list"""
        scrollbar_width = 8
        scrollbar_x = list_rect.right - scrollbar_width - 5
        scrollbar_height = list_rect.height - 20
        scrollbar_y = list_rect.y + 10
        
        # Scrollbar track
        track_rect = pygame.Rect(scrollbar_x, scrollbar_y, scrollbar_width, scrollbar_height)
        pygame.draw.rect(self.modal_surface, COLORS['surface_light'], track_rect, border_radius=4)
        
        # Scrollbar thumb
        if self.max_scroll > 0:
            thumb_height = max(20, (scrollbar_height * scrollbar_height) // (scrollbar_height + self.max_scroll))
            thumb_y = scrollbar_y + (self.scroll_offset * (scrollbar_height - thumb_height)) // self.max_scroll
            
            thumb_rect = pygame.Rect(scrollbar_x, thumb_y, scrollbar_width, thumb_height)
            pygame.draw.rect(self.modal_surface, COLORS['primary'], thumb_rect, border_radius=4)

    def _render_buttons(self):
        """Render control buttons."""
        button_y = POPUP_HEIGHT - 90
        button_height = 35
        button_width = 130
        spacing = 15
        
        # Button configurations
        buttons = []
        
        # Bluetooth buttons (if available)
        if BLUETOOTH_AVAILABLE:
            buttons.extend([
                ('scan_hc05', 'Scan HC-05', COLORS['primary'], 20),
                ('scan_all_bluetooth', 'Scan All BT', COLORS['warning'], 170),
            ])
        
        # Serial button  
        serial_x = 320 if BLUETOOTH_AVAILABLE else 20
        buttons.append(('scan_serial', 'Scan Serial', COLORS['success'], serial_x))
        
        # Control buttons
        buttons.extend([
            ('connect', 'Connect', COLORS['success'], POPUP_WIDTH - 280),
            ('cancel', 'Cancel', COLORS['error'], POPUP_WIDTH - 140)
        ])
        
        for btn_id, btn_text, btn_color, btn_x in buttons:
            if btn_id == 'connect' and self.selected_device_index is None:
                btn_color = COLORS['surface_light']  # Disabled state
            
            button_rect = pygame.Rect(btn_x, button_y, button_width, button_height)
            
            # Button hover effect
            if button_rect.collidepoint(self.mouse_pos) and not self.scanning:
                if btn_id != 'connect' or self.selected_device_index is not None:
                    hover_color = tuple(min(255, c + 25) for c in btn_color)
                    pygame.draw.rect(self.modal_surface, hover_color, button_rect, border_radius=6)
                else:
                    pygame.draw.rect(self.modal_surface, btn_color, button_rect, border_radius=6)
            else:
                pygame.draw.rect(self.modal_surface, btn_color, button_rect, border_radius=6)
            
            # Button border
            pygame.draw.rect(self.modal_surface, COLORS['border'], button_rect, 1, border_radius=6)
            
            # Button text
            text_color = COLORS['text_primary']
            if btn_id == 'connect' and self.selected_device_index is None:
                text_color = COLORS['text_muted']
            
            text_surf, text_rect = self.font_body.render(btn_text, text_color)
            text_rect.center = button_rect.center
            self.modal_surface.blit(text_surf, text_rect)
            
            self.button_rects[btn_id] = button_rect

    def _render_instructions(self):
        """Render usage instructions."""
        instruction_y = POPUP_HEIGHT - 40
        
        if BLUETOOTH_AVAILABLE:
            instructions = "HC-05: Find SensorNodes • All BT: Show all devices • Scroll: Mouse wheel/Arrow keys • Enter: Connect • Esc: Cancel"
        else:
            instructions = "Install bleak for Bluetooth • Serial: USB connections • Enter: Connect • Esc: Cancel"
        
        self.font_small.render_to(self.modal_surface, (PADDING, instruction_y), 
                                instructions, COLORS['text_muted'])

    def cleanup(self):
        """Clean up scanner resources."""
        self.running = False