"""
pygame_app/src/distance_mapping_editor.py
Advanced Distance Mapping Editor with Multiple Algorithms
"""
import pygame
import pygame.freetype
import math
from typing import Dict, Optional, Tuple, Callable
from enum import Enum

try:
    from .config import Config
    DEBUG_UI = Config.DEBUG.get('PRINT_UI_INTERACTIONS', True)
except:
    DEBUG_UI = True

class DecayType(Enum):
    LINEAR = "Linear"
    EXPONENTIAL = "Exponential"
    LOGARITHMIC = "Logarithmic"
    INVERSE_SQUARE = "Inverse Square Law"
    CUSTOM_CURVE = "Custom Curve"
    SIGMOID = "Sigmoid (S-Curve)"
    QUADRATIC = "Quadratic"

class DistanceMappingEditor:
    def __init__(self, parent_screen: pygame.Surface, current_settings: Dict):
        self.parent_screen = parent_screen
        self.parent_size = parent_screen.get_size()
        self.current_settings = current_settings.copy()
        
        # Window properties
        self.window_width = 1000
        self.window_height = 800  # Increased for enhanced preview
        self.window_rect = pygame.Rect(
            (self.parent_size[0] - self.window_width) // 2,
            (self.parent_size[1] - self.window_height) // 2,
            self.window_width,
            self.window_height
        )
        
        # Initialize fonts
        pygame.freetype.init()
        self.font_title = pygame.freetype.Font(None, 24)
        self.font_body = pygame.freetype.Font(None, 16)
        self.font_small = pygame.freetype.Font(None, 14)
        
        # UI State
        self.running = True
        self.mouse_pos = (0, 0)
        self.active_input = None
        self._cancelled = False
        self.input_values = {
            'min_distance': str(current_settings.get('min_distance', 5.0)),
            'max_distance': str(current_settings.get('max_distance', 150.0)),
            'min_volume': str(current_settings.get('min_volume', 5.0)),
            'max_volume': str(current_settings.get('max_volume', 100.0)),
            'curve_steepness': str(current_settings.get('curve_steepness', 2.0)),
            'data_history_duration': str(current_settings.get('data_history_duration', 60.0))
        }
        
        # Get current decay type
        current_decay = current_settings.get('decay_type', 'linear').lower()
        self.selected_decay = DecayType.LINEAR
        for decay in DecayType:
            if decay.value.lower().replace(" ", "_") == current_decay.replace(" ", "_"):
                self.selected_decay = decay
                break
        
        # UI Elements
        self.input_rects = {}
        self.button_rects = {}
        self.decay_button_rects = {}
        
        # Colors
        self.colors = {
            'background': (25, 30, 40),
            'surface': (35, 42, 55),
            'surface_light': (45, 52, 65),
            'primary': (70, 130, 200),
            'secondary': (120, 180, 80),
            'text': (240, 245, 250),
            'text_secondary': (180, 190, 200),
            'border': (60, 70, 85),
            'input_bg': (20, 25, 35),
            'input_active': (50, 60, 75),
            'error': (220, 80, 80),
            'success': (80, 180, 120)
        }
        
        # Background overlay
        self.overlay = pygame.Surface(self.parent_size)
        self.overlay.set_alpha(180)
        self.overlay.fill((0, 0, 0))
    
    def run(self) -> Optional[Dict]:
        """Run the editor window and return updated settings or None if cancelled"""
        clock = pygame.time.Clock()
        
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    return None
                elif event.type == pygame.MOUSEMOTION:
                    self.mouse_pos = (
                        event.pos[0] - self.window_rect.x,
                        event.pos[1] - self.window_rect.y
                    )
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        if self.window_rect.collidepoint(event.pos):
                            modal_pos = (
                                event.pos[0] - self.window_rect.x,
                                event.pos[1] - self.window_rect.y
                            )
                            self._handle_click(modal_pos)
                        else:
                            # Click outside - close window
                            self.running = False
                            return None
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                        return None
                    elif self.active_input:
                        self._handle_key_input(event)
            
            # Render
            self._render()
            
            # Update display
            pygame.display.flip()
            clock.tick(60)
        
        # Return updated settings if Apply was clicked, None if cancelled
        if hasattr(self, '_cancelled') and self._cancelled:
            print("Distance Editor: Cancelled - no changes applied")
            return None
        else:
            print("Distance Editor: Completed - returning updated settings")
            return self._get_updated_settings()
    
    def _handle_click(self, pos: Tuple[int, int]):
        """Handle mouse clicks"""
        if DEBUG_UI:
            print(f"Distance Editor: Click at modal position: {pos}")
            print(f"Distance Editor: Available input rects: {list(self.input_rects.keys())}")
            print(f"Distance Editor: Available button rects: {list(self.button_rects.keys())}")
        
        # Check input fields (these should use modal coordinates)
        for field_name, rect in self.input_rects.items():
            # Convert rect back to modal coordinates for comparison
            modal_rect = pygame.Rect(rect.x - self.window_rect.x, rect.y - self.window_rect.y, rect.width, rect.height)
            if DEBUG_UI:
                print(f"Distance Editor: Checking input field {field_name} at {modal_rect}")
            if modal_rect.collidepoint(pos):
                self.active_input = field_name
                if DEBUG_UI:
                    print(f"Distance Editor: Selected input field '{field_name}'")
                return
        
        # Clear active input if clicking elsewhere
        was_active = self.active_input
        self.active_input = None
        if was_active and DEBUG_UI:
            print(f"Distance Editor: Cleared active input field '{was_active}'")
        
        # Check decay type buttons
        for decay_type, rect in self.decay_button_rects.items():
            modal_rect = pygame.Rect(rect.x - self.window_rect.x, rect.y - self.window_rect.y, rect.width, rect.height)
            if DEBUG_UI:
                print(f"Distance Editor: Checking decay button '{decay_type.value}' at {modal_rect}")
            if modal_rect.collidepoint(pos):
                old_decay = self.selected_decay
                self.selected_decay = decay_type
                print(f"Distance Editor: Changed algorithm from '{old_decay.value}' to '{decay_type.value}'")
                return
        
        # Check action buttons
        for button_name, rect in self.button_rects.items():
            modal_rect = pygame.Rect(rect.x - self.window_rect.x, rect.y - self.window_rect.y, rect.width, rect.height)
            if DEBUG_UI:
                print(f"Distance Editor: Checking action button '{button_name}' at {modal_rect}")
            if modal_rect.collidepoint(pos):
                print(f"Distance Editor: Action button clicked - '{button_name}'")
                if button_name == 'apply':
                    if self._validate_inputs():
                        print("Distance Editor: Settings validated successfully - applying changes")
                        self.running = False
                    else:
                        print("Distance Editor: Invalid settings detected - cannot apply")
                elif button_name == 'cancel':
                    print("Distance Editor: Cancelled by user - discarding changes")
                    self._cancelled = True
                    self.running = False
                elif button_name == 'test':
                    print("Distance Editor: Testing current settings")
                    self._test_current_settings()
                return
        
        if DEBUG_UI:
            print("Distance Editor: Click not handled by any UI element")
    
    def _handle_key_input(self, event):
        """Handle keyboard input for text fields"""
        if not self.active_input:
            return
        
        if event.key == pygame.K_BACKSPACE:
            self.input_values[self.active_input] = self.input_values[self.active_input][:-1]
        elif event.key == pygame.K_RETURN or event.key == pygame.K_TAB:
            self.active_input = None
        else:
            # Only allow numbers and decimal point
            if event.unicode.isdigit() or (event.unicode == '.' and '.' not in self.input_values[self.active_input]):
                self.input_values[self.active_input] += event.unicode
    
    def _validate_inputs(self) -> bool:
        """Validate all input values"""
        try:
            min_dist = float(self.input_values['min_distance'])
            max_dist = float(self.input_values['max_distance'])
            min_vol = float(self.input_values['min_volume'])
            max_vol = float(self.input_values['max_volume'])
            steepness = float(self.input_values['curve_steepness'])
            history_duration = float(self.input_values['data_history_duration'])
            
            # Validation rules
            if min_dist < 0 or max_dist < 0 or min_vol < 0 or max_vol < 0:
                return False
            if min_dist >= max_dist:
                return False
            if min_vol > 100 or max_vol > 100:
                return False
            if steepness < 0.1 or steepness > 10:
                return False
            if history_duration < 1.0 or history_duration > 180.0:
                return False
            
            return True
        except ValueError:
            return False
    
    def _get_updated_settings(self) -> Dict:
        """Get the updated settings dictionary"""
        if not self._validate_inputs():
            return self.current_settings
        
        return {
            'min_distance': float(self.input_values['min_distance']),
            'max_distance': float(self.input_values['max_distance']),
            'min_volume': float(self.input_values['min_volume']),
            'max_volume': float(self.input_values['max_volume']),
            'decay_type': self.selected_decay.value.lower().replace(" ", "_"),
            'curve_steepness': float(self.input_values['curve_steepness']),
            'max_graph_distance': float(self.input_values['max_distance']) + 50,
            'data_history_duration': float(self.input_values['data_history_duration'])
        }
    
    def _render(self):
        """Render the editor window"""
        # Draw overlay
        self.parent_screen.blit(self.overlay, (0, 0))
        
        # Create window surface
        window_surface = pygame.Surface((self.window_width, self.window_height))
        window_surface.fill(self.colors['background'])
        
        # Draw window border
        pygame.draw.rect(window_surface, self.colors['primary'], 
                        pygame.Rect(0, 0, self.window_width, self.window_height), 3, border_radius=10)
        
        # Title
        self.font_title.render_to(window_surface, (20, 20), 
                                "Distance Mapping Configuration", self.colors['text'])
        
        # Left side: Settings
        left_column_width = 460
        
        # Distance Settings Section
        self._render_section(window_surface, 60, "Distance Range Settings", [
            ("Minimum Distance (cm)", 'min_distance', "Closest detectable distance"),
            ("Maximum Distance (cm)", 'max_distance', "Farthest detectable distance")
        ], left_column_width)
        
        # Volume Settings Section
        self._render_section(window_surface, 180, "Volume Range Settings", [
            ("Minimum Volume (%)", 'min_volume', "Volume at maximum distance"),
            ("Maximum Volume (%)", 'max_volume', "Volume at minimum distance")
        ], left_column_width)
        
        # Decay Algorithm Section
        self._render_decay_selection(window_surface, 300, left_column_width)
        
        # Right side: Preview Graph
        self._render_preview_graph(window_surface, 60, left_column_width + 20)
        
        # Action Buttons
        self._render_action_buttons(window_surface)
        
        # Blit window to parent screen
        self.parent_screen.blit(window_surface, self.window_rect)
    
    def _render_section(self, surface: pygame.Surface, y_pos: int, title: str, fields: list, max_width: int = 460):
        """Render a settings section with input fields"""
        # Section title
        self.font_body.render_to(surface, (20, y_pos), title, self.colors['text'])
        
        y_pos += 30
        for label, field_key, hint in fields:
            # Label
            self.font_small.render_to(surface, (30, y_pos), label, self.colors['text_secondary'])
            
            # Input field
            input_rect = pygame.Rect(280, y_pos - 5, 120, 30)
            is_active = self.active_input == field_key
            
            # Background
            bg_color = self.colors['input_active'] if is_active else self.colors['input_bg']
            pygame.draw.rect(surface, bg_color, input_rect, border_radius=5)
            pygame.draw.rect(surface, self.colors['border'], input_rect, 1, border_radius=5)
            
            # Value
            value_color = self.colors['text'] if self._is_valid_number(self.input_values[field_key]) else self.colors['error']
            self.font_body.render_to(surface, (input_rect.x + 8, input_rect.y + 8), 
                                   self.input_values[field_key], value_color)
            
            self.input_rects[field_key] = input_rect.move(self.window_rect.x, self.window_rect.y)
            y_pos += 40
    
    def _render_decay_selection(self, surface: pygame.Surface, y_pos: int, max_width: int = 460):
        """Render decay algorithm selection"""
        self.font_body.render_to(surface, (20, y_pos), "Volume Decay Algorithm", self.colors['text'])
        
        # Decay type buttons - arrange in a 3x2 grid
        x_pos = 30
        y_pos += 30
        button_width = 130
        button_height = 35
        buttons_per_row = 3
        
        for i, decay_type in enumerate(DecayType):
            if i % buttons_per_row == 0 and i > 0:
                y_pos += button_height + 10
                x_pos = 30
            elif i > 0:
                x_pos += button_width + 10
            
            # Adjust for 3 columns
            if i % buttons_per_row == 0:
                x_pos = 30
            
            button_rect = pygame.Rect(x_pos, y_pos, button_width, button_height)
            
            # Button appearance
            is_selected = decay_type == self.selected_decay
            is_hovered = button_rect.collidepoint(self.mouse_pos)
            
            if is_selected:
                bg_color = self.colors['primary']
                text_color = self.colors['text']
            elif is_hovered:
                bg_color = self.colors['surface_light']
                text_color = self.colors['text']
            else:
                bg_color = self.colors['surface']
                text_color = self.colors['text_secondary']
            
            pygame.draw.rect(surface, bg_color, button_rect, border_radius=5)
            pygame.draw.rect(surface, self.colors['border'], button_rect, 1, border_radius=5)
            
            # Button text - truncate if needed
            display_text = decay_type.value
            if len(display_text) > 12:
                # Abbreviate some longer names
                if "Inverse Square" in display_text:
                    display_text = "Inverse Sq."
                elif "Sigmoid" in display_text:
                    display_text = "Sigmoid"
                elif "Custom" in display_text:
                    display_text = "Custom"
            
            text_rect = self.font_small.get_rect(display_text)
            text_x = button_rect.centerx - text_rect.width // 2
            text_y = button_rect.centery - text_rect.height // 2
            self.font_small.render_to(surface, (text_x, text_y), display_text, text_color)
            
            self.decay_button_rects[decay_type] = button_rect.move(self.window_rect.x, self.window_rect.y)
        
        # Curve steepness for applicable algorithms
        if self.selected_decay in [DecayType.EXPONENTIAL, DecayType.SIGMOID, DecayType.CUSTOM_CURVE]:
            y_pos += button_height + 20
            self.font_small.render_to(surface, (30, y_pos), "Curve Steepness", self.colors['text_secondary'])
            
            input_rect = pygame.Rect(180, y_pos - 5, 100, 30)
            is_active = self.active_input == 'curve_steepness'
            
            bg_color = self.colors['input_active'] if is_active else self.colors['input_bg']
            pygame.draw.rect(surface, bg_color, input_rect, border_radius=5)
            pygame.draw.rect(surface, self.colors['border'], input_rect, 1, border_radius=5)
            
            self.font_body.render_to(surface, (input_rect.x + 8, input_rect.y + 8), 
                                   self.input_values['curve_steepness'], self.colors['text'])
            
            self.font_small.render_to(surface, (290, y_pos), "(0.1 - 10.0)", self.colors['text_secondary'])
            
            self.input_rects['curve_steepness'] = input_rect.move(self.window_rect.x, self.window_rect.y)
            
            # Data History Duration field
            y_pos += 50
            self.font_small.render_to(surface, (30, y_pos), "Chart History Duration (s)", self.colors['text_secondary'])
            
            input_rect = pygame.Rect(180, y_pos - 5, 100, 30)
            is_active = self.active_input == 'data_history_duration'
            
            bg_color = self.colors['input_active'] if is_active else self.colors['input_bg']
            pygame.draw.rect(surface, bg_color, input_rect, border_radius=5)
            pygame.draw.rect(surface, self.colors['border'], input_rect, 1, border_radius=5)
            
            self.font_body.render_to(surface, (input_rect.x + 8, input_rect.y + 8), 
                                   self.input_values['data_history_duration'], self.colors['text'])
            
            self.font_small.render_to(surface, (290, y_pos), "(1 - 180)", self.colors['text_secondary'])
            
            self.input_rects['data_history_duration'] = input_rect.move(self.window_rect.x, self.window_rect.y)
    
    def _render_preview_graph(self, surface: pygame.Surface, y_pos: int, x_pos: int = 480):
        """Render an enhanced preview graph with detailed analysis"""
        graph_width = 480
        graph_height = 400  # Increased height for more details
        graph_rect = pygame.Rect(x_pos, y_pos, graph_width, graph_height)
        
        # Graph background with gradient effect
        pygame.draw.rect(surface, self.colors['input_bg'], graph_rect, border_radius=8)
        pygame.draw.rect(surface, self.colors['primary'], graph_rect, width=2, border_radius=8)
        
        # Title with algorithm name
        title_text = f"Volume Mapping Preview - {self.selected_decay.value}"
        self.font_body.render_to(surface, (graph_rect.x + 15, graph_rect.y + 10), 
                                title_text, self.colors['text'])
        
        # Algorithm description
        algorithm_descriptions = {
            DecayType.LINEAR: "Constant rate of volume decrease",
            DecayType.EXPONENTIAL: "Rapid initial drop, gradual at distance", 
            DecayType.LOGARITHMIC: "Gradual initial drop, rapid at distance",
            DecayType.INVERSE_SQUARE: "Physically accurate 1/d² law",
            DecayType.SIGMOID: "S-shaped smooth transition curve",
            DecayType.QUADRATIC: "Parabolic volume decrease",
            DecayType.CUSTOM_CURVE: "Adjustable power function curve"
        }
        
        desc_text = algorithm_descriptions.get(self.selected_decay, "Volume mapping function")
        self.font_small.render_to(surface, (graph_rect.x + 15, graph_rect.y + 30), 
                                desc_text, self.colors['text_secondary'])
        
        # Mathematical formula display
        formula_y = graph_rect.y + 50
        formula_text = self._get_formula_text()
        self.font_small.render_to(surface, (graph_rect.x + 15, formula_y), 
                                f"Formula: {formula_text}", self.colors['primary'])
        
        
        if self._validate_inputs():
            # Get values
            min_dist = float(self.input_values['min_distance'])
            max_dist = float(self.input_values['max_distance'])
            min_vol = float(self.input_values['min_volume'])
            max_vol = float(self.input_values['max_volume'])
            steepness = float(self.input_values['curve_steepness'])
            
            # Analysis panel
            analysis_y = graph_rect.y + 75
            self._render_curve_analysis(surface, graph_rect, analysis_y, min_dist, max_dist, min_vol, max_vol, steepness)
            
            # Draw axes
            margin = 60
            axis_rect = pygame.Rect(graph_rect.x + margin, graph_rect.y + 140,
                                  graph_rect.width - margin - 30, graph_rect.height - 180)
            
            # Y-axis (volume)
            pygame.draw.line(surface, self.colors['text_secondary'],
                           (axis_rect.left, axis_rect.top), (axis_rect.left, axis_rect.bottom), 2)
            # X-axis (distance)
            pygame.draw.line(surface, self.colors['text_secondary'],
                           (axis_rect.left, axis_rect.bottom), (axis_rect.right, axis_rect.bottom), 2)
            
            # Grid lines
            for i in range(1, 5):
                y = axis_rect.top + i * axis_rect.height // 5
                pygame.draw.line(surface, self.colors['surface'], 
                               (axis_rect.left + 1, y), (axis_rect.right, y), 1)
            
            for i in range(1, 5):
                x = axis_rect.left + i * axis_rect.width // 5
                pygame.draw.line(surface, self.colors['surface'], 
                               (x, axis_rect.top), (x, axis_rect.bottom - 1), 1)
            
            # Y-axis labels (volume)
            self.font_small.render_to(surface, (axis_rect.left - 45, axis_rect.top - 5), 
                                    f"{max_vol:.0f}%", self.colors['text_secondary'])
            self.font_small.render_to(surface, (axis_rect.left - 35, axis_rect.bottom - 10), 
                                    f"{min_vol:.0f}%", self.colors['text_secondary'])
            
            # X-axis labels (distance)
            self.font_small.render_to(surface, (axis_rect.left - 10, axis_rect.bottom + 15), 
                                    f"{min_dist:.0f}", self.colors['text_secondary'])
            self.font_small.render_to(surface, (axis_rect.right - 25, axis_rect.bottom + 15), 
                                    f"{max_dist:.0f}", self.colors['text_secondary'])
            
            # Draw the curve with enhanced visualization
            points = []
            key_points = []  # Store key measurement points
            
            for i in range(axis_rect.width):
                x_ratio = i / axis_rect.width
                distance = min_dist + x_ratio * (max_dist - min_dist)
                
                # Calculate volume based on selected algorithm
                volume = self._calculate_volume(distance, min_dist, max_dist, 
                                              min_vol, max_vol, self.selected_decay, steepness)
                
                y_ratio = (volume - min_vol) / (max_vol - min_vol) if max_vol != min_vol else 0
                y_ratio = max(0, min(1, y_ratio))
                
                x = axis_rect.left + i
                y = axis_rect.bottom - int(y_ratio * axis_rect.height)
                points.append((x, y))
                
                # Mark key points (quarters)
                if i % (axis_rect.width // 4) == 0 and i > 0:
                    key_points.append((x, y, distance, volume))
            
            # Draw main curve
            if len(points) > 1:
                pygame.draw.lines(surface, self.colors['primary'], False, points, 3)
            
            # Draw key measurement points
            for x, y, distance, volume in key_points:
                # Draw point
                pygame.draw.circle(surface, self.colors['secondary'], (int(x), int(y)), 4)
                pygame.draw.circle(surface, self.colors['text'], (int(x), int(y)), 2)
                
                # Draw value label
                label_text = f"{distance:.0f}cm\n{volume:.0f}%"
                label_lines = label_text.split('\n')
                
                for j, line in enumerate(label_lines):
                    label_y = y - 25 + j * 12
                    text_rect = self.font_small.get_rect(line)
                    label_x = x - text_rect.width // 2
                    
                    # Background for readability
                    bg_rect = pygame.Rect(label_x - 2, label_y - 2, text_rect.width + 4, text_rect.height + 4)
                    pygame.draw.rect(surface, self.colors['input_bg'], bg_rect, border_radius=2)
                    
                    self.font_small.render_to(surface, (label_x, label_y), line, self.colors['text'])
            
            # Draw curve fill area for better visualization
            if len(points) > 2:
                # Create filled area under curve
                fill_points = points + [(axis_rect.right, axis_rect.bottom), (axis_rect.left, axis_rect.bottom)]
                fill_surface = pygame.Surface((axis_rect.width, axis_rect.height), pygame.SRCALPHA)
                fill_color = (*self.colors['primary'], 30)  # Semi-transparent
                
                # Adjust points for fill surface
                adjusted_points = [(x - axis_rect.left, y - axis_rect.top) for x, y in fill_points]
                if len(adjusted_points) > 2:
                    pygame.draw.polygon(fill_surface, fill_color, adjusted_points)
                    surface.blit(fill_surface, (axis_rect.left, axis_rect.top))
            
            # Add hover interaction point if mouse is over graph
            if axis_rect.collidepoint(self.mouse_pos):
                mouse_x_ratio = (self.mouse_pos[0] - axis_rect.left) / axis_rect.width
                hover_distance = min_dist + mouse_x_ratio * (max_dist - min_dist)
                hover_volume = self._calculate_volume(hover_distance, min_dist, max_dist, 
                                                    min_vol, max_vol, self.selected_decay, steepness)
                
                hover_y_ratio = (hover_volume - min_vol) / (max_vol - min_vol) if max_vol > min_vol else 0
                hover_y = axis_rect.bottom - int(hover_y_ratio * axis_rect.height)
                
                # Draw hover point
                pygame.draw.circle(surface, self.colors['error'], (self.mouse_pos[0], hover_y), 6)
                pygame.draw.circle(surface, self.colors['text'], (self.mouse_pos[0], hover_y), 3)
                
                # Draw hover info
                hover_text = f"{hover_distance:.1f}cm -> {hover_volume:.1f}%"
                hover_bg_rect = pygame.Rect(self.mouse_pos[0] - 50, hover_y - 35, 100, 20)
                pygame.draw.rect(surface, self.colors['surface'], hover_bg_rect, border_radius=4)
                pygame.draw.rect(surface, self.colors['border'], hover_bg_rect, width=1, border_radius=4)
                
                text_rect = self.font_small.get_rect(hover_text)
                text_x = self.mouse_pos[0] - text_rect.width // 2
                self.font_small.render_to(surface, (text_x, hover_y - 30), hover_text, self.colors['text'])
    
    def _calculate_volume(self, distance: float, min_dist: float, max_dist: float,
                         min_vol: float, max_vol: float, decay_type: DecayType, steepness: float) -> float:
        """Calculate volume based on distance and decay algorithm"""
        if distance <= min_dist:
            return max_vol
        if distance >= max_dist:
            return min_vol
        
        # Normalize distance to 0-1 range
        t = (distance - min_dist) / (max_dist - min_dist)
        
        if decay_type == DecayType.LINEAR:
            factor = 1.0 - t
            
        elif decay_type == DecayType.EXPONENTIAL:
            # Exponential decay: e^(-steepness * t)
            factor = math.exp(-steepness * t)
            
        elif decay_type == DecayType.LOGARITHMIC:
            # Logarithmic decay: 1 - log(1 + steepness*t) / log(1 + steepness)
            if steepness <= 0:
                steepness = 1.0
            factor = 1.0 - math.log(1 + steepness * t) / math.log(1 + steepness)
            
        elif decay_type == DecayType.INVERSE_SQUARE:
            # True inverse square law: 1/d²
            # Map t to actual distance ratio, then apply inverse square
            actual_distance_ratio = 1.0 + t * (steepness if steepness > 0 else 4.0)
            factor = 1.0 / (actual_distance_ratio * actual_distance_ratio)
            # Normalize to 0-1 range
            max_factor = 1.0  # At minimum distance
            min_factor = 1.0 / ((1.0 + (steepness if steepness > 0 else 4.0)) ** 2)
            factor = (factor - min_factor) / (max_factor - min_factor)
            factor = max(0.0, min(1.0, factor))
            
        elif decay_type == DecayType.SIGMOID:
            # S-curve using sigmoid function: 1 / (1 + e^(steepness*(t-0.5)))
            factor = 1.0 / (1.0 + math.exp(steepness * (t - 0.5)))
            
        elif decay_type == DecayType.QUADRATIC:
            # Quadratic decay: (1-t)²
            factor = (1.0 - t) ** 2
            
        elif decay_type == DecayType.CUSTOM_CURVE:
            # Custom curve: adjustable power function
            power = max(0.1, steepness)
            factor = (1.0 - t) ** power
            
        else:
            factor = 1.0 - t  # Default to linear
        
        # Ensure factor is in valid range
        factor = max(0.0, min(1.0, factor))
        
        return min_vol + factor * (max_vol - min_vol)
    
    def _render_action_buttons(self, surface: pygame.Surface):
        """Render action buttons"""
        button_y = self.window_height - 70
        button_width = 120
        button_height = 40
        
        # Test button
        test_rect = pygame.Rect(30, button_y, button_width, button_height)
        self._render_button(surface, test_rect, "Test", 'test', self.colors['secondary'])
        
        # Apply button
        apply_rect = pygame.Rect(self.window_width - 260, button_y, button_width, button_height)
        apply_color = self.colors['success'] if self._validate_inputs() else self.colors['surface']
        self._render_button(surface, apply_rect, "Apply", 'apply', apply_color)
        
        # Cancel button
        cancel_rect = pygame.Rect(self.window_width - 130, button_y, button_width, button_height)
        self._render_button(surface, cancel_rect, "Cancel", 'cancel', self.colors['error'])
    
    def _render_button(self, surface: pygame.Surface, rect: pygame.Rect, text: str, key: str, color):
        """Render a button"""
        is_hovered = rect.collidepoint(self.mouse_pos)
        
        if is_hovered:
            hover_color = tuple(min(255, c + 20) for c in color)
            pygame.draw.rect(surface, hover_color, rect, border_radius=5)
        else:
            pygame.draw.rect(surface, color, rect, border_radius=5)
        
        pygame.draw.rect(surface, self.colors['border'], rect, 1, border_radius=5)
        
        # Text
        text_rect = self.font_body.get_rect(text)
        text_x = rect.centerx - text_rect.width // 2
        text_y = rect.centery - text_rect.height // 2
        self.font_body.render_to(surface, (text_x, text_y), text, self.colors['text'])
        
        self.button_rects[key] = rect.move(self.window_rect.x, self.window_rect.y)
    
    def _is_valid_number(self, value: str) -> bool:
        """Check if a string is a valid number"""
        try:
            float(value)
            return True
        except ValueError:
            return False
    
    def _test_current_settings(self):
        """Test the current distance mapping settings with comprehensive analysis"""
        if not self._validate_inputs():
            print("Distance Editor: Cannot test - invalid input values")
            return
        
        min_dist = float(self.input_values['min_distance'])
        max_dist = float(self.input_values['max_distance'])
        min_vol = float(self.input_values['min_volume'])
        max_vol = float(self.input_values['max_volume'])
        steepness = float(self.input_values['curve_steepness'])
        
        print("\n" + "="*60)
        print("DISTANCE MAPPING TEST REPORT")
        print("="*60)
        print(f"Algorithm: {self.selected_decay.value}")
        print(f"Distance Range: {min_dist:.1f}cm to {max_dist:.1f}cm")
        print(f"Volume Range: {min_vol:.1f}% to {max_vol:.1f}%")
        print(f"Steepness Parameter: {steepness:.2f}")
        print(f"Mathematical Formula: {self._get_formula_text()}")
        print("-" * 60)
        
        # Comprehensive test points (10 points across range)
        test_points = 10
        test_distances = [min_dist + i * (max_dist - min_dist) / (test_points - 1) for i in range(test_points)]
        
        print("VOLUME MAPPING TABLE:")
        print("Distance (cm) | Volume (%) | Volume Change | Relative Position")
        print("-" * 60)
        
        previous_volume = None
        for i, dist in enumerate(test_distances):
            volume = self._calculate_volume(dist, min_dist, max_dist, min_vol, max_vol, 
                                          self.selected_decay, steepness)
            
            volume_change = ""
            if previous_volume is not None:
                change = volume - previous_volume
                volume_change = f"{change:+6.1f}%"
            else:
                volume_change = "    --   "
            
            position = f"{(i / (test_points - 1) * 100):5.1f}%"
            print(f"{dist:11.1f} | {volume:8.1f} | {volume_change} | {position}")
            previous_volume = volume
        
        print("-" * 60)
        
        # Curve analysis
        volumes = [self._calculate_volume(d, min_dist, max_dist, min_vol, max_vol, 
                                        self.selected_decay, steepness) for d in test_distances]
        
        volume_range = max(volumes) - min(volumes)
        avg_volume = sum(volumes) / len(volumes)
        midpoint_volume = volumes[len(volumes) // 2]
        
        # Calculate curve steepness (rate of change)
        max_change = max(abs(volumes[i] - volumes[i-1]) for i in range(1, len(volumes)))
        avg_change = sum(abs(volumes[i] - volumes[i-1]) for i in range(1, len(volumes))) / (len(volumes) - 1)
        
        print("CURVE ANALYSIS:")
        print(f"Total Volume Range: {volume_range:.1f}%")
        print(f"Average Volume Level: {avg_volume:.1f}%")
        print(f"Midpoint Volume: {midpoint_volume:.1f}%")
        print(f"Maximum Volume Change: {max_change:.1f}% per step")
        print(f"Average Volume Change: {avg_change:.1f}% per step")
        
        # Performance characteristics
        near_field_drop = max_vol - volumes[2]  # Volume drop in first 20%
        far_field_level = volumes[-3]  # Volume at 80% distance
        curve_smoothness = "High" if max_change < 10 else "Medium" if max_change < 20 else "Low"
        
        print(f"Near-field Drop (20%): {near_field_drop:.1f}%")
        print(f"Far-field Level (80%): {far_field_level:.1f}%")
        print(f"Curve Smoothness: {curve_smoothness}")
        
        # Recommendations
        print("-" * 60)
        print("RECOMMENDATIONS:")
        
        if self.selected_decay == DecayType.INVERSE_SQUARE:
            print("• Physically accurate for real-world audio propagation")
            print("• Best for realistic spatial audio simulation")
        elif self.selected_decay == DecayType.LINEAR:
            print("• Simple and predictable volume changes")
            print("• Good for consistent user experience")
        elif self.selected_decay == DecayType.EXPONENTIAL:
            print("• Rapid near-field changes, gradual far-field")
            print("• Suitable for dramatic audio effects")
        elif self.selected_decay == DecayType.SIGMOID:
            print("• Smooth transitions with natural feel")
            print("• Good balance between responsiveness and stability")
        
        if volume_range < 30:
            print("• Consider increasing volume range for better dynamic response")
        if max_change > 25:
            print("• Consider reducing steepness for smoother transitions")
        if avg_volume < 30:
            print("• Average volume is quite low - consider adjusting range")
        
        print("="*60)
        print("Test completed successfully - Configuration validated")
        print("="*60 + "\n")
    
    def _get_formula_text(self) -> str:
        """Get mathematical formula text for current algorithm"""
        formulas = {
            DecayType.LINEAR: "V = V_max - (V_max - V_min) * (d - d_min) / (d_max - d_min)",
            DecayType.EXPONENTIAL: "V = V_min + (V_max - V_min) * e^(-s * t)",
            DecayType.LOGARITHMIC: "V = V_min + (V_max - V_min) * (1 - log(1 + s*t) / log(1 + s))",
            DecayType.INVERSE_SQUARE: "V = V_min + (V_max - V_min) / d²",
            DecayType.SIGMOID: "V = V_min + (V_max - V_min) / (1 + e^(s*(t-0.5)))",
            DecayType.QUADRATIC: "V = V_min + (V_max - V_min) * (1 - t)²",
            DecayType.CUSTOM_CURVE: "V = V_min + (V_max - V_min) * (1 - t)^s"
        }
        return formulas.get(self.selected_decay, "V = f(d)")
    
    def _render_curve_analysis(self, surface: pygame.Surface, graph_rect: pygame.Rect, 
                              analysis_y: int, min_dist: float, max_dist: float, 
                              min_vol: float, max_vol: float, steepness: float):
        """Render detailed curve analysis"""
        # Analysis background
        analysis_rect = pygame.Rect(graph_rect.x + 15, analysis_y, graph_rect.width - 30, 55)
        pygame.draw.rect(surface, self.colors['surface'], analysis_rect, border_radius=4)
        pygame.draw.rect(surface, self.colors['border'], analysis_rect, width=1, border_radius=4)
        
        # Calculate key statistics
        test_distances = [
            min_dist,
            min_dist + (max_dist - min_dist) * 0.25,
            min_dist + (max_dist - min_dist) * 0.5,
            min_dist + (max_dist - min_dist) * 0.75,
            max_dist
        ]
        
        volumes = [self._calculate_volume(d, min_dist, max_dist, min_vol, max_vol, 
                                        self.selected_decay, steepness) for d in test_distances]
        
        # Find curve characteristics
        volume_range = max(volumes) - min(volumes)
        midpoint_volume = volumes[2]  # Volume at 50% distance
        curve_steepness_indicator = abs(volumes[1] - volumes[3]) / (max_vol - min_vol) if max_vol > min_vol else 0
        
        # Display statistics in two columns
        col1_x = analysis_rect.x + 10
        col2_x = analysis_rect.x + analysis_rect.width // 2 + 10
        text_y = analysis_y + 8
        
        # Column 1: Range and midpoint
        self.font_small.render_to(surface, (col1_x, text_y), 
                                f"Volume Range: {volume_range:.1f}%", self.colors['text'])
        self.font_small.render_to(surface, (col1_x, text_y + 15), 
                                f"Midpoint Vol: {midpoint_volume:.1f}%", self.colors['text'])
        self.font_small.render_to(surface, (col1_x, text_y + 30), 
                                f"Curve Shape: {self._get_curve_shape_description()}", self.colors['text'])
        
        # Column 2: Performance metrics  
        self.font_small.render_to(surface, (col2_x, text_y), 
                                f"Steepness Factor: {curve_steepness_indicator:.2f}", self.colors['text'])
        self.font_small.render_to(surface, (col2_x, text_y + 15), 
                                f"Near-field Drop: {max_vol - volumes[1]:.1f}%", self.colors['text'])
        self.font_small.render_to(surface, (col2_x, text_y + 30), 
                                f"Far-field Level: {volumes[3]:.1f}%", self.colors['text'])
    
    def _get_curve_shape_description(self) -> str:
        """Get curve shape description"""
        shape_descriptions = {
            DecayType.LINEAR: "Linear decline",
            DecayType.EXPONENTIAL: "Exponential drop", 
            DecayType.LOGARITHMIC: "Logarithmic curve",
            DecayType.INVERSE_SQUARE: "Inverse square",
            DecayType.SIGMOID: "S-shaped curve",
            DecayType.QUADRATIC: "Parabolic drop",
            DecayType.CUSTOM_CURVE: "Power function"
        }
        return shape_descriptions.get(self.selected_decay, "Custom curve")