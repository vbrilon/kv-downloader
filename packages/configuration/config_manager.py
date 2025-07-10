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
        # Generate name from URL if not provided
        song_name = song.get('name', '').strip()
        if not song_name:
            song_name = self._generate_name_from_url(song['url'])
        
        validated_song = {
            'url': song['url'].strip(),
            'name': song_name,
            'description': song.get('description', '').strip(),
            'key': self._validate_key_value(song.get('key', 0), song_name)
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
        
        # Note: 'name' is now optional - will be auto-generated if not provided
        
        if missing_fields:
            self.logger.error(f"Song entry {index + 1} missing required fields: {missing_fields}")
            self.logger.debug(f"Invalid song entry: {song}")
            return False
        
        return True
    
    def _generate_name_from_url(self, url: str) -> str:
        """Generate a song name from the URL when name is not provided"""
        try:
            # Extract the path part after custombackingtrack
            # Example: https://www.karaoke-version.com/custombackingtrack/artist-title.html
            if 'custombackingtrack/' in url:
                path_part = url.split('custombackingtrack/')[-1]
                # Remove .html extension if present
                if path_part.endswith('.html'):
                    path_part = path_part[:-5]
                
                # Handle apostrophe patterns in URLs - General solution
                # Transform patterns like "mama-i-m-coming-home" -> "mama-i'm-coming-home"
                import re
                
                # General pattern: Replace single letters surrounded by hyphens with apostrophes
                # This handles most English contractions where letters are separated by hyphens
                # Examples: "don-t" -> "don't", "i-m" -> "i'm", "we-re" -> "we're"
                
                def restore_apostrophes(text):
                    """Restore apostrophes in common English contractions from URL patterns"""
                    # More precise pattern matching for common contractions
                    
                    # Handle specific contraction patterns that are commonly found in URLs
                    # These patterns are more conservative and target actual contractions
                    
                    # Pattern 1: Common contractions ending in 't (don't, can't, won't, etc.)
                    text = re.sub(r'\b(\w+)-t\b', r"\1't", text, flags=re.IGNORECASE)
                    
                    # Pattern 2: Common contractions ending in 'm (I'm, etc.)
                    text = re.sub(r'\b(\w+)-m\b', r"\1'm", text, flags=re.IGNORECASE)
                    
                    # Pattern 3: Common contractions ending in 're (we're, you're, they're)
                    text = re.sub(r'\b(\w+)-re\b', r"\1're", text, flags=re.IGNORECASE)
                    
                    # Pattern 4: Common contractions ending in 's (it's, that's, etc.)
                    text = re.sub(r'\b(\w+)-s\b', r"\1's", text, flags=re.IGNORECASE)
                    
                    # Pattern 5: Common contractions ending in 'll (I'll, we'll, etc.)
                    text = re.sub(r'\b(\w+)-ll\b', r"\1'll", text, flags=re.IGNORECASE)
                    
                    # Pattern 6: Common contractions ending in 've (I've, we've, etc.)
                    text = re.sub(r'\b(\w+)-ve\b', r"\1've", text, flags=re.IGNORECASE)
                    
                    # Pattern 7: Common contractions ending in 'd (I'd, we'd, etc.)
                    text = re.sub(r'\b(\w+)-d\b', r"\1'd", text, flags=re.IGNORECASE)
                    
                    return text
                
                path_part = restore_apostrophes(path_part)
                
                # Replace remaining hyphens with spaces and title case
                name = path_part.replace('-', ' ').title()
                
                # Clean up invalid characters but preserve apostrophes
                invalid_chars = '<>:"/\\|?*'  # Removed apostrophe from invalid chars
                for char in invalid_chars:
                    name = name.replace(char, '_')
                
                # Limit length
                if len(name) > 100:
                    name = name[:97] + '...'
                
                return name if name else "Unknown Song"
            else:
                return "Unknown Song"
                
        except Exception as e:
            self.logger.warning(f"Could not generate name from URL '{url}': {e}")
            return "Unknown Song"
    
    def _validate_key_value(self, key_value: Any, song_name: str) -> int:
        """Validate and normalize key adjustment value
        
        Accepts multiple formats:
        - Integer: 2, -3, 0
        - String with explicit sign: "+2", "-3", "+0"
        - String without sign: "2", "3" (treated as positive)
        """
        
        # Default to 0 if not specified
        if key_value is None:
            return 0
        
        try:
            # Handle string inputs (with or without explicit + sign)
            if isinstance(key_value, str):
                key_value = key_value.strip()
                
                # Empty string defaults to 0
                if not key_value:
                    return 0
                
                # Handle explicit positive sign "+2" -> 2
                if key_value.startswith('+'):
                    key_value = key_value[1:]  # Remove the + sign
                
                # Convert to integer
                key_int = int(key_value)
            else:
                # Handle numeric inputs - only accept integers, reject floats
                if isinstance(key_value, float):
                    raise ValueError(f"Float values not supported: {key_value}")
                key_int = int(key_value)
            
            # Validate range
            if key_int < -12 or key_int > 12:
                self.logger.warning(
                    f"Song '{song_name}': Key value {key_int} out of range (-12 to +12), setting to 0"
                )
                return 0
            
            return key_int
            
        except (ValueError, TypeError) as e:
            self.logger.warning(
                f"Song '{song_name}': Invalid key value '{key_value}', setting to 0. Error: {e}"
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