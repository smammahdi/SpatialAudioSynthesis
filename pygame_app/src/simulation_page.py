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

# Import centralized logging configuration
from .logging_config import (
    log_simulation, log_trilateration, log_position, log_grid, 
    log_ui, log_input, log_demo, log_system, log_error
)

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
        self.show_sprite = True  # Changed from show_orientation to show_sprite
        self.show_grid = True
        self.show_connections = False  # Show dotted lines between sensor centers
        self.show_tracing = True  # Show position trace
        
        # Dictionary for the checkboxes visualization settings
        self.visualization_settings = {
            'show_grid': self.show_grid,
            'show_circles': self.show_circles,
            'show_triangle': self.show_triangle,
            'show_sprite': self.show_sprite,  # Changed from show_orientation
            'show_connections': self.show_connections,
            'show_tracing': self.show_tracing
        }
        
        # Position tracing for moving object
        self.position_trace = []  # List of past positions
        self.max_trace_points = 50  # Maximum number of trace points
        
        # Track previous manual distances to detect changes (for logging)
        self.previous_manual_distances = {}
        
        # Grid range settings
        # Fixed optimal grid range for spatial audio visualization (2m x 1.5m)
        self.grid_range_x = 200  # cm (2 meters)
        self.grid_range_y = 150  # cm (1.5 meters)
        
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
            'position': Point2D(100, 75),  # Center of 200x150 grid
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
        center_x = self.grid_range_x / 2
        center_y = self.grid_range_y / 2
        radius = min(center_x, center_y) * 0.6
        
        default_positions = [
            Point2D(center_x, center_y + radius),  # Top
            Point2D(center_x - radius * 0.866, center_y - radius * 0.5),  # Bottom left
            Point2D(center_x + radius * 0.866, center_y - radius * 0.5)   # Bottom right
        ]
        
        sensor_devices = [device for device in self.device_manager.devices.values() 
                          if device.device_type != "moving_object"][:3]
        
        log_grid(f"🔍 Initializing sensor positions for {len(sensor_devices)} sensor devices (excluding moving objects)")
        
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
        self.button_rects.clear()
        self.checkbox_rects.clear()
        
        left_rect = pygame.Rect(rect.x, rect.y, self.left_width - 20, rect.height)
        self._render_left_panel(left_rect)
        
        right_rect = pygame.Rect(self.left_width, rect.y, self.right_width, rect.height)
        self._render_grid_panel(right_rect)
    
    def _render_left_panel(self, rect: pygame.Rect):
        """Render the left control panel with new structure"""
        pygame.draw.rect(self.screen, self.colors['surface'], rect, border_radius=8)
        pygame.draw.rect(self.screen, self.colors['border'], rect, 2, border_radius=8)
        
        y_pos = rect.y + 15
        
        y_pos = self._render_moving_object_section(rect, y_pos)
        y_pos += 15
        
        y_pos = self._render_visualization_options(rect, y_pos)
        y_pos += 15
        
        y_pos = self._render_sensor_nodes_section(rect, y_pos)
        y_pos += 15
        
        self._render_moving_object_status(rect, rect.bottom - 120)
    
    def _render_moving_object_section(self, rect: pygame.Rect, y_start: int) -> int:
        """Render moving object connection section"""
        y_pos = y_start
        
        section_height = 85
        section_rect = pygame.Rect(rect.x + 5, y_pos, rect.width - 10, section_height)
        pygame.draw.rect(self.screen, (30, 35, 45), section_rect, border_radius=5)
        pygame.draw.rect(self.screen, self.colors['border'], section_rect, 1, border_radius=5)
        y_pos += 10
        
        self.fonts['body'].render_to(self.screen, (rect.x + 15, y_pos), 
                                     "Moving Object Connection", self.colors['text'])
        y_pos += 25
        
        status_text = "Connected" if self.moving_object_device else "Disconnected"
        status_color = self.colors['success'] if self.moving_object_device else self.colors['error']
        self.fonts['small'].render_to(self.screen, (rect.x + 15, y_pos), 
                                      f"Status: {status_text}", status_color)
        y_pos += 20
        
        demo_rect = pygame.Rect(rect.x + 15, y_pos, rect.width - 30, 25)
        demo_text = "Stop Demo" if self.demo_moving_object['enabled'] else "Start Demo"
        demo_color = self.colors['error'] if self.demo_moving_object['enabled'] else self.colors['success']
        self._render_button(demo_rect, 'toggle_demo', demo_text, demo_color)
        y_pos += 30
        
        if self.demo_moving_object['enabled']:
            y_pos += 5
            mode_text = f"Distance: {self.demo_moving_object['distance_mode'].title()}"
            self.fonts['small'].render_to(self.screen, (rect.x + 15, y_pos), 
                                          mode_text, self.colors['text_secondary'])
            y_pos += 18
            
            mode_rect = pygame.Rect(rect.x + 15, y_pos, rect.width - 30, 20)
            toggle_text = "Switch to Manual" if self.demo_moving_object['distance_mode'] == 'auto' else "Switch to Auto"
            self._render_button(mode_rect, 'toggle_distance_mode', toggle_text, self.colors['primary'])
            y_pos += 25
        
        return y_pos
    
    def _render_visualization_options(self, rect: pygame.Rect, y_start: int) -> int:
        """Render visualization options section"""
        y_pos = y_start
        
        section_height = 200  # Increased to accommodate 6 options
        section_rect = pygame.Rect(rect.x + 5, y_pos, rect.width - 10, section_height)
        pygame.draw.rect(self.screen, (25, 30, 40), section_rect, border_radius=5)
        pygame.draw.rect(self.screen, self.colors['border'], section_rect, 1, border_radius=5)
        y_pos += 10
        
        self.fonts['body'].render_to(self.screen, (rect.x + 15, y_pos), 
                                     "Visualization Options", self.colors['text_secondary'])
        y_pos += 20
        
        options = [
            ('show_grid', 'Show Grid', self.show_grid),
            ('show_circles', 'Distance Circles', self.show_circles),
            ('show_triangle', 'Min Area Triangle', self.show_triangle),
            ('show_connections', 'Sensor Connections', self.show_connections),
            ('show_sprite', 'Car Sprite & Orientation', self.show_sprite),
            ('show_tracing', 'Position Trace', self.show_tracing)
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
            
            # Add refresh button next to Position Trace option
            if key == 'show_tracing':
                refresh_btn_rect = pygame.Rect(rect.x + rect.width - 60, y_pos - 2, 50, 19)
                is_hovered = refresh_btn_rect.collidepoint(self.mouse_pos) if hasattr(self, 'mouse_pos') else False
                
                # Button background
                btn_color = (70, 80, 100) if is_hovered else (50, 60, 80)
                pygame.draw.rect(self.screen, btn_color, refresh_btn_rect, border_radius=3)
                pygame.draw.rect(self.screen, self.colors['border'], refresh_btn_rect, 1, border_radius=3)
                
                # Button text
                self.fonts['tiny'].render_to(self.screen, 
                                           (refresh_btn_rect.x + 8, refresh_btn_rect.y + 4), 
                                           "Refresh", self.colors['text'])
                
                self.button_rects['refresh_trace'] = refresh_btn_rect
            
            y_pos += 18
        
        y_pos += 5
        
        return y_pos
    
    def _render_sensor_nodes_section(self, rect: pygame.Rect, y_start: int) -> int:
        """Render sensor nodes configuration section"""
        y_pos = y_start
        
        sensor_devices = [device for device in self.device_manager.devices.values() 
                          if device.device_type != "moving_object"]
        num_sensor_devices = len(sensor_devices)
        section_height = 40 + (num_sensor_devices * 85)
        section_rect = pygame.Rect(rect.x + 5, y_pos, rect.width - 10, min(section_height, 400))
        pygame.draw.rect(self.screen, (20, 25, 35), section_rect, border_radius=5)
        pygame.draw.rect(self.screen, self.colors['border'], section_rect, 1, border_radius=5)
        y_pos += 10
        
        self.fonts['body'].render_to(self.screen, (rect.x + 15, y_pos), 
                                     "Sensor Nodes", self.colors['text_secondary'])
        y_pos += 20
        
        devices = [device for device in self.device_manager.devices.values() 
                   if device.device_type != "moving_object"]
        
        if len(devices) != self.last_sensor_count:
            log_grid(f"🔍 Displaying sensor nodes: {len(devices)} devices (excluding moving objects)")
            self.last_sensor_count = len(devices)
        
        for i, device in enumerate(devices):
            card_rect = pygame.Rect(rect.x + 10, y_pos, rect.width - 20, 75)
            pygame.draw.rect(self.screen, (40, 48, 62), card_rect, border_radius=5)
            pygame.draw.rect(self.screen, self.colors['border'], card_rect, 1, border_radius=5)
            
            color = self.device_colors[i % len(self.device_colors)]
            indicator_rect = pygame.Rect(card_rect.x, card_rect.y, 4, card_rect.height)
            pygame.draw.rect(self.screen, color, indicator_rect, border_radius=2)
            
            device_name = device.device_name[:18] + "..." if len(device.device_name) > 18 else device.device_name
            self.fonts['small'].render_to(self.screen, (card_rect.x + 8, card_rect.y + 5), 
                                          device_name, self.colors['text'])
            
            if device.device_id not in self.sensor_nodes:
                default_x = 50 + (i * 50) % 200
                default_y = 50 + (i * 50) % 200
                color_idx = i % len(self.device_colors)
                self.sensor_nodes[device.device_id] = SensorNode(
                    id=device.device_id,
                    position=Point2D(default_x, default_y),
                    color=self.device_colors[color_idx]
                )
            
            node = self.sensor_nodes[device.device_id]
            
            pos_text = f"Position: ({node.position.x:.1f}, {node.position.y:.1f})"
            self.fonts['small'].render_to(self.screen, (card_rect.x + 8, card_rect.y + 20), 
                                          pos_text, self.colors['text'])
            
            if self.demo_moving_object['enabled'] and self.demo_moving_object['distance_mode'] == 'manual':
                manual_dist = self.demo_moving_object['manual_distances'].get(device.device_id, 100.0)
                dist_text = f"Manual: {manual_dist:.0f}cm"
                self.fonts['small'].render_to(self.screen, (card_rect.x + 8, card_rect.y + 35), 
                                              dist_text, self.colors['text_secondary'])
                
                minus_rect = pygame.Rect(card_rect.x + card_rect.width - 45, card_rect.y + 32, 15, 15)
                plus_rect = pygame.Rect(card_rect.x + card_rect.width - 25, card_rect.y + 32, 15, 15)
                self._render_button(minus_rect, f"dist_minus_{device.device_id}", "-", self.colors['error'])
                self._render_button(plus_rect, f"dist_plus_{device.device_id}", "+", self.colors['success'])
            else:
                if self.demo_moving_object['enabled']:
                    actual_dist = self.demo_moving_object['position'].distance_to(node.position)
                    dist_text = f"Auto: {actual_dist:.1f}cm"
                else:
                    dist_text = f"Distance: {device.last_distance:.1f}cm"
                self.fonts['small'].render_to(self.screen, (card_rect.x + 8, card_rect.y + 35), 
                                              dist_text, self.colors['text_secondary'])
            
            edit_btn_rect = pygame.Rect(card_rect.x + 8, card_rect.y + 50, card_rect.width - 16, 20)
            self._render_button(edit_btn_rect, f"edit_coords_{device.device_id}", "Edit Coordinates", self.colors['primary'])
            
            y_pos += 80
        
        return y_pos
    
    def _render_moving_object_status(self, rect: pygame.Rect, y_start: int):
        """Render moving object status section at bottom"""
        y_pos = y_start
        
        section_height = 120
        section_rect = pygame.Rect(rect.x + 5, y_pos, rect.width - 10, section_height)
        pygame.draw.rect(self.screen, (30, 35, 45), section_rect, border_radius=5)
        pygame.draw.rect(self.screen, self.colors['border'], section_rect, 1, border_radius=5)
        y_pos += 10
        
        self.fonts['body'].render_to(self.screen, (rect.x + 15, y_pos), 
                                     "Moving Object", self.colors['text_secondary'])
        y_pos += 20
        
        current_orientation = self.demo_moving_object['orientation'] if self.demo_moving_object['enabled'] else self.moving_object_orientation
        orientation_text = f"Orientation: {current_orientation:.1f}°"
        self.fonts['small'].render_to(self.screen, (rect.x + 15, y_pos), 
                                      orientation_text, self.colors['text'])
        y_pos += 20
        
        car_center_x = rect.x + rect.width // 2
        car_center_y = y_pos + 25
        
        car_click_rect = pygame.Rect(car_center_x - 40, car_center_y - 30, 80, 60)
        self.button_rects['orientation_widget'] = car_click_rect
        
        pygame.draw.circle(self.screen, (40, 50, 65), (car_center_x, car_center_y), 35, 1)
        
        self._draw_mini_car(car_center_x, car_center_y, current_orientation)
        y_pos += 50
        
        recal_rect = pygame.Rect(rect.x + 15, y_pos, rect.width - 30, 25)
        self._render_button(recal_rect, 'recalibrate', "Recalibrate", self.colors['primary'])
    
    def _draw_mini_car(self, center_x: int, center_y: int, orientation: float):
        """Draw a mini car with orientation indicator using the car image"""
        if self.car_image:
            mini_scale = 0.8
            original_size = self.car_image.get_size()
            mini_size = (int(original_size[0] * mini_scale), int(original_size[1] * mini_scale))
            mini_car = pygame.transform.scale(self.car_image, mini_size)
            
            rotated_car = pygame.transform.rotate(mini_car, -orientation)
            
            car_rect = rotated_car.get_rect()
            car_rect.center = (center_x, center_y)
            
            self.screen.blit(rotated_car, car_rect)
        else:
            car_width, car_height = 30, 20
            
            car_surface = pygame.Surface((car_width, car_height), pygame.SRCALPHA)
            
            pygame.draw.rect(car_surface, (70, 130, 200), 
                             pygame.Rect(0, 0, car_width, car_height), border_radius=8)
            pygame.draw.rect(car_surface, (240, 245, 250), 
                             pygame.Rect(0, 0, car_width, car_height), 2, border_radius=8)
            
            front_points = [(car_width - 5, car_height // 2 - 4), 
                            (car_width, car_height // 2), 
                            (car_width - 5, car_height // 2 + 4)]
            pygame.draw.polygon(car_surface, (255, 217, 61), front_points)
            
            rotated_car = pygame.transform.rotate(car_surface, -orientation)
            
            car_rect = rotated_car.get_rect(center=(center_x, center_y))
            
            self.screen.blit(rotated_car, car_rect)
    
    def _render_input_field(self, rect: pygame.Rect, key: str, placeholder: str):
        """Render an input field"""
        is_active = self.active_input == key
        
        bg_color = (60, 70, 85) if is_active else (45, 55, 70)
        pygame.draw.rect(self.screen, bg_color, rect, border_radius=3)
        pygame.draw.rect(self.screen, self.colors['border'], rect, 1, border_radius=3)
        
        display_text = self.input_states.get(key, placeholder)
        self.fonts['small'].render_to(self.screen, (rect.x + 3, rect.y + 2), 
                                      display_text, self.colors['text'])
        
        self.button_rects[key] = rect
    
    def _render_grid_panel(self, rect: pygame.Rect):
        """Render the 2D grid visualization"""
        pygame.draw.rect(self.screen, (20, 25, 35), rect, border_radius=8)
        pygame.draw.rect(self.screen, self.colors['border'], rect, 2, border_radius=8)
        
        grid_rect = pygame.Rect(
            rect.x + self.grid_margin,
            rect.y + self.grid_margin,
            rect.width - 2 * self.grid_margin,
            rect.height - 2 * self.grid_margin
        )
        
        pygame.draw.rect(self.screen, (15, 20, 30), grid_rect, border_radius=5)
        
        self.grid_origin = Point2D(grid_rect.left, grid_rect.bottom)
        self.grid_width = grid_rect.width
        self.grid_height = grid_rect.height
        
        self.pixels_per_cm_x = self.grid_width / self.grid_range_x
        self.pixels_per_cm_y = self.grid_height / self.grid_range_y
        self.pixels_per_cm = min(self.pixels_per_cm_x, self.pixels_per_cm_y)
        
        if self.show_grid:
            self._draw_grid_lines(grid_rect)
        
        self._draw_sensor_nodes(grid_rect)
        
        if self.selected_node and self.mouse_pos[0] > self.left_width + 20:
            preview_x = (self.mouse_pos[0] - self.grid_origin.x) / self.pixels_per_cm_x
            preview_y = (self.grid_origin.y - self.mouse_pos[1]) / self.pixels_per_cm_y
            
            margin = 5
            if (margin <= preview_x <= self.grid_range_x - margin and 
                margin <= preview_y <= self.grid_range_y - margin):
                
                screen_x = self.grid_origin.x + preview_x * self.pixels_per_cm_x
                screen_y = self.grid_origin.y - preview_y * self.pixels_per_cm_y
                
                pygame.draw.circle(self.screen, (100, 255, 100, 100), (int(screen_x), int(screen_y)), 12, 2)
                pygame.draw.circle(self.screen, (100, 255, 100, 50), (int(screen_x), int(screen_y)), 8)
                
                pygame.draw.line(self.screen, (100, 255, 100), 
                                 (int(screen_x - 15), int(screen_y)), (int(screen_x + 15), int(screen_y)), 2)
                pygame.draw.line(self.screen, (100, 255, 100), 
                                 (int(screen_x), int(screen_y - 15)), (int(screen_x), int(screen_y + 15)), 2)
        
        if self.demo_moving_object['enabled']:
            active_nodes = list(self.sensor_nodes.values())[:3]
            distances = []
            for node in active_nodes:
                if self.demo_moving_object['distance_mode'] == 'auto':
                    distance = self.demo_moving_object['position'].distance_to(node.position)
                else:
                    distance = self.demo_moving_object['manual_distances'].get(node.id, 100.0)
                distances.append(distance)
        else:
            active_nodes = [node for node in self.sensor_nodes.values() 
                            if self.device_manager.devices.get(node.id, None) and 
                            self.device_manager.devices[node.id].last_distance > 0]
            
            if len(active_nodes) >= 3:
                nodes = active_nodes[:3]
                distances = [self.device_manager.devices[node.id].last_distance for node in nodes]
            else:
                active_nodes = []
        
        if len(active_nodes) >= 3:
            nodes = active_nodes[:3]
            
            # Perform trilateration to find moving object position
            trilateration_result = self._perform_trilateration(nodes, distances)
            
            if trilateration_result:
                self.moving_object_position = trilateration_result['position']
                
                # Only update position trace when we have a valid triangle (not fallback)
                if not trilateration_result.get('is_fallback', False):
                    self._update_position_trace(trilateration_result['position'])
                
                # Draw position trace if enabled
                if self.show_tracing:
                    self._draw_position_trace()
                
                # Draw distance circles if enabled
                if self.show_circles:
                    self._draw_distance_circles(nodes, distances)
                
                # Draw sensor connections if enabled
                if self.show_connections:
                    self._draw_sensor_connections(nodes)
                
                # Draw the minimum area triangle if enabled
                if self.show_triangle and trilateration_result['triangle']:
                    triangle_distances = trilateration_result.get('triangle_distances', distances)
                    self._draw_triangle_of_interest(trilateration_result['triangle'], triangle_distances)
                
                # Draw the estimated car position
                self._draw_estimated_car(
                    trilateration_result['position'], 
                    trilateration_result['car_dimensions'],
                    trilateration_result.get('is_fallback', False)
                )
                
                # Draw sprite with orientation if enabled
                if self.show_sprite:
                    self._draw_car_sprite_with_orientation(trilateration_result['position'])
                
                # Show "OUT OF RANGE" message if fallback is used
                if trilateration_result.get('is_fallback', False):
                    self._draw_out_of_range_message(grid_rect)
            else:
                # Show "OUT OF RANGE" message when no valid triangle
                self._draw_out_of_range_message(grid_rect)
                
                # Still draw basic visualization
                if self.show_circles:
                    self._draw_distance_circles(nodes, distances)
                if self.show_connections:
                    self._draw_sensor_connections(nodes)
                
                # Set fallback position at grid center
                self.moving_object_position = Point2D(100, 75)  # Center of 200x150 grid
        else:
            # Show "OUT OF RANGE" message when insufficient sensors
            self._draw_out_of_range_message(grid_rect)
    
    def _draw_grid_lines(self, rect: pygame.Rect):
        """Draw improved grid lines with better spacing and more labels for 2m x 1.5m grid"""
        # For 200x150cm grid, use 12.5cm spacing for optimal readability
        spacing = 12.5  # 12.5cm intervals provide good granularity for smaller spatial audio area
        
        # Draw vertical lines (X-axis)
        for x_cm in range(0, int(self.grid_range_x) + 1, int(spacing)):
            x_pixel = self.grid_origin.x + x_cm * self.pixels_per_cm_x
            if x_pixel <= rect.right:
                # Major lines every 25cm (darker), minor lines every 12.5cm (lighter)
                is_major = (x_cm % 25 == 0)
                line_color = self.colors['border'] if is_major else self.colors['grid_lines']
                line_width = 2 if is_major else 1
                
                pygame.draw.line(self.screen, line_color, 
                                 (x_pixel, rect.top), (x_pixel, rect.bottom), line_width)
                
                # Add labels for major lines and every 50cm
                if is_major:
                    label = f"{x_cm}cm" if x_cm % 50 == 0 else str(x_cm)
                    text_rect = self.fonts['tiny'].get_rect(label)
                    self.fonts['tiny'].render_to(self.screen, 
                                                  (x_pixel - text_rect.width // 2, rect.bottom + 3), 
                                                  label, self.colors['text_secondary'])
        
        # Draw horizontal lines (Y-axis)
        for y_cm in range(0, int(self.grid_range_y) + 1, int(spacing)):
            y_pixel = self.grid_origin.y - y_cm * self.pixels_per_cm_y
            if y_pixel >= rect.top:
                # Major lines every 25cm (darker), minor lines every 12.5cm (lighter)
                is_major = (y_cm % 25 == 0)
                line_color = self.colors['border'] if is_major else self.colors['grid_lines']
                line_width = 2 if is_major else 1
                
                pygame.draw.line(self.screen, line_color, 
                                 (rect.left, y_pixel), (rect.right, y_pixel), line_width)
                
                # Add labels for major lines and every 50cm
                if is_major:
                    label = f"{y_cm}cm" if y_cm % 50 == 0 else str(y_cm)
                    text_rect = self.fonts['tiny'].get_rect(label)
                    self.fonts['tiny'].render_to(self.screen, 
                                                  (rect.left - text_rect.width - 5, y_pixel - text_rect.height // 2), 
                                                  label, self.colors['text_secondary'])
        
        # Draw origin point
        pygame.draw.circle(self.screen, self.colors['error'], 
                           (int(self.grid_origin.x), int(self.grid_origin.y)), 4)
        self.fonts['tiny'].render_to(self.screen, 
                                     (self.grid_origin.x + 8, self.grid_origin.y - 12), 
                                     "(0,0)", self.colors['text'])
        
        # Draw boundary rectangle with thicker border
        max_y = self.grid_origin.y - self.grid_range_y * self.pixels_per_cm_y
        boundary_rect = pygame.Rect(self.grid_origin.x, max_y, 
                                    self.grid_range_x * self.pixels_per_cm_x, 
                                    self.grid_range_y * self.pixels_per_cm_y)
        pygame.draw.rect(self.screen, self.colors['border'], boundary_rect, 3)
        
        # Add corner labels for better reference
        # Top-right corner
        corner_label = f"({self.grid_range_x:.0f},{self.grid_range_y:.0f})"
        text_rect = self.fonts['tiny'].get_rect(corner_label)
        self.fonts['tiny'].render_to(self.screen, 
                                     (boundary_rect.right - text_rect.width - 5, boundary_rect.top - 15), 
                                     corner_label, self.colors['text_secondary'])
        
        # Add grid size indicator
        size_label = f"Grid: {self.grid_range_x/100:.1f}m × {self.grid_range_y/100:.1f}m"
        size_rect = self.fonts['small'].get_rect(size_label)
        bg_rect = pygame.Rect(boundary_rect.left + 10, boundary_rect.top + 10, 
                             size_rect.width + 8, size_rect.height + 4)
        pygame.draw.rect(self.screen, (*self.colors['surface'], 200), bg_rect, border_radius=3)
        self.fonts['small'].render_to(self.screen, 
                                     (boundary_rect.left + 14, boundary_rect.top + 12), 
                                     size_label, self.colors['text'])
        
        # Add X-axis label (bottom center)
        x_label = "X-axis (cm)"
        x_label_rect = self.fonts['small'].get_rect(x_label)
        x_label_x = boundary_rect.centerx - x_label_rect.width // 2
        x_label_y = boundary_rect.bottom + 25
        self.fonts['small'].render_to(self.screen, (x_label_x, x_label_y), 
                                     x_label, self.colors['text_secondary'])
        
        # Add Y-axis label (left center, rotated)
        y_label = "Y-axis (cm)"
        y_label_surface = pygame.Surface(self.fonts['small'].get_rect(y_label).size, pygame.SRCALPHA)
        self.fonts['small'].render_to(y_label_surface, (0, 0), y_label, self.colors['text_secondary'])
        rotated_y_label = pygame.transform.rotate(y_label_surface, 90)
        y_label_x = boundary_rect.left - 45
        y_label_y = boundary_rect.centery - rotated_y_label.get_height() // 2
        self.screen.blit(rotated_y_label, (y_label_x, y_label_y))
    
    def _update_position_trace(self, position: Point2D):
        """Update the position trace with the new position"""
        if not position:
            return
        
        # Add new position to trace
        self.position_trace.append((position.x, position.y))
        
        # Limit trace length
        if len(self.position_trace) > self.max_trace_points:
            self.position_trace.pop(0)
    
    def _clear_position_trace(self):
        """Clear all position trace points"""
        self.position_trace = []
    
    def _draw_position_trace(self):
        """Draw the position trace showing past positions"""
        if len(self.position_trace) < 2:
            return
        
        # Convert trace points to screen coordinates
        trace_points = []
        for x, y in self.position_trace:
            screen_x = self.grid_origin.x + x * self.pixels_per_cm_x
            screen_y = self.grid_origin.y - y * self.pixels_per_cm_y
            trace_points.append((int(screen_x), int(screen_y)))
        
        # Draw trace line with fading effect
        for i in range(1, len(trace_points)):
            # Calculate alpha based on position in trace (older = more transparent)
            alpha = int(255 * (i / len(trace_points)) * 0.7)  # Max 70% opacity
            
            # Create line color with alpha
            line_color = (100, 200, 255, alpha)  # Light blue with alpha
            
            # Create a surface for the line segment with alpha
            line_surface = pygame.Surface((abs(trace_points[i][0] - trace_points[i-1][0]) + 4, 
                                          abs(trace_points[i][1] - trace_points[i-1][1]) + 4), 
                                          pygame.SRCALPHA)
            
            # Adjust coordinates for the surface
            start_pos = (2, 2)
            end_pos = (trace_points[i][0] - trace_points[i-1][0] + 2, 
                      trace_points[i][1] - trace_points[i-1][1] + 2)
            
            pygame.draw.line(line_surface, line_color, start_pos, end_pos, 3)
            
            # Blit the line surface to screen
            surface_pos = (min(trace_points[i-1][0], trace_points[i][0]) - 2,
                          min(trace_points[i-1][1], trace_points[i][1]) - 2)
            self.screen.blit(line_surface, surface_pos)
        
        # Draw trace points as small circles
        for i, (x, y) in enumerate(trace_points):
            # Calculate alpha and size based on position in trace
            alpha = int(255 * ((i + 1) / len(trace_points)) * 0.8)
            size = 2 + int(3 * ((i + 1) / len(trace_points)))
            
            # Draw point with alpha
            point_surface = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(point_surface, (100, 200, 255, alpha), (size, size), size)
            self.screen.blit(point_surface, (x - size, y - size))
    
    def _draw_out_of_range_message(self, grid_rect: pygame.Rect):
        """Draw 'OUT OF RANGE' message in bottom right corner of grid"""
        message = "OUT OF RANGE"
        
        # Create the text surface
        text_surface, text_rect = self.fonts['body'].render(message, (255, 100, 100))  # Red color
        
        # Position in bottom right corner of grid
        message_x = grid_rect.right - text_rect.width - 15
        message_y = grid_rect.bottom - text_rect.height - 15
        
        # Draw background
        bg_rect = pygame.Rect(message_x - 8, message_y - 4, text_rect.width + 16, text_rect.height + 8)
        pygame.draw.rect(self.screen, (40, 15, 15, 200), bg_rect, border_radius=5)
        pygame.draw.rect(self.screen, (255, 100, 100), bg_rect, 2, border_radius=5)
        
        # Draw the text
        self.screen.blit(text_surface, (message_x, message_y))
    
    def _draw_car_sprite_with_orientation(self, position: Point2D):
        """Draw car sprite with orientation and outer rectangle"""
        if not position:
            return
        
        center_x = self.grid_origin.x + position.x * self.pixels_per_cm_x
        center_y = self.grid_origin.y - position.y * self.pixels_per_cm_y
        
        current_orientation = self.demo_moving_object['orientation'] if self.demo_moving_object['enabled'] else self.moving_object_orientation
        
        # Car dimensions
        car_length = 30.0  # cm
        car_width = 16.0   # cm
        
        if self.car_image:
            # Calculate scaling
            avg_scale = (self.pixels_per_cm_x + self.pixels_per_cm_y) / 2
            car_length_px = car_length * avg_scale
            car_width_px = car_width * avg_scale
            
            original_size = self.car_image.get_size()
            scale_x = car_length_px / original_size[1]
            scale_y = car_width_px / original_size[0]
            scale = min(scale_x, scale_y)
            
            scaled_size = (int(original_size[0] * scale), int(original_size[1] * scale))
            scaled_car = pygame.transform.scale(self.car_image, scaled_size)
            
            # Rotate the car image
            rotated_car = pygame.transform.rotate(scaled_car, -current_orientation)
            
            car_rect = rotated_car.get_rect()
            car_rect.center = (int(center_x), int(center_y))
            
            # Draw the car sprite
            self.screen.blit(rotated_car, car_rect)
            
            # Draw outer rectangle around the car
            padding = 8
            outer_rect = pygame.Rect(
                car_rect.left - padding, 
                car_rect.top - padding,
                car_rect.width + 2 * padding,
                car_rect.height + 2 * padding
            )
            pygame.draw.rect(self.screen, (255, 217, 61), outer_rect, 2, border_radius=3)
            
        else:
            # Fallback: draw oriented rectangle if no car image
            half_length = car_length * self.pixels_per_cm_x / 2
            half_width = car_width * self.pixels_per_cm_y / 2
            
            corners = [
                (-half_length, -half_width),
                (half_length, -half_width),
                (half_length, half_width),
                (-half_length, half_width)
            ]
            
            angle_rad = math.radians(current_orientation)
            cos_a = math.cos(angle_rad)
            sin_a = math.sin(angle_rad)
            
            rotated_corners = []
            for dx, dy in corners:
                rotated_x = dx * cos_a - dy * sin_a
                rotated_y = dx * sin_a + dy * cos_a
                
                screen_x = center_x + rotated_x
                screen_y = center_y + rotated_y
                rotated_corners.append((screen_x, screen_y))
            
            # Draw filled car rectangle
            pygame.draw.polygon(self.screen, (255, 217, 61, 120), rotated_corners)
            pygame.draw.polygon(self.screen, (255, 217, 61), rotated_corners, 3)
            
            # Draw outer rectangle
            padding = 8
            outer_corners = []
            for dx, dy in [(-half_length - padding, -half_width - padding),
                          (half_length + padding, -half_width - padding),
                          (half_length + padding, half_width + padding),
                          (-half_length - padding, half_width + padding)]:
                rotated_x = dx * cos_a - dy * sin_a
                rotated_y = dx * sin_a + dy * cos_a
                screen_x = center_x + rotated_x
                screen_y = center_y + rotated_y
                outer_corners.append((screen_x, screen_y))
            
            pygame.draw.polygon(self.screen, (255, 217, 61), outer_corners, 2)
    
    def _draw_sensor_nodes(self, rect: pygame.Rect):
        """Draw sensor nodes on the grid"""
        for node_id, node in self.sensor_nodes.items():
            x = self.grid_origin.x + node.position.x * self.pixels_per_cm_x
            y = self.grid_origin.y - node.position.y * self.pixels_per_cm_y
            
            if self.dragging_node == node_id:
                pygame.draw.circle(self.screen, (255, 255, 100), (int(x), int(y)), 12)
                pygame.draw.circle(self.screen, node.color, (int(x), int(y)), 10)
                pygame.draw.circle(self.screen, self.colors['text'], (int(x), int(y)), 10, 3)
                
                pygame.draw.circle(self.screen, (255, 255, 255, 100), (int(x), int(y)), 20, 2)
            elif self.selected_node == node_id:
                pygame.draw.circle(self.screen, (100, 255, 100), (int(x), int(y)), 12)
                pygame.draw.circle(self.screen, node.color, (int(x), int(y)), 10)
                pygame.draw.circle(self.screen, self.colors['text'], (int(x), int(y)), 10, 3)
                
                import time
                pulse = int(255 * (0.5 + 0.5 * math.sin(time.time() * 4)))
                pygame.draw.circle(self.screen, (100, 255, 100, pulse // 4), (int(x), int(y)), 15, 2)
                
                instruction_text = "Click on grid to place here"
                text_rect = self.fonts['tiny'].get_rect(instruction_text)
                bg_rect = pygame.Rect(x - text_rect.width // 2 - 4, y - 35, text_rect.width + 8, text_rect.height + 4)
                pygame.draw.rect(self.screen, (*self.colors['surface'], 200), bg_rect, border_radius=3)
                self.fonts['tiny'].render_to(self.screen, (x - text_rect.width // 2, y - 32), 
                                             instruction_text, (100, 255, 100))
            else:
                pygame.draw.circle(self.screen, node.color, (int(x), int(y)), 8)
                pygame.draw.circle(self.screen, self.colors['text'], (int(x), int(y)), 8, 2)
            
            device = self.device_manager.devices.get(node_id)
            if device:
                label = device.device_name[:10]
                
                if self.demo_moving_object['enabled']:
                    if self.demo_moving_object['distance_mode'] == 'auto':
                        distance = self.demo_moving_object['position'].distance_to(node.position)
                    else:
                        distance = self.demo_moving_object['manual_distances'].get(node_id, 100.0)
                else:
                    distance = device.last_distance
                
                text_rect = pygame.Rect(x - 40, y - 35, 80, 25)
                pygame.draw.rect(self.screen, (*self.colors['surface'], 200), text_rect, border_radius=3)
                
                self.fonts['tiny'].render_to(self.screen, (x - 35, y - 30), 
                                             label, self.colors['text'])
                self.fonts['tiny'].render_to(self.screen, (x - 35, y - 18), 
                                             f"{distance:.1f}cm", node.color)
    
    def _draw_distance_circles(self, nodes: List[SensorNode], distances: List[float]):
        """Draw distance circles around sensor nodes, clipped to grid boundaries"""
        grid_left = self.grid_origin.x
        grid_right = self.grid_origin.x + self.grid_range_x * self.pixels_per_cm_x
        grid_top = self.grid_origin.y - self.grid_range_y * self.pixels_per_cm_y
        grid_bottom = self.grid_origin.y
        
        for node, distance in zip(nodes, distances):
            x = self.grid_origin.x + node.position.x * self.pixels_per_cm_x
            y = self.grid_origin.y - node.position.y * self.pixels_per_cm_y
            radius = distance * ((self.pixels_per_cm_x + self.pixels_per_cm_y) / 2)
            
            if radius > 0:
                if (x + radius >= grid_left and x - radius <= grid_right and 
                    y + radius >= grid_top and y - radius <= grid_bottom):
                    
                    circle_surface = pygame.Surface((int(radius * 2 + 2), int(radius * 2 + 2)), pygame.SRCALPHA)
                    pygame.draw.circle(circle_surface, (*node.color, 40), 
                                       (int(radius + 1), int(radius + 1)), int(radius), 2)
                    
                    blit_x = x - radius - 1
                    blit_y = y - radius - 1
                    
                    clip_x = max(blit_x, grid_left)
                    clip_y = max(blit_y, grid_top)
                    clip_w = min(blit_x + circle_surface.get_width(), grid_right) - clip_x
                    clip_h = min(blit_y + circle_surface.get_height(), grid_bottom) - clip_y
                    
                    if clip_w > 0 and clip_h > 0:
                        source_x = clip_x - blit_x
                        source_y = clip_y - blit_y
                        source_rect = pygame.Rect(source_x, source_y, clip_w, clip_h)
                        self.screen.blit(circle_surface, (clip_x, clip_y), source_rect)

    def _draw_sensor_connections(self, nodes: List[SensorNode]):
        """Draw dotted lines connecting sensor centers"""
        if len(nodes) < 2:
            return
        
        # Use only the first 3 nodes for trilateration visualization
        active_nodes = nodes[:3]
        
        # Draw lines between all pairs of sensor centers
        for i in range(len(active_nodes)):
            for j in range(i + 1, len(active_nodes)):
                node1 = active_nodes[i]
                node2 = active_nodes[j]
                
                # Calculate screen positions
                x1 = self.grid_origin.x + node1.position.x * self.pixels_per_cm_x
                y1 = self.grid_origin.y - node1.position.y * self.pixels_per_cm_y
                x2 = self.grid_origin.x + node2.position.x * self.pixels_per_cm_x
                y2 = self.grid_origin.y - node2.position.y * self.pixels_per_cm_y
                
                # Draw dotted line
                self._draw_dotted_line((int(x1), int(y1)), (int(x2), int(y2)), 
                                     (180, 180, 180), 2, 8)
    
    def _draw_dotted_line(self, start_pos: Tuple[int, int], end_pos: Tuple[int, int], 
                         color: Tuple[int, int, int], width: int = 2, dash_length: int = 8):
        """Draw a dotted line between two points"""
        x1, y1 = start_pos
        x2, y2 = end_pos
        
        # Calculate line length and direction
        dx = x2 - x1
        dy = y2 - y1
        distance = math.sqrt(dx * dx + dy * dy)
        
        if distance == 0:
            return
        
        # Normalize direction vector
        dx_norm = dx / distance
        dy_norm = dy / distance
        
        # Draw dashed segments
        current_distance = 0
        draw_dash = True
        
        while current_distance < distance:
            segment_start_x = int(x1 + current_distance * dx_norm)
            segment_start_y = int(y1 + current_distance * dy_norm)
            
            segment_end_distance = min(current_distance + dash_length, distance)
            segment_end_x = int(x1 + segment_end_distance * dx_norm)
            segment_end_y = int(y1 + segment_end_distance * dy_norm)
            
            if draw_dash:
                pygame.draw.line(self.screen, color, 
                               (segment_start_x, segment_start_y), 
                               (segment_end_x, segment_end_y), width)
            
            current_distance += dash_length
            draw_dash = not draw_dash

    # ==============================================================================
    # ===== REWRITTEN TRILATERATION LOGIC STARTS HERE ==============================
    # ==============================================================================

    def _calculate_dynamic_samples(self, radius: float) -> int:
        """
        Calculates the number of samples for a circle's perimeter based on its radius.
        Larger circles get more samples for better precision.
        """
        if radius <= 0:
            return 0
        
        # Constants for dynamic sampling
        BASE_SAMPLES = 36  # Minimum samples for any circle
        SAMPLES_PER_100_CM = 36 # Add this many samples for every 100cm of radius
        MAX_SAMPLES = 144 # Cap samples to prevent performance issues on huge circles

        dynamic_samples = int(BASE_SAMPLES + (radius / 100.0) * SAMPLES_PER_100_CM)
        
        return min(dynamic_samples, MAX_SAMPLES)

    def _get_relevant_arc_points(self, center: Point2D, radius: float, other_center1: Point2D, other_center2: Point2D, num_samples: int) -> List[Point2D]:
        """
        HIGHLY OPTIMIZED: Only samples points on the arc segment that faces TOWARD 
        the region between the other two sensors. This creates a much more focused
        search space and eliminates most degenerate triangles.
        
        CRITICAL FIX: Ensures all generated points are EXACTLY on the circle perimeter.
        """
        if num_samples == 0 or radius <= 0:
            return []

        # Calculate angles from this circle's center to the other two sensor centers
        angle1 = math.atan2(other_center1.y - center.y, other_center1.x - center.x)
        angle2 = math.atan2(other_center2.y - center.y, other_center2.x - center.x)

        # Find the SHORTER arc between the two angles (more focused sampling)
        start_angle = min(angle1, angle2)
        end_angle = max(angle1, angle2)

        # Handle wraparound case and choose the SHORTER arc
        if end_angle - start_angle > math.pi:
            # The shorter arc goes the other way around
            start_angle, end_angle = end_angle, start_angle + 2 * math.pi

        # Calculate the focused arc span
        angle_span = end_angle - start_angle
        
        # Further reduce the arc to focus on the CENTRAL portion (middle 60%)
        arc_reduction_factor = 0.6  # Only sample middle 60% of the arc
        center_angle = start_angle + angle_span / 2.0
        reduced_span = angle_span * arc_reduction_factor
        
        focused_start = center_angle - reduced_span / 2.0
        focused_end = center_angle + reduced_span / 2.0
        
        # Safety check for degenerate cases
        if reduced_span < 1e-3 or num_samples <= 1:
            # Return single point at arc center - ENSURE EXACT RADIUS
            x = center.x + radius * math.cos(center_angle)
            y = center.y + radius * math.sin(center_angle)
            point = Point2D(x, y)
            
            # VERIFICATION: Confirm point is exactly on perimeter
            actual_distance = point.distance_to(center)
            if abs(actual_distance - radius) > 1e-5:
                log_trilateration(f"❌ CRITICAL: Generated point distance error: {abs(actual_distance - radius):.8f}")
            
            return [point]

        # Generate points only along the highly focused arc with EXACT radius placement
        points = []
        for i in range(num_samples):
            # FIXED: Use proper division to avoid off-by-one errors
            if num_samples == 1:
                angle = focused_start
            else:
                angle = focused_start + (i / (num_samples - 1)) * reduced_span
            
            # CRITICAL: Generate point with EXACT radius
            x = center.x + radius * math.cos(angle)
            y = center.y + radius * math.sin(angle)
            point = Point2D(x, y)
            
            # VERIFICATION: Confirm each point is exactly on the perimeter
            actual_distance = point.distance_to(center)
            if abs(actual_distance - radius) > 1e-5:
                log_trilateration(f"❌ CRITICAL: Arc point {i} distance error: {abs(actual_distance - radius):.8f}")
                log_trilateration(f"   Expected radius: {radius:.6f}, Actual: {actual_distance:.6f}")
                log_trilateration(f"   Center: ({center.x:.3f}, {center.y:.3f}), Point: ({point.x:.3f}, {point.y:.3f})")
                # Fix the point to be exactly on the perimeter
                correction_factor = radius / actual_distance
                old_point = point
                point = Point2D(center.x + (point.x - center.x) * correction_factor,
                               center.y + (point.y - center.y) * correction_factor)
                log_trilateration(f"   Corrected: ({old_point.x:.3f}, {old_point.y:.3f}) → ({point.x:.3f}, {point.y:.3f})")
                
                # Verify correction worked
                corrected_distance = point.distance_to(center)
                log_trilateration(f"   Corrected distance: {corrected_distance:.6f}, Error now: {abs(corrected_distance - radius):.8f}")
            
            points.append(point)
            
        return points

    def _perform_trilateration(self, nodes: List[SensorNode], distances: List[float]) -> Optional[Dict]:
        """
        Performs trilateration using the minimum area triangle method with dynamic
        sampling and robust validation.
        """
        if len(nodes) < 3 or len(distances) < 3:
            return None

        # --- Setup ---
        p1_node, p2_node, p3_node = nodes[:3]
        r1, r2, r3 = distances[:3]
        c1, c2, c3 = p1_node.position, p2_node.position, p3_node.position
        circles = [(c1, r1), (c2, r2), (c3, r3)]

        # Logging control
        current_time = pygame.time.get_ticks()
        should_log = not hasattr(self, '_last_trilateration_log') or current_time - self._last_trilateration_log > 2000
        if should_log:
            self._last_trilateration_log = current_time
            log_trilateration(f"\n🔧 Performing Trilateration...")
            log_trilateration(f"📍 Sensors: P1=({c1.x:.1f},{c1.y:.1f},r={r1:.1f}), "
                              f"P2=({c2.x:.1f},{c2.y:.1f},r={r2:.1f}), "
                              f"P3=({c3.x:.1f},{c3.y:.1f},r={r3:.1f})")

        # --- Step 1: Dynamic and Arc-based Sampling ---
        num_samples1 = self._calculate_dynamic_samples(r1)
        num_samples2 = self._calculate_dynamic_samples(r2)
        num_samples3 = self._calculate_dynamic_samples(r3)

        if should_log:
            log_trilateration(f"🔍 Dynamic Arc Sampling: C1={num_samples1}, C2={num_samples2}, C3={num_samples3} points")

        circle1_points = self._get_relevant_arc_points(c1, r1, c2, c3, num_samples1)
        circle2_points = self._get_relevant_arc_points(c2, r2, c1, c3, num_samples2)
        circle3_points = self._get_relevant_arc_points(c3, r3, c1, c2, num_samples3)
        
        if not all([circle1_points, circle2_points, circle3_points]):
             if should_log: log_trilateration("⚠️ One or more circles have zero radius or invalid arc, cannot sample points.")
             pass # Fallback logic will handle this case

        # --- Step 2: Find Minimum Area Triangle ---
        best_triangle = None
        min_area = float('inf')
        valid_candidates_tested = 0
        
        # DEBUG: Track all candidate triangles for analysis
        candidate_triangles = []  # List of (triangle, area) tuples
        
        # DEBUG: Add counters for rejection reasons
        perimeter_rejections = 0
        side_length_rejections = 0
        area_rejections = 0
        exterior_rejections = 0
        thinness_rejections = 0
        total_tested = 0

        # EXTREMELY STRICT THRESHOLDS to prevent degenerate triangles
        # Special handling for equal-radius cases (more lenient)
        radii_equal = abs(r1 - r2) < 1.0 and abs(r2 - r3) < 1.0 and abs(r1 - r3) < 1.0
        
        if radii_equal:
            MIN_TRIANGLE_AREA = 0.0   # More lenient for equal radius cases
            MIN_SIDE_LENGTH = 0.0     # Allow smaller triangles
            PERIMETER_TOLERANCE = 10.0  # Much more tolerance for equal radius
            if should_log:
                log_trilateration(f"🔄 Equal-radius detected, using relaxed thresholds: AREA={MIN_TRIANGLE_AREA}, SIDE={MIN_SIDE_LENGTH}, TOLERANCE={PERIMETER_TOLERANCE}")
        else:
            MIN_TRIANGLE_AREA = 0.0  # Stricter for unequal radius
            MIN_SIDE_LENGTH = 0.0    # Stricter for unequal radius
            PERIMETER_TOLERANCE = 5.0  # More lenient tolerance for mixed radius

        for pt1 in circle1_points:
            for pt2 in circle2_points:
                for pt3 in circle3_points:
                    total_tested += 1
                    triangle = (pt1, pt2, pt3)
                    
                    # CRITICAL VERIFICATION: Ensure each vertex is exactly on its respective circle perimeter
                    dist1_to_c1 = pt1.distance_to(c1)
                    dist2_to_c2 = pt2.distance_to(c2)
                    dist3_to_c3 = pt3.distance_to(c3)
                    
                    perimeter_error_1 = abs(dist1_to_c1 - r1)
                    perimeter_error_2 = abs(dist2_to_c2 - r2) 
                    perimeter_error_3 = abs(dist3_to_c3 - r3)
                    
                    # Verify all vertices are on their respective perimeters with 1e-5 tolerance
                    if (perimeter_error_1 > 1e-5 or perimeter_error_2 > 1e-5 or perimeter_error_3 > 1e-5):
                        perimeter_rejections += 1
                        if should_log and perimeter_rejections <= 3:  # Only log first few errors
                            log_trilateration(f"❌ PERIMETER ERROR: P1={perimeter_error_1:.8f}, P2={perimeter_error_2:.8f}, P3={perimeter_error_3:.8f}")
                        continue
                    
                    side1 = pt1.distance_to(pt2)
                    side2 = pt2.distance_to(pt3) 
                    side3 = pt3.distance_to(pt1)
                    
                    if (side1 < MIN_SIDE_LENGTH or side2 < MIN_SIDE_LENGTH or side3 < MIN_SIDE_LENGTH):
                        side_length_rejections += 1
                        if should_log and side_length_rejections <= 3:  # Debug first few
                            log_trilateration(f"❌ SIDE LENGTH: sides=({side1:.3f}, {side2:.3f}, {side3:.3f}) < {MIN_SIDE_LENGTH}")
                        continue

                    area = self._triangle_area_precise(pt1, pt2, pt3)
                    if area < MIN_TRIANGLE_AREA:
                        area_rejections += 1
                        if should_log and area_rejections <= 3:  # Debug first few
                            log_trilateration(f"❌ AREA TOO SMALL: area={area:.3f} < {MIN_TRIANGLE_AREA}")
                        continue

                    # Additional validation: Check for degenerate triangles (too thin/elongated)
                    # Calculate the "thinness ratio" - ratio of area to perimeter squared
                    perimeter = side1 + side2 + side3
                    thinness_ratio = (4 * math.sqrt(3) * area) / (perimeter * perimeter)
                    
                    # Reject triangles that are too thin (close to straight lines)
                    MIN_THINNESS_RATIO = 0.05  # Triangles thinner than this are likely slivers
                    if thinness_ratio < MIN_THINNESS_RATIO:
                        area_rejections += 1
                        if should_log and area_rejections <= 3:  # Debug first few
                            log_trilateration(f"❌ TRIANGLE TOO THIN: thinness_ratio={thinness_ratio:.4f} < {MIN_THINNESS_RATIO}")
                        continue

                    # Exterior validation with more lenient tolerance for interior checks
                    EXTERIOR_TOLERANCE = PERIMETER_TOLERANCE * 3.0  # Much more lenient
                    if not self._validate_triangle_exterior(triangle, circles, EXTERIOR_TOLERANCE):
                        exterior_rejections += 1
                        if should_log and exterior_rejections <= 3:  # Debug first few
                            log_trilateration(f"❌ EXTERIOR VALIDATION FAILED (tolerance={EXTERIOR_TOLERANCE:.1f})")
                        continue
                    
                    valid_candidates_tested += 1
                    
                    # DEBUG: Track this candidate triangle
                    candidate_triangles.append((triangle, area))
                    
                    if area < min_area:
                        min_area = area
                        best_triangle = triangle
                        
                        # DEBUG: Log each new minimum area candidate
                        if valid_candidates_tested <= 3:  # Always show first 3 candidates
                            log_trilateration(f"🔍 NEW MIN AREA CANDIDATE #{valid_candidates_tested}:")
                            log_trilateration(f"   Area: {area:.3f} cm²")
                            log_trilateration(f"   P1: ({pt1.x:.3f}, {pt1.y:.3f}) [dist to S1: {dist1_to_c1:.3f}]")
                            log_trilateration(f"   P2: ({pt2.x:.3f}, {pt2.y:.3f}) [dist to S2: {dist2_to_c2:.3f}]")
                            log_trilateration(f"   P3: ({pt3.x:.3f}, {pt3.y:.3f}) [dist to S3: {dist3_to_c3:.3f}]")

        # DEBUG: Final candidate analysis
        if candidate_triangles:  # Always show if we have candidates
            log_trilateration(f"\n📊 CANDIDATE TRIANGLE ANALYSIS:")
            log_trilateration(f"   Total valid candidates found: {len(candidate_triangles)}")
            
            # Sort candidates by area to show the progression
            sorted_candidates = sorted(candidate_triangles, key=lambda x: x[1])
            
            log_trilateration(f"   📈 AREA PROGRESSION (smallest to largest):")
            for i, (triangle, area) in enumerate(sorted_candidates[:5]):  # Show first 5
                pt1, pt2, pt3 = triangle
                log_trilateration(f"      #{i+1}: Area={area:.3f} cm² - P1({pt1.x:.1f},{pt1.y:.1f}), P2({pt2.x:.1f},{pt2.y:.1f}), P3({pt3.x:.1f},{pt3.y:.1f})")
            
            if len(sorted_candidates) > 5:
                log_trilateration(f"      ... and {len(sorted_candidates)-5} more candidates")
            
            # Verify the final selection
            if best_triangle:
                final_area = self._triangle_area_precise(best_triangle[0], best_triangle[1], best_triangle[2])
                log_trilateration(f"   ✅ FINAL SELECTION:")
                log_trilateration(f"      Area: {final_area:.3f} cm² (should be {min_area:.3f})")
                log_trilateration(f"      Vertices: P1({best_triangle[0].x:.3f},{best_triangle[0].y:.3f}), P2({best_triangle[1].x:.3f},{best_triangle[1].y:.3f}), P3({best_triangle[2].x:.3f},{best_triangle[2].y:.3f})")
                
                # Double-check perimeter accuracy for final triangle
                final_dist1 = best_triangle[0].distance_to(c1)
                final_dist2 = best_triangle[1].distance_to(c2) 
                final_dist3 = best_triangle[2].distance_to(c3)
                log_trilateration(f"      Final perimeter check: P1→S1={final_dist1:.6f} (expected {r1:.6f}), P2→S2={final_dist2:.6f} (expected {r2:.6f}), P3→S3={final_dist3:.6f} (expected {r3:.6f})")
        else:
            # Show rejection statistics when no candidates found
            log_trilateration(f"\n⚠️ REJECTION ANALYSIS (No valid candidates found):")
            log_trilateration(f"   Total triangles tested: {total_tested}")
            log_trilateration(f"   Perimeter rejections: {perimeter_rejections}")
            log_trilateration(f"   Side length rejections: {side_length_rejections}")
            log_trilateration(f"   Area rejections: {area_rejections}")  
            log_trilateration(f"   Exterior validation rejections: {exterior_rejections}")
            log_trilateration(f"   Thresholds: MIN_AREA={MIN_TRIANGLE_AREA}, MIN_SIDE={MIN_SIDE_LENGTH}")
            
            if total_tested == 0:
                log_trilateration(f"   ⚠️ No triangle combinations generated - check arc sampling!")
            elif perimeter_rejections == total_tested:
                log_trilateration(f"   ⚠️ All triangles rejected for perimeter errors - arc sampling issue!")
            elif side_length_rejections > total_tested * 0.8:
                log_trilateration(f"   ⚠️ Most triangles too small - consider reducing MIN_SIDE_LENGTH")
            elif area_rejections > total_tested * 0.8:
                log_trilateration(f"   ⚠️ Most triangles too small area - consider reducing MIN_TRIANGLE_AREA")

        # --- Step 3: Process Result or Fallback ---
        if best_triangle:
            centroid = Point2D(
                (best_triangle[0].x + best_triangle[1].x + best_triangle[2].x) / 3.0,
                (best_triangle[0].y + best_triangle[1].y + best_triangle[2].y) / 3.0
            )
            if should_log:
                log_trilateration(f"✅ Found valid minimum area triangle:")
                log_trilateration(f"   • Area: {min_area:.1f} cm², Valid candidates: {valid_candidates_tested}")
                log_position(f"🚗 Car position: ({centroid.x:.1f}, {centroid.y:.1f})")

            return {
                'position': centroid,
                'triangle': best_triangle,
                'car_dimensions': {'length': 30.0, 'width': 16.0},
                'is_fallback': False,
                'triangle_distances': [r1, r2, r3]  # Store the exact distances used
            }
        else:
            # Fallback if no valid triangles found
            if should_log:
                log_trilateration(f"⚠️ No valid triangles found after testing candidates, using weighted fallback.")
            
            total_weight = 0
            weighted_x = 0
            weighted_y = 0
            
            for pos, radius in circles:
                weight = 1.0 / max(radius, 1.0)
                total_weight += weight
                weighted_x += pos.x * weight
                weighted_y += pos.y * weight
            
            if total_weight > 0:
                fallback_position = Point2D(weighted_x / total_weight, weighted_y / total_weight)
            else: # Handle case where all radii are zero
                fallback_position = Point2D(
                    (circles[0][0].x + circles[1][0].x + circles[2][0].x) / 3.0,
                    (circles[0][0].y + circles[1][0].y + circles[2][0].y) / 3.0,
                )

            if should_log:
                log_position(f"📍 Fallback position: ({fallback_position.x:.1f}, {fallback_position.y:.1f})")

            return {
                'position': fallback_position,
                'triangle': None,
                'car_dimensions': {'length': 30.0, 'width': 16.0},
                'is_fallback': True
            }

    def _triangle_area_precise(self, p1: Point2D, p2: Point2D, p3: Point2D) -> float:
        """
        Calculates triangle area using the shoelace formula for numerical stability.
        """
        return abs((p1.x * (p2.y - p3.y) + p2.x * (p3.y - p1.y) + p3.x * (p1.y - p2.y)) / 2.0)

    def _validate_triangle_exterior(self, triangle: Tuple[Point2D, Point2D, Point2D], 
                                  circles: List[Tuple[Point2D, float]], tolerance: float) -> bool:
        """
        Correctly validates that a vertex from one circle is not inside any of the OTHER circles.
        Also includes additional verification that vertices are actually ON their respective perimeters.
        """
        pt1, pt2, pt3 = triangle
        (c1, r1), (c2, r2), (c3, r3) = circles

        # ENHANCED: Verify each vertex is actually ON its respective circle perimeter with strict tolerance
        dist1_to_c1 = pt1.distance_to(c1)
        dist2_to_c2 = pt2.distance_to(c2)
        dist3_to_c3 = pt3.distance_to(c3)
        
        # Use much stricter tolerance for perimeter verification (1e-5)
        perimeter_tolerance = 1e-5
        if (abs(dist1_to_c1 - r1) > perimeter_tolerance or 
            abs(dist2_to_c2 - r2) > perimeter_tolerance or 
            abs(dist3_to_c3 - r3) > perimeter_tolerance):
            return False

        # Original validation: vertex from one circle cannot be inside the OTHER circles
        # Use the passed tolerance for interior/exterior checks
        # Vertex from circle 1 (pt1) cannot be inside circle 2 or 3
        if pt1.distance_to(c2) < r2 - tolerance or pt1.distance_to(c3) < r3 - tolerance:
            return False
        
        # Vertex from circle 2 (pt2) cannot be inside circle 1 or 3
        if pt2.distance_to(c1) < r1 - tolerance or pt2.distance_to(c3) < r3 - tolerance:
            return False

        # Vertex from circle 3 (pt3) cannot be inside circle 1 or 2
        if pt3.distance_to(c1) < r1 - tolerance or pt3.distance_to(c2) < r2 - tolerance:
            return False

        return True

    # ==============================================================================
    # ===== END OF REWRITTEN TRILATERATION LOGIC ===================================
    # ==============================================================================
    
    def _draw_triangle_of_interest(self, triangle: List[Point2D], triangle_distances: List[float] = None):
        """Draw the minimum area triangle with CORRECTED coordinate conversion"""
        if not triangle or len(triangle) < 3:
            return
        
        # DEBUGGING: Log the coordinate conversion details
        current_time = pygame.time.get_ticks()
        should_debug = not hasattr(self, '_last_draw_debug') or current_time - self._last_draw_debug > 3000
        if should_debug:
            self._last_draw_debug = current_time
            log_trilateration(f"🎨 Drawing Debug:")
            log_trilateration(f"   Grid origin: ({self.grid_origin.x:.1f}, {self.grid_origin.y:.1f})")
            log_trilateration(f"   Scale factors: X={self.pixels_per_cm_x:.3f}, Y={self.pixels_per_cm_y:.3f}")
        
        # FIXED: Use exact same coordinate conversion as sensor nodes and circles
        points = []
        for i, p in enumerate(triangle):
            # Use IDENTICAL conversion formula as _draw_sensor_nodes and _draw_distance_circles
            screen_x = self.grid_origin.x + p.x * self.pixels_per_cm_x
            screen_y = self.grid_origin.y - p.y * self.pixels_per_cm_y
            points.append((int(screen_x), int(screen_y)))
            
            if should_debug:
                log_trilateration(f"   P{i+1}: ({p.x:.1f},{p.y:.1f}) → screen({screen_x:.1f},{screen_y:.1f})")
        
        # VERIFICATION: Check if vertices are actually on circle perimeters using EXACT distances
        if should_debug and triangle_distances:
            p1, p2, p3 = triangle[:3]
            r1, r2, r3 = triangle_distances[:3]  # Use the exact distances from triangle generation
            # Get the sensor positions
            sensor_list = list(self.sensor_nodes.values())[:3]
            if len(sensor_list) >= 3:
                c1, c2, c3 = sensor_list[0].position, sensor_list[1].position, sensor_list[2].position
                
                actual_dist_1 = p1.distance_to(c1)
                actual_dist_2 = p2.distance_to(c2)
                actual_dist_3 = p3.distance_to(c3)
                
                error_1 = abs(actual_dist_1 - r1)
                error_2 = abs(actual_dist_2 - r2)
                error_3 = abs(actual_dist_3 - r3)
                
                log_trilateration(f"🔍 PERIMETER VERIFICATION (using generation distances):")
                log_trilateration(f"   P1: Expected r={r1:.3f}, Actual d={actual_dist_1:.3f}, Error={error_1:.6f}")
                log_trilateration(f"   P2: Expected r={r2:.3f}, Actual d={actual_dist_2:.3f}, Error={error_2:.6f}")
                log_trilateration(f"   P3: Expected r={r3:.3f}, Actual d={actual_dist_3:.3f}, Error={error_3:.6f}")
                
                # Flag vertices that are significantly off the perimeter (should be < 1e-5)
                if error_1 > 1e-3:
                    log_trilateration(f"❌ MAJOR ERROR: P1 not on circle perimeter! Error: {error_1:.6f}")
                if error_2 > 1e-3:
                    log_trilateration(f"❌ MAJOR ERROR: P2 not on circle perimeter! Error: {error_2:.6f}")
                if error_3 > 1e-3:
                    log_trilateration(f"❌ MAJOR ERROR: P3 not on circle perimeter! Error: {error_3:.6f}")
                distances = []
                for node in sensor_list:
                    if self.demo_moving_object['enabled'] and self.demo_moving_object['distance_mode'] == 'manual':
                        distances.append(self.demo_moving_object['manual_distances'].get(node.id, 100.0))
                    elif self.demo_moving_object['enabled']:
                        distances.append(self.demo_moving_object['position'].distance_to(node.position))
                    else:
                        device = self.device_manager.devices.get(node.id)
                        distances.append(device.last_distance if device else 100.0)
                
                if len(distances) >= 3:
                    d1 = p1.distance_to(sensor_list[0].position)
                    d2 = p2.distance_to(sensor_list[1].position)
                    d3 = p3.distance_to(sensor_list[2].position)
                    log_trilateration(f"   Vertex verification: P1→S1={d1:.1f}cm (expected {distances[0]:.1f})")
                    log_trilateration(f"                         P2→S2={d2:.1f}cm (expected {distances[1]:.1f})")
                    log_trilateration(f"                         P3→S3={d3:.1f}cm (expected {distances[2]:.1f})")
        
        if len(points) >= 3:
            p1, p2, p3 = triangle[:3]
            area = self._triangle_area_precise(p1, p2, p3)
            
            # Color coding based on triangle quality
            if area > 2000:
                triangle_color = (100, 255, 100)  # Green for good triangles
                alpha = 80
            elif area > 1000:
                triangle_color = (255, 255, 100)  # Yellow for decent triangles
                alpha = 90
            else:
                triangle_color = (255, 150, 100)  # Orange for marginal triangles
                alpha = 100
            
            # Draw filled triangle
            triangle_surface = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
            pygame.draw.polygon(triangle_surface, (*triangle_color, alpha), points)
            self.screen.blit(triangle_surface, (0, 0))
            
            # Draw triangle outline
            pygame.draw.polygon(self.screen, triangle_color, points, 4)
            
            # Draw and label vertices with larger, more visible markers
            for i, (x, y) in enumerate(points):
                # Larger vertex markers
                pygame.draw.circle(self.screen, triangle_color, (int(x), int(y)), 10)
                pygame.draw.circle(self.screen, (255, 255, 255), (int(x), int(y)), 10, 3)
                pygame.draw.circle(self.screen, (0, 0, 0), (int(x), int(y)), 4)
                
                # Vertex labels
                label = f"V{i+1}"
                text_rect = self.fonts['tiny'].get_rect(label)
                bg_rect = pygame.Rect(x + 15, y - 15, text_rect.width + 6, text_rect.height + 4)
                pygame.draw.rect(self.screen, (*self.colors['surface'], 240), bg_rect, border_radius=3)
                self.fonts['tiny'].render_to(self.screen, (x + 18, y - 12), 
                                             label, self.colors['text'])
            
            # Area label at centroid
            centroid_x = sum(x for x, y in points) // 3
            centroid_y = sum(y for x, y in points) // 3
            area_label = f"Area: {area:.0f}cm²"
            text_rect = self.fonts['small'].get_rect(area_label)
            bg_rect = pygame.Rect(centroid_x - text_rect.width//2 - 4, centroid_y - text_rect.height//2 - 2, 
                                 text_rect.width + 8, text_rect.height + 4)
            pygame.draw.rect(self.screen, (*self.colors['surface'], 240), bg_rect, border_radius=4)
            self.fonts['small'].render_to(self.screen, (centroid_x - text_rect.width//2, centroid_y - text_rect.height//2), 
                                         area_label, triangle_color)
    
    def _draw_estimated_car(self, position: Point2D, car_dims: Dict, is_fallback: bool = False):
        """Draw the estimated car position using the car image"""
        if not position or not car_dims:
            return
        
        center_x = self.grid_origin.x + position.x * self.pixels_per_cm_x
        center_y = self.grid_origin.y - position.y * self.pixels_per_cm_y
        
        current_orientation = self.demo_moving_object['enabled'] if self.demo_moving_object['enabled'] else self.moving_object_orientation
        
        if self.car_image:
            avg_scale = (self.pixels_per_cm_x + self.pixels_per_cm_y) / 2
            car_length_px = car_dims['length'] * avg_scale
            car_width_px = car_dims['width'] * avg_scale
            
            original_size = self.car_image.get_size()
            scale_x = car_length_px / original_size[1]
            scale_y = car_width_px / original_size[0]
            scale = min(scale_x, scale_y)
            
            scaled_size = (int(original_size[0] * scale), int(original_size[1] * scale))
            scaled_car = pygame.transform.scale(self.car_image, scaled_size)
            
            rotated_car = pygame.transform.rotate(scaled_car, -current_orientation)
            
            car_rect = rotated_car.get_rect()
            car_rect.center = (int(center_x), int(center_y))
            
            car_surface = rotated_car.copy()
            car_surface.set_alpha(180 if not is_fallback else 100)
            self.screen.blit(car_surface, car_rect)
            
            outline_color = (220, 80, 80) if is_fallback else (255, 217, 61)
            pygame.draw.rect(self.screen, outline_color, car_rect, 2)
            
        else:
            car_length_px = car_dims['length'] * self.pixels_per_cm
            car_width_px = car_dims['width'] * self.pixels_per_cm
            
            half_length = car_length_px / 2
            half_width = car_width_px / 2
            corners = [
                (-half_length, -half_width),
                (half_length, -half_width),
                (half_length, half_width),
                (-half_length, half_width)
            ]
            
            angle_rad = math.radians(current_orientation)
            cos_a = math.cos(angle_rad)
            sin_a = math.sin(angle_rad)
            
            rotated_corners = []
            for dx, dy in corners:
                rotated_x = dx * cos_a - dy * sin_a
                rotated_y = dx * sin_a + dy * cos_a
                
                screen_x = center_x + rotated_x
                screen_y = center_y + rotated_y
                rotated_corners.append((screen_x, screen_y))
            
            fill_color = (220, 80, 80, 120) if is_fallback else (255, 217, 61, 120)
            outline_color = (220, 80, 80) if is_fallback else (255, 217, 61)
            
            pygame.draw.polygon(self.screen, fill_color, rotated_corners)
            pygame.draw.polygon(self.screen, outline_color, rotated_corners, 3)
        
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
        
        current_orientation = self.demo_moving_object['enabled'] if self.demo_moving_object['enabled'] else self.moving_object_orientation
        
        if self.car_image:
            rotated_car = pygame.transform.rotate(self.car_image, -current_orientation)
            
            car_rect = rotated_car.get_rect()
            car_rect.center = (int(x), int(y))
            
            self.screen.blit(rotated_car, car_rect)
        else:
            arrow_length = 30
            
            angle_rad = math.radians(current_orientation - 90)
            end_x = x + arrow_length * math.cos(angle_rad)
            end_y = y - arrow_length * math.sin(angle_rad)
            
            pygame.draw.line(self.screen, self.colors['orientation'], 
                             (int(x), int(y)), (int(end_x), int(end_y)), 3)
            
            head_angle = 150
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
        
        text_surface, text_rect = self.fonts['body'].render(text, self.colors['text'])
        text_rect.center = rect.center
        self.screen.blit(text_surface, text_rect)
        
        self.button_rects[key] = rect
    
    def handle_event(self, event: pygame.event.Event):
        """Handle events specific to the simulation page"""
        if event.type == pygame.MOUSEMOTION:
            self.mouse_pos = event.pos
            
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
                
                if self.selected_node:
                    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_CROSSHAIR)
                elif mouse_over_node:
                    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
                else:
                    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
            
            if self.dragging_node:
                if event.pos[0] > self.left_width + 20:
                    grid_x = (event.pos[0] - self.grid_origin.x) / self.pixels_per_cm_x
                    grid_y = (self.grid_origin.y - event.pos[1]) / self.pixels_per_cm_y
                    
                    margin = 10
                    grid_x = max(margin, min(grid_x, self.grid_range_x - margin))
                    grid_y = max(margin, min(grid_y, self.grid_range_y - margin))
                    
                    if self.dragging_node in self.sensor_nodes:
                        self.sensor_nodes[self.dragging_node].position = Point2D(grid_x, grid_y)
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                for key, rect in self.checkbox_rects.items():
                    if rect.collidepoint(event.pos):
                        if key == 'show_grid':
                            self.show_grid = not self.show_grid
                            self.visualization_settings['show_grid'] = self.show_grid
                        elif key == 'show_circles':
                            self.show_circles = not self.show_circles
                            self.visualization_settings['show_circles'] = self.show_circles
                        elif key == 'show_triangle':
                            self.show_triangle = not self.show_triangle
                            self.visualization_settings['show_triangle'] = self.show_triangle
                        elif key == 'show_connections':
                            self.show_connections = not self.show_connections
                            self.visualization_settings['show_connections'] = self.show_connections
                        elif key == 'show_sprite':
                            self.show_sprite = not self.show_sprite
                            self.visualization_settings['show_sprite'] = self.show_sprite
                        elif key == 'show_tracing':
                            self.show_tracing = not self.show_tracing
                            self.visualization_settings['show_tracing'] = self.show_tracing
                        return
                
                if 'refresh_trace' in self.button_rects and self.button_rects['refresh_trace'].collidepoint(event.pos):
                    # Clear the position trace
                    self._clear_position_trace()
                    print("🔄 Position trace cleared!")
                    return
                
                if 'recalibrate' in self.button_rects and self.button_rects['recalibrate'].collidepoint(event.pos):
                    print(f"🔄 RECALIBRATE button clicked!")
                    
                    if self.demo_moving_object['enabled']:
                        print(f"📐 Recalibrating DEMO mode: setting demo orientation to 0°")
                        self.demo_moving_object['orientation'] = 0.0
                        print(f"✅ Demo orientation reset to: {self.demo_moving_object['orientation']}°")
                    else:
                        old_offset = self.orientation_offset
                        self.orientation_offset = -self.raw_moving_object_orientation
                        
                        self.moving_object_orientation = (self.raw_moving_object_orientation + self.orientation_offset) % 360
                        
                        print(f"📐 Recalibrating REAL device mode:")
                        print(f"   Current raw orientation: {self.raw_moving_object_orientation:.1f}°")
                        print(f"   Old offset: {old_offset:.1f}°")
                        print(f"   New offset: {self.orientation_offset:.1f}°")
                        print(f"   Calibrated result: {self.moving_object_orientation:.1f}°")
                    return
                
                if 'toggle_demo' in self.button_rects and self.button_rects['toggle_demo'].collidepoint(event.pos):
                    self.demo_moving_object['enabled'] = not self.demo_moving_object['enabled']
                    if self.demo_moving_object['enabled']:
                        sensor_devices = [device for device in self.device_manager.devices.values() 
                                          if device.device_type != "moving_object"]
                        
                        if len(sensor_devices) >= 3 and all(device.device_id in self.sensor_nodes for device in sensor_devices[:3]):
                            s1 = self.sensor_nodes[sensor_devices[0].device_id].position
                            s2 = self.sensor_nodes[sensor_devices[1].device_id].position
                            s3 = self.sensor_nodes[sensor_devices[2].device_id].position
                            
                            center_x = (s1.x + s2.x + s3.x) / 3
                            center_y = (s1.y + s2.y + s3.y) / 3
                            
                            grid_center_x = self.grid_range_x / 2
                            grid_center_y = self.grid_range_y / 2
                            
                            start_x = center_x * 0.7 + grid_center_x * 0.3
                            start_y = center_y * 0.7 + grid_center_y * 0.3
                            
                            self.demo_moving_object['position'] = Point2D(start_x, start_y)
                        else:
                            self.demo_moving_object['position'] = Point2D(self.grid_range_x / 2, self.grid_range_y / 2)
                        
                        self.demo_moving_object['orientation'] = 0.0
                        log_demo(f"Demo started at position: ({self.demo_moving_object['position'].x:.1f}, {self.demo_moving_object['position'].y:.1f})")
                    return
                
                if 'toggle_distance_mode' in self.button_rects and self.button_rects['toggle_distance_mode'].collidepoint(event.pos):
                    if self.demo_moving_object['enabled']:
                        if self.demo_moving_object['distance_mode'] == 'auto':
                            self.demo_moving_object['distance_mode'] = 'manual'
                            sensor_devices = [device for device in self.device_manager.devices.values() 
                                              if device.device_type != "moving_object"]
                            for device in sensor_devices:
                                device_id = device.device_id
                                if device_id not in self.demo_moving_object['manual_distances']:
                                    if device_id in self.sensor_nodes:
                                        auto_dist = self.demo_moving_object['position'].distance_to(self.sensor_nodes[device_id].position)
                                        self.demo_moving_object['manual_distances'][device_id] = auto_dist
                                    else:
                                        self.demo_moving_object['manual_distances'][device_id] = 100.0
                        else:
                            self.demo_moving_object['distance_mode'] = 'auto'
                        log_demo(f"Distance mode switched to: {self.demo_moving_object['distance_mode']}")
                    return
                
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
                            
                            # Only log if distance actually changed
                            if new_dist != current_dist:
                                self.demo_moving_object['manual_distances'][device_id] = new_dist
                                print(f"Manual distance for {device_id} decreased to: {new_dist}")
                        return
                    
                    if plus_btn_key in self.button_rects and self.button_rects[plus_btn_key].collidepoint(event.pos):
                        if self.demo_moving_object['enabled'] and self.demo_moving_object['distance_mode'] == 'manual':
                            current_dist = self.demo_moving_object['manual_distances'].get(device_id, 100.0)
                            new_dist = min(500, current_dist + 10)
                            
                            # Only log if distance actually changed
                            if new_dist != current_dist:
                                self.demo_moving_object['manual_distances'][device_id] = new_dist
                                print(f"Manual distance for {device_id} increased to: {new_dist}")
                        return
                
                if 'orientation_widget' in self.button_rects and self.button_rects['orientation_widget'].collidepoint(event.pos):
                    widget_rect = self.button_rects['orientation_widget']
                    center_x = widget_rect.centerx
                    center_y = widget_rect.centery
                    
                    dx = event.pos[0] - center_x
                    dy = event.pos[1] - center_y
                    
                    angle_rad = math.atan2(-dy, dx)
                    angle_deg = math.degrees(angle_rad)
                    
                    orientation = (angle_deg + 90) % 360
                    
                    if self.demo_moving_object['enabled']:
                        self.demo_moving_object['orientation'] = orientation
                        print(f"Demo orientation set to: {orientation:.1f}°")
                    else:
                        self.moving_object_orientation = orientation
                        print(f"Moving object orientation set to: {orientation:.1f}°")
                    return
                
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
                
                if event.pos[0] > self.left_width + 20:
                    sensor_devices = [device for device in self.device_manager.devices.values() 
                                      if device.device_type != "moving_object"]
                    
                    clicked_node = None
                    for node_id, node in self.sensor_nodes.items():
                        if any(device.device_id == node_id for device in sensor_devices) or node_id.startswith('sensor_'):
                            node_x = self.grid_origin.x + node.position.x * self.pixels_per_cm_x
                            node_y = self.grid_origin.y - node.position.y * self.pixels_per_cm_y
                            
                            distance = math.sqrt((event.pos[0] - node_x)**2 + (event.pos[1] - node_y)**2)
                            if distance < 25:
                                clicked_node = node_id
                                break
                    
                    if clicked_node:
                        if self.selected_node == clicked_node:
                            self.selected_node = None
                            print(f"🔄 Deselected sensor node: {clicked_node}")
                        else:
                            self.selected_node = clicked_node
                            print(f"✅ Selected sensor node: {clicked_node} for repositioning")
                        return
                    else:
                        if self.selected_node:
                            grid_x = (event.pos[0] - self.grid_origin.x) / self.pixels_per_cm_x
                            grid_y = (self.grid_origin.y - event.pos[1]) / self.pixels_per_cm_y
                            
                            margin = 5
                            grid_x = max(margin, min(grid_x, self.grid_range_x - margin))
                            grid_y = max(margin, min(grid_y, self.grid_range_y - margin))
                            
                            old_pos = self.sensor_nodes[self.selected_node].position
                            self.sensor_nodes[self.selected_node].position = Point2D(grid_x, grid_y)
                            
                            print(f"📍 Moved sensor node {self.selected_node}: ({old_pos.x:.1f}, {old_pos.y:.1f}) → ({grid_x:.1f}, {grid_y:.1f})")
                            
                            self.selected_node = None
                            return
        
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                if self.dragging_node:
                    node = self.sensor_nodes[self.dragging_node]
                    print(f"✅ Sensor node {self.dragging_node} moved to: ({node.position.x:.1f}, {node.position.y:.1f})")
                    
                    margin = 10
                    if (node.position.x < margin or node.position.x > self.grid_range_x - margin or 
                        node.position.y < margin or node.position.y > self.grid_range_y - margin):
                        print(f"⚠️ Node position adjusted to stay within boundaries")
                        node.position.x = max(margin, min(node.position.x, self.grid_range_x - margin))
                        node.position.y = max(margin, min(node.position.y, self.grid_range_y - margin))
                        print(f"📍 Final position after boundary adjustment: ({node.position.x:.1f}, {node.position.y:.1f})")
                    
                    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
                    self.dragging_node = None
        
        elif event.type == pygame.KEYDOWN:
            print(f"Simulation page received key event: {pygame.key.name(event.key)}")
            print(f"Demo moving object enabled: {self.demo_moving_object['enabled']}")
            
            if event.key == pygame.K_ESCAPE:
                if self.selected_node:
                    print(f"🔄 Deselected sensor node: {self.selected_node} (Escape key)")
                    self.selected_node = None
                    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
                    return
            
            if self.demo_moving_object['enabled']:
                if event.key == pygame.K_LEFT:
                    self.demo_moving_object['orientation'] = (self.demo_moving_object['orientation'] + 15) % 360
                    print(f"Left arrow pressed (counterclockwise +15°), new orientation: {self.demo_moving_object['orientation']}°")
                elif event.key == pygame.K_RIGHT:
                    self.demo_moving_object['orientation'] = (self.demo_moving_object['orientation'] - 15) % 360
                    print(f"Right arrow pressed (clockwise -15°), new orientation: {self.demo_moving_object['orientation']}°")
                elif event.key == pygame.K_UP:
                    angle_rad = math.radians(self.demo_moving_object['orientation'] - 90)
                    new_x = self.demo_moving_object['position'].x + 10 * math.cos(angle_rad)
                    new_y = self.demo_moving_object['position'].y - 10 * math.sin(angle_rad)
                    
                    new_x = max(10, min(new_x, self.grid_range_x - 10))
                    new_y = max(10, min(new_y, self.grid_range_y - 10))
                    
                    self.demo_moving_object['position'] = Point2D(new_x, new_y)
                    print(f"Moved forward to: ({new_x:.1f}, {new_y:.1f})")
                elif event.key == pygame.K_DOWN:
                    angle_rad = math.radians(self.demo_moving_object['orientation'] - 90 + 180)
                    new_x = self.demo_moving_object['position'].x + 10 * math.cos(angle_rad)
                    new_y = self.demo_moving_object['position'].y - 10 * math.sin(angle_rad)
                    
                    new_x = max(10, min(new_x, self.grid_range_x - 10))
                    new_y = max(10, min(new_y, self.grid_range_y - 10))
                    
                    self.demo_moving_object['position'] = Point2D(new_x, new_y)
                    print(f"Moved backward to: ({new_x:.1f}, {new_y:.1f})")
    
    def update_real_moving_object_orientation(self, orientation: float):
        """Update real moving object orientation from Bluetooth device data"""
        self.raw_moving_object_orientation = orientation
        
        calibrated_orientation = (orientation + self.orientation_offset) % 360
        
        self.moving_object_orientation = calibrated_orientation
        
        print(f"🧭 Real moving object orientation updated: raw={orientation:.1f}°, offset={self.orientation_offset:.1f}°, calibrated={calibrated_orientation:.1f}°")
    
    def update(self, dt: float):
        """Update simulation state"""
        for node_id, node in self.sensor_nodes.items():
            if node_id in self.device_manager.devices:
                device = self.device_manager.devices[node_id]
                node.current_distance = device.last_distance
        
        if self.moving_object_device and self.moving_object_device in self.device_manager.devices:
            device = self.device_manager.devices[self.moving_object_device]
            self.moving_object_orientation += dt * 10
            self.moving_object_orientation %= 360
        
        if self.demo_moving_object['enabled']:
            pass
    
    def update_settings(self, distance_settings: Dict):
        """Update grid settings"""
        self.max_distance = distance_settings.get('max_distance', 200)
        if 'grid_range_x' in distance_settings:
            self.grid_range_x = distance_settings['grid_range_x']
        if 'grid_range_y' in distance_settings:
            self.grid_range_y = distance_settings['grid_range_y']
    
    def handle_click(self, pos: Tuple[int, int]):
        """Handle click events - compatibility wrapper for UI manager"""
        class MockEvent:
            def __init__(self, pos):
                self.type = pygame.MOUSEBUTTONDOWN
                self.button = 1
                self.pos = pos
        
        self.handle_event(MockEvent(pos))
