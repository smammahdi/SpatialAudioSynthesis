"""
pygame_app/src/config.py
Configuration settings for the Spatial Audio System
"""

class Config:
    """Application configuration constants"""
    
    # Window settings
    WINDOW_WIDTH = 1400
    WINDOW_HEIGHT = 900
    TARGET_FPS = 60
    
    # Audio settings
    AUDIO_SAMPLE_RATE = 44100
    AUDIO_BUFFER_SIZE = 1024
    AUDIO_CHANNELS = 2
    
    # Elegant color scheme (no emojis, elegant design)
    COLORS = {
        # Primary colors
        'background': (15, 15, 20),           # Very dark blue-gray
        'surface': (25, 30, 40),              # Dark surface
        'surface_light': (35, 42, 55),        # Lighter surface
        'surface_hover': (45, 52, 65),        # Hover state
        'panel_bg': (30, 35, 45),             # Panel background
        
        # Accent colors
        'primary': (70, 130, 200),            # Elegant blue
        'primary_dark': (50, 100, 160),       # Darker blue
        'secondary': (120, 180, 80),          # Elegant green
        'accent': (200, 150, 80),             # Warm accent
        
        # Text colors
        'text_primary': (240, 245, 250),      # Light text
        'text_secondary': (180, 190, 200),    # Secondary text
        'text_muted': (140, 150, 160),        # Muted text
        'text_light': (255, 255, 255),        # White text for dark backgrounds
        'text_dark': (40, 50, 60),            # Dark text for light backgrounds
        
        # Status colors
        'success': (80, 180, 120),            # Success green
        'warning': (220, 180, 80),            # Warning amber
        'error': (220, 80, 80),               # Error red
        'info': (80, 150, 220),               # Info blue
        
        # UI elements
        'border': (60, 70, 85),               # Border color
        'border_light': (80, 90, 105),        # Light border
        'shadow': (0, 0, 0, 50),              # Shadow color
        
        # Device-specific colors for consistent theming (matches chart_colors)
        'device_colors': [
            (70, 130, 200),   # Blue
            (120, 180, 80),   # Green
            (200, 150, 80),   # Orange
            (180, 80, 180),   # Purple
            (80, 180, 180),   # Cyan
            (200, 80, 120),   # Pink
            (150, 200, 80),   # Lime
            (200, 120, 80),   # Coral
            (100, 200, 160),  # Mint
            (200, 100, 100),  # Red
        ],
        
        # Chart colors (for device visualization)
        'chart_colors': [
            (70, 130, 200),   # Blue
            (120, 180, 80),   # Green
            (200, 150, 80),   # Orange
            (180, 80, 180),   # Purple
            (80, 180, 180),   # Cyan
            (200, 80, 120),   # Pink
            (150, 200, 80),   # Lime
            (200, 120, 80),   # Coral
            (100, 200, 160),  # Mint
            (200, 100, 100),  # Red
        ]
    }
    
    # Typography
    FONTS = {
        'title': ('Segoe UI', 28),
        'h1': ('Segoe UI', 24),
        'h2': ('Segoe UI', 20),
        'h3': ('Segoe UI', 18),
        'subtitle': ('Segoe UI', 20),
        'heading': ('Segoe UI', 16),
        'body': ('Segoe UI', 14),
        'caption': ('Segoe UI', 12),
        'small': ('Segoe UI', 10),
        'tiny': ('Segoe UI', 8)
    }
    
    # Layout settings
    LAYOUT = {
        'padding': 20,
        'margin': 10,
        'border_radius': 8,
        'card_spacing': 15,
        'section_spacing': 25,
        'button_height': 36,
        'input_height': 32,
        'sidebar_width': 320,
        'header_height': 60
    }
    
    # Animation settings
    ANIMATION = {
        'duration_fast': 0.15,
        'duration_normal': 0.25,
        'duration_slow': 0.4,
        'easing': 'ease_out'
    }
    
    # Device settings
    DEVICE = {
        'scan_timeout': 30,     # seconds
        'connection_timeout': 10,
        'max_devices': 8,
        'demo_cycle_duration': 30,  # seconds
        'distance_update_rate': 2,  # Hz
    }
    
    # Audio processing
    AUDIO_PROCESSING = {
        'min_frequency': 200,
        'max_frequency': 1000,
        'default_volume': 75,
        'volume_smoothing': 0.1,
        'synthesis_quality': 'high'
    }
    
    # Debug settings - control debug output for different subsystems
    DEBUG = {
        'PRINT_DISTANCE_UPDATES': False,    # Frequent distance updates from sensors
        'PRINT_VOLUME_CHANGES': False,      # Volume level changes
        'PRINT_DEVICE_SCANNING': True,      # Device discovery and connection
        'PRINT_AUDIO_EVENTS': True,         # Audio playback events
        'PRINT_UI_INTERACTIONS': True,      # UI button clicks and interactions
        'PRINT_BLUETOOTH_EVENTS': True,     # Bluetooth connection events
        'PRINT_VALIDATION_ERRORS': True,    # Input validation failures
        'PRINT_SYSTEM_STARTUP': True,       # Application initialization
        'PRINT_PERFORMANCE_METRICS': False, # Performance timing data
        'PRINT_FILE_OPERATIONS': True,      # File upload/download operations
    }
    
    # UI states
    UI_STATES = {
        'collapsed_height': 40,
        'expanded_min_height': 120,
        'button_padding': 8,
        'slider_width': 200,
        'dropdown_width': 180
    }
    
    @classmethod
    def get_chart_color(cls, index: int) -> tuple:
        """Get chart color by index (cycles through available colors)"""
        colors = cls.COLORS['chart_colors']
        return colors[index % len(colors)]
    
    @classmethod
    def get_font(cls, font_type: str) -> tuple:
        """Get font configuration by type"""
        return cls.FONTS.get(font_type, cls.FONTS['body'])
    
    @classmethod
    def get_color_with_alpha(cls, color_name: str, alpha: int) -> tuple:
        """Get color with alpha channel"""
        color = cls.COLORS.get(color_name, (255, 255, 255))
        if len(color) == 3:
            return (*color, alpha)
        return color
