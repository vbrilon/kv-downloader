"""Configuration management package for karaoke automation"""

from .config import *
from .config_manager import ConfigurationManager

__all__ = [
    'ConfigurationManager',
    # Export config constants that actually exist
    'USERNAME',
    'PASSWORD',
    'DOWNLOAD_FOLDER',
    'DELAY_BETWEEN_DOWNLOADS',
    'MAX_RETRIES',
    'DOWNLOAD_TIMEOUT',
    'COMMON_TRACK_TYPES',
    'LOGIN_URL',
    'SONGS_CONFIG_FILE',
    'MIN_KEY_ADJUSTMENT',
    'MAX_KEY_ADJUSTMENT',
    'load_songs_config'
]