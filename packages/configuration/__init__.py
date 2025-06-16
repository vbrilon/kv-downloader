"""Configuration management package for karaoke automation"""

from .config import *
from .config_manager import ConfigurationManager, load_songs_config

__all__ = [
    'ConfigurationManager',
    # Core configuration constants (actively used)
    'USERNAME',
    'PASSWORD',
    'DOWNLOAD_FOLDER',
    # Test-specific constants (limited usage but needed for tests)
    'DELAY_BETWEEN_DOWNLOADS',
    'MAX_RETRIES', 
    'DOWNLOAD_TIMEOUT',
    'LOGIN_URL',
    'SONGS_CONFIG_FILE',
    # Configuration function
    'load_songs_config'  # From ConfigurationManager
    # Note: MIN_KEY_ADJUSTMENT, MAX_KEY_ADJUSTMENT, COMMON_TRACK_TYPES removed - unused
]