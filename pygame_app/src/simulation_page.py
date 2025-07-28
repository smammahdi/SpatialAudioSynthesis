"""
pygame_app/src/simulation_page.py
Simulation Page with Real-time Trilateration Visualization
"""
import pygame
import pygame.freetype
import math
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from .grid_range_editor import GridRangeEditor
from .coordinate_editor import CoordinateEditor

@dataclass
class Point2D:
    x: float
    y: float
    
    def distance_to(self, other: 'Point2D') -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

@dataclass
class SensorNode:
    id: str
    position: Point2D
    current_distance: float = 0.0
    color: Tuple[int, int, int] = (100, 100, 100)

class SimulationPage:
    def __init__(self, screen: pygame.Surface, device_manager, audio_engine, fonts: Dict):
        self.screen = screen
        self.device_manager = device_manager
        self.audio_engine = audio_engine
        self.fonts = fonts
        
        # Layout
        self.left_width = int(screen.get_width() * 0.25)
        self.right_width = screen.get_width() - self.left_width
        self.content_y = 120  # Below navigation
        self.content_height = screen.get_height() - self.content_y
        
        # Sensor nodes on the grid
        self.sensor_nodes: Dict[str, SensorNode] = {}
        
        # Grid properties
        self.grid_margin = 40
        self.grid_origin = Point2D(
            self.left_width + self.grid_margin,
            self.content_y + self.content_height - self.grid_margin
        )
        self.grid_width = self.right_width - 2 * self.grid_margin
        self.grid_height = self.content_height - 2 * self.grid_margin
        self.max_distance = 200  # Will be updated from settings
        self.pixels_per_cm = 2.0  # Scale factor
        
        # Initialize independent X/Y scaling factors (will be properly calculated in render)
        self.pixels_per_cm_x = 2.0  # Initial value, updated in render
        self.pixels_per_cm_y = 2.0  # Initial value, updated in render
        
        # Visualization settings
        self.show_circles = True
        self.show_triangle = True
        self.show_orientation = True
        self.show_grid = True
        
        # Grid range settings
        self.grid_range_x = 300  # cm
        self.grid_range_y = 300  # cm
        
        # Track logging state to prevent spam
        self.last_sensor_count = -1
        
        # Moving object state
        self.moving_object_device = None
        self.moving_object_orientation = 0.0  # Calibrated degrees for display
        self.raw_moving_object_orientation = 0.0  # Raw degrees from device
        self.moving_object_position: Optional[Point2D] = None
        self.orientation_offset = 0.0  # For recalibration
        
        # Demo moving object for testing
        self.demo_moving_object = {
            'enabled': False,
            'position': Point2D(150, 150),
            'orientation': 0.0,  # Default to up direction (0 degrees = up, like a compass)
            'distance_mode': 'auto',  # 'auto' or 'manual'
            'manual_distances': {}  # Manual distance per sensor node ID when in manual mode
        }
        
        # Track previous distances to avoid continuous logging
        self.previous_distances = []
        
        # Input text states
        self.input_states = {}
        self.active_input = None
        
        # Interaction state
        self.dragging_node: Optional[str] = None
        self.selected_node: Optional[str] = None  # For click-to-select then click-to-place
        self.mouse_pos = (0, 0)
        self.button_rects = {}
        self.checkbox_rects = {}
        
        # Colors
        self.colors = {
            'grid': (60, 70, 85),
            'grid_lines': (40, 50, 65),
            'circle': (70, 130, 200, 60),  # Semi-transparent
            'triangle': (220, 180, 80),
            'orientation': (80, 220, 120),
            'node': (70, 130, 200),
            'text': (240, 245, 250),
            'text_secondary': (180, 190, 200),
            'surface': (35, 42, 55),
            'border': (60, 70, 85),
            'primary': (70, 130, 200),
            'success': (80, 180, 120),
            'error': (220, 80, 80)
        }
        
        # Device colors (matching the main UI)
        self.device_colors = [
            (70, 130, 200),   # Blue
            (120, 180, 80),   # Green
            (200, 150, 80),   # Orange
            (180, 80, 180),   # Purple
            (80, 180, 180),   # Cyan
            (200, 80, 120),   # Pink
        ]
        
        # Load car image for orientation indicator
        try:
            self.car_image = pygame.image.load("assets/images/car.png")
            # Scale the car image to a reasonable size (40x40 pixels)
            self.car_image = pygame.transform.scale(self.car_image, (40, 40))
            print("✅ Car image loaded successfully")
        except Exception as e:
            print(f"⚠️ Failed to load car image: {e}")
            self.car_image = None
        
        # Initialize default sensor positions
        self._initialize_default_positions()
    
    def _initialize_default_positions(self):
        """Initialize default sensor positions in a triangle"""
        # Default triangle setup in the grid using initial scale factor
        # Note: This uses the initial pixels_per_cm, proper scaling happens in render()
        center_x = self.grid_range_x / 2  # Use grid range directly instead of pixel calculations
        center_y = self.grid_range_y / 2
        radius = min(center_x, center_y) * 0.6
        
        default_positions = [
            Point2D(center_x, center_y + radius),  # Top
            Point2D(center_x - radius * 0.866, center_y - radius * 0.5),  # Bottom left
            Point2D(center_x + radius * 0.866, center_y - radius * 0.5)   # Bottom right
        ]
        
        # Assign to first three connected sensor devices (exclude moving objects)
        sensor_devices = [device for device in self.device_manager.devices.values() 
                         if device.device_type != "moving_object"][:3]
        
        print(f"🔍 Initializing sensor positions for {len(sensor_devices)} sensor devices (excluding moving objects)")
        
        for i, device in enumerate(sensor_devices):
            if i < len(default_positions):
                self.sensor_nodes[device.device_id] = SensorNode(
                    id=device.device_id,
                    position=default_positions[i],
                    color=self.device_colors[i % len(self.device_colors)]
                )
                print(f"📍 Sensor node {device.device_name} positioned at ({default_positions[i].x:.1f}, {default_positions[i].y:.1f})")
    
    def render(self, rect: pygame.Rect):
        """Render the simulation page"""
        # Clear button rects
        self.button_rects.clear()
        self.checkbox_rects.clear()
        
        # Left panel
        left_rect = pygame.Rect(rect.x, rect.y, self.left_width - 20, rect.height)
        self._render_left_panel(left_rect)
        
        # Right panel (grid)
        right_rect = pygame.Rect(self.left_width, rect.y, self.right_width, rect.height)
        self._render_grid_panel(right_rect)
    
    def _render_left_panel(self, rect: pygame.Rect):
        """Render the left control panel with new structure"""
        # Panel background
        pygame.draw.rect(self.screen, self.colors['surface'], rect, border_radius=8)
        pygame.draw.rect(self.screen, self.colors['border'], rect, 2, border_radius=8)
        
        y_pos = rect.y + 15
        
        # Moving Object Connection Settings
        y_pos = self._render_moving_object_section(rect, y_pos)
        y_pos += 15
        
        # Visualization Options (moved to top)
        y_pos = self._render_visualization_options(rect, y_pos)
        y_pos += 15
        
        # Sensor Nodes section
        y_pos = self._render_sensor_nodes_section(rect, y_pos)
        y_pos += 15
        
        # Moving Object Status (at bottom)
        self._render_moving_object_status(rect, rect.bottom - 120)
    
    def _render_moving_object_section(self, rect: pygame.Rect, y_start: int) -> int:
        """Render moving object connection section"""
        y_pos = y_start
        
        # Section background
        section_height = 85
        section_rect = pygame.Rect(rect.x + 5, y_pos, rect.width - 10, section_height)
        pygame.draw.rect(self.screen, (30, 35, 45), section_rect, border_radius=5)
        pygame.draw.rect(self.screen, self.colors['border'], section_rect, 1, border_radius=5)
        y_pos += 10
        
        # Section title
        self.fonts['body'].render_to(self.screen, (rect.x + 15, y_pos), 
                                 "Moving Object Connection", self.colors['text'])
        y_pos += 25
        
        # Connection status
        status_text = "Connected" if self.moving_object_device else "Disconnected"
        status_color = self.colors['success'] if self.moving_object_device else self.colors['error']
        self.fonts['small'].render_to(self.screen, (rect.x + 15, y_pos), 
                                    f"Status: {status_text}", status_color)
        y_pos += 20
        
        # Demo button
        demo_rect = pygame.Rect(rect.x + 15, y_pos, rect.width - 30, 25)
        demo_text = "Stop Demo" if self.demo_moving_object['enabled'] else "Start Demo"
        demo_color = self.colors['error'] if self.demo_moving_object['enabled'] else self.colors['success']
        self._render_button(demo_rect, 'toggle_demo', demo_text, demo_color)
        y_pos += 30
        
        # Demo distance controls (only show when demo is enabled)
        if self.demo_moving_object['enabled']:
            y_pos += 5
            # Distance mode toggle
            mode_text = f"Distance: {self.demo_moving_object['distance_mode'].title()}"
            self.fonts['small'].render_to(self.screen, (rect.x + 15, y_pos), 
                                        mode_text, self.colors['text_secondary'])
            y_pos += 18
            
            # Mode toggle button
            mode_rect = pygame.Rect(rect.x + 15, y_pos, rect.width - 30, 20)
            toggle_text = "Switch to Manual" if self.demo_moving_object['distance_mode'] == 'auto' else "Switch to Auto"
            self._render_button(mode_rect, 'toggle_distance_mode', toggle_text, self.colors['primary'])
            y_pos += 25
        
        return y_pos
    
    def _render_visualization_options(self, rect: pygame.Rect, y_start: int) -> int:
        """Render visualization options section"""
        y_pos = y_start
        
        # Section background
        section_height = 170  # Reduced height since we removed excircle
        section_rect = pygame.Rect(rect.x + 5, y_pos, rect.width - 10, section_height)
        pygame.draw.rect(self.screen, (25, 30, 40), section_rect, border_radius=5)
        pygame.draw.rect(self.screen, self.colors['border'], section_rect, 1, border_radius=5)
        y_pos += 10
        
        # Section title
        self.fonts['body'].render_to(self.screen, (rect.x + 15, y_pos), 
                                   "Visualization Options", self.colors['text_secondary'])
        y_pos += 20
        
        options = [
            ('show_grid', 'Show Grid', self.show_grid),
            ('show_circles', 'Distance Circles', self.show_circles),
            ('show_triangle', 'Min Area Triangle', self.show_triangle),
            ('show_orientation', 'Orientation', self.show_orientation)
        ]
        
        for key, label, value in options:
            checkbox_rect = pygame.Rect(rect.x + 15, y_pos, 15, 15)
            pygame.draw.rect(self.screen, self.colors['border'], checkbox_rect, 1, border_radius=3)
            
            if value:
                pygame.draw.rect(self.screen, self.colors['success'], 
                               pygame.Rect(checkbox_rect.x + 3, checkbox_rect.y + 3, 9, 9), 
                               border_radius=2)
            
            self.fonts['small'].render_to(self.screen, (checkbox_rect.right + 8, y_pos), 
                                        label, self.colors['text'])
            
            self.checkbox_rects[key] = checkbox_rect
            y_pos += 18
        
        # Grid range settings
        y_pos += 5
        self.fonts['small'].render_to(self.screen, (rect.x + 15, y_pos), 
                                    f"Grid Range: {self.grid_range_x:.0f} x {self.grid_range_y:.0f} cm", self.colors['text_secondary'])
        y_pos += 18
        
        # Edit grid range button
        edit_grid_rect = pygame.Rect(rect.x + 15, y_pos, rect.width - 30, 25)
        self._render_button(edit_grid_rect, 'edit_grid_range', "Edit Range", self.colors['primary'])
        y_pos += 30
        
        return y_pos
    
    def _render_sensor_nodes_section(self, rect: pygame.Rect, y_start: int) -> int:
        """Render sensor nodes configuration section"""
        y_pos = y_start
        
        # Calculate section height based on number of sensor devices only
        sensor_devices = [device for device in self.device_manager.devices.values() 
                         if device.device_type != "moving_object"]
        num_sensor_devices = len(sensor_devices)
        section_height = 40 + (num_sensor_devices * 85)
        section_rect = pygame.Rect(rect.x + 5, y_pos, rect.width - 10, min(section_height, 400))
        pygame.draw.rect(self.screen, (20, 25, 35), section_rect, border_radius=5)
        pygame.draw.rect(self.screen, self.colors['border'], section_rect, 1, border_radius=5)
        y_pos += 10
        
        # Section title
        self.fonts['body'].render_to(self.screen, (rect.x + 15, y_pos), 
                                   "Sensor Nodes", self.colors['text_secondary'])
        y_pos += 20
        
        # Filter to only show actual sensor nodes (exclude moving objects)
        devices = [device for device in self.device_manager.devices.values() 
                  if device.device_type != "moving_object"]
        
        # Only log when sensor count changes to prevent spam
        if len(devices) != self.last_sensor_count:
            print(f"🔍 Displaying sensor nodes: {len(devices)} devices (excluding moving objects)")
            self.last_sensor_count = len(devices)
        
        for i, device in enumerate(devices):
            # Device card
            card_rect = pygame.Rect(rect.x + 10, y_pos, rect.width - 20, 75)
            pygame.draw.rect(self.screen, (40, 48, 62), card_rect, border_radius=5)
            pygame.draw.rect(self.screen, self.colors['border'], card_rect, 1, border_radius=5)
            
            # Color indicator
            color = self.device_colors[i % len(self.device_colors)]
            indicator_rect = pygame.Rect(card_rect.x, card_rect.y, 4, card_rect.height)
            pygame.draw.rect(self.screen, color, indicator_rect, border_radius=2)
            
            # Device name
            device_name = device.device_name[:18] + "..." if len(device.device_name) > 18 else device.device_name
            self.fonts['small'].render_to(self.screen, (card_rect.x + 8, card_rect.y + 5), 
                                        device_name, self.colors['text'])
            
            # Always show coordinate display and edit button
            # Get or create default node position
            if device.device_id not in self.sensor_nodes:
                # Create default position
                default_x = 50 + (i * 50) % 200
                default_y = 50 + (i * 50) % 200
                color_idx = i % len(self.device_colors)
                self.sensor_nodes[device.device_id] = SensorNode(
                    id=device.device_id,
                    position=Point2D(default_x, default_y),
                    color=self.device_colors[color_idx]
                )
            
            node = self.sensor_nodes[device.device_id]
            
            # Position display
            pos_text = f"Position: ({node.position.x:.1f}, {node.position.y:.1f})"
            self.fonts['small'].render_to(self.screen, (card_rect.x + 8, card_rect.y + 20), 
                                        pos_text, self.colors['text'])
            
            # Distance info or controls
            if self.demo_moving_object['enabled'] and self.demo_moving_object['distance_mode'] == 'manual':
                # Show manual distance controls
                manual_dist = self.demo_moving_object['manual_distances'].get(device.device_id, 100.0)
                dist_text = f"Manual: {manual_dist:.0f}cm"
                self.fonts['small'].render_to(self.screen, (card_rect.x + 8, card_rect.y + 35), 
                                            dist_text, self.colors['text_secondary'])
                
                # Distance control buttons
                minus_rect = pygame.Rect(card_rect.x + card_rect.width - 45, card_rect.y + 32, 15, 15)
                plus_rect = pygame.Rect(card_rect.x + card_rect.width - 25, card_rect.y + 32, 15, 15)
                self._render_button(minus_rect, f"dist_minus_{device.device_id}", "-", self.colors['error'])
                self._render_button(plus_rect, f"dist_plus_{device.device_id}", "+", self.colors['success'])
            else:
                # Show actual distance
                if self.demo_moving_object['enabled']:
                    # Calculate auto distance in demo mode
                    actual_dist = self.demo_moving_object['position'].distance_to(node.position)
                    dist_text = f"Auto: {actual_dist:.1f}cm"
                else:
                    # Show device distance
                    dist_text = f"Distance: {device.last_distance:.1f}cm"
                self.fonts['small'].render_to(self.screen, (card_rect.x + 8, card_rect.y + 35), 
                                            dist_text, self.colors['text_secondary'])
            
            # Edit coordinates button
            edit_btn_rect = pygame.Rect(card_rect.x + 8, card_rect.y + 50, card_rect.width - 16, 20)
            self._render_button(edit_btn_rect, f"edit_coords_{device.device_id}", "Edit Coordinates", self.colors['primary'])
            
            y_pos += 80
        
        return y_pos
    
    def _render_moving_object_status(self, rect: pygame.Rect, y_start: int):
        """Render moving object status section at bottom"""
        y_pos = y_start
        
        # Section background
        section_height = 120
        section_rect = pygame.Rect(rect.x + 5, y_pos, rect.width - 10, section_height)
        pygame.draw.rect(self.screen, (30, 35, 45), section_rect, border_radius=5)
        pygame.draw.rect(self.screen, self.colors['border'], section_rect, 1, border_radius=5)
        y_pos += 10
        
        # Section title
        self.fonts['body'].render_to(self.screen, (rect.x + 15, y_pos), 
                                   "Moving Object", self.colors['text_secondary'])
        y_pos += 20
        
        # Orientation display with animation
        current_orientation = self.demo_moving_object['orientation'] if self.demo_moving_object['enabled'] else self.moving_object_orientation
        orientation_text = f"Orientation: {current_orientation:.1f}°"
        self.fonts['small'].render_to(self.screen, (rect.x + 15, y_pos), 
                                    orientation_text, self.colors['text'])
        y_pos += 20
        
        # Visual orientation indicator (mini car) - clickable for manual control
        car_center_x = rect.x + rect.width // 2
        car_center_y = y_pos + 25
        
        # Create clickable area around the car
        car_click_rect = pygame.Rect(car_center_x - 40, car_center_y - 30, 80, 60)
        self.button_rects['orientation_widget'] = car_click_rect
        
        # Draw background circle for visual feedback
        pygame.draw.circle(self.screen, (40, 50, 65), (car_center_x, car_center_y), 35, 1)
        
        self._draw_mini_car(car_center_x, car_center_y, current_orientation)
        y_pos += 50
        
        # Recalibrate button
        recal_rect = pygame.Rect(rect.x + 15, y_pos, rect.width - 30, 25)
        self._render_button(recal_rect, 'recalibrate', "Recalibrate", self.colors['primary'])
    
    def _draw_mini_car(self, center_x: int, center_y: int, orientation: float):
        """Draw a mini car with orientation indicator using the car image"""
        if self.car_image:
            # Use the actual car image
            # Scale for the mini display - enlarged as requested
            mini_scale = 0.8  # Increased from 0.5 to make it larger in left panel
            original_size = self.car_image.get_size()
            mini_size = (int(original_size[0] * mini_scale), int(original_size[1] * mini_scale))
            mini_car = pygame.transform.scale(self.car_image, mini_size)
            
            # Rotate the mini car image
            # 0° = no rotation (car points up), positive angles = clockwise rotation
            # pygame.transform.rotate rotates counterclockwise, so we negate for clockwise
            rotated_car = pygame.transform.rotate(mini_car, -orientation)
            
            # Get the rotated image rect and center it on the position
            car_rect = rotated_car.get_rect()
            car_rect.center = (center_x, center_y)
            
            # Draw the mini car
            self.screen.blit(rotated_car, car_rect)
        else:
            # Fallback to rectangle if car image not available
            car_width, car_height = 30, 20
            
            # Create car surface
            car_surface = pygame.Surface((car_width, car_height), pygame.SRCALPHA)
            
            # Car body (rounded rectangle)
            pygame.draw.rect(car_surface, (70, 130, 200), 
                            pygame.Rect(0, 0, car_width, car_height), border_radius=8)
            pygame.draw.rect(car_surface, (240, 245, 250), 
                            pygame.Rect(0, 0, car_width, car_height), 2, border_radius=8)
            
            # Front indicator (triangle)
            front_points = [(car_width - 5, car_height // 2 - 4), 
                           (car_width, car_height // 2), 
                           (car_width - 5, car_height // 2 + 4)]
            pygame.draw.polygon(car_surface, (255, 217, 61), front_points)
            
            # Rotate the car surface
            # 0° = no rotation (car points up), positive angles = clockwise rotation
            # pygame.transform.rotate rotates counterclockwise, so we negate for clockwise
            rotated_car = pygame.transform.rotate(car_surface, -orientation)
            
            # Get the rect and center it
            car_rect = rotated_car.get_rect(center=(center_x, center_y))
            
            # Blit to screen
            self.screen.blit(rotated_car, car_rect)
    
    def _render_input_field(self, rect: pygame.Rect, key: str, placeholder: str):
        """Render an input field"""
        is_active = self.active_input == key
        
        # Background
        bg_color = (60, 70, 85) if is_active else (45, 55, 70)
        pygame.draw.rect(self.screen, bg_color, rect, border_radius=3)
        pygame.draw.rect(self.screen, self.colors['border'], rect, 1, border_radius=3)
        
        # Text
        display_text = self.input_states.get(key, placeholder)
        self.fonts['small'].render_to(self.screen, (rect.x + 3, rect.y + 2), 
                                    display_text, self.colors['text'])
        
        # Store rect for click detection
        self.button_rects[key] = rect
    
    def _render_grid_panel(self, rect: pygame.Rect):
        """Render the 2D grid visualization"""
        # Panel background
        pygame.draw.rect(self.screen, (20, 25, 35), rect, border_radius=8)
        pygame.draw.rect(self.screen, self.colors['border'], rect, 2, border_radius=8)
        
        # Grid area
        grid_rect = pygame.Rect(
            rect.x + self.grid_margin,
            rect.y + self.grid_margin,
            rect.width - 2 * self.grid_margin,
            rect.height - 2 * self.grid_margin
        )
        
        # Grid background
        pygame.draw.rect(self.screen, (15, 20, 30), grid_rect, border_radius=5)
        
        # Update grid properties
        self.grid_origin = Point2D(grid_rect.left, grid_rect.bottom)
        self.grid_width = grid_rect.width
        self.grid_height = grid_rect.height
        
        # Calculate scale to fill the entire grid space independently for X and Y
        self.pixels_per_cm_x = self.grid_width / self.grid_range_x
        self.pixels_per_cm_y = self.grid_height / self.grid_range_y
        # For uniform scaling, use the smaller value, but we'll use independent scaling for grid lines
        self.pixels_per_cm = min(self.pixels_per_cm_x, self.pixels_per_cm_y)
        
        # Draw grid lines if enabled
        if self.show_grid:
            self._draw_grid_lines(grid_rect)
        
        # Draw sensor nodes and their circles
        self._draw_sensor_nodes(grid_rect)
        
        # Draw placement preview if a node is selected
        if self.selected_node and self.mouse_pos[0] > self.left_width + 20:
            # Convert mouse position to grid coordinates with INDEPENDENT X/Y scaling
            preview_x = (self.mouse_pos[0] - self.grid_origin.x) / self.pixels_per_cm_x
            preview_y = (self.grid_origin.y - self.mouse_pos[1]) / self.pixels_per_cm_y
            
            # Check if preview position is within grid bounds with smaller margin
            margin = 5
            if (margin <= preview_x <= self.grid_range_x - margin and 
                margin <= preview_y <= self.grid_range_y - margin):
                
                # Convert back to screen coordinates for drawing with INDEPENDENT scaling
                screen_x = self.grid_origin.x + preview_x * self.pixels_per_cm_x
                screen_y = self.grid_origin.y - preview_y * self.pixels_per_cm_y
                
                # Draw preview placement indicator
                pygame.draw.circle(self.screen, (100, 255, 100, 100), (int(screen_x), int(screen_y)), 12, 2)
                pygame.draw.circle(self.screen, (100, 255, 100, 50), (int(screen_x), int(screen_y)), 8)
                
                # Draw crosshair
                pygame.draw.line(self.screen, (100, 255, 100), 
                               (int(screen_x - 15), int(screen_y)), (int(screen_x + 15), int(screen_y)), 2)
                pygame.draw.line(self.screen, (100, 255, 100), 
                               (int(screen_x), int(screen_y - 15)), (int(screen_x), int(screen_y + 15)), 2)
        
        # Perform trilateration if we have at least 3 nodes with valid distances
        if self.demo_moving_object['enabled']:
            # Use demo mode - calculate distances from demo position to sensor nodes
            active_nodes = list(self.sensor_nodes.values())[:3]  # Use first 3 nodes
            distances = []
            for node in active_nodes:
                if self.demo_moving_object['distance_mode'] == 'auto':
                    # Calculate actual distance from demo position to sensor node
                    distance = self.demo_moving_object['position'].distance_to(node.position)
                else:
                    # Use manual distance for this specific sensor
                    distance = self.demo_moving_object['manual_distances'].get(node.id, 100.0)
                distances.append(distance)
        else:
            # Use real device data
            active_nodes = [node for node in self.sensor_nodes.values() 
                           if self.device_manager.devices.get(node.id, None) and 
                           self.device_manager.devices[node.id].last_distance > 0]
            
            if len(active_nodes) >= 3:
                # Get the first 3 nodes for trilateration
                nodes = active_nodes[:3]
                distances = [self.device_manager.devices[node.id].last_distance for node in nodes]
            else:
                active_nodes = []
        
        if len(active_nodes) >= 3:
            nodes = active_nodes[:3]
            
            # Perform trilateration directly
            result = self._perform_trilateration(nodes, distances)
            if result:
                self.moving_object_position = result['position']
                
                # Draw visualization layers
                if self.show_circles:
                    self._draw_distance_circles(nodes, distances)
                
                if self.show_triangle and 'triangle' in result and result['triangle'] is not None:
                    self._draw_triangle_of_interest(result['triangle'])
                
                # Draw estimated car with physical dimensions (includes orientation)
                if 'car_dimensions' in result:
                    is_fallback = result.get('is_fallback', False) or result.get('triangle') is None
                    self._draw_estimated_car(self.moving_object_position, result['car_dimensions'], is_fallback)
                elif self.show_orientation and self.moving_object_position:
                    # Fallback: draw simple orientation if no car dimensions available
                    self._draw_orientation(self.moving_object_position)
    
    def _draw_grid_lines(self, rect: pygame.Rect):
        """Draw improved grid lines with proper labels and range"""
        # Determine grid spacing based on range
        spacing_options = [10, 25, 50, 100, 200]
        optimal_spacing = 50
        
        for spacing in spacing_options:
            if self.grid_range_x / spacing <= 12 and self.grid_range_y / spacing <= 12:
                optimal_spacing = spacing
                break
        
        # Draw vertical lines (X-axis) using independent X scaling
        for x_cm in range(0, int(self.grid_range_x) + 1, optimal_spacing):
            x_pixel = self.grid_origin.x + x_cm * self.pixels_per_cm_x
            if x_pixel <= rect.right:
                # Main grid line
                line_color = self.colors['grid_lines'] if x_cm % (optimal_spacing * 2) != 0 else self.colors['border']
                pygame.draw.line(self.screen, line_color, 
                               (x_pixel, rect.top), (x_pixel, rect.bottom), 1)
                
                # Label every other line or every 100cm
                if x_cm % (optimal_spacing * 2) == 0 or optimal_spacing >= 100:
                    text_rect = self.fonts['small'].get_rect(str(x_cm))
                    self.fonts['small'].render_to(self.screen, 
                                                (x_pixel - text_rect.width // 2, rect.bottom + 3), 
                                                str(x_cm), self.colors['text_secondary'])
        
        # Draw horizontal lines (Y-axis) using independent Y scaling
        for y_cm in range(0, int(self.grid_range_y) + 1, optimal_spacing):
            y_pixel = self.grid_origin.y - y_cm * self.pixels_per_cm_y
            if y_pixel >= rect.top:
                # Main grid line
                line_color = self.colors['grid_lines'] if y_cm % (optimal_spacing * 2) != 0 else self.colors['border']
                pygame.draw.line(self.screen, line_color, 
                               (rect.left, y_pixel), (rect.right, y_pixel), 1)
                
                # Label every other line or every 100cm
                if y_cm % (optimal_spacing * 2) == 0 or optimal_spacing >= 100:
                    text_rect = self.fonts['small'].get_rect(str(y_cm))
                    self.fonts['small'].render_to(self.screen, 
                                                (rect.left - text_rect.width - 5, y_pixel - text_rect.height // 2), 
                                                str(y_cm), self.colors['text_secondary'])
        
        # Origin marker
        pygame.draw.circle(self.screen, self.colors['error'], 
                         (int(self.grid_origin.x), int(self.grid_origin.y)), 4)
        self.fonts['tiny'].render_to(self.screen, 
                                   (self.grid_origin.x + 8, self.grid_origin.y - 12), 
                                   "(0,0)", self.colors['text'])
        
        # Grid boundary using independent scaling  
        max_y = self.grid_origin.y - self.grid_range_y * self.pixels_per_cm_y
        boundary_rect = pygame.Rect(self.grid_origin.x, max_y, 
                                   self.grid_range_x * self.pixels_per_cm_x, 
                                   self.grid_range_y * self.pixels_per_cm_y)
        pygame.draw.rect(self.screen, self.colors['border'], boundary_rect, 2)
    
    def _draw_sensor_nodes(self, rect: pygame.Rect):
        """Draw sensor nodes on the grid"""
        # Note: rect parameter kept for consistency with other draw methods
        for node_id, node in self.sensor_nodes.items():
            # Convert to pixel coordinates using INDEPENDENT X/Y scaling
            x = self.grid_origin.x + node.position.x * self.pixels_per_cm_x
            y = self.grid_origin.y - node.position.y * self.pixels_per_cm_y
            
            # Draw node with enhanced visual feedback if being dragged or selected
            if self.dragging_node == node_id:
                # Highlight the node being dragged (keep existing drag functionality)
                pygame.draw.circle(self.screen, (255, 255, 100), (int(x), int(y)), 12)  # Larger yellow highlight
                pygame.draw.circle(self.screen, node.color, (int(x), int(y)), 10)
                pygame.draw.circle(self.screen, self.colors['text'], (int(x), int(y)), 10, 3)
                
                # Draw drag indicator
                pygame.draw.circle(self.screen, (255, 255, 255, 100), (int(x), int(y)), 20, 2)
            elif self.selected_node == node_id:
                # Highlight the selected node for click-to-place
                pygame.draw.circle(self.screen, (100, 255, 100), (int(x), int(y)), 12)  # Larger green highlight
                pygame.draw.circle(self.screen, node.color, (int(x), int(y)), 10)
                pygame.draw.circle(self.screen, self.colors['text'], (int(x), int(y)), 10, 3)
                
                # Draw selection indicator with pulsing effect
                import time
                pulse = int(255 * (0.5 + 0.5 * math.sin(time.time() * 4)))  # Pulsing effect
                pygame.draw.circle(self.screen, (100, 255, 100, pulse // 4), (int(x), int(y)), 15, 2)
                
                # Draw instruction text
                instruction_text = "Click on grid to place here"
                text_rect = self.fonts['tiny'].get_rect(instruction_text)
                bg_rect = pygame.Rect(x - text_rect.width // 2 - 4, y - 35, text_rect.width + 8, text_rect.height + 4)
                pygame.draw.rect(self.screen, (*self.colors['surface'], 200), bg_rect, border_radius=3)
                self.fonts['tiny'].render_to(self.screen, (x - text_rect.width // 2, y - 32), 
                                           instruction_text, (100, 255, 100))
            else:
                # Normal node appearance
                pygame.draw.circle(self.screen, node.color, (int(x), int(y)), 8)
                pygame.draw.circle(self.screen, self.colors['text'], (int(x), int(y)), 8, 2)
            
            # Node label
            device = self.device_manager.devices.get(node_id)
            if device:
                label = device.device_name[:10]
                
                # Determine which distance to display based on current mode
                if self.demo_moving_object['enabled']:
                    if self.demo_moving_object['distance_mode'] == 'auto':
                        # Calculate distance from demo position to sensor node
                        distance = self.demo_moving_object['position'].distance_to(node.position)
                    else:
                        # Use manual distance for this specific sensor
                        distance = self.demo_moving_object['manual_distances'].get(node_id, 100.0)
                else:
                    # Use real device data
                    distance = device.last_distance
                
                # Background for text
                text_rect = pygame.Rect(x - 40, y - 35, 80, 25)
                pygame.draw.rect(self.screen, (*self.colors['surface'], 200), text_rect, border_radius=3)
                
                self.fonts['tiny'].render_to(self.screen, (x - 35, y - 30), 
                                           label, self.colors['text'])
                self.fonts['tiny'].render_to(self.screen, (x - 35, y - 18), 
                                           f"{distance:.1f}cm", node.color)
    
    def _draw_distance_circles(self, nodes: List[SensorNode], distances: List[float]):
        """Draw distance circles around sensor nodes, clipped to grid boundaries"""
        # Get grid boundaries for clipping
        grid_left = self.grid_origin.x
        grid_right = self.grid_origin.x + self.grid_range_x * self.pixels_per_cm_x
        grid_top = self.grid_origin.y - self.grid_range_y * self.pixels_per_cm_y
        grid_bottom = self.grid_origin.y
        
        for node, distance in zip(nodes, distances):
            x = self.grid_origin.x + node.position.x * self.pixels_per_cm_x
            y = self.grid_origin.y - node.position.y * self.pixels_per_cm_y
            # Use average scaling for radius to maintain circular shape
            radius = distance * ((self.pixels_per_cm_x + self.pixels_per_cm_y) / 2)
            
            if radius > 0:
                # Check if circle intersects with grid area
                if (x + radius >= grid_left and x - radius <= grid_right and 
                    y + radius >= grid_top and y - radius <= grid_bottom):
                    
                    # Draw circle with clipping
                    circle_surface = pygame.Surface((int(radius * 2 + 2), int(radius * 2 + 2)), pygame.SRCALPHA)
                    pygame.draw.circle(circle_surface, (*node.color, 40), 
                                     (int(radius + 1), int(radius + 1)), int(radius), 2)
                    
                    # Calculate blit position
                    blit_x = x - radius - 1
                    blit_y = y - radius - 1
                    
                    # Clip to grid boundaries
                    clip_x = max(blit_x, grid_left)
                    clip_y = max(blit_y, grid_top)
                    clip_w = min(blit_x + circle_surface.get_width(), grid_right) - clip_x
                    clip_h = min(blit_y + circle_surface.get_height(), grid_bottom) - clip_y
                    
                    if clip_w > 0 and clip_h > 0:
                        source_x = clip_x - blit_x
                        source_y = clip_y - blit_y
                        source_rect = pygame.Rect(source_x, source_y, clip_w, clip_h)
                        self.screen.blit(circle_surface, (clip_x, clip_y), source_rect)
    
    def _perform_trilateration(self, nodes: List[SensorNode], distances: List[float]) -> Optional[Dict]:
        """
        ROBUST MINIMUM AREA TRIANGLE ALGORITHM:
        Find the smallest valid triangle formed by points on the three distance circles.
        """
        if len(nodes) < 3 or len(distances) < 3:
            return None
        
        # Car physical dimensions (30cm x 16cm)
        CAR_LENGTH = 30.0  # cm
        CAR_WIDTH = 16.0   # cm  
        CAR_RADIUS = math.sqrt((CAR_LENGTH/2)**2 + (CAR_WIDTH/2)**2)  # ~17.9cm diagonal
        
        # Use the first 3 nodes
        p1, p2, p3 = nodes[:3]
        r1, r2, r3 = distances[:3]
        
        # Only log once per second to avoid spam
        current_time = pygame.time.get_ticks()
        should_log = not hasattr(self, '_last_trilateration_log') or current_time - self._last_trilateration_log > 2000
        if should_log:
            self._last_trilateration_log = current_time
            print(f"\n🔧 Trilateration Algorithm")
            print(f"📍 Sensors: P1=({p1.position.x:.1f},{p1.position.y:.1f},r={r1:.1f}), " +
                  f"P2=({p2.position.x:.1f},{p2.position.y:.1f},r={r2:.1f}), " +
                  f"P3=({p3.position.x:.1f},{p3.position.y:.1f},r={r3:.1f})")
        
        # First try analytical circle intersections for robustness
        intersection_candidates = []
        
        # Find all pairwise circle intersections
        int_12 = self._circle_intersections(p1.position, r1, p2.position, r2)
        int_13 = self._circle_intersections(p1.position, r1, p3.position, r3)
        int_23 = self._circle_intersections(p2.position, r2, p3.position, r3)
        
        # Collect all intersection points and calculate their error relative to all three circles
        all_intersections = []
        if int_12:
            all_intersections.extend(int_12)
        if int_13:
            all_intersections.extend(int_13)
        if int_23:
            all_intersections.extend(int_23)
        
        if all_intersections:
            for point in all_intersections:
                # Calculate total error for this point relative to all three circles
                error1 = abs(point.distance_to(p1.position) - r1)
                error2 = abs(point.distance_to(p2.position) - r2)
                error3 = abs(point.distance_to(p3.position) - r3)
                total_error = error1 + error2 + error3
                intersection_candidates.append((point, total_error))
            
            # Sort by total error
            intersection_candidates.sort(key=lambda x: x[1])
            
            # If the best intersection point has low error, use it
            if intersection_candidates[0][1] < 5.0:  # 5cm total error threshold
                best_point = intersection_candidates[0][0]
                if should_log:
                    print(f"✅ Using analytical intersection with error: {intersection_candidates[0][1]:.1f}cm")
                    print(f"🚗 Car position: ({best_point.x:.1f}, {best_point.y:.1f})")
                
                return {
                    'position': best_point,
                    'triangle': None,  # No triangle visualization for analytical solution
                    'car_dimensions': {'length': CAR_LENGTH, 'width': CAR_WIDTH, 'radius': CAR_RADIUS}
                }
        
        # If analytical approach fails, use minimum area triangle approach
        # Sample fewer points for efficiency but ensure good coverage
        samples_per_circle = 24
        circle1_points = self._sample_circle_points(p1.position, r1, samples_per_circle)
        circle2_points = self._sample_circle_points(p2.position, r2, samples_per_circle)  
        circle3_points = self._sample_circle_points(p3.position, r3, samples_per_circle)
        
        best_triangle = None
        min_area = float('inf')
        best_centroid = None
        valid_count = 0
        
        # More reasonable minimum area threshold
        MIN_TRIANGLE_AREA = 100.0  # cm² - larger minimum to avoid degenerate triangles
        MIN_SIDE_LENGTH = 15.0     # cm - minimum distance between any two points
        
        # Smart sampling: don't check every combination, sample strategically
        sample_step = max(1, samples_per_circle // 8)  # Check every 8th point for efficiency
        
        for i in range(0, samples_per_circle, sample_step):
            pt1 = circle1_points[i]
            for j in range(0, samples_per_circle, sample_step):
                pt2 = circle2_points[j]
                
                # Quick distance check
                if pt1.distance_to(pt2) < MIN_SIDE_LENGTH:
                    continue
                    
                for k in range(0, samples_per_circle, sample_step):
                    pt3 = circle3_points[k]
                    
                    # Check minimum distances between all points
                    d12 = pt1.distance_to(pt2)
                    d23 = pt2.distance_to(pt3)
                    d13 = pt1.distance_to(pt3)
                    
                    if d23 < MIN_SIDE_LENGTH or d13 < MIN_SIDE_LENGTH:
                        continue
                    
                    # Calculate triangle area
                    area = self._triangle_area(pt1, pt2, pt3)
                    
                    # Skip degenerate triangles
                    if area < MIN_TRIANGLE_AREA:
                        continue
                    
                    valid_count += 1
                    
                    # Update best triangle if this one has smaller area
                    if area < min_area:
                        min_area = area
                        best_triangle = [pt1, pt2, pt3]
                        # Calculate centroid
                        best_centroid = Point2D(
                            (pt1.x + pt2.x + pt3.x) / 3,
                            (pt1.y + pt2.y + pt3.y) / 3
                        )
        
        if best_triangle and best_centroid:
            if should_log:
                print(f"✅ Found minimum area triangle (area: {min_area:.1f} cm², {valid_count} valid triangles)")
                print(f"🚗 Car position: ({best_centroid.x:.1f}, {best_centroid.y:.1f})")
            
            return {
                'position': best_centroid,
                'triangle': best_triangle,
                'car_dimensions': {'length': CAR_LENGTH, 'width': CAR_WIDTH, 'radius': CAR_RADIUS}
            }
        
        # Final fallback: weighted centroid
        if should_log:
            print(f"⚠️ No valid triangles found, using fallback")
        
        # Simple weighted position based on inverse distance
        total_weight = 0
        weighted_x = 0
        weighted_y = 0
        
        for i, (pos, radius) in enumerate([(p1.position, r1), (p2.position, r2), (p3.position, r3)]):
            # Weight inversely proportional to distance (closer sensors have more influence)
            weight = 1.0 / max(radius, 1.0)  # Avoid division by zero
            total_weight += weight
            weighted_x += pos.x * weight
            weighted_y += pos.y * weight
        
        fallback_position = Point2D(weighted_x / total_weight, weighted_y / total_weight)
        
        if should_log:
            print(f"📍 Fallback position: ({fallback_position.x:.1f}, {fallback_position.y:.1f})")
        
        return {
            'position': fallback_position,
            'triangle': None,
            'car_dimensions': {'length': CAR_LENGTH, 'width': CAR_WIDTH, 'radius': CAR_RADIUS},
            'is_fallback': True
        }
    
    def _sample_circle_points(self, center: Point2D, radius: float, num_samples: int = 24) -> List[Point2D]:
        """Sample points uniformly around a circle"""
        points = []
        for i in range(num_samples):
            angle = (2 * math.pi * i) / num_samples
            x = center.x + radius * math.cos(angle)
            y = center.y + radius * math.sin(angle)
            points.append(Point2D(x, y))
        return points
    
    def _circle_intersections(self, c1: Point2D, r1: float, c2: Point2D, r2: float) -> Optional[List[Point2D]]:
        """Find intersection points of two circles"""
        d = c1.distance_to(c2)
        
        # Check if circles intersect
        if d > r1 + r2 or d < abs(r1 - r2) or d < 0.1:
            return None
        
        # Calculate intersection points
        try:
            a = (r1*r1 - r2*r2 + d*d) / (2*d)
            h_squared = r1*r1 - a*a
            
            if h_squared < 0:
                return None
                
            h = math.sqrt(h_squared)
        except:
            return None
        
        # Point on line between centers
        px = c1.x + a * (c2.x - c1.x) / d
        py = c1.y + a * (c2.y - c1.y) / d
        
        # Intersection points
        p1 = Point2D(
            px + h * (c2.y - c1.y) / d,
            py - h * (c2.x - c1.x) / d
        )
        p2 = Point2D(
            px - h * (c2.y - c1.y) / d,
            py + h * (c2.x - c1.x) / d
        )
        
        return [p1, p2]
    
    def _triangle_area(self, p1: Point2D, p2: Point2D, p3: Point2D) -> float:
        """Calculate area of a triangle using cross product"""
        return abs((p2.x - p1.x) * (p3.y - p1.y) - (p3.x - p1.x) * (p2.y - p1.y)) / 2
    
    def _draw_triangle_of_interest(self, triangle: List[Point2D]):
        """Draw the minimum area triangle"""
        if not triangle or len(triangle) < 3:
            return
        
        points = []
        for p in triangle:
            x = self.grid_origin.x + p.x * self.pixels_per_cm_x
            y = self.grid_origin.y - p.y * self.pixels_per_cm_y
            points.append((int(x), int(y)))
        
        if len(points) >= 3:
            # Calculate the actual triangle area in cm² for coloring
            p1, p2, p3 = triangle[:3]
            area = self._triangle_area(p1, p2, p3)
            
            # Color triangle based on quality (green = good, yellow = okay, orange = acceptable)
            if area > 500:  # Large triangle = good
                triangle_color = (100, 255, 100)  # Green
                alpha = 60
            elif area > 200:  # Medium triangle = okay
                triangle_color = (255, 255, 100)  # Yellow
                alpha = 80
            else:  # Small triangle = acceptable but not ideal
                triangle_color = (255, 200, 100)  # Orange
                alpha = 100
            
            # Create a surface for the filled triangle with transparency
            triangle_surface = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
            pygame.draw.polygon(triangle_surface, (*triangle_color, alpha), points)
            self.screen.blit(triangle_surface, (0, 0))
            
            # Draw triangle outline (solid) - thicker for visibility
            pygame.draw.polygon(self.screen, triangle_color, points, 3)
            
            # Draw vertices as circles
            for i, (x, y) in enumerate(points):
                # Larger circles for better visibility
                pygame.draw.circle(self.screen, triangle_color, (int(x), int(y)), 8)
                pygame.draw.circle(self.screen, (255, 255, 255), (int(x), int(y)), 8, 2)
                
                # Label vertices with background for better readability
                label = f"P{i+1}"
                text_rect = self.fonts['tiny'].get_rect(label)
                bg_rect = pygame.Rect(x + 12, y - 12, text_rect.width + 4, text_rect.height + 2)
                pygame.draw.rect(self.screen, (*self.colors['surface'], 200), bg_rect, border_radius=2)
                self.fonts['tiny'].render_to(self.screen, (x + 14, y - 10), 
                                           label, self.colors['text'])
            
            # Add area label in center of triangle
            centroid_x = sum(x for x, y in points) // 3
            centroid_y = sum(y for x, y in points) // 3
            area_label = f"Area: {area:.0f}cm²"
            text_rect = self.fonts['tiny'].get_rect(area_label)
            bg_rect = pygame.Rect(centroid_x - text_rect.width//2 - 2, centroid_y - text_rect.height//2 - 1, 
                                text_rect.width + 4, text_rect.height + 2)
            pygame.draw.rect(self.screen, (*self.colors['surface'], 220), bg_rect, border_radius=2)
            self.fonts['tiny'].render_to(self.screen, (centroid_x - text_rect.width//2, centroid_y - text_rect.height//2), 
                                       area_label, triangle_color)
    
    def _draw_estimated_car(self, position: Point2D, car_dims: Dict, is_fallback: bool = False):
        """Draw the estimated car position using the car image"""
        if not position or not car_dims:
            return
        
        # Convert to screen coordinates using INDEPENDENT X/Y scaling
        center_x = self.grid_origin.x + position.x * self.pixels_per_cm_x
        center_y = self.grid_origin.y - position.y * self.pixels_per_cm_y
        
        # Get current orientation
        current_orientation = self.demo_moving_object['orientation'] if self.demo_moving_object['enabled'] else self.moving_object_orientation
        
        if self.car_image:
            # Scale the car image to match physical dimensions using average scaling
            avg_scale = (self.pixels_per_cm_x + self.pixels_per_cm_y) / 2
            car_length_px = car_dims['length'] * avg_scale
            car_width_px = car_dims['width'] * avg_scale
            
            # Calculate scale factor to match physical dimensions
            original_size = self.car_image.get_size()
            scale_x = car_length_px / original_size[1]  # Length corresponds to height in image
            scale_y = car_width_px / original_size[0]   # Width corresponds to width in image
            scale = min(scale_x, scale_y)  # Use uniform scaling
            
            # Scale the image
            scaled_size = (int(original_size[0] * scale), int(original_size[1] * scale))
            scaled_car = pygame.transform.scale(self.car_image, scaled_size)
            
            # Rotate the scaled car image
            # 0° = no rotation (car points up), positive angles = clockwise rotation
            # pygame.transform.rotate rotates counterclockwise, so we negate for clockwise
            rotated_car = pygame.transform.rotate(scaled_car, -current_orientation)
            
            # Get the rotated image rect and center it on the position
            car_rect = rotated_car.get_rect()
            car_rect.center = (int(center_x), int(center_y))
            
            # Draw the car with semi-transparency to show it's estimated
            car_surface = rotated_car.copy()
            car_surface.set_alpha(180 if not is_fallback else 100)  # More transparent if fallback
            self.screen.blit(car_surface, car_rect)
            
            # Draw outline - red if fallback, yellow if normal
            outline_color = (220, 80, 80) if is_fallback else (255, 217, 61)
            pygame.draw.rect(self.screen, outline_color, car_rect, 2)
            
        else:
            # Fallback to rectangle if car image not available
            car_length_px = car_dims['length'] * self.pixels_per_cm
            car_width_px = car_dims['width'] * self.pixels_per_cm
            
            # Calculate car corners before rotation
            half_length = car_length_px / 2
            half_width = car_width_px / 2
            corners = [
                (-half_length, -half_width),  # Back left
                (half_length, -half_width),   # Front left  
                (half_length, half_width),    # Front right
                (-half_length, half_width)    # Back right
            ]
            
            # Rotate corners based on orientation
            angle_rad = math.radians(current_orientation)
            cos_a = math.cos(angle_rad)
            sin_a = math.sin(angle_rad)
            
            rotated_corners = []
            for dx, dy in corners:
                # Rotate point
                rotated_x = dx * cos_a - dy * sin_a
                rotated_y = dx * sin_a + dy * cos_a
                
                # Translate to screen position
                screen_x = center_x + rotated_x
                screen_y = center_y + rotated_y
                rotated_corners.append((screen_x, screen_y))
            
            # Draw car body - red tint if fallback
            fill_color = (220, 80, 80, 120) if is_fallback else (255, 217, 61, 120)
            outline_color = (220, 80, 80) if is_fallback else (255, 217, 61)
            
            pygame.draw.polygon(self.screen, fill_color, rotated_corners)  # Semi-transparent
            pygame.draw.polygon(self.screen, outline_color, rotated_corners, 3)    # Outline
        
        # Label
        status_text = " (Fallback)" if is_fallback else ""
        label = f"Car Center ({position.x:.1f}, {position.y:.1f}){status_text}"
        text_rect = pygame.Rect(center_x - 80, center_y - 25, 160, 15)
        pygame.draw.rect(self.screen, (*self.colors['surface'], 200), text_rect, border_radius=3)
        
        label_color = (220, 80, 80) if is_fallback else self.colors['text']
        text_width = self.fonts['tiny'].get_rect(label).width
        self.fonts['tiny'].render_to(self.screen, (center_x - text_width // 2, center_y - 20), 
                                   label, label_color)
    
    def _draw_orientation(self, position: Point2D):
        """Draw the moving object with car image rotated based on orientation"""
        x = self.grid_origin.x + position.x * self.pixels_per_cm_x
        y = self.grid_origin.y - position.y * self.pixels_per_cm_y
        
        # Get current orientation (already calibrated)
        current_orientation = self.demo_moving_object['orientation'] if self.demo_moving_object['enabled'] else self.moving_object_orientation
        
        if self.car_image:
            # Rotate the car image based on orientation
            # 0° = no rotation (car points up), positive angles = clockwise rotation
            # pygame.transform.rotate rotates counterclockwise, so we negate for clockwise
            rotated_car = pygame.transform.rotate(self.car_image, -current_orientation)
            
            # Get the rotated image rect and center it on the position
            car_rect = rotated_car.get_rect()
            car_rect.center = (int(x), int(y))
            
            # Draw the rotated car
            self.screen.blit(rotated_car, car_rect)
        else:
            # Fallback to arrow if car image failed to load
            arrow_length = 30
            
            # Calculate arrow end point (0° = up, positive = clockwise)
            angle_rad = math.radians(current_orientation - 90)  # Convert to math coordinates
            end_x = x + arrow_length * math.cos(angle_rad)
            end_y = y - arrow_length * math.sin(angle_rad)
            
            # Draw arrow
            pygame.draw.line(self.screen, self.colors['orientation'], 
                            (int(x), int(y)), (int(end_x), int(end_y)), 3)
            
            # Arrowhead
            head_angle = 150  # degrees
            head_length = 10
            
            left_angle = angle_rad + math.radians(head_angle)
            left_x = end_x - head_length * math.cos(left_angle)
            left_y = end_y - head_length * math.sin(left_angle)
            
            right_angle = angle_rad - math.radians(head_angle)
            right_x = end_x - head_length * math.cos(right_angle)
            right_y = end_y - head_length * math.sin(right_angle)
            
            pygame.draw.polygon(self.screen, self.colors['orientation'], 
                              [(int(end_x), int(end_y)), 
                               (int(left_x), int(left_y)), 
                               (int(right_x), int(right_y))])
            
            # Object circle
            pygame.draw.circle(self.screen, self.colors['orientation'], 
                             (int(x), int(y)), 5)
    
    def _render_button(self, rect: pygame.Rect, key: str, text: str, color):
        """Render a button"""
        is_hovered = rect.collidepoint(self.mouse_pos)
        
        if is_hovered:
            hover_color = tuple(min(255, c + 20) for c in color)
            pygame.draw.rect(self.screen, hover_color, rect, border_radius=5)
        else:
            pygame.draw.rect(self.screen, color, rect, border_radius=5)
        
        pygame.draw.rect(self.screen, self.colors['border'], rect, 1, border_radius=5)
        
        # Text
        text_surface, text_rect = self.fonts['body'].render(text, self.colors['text'])
        text_rect.center = rect.center
        self.screen.blit(text_surface, text_rect)
        
        self.button_rects[key] = rect
    
    def handle_event(self, event: pygame.event.Event):
        """Handle events specific to the simulation page"""
        if event.type == pygame.MOUSEMOTION:
            self.mouse_pos = event.pos
            
            # Check if mouse is over a sensor node or in placement mode (for cursor feedback)
            if not self.dragging_node and event.pos[0] > self.left_width + 20:
                mouse_over_node = False
                sensor_devices = [device for device in self.device_manager.devices.values() 
                                if device.device_type != "moving_object"]
                
                for node_id, node in self.sensor_nodes.items():
                    if any(device.device_id == node_id for device in sensor_devices) or node_id.startswith('sensor_'):
                        node_x = self.grid_origin.x + node.position.x * self.pixels_per_cm_x
                        node_y = self.grid_origin.y - node.position.y * self.pixels_per_cm_y
                        distance = math.sqrt((event.pos[0] - node_x)**2 + (event.pos[1] - node_y)**2)
                        if distance < 25:
                            mouse_over_node = True
                            break
                
                # Set cursor based on current state
                if self.selected_node:
                    # A node is selected, show placement cursor
                    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_CROSSHAIR)
                elif mouse_over_node:
                    # Mouse over a selectable node
                    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
                else:
                    # Normal cursor
                    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
            
            # Handle node dragging
            if self.dragging_node:
                # Only allow dragging within the simulation grid area (not in left panel)
                if event.pos[0] > self.left_width + 20:  # Ensure mouse is in simulation area with buffer
                    # Convert mouse position to grid coordinates with INDEPENDENT X/Y scaling
                    grid_x = (event.pos[0] - self.grid_origin.x) / self.pixels_per_cm_x
                    grid_y = (self.grid_origin.y - event.pos[1]) / self.pixels_per_cm_y
                    
                    # Add margin from edges to keep nodes fully visible
                    margin = 10  # 10cm margin from edges for better visibility
                    grid_x = max(margin, min(grid_x, self.grid_range_x - margin))
                    grid_y = max(margin, min(grid_y, self.grid_range_y - margin))
                    
                    if self.dragging_node in self.sensor_nodes:
                        self.sensor_nodes[self.dragging_node].position = Point2D(grid_x, grid_y)
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                # Check checkboxes
                for key, rect in self.checkbox_rects.items():
                    if rect.collidepoint(event.pos):
                        if key == 'show_grid':
                            self.show_grid = not self.show_grid
                        elif key == 'show_circles':
                            self.show_circles = not self.show_circles
                        elif key == 'show_triangle':
                            self.show_triangle = not self.show_triangle
                        elif key == 'show_orientation':
                            self.show_orientation = not self.show_orientation
                        return
                
                # Check buttons
                if 'recalibrate' in self.button_rects and self.button_rects['recalibrate'].collidepoint(event.pos):
                    print(f"🔄 RECALIBRATE button clicked!")
                    
                    # Reset orientation to up direction (0 degrees)
                    if self.demo_moving_object['enabled']:
                        print(f"📐 Recalibrating DEMO mode: setting demo orientation to 0°")
                        self.demo_moving_object['orientation'] = 0.0
                        print(f"✅ Demo orientation reset to: {self.demo_moving_object['orientation']}°")
                    else:
                        # For real device, set offset to make current RAW orientation appear as 0 degrees
                        old_offset = self.orientation_offset
                        self.orientation_offset = -self.raw_moving_object_orientation
                        
                        # Immediately update the calibrated orientation
                        self.moving_object_orientation = (self.raw_moving_object_orientation + self.orientation_offset) % 360
                        
                        print(f"📐 Recalibrating REAL device mode:")
                        print(f"   Current raw orientation: {self.raw_moving_object_orientation:.1f}°")
                        print(f"   Old offset: {old_offset:.1f}°")
                        print(f"   New offset: {self.orientation_offset:.1f}°")
                        print(f"   Calibrated result: {self.moving_object_orientation:.1f}°")
                    return
                
                # Toggle demo button
                if 'toggle_demo' in self.button_rects and self.button_rects['toggle_demo'].collidepoint(event.pos):
                    self.demo_moving_object['enabled'] = not self.demo_moving_object['enabled']
                    if self.demo_moving_object['enabled']:
                        # Start demo at a position that makes sense for the sensor configuration
                        # Try to start near where the circles would intersect
                        sensor_devices = [device for device in self.device_manager.devices.values() 
                                        if device.device_type != "moving_object"]
                        
                        if len(sensor_devices) >= 3 and all(device.device_id in self.sensor_nodes for device in sensor_devices[:3]):
                            # Get first 3 sensor positions
                            s1 = self.sensor_nodes[sensor_devices[0].device_id].position
                            s2 = self.sensor_nodes[sensor_devices[1].device_id].position
                            s3 = self.sensor_nodes[sensor_devices[2].device_id].position
                            
                            # Start at weighted center, slightly offset toward the middle
                            center_x = (s1.x + s2.x + s3.x) / 3
                            center_y = (s1.y + s2.y + s3.y) / 3
                            
                            # Move slightly toward grid center for better initial position
                            grid_center_x = self.grid_range_x / 2
                            grid_center_y = self.grid_range_y / 2
                            
                            start_x = center_x * 0.7 + grid_center_x * 0.3
                            start_y = center_y * 0.7 + grid_center_y * 0.3
                            
                            self.demo_moving_object['position'] = Point2D(start_x, start_y)
                        else:
                            # Default to center of grid
                            self.demo_moving_object['position'] = Point2D(self.grid_range_x / 2, self.grid_range_y / 2)
                        
                        self.demo_moving_object['orientation'] = 0.0  # Up direction (0° = north/up)
                        print(f"Demo started at position: ({self.demo_moving_object['position'].x:.1f}, {self.demo_moving_object['position'].y:.1f})")
                    return
                
                # Toggle distance mode button
                if 'toggle_distance_mode' in self.button_rects and self.button_rects['toggle_distance_mode'].collidepoint(event.pos):
                    if self.demo_moving_object['enabled']:
                        if self.demo_moving_object['distance_mode'] == 'auto':
                            self.demo_moving_object['distance_mode'] = 'manual'
                            # Initialize manual distances if not already set (only for sensor devices)
                            sensor_devices = [device for device in self.device_manager.devices.values() 
                                            if device.device_type != "moving_object"]
                            for device in sensor_devices:
                                device_id = device.device_id
                                if device_id not in self.demo_moving_object['manual_distances']:
                                    # Use current auto distance as initial manual distance
                                    if device_id in self.sensor_nodes:
                                        auto_dist = self.demo_moving_object['position'].distance_to(self.sensor_nodes[device_id].position)
                                        self.demo_moving_object['manual_distances'][device_id] = auto_dist
                                    else:
                                        self.demo_moving_object['manual_distances'][device_id] = 100.0
                        else:
                            self.demo_moving_object['distance_mode'] = 'auto'
                        print(f"Distance mode switched to: {self.demo_moving_object['distance_mode']}")
                    return
                
                # Individual sensor distance adjustment buttons (only for sensor devices)
                sensor_devices = [device for device in self.device_manager.devices.values() 
                                if device.device_type != "moving_object"]
                for device in sensor_devices:
                    device_id = device.device_id
                    minus_btn_key = f"dist_minus_{device_id}"
                    plus_btn_key = f"dist_plus_{device_id}"
                    
                    if minus_btn_key in self.button_rects and self.button_rects[minus_btn_key].collidepoint(event.pos):
                        if self.demo_moving_object['enabled'] and self.demo_moving_object['distance_mode'] == 'manual':
                            current_dist = self.demo_moving_object['manual_distances'].get(device_id, 100.0)
                            new_dist = max(10, current_dist - 10)
                            self.demo_moving_object['manual_distances'][device_id] = new_dist
                            print(f"Manual distance for {device_id} decreased to: {new_dist}")
                        return
                    
                    if plus_btn_key in self.button_rects and self.button_rects[plus_btn_key].collidepoint(event.pos):
                        if self.demo_moving_object['enabled'] and self.demo_moving_object['distance_mode'] == 'manual':
                            current_dist = self.demo_moving_object['manual_distances'].get(device_id, 100.0)
                            new_dist = min(500, current_dist + 10)
                            self.demo_moving_object['manual_distances'][device_id] = new_dist
                            print(f"Manual distance for {device_id} increased to: {new_dist}")
                        return
                
                # Orientation widget click - allows manual orientation control
                if 'orientation_widget' in self.button_rects and self.button_rects['orientation_widget'].collidepoint(event.pos):
                    # Calculate angle from click position relative to widget center
                    widget_rect = self.button_rects['orientation_widget']
                    center_x = widget_rect.centerx
                    center_y = widget_rect.centery
                    
                    # Calculate angle from center to click point
                    dx = event.pos[0] - center_x
                    dy = event.pos[1] - center_y
                    
                    # Convert to degrees with proper coordinate system
                    # In pygame: positive x = right, positive y = down
                    # We want: 0° = up (north), 90° = right, 180° = down, 270° = left
                    angle_rad = math.atan2(-dy, dx)  # Negate dy to flip y-axis
                    angle_deg = math.degrees(angle_rad)
                    
                    # Adjust so 0° is up (north)
                    orientation = (angle_deg + 90) % 360
                    
                    if self.demo_moving_object['enabled']:
                        self.demo_moving_object['orientation'] = orientation
                        print(f"Demo orientation set to: {orientation:.1f}°")
                    else:
                        self.moving_object_orientation = orientation
                        print(f"Moving object orientation set to: {orientation:.1f}°")
                    return
                
                # Edit grid range button
                if 'edit_grid_range' in self.button_rects and self.button_rects['edit_grid_range'].collidepoint(event.pos):
                    editor = GridRangeEditor(self.screen, self.grid_range_x, self.grid_range_y)
                    result = editor.run()
                    if result:
                        self.grid_range_x, self.grid_range_y = result
                        print(f"Grid range updated to: {self.grid_range_x} x {self.grid_range_y}")
                    return
                
                # Edit coordinates buttons for sensor nodes (only for sensor devices)
                sensor_devices = [device for device in self.device_manager.devices.values() 
                                if device.device_type != "moving_object"]
                for device in sensor_devices:
                    device_id = device.device_id
                    edit_btn_key = f"edit_coords_{device_id}"
                    if edit_btn_key in self.button_rects and self.button_rects[edit_btn_key].collidepoint(event.pos):
                        current_node = self.sensor_nodes.get(device_id)
                        if current_node:
                            editor = CoordinateEditor(
                                self.screen, 
                                device.device_name,
                                current_node.position.x,
                                current_node.position.y,
                                self.grid_range_x,
                                self.grid_range_y
                            )
                            result = editor.run()
                            if result:
                                new_x, new_y = result
                                current_node.position = Point2D(new_x, new_y)
                                print(f"Coordinates updated for {device.device_name}: ({new_x:.1f}, {new_y:.1f})")
                        return
                
                # Handle click-to-select and click-to-place for sensor nodes
                if event.pos[0] > self.left_width + 20:  # Only check if clicking on simulation grid area with buffer
                    # Only allow interaction with sensor nodes (not moving objects)
                    sensor_devices = [device for device in self.device_manager.devices.values() 
                                    if device.device_type != "moving_object"]
                    
                    # Check if clicking on a sensor node
                    clicked_node = None
                    for node_id, node in self.sensor_nodes.items():
                        # Only allow interaction if this is actually a sensor node
                        if any(device.device_id == node_id for device in sensor_devices) or node_id.startswith('sensor_'):
                            # Convert node position to screen coordinates using INDEPENDENT X/Y scaling
                            node_x = self.grid_origin.x + node.position.x * self.pixels_per_cm_x
                            node_y = self.grid_origin.y - node.position.y * self.pixels_per_cm_y
                            
                            # Check if click is within sensor node radius
                            distance = math.sqrt((event.pos[0] - node_x)**2 + (event.pos[1] - node_y)**2)
                            if distance < 25:  # 25 pixel radius for easier clicking
                                clicked_node = node_id
                                break
                    
                    if clicked_node:
                        # Clicked on a sensor node
                        if self.selected_node == clicked_node:
                            # Clicking on already selected node - deselect it
                            self.selected_node = None
                            print(f"🔄 Deselected sensor node: {clicked_node}")
                        else:
                            # Select the clicked node
                            self.selected_node = clicked_node
                            print(f"✅ Selected sensor node: {clicked_node} for repositioning")
                        return
                    else:
                        # Clicked on empty grid space
                        if self.selected_node:
                            # Move the selected node to the clicked position
                            # Convert mouse position to grid coordinates with INDEPENDENT X/Y scaling
                            grid_x = (event.pos[0] - self.grid_origin.x) / self.pixels_per_cm_x
                            grid_y = (self.grid_origin.y - event.pos[1]) / self.pixels_per_cm_y
                            
                            # Add margin from edges to keep nodes fully visible - MUCH SMALLER MARGIN
                            margin = 5  # 5cm margin from edges - reduce from 10cm
                            grid_x = max(margin, min(grid_x, self.grid_range_x - margin))
                            grid_y = max(margin, min(grid_y, self.grid_range_y - margin))
                            
                            # Update the selected node's position
                            old_pos = self.sensor_nodes[self.selected_node].position
                            self.sensor_nodes[self.selected_node].position = Point2D(grid_x, grid_y)
                            
                            print(f"📍 Moved sensor node {self.selected_node}: ({old_pos.x:.1f}, {old_pos.y:.1f}) → ({grid_x:.1f}, {grid_y:.1f})")
                            
                            # Clear selection after successful placement
                            self.selected_node = None
                            return
                
        
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                if self.dragging_node:
                    # Update completed - show new position
                    node = self.sensor_nodes[self.dragging_node]
                    print(f"✅ Sensor node {self.dragging_node} moved to: ({node.position.x:.1f}, {node.position.y:.1f})")
                    
                    # Ensure the node stays within boundaries with better margin
                    margin = 10  # 10cm margin for better visibility
                    if (node.position.x < margin or node.position.x > self.grid_range_x - margin or 
                        node.position.y < margin or node.position.y > self.grid_range_y - margin):
                        print(f"⚠️ Node position adjusted to stay within boundaries")
                        node.position.x = max(margin, min(node.position.x, self.grid_range_x - margin))
                        node.position.y = max(margin, min(node.position.y, self.grid_range_y - margin))
                        print(f"📍 Final position after boundary adjustment: ({node.position.x:.1f}, {node.position.y:.1f})")
                
                # Reset cursor after dragging
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
                self.dragging_node = None
        
        elif event.type == pygame.KEYDOWN:
            print(f"Simulation page received key event: {pygame.key.name(event.key)}")
            print(f"Demo moving object enabled: {self.demo_moving_object['enabled']}")
            
            # Handle escape key to deselect sensor node
            if event.key == pygame.K_ESCAPE:
                if self.selected_node:
                    print(f"🔄 Deselected sensor node: {self.selected_node} (Escape key)")
                    self.selected_node = None
                    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
                    return
            
            # Handle demo moving object controls (always check, regardless of UI state)
            if self.demo_moving_object['enabled']:
                if event.key == pygame.K_LEFT:
                    # Left arrow = counterclockwise = positive degrees
                    self.demo_moving_object['orientation'] = (self.demo_moving_object['orientation'] + 15) % 360
                    print(f"Left arrow pressed (counterclockwise +15°), new orientation: {self.demo_moving_object['orientation']}°")
                elif event.key == pygame.K_RIGHT:
                    # Right arrow = clockwise = negative degrees (but stored as 0-360)
                    self.demo_moving_object['orientation'] = (self.demo_moving_object['orientation'] - 15) % 360
                    print(f"Right arrow pressed (clockwise -15°), new orientation: {self.demo_moving_object['orientation']}°")
                elif event.key == pygame.K_UP:
                    # Move forward in the direction the object is facing
                    # Use the same angle calculation as the arrow display
                    angle_rad = math.radians(self.demo_moving_object['orientation'] - 90)
                    new_x = self.demo_moving_object['position'].x + 10 * math.cos(angle_rad)
                    new_y = self.demo_moving_object['position'].y - 10 * math.sin(angle_rad)  # Negate for grid coordinate system
                    
                    # Clamp to grid bounds
                    new_x = max(10, min(new_x, self.grid_range_x - 10))
                    new_y = max(10, min(new_y, self.grid_range_y - 10))
                    
                    self.demo_moving_object['position'] = Point2D(new_x, new_y)
                    print(f"Moved forward to: ({new_x:.1f}, {new_y:.1f})")
                elif event.key == pygame.K_DOWN:
                    # Move backward (opposite direction)
                    # Use the same angle calculation as the arrow display, but add 180°
                    angle_rad = math.radians(self.demo_moving_object['orientation'] - 90 + 180)
                    new_x = self.demo_moving_object['position'].x + 10 * math.cos(angle_rad)
                    new_y = self.demo_moving_object['position'].y - 10 * math.sin(angle_rad)  # Negate for grid coordinate system
                    
                    # Clamp to grid bounds
                    new_x = max(10, min(new_x, self.grid_range_x - 10))
                    new_y = max(10, min(new_y, self.grid_range_y - 10))
                    
                    self.demo_moving_object['position'] = Point2D(new_x, new_y)
                    print(f"Moved backward to: ({new_x:.1f}, {new_y:.1f})")
    
    def update_real_moving_object_orientation(self, orientation: float):
        """Update real moving object orientation from Bluetooth device data"""
        # Store raw orientation
        self.raw_moving_object_orientation = orientation
        
        # Apply orientation offset for recalibration
        calibrated_orientation = (orientation + self.orientation_offset) % 360
        
        # Update the moving object orientation for display
        self.moving_object_orientation = calibrated_orientation
        
        print(f"🧭 Real moving object orientation updated: raw={orientation:.1f}°, offset={self.orientation_offset:.1f}°, calibrated={calibrated_orientation:.1f}°")
    
    def update(self, dt: float):
        """Update simulation state"""
        # Update sensor node distances from device manager
        for node_id, node in self.sensor_nodes.items():
            if node_id in self.device_manager.devices:
                device = self.device_manager.devices[node_id]
                node.current_distance = device.last_distance
        
        # Update moving object orientation if we have a connected device
        if self.moving_object_device and self.moving_object_device in self.device_manager.devices:
            device = self.device_manager.devices[self.moving_object_device]
            # The orientation data would come from the device
            # For now, we simulate it
            self.moving_object_orientation += dt * 10  # Rotate 10 degrees per second
            self.moving_object_orientation %= 360
        
        # Update demo moving object if enabled
        if self.demo_moving_object['enabled']:
            # Keep current demo values (will be controlled by arrow keys)
            pass
    
    def update_settings(self, distance_settings: Dict):
        """Update grid settings"""
        self.max_distance = distance_settings.get('max_distance', 200)
        # Update grid ranges if provided
        if 'grid_range_x' in distance_settings:
            self.grid_range_x = distance_settings['grid_range_x']
        if 'grid_range_y' in distance_settings:
            self.grid_range_y = distance_settings['grid_range_y']
    
    def handle_click(self, pos: Tuple[int, int]):
        """Handle click events - compatibility wrapper for UI manager"""
        # Create a mock pygame event for compatibility with handle_event
        class MockEvent:
            def __init__(self, pos):
                self.type = pygame.MOUSEBUTTONDOWN
                self.button = 1
                self.pos = pos
        
        self.handle_event(MockEvent(pos))