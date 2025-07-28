"""
pygame_app/src/coordinate_editor.py
Coordinate Editor Modal Window for Sensor Nodes
"""
import pygame
import pygame.freetype
from typing import Optional, Tuple, Dict

class CoordinateEditor:
    """Modal window for editing sensor node coordinates"""
    
    def __init__(self, parent_screen: pygame.Surface, device_name: str, current_x: float, current_y: float, max_x: float, max_y: float):
        self.parent_screen = parent_screen
        self.parent_size = parent_screen.get_size()
        self.device_name = device_name
        self.current_x = current_x
        self.current_y = current_y
        self.max_x = max_x
        self.max_y = max_y
        
        # Modal settings
        self.modal_width = 420
        self.modal_height = 320
        self.modal_rect = pygame.Rect(
            (self.parent_size[0] - self.modal_width) // 2,
            (self.parent_size[1] - self.modal_height) // 2,
            self.modal_width,
            self.modal_height
        )
        
        # Colors
        self.colors = {
            'background': (25, 30, 40),
            'surface': (35, 42, 55),
            'surface_light': (50, 58, 70),
            'primary': (70, 130, 200),
            'primary_hover': (90, 150, 220),
            'success': (80, 180, 120),
            'error': (220, 80, 80),
            'text_primary': (240, 245, 250),
            'text_secondary': (180, 190, 200),
            'border': (60, 70, 85),
        }
        
        # Initialize fonts
        pygame.freetype.init()
        try:
            self.font_title = pygame.freetype.Font(None, 20)
            self.font_body = pygame.freetype.Font(None, 16)
            self.font_small = pygame.freetype.Font(None, 14)
        except Exception as e:
            print(f"Font initialization error: {e}")
            self.font_title = pygame.freetype.Font(None, 20)
            self.font_body = pygame.freetype.Font(None, 16)
            self.font_small = pygame.freetype.Font(None, 14)
        
        # Input states
        self.x_input = f"{current_x:.1f}" if current_x != int(current_x) else str(int(current_x))
        self.y_input = f"{current_y:.1f}" if current_y != int(current_y) else str(int(current_y))
        self.active_input = None  # 'x' or 'y'
        
        # UI elements
        self.button_rects = {}
        self.input_rects = {}
        self.mouse_pos = (0, 0)
        
        # Modal state
        self.running = True
        self.result = None
        
        # Create overlay
        self.overlay = pygame.Surface(self.parent_size)
        self.overlay.set_alpha(128)
        self.overlay.fill((0, 0, 0))
        
        # Create modal surface
        self.modal_surface = pygame.Surface((self.modal_width, self.modal_height))
    
    def run(self) -> Optional[Tuple[float, float]]:
        """Run the modal and return the new coordinates or None if cancelled"""
        clock = pygame.time.Clock()
        
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    return None
                elif event.type == pygame.MOUSEMOTION:
                    # Convert to modal coordinates
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
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                        return None
                    elif event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                        self._apply_changes()
                    elif self.active_input:
                        self._handle_text_input(event)
            
            # Render
            self._render()
            
            # Draw everything
            self.parent_screen.blit(self.overlay, (0, 0))
            self.parent_screen.blit(self.modal_surface, self.modal_rect)
            
            # Draw modal border
            pygame.draw.rect(self.parent_screen, self.colors['border'], self.modal_rect, 3, border_radius=10)
            
            pygame.display.flip()
            clock.tick(60)
        
        return self.result
    
    def _handle_click(self, pos: Tuple[int, int]):
        """Handle mouse clicks within the modal"""
        # Check input field clicks
        if 'x_input' in self.input_rects and self.input_rects['x_input'].collidepoint(pos):
            self.active_input = 'x'
            return
        
        if 'y_input' in self.input_rects and self.input_rects['y_input'].collidepoint(pos):
            self.active_input = 'y'
            return
        
        # Check button clicks
        if 'apply' in self.button_rects and self.button_rects['apply'].collidepoint(pos):
            self._apply_changes()
            return
        
        if 'cancel' in self.button_rects and self.button_rects['cancel'].collidepoint(pos):
            self.running = False
            return
        
        if 'center' in self.button_rects and self.button_rects['center'].collidepoint(pos):
            self._set_center()
            return
        
        # Click elsewhere deactivates input
        self.active_input = None
    
    def _handle_text_input(self, event: pygame.event.Event):
        """Handle text input for active field"""
        if not self.active_input:
            return
        
        current_text = self.x_input if self.active_input == 'x' else self.y_input
        
        if event.key == pygame.K_BACKSPACE:
            new_text = current_text[:-1]
        elif event.unicode.isdigit() or event.unicode == '.':
            # Limit length and allow only one decimal point
            if len(current_text) < 8 and (event.unicode != '.' or '.' not in current_text):
                new_text = current_text + event.unicode
            else:
                return
        else:
            return
        
        # Update the appropriate input
        if self.active_input == 'x':
            self.x_input = new_text
        else:
            self.y_input = new_text
    
    def _set_center(self):
        """Set coordinates to center of grid"""
        self.x_input = f"{self.max_x / 2:.1f}"
        self.y_input = f"{self.max_y / 2:.1f}"
    
    def _apply_changes(self):
        """Apply the changes and close the modal"""
        try:
            new_x = float(self.x_input) if self.x_input else self.current_x
            new_y = float(self.y_input) if self.y_input else self.current_y
            
            # Validate ranges
            new_x = max(0, min(new_x, self.max_x))
            new_y = max(0, min(new_y, self.max_y))
            
            self.result = (new_x, new_y)
            self.running = False
        except ValueError:
            # Invalid input, ignore
            pass
    
    def _render(self):
        """Render the modal content"""
        self.modal_surface.fill(self.colors['background'])
        self.button_rects.clear()
        self.input_rects.clear()
        
        padding = 20
        y_pos = padding
        
        # Title
        title = f"Edit Coordinates"
        self.font_title.render_to(self.modal_surface, (padding, y_pos), 
                                title, self.colors['text_primary'])
        y_pos += 30
        
        # Device name
        device_text = f"Device: {self.device_name}"
        self.font_body.render_to(self.modal_surface, (padding, y_pos), 
                               device_text, self.colors['text_secondary'])
        y_pos += 30
        
        # Description
        desc = f"Set position within grid (0 to {self.max_x:.0f}, 0 to {self.max_y:.0f}):"
        self.font_small.render_to(self.modal_surface, (padding, y_pos), 
                                desc, self.colors['text_secondary'])
        y_pos += 25
        
        # Current position info
        current_info = f"Current: ({self.current_x:.1f}, {self.current_y:.1f})"
        self.font_small.render_to(self.modal_surface, (padding, y_pos), 
                                current_info, self.colors['text_secondary'])
        y_pos += 30
        
        # X Coordinate input
        self.font_body.render_to(self.modal_surface, (padding, y_pos), 
                               "X Coordinate (cm):", self.colors['text_primary'])
        y_pos += 20
        
        x_rect = pygame.Rect(padding, y_pos, self.modal_width - padding * 2, 30)
        self._render_input_field(x_rect, 'x_input', self.x_input, self.active_input == 'x')
        y_pos += 40
        
        # Y Coordinate input
        self.font_body.render_to(self.modal_surface, (padding, y_pos), 
                               "Y Coordinate (cm):", self.colors['text_primary'])
        y_pos += 20
        
        y_rect = pygame.Rect(padding, y_pos, self.modal_width - padding * 2, 30)
        self._render_input_field(y_rect, 'y_input', self.y_input, self.active_input == 'y')
        y_pos += 50
        
        # Buttons
        button_width = 90
        button_height = 35
        button_spacing = 10
        
        # Center button
        center_rect = pygame.Rect(
            padding,
            self.modal_height - padding - button_height,
            button_width, button_height
        )
        self._render_button(center_rect, 'center', "Center", self.colors['primary'])
        
        # Cancel button
        cancel_rect = pygame.Rect(
            self.modal_width - padding - button_width * 2 - button_spacing,
            self.modal_height - padding - button_height,
            button_width, button_height
        )
        self._render_button(cancel_rect, 'cancel', "Cancel", self.colors['error'])
        
        # Apply button
        apply_rect = pygame.Rect(
            self.modal_width - padding - button_width,
            self.modal_height - padding - button_height,
            button_width, button_height
        )
        self._render_button(apply_rect, 'apply', "Apply", self.colors['success'])
    
    def _render_input_field(self, rect: pygame.Rect, key: str, text: str, is_active: bool):
        """Render an input field"""
        # Background
        bg_color = self.colors['surface_light'] if is_active else self.colors['surface']
        pygame.draw.rect(self.modal_surface, bg_color, rect, border_radius=5)
        
        # Border
        border_color = self.colors['primary'] if is_active else self.colors['border']
        pygame.draw.rect(self.modal_surface, border_color, rect, 2, border_radius=5)
        
        # Text
        display_text = text if text else "0"
        self.font_body.render_to(self.modal_surface, (rect.x + 10, rect.y + 6), 
                               display_text, self.colors['text_primary'])
        
        # Cursor
        if is_active:
            text_width = self.font_body.get_rect(display_text)[0]
            cursor_x = rect.x + 10 + text_width
            pygame.draw.line(self.modal_surface, self.colors['text_primary'],
                           (cursor_x, rect.y + 5), (cursor_x, rect.bottom - 5), 2)
        
        self.input_rects[key] = rect
    
    def _render_button(self, rect: pygame.Rect, key: str, text: str, color):
        """Render a button"""
        is_hovered = rect.collidepoint(self.mouse_pos)
        
        # Background
        if is_hovered:
            button_color = tuple(min(255, c + 20) for c in color)
        else:
            button_color = color
        
        pygame.draw.rect(self.modal_surface, button_color, rect, border_radius=6)
        pygame.draw.rect(self.modal_surface, self.colors['border'], rect, 1, border_radius=6)
        
        # Text
        text_surf, text_rect = self.font_body.render(text, self.colors['text_primary'])
        text_rect.center = rect.center
        self.modal_surface.blit(text_surf, text_rect)
        
        self.button_rects[key] = rect