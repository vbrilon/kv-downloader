#!/usr/bin/env python3
"""
Configuration Manager
Handles loading, validation, and processing of application configuration
Separated from config.py to keep config file clean
"""

import os
import yaml
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

class ConfigurationManager:
    """Manages application configuration with validation and defaults"""
    
    def __init__(self, songs_config_file: str = "songs.yaml"):
        self.songs_config_file = songs_config_file
        self.logger = logging.getLogger(__name__)
    
    def load_songs_config(self) -> List[Dict[str, Any]]:
        """Load and validate songs configuration from YAML file"""
        try:
            config_path = Path(self.songs_config_file)
            if not config_path.exists():
                self.logger.error(f"Songs config file '{self.songs_config_file}' not found. Please create it.")
                return []
            
            with open(config_path, 'r') as file:
                config = yaml.safe_load(file)
                songs = config.get('songs', [])
                
                if not songs:
                    self.logger.warning(f"No songs found in {self.songs_config_file}")
                    return []
                
                # Validate and process song entries
                validated_songs = []
                for i, song in enumerate(songs):
                    validated_song = self._validate_song_entry(song, i)
                    if validated_song:
                        validated_songs.append(validated_song)
                
                self.logger.info(f"Loaded {len(validated_songs)} valid songs from configuration")
                return validated_songs
                
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing songs config file: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error loading configuration: {e}")
            return []
    
    def _validate_song_entry(self, song: Dict[str, Any], index: int) -> Optional[Dict[str, Any]]:
        """Validate and process a single song entry"""
        
        # Check required fields
        if not self._has_required_fields(song, index):
            return None
        
        # Create validated song with defaults
        validated_song = {
            'url': song['url'].strip(),
            'name': song['name'].strip(),
            'description': song.get('description', '').strip(),
            'key': self._validate_key_value(song.get('key', 0), song['name'])
        }
        
        # Additional validation
        if not self._validate_url(validated_song['url']):
            self.logger.warning(f"Song '{validated_song['name']}' has potentially invalid URL")
        
        if not self._validate_name(validated_song['name']):
            self.logger.warning(f"Song name '{validated_song['name']}' may contain invalid characters for folder names")
        
        return validated_song
    
    def _has_required_fields(self, song: Dict[str, Any], index: int) -> bool:
        """Check if song has required fields"""
        missing_fields = []
        
        if 'url' not in song or not song['url']:
            missing_fields.append('url')
        
        if 'name' not in song or not song['name']:
            missing_fields.append('name')
        
        if missing_fields:
            self.logger.error(f"Song entry {index + 1} missing required fields: {missing_fields}")
            self.logger.debug(f"Invalid song entry: {song}")
            return False
        
        return True
    
    def _validate_key_value(self, key_value: Any, song_name: str) -> int:
        """Validate and normalize key adjustment value"""
        
        # Default to 0 if not specified
        if key_value is None:
            return 0
        
        try:
            key_int = int(key_value)
            
            # Validate range
            if key_int < -12 or key_int > 12:
                self.logger.warning(
                    f"Song '{song_name}': Key value {key_int} out of range (-12 to +12), setting to 0"
                )
                return 0
            
            return key_int
            
        except (ValueError, TypeError):
            self.logger.warning(
                f"Song '{song_name}': Invalid key value '{key_value}', setting to 0"
            )
            return 0
    
    def _validate_url(self, url: str) -> bool:
        """Basic URL validation"""
        if not url:
            return False
        
        # Check for karaoke-version.com URLs
        if 'karaoke-version.com' not in url.lower():
            return False
        
        # Check for HTTPS
        if not url.startswith('https://'):
            return False
        
        # Check for custombackingtrack path
        if 'custombackingtrack' not in url.lower():
            return False
        
        return True
    
    def _validate_name(self, name: str) -> bool:
        """Validate song name for filesystem compatibility"""
        if not name:
            return False
        
        # Check for invalid filesystem characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            if char in name:
                return False
        
        # Check length
        if len(name) > 100:
            return False
        
        return True
    
    def validate_configuration_file(self) -> bool:
        """Validate the configuration file exists and is readable"""
        try:
            config_path = Path(self.songs_config_file)
            
            if not config_path.exists():
                self.logger.error(f"Configuration file {self.songs_config_file} does not exist")
                return False
            
            if not config_path.is_file():
                self.logger.error(f"Configuration path {self.songs_config_file} is not a file")
                return False
            
            # Try to read and parse
            with open(config_path, 'r') as file:
                yaml.safe_load(file)
            
            self.logger.debug(f"Configuration file {self.songs_config_file} is valid")
            return True
            
        except yaml.YAMLError as e:
            self.logger.error(f"YAML syntax error in {self.songs_config_file}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error validating configuration file: {e}")
            return False
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get summary of current configuration"""
        songs = self.load_songs_config()
        
        summary = {
            'config_file': self.songs_config_file,
            'config_exists': Path(self.songs_config_file).exists(),
            'total_songs': len(songs),
            'songs_with_key_adjustment': len([s for s in songs if s['key'] != 0]),
            'key_adjustments': {s['name']: s['key'] for s in songs if s['key'] != 0}
        }
        
        return summary

# Create a default instance for backward compatibility
_default_config_manager = ConfigurationManager()

def load_songs_config() -> List[Dict[str, Any]]:
    """Backward compatibility function - use ConfigurationManager.load_songs_config() instead"""
    return _default_config_manager.load_songs_config()

def validate_configuration() -> bool:
    """Validate the current configuration file"""
    return _default_config_manager.validate_configuration_file()

def get_configuration_summary() -> Dict[str, Any]:
    """Get configuration summary"""
    return _default_config_manager.get_configuration_summary()