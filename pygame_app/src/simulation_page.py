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
        self.show_excircle = True
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
            'excircle': (180, 80, 180),
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
        section_height = 190
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
            ('show_excircle', 'Excircle', self.show_excircle),
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
            # Show all devices, no artificial limit
            # if y_pos + 80 > rect.bottom - 130:  # Reserve space for moving object status
            #     break
            
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
            
            # Perform trilateration directly - no throttling
            result = self._perform_trilateration(nodes, distances, force_log=True)
            if result:
                # Use the optimized position calculated by trilateration method
                # This is already the best position found by the minimum area triangle optimization
                self.moving_object_position = result['position']
                
                # Draw visualization layers
                if self.show_circles:
                    self._draw_distance_circles(nodes, distances)
                
                if self.show_triangle and 'triangle' in result and result['triangle'] is not None:
                    self._draw_triangle_of_interest(result['triangle'])
                
                if self.show_excircle and 'excircle' in result:
                    self._draw_approx_circle(result['excircle'])
                
                # Draw estimated car with physical dimensions (includes orientation)
                if 'car_dimensions' in result:
                    self._draw_estimated_car(self.moving_object_position, result['car_dimensions'])
                elif self.show_orientation and self.moving_object_position:
                    # Fallback: draw simple orientation if no car dimensions available
                    self._draw_orientation(self.moving_object_position)
        
        # Note: Demo moving object is no longer drawn on the simulation graph
        # It's only shown in the bottom left status section
    
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
                    
                    # Clipping will be done manually without creating a rect
                    
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
    
    def _perform_trilateration(self, nodes: List[SensorNode], distances: List[float], force_log: bool = False) -> Optional[Dict]:
        """
        ENHANCED MINIMUM AREA TRIANGLE ALGORITHM:
        1. Adaptive sampling based on circle proximity
        2. Physics-based constraint validation  
        3. Multi-objective optimization (area + feasibility)
        4. Robust handling of overlapping circles
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
        
        if force_log:
            print(f"🔧 Enhanced Minimum Area Triangle Algorithm")
            print(f"📍 Distance circles:")
            print(f"   Circle 1: center=({p1.position.x:.1f}, {p1.position.y:.1f}), radius={r1:.1f}cm")
            print(f"   Circle 2: center=({p2.position.x:.1f}, {p2.position.y:.1f}), radius={r2:.1f}cm")
            print(f"   Circle 3: center=({p3.position.x:.1f}, {p3.position.y:.1f}), radius={r3:.1f}cm")
            print(f"🚗 Car dimensions: {CAR_LENGTH}×{CAR_WIDTH}cm (radius: {CAR_RADIUS:.1f}cm)")
        
        # Adaptive sampling based on circle proximity and sizes
        base_samples = 16  # Minimum samples per circle
        proximity_factor = self._calculate_circle_proximity_factor(
            [(p1.position, r1), (p2.position, r2), (p3.position, r3)]
        )
        adaptive_samples = max(base_samples, min(32, int(base_samples * proximity_factor)))
        
        if force_log:
            print(f"📊 Adaptive sampling: {adaptive_samples} points per circle (proximity factor: {proximity_factor:.2f})")
        
        # Sample points on each distance circle perimeter
        circle1_points = self._sample_circle_points(p1.position, r1, adaptive_samples)
        circle2_points = self._sample_circle_points(p2.position, r2, adaptive_samples)  
        circle3_points = self._sample_circle_points(p3.position, r3, adaptive_samples)
        
        # Enhanced triangle evaluation with multiple criteria
        best_result = {
            'triangle': None,
            'area': float('inf'),
            'score': float('-inf'),  # Combined score
            'car_center': None
        }
        
        tested_combinations = 0
        max_combinations = 8000  # Performance limit
        
        if force_log:
            total_possible = len(circle1_points) * len(circle2_points) * len(circle3_points)
            print(f"🔍 Testing up to {min(total_possible, max_combinations)} combinations...")
        
        # Try all combinations with early termination
        for p1_point in circle1_points:
            for p2_point in circle2_points:
                for p3_point in circle3_points:
                    tested_combinations += 1
                    if tested_combinations > max_combinations:
                        break
                        
                    # Calculate triangle properties
                    triangle_vertices = [p1_point, p2_point, p3_point]
                    area = self._triangle_area(p1_point, p2_point, p3_point)
                    
                    # Skip degenerate triangles
                    if area < 10.0:  # Reduced minimum area for demo mode
                        continue
                    
                    # Calculate potential car center (triangle centroid)
                    car_center = Point2D(
                        sum(p.x for p in triangle_vertices) / 3,
                        sum(p.y for p in triangle_vertices) / 3
                    )
                    
                    # Physics-based constraint validation (more lenient for demo)
                    if not self._is_valid_car_position(car_center, 
                                                     [(p1.position, r1), (p2.position, r2), (p3.position, r3)], 
                                                     CAR_RADIUS, tolerance=10.0):  # Increased tolerance
                        continue
                    
                    # Multi-objective scoring
                    score = self._calculate_triangle_score(triangle_vertices, car_center, area, 
                                                         [(p1.position, r1), (p2.position, r2), (p3.position, r3)])
                    
                    # Update best solution
                    if score > best_result['score']:
                        best_result.update({
                            'triangle': triangle_vertices,
                            'area': area,
                            'score': score,
                            'car_center': car_center
                        })
                        
                        # Early termination for excellent solutions
                        if area < 100.0 and score > 0.9:  # Very good solution
                            if force_log:
                                print(f"⚡ Early termination: excellent solution found (area: {area:.1f}cm², score: {score:.3f})")
                            break
                if tested_combinations > max_combinations:
                    break
            if tested_combinations > max_combinations or (best_result['triangle'] and best_result['area'] < 100.0):
                break
        
        # Process best solution
        if best_result['triangle']:
            triangle = best_result['triangle']
            car_center = best_result['car_center']
            area = best_result['area']
            score = best_result['score']
            
            # Calculate excircle for visualization
            excircle = self._calculate_excircle(triangle)
            
            if force_log:
                print(f"✅ Enhanced algorithm found optimal triangle")
                print(f"🎯 Triangle area: {area:.2f} cm² (score: {score:.3f})")
                print(f"🚗 Car center: ({car_center.x:.1f}, {car_center.y:.1f})")
                print(f"� Tested {tested_combinations} combinations")
                print(f"� Triangle vertices:")
                for i, vertex in enumerate(triangle, 1):
                    print(f"   P{i}: ({vertex.x:.1f}, {vertex.y:.1f})")
            
            # Verify vertices are on circle perimeters (enhanced validation)
            sensors = [(p1.position, r1), (p2.position, r2), (p3.position, r3)]
            for i, (vertex, (sensor_pos, radius)) in enumerate(zip(triangle, sensors), 1):
                dist_to_sensor = vertex.distance_to(sensor_pos)
                error = abs(dist_to_sensor - radius)
                status = "✅" if error <= 2.0 else "⚠️"
                if force_log:
                    print(f"   {status} P{i} distance to sensor: {dist_to_sensor:.2f}cm (target: {radius:.2f}cm, error: {error:.2f}cm)")
            
            if excircle and force_log:
                print(f"   Excircle: center=({excircle['center'].x:.1f}, {excircle['center'].y:.1f}), radius={excircle['radius']:.1f}cm")
            
            return {
                'position': car_center,
                'triangle': triangle,
                'excircle': excircle,
                'algorithm_info': {
                    'type': 'enhanced_minimum_area',
                    'area': area,
                    'score': score,
                    'samples_per_circle': adaptive_samples,
                    'combinations_tested': tested_combinations
                },
                'car_dimensions': {'length': CAR_LENGTH, 'width': CAR_WIDTH, 'radius': CAR_RADIUS}
            }
        else:
            if force_log:
                print(f"❌ Enhanced algorithm found no valid solution - using fallback")
                print(f"   Tested {tested_combinations} combinations")
            
            # Fallback: use geometric center with physics validation
            center_x = (p1.position.x + p2.position.x + p3.position.x) / 3
            center_y = (p1.position.y + p2.position.y + p3.position.y) / 3
            fallback_position = Point2D(center_x, center_y)
            
            return {
                'position': fallback_position,
                'triangle': None,
                'excircle': None,
                'car_dimensions': {'length': CAR_LENGTH, 'width': CAR_WIDTH, 'radius': CAR_RADIUS}
            }
    
    def _calculate_circle_proximity_factor(self, circles: List[tuple]) -> float:
        """
        Calculate proximity factor for adaptive sampling.
        Returns higher value when circles are closer together.
        """
        proximities = []
        for i in range(len(circles)):
            for j in range(i + 1, len(circles)):
                center1, r1 = circles[i]
                center2, r2 = circles[j]
                
                # Distance between centers
                center_dist = center1.distance_to(center2)
                
                # Normalized proximity (closer = higher value)
                # If circles overlap significantly, increase sampling
                if center_dist < (r1 + r2):  # Overlapping or touching
                    proximity = 2.0 + (r1 + r2 - center_dist) / max(r1, r2)
                else:
                    proximity = max(0.5, (r1 + r2) / center_dist)
                
                proximities.append(proximity)
        
        return max(1.0, sum(proximities) / len(proximities))
    
    def _is_valid_car_position(self, car_center: Point2D, sensor_distances: List[tuple], 
                              car_radius: float, tolerance: float = 3.0) -> bool:
        """
        Physics-based validation for car position.
        Checks if the car can physically exist at this position given sensor measurements.
        """
        for sensor_pos, measured_distance in sensor_distances:
            # Distance from car center to sensor
            actual_distance = car_center.distance_to(sensor_pos)
            
            # For a car with radius car_radius, the sensor should measure
            # somewhere between (actual_distance - car_radius) and (actual_distance + car_radius)
            min_expected = max(0, actual_distance - car_radius - tolerance)
            max_expected = actual_distance + car_radius + tolerance
            
            # Check if measured distance is within expected range
            if not (min_expected <= measured_distance <= max_expected):
                return False
        
        return True
    
    def _calculate_triangle_score(self, triangle: List[Point2D], car_center: Point2D, 
                                area: float, sensor_distances: List[tuple]) -> float:
        """
        Multi-objective scoring for triangle quality.
        Higher score = better triangle.
        """
        # Base score from area (smaller area is better)
        area_score = max(0, 1.0 - area / 1000.0)  # Normalize to 0-1 range
        
        # Physics consistency score
        physics_score = 1.0
        for sensor_pos, measured_distance in sensor_distances:
            actual_distance = car_center.distance_to(sensor_pos)
            error = abs(actual_distance - measured_distance)
            physics_score *= max(0.1, 1.0 - error / 50.0)  # Penalize large errors
        
        # Triangle regularity score (more regular = better)
        side_lengths = [
            triangle[0].distance_to(triangle[1]),
            triangle[1].distance_to(triangle[2]),
            triangle[2].distance_to(triangle[0])
        ]
        max_side = max(side_lengths)
        min_side = min(side_lengths)
        regularity_score = min_side / max_side if max_side > 0 else 0
        
        # Combined score with weights
        combined_score = (0.4 * area_score + 
                         0.4 * physics_score + 
                         0.2 * regularity_score)
        
        return combined_score
    
    def _find_outer_tangent_circle(self, c1: Point2D, r1: float, c2: Point2D, r2: float, c3: Point2D, r3: float) -> Optional[Dict]:
        """
        Find the outer tangent circle using a geometric optimization approach.
        This is more robust than Descartes Circle Theorem for practical cases.
        """
        try:
            # Check for zero or negative radii
            if r1 <= 0 or r2 <= 0 or r3 <= 0:
                return None
            
            # Simple approach: Use circumcircle of sensor positions and expand outward
            # This will give us a reasonable approximation of the outer tangent circle
            
            # Calculate circumcenter of the three sensor nodes
            d = 2 * (c1.x * (c2.y - c3.y) + c2.x * (c3.y - c1.y) + c3.x * (c1.y - c2.y))
            
            if abs(d) < 1e-10:  # Collinear points
                return None
                
            ux = ((c1.x*c1.x + c1.y*c1.y) * (c2.y - c3.y) + 
                  (c2.x*c2.x + c2.y*c2.y) * (c3.y - c1.y) + 
                  (c3.x*c3.x + c3.y*c3.y) * (c1.y - c2.y)) / d
            
            uy = ((c1.x*c1.x + c1.y*c1.y) * (c3.x - c2.x) + 
                  (c2.x*c2.x + c2.y*c2.y) * (c1.x - c3.x) + 
                  (c3.x*c3.x + c3.y*c3.y) * (c2.x - c1.x)) / d
            
            circumcenter = Point2D(ux, uy)
            
            # Calculate distances from circumcenter to each circle center
            dist_to_c1 = circumcenter.distance_to(c1)
            dist_to_c2 = circumcenter.distance_to(c2)
            dist_to_c3 = circumcenter.distance_to(c3)
            
            # The key insight: for an outer tangent circle, we need a much larger radius
            # The outer tangent circle should encompass all the distance circles
            
            # Method 1: Try to use circumcenter if it's outside all circles
            all_outside = (dist_to_c1 > r1 and dist_to_c2 > r2 and dist_to_c3 > r3)
            
            # FIXED: Proper outer radius calculation using bounding box approach
            # Calculate the bounding box of all circles (including their radii)
            min_x = min(c1.x - r1, c2.x - r2, c3.x - r3)
            max_x = max(c1.x + r1, c2.x + r2, c3.x + r3)
            min_y = min(c1.y - r1, c2.y - r2, c3.y - r3)
            max_y = max(c1.y + r1, c2.y + r2, c3.y + r3)
            
            # Calculate the diagonal of the bounding box
            bbox_width = max_x - min_x
            bbox_height = max_y - min_y
            bbox_diagonal = math.sqrt(bbox_width**2 + bbox_height**2)
            
            # Use the circumcenter if it's reasonable, otherwise use bounding box center
            center = circumcenter
            
            if all_outside:
                # Good case: circumcenter is outside all circles
                required_radii = [
                    dist_to_c1 - r1,  # Radius needed for external tangency with circle 1
                    dist_to_c2 - r2,  # Radius needed for external tangency with circle 2  
                    dist_to_c3 - r3   # Radius needed for external tangency with circle 3
                ]
                # Use the maximum to ensure external tangency with all circles
                outer_radius = max(required_radii) + 5.0  # Add 5cm margin
            else:
                # Fallback: circumcenter is inside some circles, use bounding box approach
                center = Point2D((min_x + max_x) / 2, (min_y + max_y) / 2)
                
                # Calculate radius needed to encompass all circles from bounding box center
                dist_to_c1_new = center.distance_to(c1)
                dist_to_c2_new = center.distance_to(c2)
                dist_to_c3_new = center.distance_to(c3)
                
                required_radii = [
                    dist_to_c1_new + r1 + 10,  # Ensure we're outside circle 1 with 10cm margin
                    dist_to_c2_new + r2 + 10,  # Ensure we're outside circle 2 with 10cm margin
                    dist_to_c3_new + r3 + 10   # Ensure we're outside circle 3 with 10cm margin
                ]
                
                outer_radius = max(required_radii)
            
            # Ensure minimum reasonable radius
            outer_radius = max(outer_radius, bbox_diagonal / 2)
            
            # Verify the solution by checking distances
            dist1 = center.distance_to(c1)
            dist2 = center.distance_to(c2)
            dist3 = center.distance_to(c3)
            
            expected_dist1 = outer_radius + r1
            expected_dist2 = outer_radius + r2  
            expected_dist3 = outer_radius + r3
            
            # Use a reasonable tolerance (20cm) for this approximation method
            tolerance = 20.0
            
            # Check if the solution is reasonable (not necessarily perfect)
            reasonable = (
                abs(dist1 - expected_dist1) < tolerance and 
                abs(dist2 - expected_dist2) < tolerance and
                abs(dist3 - expected_dist3) < tolerance
            )
            
            if reasonable or outer_radius > bbox_diagonal / 3:  # Accept if reasonable or large enough
                return {
                    'center': center,
                    'radius': outer_radius
                }
            
            return None
            
        except (ZeroDivisionError, ValueError, OverflowError):
            return None
    
    def _find_external_tangent_point(self, outer_center: Point2D, outer_radius: float, 
                                   circle_center: Point2D, circle_radius: float) -> Optional[Point2D]:
        """
        Find the point where the outer tangent circle touches a distance circle externally.
        """
        try:
            # Distance between centers
            distance = outer_center.distance_to(circle_center)
            
            if distance < 1e-6:  # Centers are too close
                return None
            
            # For external tangency, the tangent point lies on the line connecting the centers
            # Distance from circle center to tangent point equals the circle radius
            # Direction from outer center to circle center
            direction_x = (circle_center.x - outer_center.x) / distance
            direction_y = (circle_center.y - outer_center.y) / distance
            
            # Tangent point is circle_radius distance from circle center towards outer center
            tangent_x = circle_center.x - circle_radius * direction_x
            tangent_y = circle_center.y - circle_radius * direction_y
            
            return Point2D(tangent_x, tangent_y)
            
        except (ZeroDivisionError, ValueError):
            return None
    
    def _calculate_excircle(self, triangle_vertices: List[Point2D]) -> Optional[Dict]:
        """Calculate the excircle (circumcircle) of a triangle."""
        if len(triangle_vertices) != 3:
            return None
        
        p1, p2, p3 = triangle_vertices
        
        # Calculate circumcenter using the formula
        ax, ay = p1.x, p1.y
        bx, by = p2.x, p2.y
        cx, cy = p3.x, p3.y
        
        D = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
        
        if abs(D) < 1e-6:  # Degenerate triangle
            return None
        
        ux = ((ax*ax + ay*ay) * (by - cy) + (bx*bx + by*by) * (cy - ay) + (cx*cx + cy*cy) * (ay - by)) / D
        uy = ((ax*ax + ay*ay) * (cx - bx) + (bx*bx + by*by) * (ax - cx) + (cx*cx + cy*cy) * (bx - ax)) / D
        
        center = Point2D(ux, uy)
        radius = center.distance_to(p1)
        
        return {
            'center': center,
            'radius': radius
        }
    
    def _is_triangle_outside_circles(self, triangle_vertices: List[Point2D], sensor_positions: List[Point2D], radii: List[float]) -> bool:
        """Check if all triangle vertices are outside their respective distance circles."""
        if len(triangle_vertices) != 3 or len(sensor_positions) != 3 or len(radii) != 3:
            return False
        
        for i, vertex in enumerate(triangle_vertices):
            sensor_pos = sensor_positions[i]
            radius = radii[i]
            distance_to_sensor = vertex.distance_to(sensor_pos)
            
            # Vertex should be outside the distance circle (with small tolerance)
            if distance_to_sensor <= radius + 1.0:  # 1cm tolerance
                return False
        
        return True
    
    def _calculate_excircle(self, triangle_vertices: List[Point2D]) -> Optional[Dict]:
        """Calculate the excircle (circumcircle) of a triangle."""
        if len(triangle_vertices) != 3:
            return None
        
        p1, p2, p3 = triangle_vertices
        
        # Calculate circumcenter using the formula
        ax, ay = p1.x, p1.y
        bx, by = p2.x, p2.y
        cx, cy = p3.x, p3.y
        
        D = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
        
        if abs(D) < 1e-6:  # Degenerate triangle
            return None
        
        ux = ((ax*ax + ay*ay) * (by - cy) + (bx*bx + by*by) * (cy - ay) + (cx*cx + cy*cy) * (ay - by)) / D
        uy = ((ax*ax + ay*ay) * (cx - bx) + (bx*bx + by*by) * (ax - cx) + (cx*cx + cy*cy) * (bx - ax)) / D
        
        center = Point2D(ux, uy)
        radius = center.distance_to(p1)
        
        return {
            'center': center,
            'radius': radius
        }

    def _is_triangle_outside_circles(self, triangle_vertices: List[Point2D], sensor_positions: List[Point2D], radii: List[float]) -> bool:
        """Check if triangle is completely outside all distance circles"""
        for vertex in triangle_vertices:
            for sensor_pos, radius in zip(sensor_positions, radii):
                distance = vertex.distance_to(sensor_pos)
                if distance < radius:  # Vertex is inside a circle
                    return False
        return True
    
    def _sample_circle_points(self, center: Point2D, radius: float, num_samples: int = 24) -> List[Point2D]:
        """Sample points uniformly around a circle"""
        points = []
        for i in range(num_samples):
            angle = (2 * math.pi * i) / num_samples
            x = center.x + radius * math.cos(angle)
            y = center.y + radius * math.sin(angle)
            points.append(Point2D(x, y))
        return points
    
    def _find_optimal_car_position(self, triangle_vertices: List[Point2D], sensor_positions: List[Point2D], distances: List[float], car_radius: float) -> Optional[Point2D]:
        """
        Find the optimal car center position within a triangle that satisfies distance constraints.
        The car center must be at least (measured_distance + car_radius) from each sensor.
        """
        if len(triangle_vertices) != 3 or len(sensor_positions) != 3 or len(distances) != 3:
            return None
        
        # Start with triangle centroid as initial estimate
        centroid = Point2D(
            sum(p.x for p in triangle_vertices) / 3,
            sum(p.y for p in triangle_vertices) / 3
        )
        
        # Check if centroid satisfies distance constraints
        if self._verify_car_position(centroid, sensor_positions, distances, car_radius):
            return centroid
        
        # If centroid doesn't work, try to find a valid position within the triangle
        # Sample points within the triangle and find the one closest to centroid that satisfies constraints
        best_position = None
        min_distance_to_centroid = float('inf')
        
        # Generate candidate points within the triangle using barycentric coordinates
        for alpha in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
            for beta in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
                gamma = 1.0 - alpha - beta
                if gamma > 0:  # Valid barycentric coordinates
                    # Calculate point using barycentric coordinates
                    candidate = Point2D(
                        alpha * triangle_vertices[0].x + beta * triangle_vertices[1].x + gamma * triangle_vertices[2].x,
                        alpha * triangle_vertices[0].y + beta * triangle_vertices[1].y + gamma * triangle_vertices[2].y
                    )
                    
                    if self._verify_car_position(candidate, sensor_positions, distances, car_radius):
                        distance_to_centroid = candidate.distance_to(centroid)
                        if distance_to_centroid < min_distance_to_centroid:
                            min_distance_to_centroid = distance_to_centroid
                            best_position = candidate
        
        return best_position
    
    def _verify_car_position(self, car_center: Point2D, sensor_positions: List[Point2D], distances: List[float], car_radius: float) -> bool:
        """
        Verify that a car center position satisfies distance constraints.
        The car center must be at least (measured_distance + car_radius) from each sensor.
        """
        tolerance = 2.0  # 2cm tolerance
        
        for sensor_pos, measured_distance in zip(sensor_positions, distances):
            distance_to_sensor = car_center.distance_to(sensor_pos)
            required_distance = measured_distance + car_radius
            
            # Car center must be far enough from sensor
            if distance_to_sensor < required_distance - tolerance:
                return False
        
        return True
    
    def _adjust_center_for_constraints(self, initial_center: Point2D, sensor_positions: List[Point2D], distances: List[float], car_radius: float) -> Point2D:
        """
        Adjust an initial car center position to satisfy distance constraints.
        Move the center away from sensors that are too close.
        """
        adjusted_center = Point2D(initial_center.x, initial_center.y)
        max_iterations = 10
        
        for iteration in range(max_iterations):
            needs_adjustment = False
            total_adjustment_x = 0.0
            total_adjustment_y = 0.0
            
            for sensor_pos, measured_distance in zip(sensor_positions, distances):
                distance_to_sensor = adjusted_center.distance_to(sensor_pos)
                required_distance = measured_distance + car_radius
                
                if distance_to_sensor < required_distance:
                    needs_adjustment = True
                    
                    # Calculate adjustment vector (move away from sensor)
                    if distance_to_sensor > 0:
                        adjustment_magnitude = required_distance - distance_to_sensor + 5.0  # 5cm buffer
                        direction_x = (adjusted_center.x - sensor_pos.x) / distance_to_sensor
                        direction_y = (adjusted_center.y - sensor_pos.y) / distance_to_sensor
                        
                        total_adjustment_x += direction_x * adjustment_magnitude
                        total_adjustment_y += direction_y * adjustment_magnitude
            
            if not needs_adjustment:
                break
                
            # Apply adjustments
            adjusted_center = Point2D(
                adjusted_center.x + total_adjustment_x / len(sensor_positions),
                adjusted_center.y + total_adjustment_y / len(sensor_positions)
            )
        
        return adjusted_center
    
    def _triangle_fits_in_car(self, triangle_vertices: List[Point2D], car_center: Point2D, car_radius: float) -> bool:
        """
        Check if a triangle fits entirely within the car's boundaries.
        Since the car CONTAINS the triangle, all triangle vertices must be within car_radius of car_center.
        """
        if len(triangle_vertices) != 3:
            return False
        
        # Check that all triangle vertices are within the car's radius
        for vertex in triangle_vertices:
            distance_from_car_center = vertex.distance_to(car_center)
            if distance_from_car_center > car_radius:
                return False
        
        return True
    
    def _analytical_trilateration(self, p1: Point2D, r1: float, p2: Point2D, r2: float, p3: Point2D, r3: float) -> List[Point2D]:
        """
        Perform analytical trilateration to find intersection points of three circles.
        Returns a list of candidate positions where all three circles intersect.
        """
        try:
            # Convert to matrix form for solving the trilateration equations
            # Circle equations: (x-p1.x)² + (y-p1.y)² = r1²
            # Expanding and rearranging gives us a system of linear equations
            
            # Use the first circle as reference, solve relative to other two
            A = 2 * (p2.x - p1.x)
            B = 2 * (p2.y - p1.y)
            C = r1*r1 - r2*r2 - p1.x*p1.x + p2.x*p2.x - p1.y*p1.y + p2.y*p2.y
            
            D = 2 * (p3.x - p1.x)  
            E = 2 * (p3.y - p1.y)
            F = r1*r1 - r3*r3 - p1.x*p1.x + p3.x*p3.x - p1.y*p1.y + p3.y*p3.y
            
            # Solve the system: Ax + By = C, Dx + Ey = F
            denominator = A * E - B * D
            
            if abs(denominator) < 1e-10:
                # Lines are parallel, no unique solution
                return []
            
            x = (C * E - F * B) / denominator
            y = (A * F - D * C) / denominator
            
            # Verify this point is actually on all three circles (within tolerance)
            tolerance = 1.0  # cm
            solution = Point2D(x, y)
            
            dist1 = solution.distance_to(p1)
            dist2 = solution.distance_to(p2)
            dist3 = solution.distance_to(p3)
            
            if (abs(dist1 - r1) <= tolerance and 
                abs(dist2 - r2) <= tolerance and 
                abs(dist3 - r3) <= tolerance):
                return [solution]
            else:
                return []
                
        except Exception:
            return []
    
    def _circle_intersections(self, c1: Point2D, r1: float, c2: Point2D, r2: float) -> Optional[List[Point2D]]:
        """Find intersection points of two circles (legacy method, kept for reference)"""
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
    
    def _point_in_triangle(self, point: Point2D, p1: Point2D, p2: Point2D, p3: Point2D) -> bool:
        """Check if a point is inside a triangle using barycentric coordinates"""
        # Calculate vectors
        v0x, v0y = p3.x - p1.x, p3.y - p1.y
        v1x, v1y = p2.x - p1.x, p2.y - p1.y
        v2x, v2y = point.x - p1.x, point.y - p1.y
        
        # Calculate dot products
        dot00 = v0x * v0x + v0y * v0y
        dot01 = v0x * v1x + v0y * v1y
        dot02 = v0x * v2x + v0y * v2y
        dot11 = v1x * v1x + v1y * v1y
        dot12 = v1x * v2x + v1y * v2y
        
        # Calculate barycentric coordinates
        denom = dot00 * dot11 - dot01 * dot01
        if abs(denom) < 1e-10:  # Degenerate triangle
            return False
            
        inv_denom = 1.0 / denom
        u = (dot11 * dot02 - dot01 * dot12) * inv_denom
        v = (dot00 * dot12 - dot01 * dot02) * inv_denom
        
        # Check if point is in triangle
        return (u >= 0) and (v >= 0) and (u + v <= 1)
    
    def _calculate_excircle(self, triangle: List[Point2D]) -> Optional[Dict]:
        """Calculate the excircle (circumcircle) of a triangle with improved robustness"""
        if not triangle or len(triangle) != 3:
            return None
            
        p1, p2, p3 = triangle
        
        # Calculate circumcenter using more stable algorithm
        try:
            d = 2 * (p1.x * (p2.y - p3.y) + p2.x * (p3.y - p1.y) + p3.x * (p1.y - p2.y))
            
            # Check for degenerate triangle (collinear points)
            if abs(d) < 0.1:  # Increased threshold for practical stability
                return None
            
            ux = ((p1.x*p1.x + p1.y*p1.y) * (p2.y - p3.y) + 
                  (p2.x*p2.x + p2.y*p2.y) * (p3.y - p1.y) + 
                  (p3.x*p3.x + p3.y*p3.y) * (p1.y - p2.y)) / d
            
            uy = ((p1.x*p1.x + p1.y*p1.y) * (p3.x - p2.x) + 
                  (p2.x*p2.x + p2.y*p2.y) * (p1.x - p3.x) + 
                  (p3.x*p3.x + p3.y*p3.y) * (p2.x - p1.x)) / d
            
            center = Point2D(ux, uy)
            radius = center.distance_to(p1)
            
            # Sanity checks for reasonable excircle
            if radius > 1000 or radius <= 0:  # Very large or invalid radius
                return None
            
            # Check if center is too far from triangle vertices
            max_distance = max(center.distance_to(p1), center.distance_to(p2), center.distance_to(p3))
            if max_distance > 500:  # Center too far from triangle
                return None
            
            return {'center': center, 'radius': radius}
            
        except (ZeroDivisionError, ValueError, OverflowError):
            return None
    
    def _draw_triangle_of_interest(self, triangle: List[Point2D]):
        """Draw the support triangle (closest points on distance circles)"""
        if not triangle or len(triangle) < 3:
            return  # Quietly skip invalid triangles
        
        points = []
        for p in triangle:
            x = self.grid_origin.x + p.x * self.pixels_per_cm_x
            y = self.grid_origin.y - p.y * self.pixels_per_cm_y
            points.append((int(x), int(y)))
        
        if len(points) >= 3:
            # Create a surface for the filled triangle with transparency
            triangle_surface = pygame.Surface((800, 600), pygame.SRCALPHA)
            pygame.draw.polygon(triangle_surface, (*self.colors['triangle'], 80), points)
            self.screen.blit(triangle_surface, (0, 0))
            
            # Draw triangle outline (solid)
            pygame.draw.polygon(self.screen, self.colors['triangle'], points, 4)
            
            # Draw vertices as small circles
            for i, (x, y) in enumerate(points):
                pygame.draw.circle(self.screen, self.colors['triangle'], (int(x), int(y)), 6)
                # Label vertices
                self.fonts['tiny'].render_to(self.screen, (x + 10, y - 10), 
                                           f"P{i+1}", self.colors['text'])
        else:
            print(f"❌ DEBUG: Not enough points to draw triangle: {points}")
    
    def _draw_approx_circle(self, excircle: Dict):
        """Draw the excircle of the triangle, clipped to grid boundaries"""
        if not excircle or 'center' not in excircle or 'radius' not in excircle:
            return  # Quietly skip invalid excircles
        
        center = excircle['center']
        radius = excircle['radius']
        
        x = self.grid_origin.x + center.x * self.pixels_per_cm_x
        y = self.grid_origin.y - center.y * self.pixels_per_cm_y
        r = radius * self.pixels_per_cm_x  # Use x scale for radius
        
        # Sanity check for reasonable drawing parameters
        if r > 0 and r < 2000 and abs(x) < 5000 and abs(y) < 5000:
            # Draw the excircle
            pygame.draw.circle(self.screen, self.colors['excircle'], (int(x), int(y)), int(r), 3)
            
            # Draw center point for debugging
            pygame.draw.circle(self.screen, self.colors['excircle'], (int(x), int(y)), 3)
    
    def _draw_estimated_car(self, position: Point2D, car_dims: Dict):
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
            car_surface.set_alpha(180)  # Make it semi-transparent
            self.screen.blit(car_surface, car_rect)
            
            # Draw outline
            pygame.draw.rect(self.screen, (255, 217, 61), car_rect, 2)
            
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
            
            # Draw car body
            pygame.draw.polygon(self.screen, (255, 217, 61, 120), rotated_corners)  # Semi-transparent yellow
            pygame.draw.polygon(self.screen, (255, 217, 61), rotated_corners, 3)    # Yellow outline
        
        # Label
        label = f"Car Center ({position.x:.1f}, {position.y:.1f})"
        text_rect = pygame.Rect(center_x - 50, center_y - 25, 100, 15)
        pygame.draw.rect(self.screen, (*self.colors['surface'], 200), text_rect, border_radius=3)
        self.fonts['tiny'].render_to(self.screen, (center_x - 45, center_y - 20), 
                                   label, self.colors['text'])
    
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
            
            # Debug: Only print occasionally to avoid spam
            if int(current_orientation) % 15 == 0:  # Print every 15 degrees
                print(f"🚗 Car at ({position.x:.1f}, {position.y:.1f}) facing {current_orientation:.0f}°")
        else:
            # Fallback to arrow if car image failed to load
            print(f"⚠️ Car image not loaded, using arrow fallback at {current_orientation:.1f}°")
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
    
    def _draw_demo_moving_object(self):
        """Draw the demo moving object using the car image"""
        if not self.demo_moving_object['enabled']:
            return
        
        pos = self.demo_moving_object['position']
        orientation = self.demo_moving_object['orientation']
        
        # Convert to screen coordinates using INDEPENDENT X/Y scaling
        x = self.grid_origin.x + pos.x * self.pixels_per_cm_x
        y = self.grid_origin.y - pos.y * self.pixels_per_cm_y
        
        if self.car_image:
            # Use the actual car image and rotate it
            # 0° = no rotation (car points up), positive angles = counterclockwise rotation
            rotated_car = pygame.transform.rotate(self.car_image, orientation)  # Positive for counterclockwise
            
            # Get the rotated image rect and center it on the position
            car_rect = rotated_car.get_rect()
            car_rect.center = (int(x), int(y))
            
            # Draw shadow first
            shadow_offset = 2
            shadow_rect = rotated_car.get_rect(center=(int(x + shadow_offset), int(y + shadow_offset)))
            shadow_surface = pygame.Surface(rotated_car.get_size(), pygame.SRCALPHA)
            shadow_surface.fill((0, 0, 0, 50))
            self.screen.blit(shadow_surface, shadow_rect)
            
            # Draw the car
            self.screen.blit(rotated_car, car_rect)
        else:
            # Fallback to simple rectangle if car image not available
            car_width, car_height = 40, 25
            
            # Create car surface
            car_surface = pygame.Surface((car_width, car_height), pygame.SRCALPHA)
            
            # Car body (main rectangle)
            body_rect = pygame.Rect(2, 2, car_width - 4, car_height - 4)
            pygame.draw.rect(car_surface, (70, 130, 200), body_rect, border_radius=8)
            pygame.draw.rect(car_surface, (240, 245, 250), body_rect, 2, border_radius=8)
            
            # Front bumper (to show orientation)
            front_rect = pygame.Rect(car_width - 8, car_height // 2 - 6, 6, 12)
            pygame.draw.rect(car_surface, (255, 217, 61), front_rect, border_radius=3)
            
            # Rotate the car surface
            rotated_car = pygame.transform.rotate(car_surface, orientation)  # Positive for counterclockwise
            
            # Get the rect and center it
            car_rect = rotated_car.get_rect(center=(int(x), int(y)))
            
            # Draw shadow first
            shadow_surface = pygame.Surface(rotated_car.get_size(), pygame.SRCALPHA)
            shadow_surface.fill((0, 0, 0, 50))
            shadow_rect = shadow_surface.get_rect(center=(int(x + 2), int(y + 2)))
            self.screen.blit(shadow_surface, shadow_rect)
            
            # Draw the car
            self.screen.blit(rotated_car, car_rect)
        
        # Draw position indicator
        pygame.draw.circle(self.screen, (255, 217, 61), (int(x), int(y)), 3)
        
        # Show coordinates
        coord_text = f"({pos.x:.0f}, {pos.y:.0f})"
        text_rect = self.fonts['tiny'].get_rect(coord_text)
        bg_rect = pygame.Rect(x - text_rect.width // 2 - 2, y - 40, text_rect.width + 4, text_rect.height + 2)
        pygame.draw.rect(self.screen, (*self.colors['surface'], 200), bg_rect, border_radius=3)
        self.fonts['tiny'].render_to(self.screen, (x - text_rect.width // 2, y - 39), 
                                   coord_text, self.colors['text'])
    
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
                        # Only provide feedback every few pixels to avoid spam
                        if int(event.pos[0]) % 10 == 0:  # Reduce logging frequency
                            print(f"📍 Dragging {self.dragging_node} to ({grid_x:.1f}, {grid_y:.1f})")
        
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
                        elif key == 'show_excircle':
                            self.show_excircle = not self.show_excircle
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
                        # Start demo in center of grid
                        self.demo_moving_object['position'] = Point2D(self.grid_range_x / 2, self.grid_range_y / 2)
                        self.demo_moving_object['orientation'] = 0.0  # Up direction (0° = north/up)
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
                            
                            print(f"🔍 Debug placement: mouse=({event.pos[0]}, {event.pos[1]}), origin=({self.grid_origin.x}, {self.grid_origin.y})")
                            print(f"🔍 Scaling: x_scale={self.pixels_per_cm_x:.2f}, y_scale={self.pixels_per_cm_y:.2f}")
                            print(f"🔍 Raw grid coords: ({grid_x:.1f}, {grid_y:.1f})")
                            
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